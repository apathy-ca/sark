"""HTTP transport client for MCP Gateway communication.

This module provides async HTTP client functionality for communicating with
MCP Gateway servers, including:
- Server discovery with pagination
- Tool listing and discovery
- Tool invocation with OPA authorization
- TTL-based response caching
- Connection pooling and retry logic
- Comprehensive error handling
"""

import asyncio
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from cachetools import TTLCache

from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    GatewayServerInfo,
    GatewayToolInfo,
)
from sark.services.policy.opa_client import AuthorizationInput, OPAClient

logger = structlog.get_logger()


class PaginationParams:
    """Pagination parameters for API requests."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 100,
        offset: int | None = None,
    ) -> None:
        """Initialize pagination parameters.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page (max 1000)
            offset: Direct offset (overrides page if provided)
        """
        self.page = max(1, page)
        self.page_size = min(page_size, 1000)  # Cap at 1000 items per page
        self.offset = offset if offset is not None else (self.page - 1) * self.page_size

    def to_query_params(self) -> dict[str, Any]:
        """Convert to query parameters dict."""
        return {
            "offset": self.offset,
            "limit": self.page_size,
        }


class CacheEntry:
    """Cache entry with TTL and metadata."""

    def __init__(self, data: Any, ttl: int) -> None:
        """Initialize cache entry.

        Args:
            data: Cached data
            ttl: Time-to-live in seconds
        """
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - self.created_at) < self.ttl


class GatewayHTTPClient:
    """Async HTTP client for MCP Gateway communication.

    Features:
    - Connection pooling (max 50 concurrent connections)
    - TTL-based caching (5-minute default, configurable per endpoint)
    - Automatic pagination for large result sets
    - OPA integration for authorization
    - Retry logic with exponential backoff
    - Comprehensive error handling

    Example:
        >>> async with GatewayHTTPClient(
        ...     base_url="http://gateway:8080",
        ...     api_key="secret",
        ...     opa_client=opa_client,
        ... ) as client:
        ...     servers = await client.list_servers()
        ...     tools = await client.list_tools(server_name="postgres-mcp")
        ...     result = await client.invoke_tool(
        ...         server_name="postgres-mcp",
        ...         tool_name="execute_query",
        ...         parameters={"query": "SELECT 1"},
        ...         user_token="jwt-token",
        ...     )
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_connections: int = 50,
        opa_client: OPAClient | None = None,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 300,  # 5 minutes default
        max_retries: int = 3,
    ) -> None:
        """Initialize Gateway HTTP client.

        Args:
            base_url: Gateway base URL (e.g., "http://gateway:8080")
            api_key: Optional API key for Gateway authentication
            timeout: Request timeout in seconds
            max_connections: Maximum concurrent connections (default: 50)
            opa_client: OPA client for authorization (optional)
            cache_enabled: Enable response caching
            cache_ttl_seconds: Default cache TTL (default: 300s = 5 minutes)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.opa_client = opa_client

        # Connection pooling limits
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=20,
        )

        # Create async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
        )

        # Initialize TTL cache
        self.cache_enabled = cache_enabled
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: TTLCache = TTLCache(maxsize=1000, ttl=cache_ttl_seconds)

        # Cache hit/miss metrics
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(
            "gateway_http_client_initialized",
            base_url=base_url,
            has_api_key=bool(api_key),
            has_opa_client=bool(opa_client),
            cache_enabled=cache_enabled,
            max_connections=max_connections,
        )

    async def __aenter__(self) -> "GatewayHTTPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        await self.client.aclose()
        self._cache.clear()
        logger.info("gateway_http_client_closed")

    def _get_headers(self, user_token: str | None = None) -> dict[str, str]:
        """Build request headers with optional authentication.

        Args:
            user_token: Optional user JWT token for authorization

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"

        return headers

    def _get_cache_key(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """Generate cache key for endpoint and parameters.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Cache key string
        """
        if params:
            query_string = urlencode(sorted(params.items()))
            return f"{endpoint}?{query_string}"
        return endpoint

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        user_token: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Make HTTP request with caching and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            user_token: Optional user JWT token
            use_cache: Whether to use cache for GET requests

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPError: If request fails after retries
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(user_token)

        # Check cache for GET requests
        if method == "GET" and use_cache and self.cache_enabled:
            cache_key = self._get_cache_key(endpoint, params)
            if cache_key in self._cache:
                self._cache_hits += 1
                logger.debug("cache_hit", endpoint=endpoint, cache_key=cache_key)
                return self._cache[cache_key]
            self._cache_misses += 1

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )

                latency_ms = (time.time() - start_time) * 1000

                response.raise_for_status()

                result = response.json()

                logger.info(
                    "gateway_request_success",
                    method=method,
                    endpoint=endpoint,
                    status_code=response.status_code,
                    latency_ms=round(latency_ms, 2),
                    attempt=attempt + 1,
                )

                # Cache GET responses
                if method == "GET" and use_cache and self.cache_enabled:
                    cache_key = self._get_cache_key(endpoint, params)
                    self._cache[cache_key] = result

                return result

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(
                    "gateway_request_http_error",
                    method=method,
                    endpoint=endpoint,
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )

                # Don't retry client errors (4xx), only server errors (5xx)
                if 400 <= e.response.status_code < 500:
                    raise

            except httpx.RequestError as e:
                last_exception = e
                logger.warning(
                    "gateway_request_connection_error",
                    method=method,
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                backoff_seconds = 2**attempt  # 1s, 2s, 4s
                await asyncio.sleep(backoff_seconds)

        # All retries exhausted
        logger.error(
            "gateway_request_failed",
            method=method,
            endpoint=endpoint,
            max_retries=self.max_retries,
            error=str(last_exception),
        )
        raise last_exception  # type: ignore

    async def list_servers(
        self,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> list[GatewayServerInfo]:
        """List MCP servers registered with Gateway (with pagination).

        Supports pagination for 1000+ servers by making multiple requests
        if needed. Results are cached by default.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page (max 1000)
            use_cache: Whether to use cache

        Returns:
            List of Gateway server info objects

        Example:
            >>> servers = await client.list_servers(page=1, page_size=100)
            >>> len(servers)
            100
        """
        pagination = PaginationParams(page=page, page_size=page_size)
        params = pagination.to_query_params()

        try:
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/servers",
                params=params,
                use_cache=use_cache,
            )

            servers_data = response.get("servers", [])
            servers = [GatewayServerInfo(**server) for server in servers_data]

            logger.info(
                "servers_listed",
                count=len(servers),
                page=page,
                page_size=page_size,
            )

            return servers

        except Exception as e:
            logger.error("list_servers_failed", error=str(e))
            raise

    async def list_all_servers(
        self,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> list[GatewayServerInfo]:
        """List ALL MCP servers by automatically paginating through results.

        This method handles pagination automatically, fetching all pages
        until no more results are returned. Useful for large deployments
        with 1000+ servers.

        Args:
            page_size: Number of items per page (max 1000)
            use_cache: Whether to use cache

        Returns:
            Complete list of all Gateway server info objects

        Example:
            >>> all_servers = await client.list_all_servers()
            >>> len(all_servers)
            1543  # All servers across multiple pages
        """
        all_servers = []
        page = 1

        while True:
            servers = await self.list_servers(
                page=page,
                page_size=page_size,
                use_cache=use_cache,
            )

            if not servers:
                break

            all_servers.extend(servers)

            # If we got fewer results than page_size, we've reached the end
            if len(servers) < page_size:
                break

            page += 1

        logger.info("all_servers_listed", total_count=len(all_servers))
        return all_servers

    async def get_server(
        self,
        server_name: str,
        use_cache: bool = True,
    ) -> GatewayServerInfo:
        """Get specific server information by name.

        Args:
            server_name: Server name to retrieve
            use_cache: Whether to use cache

        Returns:
            Gateway server info object

        Raises:
            httpx.HTTPStatusError: If server not found (404)
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/servers/{server_name}",
                use_cache=use_cache,
            )

            server = GatewayServerInfo(**response)

            logger.info("server_retrieved", server_name=server_name)

            return server

        except Exception as e:
            logger.error("get_server_failed", server_name=server_name, error=str(e))
            raise

    async def list_tools(
        self,
        server_name: str | None = None,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> list[GatewayToolInfo]:
        """List tools available via Gateway (optionally filtered by server).

        Args:
            server_name: Optional server filter
            page: Page number (1-indexed)
            page_size: Number of items per page
            use_cache: Whether to use cache

        Returns:
            List of Gateway tool info objects

        Example:
            >>> # List all tools
            >>> all_tools = await client.list_tools()
            >>> # List tools for specific server
            >>> postgres_tools = await client.list_tools(server_name="postgres-mcp")
        """
        pagination = PaginationParams(page=page, page_size=page_size)
        params = pagination.to_query_params()

        if server_name:
            params["server"] = server_name

        try:
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/tools",
                params=params,
                use_cache=use_cache,
            )

            tools_data = response.get("tools", [])
            tools = [GatewayToolInfo(**tool) for tool in tools_data]

            logger.info(
                "tools_listed",
                count=len(tools),
                server_name=server_name,
                page=page,
            )

            return tools

        except Exception as e:
            logger.error("list_tools_failed", server_name=server_name, error=str(e))
            raise

    async def invoke_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: dict[str, Any],
        user_token: str,
        check_authorization: bool = True,
    ) -> dict[str, Any]:
        """Invoke a tool via Gateway with optional OPA authorization.

        This method:
        1. Optionally checks authorization via OPA client
        2. Forwards user JWT to Gateway
        3. Gateway validates authorization with SARK
        4. Gateway routes request to MCP server
        5. Returns tool invocation result

        Args:
            server_name: Target MCP server name
            tool_name: Tool to invoke
            parameters: Tool parameters
            user_token: User JWT token for authorization
            check_authorization: Whether to check OPA authorization first

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
            >>> result["status"]
            'success'
        """
        # Optional OPA authorization check before making Gateway request
        if check_authorization and self.opa_client:
            try:
                # Extract user context from token (simplified - in production, decode JWT)
                # For now, use token as user_id
                auth_decision = await self.opa_client.evaluate_gateway_policy(
                    user_context={"id": user_token[:8], "token": user_token},
                    action="gateway:tool:invoke",
                    server={"name": server_name},
                    tool={"name": tool_name, "parameters": parameters},
                    context={"timestamp": int(time.time())},
                )

                if not auth_decision.allow:
                    logger.warning(
                        "tool_invocation_denied_by_opa",
                        server_name=server_name,
                        tool_name=tool_name,
                        reason=auth_decision.reason,
                    )
                    raise PermissionError(
                        f"Tool invocation denied: {auth_decision.reason}"
                    )

                # Use filtered parameters if provided by OPA
                if auth_decision.filtered_parameters:
                    parameters = auth_decision.filtered_parameters

                logger.info(
                    "tool_invocation_authorized",
                    server_name=server_name,
                    tool_name=tool_name,
                )

            except PermissionError:
                raise
            except Exception as e:
                logger.error(
                    "opa_authorization_check_failed",
                    error=str(e),
                    server_name=server_name,
                    tool_name=tool_name,
                )
                # Fail closed - deny on OPA error
                raise PermissionError(f"Authorization check failed: {e!s}") from e

        # Make Gateway tool invocation request
        try:
            request_data = {
                "server": server_name,
                "tool": tool_name,
                "parameters": parameters,
            }

            response = await self._make_request(
                method="POST",
                endpoint="/api/v1/invoke",
                json_data=request_data,
                user_token=user_token,
                use_cache=False,  # Never cache tool invocations
            )

            logger.info(
                "tool_invoked",
                server_name=server_name,
                tool_name=tool_name,
            )

            return response

        except Exception as e:
            logger.error(
                "invoke_tool_failed",
                server_name=server_name,
                tool_name=tool_name,
                error=str(e),
            )
            raise

    async def health_check(self) -> dict[str, bool]:
        """Check Gateway health status.

        Returns:
            Dictionary with Gateway health status

        Example:
            >>> health = await client.health_check()
            >>> health["healthy"]
            True
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health",
                use_cache=False,  # Never cache health checks
            )

            is_healthy = response.get("status") == "healthy"

            logger.info("gateway_health_checked", healthy=is_healthy)

            return {
                "healthy": is_healthy,
                "details": response,
            }

        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
            }

    def get_cache_metrics(self) -> dict[str, Any]:
        """Get cache performance metrics.

        Returns:
            Dictionary with cache hit rate and statistics

        Example:
            >>> metrics = client.get_cache_metrics()
            >>> metrics["hit_rate"]
            0.87  # 87% hit rate
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            self._cache_hits / total_requests if total_requests > 0 else 0.0
        )

        return {
            "cache_enabled": self.cache_enabled,
            "cache_size": len(self._cache),
            "cache_maxsize": self._cache.maxsize,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 4),
        }

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("cache_cleared")
