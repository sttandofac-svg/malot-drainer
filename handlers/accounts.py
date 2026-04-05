# handlers/accounts.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states.user_states import AccountStates
from config import OWNER_ID
from utils.pyrogram_manager import pyrogram_manager
from keyboards.inline import main_menu_kb

router = Router()

@router.callback_query(F.data == "add_account")
async def cb_add_account(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text("Введите имя сессии (например: session1):")
    await state.set_state(AccountStates.waiting_session_name)
    await callback.answer()


@router.message(AccountStates.waiting_session_name)
async def process_session_name(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Имя сессии слишком короткое. Минимум 3 символа.")
        return
    await state.update_data(session_name=name)
    await message.answer("Введите api_id (число):")
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
        await message.answer("❌ api_id должен быть числом. Попробуйте снова.")


@router.message(AccountStates.waiting_api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return

    data = await state.get_data()
    session_name = data["session_name"]
    api_id = data["api_id"]
    api_hash = message.text.strip().strip('"').strip("'")

    await message.answer("⏳ Подключаюсь к Telegram... Это может занять 10–20 секунд.")

    try:
        account_id = len(pyrogram_manager.clients) + 1
        await pyrogram_manager.add_account(account_id, session_name, api_id, api_hash)

        await message.answer(
            f"✅ <b>Аккаунт успешно добавлен!</b>\n\n"
            f"Название: <b>{session_name}</b>\n"
            f"ID аккаунта: <code>{account_id}</code>\n\n"
            "Теперь можно использовать его для рассылки.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
        print(f"[SUCCESS] Аккаунт {session_name} добавлен пользователем {message.from_user.id}")

    except Exception as e:
        error_str = str(e)
        await message.answer(
            f"❌ Не удалось запустить аккаунт.\n\n"
            f"Ошибка: {error_str[:350]}...",
            reply_markup=main_menu_kb()
        )
        print(f"[ERROR] При добавлении аккаунта: {error_str}")

    await state.clear()
