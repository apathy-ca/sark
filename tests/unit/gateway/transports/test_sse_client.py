"""Comprehensive tests for Gateway SSE transport client."""

from unittest.mock import MagicMock

import httpx
import pytest

from sark.gateway.transports.sse_client import (
    ConnectionState,
    GatewaySSEClient,
    SSEEvent,
)


class TestSSEEvent:
    """Test suite for SSEEvent class."""

    def test_sse_event_creation_defaults(self):
        """Test creating SSE event with defaults."""
        event = SSEEvent()
        assert event.event_type == "message"
        assert event.data == ""
        assert event.event_id is None
        assert event.retry is None

    def test_sse_event_creation_with_data(self):
        """Test creating SSE event with data."""
        event = SSEEvent(
            event_type="tool_invoked",
            data='{"tool": "test", "result": "success"}',
            event_id="evt-123",
            retry=3000,
        )
        assert event.event_type == "tool_invoked"
        assert "test" in event.data
        assert event.event_id == "evt-123"
        assert event.retry == 3000

    def test_sse_event_repr(self):
        """Test SSE event string representation."""
        event = SSEEvent(event_type="test", data="x" * 100, event_id="123")
        repr_str = repr(event)
        assert "SSEEvent" in repr_str
        assert "test" in repr_str
        assert "123" in repr_str


class TestConnectionState:
    """Test suite for ConnectionState enum."""

    def test_connection_states(self):
        """Test all connection states exist."""
        assert ConnectionState.DISCONNECTED == "disconnected"
        assert ConnectionState.CONNECTING == "connecting"
        assert ConnectionState.CONNECTED == "connected"
        assert ConnectionState.RECONNECTING == "reconnecting"
        assert ConnectionState.CLOSED == "closed"


