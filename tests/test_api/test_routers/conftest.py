"""Pytest configuration for router tests."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from sark.api.dependencies import UserContext as UserContextAPI, get_current_user as get_current_user_api
from sark.services.auth import UserContext as UserContextAuth, get_current_user as get_current_user_auth
from sark.db import get_db
from sark.main import app


# Mock user contexts for testing - API dependencies version
def override_get_current_user_admin_api():
    """Override get_current_user (API) to return admin user."""
    return UserContextAPI({
        "user_id": "test-admin-123",
        "email": "admin@example.com",
        "name": "Test Admin",
        "roles": ["admin"],
        "teams": ["admin-team"],
        "permissions": ["*"],
    })


def override_get_current_user_api_regular():
    """Override get_current_user (API) to return regular user."""
    return UserContextAPI({
        "user_id": "test-user-123",
        "email": "user@example.com",
        "name": "Test User",
        "roles": ["user"],
        "teams": ["user-team"],
        "permissions": [],
    })


# Mock user contexts - services/auth version
async def override_get_current_user_admin_auth():
    """Override get_current_user (auth) to return admin user."""
    from uuid import uuid4
    return UserContextAuth(
        user_id=uuid4(),
        email="admin@example.com",
        role="admin",
        teams=["admin-team"],
        is_authenticated=True,
        is_admin=True,
    )


async def override_get_current_user_auth_regular():
    """Override get_current_user (auth) to return regular user."""
    from uuid import uuid4
    return UserContextAuth(
        user_id=uuid4(),
        email="user@example.com",
        role="user",
        teams=["user-team"],
        is_authenticated=True,
        is_admin=False,
    )


async def override_get_db():
    """Override get_db to return a mock database session."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    yield mock_session


@pytest.fixture
def client():
    """Create a test client with dependency overrides."""
    # Override authentication to return admin user by default
    # Override BOTH versions of get_current_user (from different modules)
    app.dependency_overrides[get_current_user_api] = override_get_current_user_admin_api
    app.dependency_overrides[get_current_user_auth] = override_get_current_user_admin_auth

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def client_user():
    """Create a test client with regular user auth."""
    # Override BOTH versions of get_current_user (from different modules)
    app.dependency_overrides[get_current_user_api] = override_get_current_user_api_regular
    app.dependency_overrides[get_current_user_auth] = override_get_current_user_auth_regular

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()
