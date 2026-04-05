from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID
from utils.pyrogram_manager import pyrogram_manager
from keyboards.inline import main_menu_kb

router = Router()

class AccountStates(StatesGroup):
    waiting_session_name = State()

@router.callback_query(F.data == "add_account")
async def cb_add_account(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text(
        "Введите название сессии (любое имя, например: myacc1):"
    )
    await state.set_state(AccountStates.waiting_session_name)
    await callback.answer()


@router.message(AccountStates.waiting_session_name)
async def process_session_name(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return

    session_name = message.text.strip()
    if len(session_name) < 3:
        await message.answer("Имя сессии слишком короткое.")
        return

    await message.answer(f"⏳ Запускаю авторизацию для сессии <b>{session_name}</b>...\n\nPyrogram сейчас попросит номер телефона, код из SMS и пароль (если есть).", parse_mode="HTML")

    try:
        account_id = len(pyrogram_manager.clients) + 1
        await pyrogram_manager.add_account(account_id, session_name)

        await message.answer(
            f"✅ Аккаунт <b>{session_name}</b> успешно добавлен и запущен!",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка авторизации:\n{str(e)[:500]}")

    await state.clear()
