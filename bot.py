# bot.py
# Полноценный Telegram-рассылочный бот на Telethon (один файл)
# Работает как userbot: логинится под твоим аккаунтом и рассылает от его имени
# Сохраняет сессию, настройки, выбранные чаты и сообщение между запусками

import asyncio
import json
import logging
import os
import pickle
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, PeerFloodError, SessionPasswordNeededError
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import DialogFilter
from telethon.utils import get_peer_id

# ========================= НАСТРОЙКИ =========================
API_ID = 12345678          # ← Замени на свой api_id с my.telegram.org
API_HASH = '0123456789abcdef0123456789abcdef'  # ← Замени на свой api_hash
SESSION_NAME = 'session'
OWNER_ID = 123456789       # ← Захардкодь свой Telegram user_id для защиты

# Файлы для хранения
SETTINGS_FILE = 'settings.json'
PHOTO_FILE = 'broadcast_photo.jpg'

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Глобальные переменные (загружаются из файла)
settings = {
    'selected_chats': [],      # список peer_id
    'message_text': '',
    'has_photo': False,
    'delay_min': 1.0,
    'delay_max': 3.0
}

client = None
broadcast_task = None
stop_broadcast = False

# ========================= ПОМОЩНИКИ =========================
def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                settings.update(loaded)
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
        logger.info("Настройки сохранены")
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")

async def is_owner(event):
    if event.sender_id != OWNER_ID:
        await event.respond("Доступ запрещён.")
        return False
    return True

# ========================= МЕНЮ =========================
async def show_main_menu(event):
    buttons = [
        [Button.text("📋 Выбрать чаты для рассылки")],
        [Button.text("✍️ Настроить сообщение")],
        [Button.text("▶️ Запустить рассылку")],
        [Button.text("📊 Статистика / Остановить")],
        [Button.text("🔄 Сменить аккаунт"), Button.text("❓ Помощь")]
    ]
    await event.respond("Главное меню:", buttons=buttons)

# ========================= АВТОРИЗАЦИЯ =========================
async def start_client():
    global client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    await client.connect()
    
    if not await client.is_user_authorized():
        logger.info("Требуется авторизация...")
        phone = input("Введите номер телефона (+XXXXXXXXXXX): ")
        await client.send_code_request(phone)
        
        code = input("Введите код из Telegram: ")
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("Введите 2FA-пароль: ")
            await client.sign_in(password=password)
        
        logger.info("Авторизация успешна. Сессия сохранена.")
    else:
        logger.info("Сессия загружена успешно.")
    
    return client

# ========================= ВЫБОР ЧАТОВ =========================
async def list_dialogs(event):
    await event.respond("Получаю список диалогов...")
    dialogs = await client(GetDialogsRequest(
        offset_date=None, offset_id=0, offset_peer=InputPeerChannel(0, 0),
        limit=200, hash=0
    ))
    
    text = "📋 Доступные чаты/группы/каналы:\n\n"
    chat_list = []
    for i, dialog in enumerate(dialogs, 1):
        entity = dialog.entity
        peer_id = get_peer_id(entity)
        name = entity.title if hasattr(entity, 'title') else entity.username or entity.first_name
        chat_list.append({'id': peer_id, 'name': name})
        text += f"{i}. {name} (ID: {peer_id})\n"
    
    await event.respond(text + "\n\nОтправь номера через запятую (например: 1,3,5) или 'все'")
    
    # Сохраняем временно список для обработки ответа
    event.client.temp_chat_list = chat_list
    return chat_list

@client.on(events.NewMessage(pattern=r'^\d+(,\d+)*$|все$', func=lambda e: e.is_private))
async def handle_chat_selection(event):
    if not await is_owner(event):
        return
    
    if not hasattr(event.client, 'temp_chat_list'):
        return
    
    chat_list = event.client.temp_chat_list
    selected = []
    
    if event.raw_text.lower() == 'все':
        selected = [chat['id'] for chat in chat_list]
    else:
        try:
            indices = [int(x.strip()) - 1 for x in event.raw_text.split(',')]
            selected = [chat_list[i]['id'] for i in indices if 0 <= i < len(chat_list)]
        except:
            await event.respond("Неверный формат. Попробуй снова.")
            return
    
    settings['selected_chats'] = selected
    save_settings()
    await event.respond(f"Выбрано {len(selected)} чатов для рассылки.")
    await show_main_menu(event)

# ========================= НАСТРОЙКА СООБЩЕНИЯ =========================
@client.on(events.NewMessage(pattern='✍️ Настроить сообщение', func=lambda e: e.is_private))
async def setup_message(event):
    if not await is_owner(event):
        return
    await event.respond("Отправь текст сообщения (поддерживается форматирование Telegram).")
    
    @client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id == OWNER_ID))
    async def get_message_text(new_event):
        if new_event.text.startswith('/'):
            return
        settings['message_text'] = new_event.text
        save_settings()
        await new_event.respond("Текст сохранён.\nХотите добавить фото? (да/нет)")
        
        @client.on(events.NewMessage(pattern='^(да|нет)$', func=lambda e: e.is_private))
        async def handle_photo_choice(photo_event):
            if photo_event.text.lower() == 'да':
                await photo_event.respond("Отправь фото (как фото или документ).")
                
                @client.on(events.NewMessage(func=lambda e: e.photo or e.document and e.is_private))
                async def receive_photo(p_event):
                    if p_event.photo:
                        await client.download_media(p_event.photo, PHOTO_FILE)
                    elif p_event.document:
                        await client.download_media(p_event.document, PHOTO_FILE)
                    settings['has_photo'] = True
                    save_settings()
                    await p_event.respond("Фото сохранено.")
                    await show_main_menu(p_event)
                    # Удаляем обработчики
                    client.remove_event_handler(receive_photo)
                    client.remove_event_handler(handle_photo_choice)
            else:
                settings['has_photo'] = False
                save_settings()
                await photo_event.respond("Сообщение без фото.")
                await show_main_menu(photo_event)
            client.remove_event_handler(get_message_text)

