# database/db.py  ← СОЗДАЙ ПАПКУ database И ФАЙЛ db.py В НЕЙ
import aiosqlite
import os

DB_NAME = "mass_sender.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT UNIQUE NOT NULL,
                api_id INTEGER NOT NULL,
                api_hash TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 0
            )
        """)
        await db.commit()
    print(f"✅ База данных инициализирована: {DB_NAME}")

# Пустые заглушки для остальных таблиц — добавим позже
