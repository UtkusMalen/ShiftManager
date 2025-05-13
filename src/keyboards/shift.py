import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.sql.functions import current_time

from src.utils.text_manager import text_manager as tm

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
logger = logging.getLogger(__name__)

def active_shift_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    try:
        builder.button(text=tm.get("shift.active.buttons.enter_initial_data"), callback_data="shift:initial_data")
        builder.button(text=tm.get("shift.active.buttons.add_order_1"), callback_data="shift:add_order_1")
        builder.button(text=tm.get("shift.active.buttons.add_order_2"), callback_data="shift:add_order_2")
        builder.button(text=tm.get("shift.active.buttons.add_order_3"), callback_data="shift:add_order_3")
        builder.button(text=tm.get("shift.active.buttons.add_order_4"), callback_data="shift:add_order_4")

        builder.button(text=tm.get("shift.active.buttons.add_mileage"), callback_data="shift:add_mileage_prompt")
        builder.button(text=tm.get("shift.active.buttons.add_tips"), callback_data="shift:add_tips_prompt")
        builder.button(text=tm.get("shift.active.buttons.add_expenses"), callback_data="shift:add_expenses_prompt")
        builder.button(text=tm.get("shift.active.buttons.end_shift"), callback_data="shift:end")
        builder.button(text=tm.get("menu.main.buttons.main_menu"), callback_data="main_menu")
        builder.adjust(1,2,2,2,1,1,1)
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Failed to create active shift keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[])

def mileage_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [20, 40, 60, 70, 80, 100, 120, 140, 160, 180, 200, 220]
    for button_text in buttons:
        builder.button(text=str(button_text), callback_data=f"shift:mileage:add:{button_text}")
    builder.button(text=tm.get("common.buttons.cancel", "Отмена"), callback_data="shift:show_active")
    builder.adjust(4)
    return builder.as_markup()

def tips_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [50, 100, 150, 200, 250, 300, 350, 400]
    for button_text in buttons:
        builder.button(text=str(button_text), callback_data=f"shift:tips:add:{button_text}")
    builder.button(text=tm.get("common.buttons.cancel", "Отмена"), callback_data="shift:show_active")
    builder.adjust(4)
    return builder.as_markup()

def cancel_action_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tm.get("common.buttons.cancel", "Отмена"), callback_data="shift:show_active")
    return builder.as_markup()

def expenses_category_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tm.get("shift.expenses.categories.food", "Еда"), callback_data="shift:expenses:category:food")
    builder.button(text=tm.get("shift.expenses.categories.other", "Другое"), callback_data="shift:expenses:category:other")
    builder.button(text=tm.get("common.buttons.cancel", "Отмена"), callback_data="shift:show_active")
    builder.adjust(2,1)
    return builder.as_markup()

def get_start_time_options_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    now_moscow = datetime.now(MOSCOW_TZ)
    current_time_str = now_moscow.strftime("%H:%M %d.%m")

    builder.button(
        text=tm.get("common.buttons.use_current_time", current_time_str=current_time_str),
        callback_data="shift:start_now"
    )
    builder.button(
        text=tm.get("common.buttons.specify_time"),
        callback_data="shift:start_manual_time"
    )
    builder.button(
        text=tm.get("common.buttons.cancel", "Отмена"),
        callback_data="main_menu"
    )
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_start_time_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tm.get("common.buttons.cancel"),
        callback_data="shift:start_cancel_manual_input"
    )
    return builder.as_markup()

def get_end_time_options_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    now_moscow = datetime.now(MOSCOW_TZ)
    current_time_str = now_moscow.strftime("%H:%M")

    builder.button(
        text=tm.get("common.buttons.use_current_time", current_time_str=current_time_str),
        callback_data="shift:end_now"
    )
    builder.button(
        text=tm.get("common.buttons.specify_time"),
        callback_data="shift:end_manual_time"
    )
    builder.button(
        text=tm.get("common.buttons.cancel"),
        callback_data="shift:show_active"
    )
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_end_time_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tm.get("common.buttons.cancel"),
        callback_data="shift:end_cancel_manual_input"
    )
    return builder.as_markup()