"""Unit tests for database session management."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from sark.db import session


@pytest.fixture(autouse=True)
def reset_engines():
    """Reset global engine instances before each test."""
    session._postgres_engine = None
    session._timescale_engine = None
    session._async_session_local = None
    session._async_timescale_session_local = None
    yield
    # Cleanup after test
    session._postgres_engine = None
    session._timescale_engine = None
    session._async_session_local = None
    session._async_timescale_session_local = None


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock()
    settings.postgres_dsn = "postgresql+asyncpg://user:pass@localhost:5432/sark"
    settings.timescale_dsn = "postgresql+asyncpg://user:pass@localhost:5432/sark_audit"
    settings.postgres_pool_size = 5
    settings.postgres_max_overflow = 10
    settings.postgres_pool_timeout = 30
    settings.postgres_pool_recycle = 3600
    settings.postgres_pool_pre_ping = True
    settings.postgres_echo_pool = False
    settings.debug = False
    return settings


class TestPostgresEngine:
    """Test PostgreSQL engine management."""

    def test_get_postgres_engine_creates_engine(self, mock_settings):
        """Test that get_postgres_engine creates a new engine if none exists."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                engine = session.get_postgres_engine()

                assert engine is mock_engine
                mock_create.assert_called_once()

    def test_get_postgres_engine_returns_singleton(self, mock_settings):
        """Test that get_postgres_engine returns the same instance on multiple calls."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                engine1 = session.get_postgres_engine()
                engine2 = session.get_postgres_engine()

                assert engine1 is engine2
                # Should only create once
                assert mock_create.call_count == 1

    def test_get_postgres_engine_configuration(self, mock_settings):
        """Test that PostgreSQL engine is configured with correct settings."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                session.get_postgres_engine()

                call_args = mock_create.call_args
                assert call_args[0][0] == "postgresql+asyncpg://user:pass@localhost:5432/sark"
                assert call_args[1]["pool_size"] == 5
                assert call_args[1]["max_overflow"] == 10
                assert call_args[1]["pool_timeout"] == 30
                assert call_args[1]["pool_recycle"] == 3600
                assert call_args[1]["pool_pre_ping"] is True
                assert call_args[1]["echo"] is False


class TestTimescaleEngine:
    """Test TimescaleDB engine management."""

    def test_get_timescale_engine_creates_engine(self, mock_settings):
        """Test that get_timescale_engine creates a new engine if none exists."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                engine = session.get_timescale_engine()

                assert engine is mock_engine
                mock_create.assert_called_once()

    def test_get_timescale_engine_returns_singleton(self, mock_settings):
        """Test that get_timescale_engine returns the same instance on multiple calls."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                engine1 = session.get_timescale_engine()
                engine2 = session.get_timescale_engine()

                assert engine1 is engine2
                assert mock_create.call_count == 1

    def test_get_timescale_engine_configuration(self, mock_settings):
        """Test that TimescaleDB engine is configured with correct settings."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                session.get_timescale_engine()

                call_args = mock_create.call_args
                assert call_args[0][0] == "postgresql+asyncpg://user:pass@localhost:5432/sark_audit"
                assert call_args[1]["pool_size"] == 5
                assert call_args[1]["max_overflow"] == 10


class TestSessionFactories:
    """Test session factory creation."""

    def test_get_session_factory_creates_factory(self, mock_settings):
        """Test that get_session_factory creates a new factory if none exists."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                factory = session.get_session_factory()

                assert factory is not None
                assert isinstance(factory, sessionmaker)

    def test_get_session_factory_returns_singleton(self, mock_settings):
        """Test that get_session_factory returns the same instance on multiple calls."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                factory1 = session.get_session_factory()
                factory2 = session.get_session_factory()

                assert factory1 is factory2

    def test_get_session_factory_configuration(self, mock_settings):
        """Test that session factory is configured correctly."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                factory = session.get_session_factory()

                # Verify factory produces AsyncSession instances
                assert factory.class_ == AsyncSession
                # Check expire_on_commit setting
                assert factory.kw.get("expire_on_commit") is False

    def test_get_timescale_session_factory_creates_factory(self, mock_settings):
        """Test that get_timescale_session_factory creates a new factory if none exists."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                factory = session.get_timescale_session_factory()

                assert factory is not None
                assert isinstance(factory, sessionmaker)

    def test_get_timescale_session_factory_returns_singleton(self, mock_settings):
        """Test that get_timescale_session_factory returns the same instance on multiple calls."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                factory1 = session.get_timescale_session_factory()
                factory2 = session.get_timescale_session_factory()

                assert factory1 is factory2


