"""Pytest configuration for router tests."""

import pytest
from fastapi.testclient import TestClient

from sark.api.dependencies import UserContext, get_current_user
from sark.main import app


# Mock user context for testing
class MockUserContext(UserContext):
    """Mock user context for testing."""

    def __init__(self, role: str = "admin"):
        """Initialize mock user with specified role."""
        super().__init__({
            "user_id": "test-user-123",
            "email": "test@example.com",
            "name": "Test User",
            "roles": [role],
            "teams": ["test-team"],
            "permissions": ["*"],
        })


async def override_get_current_user_admin():
    """Override get_current_user to return admin user."""
    return MockUserContext(role="admin")


async def override_get_current_user():
    """Override get_current_user to return regular user."""
    return MockUserContext(role="user")


@pytest.fixture
def client():
    """Create a test client with dependency overrides."""
    # Override authentication to return admin user by default
    app.dependency_overrides[get_current_user] = override_get_current_user_admin

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def client_user():
    """Create a test client with regular user auth."""
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()
