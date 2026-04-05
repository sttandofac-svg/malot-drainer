from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from keyboards.inline import main_menu_kb
from config import OWNER_ID

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer(
        "🔥 <b>Mass Sender v2</b>\n\n"
        "Управление массовой рассылкой через Telegram.\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
