import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.db.models import Shift, ShiftStatus
from src.keyboards.inline import active_shift_keyboard
from src.states.menu import MenuStates
from src.utils.formatters import get_active_shift_message_text
from src.handlers.user_handlers import get_or_create_user 

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "shift:start", MenuStates.in_main_menu)
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
    ).order_by(Shift.start_time.desc())
    result = await session.execute(existing_shift_stmt)
    existing_shift = result.scalar_one_or_none()

    shift_to_display: Shift
    message_text: str
    transition_message: str

    if existing_shift:
        logger.warning(f"User {user.id} already has an active/forming shift (ID: {existing_shift.id}). Resuming it.")
        shift_to_display = existing_shift
        await state.set_state(MenuStates.in_shift_active)

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
        session.add(new_shift)
        await session.flush() 
        shift_to_display = new_shift
        logger.info(f"New shift created with ID: {shift_to_display.id} (pending commit)")
        await state.set_state(MenuStates.in_shift_active)
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
