"""Pytest configuration for router tests."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from sark.api.dependencies import UserContext as UserContextAPI, get_current_user as get_current_user_api
from sark.services.auth import UserContext as UserContextAuth, get_current_user as get_current_user_auth
from sark.db import get_db
from sark.api.main import app


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
def db_session():
    """Mock database session for tests that need to create objects."""
    mock_session = MagicMock()
    # Mock add and commit as no-ops
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.refresh = MagicMock()
    return mock_session


@pytest.fixture
def client():
    """Create a test client with dependency overrides."""
    # Remove auth and CSRF middleware for testing by rebuilding the middleware stack
    # Save original middleware
    original_middleware = app.user_middleware.copy()

    # Remove AuthMiddleware and CSRFProtectionMiddleware from the stack
    # CSRF requires SessionMiddleware which we don't configure in tests
    app.user_middleware = [
        m for m in app.user_middleware
        if not (hasattr(m, 'cls') and m.cls.__name__ in ('AuthMiddleware', 'CSRFProtectionMiddleware'))
    ]

    # Rebuild middleware stack
    app.middleware_stack = app.build_middleware_stack()

    # Override authentication to return admin user by default
    # Override BOTH versions of get_current_user (from different modules)
    app.dependency_overrides[get_current_user_api] = override_get_current_user_admin_api
    app.dependency_overrides[get_current_user_auth] = override_get_current_user_admin_auth
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    yield client

    # Clean up - restore original middleware
    app.user_middleware = original_middleware
    app.middleware_stack = app.build_middleware_stack()
    app.dependency_overrides.clear()


@pytest.fixture
def client_user():
    """Create a test client with regular user auth."""
    # Remove auth and CSRF middleware for testing
    original_middleware = app.user_middleware.copy()
    app.user_middleware = [
        m for m in app.user_middleware
        if not (hasattr(m, 'cls') and m.cls.__name__ in ('AuthMiddleware', 'CSRFProtectionMiddleware'))
    ]

    app.middleware_stack = app.build_middleware_stack()

    # Override BOTH versions of get_current_user (from different modules)
    app.dependency_overrides[get_current_user_api] = override_get_current_user_api_regular
    app.dependency_overrides[get_current_user_auth] = override_get_current_user_auth_regular
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    yield client

    # Clean up
    app.user_middleware = original_middleware
    app.middleware_stack = app.build_middleware_stack()
    app.dependency_overrides.clear()
