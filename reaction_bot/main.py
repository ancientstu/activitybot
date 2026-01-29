import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import load_config
from db import Database
from handlers import all_routers

logging.basicConfig(level=logging.INFO)


async def main():
    config = load_config()

    db = Database(config.db_path)
    await db.init()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    for r in all_routers:
        dp.include_router(r)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, config=config, db=db)


if __name__ == "__main__":
    asyncio.run(main())