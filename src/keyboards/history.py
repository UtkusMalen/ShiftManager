import logging
from typing import List
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import Shift
from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

def history_selection_keyboard(shifts: List[Shift]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if shifts:
        for shift in shifts:
            if shift.id is None:
                logger.warning(f"Shift with no ID encountered in history_selection_keyboard: {shift}")
                continue
            if shift.end_time:
                end_time_aware = shift.end_time.astimezone(MOSCOW_TZ) if shift.end_time.tzinfo else MOSCOW_TZ.localize(shift.end_time)
                shift_display_text = tm.get(
                    "history.buttons.shift_entry_ended",
                    date=end_time_aware.strftime('%d.%m.%Y'),
                    time=end_time_aware.strftime('%H:%M')
                )
            elif shift.start_time:
                start_time_aware = shift.start_time.astimezone(MOSCOW_TZ) if shift.start_time.tzinfo else MOSCOW_TZ.localize(shift.start_time)
                shift_display_text = tm.get(
                    "history.buttons.shift_entry_started",
                    date=start_time_aware.strftime('%d.%m.%Y'),
                    time=start_time_aware.strftime('%H:%M')
                )
            else:
                shift_display_text = tm.get("history.buttons.shift_entry_unknown", id=shift.id)

            builder.button(
                text=shift_display_text,
                callback_data=f"history:shift:{shift.id}"
            )
        builder.adjust(1)
    builder.button(text=tm.get("common.buttons.back_to_main_menu", "Главное меню"), callback_data="main_menu")
    if shifts:
        builder.adjust(1)
    return builder.as_markup()

def shift_details_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tm.get("history.buttons.back_to_list", "К списку смен"), callback_data="main_menu:history")
    builder.button(text=tm.get("common.buttons.back_to_main_menu", "Главное меню"), callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()