# config.py
import os
from dotenv import load_dotenv

load_dotenv()

OWNER_ID = int(os.getenv("OWNER_ID"))  # Только этот user_id имеет доступ

# Для Railway — все секреты берутся из Environment Variables
API_TOKEN = os.getenv("BOT_TOKEN")  # токен бота от @BotFather
