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
