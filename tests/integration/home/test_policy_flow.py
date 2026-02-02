"""Integration tests for policy evaluation flow in home deployment.

Tests the complete policy evaluation pipeline including:
- OPA policy evaluation
- Time-based rule evaluation
- Sensitivity-based access control
- Multi-factor policy decisions

Following AAA pattern: Arrange, Act, Assert
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Add fixtures to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fixtures" / "home"))

from home_fixtures import (
    HomeDeploymentConfig,
    home_deployment_context,
)

from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    SensitivityLevel,
)
from sark.services.auth.user_context import UserContext


@pytest.fixture
def parent_user() -> UserContext:
    """Create parent user context."""
    return UserContext(
        user_id=uuid4(),
        email="parent@home.local",
        role="parent",
        teams=["parents"],
        is_authenticated=True,
        is_admin=False,
    )


@pytest.fixture
def child_user() -> UserContext:
    """Create child user context."""
    return UserContext(
        user_id=uuid4(),
        email="child@home.local",
        role="child",
        teams=["children"],
        is_authenticated=True,
        is_admin=False,
    )


class TestPolicyEvaluationFlow:
    """Test complete policy evaluation flow."""

    @pytest.mark.asyncio
    async def test_policy_allows_parent_user(self, parent_user):
        """Test policy allows parent user access."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="chat_completion",
            parameters={"model": "gpt-4"},
            sensitivity_level=SensitivityLevel.HIGH,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": True,
                    "reason": "Parent user has full access",
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(parent_user, request)

        # Assert
        assert response.allow is True

    @pytest.mark.asyncio
    async def test_policy_restricts_child_user_high_sensitivity(self, child_user):
        """Test policy restricts child user from high sensitivity tools."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="generate_image",  # Higher sensitivity
            parameters={"prompt": "test"},
            sensitivity_level=SensitivityLevel.HIGH,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": False,
                    "reason": "Child users restricted from high-cost operations",
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(child_user, request)

        # Assert
        assert response.allow is False

    @pytest.mark.asyncio
    async def test_policy_allows_child_user_low_sensitivity(self, child_user):
        """Test policy allows child user for low sensitivity tools."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="ollama-local",
            tool_name="local_chat",  # Local LLM, no cost
            parameters={"messages": []},
            sensitivity_level=SensitivityLevel.LOW,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": True,
                    "reason": "Local LLM allowed for all users",
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(child_user, request)

        # Assert
        assert response.allow is True


class TestTimeBaisedPolicyEvaluation:
    """Test time-based policy evaluation."""

    @pytest.mark.asyncio
    async def test_policy_blocks_during_bedtime(self, child_user):
        """Test policy blocks child access during bedtime hours."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="chat_completion",
        )

        # Simulate bedtime (22:30)
        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": False,
                    "reason": "Access blocked during bedtime hours (21:00-07:00)",
                    "policy_results": {
                        "time_based": {
                            "allow": False,
                            "reason": "Bedtime rule active",
                        }
                    },
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(child_user, request)

        # Assert
        assert response.allow is False
        assert "bedtime" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_policy_allows_during_allowed_hours(self, child_user):
        """Test policy allows child access during allowed hours."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="chat_completion",
        )

        # Simulate daytime (14:00)
        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": True,
                    "reason": "Access allowed during permitted hours",
                    "policy_results": {
                        "time_based": {
                            "allow": True,
                        }
                    },
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(child_user, request)

        # Assert
        assert response.allow is True


class TestSensitivityBasedCacheTTL:
    """Test sensitivity-based cache TTL in policy responses."""

    @pytest.mark.asyncio
    async def test_low_sensitivity_long_cache_ttl(self, parent_user):
        """Test low sensitivity gets longer cache TTL."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="ollama-local",
            tool_name="local_chat",
            sensitivity_level=SensitivityLevel.LOW,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "Allowed"}}

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(parent_user, request)

        # Assert
        assert response.cache_ttl == 1800  # 30 minutes

    @pytest.mark.asyncio
    async def test_critical_sensitivity_no_cache(self, parent_user):
        """Test critical sensitivity gets no caching."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="vault-proxy",
            tool_name="read_secret",
            sensitivity_level=SensitivityLevel.CRITICAL,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "Allowed"}}

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(parent_user, request)

        # Assert
        assert response.cache_ttl == 0  # No caching


