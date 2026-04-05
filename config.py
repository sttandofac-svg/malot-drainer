import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")
if OWNER_ID == 0:
    raise ValueError("OWNER_ID не задан")
if API_ID == 0 or not API_HASH:
    raise ValueError("API_ID и API_HASH обязательны! Добавь их в Railway Variables")
