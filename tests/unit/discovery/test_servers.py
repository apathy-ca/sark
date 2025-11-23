"""Unit tests for Server Registration and Management."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.mcp_server import MCPServer, MCPTool, SensitivityLevel, ServerStatus, TransportType
from sark.services.discovery import DiscoveryService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_consul():
    """Mock Consul client."""
    consul = MagicMock()
    consul.agent = MagicMock()
    consul.agent.service = MagicMock()
    consul.agent.service.register = MagicMock()
    consul.agent.service.deregister = MagicMock()
    return consul


@pytest.fixture
def discovery_service(mock_db, mock_consul):
    """Discovery service with mocked dependencies."""
    with patch("sark.services.discovery.discovery_service.consul.Consul", return_value=mock_consul):
        service = DiscoveryService(mock_db)
        return service


class TestServerRegistration:
    """Test server registration functionality."""

    @pytest.mark.asyncio
    async def test_register_http_server_minimal_config(self, discovery_service, mock_db):
        """Test registering HTTP server with minimal configuration."""

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="minimal-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=[],
            endpoint="http://localhost:8000",
        )

        assert server.name == "minimal-server"
        assert server.transport == TransportType.HTTP
        assert server.endpoint == "http://localhost:8000"
        assert server.status == ServerStatus.REGISTERED
        assert server.capabilities == ["tools"]

    @pytest.mark.asyncio
    async def test_register_server_with_full_config(self, discovery_service, mock_db):
        """Test registering server with complete configuration."""
        user_id = uuid4()
        team_id = uuid4()

        tools = [
            {
                "name": "query-database",
                "description": "Query database",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
                "sensitivity_level": "high",
                "signature": "sig123",
                "requires_approval": True,
                "metadata": {"version": "1.0"},
            }
        ]

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="full-config-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools", "prompts", "resources"],
            tools=tools,
            owner_id=user_id,
            team_id=team_id,
            endpoint="https://api.example.com",
            description="Fully configured test server",
            sensitivity_level="high",
            signature="server-sig-456",
            tags=["production", "critical", "database"],
            metadata={"region": "us-west", "datacenter": "dc1"},
        )

        assert server.name == "full-config-server"
        assert server.owner_id == user_id
        assert server.team_id == team_id
        assert server.description == "Fully configured test server"
        assert server.sensitivity_level == "high"
        assert server.signature == "server-sig-456"
        assert "production" in server.tags
        assert server.extra_metadata["region"] == "us-west"

        # Verify tool was added
        assert mock_db.add.call_count == 2  # Server + 1 tool

    @pytest.mark.asyncio
    async def test_register_stdio_server(self, discovery_service, mock_db):
        """Test registering stdio server."""

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="stdio-server",
            transport=TransportType.STDIO,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=[],
            command="python -m my_mcp_server",
            description="Stdio-based server",
        )

        assert server.name == "stdio-server"
        assert server.transport == TransportType.STDIO
        assert server.command == "python -m my_mcp_server"
        assert server.endpoint is None

    @pytest.mark.asyncio
    async def test_register_sse_server(self, discovery_service, mock_db):
        """Test registering SSE server."""

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="sse-server",
            transport=TransportType.SSE,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=[],
            endpoint="https://sse.example.com/events",
        )

        assert server.name == "sse-server"
        assert server.transport == TransportType.SSE
        assert server.endpoint == "https://sse.example.com/events"

    @pytest.mark.asyncio
    async def test_register_server_with_multiple_capabilities(self, discovery_service, mock_db):
        """Test registering server with multiple capabilities."""

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="multi-capability-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools", "prompts", "resources", "sampling"],
            tools=[],
            endpoint="http://localhost:8000",
        )

        assert len(server.capabilities) == 4
        assert "tools" in server.capabilities
        assert "prompts" in server.capabilities
        assert "resources" in server.capabilities
        assert "sampling" in server.capabilities

    @pytest.mark.asyncio
    async def test_register_server_with_complex_tools(self, discovery_service, mock_db):
        """Test registering server with complex tool definitions."""
        tools = [
            {
                "name": "execute-query",
                "description": "Execute database query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "timeout": {"type": "integer"},
                        "database": {"type": "string"},
                    },
                    "required": ["query"],
                },
                "sensitivity_level": "critical",
                "requires_approval": True,
            },
            {
                "name": "read-file",
                "description": "Read file contents",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
                "sensitivity_level": "medium",
                "requires_approval": False,
            },
            {
                "name": "list-directory",
                "description": "List directory contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "recursive": {"type": "boolean"},
                    },
                },
                "sensitivity_level": "low",
            },
        ]

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        await discovery_service.register_server(
            name="complex-tools-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=tools,
            endpoint="http://localhost:8000",
        )

        # Verify server and 3 tools were added
        assert mock_db.add.call_count == 4


class TestServerStatusManagement:
    """Test server status management."""

    @pytest.mark.asyncio
    async def test_update_status_to_active(self, discovery_service, mock_db):
        """Test updating server status to active."""
        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.REGISTERED,
            tags=[],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = server

        updated = await discovery_service.update_server_status(
            server_id=server.id,
            status=ServerStatus.ACTIVE,
        )

        assert updated.status == ServerStatus.ACTIVE
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_to_inactive(self, discovery_service, mock_db):
        """Test updating server status to inactive."""
        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
            tags=[],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = server

        updated = await discovery_service.update_server_status(
            server_id=server.id,
            status=ServerStatus.INACTIVE,
        )

        assert updated.status == ServerStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_update_status_to_unhealthy(self, discovery_service, mock_db):
        """Test updating server status to unhealthy."""
        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
            tags=[],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = server

        updated = await discovery_service.update_server_status(
            server_id=server.id,
            status=ServerStatus.UNHEALTHY,
        )

        assert updated.status == ServerStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_update_status_lifecycle(self, discovery_service, mock_db):
        """Test complete server status lifecycle."""
        server = MCPServer(
            id=uuid4(),
            name="lifecycle-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.REGISTERED,
            tags=[],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = server

        # REGISTERED -> ACTIVE
        await discovery_service.update_server_status(server.id, ServerStatus.ACTIVE)
        assert server.status == ServerStatus.ACTIVE

        # ACTIVE -> UNHEALTHY
        await discovery_service.update_server_status(server.id, ServerStatus.UNHEALTHY)
        assert server.status == ServerStatus.UNHEALTHY

        # UNHEALTHY -> ACTIVE
        await discovery_service.update_server_status(server.id, ServerStatus.ACTIVE)
        assert server.status == ServerStatus.ACTIVE

        # ACTIVE -> INACTIVE
        await discovery_service.update_server_status(server.id, ServerStatus.INACTIVE)
        assert server.status == ServerStatus.INACTIVE

        # INACTIVE -> ACTIVE
        await discovery_service.update_server_status(server.id, ServerStatus.ACTIVE)
        assert server.status == ServerStatus.ACTIVE


class TestServerRetrieval:
    """Test server retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_server_by_id(self, discovery_service, mock_db):
        """Test getting server by ID."""
        server_id = uuid4()
        expected_server = MCPServer(
            id=server_id,
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
            tags=["test"],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = expected_server

        server = await discovery_service.get_server(server_id)

        assert server == expected_server
        assert server.id == server_id
        assert server.name == "test-server"

    @pytest.mark.asyncio
    async def test_get_server_by_name(self, discovery_service, mock_db):
        """Test getting server by name."""
        expected_server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
            tags=[],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_server
        mock_db.execute.return_value = mock_result

        server = await discovery_service.get_server_by_name("test-server")

        assert server == expected_server
        assert server.name == "test-server"

    @pytest.mark.asyncio
    async def test_get_nonexistent_server_by_id(self, discovery_service, mock_db):
        """Test getting non-existent server by ID."""
        mock_db.get.return_value = None

        server = await discovery_service.get_server(uuid4())

        assert server is None

    @pytest.mark.asyncio
    async def test_get_nonexistent_server_by_name(self, discovery_service, mock_db):
        """Test getting non-existent server by name."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        server = await discovery_service.get_server_by_name("nonexistent")

        assert server is None


class TestServerTools:
    """Test server tool management."""

    @pytest.mark.asyncio
    async def test_get_server_tools(self, discovery_service, mock_db):
        """Test getting tools for a server."""
        server_id = uuid4()
        tools = [
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool-1",
                description="First tool",
                parameters={},
                sensitivity_level=SensitivityLevel.MEDIUM,
                signature=None,
                requires_approval=False,
                extra_metadata={},
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool-2",
                description="Second tool",
                parameters={},
                sensitivity_level=SensitivityLevel.HIGH,
                signature=None,
                requires_approval=True,
                extra_metadata={},
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tools
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await discovery_service.get_server_tools(server_id)

        assert len(result) == 2
        assert result[0].name == "tool-1"
        assert result[1].name == "tool-2"
        assert result[1].requires_approval is True

    @pytest.mark.asyncio
    async def test_get_tools_for_server_with_no_tools(self, discovery_service, mock_db):
        """Test getting tools for server with no tools."""
        server_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await discovery_service.get_server_tools(server_id)

        assert len(result) == 0


class TestServerDeregistration:
    """Test server deregistration."""

    @pytest.mark.asyncio
    async def test_deregister_server(self, discovery_service, mock_db, mock_consul):
        """Test deregistering a server."""
        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
            consul_id="mcp-test-server-123",
            tags=[],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = server

        await discovery_service.deregister_server(server.id)

        # Verify Consul deregistration
        mock_consul.agent.service.deregister.assert_called_once_with("mcp-test-server-123")

        # Verify status updated
        assert server.status == ServerStatus.DECOMMISSIONED
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deregister_server_without_consul(self, discovery_service, mock_db, mock_consul):
        """Test deregistering server without Consul ID."""
        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
            consul_id=None,
            tags=[],
            extra_metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = server

        await discovery_service.deregister_server(server.id)

        # Should not attempt Consul deregistration
        mock_consul.agent.service.deregister.assert_not_called()

        # Status should still be updated
        assert server.status == ServerStatus.DECOMMISSIONED

    @pytest.mark.asyncio
    async def test_deregister_nonexistent_server(self, discovery_service, mock_db):
        """Test deregistering non-existent server."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Server .* not found"):
            await discovery_service.deregister_server(uuid4())


class TestServerSensitivityLevels:
    """Test server sensitivity level handling."""

    @pytest.mark.asyncio
    async def test_register_low_sensitivity_server(self, discovery_service, mock_db):
        """Test registering low sensitivity server."""

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="low-sensitivity-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=[],
            endpoint="http://localhost:8000",
            sensitivity_level="low",
        )

        assert server.sensitivity_level == "low"

    @pytest.mark.asyncio
    async def test_register_critical_sensitivity_server(self, discovery_service, mock_db):
        """Test registering critical sensitivity server."""

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="critical-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=[],
            endpoint="http://localhost:8000",
            sensitivity_level="critical",
        )

        assert server.sensitivity_level == "critical"

    @pytest.mark.asyncio
    async def test_register_server_default_sensitivity(self, discovery_service, mock_db):
        """Test that server defaults to medium sensitivity."""

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="default-sensitivity-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=[],
            endpoint="http://localhost:8000",
        )

        assert server.sensitivity_level == "medium"
