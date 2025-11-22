"""Unit tests for Discovery Service."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.mcp_server import MCPServer, MCPTool, ServerStatus, TransportType
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
    db.rollback = AsyncMock()
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


@pytest.fixture
def sample_server():
    """Sample MCP server."""
    from sark.models.mcp_server import SensitivityLevel

    server_id = uuid4()
    return MCPServer(
        id=server_id,
        name="test-server",
        description="Test server",
        transport=TransportType.HTTP,
        endpoint="http://localhost:8000",
        command=None,
        mcp_version="2025-06-18",
        capabilities=["tools", "prompts"],
        sensitivity_level=SensitivityLevel.MEDIUM,
        signature=None,
        status=ServerStatus.REGISTERED,
        owner_id=uuid4(),
        team_id=uuid4(),
        tags=["test", "development"],
        extra_metadata={"env": "test"},
        consul_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_tools():
    """Sample MCP tools."""
    from sark.models.mcp_server import SensitivityLevel

    server_id = uuid4()
    return [
        MCPTool(
            id=uuid4(),
            server_id=server_id,
            name="test-tool-1",
            description="First test tool",
            parameters={"type": "object"},
            sensitivity_level=SensitivityLevel.MEDIUM,
            signature=None,
            requires_approval=False,
            extra_metadata={},
        ),
        MCPTool(
            id=uuid4(),
            server_id=server_id,
            name="test-tool-2",
            description="Second test tool",
            parameters={"type": "object"},
            sensitivity_level=SensitivityLevel.HIGH,
            signature=None,
            requires_approval=True,
            extra_metadata={},
        ),
    ]


class TestDiscoveryServiceRegisterServer:
    """Test register_server method."""

    @pytest.mark.asyncio
    async def test_register_server_http_success(self, discovery_service, mock_db, mock_consul):
        """Test successful HTTP server registration."""
        user_id = uuid4()
        team_id = uuid4()

        tools = [
            {
                "name": "test-tool",
                "description": "Test tool",
                "parameters": {"type": "object"},
                "sensitivity_level": "medium",
                "signature": None,
                "requires_approval": False,
                "metadata": {},
            }
        ]

        # Mock flush to set server ID
        def flush_side_effect():
            # Simulate database setting the ID on flush
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        server = await discovery_service.register_server(
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=tools,
            owner_id=user_id,
            team_id=team_id,
            endpoint="http://localhost:8000",
            description="Test server",
            sensitivity_level="medium",
            tags=["test"],
            metadata={"env": "test"},
        )

        # Verify server was created
        assert server.name == "test-server"
        assert server.transport == TransportType.HTTP
        assert server.endpoint == "http://localhost:8000"
        assert server.status == ServerStatus.REGISTERED
        assert server.owner_id == user_id
        assert server.team_id == team_id
        assert server.tags == ["test"]
        assert server.extra_metadata == {"env": "test"}

        # Verify database operations
        assert mock_db.add.call_count >= 2  # Server + tool
        mock_db.flush.assert_awaited_once()
        # Commit is called at least once
        assert mock_db.commit.await_count >= 1
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_server_stdio_success(self, discovery_service, mock_db):
        """Test successful stdio server registration."""
        tools = []

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
            tools=tools,
            command="python server.py",
            description="Stdio server",
        )

        assert server.name == "stdio-server"
        assert server.transport == TransportType.STDIO
        assert server.command == "python server.py"
        assert server.endpoint is None

    @pytest.mark.asyncio
    async def test_register_server_with_multiple_tools(self, discovery_service, mock_db):
        """Test server registration with multiple tools."""
        tools = [
            {
                "name": "tool-1",
                "description": "First tool",
                "parameters": {},
                "sensitivity_level": "low",
            },
            {
                "name": "tool-2",
                "description": "Second tool",
                "parameters": {},
                "sensitivity_level": "high",
                "requires_approval": True,
            },
            {
                "name": "tool-3",
                "description": "Third tool",
                "parameters": {},
            },
        ]

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        await discovery_service.register_server(
            name="multi-tool-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=tools,
            endpoint="http://localhost:8000",
        )

        # Verify server + 3 tools were added
        assert mock_db.add.call_count == 4

    @pytest.mark.asyncio
    async def test_register_server_consul_failure_logs_error(
        self, discovery_service, mock_db, mock_consul
    ):
        """Test that Consul registration failures are logged but don't fail registration."""
        mock_consul.agent.service.register.side_effect = Exception("Consul unavailable")

        def flush_side_effect():
            for call in mock_db.add.call_args_list:
                obj = call[0][0]
                if isinstance(obj, MCPServer) and not obj.id:
                    obj.id = uuid4()

        mock_db.flush.side_effect = flush_side_effect

        # Should not raise exception
        server = await discovery_service.register_server(
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=["tools"],
            tools=[],
            endpoint="http://localhost:8000",
        )

        assert server.name == "test-server"
        # Server should still be registered in DB even though Consul failed
        mock_db.commit.assert_awaited_once()


