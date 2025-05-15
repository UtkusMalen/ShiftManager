import logging
from typing import List
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import Shift, ShiftStatus, ShiftEventType
from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def _calculate_shift_profit_for_button(shift: Shift) -> float:
    if not shift.start_time or not shift.end_time:
        return 0.0

    duration_seconds = (shift.end_time - shift.start_time).total_seconds()
    if duration_seconds <= 0:
        return 0.0

    duration_hours = duration_seconds / 3600.0

    revenue_from_time = duration_hours * (shift.rate or 0.0)
    revenue_from_orders = (shift.orders_count or 0) * (shift.order_rate or 0.0)
    total_tips = shift.total_tips or 0.0
    gross_income = revenue_from_time + revenue_from_orders + total_tips

    mileage_cost = (shift.total_mileage or 0.0) * (shift.mileage_rate or 0.0)

    manual_food_expenses = 0.0
    manual_other_expenses = 0.0
    if hasattr(shift, 'events') and shift.events:
        for event in shift.events:
            if event.event_type == ShiftEventType.ADD_EXPENSE and isinstance(event.details, dict):
                amount = event.details.get("amount", 0.0)
                category_code = event.details.get("category_code", "other")
                if category_code == "food":
                    manual_food_expenses += amount
                elif category_code == "other":
                    manual_other_expenses += amount

    total_manual_expenses = manual_food_expenses + manual_other_expenses
    total_operational_expenses = total_manual_expenses + mileage_cost

    tax_rate_decimal = 0.05
    tax_amount = gross_income * tax_rate_decimal

    net_profit = gross_income - total_operational_expenses - tax_amount
    return net_profit


def history_selection_keyboard(shifts: List[Shift],current_page: int,total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if shifts:
        for shift in shifts:
            if shift.id is None:
                logger.warning(f"Shift with no ID encountered in history_selection_keyboard: {shift}")
                continue
            if shift.start_time and shift.end_time and shift.status == ShiftStatus.COMPLETED:
                start_time_local = shift.start_time
                if start_time_local.tzinfo is None:
                    start_time_local = start_time_local.replace(tzinfo=MOSCOW_TZ)
                else:
                    start_time_local = start_time_local.astimezone(MOSCOW_TZ)

                end_time_local = shift.end_time
                if end_time_local.tzinfo is None:
                    end_time_local = end_time_local.replace(tzinfo=MOSCOW_TZ)
                else:
                    end_time_local = end_time_local.astimezone(MOSCOW_TZ)

                date_str = start_time_local.strftime('%d.%m')
                start_hm_str = start_time_local.strftime('%H:%M')
                end_hm_str = end_time_local.strftime('%H:%M')

                profit = _calculate_shift_profit_for_button(shift)
                profit_str = f"{profit:,.0f}₽".replace(",", " ")

                shift_display_text = tm.get(
                    "history.buttons.shift_entry_completed",
                    date=date_str,
                    profit=profit_str,
                    start_time=start_hm_str,
                    end_time=end_hm_str
                )
            elif shift.start_time:
                start_time_local = shift.start_time
                if start_time_local.tzinfo is None:
                    start_time_local = start_time_local.replace(tzinfo=MOSCOW_TZ)
                else:
                    start_time_local = start_time_local.astimezone(MOSCOW_TZ)

                date_str = start_time_local.strftime('%d.%m')
                time_str = start_time_local.strftime('%H:%M')

                shift_display_text = tm.get(
                    "history.buttons.shift_entry_started",
                    date=date_str,
                    start_time=time_str
                )
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

def shift_details_keyboard(shift_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tm.get("history.buttons.delete_shift", "🗑️ Удалить смену"),callback_data=f"history:delete_shift_prompt:{shift_id}")
    builder.button(text=tm.get("history.buttons.back_to_list", "К списку смен"), callback_data="main_menu:history")
    builder.button(text=tm.get("common.buttons.back_to_main_menu", "Главное меню"), callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def confirm_delete_shift_keyboard(shift_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tm.get("common.buttons.yes", "✅Да"),
        callback_data=f"history:delete_shift_confirm:{shift_id}"
    )
    builder.button(
        text=tm.get("common.buttons.no", "❌Нет"),
        callback_data=f"history:delete_shift_cancel:{shift_id}"
    )
    builder.adjust(2)
    return builder.as_markup()