# bot.py — точка входа
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import API_TOKEN, OWNER_ID
from database.db import init_db
from handlers import start, accounts, chats, broadcast, callbacks

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация роутеров
dp.include_router(start.router)
dp.include_router(accounts.router)
dp.include_router(chats.router)
dp.include_router(broadcast.router)
dp.include_router(callbacks.router)

async def main():
    await init_db()
    print("🚀 Mass Sender v2 запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
