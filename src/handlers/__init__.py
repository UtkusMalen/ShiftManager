from aiogram import Router
from src.handlers.common import router as common_router

main_handler_router = Router()
main_handler_router.include_router(common_router)

__all__ = ["main_handler_router"]