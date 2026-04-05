# utils/pyrogram_manager.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
import os
from pyrogram import Client
from typing import Dict, Optional

class PyrogramManager:
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.sessions_dir = "sessions"
        
        # Полная очистка старых сессий при запуске
        if os.path.exists(self.sessions_dir):
            for filename in os.listdir(self.sessions_dir):
                try:
                    os.remove(os.path.join(self.sessions_dir, filename))
                except:
                    pass
        os.makedirs(self.sessions_dir, exist_ok=True)

    async def add_account(self, account_id: int, session_name: str, api_id: int, api_hash: str):
        """Добавление и запуск Pyrogram клиента"""
        # Создаём клиент полностью в памяти
        client = Client(
            name=session_name,
            api_id=api_id,
            api_hash=api_hash,
            in_memory=True,           # обязательно
            workdir=self.sessions_dir,
            no_updates=True,          # снижает нагрузку
            takeout=False
        )

        try:
            print(f"Запуск клиента {session_name}...")
            await client.start()
            self.clients[account_id] = client
            print(f"✅ Клиент {session_name} (ID: {account_id}) успешно запущен")
            return client
        except Exception as e:
            error = str(e).lower()
            print(f"❌ Ошибка запуска {session_name}: {e}")
            
            # Автоматическая повторная попытка при типичных ошибках Railway
            if any(x in error for x in ["eof", "database", "session", "file"]):
                print("Повторная попытка с чистой сессией...")
                # Удаляем возможные остатки
                for f in os.listdir(self.sessions_dir):
                    if session_name in f:
                        try:
                            os.remove(os.path.join(self.sessions_dir, f))
                        except:
                            pass
                
                # Вторая попытка
                client = Client(
                    name=session_name,
                    api_id=api_id,
                    api_hash=api_hash,
                    in_memory=True,
                    workdir=self.sessions_dir,
                    no_updates=True
                )
                await client.start()
                self.clients[account_id] = client
                print(f"✅ Клиент {session_name} запущен после повторной попытки")
                return client
            else:
                raise

    def get_client(self, account_id: int) -> Optional[Client]:
        return self.clients.get(account_id)

    async def stop_all(self):
        for client in list(self.clients.values()):
            if client.is_connected:
                try:
                    await client.stop()
                except:
                    pass
        self.clients.clear()

pyrogram_manager = PyrogramManager()
