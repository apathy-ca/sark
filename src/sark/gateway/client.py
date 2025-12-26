"""Unified Gateway Client with automatic transport selection.

This module provides a high-level client for MCP Gateway communication that:
- Automatically selects appropriate transport (HTTP, SSE, or stdio)
- Integrates error handling (circuit breaker, retry, timeout)
- Provides unified interface for all Gateway operations
- Supports connection pooling and resource management
"""

from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

import structlog

from sark.gateway.error_handler import GatewayErrorHandler
from sark.gateway.transports.http_client import GatewayHTTPClient
from sark.gateway.transports.sse_client import GatewaySSEClient, SSEEvent
from sark.gateway.transports.stdio_client import StdioTransport
from sark.models.gateway import (
    GatewayServerInfo,
    GatewayToolInfo,
)
from sark.services.policy.opa_client import OPAClient

logger = structlog.get_logger()


class TransportType(str, Enum):
    """Available transport types."""

    HTTP = "http"
    SSE = "sse"
    STDIO = "stdio"


class TransportMode(str, Enum):
    """Transport selection modes."""

    AUTO = "auto"  # Automatically select best transport
    HTTP_ONLY = "http_only"  # Use only HTTP transport
    SSE_ONLY = "sse_only"  # Use only SSE transport
    STDIO_ONLY = "stdio_only"  # Use only stdio transport


class GatewayClientError(Exception):
    """Base exception for Gateway client errors."""

    pass


class TransportNotAvailableError(GatewayClientError):
    """Requested transport is not available."""

    pass


