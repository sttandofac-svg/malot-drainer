# utils/pyrogram_manager.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
import os
from pyrogram import Client
from typing import Dict, Optional
from config import API_ID, API_HASH

class PyrogramManager:
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.sessions_dir = "sessions"
        if os.path.exists(self.sessions_dir):
            for f in os.listdir(self.sessions_dir):
                try:
                    os.remove(os.path.join(self.sessions_dir, f))
                except:
                    pass
        os.makedirs(self.sessions_dir, exist_ok=True)

    async def add_account(self, account_id: int, session_name: str, phone_number: str):
        """Авторизация через номер телефона с общими api_id/api_hash"""
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
            workdir=self.sessions_dir,
            no_updates=True
        )

        try:
            print(f"Запуск авторизации для {phone_number}...")
            await client.start(phone_number=phone_number)
            self.clients[account_id] = client
            print(f"✅ Аккаунт {session_name} успешно авторизован")
            return client
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            # Повторная попытка
            for f in os.listdir(self.sessions_dir):
                if session_name in f:
                    try:
                        os.remove(os.path.join(self.sessions_dir, f))
                    except:
                        pass
            client = Client(
                name=session_name,
                api_id=API_ID,
                api_hash=API_HASH,
                in_memory=True,
                workdir=self.sessions_dir
            )
            await client.start(phone_number=phone_number)
            self.clients[account_id] = client
            return client

pyrogram_manager = PyrogramManager() 
