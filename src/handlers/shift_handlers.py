import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.db.models import Shift, ShiftStatus, ShiftEvent, ShiftEventType
from src.keyboards.shift import active_shift_keyboard, mileage_keyboard
from src.keyboards.main_menu import main_menu_keyboard
from src.states.shift import ShiftStates
from src.states.menu import MenuStates
from src.utils.formatters import get_active_shift_message_text
from src.handlers.user_handlers import get_or_create_user
from src.utils.text_manager import text_manager

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "shift:start")
async def handle_start_shift(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    user = await get_or_create_user( 
        session,
        call.from_user.id,
        call.from_user.username
    )
    logger.info(f"User {user.id} attempting to start or resume a shift via callback.")

    existing_shift_stmt = select(Shift).where(
        Shift.user_id == user.user_id,
        Shift.status.in_([ShiftStatus.FORMING, ShiftStatus.ACTIVE])
    ).options(
        selectinload(Shift.user),
        selectinload(Shift.events)
    ).order_by(Shift.start_time.desc())
    result = await session.execute(existing_shift_stmt)
    existing_shift = result.scalar_one_or_none()

    shift_to_display: Shift
    message_text: str
    transition_message: str

    if existing_shift:
        logger.warning(f"User {user.id} already has an active/forming shift (ID: {existing_shift.id}). Resuming it.")
        shift_to_display = existing_shift
        await state.set_state(ShiftStates.in_shift_active)

        if shift_to_display.status == ShiftStatus.FORMING:
            logger.info(f"Shift {shift_to_display.id} was FORMING, setting to ACTIVE.")
            shift_to_display.status = ShiftStatus.ACTIVE
            await session.flush() 
            transition_message = "Активная смена возобновлена."
        else:
            transition_message = "У вас уже есть активная смена"

    else:
        logger.info(f"Creating new shift for user {user.id}")
        new_shift = Shift(user_id=user.user_id, status=ShiftStatus.ACTIVE)
        start_event = ShiftEvent(
            event_type=ShiftEventType.START_SHIFT,
            details={"message": "Смена начата"}
        )
        start_event.shift = new_shift
        session.add(new_shift)
        session.add(start_event)
        shift_to_display = new_shift
        await session.flush()
        logger.info(f"New shift created with ID: {new_shift.id} (pending commit)")
        await state.set_state(ShiftStates.in_shift_active)
        transition_message = "Новая смена начата!"

    message_text = await get_active_shift_message_text(shift_to_display)

    try:
        await call.message.edit_text(
            message_text,
            reply_markup=active_shift_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e: 
        logger.error(f"Failed to edit active shift message for shift {shift_to_display.id}: {e}", exc_info=True)
        pass 

    await call.answer(transition_message)

@router.callback_query(F.data == "shift:end", ShiftStates.in_shift_active)
async def handle_end_shift(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE).options(selectinload(Shift.events))
    shift = await session.scalar(stmt)
    shift.status = ShiftStatus.COMPLETED

    end_event = ShiftEvent(
        event_type=ShiftEventType.COMPLETE_SHIFT,
        details={"message": "Смена завершена"}
    )
    moscow_tz = ZoneInfo('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz)
    shift.end_time = now_moscow
    end_event.shift = shift
    session.add(end_event)
    session.add(shift)
    await session.commit()

    await call.message.edit_text(
        text=text_manager.get("menu.main.message"),
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MenuStates.in_main_menu)
    await call.answer("Смена завершена")

@router.callback_query(F.data == "shift:add_mileage", ShiftStates.in_shift_active)
async def handle_mileage(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        text=text_manager.get("shift.mileage"),
        reply_markup=mileage_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(ShiftStates.in_shift_mileage)



