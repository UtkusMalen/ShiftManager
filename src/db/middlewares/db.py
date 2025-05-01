from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

class DBSessionMiddleware(BaseMiddleware):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    async def __call__(self, handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]], event: Update, data: Dict[str, Any]) -> Any:
        async with self.session_factory() as session:
            try:
                data["session"] = session
                return await handler(event, data)
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error during request: {e}", exc_info=True)
                raise
            finally:
                await session.close()
