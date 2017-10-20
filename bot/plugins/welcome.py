from plugin import Plugin
import asyncio
import logging
from types import MethodTypes
import discord

log = logging.getLogger('discord')

class Welcome(Plugin):

    fancy_name = "Welcome"

    async def on_member_join(self, member):
        server = member.server
        storage = self.get_storage(server)
        welcome_message = storage.get('welcome_message').format(
            server = server.name,
            user = member.mention
        )
        channel_name = storage.get('channel_name')

        destination = server
        channel = discord.utils.find(lambda c: c.name == channel_name,
            server.channels)
        if channel is not None:
            destination = channel

        await self.rickbot.send_message(destination, welcome_message)
