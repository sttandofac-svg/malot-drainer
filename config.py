# config.py  ← СОЗДАЙ В КОРНЕ
import os
from dotenv import load_dotenv

load_dotenv()

OWNER_ID = int(os.getenv("OWNER_ID", 0))
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в Environment Variables Railway!")
if not OWNER_ID:
    raise ValueError("OWNER_ID не задан в Environment Variables Railway!") 
