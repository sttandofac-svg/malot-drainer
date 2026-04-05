from aiogram.fsm.state import State, StatesGroup

class AccountStates(StatesGroup):
    waiting_session_name = State()
    waiting_api_id = State()
    waiting_api_hash = State()

class ChatStates(StatesGroup):
    waiting_chat_input = State()
    waiting_group_name = State()

class BroadcastStates(StatesGroup):
    choosing_account = State()
    choosing_chats = State()
    waiting_text = State()
    waiting_media = State()
    waiting_delay = State()
    confirm = State()
