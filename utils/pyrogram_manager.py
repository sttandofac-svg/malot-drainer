import os
from pyrogram import Client
from typing import Dict, Optional

class PyrogramManager:
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)

    async def add_account(self, account_id: int, session_name: str, api_id: int, api_hash: str):
        client = Client(
            name=session_name,
            api_id=api_id,
            api_hash=api_hash,
            in_memory=True,        # обязательно для Railway
            workdir=self.sessions_dir
        )
        try:
            await client.start()
            self.clients[account_id] = client
            print(f"✅ Клиент {session_name} запущен")
            return client
        except Exception as e:
            print(f"❌ Ошибка запуска {session_name}: {e}")
            raise

    def get_client(self, account_id: int) -> Optional[Client]:
        return self.clients.get(account_id)

pyrogram_manager = PyrogramManager()
