# states/user_states.py
from aiogram.fsm.state import State, StatesGroup

class BroadcastStates(StatesGroup):
    waiting_for_session_name = State()
    waiting_for_api_id = State()
    waiting_for_api_hash = State()
    
    waiting_for_chat_input = State()      # добавить чат
    waiting_for_group_name = State()
    
    choosing_account = State()
    choosing_chat_group_or_chats = State()
    waiting_for_message_text = State()
    waiting_for_photo = State()           # одно или альбом
    waiting_for_delay = State()
    confirm_broadcast = State()
