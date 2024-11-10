import asyncio
import logging
import sys
from os import getenv

from dotenv import load_dotenv
from bot import BookReaderBot

if __name__ == '__main__':
    load_dotenv()
    book_bot = BookReaderBot(
        bot_token=getenv("BOT_TOKEN")
    )
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(book_bot.main())