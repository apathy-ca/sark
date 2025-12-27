"""Comprehensive tests for unified Gateway client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.gateway.client import (
    GatewayClient,
    GatewayClientError,
    LocalServerClient,
    TransportMode,
    TransportNotAvailableError,
    TransportType,
)
from sark.gateway.error_handler import GatewayErrorHandler
from sark.gateway.transports.http_client import GatewayHTTPClient
from sark.gateway.transports.sse_client import GatewaySSEClient, SSEEvent
from sark.gateway.transports.stdio_client import StdioTransport
from sark.models.gateway import GatewayServerInfo, GatewayToolInfo


class TestGatewayClientInitialization:
    """Test suite for GatewayClient initialization."""

    def test_client_initialization_defaults(self):
        """Test client initialization with default values."""
        client = GatewayClient(gateway_url="http://test:8080")

        assert client.gateway_url == "http://test:8080"
        assert client.api_key is None
        assert client.opa_client is None
        assert client.transport_mode == TransportMode.AUTO
        assert client.timeout == 30.0
        assert client.max_connections == 50
        assert client.error_handler is not None
        assert isinstance(client.error_handler, GatewayErrorHandler)
        assert client._http_client is None
        assert client._sse_client is None
        assert client._stdio_transports == {}
        assert client._is_closed is False

    def test_client_initialization_custom_config(self):
        """Test client initialization with custom configuration."""
        client = GatewayClient(
            gateway_url="http://custom:9000",
            api_key="custom-key",
            transport_mode=TransportMode.HTTP_ONLY,
            timeout=60.0,
            max_connections=100,
        )

        assert client.gateway_url == "http://custom:9000"
        assert client.api_key == "custom-key"
        assert client.transport_mode == TransportMode.HTTP_ONLY
        assert client.timeout == 60.0
        assert client.max_connections == 100

    def test_client_initialization_with_opa(self, opa_client):
        """Test client initialization with OPA client."""
        client = GatewayClient(
            gateway_url="http://test:8080",
            opa_client=opa_client,
        )

        assert client.opa_client is opa_client

    def test_client_initialization_without_error_handling(self):
        """Test client initialization with error handling disabled."""
        client = GatewayClient(
            gateway_url="http://test:8080",
            enable_error_handling=False,
        )

        assert client.error_handler is None

    def test_client_initialization_custom_error_handler_config(self):
        """Test client initialization with custom error handler config."""
        circuit_breaker_config = {"failure_threshold": 10}
        retry_config = {"max_attempts": 5}

        client = GatewayClient(
            gateway_url="http://test:8080",
            circuit_breaker_config=circuit_breaker_config,
            retry_config=retry_config,
        )

        assert client.error_handler is not None

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client as async context manager."""
        async with GatewayClient(gateway_url="http://test:8080") as client:
            assert client is not None
            assert not client._is_closed

        assert client._is_closed


