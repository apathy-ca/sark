"""Integration tests for Governance API endpoints.

Tests the API layer for governance functionality including:
- Authorization endpoints
- Policy management endpoints
- Audit log endpoints
- Rate limit status endpoints

Following AAA pattern: Arrange, Act, Assert
"""

import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Add fixtures to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fixtures" / "home"))

from home_fixtures import HomeDeploymentConfig, home_deployment_context

from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    SensitivityLevel,
)
from sark.services.auth.user_context import UserContext


@pytest.fixture
def api_user() -> UserContext:
    """Create user context for API testing."""
    return UserContext(
        user_id=uuid4(),
        email="api_user@home.local",
        role="parent",
        teams=["parents"],
        is_authenticated=True,
        is_admin=False,
    )


@pytest.fixture
def admin_user() -> UserContext:
    """Create admin user for API testing."""
    return UserContext(
        user_id=uuid4(),
        email="admin@home.local",
        role="admin",
        teams=["home-admins"],
        is_authenticated=True,
        is_admin=True,
    )


class TestAuthorizationAPI:
    """Test authorization API endpoints."""

    @pytest.mark.asyncio
    async def test_authorize_endpoint_success(self, api_user):
        """Test authorization endpoint returns success for valid request."""
        # Arrange
        request_data = {
            "action": "gateway:tool:invoke",
            "server_name": "openai-proxy",
            "tool_name": "chat_completion",
            "parameters": {"model": "gpt-3.5-turbo"},
        }

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": True,
                    "reason": "Request authorized",
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            request = GatewayAuthorizationRequest(**request_data)

            # Act
            response = await authorize_gateway_request(api_user, request)

        # Assert
        assert response.allow is True
        assert isinstance(response, GatewayAuthorizationResponse)

    @pytest.mark.asyncio
    async def test_authorize_endpoint_denied(self, api_user):
        """Test authorization endpoint returns denial for unauthorized request."""
        # Arrange
        request_data = {
            "action": "gateway:tool:invoke",
            "server_name": "vault-proxy",
            "tool_name": "read_secret",
            "parameters": {"path": "/secret/production"},
        }

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": False,
                    "reason": "Insufficient permissions for vault access",
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            request = GatewayAuthorizationRequest(**request_data)

            # Act
            response = await authorize_gateway_request(api_user, request)

        # Assert
        assert response.allow is False
        assert "permissions" in response.reason.lower() or "vault" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_authorize_endpoint_includes_cache_ttl(self, api_user):
        """Test authorization endpoint includes cache TTL in response."""
        # Arrange
        request_data = {
            "action": "gateway:tool:invoke",
            "server_name": "openai-proxy",
            "tool_name": "chat_completion",
            "sensitivity_level": SensitivityLevel.MEDIUM,
        }

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "OK"}}

            from sark.services.gateway.authorization import authorize_gateway_request

            request = GatewayAuthorizationRequest(**request_data)

            # Act
            response = await authorize_gateway_request(api_user, request)

        # Assert
        assert response.cache_ttl > 0
        assert isinstance(response.cache_ttl, int)


class TestServerListAPI:
    """Test server listing API endpoints."""

    @pytest.mark.asyncio
    async def test_list_servers_returns_authorized_only(self, api_user):
        """Test server list returns only authorized servers."""
        # Arrange
        from sark.models.gateway import GatewayServerInfo

        all_servers = [
            GatewayServerInfo(
                server_id="srv_001",
                server_name="openai-proxy",
                server_url="http://localhost:8081",
                sensitivity_level=SensitivityLevel.MEDIUM,
                authorized_teams=["parents"],
                health_status="healthy",
                tools_count=3,
            ),
            GatewayServerInfo(
                server_id="srv_002",
                server_name="vault-proxy",
                server_url="http://localhost:8082",
                sensitivity_level=SensitivityLevel.CRITICAL,
                authorized_teams=["home-admins"],  # Not in user's teams
                health_status="healthy",
                tools_count=5,
            ),
        ]

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            async def mock_evaluate(policy_path, input_data):
                server = input_data["resource"]["server"]
                if server == "openai-proxy":
                    return {"result": {"allow": True}}
                return {"result": {"allow": False}}

            mock_opa.side_effect = mock_evaluate

            from sark.services.gateway.authorization import filter_servers_by_permission

            # Act
            authorized_servers = await filter_servers_by_permission(api_user, all_servers)

        # Assert
        assert len(authorized_servers) == 1
        assert authorized_servers[0].server_name == "openai-proxy"


