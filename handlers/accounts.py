# handlers/accounts.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states.user_states import AccountStates
from config import OWNER_ID
from database.db import init_db  # можно расширить позже
from utils.pyrogram_manager import pyrogram_manager
from keyboards.inline import main_menu_kb, back_to_menu

router = Router()

@router.callback_query(F.data == "add_account")
async def cb_add_account(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await callback.message.edit_text("Введите имя сессии (например: my_session):")
    await state.set_state(AccountStates.waiting_session_name)
    await callback.answer()

@router.message(AccountStates.waiting_session_name)
async def process_session_name(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.update_data(session_name=message.text.strip())
    await message.answer("Введите api_id:")
    await state.set_state(AccountStates.waiting_api_id)

@router.message(AccountStates.waiting_api_id)
async def process_api_id(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    try:
        api_id = int(message.text.strip())
        await state.update_data(api_id=api_id)
        await message.answer("Введите api_hash:")
        await state.set_state(AccountStates.waiting_api_hash)
    except ValueError:
        await message.answer("api_id должен быть числом. Попробуйте снова.")

@router.message(AccountStates.waiting_api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data = await state.get_data()
    session_name = data["session_name"]
    api_id = data["api_id"]
    api_hash = message.text.strip()

    # Добавляем аккаунт в Pyrogram
    await pyrogram_manager.add_account(
        account_id=len(pyrogram_manager.clients) + 1,
        session_name=session_name,
        api_id=api_id,
        api_hash=api_hash
    )

    await message.answer(
        f"✅ Аккаунт <b>{session_name}</b> успешно добавлен и запущен!",
        reply_markup=main_menu_kb()
    )
    await state.clear()
