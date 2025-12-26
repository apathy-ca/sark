"""Unit tests for Gateway data models."""

from datetime import datetime

from pydantic import ValidationError
import pytest

from sark.models.gateway import (
    A2AAuthorizationRequest,
    AgentContext,
    AgentType,
    GatewayAuditEvent,
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    GatewayServerInfo,
    GatewayToolInfo,
    SensitivityLevel,
    TrustLevel,
)


class TestSensitivityLevel:
    """Test SensitivityLevel enum."""

    def test_all_levels_defined(self):
        """Test all sensitivity levels are defined."""
        assert SensitivityLevel.LOW == "low"
        assert SensitivityLevel.MEDIUM == "medium"
        assert SensitivityLevel.HIGH == "high"
        assert SensitivityLevel.CRITICAL == "critical"


class TestGatewayServerInfo:
    """Test GatewayServerInfo model."""

    def test_valid_server_info(self):
        """Test creating valid server info."""
        server = GatewayServerInfo(
            server_id="srv_123",
            server_name="test-server",
            server_url="http://localhost:8080",
            health_status="healthy",
            tools_count=5,
        )
        assert server.server_id == "srv_123"
        assert server.server_name == "test-server"
        assert str(server.server_url) == "http://localhost:8080/"
        assert server.sensitivity_level == SensitivityLevel.MEDIUM
        assert server.health_status == "healthy"
        assert server.tools_count == 5

    def test_server_info_with_all_fields(self):
        """Test server info with all optional fields."""
        now = datetime.now()
        server = GatewayServerInfo(
            server_id="srv_123",
            server_name="test-server",
            server_url="http://localhost:8080",
            sensitivity_level=SensitivityLevel.HIGH,
            authorized_teams=["team1", "team2"],
            access_restrictions={"role": "admin"},
            health_status="healthy",
            tools_count=10,
            created_at=now,
            updated_at=now,
        )
        assert server.sensitivity_level == SensitivityLevel.HIGH
        assert server.authorized_teams == ["team1", "team2"]
        assert server.access_restrictions == {"role": "admin"}
        assert server.created_at == now
        assert server.updated_at == now

    def test_server_info_negative_tools_count(self):
        """Test that negative tools_count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GatewayServerInfo(
                server_id="srv_123",
                server_name="test-server",
                server_url="http://localhost:8080",
                health_status="healthy",
                tools_count=-1,
            )
        assert "tools_count" in str(exc_info.value)

    def test_server_info_invalid_url(self):
        """Test that invalid URL is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GatewayServerInfo(
                server_id="srv_123",
                server_name="test-server",
                server_url="not-a-url",
                health_status="healthy",
                tools_count=0,
            )
        assert "server_url" in str(exc_info.value)


class TestGatewayToolInfo:
    """Test GatewayToolInfo model."""

    def test_valid_tool_info(self):
        """Test creating valid tool info."""
        tool = GatewayToolInfo(
            tool_name="execute_query", server_name="postgres-mcp", description="Execute SQL query"
        )
        assert tool.tool_name == "execute_query"
        assert tool.server_name == "postgres-mcp"
        assert tool.description == "Execute SQL query"
        assert tool.sensitivity_level == SensitivityLevel.MEDIUM
        assert tool.parameters == []
        assert tool.sensitive_params == []

    def test_tool_info_with_all_fields(self):
        """Test tool info with all optional fields."""
        parameters = [
            {"name": "query", "type": "string", "required": True},
            {"name": "database", "type": "string", "required": True},
        ]
        tool = GatewayToolInfo(
            tool_name="execute_query",
            server_name="postgres-mcp",
            description="Execute SQL query on database",
            sensitivity_level=SensitivityLevel.HIGH,
            parameters=parameters,
            sensitive_params=["password", "secret"],
            required_capabilities=["database", "admin"],
        )
        assert tool.sensitivity_level == SensitivityLevel.HIGH
        assert tool.parameters == parameters
        assert tool.sensitive_params == ["password", "secret"]
        assert tool.required_capabilities == ["database", "admin"]


class TestAgentContext:
    """Test AgentContext model."""

    def test_valid_agent_context(self):
        """Test creating valid agent context."""
        context = AgentContext(
            agent_id="agent_123", agent_type=AgentType.SERVICE, environment="production"
        )
        assert context.agent_id == "agent_123"
        assert context.agent_type == AgentType.SERVICE
        assert context.trust_level == TrustLevel.LIMITED
        assert context.environment == "production"
        assert context.rate_limited is False

    def test_agent_context_with_all_fields(self):
        """Test agent context with all optional fields."""
        context = AgentContext(
            agent_id="agent_123",
            agent_type=AgentType.WORKER,
            trust_level=TrustLevel.TRUSTED,
            capabilities=["execute", "query"],
            environment="staging",
            rate_limited=True,
            metadata={"version": "1.0"},
        )
        assert context.trust_level == TrustLevel.TRUSTED
        assert context.capabilities == ["execute", "query"]
        assert context.rate_limited is True
        assert context.metadata == {"version": "1.0"}


