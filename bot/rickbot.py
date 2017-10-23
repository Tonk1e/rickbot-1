import discord
import asyncio
import logging
from plugin_manager import PluginManager
from database import Db
from utils import find_server
from time import time

from plugins.commands import Commands
from plugins.help import Help
from plugins.levels import Levels
from plugins.welcome import Welcome

log = logging.getLogger('discord')


class RickBot(discord.Client):
    def __init__(self, *args, **kwargs):
        self.redis_url = kwargs.get('redis_url')
        self.db = Db(self.redis_url)
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()
        self.last_messages = []

    async def on_ready(self):
        with open('welcome_ascii.txt') as f:
            print(f.read())

        self.add_all_servers()
        discord.utils.create_task(self.heartbeat(5), loop=self.loop)
        discord.utils.create_task(self.update_stats(60), loop=self.loop)

    async def add_all_servers(self):
        log.debug('Syncing servers and DB')
        self.db.redis.delete('servers')
        for server in self.servers:
            log.debug('Adding server {}\'s ID to DB'.format(server.id))
            self.db.redis.sadd('servers', server.id)

    async def send_message(self, *args, **kwargs):
        server = args[0].server
        log.info('RickBot@{} >> {}'.format(server.name, args[1].replace('\n', '~')))
        await super().send_message(*args, **kwargs)

    async def on_server_join(self, server):
        log.info('Joined {} server: {}!'.format(server.owner.name, server.name))
        log.debug('Adding self {}\'s ID to DB'.format(server.id))
        self.db.redis.sadd('servers', server.id)
        self.db.redis.set('server:{}:name'.format(server.id), server.name)
        if server.icon:
            self.db.redis.set('server:{}:icon'.format(server.id), server.icon)

    async def on_server_remove(self, server):
        log.info('Leaving {} server: {}'.format(server.owner.name, sever.name))
        log.debug('Removing server {}\'s from DB'.format(server.id))
        self.db.redis.srem('servers', server.id)

    async def heartbeat(self, interval):
        while self.is_logged_in:
            self.db.redis.set('heartbeat', 1, ex=interval)
            await asyncio.sleep(0.9 * interval)

    async def update_stats(self, interval):
        while self.is_logged_in:
            # Total members and online members
            members = list(self.get_all_members())
            online_members = filter(lambda m: m.status is discord.Status.online,
                                    members)
            online_members = list(online_members)
            self.db.redis.set('rickbot:stats:online_members',
                              len(online_members))
            self.db.redis.set('rickbot:stats:members', len(members))

            # Last messages
            for index, timestamp in enumerate(self.last_messages):
                if timestamp + interval < time():
                    self.last_messages.pop(index)
            self.db.redis.set('rickbot:stats:last_messages',
                              len(self.last_messages))

            await asyncio.sleep(interval)

    async def _run_plugin_event(self, plugin, event, *args, **kwargs):
        # A yummy modified coroutine that is based on Client._run_event
        try:
            await getattr(plugin, event)(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_error(event, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    def dispatch(self, event, *args, **kwargs):
        # A list of events that are avalible from the plugins.
        plugin_events = (
            'message',
            'message_delete',
            'message_edit',
            'channel_delete',
            'channel_create',
            'channel_update',
            'member_join',
            'member_update',
            'server_update',
            'server_role_create',
            'server_role_delete',
            'server_role_update',
            'voice_state_update',
            'member_ban',
            'member_unban',
            'typing'
        )

        # Total number of messages stats update
        if event == 'message':
            self.db.redis.incr('rickbot:stats:messages')
            self.last_messages.append(time())

        log.debug('Dispatching event {}'.format(event))
        method = 'on_' + event
        handler = 'handle_' + event

        if hasattr(self, handler):
            getattr(self, handler)(*args, **kwargs)

        if event in plugin_events:
            server_context = find_server(*args, **kwargs)
            if server_context is None:
                return

            # For each plugin that the server has enabled
            for plugin in enabled_plugins:
                if hasattr(plugin, method):
                    discord.utils.create_task(self._run_plugin_event(\
                    plugin, method, *args, **kwargs), loop=self.loop)
        else:
            if hasattr(self, method):
                discord.utils.channel_create(self._run_event(method, *args, \
                **kwargs), loop=self.loop)

    def run(self, token):
        self.token = token
        self.headers['authorization'] = token
        self._is_logged_in.set()
        try:
            self.loop.run_until_complete(self.connect())
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.logout())
            pending = async.Task.all_tasks()
            gathered = asyncio.gather(*pending)
            try:
                gathered.cancel()
                self.loop.run_forever()
                gathered.exception()
            except:
                pass
        finally:
            self.loop.close()
