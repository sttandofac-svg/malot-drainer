# utils/pyrogram_manager.py  ← ЗАМЕНИ ПОЛНОСТЬЮ (самая чистая версия)
import os
from pyrogram import Client
from typing import Dict, Optional
from config import API_ID, API_HASH

class PyrogramManager:
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.sessions_dir = "/tmp/sessions"   # используем /tmp — единственное место, где точно можно писать

        # Полная очистка
        if os.path.exists(self.sessions_dir):
            try:
                import shutil
                shutil.rmtree(self.sessions_dir)
            except:
                pass
        os.makedirs(self.sessions_dir, exist_ok=True)

    async def add_account(self, account_id: int, session_name: str):
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
            workdir=self.sessions_dir,
            no_updates=True,
            sleep_threshold=30
        )

        try:
            print(f"[Pyrogram] Старт авторизации {session_name}...")
            await client.start()
            self.clients[account_id] = client
            print(f"✅ {session_name} успешно авторизован")
            return client
        except Exception as e:
            error = str(e)
            print(f"❌ Ошибка: {error}")
            
            # Последняя попытка
            try:
                import shutil
                shutil.rmtree(self.sessions_dir)
            except:
                pass
            os.makedirs(self.sessions_dir, exist_ok=True)

            client = Client(
                name=session_name,
                api_id=API_ID,
                api_hash=API_HASH,
                in_memory=True,
                workdir=self.sessions_dir
            )
            await client.start()
            self.clients[account_id] = client
            return client

pyrogram_manager = PyrogramManager()
