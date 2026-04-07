# bot.py
# Исправленная версия — все обработчики регистрируются ТОЛЬКО после создания клиента

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
API_ID = 12345678                    # ← ТВОЙ api_id
API_HASH = '0123456789abcdef0123456789abcdef'  # ← ТВОЙ api_hash
SESSION_NAME = 'session'
OWNER_ID = 123456789                 # ← ТВОЙ user_id

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
            logger.error(f"Ошибка загрузки: {e}")

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
    await event.respond("Главное меню:", buttons=buttons)

async def start_client():
    global client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        logger.info("Новая авторизация...")
        phone = input("Номер телефона (+...): ")
        await client.send_code_request(phone)
        code = input("Код из Telegram: ")
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            pw = input("2FA пароль: ")
            await client.sign_in(password=pw)
        logger.info("Аккаунт авторизован, сессия сохранена.")
    else:
        logger.info("Сессия загружена.")

    return client

# ========================= ОБРАБОТЧИКИ (регистрируются после создания клиента) =========================
async def register_handlers():
    @client.on(events.NewMessage(pattern='/start', func=lambda e: e.is_private))
    async def cmd_start(event):
        if not await is_owner(event): return
        load_settings()
        await show_main_menu(event)

    @client.on(events.NewMessage(pattern='/help', func=lambda e: e.is_private))
    async def cmd_help(event):
        if not await is_owner(event): return
        await event.respond("Команды:\n/start — меню\nстоп — остановить рассылку")

    @client.on(events.NewMessage(pattern='📋 Выбрать чаты', func=lambda e: e.is_private))
    async def menu_choose_chats(event):
        if not await is_owner(event): return
        await event.respond("Получаю диалоги...")
        dialogs = await client(GetDialogsRequest(offset_date=None, offset_id=0, offset_peer=InputPeerChannel(0, 0), limit=200, hash=0))
        
        text = "Доступные чаты:\n\n"
        chat_list = []
        for i, d in enumerate(dialogs, 1):
            entity = d.entity
            pid = get_peer_id(entity)
            name = getattr(entity, 'title', None) or getattr(entity, 'username', None) or entity.first_name
            chat_list.append({'id': pid, 'name': name})
            text += f"{i}. {name} (ID: {pid})\n"
        
        await event.respond(text + "\nОтправь номера через запятую или 'все'")
        event.client.temp_chat_list = chat_list

    @client.on(events.NewMessage(pattern=r'^\d+(,\d+)*$|все$', func=lambda e: e.is_private))
    async def handle_chat_selection(event):
        if not await is_owner(event): return
        if not hasattr(event.client, 'temp_chat_list'): return
        chat_list = event.client.temp_chat_list
        selected = []
        if event.raw_text.lower() == 'все':
            selected = [c['id'] for c in chat_list]
        else:
            try:
                idx = [int(x.strip())-1 for x in event.raw_text.split(',')]
                selected = [chat_list[i]['id'] for i in idx if 0 <= i < len(chat_list)]
            except:
                await event.respond("Неверный формат")
                return
        settings['selected_chats'] = selected
        save_settings()
        await event.respond(f"Выбрано {len(selected)} чатов")
        await show_main_menu(event)

    @client.on(events.NewMessage(pattern='✍️ Настроить сообщение', func=lambda e: e.is_private))
    async def menu_setup_message(event):
        if not await is_owner(event): return
        await event.respond("Отправь текст сообщения (поддерживается md-разметка)")

        @client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id == OWNER_ID))
        async def get_text(new_event):
            if new_event.text.startswith(('/', '📋', '✍️', '▶️', '📊')): return
            settings['message_text'] = new_event.text
            save_settings()
            await new_event.respond("Текст сохранён.\nДобавить фото? (да/нет)")

            @client.on(events.NewMessage(pattern='^(да|нет)$', func=lambda e: e.is_private))
            async def photo_choice(p_event):
                if p_event.text.lower() == 'да':
                    await p_event.respond("Отправь фото")
                    @client.on(events.NewMessage(func=lambda e: (e.photo or e.document) and e.is_private))
                    async def save_photo(sp_event):
                        if sp_event.photo:
                            await client.download_media(sp_event.photo, PHOTO_FILE)
                        else:
                            await client.download_media(sp_event.document, PHOTO_FILE)
                        settings['has_photo'] = True
                        save_settings()
                        await sp_event.respond("Фото сохранено")
                        await show_main_menu(sp_event)
                        client.remove_event_handler(save_photo)
                else:
                    settings['has_photo'] = False
                    save_settings()
                    await p_event.respond("Без фото")
                    await show_main_menu(p_event)
                client.remove_event_handler(photo_choice)
            client.remove_event_handler(get_text)

    @client.on(events.NewMessage(pattern='▶️ Запустить рассылку', func=lambda e: e.is_private))
    async def menu_start_broadcast(event):
        if not await is_owner(event): return
        if not settings['selected_chats'] or not settings['message_text']:
            await event.respond("Сначала выбери чаты и настрой сообщение")
            return
        preview = f"Превью:\n\n{settings['message_text']}\n\nФото: {'Да' if settings['has_photo'] else 'Нет'}\nЧатов: {len(settings['selected_chats'])}"
        await event.respond(preview, file=PHOTO_FILE if settings['has_photo'] else None)
        await event.respond("Запустить? (да/нет)")

        @client.on(events.NewMessage(pattern='^да$', func=lambda e: e.is_private))
        async def confirm(ce):
            global broadcast_task, stop_broadcast
            stop_broadcast = False
            broadcast_task = asyncio.create_task(run_broadcast(ce))
            await ce.respond("Рассылка запущена. Напиши 'стоп' для остановки")
            client.remove_event_handler(confirm)

    async def run_broadcast(event):
        global stop_broadcast
        total = len(settings['selected_chats'])
        sent = 0
        for peer_id in settings['selected_chats']:
            if stop_broadcast: 
                await event.respond("Остановлено")
                break
            try:
                entity = await client.get_entity(peer_id)
                if settings['has_photo']:
                    await client.send_file(entity, PHOTO_FILE, caption=settings['message_text'], parse_mode='md')
                else:
                    await client.send_message(entity, settings['message_text'], parse_mode='md')
                sent += 1
                await event.respond(f"✅ {sent}/{total}")
                await asyncio.sleep(random.uniform(settings['delay_min'], settings['delay_max']))
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 5)
            except PeerFloodError:
                await asyncio.sleep(30)
            except Exception as ex:
                logger.error(f"Ошибка: {ex}")
                await asyncio.sleep(2)
        await event.respond(f"Готово. Отправлено: {sent}/{total}")

    @client.on(events.NewMessage(pattern='стоп', func=lambda e: e.is_private))
    async def cmd_stop(event):
        global stop_broadcast
        stop_broadcast = True
        await event.respond("Остановка...")

    @client.on(events.NewMessage(pattern='📊 Статистика', func=lambda e: e.is_private))
    async def menu_stats(event):
        if not await is_owner(event): return
        status = "В процессе" if broadcast_task and not broadcast_task.done() else "Не запущена"
        await event.respond(f"Чатов: {len(settings['selected_chats'])}\nСообщение: {'Есть' if settings['message_text'] else 'Нет'}\nФото: {'Есть' if settings['has_photo'] else 'Нет'}\nСтатус: {status}")

# ========================= ЗАПУСК =========================
async def main():
    global client
    load_settings()
    client = await start_client()
    await register_handlers()
    logger.info("Бот запущен. Ждём команд...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
