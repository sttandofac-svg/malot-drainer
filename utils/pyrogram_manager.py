# utils/pyrogram_manager.py  ← ЗАМЕНИ ПОЛНОСТЬЮ (добавлена поддержка phone login)
import os
from pyrogram import Client
from typing import Dict, Optional

class PyrogramManager:
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.sessions_dir = "sessions"
        
        # Очистка старых сессий
        if os.path.exists(self.sessions_dir):
            for f in os.listdir(self.sessions_dir):
                try:
                    os.remove(os.path.join(self.sessions_dir, f))
                except:
                    pass
        os.makedirs(self.sessions_dir, exist_ok=True)

    async def add_account(self, account_id: int, session_name: str, phone_number: str = None):
        """Добавление аккаунта через номер телефона"""
        client = Client(
            name=session_name,
            in_memory=True,
            workdir=self.sessions_dir,
            no_updates=True
        )

        # Если номер не передан — Pyrogram сам попросит его при start()
        if phone_number:
            client.phone_number = phone_number

        try:
            print(f"Запуск клиента {session_name} через телефон...")
            await client.start()
            self.clients[account_id] = client
            print(f"✅ Клиент {session_name} успешно авторизован")
            return client
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            # Повторная попытка с очисткой
            for f in os.listdir(self.sessions_dir):
                if session_name in f:
                    try:
                        os.remove(os.path.join(self.sessions_dir, f))
                    except:
                        pass
            client = Client(name=session_name, in_memory=True, workdir=self.sessions_dir)
            await client.start()
            self.clients[account_id] = client
            return client

pyrogram_manager = PyrogramManager()
