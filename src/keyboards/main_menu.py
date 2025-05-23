import logging

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    try:
        builder.button(
            text=tm.get("menu.main.buttons.statistics"),
            callback_data="statistics:select_period",
        )
        builder.button(
            text=tm.get("menu.main.buttons.history"),
            callback_data="main_menu:history",
        )
        builder.button(
            text=tm.get("menu.main.buttons.my_profile"),
            callback_data="main_menu:in_development",
        )
        builder.button(
            text=tm.get("menu.main.buttons.start_shift"),
            callback_data="shift:start",
        )
        builder.adjust(2, 2)
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Failed to create main menu keyboard: {e}", exc_info=True)
        fallback_builder = InlineKeyboardBuilder()
        fallback_builder.button(text="Ошибка меню", callback_data="error:menu")
        return fallback_builder.as_markup()