"""
Test suite for MCPAdapter - validates MCP protocol adapter implementation.

This test suite ensures the MCP adapter correctly implements the ProtocolAdapter
interface and handles MCP-specific functionality.
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import (
    AdapterConfigurationError,
    DiscoveryError,
)
from sark.adapters.exceptions import (
    ConnectionError as AdapterConnectionError,
)
from sark.adapters.mcp_adapter import MCPAdapter
from sark.models.base import (
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
    ResourceSchema,
)
from tests.adapters.base_adapter_test import BaseAdapterTest

# ============================================================================
# Contract Tests for MCPAdapter
# ============================================================================


class TestMCPAdapterContract(BaseAdapterTest):
    """
    Contract tests for MCPAdapter.

    These tests verify that MCPAdapter complies with the ProtocolAdapter interface.
    """

    @pytest.fixture
    def adapter(self) -> ProtocolAdapter:
        """Return an MCPAdapter instance."""
        return MCPAdapter()

    @pytest.fixture
    def discovery_config(self) -> dict[str, Any]:
        """Return valid discovery configuration for stdio transport."""
        return {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "env": {"HOME": "/tmp"},
            "name": "Test Filesystem Server",
        }

    @pytest.fixture
    def sample_resource(self) -> ResourceSchema:
        """Return a sample MCP resource."""
        return ResourceSchema(
            id="mcp-stdio-test123",
            name="Test MCP Server",
            protocol="mcp",
            endpoint="npx -y @modelcontextprotocol/server-filesystem",
            sensitivity_level="medium",
            metadata={
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "env": {},
                "mcp_version": "2024-11-05",
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.fixture
    def sample_capability(self) -> CapabilitySchema:
        """Return a sample MCP capability."""
        return CapabilitySchema(
            id="mcp-stdio-test123-read_file",
            resource_id="mcp-stdio-test123",
            name="read_file",
            description="Read a file from the filesystem",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            output_schema={},
            sensitivity_level="medium",
            metadata={"mcp_tool": True},
        )

    @pytest.fixture
    def valid_invocation_request(self) -> InvocationRequest:
        """Return a valid MCP invocation request."""
        return InvocationRequest(
            capability_id="mcp-stdio-test123-read_file",
            principal_id="user-123",
            arguments={"path": "/etc/hosts"},
        )

    # All contract tests are inherited from BaseAdapterTest


# ============================================================================
# MCP-Specific Tests
# ============================================================================


class TestMCPAdapterDiscovery:
    """Test MCP server discovery functionality."""

    @pytest.mark.asyncio
    async def test_discover_stdio_transport(self):
        """MCPAdapter should discover stdio transport servers."""
        adapter = MCPAdapter()

        config = {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "name": "Filesystem Server",
        }

        resources = await adapter.discover_resources(config)

        assert len(resources) == 1
        resource = resources[0]
        assert resource.protocol == "mcp"
        assert resource.name == "Filesystem Server"
        assert resource.metadata["transport"] == "stdio"
        assert resource.metadata["command"] == "npx"
        assert resource.metadata["args"] == ["-y", "@modelcontextprotocol/server-filesystem"]

    @pytest.mark.asyncio
    async def test_discover_sse_transport(self):
        """MCPAdapter should discover SSE transport servers."""
        adapter = MCPAdapter()

        config = {
            "transport": "sse",
            "endpoint": "http://localhost:8080/sse",
            "name": "SSE Server",
        }

        # Mock the HTTP client
        with patch.object(adapter._http_client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            resources = await adapter.discover_resources(config)

            assert len(resources) == 1
            resource = resources[0]
            assert resource.protocol == "mcp"
            assert resource.metadata["transport"] == "sse"
            assert resource.metadata["endpoint"] == "http://localhost:8080/sse"

    @pytest.mark.asyncio
    async def test_discover_http_transport(self):
        """MCPAdapter should discover HTTP transport servers."""
        adapter = MCPAdapter()

        config = {
            "transport": "http",
            "endpoint": "http://localhost:8080",
            "name": "HTTP Server",
        }

        # Mock the HTTP client
        with patch.object(adapter._http_client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            resources = await adapter.discover_resources(config)

            assert len(resources) == 1
            resource = resources[0]
            assert resource.protocol == "mcp"
            assert resource.metadata["transport"] == "http"
            assert resource.metadata["endpoint"] == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_discover_missing_transport(self):
        """MCPAdapter should raise error if transport is missing."""
        adapter = MCPAdapter()

        config = {"command": "npx"}

        with pytest.raises(AdapterConfigurationError) as exc_info:
            await adapter.discover_resources(config)

        assert "transport" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_discover_missing_command_for_stdio(self):
        """MCPAdapter should raise error if command is missing for stdio."""
        adapter = MCPAdapter()

        config = {"transport": "stdio"}

        with pytest.raises(AdapterConfigurationError) as exc_info:
            await adapter.discover_resources(config)

        assert "command" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_discover_missing_endpoint_for_sse(self):
        """MCPAdapter should raise error if endpoint is missing for SSE."""
        adapter = MCPAdapter()

        config = {"transport": "sse"}

        with pytest.raises(AdapterConfigurationError) as exc_info:
            await adapter.discover_resources(config)

        assert "endpoint" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_discover_sse_connection_failure(self):
        """MCPAdapter should handle SSE connection failures."""
        adapter = MCPAdapter()

        config = {
            "transport": "sse",
            "endpoint": "http://invalid-endpoint:9999",
        }

        # Mock connection failure
        with patch.object(adapter._http_client, "get") as mock_get:
            import httpx

            # Wrap the exception properly
            async def raise_error(*args, **kwargs):
                raise httpx.ConnectError("Connection refused")

            mock_get.side_effect = raise_error

            with pytest.raises((AdapterConnectionError, DiscoveryError)):
                await adapter.discover_resources(config)


class TestMCPAdapterCapabilities:
    """Test MCP capability discovery."""

    @pytest.mark.asyncio
    async def test_get_capabilities_http(self):
        """MCPAdapter should get capabilities from HTTP server."""
        adapter = MCPAdapter()

        resource = ResourceSchema(
            id="mcp-http-test",
            name="Test Server",
            protocol="mcp",
            endpoint="http://localhost:8080",
            sensitivity_level="medium",
            metadata={
                "transport": "http",
                "endpoint": "http://localhost:8080",
                "headers": {},
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Mock HTTP response with tools
        tools_response = {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                },
                {
                    "name": "write_file",
                    "description": "Write to a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                },
            ]
        }

        with patch.object(adapter._http_client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = tools_response
            mock_post.return_value = mock_response

            capabilities = await adapter.get_capabilities(resource)

            assert len(capabilities) == 2
            assert capabilities[0].name == "read_file"
            assert capabilities[1].name == "write_file"
            assert capabilities[0].resource_id == resource.id
            assert capabilities[0].metadata["mcp_tool"] is True

    @pytest.mark.asyncio
    async def test_get_capabilities_caching(self):
        """MCPAdapter should cache capabilities."""
        adapter = MCPAdapter()

        resource = ResourceSchema(
            id="mcp-http-test",
            name="Test Server",
            protocol="mcp",
            endpoint="http://localhost:8080",
            sensitivity_level="medium",
            metadata={
                "transport": "http",
                "endpoint": "http://localhost:8080",
                "headers": {},
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        tools_response = {"tools": [{"name": "test_tool", "description": "Test"}]}

        with patch.object(adapter._http_client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = tools_response
            mock_post.return_value = mock_response

            # First call - should hit server
            capabilities1 = await adapter.get_capabilities(resource)
            assert mock_post.call_count == 1

            # Second call - should use cache
            capabilities2 = await adapter.get_capabilities(resource)
            assert mock_post.call_count == 1  # No additional call

            assert capabilities1 == capabilities2

    @pytest.mark.asyncio
    async def test_sensitivity_detection_critical(self):
        """MCPAdapter should detect critical sensitivity keywords."""
        adapter = MCPAdapter()

        sensitivity = adapter._detect_tool_sensitivity(
            "decrypt_password", "Decrypt a password using secret key"
        )

        assert sensitivity == "critical"

    @pytest.mark.asyncio
    async def test_sensitivity_detection_high(self):
        """MCPAdapter should detect high sensitivity keywords."""
        adapter = MCPAdapter()

        sensitivity = adapter._detect_tool_sensitivity("delete_database", "Delete entire database")

        assert sensitivity == "high"

    @pytest.mark.asyncio
    async def test_sensitivity_detection_medium(self):
        """MCPAdapter should detect medium sensitivity keywords."""
        adapter = MCPAdapter()

        sensitivity = adapter._detect_tool_sensitivity("write_file", "Write content to a file")

        assert sensitivity == "medium"

    @pytest.mark.asyncio
    async def test_sensitivity_detection_low(self):
        """MCPAdapter should detect low sensitivity keywords."""
        adapter = MCPAdapter()

        sensitivity = adapter._detect_tool_sensitivity("read_file", "Read a file from disk")

        assert sensitivity == "low"


class TestMCPAdapterValidation:
    """Test MCP request validation."""

    @pytest.mark.asyncio
    async def test_validate_request_valid_format(self):
        """MCPAdapter should validate requests with correct format."""
        adapter = MCPAdapter()

        request = InvocationRequest(
            capability_id="mcp-test-resource-tool_name",
            principal_id="user-123",
            arguments={},
        )

        result = await adapter.validate_request(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_request_invalid_format(self):
        """MCPAdapter should reject requests with invalid format."""
        adapter = MCPAdapter()

        request = InvocationRequest(
            capability_id="invalid_format",  # Missing resource-tool separator
            principal_id="user-123",
            arguments={},
        )

        # Should return False (contract allows both False and ValidationError)
        result = await adapter.validate_request(request)
        assert result is False


class TestMCPAdapterInvocation:
    """Test MCP tool invocation."""

    @pytest.mark.asyncio
    async def test_invoke_returns_result(self):
        """MCPAdapter should return invocation result."""
        adapter = MCPAdapter()

        request = InvocationRequest(
            capability_id="mcp-test-read_file",
            principal_id="user-123",
            arguments={"path": "/etc/hosts"},
        )

        result = await adapter.invoke(request)

        assert isinstance(result, InvocationResult)
        assert result.success is True
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_streaming(self):
        """MCPAdapter should support streaming invocation."""
        adapter = MCPAdapter()

        request = InvocationRequest(
            capability_id="mcp-test-stream_tool",
            principal_id="user-123",
            arguments={},
        )

        chunks = []
        async for chunk in adapter.invoke_streaming(request):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert chunks[0]["type"] == "start"
        assert chunks[-1]["type"] == "end"


class TestMCPAdapterHealthCheck:
    """Test MCP server health checks."""

    @pytest.mark.asyncio
    async def test_health_check_http_healthy(self):
        """MCPAdapter should report HTTP server as healthy."""
        adapter = MCPAdapter()

        resource = ResourceSchema(
            id="mcp-http-test",
            name="Test Server",
            protocol="mcp",
            endpoint="http://localhost:8080",
            sensitivity_level="medium",
            metadata={"transport": "http", "endpoint": "http://localhost:8080"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch.object(adapter._http_client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            is_healthy = await adapter.health_check(resource)
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_http_unhealthy(self):
        """MCPAdapter should report HTTP server as unhealthy on error."""
        adapter = MCPAdapter()

        resource = ResourceSchema(
            id="mcp-http-test",
            name="Test Server",
            protocol="mcp",
            endpoint="http://localhost:8080",
            sensitivity_level="medium",
            metadata={"transport": "http", "endpoint": "http://localhost:8080"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch.object(adapter._http_client, "get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            is_healthy = await adapter.health_check(resource)
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_stdio_always_healthy(self):
        """MCPAdapter should report stdio as healthy by default."""
        adapter = MCPAdapter()

        resource = ResourceSchema(
            id="mcp-stdio-test",
            name="Test Server",
            protocol="mcp",
            endpoint="npx test",
            sensitivity_level="medium",
            metadata={"transport": "stdio", "command": "npx"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        is_healthy = await adapter.health_check(resource)
        assert is_healthy is True


class TestMCPAdapterLifecycle:
    """Test MCP adapter lifecycle hooks."""

    @pytest.mark.asyncio
    async def test_on_resource_registered_warms_cache(self):
        """MCPAdapter should warm capability cache on registration."""
        adapter = MCPAdapter()

        resource = ResourceSchema(
            id="mcp-http-test",
            name="Test Server",
            protocol="mcp",
            endpoint="http://localhost:8080",
            sensitivity_level="medium",
            metadata={"transport": "http", "endpoint": "http://localhost:8080"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch.object(adapter._http_client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"tools": []}
            mock_post.return_value = mock_response

            await adapter.on_resource_registered(resource)

            # Cache should be populated
            assert resource.id in adapter._capability_cache

    @pytest.mark.asyncio
    async def test_on_resource_unregistered_clears_cache(self):
        """MCPAdapter should clear cache on unregistration."""
        adapter = MCPAdapter()

        resource = ResourceSchema(
            id="mcp-test",
            name="Test Server",
            protocol="mcp",
            endpoint="http://localhost:8080",
            sensitivity_level="medium",
            metadata={"transport": "http"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Add to cache
        adapter._capability_cache[resource.id] = []

        await adapter.on_resource_unregistered(resource)

        # Cache should be cleared
        assert resource.id not in adapter._capability_cache


class TestMCPAdapterMetadata:
    """Test MCP adapter metadata."""

    def test_adapter_info(self):
        """MCPAdapter should provide complete adapter info."""
        adapter = MCPAdapter()

        info = adapter.get_adapter_info()

        assert info["protocol_name"] == "mcp"
        assert info["protocol_version"] == "2024-11-05"
        assert info["adapter_class"] == "MCPAdapter"
        assert info["supports_streaming"] is True

    def test_adapter_metadata(self):
        """MCPAdapter should provide MCP-specific metadata."""
        adapter = MCPAdapter()

        metadata = adapter.get_adapter_metadata()

        assert "transport_types" in metadata
        assert "stdio" in metadata["transport_types"]
        assert "sse" in metadata["transport_types"]
        assert "http" in metadata["transport_types"]
        assert metadata["mcp_protocol_version"] == "2024-11-05"

    def test_protocol_properties(self):
        """MCPAdapter should have correct protocol properties."""
        adapter = MCPAdapter()

        assert adapter.protocol_name == "mcp"
        assert adapter.protocol_version == "2024-11-05"
        assert isinstance(adapter.protocol_name, str)
        assert isinstance(adapter.protocol_version, str)
