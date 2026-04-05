import asyncio
import logging
import sys

print("=== MASS SENDER v2 STARTING ON RAILWAY ===")
print("Python version:", sys.version)

from config import BOT_TOKEN, OWNER_ID
from database.db import init_db
from utils.pyrogram_manager import pyrogram_manager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.start import router as start_router
from handlers.accounts import router as accounts_router
from handlers.chats import router as chats_router
from handlers.broadcast import router as broadcast_router
from handlers.callbacks import router as callbacks_router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start_router)
dp.include_router(accounts_router)
dp.include_router(chats_router)
dp.include_router(broadcast_router)
dp.include_router(callbacks_router)

async def main():
    await init_db()
    print("🚀 Mass Sender v2 успешно запущен на Railway!")
    print(f"Владелец бота: {OWNER_ID}")
    print("✅ Все модули загружены")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
