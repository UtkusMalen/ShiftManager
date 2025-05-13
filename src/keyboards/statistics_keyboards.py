from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.utils.text_manager import text_manager as tm

def get_period_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tm.get("statistics.buttons.current_week", "Текущая неделя"),
        callback_data="stats_period:current_week"
    )
    builder.button(
        text=tm.get("statistics.buttons.last_week", "Прошлая неделя"),
        callback_data="stats_period:last_week"
    )
    builder.button(
        text=tm.get("statistics.buttons.current_month", "Текущий месяц"),
        callback_data="stats_period:current_month",
    )
    builder.button(
        text=tm.get("statistics.buttons.last_month", "Предыдущий месяц"),
        callback_data="stats_period:last_month",
    )
    builder.button(
        text=tm.get("statistics.buttons.all_time", "всё время"),
        callback_data="stats_period:all_time",
    )
    builder.button(
        text=tm.get("common.buttons.back_to_main_menu", "Главное меню"),
        callback_data="main_menu",
    )
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def back_to_period_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tm.get("statistics.buttons.back_to_select", "Назад к выбору периода"),
        callback_data="statistics:select_period"
    )
    builder.button(
        text=tm.get("common.buttons.back_to_main_menu", "Главное меню"),
        callback_data="main_menu",
    )
    return builder.as_markup()