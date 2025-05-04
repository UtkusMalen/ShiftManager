import logging
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)

def active_shift_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    try:
        builder.button(text=tm.get("shift.active.buttons.enter_initial_data"), callback_data="shift:initial_data")
        builder.button(text=tm.get("shift.active.buttons.add_order_1"), callback_data="shift:add_order_1")
        builder.button(text=tm.get("shift.active.buttons.add_order_2"), callback_data="shift:add_order_2")
        builder.button(text=tm.get("shift.active.buttons.add_order_3"), callback_data="shift:add_order_3")
        builder.button(text=tm.get("shift.active.buttons.add_order_4"), callback_data="shift:add_order_4")

        builder.button(text=tm.get("shift.active.buttons.add_mileage"), callback_data="shift:add_mileage")
        builder.button(text=tm.get("shift.active.buttons.add_tips"), callback_data="shift:add_tips")
        builder.button(text=tm.get("shift.active.buttons.add_expenses"), callback_data="shift:add_expenses")
        builder.button(text=tm.get("shift.active.buttons.end_shift"), callback_data="shift:end")
        builder.button(text=tm.get("menu.main.buttons.main_menu"), callback_data="main_menu")
        builder.adjust(1,2,2,2,1,1,1)
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Failed to create active shift keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[])

def mileage_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240]
    for button_text in buttons:
        builder.button(text=str(button_text), callback_data=f"initial_data:mileage:{button_text}")
    builder.button(text=tm.get("shift.initial_data.cancel"), callback_data="initial_data:cancel")
    builder.adjust(4,4,4,4,1)
    return builder.as_markup()