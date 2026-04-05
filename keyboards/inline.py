# keyboards/inline.py  ← СОЗДАЙ ПАПКУ keyboards И ФАЙЛ
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить аккаунт", callback_data="add_account")
    builder.button(text="📋 Мои аккаунты", callback_data="list_accounts")
    builder.button(text="📋 Мои чаты", callback_data="list_chats")
    builder.button(text="➕ Добавить чат", callback_data="add_chat")
    builder.button(text="🚀 Новая рассылка", callback_data="new_broadcast")
    builder.adjust(2)
    return builder.as_markup()

def back_to_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="← Главное меню", callback_data="main_menu")
    return builder.as_markup()
