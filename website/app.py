from flask import Flask, session, request, url_for, render_template, \
redirect, jsonify, make_response
import os
from functools import wraps
from requests_oauthlib import OAuth2Session
import redis
import json

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = ""

REDIS_URL = os.environ.get('REDIS_URL')
OAUTH2_CLIENT_ID = os.environ['OAUTH2_CLIENT_ID']
OAUTH2_CLIENT_SECRET = os.environ['OAUTH2_CLIENT_SECRET']
OAUTH2_REDIRECT_URI = 'http://localhost:5000/confirm_login'
API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

db = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# CSRF Security
@app.before_request
def csrf_protect():
    if request.method = "POST":
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = some_random_string()
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

def token_updater(token):
    session['oauth2_token'] = token

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = session.get('user')
        if user is None:
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return wrapper

def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': OAUTH2_CLIENT_ID,
            'client_secret': OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater)

@app.route('/')
def index():
    oauth2_token = requests.cookies.get('oauth2_token')
    # Hm. I remember you!
    if oauth2_token:
        oauth2_token = json.loads(oauth2_token)
        session['oauth2_token'] = oauth2_token
        try:
            get_or_update_user()
            return redirect(url_for('select_server'))
        except:
            pass
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
def logout():
    session.pop('user')
    resp = make_response(redirect(url_for('index')))
    resp.set_cookie('oauth2_token', '', expires=0)
    return resp

@app.route('/login')
def login():
    user = session.get('user')
    if user is not None:
        return redirect(url_for('select_server'))

    scope = 'identify guilds'.split()
    discord = make_session(scope=scope)
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)

@app.route('/confirm_login')
def confirm_login():
    if request.values.get('error'):
        return redirect(url_for('index'))

    discord = make_session(state=session.get('oauth2_state'))
    token = discord.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url)
    session['oauth2_token'] = token
    get_or_update_user()

    resp = make_response(redirect(url_for('select_server')))
    # Mark my words; I'll remember you!
    resp.set_cookie('oauth2_token', json.dumps(token), max_age=3600*24*7)

    return resp

def get_or_update_user():
    oauth2_token = session.get('oauth2_token')
    if oauth2_token:
        discord = make_session(token=oauth2_token)
        session['user'] = discord.get(API_BASE_URL + '/users/@me').json()
        session['guilds'] = discord.get(
                            API_BASE_URL + '/users/@me/guilds').json()
        print(url_for('static', filename='img/no_logo.png'))
        if session['user'].get('avatar') is None:
            session['user']['avatar'] = url_for('static',
                                                filename='img/no_logo.png')
        else:
            session['user']['avatar'] = "https://cdn.discordapp.com/avatars" \
            + session['user']['id'] + "/" + session['user']['avatar'] + ".jpg"


def get_user_servers(user, guilds):
    return list(filter(lambda g: g['owners'] is True, guilds))

@app.route('/servers')
@require_auth
def select_server():
    get_or_update_user()
    user_servers = get_user_servers(session['user'], session['guilds'])

    return render_template('select-server.html', user_servers=user_servers)

def server_check(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        server_id = kwargs.get('server_id')
        server_ids = db.smembers('servers')

        if str(server_id) not in server_ids:
            url = "https://discordapp.com/oauth2/authorize?&client_id={}"\
                "&scope=bot&permissions={}&guild_id={}".format(
                    OAUTH2_CLIENT_ID,
                    '1'*32,
                    server_id
                )
            return redirect(url)

        return f(*args, **kwargs)
    return wrapper

def require_bot_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        server_id = kwargs.get('server_id')
        user_servers = get_user_servers(session['user'], session['guilds'])
        if str(server_id) not in list(map(lambda g: g['id'], user_servers)):
            return redirect(url_for('select_server'))

        return r(*args, **kwargs)
    return wrapper

# This will soon be dashboard stuff. For now it is just some text...
@app.route('/dashboard/<int:server_id>')
@require_auth
@require_bot_admin
@server_check
def dashboard(server_id):
    servers = session['guilds']
    server = list(filter(lambda g: g['id'] == str(server_id), servers))[0]
    enabled_plugins = db.smembers('plugins:{}'.format(server_id))
    return render_template('dashboard.html', server=server,
                           enabled_plugins=enabled_plugins)

@app.route('/dashboard/<int:server_id>/commands')
@require_auth
@require_bot_admin
@server_check
def plugin_commands(server_id):
    disable = request.args.get('disable')
    if disable:
        db.srem('plugins:{}'.format(server_id), 'Commands')
        return redirect(url_for('dashboard', server_id=server_id))

    db.sadd('plugins:{}'.format(server_id), 'Commands')
    servers = session['guilds']
    server = list(filter(lambda g: g['id'] == str(server_id), servers))[0]
    enabled_plugins = db.smembers('plugins:{}'.format(server_id))
    return render_template('plugin_commands.html', server=server,
                           enabled_plugins=enabled_plugins)

app.run()
