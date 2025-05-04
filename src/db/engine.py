from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
import logging

from src.config import settings
from src.db.models import Base

logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(settings.database_url, echo=False, pool_size=5, max_overflow=10)

AsyncSessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def dispose_engine():
    logger.info("Disposing engine")
    await engine.dispose()
    logger.info("Engine disposed")

async def create_db_and_tables():
    logger.info("Creating database and tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database and tables created")