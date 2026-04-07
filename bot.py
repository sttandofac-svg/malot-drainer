# bot.py
# Полноценный Telegram-бот для массовой рассылки
# Всё управление — внутри Telegram (никакого input() в консоли)
# Telethon + conversational handlers

import asyncio
import json
import logging
import os
import random
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, PeerFloodError, SessionPasswordNeededError
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerChannel
from telethon.utils import get_peer_id

# ========================= НАСТРОЙКИ =========================
API_ID = 12345678                    # ← Замени
API_HASH = '0123456789abcdef0123456789abcdef'  # ← Замени
SESSION_NAME = 'session'
OWNER_ID = 123456789                 # ← Твой user_id для защиты

SETTINGS_FILE = 'settings.json'
PHOTO_FILE = 'broadcast_photo.jpg'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings = {
    'selected_chats': [],
    'message_text': '',
    'has_photo': False,
    'delay_min': 1.0,
    'delay_max': 3.0
}

client = None
broadcast_task = None
stop_broadcast = False
temp_data = {}  # Для хранения временных данных разговора

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings.update(json.load(f))
            if os.path.exists(PHOTO_FILE):
                settings['has_photo'] = True
            logger.info("Настройки загружены")
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'selected_chats': settings['selected_chats'],
                'message_text': settings['message_text'],
                'has_photo': settings['has_photo'],
                'delay_min': settings['delay_min'],
                'delay_max': settings['delay_max']
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")

async def is_owner(event):
    if event.sender_id != OWNER_ID:
        await event.respond("Доступ запрещён.")
        return False
    return True

async def show_main_menu(event):
    buttons = [
        [Button.text("📋 Выбрать чаты")],
        [Button.text("✍️ Настроить сообщение")],
        [Button.text("▶️ Запустить рассылку")],
        [Button.text("📊 Статистика")],
        [Button.text("❓ Помощь")]
    ]
    await event.respond("Главное меню рассылочного бота:", buttons=buttons)

# ========================= АВТОРИЗАЦИЯ ВНУТРИ TELEGRAM =========================
@client.on(events.NewMessage(pattern='/start', func=lambda e: e.is_private))
async def cmd_start(event):
    if not await is_owner(event):
        return
    if not await client.is_user_authorized():
        temp_data[event.sender_id] = {'step': 'phone'}
        await event.respond("Для авторизации введи номер телефона в формате +XXXXXXXXXXX")
    else:
        load_settings()
        await show_main_menu(event)

@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id == OWNER_ID))
async def conversation_handler(event):
    user_id = event.sender_id
    if user_id not in temp_data:
        return

    data = temp_data[user_id]
    step = data.get('step')

    if step == 'phone':
        data['phone'] = event.raw_text.strip()
        await client.send_code_request(data['phone'])
        data['step'] = 'code'
        await event.respond("Код подтверждения отправлен в Telegram. Введи его сюда:")

    elif step == 'code':
        try:
            await client.sign_in(data['phone'], event.raw_text.strip())
            await event.respond("Авторизация успешна!")
            del temp_data[user_id]
            load_settings()
            await show_main_menu(event)
        except SessionPasswordNeededError:
            data['step'] = 'password'
            await event.respond("Нужен 2FA-пароль. Введи его:")
        except Exception as e:
            await event.respond(f"Ошибка: {e}")
            del temp_data[user_id]

    elif step == 'password':
        try:
            await client.sign_in(password=event.raw_text.strip())
            await event.respond("Авторизация с 2FA успешна!")
            del temp_data[user_id]
            load_settings()
            await show_main_menu(event)
        except Exception as e:
            await event.respond(f"Ошибка 2FA: {e}")
            del temp_data[user_id]

# ========================= ОСНОВНЫЕ ФУНКЦИИ =========================
@client.on(events.NewMessage(pattern='📋 Выбрать чаты', func=lambda e: e.is_private))
async def choose_chats(event):
    if not await is_owner(event): return
    await event.respond("Загружаю список диалогов...")
    dialogs = await client(GetDialogsRequest(
        offset_date=None, offset_id=0, offset_peer=InputPeerChannel(0, 0),
        limit=200, hash=0
    ))
    text = "Доступные чаты:\n\n"
    chat_list = []
    for i, d in enumerate(dialogs, 1):
        entity = d.entity
        pid = get_peer_id(entity)
        name = getattr(entity, 'title', None) or getattr(entity, 'username', None) or getattr(entity, 'first_name', 'Unknown')
        chat_list.append({'id': pid, 'name': name})
        text += f"{i}. {name}\n"
    await event.respond(text + "\nОтправь номера через запятую (1,3,5) или 'все'")
    temp_data[event.sender_id] = {'chat_list': chat_list, 'step': 'chat_select'}

@client.on(events.NewMessage(pattern=r'^\d+(,\d+)*$|все$', func=lambda e: e.is_private))
async def handle_chat_select(event):
    if not await is_owner(event): return
    if event.sender_id not in temp_data or temp_data[event.sender_id].get('step') != 'chat_select':
        return
    chat_list = temp_data[event.sender_id]['chat_list']
    selected = []
    if event.raw_text.lower() == 'все':
        selected = [c['id'] for c in chat_list]
    else:
        try:
            indices = [int(x.strip()) - 1 for x in event.raw_text.split(',')]
            selected = [chat_list[i]['id'] for i in indices if 0 <= i < len(chat_list)]
        except:
            await event.respond("Неверный формат")
            return
    settings['selected_chats'] = selected
    save_settings()
    await event.respond(f"Выбрано {len(selected)} чатов")
    del temp_data[event.sender_id]
    await show_main_menu(event)