class TestGatewayAuthorizationRequest:
    """Test GatewayAuthorizationRequest model."""

    def test_valid_authorization_request(self):
        """Test creating valid authorization request."""
        request = GatewayAuthorizationRequest(action="gateway:tool:invoke")
        assert request.action == "gateway:tool:invoke"
        assert request.server_name is None
        assert request.tool_name is None
        assert request.parameters == {}

    def test_authorization_request_with_all_fields(self):
        """Test authorization request with all optional fields."""
        request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT * FROM users"},
            gateway_metadata={"request_id": "req_123"},
        )
        assert request.server_name == "postgres-mcp"
        assert request.tool_name == "execute_query"
        assert request.parameters == {"query": "SELECT * FROM users"}
        assert request.gateway_metadata == {"request_id": "req_123"}

    def test_authorization_request_invalid_action(self):
        """Test that invalid action is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GatewayAuthorizationRequest(action="invalid:action")
        assert "Action must be one of" in str(exc_info.value)

    def test_authorization_request_valid_actions(self):
        """Test all valid actions are accepted."""
        valid_actions = [
            "gateway:tool:invoke",
            "gateway:server:list",
            "gateway:tool:discover",
            "gateway:server:info",
        ]
        for action in valid_actions:
            request = GatewayAuthorizationRequest(action=action)
            assert request.action == action


class TestGatewayAuthorizationResponse:
    """Test GatewayAuthorizationResponse model."""

    def test_valid_authorization_response(self):
        """Test creating valid authorization response."""
        response = GatewayAuthorizationResponse(allow=True, reason="User has permission")
        assert response.allow is True
        assert response.reason == "User has permission"
        assert response.cache_ttl == 60

    def test_authorization_response_with_all_fields(self):
        """Test authorization response with all optional fields."""
        response = GatewayAuthorizationResponse(
            allow=False,
            reason="Insufficient permissions",
            filtered_parameters={"query": "REDACTED"},
            audit_id="audit_123",
            cache_ttl=120,
        )
        assert response.allow is False
        assert response.filtered_parameters == {"query": "REDACTED"}
        assert response.audit_id == "audit_123"
        assert response.cache_ttl == 120

    def test_authorization_response_negative_cache_ttl(self):
        """Test that negative cache_ttl is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GatewayAuthorizationResponse(allow=True, reason="Test", cache_ttl=-1)
        assert "cache_ttl" in str(exc_info.value)


class TestA2AAuthorizationRequest:
    """Test A2AAuthorizationRequest model."""

    def test_valid_a2a_request(self):
        """Test creating valid A2A authorization request."""
        request = A2AAuthorizationRequest(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            capability="execute",
            message_type="request",
        )
        assert request.source_agent_id == "agent_1"
        assert request.target_agent_id == "agent_2"
        assert request.capability == "execute"
        assert request.message_type == "request"
        assert request.payload_metadata == {}

    def test_a2a_request_with_metadata(self):
        """Test A2A request with payload metadata."""
        request = A2AAuthorizationRequest(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            capability="query",
            message_type="response",
            payload_metadata={"task_id": "task_123"},
        )
        assert request.payload_metadata == {"task_id": "task_123"}

    def test_a2a_request_invalid_capability(self):
        """Test that invalid capability is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            A2AAuthorizationRequest(
                source_agent_id="agent_1",
                target_agent_id="agent_2",
                capability="invalid",
                message_type="request",
            )
        assert "Capability must be one of" in str(exc_info.value)

    def test_a2a_request_valid_capabilities(self):
        """Test all valid capabilities are accepted."""
        valid_capabilities = ["execute", "query", "delegate"]
        for capability in valid_capabilities:
            request = A2AAuthorizationRequest(
                source_agent_id="agent_1",
                target_agent_id="agent_2",
                capability=capability,
                message_type="request",
            )
            assert request.capability == capability


class TestGatewayAuditEvent:
    """Test GatewayAuditEvent model."""

    def test_valid_audit_event(self):
        """Test creating valid audit event."""
        event = GatewayAuditEvent(
            event_type="tool_invoke",
            decision="allow",
            reason="User authorized",
            timestamp=1234567890,
            gateway_request_id="req_123",
        )
        assert event.event_type == "tool_invoke"
        assert event.decision == "allow"
        assert event.reason == "User authorized"
        assert event.timestamp == 1234567890
        assert event.gateway_request_id == "req_123"

    def test_audit_event_with_all_fields(self):
        """Test audit event with all optional fields."""
        event = GatewayAuditEvent(
            event_type="a2a_communication",
            user_id="user_123",
            agent_id="agent_456",
            server_name="postgres-mcp",
            tool_name="execute_query",
            decision="deny",
            reason="Insufficient permissions",
            timestamp=1234567890,
            gateway_request_id="req_123",
            metadata={"ip": "192.168.1.1"},
        )
        assert event.user_id == "user_123"
        assert event.agent_id == "agent_456"
        assert event.server_name == "postgres-mcp"
        assert event.tool_name == "execute_query"
        assert event.metadata == {"ip": "192.168.1.1"}
