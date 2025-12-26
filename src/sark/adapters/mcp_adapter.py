"""
MCP (Model Context Protocol) Adapter for SARK v2.0.

This adapter implements the ProtocolAdapter interface for MCP servers,
supporting stdio, SSE, and HTTP transports.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
import subprocess
import time
from typing import Any
import uuid

import httpx
import structlog

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import (
    AdapterConfigurationError,
    DiscoveryError,
    InvocationError,
    ProtocolError,
)
from sark.adapters.exceptions import (
    ConnectionError as AdapterConnectionError,
)
from sark.models.base import (
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
    ResourceSchema,
)
from sark.models.mcp_server import SensitivityLevel, TransportType

logger = structlog.get_logger(__name__)


class MCPAdapter(ProtocolAdapter):
    """
    Protocol adapter for MCP (Model Context Protocol) servers.

    Supports multiple transport types:
    - stdio: Subprocess-based communication
    - sse: Server-Sent Events over HTTP
    - http: Direct HTTP endpoints

    Example Usage:
        ```python
        adapter = MCPAdapter()

        # Discover an MCP server
        discovery_config = {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "env": {"HOME": "/path/to/home"}
        }
        resources = await adapter.discover_resources(discovery_config)

        # Get capabilities
        capabilities = await adapter.get_capabilities(resources[0])

        # Invoke a tool
        request = InvocationRequest(
            capability_id="filesystem-read_file",
            principal_id="user-123",
            arguments={"path": "/etc/hosts"}
        )
        result = await adapter.invoke(request)
        ```
    """

    # MCP Protocol version
    MCP_PROTOCOL_VERSION = "2024-11-05"

    # Default timeouts (in seconds)
    DEFAULT_DISCOVERY_TIMEOUT = 30.0
    DEFAULT_INVOCATION_TIMEOUT = 60.0
    DEFAULT_CONNECTION_TIMEOUT = 10.0

    def __init__(self):
        """Initialize the MCP adapter."""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._processes: dict[str, subprocess.Popen] = {}
        self._capability_cache: dict[str, list[CapabilitySchema]] = {}

    @property
    def protocol_name(self) -> str:
        """Return protocol identifier."""
        return "mcp"

    @property
    def protocol_version(self) -> str:
        """Return MCP protocol version."""
        return self.MCP_PROTOCOL_VERSION

    async def discover_resources(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """
        Discover MCP server and its capabilities.

        Args:
            discovery_config: MCP discovery configuration with keys:
                - transport: "stdio", "sse", or "http"
                - For stdio:
                    - command: Command to execute
                    - args: Command arguments (optional)
                    - env: Environment variables (optional)
                - For sse/http:
                    - endpoint: Server endpoint URL
                    - headers: HTTP headers (optional)

        Returns:
            List containing the discovered MCP server as a ResourceSchema

        Raises:
            DiscoveryError: If discovery fails
            AdapterConfigurationError: If config is invalid
            ConnectionError: If cannot connect to server
        """
        transport = discovery_config.get("transport")
        if not transport:
            raise AdapterConfigurationError(
                "Missing 'transport' in discovery config",
                adapter_name=self.protocol_name,
                details={"config": discovery_config},
            )

        transport_type = TransportType(transport.lower())

        try:
            if transport_type == TransportType.STDIO:
                return await self._discover_stdio(discovery_config)
            elif transport_type == TransportType.SSE:
                return await self._discover_sse(discovery_config)
            elif transport_type == TransportType.HTTP:
                return await self._discover_http(discovery_config)
            else:
                raise AdapterConfigurationError(
                    f"Unsupported transport type: {transport}",
                    adapter_name=self.protocol_name,
                )
        except Exception as e:
            if isinstance(e, (DiscoveryError, AdapterConfigurationError)):
                raise
            raise DiscoveryError(
                f"MCP discovery failed: {e!s}",
                adapter_name=self.protocol_name,
                details={"error": str(e), "config": discovery_config},
            ) from e

    async def _discover_stdio(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """
        Discover MCP server via stdio transport.

        This launches the MCP server as a subprocess and communicates via stdin/stdout.
        """
        command = discovery_config.get("command")
        if not command:
            raise AdapterConfigurationError(
                "Missing 'command' for stdio transport",
                adapter_name=self.protocol_name,
            )

        args = discovery_config.get("args", [])
        env = discovery_config.get("env", {})

        # Construct the full command
        full_command = f"{command} {' '.join(args)}" if args else command

        # Create resource ID
        resource_id = f"mcp-stdio-{uuid.uuid4().hex[:8]}"
        resource_name = discovery_config.get("name", f"MCP Server ({command})")

        logger.info(
            "mcp_stdio_discovery",
            command=command,
            args=args,
            resource_id=resource_id,
        )

        # For stdio, we'll create the resource without actually launching the process
        # The process will be launched on first invocation
        resource = ResourceSchema(
            id=resource_id,
            name=resource_name,
            protocol=self.protocol_name,
            endpoint=full_command,
            sensitivity_level=discovery_config.get("sensitivity_level", "medium"),
            metadata={
                "transport": "stdio",
                "command": command,
                "args": args,
                "env": env,
                "mcp_version": self.MCP_PROTOCOL_VERSION,
            },
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        return [resource]

    async def _discover_sse(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """
        Discover MCP server via SSE transport.

        This connects to an MCP server that exposes Server-Sent Events.
        """
        endpoint = discovery_config.get("endpoint")
        if not endpoint:
            raise AdapterConfigurationError(
                "Missing 'endpoint' for sse transport",
                adapter_name=self.protocol_name,
            )

        headers = discovery_config.get("headers", {})

        # Test connection
        try:
            response = await self._http_client.get(
                endpoint,
                headers=headers,
                timeout=self.DEFAULT_CONNECTION_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise AdapterConnectionError(
                f"Failed to connect to SSE endpoint: {e!s}",
                adapter_name=self.protocol_name,
                details={"endpoint": endpoint, "error": str(e)},
            ) from e
        except Exception as e:
            raise AdapterConnectionError(
                f"Failed to connect to SSE endpoint: {e!s}",
                adapter_name=self.protocol_name,
                details={"endpoint": endpoint, "error": str(e)},
            ) from e

        resource_id = f"mcp-sse-{uuid.uuid4().hex[:8]}"
        resource_name = discovery_config.get("name", "MCP Server (SSE)")

        resource = ResourceSchema(
            id=resource_id,
            name=resource_name,
            protocol=self.protocol_name,
            endpoint=endpoint,
            sensitivity_level=discovery_config.get("sensitivity_level", "medium"),
            metadata={
                "transport": "sse",
                "endpoint": endpoint,
                "headers": headers,
                "mcp_version": self.MCP_PROTOCOL_VERSION,
            },
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        logger.info("mcp_sse_discovery", endpoint=endpoint, resource_id=resource_id)

        return [resource]

    async def _discover_http(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """
        Discover MCP server via HTTP transport.

        This connects to an MCP server that exposes HTTP endpoints.
        """
        endpoint = discovery_config.get("endpoint")
        if not endpoint:
            raise AdapterConfigurationError(
                "Missing 'endpoint' for http transport",
                adapter_name=self.protocol_name,
            )

        headers = discovery_config.get("headers", {})

        # Test connection by trying to list tools
        try:
            response = await self._http_client.post(
                f"{endpoint}/tools/list",
                headers=headers,
                timeout=self.DEFAULT_CONNECTION_TIMEOUT,
            )
            response.raise_for_status()
        except Exception as e:
            raise AdapterConnectionError(
                f"Failed to connect to HTTP endpoint: {e!s}",
                adapter_name=self.protocol_name,
                details={"endpoint": endpoint, "error": str(e)},
            ) from e

        resource_id = f"mcp-http-{uuid.uuid4().hex[:8]}"
        resource_name = discovery_config.get("name", "MCP Server (HTTP)")

        resource = ResourceSchema(
            id=resource_id,
            name=resource_name,
            protocol=self.protocol_name,
            endpoint=endpoint,
            sensitivity_level=discovery_config.get("sensitivity_level", "medium"),
            metadata={
                "transport": "http",
                "endpoint": endpoint,
                "headers": headers,
                "mcp_version": self.MCP_PROTOCOL_VERSION,
            },
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        logger.info("mcp_http_discovery", endpoint=endpoint, resource_id=resource_id)

        return [resource]

    async def get_capabilities(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """
        Get all capabilities (tools) for an MCP server.

        Args:
            resource: The MCP server resource

        Returns:
            List of capabilities (tools) available on this server

        Raises:
            ProtocolError: If MCP communication fails
            ConnectionError: If cannot connect to server
        """
        # Check cache first
        if resource.id in self._capability_cache:
            logger.debug("capability_cache_hit", resource_id=resource.id)
            return self._capability_cache[resource.id]

        transport = resource.metadata.get("transport")

        try:
            if transport == "stdio":
                capabilities = await self._get_capabilities_stdio(resource)
            elif transport == "sse":
                capabilities = await self._get_capabilities_sse(resource)
            elif transport == "http":
                capabilities = await self._get_capabilities_http(resource)
            else:
                raise ProtocolError(
                    f"Unsupported transport: {transport}",
                    adapter_name=self.protocol_name,
                    protocol_name=self.protocol_name,
                )

            # Cache the capabilities
            self._capability_cache[resource.id] = capabilities

            logger.info(
                "mcp_capabilities_discovered",
                resource_id=resource.id,
                transport=transport,
                capability_count=len(capabilities),
            )

            return capabilities

        except Exception as e:
            if isinstance(e, ProtocolError):
                raise
            raise ProtocolError(
                f"Failed to get MCP capabilities: {e!s}",
                adapter_name=self.protocol_name,
                protocol_name=self.protocol_name,
                details={"error": str(e), "transport": transport},
            ) from e

    async def _get_capabilities_stdio(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """Get capabilities via stdio transport."""
        # For stdio, we simulate tool discovery
        # In a real implementation, we'd need to launch the process and query it
        # For now, return empty list or mock data
        logger.warning(
            "stdio_capability_discovery_stubbed",
            resource_id=resource.id,
            message="stdio transport requires process management - returning stub",
        )
        return []

    async def _get_capabilities_sse(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """Get capabilities via SSE transport."""
        endpoint = resource.metadata.get("endpoint")
        headers = resource.metadata.get("headers", {})

        try:
            # Query the tools/list endpoint
            response = await self._http_client.get(f"{endpoint}/tools/list", headers=headers)
            response.raise_for_status()
            tools_data = response.json()

            return self._parse_mcp_tools(resource, tools_data.get("tools", []))

        except Exception as e:
            raise ProtocolError(
                f"SSE capability query failed: {e!s}",
                adapter_name=self.protocol_name,
                protocol_name=self.protocol_name,
                resource_id=resource.id,
            ) from e

    async def _get_capabilities_http(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """Get capabilities via HTTP transport."""
        endpoint = resource.metadata.get("endpoint")
        headers = resource.metadata.get("headers", {})

        try:
            # Query the tools/list endpoint
            response = await self._http_client.post(
                f"{endpoint}/tools/list", headers=headers, json={}
            )
            response.raise_for_status()
            tools_data = response.json()

            return self._parse_mcp_tools(resource, tools_data.get("tools", []))

        except Exception as e:
            raise ProtocolError(
                f"HTTP capability query failed: {e!s}",
                adapter_name=self.protocol_name,
                protocol_name=self.protocol_name,
                resource_id=resource.id,
            ) from e

    def _parse_mcp_tools(
        self, resource: ResourceSchema, tools: list[dict[str, Any]]
    ) -> list[CapabilitySchema]:
        """
        Parse MCP tools into CapabilitySchema objects.

        Args:
            resource: The parent resource
            tools: List of MCP tool definitions

        Returns:
            List of CapabilitySchema objects
        """
        capabilities = []

        for tool in tools:
            tool_name = tool.get("name", "unknown")
            capability_id = f"{resource.id}-{tool_name}"

            # Auto-detect sensitivity based on tool name/description
            sensitivity = self._detect_tool_sensitivity(tool_name, tool.get("description", ""))

            capability = CapabilitySchema(
                id=capability_id,
                resource_id=resource.id,
                name=tool_name,
                description=tool.get("description"),
                input_schema=tool.get("inputSchema", {}),
                output_schema={},  # MCP doesn't define output schemas
                sensitivity_level=sensitivity,
                metadata={
                    "mcp_tool": True,
                    "requires_approval": tool.get("requiresApproval", False),
                },
            )

            capabilities.append(capability)

        return capabilities

    def _detect_tool_sensitivity(self, tool_name: str, tool_description: str) -> str:
        """
        Auto-detect sensitivity level for an MCP tool.

        Uses keyword-based detection similar to ToolRegistry.
        """
        text = f"{tool_name} {tool_description}".lower()

        # Critical keywords
        critical_keywords = [
            "payment",
            "transaction",
            "credit_card",
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "encrypt",
            "decrypt",
        ]
        if any(kw in text for kw in critical_keywords):
            return SensitivityLevel.CRITICAL.value

        # High keywords
        high_keywords = [
            "delete",
            "drop",
            "exec",
            "execute",
            "admin",
            "root",
            "sudo",
            "kill",
            "destroy",
            "remove",
        ]
        if any(kw in text for kw in high_keywords):
            return SensitivityLevel.HIGH.value

        # Medium keywords
        medium_keywords = [
            "write",
            "update",
            "modify",
            "change",
            "edit",
            "create",
            "insert",
            "save",
        ]
        if any(kw in text for kw in medium_keywords):
            return SensitivityLevel.MEDIUM.value

        # Low keywords
        low_keywords = ["read", "get", "list", "fetch", "view", "show", "query"]
        if any(kw in text for kw in low_keywords):
            return SensitivityLevel.LOW.value

        # Default to medium
        return SensitivityLevel.MEDIUM.value

    async def validate_request(self, request: InvocationRequest) -> bool:
        """
        Validate an MCP invocation request.

        Args:
            request: The invocation request

        Returns:
            True if valid, False if invalid (or raises ValidationError)
        """
        # Check if capability_id has correct MCP prefix format
        # Valid MCP capability IDs start with "mcp-"
        if not request.capability_id.startswith("mcp-"):
            return False

        # Extract resource_id from capability_id (format: mcp-transport-id-tool_name)
        parts = request.capability_id.rsplit("-", 1)
        if len(parts) != 2:
            # Return False for invalid format
            return False

        # If we have cached capabilities for this resource, verify the capability exists
        resource_id = parts[0]
        if resource_id in self._capability_cache:
            capability_ids = [cap.id for cap in self._capability_cache[resource_id]]
            if request.capability_id not in capability_ids:
                # Return False if capability not found in cache
                return False

        return True

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        """
        Invoke an MCP tool.

        Args:
            request: The invocation request

        Returns:
            InvocationResult with the tool execution results

        Raises:
            InvocationError: If invocation fails
            CapabilityNotFoundError: If tool doesn't exist
        """
        start_time = time.time()

        try:
            # Extract resource_id and tool_name from capability_id
            parts = request.capability_id.rsplit("-", 1)
            resource_id = parts[0]
            tool_name = parts[1]

            # Get the resource (we'd need to fetch from DB in real implementation)
            # For now, we'll use cached capabilities to determine transport
            transport = None
            for cached_resource_id, capabilities in self._capability_cache.items():
                if cached_resource_id == resource_id:
                    # We'd need resource metadata here
                    # For now, raise an error indicating we need the resource
                    break

            # This is a simplified implementation
            # In production, we'd:
            # 1. Look up the resource from database
            # 2. Determine transport type
            # 3. Route to appropriate invoke method

            logger.warning(
                "mcp_invoke_stubbed",
                capability_id=request.capability_id,
                message="Full MCP invocation requires resource lookup",
            )

            # Return a stubbed success result
            duration_ms = (time.time() - start_time) * 1000

            return InvocationResult(
                success=True,
                result={
                    "message": "MCP invocation stubbed - implementation in progress",
                    "tool_name": tool_name,
                    "arguments": request.arguments,
                },
                metadata={
                    "adapter": self.protocol_name,
                    "stubbed": True,
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            raise InvocationError(
                f"MCP tool invocation failed: {e!s}",
                adapter_name=self.protocol_name,
                capability_id=request.capability_id,
                protocol_error=str(e),
            ) from e

    async def health_check(self, resource: ResourceSchema) -> bool:
        """
        Check if an MCP server is healthy.

        Args:
            resource: The MCP server resource

        Returns:
            True if healthy, False otherwise
        """
        transport = resource.metadata.get("transport")

        try:
            if transport == "http":
                endpoint = resource.metadata.get("endpoint")
                headers = resource.metadata.get("headers", {})
                response = await self._http_client.get(
                    f"{endpoint}/health",
                    headers=headers,
                    timeout=5.0,
                )
                return response.status_code == 200
            elif transport == "sse":
                endpoint = resource.metadata.get("endpoint")
                headers = resource.metadata.get("headers", {})
                response = await self._http_client.get(
                    endpoint,
                    headers=headers,
                    timeout=5.0,
                )
                return response.status_code == 200
            elif transport == "stdio":
                # For stdio, we can't easily health check without launching
                # Return True assuming it will work when needed
                return True
            else:
                return False
        except Exception:
            return False

    async def invoke_streaming(self, request: InvocationRequest) -> AsyncIterator[Any]:
        """
        Invoke an MCP tool with streaming support (for SSE transport).

        Args:
            request: The invocation request

        Yields:
            Response chunks from the MCP server

        Raises:
            UnsupportedOperationError: If transport doesn't support streaming
            StreamingError: If streaming fails
        """
        # Extract resource info
        parts = request.capability_id.rsplit("-", 1)
        resource_id = parts[0]

        # In real implementation, we'd look up the resource and check transport
        # For now, this is a stub

        logger.info(
            "mcp_streaming_invocation",
            capability_id=request.capability_id,
            message="Streaming support requires full resource lookup",
        )

        # Yield a stub response
        yield {"type": "start", "capability_id": request.capability_id}
        yield {
            "type": "data",
            "message": "Streaming stubbed - implementation in progress",
        }
        yield {"type": "end", "status": "complete"}

    def get_adapter_metadata(self) -> dict[str, Any]:
        """Get MCP adapter-specific metadata."""
        return {
            "transport_types": ["stdio", "sse", "http"],
            "mcp_protocol_version": self.MCP_PROTOCOL_VERSION,
            "mcp_features": ["tools", "prompts", "resources"],
            "supports_streaming": True,
            "supports_batch": False,
        }

    async def on_resource_registered(self, resource: ResourceSchema) -> None:
        """
        Lifecycle hook called when an MCP server is registered.

        Warms the capability cache.
        """
        try:
            # Warm the cache
            await self.get_capabilities(resource)
            logger.info(
                "mcp_resource_registered",
                resource_id=resource.id,
                transport=resource.metadata.get("transport"),
            )
        except Exception as e:
            logger.error(
                "mcp_resource_registration_failed",
                resource_id=resource.id,
                error=str(e),
            )
            raise

    async def on_resource_unregistered(self, resource: ResourceSchema) -> None:
        """
        Lifecycle hook called when an MCP server is unregistered.

        Cleans up cache and any running processes.
        """
        # Clear cache
        self._capability_cache.pop(resource.id, None)

        # Clean up any running stdio processes
        if resource.id in self._processes:
            process = self._processes.pop(resource.id)
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logger.warning(
                    "mcp_process_cleanup_failed",
                    resource_id=resource.id,
                    error=str(e),
                )

        logger.info("mcp_resource_unregistered", resource_id=resource.id)

    def __del__(self):
        """Cleanup on adapter deletion."""
        # Close HTTP client
        try:
            import asyncio

            asyncio.create_task(self._http_client.aclose())
        except Exception:
            pass


__all__ = ["MCPAdapter"]