class TestTransportManagement:
    """Test suite for transport management and selection."""

    def test_ensure_gateway_url_raises_when_missing(self):
        """Test that operations requiring gateway URL raise error."""
        client = GatewayClient()

        with pytest.raises(GatewayClientError, match="Gateway URL is required"):
            client._ensure_gateway_url()

    def test_get_http_client_lazy_initialization(self):
        """Test HTTP client lazy initialization."""
        client = GatewayClient(gateway_url="http://test:8080", api_key="test-key")

        assert client._http_client is None

        # First call creates the client
        http_client = client._get_http_client()
        assert http_client is not None
        assert isinstance(http_client, GatewayHTTPClient)
        assert client._http_client is http_client

        # Second call returns same instance
        http_client2 = client._get_http_client()
        assert http_client2 is http_client

    def test_get_sse_client_lazy_initialization(self):
        """Test SSE client lazy initialization."""
        client = GatewayClient(gateway_url="http://test:8080", api_key="test-key")

        assert client._sse_client is None

        # First call creates the client
        sse_client = client._get_sse_client()
        assert sse_client is not None
        assert isinstance(sse_client, GatewaySSEClient)
        assert client._sse_client is sse_client

        # Second call returns same instance
        sse_client2 = client._get_sse_client()
        assert sse_client2 is sse_client

    def test_check_transport_available_auto_mode(self):
        """Test transport availability in AUTO mode."""
        client = GatewayClient(gateway_url="http://test:8080", transport_mode=TransportMode.AUTO)

        # All transports should be available in AUTO mode
        client._check_transport_available(TransportType.HTTP)
        client._check_transport_available(TransportType.SSE)
        client._check_transport_available(TransportType.STDIO)

    def test_check_transport_available_http_only_mode(self):
        """Test transport availability in HTTP_ONLY mode."""
        client = GatewayClient(gateway_url="http://test:8080", transport_mode=TransportMode.HTTP_ONLY)

        # Only HTTP should be available
        client._check_transport_available(TransportType.HTTP)

        with pytest.raises(TransportNotAvailableError, match="not available in HTTP_ONLY mode"):
            client._check_transport_available(TransportType.SSE)

        with pytest.raises(TransportNotAvailableError, match="not available in HTTP_ONLY mode"):
            client._check_transport_available(TransportType.STDIO)

    def test_check_transport_available_sse_only_mode(self):
        """Test transport availability in SSE_ONLY mode."""
        client = GatewayClient(gateway_url="http://test:8080", transport_mode=TransportMode.SSE_ONLY)

        # Only SSE should be available
        client._check_transport_available(TransportType.SSE)

        with pytest.raises(TransportNotAvailableError, match="not available in SSE_ONLY mode"):
            client._check_transport_available(TransportType.HTTP)

        with pytest.raises(TransportNotAvailableError, match="not available in SSE_ONLY mode"):
            client._check_transport_available(TransportType.STDIO)

    def test_check_transport_available_stdio_only_mode(self):
        """Test transport availability in STDIO_ONLY mode."""
        client = GatewayClient(transport_mode=TransportMode.STDIO_ONLY)

        # Only STDIO should be available
        client._check_transport_available(TransportType.STDIO)

        with pytest.raises(TransportNotAvailableError, match="not available in STDIO_ONLY mode"):
            client._check_transport_available(TransportType.HTTP)

        with pytest.raises(TransportNotAvailableError, match="not available in STDIO_ONLY mode"):
            client._check_transport_available(TransportType.SSE)

    @pytest.mark.asyncio
    async def test_execute_with_error_handling_enabled(self):
        """Test execution with error handling enabled."""
        client = GatewayClient(gateway_url="http://test:8080", enable_error_handling=True)

        # Mock the error handler's execute method
        client.error_handler.execute = AsyncMock(return_value="result")

        async def test_func():
            return "original"

        result = await client._execute_with_error_handling(test_func)

        # Should delegate to error handler
        client.error_handler.execute.assert_called_once()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_execute_with_error_handling_disabled(self):
        """Test execution with error handling disabled."""
        client = GatewayClient(gateway_url="http://test:8080", enable_error_handling=False)

        async def test_func():
            return "result"

        result = await client._execute_with_error_handling(test_func)

        # Should call function directly
        assert result == "result"


class TestServerDiscoveryOperations:
    """Test suite for server discovery operations."""

    @pytest.mark.asyncio
    async def test_list_servers_success(self):
        """Test listing servers successfully."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_servers = [
            GatewayServerInfo(
                server_id="srv1",
                server_name="server1",
                server_url="http://s1:8080",
                health_status="healthy",
                tools_count=5,
            ),
            GatewayServerInfo(
                server_id="srv2",
                server_name="server2",
                server_url="http://s2:8080",
                health_status="healthy",
                tools_count=3,
            ),
        ]
        mock_http.list_servers = AsyncMock(return_value=expected_servers)
        client._http_client = mock_http

        result = await client.list_servers(page=2, page_size=50)

        assert result == expected_servers
        mock_http.list_servers.assert_called_once_with(page=2, page_size=50)

    @pytest.mark.asyncio
    async def test_list_servers_transport_not_available(self):
        """Test listing servers when HTTP transport not available."""
        client = GatewayClient(gateway_url="http://test:8080", transport_mode=TransportMode.SSE_ONLY)

        with pytest.raises(TransportNotAvailableError):
            await client.list_servers()

    @pytest.mark.asyncio
    async def test_list_all_servers_success(self):
        """Test listing all servers with pagination."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_servers = [
            GatewayServerInfo(
                server_id=f"srv{i}",
                server_name=f"server{i}",
                server_url=f"http://s{i}:8080",
                health_status="healthy",
                tools_count=i,
            )
            for i in range(100)
        ]
        mock_http.list_all_servers = AsyncMock(return_value=expected_servers)
        client._http_client = mock_http

        result = await client.list_all_servers()

        assert result == expected_servers
        assert len(result) == 100
        mock_http.list_all_servers.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_server_info_success(self):
        """Test getting server info successfully."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_server = GatewayServerInfo(
            server_id="srv_test",
            server_name="test-server",
            server_url="http://test:8080",
            health_status="healthy",
            tools_count=10,
        )
        mock_http.get_server_info = AsyncMock(return_value=expected_server)
        client._http_client = mock_http

        result = await client.get_server_info("test-server")

        assert result == expected_server
        mock_http.get_server_info.assert_called_once_with(server_name="test-server")


class TestToolDiscoveryOperations:
    """Test suite for tool discovery operations."""

    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """Test listing tools successfully."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_tools = [
            GatewayToolInfo(tool_name="tool1", server_name="server1", description="Tool 1"),
            GatewayToolInfo(tool_name="tool2", server_name="server1", description="Tool 2"),
        ]
        mock_http.list_tools = AsyncMock(return_value=expected_tools)
        client._http_client = mock_http

        result = await client.list_tools(server_name="server1", page=1, page_size=100)

        assert result == expected_tools
        mock_http.list_tools.assert_called_once_with(
            server_name="server1", page=1, page_size=100
        )

    @pytest.mark.asyncio
    async def test_list_tools_all_servers(self):
        """Test listing tools from all servers."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_tools = [
            GatewayToolInfo(tool_name="tool1", server_name="server1", description="Tool 1"),
            GatewayToolInfo(tool_name="tool2", server_name="server2", description="Tool 2"),
        ]
        mock_http.list_tools = AsyncMock(return_value=expected_tools)
        client._http_client = mock_http

        result = await client.list_tools(server_name=None)

        assert result == expected_tools
        mock_http.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_all_tools_success(self):
        """Test listing all tools with pagination."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_tools = [
            GatewayToolInfo(tool_name=f"tool{i}", server_name="server1", description=f"Tool {i}")
            for i in range(50)
        ]
        mock_http.list_all_tools = AsyncMock(return_value=expected_tools)
        client._http_client = mock_http

        result = await client.list_all_tools(server_name="server1")

        assert result == expected_tools
        assert len(result) == 50
        mock_http.list_all_tools.assert_called_once_with(server_name="server1")