@client.on(events.NewMessage(pattern='✍️ Настроить сообщение', func=lambda e: e.is_private))
async def setup_message(event):
    if not await is_owner(event): return
    await event.respond("Отправь текст сообщения (поддерживается **жирный**, __курсив__, ||спойлер|| и т.д.)")
    temp_data[event.sender_id] = {'step': 'message_text'}

@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id == OWNER_ID))
async def get_message_text(event):
    if event.sender_id not in temp_data or temp_data[event.sender_id].get('step') != 'message_text':
        return
    settings['message_text'] = event.raw_text
    save_settings()
    await event.respond("Текст сохранён.\nДобавить фото? (да/нет)")
    temp_data[event.sender_id]['step'] = 'photo_choice'

@client.on(events.NewMessage(pattern='^(да|нет)$', func=lambda e: e.is_private))
async def handle_photo_choice(event):
    if event.sender_id not in temp_data or temp_data[event.sender_id].get('step') != 'photo_choice':
        return
    if event.raw_text.lower() == 'да':
        await event.respond("Отправь одно фото (как фото или файл)")
        temp_data[event.sender_id]['step'] = 'receive_photo'
    else:
        settings['has_photo'] = False
        save_settings()
        await event.respond("Сообщение без фото сохранено")
        del temp_data[event.sender_id]
        await show_main_menu(event)

@client.on(events.NewMessage(func=lambda e: e.is_private and (e.photo or e.document) and e.sender_id == OWNER_ID))
async def receive_photo(event):
    if event.sender_id not in temp_data or temp_data[event.sender_id].get('step') != 'receive_photo':
        return
    try:
        if event.photo:
            await client.download_media(event.photo, PHOTO_FILE)
        else:
            await client.download_media(event.document, PHOTO_FILE)
        settings['has_photo'] = True
        save_settings()
        await event.respond("Фото успешно сохранено")
    except Exception as e:
        await event.respond(f"Ошибка сохранения фото: {e}")
    del temp_data[event.sender_id]
    await show_main_menu(event)

@client.on(events.NewMessage(pattern='▶️ Запустить рассылку', func=lambda e: e.is_private))
async def start_broadcast_cmd(event):
    if not await is_owner(event): return
    if not settings.get('selected_chats') or not settings.get('message_text'):
        await event.respond("Сначала выбери чаты и настрой сообщение!")
        return
    preview_text = f"Превью рассылки:\n\n{settings['message_text']}\n\nЧатов: {len(settings['selected_chats'])}\nФото: {'Да' if settings['has_photo'] else 'Нет'}"
    await event.respond(preview_text, file=PHOTO_FILE if settings['has_photo'] else None)
    await event.respond("Запустить рассылку? (да/нет)")
    temp_data[event.sender_id] = {'step': 'confirm_broadcast'}

@client.on(events.NewMessage(pattern='^да$', func=lambda e: e.is_private))
async def confirm_broadcast(event):
    if event.sender_id not in temp_data or temp_data[event.sender_id].get('step') != 'confirm_broadcast':
        return
    global broadcast_task, stop_broadcast
    stop_broadcast = False
    broadcast_task = asyncio.create_task(run_broadcast(event))
    await event.respond("Рассылка запущена! Для остановки напиши 'стоп'")
    del temp_data[event.sender_id]

async def run_broadcast(event):
    global stop_broadcast
    total = len(settings['selected_chats'])
    sent = 0
    for idx, peer_id in enumerate(settings['selected_chats'], 1):
        if stop_broadcast:
            await event.respond("Рассылка остановлена")
            break
        try:
            entity = await client.get_entity(peer_id)
            if settings['has_photo']:
                await client.send_file(entity, PHOTO_FILE, caption=settings['message_text'], parse_mode='md')
            else:
                await client.send_message(entity, settings['message_text'], parse_mode='md')
            sent += 1
            await event.respond(f"✅ Отправлено {sent}/{total} ({idx})")
            await asyncio.sleep(random.uniform(settings['delay_min'], settings['delay_max']))
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 10)
        except PeerFloodError:
            await asyncio.sleep(60)
        except Exception as ex:
            logger.error(f"Ошибка в чате {peer_id}: {ex}")
            await asyncio.sleep(3)
    await event.respond(f"Рассылка завершена. Успешно отправлено: {sent}/{total}")

@client.on(events.NewMessage(pattern='стоп', func=lambda e: e.is_private))
async def stop_broadcast_cmd(event):
    global stop_broadcast
    stop_broadcast = True
    await event.respond("Команда остановки принята...")

@client.on(events.NewMessage(pattern='📊 Статистика', func=lambda e: e.is_private))
async def stats_cmd(event):
    if not await is_owner(event): return
    status = "В процессе" if broadcast_task and not broadcast_task.done() else "Остановлена"
    await event.respond(
        f"📊 Статистика:\n"
        f"Выбрано чатов: {len(settings['selected_chats'])}\n"
        f"Сообщение: {'Настроено' if settings['message_text'] else 'Нет'}\n"
        f"Фото: {'Прикреплено' if settings['has_photo'] else 'Нет'}\n"
        f"Статус рассылки: {status}"
    )

@client.on(events.NewMessage(pattern='❓ Помощь', func=lambda e: e.is_private))
async def help_cmd(event):
    if not await is_owner(event): return
    await event.respond("Бот полностью работает внутри Telegram.\n/start — меню\nстоп — остановить рассылку")

# ========================= ЗАПУСК =========================
async def main():
    global client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        logger.info("Аккаунт не авторизован. Используй /start в чате с ботом.")
    else:
        logger.info("Аккаунт уже авторизован.")

    load_settings()
    logger.info("Бот запущен и полностью работает внутри Telegram.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
