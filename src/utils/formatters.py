import logging
from datetime import datetime
from typing import Dict, Any, List
from zoneinfo import ZoneInfo

from src.db.models import Shift, ShiftEventType, ShiftEvent
from src.utils.text_manager import text_manager

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo('Europe/Moscow')


def format_duration(start_time: datetime, end_time: datetime) -> str:
    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        logger.error(f"Invalid input types for format_duration: start={type(start_time)}, end={type(end_time)}")
        return "Ошибка времени"

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=MOSCOW_TZ)
        logger.warning("format_duration received naive start_time, assuming Moscow TZ.")
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=MOSCOW_TZ)
        logger.warning("format_duration received naive end_time, assuming Moscow TZ.")

    start_time = start_time.astimezone(MOSCOW_TZ)
    end_time = end_time.astimezone(MOSCOW_TZ)

    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())

    if total_seconds < 0:
        logger.warning(f"Calculated negative duration: start={start_time}, end={end_time}")
        total_seconds = 0

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours % 10 == 1 and hours % 100 != 11:
        h_str = f"{hours} час"
    elif 2 <= hours % 10 <= 4 and (hours % 100 < 10 or hours % 100 >= 20):
        h_str = f"{hours} часа"
    else:
        h_str = f"{hours} часов"

    if minutes == 1 or (minutes % 10 == 1 and minutes % 100 != 11 and minutes > 20):
        m_str = f"{minutes} минута"
    elif (1 < minutes < 5) or \
            (1 < minutes % 10 < 5 and (minutes % 100 < 10 or minutes % 100 >= 20) and minutes > 20):
        m_str = f"{minutes} минуты"
    else:
        m_str = f"{minutes} минут"

    return f"{h_str}, {m_str}"