class TestToolInvocation:
    """Test suite for tool invocation operations."""

    @pytest.mark.asyncio
    async def test_invoke_tool_success(self):
        """Test invoking tool successfully."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_result = {"status": "success", "data": {"result": 42}}
        mock_http.invoke_tool = AsyncMock(return_value=expected_result)
        client._http_client = mock_http

        result = await client.invoke_tool(
            server_name="test-server",
            tool_name="test-tool",
            parameters={"input": "test"},
            user_token="jwt-token",
        )

        assert result == expected_result
        mock_http.invoke_tool.assert_called_once_with(
            server_name="test-server",
            tool_name="test-tool",
            parameters={"input": "test"},
            user_token="jwt-token",
        )

    @pytest.mark.asyncio
    async def test_invoke_tool_without_user_token(self):
        """Test invoking tool without user token."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        expected_result = {"status": "success"}
        mock_http.invoke_tool = AsyncMock(return_value=expected_result)
        client._http_client = mock_http

        result = await client.invoke_tool(
            server_name="test-server",
            tool_name="test-tool",
            parameters={},
        )

        assert result == expected_result
        mock_http.invoke_tool.assert_called_once_with(
            server_name="test-server",
            tool_name="test-tool",
            parameters={},
            user_token=None,
        )

    @pytest.mark.asyncio
    async def test_invoke_tool_transport_not_available(self):
        """Test invoking tool when HTTP transport not available."""
        client = GatewayClient(gateway_url="http://test:8080", transport_mode=TransportMode.STDIO_ONLY)

        with pytest.raises(TransportNotAvailableError):
            await client.invoke_tool(
                server_name="test-server",
                tool_name="test-tool",
                parameters={},
            )


class TestEventStreaming:
    """Test suite for SSE event streaming operations."""

    @pytest.mark.asyncio
    async def test_stream_events_success(self):
        """Test streaming events successfully."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock SSE client
        mock_sse = AsyncMock()
        test_events = [
            SSEEvent(event_type="tool_invoked", data={"tool": "test1"}),
            SSEEvent(event_type="server_registered", data={"server": "test2"}),
        ]

        async def mock_stream_events(*args, **kwargs):
            for event in test_events:
                yield event

        mock_sse.stream_events = mock_stream_events
        client._sse_client = mock_sse

        # Collect events
        events = []
        async for event in client.stream_events(endpoint="/api/v1/events"):
            events.append(event)

        assert len(events) == 2
        assert events[0].event_type == "tool_invoked"
        assert events[1].event_type == "server_registered"

    @pytest.mark.asyncio
    async def test_stream_events_with_filtering(self):
        """Test streaming events with type filtering."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock SSE client
        mock_sse = AsyncMock()
        test_events = [
            SSEEvent(event_type="tool_invoked", data={"tool": "test"}),
        ]

        async def mock_stream_events(*args, **kwargs):
            for event in test_events:
                yield event

        mock_sse.stream_events = mock_stream_events
        client._sse_client = mock_sse

        # Collect events with filter
        events = []
        async for event in client.stream_events(
            event_types=["tool_invoked"],
            user_token="jwt-token"
        ):
            events.append(event)

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_stream_events_transport_not_available(self):
        """Test streaming events when SSE transport not available."""
        client = GatewayClient(gateway_url="http://test:8080", transport_mode=TransportMode.HTTP_ONLY)

        with pytest.raises(TransportNotAvailableError):
            async for _ in client.stream_events():
                pass


