import logging
from zoneinfo import ZoneInfo
from datetime import datetime

from src.utils.text_manager import text_manager
from src.db.models import Shift, ShiftEventType

logger = logging.getLogger(__name__)

def format_duration(start_time: datetime, end_time: datetime) -> str:
    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        logger.error(f"Invalid input types for format_duration: start={type(start_time)}, end={type(end_time)}")
        return "Ошибка времени"

    moscow_tz = ZoneInfo('Europe/Moscow')
    if start_time.tzinfo is None:
        start_time = moscow_tz.localize(start_time)
        logger.warning("format_duration received naive start_time, assuming Moscow TZ.")
    if end_time.tzinfo is None:
        end_time = moscow_tz.localize(end_time)
        logger.warning("format_duration received naive end_time, assuming Moscow TZ.")

    start_time = start_time.astimezone(moscow_tz)
    end_time = end_time.astimezone(moscow_tz)

    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())

    if total_seconds < 0:
        logger.warning(f"Calculated negative duration: start={start_time}, end={end_time}")
        total_seconds = 0

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    h_str = f"{hours} час" + ("" if hours == 1 else ("а" if 1 < hours < 5 else "ов"))
    m_str = f"{minutes} минут" + ("а" if minutes == 1 else ("ы" if 1 < minutes < 5 else ""))
    return f"{h_str}, {m_str}"


async def get_active_shift_message_text(shift: Shift) -> str:
    moscow_tz = ZoneInfo('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz)

    if shift.start_time.tzinfo is None:
        start_local = moscow_tz.localize(shift.start_time)
        logger.warning(f"Shift {shift.id} start_time was timezone-naive. Assuming Moscow time.")
    else:
        start_local = shift.start_time.astimezone(moscow_tz)

    history_lines = []
    if shift.events:
        sorted_events = sorted(shift.events, key=lambda e: e.timestamp, reverse=True)

        for event in sorted_events:
            event_time_str = event.timestamp.astimezone(moscow_tz).strftime('%H:%M')

            details_data = event.details if isinstance(event.details, dict) else {}

            if event.event_type == ShiftEventType.START_SHIFT:
                event_type_str = "Старт"
                details_str = details_data.get("message", "Смена начата")
            elif event.event_type == ShiftEventType.COMPLETE_SHIFT:
                event_type_str = "Финиш"
                details_str = details_data.get("message", "Смена завершена")
            elif event.event_type == ShiftEventType.ADD_ORDER:
                event_type_str = "+Заказ"
                details_str = details_data.get("description", f"+{details_data.get('count', '?')} заказ(а)")
            elif event.event_type == ShiftEventType.ADD_TIPS:
                event_type_str = "+Чаевые"
                details_str = details_data.get("description", f"+{details_data.get('amount', '?')} {details_data.get('currency', '')}")
            elif event.event_type == ShiftEventType.ADD_EXPENSE:
                event_type_str = "-Расход"
                details_str = details_data.get("description", f"{details_data.get('category', 'Прочее')} {details_data.get('amount', '?')}")
            elif event.event_type == ShiftEventType.ADD_MILEAGE:
                event_type_str = "+Пробег"
                details_str = details_data.get("description", f"+{details_data.get('distance_km', '?')} км")
            elif event.event_type == ShiftEventType.UPDATE_INITIAL_DATA:
                 event_type_str = "Параметры"
                 details_str = details_data.get("description", "Параметры обновлены")
            else:
                event_type_str = event.event_type.name
                details_str = str(details_data) if details_data else "(нет данных)"

            line = f"{event_time_str} {event_type_str}: {details_str}"
            history_lines.append(line)

    history_entries_str = "\n".join(history_lines[:5])
    if not history_entries_str:
        history_entries_str = text_manager.get("shift.active.default_history", default="Пока пусто")

    orders_completed = shift.orders_count if shift.orders_count is not None else 0
    current_duration_hours = (now_moscow - start_local).total_seconds() / 3600.0 if now_moscow > start_local else 0

    total_mileage_display = shift.total_mileage
    revenue = (current_duration_hours * shift.rate) + (orders_completed * shift.order_rate) + (total_mileage_display * shift.mileage_rate)
    total_expenses_display = shift.total_expenses
    tax_rate = 0.05
    tax = revenue * tax_rate
    profit = revenue - total_expenses_display - tax
    profit_per_hour = (profit / current_duration_hours) if current_duration_hours > 0 else 0

    status_text = text_manager.get(f"shift.status.{shift.status.value}", default=shift.status.value)

    revenue_f = f"{revenue:.2f}"
    tax_f = f"{tax:.2f}"
    profit_f = f"{profit:.2f}"
    profit_per_hour_f = f"{profit_per_hour:.2f}"
    mileage_f = f"{total_mileage_display:.1f}"


    return text_manager.get(
        "shift.active.message_template",
        date=start_local.strftime('%d.%m.%Y'),
        status=status_text,
        start_time=start_local.strftime('%H:%M МСК'),
        current_time=now_moscow.strftime('%H:%M МСК'),
        duration=format_duration(start_local, now_moscow),
        orders_completed=orders_completed,
        mileage=mileage_f,
        revenue=revenue_f,
        tax=tax_f,
        profit=profit_f,
        profit_per_hour=profit_per_hour_f,
        history_entries=history_entries_str
    )