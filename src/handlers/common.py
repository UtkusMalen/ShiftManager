from aiogram import Router, types
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.keyboards.reply import main_menu_keyboard
from src.utils.text_manager import text_manager
from src.states.menu import MenuStates

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, session: AsyncSession):
    user_name = message.from_user.first_name
    await message.answer(
        f"{text_manager.get('menu.main.message')}",
        reply_markup=main_menu_keyboard()
    )

    await state.set_state(MenuStates.in_main_menu)

@router.message(MenuStates.in_main_menu)
async def handle_main_menu_buttons(message: Message, state: FSMContext, session: AsyncSession):
    button_text = message.text
    stats_button_text = text_manager.get("menu.main.buttons.statistics")
    history_button_text = text_manager.get("menu.main.buttons.history")
    my_profile_button_text = text_manager.get("menu.main.buttons.my_profile")
    start_shift_button_text = text_manager.get("menu.main.buttons.start_shift")

