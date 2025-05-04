import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from src.states.menu import MenuStates
from src.utils.text_manager import text_manager
from src.keyboards.main_menu import main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "main_menu")
async def goto_main_menu(call: CallbackQuery, state: FSMContext):
    logger.info(f"User {call.from_user.id} went back to the main menu via callback.")
    try:
        await call.message.edit_text(
            text=text_manager.get("menu.main.message"),
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to edit main menu message: {e}", exc_info=True)
        await call.message.answer(
            text=text_manager.get("menu.main.message"),
            reply_markup=main_menu_keyboard()
        )
    await state.set_state(MenuStates.in_main_menu)
    await call.answer()

