# config.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

if not BOT_TOKEN or OWNER_ID == 0 or API_ID == 0 or not API_HASH:
    raise ValueError("❌ В Railway Variables должны быть: BOT_TOKEN, OWNER_ID, API_ID, API_HASH")
