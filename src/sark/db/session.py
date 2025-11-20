"""Database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from sark.config import get_settings

settings = get_settings()

# PostgreSQL engine for main database
postgres_engine: AsyncEngine = create_async_engine(
    settings.postgres_dsn,
    pool_size=settings.postgres_pool_size,
    max_overflow=settings.postgres_max_overflow,
    echo=settings.debug,
)

# TimescaleDB engine for audit database
timescale_engine: AsyncEngine = create_async_engine(
    settings.timescale_dsn,
    pool_size=settings.postgres_pool_size,
    max_overflow=settings.postgres_max_overflow,
    echo=settings.debug,
)

# Session factories
AsyncSessionLocal = sessionmaker(
    postgres_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AsyncTimescaleSessionLocal = sessionmaker(
    timescale_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for main PostgreSQL database."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_timescale_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for TimescaleDB audit database."""
    async with AsyncTimescaleSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    from sark.db.base import Base

    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with timescale_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
