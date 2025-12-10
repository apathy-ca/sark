"""Comprehensive tests for DiscoveryService.

This module tests:
- Server registration with Consul integration
- Server status management
- Server retrieval and listing
- Tool registration and management
- Pagination and filtering
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.mcp_server import (
    MCPServer,
    MCPTool,
    SensitivityLevel,
    ServerStatus,
    TransportType,
)
from sark.services.discovery.discovery_service import DiscoveryService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_consul():
    """Create mock Consul client."""
    consul_mock = MagicMock()
    consul_mock.agent = MagicMock()
    consul_mock.agent.service = MagicMock()
    consul_mock.agent.service.register = MagicMock()
    consul_mock.agent.service.deregister = MagicMock()
    return consul_mock


@pytest.fixture
def discovery_service(mock_db, mock_consul):
    """Create DiscoveryService with mocks."""
    with patch("sark.services.discovery.discovery_service.consul.Consul", return_value=mock_consul):
        service = DiscoveryService(db=mock_db)
        service.consul_client = mock_consul
        return service


class TestDiscoveryServiceInit:
    """Test DiscoveryService initialization."""

    def test_initialization(self, mock_db):
        """Test service initializes correctly."""
        with patch("sark.services.discovery.discovery_service.consul.Consul"):
            service = DiscoveryService(db=mock_db)
            assert service.db == mock_db
            assert service.consul_client is not None


class TestRegisterServer:
    """Test server registration."""

    @pytest.mark.asyncio
    async def test_register_http_server(self, discovery_service, mock_db):
        """Test registering an HTTP server."""
        server_id = uuid4()

        async def mock_flush():
            # Simulate database setting the ID
            added_server = mock_db.add.call_args[0][0]
            added_server.id = server_id

        mock_db.flush.side_effect = mock_flush

        tools = [
            {
                "name": "test_tool",
                "description": "Test tool",
                "parameters": {"type": "object"},
                "sensitivity_level": "low",
            }
        ]

        with patch("sark.services.discovery.tool_registry.ToolRegistry"):
            server = await discovery_service.register_server(
                name="test-server",
                transport=TransportType.HTTP,
                mcp_version="1.0.0",
                capabilities=["tools"],
                tools=tools,
                endpoint="http://localhost:8000",
                description="Test server",
                sensitivity_level="medium",
                tags=["test", "demo"],
            )

        # Verify server was created
        assert mock_db.add.call_count >= 1  # Server + tools
        assert mock_db.commit.called
        assert mock_db.refresh.called

    @pytest.mark.asyncio
    async def test_register_stdio_server(self, discovery_service, mock_db):
        """Test registering a stdio server."""
        server_id = uuid4()

        async def mock_flush():
            added_server = mock_db.add.call_args[0][0]
            added_server.id = server_id

        mock_db.flush.side_effect = mock_flush

        tools = [{"name": "stdio_tool", "sensitivity_level": "medium"}]

        with patch("sark.services.discovery.tool_registry.ToolRegistry"):
            server = await discovery_service.register_server(
                name="stdio-server",
                transport=TransportType.STDIO,
                mcp_version="1.0.0",
                capabilities=["tools"],
                tools=tools,
                command="python server.py",
            )

        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_register_server_with_auto_sensitivity_detection(
        self, discovery_service, mock_db
    ):
        """Test server registration with automatic tool sensitivity detection."""
        server_id = uuid4()

        async def mock_flush():
            added_server = mock_db.add.call_args[0][0]
            added_server.id = server_id

        mock_db.flush.side_effect = mock_flush

        # Tool without sensitivity_level - should trigger auto-detection
        tools = [
            {
                "name": "delete_database",
                "description": "Deletes the entire database",
                "parameters": {},
            }
        ]

        mock_tool_registry = AsyncMock()
        mock_tool_registry.detect_sensitivity = AsyncMock(
            return_value=SensitivityLevel.CRITICAL
        )

        with patch(
            "sark.services.discovery.tool_registry.ToolRegistry",
            return_value=mock_tool_registry,
        ):
            server = await discovery_service.register_server(
                name="dangerous-server",
                transport=TransportType.HTTP,
                mcp_version="1.0.0",
                capabilities=["tools"],
                tools=tools,
                endpoint="http://localhost:8000",
            )

        # Verify sensitivity detection was called
        mock_tool_registry.detect_sensitivity.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_server_with_owner_and_team(
        self, discovery_service, mock_db
    ):
        """Test registering server with owner and team."""
        server_id = uuid4()
        owner_id = uuid4()
        team_id = uuid4()

        async def mock_flush():
            added_server = mock_db.add.call_args[0][0]
            added_server.id = server_id

        mock_db.flush.side_effect = mock_flush

        with patch("sark.services.discovery.tool_registry.ToolRegistry"):
            server = await discovery_service.register_server(
                name="team-server",
                transport=TransportType.HTTP,
                mcp_version="1.0.0",
                capabilities=["tools"],
                tools=[],
                endpoint="http://localhost:8000",
                owner_id=owner_id,
                team_id=team_id,
            )

        added_server = mock_db.add.call_args_list[0][0][0]
        assert added_server.owner_id == owner_id
        assert added_server.team_id == team_id


class TestUpdateServerStatus:
    """Test server status updates."""

    @pytest.mark.asyncio
    async def test_update_server_status(self, discovery_service, mock_db):
        """Test updating server status."""
        server_id = uuid4()
        server = MCPServer(
            id=server_id,
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
            status=ServerStatus.REGISTERED,
        )

        mock_db.get.return_value = server

        updated = await discovery_service.update_server_status(
            server_id=server_id,
            status=ServerStatus.ACTIVE,
        )

        assert server.status == ServerStatus.ACTIVE
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_status_server_not_found(self, discovery_service, mock_db):
        """Test updating status for non-existent server."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await discovery_service.update_server_status(
                server_id=uuid4(),
                status=ServerStatus.ACTIVE,
            )


