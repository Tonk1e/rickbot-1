from plugin import Plugin
import asyncio

class Commands(Plugin):

    async def on_message(self, message):
        storage = self.get_storage(message.server)
        commands = storage.smembers('commands')
        if message.content in commands:
            response = storage.get('command:{}'.format(message.content))
            await self.rickbot.send_message(
                message.channel,
                response
            )
