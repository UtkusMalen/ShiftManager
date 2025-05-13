import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Union, Dict, Any, Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.db.models import Shift, ShiftStatus, ShiftEvent, ShiftEventType
from src.keyboards.shift import (
    active_shift_keyboard, mileage_keyboard, tips_keyboard,
    cancel_action_keyboard, expenses_category_keyboard,
    get_start_time_options_keyboard, get_cancel_start_time_keyboard, get_cancel_end_time_keyboard, get_end_time_options_keyboard
)
from src.keyboards.main_menu import main_menu_keyboard
from src.states.shift import ShiftStates
from src.states.menu import MenuStates
from src.utils.formatters import get_active_shift_message_text
from src.handlers.user_handlers import get_or_create_user
from src.utils.text_manager import text_manager

logger = logging.getLogger(__name__)
router = Router()

async def _update_shift_value_and_event(
        session: AsyncSession,
        user_id: int,
        value_to_add: float,
        shift_field_name: str,
        event_type: ShiftEventType,
        event_details: Dict[str, Any]
) -> Optional[Shift]:
    stmt = select(Shift).where(
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.ACTIVE
    ).options(selectinload(Shift.events))
    shift = await session.scalar(stmt)

    if not shift:
        logger.error(f"No active shift found for user {user_id} during value update.")
        return None

    current_value = getattr(shift, shift_field_name, 0.0)
    setattr(shift, shift_field_name, current_value + value_to_add)

    new_event = ShiftEvent(
        event_type=event_type,
        details=event_details,
        timestamp=datetime.now(ZoneInfo('Europe/Moscow'))
    )
    new_event.shift = shift

    session.add(shift)
    session.add(new_event)
    return shift


