class PluginMount(type):

    def __init__(cls, name, bases, attrs):
        """ Called when a plugin derrived class is imported """

        if not hasattr(cls, 'plugins'):
            cls.plugins = []
        else:
            cls.plugins.append(cls)

class Plugin(object, metaclass=PluginMount):

    def __init__(self, rickbot):
        self.rickbot = rickbot
        self.db = rickbot.db

    def key(self, k):
        prefix = '{0.__class__.__name__}.{1}:'.format(self, server.id)