class TestGatewaySSEClient:
    """Test suite for GatewaySSEClient class."""

    @pytest.fixture
    def client(self):
        """Create SSE client instance."""
        return GatewaySSEClient(
            base_url="http://test-gateway:8080",
            api_key="test-api-key",
            timeout=30.0,
            reconnect_enabled=True,
        )

    @pytest.fixture
    def client_no_reconnect(self):
        """Create SSE client with reconnection disabled."""
        return GatewaySSEClient(
            base_url="http://test-gateway:8080",
            reconnect_enabled=False,
        )

    async def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "http://test-gateway:8080"
        assert client.api_key == "test-api-key"
        assert client.timeout == 30.0
        assert client.reconnect_enabled is True
        assert client.state == ConnectionState.DISCONNECTED
        await client.close()

    async def test_client_context_manager(self):
        """Test client as async context manager."""
        async with GatewaySSEClient(base_url="http://test:8080") as client:
            assert client is not None
            assert client.state != ConnectionState.CLOSED
        # Client should be closed after context

    async def test_get_headers_with_api_key(self, client):
        """Test building headers with API key."""
        headers = client._get_headers()
        assert headers["X-API-Key"] == "test-api-key"
        assert headers["Accept"] == "text/event-stream"
        assert headers["Cache-Control"] == "no-cache"
        await client.close()

    async def test_get_headers_with_user_token(self, client):
        """Test building headers with user token."""
        headers = client._get_headers(user_token="jwt-token-123")
        assert headers["Authorization"] == "Bearer jwt-token-123"
        await client.close()

    async def test_get_headers_with_last_event_id(self, client):
        """Test headers include Last-Event-ID for reconnection."""
        client.last_event_id = "evt-456"
        headers = client._get_headers()
        assert headers["Last-Event-ID"] == "evt-456"
        await client.close()

    def test_parse_sse_line_event_type(self, client):
        """Test parsing SSE event type line."""
        event = SSEEvent()
        result = client._parse_sse_line("event: tool_invoked", event)
        assert result is None  # Not complete yet
        assert event.event_type == "tool_invoked"

    def test_parse_sse_line_data(self, client):
        """Test parsing SSE data line."""
        event = SSEEvent()
        result = client._parse_sse_line("data: test data", event)
        assert result is None  # Not complete yet
        assert event.data == "test data"

    def test_parse_sse_line_multiline_data(self, client):
        """Test parsing multiline SSE data."""
        event = SSEEvent()
        client._parse_sse_line("data: line 1", event)
        client._parse_sse_line("data: line 2", event)
        assert event.data == "line 1\nline 2"

    def test_parse_sse_line_event_id(self, client):
        """Test parsing SSE event ID."""
        event = SSEEvent()
        result = client._parse_sse_line("id: evt-123", event)
        assert result is None
        assert event.event_id == "evt-123"
        assert client.last_event_id == "evt-123"

    def test_parse_sse_line_retry(self, client):
        """Test parsing SSE retry value."""
        event = SSEEvent()
        result = client._parse_sse_line("retry: 5000", event)
        assert result is None
        assert event.retry == 5000

    def test_parse_sse_line_invalid_retry(self, client):
        """Test parsing invalid retry value."""
        event = SSEEvent()
        client._parse_sse_line("retry: invalid", event)
        assert event.retry is None

    def test_parse_sse_line_comment(self, client):
        """Test parsing SSE comment line."""
        event = SSEEvent()
        result = client._parse_sse_line(": this is a comment", event)
        assert result is None
        assert event.data == ""

    def test_parse_sse_line_empty(self, client):
        """Test parsing empty line (event separator)."""
        event = SSEEvent(event_type="test", data="some data")
        result = client._parse_sse_line("", event)
        assert result is not None
        assert result.event_type == "test"
        assert result.data == "some data"

    def test_parse_sse_line_no_colon(self, client):
        """Test parsing line without colon."""
        event = SSEEvent()
        result = client._parse_sse_line("invalid line", event)
        assert result is None

    async def test_stream_events_basic(self, client):
        """Test basic event streaming."""

        # Create mock async iterator for SSE stream
        async def mock_aiter_lines():
            yield "event: test_event"
            yield "data: test data"
            yield "id: evt-1"
            yield ""  # Event separator
            yield "data: second event"
            yield ""

        # Mock the HTTP client stream method
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        async def mock_stream(*args, **kwargs):
            # Return async context manager
            class MockAsyncContext:
                async def __aenter__(self):
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream

        events = []
        count = 0
        async for event in client.stream_events(endpoint="/api/v1/stream"):
            events.append(event)
            count += 1
            if count >= 2:
                break  # Stop after 2 events

        assert len(events) == 2
        assert events[0].event_type == "test_event"
        assert events[0].data == "test data"
        assert events[1].event_type == "message"  # Default type
        assert events[1].data == "second event"
        await client.close()

    async def test_stream_events_with_filter(self, client):
        """Test streaming events with type filter."""

        async def mock_aiter_lines():
            yield "event: tool_invoked"
            yield "data: tool data"
            yield ""
            yield "event: other_event"
            yield "data: other data"
            yield ""
            yield "event: tool_invoked"
            yield "data: second tool"
            yield ""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream

        events = []
        count = 0
        async for event in client.stream_events(
            endpoint="/api/v1/stream",
            event_types=["tool_invoked"],
        ):
            events.append(event)
            count += 1
            if count >= 2:
                break

        # Should only receive filtered events
        assert len(events) == 2
        assert all(e.event_type == "tool_invoked" for e in events)
        await client.close()

    async def test_stream_audit_events(self, client):
        """Test streaming audit events."""

        async def mock_aiter_lines():
            yield "event: authorization_denied"
            yield "data: audit data"
            yield ""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream

        events = []
        async for event in client.stream_audit_events(user_token="token"):
            events.append(event)
            break

        assert len(events) == 1
        await client.close()

    async def test_stream_server_events(self, client):
        """Test streaming server-specific events."""

        async def mock_aiter_lines():
            yield "event: server_health"
            yield "data: healthy"
            yield ""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream

        events = []
        async for event in client.stream_server_events(
            server_name="postgres-mcp",
            user_token="token",
        ):
            events.append(event)
            break

        assert len(events) == 1
        await client.close()

    async def test_connection_pool_limit(self, client):
        """Test connection pool limit enforcement."""
        # Fill up the connection pool
        for i in range(client._max_streams):
            client._active_streams.add(f"stream-{i}")

        # Next stream should raise error
        async def mock_aiter_lines():
            yield "data: test"
            yield ""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream

        with pytest.raises(RuntimeError, match="Connection pool exhausted"):
            async for event in client.stream_events(endpoint="/test"):
                break

        await client.close()

    async def test_reconnection_on_error(self, client):
        """Test automatic reconnection on connection error."""
        call_count = 0

        async def mock_aiter_lines():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First connection fails
                raise httpx.RequestError("Connection lost")
            # Second connection succeeds
            yield "data: reconnected"
            yield ""

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.raise_for_status = MagicMock()
                    mock_response.aiter_lines = mock_aiter_lines
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream
        client.reconnect_initial_delay = 0.01  # Fast reconnection for test

        events = []
        async for event in client.stream_events(endpoint="/test"):
            events.append(event)
            break

        assert len(events) == 1
        assert call_count >= 2  # Should have reconnected
        await client.close()

    async def test_no_reconnection_when_disabled(self, client_no_reconnect):
        """Test that reconnection doesn't happen when disabled."""

        async def mock_aiter_lines():
            raise httpx.RequestError("Connection lost")

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.raise_for_status = MagicMock()
                    mock_response.aiter_lines = mock_aiter_lines
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client_no_reconnect.client.stream = mock_stream

        with pytest.raises(httpx.RequestError):
            async for event in client_no_reconnect.stream_events(endpoint="/test"):
                pass

        await client_no_reconnect.close()

    async def test_max_retries_exceeded(self, client):
        """Test max retries exceeded."""

        async def mock_aiter_lines():
            raise httpx.RequestError("Persistent error")

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.raise_for_status = MagicMock()
                    mock_response.aiter_lines = mock_aiter_lines
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream
        client.reconnect_max_retries = 2
        client.reconnect_initial_delay = 0.01

        with pytest.raises(RuntimeError, match="max retries exceeded"):
            async for event in client.stream_events(endpoint="/test"):
                pass

        await client.close()

    async def test_no_retry_on_client_error(self, client):
        """Test no retry on 4xx client errors."""

        async def mock_stream(*args, **kwargs):
            class MockAsyncContext:
                async def __aenter__(self):
                    mock_response = MagicMock()
                    mock_response.status_code = 401
                    mock_response.raise_for_status = MagicMock(
                        side_effect=httpx.HTTPStatusError(
                            "Unauthorized",
                            request=MagicMock(),
                            response=MagicMock(status_code=401),
                        )
                    )
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            return MockAsyncContext()

        client.client.stream = mock_stream

        with pytest.raises(httpx.HTTPStatusError):
            async for event in client.stream_events(endpoint="/test"):
                pass

        await client.close()

    async def test_get_metrics(self, client):
        """Test getting client metrics."""
        metrics = client.get_metrics()
        assert metrics["state"] == "disconnected"
        assert metrics["events_received"] == 0
        assert metrics["connections_made"] == 0
        assert metrics["active_streams"] == 0
        assert metrics["max_streams"] == 50
        await client.close()

    async def test_health_check_success(self, client):
        """Test health check success."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_get(*args, **kwargs):
            return mock_response

        client.client.get = mock_get

        health = await client.health_check()
        assert health["healthy"] is True
        assert health["state"] == "disconnected"
        await client.close()

    async def test_health_check_failure(self, client):
        """Test health check failure."""

        async def mock_get(*args, **kwargs):
            raise httpx.RequestError("Connection failed")

        client.client.get = mock_get

        health = await client.health_check()
        assert health["healthy"] is False
        assert "error" in health
        await client.close()

    async def test_base_url_trailing_slash_removal(self):
        """Test that trailing slash is removed from base URL."""
        async with GatewaySSEClient(
            base_url="http://test:8080/",
        ) as client:
            assert client.base_url == "http://test:8080"

    async def test_connection_pooling_limits(self):
        """Test connection pooling configuration."""
        async with GatewaySSEClient(
            base_url="http://test:8080",
            max_connections=100,
        ) as client:
            assert client.client.limits.max_connections == 100
            assert client._max_streams == 100

    async def test_timeout_configuration(self):
        """Test timeout configuration."""
        async with GatewaySSEClient(
            base_url="http://test:8080",
            timeout=120.0,
        ) as client:
            assert client.timeout == 120.0
