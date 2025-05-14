import logging
from typing import Union
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Shift, ShiftStatus
from src.keyboards.history import history_selection_keyboard, shift_details_keyboard, confirm_delete_shift_keyboard
from src.states import MenuStates
from src.utils.formatters import format_completed_shift_details_message
from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)
router = Router()

HISTORY_PAGE_SIZE = 6
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

async def show_history_page(call_or_message: Union[CallbackQuery, Message],state: FSMContext,session: AsyncSession,page: int = 1):
    user_id = call_or_message.from_user.id
    logger.info(f"User {user_id} requested history page {page}.")

    await state.update_data(history_current_page=page)

    count_stmt = select(func.count(Shift.id)).where(
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.COMPLETED
    )
    total_shifts_count_result = await session.execute(count_stmt)
    total_shifts_count = total_shifts_count_result.scalar_one_or_none()
    if total_shifts_count is None:
        total_shifts_count = 0

    total_pages = (total_shifts_count + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE
    if total_pages == 0:
        total_pages = 1

    page = max(1, min(page, total_pages))
    await state.update_data(history_current_page=page)
    offset = (page - 1) * HISTORY_PAGE_SIZE

    stmt = select(Shift).where(
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.COMPLETED
    ).options(
        selectinload(Shift.events),
        selectinload(Shift.user)
    ).order_by(Shift.end_time.desc()).offset(offset).limit(HISTORY_PAGE_SIZE)

    result = await session.execute(stmt)
    shifts = result.scalars().all()

    message_text: str
    if not shifts and page == 1:
        message_text = tm.get("history.no_shifts_found")
    elif not shifts and page > 1:
        if total_shifts_count > 0 and page > 1:
            page = max(1, page - 1)
            await show_history_page(call_or_message, state, session, page=page)
            return
        else:
            message_text = tm.get("history.no_shifts_found")
    else:
        message_text = tm.get("history.title")

    reply_markup = history_selection_keyboard(shifts, page, total_pages)

    target_message = None
    if isinstance(call_or_message, CallbackQuery):
        target_message = call_or_message.message
        await call_or_message.answer()
    elif isinstance(call_or_message, Message):
        target_message = call_or_message

    if target_message:
        if isinstance(call_or_message, CallbackQuery):
             if target_message.text != message_text or target_message.reply_markup != reply_markup:
                try:
                    await target_message.edit_text(text=message_text, reply_markup=reply_markup)
                except Exception as e:
                    logger.error(f"Error editing history message: {e}. Sending new one.")
                    await call_or_message.bot.send_message(target_message.chat.id, text=message_text, reply_markup=reply_markup)
        else:
            await target_message.answer(text=message_text, reply_markup=reply_markup)

    await state.set_state(MenuStates.in_history)


@router.callback_query(F.data == "main_menu:history", MenuStates.in_main_menu)
async def handle_work_history_menu_entry(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    await show_history_page(call, state, session, page=1)


@router.callback_query(F.data.startswith("history:page:"), MenuStates.in_history)
async def handle_history_page_navigation(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    data_parts = call.data.split(":")
    if len(data_parts) < 3 or data_parts[2] == "noop":
        await call.answer()
        return
    try:
        page = int(data_parts[2])
        await show_history_page(call, state, session, page=page)
    except ValueError:
        logger.error(f"Invalid page number in callback data: {call.data}")
        await call.answer("Ошибка навигации.", show_alert=True)


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
        current_data = await state.get_data()
        last_page = current_data.get("history_last_page", 1)
        await show_history_page(call, state, session, page=last_page)
        return

    if not shift.end_time:
        logger.error(f"Shift {shift_id} is COMPLETED but has no end_time.")
        await call.answer("Ошибка: Данные смены неполные.", show_alert=True)
        current_data = await state.get_data()
        last_page = current_data.get("history_last_page", 1)
        await show_history_page(call, state, session, page=last_page)
        return

    message_text = await format_completed_shift_details_message(shift)
    reply_markup = shift_details_keyboard(shift_id=shift.id)

    if call.message:
        await call.message.edit_text(text=message_text, reply_markup=reply_markup, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "main_menu:history", MenuStates.in_history)
async def back_to_history_list(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    current_data = await state.get_data()
    page_to_return = current_data.get("history_last_page_for_details", 1)
    await show_history_page(call, state, session, page=page_to_return)

@router.callback_query(F.data.startswith("history:delete_shift_prompt:"), MenuStates.in_history)
async def prompt_delete_shift_confirmation(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        shift_id = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.error(f"Invalid shift_id in callback data: {call.data}")
        await call.answer("Ошибка: Неверный ID смены.", show_alert=True)
        return

    stmt = select(Shift).where(
        Shift.id == shift_id, Shift.user_id == call.from_user.id
    )
    shift_to_delete = await session.scalar(stmt)

    if not shift_to_delete or not shift_to_delete.start_time:
        await call.answer(tm.get("history.shift_not_found_for_deletion"), show_alert=True)
        return

    shift_date_time_str = shift_to_delete.start_time.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
    confirmation_text = tm.get("history.delete_confirmation_prompt", shift_date_time=shift_date_time_str)

    await state.update_data(shift_id_to_delete=shift_id)
    await call.message.edit_text(
        text=confirmation_text,
        reply_markup=confirm_delete_shift_keyboard(shift_id)
    )
    await state.set_state(MenuStates.confirming_shift_deletion)
    await call.answer()

@router.callback_query(F.data.startswith("history:delete_shift_confirm:"), MenuStates.confirming_shift_deletion)
async def confirm_delete_shift(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        shift_id_from_callback = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.error(f"Invalid shift_id in delete confirm callback: {call.data}")
        await call.answer("Ошибка при подтверждении удаления.", show_alert=True)
        current_data = await state.get_data()
        page = current_data.get("history_current_page", 1)
        await show_history_page(call, state, session, page=page)
        return

    data = await state.get_data()
    shift_id_from_state = data.get("shift_id_to_delete")

    if shift_id_from_callback != shift_id_from_state:
        logger.error(f"Shift ID mismatch: callback {shift_id_from_callback}, state {shift_id_from_state}")
        await call.answer("Ошибка: несоответствие ID смены для удаления.", show_alert=True)
        page = data.get("history_current_page", 1)
        await show_history_page(call, state, session, page=page)
        return

    shift_to_delete = await session.get(Shift, shift_id_from_state)

    if not shift_to_delete or shift_to_delete.user_id != call.from_user.id:
        await call.answer(tm.get("history.shift_not_found_for_deletion"), show_alert=True)
    else:
        await session.delete(shift_to_delete)
        await session.commit()
        logger.info(f"User {call.from_user.id} deleted shift {shift_id_from_state}.")
        await call.answer(tm.get("history.shift_deleted_successfully"), show_alert=False)

    page = data.get("history_current_page", 1)
    await show_history_page(call, state, session, page=page)
    await state.set_state(MenuStates.in_history)

@router.callback_query(F.data.startswith("history:delete_shift_cancel:"), MenuStates.confirming_shift_deletion)
async def cancel_delete_shift(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        shift_id = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.error(f"Invalid shift_id in delete cancel callback: {call.data}")
        await call.answer("Ошибка при отмене удаления.", show_alert=True)
        current_data = await state.get_data()
        page = current_data.get("history_current_page", 1)
        await show_history_page(call, state, session, page=page)
        return

    await call.answer(tm.get("history.shift_deletion_cancelled"))
    await state.set_state(MenuStates.in_history)

    stmt = select(Shift).where(
        Shift.id == shift_id,
        Shift.user_id == call.from_user.id,
        Shift.status == ShiftStatus.COMPLETED
    ).options(
        selectinload(Shift.events), selectinload(Shift.user)
    )
    shift = await session.scalar(stmt)

    if not shift:
        logger.warning(f"Shift {shift_id} not found after cancel delete for user {call.from_user.id}.")
        await call.answer("Ошибка: Смена не найдена.", show_alert=True)
        current_data = await state.get_data()
        last_page = current_data.get("history_current_page", 1)
        await show_history_page(call, state, session, page=last_page)
        return

    message_text = await format_completed_shift_details_message(shift)
    reply_markup = shift_details_keyboard(shift_id=shift.id)
    if call.message:
        await call.message.edit_text(text=message_text, reply_markup=reply_markup, parse_mode="HTML")
