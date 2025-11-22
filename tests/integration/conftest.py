"""
Shared fixtures for integration tests.

Provides common test fixtures including:
- Database sessions with cleanup
- Authenticated test clients
- Test users and servers
- OPA client configuration
- SIEM mocks
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sark.models.user import User
from sark.models.mcp_server import MCPServer, TransportType, SensitivityLevel
from sark.services.auth.jwt import JWTHandler
from sark.services.auth.api_key import APIKeyService
from sark.services.policy.opa_client import OPAClient


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
async def test_db():
    """
    Provide test database session with automatic cleanup.

    In a real implementation, this would:
    1. Create test database connection
    2. Run migrations
    3. Provide session
    4. Cleanup after test
    """
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.close = AsyncMock()

    yield session

    # Cleanup
    await session.close()


@pytest.fixture
async def test_audit_db():
    """
    Provide test TimescaleDB session for audit events.

    In a real implementation, this would:
    1. Create TimescaleDB connection
    2. Create hypertables
    3. Provide session
    4. Cleanup after test
    """
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.close = AsyncMock()

    yield session

    # Cleanup
    await session.close()


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def jwt_handler():
    """JWT handler for creating auth tokens."""
    return JWTHandler(
        secret_key="test-secret-key-for-integration-tests",
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )


@pytest.fixture
def api_key_service():
    """API key service for tests."""
    return APIKeyService(key_length=32)


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user():
    """Regular test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password_here",
        role="developer",
        is_active=True,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def admin_user():
    """Admin test user."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashed_password_here",
        role="admin",
        is_active=True,
        is_admin=True,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def test_user_token(jwt_handler, test_user):
    """Generate JWT token for test user."""
    return jwt_handler.create_access_token(user_id=test_user.id)


@pytest.fixture
def admin_token(jwt_handler, admin_user):
    """Generate JWT token for admin user."""
    return jwt_handler.create_access_token(user_id=admin_user.id)


@pytest.fixture
def auth_headers(test_user_token):
    """Generate authentication headers for test user."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Generate authentication headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


# ============================================================================
# Server Fixtures
# ============================================================================

@pytest.fixture
def test_server(test_user):
    """Sample MCP server for testing."""
    return MCPServer(
        id=uuid4(),
        name="test-server",
        description="Test MCP server for integration tests",
        transport=TransportType.HTTP,
        endpoint="http://example.com/mcp",
        sensitivity_level=SensitivityLevel.MEDIUM,
        owner_id=test_user.id,
        team_id=uuid4(),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def high_sensitivity_server(admin_user):
    """High-sensitivity MCP server for testing."""
    return MCPServer(
        id=uuid4(),
        name="secure-server",
        description="High-sensitivity server",
        transport=TransportType.HTTP,
        endpoint="http://secure.example.com/mcp",
        sensitivity_level=SensitivityLevel.HIGH,
        owner_id=admin_user.id,
        team_id=uuid4(),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def sample_server_data():
    """Sample server registration data."""
    return {
        "name": "test-server",
        "description": "Test MCP server",
        "transport": "http",
        "endpoint": "http://example.com/mcp",
        "sensitivity_level": "medium",
        "tools": [],
        "prompts": [],
        "resources": []
    }


# ============================================================================
# Policy Fixtures
# ============================================================================

@pytest.fixture
async def opa_client():
    """OPA client configured for test policies."""
    return OPAClient(base_url="http://localhost:8181")


@pytest.fixture
def allow_policy_response():
    """Mock OPA response that allows the action."""
    return {"result": {"allow": True}}


@pytest.fixture
def deny_policy_response():
    """Mock OPA response that denies the action."""
    return {
        "result": {
            "allow": False,
            "reason": "Insufficient permissions"
        }
    }


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
async def async_client():
    """
    FastAPI TestClient for API requests.

    In a real implementation, this would:
    1. Create FastAPI app instance
    2. Override dependencies with test versions
    3. Create AsyncClient
    4. Cleanup after test
    """
    # Mock client for testing
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    client.patch = AsyncMock()

    yield client

    # Cleanup
    # In real implementation: await client.aclose()


# ============================================================================
# Audit/SIEM Fixtures
# ============================================================================

@pytest.fixture
def mock_splunk_client():
    """Mock Splunk HEC client."""
    client = MagicMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def mock_datadog_client():
    """Mock Datadog Logs API client."""
    client = MagicMock()
    client.post = AsyncMock()
    return client


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication test"
    )
    config.addinivalue_line(
        "markers", "policy: mark test as policy enforcement test"
    )
    config.addinivalue_line(
        "markers", "siem: mark test as SIEM integration test"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API endpoint test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running (>5 seconds)"
    )
    config.addinivalue_line(
        "markers", "requires_opa: mark test as requiring OPA service"
    )
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring database"
    )
