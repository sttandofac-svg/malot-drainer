# database/db.py  ← ПОЛНОСТЬЮ ЗАМЕНИ
import aiosqlite
from typing import List, Dict, Optional

DB_NAME = "mass_sender.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT UNIQUE NOT NULL,
                api_id INTEGER NOT NULL,
                api_hash TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS chat_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                username TEXT,
                group_id INTEGER,
                FOREIGN KEY(group_id) REFERENCES chat_groups(id)
            );

            CREATE TABLE IF NOT EXISTS broadcast_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                total INTEGER,
                success INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                blocked INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
    print("✅ База данных инициализирована")

# CRUD функции будут добавлены в handlers
