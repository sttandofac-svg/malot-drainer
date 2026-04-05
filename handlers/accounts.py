# handlers/accounts.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states.user_states import AccountStates
from config import OWNER_ID
from keyboards.inline import main_menu_kb, back_to_menu

router = Router()

@router.callback_query(F.data == "add_account")
async def add_account_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.message.edit_text("Введите имя сессии (session_name):")
    await state.set_state(AccountStates.waiting_session_name)
    await callback.answer()
