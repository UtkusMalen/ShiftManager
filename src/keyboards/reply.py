from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from src.utils.text_manager import text_manager

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=text_manager.get("menu.main.buttons.statistics"))
    builder.button(text=text_manager.get("menu.main.buttons.history"))
    builder.button(text=text_manager.get("menu.main.buttons.my_profile"))
    builder.button(text=text_manager.get("menu.main.buttons.start_shift"))

    builder.adjust(2,2)
    return builder.as_markup(resize_keyboard=True)
