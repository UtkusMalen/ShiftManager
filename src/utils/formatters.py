import logging
from typing import Dict, Any, List
from zoneinfo import ZoneInfo
from datetime import datetime

from src.utils.text_manager import text_manager
from src.db.models import Shift, ShiftEventType, ShiftEvent

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo('Europe/Moscow')


def format_duration(start_time: datetime, end_time: datetime) -> str:
    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        logger.error(f"Invalid input types for format_duration: start={type(start_time)}, end={type(end_time)}")
        return "Ошибка времени"

    if start_time.tzinfo is None:
        start_time = MOSCOW_TZ.localize(start_time)
        logger.warning("format_duration received naive start_time, assuming Moscow TZ.")
    if end_time.tzinfo is None:
        end_time = MOSCOW_TZ.localize(end_time)
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
        start_local = MOSCOW_TZ.localize(shift.start_time)
        logger.warning(f"Shift {shift.id} start_time was timezone-naive. Assuming Moscow time.")
    else:
        start_local = shift.start_time.astimezone(MOSCOW_TZ)

    history_lines: List[str] = []
    if hasattr(shift, 'events') and shift.events:
        valid_events = [e for e in shift.events if e.timestamp is not None]
        sorted_events: List[ShiftEvent] = sorted(valid_events, key=lambda e: e.timestamp, reverse=True)

        for event in sorted_events:
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
                amount = details_data.get('amount', '?')
                category = details_data.get('category', 'Прочее')
                details_str = details_data.get("description", f"-{amount} руб. ({category})")
            elif event.event_type == ShiftEventType.ADD_MILEAGE:
                event_type_str = "🚗 +Пробег"
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

    total_mileage_display = shift.total_mileage if shift.total_mileage is not None else 0.0
    total_tips_display = shift.total_tips if shift.total_tips is not None else 0.0
    manual_expenses_display = shift.total_expenses if shift.total_expenses is not None else 0.0

    revenue_from_time = current_duration_hours * (shift.rate or 0.0)
    revenue_from_orders = orders_completed * (shift.order_rate or 0.0)
    gross_income = revenue_from_time + revenue_from_orders + total_tips_display

    mileage_cost = total_mileage_display * (shift.mileage_rate or 0.0)

    total_operational_expenses = manual_expenses_display + mileage_cost

    tax_rate_decimal = 0.05
    tax_percentage = int(tax_rate_decimal * 100)
    tax_amount = gross_income * tax_rate_decimal

    profit = gross_income - total_operational_expenses - tax_amount

    profit_per_hour = (profit / current_duration_hours) if current_duration_hours > 0.001 else 0.0

    status_text = text_manager.get(f"shift.status.{shift.status.value}", default=shift.status.value)

    return text_manager.get(
        "shift.active.message_template",
        date=start_local.strftime('%d.%m.%Y'),
        status=status_text,
        start_time=start_local.strftime('%H:%M МСК'),
        current_time=now_moscow.strftime('%H:%M МСК'),
        duration=format_duration(start_local, now_moscow),
        orders_completed=orders_completed,
        mileage=f"{total_mileage_display:.1f}",
        total_tips=f"{total_tips_display:.2f}",
        total_expenses=f"{total_operational_expenses:.2f}",
        revenue=f"{gross_income:.2f}",
        tax_percentage=tax_percentage,
        tax=f"{tax_amount:.2f}",
        profit=f"{profit:.2f}",
        profit_per_hour=f"{profit_per_hour:.2f}",
        history_entries=history_entries_str
    )


