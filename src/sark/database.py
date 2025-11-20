"""
Database connection utilities for SARK application.

This module provides PostgreSQL database connection management,
supporting both managed (Docker Compose) and external enterprise deployments.
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from sark.config import PostgreSQLConfig, ServiceMode

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manager for PostgreSQL database connections."""

    def __init__(self, config: PostgreSQLConfig):
        """
        Initialize database manager.

        Args:
            config: PostgreSQL configuration
        """
        self.config = config
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[sessionmaker] = None

        logger.info(
            f"Initialized DatabaseManager in {config.mode} mode: "
            f"host={config.host}, port={config.port}, database={config.database}"
        )

    @property
    def engine(self) -> Engine:
        """
        Get or create synchronous database engine.

        Returns:
            SQLAlchemy Engine instance
        """
        if self._engine is None:
            # Determine pool class based on configuration
            if self.config.pool_size == 0:
                poolclass = NullPool
                logger.info("Using NullPool (no connection pooling)")
            else:
                poolclass = QueuePool
                logger.info(
                    f"Using QueuePool (size={self.config.pool_size}, "
                    f"max_overflow={self.config.max_overflow})"
                )

            self._engine = create_engine(
                self.config.connection_string,
                poolclass=poolclass,
                pool_size=self.config.pool_size if poolclass == QueuePool else 0,
                max_overflow=self.config.max_overflow if poolclass == QueuePool else 0,
                pool_pre_ping=True,  # Verify connections before using
                echo=False,  # Set to True for SQL logging
            )
            logger.info(f"Created database engine: {self.config.host}:{self.config.port}")

        return self._engine

    @property
    def async_engine(self) -> AsyncEngine:
        """
        Get or create asynchronous database engine.

        Returns:
            SQLAlchemy AsyncEngine instance
        """
        if self._async_engine is None:
            # Convert connection string to async version
            async_url = self.config.connection_string.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

            # Determine pool class
            if self.config.pool_size == 0:
                poolclass = NullPool
            else:
                poolclass = QueuePool

            self._async_engine = create_async_engine(
                async_url,
                poolclass=poolclass,
                pool_size=self.config.pool_size if poolclass == QueuePool else 0,
                max_overflow=self.config.max_overflow if poolclass == QueuePool else 0,
                pool_pre_ping=True,
                echo=False,
            )
            logger.info(f"Created async database engine: {self.config.host}:{self.config.port}")

        return self._async_engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                class_=Session,
                expire_on_commit=False,
            )
        return self._session_factory

    @property
    def async_session_factory(self) -> sessionmaker:
        """Get or create async session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._async_session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session (context manager).

        Yields:
            SQLAlchemy Session instance

        Example:
            with db_manager.get_session() as session:
                result = session.execute(text("SELECT 1"))
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session (async context manager).

        Yields:
            SQLAlchemy AsyncSession instance

        Example:
            async with db_manager.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def test_connection(self) -> dict[str, Any]:
        """
        Test database connection and return diagnostic information.

        Returns:
            Dictionary containing connection test results
        """
        result = {
            "mode": self.config.mode.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "connected": False,
            "version": None,
            "error": None,
        }

        try:
            with self.get_session() as session:
                # Test connection with simple query
                query_result = session.execute(text("SELECT version()"))
                version = query_result.scalar()
                result["version"] = version
                result["connected"] = True
                logger.info(f"Database connection test successful: {version}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Database connection test failed: {e}")

        return result

    def health_check(self) -> bool:
        """
        Check if database is healthy and accessible.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database health check successful")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def close(self) -> None:
        """Close all database connections."""
        if self._engine is not None:
            self._engine.dispose()
            logger.info("Disposed synchronous database engine")
            self._engine = None

        if self._async_engine is not None:
            # Async engine disposal must be awaited, so we log a warning
            logger.warning("Async engine should be disposed asynchronously")
            self._async_engine = None

    async def async_close(self) -> None:
        """Close all database connections (async version)."""
        if self._async_engine is not None:
            await self._async_engine.dispose()
            logger.info("Disposed async database engine")
            self._async_engine = None

        if self._engine is not None:
            self._engine.dispose()
            logger.info("Disposed synchronous database engine")
            self._engine = None


def create_database_manager(config: Optional[PostgreSQLConfig] = None) -> Optional[DatabaseManager]:
    """
    Create a database manager instance.

    Args:
        config: PostgreSQL configuration (if None, loads from environment)

    Returns:
        DatabaseManager instance if database is enabled, None otherwise
    """
    if config is None:
        from sark.config import get_config

        app_config = get_config()
        config = app_config.postgres

    if not config.enabled:
        logger.info("PostgreSQL is not enabled")
        return None

    return DatabaseManager(config)


def verify_database_connectivity(config: Optional[PostgreSQLConfig] = None) -> bool:
    """
    Verify connectivity to PostgreSQL database.

    Args:
        config: PostgreSQL configuration (if None, loads from environment)

    Returns:
        True if database is accessible, False otherwise
    """
    manager = create_database_manager(config)
    if manager is None:
        return False

    try:
        return manager.health_check()
    finally:
        manager.close()
