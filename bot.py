# bot.py  ← ПОЛНОСТЬЮ ЗАМЕНИ СОДЕРЖИМОЕ НА ЭТО (минимальная версия для теста деплоя)

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Защитный вывод для диагностики Railway
print("=== MASS SENDER v2 STARTING ===")
print("Python version:", sys.version)

try:
    import aiogram
    print(f"aiogram imported: {aiogram.__version__}")
except Exception as e:
    print(f"ERROR importing aiogram: {e}")

try:
    import pyrogram
    print(f"pyrogram imported: {pyrogram.__version__}")
except Exception as e:
    print(f"ERROR importing pyrogram: {e}")

print("=== IMPORTS CHECK COMPLETED ===")

from config import API_TOKEN, OWNER_ID
from database.db import init_db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def main():
    await init_db()
    print("🚀 Mass Sender v2 успешно запущен на Railway!")
    # Пока только запуск — остальные handlers добавим позже
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
