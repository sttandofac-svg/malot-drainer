# bot.py  ← ЗАМЕНИ ПОЛНОСТЬЮ на эту версию (временная, чтобы бот запустился)
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
from database.db import init_db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Пустые заглушки для роутеров, чтобы не падал импорт
from aiogram import Router
start_router = Router()
accounts_router = Router()
chats_router = Router()
broadcast_router = Router()
callbacks_router = Router()

dp.include_router(start_router)
dp.include_router(accounts_router)
dp.include_router(chats_router)
dp.include_router(broadcast_router)
dp.include_router(callbacks_router)

async def main():
    await init_db()
    print("🚀 Mass Sender v2 успешно запущен на Railway!")
    print(f"Владелец бота: {OWNER_ID}")
    print("⚠️  Полные handlers пока не загружены — бот работает в минимальном режиме")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
