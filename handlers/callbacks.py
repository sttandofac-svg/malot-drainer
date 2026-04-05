# handlers/callbacks.py  ← ЗАМЕНИ ПОЛНОСТЬЮ
from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import OWNER_ID
from keyboards.inline import main_menu_kb

router = Router()

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.message.edit_text(
        "🔥 <b>Mass Sender v2</b>\n\nГлавное меню:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
