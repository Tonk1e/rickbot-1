import logging
import asyncio
from plugin import Plugin

log = logging.getLogger('discord')

class PluginManager:

    def __init__(self, rickbot):
        self.rickbot = rickbot
        self.db = rickbot.db
        self.rickbot.plugins = []

    def load(self, plugin):
        log.info('Loading plugin {}'.format(plugin.__name__))
        plugin_instance = plugin(self.rickbot)
        self.rickbot.plugins.append(plugin_instance)
        log.info('Plugin {} loaded'.format(plugin.__name__))

    def load_all(self):
        for plugin in Plugin.plugins:
            self.load(plugin)

    def get_all(self, server):
        plugin_names = self.db.redis.smembers('plugin:{}'.format(server.id))
        plugins = []
        for plugin in self.rickbot.plugins:
            if plugin.__class__.__name__ in plugin_names:
                plugins.append(plugin)
        return plugins
