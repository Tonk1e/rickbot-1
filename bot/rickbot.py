import discord
import asyncio
import logging
from plugin_manager import PluginManager
from database import Db
from utils import find_server

from plugins.hello import Hello
from plugins.commands import Commands

log = logging.getLogger('discord')


class RickBot(discord.Client):
    def __init__(self, *args, **kwargs):
        self.redis_url = kwargs.get('redis_url')
        self.db = Db(self.redis_url)
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()

    async def on_ready(self):
        with open('welcome_ascii.txt') as f:
            print(f.read())

        await self.heartbeat(5)

    async def heartbeat(self, interval):
        while self.is_logged_in:
            self.db.redis.set('heartbeat', 1, ex=interval)
            await asyncio.sleep(0.9 * interval)

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