async def format_completed_shift_details_message(shift: Shift) -> str:
    if not shift.start_time or not shift.end_time:
        logger.error(f"Attempted to format completed shift {shift.id} without start or end time.")
        return "Ошибка: Неполные данные по смене."

    start_local = shift.start_time.astimezone(MOSCOW_TZ) if shift.start_time.tzinfo else MOSCOW_TZ.localize(
        shift.start_time)
    end_local = shift.end_time.astimezone(MOSCOW_TZ) if shift.end_time.tzinfo else MOSCOW_TZ.localize(shift.end_time)

    history_lines: List[str] = []
    if hasattr(shift, 'events') and shift.events:
        valid_events = [e for e in shift.events if e.timestamp is not None]
        sorted_events: List[ShiftEvent] = sorted(valid_events, key=lambda e: e.timestamp, reverse=True)

        for event in sorted_events:
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
                details_str = details_data.get(
                    "description", f"+{count} заказ(а)")
            elif event.event_type == ShiftEventType.ADD_TIPS:
                event_type_str = "💰 +Чаевые"
                amount = details_data.get('amount', '?')
                details_str = details_data.get(
                    "description", f"+{amount} руб.")
            elif event.event_type == ShiftEventType.ADD_EXPENSE:
                event_type_str = "💸 -Расход"
                amount = details_data.get('amount', '?')
                category = details_data.get(
                    'category', 'Прочее')
                details_str = details_data.get("description", f"-{amount} руб. ({category})")
            elif event.event_type == ShiftEventType.ADD_MILEAGE:
                event_type_str = "🚗 +Пробег"
                distance = details_data.get('distance_km','?')
                details_str = details_data.get(
                    "description", f"+{distance} км")
            elif event.event_type == ShiftEventType.UPDATE_INITIAL_DATA:
                event_type_str = "⚙️ Параметры"
                details_str = details_data.get("description", "Параметры обновлены")
            else:
                event_type_str = event.event_type.name
                details_str = str(
                    details_data) if details_data else "(нет данных)"
            line = f"<code>{event_time_str}</code> {event_type_str}: {details_str}"
            history_lines.append(line)

    history_entries_str = "\n".join(history_lines) if history_lines else text_manager.get("shift.active.default_history", default="Нет событий")

    orders_completed = shift.orders_count if shift.orders_count is not None else 0

    total_duration_seconds = (end_local - start_local).total_seconds() if end_local > start_local else 0
    total_duration_hours = total_duration_seconds / 3600.0

    total_mileage_display = shift.total_mileage if shift.total_mileage is not None else 0.0
    total_tips_display = shift.total_tips if shift.total_tips is not None else 0.0
    manual_expenses_display = shift.total_expenses if shift.total_expenses is not None else 0.0

    revenue_from_time = total_duration_hours * (shift.rate or 0.0)
    revenue_from_orders = orders_completed * (shift.order_rate or 0.0)
    gross_income = revenue_from_time + revenue_from_orders + total_tips_display

    mileage_cost = total_mileage_display * (shift.mileage_rate or 0.0)

    total_operational_expenses = manual_expenses_display + mileage_cost

    tax_rate_decimal = 0.05
    tax_percentage = int(tax_rate_decimal * 100)
    tax_amount = gross_income * tax_rate_decimal

    profit = gross_income - total_operational_expenses - tax_amount

    profit_per_hour = (profit / total_duration_hours) if total_duration_hours > 0.001 else 0.0

    status_text = text_manager.get(f"shift.status.{shift.status.value}", default=shift.status.value)

    return text_manager.get(
        "shift.active.message_template",
        date=start_local.strftime('%d.%m.%Y'),
        status=status_text,
        start_time=start_local.strftime('%H:%M МСК'),
        current_time=end_local.strftime('%H:%M МСК'),
        duration=format_duration(start_local, end_local),
        orders_completed=orders_completed,
        mileage=f"{total_mileage_display:.1f}",
        total_tips=f"{total_tips_display:.2f}",
        total_expenses=f"{total_operational_expenses:.2f}",
        revenue=f"{gross_income:.2f}",
        tax_percentage=tax_percentage,
        tax=f"{tax_amount:.2f}",
        profit=f"{profit:.2f}",
        profit_per_hour=f"{profit_per_hour:.2f}",
        history_entries=history_entries_str
    )