"""Tests for database models."""

from datetime import UTC, datetime

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.models.principal import Principal


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


class TestPrincipalModel:
    """Tests for Principal model."""

    def test_user_creation(self) -> None:
        """Test creating user instance."""
        user = Principal(
            email="test@example.com",
            full_name="Test Principal",
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
