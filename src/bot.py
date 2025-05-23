import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import settings
from src.db.engine import AsyncSessionFactory, dispose_engine
from src.db.middlewares.db import DBSessionMiddleware
from src.handlers import user_handlers, shift_handlers, main_menu, orders, initial_data, history, in_developement, statistics_handlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(DBSessionMiddleware(AsyncSessionFactory))
    dp.callback_query.middleware(DBSessionMiddleware(AsyncSessionFactory))
    logger.info("Database session middleware added")

    dp.include_router(user_handlers.router)
    dp.include_router(shift_handlers.router)
    dp.include_router(main_menu.router)
    dp.include_router(orders.router)
    dp.include_router(initial_data.router)
    dp.include_router(history.router)
    dp.include_router(in_developement.router)
    dp.include_router(statistics_handlers.router)

    logger.info("Starting bot polling")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot polling error: {e}", exc_info=True)
    finally:
        logger.info("Stopping bot polling")
        await dispose_engine()
        await dp.storage.close()
        await bot.session.close()
        logger.info("Bot polling stopped")

if __name__ == "__main__":
    if not settings.telegram_bot_token:
        logger.error("Error: Telegram bot token is not set. Please check your .env file or environment variables.")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)

