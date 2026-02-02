"""Unit tests for policy enforcement via Gateway authorization.

These tests cover:
- Gateway request authorization
- Agent-to-agent (A2A) authorization
- Enforcement restrictions (cross-environment, delegation depth, capabilities)
- Fail-closed behavior

Following AAA pattern: Arrange, Act, Assert
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from sark.models.gateway import (
    A2AAuthorizationRequest,
    AgentContext,
    AgentType,
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    SensitivityLevel,
    TrustLevel,
)
from sark.services.auth.user_context import UserContext


@pytest.fixture
def sample_user() -> UserContext:
    """Create sample user context."""
    return UserContext(
        user_id=uuid4(),
        email="developer@example.com",
        role="developer",
        teams=["backend-team"],
        is_authenticated=True,
        is_admin=False,
    )


@pytest.fixture
def trusted_agent() -> AgentContext:
    """Create trusted agent context."""
    return AgentContext(
        agent_id="agent_trusted_001",
        agent_type=AgentType.SERVICE,
        trust_level=TrustLevel.TRUSTED,
        capabilities=["execute", "query", "delegate"],
        environment="production",
        rate_limited=False,
    )


@pytest.fixture
def untrusted_agent() -> AgentContext:
    """Create untrusted agent context."""
    return AgentContext(
        agent_id="agent_untrusted_001",
        agent_type=AgentType.WORKER,
        trust_level=TrustLevel.UNTRUSTED,
        capabilities=["query"],
        environment="development",
        rate_limited=True,
    )


class TestGatewayAuthorization:
    """Test gateway request authorization."""

    @pytest.mark.asyncio
    async def test_authorize_gateway_request_allowed(self, sample_user):
        """Test gateway authorization returns allow when policy permits."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT 1"},
            sensitivity_level=SensitivityLevel.MEDIUM,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": True,
                    "reason": "User has required permissions",
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(sample_user, request)

        # Assert
        assert response.allow is True
        assert "permissions" in response.reason

    @pytest.mark.asyncio
    async def test_authorize_gateway_request_denied(self, sample_user):
        """Test gateway authorization returns deny when policy denies."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="vault-mcp",
            tool_name="read_secret",
            parameters={"path": "/secret/production"},
            sensitivity_level=SensitivityLevel.CRITICAL,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {
                "result": {
                    "allow": False,
                    "reason": "User lacks required permissions for critical resources",
                }
            }

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(sample_user, request)

        # Assert
        assert response.allow is False
        assert "critical" in response.reason.lower() or "permissions" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_authorize_gateway_fails_closed_on_error(self, sample_user):
        """Test gateway authorization denies on OPA error (fail closed)."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="postgres-mcp",
            tool_name="execute_query",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("OPA service unavailable")

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(sample_user, request)

        # Assert
        assert response.allow is False
        assert "error" in response.reason.lower()
        assert response.cache_ttl == 0  # No caching on error

    @pytest.mark.asyncio
    async def test_authorize_gateway_includes_cache_ttl(self, sample_user):
        """Test gateway authorization includes appropriate cache TTL."""
        # Arrange
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="redis-mcp",
            tool_name="get_cache",
            sensitivity_level=SensitivityLevel.LOW,
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "Allowed"}}

            from sark.services.gateway.authorization import authorize_gateway_request

            # Act
            response = await authorize_gateway_request(sample_user, request)

        # Assert
        assert response.cache_ttl > 0
        assert response.cache_ttl == 1800  # LOW sensitivity = 30 min


class TestA2AAuthorization:
    """Test agent-to-agent authorization."""

    @pytest.mark.asyncio
    async def test_a2a_authorization_allowed(self, trusted_agent):
        """Test A2A authorization allows trusted agent communication."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=trusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="execute",
            message_type="request",
            target_environment="production",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "A2A allowed"}}

            from sark.services.gateway.authorization import authorize_a2a_request

            # Act
            response = await authorize_a2a_request(trusted_agent, request)

        # Assert
        assert response.allow is True

    @pytest.mark.asyncio
    async def test_a2a_blocks_cross_environment_for_untrusted(self, untrusted_agent):
        """Test A2A blocks cross-environment communication for untrusted agents."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=untrusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="query",
            message_type="request",
            target_environment="production",  # Different from agent's "development"
        )

        from sark.services.gateway.authorization import authorize_a2a_request

        # Act
        response = await authorize_a2a_request(untrusted_agent, request)

        # Assert
        assert response.allow is False
        assert "untrusted" in response.reason.lower() or "environment" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_a2a_allows_same_environment_for_untrusted(self, untrusted_agent):
        """Test A2A allows same-environment communication for untrusted agents."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=untrusted_agent.agent_id,
            target_agent_id="agent_target_002",
            capability="query",
            message_type="request",
            target_environment="development",  # Same as agent's environment
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "A2A allowed"}}

            from sark.services.gateway.authorization import authorize_a2a_request

            # Act
            response = await authorize_a2a_request(untrusted_agent, request)

        # Assert
        assert response.allow is True

    @pytest.mark.asyncio
    async def test_a2a_blocks_missing_capability(self, untrusted_agent):
        """Test A2A blocks request when agent lacks required capability."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=untrusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="execute",  # Agent only has "query" capability
            message_type="request",
            target_environment="development",
        )

        from sark.services.gateway.authorization import authorize_a2a_request

        # Act
        response = await authorize_a2a_request(untrusted_agent, request)

        # Assert
        assert response.allow is False
        assert "capability" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_a2a_blocks_excessive_delegation_depth(self, trusted_agent):
        """Test A2A blocks requests with excessive delegation depth."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=trusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="delegate",
            message_type="request",
            target_environment="production",
            context={"delegation_depth": 5},  # Exceeds max of 2
        )

        from sark.services.gateway.authorization import authorize_a2a_request

        # Act
        response = await authorize_a2a_request(trusted_agent, request)

        # Assert
        assert response.allow is False
        assert "delegation" in response.reason.lower()

    @pytest.mark.asyncio
    async def test_a2a_allows_valid_delegation_depth(self, trusted_agent):
        """Test A2A allows requests with valid delegation depth."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=trusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="delegate",
            message_type="request",
            target_environment="production",
            context={"delegation_depth": 1},  # Within max of 2
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "A2A allowed"}}

            from sark.services.gateway.authorization import authorize_a2a_request

            # Act
            response = await authorize_a2a_request(trusted_agent, request)

        # Assert
        assert response.allow is True

    @pytest.mark.asyncio
    async def test_a2a_has_short_cache_ttl(self, trusted_agent):
        """Test A2A authorization has shorter cache TTL for security."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=trusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="query",
            message_type="request",
            target_environment="production",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.return_value = {"result": {"allow": True, "reason": "A2A allowed"}}

            from sark.services.gateway.authorization import authorize_a2a_request

            # Act
            response = await authorize_a2a_request(trusted_agent, request)

        # Assert
        assert response.cache_ttl == 60  # 1 minute for A2A

    @pytest.mark.asyncio
    async def test_a2a_fails_closed_on_error(self, trusted_agent):
        """Test A2A authorization denies on error (fail closed)."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=trusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="execute",
            message_type="request",
            target_environment="production",
        )

        with patch("sark.services.gateway.authorization.evaluate_policy") as mock_opa:
            mock_opa.side_effect = Exception("OPA service unavailable")

            from sark.services.gateway.authorization import authorize_a2a_request

            # Act
            response = await authorize_a2a_request(trusted_agent, request)

        # Assert
        assert response.allow is False
        assert "error" in response.reason.lower()
        assert response.cache_ttl == 0  # No caching on error