async def _return_to_active_shift_view(
        target: Union[Message, CallbackQuery],
        state: FSMContext,
        shift: Shift,
        answer_text: Optional[str] = None
):
    data = await state.get_data()
    original_message_id = data.get("active_shift_message_id")
    bot_instance = target.bot

    text_content = await get_active_shift_message_text(shift)
    reply_markup_content = active_shift_keyboard()

    chat_id_to_use = target.chat.id if isinstance(target, Message) else target.message.chat.id

    if isinstance(target, Message):
        await target.delete()

    if original_message_id:
        try:
            await bot_instance.edit_message_text(
                chat_id=chat_id_to_use,
                message_id=original_message_id,
                text=text_content,
                reply_markup=reply_markup_content,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(
                f"Failed to edit original active shift message (ID: {original_message_id}): {e}. Sending new one.")
            if isinstance(target, CallbackQuery) and target.message:
                await target.message.delete()
            new_msg = await bot_instance.send_message(chat_id_to_use, text=text_content,
                                                      reply_markup=reply_markup_content, parse_mode='HTML')
            await state.update_data(active_shift_message_id=new_msg.message_id)
    else:
        logger.info("No original_message_id found in state, sending new active shift message.")
        if isinstance(target, CallbackQuery) and target.message:
            await target.message.delete()
        new_msg = await bot_instance.send_message(chat_id_to_use, text=text_content, reply_markup=reply_markup_content,
                                                  parse_mode='HTML')
        await state.update_data(active_shift_message_id=new_msg.message_id)

    await state.set_state(ShiftStates.in_shift_active)
    if answer_text:
        if isinstance(target, CallbackQuery):
            await target.answer(answer_text)


@router.callback_query(F.data == "shift:start")
async def handle_start_shift_logic(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    user_db = await get_or_create_user(
        session,
        call.from_user.id,
        call.from_user.username
    )
    logger.info(f"User {user_db.user_id} (DB ID: {user_db.id}) clicked 'Start Shift'.")

    existing_shift_stmt = select(Shift).where(
        Shift.user_id == user_db.user_id,
        Shift.status.in_([ShiftStatus.FORMING, ShiftStatus.ACTIVE])
    ).options(
        selectinload(Shift.user),
        selectinload(Shift.events)
    ).order_by(Shift.start_time.desc())

    result = await session.execute(existing_shift_stmt)
    existing_shift = result.scalar_one_or_none()

    if existing_shift:
        logger.info(f"User {user_db.user_id} already has an active/forming shift (ID: {existing_shift.id}). Resuming it.")
        shift_to_display = existing_shift
        transition_message = text_manager.get("shift.already_active", "У вас уже есть активная смена.")

        if shift_to_display.status == ShiftStatus.FORMING:
            logger.info(f"Shift {shift_to_display.id} was FORMING, setting to ACTIVE.")
            shift_to_display.status = ShiftStatus.ACTIVE
            session.add(shift_to_display)
            await session.flush()
            transition_message = text_manager.get("shift.resumed_forming", "Активная смена возобновлена.")

        await state.set_state(ShiftStates.in_shift_active)
        message_text_content = await get_active_shift_message_text(shift_to_display)
        try:
            await call.message.edit_text(
                message_text_content,
                reply_markup=active_shift_keyboard(),
                parse_mode='HTML'
            )
            await state.update_data(active_shift_message_id=call.message.message_id)
        except Exception as e:
            logger.error(f"Failed to edit message for existing shift (User: {user_db.user_id}): {e}", exc_info=True)
        await call.answer(transition_message)
    else:
        logger.info(f"No active/forming shift found for user {user_db.user_id}. Prompting for start time.")
        await call.message.edit_text(
            text=text_manager.get("shift.start_time_prompt"),
            reply_markup=get_start_time_options_keyboard(),
            parse_mode='HTML'
        )
        await state.set_state(ShiftStates.waiting_for_start_time)
        await call.answer()

async def _create_new_shift(session: AsyncSession, user_telegram_id: int, user_telegram_username: Optional[str], start_time_dt: datetime) -> tuple[Shift, str]:
    user_db = await get_or_create_user(
        session, user_telegram_id, user_telegram_username
    )
    if not user_db:
        return None

    logger.info(f"Creating new shift for user {user_db.user_id} with start time {start_time_dt}")
    new_shift = Shift(
        user_id=user_db.user_id,
        start_time=start_time_dt,
        status=ShiftStatus.ACTIVE
    )
    start_event = ShiftEvent(
        event_type=ShiftEventType.START_SHIFT,
        details={"message": "Смена начата"},
        timestamp=start_time_dt
    )
    start_event.shift = new_shift
    session.add(new_shift)
    session.add(start_event)

    await session.flush()
    if new_shift.id is None:
        await session.refresh(new_shift)
        await session.refresh(start_event)

    return new_shift, text_manager.get("shift.new_started")

@router.callback_query(F.data == "shift:start_now", ShiftStates.waiting_for_start_time)
async def handle_start_shift_now(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    start_time = datetime.now(ZoneInfo('Europe/Moscow'))
    logger.info(f"User {call.from_user.id} chose to start shift now at {start_time}.")

    shift_to_display, transition_message = await _create_new_shift(
        session,
        call.from_user.id,
        call.from_user.username,
        start_time
    )

    if not shift_to_display:
        await call.answer(transition_message, show_alert=True)
        if call.message:
            await call.message.edit_text(text_manager.get("menu.main.message"), reply_markup=main_menu_keyboard())
        await state.set_state(MenuStates.in_main_menu)
        return

    await state.set_state(ShiftStates.in_shift_active)
    message_text_content = await get_active_shift_message_text(shift_to_display)

    try:
        if call.message:
            await call.message.edit_text(
                message_text_content,
                reply_markup=active_shift_keyboard(),
                parse_mode='HTML'
            )
            await state.update_data(active_shift_message_id=call.message.message_id)
    except Exception as e:
        logger.error(f"Failed to edit active shift message (start_now) for user {call.from_user.id}: {e}",exc_info=True)
        if call.message:
            await call.message.delete()
            new_msg = await call.bot.send_message(
                chat_id=call.from_user.id,
                text=message_text_content,
                reply_markup=active_shift_keyboard(),
                parse_mode="HTML"
            )
            await state.update_data(active_shift_message_id=new_msg.message_id)

    await call.answer(transition_message)

@router.callback_query(F.data == "shift:start_manual_time", ShiftStates.waiting_for_start_time)
async def prompt_manual_start_time(call: CallbackQuery, state: FSMContext):
    logger.info(f"User {call.from_user.id} chose to specify start time manually.")
    if call.message:
        await call.message.edit_text(
            text=text_manager.get("shift.start_time_manual_prompt"),
            reply_markup=get_cancel_start_time_keyboard(),
            parse_mode="HTML"
        )
        await state.update_data(prompt_message_id=call.message.message_id)
    await call.answer()

@router.message(ShiftStates.waiting_for_start_time, F.text)
async def process_manual_start_time(message: Message, state: FSMContext, session: AsyncSession):
    user_input = message.text.strip()
    now_moscow = datetime.now(ZoneInfo('Europe/Moscow'))
    parsed_time: Optional[datetime] = None
    error_occurred = False

    try:
        if ' ' in user_input:
            time_str, date_str = user_input.split(' ', 1)
            date_parts = date_str.split('.')
            if len(date_parts) == 2:
                dt_str = f"{date_str}.{now_moscow.year} {time_str}"
                parsed_time = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
            elif len(date_parts) == 3:
                year_part = date_parts[2]
                dt_str = f"{date_str} {time_str}"
                if len(year_part) == 2:
                    parsed_time = datetime.strptime(dt_str, "%d.%m.%y %H:%M")
                elif len(year_part) == 4:
                    parsed_time = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
                else:
                    raise ValueError("Invalid year format in date")
            else:
                raise ValueError("Invalid date format")
        else:
            parsed_time = datetime.strptime(user_input, "%H:%M")
            parsed_time = parsed_time.replace(year=now_moscow.year, month=now_moscow.month, day=now_moscow.day)

        if parsed_time:
            parsed_time = parsed_time.replace(tzinfo=ZoneInfo('Europe/Moscow'))
            if parsed_time > now_moscow:
                error_msg = await message.reply(text_manager.get("shift.start_time_in_future"))
                error_occurred = True
                await asyncio.sleep(3)
                await error_msg.delete()
                await message.delete()
    except ValueError:
        error_msg = await message.reply(text_manager.get("shift.start_time_invalid_format"))
        error_occurred = True
        await asyncio.sleep(3)
        await error_msg.delete()
        await message.delete()

    if error_occurred or not parsed_time:
        return

    logger.info(f"User {message.from_user.id} entered start time manually: {parsed_time}")

    shift_to_display, transition_message = await _create_new_shift(
        session,
        message.from_user.id,
        message.from_user.username,
        parsed_time
    )

    if not shift_to_display:
        error_msg = await message.reply(transition_message)
        await asyncio.sleep(3)
        await error_msg.delete()
        await message.delete()
        return

    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    await message.delete()

    await state.set_state(ShiftStates.in_shift_active)
    message_text_content = await get_active_shift_message_text(shift_to_display)

    try:
        if prompt_message_id:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=message_text_content,
                reply_markup=active_shift_keyboard(),
                parse_mode='HTML'
            )
            await state.update_data(active_shift_message_id=prompt_message_id)
        else:
            new_msg = await message.answer(
                message_text_content,
                reply_markup=active_shift_keyboard(),
                parse_mode='HTML'
            )
            await state.update_data(active_shift_message_id=new_msg.message_id)

    except Exception as e:
        logger.error(f"Failed to edit active shift message (start_manual_time) for user {message.from_user.id}: {e}",exc_info=True)
        new_msg = await message.answer(
            message_text_content,
            reply_markup=active_shift_keyboard(),
            parse_mode="HTML"
        )
        await state.update_data(active_shift_message_id=new_msg.message_id)

@router.callback_query(F.data == "shift:start_cancel_manual_input", ShiftStates.waiting_for_start_time)
async def cancel_manual_start_time_input(call: CallbackQuery):
    logger.info(f"User {call.from_user.id} cancelled manual time input.")
    if call.message:
        await call.message.edit_text(
            text=text_manager.get("shift.start_time_prompt"),
            reply_markup=get_start_time_options_keyboard(),
            parse_mode="HTML"
        )
    await call.answer(text_manager.get("shift.start_shift_cancelled", "Начало смены отменено."))

@router.callback_query(F.data == "shift:end", ShiftStates.in_shift_active)
async def prompt_end_shift_time(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    stmt = select(Shift).where(
        Shift.user_id == call.from_user.id,
        Shift.status == ShiftStatus.ACTIVE
    )
    shift = await session.scalar(stmt)

    if not shift:
        await call.answer(text_manager.get("shift.no_active_shift", "Активная смена не найдена."), show_alert=True)
        if call.message:
            await call.message.edit_text(text=text_manager.get("menu.main.message"), reply_markup=main_menu_keyboard())
        await state.set_state(MenuStates.in_main_menu)
        return

    logger.info(f"User {call.from_user.id} initiated end shift process for shift ID {shift.id}.")
    if call.message:
        await call.message.edit_text(
            text=text_manager.get("shift.end_time_prompt"),
            reply_markup=get_end_time_options_keyboard(),
            parse_mode="HTML"
        )
    await state.set_state(ShiftStates.waiting_for_end_time)
    await call.answer()


async def _finalize_shift_completion(
    call_or_message: Union[CallbackQuery, Message],
    state: FSMContext,
    session: AsyncSession,
    user_telegram_id: int,
    end_time_dt: datetime
):
    stmt = select(Shift).where(
        Shift.user_id == user_telegram_id,
        Shift.status == ShiftStatus.ACTIVE
    ).options(selectinload(Shift.events))
    shift = await session.scalar(stmt)

    if not shift:
        error_text = text_manager.get("shift.no_active_shift", "Активная смена не найдена.")
        if isinstance(call_or_message, CallbackQuery):
            await call_or_message.answer(error_text, show_alert=True)
            if call_or_message.message:
                await call_or_message.message.edit_text(text=text_manager.get("menu.main.message"), reply_markup=main_menu_keyboard())
        else:
            await call_or_message.reply(error_text)
            await call_or_message.delete()
        await state.set_state(MenuStates.in_main_menu)
        return

    if shift.start_time >= end_time_dt:
        error_text = text_manager.get("shift.end_time_before_start")
        if isinstance(call_or_message, CallbackQuery):
            await call_or_message.answer(error_text, show_alert=True)
            if call_or_message.message:
                await call_or_message.message.edit_text(
                    text=text_manager.get("shift.end_time_prompt"),
                    reply_markup=get_end_time_options_keyboard(),
                    parse_mode="HTML"
                )
            await state.set_state(ShiftStates.waiting_for_end_time)
        else:
            error_msg = await call_or_message.reply(error_text)
            await asyncio.sleep(3)
            await error_msg.delete()
            await call_or_message.delete()
        return

    shift.status = ShiftStatus.COMPLETED
    shift.end_time = end_time_dt
    end_event = ShiftEvent(
        event_type=ShiftEventType.COMPLETE_SHIFT,
        details={"message": "Смена завершена"},
        timestamp=end_time_dt
    )
    end_event.shift = shift
    session.add(shift)
    session.add(end_event)
    await session.flush()

    logger.info(f"Shift ID {shift.id} for user {user_telegram_id} completed at {end_time_dt}.")

    target_message_id_to_edit = None
    chat_id_for_menu = None

    if isinstance(call_or_message, CallbackQuery) and call_or_message.message:
        target_message_id_to_edit = call_or_message.message.message_id
        chat_id_for_menu = call_or_message.message.chat.id
    elif isinstance(call_or_message, Message):
        data = await state.get_data()
        target_message_id_to_edit = data.get("prompt_message_id_end_shift")
        chat_id_for_menu = call_or_message.chat.id
        await call_or_message.delete()

    if target_message_id_to_edit and chat_id_for_menu:
        try:
            await call_or_message.bot.edit_message_text(
                chat_id=chat_id_for_menu,
                message_id=target_message_id_to_edit,
                text=text_manager.get("menu.main.message"),
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to edit message to main menu after shift completion: {e}")
            await call_or_message.bot.send_message(
                chat_id_for_menu,
                text=text_manager.get("menu.main.message"),
                reply_markup=main_menu_keyboard()
            )
    elif chat_id_for_menu:
         await call_or_message.bot.send_message(
                chat_id_for_menu,
                text=text_manager.get("menu.main.message"),
                reply_markup=main_menu_keyboard()
            )


    await state.set_state(MenuStates.in_main_menu)
    if isinstance(call_or_message, CallbackQuery):
        await call_or_message.answer(text_manager.get("shift.shift_completed_success"))


@router.callback_query(F.data == "shift:end_now", ShiftStates.waiting_for_end_time)
async def handle_end_shift_now(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    end_time = datetime.now(ZoneInfo('Europe/Moscow'))
    logger.info(f"User {call.from_user.id} chose to end shift now at {end_time}.")
    await _finalize_shift_completion(call, state, session, call.from_user.id, end_time)


@router.callback_query(F.data == "shift:end_manual_time", ShiftStates.waiting_for_end_time)
async def prompt_manual_end_time(call: CallbackQuery, state: FSMContext):
    logger.info(f"User {call.from_user.id} chose to specify end time manually.")
    if call.message:
        await call.message.edit_text(
            text=text_manager.get("shift.end_time_manual_prompt"),
            reply_markup=get_cancel_end_time_keyboard(),
            parse_mode="HTML"
        )
        await state.update_data(prompt_message_id_end_shift=call.message.message_id)
    await call.answer()


@router.message(ShiftStates.waiting_for_end_time, F.text)
async def process_manual_end_time(message: Message, state: FSMContext, session: AsyncSession):
    user_input = message.text.strip()
    now_moscow = datetime.now(ZoneInfo('Europe/Moscow'))
    parsed_time: Optional[datetime] = None
    error_occurred = False

    try:
        if ' ' in user_input:
            time_str, date_str = user_input.split(' ', 1)
            date_parts = date_str.split('.')
            if len(date_parts) == 2:
                dt_str_to_parse = f"{date_str}.{now_moscow.year} {time_str}"
                parsed_time = datetime.strptime(dt_str_to_parse, "%d.%m.%Y %H:%M")
            elif len(date_parts) == 3:
                year_part = date_parts[2]
                dt_str_to_parse = f"{date_str} {time_str}"
                if len(year_part) == 2: parsed_time = datetime.strptime(dt_str_to_parse, "%d.%m.%y %H:%M")
                elif len(year_part) == 4: parsed_time = datetime.strptime(dt_str_to_parse, "%d.%m.%Y %H:%M")
                else: raise ValueError("Invalid year format in date")
            else: raise ValueError("Invalid date format")
        else:
            parsed_time = datetime.strptime(user_input, "%H:%M")
            parsed_time = parsed_time.replace(year=now_moscow.year, month=now_moscow.month, day=now_moscow.day)

        if parsed_time:
            parsed_time = parsed_time.replace(tzinfo=ZoneInfo('Europe/Moscow'))
            if parsed_time > now_moscow:
                error_msg = await message.reply(text_manager.get("shift.end_time_in_future"))
                error_occurred = True
                await asyncio.sleep(3)
                await error_msg.delete()
                await message.delete()
    except ValueError:
        error_msg = await message.reply(text_manager.get("shift.end_time_invalid_format"))
        error_occurred = True
        await asyncio.sleep(3)
        await error_msg.delete()
        await message.delete()

    if error_occurred or not parsed_time:
        return

    logger.info(f"User {message.from_user.id} entered end time manually: {parsed_time}")
    await _finalize_shift_completion(message, state, session, message.from_user.id, parsed_time)


@router.callback_query(F.data == "shift:end_cancel_manual_input", ShiftStates.waiting_for_end_time)
async def cancel_manual_end_time_input(call: CallbackQuery, state: FSMContext):
    logger.info(f"User {call.from_user.id} cancelled manual end time input.")
    if call.message:
        await call.message.edit_text(
            text=text_manager.get("shift.end_time_prompt"),
            reply_markup=get_end_time_options_keyboard(),
            parse_mode="HTML"
        )
    await call.answer(text_manager.get("shift.end_shift_cancelled"))


@router.callback_query(F.data == "shift:show_active")
async def show_active_shift_menu_callback(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    user_id = call.from_user.id
    stmt = select(Shift).where(
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.ACTIVE
    ).options(selectinload(Shift.events), selectinload(Shift.user))
    shift = await session.scalar(stmt)

    if not shift:
        await call.answer(text_manager.get("shift.no_active_shift"), show_alert=True)
        if call.message:
            try:
                await call.message.edit_text(
                    text=text_manager.get("menu.main.message"),
                    reply_markup=main_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"Error editing message to main menu on no active shift (cancel): {e}")
                try:
                    await call.message.delete()
                except Exception as del_e:
                    logger.error(f"Error deleting message on no active shift (cancel) fallback: {del_e}")
                await call.bot.send_message(call.from_user.id, text_manager.get("menu.main.message"), reply_markup=main_menu_keyboard())

        await state.set_state(MenuStates.in_main_menu)
        return

    await _return_to_active_shift_view(call, state, shift)


@router.callback_query(F.data == "shift:add_mileage_prompt", ShiftStates.in_shift_active)
async def handle_add_mileage_prompt(call: CallbackQuery, state: FSMContext):
    if call.message:
        await state.update_data(active_shift_message_id=call.message.message_id)
        await call.message.edit_text(
            text=text_manager.get("shift.mileage_prompt"),
            reply_markup=mileage_keyboard(),
            parse_mode='HTML'
        )
    await state.set_state(ShiftStates.in_shift_mileage)
    await call.answer()


@router.callback_query(F.data.startswith("shift:mileage:add:"), ShiftStates.in_shift_mileage)
async def handle_add_mileage_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        mileage_value = float(call.data.split(":")[-1])
        if mileage_value < 0:
            await call.answer(text_manager.get("shift.value_error_negative"), show_alert=True)
            return
    except ValueError:
        await call.answer(text_manager.get("shift.value_error_generic"), show_alert=True)
        return

    stmt = select(Shift).where(
        Shift.user_id == call.from_user.id,
        Shift.status == ShiftStatus.ACTIVE
    ).options(selectinload(Shift.events))
    shift = await session.scalar(stmt)

    shift.total_mileage = mileage_value
    new_event = ShiftEvent(
        event_type=ShiftEventType.ADD_MILEAGE,
        details={"distance_km": mileage_value, "description": f"+{mileage_value} км"},
        timestamp=datetime.now(ZoneInfo('Europe/Moscow'))
    )
    new_event.shift = shift
    session.add_all([shift, new_event])
    await session.flush()

    if shift:
        await _return_to_active_shift_view(call, state, shift,
                                           text_manager.get("shift.mileage_added", value=mileage_value))
    else:
        await call.answer(text_manager.get("shift.no_active_shift"), show_alert=True)
        if call.message:
            await call.message.edit_text(text=text_manager.get("menu.main.message"), reply_markup=main_menu_keyboard())
        await state.set_state(MenuStates.in_main_menu)


@router.message(ShiftStates.in_shift_mileage, F.text)
async def handle_add_mileage_input(message: Message, state: FSMContext, session: AsyncSession):
    try:
        mileage_value = float(message.text)
        if mileage_value < 0:
            error_msg = await message.answer(text_manager.get("shift.value_error_negative"))
            await message.delete()
            await asyncio.sleep(3)
            await error_msg.delete()
            return
    except ValueError:
        error_msg = await message.answer(text_manager.get("shift.value_error_generic"))
        await message.delete()
        await asyncio.sleep(3)
        await error_msg.delete()
        return

    stmt = select(Shift).where(
        Shift.user_id == message.from_user.id,
        Shift.status == ShiftStatus.ACTIVE
    ).options(selectinload(Shift.events))
    shift = await session.scalar(stmt)

    shift.total_mileage = mileage_value
    new_event = ShiftEvent(
        event_type=ShiftEventType.ADD_MILEAGE,
        details={"distance_km": mileage_value, "description": f"Пробег обновлен до {mileage_value} км"},
        timestamp=datetime.now(ZoneInfo('Europe/Moscow'))
    )
    new_event.shift = shift
    session.add_all([shift, new_event])
    await session.flush()

    if shift:
        await _return_to_active_shift_view(message, state, shift,
                                           text_manager.get("shift.mileage_added", value=mileage_value))
    else:
        await message.answer(text_manager.get("shift.no_active_shift"))


@router.callback_query(F.data == "shift:add_tips_prompt", ShiftStates.in_shift_active)
async def handle_add_tips_prompt(call: CallbackQuery, state: FSMContext):
    if call.message:
        await state.update_data(active_shift_message_id=call.message.message_id)
        await call.message.edit_text(
            text=text_manager.get("shift.tips_prompt"),
            reply_markup=tips_keyboard(),
            parse_mode='HTML'
        )
    await state.set_state(ShiftStates.in_shift_tips)
    await call.answer()


@router.callback_query(F.data.startswith("shift:tips:add:"), ShiftStates.in_shift_tips)
async def handle_add_tips_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        tips_value = float(call.data.split(":")[-1])
        if tips_value < 0:
            await call.answer(text_manager.get("shift.value_error_negative"), show_alert=True)
            return
    except ValueError:
        await call.answer(text_manager.get("shift.value_error_generic"), show_alert=True)
        return

    shift = await _update_shift_value_and_event(
        session, call.from_user.id, tips_value, "total_tips",
        ShiftEventType.ADD_TIPS,
        {"amount": tips_value, "currency": "RUB", "description": f"+{tips_value} руб."}
    )
    if shift:
        await _return_to_active_shift_view(call, state, shift, text_manager.get("shift.tips_added", value=tips_value))
    else:
        await call.answer(text_manager.get("shift.no_active_shift"), show_alert=True)
        if call.message:
            await call.message.edit_text(text=text_manager.get("menu.main.message"), reply_markup=main_menu_keyboard())
        await state.set_state(MenuStates.in_main_menu)


@router.message(ShiftStates.in_shift_tips, F.text)
async def handle_add_tips_input(message: Message, state: FSMContext, session: AsyncSession):
    try:
        tips_value = float(message.text)
        if tips_value < 0:
            error_msg = await message.answer(text_manager.get("shift.value_error_negative"))
            await message.delete()
            await asyncio.sleep(3)
            await error_msg.delete()
            return
    except ValueError:
        error_msg = await message.answer(text_manager.get("shift.value_error_generic"))
        await message.delete()
        await asyncio.sleep(3)
        await error_msg.delete()
        return

    shift = await _update_shift_value_and_event(
        session, message.from_user.id, tips_value, "total_tips",
        ShiftEventType.ADD_TIPS,
        {"amount": tips_value, "currency": "RUB", "description": f"+{tips_value} руб."}
    )
    if shift:
        await _return_to_active_shift_view(message, state, shift,
                                           text_manager.get("shift.tips_added", value=tips_value))
    else:
        await message.answer(text_manager.get("shift.no_active_shift"))


@router.callback_query(F.data == "shift:add_expenses_prompt", ShiftStates.in_shift_active)
async def handle_add_expenses_category_prompt(call: CallbackQuery, state: FSMContext):
    if call.message:
        await state.update_data(active_shift_message_id=call.message.message_id)
        await call.message.edit_text(
            text=text_manager.get("shift.expenses_category_prompt"),
            reply_markup=expenses_category_keyboard(),
            parse_mode='HTML'
        )
    await state.set_state(ShiftStates.in_shift_expenses_category)
    await call.answer()


@router.callback_query(F.data.startswith("shift:expenses:category:"), ShiftStates.in_shift_expenses_category)
async def handle_expense_category_selected(call: CallbackQuery, state: FSMContext):
    category_code = call.data.split(":")[-1]
    category_display_name = text_manager.get(f"shift.expenses.categories.{category_code}",
                                             default=category_code.capitalize())

    await state.update_data(expense_category=category_code, expense_category_display=category_display_name)

    if call.message:
        await call.message.edit_text(
            text=text_manager.get("shift.expenses_amount_prompt", category=category_display_name),
            reply_markup=cancel_action_keyboard(),
            parse_mode='HTML'
        )
    await state.set_state(ShiftStates.in_shift_expenses)
    await call.answer()


@router.message(ShiftStates.in_shift_expenses, F.text)
async def handle_add_expenses_amount_input(message: Message, state: FSMContext, session: AsyncSession):
    try:
        expenses_value = float(message.text)
        if expenses_value <= 0:
            error_msg_text = text_manager.get("shift.value_error_negative") \
                if expenses_value < 0 else "Сумма расхода должна быть больше нуля."
            error_msg = await message.answer(error_msg_text)
            await message.delete()
            await asyncio.sleep(3)
            await error_msg.delete()
            return
    except ValueError:
        error_msg = await message.answer(text_manager.get("shift.value_error_generic"))
        await message.delete()
        await asyncio.sleep(3)
        await error_msg.delete()
        return

    data = await state.get_data()
    category_code = data.get("expense_category", "other")
    category_display_name = data.get("expense_category_display",
                                     text_manager.get("shift.expenses.categories.other", "Другое"))

    shift = await _update_shift_value_and_event(
        session, message.from_user.id, expenses_value, "total_expenses",
        ShiftEventType.ADD_EXPENSE,
        {
            "amount": expenses_value,
            "category_code": category_code,
            "category": category_display_name,
            "description": f"-{expenses_value} руб. ({category_display_name})"
        }
    )
    if shift:
        await _return_to_active_shift_view(
            message,
            state,
            shift,
            text_manager.get("shift.expenses_added", value=expenses_value, category=category_display_name)
        )
    else:
        await message.answer(text_manager.get("shift.no_active_shift"))