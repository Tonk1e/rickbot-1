from plugin import Plugin
import asyncio
import logging

log = logging.getLogger('discord')

class Commands(Plugin):

    dank_name = 'Custom Commands'

    def get_commands(self, server):
        storage = self.get_storage(server)
        commands = sorted(storage.smembers('commands'))
        cmds = []
        for command in commands:
            cmd = {
                'name': command
            }
            cmds.append(cmd)
        return cmds

    async def on_message(self, message):
        storage = self.get_storage(message.server)
        commands = storage.smembers('commands')
        if message.content in commands:
            log.info('{}#{}@{} >> {}'.format(
                message.author.name,
                message.author.discriminator,
                message.server.name,
                message.content
            ))
            response = storage.get('command:{}'.format(message.content))
            await self.rickbot.send_message(
                message.channel,
                response
            )
