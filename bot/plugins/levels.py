from plugin import Plugin
import logging
import asyncio
from random import randint

log = logging.getLogger('discord')

class Levels(Plugin):

    dank_name = 'Levels'

    def get_commands(self, server):
        commands = [
            {
                'name': '!levels',
                'description': 'Gives you the leaderboard for your server!'
            },
            {
                'name': '!xp',
                'description': 'Gives you your xp, level and rank'
            }
        ]
        return commands

    @staticmethod
    def _get_level_xp(n):
        return 100*(1.2**n)

    @staticmethod
    def _get_level_from_xp(xp):
        remaining_xp = int(xp)
        level = 0
        while remaining_xp >= Levels._get_level_xp(level):
            remaining_xp -= Levels._get_level_xp(level)
            level += 1
        return level

    async def on_message(self, message):
        if message.author.id == self.rickbot.user.id:
            return

        if message.content == '!levels':
            url = 'http://rick-bot.xyz/levels/{}'.format(message.server.id)
            response = "Go and check out **{}**\'s leaderboard " \
                "here: {} :wink:".format(
                    message.server.name,
                    url
                )
            await self.rickbot.send_message(message.channel, response)
            return

        if message.content == '!xp':
            storage = self.get_storage(message.server)
            player = message.author
            players = storage.smembers('players')
            if player.id not in players:
                await self.rickbot.send_message(message.channel,
                    "**{}**. It looks like you haven't been ranked yet. Get "\
                    "talking in the chats to get ranked and " \
                    "assigned xp!".format(
                        player.mention
                    )
                )
                return

            total_player_xp = storage.get('player:{}:xp'.format(player.id))
            player_lvl = storage.get('player:{}:lvl'.format(player.id))
            x = 0
            for l in range(0,int(player_lvl)):
                x += 100*(1.2**l)
            remaining_xp = int(int(player_total_xp) - x)
            level_xp = int(Levels._get_level_xp(int(player_lvl)))
            players = self.rickbot.db.redis.sort('Levels.{}:players'.format(message.server.id),
                        by='Levels.{}:player:*:xp'.format(message.server.id),
                        start=0,
                        num=1,
                        desc=True)
            player_rank = players.index(player.id)+1

            response = '{}: **Level {}** | **XP {}/{}** | **Total XP {}** | **Rank {}/{}**'.format(
                player.mention,
                player_lvl,
                remaining_xp,
                level_xp,
                player_total_xp,
                player_rank,
                len(players)
            )

            await self.rickbot.send_message(message.channel, response)
            return

        storage = self.get_storage(server)

        # Update le player's profile
        player = message.author
        server = message.server
        self.rickbot.db.redis.set('server:{}:name'.format(server.id), server.name)
        if server.icon:
            self.rickbot.db.redis.set('server:{}:icon'.format(server.id), server.icon)
        if server.icon:
            storage.sadd('server:icon', server.icon)
        storage.sadd('players', player.id)
        storage.set('player:{}:name'.format(player.id), player.name)
        storage.set('player:{}:discriminator'.format(player.id), player.discriminator)
        storage.set('player:{}:avatar'.format(player.id), player.avatar)

        # Is the player now ready?
        check = storage.get('player:{}:check'.format(player.id))
        if check:
            return

        # Get the player's level
        lvl = storage.get('player:{}:lvl'.format(player.id))
        if lvl is None:
            storage.set('player:{}:lvl'.format(player.id), 0)
            lvl = 0
        else:
            lvl = int(lvl)

        # Give player random int xp between 5 and 10
        storage.incr('player:{}:xp'.format(player.id), amount=randint(5,10))
        # Block player for a 60 sec cooldown
        storage.set('player:{}:check'.format(player.id), '1', ex=60)
        # Get the new player xp
        player_xp = storage.get('player:{}:xp'.format(player.id))
        # Update the levels
        storage.set('player:{}:lvl'.format(player.id), Levels._get_level_from_xp(player_xp))
        # Now compare the level before and after
        new_level = int(storage.get('player:{}:lvl'.format(player.id)))
        if new_level != lvl:
            # Check if the annoucement is ok
            annoucement_enabled = storage.get('annoucement_enabled')
            if annoucement_enabled:
                annoucement = storage.get('annoucement')
                await self.rickbot.send_message(message.channel, annoucement.format(
                    player=player.mention,
                    level=new_level
                ))