class TestDiscoveryServiceUpdateServerStatus:
    """Test update_server_status method."""

    @pytest.mark.asyncio
    async def test_update_status_success(self, discovery_service, mock_db, sample_server):
        """Test successful status update."""
        mock_db.get.return_value = sample_server

        updated_server = await discovery_service.update_server_status(
            server_id=sample_server.id,
            status=ServerStatus.ACTIVE,
        )

        assert updated_server.status == ServerStatus.ACTIVE
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_server_not_found(self, discovery_service, mock_db):
        """Test status update when server doesn't exist."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Server .* not found"):
            await discovery_service.update_server_status(
                server_id=uuid4(),
                status=ServerStatus.ACTIVE,
            )

    @pytest.mark.asyncio
    async def test_update_status_to_unhealthy(self, discovery_service, mock_db, sample_server):
        """Test updating server to unhealthy status."""
        mock_db.get.return_value = sample_server

        updated_server = await discovery_service.update_server_status(
            server_id=sample_server.id,
            status=ServerStatus.UNHEALTHY,
        )

        assert updated_server.status == ServerStatus.UNHEALTHY


class TestDiscoveryServiceGetServer:
    """Test get_server method."""

    @pytest.mark.asyncio
    async def test_get_server_found(self, discovery_service, mock_db, sample_server):
        """Test getting an existing server."""
        mock_db.get.return_value = sample_server

        result = await discovery_service.get_server(sample_server.id)

        assert result == sample_server
        mock_db.get.assert_awaited_once_with(MCPServer, sample_server.id)

    @pytest.mark.asyncio
    async def test_get_server_not_found(self, discovery_service, mock_db):
        """Test getting a non-existent server."""
        mock_db.get.return_value = None

        result = await discovery_service.get_server(uuid4())

        assert result is None


class TestDiscoveryServiceGetServerByName:
    """Test get_server_by_name method."""

    @pytest.mark.asyncio
    async def test_get_server_by_name_found(self, discovery_service, mock_db, sample_server):
        """Test getting server by name."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_server
        mock_db.execute.return_value = mock_result

        result = await discovery_service.get_server_by_name("test-server")

        assert result == sample_server
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_server_by_name_not_found(self, discovery_service, mock_db):
        """Test getting non-existent server by name."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await discovery_service.get_server_by_name("nonexistent")

        assert result is None


class TestDiscoveryServiceListServers:
    """Test list_servers method."""

    @pytest.mark.asyncio
    async def test_list_servers_no_filters(self, discovery_service, mock_db, sample_server):
        """Test listing all servers without filters."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_server]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        servers = await discovery_service.list_servers()

        assert len(servers) == 1
        assert servers[0] == sample_server

    @pytest.mark.asyncio
    async def test_list_servers_with_status_filter(self, discovery_service, mock_db, sample_server):
        """Test listing servers filtered by status."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_server]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        servers = await discovery_service.list_servers(status=ServerStatus.ACTIVE)

        assert len(servers) == 1

    @pytest.mark.asyncio
    async def test_list_servers_with_owner_filter(self, discovery_service, mock_db, sample_server):
        """Test listing servers filtered by owner."""
        owner_id = uuid4()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_server]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        servers = await discovery_service.list_servers(owner_id=owner_id)

        assert len(servers) == 1

    @pytest.mark.asyncio
    async def test_list_servers_with_team_filter(self, discovery_service, mock_db):
        """Test listing servers filtered by team."""
        team_id = uuid4()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        servers = await discovery_service.list_servers(team_id=team_id)

        assert len(servers) == 0

    @pytest.mark.asyncio
    async def test_list_servers_with_multiple_filters(
        self, discovery_service, mock_db, sample_server
    ):
        """Test listing servers with multiple filters."""
        owner_id = uuid4()
        team_id = uuid4()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_server]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        servers = await discovery_service.list_servers(
            status=ServerStatus.ACTIVE,
            owner_id=owner_id,
            team_id=team_id,
        )

        assert len(servers) == 1


class TestDiscoveryServiceListServersPaginated:
    """Test list_servers_paginated method."""

    @pytest.mark.asyncio
    async def test_list_servers_paginated_basic(self, discovery_service, mock_db, sample_server):
        """Test paginated server listing."""
        from sark.api.pagination import PaginationParams

        pagination = PaginationParams(limit=50, cursor=None, sort_order="desc")

        # Mock the paginator response
        with patch(
            "sark.services.discovery.discovery_service.CursorPaginator.paginate",
            new=AsyncMock(return_value=([sample_server], None, False, None)),
        ):
            servers, next_cursor, has_more, total = (
                await discovery_service.list_servers_paginated(
                    pagination=pagination,
                )
            )

            assert len(servers) == 1
            assert next_cursor is None
            assert has_more is False
            assert total is None

    @pytest.mark.asyncio
    async def test_list_servers_paginated_with_filters(
        self, discovery_service, mock_db, sample_server
    ):
        """Test paginated listing with filters."""
        from sark.api.pagination import PaginationParams

        pagination = PaginationParams(limit=10, cursor=None, sort_order="asc")

        with patch(
            "sark.services.discovery.discovery_service.CursorPaginator.paginate",
            new=AsyncMock(return_value=([sample_server], "cursor123", True, 100)),
        ):
            servers, next_cursor, has_more, total = (
                await discovery_service.list_servers_paginated(
                    pagination=pagination,
                    status=ServerStatus.ACTIVE,
                    owner_id=uuid4(),
                    tags=["production"],
                    search="test",
                    count_total=True,
                )
            )

            assert len(servers) == 1
            assert next_cursor == "cursor123"
            assert has_more is True
            assert total == 100


class TestDiscoveryServiceGetServerTools:
    """Test get_server_tools method."""

    @pytest.mark.asyncio
    async def test_get_server_tools_success(self, discovery_service, mock_db, sample_tools):
        """Test getting tools for a server."""
        server_id = uuid4()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_tools
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        tools = await discovery_service.get_server_tools(server_id)

        assert len(tools) == 2
        assert tools[0].name == "test-tool-1"
        assert tools[1].name == "test-tool-2"

    @pytest.mark.asyncio
    async def test_get_server_tools_no_tools(self, discovery_service, mock_db):
        """Test getting tools for server with no tools."""
        server_id = uuid4()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        tools = await discovery_service.get_server_tools(server_id)

        assert len(tools) == 0


class TestDiscoveryServiceDeregisterServer:
    """Test deregister_server method."""

    @pytest.mark.asyncio
    async def test_deregister_server_success(
        self, discovery_service, mock_db, mock_consul, sample_server
    ):
        """Test successful server deregistration."""
        sample_server.consul_id = "mcp-test-server-123"
        mock_db.get.return_value = sample_server

        await discovery_service.deregister_server(sample_server.id)

        # Verify Consul deregistration
        mock_consul.agent.service.deregister.assert_called_once_with("mcp-test-server-123")

        # Verify status update
        assert sample_server.status == ServerStatus.DECOMMISSIONED
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deregister_server_not_found(self, discovery_service, mock_db):
        """Test deregistering non-existent server."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Server .* not found"):
            await discovery_service.deregister_server(uuid4())

    @pytest.mark.asyncio
    async def test_deregister_server_without_consul_id(
        self, discovery_service, mock_db, sample_server
    ):
        """Test deregistering server without Consul ID."""
        sample_server.consul_id = None
        mock_db.get.return_value = sample_server

        await discovery_service.deregister_server(sample_server.id)

        # Should still update status
        assert sample_server.status == ServerStatus.DECOMMISSIONED
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deregister_server_consul_failure_continues(
        self, discovery_service, mock_db, mock_consul, sample_server
    ):
        """Test that Consul deregistration failures don't prevent status update."""
        sample_server.consul_id = "mcp-test-server-123"
        mock_db.get.return_value = sample_server
        mock_consul.agent.service.deregister.side_effect = Exception("Consul error")

        # Should not raise exception
        await discovery_service.deregister_server(sample_server.id)

        # Status should still be updated
        assert sample_server.status == ServerStatus.DECOMMISSIONED
        mock_db.commit.assert_awaited_once()


