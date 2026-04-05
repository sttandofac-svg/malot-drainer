# handlers/accounts.py  ← ЗАМЕНИ ПОЛНОСТЬЮ (упрощённая версия через телефон)
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID
from utils.pyrogram_manager import pyrogram_manager
from keyboards.inline import main_menu_kb

router = Router()

class PhoneLoginStates(StatesGroup):
    waiting_phone = State()

@router.callback_query(F.data == "add_account")
async def cb_add_account(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text(
        "📱 Введите номер телефона:\n"
        "Пример: +79161234567"
    )
    await state.set_state(PhoneLoginStates.waiting_phone)
    await callback.answer()


@router.message(PhoneLoginStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return

    phone = message.text.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    session_name = f"session_{phone[-8:]}"

    await message.answer(f"⏳ Подключаюсь с номером {phone}...\nЭто может занять 10-30 секунд.")

    try:
        account_id = len(pyrogram_manager.clients) + 1
        await pyrogram_manager.add_account(account_id, session_name, phone)

        await message.answer(
            f"✅ Аккаунт успешно добавлен!\n"
            f"Номер: <b>{phone}</b>\n"
            f"Сессия: <b>{session_name}</b>",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
        print(f"[SUCCESS] Аккаунт {phone} добавлен")

    except Exception as e:
        await message.answer(f"❌ Ошибка авторизации:\n{str(e)[:400]}")

    await state.clear()
