# utils/pyrogram_manager.py  ← СОЗДАЙ ПАПКУ utils И ФАЙЛ
import asyncio
from pyrogram import Client
from typing import Dict, Optional
import os

class PyrogramManager:
    def __init__(self):
        self.clients: Dict[int, Client] = {}  # account_id -> Client
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)

    async def add_account(self, account_id: int, session_name: str, api_id: int, api_hash: str):
        session_path = f"{self.sessions_dir}/{session_name}"
        client = Client(
            name=session_path,
            api_id=api_id,
            api_hash=api_hash,
            workdir=self.sessions_dir
        )
        await client.start()
        self.clients[account_id] = client
        print(f"✅ Pyrogram клиент {session_name} запущен")
        return client

    def get_client(self, account_id: int) -> Optional[Client]:
        return self.clients.get(account_id)

    async def stop_all(self):
        for client in self.clients.values():
            await client.stop()
        print("Все Pyrogram клиенты остановлены")

pyrogram_manager = PyrogramManager()
