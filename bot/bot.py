from rickbot import RickBot
import os
import logging

logging.basicConfig(level=logging.INFO)

token = os.getenv('RICKBOT_TOKEN')
redis_url = os.getenv('REDIS_URL')

bot = RickBot(redis_url=redis_url)
bot.run(token)
