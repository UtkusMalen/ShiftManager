from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.utils.text_manager import text_manager


def initial_data_keyboard(rate, order_rate, mileage_rate) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text_manager.get("shift.initial_data.rate",rate=rate), callback_data="initial_data:rate")
    builder.button(text=text_manager.get("shift.initial_data.order_rate", order_rate=order_rate), callback_data="initial_data:order_rate")
    builder.button(text=text_manager.get("shift.initial_data.mileage_rate", mileage_rate=mileage_rate), callback_data="initial_data:mileage_rate")
    builder.button(text=text_manager.get("common.buttons.back"), callback_data="shift:start")
    builder.adjust(2,1)
    return builder.as_markup()

def rate_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [150, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270]
    for button_text in buttons:
        builder.button(text=str(button_text), callback_data=f"initial_data:rate:{button_text}")
    builder.button(text=text_manager.get("shift.initial_data.cancel"), callback_data="initial_data:cancel")
    builder.adjust(4,4,4,4,1)
    return builder.as_markup()

def order_rate_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180]
    for button_text in buttons:
        builder.button(text=str(button_text), callback_data=f"initial_data:order_rate:{button_text}")
    builder.button(text=text_manager.get("shift.initial_data.cancel"), callback_data="initial_data:cancel")
    builder.adjust(4,4,4,4,1)
    return builder.as_markup()

def mileage_rate_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    for button_text in buttons:
        builder.button(text=str(button_text), callback_data=f"initial_data:mileage_rate:{button_text}")
    builder.button(text=text_manager.get("shift.initial_data.cancel"), callback_data="initial_data:cancel")
    builder.adjust(4,4,4,4,1)
    return builder.as_markup()