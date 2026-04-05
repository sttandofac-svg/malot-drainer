# bot.py  ← ПОЛНОСТЬЮ ЗАМЕНИ НА ЭТОТ ФАЙЛ
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

print("=== MASS SENDER v2 STARTING ON RAILWAY ===")
print("Python version:", sys.version)

from config import BOT_TOKEN, OWNER_ID

# Импорт всех роутеров
from handlers.start import router as start_router
from handlers.accounts import router as accounts_router
from handlers.chats import router as chats_router
from handlers.broadcast import router as broadcast_router
from handlers.callbacks import router as callbacks_router

from database.db import init_db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(start_router)
dp.include_router(accounts_router)
dp.include_router(chats_router)
dp.include_router(broadcast_router)
dp.include_router(callbacks_router)

async def main():
    await init_db()
    print("🚀 Mass Sender v2 успешно запущен на Railway!")
    print(f"Владелец: {OWNER_ID}")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
