from aiogram.fsm.state import State, StatesGroup

class MenuStates(StatesGroup):
    in_main_menu = State()
    in_statistics = State()
    in_history = State()
    in_profile = State()