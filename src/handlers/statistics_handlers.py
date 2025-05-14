import logging
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Shift, ShiftStatus
from src.keyboards.statistics_keyboards import get_period_selection_keyboard, back_to_period_selection_keyboard
from src.states import MenuStates
from src.utils.statistics_generator import generate_statistics_image
from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)
router = Router()
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

async def get_shifts_for_period(session: AsyncSession, user_id: int, start_date: datetime, end_date: datetime) -> list[Shift]:
    stmt = select(Shift).where(
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.COMPLETED,
        Shift.end_time >= start_date,
        Shift.end_time <= end_date
    ).options(
        selectinload(Shift.events)
    ).order_by(Shift.end_time.desc())
    result = await session.execute(stmt)
    return result.scalars().all()

@router.callback_query(F.data == "statistics:select_period")
async def cmd_select_statistics_period(call: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.in_statistics)
    try:
        await call.message.edit_text(
            text=tm.get("statistics.select_period", "Выберите период:"),
            reply_markup=get_period_selection_keyboard()
        )
    except Exception:
        await call.message.delete()
        await call.bot.send_message(
            chat_id=call.from_user.id,
            text=tm.get("statistics.select_period", "Выберите период:"),
            reply_markup=get_period_selection_keyboard()
        )

    await call.answer()

async def process_period_selection(call_or_msg: CallbackQuery | Message, session: AsyncSession, period_type: str, period_name_for_img: str):
    user_id = call_or_msg.from_user.id
    now_moscow = datetime.now(MOSCOW_TZ)
    start_date, end_date = None, None

    if period_type == "current_week":
        start_of_week = now_moscow - timedelta(days=now_moscow.weekday())
        start_date = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=6)
        end_date = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period_type == "last_week":
        start_of_week = now_moscow - timedelta(days=now_moscow.weekday() + 7)
        start_date = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=6)
        end_date = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period_type == "current_month":
        start_date = now_moscow.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = (start_date + relativedelta(months=1)) - timedelta(microseconds=1)
    elif period_type == "last_month":
        first_day_current_month = now_moscow.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = first_day_current_month - timedelta(microseconds=1)
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period_type == "all_time":
        start_date = datetime(2000, 1, 1, tzinfo=MOSCOW_TZ)
        end_date = now_moscow.replace(hour=23, minute=59, second=59, microsecond=999999)

    if not start_date or not end_date:
        await call_or_msg.answer(tm.get("statistics.error_generating"), show_alert=True)
        return

    bot_instance: Bot = call_or_msg.bot
    chat_id = call_or_msg.chat.id if isinstance(call_or_msg, Message) else call_or_msg.message.chat.id
    source_message_id = call_or_msg.message.message_id if isinstance(call_or_msg, CallbackQuery) else call_or_msg.message_id

    generating_msg = None
    try:
        if source_message_id:
            await bot_instance.delete_message(chat_id=chat_id, message_id=source_message_id)
        generating_msg = await bot_instance.send_message(
            chat_id=chat_id,
            text=tm.get("statistics.generating")
        )
    except TelegramBadRequest as e_del_send:
        logger.warning(f"Could not delete old or send 'generating stats' message: {e_del_send}")
    except Exception as e_gen_msg:
        logger.error(f"General error sending 'generating stats' message: {e_gen_msg}")

    shifts = await get_shifts_for_period(session, user_id, start_date, end_date)

    if generating_msg:
        try:
            await bot_instance.delete_message(chat_id=chat_id, message_id=generating_msg.message_id)
        except TelegramBadRequest as e:
            logger.warning(f"Could not delete 'generating stats' message: {e}")

    if not shifts:
        await bot_instance.send_message(
            chat_id=chat_id,
            text=tm.get("statistics.no_data"),
            reply_markup=back_to_period_selection_keyboard()
        )
        if isinstance(call_or_msg, CallbackQuery):
            await call_or_msg.answer()
            return

    generated_image_data: BytesIO | None = await generate_statistics_image(shifts, period_name_for_img)

    if generated_image_data:
        await bot_instance.send_photo(
            chat_id=chat_id,
            photo=BufferedInputFile(generated_image_data.getvalue(), filename="statistics.png"),
            caption=tm.get("statistics.title"),
            reply_markup=back_to_period_selection_keyboard()
        )
    else:
        await bot_instance.send_message(
            chat_id=chat_id,
            text=tm.get("statistics.error_generating"),
            reply_markup=back_to_period_selection_keyboard()
        )

    if isinstance(call_or_msg, CallbackQuery): await call_or_msg.answer()

@router.callback_query(F.data.startswith("stats_period:"), MenuStates.in_statistics)
async def handle_period_selection(call: CallbackQuery, session: AsyncSession):
    period_type = call.data.split(":")[-1]
    period_name = ""
    if period_type == "current_week":
        period_name = tm.get("statistics.prompts.current_week")
    elif period_type == "last_week":
        period_name = tm.get("statistics.prompts.last_week")
    elif period_type == "current_month":
        period_name = tm.get("statistics.prompts.current_month")
    elif period_type == "last_month":
        period_name = tm.get("statistics.prompts.last_month")
    elif period_type == "all_time":
        period_name = tm.get("statistics.prompts.all_time")

    await process_period_selection(call, session, period_type, period_name)