class GatewayClient:
    """
    Unified Gateway client with automatic transport selection.

    This client provides a high-level interface for all Gateway operations,
    automatically selecting the most appropriate transport based on the
    operation type and configuration.

    Transport Selection Logic:
    - Server listing/discovery: HTTP (best for REST operations)
    - Tool invocation: HTTP (with optional OPA authorization)
    - Event streaming: SSE (Server-Sent Events)
    - Local subprocess: stdio (for local MCP servers)

    Features:
    - Automatic transport selection
    - Integrated error handling (circuit breaker, retry, timeout)
    - Connection pooling for HTTP/SSE
    - Process lifecycle management for stdio
    - Comprehensive logging and metrics

    Example:
        ```python
        async with GatewayClient(
            gateway_url="http://gateway:8080",
            api_key="secret",
            opa_client=opa_client,
        ) as client:
            # List servers (uses HTTP)
            servers = await client.list_servers()

            # Invoke tool (uses HTTP + OPA)
            result = await client.invoke_tool(
                server_name="postgres-mcp",
                tool_name="execute_query",
                parameters={"query": "SELECT 1"},
                user_token="jwt-token",
            )

            # Stream events (uses SSE)
            async for event in client.stream_events():
                print(f"Event: {event.event_type}")

            # Local subprocess (uses stdio)
            local_client = await client.connect_local_server(
                command=["python", "local_server.py"]
            )
        ```
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        api_key: str | None = None,
        opa_client: OPAClient | None = None,
        transport_mode: TransportMode = TransportMode.AUTO,
        timeout: float = 30.0,
        max_connections: int = 50,
        enable_error_handling: bool = True,
        circuit_breaker_config: dict[str, Any] | None = None,
        retry_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize Gateway client.

        Args:
            gateway_url: Gateway base URL (required for HTTP/SSE)
            api_key: API key for Gateway authentication
            opa_client: OPA client for authorization (optional)
            transport_mode: Transport selection mode (default: AUTO)
            timeout: Default timeout in seconds (default: 30.0)
            max_connections: Max concurrent connections (default: 50)
            enable_error_handling: Enable circuit breaker and retry (default: True)
            circuit_breaker_config: Circuit breaker configuration
            retry_config: Retry configuration
        """
        self.gateway_url = gateway_url
        self.api_key = api_key
        self.opa_client = opa_client
        self.transport_mode = transport_mode
        self.timeout = timeout
        self.max_connections = max_connections

        # Initialize error handler
        self.error_handler: GatewayErrorHandler | None = None
        if enable_error_handling:
            self.error_handler = GatewayErrorHandler(
                circuit_breaker_config=circuit_breaker_config,
                retry_config=retry_config,
                default_timeout=timeout,
            )

        # Initialize transports (lazy initialization)
        self._http_client: GatewayHTTPClient | None = None
        self._sse_client: GatewaySSEClient | None = None
        self._stdio_transports: dict[str, StdioTransport] = {}

        # Track client state
        self._is_closed = False

        logger.info(
            "gateway_client_initialized",
            gateway_url=gateway_url,
            transport_mode=transport_mode,
            has_opa_client=bool(opa_client),
            error_handling_enabled=enable_error_handling,
        )

    async def __aenter__(self) -> "GatewayClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def _ensure_gateway_url(self) -> str:
        """Ensure gateway URL is configured."""
        if not self.gateway_url:
            raise GatewayClientError(
                "Gateway URL is required for HTTP/SSE transports. "
                "Set gateway_url in constructor."
            )
        return self.gateway_url

    def _get_http_client(self) -> GatewayHTTPClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            gateway_url = self._ensure_gateway_url()
            self._http_client = GatewayHTTPClient(
                base_url=gateway_url,
                api_key=self.api_key,
                timeout=self.timeout,
                max_connections=self.max_connections,
                opa_client=self.opa_client,
            )
            logger.info("http_client_created")
        return self._http_client

    def _get_sse_client(self) -> GatewaySSEClient:
        """Get or create SSE client."""
        if self._sse_client is None:
            gateway_url = self._ensure_gateway_url()
            self._sse_client = GatewaySSEClient(
                base_url=gateway_url,
                api_key=self.api_key,
                timeout=self.timeout,
                max_connections=self.max_connections,
            )
            logger.info("sse_client_created")
        return self._sse_client

    def _check_transport_available(self, transport: TransportType) -> None:
        """Check if transport is available based on mode."""
        if self.transport_mode == TransportMode.HTTP_ONLY and transport != TransportType.HTTP:
            raise TransportNotAvailableError(
                f"Transport {transport} not available in HTTP_ONLY mode"
            )
        if self.transport_mode == TransportMode.SSE_ONLY and transport != TransportType.SSE:
            raise TransportNotAvailableError(
                f"Transport {transport} not available in SSE_ONLY mode"
            )
        if self.transport_mode == TransportMode.STDIO_ONLY and transport != TransportType.STDIO:
            raise TransportNotAvailableError(
                f"Transport {transport} not available in STDIO_ONLY mode"
            )

    async def _execute_with_error_handling(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute function with error handling if enabled."""
        if self.error_handler:
            return await self.error_handler.execute(func, *args, **kwargs)
        else:
            return await func(*args, **kwargs)

    # =========================================================================
    # Server Discovery Operations (HTTP Transport)
    # =========================================================================

    async def list_servers(self, page: int = 1, page_size: int = 100) -> list[GatewayServerInfo]:
        """
        List all MCP servers registered with Gateway.

        Uses HTTP transport for efficient REST operations.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page (max 1000)

        Returns:
            List of server information

        Raises:
            TransportNotAvailableError: If HTTP transport not available
            GatewayClientError: If operation fails
        """
        self._check_transport_available(TransportType.HTTP)
        http_client = self._get_http_client()

        return await self._execute_with_error_handling(
            http_client.list_servers, page=page, page_size=page_size
        )

    async def list_all_servers(self) -> list[GatewayServerInfo]:
        """
        List ALL servers with automatic pagination.

        Uses HTTP transport and automatically handles pagination for
        large result sets (1000+ servers).

        Returns:
            Complete list of all servers

        Raises:
            TransportNotAvailableError: If HTTP transport not available
            GatewayClientError: If operation fails
        """
        self._check_transport_available(TransportType.HTTP)
        http_client = self._get_http_client()

        return await self._execute_with_error_handling(http_client.list_all_servers)

    async def get_server_info(self, server_name: str) -> GatewayServerInfo:
        """
        Get detailed information about a specific server.

        Args:
            server_name: Server name to query

        Returns:
            Server information

        Raises:
            TransportNotAvailableError: If HTTP transport not available
            GatewayClientError: If server not found
        """
        self._check_transport_available(TransportType.HTTP)
        http_client = self._get_http_client()

        return await self._execute_with_error_handling(
            http_client.get_server_info, server_name=server_name
        )

    # =========================================================================
    # Tool Discovery Operations (HTTP Transport)
    # =========================================================================

    async def list_tools(
        self, server_name: str | None = None, page: int = 1, page_size: int = 100
    ) -> list[GatewayToolInfo]:
        """
        List tools available via Gateway.

        Uses HTTP transport for efficient REST operations.

        Args:
            server_name: Filter by server name (optional)
            page: Page number (1-indexed)
            page_size: Items per page (max 1000)

        Returns:
            List of tool information

        Raises:
            TransportNotAvailableError: If HTTP transport not available
        """
        self._check_transport_available(TransportType.HTTP)
        http_client = self._get_http_client()

        return await self._execute_with_error_handling(
            http_client.list_tools,
            server_name=server_name,
            page=page,
            page_size=page_size,
        )

    async def list_all_tools(self, server_name: str | None = None) -> list[GatewayToolInfo]:
        """
        List ALL tools with automatic pagination.

        Uses HTTP transport and automatically handles pagination.

        Args:
            server_name: Filter by server name (optional)

        Returns:
            Complete list of all tools

        Raises:
            TransportNotAvailableError: If HTTP transport not available
        """
        self._check_transport_available(TransportType.HTTP)
        http_client = self._get_http_client()

        return await self._execute_with_error_handling(
            http_client.list_all_tools, server_name=server_name
        )

    # =========================================================================
    # Tool Invocation Operations (HTTP Transport + OPA)
    # =========================================================================

    async def invoke_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: dict[str, Any],
        user_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Invoke a tool on a Gateway-managed MCP server.

        Uses HTTP transport with optional OPA authorization.
        If OPA client is configured, the request will be authorized
        before being sent to the Gateway.

        Args:
            server_name: Target server name
            tool_name: Tool to invoke
            parameters: Tool parameters
            user_token: User JWT token for authorization (optional)

        Returns:
            Tool execution result

        Raises:
            TransportNotAvailableError: If HTTP transport not available
            PermissionError: If OPA denies the request
            GatewayClientError: If invocation fails
        """
        self._check_transport_available(TransportType.HTTP)
        http_client = self._get_http_client()

        return await self._execute_with_error_handling(
            http_client.invoke_tool,
            server_name=server_name,
            tool_name=tool_name,
            parameters=parameters,
            user_token=user_token,
        )

    # =========================================================================
    # Event Streaming Operations (SSE Transport)
    # =========================================================================

    async def stream_events(
        self,
        endpoint: str = "/api/v1/events",
        event_types: list[str] | None = None,
        user_token: str | None = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Stream real-time events from Gateway using Server-Sent Events.

        Uses SSE transport for efficient real-time streaming.

        Args:
            endpoint: SSE endpoint path (default: /api/v1/events)
            event_types: Filter by event types (optional)
            user_token: User JWT token for authorization (optional)

        Yields:
            SSE events as they arrive

        Raises:
            TransportNotAvailableError: If SSE transport not available
            GatewayClientError: If connection fails

        Example:
            ```python
            async for event in client.stream_events(
                event_types=["tool_invoked", "server_registered"]
            ):
                print(f"Event: {event.event_type} - {event.data}")
            ```
        """
        self._check_transport_available(TransportType.SSE)
        sse_client = self._get_sse_client()

        # Note: Error handling wrapper not applied to generators
        # SSE client has built-in reconnection logic
        async for event in sse_client.stream_events(
            endpoint=endpoint, event_types=event_types, user_token=user_token
        ):
            yield event

    # =========================================================================
    # Local Server Operations (stdio Transport)
    # =========================================================================

    async def connect_local_server(
        self,
        command: list[str],
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        server_id: str | None = None,
    ) -> "LocalServerClient":
        """
        Connect to a local MCP server via stdio transport.

        Uses stdio transport for subprocess-based communication.
        Useful for local development and testing.

        Args:
            command: Command to execute (e.g., ["python", "server.py"])
            cwd: Working directory (optional)
            env: Environment variables (optional)
            server_id: Unique identifier for this server (optional)

        Returns:
            Local server client wrapper

        Raises:
            TransportNotAvailableError: If stdio transport not available
            GatewayClientError: If subprocess fails to start

        Example:
            ```python
            local_server = await client.connect_local_server(
                command=["python", "my_mcp_server.py"],
                cwd="/path/to/server",
            )
            try:
                response = await local_server.send_request("tools/list", {})
                print(response)
            finally:
                await local_server.stop()
            ```
        """
        self._check_transport_available(TransportType.STDIO)

        # Generate server ID if not provided
        if server_id is None:
            import hashlib

            server_id = hashlib.md5("".join(command).encode()).hexdigest()[:8]

        # Create stdio transport
        stdio_transport = StdioTransport(command=command, cwd=cwd, env=env)

        # Start transport
        await self._execute_with_error_handling(stdio_transport.start)

        # Track transport
        self._stdio_transports[server_id] = stdio_transport

        logger.info(
            "local_server_connected",
            server_id=server_id,
            command=command,
        )

        return LocalServerClient(transport=stdio_transport, server_id=server_id, parent=self)

    async def disconnect_local_server(self, server_id: str) -> None:
        """
        Disconnect from a local server.

        Args:
            server_id: Server identifier

        Raises:
            GatewayClientError: If server not found
        """
        if server_id not in self._stdio_transports:
            raise GatewayClientError(f"Local server {server_id} not found")

        transport = self._stdio_transports[server_id]
        await transport.stop()
        del self._stdio_transports[server_id]

        logger.info("local_server_disconnected", server_id=server_id)

    # =========================================================================
    # Health & Metrics
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on all active transports.

        Returns:
            Health status for each transport

        Example:
            ```python
            health = await client.health_check()
            print(health)
            # {
            #     "http": {"status": "healthy", "cache_hit_rate": 0.92},
            #     "sse": {"status": "connected", "connection_state": "connected"},
            #     "stdio": {"server1": {"status": "running", "pid": 12345}}
            # }
            ```
        """
        health = {}

        # HTTP client health
        if self._http_client:
            health["http"] = {
                "status": "healthy",
                "cache_hit_rate": self._http_client.cache_hit_rate,
            }

        # SSE client health
        if self._sse_client:
            health["sse"] = {
                "status": "connected",
                "connection_state": self._sse_client.state.value,
            }

        # stdio transports health
        if self._stdio_transports:
            health["stdio"] = {}
            for server_id, transport in self._stdio_transports.items():
                is_running = transport.is_running
                health["stdio"][server_id] = {
                    "status": "running" if is_running else "stopped",
                    "pid": transport._process.pid if transport._process else None,
                }

        # Error handler metrics
        if self.error_handler:
            health["error_handler"] = self.error_handler.get_metrics()

        return health

    def get_metrics(self) -> dict[str, Any]:
        """
        Get client metrics.

        Returns:
            Metrics dictionary
        """
        metrics = {
            "transport_mode": self.transport_mode.value,
            "active_transports": [],
        }

        if self._http_client:
            metrics["active_transports"].append("http")
            metrics["http_cache_hit_rate"] = self._http_client.cache_hit_rate

        if self._sse_client:
            metrics["active_transports"].append("sse")

        if self._stdio_transports:
            metrics["active_transports"].append("stdio")
            metrics["stdio_servers_count"] = len(self._stdio_transports)

        if self.error_handler:
            metrics["error_handler"] = self.error_handler.get_metrics()

        return metrics

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def close(self) -> None:
        """
        Close all transports and cleanup resources.

        Closes HTTP client, SSE client, and all stdio transports.
        Safe to call multiple times.
        """
        if self._is_closed:
            return

        logger.info("gateway_client_closing")

        # Close HTTP client
        if self._http_client:
            await self._http_client.close()
            self._http_client = None

        # Close SSE client
        if self._sse_client:
            await self._sse_client.close()
            self._sse_client = None

        # Close all stdio transports
        for server_id, transport in list(self._stdio_transports.items()):
            try:
                await transport.stop()
            except Exception as e:
                logger.error(
                    "stdio_transport_close_error",
                    server_id=server_id,
                    error=str(e),
                )
        self._stdio_transports.clear()

        self._is_closed = True
        logger.info("gateway_client_closed")


class LocalServerClient:
    """
    Wrapper for local stdio-based MCP server.

    Provides a simple interface for interacting with local servers
    connected via stdio transport.
    """

    def __init__(self, transport: StdioTransport, server_id: str, parent: GatewayClient) -> None:
        """
        Initialize local server client.

        Args:
            transport: stdio transport instance
            server_id: Server identifier
            parent: Parent GatewayClient instance
        """
        self.transport = transport
        self.server_id = server_id
        self._parent = parent

    async def send_request(
        self, method: str, params: dict[str, Any], timeout: float | None = None
    ) -> dict[str, Any]:
        """
        Send JSON-RPC request to local server.

        Args:
            method: JSON-RPC method name
            params: Request parameters
            timeout: Request timeout (optional)

        Returns:
            Response from server

        Raises:
            TimeoutError: If request times out
            Exception: If server returns error
        """
        return await self.transport.send_request(method, params, timeout=timeout)

    async def send_notification(self, method: str, params: dict[str, Any]) -> None:
        """
        Send JSON-RPC notification to local server (no response expected).

        Args:
            method: JSON-RPC method name
            params: Notification parameters
        """
        await self.transport.send_notification(method, params)

    @property
    def is_running(self) -> bool:
        """Check if local server is running."""
        return self.transport.is_running

    async def stop(self) -> None:
        """Stop local server."""
        await self._parent.disconnect_local_server(self.server_id)
