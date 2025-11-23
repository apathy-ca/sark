"""Database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from sark.config import get_settings

# Global engine instances (lazy-loaded)
_postgres_engine: AsyncEngine | None = None
_timescale_engine: AsyncEngine | None = None
_async_session_local: sessionmaker | None = None
_async_timescale_session_local: sessionmaker | None = None


def get_postgres_engine() -> AsyncEngine:
    """Get or create PostgreSQL engine with optimized connection pooling."""
    global _postgres_engine
    if _postgres_engine is None:
        settings = get_settings()
        _postgres_engine = create_async_engine(
            settings.postgres_dsn,
            # Connection pool settings
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
            pool_timeout=settings.postgres_pool_timeout,
            pool_recycle=settings.postgres_pool_recycle,
            pool_pre_ping=settings.postgres_pool_pre_ping,
            # Logging
            echo=settings.debug,
            echo_pool=settings.postgres_echo_pool,
            # Performance optimizations
            # Use prepared statements for better performance
            # executemany_mode="values_plus_batch",  # Async doesn't support this
        )
    return _postgres_engine


def get_timescale_engine() -> AsyncEngine:
    """Get or create TimescaleDB engine with optimized connection pooling."""
    global _timescale_engine
    if _timescale_engine is None:
        settings = get_settings()
        _timescale_engine = create_async_engine(
            settings.timescale_dsn,
            # Connection pool settings
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
            pool_timeout=settings.postgres_pool_timeout,
            pool_recycle=settings.postgres_pool_recycle,
            pool_pre_ping=settings.postgres_pool_pre_ping,
            # Logging
            echo=settings.debug,
            echo_pool=settings.postgres_echo_pool,
        )
    return _timescale_engine


def get_session_factory() -> sessionmaker:
    """Get or create session factory for main database."""
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = sessionmaker(
            get_postgres_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_local


def get_timescale_session_factory() -> sessionmaker:
    """Get or create session factory for TimescaleDB."""
    global _async_timescale_session_local
    if _async_timescale_session_local is None:
        _async_timescale_session_local = sessionmaker(
            get_timescale_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_timescale_session_local


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for main PostgreSQL database."""
    session_factory = get_session_factory()
    async with session_factory() as session:
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
    session_factory = get_timescale_session_factory()
    async with session_factory() as session:
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

    postgres_engine = get_postgres_engine()
    timescale_engine = get_timescale_engine()

    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with timescale_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