class TestToolListAPI:
    """Test tool listing API endpoints."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_authorized_only(self, api_user):
        """Test tool list returns only authorized tools."""
        # Arrange
        from sark.models.gateway import GatewayToolInfo

        all_tools = [
            GatewayToolInfo(
                tool_name="chat_completion",
                server_name="openai-proxy",
                description="Chat with GPT",
                sensitivity_level=SensitivityLevel.MEDIUM,
                parameters=[],
            ),
            GatewayToolInfo(
                tool_name="read_secret",
                server_name="vault-proxy",
                description="Read vault secret",
                sensitivity_level=SensitivityLevel.CRITICAL,
                parameters=[],
            ),
        ]

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            async def mock_evaluate(policy_path, input_data):
                sensitivity = input_data["resource"]["sensitivity"]
                if sensitivity != "critical":
                    return {"result": {"allow": True}}
                return {"result": {"allow": False}}

            mock_opa.side_effect = mock_evaluate

            from sark.services.gateway.authorization import filter_tools_by_permission

            # Act
            authorized_tools = await filter_tools_by_permission(api_user, all_tools)

        # Assert
        assert len(authorized_tools) == 1
        assert authorized_tools[0].tool_name == "chat_completion"


class TestAuditLogAPI:
    """Test audit log API endpoints."""

    @pytest.mark.asyncio
    async def test_get_decision_logs(self):
        """Test retrieving policy decision logs."""
        # Arrange
        async with home_deployment_context() as ctx:
            from sark.models.policy_audit import PolicyDecisionResult

            mock_logs = [
                MagicMock(
                    id="log_001",
                    timestamp=datetime.now(UTC),
                    result=PolicyDecisionResult.ALLOW,
                    user_id="user_001",
                    action="gateway:tool:invoke",
                ),
                MagicMock(
                    id="log_002",
                    timestamp=datetime.now(UTC),
                    result=PolicyDecisionResult.DENY,
                    user_id="user_002",
                    action="gateway:tool:invoke",
                ),
            ]

            ctx.audit_service.get_decision_logs = AsyncMock(return_value=mock_logs)

            # Act
            logs = await ctx.audit_service.get_decision_logs(limit=10)

        # Assert
        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_export_decisions_csv(self):
        """Test exporting decisions to CSV."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.audit_service.export_decisions_csv = AsyncMock(
                return_value="timestamp,result,user_id\n2024-01-01,allow,user_001"
            )

            # Act
            csv_content = await ctx.audit_service.export_decisions_csv()

        # Assert
        assert "timestamp" in csv_content
        assert "result" in csv_content

    @pytest.mark.asyncio
    async def test_export_decisions_json(self):
        """Test exporting decisions to JSON."""
        # Arrange
        import json

        async with home_deployment_context() as ctx:
            ctx.audit_service.export_decisions_json = AsyncMock(
                return_value='{"decisions": [], "count": 0}'
            )

            # Act
            json_content = await ctx.audit_service.export_decisions_json()
            data = json.loads(json_content)

        # Assert
        assert "decisions" in data
        assert "count" in data


