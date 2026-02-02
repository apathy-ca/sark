"""Pytest configuration and fixtures for benchmark tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def db_session():
    """Mock database session for benchmark tests.

    This provides a sync fixture compatible with benchmark tests
    that use synchronous fixtures.
    """
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
    )
    session.close = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()

    return session
