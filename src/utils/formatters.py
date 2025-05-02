import logging
from zoneinfo import ZoneInfo
from datetime import datetime

from src.utils.text_manager import text_manager
from src.db.models import Shift

logger = logging.getLogger(__name__)

def format_duration(start_time: datetime, end_time: datetime) -> str:
    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        logger.error(f"Invalid input types for format_duration: start={type(start_time)}, end={type(end_time)}")
        return "Ошибка времени" 

    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())

    if total_seconds < 0:
        logger.warning(f"Calculated negative duration: start={start_time}, end={end_time}")
        total_seconds = 0 

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours} час(a/ов), {minutes} минут"

async def get_active_shift_message_text(shift: Shift) -> str:
    moscow_tz = ZoneInfo('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz) 

    if shift.start_time.tzinfo is None:
        start_local = moscow_tz.localize(shift.start_time) 
        logger.warning(f"Shift start_time was timezone-naive. Assuming Moscow time.")
    else:
        start_local = shift.start_time.astimezone(moscow_tz)

    orders_completed = text_manager.get("shift.active.default_value", default="0")
    mileage = text_manager.get("shift.active.default_value", default="0")
    revenue = text_manager.get("shift.active.default_value", default="0")
    tax = text_manager.get("shift.active.default_value", default="0")
    profit = text_manager.get("shift.active.default_value", default="0")
    profit_per_hour = text_manager.get("shift.active.default_value", default="0")
    history_entries = text_manager.get("shift.active.default_history", default="Пока пусто")

    status_text = text_manager.get(f"shift.status.{shift.status.value}", default=shift.status.value)

    return text_manager.get(
        "shift.active.message_template",
        date=start_local.strftime('%d.%m.%Y'),
        status=status_text,
        start_time=start_local.strftime('%H:%M МСК'), 
        current_time=now_moscow.strftime('%H:%M МСК'), 
        duration=format_duration(start_local, now_moscow),
        orders_completed=orders_completed,
        mileage=mileage,
        revenue=revenue,
        tax=tax,
        profit=profit,
        profit_per_hour=profit_per_hour,
        history_entries=history_entries
    )
