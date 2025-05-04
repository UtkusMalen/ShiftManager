import asyncio
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Shift, ShiftStatus
from src.keyboards.initial_data import initial_data_keyboard, rate_keyboard, order_rate_keyboard, mileage_rate_keyboard
from src.states.shift import ShiftStates
from src.utils.text_manager import text_manager

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "shift:initial_data", ShiftStates.in_shift_active)
async def initial_data(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    await call.message.edit_text(text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)

    await call.answer()

@router.callback_query(F.data == "initial_data:rate", ShiftStates.in_initial_data_menu)
async def initial_data_rate(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    message = await call.message.edit_text(text=text_manager.get("shift.initial_data.rate_prompt", rate=shift.rate), reply_markup=rate_keyboard(), parse_mode='HTML')
    await state.update_data(message_id=message.message_id)
    await state.set_state(ShiftStates.in_initial_data_rate)
    await call.answer()

@router.callback_query(F.data.startswith("initial_data:rate:"), ShiftStates.in_initial_data_rate)
async def initial_data_rate_set(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    rate = float(call.data.split(":")[-1])
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    shift.rate = rate
    session.add(shift)
    await session.commit()
    await session.refresh(shift)

    await call.message.edit_text(text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)
    await call.answer()

@router.message(ShiftStates.in_initial_data_rate)
async def initial_data_rate_set(message: Message, state: FSMContext, session: AsyncSession):
    rate = float(message.text)
    if rate < 0:
        bot_answer = await message.answer(text=text_manager.get("shift.initial_data.rate_error"))
        await message.delete()
        await asyncio.sleep(4)
        await message.bot.delete_message(chat_id=message.chat.id, message_id=bot_answer.message_id)
        return

    stmt = select(Shift).where(Shift.user_id == message.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    data = await state.get_data()
    message_id = data.get("message_id")

    shift.rate = rate
    session.add(shift)
    await session.commit()
    await session.refresh(shift)
    await message.delete()

    await message.bot.edit_message_text(chat_id=message.chat.id,message_id=message_id,text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)

@router.callback_query(F.data == "initial_data:order_rate", ShiftStates.in_initial_data_menu)
async def initial_data_order_rate(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    message = await call.message.edit_text(text=text_manager.get("shift.initial_data.order_rate_prompt", order_rate=shift.order_rate), reply_markup=order_rate_keyboard(), parse_mode='HTML')
    await state.update_data(message_id=message.message_id)
    await state.set_state(ShiftStates.in_initial_data_order_rate)
    await call.answer()

@router.callback_query(F.data.startswith("initial_data:order_rate:"), ShiftStates.in_initial_data_order_rate)
async def initial_data_order_rate_set(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    order_rate = float(call.data.split(":")[-1])
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    shift.order_rate = order_rate
    session.add(shift)
    await session.commit()
    await session.refresh(shift)

    await call.message.edit_text(text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)
    await call.answer()

@router.message(ShiftStates.in_initial_data_order_rate)
async def initial_data_order_rate_set(message: Message, state: FSMContext, session: AsyncSession):
    order_rate = float(message.text)
    if order_rate < 0:
        bot_answer = await message.answer(text=text_manager.get("shift.initial_data.rate_error"))
        await message.delete()
        await asyncio.sleep(4)
        await message.bot.delete_message(chat_id=message.chat.id, message_id=bot_answer.message_id)
        return

    stmt = select(Shift).where(Shift.user_id == message.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    data = await state.get_data()
    message_id = data.get("message_id")

    shift.order_rate = order_rate
    session.add(shift)
    await session.commit()
    await session.refresh(shift)
    await message.delete()
    await message.bot.edit_message_text(chat_id=message.chat.id,message_id=message_id,text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)


@router.callback_query(F.data == "initial_data:mileage_rate", ShiftStates.in_initial_data_menu)
async def initial_data_mileage_rate(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    message = await call.message.edit_text(text=text_manager.get("shift.initial_data.mileage_rate_prompt", mileage_rate=shift.mileage_rate), reply_markup=mileage_rate_keyboard(), parse_mode='HTML')
    await state.update_data(message_id=message.message_id)
    await state.set_state(ShiftStates.in_initial_data_mileage_rate)
    await call.answer()

@router.callback_query(F.data.startswith("initial_data:mileage_rate:"), ShiftStates.in_initial_data_mileage_rate)
async def initial_data_mileage_rate_set(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    mileage_rate = float(call.data.split(":")[-1])
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    shift.mileage_rate = mileage_rate
    session.add(shift)
    await session.commit()
    await session.refresh(shift)

    await call.message.edit_text(text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)
    await call.answer()

@router.message(ShiftStates.in_initial_data_mileage_rate)
async def initial_data_mileage_rate_set(message: Message, state: FSMContext, session: AsyncSession):
    mileage_rate = float(message.text)
    if mileage_rate < 0:
        bot_answer = await message.answer(text=text_manager.get("shift.initial_data.rate_error"))
        await message.delete()
        await asyncio.sleep(4)
        await message.bot.delete_message(chat_id=message.chat.id, message_id=bot_answer.message_id)
        return

    stmt = select(Shift).where(Shift.user_id == message.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    data = await state.get_data()
    message_id = data.get("message_id")

    shift.mileage_rate = mileage_rate
    session.add(shift)
    await session.commit()
    await session.refresh(shift)
    await message.delete()
    await message.bot.edit_message_text(chat_id=message.chat.id,message_id=message_id,text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)

@router.callback_query(F.data == "initial_data:cancel")
async def initial_data_cancel(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    stmt = select(Shift).where(Shift.user_id == call.from_user.id, Shift.status == ShiftStatus.ACTIVE)
    shift = await session.scalar(stmt)

    await call.message.edit_text(text=text_manager.get("shift.initial_data.in_menu"), reply_markup=initial_data_keyboard(rate=shift.rate, order_rate=shift.order_rate, mileage_rate=shift.mileage_rate))
    await state.set_state(ShiftStates.in_initial_data_menu)
    await call.answer()