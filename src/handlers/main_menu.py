import logging

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
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

    current_message = call.message
    new_text = text_manager.get("menu.main.message")
    new_markup = main_menu_keyboard()

    try:
        if current_message and current_message.content_type == 'text':
            await current_message.edit_text(
                text=new_text,
                reply_markup=new_markup
            )
        elif current_message:
            await current_message.delete()
            await call.bot.send_message(
                chat_id=call.from_user.id,
                text=new_text,
                reply_markup=new_markup
            )
        else:
            await call.bot.send_message(
                chat_id=call.from_user.id,
                text=new_text,
                reply_markup=new_markup
            )
    except TelegramBadRequest as e:
        logger.error(f"Failed to edit/delete previous message in main_menu: {e}. Sending new message.")
        await call.bot.send_message(
            chat_id=call.from_user.id,
            text=new_text,
            reply_markup=new_markup
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred in goto_main_menu: {e}", exc_info=True)
        await call.bot.send_message(
            chat_id=call.from_user.id,
            text=new_text,
            reply_markup=new_markup
        )

    await state.set_state(MenuStates.in_main_menu)
    await call.answer()

