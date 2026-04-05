# handlers/broadcast.py  ← ЗАМЕНИ ПОЛНОСТЬЮ (главный модуль рассылки)
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from states.user_states import BroadcastStates
from config import OWNER_ID
from utils.pyrogram_manager import pyrogram_manager
from keyboards.inline import main_menu_kb
import asyncio
import time

router = Router()
active_broadcasts = {}  # chat_id: task

@router.callback_query(F.data == "new_broadcast")
async def cb_new_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return
    accounts = list(pyrogram_manager.clients.keys())
    if not accounts:
        await callback.message.edit_text("❌ Сначала добавьте хотя бы один аккаунт!", reply_markup=main_menu_kb())
        return

    await callback.message.edit_text("Выберите аккаунт для рассылки (пока просто введите ID аккаунта из списка выше):")
    await state.set_state(BroadcastStates.choosing_account)

@router.message(BroadcastStates.choosing_account)
async def process_account(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    try:
        account_id = int(message.text.strip())
        if account_id not in pyrogram_manager.clients:
            await message.answer("Такого аккаунта нет.")
            return
        await state.update_data(account_id=account_id)
        await message.answer("Отправьте текст сообщения (поддержка MarkdownV2):")
        await state.set_state(BroadcastStates.waiting_text)
    except:
        await message.answer("Введите числовой ID аккаунта.")

@router.message(BroadcastStates.waiting_text)
async def process_text(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.update_data(text=message.text)
    await message.answer(
        "Отправьте фото (одно или несколько для альбома) или напишите «готов» если без медиа.\n"
        "Максимум 10 фото."
    )
    await state.set_state(BroadcastStates.waiting_media)

@router.message(BroadcastStates.waiting_media, F.photo)
async def process_photo(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data = await state.get_data()
    media = data.get("media", [])
    media.append(message.photo[-1].file_id)
    await state.update_data(media=media)
    await message.answer(f"Фото добавлено ({len(media)}/10). Отправьте ещё или напишите «готов».")

@router.message(BroadcastStates.waiting_media, F.text.lower() == "готов")
async def media_ready(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("Введите задержку между сообщениями в секундах (например: 2):")
    await state.set_state(BroadcastStates.waiting_delay)

@router.message(BroadcastStates.waiting_delay)
async def process_delay(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    try:
        delay = float(message.text.strip())
        await state.update_data(delay=delay)
        await message.answer("✅ Всё готово. Нажмите кнопку ниже для запуска.", 
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Запустить рассылку", callback_data="start_broadcast")]]))
        await state.set_state(BroadcastStates.confirm)
    except:
        await message.answer("Введите число.")

# Здесь можно добавить кнопку остановки и живой прогресс — расширим в следующей итерации по запросу