class TestLocalServerOperations:
    """Test suite for local server (stdio) operations."""

    @pytest.mark.asyncio
    async def test_connect_local_server_success(self):
        """Test connecting to local server successfully."""
        client = GatewayClient()

        # Mock StdioTransport
        with patch("sark.gateway.client.StdioTransport") as MockStdio:
            mock_transport = AsyncMock()
            mock_transport.start = AsyncMock()
            MockStdio.return_value = mock_transport

            local_client = await client.connect_local_server(
                command=["python", "server.py"],
                cwd="/test",
                env={"KEY": "value"},
            )

            assert isinstance(local_client, LocalServerClient)
            assert local_client.transport is mock_transport
            assert local_client.server_id in client._stdio_transports
            mock_transport.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_local_server_custom_id(self):
        """Test connecting to local server with custom ID."""
        client = GatewayClient()

        with patch("sark.gateway.client.StdioTransport") as MockStdio:
            mock_transport = AsyncMock()
            mock_transport.start = AsyncMock()
            MockStdio.return_value = mock_transport

            local_client = await client.connect_local_server(
                command=["python", "server.py"],
                server_id="custom-id",
            )

            assert local_client.server_id == "custom-id"
            assert "custom-id" in client._stdio_transports

    @pytest.mark.asyncio
    async def test_connect_local_server_transport_not_available(self):
        """Test connecting to local server when stdio transport not available."""
        client = GatewayClient(gateway_url="http://test:8080", transport_mode=TransportMode.HTTP_ONLY)

        with pytest.raises(TransportNotAvailableError):
            await client.connect_local_server(command=["python", "server.py"])

    @pytest.mark.asyncio
    async def test_disconnect_local_server_success(self):
        """Test disconnecting from local server successfully."""
        client = GatewayClient()

        # Mock transport
        mock_transport = AsyncMock()
        mock_transport.stop = AsyncMock()
        client._stdio_transports["test-id"] = mock_transport

        await client.disconnect_local_server("test-id")

        assert "test-id" not in client._stdio_transports
        mock_transport.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_local_server_not_found(self):
        """Test disconnecting from non-existent local server."""
        client = GatewayClient()

        with pytest.raises(GatewayClientError, match="not found"):
            await client.disconnect_local_server("nonexistent-id")


class TestLocalServerClient:
    """Test suite for LocalServerClient wrapper."""

    @pytest.mark.asyncio
    async def test_send_request_success(self):
        """Test sending request to local server."""
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(return_value={"result": "success"})

        local_client = LocalServerClient(
            transport=mock_transport,
            server_id="test-id",
            parent=MagicMock(),
        )

        result = await local_client.send_request("test_method", {"param": "value"}, timeout=10.0)

        assert result == {"result": "success"}
        mock_transport.send_request.assert_called_once_with(
            "test_method", {"param": "value"}, timeout=10.0
        )

    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """Test sending notification to local server."""
        mock_transport = AsyncMock()
        mock_transport.send_notification = AsyncMock()

        local_client = LocalServerClient(
            transport=mock_transport,
            server_id="test-id",
            parent=MagicMock(),
        )

        await local_client.send_notification("test_notification", {"data": "value"})

        mock_transport.send_notification.assert_called_once_with(
            "test_notification", {"data": "value"}
        )

    def test_is_running_property(self):
        """Test is_running property."""
        mock_transport = MagicMock()
        mock_transport.is_running = True

        local_client = LocalServerClient(
            transport=mock_transport,
            server_id="test-id",
            parent=MagicMock(),
        )

        assert local_client.is_running is True

        mock_transport.is_running = False
        assert local_client.is_running is False

    @pytest.mark.asyncio
    async def test_stop_delegates_to_parent(self):
        """Test stop delegates to parent disconnect."""
        mock_parent = AsyncMock()
        mock_parent.disconnect_local_server = AsyncMock()

        local_client = LocalServerClient(
            transport=AsyncMock(),
            server_id="test-id",
            parent=mock_parent,
        )

        await local_client.stop()

        mock_parent.disconnect_local_server.assert_called_once_with("test-id")


