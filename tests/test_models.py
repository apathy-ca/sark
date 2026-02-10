"""Tests for database models."""

from datetime import UTC, datetime

from sark.models.action import Action, ActionContext, ActionRequest, OperationType
from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.models.user import User


class TestMCPServerModel:
    """Tests for MCP Server model."""

    def test_server_creation(self) -> None:
        """Test creating MCP server instance."""
        server = MCPServer(
            name="test-server",
            description="Test MCP server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8080",
            mcp_version="2025-06-18",
            capabilities=["tools", "resources"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.REGISTERED,
        )

        assert server.name == "test-server"
        assert server.transport == TransportType.HTTP
        assert server.status == ServerStatus.REGISTERED
        assert server.sensitivity_level == SensitivityLevel.MEDIUM

    def test_server_repr(self) -> None:
        """Test server string representation."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=[],
        )

        repr_str = repr(server)
        assert "MCPServer" in repr_str
        assert "test-server" in repr_str


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self) -> None:
        """Test creating user instance."""
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            is_active=True,
            is_admin=False,
            role="developer",
        )

        assert user.email == "test@example.com"
        assert user.role == "developer"
        assert user.is_active is True
        assert user.is_admin is False


class TestAuditEventModel:
    """Tests for Audit Event model."""

    def test_audit_event_creation(self) -> None:
        """Test creating audit event."""
        event = AuditEvent(
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.LOW,
            user_email="test@example.com",
            tool_name="test_tool",
            decision="allow",
            details={"test": "data"},
        )

        assert event.event_type == AuditEventType.TOOL_INVOKED
        assert event.severity == SeverityLevel.LOW
        assert event.decision == "allow"
        assert event.details["test"] == "data"


class TestActionModel:
    """Tests for Action model."""

    def test_action_creation(self) -> None:
        """Test creating action instance."""
        action = Action(
            resource_id="mcp-server-1",
            operation=OperationType.EXECUTE,
            parameters={"tool": "query_database", "query": "SELECT * FROM users"},
            timestamp=datetime.now(UTC),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
            environment="production",
            principal_id="alice@example.com",
            authorized="allow",
        )

        assert action.resource_id == "mcp-server-1"
        assert action.operation == OperationType.EXECUTE
        assert action.parameters["tool"] == "query_database"
        assert action.ip_address == "192.168.1.1"
        assert action.principal_id == "alice@example.com"
        assert action.authorized == "allow"

    def test_action_repr(self) -> None:
        """Test action string representation."""
        action = Action(
            resource_id="test-resource",
            operation=OperationType.READ,
            parameters={},
            timestamp=datetime.now(UTC),
        )

        repr_str = repr(action)
        assert "Action" in repr_str
        assert "test-resource" in repr_str
        assert "READ" in repr_str or "read" in repr_str

    def test_operation_type_enum(self) -> None:
        """Test OperationType enum values."""
        assert OperationType.READ.value == "read"
        assert OperationType.WRITE.value == "write"
        assert OperationType.EXECUTE.value == "execute"
        assert OperationType.CONTROL.value == "control"
        assert OperationType.MANAGE.value == "manage"
        assert OperationType.AUDIT.value == "audit"

    def test_action_context_creation(self) -> None:
        """Test ActionContext pydantic model."""
        context = ActionContext(
            timestamp=datetime.now(UTC),
            ip_address="10.0.0.1",
            user_agent="Test Agent",
            request_id="test-req-456",
            environment="staging",
        )

        assert context.ip_address == "10.0.0.1"
        assert context.user_agent == "Test Agent"
        assert context.request_id == "test-req-456"
        assert context.environment == "staging"

    def test_action_request_creation(self) -> None:
        """Test ActionRequest pydantic model."""
        request = ActionRequest(
            resource_id="api-gateway",
            operation=OperationType.WRITE,
            parameters={"data": "test"},
            context=ActionContext(ip_address="127.0.0.1"),
        )

        assert request.resource_id == "api-gateway"
        assert request.operation == OperationType.WRITE
        assert request.parameters["data"] == "test"
        assert request.context.ip_address == "127.0.0.1"
