# keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить аккаунт", callback_data="add_account")
    builder.button(text="📋 Мои аккаунты", callback_data="list_accounts")
    builder.button(text="📋 Мои чаты", callback_data="list_chats")
    builder.button(text="➕ Добавить чат", callback_data="add_chat")
    builder.button(text="🚀 Новая рассылка", callback_data="new_broadcast")
    builder.adjust(2)
    return builder.as_markup()

def accounts_keyboard(accounts):
    builder = InlineKeyboardBuilder()
    for acc in accounts:
        status = "✅" if acc["is_active"] else "⚪"
        builder.button(text=f"{status} {acc['session_name']}", callback_data=f"select_account:{acc['id']}")
    builder.button(text="← Назад", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()