class TestHealthAndMetrics:
    """Test suite for health check and metrics operations."""

    @pytest.mark.asyncio
    async def test_health_check_all_transports(self):
        """Test health check with all transports active."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = MagicMock()
        mock_http.cache_hit_rate = 0.92
        client._http_client = mock_http

        # Mock SSE client
        mock_sse = MagicMock()
        mock_sse.state = MagicMock(value="connected")
        client._sse_client = mock_sse

        # Mock stdio transport
        mock_stdio = MagicMock()
        mock_stdio.is_running = True
        mock_stdio._process = MagicMock(pid=12345)
        client._stdio_transports["server1"] = mock_stdio

        # Mock error handler
        client.error_handler.get_metrics = MagicMock(return_value={"calls": 100})

        health = await client.health_check()

        assert "http" in health
        assert health["http"]["status"] == "healthy"
        assert health["http"]["cache_hit_rate"] == 0.92

        assert "sse" in health
        assert health["sse"]["status"] == "connected"

        assert "stdio" in health
        assert "server1" in health["stdio"]
        assert health["stdio"]["server1"]["status"] == "running"
        assert health["stdio"]["server1"]["pid"] == 12345

        assert "error_handler" in health

    @pytest.mark.asyncio
    async def test_health_check_no_transports(self):
        """Test health check with no active transports."""
        client = GatewayClient(gateway_url="http://test:8080")
        client.error_handler = None

        health = await client.health_check()

        assert health == {}

    def test_get_metrics_all_transports(self):
        """Test getting metrics with all transports."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock transports
        mock_http = MagicMock()
        mock_http.cache_hit_rate = 0.85
        client._http_client = mock_http

        client._sse_client = MagicMock()

        client._stdio_transports = {"server1": MagicMock(), "server2": MagicMock()}

        client.error_handler.get_metrics = MagicMock(return_value={"calls": 50})

        metrics = client.get_metrics()

        assert metrics["transport_mode"] == "auto"
        assert "http" in metrics["active_transports"]
        assert "sse" in metrics["active_transports"]
        assert "stdio" in metrics["active_transports"]
        assert metrics["http_cache_hit_rate"] == 0.85
        assert metrics["stdio_servers_count"] == 2
        assert "error_handler" in metrics

    def test_get_metrics_no_transports(self):
        """Test getting metrics with no active transports."""
        client = GatewayClient(gateway_url="http://test:8080")
        client.error_handler = None

        metrics = client.get_metrics()

        assert metrics["transport_mode"] == "auto"
        assert metrics["active_transports"] == []


class TestCleanup:
    """Test suite for cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_close_all_transports(self):
        """Test closing all transports."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock transports
        mock_http = AsyncMock()
        mock_http.close = AsyncMock()
        client._http_client = mock_http

        mock_sse = AsyncMock()
        mock_sse.close = AsyncMock()
        client._sse_client = mock_sse

        mock_stdio1 = AsyncMock()
        mock_stdio1.stop = AsyncMock()
        mock_stdio2 = AsyncMock()
        mock_stdio2.stop = AsyncMock()
        client._stdio_transports = {"s1": mock_stdio1, "s2": mock_stdio2}

        await client.close()

        assert client._is_closed is True
        assert client._http_client is None
        assert client._sse_client is None
        assert client._stdio_transports == {}

        mock_http.close.assert_called_once()
        mock_sse.close.assert_called_once()
        mock_stdio1.stop.assert_called_once()
        mock_stdio2.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Test that close can be called multiple times safely."""
        client = GatewayClient(gateway_url="http://test:8080")

        await client.close()
        assert client._is_closed is True

        # Should not raise error
        await client.close()
        assert client._is_closed is True

    @pytest.mark.asyncio
    async def test_close_handles_stdio_errors(self):
        """Test that close handles stdio transport errors gracefully."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock stdio transport that raises error
        mock_stdio = AsyncMock()
        mock_stdio.stop = AsyncMock(side_effect=Exception("Stop failed"))
        client._stdio_transports = {"server1": mock_stdio}

        # Should not raise error
        await client.close()

        assert client._is_closed is True
        assert client._stdio_transports == {}

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self):
        """Test that context manager calls close on exit."""
        client = GatewayClient(gateway_url="http://test:8080")

        # Mock HTTP client
        mock_http = AsyncMock()
        mock_http.close = AsyncMock()
        client._http_client = mock_http

        async with client:
            assert not client._is_closed

        assert client._is_closed
        mock_http.close.assert_called_once()