class TestDiscoveryServiceConsulRegistration:
    """Test _register_consul method."""

    @pytest.mark.asyncio
    async def test_register_consul_http_with_health_check(
        self, discovery_service, mock_db, mock_consul, sample_server
    ):
        """Test Consul registration for HTTP server with health check."""
        sample_server.health_endpoint = "http://localhost:8000/health"
        sample_server.consul_id = None

        await discovery_service._register_consul(sample_server)

        # Verify Consul registration was called
        assert discovery_service.consul_client.agent.service.register.called
        call_kwargs = discovery_service.consul_client.agent.service.register.call_args[1]

        assert call_kwargs["name"] == "mcp-test-server"
        assert "mcp-server" in call_kwargs["tags"]
        assert call_kwargs["meta"]["server_id"] == str(sample_server.id)
        assert "check" in call_kwargs
        assert call_kwargs["check"]["http"] == "http://localhost:8000/health"

        # Verify consul_id was updated
        assert sample_server.consul_id is not None
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_consul_stdio_no_health_check(
        self, discovery_service, mock_db, mock_consul, sample_server
    ):
        """Test Consul registration for stdio server without health check."""
        sample_server.transport = TransportType.STDIO
        sample_server.health_endpoint = None
        sample_server.consul_id = None

        await discovery_service._register_consul(sample_server)

        # Verify Consul registration was called
        assert discovery_service.consul_client.agent.service.register.called
        call_kwargs = discovery_service.consul_client.agent.service.register.call_args[1]

        # Should not have health check
        assert "check" not in call_kwargs

    @pytest.mark.asyncio
    async def test_register_consul_with_tags(
        self, discovery_service, mock_db, mock_consul, sample_server
    ):
        """Test Consul registration includes server tags."""
        sample_server.tags = ["production", "critical", "analytics"]
        sample_server.consul_id = None

        await discovery_service._register_consul(sample_server)

        call_kwargs = discovery_service.consul_client.agent.service.register.call_args[1]
        assert "production" in call_kwargs["tags"]
        assert "critical" in call_kwargs["tags"]
        assert "analytics" in call_kwargs["tags"]
        assert "mcp-server" in call_kwargs["tags"]
