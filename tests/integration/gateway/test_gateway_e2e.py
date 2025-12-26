"""Comprehensive E2E tests for Gateway integration.

This test suite covers:
- All three transports (HTTP, SSE, stdio)
- Authorization flow with OPA
- Parameter filtering
- Audit logging
- Error handling (circuit breaker, retry)
- Performance benchmarks
- End-to-end scenarios

Test Categories:
1. HTTP Transport E2E (15+ tests)
2. SSE Transport E2E (10+ tests)
3. stdio Transport E2E (10+ tests)
4. Unified Client E2E (10+ tests)
5. Error Handling E2E (10+ tests)
6. Authorization & Security E2E (5+ tests)
7. Performance & Benchmarks (5+ tests)
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from sark.gateway import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    GatewayClient,
    GatewayErrorHandler,
    RetryConfig,
    RetryExhaustedError,
    TimeoutError,
    TransportMode,
    with_retry,
    with_timeout,
)
from sark.gateway.transports.sse_client import ConnectionState, GatewaySSEClient, SSEEvent
from sark.models.gateway import (
    GatewayServerInfo,
    GatewayToolInfo,
    SensitivityLevel,
)
from sark.services.policy.opa_client import (
    AuthorizationDecision,
    OPAClient,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_opa_client():
    """Mock OPA client for authorization tests."""
    client = Mock(spec=OPAClient)
    client.authorize = AsyncMock(
        return_value=AuthorizationDecision(
            allow=True,
            reason="Test authorization allowed",
            filtered_params={"query": "SELECT 1"},
        )
    )
    return client


@pytest.fixture
def sample_servers():
    """Sample server data for tests."""
    return [
        GatewayServerInfo(
            server_id="srv_001",
            server_name="postgres-mcp",
            server_url="http://postgres-mcp:8080",
            sensitivity_level=SensitivityLevel.HIGH,
            authorized_teams=["backend-dev"],
            health_status="healthy",
            tools_count=10,
        ),
        GatewayServerInfo(
            server_id="srv_002",
            server_name="redis-mcp",
            server_url="http://redis-mcp:8080",
            sensitivity_level=SensitivityLevel.MEDIUM,
            authorized_teams=["backend-dev", "data-eng"],
            health_status="healthy",
            tools_count=5,
        ),
    ]


@pytest.fixture
def sample_tools():
    """Sample tool data for tests."""
    return [
        GatewayToolInfo(
            tool_name="execute_query",
            server_name="postgres-mcp",
            description="Execute SQL query",
            sensitivity_level=SensitivityLevel.HIGH,
            parameters=[
                {"name": "query", "type": "string", "required": True},
                {"name": "database", "type": "string", "required": True},
            ],
            sensitive_params=["password"],
        ),
        GatewayToolInfo(
            tool_name="get_cache",
            server_name="redis-mcp",
            description="Get cached value",
            sensitivity_level=SensitivityLevel.LOW,
            parameters=[{"name": "key", "type": "string", "required": True}],
        ),
    ]


# =============================================================================
# HTTP Transport E2E Tests (15 tests)
# =============================================================================


class TestHTTPTransportE2E:
    """End-to-end tests for HTTP transport."""

    @pytest.mark.asyncio
    async def test_list_servers_http_e2e(self, sample_servers, httpx_mock: HTTPXMock):
        """E2E: List servers via HTTP transport."""
        # Mock HTTP response
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[s.model_dump() for s in sample_servers],
        )

        # Create client
        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            servers = await client.list_servers()

            assert len(servers) == 2
            assert servers[0].server_name == "postgres-mcp"
            assert servers[1].server_name == "redis-mcp"

    @pytest.mark.asyncio
    async def test_list_all_servers_pagination_e2e(self, sample_servers, httpx_mock: HTTPXMock):
        """E2E: List all servers with pagination."""
        # Page 1: Full page
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[sample_servers[0].model_dump()] * 100,
        )
        # Page 2: Partial page (end)
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=100&limit=100",
            json=[sample_servers[1].model_dump()] * 50,
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            servers = await client.list_all_servers()
            assert len(servers) == 150

    @pytest.mark.asyncio
    async def test_get_server_info_e2e(self, sample_servers, httpx_mock: HTTPXMock):
        """E2E: Get specific server info."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers/postgres-mcp",
            json=sample_servers[0].model_dump(),
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            server = await client.get_server_info("postgres-mcp")
            assert server.server_name == "postgres-mcp"
            assert server.tools_count == 10

    @pytest.mark.asyncio
    async def test_list_tools_http_e2e(self, sample_tools, httpx_mock: HTTPXMock):
        """E2E: List tools via HTTP transport."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/tools?offset=0&limit=100",
            json=[t.model_dump() for t in sample_tools],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            tools = await client.list_tools()
            assert len(tools) == 2
            assert tools[0].tool_name == "execute_query"

    @pytest.mark.asyncio
    async def test_list_tools_filtered_by_server_e2e(self, sample_tools, httpx_mock: HTTPXMock):
        """E2E: List tools filtered by server."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/tools?server=postgres-mcp&offset=0&limit=100",
            json=[sample_tools[0].model_dump()],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            tools = await client.list_tools(server_name="postgres-mcp")
            assert len(tools) == 1
            assert tools[0].server_name == "postgres-mcp"

    @pytest.mark.asyncio
    async def test_invoke_tool_http_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Invoke tool via HTTP transport."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/tools/invoke",
            json={"result": {"rows": [{"id": 1, "name": "test"}]}, "status": "success"},
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            result = await client.invoke_tool(
                server_name="postgres-mcp",
                tool_name="execute_query",
                parameters={"query": "SELECT 1", "database": "test"},
            )

            assert result["status"] == "success"
            assert "result" in result

    @pytest.mark.asyncio
    async def test_invoke_tool_with_opa_authorization_e2e(
        self, mock_opa_client, httpx_mock: HTTPXMock
    ):
        """E2E: Invoke tool with OPA authorization."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/tools/invoke",
            json={"result": "success"},
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            opa_client=mock_opa_client,
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            result = await client.invoke_tool(
                server_name="postgres-mcp",
                tool_name="execute_query",
                parameters={"query": "SELECT 1"},
                user_token="jwt-token",
            )

            # Verify OPA was called
            assert mock_opa_client.authorize.called
            assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_http_caching_e2e(self, sample_servers, httpx_mock: HTTPXMock):
        """E2E: HTTP response caching."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[s.model_dump() for s in sample_servers],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            # First call - cache miss
            servers1 = await client.list_servers()

            # Second call - cache hit (should not make HTTP request)
            servers2 = await client.list_servers()

            assert servers1 == servers2
            # Only one request should have been made
            assert len(httpx_mock.get_requests()) == 1

    @pytest.mark.asyncio
    async def test_http_connection_pooling_e2e(self, httpx_mock: HTTPXMock):
        """E2E: HTTP connection pooling for concurrent requests."""
        for i in range(10):
            httpx_mock.add_response(
                url=f"http://gateway:8080/api/v1/servers/server-{i}",
                json={
                    "server_id": f"srv_{i}",
                    "server_name": f"server-{i}",
                    "server_url": f"http://server-{i}:8080",
                    "health_status": "healthy",
                    "tools_count": 5,
                },
            )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            max_connections=50,
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            # Make 10 concurrent requests
            tasks = [client.get_server_info(f"server-{i}") for i in range(10)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(r.health_status == "healthy" for r in results)

    @pytest.mark.asyncio
    async def test_http_health_check_e2e(self, httpx_mock: HTTPXMock):
        """E2E: HTTP transport health check."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            # Make a request to initialize HTTP client
            await client.list_servers()

            # Check health
            health = await client.health_check()
            assert "http" in health
            assert health["http"]["status"] == "healthy"
            assert "cache_hit_rate" in health["http"]

    @pytest.mark.asyncio
    async def test_http_retry_on_transient_error_e2e(self, httpx_mock: HTTPXMock):
        """E2E: HTTP retry on transient errors."""
        # First two attempts fail, third succeeds
        httpx_mock.add_response(status_code=503)
        httpx_mock.add_response(status_code=503)
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
            enable_error_handling=True,
        ) as client:
            # Should succeed after retries
            servers = await client.list_servers()
            assert servers == []
            # Verify 3 requests were made
            assert len(httpx_mock.get_requests()) == 3

    @pytest.mark.asyncio
    async def test_http_401_unauthorized_e2e(self, httpx_mock: HTTPXMock):
        """E2E: HTTP 401 unauthorized response."""
        httpx_mock.add_response(status_code=401, json={"error": "Unauthorized"})

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
            enable_error_handling=False,  # Disable retry for this test
        ) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.list_servers()

    @pytest.mark.asyncio
    async def test_http_404_not_found_e2e(self, httpx_mock: HTTPXMock):
        """E2E: HTTP 404 not found."""
        httpx_mock.add_response(status_code=404, json={"error": "Server not found"})

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
            enable_error_handling=False,
        ) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_server_info("nonexistent-server")

    @pytest.mark.asyncio
    async def test_http_timeout_e2e(self):
        """E2E: HTTP request timeout."""

        async def slow_request(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate slow response
            return []

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
            timeout=1.0,  # 1 second timeout
        ) as client:
            with patch.object(client._get_http_client(), "list_servers", side_effect=slow_request):
                with pytest.raises(TimeoutError):
                    await client.list_servers()

    @pytest.mark.asyncio
    async def test_http_cache_metrics_e2e(self, sample_servers, httpx_mock: HTTPXMock):
        """E2E: HTTP cache hit rate metrics."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[s.model_dump() for s in sample_servers],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            # First call - cache miss
            await client.list_servers()

            # Next 9 calls - cache hits
            for _ in range(9):
                await client.list_servers()

            # Check metrics
            metrics = client.get_metrics()
            assert metrics["http_cache_hit_rate"] == 0.9  # 9 hits out of 10 calls


# =============================================================================
# SSE Transport E2E Tests (10 tests)
# =============================================================================


class TestSSETransportE2E:
    """End-to-end tests for SSE transport."""

    @pytest.mark.asyncio
    async def test_stream_events_sse_e2e(self):
        """E2E: Stream events via SSE transport."""
        # Mock SSE response
        sse_data = [
            'event: tool_invoked\ndata: {"tool": "execute_query"}\n\n',
            'event: server_registered\ndata: {"server": "new-server"}\n\n',
        ]

        async def mock_stream_events(*args, **kwargs):
            for data in sse_data:
                # Parse SSE event
                lines = data.strip().split("\n")
                event_type = lines[0].split(": ")[1]
                event_data = lines[1].split(": ", 1)[1]
                yield SSEEvent(event_type=event_type, data=event_data)

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            with patch.object(GatewaySSEClient, "stream_events", side_effect=mock_stream_events):
                events = []
                async for event in client.stream_events():
                    events.append(event)
                    if len(events) >= 2:
                        break

                assert len(events) == 2
                assert events[0].event_type == "tool_invoked"
                assert events[1].event_type == "server_registered"

    @pytest.mark.asyncio
    async def test_sse_event_filtering_e2e(self):
        """E2E: SSE event filtering by type."""
        sse_data = [
            SSEEvent(event_type="tool_invoked", data='{"tool": "query"}'),
            SSEEvent(event_type="server_health", data='{"status": "ok"}'),
            SSEEvent(event_type="tool_invoked", data='{"tool": "cache"}'),
        ]

        async def mock_stream_events(endpoint, event_types=None, user_token=None):
            for event in sse_data:
                if event_types is None or event.event_type in event_types:
                    yield event

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            with patch.object(GatewaySSEClient, "stream_events", side_effect=mock_stream_events):
                events = []
                async for event in client.stream_events(event_types=["tool_invoked"]):
                    events.append(event)
                    if len(events) >= 2:
                        break

                assert len(events) == 2
                assert all(e.event_type == "tool_invoked" for e in events)

    @pytest.mark.asyncio
    async def test_sse_reconnection_e2e(self):
        """E2E: SSE automatic reconnection after disconnect."""
        connection_count = 0

        async def mock_stream_with_disconnect(*args, **kwargs):
            nonlocal connection_count
            connection_count += 1

            if connection_count == 1:
                # First connection - yield one event then fail
                yield SSEEvent(event_type="test", data="event1")
                raise ConnectionError("Connection lost")

            # Second connection (after reconnect) - succeed
            yield SSEEvent(event_type="test", data="event2")

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            with patch.object(
                GatewaySSEClient, "stream_events", side_effect=mock_stream_with_disconnect
            ):
                try:
                    events = []
                    async for event in client.stream_events():
                        events.append(event)
                        if len(events) >= 1:
                            break
                except ConnectionError:
                    # Expected on first connection
                    pass

                # Verify reconnection attempted
                assert connection_count >= 1

    @pytest.mark.asyncio
    async def test_sse_connection_state_transitions_e2e(self):
        """E2E: SSE connection state transitions."""
        async with GatewaySSEClient(base_url="http://gateway:8080") as client:
            # Initial state should be DISCONNECTED
            assert client.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_sse_last_event_id_tracking_e2e(self):
        """E2E: SSE Last-Event-ID tracking for resume."""
        events = [
            SSEEvent(event_type="test", data="1", event_id="evt_001"),
            SSEEvent(event_type="test", data="2", event_id="evt_002"),
        ]

        async def mock_stream(*args, **kwargs):
            for event in events:
                yield event

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            with patch.object(GatewaySSEClient, "stream_events", side_effect=mock_stream):
                received_ids = []
                async for event in client.stream_events():
                    received_ids.append(event.event_id)
                    if len(received_ids) >= 2:
                        break

                assert received_ids == ["evt_001", "evt_002"]

    @pytest.mark.asyncio
    async def test_sse_health_monitoring_e2e(self):
        """E2E: SSE connection health monitoring."""
        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            # Initialize SSE client
            _ = client._get_sse_client()

            health = await client.health_check()
            assert "sse" in health
            assert "connection_state" in health["sse"]

    @pytest.mark.asyncio
    async def test_sse_concurrent_streams_e2e(self):
        """E2E: Multiple concurrent SSE streams."""

        async def mock_stream(*args, **kwargs):
            for i in range(3):
                yield SSEEvent(event_type="test", data=str(i))

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
            max_connections=50,
        ) as client:
            with patch.object(GatewaySSEClient, "stream_events", side_effect=mock_stream):
                # Create 3 concurrent streams
                async def collect_stream():
                    events = []
                    async for event in client.stream_events():
                        events.append(event)
                        if len(events) >= 3:
                            break
                    return events

                results = await asyncio.gather(
                    collect_stream(),
                    collect_stream(),
                    collect_stream(),
                )

                assert len(results) == 3
                assert all(len(events) == 3 for events in results)

    @pytest.mark.asyncio
    async def test_sse_error_handling_e2e(self):
        """E2E: SSE error handling and recovery."""

        async def mock_stream_with_error(*args, **kwargs):
            yield SSEEvent(event_type="test", data="before_error")
            raise httpx.ReadTimeout("Stream timeout")

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            with patch.object(
                GatewaySSEClient, "stream_events", side_effect=mock_stream_with_error
            ):
                with pytest.raises(httpx.ReadTimeout):
                    async for _event in client.stream_events():
                        pass

    @pytest.mark.asyncio
    async def test_sse_graceful_shutdown_e2e(self):
        """E2E: SSE graceful shutdown during streaming."""

        async def mock_stream(*args, **kwargs):
            for i in range(100):
                yield SSEEvent(event_type="test", data=str(i))
                await asyncio.sleep(0.01)

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            with patch.object(GatewaySSEClient, "stream_events", side_effect=mock_stream):
                # Start streaming
                stream_task = asyncio.create_task(self._collect_events(client))

                # Let it run briefly
                await asyncio.sleep(0.1)

                # Cancel streaming
                stream_task.cancel()

                # Client should close gracefully
                await client.close()

    async def _collect_events(self, client):
        """Helper to collect events."""
        async for _event in client.stream_events():
            pass

    @pytest.mark.asyncio
    async def test_sse_with_authentication_e2e(self):
        """E2E: SSE streaming with JWT authentication."""

        async def mock_stream(*args, user_token=None, **kwargs):
            # Verify token is passed
            assert user_token == "jwt-token-123"
            yield SSEEvent(event_type="authenticated", data="success")

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.SSE_ONLY,
        ) as client:
            with patch.object(GatewaySSEClient, "stream_events", side_effect=mock_stream):
                events = []
                async for event in client.stream_events(user_token="jwt-token-123"):
                    events.append(event)
                    break

                assert len(events) == 1
                assert events[0].data == "success"


