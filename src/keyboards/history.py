import logging
from typing import List
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import Shift, ShiftStatus
from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

def history_selection_keyboard(shifts: List[Shift],current_page: int,total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if shifts:
        for shift in shifts:
            if shift.id is None:
                logger.warning(f"Shift with no ID encountered in history_selection_keyboard: {shift}")
                continue
            if shift.start_time:
                start_time_local = shift.start_time
                if start_time_local.tzinfo is None:
                    start_time_local = start_time_local.replace(tzinfo=MOSCOW_TZ)
                else:
                    start_time_local = start_time_local.astimezone(MOSCOW_TZ)

                date_str = start_time_local.strftime('%d.%m.%Y')
                time_str = start_time_local.strftime('%H:%M')

                if shift.status == ShiftStatus.COMPLETED and shift.end_time:
                    shift_display_text = tm.get(
                        "history.buttons.shift_entry_completed_display",
                        date=date_str,
                        start_time=time_str
                    )
                else:
                    shift_display_text = tm.get(
                        "history.buttons.shift_entry_started",
                        date=date_str,
                        start_time=time_str
                    )
            else:
                shift_display_text = tm.get("history.buttons.shift_entry_unknown", id=shift.id)

            builder.button(
                text=shift_display_text,
                callback_data=f"history:shift:{shift.id}"
            )
        builder.adjust(1)

    pagination_buttons = []
    has_prev_page = current_page > 1
    has_next_page = current_page < total_pages

    if has_prev_page:
        pagination_buttons.append(
            InlineKeyboardBuilder().button(text="⬅️ Пред.", callback_data=f"history:page:{current_page - 1}").as_markup().inline_keyboard[0][0]
        )

    if total_pages > 1:
         pagination_buttons.append(
             InlineKeyboardBuilder().button(text=f"📄{current_page}/{total_pages}", callback_data="history:page:noop").as_markup().inline_keyboard[0][0]
         )

    if has_next_page:
        pagination_buttons.append(
            InlineKeyboardBuilder().button(text="След. ➡️", callback_data=f"history:page:{current_page + 1}").as_markup().inline_keyboard[0][0]
        )

    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.button(text=tm.get("common.buttons.back_to_main_menu", "Главное меню"), callback_data="main_menu")
    return builder.as_markup()

def shift_details_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tm.get("history.buttons.back_to_list", "К списку смен"), callback_data="main_menu:history")
    builder.button(text=tm.get("common.buttons.back_to_main_menu", "Главное меню"), callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()