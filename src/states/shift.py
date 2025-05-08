from aiogram.fsm.state import State, StatesGroup

class ShiftStates(StatesGroup):
    in_shift_active = State()
    in_initial_data_menu = State()
    in_initial_data_rate = State()
    in_initial_data_order_rate = State()
    in_initial_data_mileage_rate = State()
    in_shift_mileage = State()
    in_shift_tips = State()
    in_shift_expenses = State()
    in_shift_expenses_category = State()