async def get_active_shift_message_text(shift: Shift) -> str:
    now_moscow = datetime.now(MOSCOW_TZ)

    if shift.start_time.tzinfo is None:
        start_local = shift.start_time.replace(tzinfo=MOSCOW_TZ) # Corrected replace tzinfo
        logger.warning(f"Shift {shift.id} start_time was timezone-naive. Assuming Moscow time.")
    else:
        start_local = shift.start_time.astimezone(MOSCOW_TZ)

    history_lines: List[str] = []
    food_expenses_raw = 0.0
    other_expenses_raw = 0.0

    if hasattr(shift, 'events') and shift.events:
        valid_events = [e for e in shift.events if e.timestamp is not None]
        sorted_events: List[ShiftEvent] = sorted(valid_events, key=lambda e: e.timestamp, reverse=True)

        for event in sorted_events: # Iterate through all events for history and expense calculation
            event_time_str = event.timestamp.astimezone(MOSCOW_TZ).strftime('%H:%M')
            details_data: Dict[str, Any] = event.details if isinstance(event.details, dict) else {}

            if event.event_type == ShiftEventType.START_SHIFT:
                event_type_str = "🏁 Старт"
                details_str = details_data.get("message", "Смена начата")
            elif event.event_type == ShiftEventType.COMPLETE_SHIFT:
                event_type_str = "🏁 Финиш"
                details_str = details_data.get("message", "Смена завершена")
            elif event.event_type == ShiftEventType.ADD_ORDER:
                event_type_str = "📦 +Заказ"
                count = details_data.get('count', '?')
                details_str = details_data.get("description", f"+{count} заказ(а)")
            elif event.event_type == ShiftEventType.ADD_TIPS:
                event_type_str = "💰 +Чаевые"
                amount = details_data.get('amount', '?')
                details_str = details_data.get("description", f"+{amount} руб.")
            elif event.event_type == ShiftEventType.ADD_EXPENSE:
                event_type_str = "💸 -Расход"
                amount = details_data.get('amount', 0.0)
                category = details_data.get('category', 'Прочее') # For display string
                category_code = details_data.get('category_code', 'other') # For calculation
                details_str = details_data.get("description", f"-{amount} руб. ({category})")
                if category_code == "food":
                    food_expenses_raw += float(amount)
                elif category_code == "other":
                    other_expenses_raw += float(amount)
            elif event.event_type == ShiftEventType.ADD_MILEAGE:
                event_type_str = "🚗 Пробег"
                distance = details_data.get('distance_km', '?')
                details_str = details_data.get("description", f"+{distance} км")
            elif event.event_type == ShiftEventType.UPDATE_INITIAL_DATA:
                event_type_str = "⚙️ Параметры"
                details_str = details_data.get("description", "Параметры обновлены")
            else:
                event_type_str = event.event_type.name
                details_str = str(details_data) if details_data else "(нет данных)"

            line = f"<code>{event_time_str}</code> {event_type_str}: {details_str}"
            history_lines.append(line)

    history_entries_str = "\n".join(history_lines[:5])
    if not history_entries_str:
        history_entries_str = text_manager.get("shift.active.default_history", default="Пока пусто")

    orders_completed = shift.orders_count if shift.orders_count is not None else 0
    current_duration_seconds = (now_moscow - start_local).total_seconds() if now_moscow > start_local else 0
    current_duration_hours = current_duration_seconds / 3600.0

    orders_per_hour_raw = (orders_completed / current_duration_hours) if current_duration_hours > 0.001 else 0.0

    total_mileage_display = shift.total_mileage if shift.total_mileage is not None else 0.0
    total_tips_display_raw = shift.total_tips if shift.total_tips is not None else 0.0
    # manual_expenses_display = shift.total_expenses if shift.total_expenses is not None else 0.0 # Sum of all direct expenses

    revenue_from_time_raw = current_duration_hours * (shift.rate or 0.0)
    revenue_from_orders_raw = orders_completed * (shift.order_rate or 0.0)
    gross_income = revenue_from_time_raw + revenue_from_orders_raw + total_tips_display_raw

    mileage_cost_raw = total_mileage_display * (shift.mileage_rate or 0.0)

    # Total operational expenses = sum of categorized expenses + mileage cost
    # Note: shift.total_expenses on the model is the sum of food_expenses_raw + other_expenses_raw and any other manual expenses.
    # For this template, we are displaying food and other explicitly.
    total_operational_expenses = food_expenses_raw + other_expenses_raw + mileage_cost_raw

    tax_rate_decimal = 0.05
    tax_percentage = int(tax_rate_decimal * 100)
    tax_amount_raw = gross_income * tax_rate_decimal

    profit_raw = gross_income - total_operational_expenses - tax_amount_raw
    profit_per_hour_raw = (profit_raw / current_duration_hours) if current_duration_hours > 0.001 else 0.0

    status_text = text_manager.get(f"shift.status.{shift.status.value}", default=shift.status.value)

    return text_manager.get(
        "shift.active.message_template",
        date=start_local.strftime('%d.%m.%Y'),
        status=status_text,
        start_time=start_local.strftime('%H:%M МСК'),
        end_shift_time_label=text_manager.get("shift.active.current_time_label", default="⏱️ Время сейчас:"),
        current_time=now_moscow.strftime('%H:%M МСК'),
        duration=format_duration(start_local, now_moscow),
        orders_completed=orders_completed,
        orders_per_hour=f"{orders_per_hour_raw:.2f}",
        mileage=f"{total_mileage_display:.1f}",
        mileage_cost=f"{mileage_cost_raw:.2f}",
        food_expenses=f"{food_expenses_raw:.2f}",
        other_expenses=f"{other_expenses_raw:.2f}",
        tax_percentage=tax_percentage,
        tax=f"{tax_amount_raw:.2f}",
        revenue_from_orders=f"{revenue_from_orders_raw:.2f}",
        revenue_from_time=f"{revenue_from_time_raw:.2f}",
        total_tips=f"{total_tips_display_raw:.2f}",
        profit=f"{profit_raw:.2f}",
        profit_per_hour=f"{profit_per_hour_raw:.2f}",
        history_entries=history_entries_str
    )


