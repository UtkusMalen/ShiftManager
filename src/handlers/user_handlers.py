import logging
from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.db.models import User
from src.keyboards.inline import main_menu_keyboard
from src.states.menu import MenuStates
from src.utils.text_manager import text_manager

logger = logging.getLogger(__name__)
router = Router()

async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None = None
) -> User:
    """Get user from DB or create a new one."""
    stmt = select(User).where(User.user_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        logging.info(f"User with telegram_id={telegram_id} not found. Creating new user...")
        user = User(user_id=telegram_id, username=username)
        session.add(user)
        await session.flush()
        logger.info(f"New user created with temporary ID before commit: {user}")
    elif user.username != username:
        logger.info(f"Updating username for user with telegram_id={telegram_id} from {user.username} to {username}")
        user.username = username
        await session.flush() 

    return user

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, session: AsyncSession):
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    logger.info(f"User {user.id} started the bot.")

    await message.answer(
        f"{text_manager.get('menu.main.message')}",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MenuStates.in_main_menu)
