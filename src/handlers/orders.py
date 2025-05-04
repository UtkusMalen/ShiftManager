import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.models import Shift, ShiftStatus, ShiftEvent, ShiftEventType
from sqlalchemy.ext.asyncio import AsyncSession

from src.states.shift import ShiftStates
from src.utils.formatters import get_active_shift_message_text
from src.keyboards.shift import active_shift_keyboard

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data.startswith("shift:add_order_"), ShiftStates.in_shift_active)
async def add_order(call: CallbackQuery, session: AsyncSession):
    user_id = call.from_user.id
    order = int(call.data.split("_")[-1])
    stmt = select(Shift).where(
        Shift.user_id == user_id,
        Shift.status == ShiftStatus.ACTIVE
    ).options(
        selectinload(Shift.events)
    )
    shift = await session.scalar(stmt)
    if shift:
        shift.orders_count += order
        order_event = ShiftEvent(
            event_type=ShiftEventType.ADD_ORDER,
            details={
                "count": order,
                "description": f"{order} заказ(а)"
            }
        )
        order_event.shift = shift
        session.add(shift)
        session.add(order_event)
        await session.commit()
        await session.refresh(shift)
        await call.message.edit_text(
            await get_active_shift_message_text(shift),
            reply_markup=active_shift_keyboard(),
            parse_mode='HTML'
        )
        await call.answer("Заказ добавлен!")