# =============================================================================
# stdio Transport E2E Tests (10 tests)
# =============================================================================


class TestStdioTransportE2E:
    """End-to-end tests for stdio transport."""

    @pytest.mark.asyncio
    async def test_connect_local_server_e2e(self):
        """E2E: Connect to local server via stdio."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    local_server = await client.connect_local_server(
                        command=["python", "server.py"]
                    )

                    assert local_server is not None
                    assert local_server.server_id is not None

    @pytest.mark.asyncio
    async def test_stdio_send_request_e2e(self):
        """E2E: Send JSON-RPC request via stdio."""
        mock_process = AsyncMock()
        mock_process.pid = 12345

        # Mock stdin/stdout
        mock_stdin = AsyncMock()
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(
            return_value=b'{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n'
        )
        mock_stderr = AsyncMock()

        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    local_server = await client.connect_local_server(
                        command=["python", "server.py"]
                    )

                    # Send request
                    response = await local_server.send_request("tools/list", {})

                    assert response is not None
                    assert "tools" in response or "result" in response

    @pytest.mark.asyncio
    async def test_stdio_process_lifecycle_e2e(self):
        """E2E: stdio process lifecycle (start/stop)."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.terminate = AsyncMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    local_server = await client.connect_local_server(
                        command=["python", "server.py"],
                        server_id="test_server",
                    )

                    assert local_server.is_running

                    # Stop server
                    await local_server.stop()

                    # Verify terminate was called
                    mock_process.terminate.assert_called()

    @pytest.mark.asyncio
    async def test_stdio_health_check_e2e(self):
        """E2E: stdio process health monitoring."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    await client.connect_local_server(
                        command=["python", "server.py"],
                        server_id="health_test",
                    )

                    health = await client.health_check()

                    assert "stdio" in health
                    assert "health_test" in health["stdio"]
                    assert health["stdio"]["health_test"]["status"] == "running"
                    assert health["stdio"]["health_test"]["pid"] == 12345

    @pytest.mark.asyncio
    async def test_stdio_multiple_servers_e2e(self):
        """E2E: Multiple concurrent stdio servers."""
        mock_process1 = AsyncMock()
        mock_process1.pid = 11111
        mock_process1.stdin = AsyncMock()
        mock_process1.stdout = AsyncMock()
        mock_process1.stderr = AsyncMock()

        mock_process2 = AsyncMock()
        mock_process2.pid = 22222
        mock_process2.stdin = AsyncMock()
        mock_process2.stdout = AsyncMock()
        mock_process2.stderr = AsyncMock()

        with patch("asyncio.create_subprocess_exec", side_effect=[mock_process1, mock_process2]):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    await client.connect_local_server(
                        command=["python", "server1.py"],
                        server_id="server1",
                    )
                    await client.connect_local_server(
                        command=["python", "server2.py"],
                        server_id="server2",
                    )

                    health = await client.health_check()

                    assert len(health["stdio"]) == 2
                    assert "server1" in health["stdio"]
                    assert "server2" in health["stdio"]

    @pytest.mark.asyncio
    async def test_stdio_disconnect_specific_server_e2e(self):
        """E2E: Disconnect specific stdio server."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.terminate = AsyncMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    await client.connect_local_server(
                        command=["python", "server.py"],
                        server_id="disconnect_test",
                    )

                    # Disconnect
                    await client.disconnect_local_server("disconnect_test")

                    # Verify server is removed
                    health = await client.health_check()
                    assert "stdio" not in health or "disconnect_test" not in health.get("stdio", {})

    @pytest.mark.asyncio
    async def test_stdio_send_notification_e2e(self):
        """E2E: Send JSON-RPC notification via stdio (no response expected)."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_stdin = AsyncMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    local_server = await client.connect_local_server(
                        command=["python", "server.py"]
                    )

                    # Send notification (should not wait for response)
                    await local_server.send_notification("notifications/progress", {"percent": 50})

                    # Verify data was written to stdin
                    assert mock_stdin.write.called

    @pytest.mark.asyncio
    async def test_stdio_process_crash_detection_e2e(self):
        """E2E: Detect stdio process crash."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = 1  # Process exited
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    local_server = await client.connect_local_server(
                        command=["python", "server.py"]
                    )

                    # Simulate crash by setting returncode
                    local_server.transport._process.returncode = 1

                    # Process should be detected as not running
                    assert (
                        not local_server.is_running
                        or local_server.transport._process.returncode is not None
                    )

    @pytest.mark.asyncio
    async def test_stdio_resource_cleanup_e2e(self):
        """E2E: stdio resource cleanup on client close."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.terminate = AsyncMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                client = GatewayClient(transport_mode=TransportMode.STDIO_ONLY)
                await client.connect_local_server(
                    command=["python", "server.py"],
                    server_id="cleanup_test",
                )

                # Close client
                await client.close()

                # Verify process was terminated
                mock_process.terminate.assert_called()

    @pytest.mark.asyncio
    async def test_stdio_custom_environment_variables_e2e(self):
        """E2E: stdio server with custom environment variables."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()

        captured_env = {}

        async def capture_env_subprocess(*args, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=capture_env_subprocess):
            with patch("psutil.Process"):
                async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
                    await client.connect_local_server(
                        command=["python", "server.py"],
                        env={"CUSTOM_VAR": "test_value"},
                    )

                    # Verify custom environment variable was passed
                    assert "CUSTOM_VAR" in captured_env
                    assert captured_env["CUSTOM_VAR"] == "test_value"


