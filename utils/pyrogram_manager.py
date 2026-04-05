# utils/pyrogram_manager.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
import os
from pyrogram import Client
from typing import Dict, Optional

class PyrogramManager:
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.sessions_dir = "sessions"
        # Очищаем старую папку сессий при каждом перезапуске бота
        if os.path.exists(self.sessions_dir):
            for f in os.listdir(self.sessions_dir):
                if f.endswith(".session") or f.endswith(".session-journal"):
                    try:
                        os.remove(os.path.join(self.sessions_dir, f))
                    except:
                        pass
        os.makedirs(self.sessions_dir, exist_ok=True)

    async def add_account(self, account_id: int, session_name: str, api_id: int, api_hash: str):
        # Полностью чистая сессия в памяти
        client = Client(
            name=session_name,
            api_id=api_id,
            api_hash=api_hash,
            in_memory=True,           # главное для Railway
            workdir=self.sessions_dir,
            no_updates=True           # уменьшает нагрузку
        )

        try:
            await client.start()
            self.clients[account_id] = client
            print(f"✅ Клиент {session_name} успешно запущен")
            return client
        except Exception as e:
            error_msg = str(e)
            if "EOF when reading a line" in error_msg or "database" in error_msg.lower():
                # Повторная попытка с полностью чистой сессией
                print(f"⚠️ Обнаружена ошибка EOF, пробуем заново...")
                # Удаляем возможные остатки
                for f in os.listdir(self.sessions_dir):
                    if session_name in f:
                        try:
                            os.remove(os.path.join(self.sessions_dir, f))
                        except:
                            pass
                # Повторный запуск
                client = Client(
                    name=session_name,
                    api_id=api_id,
                    api_hash=api_hash,
                    in_memory=True,
                    workdir=self.sessions_dir
                )
                await client.start()
                self.clients[account_id] = client
                print(f"✅ Клиент {session_name} запущен после очистки")
                return client
            else:
                print(f"❌ Критическая ошибка запуска {session_name}: {error_msg}")
                raise

    def get_client(self, account_id: int) -> Optional[Client]:
        return self.clients.get(account_id)

pyrogram_manager = PyrogramManager()
