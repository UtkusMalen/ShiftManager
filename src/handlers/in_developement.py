from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.utils.text_manager import text_manager

router = Router()


@router.callback_query(F.data == "main_menu:in_development")
async def in_development(call: CallbackQuery):
    await call.answer(text_manager.get("menu.in_development"), show_alert=True)