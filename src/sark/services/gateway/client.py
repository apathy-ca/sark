"""Gateway client service.

Placeholder implementation for Gateway HTTP client.
Full implementation will be provided by Engineer 1.

This provides the interface that Engineer 2's API endpoints depend on.
"""

import structlog
from typing import Optional

from sark.models.gateway import GatewayServerInfo, GatewayToolInfo

logger = structlog.get_logger()

# Singleton gateway client instance
_gateway_client: Optional["GatewayClient"] = None


class GatewayClient:
    """
    HTTP client for communicating with MCP Gateway.

    Placeholder implementation - full version by Engineer 1 will include:
    - Circuit breaker pattern
    - Retry logic with exponential backoff
    - Connection pooling
    - Health checks
    - Metrics collection
    """

    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 5.0):
        """
        Initialize Gateway client.

        Args:
            base_url: Gateway base URL (e.g., "http://localhost:8080")
            api_key: Optional API key for Gateway authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        logger.info(
            "gateway_client_initialized",
            base_url=base_url,
            has_api_key=bool(api_key),
        )

    async def list_servers(self) -> list[GatewayServerInfo]:
        """
        List all MCP servers registered with Gateway.

        Placeholder implementation returns empty list.
        Full implementation by Engineer 1 will query Gateway's /servers endpoint.

        Returns:
            List of Gateway server info objects
        """
        logger.warning(
            "gateway_client_placeholder",
            method="list_servers",
            message="Using placeholder implementation - returns empty list",
        )
        # TODO(Engineer 1): Implement actual Gateway HTTP request
        # GET {base_url}/servers
        return []

    async def list_tools(self, server_name: str | None = None) -> list[GatewayToolInfo]:
        """
        List tools available via Gateway.

        Placeholder implementation returns empty list.
        Full implementation by Engineer 1 will query Gateway's /tools endpoint.

        Args:
            server_name: Optional server filter

        Returns:
            List of Gateway tool info objects
        """
        logger.warning(
            "gateway_client_placeholder",
            method="list_tools",
            server_name=server_name,
            message="Using placeholder implementation - returns empty list",
        )
        # TODO(Engineer 1): Implement actual Gateway HTTP request
        # GET {base_url}/tools?server={server_name}
        return []

    async def invoke_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: dict,
        user_token: str,
    ) -> dict:
        """
        Invoke a tool via Gateway (with authorization).

        Placeholder implementation raises NotImplementedError.
        Full implementation by Engineer 1 will:
        1. Forward user JWT to Gateway
        2. Gateway calls SARK /authorize endpoint
        3. Gateway routes to MCP server if authorized
        4. Return tool result

        Args:
            server_name: Target MCP server name
            tool_name: Tool to invoke
            parameters: Tool parameters
            user_token: User JWT token for authorization

        Returns:
            Tool invocation result

        Raises:
            NotImplementedError: Placeholder - not yet implemented
        """
        logger.warning(
            "gateway_client_placeholder",
            method="invoke_tool",
            server_name=server_name,
            tool_name=tool_name,
            message="Using placeholder implementation - raises NotImplementedError",
        )
        # TODO(Engineer 1): Implement actual Gateway HTTP request
        # POST {base_url}/invoke
        # Headers: Authorization: Bearer {user_token}
        # Body: {server: server_name, tool: tool_name, parameters: parameters}
        raise NotImplementedError("Gateway tool invocation not yet implemented by Engineer 1")

    async def health_check(self) -> bool:
        """
        Check Gateway health.

        Placeholder implementation returns False.
        Full implementation by Engineer 1 will query Gateway's health endpoint.

        Returns:
            True if Gateway is healthy, False otherwise
        """
        logger.warning(
            "gateway_client_placeholder",
            method="health_check",
            message="Using placeholder implementation - returns False",
        )
        # TODO(Engineer 1): Implement actual Gateway HTTP request
        # GET {base_url}/health
        return False


async def get_gateway_client() -> GatewayClient:
    """
    Get singleton Gateway client instance.

    Initializes client from settings if not already created.

    Returns:
        GatewayClient instance
    """
    global _gateway_client

    if _gateway_client is None:
        from sark.config import get_settings

        settings = get_settings()

        if not settings.gateway_enabled:
            logger.warning("gateway_disabled", message="Gateway integration is disabled in settings")

        _gateway_client = GatewayClient(
            base_url=settings.gateway_url,
            api_key=settings.gateway_api_key,
            timeout=settings.gateway_timeout_seconds,
        )

    return _gateway_client
