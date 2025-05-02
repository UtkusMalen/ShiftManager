import logging

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime, timezone
from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import now

from src.keyboards.inline import main_menu_keyboard, active_shift_keyboard
from src.utils.text_manager import text_manager
from src.states.menu import MenuStates
from src.db.models import User, ShiftStatus, Shift

logger = logging.getLogger(__name__)
router = Router()

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        logging.info(f"User with telegram_id={telegram_id} and username={username} not found. Creating new user...")
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.flush()
        await session.commit()
        result = await session.execute(stmt)
        user = result.scalar_one()
        logger.info(f"New user created: {user}")
    elif user.username != username:
        logger.info(f"Updating username for user with telegram_id={telegram_id} from {user.username} to {username}")
        user.username = username
        await session.commit()

    return user

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, session: AsyncSession):
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    # Check if user has an active/forming shift
    # TODO: Add logic here to potentially resume an existing shift instead of showing main menu directly
    await message.answer(
        f"{text_manager.get('menu.main.message')}",
        reply_markup=main_menu_keyboard()
    )

    await state.set_state(MenuStates.in_main_menu)

def format_duration(start_time: datetime, end_time: datetime) -> str:
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours} час(a/ов), {minutes} минут"

async def get_active_shift_message_text(shift: Shift) -> str:
    """Generates the text for the active shift message."""
    try:
        # Define the target timezone reliably
        target_tz = ZoneInfo("Europe/Moscow")
    except ZoneInfoNotFoundError:
        logger.error("Timezone 'Europe/Moscow' not found. Falling back to UTC.")
        target_tz = timezone.utc # Fallback to UTC

    start_utc = shift.start_time
    start_local = start_utc.astimezone(target_tz)

    # Get the current time in the target timezone
    now_local = datetime.now(target_tz)

    # TODO: Fetch actual shift data (orders, mileage, etc.) when implemented
    orders_completed = text_manager.get("shift.active.default_value", default="0")
    mileage = text_manager.get("shift.active.default_value", default="0")
    revenue = text_manager.get("shift.active.default_value", default="0")
    tax = text_manager.get("shift.active.default_value", default="0")
    profit = text_manager.get("shift.active.default_value", default="0")
    profit_per_hour = text_manager.get("shift.active.default_value", default="0")
    history_entries = text_manager.get("shift.active.default_history", default="Пока пусто")

    return text_manager.get(
        "shift.active.message_template",
        date=start_local.strftime('%d.%m.%Y'),
        status=text_manager.get(f"shift.status.{shift.status.value}", default=shift.status.value),
        start_time=start_local.strftime('%H:%M'),
        current_time=now.strftime('%H:%M'),
        duration=format_duration(start_local, now),
        orders_completed=orders_completed,
        mileage=mileage,
        revenue=revenue,
        tax=tax,
        profit=profit,
        profit_per_hour=profit_per_hour,
        history_entries=history_entries
    )

@router.callback_query(F.data == "shift:start", MenuStates.in_main_menu)
async def handle_start_shift(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    user = await get_or_create_user(
        session,
        call.from_user.id,
        call.from_user.username
    )
    logger.info(f"User {user.id} trying to start a shift.")

    existing_shift_stmt = select(Shift).where(
        Shift.user_id == user.user_id, # Use user.user_id (Telegram ID)
        Shift.status.in_([ShiftStatus.FORMING, ShiftStatus.ACTIVE])
    ).order_by(Shift.start_time.desc())
    result = await session.execute(existing_shift_stmt)
    active_shift = result.scalar_one_or_none()

    if active_shift:
        logger.warning(f"User {user.id} already has an active/forming shift (ID: {active_shift.id}). Resuming it.")
        # TODO: Add logic to maybe ask the user if they want to resume or discard?
        # For now, just transition to the existing active shift view
        shift = active_shift
        await state.set_state(MenuStates.in_shift_active)
        if shift.status == ShiftStatus.FORMING:
            shift.status = ShiftStatus.ACTIVE
            await session.commit()
        message_text = await get_active_shift_message_text(shift)
        try:
            await call.message.edit_text(message_text, reply_markup=active_shift_keyboard(), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to edit active shift message: {e}", exc_info=True)
            await call.message.answer(message_text, reply_markup=active_shift_keyboard(), parse_mode="HTML")
        await call.answer("Смена уже начата")
        return

    logger.info(f"Creating new shift for user {user.id}")
    new_shift = Shift(user_id=user.user_id, status=ShiftStatus.FORMING) # Use user.user_id (Telegram ID)
    session.add(new_shift)
    await session.flush()
    await session.commit()
    shift = new_shift
    logger.info(f"New shift created with ID: {new_shift.id}")

    await state.set_state(MenuStates.in_shift_active)
    message_text = await get_active_shift_message_text(new_shift)
    try:
        await call.message.edit_text(message_text, reply_markup=active_shift_keyboard(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to edit active shift message: {e}", exc_info=True)
        await call.message.answer(message_text, reply_markup=active_shift_keyboard(), parse_mode="HTML")
    await call.answer()