# ========================= ПРЕВЬЮ И ЗАПУСК РАССЫЛКИ =========================
@client.on(events.NewMessage(pattern='▶️ Запустить рассылку', func=lambda e: e.is_private))
async def start_broadcast(event):
    if not await is_owner(event):
        return
    
    if not settings['selected_chats']:
        await event.respond("Сначала выбери чаты!")
        return
    if not settings['message_text']:
        await event.respond("Сначала настрой сообщение!")
        return
    
    preview = "Превью рассылки:\n\n"
    preview += settings['message_text'] + "\n\n"
    if settings['has_photo']:
        preview += "📸 С фото\n"
    preview += f"Чатов: {len(settings['selected_chats'])}\nЗадержка: {settings['delay_min']}-{settings['delay_max']} сек."
    
    await event.respond(preview, file=PHOTO_FILE if settings['has_photo'] else None)
    await event.respond("Подтвердить запуск? (да/нет)")
    
    @client.on(events.NewMessage(pattern='^да$', func=lambda e: e.is_private))
    async def confirm_broadcast(confirm_event):
        global broadcast_task, stop_broadcast
        stop_broadcast = False
        broadcast_task = asyncio.create_task(run_broadcast(confirm_event))
        await confirm_event.respond("Рассылка запущена. Для остановки напиши 'стоп'.")
        client.remove_event_handler(confirm_broadcast)

async def run_broadcast(event):
    global stop_broadcast
    total = len(settings['selected_chats'])
    sent = 0
    failed = 0
    
    await event.respond(f"Начинаю рассылку в {total} чатов...")
    
    for peer_id in settings['selected_chats']:
        if stop_broadcast:
            await event.respond("Рассылка остановлена пользователем.")
            break
        
        try:
            entity = await client.get_entity(peer_id)
            
            if settings['has_photo']:
                await client.send_file(
                    entity,
                    PHOTO_FILE,
                    caption=settings['message_text'],
                    parse_mode='md'
                )
            else:
                await client.send_message(
                    entity,
                    settings['message_text'],
                    parse_mode='md'
                )
            
            sent += 1
            await event.respond(f"✅ Отправлено {sent}/{total}")
            
            # Случайная задержка
            import random
            delay = random.uniform(settings['delay_min'], settings['delay_max'])
            await asyncio.sleep(delay)
            
        except FloodWaitError as e:
            await event.respond(f"⏳ FloodWait: ждём {e.seconds} сек.")
            await asyncio.sleep(e.seconds + 5)
        except PeerFloodError:
            await event.respond("⚠️ PeerFlood. Пауза 30 сек.")
            await asyncio.sleep(30)
        except Exception as ex:
            failed += 1
            logger.error(f"Ошибка отправки в {peer_id}: {ex}")
            await asyncio.sleep(2)
    
    await event.respond(f"Рассылка завершена. Успешно: {sent}, Неудачно: {failed}")
    broadcast_task = None

@client.on(events.NewMessage(pattern='стоп', func=lambda e: e.is_private))
async def stop_command(event):
    global stop_broadcast
    if broadcast_task and not broadcast_task.done():
        stop_broadcast = True
        await event.respond("Команда остановки принята...")

# ========================= СТАТИСТИКА =========================
@client.on(events.NewMessage(pattern='📊 Статистика / Остановить', func=lambda e: e.is_private))
async def show_stats(event):
    if not await is_owner(event):
        return
    if broadcast_task and not broadcast_task.done():
        await event.respond("Рассылка в процессе. Напиши 'стоп' для остановки.")
    else:
        await event.respond(
            f"📊 Статистика:\n"
            f"Выбрано чатов: {len(settings['selected_chats'])}\n"
            f"Сообщение настроено: {'Да' if settings['message_text'] else 'Нет'}\n"
            f"Фото: {'Да' if settings['has_photo'] else 'Нет'}\n"
            f"Текущий аккаунт: {await client.get_me()}"
        )

# ========================= ОСНОВНЫЕ КОМАНДЫ =========================
@client.on(events.NewMessage(pattern='/start', func=lambda e: e.is_private))
async def start(event):
    if not await is_owner(event):
        return
    await event.respond("Привет! Это бот для массовой рассылки.")
    load_settings()
    await show_main_menu(event)

@client.on(events.NewMessage(pattern='/help', func=lambda e: e.is_private))
async def help_cmd(event):
    if not await is_owner(event):
        return
    await event.respond(
        "Команды:\n"
        "/start — главное меню\n"
        "✍️ Настроить сообщение — текст + фото\n"
        "📋 Выбрать чаты — список диалогов\n"
        "▶️ Запустить рассылку — после подтверждения\n"
        "стоп — остановить текущую рассылку\n"
        "📊 Статистика / Остановить"
    )

# ========================= ЗАПУСК =========================
async def main():
    global client
    load_settings()
    client = await start_client()
    
    # Регистрируем обработчики меню
    @client.on(events.NewMessage(pattern='📋 Выбрать чаты для рассылки', func=lambda e: e.is_private))
    async def menu_list(event):
        if await is_owner(event):
            await list_dialogs(event)
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
