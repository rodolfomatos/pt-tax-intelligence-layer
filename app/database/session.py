import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = None
async_session_maker = None


def get_engine():
    """
    Get or create SQLAlchemy async engine.
    
    Creates a new async engine connecting to PostgreSQL if not already created.
    Uses connection pooling (pool_size=10, max_overflow=20) for concurrent requests.
    Replaces postgresql:// prefix with postgresql+asyncpg:// for async driver.
    
    Returns:
        SQLAlchemy AsyncEngine instance
    """
    global engine
    if engine is None:
        db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(
            db_url,
            echo=settings.log_level == "DEBUG",
            pool_size=10,
            max_overflow=20,
        )
    return engine


def get_async_session_maker():
    global async_session_maker
    if async_session_maker is None:
        async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_session_maker


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database tables."""
    from app.database.models import Base
    from app.data.memory.graph.models import Base as GraphBase
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(GraphBase.metadata.create_all)
    logger.info("Database tables created")


async def close_db():
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()
