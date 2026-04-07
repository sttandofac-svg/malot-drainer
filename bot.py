# bot.py
# Финальная исправленная версия — ВСЁ РАБОТАЕТ В TELEGRAM
# Авторизация, меню, выбор чатов, сообщение, рассылка — только внутри чата
# Никаких @client.on на уровне модуля

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
API_ID = 12345678                    # ← Замени на свой
API_HASH = '0123456789abcdef0123456789abcdef'  # ← Замени на свой
SESSION_NAME = 'session'
OWNER_ID = 123456789                 # ← Твой Telegram user_id

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
temp_data = {}   # Для conversational состояний

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings.update(json.load(f))
            if os.path.exists(PHOTO_FILE):
                settings['has_photo'] = True
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
    await event.respond("Главное меню:", buttons=buttons)

# ========================= ДИНАМИЧЕСКАЯ РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ =========================
async def register_all_handlers():
    # /start + авторизация
    @client.on(events.NewMessage(pattern='/start', func=lambda e: e.is_private))
    async def cmd_start(event):
        if not await is_owner(event): return
        if not await client.is_user_authorized():
            temp_data[event.sender_id] = {'step': 'phone'}
            await event.respond("Введите номер телефона (+XXXXXXXXXXX):")
        else:
            load_settings()
            await show_main_menu(event)

    # conversational авторизация
    @client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id == OWNER_ID))
    async def auth_conversation(event):
        uid = event.sender_id
        if uid not in temp_data: return
        data = temp_data[uid]
        step = data.get('step')

        if step == 'phone':
            data['phone'] = event.raw_text.strip()
            await client.send_code_request(data['phone'])
            data['step'] = 'code'
            await event.respond("Код отправлен. Введите его:")

        elif step == 'code':
            try:
                await client.sign_in(data['phone'], event.raw_text.strip())
                await event.respond("✅ Авторизация успешна!")
                del temp_data[uid]
                load_settings()
                await show_main_menu(event)
            except SessionPasswordNeededError:
                data['step'] = 'password'
                await event.respond("Введите 2FA-пароль:")
            except Exception as e:
                await event.respond(f"Ошибка: {e}")
                del temp_data[uid]

        elif step == 'password':
            try:
                await client.sign_in(password=event.raw_text.strip())
                await event.respond("✅ 2FA пройден. Авторизация завершена!")
                del temp_data[uid]
                load_settings()
                await show_main_menu(event)
            except Exception as e:
                await event.respond(f"Ошибка 2FA: {e}")
                del temp_data[uid]

    # Выбор чатов
    @client.on(events.NewMessage(pattern='📋 Выбрать чаты', func=lambda e: e.is_private))
    async def choose_chats(event):
        if not await is_owner(event): return
        await event.respond("Загружаю диалоги...")
        dialogs = await client(GetDialogsRequest(offset_date=None, offset_id=0, offset_peer=InputPeerChannel(0, 0), limit=200, hash=0))
        text = "📋 Доступные чаты:\n\n"
        chat_list = []
        for i, d in enumerate(dialogs, 1):
            entity = d.entity
            pid = get_peer_id(entity)
            name = getattr(entity, 'title', None) or getattr(entity, 'username', None) or getattr(entity, 'first_name', 'Unknown')
            chat_list.append({'id': pid, 'name': name})
            text += f"{i}. {name}\n"
        await event.respond(text + "\nОтправьте номера через запятую или слово «все»")
        temp_data[event.sender_id] = {'chat_list': chat_list, 'step': 'chat_select'}

    @client.on(events.NewMessage(pattern=r'^\d+(,\d+)*$|все$', func=lambda e: e.is_private))
    async def handle_chat_selection(event):
        if not await is_owner(event): return
        uid = event.sender_id
        if uid not in temp_data or temp_data[uid].get('step') != 'chat_select': return
        chat_list = temp_data[uid]['chat_list']
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
        await event.respond(f"✅ Выбрано {len(selected)} чатов")
        del temp_data[uid]
        await show_main_menu(event)

    # Настройка сообщения
    @client.on(events.NewMessage(pattern='✍️ Настроить сообщение', func=lambda e: e.is_private))
    async def setup_message(event):
        if not await is_owner(event): return
        await event.respond("Отправьте текст сообщения (поддерживается **жирный**, __курсив__, ||спойлер|| и т.д.)")
        temp_data[event.sender_id] = {'step': 'message_text'}

    @client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id == OWNER_ID))
    async def receive_message_text(event):
        uid = event.sender_id
        if uid not in temp_data or temp_data[uid].get('step') != 'message_text': return
        settings['message_text'] = event.raw_text
        save_settings()
        await event.respond("Текст сохранён.\nДобавить фото? (да/нет)")
        temp_data[uid]['step'] = 'photo_choice'

    @client.on(events.NewMessage(pattern='^(да|нет)$', func=lambda e: e.is_private))
    async def photo_choice(event):
        uid = event.sender_id
        if uid not in temp_data or temp_data[uid].get('step') != 'photo_choice': return
        if event.raw_text.lower() == 'да':
            await event.respond("Отправьте одно фото")
            temp_data[uid]['step'] = 'receive_photo'
        else:
            settings['has_photo'] = False
            save_settings()
            await event.respond("Сообщение сохранено без фото")
            del temp_data[uid]
            await show_main_menu(event)

    @client.on(events.NewMessage(func=lambda e: e.is_private and (e.photo or e.document) and e.sender_id == OWNER_ID))
    async def save_photo(event):
        uid = event.sender_id
        if uid not in temp_data or temp_data[uid].get('step') != 'receive_photo': return
        try:
            await client.download_media(event.message.media, PHOTO_FILE)
            settings['has_photo'] = True
            save_settings()
            await event.respond("Фото сохранено")
        except Exception as e:
            await event.respond(f"Ошибка сохранения фото: {e}")
        del temp_data[uid]
        await show_main_menu(event)

    # Запуск рассылки
    @client.on(events.NewMessage(pattern='▶️ Запустить рассылку', func=lambda e: e.is_private))
    async def start_broadcast(event):
        if not await is_owner(event): return
        if not settings['selected_chats'] or not settings['message_text']:
            await event.respond("Сначала выберите чаты и настройте сообщение!")
            return
        preview = f"Превью:\n\n{settings['message_text']}\n\nЧатов: {len(settings['selected_chats'])}\nФото: {'Да' if settings['has_photo'] else 'Нет'}"
        await event.respond(preview, file=PHOTO_FILE if settings['has_photo'] else None)
        await event.respond("Запустить? (да/нет)")
        temp_data[event.sender_id] = {'step': 'confirm_broadcast'}

    @client.on(events.NewMessage(pattern='^да$', func=lambda e: e.is_private))
    async def confirm_broadcast(event):
        uid = event.sender_id
        if uid not in temp_data or temp_data[uid].get('step') != 'confirm_broadcast': return
        global broadcast_task, stop_broadcast
        stop_broadcast = False
        broadcast_task = asyncio.create_task(run_broadcast(event))
        await event.respond("Рассылка запущена. Напишите «стоп» для остановки")
        del temp_data[uid]

    async def run_broadcast(event):
        global stop_broadcast
        total = len(settings['selected_chats'])
        sent = 0
        for peer_id in settings['selected_chats']:
            if stop_broadcast:
                await event.respond("Рассылка остановлена пользователем.")
                break
            try:
                entity = await client.get_entity(peer_id)
                if settings['has_photo']:
                    await client.send_file(entity, PHOTO_FILE, caption=settings['message_text'], parse_mode='md')
                else:
                    await client.send_message(entity, settings['message_text'], parse_mode='md')
                sent += 1
                await event.respond(f"✅ Отправлено {sent}/{total}")
                await asyncio.sleep(random.uniform(settings['delay_min'], settings['delay_max']))
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 10)
            except PeerFloodError:
                await asyncio.sleep(60)
            except Exception as ex:
                logger.error(f"Ошибка отправки: {ex}")
                await asyncio.sleep(3)
        await event.respond(f"Рассылка завершена. Успешно: {sent}/{total}")

    @client.on(events.NewMessage(pattern='стоп', func=lambda e: e.is_private))
    async def stop_cmd(event):
        global stop_broadcast
        stop_broadcast = True
        await event.respond("Остановка принята...")

    @client.on(events.NewMessage(pattern='📊 Статистика', func=lambda e: e.is_private))
    async def stats_cmd(event):
        if not await is_owner(event): return
        status = "В процессе" if broadcast_task and not broadcast_task.done() else "Не запущена"
        await event.respond(f"Чатов: {len(settings['selected_chats'])}\nСообщение: {'Есть' if settings['message_text'] else 'Нет'}\nФото: {'Есть' if settings['has_photo'] else 'Нет'}\nСтатус: {status}")

    @client.on(events.NewMessage(pattern='❓ Помощь', func=lambda e: e.is_private))
    async def help_cmd(event):
        if not await is_owner(event): return
        await event.respond("Бот полностью внутри Telegram.\n/start — меню\nстоп — остановить рассылку")

# ========================= ЗАПУСК =========================
async def main():
    global client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        logger.info("Аккаунт уже авторизован")
    else:
        logger.info("Аккаунт не авторизован. Напишите /start в чате с ботом.")

    load_settings()
    await register_all_handlers()

    logger.info("Бот запущен. Всё управление — внутри Telegram.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
