"""Unit tests for allowlist-style authorization functionality.

These tests cover the authorization filtering mechanisms that control
which servers and tools a user can access, similar to allowlist functionality
in home deployment scenarios.

Following AAA pattern: Arrange, Act, Assert
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from sark.models.gateway import (
    GatewayServerInfo,
    GatewayToolInfo,
    SensitivityLevel,
)
from sark.services.auth.user_context import UserContext


@pytest.fixture
def sample_user() -> UserContext:
    """Create sample user context."""
    return UserContext(
        user_id=uuid4(),
        email="test@example.com",
        role="developer",
        teams=["backend-team", "data-eng"],
        is_authenticated=True,
        is_admin=False,
    )


@pytest.fixture
def admin_user() -> UserContext:
    """Create admin user context."""
    return UserContext(
        user_id=uuid4(),
        email="admin@example.com",
        role="admin",
        teams=["admin-team"],
        is_authenticated=True,
        is_admin=True,
    )


@pytest.fixture
def sample_servers() -> list[GatewayServerInfo]:
    """Create list of sample servers."""
    return [
        GatewayServerInfo(
            server_id="srv_postgres",
            server_name="postgres-mcp",
            server_url="http://postgres-mcp:8080",
            sensitivity_level=SensitivityLevel.HIGH,
            authorized_teams=["backend-team", "data-eng"],
            health_status="healthy",
            tools_count=15,
        ),
        GatewayServerInfo(
            server_id="srv_redis",
            server_name="redis-mcp",
            server_url="http://redis-mcp:8080",
            sensitivity_level=SensitivityLevel.MEDIUM,
            authorized_teams=["backend-team"],
            health_status="healthy",
            tools_count=5,
        ),
        GatewayServerInfo(
            server_id="srv_secret",
            server_name="vault-mcp",
            server_url="http://vault-mcp:8080",
            sensitivity_level=SensitivityLevel.CRITICAL,
            authorized_teams=["security-team"],
            health_status="healthy",
            tools_count=8,
        ),
    ]


@pytest.fixture
def sample_tools() -> list[GatewayToolInfo]:
    """Create list of sample tools."""
    return [
        GatewayToolInfo(
            tool_name="execute_query",
            server_name="postgres-mcp",
            description="Execute SQL query",
            sensitivity_level=SensitivityLevel.HIGH,
            parameters=[
                {"name": "query", "type": "string", "required": True},
            ],
            required_capabilities=["database:read"],
        ),
        GatewayToolInfo(
            tool_name="get_cache",
            server_name="redis-mcp",
            description="Get value from cache",
            sensitivity_level=SensitivityLevel.LOW,
            parameters=[
                {"name": "key", "type": "string", "required": True},
            ],
            required_capabilities=["cache:read"],
        ),
        GatewayToolInfo(
            tool_name="read_secret",
            server_name="vault-mcp",
            description="Read secret from vault",
            sensitivity_level=SensitivityLevel.CRITICAL,
            parameters=[
                {"name": "path", "type": "string", "required": True},
            ],
            required_capabilities=["secrets:read"],
        ),
    ]


class TestUserContextAllowlist:
    """Test user context team membership (allowlist-like behavior)."""

    def test_user_in_team_returns_true(self, sample_user):
        """Test in_team returns True for team member."""
        # Arrange
        user = sample_user

        # Act
        result = user.in_team("backend-team")

        # Assert
        assert result is True

    def test_user_not_in_team_returns_false(self, sample_user):
        """Test in_team returns False for non-member."""
        # Arrange
        user = sample_user

        # Act
        result = user.in_team("security-team")

        # Assert
        assert result is False

    def test_user_has_any_team_returns_true(self, sample_user):
        """Test has_any_team returns True when user is in any of the teams."""
        # Arrange
        user = sample_user
        authorized_teams = ["admin-team", "backend-team", "frontend-team"]

        # Act
        result = user.has_any_team(authorized_teams)

        # Assert
        assert result is True

    def test_user_has_any_team_returns_false(self, sample_user):
        """Test has_any_team returns False when user is in none of the teams."""
        # Arrange
        user = sample_user
        authorized_teams = ["security-team", "ops-team"]

        # Act
        result = user.has_any_team(authorized_teams)

        # Assert
        assert result is False

    def test_admin_has_role_returns_true(self, admin_user):
        """Test admin user has_role returns True for any role."""
        # Arrange
        user = admin_user

        # Act & Assert
        assert user.has_role("developer") is True
        assert user.has_role("admin") is True
        assert user.has_role("viewer") is True


class TestServerFiltering:
    """Test server filtering by team membership (allowlist)."""

    @pytest.mark.asyncio
    async def test_filter_servers_returns_authorized_only(self, sample_user, sample_servers):
        """Test filter_servers_by_permission returns only authorized servers."""
        # Arrange
        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            # Configure mock to return True for authorized teams
            async def mock_evaluate(policy_path, input_data):
                user_teams = input_data["user"]["permissions"]
                server = input_data["resource"]["server"]
                # Simulate allowlist check
                if server == "postgres-mcp":
                    return {"result": {"allow": True}}
                elif server == "redis-mcp":
                    return {"result": {"allow": True}}
                else:
                    return {"result": {"allow": False}}

            mock_opa.side_effect = mock_evaluate

            from sark.services.gateway.authorization import filter_servers_by_permission

            # Override user permissions to match teams
            sample_user_dict = sample_user.model_copy()

            # Act
            result = await filter_servers_by_permission(sample_user, sample_servers)

        # Assert
        assert len(result) == 2
        server_names = [s.server_name for s in result]
        assert "postgres-mcp" in server_names
        assert "redis-mcp" in server_names
        assert "vault-mcp" not in server_names

    @pytest.mark.asyncio
    async def test_filter_servers_empty_on_error(self, sample_user, sample_servers):
        """Test filter_servers_by_permission returns empty list on error (fail closed)."""
        # Arrange
        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("OPA unavailable")

            from sark.services.gateway.authorization import filter_servers_by_permission

            # Act
            result = await filter_servers_by_permission(sample_user, sample_servers)

        # Assert
        assert result == []  # Fail closed


class TestToolFiltering:
    """Test tool filtering by permissions (allowlist)."""

    @pytest.mark.asyncio
    async def test_filter_tools_returns_authorized_only(self, sample_user, sample_tools):
        """Test filter_tools_by_permission returns only authorized tools."""
        # Arrange
        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            async def mock_evaluate(policy_path, input_data):
                tool = input_data["resource"]["tool"]
                sensitivity = input_data["resource"]["sensitivity"]
                # Simulate: allow low/medium sensitivity, deny critical
                if sensitivity in ["low", "medium", "high"]:
                    return {"result": {"allow": True}}
                else:
                    return {"result": {"allow": False}}

            mock_opa.side_effect = mock_evaluate

            from sark.services.gateway.authorization import filter_tools_by_permission

            # Act
            result = await filter_tools_by_permission(sample_user, sample_tools)

        # Assert
        assert len(result) == 2
        tool_names = [t.tool_name for t in result]
        assert "execute_query" in tool_names
        assert "get_cache" in tool_names
        assert "read_secret" not in tool_names

    @pytest.mark.asyncio
    async def test_filter_tools_empty_on_error(self, sample_user, sample_tools):
        """Test filter_tools_by_permission returns empty list on error (fail closed)."""
        # Arrange
        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("OPA unavailable")

            from sark.services.gateway.authorization import filter_tools_by_permission

            # Act
            result = await filter_tools_by_permission(sample_user, sample_tools)

        # Assert
        assert result == []  # Fail closed


class TestAllowlistBypassForAdmin:
    """Test that admin users can bypass allowlist restrictions."""

    def test_admin_passes_all_role_checks(self, admin_user):
        """Test admin user passes any role check."""
        # Arrange
        user = admin_user

        # Act & Assert
        assert user.has_role("developer") is True
        assert user.has_role("viewer") is True
        assert user.has_role("custom_role") is True

    def test_admin_is_admin_flag(self, admin_user):
        """Test admin user has is_admin flag set."""
        # Arrange
        user = admin_user

        # Assert
        assert user.is_admin is True


class TestSensitivityLevelAllowlist:
    """Test sensitivity level based access control."""

    def test_sensitivity_levels_exist(self):
        """Test that all expected sensitivity levels exist."""
        # Assert
        assert SensitivityLevel.LOW.value == "low"
        assert SensitivityLevel.MEDIUM.value == "medium"
        assert SensitivityLevel.HIGH.value == "high"
        assert SensitivityLevel.CRITICAL.value == "critical"

    def test_server_has_sensitivity_level(self, sample_servers):
        """Test servers have sensitivity levels."""
        # Arrange
        servers = sample_servers

        # Assert
        postgres = next(s for s in servers if s.server_name == "postgres-mcp")
        vault = next(s for s in servers if s.server_name == "vault-mcp")

        assert postgres.sensitivity_level == SensitivityLevel.HIGH
        assert vault.sensitivity_level == SensitivityLevel.CRITICAL

    def test_tool_has_sensitivity_level(self, sample_tools):
        """Test tools have sensitivity levels."""
        # Arrange
        tools = sample_tools

        # Assert
        query_tool = next(t for t in tools if t.tool_name == "execute_query")
        cache_tool = next(t for t in tools if t.tool_name == "get_cache")
        secret_tool = next(t for t in tools if t.tool_name == "read_secret")

        assert query_tool.sensitivity_level == SensitivityLevel.HIGH
        assert cache_tool.sensitivity_level == SensitivityLevel.LOW
        assert secret_tool.sensitivity_level == SensitivityLevel.CRITICAL