class TestA2ARestrictions:
    """Test A2A-specific enforcement restrictions."""

    @pytest.mark.asyncio
    async def test_enforce_a2a_restrictions_trusted_passes(self, trusted_agent):
        """Test trusted agent passes A2A restrictions."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=trusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="execute",
            message_type="request",
            target_environment="production",
        )

        from sark.services.gateway.authorization import _enforce_a2a_restrictions

        # Act
        result = await _enforce_a2a_restrictions(trusted_agent, request)

        # Assert
        assert result["allow"] is True

    @pytest.mark.asyncio
    async def test_enforce_a2a_restrictions_blocks_cross_env(self, untrusted_agent):
        """Test untrusted agent blocked from cross-environment."""
        # Arrange
        request = A2AAuthorizationRequest(
            source_agent_id=untrusted_agent.agent_id,
            target_agent_id="agent_target_001",
            capability="query",
            message_type="request",
            target_environment="production",  # Different from "development"
        )

        from sark.services.gateway.authorization import _enforce_a2a_restrictions

        # Act
        result = await _enforce_a2a_restrictions(untrusted_agent, request)

        # Assert
        assert result["allow"] is False
        assert "untrusted" in result["reason"].lower()


class TestTrustLevels:
    """Test trust level enforcement."""

    def test_trust_level_values(self):
        """Test trust level enum values."""
        # Assert
        assert TrustLevel.TRUSTED.value == "trusted"
        assert TrustLevel.LIMITED.value == "limited"
        assert TrustLevel.UNTRUSTED.value == "untrusted"

    def test_agent_type_values(self):
        """Test agent type enum values."""
        # Assert
        assert AgentType.SERVICE.value == "service"
        assert AgentType.WORKER.value == "worker"
        assert AgentType.QUERY.value == "query"


class TestGatewayAuthorizationRequest:
    """Test GatewayAuthorizationRequest validation."""

    def test_valid_action_gateway_tool_invoke(self):
        """Test valid action: gateway:tool:invoke."""
        # Arrange & Act
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="test-server",
            tool_name="test-tool",
        )

        # Assert
        assert request.action == "gateway:tool:invoke"

    def test_valid_action_gateway_server_list(self):
        """Test valid action: gateway:server:list."""
        # Arrange & Act
        request = GatewayAuthorizationRequest(
            action="gateway:server:list",
        )

        # Assert
        assert request.action == "gateway:server:list"

    def test_invalid_action_raises_error(self):
        """Test invalid action raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError):
            GatewayAuthorizationRequest(
                action="invalid:action",
                server_name="test-server",
            )


class TestGatewayAuthorizationResponse:
    """Test GatewayAuthorizationResponse model."""

    def test_response_allow_true(self):
        """Test response with allow=True."""
        # Arrange & Act
        response = GatewayAuthorizationResponse(
            allow=True,
            reason="User has required permissions",
            cache_ttl=300,
        )

        # Assert
        assert response.allow is True
        assert response.cache_ttl == 300

    def test_response_allow_false(self):
        """Test response with allow=False."""
        # Arrange & Act
        response = GatewayAuthorizationResponse(
            allow=False,
            reason="Access denied",
            cache_ttl=0,
        )

        # Assert
        assert response.allow is False
        assert response.cache_ttl == 0

    def test_response_with_filtered_parameters(self):
        """Test response includes filtered parameters."""
        # Arrange & Act
        response = GatewayAuthorizationResponse(
            allow=True,
            reason="Allowed with filtered params",
            filtered_parameters={"query": "SELECT 1", "password": "[REDACTED]"},
            cache_ttl=60,
        )

        # Assert
        assert response.filtered_parameters is not None
        assert response.filtered_parameters["password"] == "[REDACTED]"
