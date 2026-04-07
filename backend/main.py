<<<<<<< HEAD
import asyncio
import logging

from aiogram import Bot

from app.bot import create_dispatcher
from app.config import settings
from app.db import init_db


async def run() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Set it in environment variables.")
    if not settings.webapp_url:
        raise RuntimeError("WEBAPP_URL is empty. Set GitHub Pages URL.")

    init_db()
    bot = Bot(token=settings.bot_token)
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
=======
import asyncio
import logging

from aiogram import Bot

from app.bot import create_dispatcher
from app.config import settings
from app.db import init_db


async def run() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Set it in environment variables.")
    if not settings.webapp_url:
        raise RuntimeError("WEBAPP_URL is empty. Set GitHub Pages URL.")

    init_db()
    bot = Bot(token=settings.bot_token)
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
>>>>>>> 812b10437b3ace4a467d917045a8e96128a6b6a4
