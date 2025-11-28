"""Pytest fixtures for Gateway tests."""

import pytest
from typing import Dict, Any


# Mock models until real models are available from Engineer 1
class GatewayServerInfo:
    """Mock GatewayServerInfo model."""

    def __init__(
        self,
        server_id: str,
        server_name: str,
        server_url: str,
        sensitivity_level: str,
        health_status: str,
        tools_count: int,
    ):
        self.server_id = server_id
        self.server_name = server_name
        self.server_url = server_url
        self.sensitivity_level = sensitivity_level
        self.health_status = health_status
        self.tools_count = tools_count


class GatewayAuthorizationRequest:
    """Mock GatewayAuthorizationRequest model."""

    def __init__(
        self,
        action: str,
        server_name: str,
        tool_name: str,
        parameters: Dict[str, Any],
        gateway_metadata: Dict[str, Any],
    ):
        self.action = action
        self.server_name = server_name
        self.tool_name = tool_name
        self.parameters = parameters
        self.gateway_metadata = gateway_metadata


class UserContext:
    """Mock UserContext model."""

    def __init__(
        self, user_id: str, email: str, role: str, teams: list[str]
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.teams = teams


@pytest.fixture
def sample_gateway_server():
    """Sample Gateway server for testing."""
    return GatewayServerInfo(
        server_id="srv_test",
        server_name="test-server",
        server_url="http://localhost:8080",
        sensitivity_level="medium",
        health_status="healthy",
        tools_count=5,
    )


@pytest.fixture
def sample_authorization_request():
    """Sample authorization request for testing."""
    return GatewayAuthorizationRequest(
        action="gateway:tool:invoke",
        server_name="test-server",
        tool_name="test-tool",
        parameters={"param1": "value1"},
        gateway_metadata={"request_id": "req_123"},
    )


@pytest.fixture
def mock_user_context():
    """Mock user context for testing."""
    return UserContext(
        user_id="user_123",
        email="test@example.com",
        role="developer",
        teams=["team1"],
    )


@pytest.fixture
def sample_gateway_servers_list():
    """Sample list of Gateway servers."""
    return [
        GatewayServerInfo(
            server_id="srv_1",
            server_name="test-server-1",
            server_url="http://test1:8080",
            sensitivity_level="medium",
            health_status="healthy",
            tools_count=5,
        ),
        GatewayServerInfo(
            server_id="srv_2",
            server_name="test-server-2",
            server_url="http://test2:8080",
            sensitivity_level="high",
            health_status="healthy",
            tools_count=10,
        ),
    ]


@pytest.fixture
def admin_user_context():
    """Admin user context for testing."""
    return UserContext(
        user_id="admin_123",
        email="admin@example.com",
        role="admin",
        teams=["team1", "admin"],
    )


@pytest.fixture
def restricted_user_context():
    """Restricted user context for testing."""
    return UserContext(
        user_id="user_456",
        email="restricted@example.com",
        role="viewer",
        teams=["team2"],
    )
