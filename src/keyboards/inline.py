import logging

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.utils.text_manager import text_manager

logger = logging.getLogger(__name__)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    try:
        builder.button(text=text_manager.get("menu.main.buttons.statistics"), callback_data="main_menu:statistics")
        builder.button(text=text_manager.get("menu.main.buttons.history"), callback_data="main_menu:history")
        builder.button(text=text_manager.get("menu.main.buttons.my_profile"), callback_data="main_menu:profile")
        builder.button(text=text_manager.get("menu.main.buttons.start_shift"), callback_data="shift:start")

        builder.adjust(2,2)
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Failed to create main menu keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[])

def active_shift_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    try:
        builder.button(text=text_manager.get("shift.active.buttons.enter_initial_data"), callback_data="shift:initial_data")
        builder.button(text=text_manager.get("shift.active.buttons.add_order_1"), callback_data="shift:add_order_1")
        builder.button(text=text_manager.get("shift.active.buttons.add_order_2"), callback_data="shift:add_order_2")
        builder.button(text=text_manager.get("shift.active.buttons.add_mileage"), callback_data="shift:add_mileage")

        builder.button(text=text_manager.get("shift.active.buttons.add_order_3"), callback_data="shift:add_order_3")
        builder.button(text=text_manager.get("shift.active.buttons.add_order_4"), callback_data="shift:add_order_4")
        builder.button(text=text_manager.get("shift.active.buttons.add_tips"), callback_data="shift:add_tips")

        builder.button(text=text_manager.get("shift.active.buttons.add_expenses"), callback_data="shift:add_expenses")

        builder.button(text=text_manager.get("shift.active.buttons.shift_stats"), callback_data="shift:stats")
        builder.button(text=text_manager.get("shift.active.buttons.end_shift"), callback_data="shift:end")
        builder.adjust(1,3,3,1,2)
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Failed to create active shift keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[])