class TestGetDB:
    """Test get_db session generator."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self, mock_settings):
        """Test that get_db yields a database session."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                with patch("sark.db.session.get_session_factory") as mock_factory_getter:
                    mock_session = AsyncMock(spec=AsyncSession)
                    mock_session.commit = AsyncMock()
                    mock_session.close = AsyncMock()

                    mock_factory = Mock()
                    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_factory.return_value.__aexit__ = AsyncMock()
                    mock_factory_getter.return_value = mock_factory

                    # Use the generator
                    async for db in session.get_db():
                        assert db is mock_session

    @pytest.mark.asyncio
    async def test_get_db_commits_on_success(self, mock_settings):
        """Test that get_db commits the session on successful completion."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                with patch("sark.db.session.get_session_factory") as mock_factory_getter:
                    mock_session = AsyncMock(spec=AsyncSession)
                    mock_session.commit = AsyncMock()
                    mock_session.close = AsyncMock()
                    mock_session.rollback = AsyncMock()

                    mock_factory = Mock()
                    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
                    mock_factory_getter.return_value = mock_factory

                    # Use the generator normally (no exception)
                    async for _db in session.get_db():
                        pass

                    mock_session.commit.assert_called()
                    mock_session.rollback.assert_not_called()
                    mock_session.close.assert_called()

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_exception(self, mock_settings):
        """Test that get_db rolls back the session on exception."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                with patch("sark.db.session.get_session_factory") as mock_factory_getter:
                    mock_session = AsyncMock(spec=AsyncSession)
                    mock_session.commit = AsyncMock()
                    mock_session.close = AsyncMock()
                    mock_session.rollback = AsyncMock()

                    # Simulate exception during context
                    mock_factory = Mock()
                    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)

                    async def mock_aexit(exc_type, exc_val, exc_tb):
                        if exc_type:
                            await mock_session.rollback()
                        return False

                    mock_factory.return_value.__aexit__ = mock_aexit
                    mock_factory_getter.return_value = mock_factory

                    # Use the generator and raise exception
                    try:
                        async for _db in session.get_db():
                            raise ValueError("Test exception")
                    except ValueError:
                        pass

                    # Rollback should be called due to exception
                    mock_session.rollback.assert_called()


class TestGetTimescaleDB:
    """Test get_timescale_db session generator."""

    @pytest.mark.asyncio
    async def test_get_timescale_db_yields_session(self, mock_settings):
        """Test that get_timescale_db yields a database session."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                with patch("sark.db.session.get_timescale_session_factory") as mock_factory_getter:
                    mock_session = AsyncMock(spec=AsyncSession)
                    mock_session.commit = AsyncMock()
                    mock_session.close = AsyncMock()

                    mock_factory = Mock()
                    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_factory.return_value.__aexit__ = AsyncMock()
                    mock_factory_getter.return_value = mock_factory

                    # Use the generator
                    async for db in session.get_timescale_db():
                        assert db is mock_session

    @pytest.mark.asyncio
    async def test_get_timescale_db_commits_on_success(self, mock_settings):
        """Test that get_timescale_db commits the session on successful completion."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine"):
                with patch("sark.db.session.get_timescale_session_factory") as mock_factory_getter:
                    mock_session = AsyncMock(spec=AsyncSession)
                    mock_session.commit = AsyncMock()
                    mock_session.close = AsyncMock()
                    mock_session.rollback = AsyncMock()

                    mock_factory = Mock()
                    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
                    mock_factory_getter.return_value = mock_factory

                    # Use the generator normally
                    async for _db in session.get_timescale_db():
                        pass

                    mock_session.commit.assert_called()
                    mock_session.rollback.assert_not_called()


