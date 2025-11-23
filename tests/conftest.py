"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def sample_fixture() -> str:
    """Sample fixture for testing."""
    return "test_data"


@pytest.fixture(autouse=True)
def mock_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock database initialization for all tests."""

    # Mock init_db to prevent actual database connections during tests
    async def mock_init_db() -> None:
        """Mock database initialization."""
        pass

    monkeypatch.setattr("sark.db.session.init_db", mock_init_db)


@pytest.fixture(autouse=True)
def mock_db_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock database engines to prevent connection attempts."""
    mock_engine = MagicMock()
    mock_engine.begin = AsyncMock()

    def mock_get_postgres_engine() -> MagicMock:
        return mock_engine

    def mock_get_timescale_engine() -> MagicMock:
        return mock_engine

    monkeypatch.setattr("sark.db.session.get_postgres_engine", mock_get_postgres_engine)
    monkeypatch.setattr("sark.db.session.get_timescale_engine", mock_get_timescale_engine)


@pytest.fixture
async def db_session() -> AsyncMock:
    """Mock database session for tests."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    session.close = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()

    yield session

    await session.close()


@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client for tests."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    redis.keys = AsyncMock(return_value=[])
    redis.mget = AsyncMock(return_value=[])
    redis.mset = AsyncMock(return_value=True)
    redis.pipeline = MagicMock(return_value=MagicMock(
        execute=AsyncMock(return_value=[]),
        get=MagicMock(),
        set=MagicMock(),
        delete=MagicMock(),
    ))
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()

    return redis


@pytest.fixture
def opa_client() -> MagicMock:
    """Mock OPA client for tests."""
    client = MagicMock()
    client.evaluate_policy = AsyncMock()
    client.evaluate_policy_batch = AsyncMock(return_value=[])
    client.check_tool_access = AsyncMock()
    client.check_server_registration = AsyncMock()
    client.invalidate_cache = AsyncMock(return_value=0)
    client.get_cache_metrics = MagicMock(return_value={})
    client.get_cache_size = AsyncMock(return_value=0)
    client.close = AsyncMock()
    client.health_check = AsyncMock(return_value={"opa": True, "cache": True, "overall": True})
    client.authorize = AsyncMock(return_value=True)

    return client