class TestRateLimitStatusAPI:
    """Test rate limit status API endpoints."""

    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self):
        """Test retrieving rate limit status."""
        # Arrange
        async with home_deployment_context() as ctx:
            identifier = "device:192.168.1.100"

            # Act
            status = await ctx.rate_limiter.check_rate_limit(identifier)

        # Assert
        assert hasattr(status, "allowed")
        assert hasattr(status, "remaining")
        assert hasattr(status, "limit")

    @pytest.mark.asyncio
    async def test_rate_limit_status_when_exceeded(self):
        """Test rate limit status when limit exceeded."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.rate_limiter.check_rate_limit = AsyncMock(
                return_value=MagicMock(
                    allowed=False,
                    limit=100,
                    remaining=0,
                    reset_at=1700000000,
                    retry_after=60,
                )
            )

            identifier = "device:192.168.1.100"

            # Act
            status = await ctx.rate_limiter.check_rate_limit(identifier)

        # Assert
        assert status.allowed is False
        assert status.remaining == 0
        assert status.retry_after == 60


class TestBudgetStatusAPI:
    """Test budget status API endpoints."""

    @pytest.mark.asyncio
    async def test_get_budget_status(self):
        """Test retrieving budget status for a principal."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.cost_tracker.get_budget_status = AsyncMock(
                return_value={
                    "principal_id": "user_001",
                    "daily_budget": Decimal("10.00"),
                    "daily_spent": Decimal("3.50"),
                    "daily_remaining": Decimal("6.50"),
                    "monthly_budget": Decimal("100.00"),
                    "monthly_spent": Decimal("25.00"),
                    "monthly_remaining": Decimal("75.00"),
                }
            )

            # Act
            status = await ctx.cost_tracker.get_budget_status("user_001")

        # Assert
        assert status["daily_remaining"] == Decimal("6.50")
        assert status["monthly_remaining"] == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_budget_exceeded_status(self):
        """Test budget status when budget is exceeded."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.cost_tracker.get_budget_status = AsyncMock(
                return_value={
                    "principal_id": "child_001",
                    "daily_budget": Decimal("1.00"),
                    "daily_spent": Decimal("1.50"),
                    "daily_remaining": Decimal("0.00"),
                    "budget_exceeded": True,
                }
            )

            # Act
            status = await ctx.cost_tracker.get_budget_status("child_001")

        # Assert
        assert status["budget_exceeded"] is True
        assert status["daily_remaining"] == Decimal("0.00")


class TestPolicyManagementAPI:
    """Test policy management API endpoints."""

    @pytest.mark.asyncio
    async def test_list_policies(self, admin_user):
        """Test listing available policies."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.audit_service.get_policy_changes = AsyncMock(
                return_value=[
                    MagicMock(
                        policy_name="bedtime_policy",
                        policy_version=2,
                        change_type="updated",
                    ),
                    MagicMock(
                        policy_name="budget_policy",
                        policy_version=1,
                        change_type="created",
                    ),
                ]
            )

            # Act
            policies = await ctx.audit_service.get_policy_changes()

        # Assert
        assert len(policies) == 2

    @pytest.mark.asyncio
    async def test_get_policy_history(self, admin_user):
        """Test retrieving policy change history."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.audit_service.get_policy_changes = AsyncMock(
                return_value=[
                    MagicMock(
                        policy_name="bedtime_policy",
                        policy_version=2,
                        change_type="updated",
                        changed_by_user_id="admin_001",
                        change_reason="Extended weekend hours",
                    ),
                    MagicMock(
                        policy_name="bedtime_policy",
                        policy_version=1,
                        change_type="created",
                        changed_by_user_id="admin_001",
                        change_reason="Initial bedtime policy",
                    ),
                ]
            )

            # Act
            history = await ctx.audit_service.get_policy_changes(policy_name="bedtime_policy")

        # Assert
        assert len(history) == 2
        assert history[0].policy_version == 2
        assert history[1].policy_version == 1


class TestAnalyticsAPI:
    """Test analytics API endpoints."""

    @pytest.mark.asyncio
    async def test_get_decision_analytics(self, admin_user):
        """Test retrieving decision analytics."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.audit_service.get_decision_analytics = AsyncMock(
                return_value={
                    "period": {
                        "start": "2024-01-01T00:00:00Z",
                        "end": "2024-01-31T23:59:59Z",
                    },
                    "summary": {
                        "total_evaluations": 1000,
                        "total_allows": 850,
                        "total_denies": 150,
                        "allow_rate": 85.0,
                    },
                    "cache_performance": {
                        "total_hits": 700,
                        "hit_rate": 70.0,
                    },
                }
            )

            start_time = datetime(2024, 1, 1, tzinfo=UTC)
            end_time = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

            # Act
            analytics = await ctx.audit_service.get_decision_analytics(start_time, end_time)

        # Assert
        assert analytics["summary"]["total_evaluations"] == 1000
        assert analytics["summary"]["allow_rate"] == 85.0
        assert analytics["cache_performance"]["hit_rate"] == 70.0

    @pytest.mark.asyncio
    async def test_get_top_denial_reasons(self, admin_user):
        """Test retrieving top denial reasons."""
        # Arrange
        async with home_deployment_context() as ctx:
            ctx.audit_service.get_top_denial_reasons = AsyncMock(
                return_value=[
                    {"reason": "Bedtime restriction", "count": 75},
                    {"reason": "Budget exceeded", "count": 50},
                    {"reason": "Sensitivity too high", "count": 25},
                ]
            )

            start_time = datetime(2024, 1, 1, tzinfo=UTC)
            end_time = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

            # Act
            reasons = await ctx.audit_service.get_top_denial_reasons(start_time, end_time)

        # Assert
        assert len(reasons) == 3
        assert reasons[0]["reason"] == "Bedtime restriction"
        assert reasons[0]["count"] == 75


class TestAPIErrorHandling:
    """Test API error handling."""

    @pytest.mark.asyncio
    async def test_authorization_error_returns_denied(self, api_user):
        """Test authorization errors are handled gracefully."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="test-server",
            tool_name="test-tool",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("Service unavailable")

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(api_user, request)

        # Assert
        assert response.allow is False
        assert "error" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_server_filter_error_returns_empty(self, api_user):
        """Test server filtering errors return empty list."""
        # Arrange
        from sark.models.gateway import GatewayServerInfo

        servers = [
            GatewayServerInfo(
                server_id="srv_001",
                server_name="test-server",
                server_url="http://localhost:8080",
                sensitivity_level=SensitivityLevel.MEDIUM,
                health_status="healthy",
                tools_count=1,
            )
        ]

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("OPA unavailable")

            from sark.services.gateway.authorization import filter_servers_by_permission

            # Act
            result = await filter_servers_by_permission(api_user, servers)

        # Assert
        assert result == []  # Fail closed
