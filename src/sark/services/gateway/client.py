"""Gateway client service.

Production implementation integrating HTTP transport layer.
Provides high-level interface for Gateway communication with connection pooling,
caching, retry logic, and OPA authorization.
"""

from typing import Any, Optional

import structlog

from sark.gateway.transports.http_client import GatewayHTTPClient
from sark.models.gateway import GatewayServerInfo, GatewayToolInfo
from sark.services.policy.opa_client import OPAClient

logger = structlog.get_logger()

# Singleton gateway client instance
_gateway_client: Optional["GatewayClient"] = None


class GatewayClient:
    """
    HTTP client for communicating with MCP Gateway.

    Features:
    - Connection pooling (via GatewayHTTPClient)
    - Retry logic with exponential backoff
    - TTL-based response caching
    - OPA authorization integration
    - Comprehensive error handling
    - Health monitoring

    Example:
        >>> client = GatewayClient(base_url="http://gateway:8080", api_key="secret")
        >>> servers = await client.list_servers()
        >>> tools = await client.list_tools(server_name="postgres-mcp")
        >>> result = await client.invoke_tool(
        ...     server_name="postgres-mcp",
        ...     tool_name="execute_query",
        ...     parameters={"query": "SELECT 1"},
        ...     user_token="jwt-token",
        ... )
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_connections: int = 50,
        opa_client: OPAClient | None = None,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 300,
        max_retries: int = 3,
    ):
        """
        Initialize Gateway client.

        Args:
            base_url: Gateway base URL (e.g., "http://localhost:8080")
            api_key: Optional API key for Gateway authentication
            timeout: Request timeout in seconds (default: 30s)
            max_connections: Maximum concurrent connections (default: 50)
            opa_client: Optional OPA client for authorization checks
            cache_enabled: Enable response caching (default: True)
            cache_ttl_seconds: Cache TTL in seconds (default: 300s = 5 minutes)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # Create HTTP transport with all configuration
        self._transport = GatewayHTTPClient(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_connections=max_connections,
            opa_client=opa_client,
            cache_enabled=cache_enabled,
            cache_ttl_seconds=cache_ttl_seconds,
            max_retries=max_retries,
        )

        logger.info(
            "gateway_client_initialized",
            base_url=base_url,
            has_api_key=bool(api_key),
            has_opa_client=bool(opa_client),
            cache_enabled=cache_enabled,
            max_connections=max_connections,
        )

    async def __aenter__(self) -> "GatewayClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close Gateway client and cleanup resources."""
        await self._transport.close()
        logger.info("gateway_client_closed")

    async def list_servers(
        self,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> list[GatewayServerInfo]:
        """
        List all MCP servers registered with Gateway.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page (max 1000)
            use_cache: Whether to use cache (default: True)

        Returns:
            List of Gateway server info objects

        Example:
            >>> servers = await client.list_servers(page=1, page_size=100)
            >>> for server in servers:
            ...     print(f"Server: {server.server_name}")
        """
        return await self._transport.list_servers(
            page=page,
            page_size=page_size,
            use_cache=use_cache,
        )

    async def list_all_servers(
        self,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> list[GatewayServerInfo]:
        """
        List ALL MCP servers by automatically paginating through results.

        Args:
            page_size: Number of items per page (max 1000)
            use_cache: Whether to use cache (default: True)

        Returns:
            Complete list of all Gateway server info objects

        Example:
            >>> all_servers = await client.list_all_servers()
            >>> print(f"Total servers: {len(all_servers)}")
        """
        return await self._transport.list_all_servers(
            page_size=page_size,
            use_cache=use_cache,
        )

    async def get_server(
        self,
        server_name: str,
        use_cache: bool = True,
    ) -> GatewayServerInfo:
        """
        Get specific server information by name.

        Args:
            server_name: Server name to retrieve
            use_cache: Whether to use cache (default: True)

        Returns:
            Gateway server info object

        Raises:
            httpx.HTTPStatusError: If server not found (404)

        Example:
            >>> server = await client.get_server("postgres-mcp")
            >>> print(f"Server health: {server.health_status}")
        """
        return await self._transport.get_server(
            server_name=server_name,
            use_cache=use_cache,
        )

    async def list_tools(
        self,
        server_name: str | None = None,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> list[GatewayToolInfo]:
        """
        List tools available via Gateway.

        Args:
            server_name: Optional server filter
            page: Page number (1-indexed)
            page_size: Number of items per page (max 1000)
            use_cache: Whether to use cache (default: True)

        Returns:
            List of Gateway tool info objects

        Example:
            >>> # List all tools
            >>> all_tools = await client.list_tools()
            >>> # List tools for specific server
            >>> postgres_tools = await client.list_tools(server_name="postgres-mcp")
        """
        return await self._transport.list_tools(
            server_name=server_name,
            page=page,
            page_size=page_size,
            use_cache=use_cache,
        )

    async def invoke_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: dict,
        user_token: str,
        check_authorization: bool = True,
    ) -> dict:
        """
        Invoke a tool via Gateway (with authorization).

        This method:
        1. Optionally checks authorization via OPA client (if configured)
        2. Forwards user JWT to Gateway
        3. Gateway validates authorization with SARK
        4. Gateway routes request to MCP server
        5. Returns tool invocation result

        Args:
            server_name: Target MCP server name
            tool_name: Tool to invoke
            parameters: Tool parameters
            user_token: User JWT token for authorization
            check_authorization: Whether to check OPA authorization first (default: True)

        Returns:
            Tool invocation result from MCP server

        Raises:
            PermissionError: If OPA authorization check fails
            httpx.HTTPStatusError: If Gateway request fails

        Example:
            >>> result = await client.invoke_tool(
            ...     server_name="postgres-mcp",
            ...     tool_name="execute_query",
            ...     parameters={"query": "SELECT * FROM users LIMIT 10"},
            ...     user_token="eyJhbG...",
            ... )
            >>> print(result["status"])
        """
        return await self._transport.invoke_tool(
            server_name=server_name,
            tool_name=tool_name,
            parameters=parameters,
            user_token=user_token,
            check_authorization=check_authorization,
        )

    async def health_check(self) -> dict[str, bool]:
        """
        Check Gateway health status.

        Returns:
            Dictionary with Gateway health status and details

        Example:
            >>> health = await client.health_check()
            >>> if health["healthy"]:
            ...     print("Gateway is healthy")
            ... else:
            ...     print(f"Gateway unhealthy: {health.get('error')}")
        """
        return await self._transport.health_check()

    def get_cache_metrics(self) -> dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary with cache hit rate and statistics

        Example:
            >>> metrics = client.get_cache_metrics()
            >>> print(f"Cache hit rate: {metrics['hit_rate']:.1%}")
            >>> print(f"Cache size: {metrics['cache_size']}/{metrics['cache_maxsize']}")
        """
        return self._transport.get_cache_metrics()

    def clear_cache(self) -> None:
        """
        Clear all cached responses.

        Example:
            >>> client.clear_cache()
            >>> print("Cache cleared")
        """
        self._transport.clear_cache()


async def get_gateway_client() -> GatewayClient:
    """
    Get singleton Gateway client instance.

    Initializes client from settings if not already created.
    The client includes connection pooling, caching, and retry logic.

    Returns:
        GatewayClient instance

    Example:
        >>> client = await get_gateway_client()
        >>> servers = await client.list_servers()
    """
    global _gateway_client

    if _gateway_client is None:
        from sark.config import get_settings

        settings = get_settings()

        if not settings.gateway_enabled:
            logger.warning(
                "gateway_disabled", message="Gateway integration is disabled in settings"
            )

        _gateway_client = GatewayClient(
            base_url=settings.gateway_url,
            api_key=settings.gateway_api_key,
            timeout=settings.gateway_timeout_seconds,
        )

    return _gateway_client


async def close_gateway_client() -> None:
    """
    Close and cleanup the singleton Gateway client instance.

    This should be called on application shutdown to properly
    close HTTP connections and free resources.

    Example:
        >>> await close_gateway_client()
    """
    global _gateway_client

    if _gateway_client is not None:
        await _gateway_client.close()
        _gateway_client = None
        logger.info("gateway_client_singleton_closed")
