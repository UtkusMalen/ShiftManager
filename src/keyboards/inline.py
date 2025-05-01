import logging

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.utils.text_manager import text_manager

logger = logging.getLogger(__name__)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    try:
        builder.button(text=text_manager.get("menu.main.buttons.statistics"), callback_data="main_menu:statistics")
        builder.button(text=text_manager.get("menu.main.buttons.history"), callback_data="main_menu:history")
        builder.button(text=text_manager.get("menu.main.buttons.my_profile"), callback_data="main_menu:profile")
        builder.button(text=text_manager.get("menu.main.buttons.start_shift"), callback_data="main_menu:start_shift")

        builder.adjust(2,2)
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Failed to create main menu keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[])