async def format_completed_shift_details_message(shift: Shift) -> str:
    if not shift.start_time or not shift.end_time:
        logger.error(f"Attempted to format completed shift {shift.id} without start or end time.")
        return "Ошибка: Неполные данные по смене."

    start_local = shift.start_time.astimezone(MOSCOW_TZ) if shift.start_time.tzinfo else shift.start_time.replace(tzinfo=MOSCOW_TZ)
    end_local = shift.end_time.astimezone(MOSCOW_TZ) if shift.end_time.tzinfo else shift.end_time.replace(tzinfo=MOSCOW_TZ)


    history_lines: List[str] = []
    food_expenses_raw = 0.0
    other_expenses_raw = 0.0

    if hasattr(shift, 'events') and shift.events:
        valid_events = [e for e in shift.events if e.timestamp is not None]
        sorted_events: List[ShiftEvent] = sorted(valid_events, key=lambda e: e.timestamp, reverse=True)

        for event in sorted_events: # Iterate through all events for history and expense calculation
            event_time_str = event.timestamp.astimezone(MOSCOW_TZ).strftime('%H:%M')
            details_data: Dict[str, Any] = event.details if isinstance(event.details, dict) else {}
            if event.event_type == ShiftEventType.START_SHIFT:
                event_type_str = "🏁 Старт"
                details_str = details_data.get("message", "Смена начата")
            elif event.event_type == ShiftEventType.COMPLETE_SHIFT:
                event_type_str = "🏁 Финиш"
                details_str = details_data.get("message", "Смена завершена")
            elif event.event_type == ShiftEventType.ADD_ORDER:
                event_type_str = "📦 +Заказ"
                count = details_data.get('count', '?')
                details_str = details_data.get("description", f"+{count} заказ(а)")
            elif event.event_type == ShiftEventType.ADD_TIPS:
                event_type_str = "💰 +Чаевые"
                amount = details_data.get('amount', '?')
                details_str = details_data.get("description", f"+{amount} руб.")
            elif event.event_type == ShiftEventType.ADD_EXPENSE:
                event_type_str = "💸 -Расход"
                amount = details_data.get('amount', 0.0)
                category = details_data.get('category', 'Прочее') # For display string
                category_code = details_data.get('category_code', 'other') # For calculation
                details_str = details_data.get("description", f"-{amount} руб. ({category})")
                if category_code == "food":
                    food_expenses_raw += float(amount)
                elif category_code == "other":
                    other_expenses_raw += float(amount)
            elif event.event_type == ShiftEventType.ADD_MILEAGE:
                event_type_str = "🚗 +Пробег"
                distance = details_data.get('distance_km','?')
                details_str = details_data.get("description", f"+{distance} км")
            elif event.event_type == ShiftEventType.UPDATE_INITIAL_DATA:
                event_type_str = "⚙️ Параметры"
                details_str = details_data.get("description", "Параметры обновлены")
            else:
                event_type_str = event.event_type.name
                details_str = str(details_data) if details_data else "(нет данных)"
            line = f"<code>{event_time_str}</code> {event_type_str}: {details_str}"
            history_lines.append(line)

    history_entries_str = "\n".join(history_lines) if history_lines else text_manager.get("shift.active.default_history", default="Нет событий")

    orders_completed = shift.orders_count if shift.orders_count is not None else 0

    total_duration_seconds = (end_local - start_local).total_seconds() if end_local > start_local else 0
    total_duration_hours = total_duration_seconds / 3600.0

    orders_per_hour_raw = (orders_completed / total_duration_hours) if total_duration_hours > 0.001 else 0.0

    total_mileage_display = shift.total_mileage if shift.total_mileage is not None else 0.0
    total_tips_display_raw = shift.total_tips if shift.total_tips is not None else 0.0
    # manual_expenses_display = shift.total_expenses if shift.total_expenses is not None else 0.0

    revenue_from_time_raw = total_duration_hours * (shift.rate or 0.0)
    revenue_from_orders_raw = orders_completed * (shift.order_rate or 0.0)
    gross_income = revenue_from_time_raw + revenue_from_orders_raw + total_tips_display_raw

    mileage_cost_raw = total_mileage_display * (shift.mileage_rate or 0.0)

    total_operational_expenses = food_expenses_raw + other_expenses_raw + mileage_cost_raw

    tax_rate_decimal = 0.05
    tax_percentage = int(tax_rate_decimal * 100)
    tax_amount_raw = gross_income * tax_rate_decimal

    profit_raw = gross_income - total_operational_expenses - tax_amount_raw
    profit_per_hour_raw = (profit_raw / total_duration_hours) if total_duration_hours > 0.001 else 0.0

    status_text = text_manager.get(f"shift.status.{shift.status.value}", default=shift.status.value)

    return text_manager.get(
        "shift.active.message_template",
        date=start_local.strftime('%d.%m.%Y'),
        status=status_text,
        start_time=start_local.strftime('%H:%M МСК'),
        end_shift_time_label=text_manager.get("shift.completed.end_time_label", default="🏁 Конец смены:"),
        current_time=end_local.strftime('%H:%M МСК'),
        duration=format_duration(start_local, end_local),
        orders_completed=orders_completed,
        orders_per_hour=f"{orders_per_hour_raw:.2f}",
        mileage=f"{total_mileage_display:.1f}",
        mileage_cost=f"{mileage_cost_raw:.2f}",
        food_expenses=f"{food_expenses_raw:.2f}",
        other_expenses=f"{other_expenses_raw:.2f}",
        tax_percentage=tax_percentage,
        tax=f"{tax_amount_raw:.2f}",
        revenue_from_orders=f"{revenue_from_orders_raw:.2f}",
        revenue_from_time=f"{revenue_from_time_raw:.2f}",
        total_tips=f"{total_tips_display_raw:.2f}",
        profit=f"{profit_raw:.2f}",
        profit_per_hour=f"{profit_per_hour_raw:.2f}",
        history_entries=history_entries_str
    )