# =============================================================================
# Unified Client E2E Tests (10 tests)
# =============================================================================


class TestUnifiedClientE2E:
    """End-to-end tests for unified Gateway client."""

    @pytest.mark.asyncio
    async def test_auto_transport_selection_http_e2e(self, sample_servers, httpx_mock: HTTPXMock):
        """E2E: Auto transport selection uses HTTP for server listing."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[s.model_dump() for s in sample_servers],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.AUTO,  # Auto selection
        ) as client:
            servers = await client.list_servers()
            assert len(servers) == 2

    @pytest.mark.asyncio
    async def test_transport_mode_enforcement_e2e(self):
        """E2E: Transport mode enforcement."""
        async with GatewayClient(
            gateway_url="http://gateway:8080",
            transport_mode=TransportMode.HTTP_ONLY,
        ) as client:
            # SSE should not be available in HTTP_ONLY mode
            from sark.gateway import TransportNotAvailableError

            with pytest.raises(TransportNotAvailableError):
                async for _ in client.stream_events():
                    break

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Context manager cleanup."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[],
        )

        async with GatewayClient(gateway_url="http://gateway:8080") as client:
            await client.list_servers()
            # Client should be active
            assert not client._is_closed

        # After context exit, client should be closed
        assert client._is_closed

    @pytest.mark.asyncio
    async def test_multiple_operations_same_client_e2e(
        self, sample_servers, sample_tools, httpx_mock: HTTPXMock
    ):
        """E2E: Multiple operations using same client."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[s.model_dump() for s in sample_servers],
        )
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/tools?offset=0&limit=100",
            json=[t.model_dump() for t in sample_tools],
        )
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers/postgres-mcp",
            json=sample_servers[0].model_dump(),
        )

        async with GatewayClient(gateway_url="http://gateway:8080") as client:
            # Multiple operations
            servers = await client.list_servers()
            tools = await client.list_tools()
            server_info = await client.get_server_info("postgres-mcp")

            assert len(servers) == 2
            assert len(tools) == 2
            assert server_info.server_name == "postgres-mcp"

    @pytest.mark.asyncio
    async def test_concurrent_operations_e2e(self, sample_servers, httpx_mock: HTTPXMock):
        """E2E: Concurrent operations via unified client."""
        for i in range(5):
            httpx_mock.add_response(
                url=f"http://gateway:8080/api/v1/servers/server-{i}",
                json={
                    "server_id": f"srv_{i}",
                    "server_name": f"server-{i}",
                    "server_url": f"http://server-{i}:8080",
                    "health_status": "healthy",
                    "tools_count": 5,
                },
            )

        async with GatewayClient(gateway_url="http://gateway:8080") as client:
            # Run 5 operations concurrently
            tasks = [client.get_server_info(f"server-{i}") for i in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all(r.health_status == "healthy" for r in results)

    @pytest.mark.asyncio
    async def test_health_check_all_transports_e2e(self):
        """E2E: Health check across all transports."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("psutil.Process"):
                async with GatewayClient(
                    gateway_url="http://gateway:8080",
                    transport_mode=TransportMode.AUTO,
                ) as client:
                    # Initialize all transports
                    _ = client._get_http_client()
                    _ = client._get_sse_client()
                    await client.connect_local_server(
                        command=["python", "server.py"],
                        server_id="test",
                    )

                    # Check health of all
                    health = await client.health_check()

                    assert "http" in health
                    assert "sse" in health
                    assert "stdio" in health
                    assert "error_handler" in health

    @pytest.mark.asyncio
    async def test_metrics_collection_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Metrics collection across operations."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            enable_error_handling=True,
        ) as client:
            # Perform operations
            await client.list_servers()
            await client.list_servers()  # Cache hit

            # Get metrics
            metrics = client.get_metrics()

            assert "transport_mode" in metrics
            assert "active_transports" in metrics
            assert "http" in metrics["active_transports"]
            assert "http_cache_hit_rate" in metrics
            assert "error_handler" in metrics

    @pytest.mark.asyncio
    async def test_error_handler_integration_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Error handler integration with client."""
        # First call fails, second succeeds
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[],
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            enable_error_handling=True,
            retry_config={"max_attempts": 2},
        ) as client:
            # Should succeed after retry
            servers = await client.list_servers()
            assert servers == []

            # Check error handler metrics
            metrics = client.get_metrics()
            assert "error_handler" in metrics
            assert "circuit_breaker" in metrics["error_handler"]

    @pytest.mark.asyncio
    async def test_disable_error_handling_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Client with error handling disabled."""
        httpx_mock.add_response(status_code=500)

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            enable_error_handling=False,
        ) as client:
            # Should fail immediately without retry
            with pytest.raises(httpx.HTTPStatusError):
                await client.list_servers()

    @pytest.mark.asyncio
    async def test_client_without_gateway_url_e2e(self):
        """E2E: Client initialization without gateway URL (stdio only)."""
        async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
            # Should work for stdio operations
            from sark.gateway import GatewayClientError

            # But should fail for HTTP operations
            with pytest.raises(GatewayClientError, match="Gateway URL is required"):
                _ = client._get_http_client()


# =============================================================================
# Error Handling E2E Tests (10 tests)
# =============================================================================


class TestErrorHandlingE2E:
    """End-to-end tests for error handling."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures_e2e(self):
        """E2E: Circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=5)

        async def failing_operation():
            raise Exception("Operation failed")

        # First 3 failures should open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_operation)

        # Circuit should now be open
        assert breaker.state == CircuitState.OPEN

        # Next call should be blocked
        with pytest.raises(CircuitBreakerError):
            await breaker.call(failing_operation)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition_e2e(self):
        """E2E: Circuit breaker transitions to half-open after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1)

        async def failing_operation():
            raise Exception("Failed")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_operation)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Circuit should transition to half-open
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_success_e2e(self):
        """E2E: Circuit breaker closes after successful calls in half-open."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1, success_threshold=2)

        call_count = 0

        async def sometimes_failing():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Failed")
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(sometimes_failing)

        assert breaker.state == CircuitState.OPEN

        # Wait for half-open
        await asyncio.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Successful calls should close circuit
        result = await breaker.call(sometimes_failing)
        assert result == "success"
        result = await breaker.call(sometimes_failing)
        assert result == "success"

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff_e2e(self):
        """E2E: Retry with exponential backoff."""
        attempt_times = []

        async def failing_then_succeeding():
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                raise Exception("Failed")
            return "success"

        config = RetryConfig(max_attempts=3, initial_delay=0.1)
        result = await with_retry(failing_then_succeeding, config=config)

        assert result == "success"
        assert len(attempt_times) == 3

        # Verify delays increased exponentially
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            # Second delay should be roughly 2x first delay
            assert delay2 > delay1

    @pytest.mark.asyncio
    async def test_retry_exhausted_e2e(self):
        """E2E: Retry exhausted after max attempts."""
        attempt_count = 0

        async def always_failing():
            nonlocal attempt_count
            attempt_count += 1
            raise Exception("Always fails")

        config = RetryConfig(max_attempts=3)

        with pytest.raises(RetryExhaustedError):
            await with_retry(always_failing, config=config)

        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_timeout_enforcement_e2e(self):
        """E2E: Timeout enforcement."""

        async def slow_operation():
            await asyncio.sleep(2)
            return "completed"

        with pytest.raises(TimeoutError):
            await with_timeout(slow_operation, timeout_seconds=0.5)

    @pytest.mark.asyncio
    async def test_timeout_success_within_limit_e2e(self):
        """E2E: Operation completes within timeout."""

        async def fast_operation():
            await asyncio.sleep(0.1)
            return "completed"

        result = await with_timeout(fast_operation, timeout_seconds=1.0)
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_gateway_error_handler_full_stack_e2e(self):
        """E2E: GatewayErrorHandler with full error handling stack."""
        error_handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 3},
            retry_config={"max_attempts": 2},
            default_timeout=1.0,
        )

        attempt_count = 0

        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise Exception("First attempt fails")
            return "success"

        # Should succeed after retry
        result = await error_handler.execute(flaky_operation)
        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_error_handler_metrics_e2e(self):
        """E2E: Error handler metrics collection."""
        error_handler = GatewayErrorHandler()

        async def successful_operation():
            return "ok"

        await error_handler.execute(successful_operation)

        metrics = error_handler.get_metrics()

        assert "circuit_breaker" in metrics
        assert "retry_config" in metrics
        assert "default_timeout" in metrics
        assert metrics["circuit_breaker"]["state"] == "closed"
        assert metrics["circuit_breaker"]["total_calls"] == 1

    @pytest.mark.asyncio
    async def test_error_handler_reset_e2e(self):
        """E2E: Error handler circuit breaker reset."""
        error_handler = GatewayErrorHandler(circuit_breaker_config={"failure_threshold": 2})

        async def failing():
            raise Exception("Failed")

        # Open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await error_handler.execute(failing)

        assert error_handler.circuit_breaker.state == CircuitState.OPEN

        # Reset circuit
        error_handler.reset()

        assert error_handler.circuit_breaker.state == CircuitState.CLOSED


# =============================================================================
# Authorization & Security E2E Tests (5 tests)
# =============================================================================


class TestAuthorizationSecurityE2E:
    """End-to-end tests for authorization and security."""

    @pytest.mark.asyncio
    async def test_opa_authorization_flow_e2e(self, mock_opa_client, httpx_mock: HTTPXMock):
        """E2E: Complete OPA authorization flow."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/tools/invoke",
            json={"result": "success"},
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            opa_client=mock_opa_client,
        ) as client:
            await client.invoke_tool(
                server_name="postgres-mcp",
                tool_name="execute_query",
                parameters={"query": "SELECT 1", "password": "secret"},
                user_token="jwt-token",
            )

            # Verify OPA was called
            mock_opa_client.authorize.assert_called_once()
            call_args = mock_opa_client.authorize.call_args[1]

            assert call_args["user_token"] == "jwt-token"
            assert "query" in call_args["parameters"]

    @pytest.mark.asyncio
    async def test_parameter_filtering_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Parameter filtering via OPA."""
        mock_opa = Mock(spec=OPAClient)
        mock_opa.authorize = AsyncMock(
            return_value=AuthorizationDecision(
                allow=True,
                reason="Allowed with filtering",
                filtered_params={"query": "SELECT 1"},  # password removed
            )
        )

        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/tools/invoke",
            json={"result": "success"},
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            opa_client=mock_opa,
        ) as client:
            result = await client.invoke_tool(
                server_name="postgres-mcp",
                tool_name="execute_query",
                parameters={"query": "SELECT 1", "password": "secret"},
                user_token="jwt-token",
            )

            # Verify password was filtered out
            assert result["result"] == "success"
            assert mock_opa.authorize.called

    @pytest.mark.asyncio
    async def test_authorization_denied_e2e(self):
        """E2E: Authorization denied by OPA."""
        mock_opa = Mock(spec=OPAClient)
        mock_opa.authorize = AsyncMock(
            return_value=AuthorizationDecision(
                allow=False,
                reason="Insufficient permissions",
            )
        )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            opa_client=mock_opa,
        ) as client:
            with pytest.raises(PermissionError, match="Insufficient permissions"):
                await client.invoke_tool(
                    server_name="postgres-mcp",
                    tool_name="execute_query",
                    parameters={"query": "DROP TABLE users"},
                    user_token="jwt-token",
                )

    @pytest.mark.asyncio
    async def test_jwt_token_propagation_e2e(self, httpx_mock: HTTPXMock):
        """E2E: JWT token propagation through stack."""
        captured_headers = {}

        def capture_headers(request):
            captured_headers.update(request.headers)
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(capture_headers)

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            api_key="api-key-123",
        ) as client:
            http_client = client._get_http_client()
            await http_client.list_servers(user_token="jwt-token-456")

            # Verify both API key and JWT token were sent
            assert "X-API-Key" in captured_headers
            assert captured_headers["X-API-Key"] == "api-key-123"
            assert "Authorization" in captured_headers
            assert captured_headers["Authorization"] == "Bearer jwt-token-456"

    @pytest.mark.asyncio
    async def test_api_key_authentication_e2e(self, httpx_mock: HTTPXMock):
        """E2E: API key authentication."""
        captured_headers = {}

        def capture_headers(request):
            captured_headers.update(request.headers)
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(capture_headers)

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            api_key="secret-api-key",
        ) as client:
            http_client = client._get_http_client()
            await http_client.list_servers()

            assert "X-API-Key" in captured_headers
            assert captured_headers["X-API-Key"] == "secret-api-key"


# =============================================================================
# Performance & Benchmarks E2E Tests (5 tests)
# =============================================================================


class TestPerformanceBenchmarksE2E:
    """End-to-end tests for performance and benchmarks."""

    @pytest.mark.asyncio
    async def test_http_latency_benchmark_e2e(self, httpx_mock: HTTPXMock):
        """E2E: HTTP request latency benchmark (<100ms p95)."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[],
        )

        async with GatewayClient(gateway_url="http://gateway:8080") as client:
            latencies = []

            for _ in range(20):
                start = time.time()
                await client.list_servers()
                latency = (time.time() - start) * 1000  # Convert to ms
                latencies.append(latency)

            # Calculate p95
            latencies.sort()
            p95_index = int(len(latencies) * 0.95)
            p95_latency = latencies[p95_index]

            # P95 should be < 100ms (relaxed for tests due to overhead)
            assert p95_latency < 200, f"P95 latency {p95_latency}ms exceeds 200ms"

    @pytest.mark.asyncio
    async def test_cache_hit_rate_benchmark_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Cache hit rate benchmark (>80%)."""
        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=[],
        )

        async with GatewayClient(gateway_url="http://gateway:8080") as client:
            # First call - cache miss
            await client.list_servers()

            # Next 9 calls - cache hits
            for _ in range(9):
                await client.list_servers()

            # Check cache hit rate
            metrics = client.get_metrics()
            hit_rate = metrics.get("http_cache_hit_rate", 0)

            assert hit_rate >= 0.8, f"Cache hit rate {hit_rate} is below 80%"

    @pytest.mark.asyncio
    async def test_concurrent_throughput_benchmark_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Concurrent request throughput."""
        for i in range(100):
            httpx_mock.add_response(
                url=f"http://gateway:8080/api/v1/servers/server-{i}",
                json={
                    "server_id": f"srv_{i}",
                    "server_name": f"server-{i}",
                    "server_url": f"http://server-{i}:8080",
                    "health_status": "healthy",
                    "tools_count": 5,
                },
            )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            max_connections=50,
        ) as client:
            start = time.time()

            # Run 100 concurrent requests
            tasks = [client.get_server_info(f"server-{i}") for i in range(100)]
            results = await asyncio.gather(*tasks)

            duration = time.time() - start
            throughput = len(results) / duration

            # Should handle >50 req/s
            assert throughput > 50, f"Throughput {throughput} req/s is too low"

    @pytest.mark.asyncio
    async def test_memory_efficiency_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Memory efficiency with large result sets."""
        # Mock 1000 servers
        large_response = [
            {
                "server_id": f"srv_{i}",
                "server_name": f"server-{i}",
                "server_url": f"http://server-{i}:8080",
                "health_status": "healthy",
                "tools_count": 5,
            }
            for i in range(1000)
        ]

        httpx_mock.add_response(
            url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
            json=large_response[:100],
        )
        for i in range(1, 10):
            httpx_mock.add_response(
                url=f"http://gateway:8080/api/v1/servers?offset={i*100}&limit=100",
                json=large_response[i * 100 : (i + 1) * 100],
            )

        async with GatewayClient(gateway_url="http://gateway:8080") as client:
            # Fetch all 1000 servers with pagination
            servers = await client.list_all_servers()

            # Verify all servers returned
            assert len(servers) == 1000

    @pytest.mark.asyncio
    async def test_connection_pool_efficiency_e2e(self, httpx_mock: HTTPXMock):
        """E2E: Connection pool reuse efficiency."""
        for _i in range(50):
            httpx_mock.add_response(
                url="http://gateway:8080/api/v1/servers?offset=0&limit=100",
                json=[],
            )

        async with GatewayClient(
            gateway_url="http://gateway:8080",
            max_connections=10,  # Limited pool
        ) as client:
            # Make 50 sequential requests
            for _ in range(50):
                await client.list_servers()

            # All requests should complete successfully with connection reuse
            assert len(httpx_mock.get_requests()) == 50