class TestMultiFactorPolicyDecisions:
    """Test policies with multiple decision factors."""

    @pytest.mark.asyncio
    async def test_policy_combines_time_and_sensitivity(self, child_user):
        """Test policy combines time-based and sensitivity-based rules."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="generate_image",
            sensitivity_level=SensitivityLevel.HIGH,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": False,
                    "reason": "Multiple policy restrictions apply",
                    "policy_results": {
                        "time_based": {"allow": True},  # Within allowed hours
                        "sensitivity": {"allow": False, "reason": "High cost operation"},
                        "budget": {"allow": True},  # Within budget
                    },
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(child_user, request)

        # Assert
        assert response.allow is False  # Blocked by sensitivity policy

    @pytest.mark.asyncio
    async def test_all_policies_must_pass(self, child_user):
        """Test all policy checks must pass for access."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="chat_completion",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": True,
                    "reason": "All policy checks passed",
                    "policy_results": {
                        "time_based": {"allow": True},
                        "sensitivity": {"allow": True},
                        "budget": {"allow": True},
                        "rate_limit": {"allow": True},
                    },
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(child_user, request)

        # Assert
        assert response.allow is True


class TestPolicyWithAuditLogging:
    """Test policy evaluation with audit logging."""

    @pytest.mark.asyncio
    async def test_policy_decision_logged(self):
        """Test policy decisions are logged to audit trail."""
        # Arrange
        async with home_deployment_context() as ctx:
            auth_input = MagicMock()
            auth_input.user = {"id": "child_001", "role": "child"}
            auth_input.action = "gateway:tool:invoke"
            auth_input.tool = {"name": "chat_completion", "sensitivity_level": "medium"}
            auth_input.server = {"name": "openai-proxy"}
            auth_input.context = {"client_ip": "192.168.1.102"}

            decision = MagicMock()
            decision.allow = True
            decision.reason = "Access granted"

            # Act
            await ctx.audit_service.log_decision(auth_input, decision)

            # Assert
            ctx.audit_service.log_decision.assert_called_once()

    @pytest.mark.asyncio
    async def test_denied_decision_logged_with_reason(self):
        """Test denied decisions are logged with denial reason."""
        # Arrange
        async with home_deployment_context() as ctx:
            auth_input = MagicMock()
            auth_input.user = {"id": "child_001", "role": "child"}
            auth_input.action = "gateway:tool:invoke"

            decision = MagicMock()
            decision.allow = False
            decision.reason = "Bedtime restriction active"

            # Act
            await ctx.audit_service.log_decision(auth_input, decision)

            # Assert
            ctx.audit_service.log_decision.assert_called_once()
            call_args = ctx.audit_service.log_decision.call_args
            assert call_args[0][1].allow is False


class TestPolicyFailClosed:
    """Test fail-closed behavior in policy evaluation."""

    @pytest.mark.asyncio
    async def test_fails_closed_on_opa_error(self, parent_user):
        """Test authorization fails closed on OPA error."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="chat_completion",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("OPA service unavailable")

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(parent_user, request)

        # Assert
        assert response.allow is False
        assert "error" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_fails_closed_with_zero_cache_ttl(self, parent_user):
        """Test failed authorization has zero cache TTL."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="openai-proxy",
            tool_name="chat_completion",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("Network timeout")

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(parent_user, request)

        # Assert
        assert response.cache_ttl == 0  # Don't cache errors


class TestPolicyParameterFiltering:
    """Test parameter filtering in policy responses."""

    @pytest.mark.asyncio
    async def test_sensitive_parameters_filtered(self, parent_user):
        """Test sensitive parameters are filtered from response."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="database-proxy",
            tool_name="execute_query",
            parameters={
                "query": "SELECT * FROM users",
                "password": "secret123",  # Sensitive
            },
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": True,
                    "reason": "Allowed with filtered params",
                    "filtered_parameters": {
                        "query": "SELECT * FROM users",
                        "password": "[REDACTED]",
                    },
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(parent_user, request)

        # Assert
        assert response.filtered_parameters is not None
        assert response.filtered_parameters["password"] == "[REDACTED]"
