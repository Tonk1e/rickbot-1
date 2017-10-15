from rickbot import RickBot
import os
import logging

logging.basicConfig(level=logging.INFO)

token = os.getenv('RICKBOT_TOKEN')
redis_url = os.getenv('REDIS_URL')
rickbot_debug = os.getenv('RICKBOT_DEBUG')

if rickbot_debug:
    logging.basicConfig(level=logging.DEBUG)

bot = RickBot(redis_url=redis_url)
bot.run(token)
