# config.py  ← ЗАМЕНИ ПОЛНОСТЬЮ на этот вариант
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в Environment Variables Railway!")
if OWNER_ID == 0:
    raise ValueError("❌ OWNER_ID не задан в Environment Variables Railway!")

print(f"✅ Конфиг загружен. OWNER_ID = {OWNER_ID}")
# config.py  ← ДОБАВЬ В КОНЕЦ ФАЙЛА
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

if API_ID == 0 or not API_HASH:
    raise ValueError("❌ В Railway Variables нужно добавить API_ID и API_HASH!")
