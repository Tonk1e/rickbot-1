from plugin import Plugin
import asyncio

class Hello(Plugin):

    async def on_message(self, message):
        if message.content == '!hello':
            await self.rickbot.send_message(message.channel,
                'Hello! {} from {}!'.format(
                    message.author.mention,
                        message.server.name
            ))
