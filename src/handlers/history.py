import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Shift, ShiftStatus
from src.keyboards.history import history_selection_keyboard, shift_details_keyboard
from src.states import MenuStates
from src.utils.formatters import format_completed_shift_details_message
from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)
router = Router()

HISTORY_PAGE_SIZE = 5

@router.callback_query(F.data == "main_menu:history")
async def handle_work_history_menu(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    user_id = call.from_user.id
    logger.info(f"User {user_id} opened history menu.")

    stmt = select(Shift).where(
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.COMPLETED
    ).options(
        selectinload(Shift.events),
        selectinload(Shift.user)
    ).order_by(Shift.end_time.desc()).limit(HISTORY_PAGE_SIZE)

    result = await session.execute(stmt)
    shifts = result.scalars().all()

    if not shifts:
        message_text = tm.get("history.no_shifts_found")
        reply_markup = history_selection_keyboard([])
    else:
        message_text = tm.get("history.title")
        reply_markup = history_selection_keyboard(shifts)

    if call.message:
        await call.message.edit_text(text=message_text, reply_markup=reply_markup)

    await state.set_state(MenuStates.in_history)
    await call.answer()


@router.callback_query(F.data.startswith("history:shift:"), MenuStates.in_history)
async def handle_select_shift_from_history(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        shift_id = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.error(f"Invalid shift_id in callback data: {call.data}")
        await call.answer("Ошибка: Неверный ID смены.", show_alert=True)
        return

    user_id = call.from_user.id
    logger.info(f"User {user_id} selected shift {shift_id} from history.")

    stmt = select(Shift).where(
        Shift.id == shift_id,
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.COMPLETED
    ).options(selectinload(Shift.events), selectinload(Shift.user))

    shift = await session.scalar(stmt)

    if not shift:
        logger.warning(f"Shift {shift_id} not found or not accessible for user {user_id}.")
        await call.answer("Ошибка: Смена не найдена или недоступна.", show_alert=True)
        await handle_work_history_menu(call, state, session)
        return

    if not shift.end_time:
        logger.error(f"Shift {shift_id} is COMPLETED but has no end_time.")
        await call.answer("Ошибка: Данные смены неполные.", show_alert=True)
        await handle_work_history_menu(call, state, session)
        return

    message_text = await format_completed_shift_details_message(shift)
    reply_markup = shift_details_keyboard()

    if call.message:
        await call.message.edit_text(text=message_text, reply_markup=reply_markup, parse_mode="HTML")

    await call.answer()