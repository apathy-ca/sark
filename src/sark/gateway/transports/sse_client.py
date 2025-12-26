"""SSE (Server-Sent Events) transport client for MCP Gateway streaming.

This module provides async SSE client functionality for real-time streaming
communication with MCP Gateway servers, including:
- Server-Sent Events streaming support
- Connection pooling (max 50 concurrent connections)
- Automatic reconnection with exponential backoff
- Event parsing and handling
- Stream health monitoring
- Comprehensive error recovery
"""

import asyncio
from collections.abc import AsyncGenerator
import contextlib
from enum import Enum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class SSEEvent:
    """Server-Sent Event representation."""

    def __init__(
        self,
        event_type: str | None = None,
        data: str = "",
        event_id: str | None = None,
        retry: int | None = None,
    ) -> None:
        """Initialize SSE event.

        Args:
            event_type: Event type (defaults to "message")
            data: Event data payload
            event_id: Event ID for reconnection
            retry: Retry timeout in milliseconds
        """
        self.event_type = event_type or "message"
        self.data = data
        self.event_id = event_id
        self.retry = retry

    def __repr__(self) -> str:
        """String representation of SSE event."""
        return f"SSEEvent(type={self.event_type}, id={self.event_id}, data={self.data[:50]}...)"


class ConnectionState(str, Enum):
    """SSE connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"


class GatewaySSEClient:
    """Async SSE client for MCP Gateway real-time streaming.

    Features:
    - Server-Sent Events (SSE) streaming support
    - Connection pooling (max 50 concurrent streams)
    - Automatic reconnection with exponential backoff
    - Event parsing and type handling
    - Stream health monitoring
    - Last-Event-ID tracking for resume
    - Comprehensive error recovery

    Example:
        >>> async with GatewaySSEClient(
        ...     base_url="http://gateway:8080",
        ...     api_key="secret",
        ... ) as client:
        ...     async for event in client.stream_events(
        ...         endpoint="/api/v1/events",
        ...         event_types=["tool_invoked", "server_registered"],
        ...     ):
        ...         print(f"Received: {event.event_type} - {event.data}")
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 60.0,
        max_connections: int = 50,
        reconnect_enabled: bool = True,
        reconnect_max_retries: int = 5,
        reconnect_initial_delay: float = 1.0,
        reconnect_max_delay: float = 60.0,
    ) -> None:
        """Initialize Gateway SSE client.

        Args:
            base_url: Gateway base URL (e.g., "http://gateway:8080")
            api_key: Optional API key for Gateway authentication
            timeout: Stream timeout in seconds (default: 60s)
            max_connections: Maximum concurrent SSE connections (default: 50)
            reconnect_enabled: Enable automatic reconnection (default: True)
            reconnect_max_retries: Maximum reconnection attempts (default: 5)
            reconnect_initial_delay: Initial reconnection delay in seconds (default: 1s)
            reconnect_max_delay: Maximum reconnection delay in seconds (default: 60s)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.reconnect_enabled = reconnect_enabled
        self.reconnect_max_retries = reconnect_max_retries
        self.reconnect_initial_delay = reconnect_initial_delay
        self.reconnect_max_delay = reconnect_max_delay

        # Connection pooling limits
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=20,
        )

        # Create async HTTP client for SSE streaming
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
        )

        # Connection state tracking
        self.state = ConnectionState.DISCONNECTED
        self.last_event_id: str | None = None

        # Connection pool tracking (active streams)
        self._active_streams: set[str] = set()
        self._max_streams = max_connections

        # Metrics
        self._events_received = 0
        self._connections_made = 0
        self._reconnections = 0
        self._errors = 0

        logger.info(
            "gateway_sse_client_initialized",
            base_url=base_url,
            has_api_key=bool(api_key),
            max_connections=max_connections,
            reconnect_enabled=reconnect_enabled,
        )

    async def __aenter__(self) -> "GatewaySSEClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close SSE client and cleanup resources."""
        self.state = ConnectionState.CLOSED
        await self.client.aclose()
        self._active_streams.clear()
        logger.info(
            "gateway_sse_client_closed",
            total_events_received=self._events_received,
            total_connections=self._connections_made,
            total_reconnections=self._reconnections,
        )

    def _get_headers(self, user_token: str | None = None) -> dict[str, str]:
        """Build SSE request headers with optional authentication.

        Args:
            user_token: Optional user JWT token for authorization

        Returns:
            Dictionary of HTTP headers for SSE
        """
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"

        # Include Last-Event-ID for reconnection resume
        if self.last_event_id:
            headers["Last-Event-ID"] = self.last_event_id

        return headers

    def _parse_sse_line(
        self,
        line: str,
        event: SSEEvent,
    ) -> SSEEvent | None:
        """Parse a single SSE line and update event object.

        Args:
            line: SSE line to parse
            event: Current event being built

        Returns:
            Complete event if line is empty (event separator), else None
        """
        # Empty line signals end of event
        if not line or line == "\n":
            if event.data or event.event_type:
                return event
            return None

        # Comment line (ignore)
        if line.startswith(":"):
            return None

        # Parse field:value format
        if ":" in line:
            field, _, value = line.partition(":")
            value = value.lstrip()  # Remove leading space

            if field == "event":
                event.event_type = value
            elif field == "data":
                if event.data:
                    event.data += "\n" + value
                else:
                    event.data = value
            elif field == "id":
                event.event_id = value
                self.last_event_id = value
            elif field == "retry":
                with contextlib.suppress(ValueError):
                    event.retry = int(value)

        return None

    async def stream_events(
        self,
        endpoint: str,
        event_types: list[str] | None = None,
        user_token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        """Stream events from Gateway SSE endpoint with automatic reconnection.

        This method establishes an SSE connection and yields events as they
        arrive. If the connection is lost, it automatically reconnects with
        exponential backoff (if enabled).

        Args:
            endpoint: SSE endpoint path (e.g., "/api/v1/stream")
            event_types: Optional list of event types to filter
            user_token: Optional user JWT token for authorization
            params: Optional query parameters

        Yields:
            SSEEvent objects as they are received

        Example:
            >>> async for event in client.stream_events(
            ...     endpoint="/api/v1/events",
            ...     event_types=["tool_invoked"],
            ... ):
            ...     if event.event_type == "tool_invoked":
            ...         print(f"Tool invoked: {event.data}")
        """
        url = f"{self.base_url}{endpoint}"
        stream_id = f"{endpoint}:{id(self)}"

        # Check connection pool limit
        if len(self._active_streams) >= self._max_streams:
            logger.error(
                "sse_connection_pool_exhausted",
                active_streams=len(self._active_streams),
                max_streams=self._max_streams,
            )
            raise RuntimeError(
                f"Connection pool exhausted: {len(self._active_streams)}/{self._max_streams}"
            )

        self._active_streams.add(stream_id)

        retry_count = 0
        backoff_delay = self.reconnect_initial_delay

        try:
            while True:
                try:
                    # Update state
                    if retry_count > 0:
                        self.state = ConnectionState.RECONNECTING
                        logger.info(
                            "sse_reconnecting",
                            endpoint=endpoint,
                            retry_count=retry_count,
                            backoff_delay=backoff_delay,
                        )
                    else:
                        self.state = ConnectionState.CONNECTING

                    headers = self._get_headers(user_token)

                    # Establish SSE connection
                    async with self.client.stream(
                        method="GET",
                        url=url,
                        headers=headers,
                        params=params,
                    ) as response:
                        response.raise_for_status()

                        self.state = ConnectionState.CONNECTED
                        self._connections_made += 1
                        if retry_count > 0:
                            self._reconnections += 1

                        logger.info(
                            "sse_connected",
                            endpoint=endpoint,
                            status_code=response.status_code,
                        )

                        # Reset retry count on successful connection
                        retry_count = 0
                        backoff_delay = self.reconnect_initial_delay

                        # Stream events line by line
                        current_event = SSEEvent()

                        async for line in response.aiter_lines():
                            # Parse SSE line
                            event = self._parse_sse_line(line, current_event)

                            if event:
                                # Event complete - yield if type matches filter
                                if not event_types or event.event_type in event_types:
                                    self._events_received += 1
                                    yield event

                                # Start new event
                                current_event = SSEEvent()

                except httpx.HTTPStatusError as e:
                    self._errors += 1
                    logger.error(
                        "sse_http_error",
                        endpoint=endpoint,
                        status_code=e.response.status_code,
                        error=str(e),
                    )

                    # Don't retry on client errors (4xx)
                    if 400 <= e.response.status_code < 500:
                        raise

                    # Retry on server errors (5xx)
                    if not self.reconnect_enabled:
                        raise

                except httpx.RequestError as e:
                    self._errors += 1
                    logger.error(
                        "sse_connection_error",
                        endpoint=endpoint,
                        error=str(e),
                    )

                    if not self.reconnect_enabled:
                        raise

                except Exception as e:
                    self._errors += 1
                    logger.error(
                        "sse_unexpected_error",
                        endpoint=endpoint,
                        error=str(e),
                    )
                    raise

                # Reconnection logic
                retry_count += 1

                if retry_count > self.reconnect_max_retries:
                    logger.error(
                        "sse_max_retries_exceeded",
                        endpoint=endpoint,
                        max_retries=self.reconnect_max_retries,
                    )
                    raise RuntimeError(f"SSE max retries exceeded: {self.reconnect_max_retries}")

                # Exponential backoff
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 2, self.reconnect_max_delay)

        finally:
            # Cleanup stream from pool
            self._active_streams.discard(stream_id)
            self.state = ConnectionState.DISCONNECTED
            logger.info(
                "sse_stream_closed",
                endpoint=endpoint,
                events_received=self._events_received,
            )

    async def stream_audit_events(
        self,
        user_token: str,
        event_types: list[str] | None = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        """Stream audit events from Gateway.

        Convenience method for streaming audit events.

        Args:
            user_token: User JWT token for authorization
            event_types: Optional list of audit event types to filter

        Yields:
            SSEEvent objects for audit events

        Example:
            >>> async for event in client.stream_audit_events(
            ...     user_token="jwt-token",
            ...     event_types=["tool_invoked", "authorization_denied"],
            ... ):
            ...     print(f"Audit event: {event.data}")
        """
        async for event in self.stream_events(
            endpoint="/api/v1/audit/stream",
            event_types=event_types,
            user_token=user_token,
        ):
            yield event

    async def stream_server_events(
        self,
        server_name: str,
        user_token: str,
        event_types: list[str] | None = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        """Stream events for a specific MCP server.

        Args:
            server_name: MCP server name to stream events for
            user_token: User JWT token for authorization
            event_types: Optional list of event types to filter

        Yields:
            SSEEvent objects for server-specific events

        Example:
            >>> async for event in client.stream_server_events(
            ...     server_name="postgres-mcp",
            ...     user_token="jwt-token",
            ... ):
            ...     print(f"Server event: {event.data}")
        """
        async for event in self.stream_events(
            endpoint=f"/api/v1/servers/{server_name}/stream",
            event_types=event_types,
            user_token=user_token,
        ):
            yield event

    def get_metrics(self) -> dict[str, Any]:
        """Get SSE client metrics.

        Returns:
            Dictionary with connection and event statistics

        Example:
            >>> metrics = client.get_metrics()
            >>> metrics["events_received"]
            1543
            >>> metrics["active_streams"]
            5
        """
        return {
            "state": self.state.value,
            "events_received": self._events_received,
            "connections_made": self._connections_made,
            "reconnections": self._reconnections,
            "errors": self._errors,
            "active_streams": len(self._active_streams),
            "max_streams": self._max_streams,
            "last_event_id": self.last_event_id,
        }

    async def health_check(self) -> dict[str, bool]:
        """Check SSE client health status.

        Returns:
            Dictionary with health status

        Example:
            >>> health = await client.health_check()
            >>> health["healthy"]
            True
        """
        try:
            # Simple HTTP health check (not SSE stream)
            response = await self.client.get(
                f"{self.base_url}/health",
                headers={"Accept": "application/json"},
            )

            is_healthy = response.status_code == 200

            return {
                "healthy": is_healthy,
                "state": self.state.value,
                "active_streams": len(self._active_streams),
            }

        except Exception as e:
            logger.error("sse_health_check_failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
                "state": self.state.value,
            }
