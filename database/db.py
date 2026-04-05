# database/db.py
import aiosqlite
import json
from typing import List, Dict, Optional

DB_NAME = "mass_sender.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                session_name TEXT UNIQUE,
                api_id INTEGER,
                api_hash TEXT,
                is_active BOOLEAN DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_groups (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                username TEXT,
                group_id INTEGER,
                FOREIGN KEY(group_id) REFERENCES chat_groups(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_stats (
                id INTEGER PRIMARY KEY,
                account_id INTEGER,
                total INTEGER,
                success INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                blocked INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# ... (остальные CRUD функции: add_account, get_accounts, add_chat, etc.)
# Полный код базы будет в следующем модуле по запросу