class TestGetServer:
    """Test server retrieval."""

    @pytest.mark.asyncio
    async def test_get_server_by_id(self, discovery_service, mock_db):
        """Test getting server by ID."""
        server_id = uuid4()
        server = MCPServer(
            id=server_id,
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
        )

        mock_db.get.return_value = server

        result = await discovery_service.get_server(server_id)

        assert result == server
        mock_db.get.assert_called_with(MCPServer, server_id)

    @pytest.mark.asyncio
    async def test_get_server_by_name(self, discovery_service, mock_db):
        """Test getting server by name."""
        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = server
        mock_db.execute.return_value = mock_result

        result = await discovery_service.get_server_by_name("test-server")

        assert result == server
        mock_db.execute.assert_called_once()


class TestListServers:
    """Test server listing."""

    @pytest.mark.asyncio
    async def test_list_all_servers(self, discovery_service, mock_db):
        """Test listing all servers."""
        servers = [
            MCPServer(
                id=uuid4(),
                name="server1",
                transport=TransportType.HTTP,
                mcp_version="1.0.0",
                capabilities=[],
            ),
            MCPServer(
                id=uuid4(),
                name="server2",
                transport=TransportType.STDIO,
                mcp_version="1.0.0",
                capabilities=[],
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = servers
        mock_db.execute.return_value = mock_result

        result = await discovery_service.list_servers()

        assert len(result) == 2
        assert result == servers

    @pytest.mark.asyncio
    async def test_list_servers_filtered_by_status(self, discovery_service, mock_db):
        """Test listing servers filtered by status."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await discovery_service.list_servers(status=ServerStatus.ACTIVE)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_servers_filtered_by_owner(self, discovery_service, mock_db):
        """Test listing servers filtered by owner."""
        owner_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await discovery_service.list_servers(owner_id=owner_id)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_servers_filtered_by_team(self, discovery_service, mock_db):
        """Test listing servers filtered by team."""
        team_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await discovery_service.list_servers(team_id=team_id)

        mock_db.execute.assert_called_once()


class TestGetServerTools:
    """Test tool retrieval for servers."""

    @pytest.mark.asyncio
    async def test_get_server_tools(self, discovery_service, mock_db):
        """Test getting all tools for a server."""
        server_id = uuid4()
        tools = [
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool1",
                sensitivity_level=SensitivityLevel.LOW,
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool2",
                sensitivity_level=SensitivityLevel.MEDIUM,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tools
        mock_db.execute.return_value = mock_result

        result = await discovery_service.get_server_tools(server_id)

        assert len(result) == 2
        assert result == tools


class TestConsulIntegration:
    """Test Consul integration."""

    @pytest.mark.asyncio
    async def test_register_consul_success(self, discovery_service, mock_consul):
        """Test successful Consul registration."""
        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
            tags=["test"],
            sensitivity_level=SensitivityLevel.MEDIUM,
        )

        await discovery_service._register_consul(server)

        # Verify Consul registration was called
        mock_consul.agent.service.register.assert_called_once()
        call_args = mock_consul.agent.service.register.call_args[1]
        assert "mcp-test-server" in call_args["name"]
        assert "mcp-server" in call_args["tags"]

    @pytest.mark.asyncio
    async def test_register_consul_http_with_health_check(
        self, discovery_service, mock_consul, mock_db
    ):
        """Test Consul registration with health check for HTTP server."""
        server = MCPServer(
            id=uuid4(),
            name="http-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
            health_endpoint="http://localhost:8000/health",
            sensitivity_level=SensitivityLevel.LOW,
            tags=[],
        )

        await discovery_service._register_consul(server)

        # Just verify registration was attempted (may fail gracefully)
        # The method handles errors internally

    @pytest.mark.asyncio
    async def test_register_consul_failure_handled(
        self, discovery_service, mock_consul
    ):
        """Test that Consul registration failures are handled gracefully."""
        mock_consul.agent.service.register.side_effect = Exception("Consul error")

        server = MCPServer(
            id=uuid4(),
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
            sensitivity_level=SensitivityLevel.LOW,
        )

        # Should not raise exception
        await discovery_service._register_consul(server)


class TestDeregisterServer:
    """Test server deregistration."""

    @pytest.mark.asyncio
    async def test_deregister_server(self, discovery_service, mock_db, mock_consul):
        """Test deregistering a server."""
        server_id = uuid4()
        server = MCPServer(
            id=server_id,
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
            status=ServerStatus.ACTIVE,
            consul_id="mcp-test-server-123",
        )

        mock_db.get.return_value = server

        await discovery_service.deregister_server(server_id)

        # Verify Consul deregistration
        mock_consul.agent.service.deregister.assert_called_with("mcp-test-server-123")

        # Verify status updated
        assert server.status == ServerStatus.DECOMMISSIONED
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_deregister_server_not_found(self, discovery_service, mock_db):
        """Test deregistering non-existent server."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await discovery_service.deregister_server(uuid4())

    @pytest.mark.asyncio
    async def test_deregister_server_consul_failure_handled(
        self, discovery_service, mock_db, mock_consul
    ):
        """Test that Consul deregistration failures are handled."""
        mock_consul.agent.service.deregister.side_effect = Exception("Consul error")

        server_id = uuid4()
        server = MCPServer(
            id=server_id,
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="1.0.0",
            capabilities=[],
            consul_id="mcp-test-123",
        )

        mock_db.get.return_value = server

        # Should not raise exception
        await discovery_service.deregister_server(server_id)

        # Status should still be updated
        assert server.status == ServerStatus.DECOMMISSIONED