class TestInitDB:
    """Test database initialization."""

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self, mock_settings):
        """Test that init_db creates all database tables."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create_engine:
                # Mock engines
                mock_pg_engine = AsyncMock(spec=AsyncEngine)
                mock_ts_engine = AsyncMock(spec=AsyncEngine)

                def engine_factory(dsn, **kwargs):
                    if "sark_audit" in dsn:
                        return mock_ts_engine
                    return mock_pg_engine

                mock_create_engine.side_effect = engine_factory

                # Mock begin context managers
                mock_pg_conn = AsyncMock()
                mock_pg_conn.run_sync = AsyncMock()
                mock_pg_engine.begin = AsyncMock()
                mock_pg_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_pg_conn)
                mock_pg_engine.begin.return_value.__aexit__ = AsyncMock()

                mock_ts_conn = AsyncMock()
                mock_ts_conn.run_sync = AsyncMock()
                mock_ts_engine.begin = AsyncMock()
                mock_ts_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_ts_conn)
                mock_ts_engine.begin.return_value.__aexit__ = AsyncMock()

                # Run init_db
                await session.init_db()

                # Verify both engines created tables
                mock_pg_conn.run_sync.assert_called_once()
                mock_ts_conn.run_sync.assert_called_once()


class TestEngineLifecycle:
    """Test engine lifecycle management."""

    def test_engines_created_lazily(self, mock_settings):
        """Test that engines are created lazily (on first access)."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            # Engines don't exist initially
            assert session._postgres_engine is None
            assert session._timescale_engine is None

            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                # Create engines
                pg_engine = session.get_postgres_engine()
                ts_engine = session.get_timescale_engine()

                assert pg_engine is not None
                assert ts_engine is not None
                assert session._postgres_engine is pg_engine
                assert session._timescale_engine is ts_engine

    def test_session_factories_use_correct_engines(self, mock_settings):
        """Test that session factories use the correct engines."""
        with patch("sark.db.session.get_settings", return_value=mock_settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_pg_engine = Mock(spec=AsyncEngine)
                mock_ts_engine = Mock(spec=AsyncEngine)

                def engine_factory(dsn, **kwargs):
                    if "sark_audit" in dsn:
                        return mock_ts_engine
                    return mock_pg_engine

                mock_create.side_effect = engine_factory

                pg_factory = session.get_session_factory()
                ts_factory = session.get_timescale_session_factory()

                # Verify factories use correct engines
                assert pg_factory.kw["bind"] == mock_pg_engine
                assert ts_factory.kw["bind"] == mock_ts_engine


class TestDebugMode:
    """Test engine behavior in debug mode."""

    def test_engine_echo_in_debug_mode(self):
        """Test that engine echo is enabled in debug mode."""
        settings = Mock()
        settings.postgres_dsn = "postgresql+asyncpg://user:pass@localhost:5432/sark"
        settings.timescale_dsn = "postgresql+asyncpg://user:pass@localhost:5432/sark_audit"
        settings.postgres_pool_size = 5
        settings.postgres_max_overflow = 10
        settings.postgres_pool_timeout = 30
        settings.postgres_pool_recycle = 3600
        settings.postgres_pool_pre_ping = True
        settings.postgres_echo_pool = True
        settings.debug = True  # Debug mode enabled

        with patch("sark.db.session.get_settings", return_value=settings):
            with patch("sark.db.session.create_async_engine") as mock_create:
                mock_engine = Mock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                session.get_postgres_engine()

                call_args = mock_create.call_args
                assert call_args[1]["echo"] is True  # Should echo SQL in debug mode
                assert call_args[1]["echo_pool"] is True
