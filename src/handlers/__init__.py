from aiogram import Router
from src.handlers.user_handlers import router as user_router
from src.handlers.shift_handlers import router as shift_router

main_handler_router = Router()

main_handler_router.include_router(user_router)
main_handler_router.include_router(shift_router)


__all__ = ["main_handler_router"]