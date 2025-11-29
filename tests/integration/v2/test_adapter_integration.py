"""
Integration tests for SARK v2.0 protocol adapters.

Tests adapter functionality including:
- Resource discovery across protocols
- Capability enumeration
- Request validation
- Capability invocation
- Health checking
- Lifecycle hooks
- Adapter registry integration
"""

import pytest
from unittest.mock import AsyncMock

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import ValidationError, UnsupportedOperationError
from sark.models.base import InvocationRequest


# ============================================================================
# Adapter Registry Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
class TestAdapterRegistry:
    """Test the adapter registry functionality."""

    def test_register_adapter(self, adapter_registry, mock_mcp_adapter):
        """Test registering a single adapter."""
        adapter_registry.register(mock_mcp_adapter)

        assert adapter_registry.supports("mcp")
        assert adapter_registry.get("mcp") == mock_mcp_adapter
        assert "mcp" in adapter_registry.list_protocols()

    def test_register_duplicate_adapter(self, adapter_registry, mock_mcp_adapter):
        """Test that registering duplicate adapter raises error."""
        adapter_registry.register(mock_mcp_adapter)

        with pytest.raises(ValueError, match="already registered"):
            adapter_registry.register(mock_mcp_adapter)

    def test_register_multiple_adapters(self, populated_registry):
        """Test registering multiple adapters."""
        protocols = populated_registry.list_protocols()

        assert len(protocols) == 3
        assert "mcp" in protocols
        assert "http" in protocols
        assert "grpc" in protocols

    def test_unregister_adapter(self, adapter_registry, mock_mcp_adapter):
        """Test unregistering an adapter."""
        adapter_registry.register(mock_mcp_adapter)
        assert adapter_registry.supports("mcp")

        adapter_registry.unregister("mcp")
        assert not adapter_registry.supports("mcp")
        assert adapter_registry.get("mcp") is None

    def test_unregister_nonexistent_adapter(self, adapter_registry):
        """Test unregistering non-existent adapter raises error."""
        with pytest.raises(KeyError, match="No adapter registered"):
            adapter_registry.unregister("nonexistent")

    def test_get_adapter_info(self, populated_registry):
        """Test getting registry information."""
        info = populated_registry.get_info()

        assert info["initialized"] == False  # Not explicitly initialized
        assert info["adapter_count"] == 3
        assert len(info["protocols"]) == 3

    def test_adapter_lookup_by_protocol(self, populated_registry):
        """Test looking up adapters by protocol name."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        assert mcp_adapter is not None
        assert mcp_adapter.protocol_name == "mcp"

        assert http_adapter is not None
        assert http_adapter.protocol_name == "http"

        assert grpc_adapter is not None
        assert grpc_adapter.protocol_name == "grpc"


# ============================================================================
# MCP Adapter Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
class TestMCPAdapter:
    """Test MCP adapter implementation."""

    @pytest.mark.asyncio
    async def test_mcp_discovery(self, mock_mcp_adapter):
        """Test MCP server discovery."""
        config = {
            "name": "filesystem-server",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "transport": "stdio",
        }

        resources = await mock_mcp_adapter.discover_resources(config)

        assert len(resources) == 1
        resource = resources[0]
        assert resource.protocol == "mcp"
        assert resource.name == "filesystem-server"
        assert resource.endpoint == "npx"

    @pytest.mark.asyncio
    async def test_mcp_get_capabilities(self, mock_mcp_adapter, sample_mcp_resource):
        """Test getting MCP tool capabilities."""
        capabilities = await mock_mcp_adapter.get_capabilities(sample_mcp_resource)

        assert len(capabilities) >= 2

        # Check for expected tools
        tool_names = [cap.name for cap in capabilities]
        assert "read_file" in tool_names
        assert "list_files" in tool_names

    @pytest.mark.asyncio
    async def test_mcp_validate_request(self, mock_mcp_adapter, sample_invocation_request):
        """Test MCP request validation."""
        is_valid = await mock_mcp_adapter.validate_request(sample_invocation_request)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_mcp_invoke(self, mock_mcp_adapter, sample_invocation_request):
        """Test MCP tool invocation."""
        result = await mock_mcp_adapter.invoke(sample_invocation_request)

        assert result.success is True
        assert result.result is not None
        assert "content" in result.result
        assert result.duration_ms > 0
        assert result.metadata["adapter"] == "mcp"

    @pytest.mark.asyncio
    async def test_mcp_health_check(self, mock_mcp_adapter, sample_mcp_resource):
        """Test MCP server health check."""
        is_healthy = await mock_mcp_adapter.health_check(sample_mcp_resource)
        assert is_healthy is True

    def test_mcp_adapter_info(self, mock_mcp_adapter):
        """Test MCP adapter metadata."""
        info = mock_mcp_adapter.get_adapter_info()

        assert info["protocol_name"] == "mcp"
        assert info["protocol_version"] == "2024-11-05"
        assert info["adapter_class"] == "MockMCPAdapter"


# ============================================================================
# HTTP Adapter Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
class TestHTTPAdapter:
    """Test HTTP/REST adapter implementation."""

    @pytest.mark.asyncio
    async def test_http_discovery(self, mock_http_adapter):
        """Test HTTP API discovery via OpenAPI."""
        config = {
            "name": "GitHub API",
            "base_url": "https://api.github.com",
            "openapi_spec_url": "https://api.github.com/openapi.json",
            "auth_type": "bearer",
        }

        resources = await mock_http_adapter.discover_resources(config)

        assert len(resources) == 1
        resource = resources[0]
        assert resource.protocol == "http"
        assert resource.name == "GitHub API"
        assert resource.endpoint == "https://api.github.com"
        assert resource.metadata["auth_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_http_get_capabilities(self, mock_http_adapter, sample_http_resource):
        """Test getting HTTP endpoint capabilities."""
        capabilities = await mock_http_adapter.get_capabilities(sample_http_resource)

        assert len(capabilities) >= 2

        # Check for expected endpoints
        endpoint_names = [cap.name for cap in capabilities]
        assert "list_users" in endpoint_names
        assert "create_user" in endpoint_names

        # Verify metadata includes HTTP details
        for cap in capabilities:
            assert "http_method" in cap.metadata
            assert "http_path" in cap.metadata

    @pytest.mark.asyncio
    async def test_http_invoke(self, mock_http_adapter, sample_invocation_request):
        """Test HTTP API invocation."""
        result = await mock_http_adapter.invoke(sample_invocation_request)

        assert result.success is True
        assert result.result is not None
        assert "status" in result.result
        assert result.result["status"] == 200
        assert result.metadata["adapter"] == "http"

    @pytest.mark.asyncio
    async def test_http_health_check(self, mock_http_adapter, sample_http_resource):
        """Test HTTP API health check."""
        is_healthy = await mock_http_adapter.health_check(sample_http_resource)
        assert is_healthy is True

    def test_http_adapter_info(self, mock_http_adapter):
        """Test HTTP adapter metadata."""
        info = mock_http_adapter.get_adapter_info()

        assert info["protocol_name"] == "http"
        assert info["protocol_version"] == "1.1"
        assert info["adapter_class"] == "MockHTTPAdapter"


# ============================================================================
# gRPC Adapter Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
class TestGRPCAdapter:
    """Test gRPC adapter implementation."""

    @pytest.mark.asyncio
    async def test_grpc_discovery(self, mock_grpc_adapter):
        """Test gRPC service discovery via reflection."""
        config = {
            "name": "User Service",
            "endpoint": "localhost:50051",
            "use_reflection": True,
        }

        resources = await mock_grpc_adapter.discover_resources(config)

        assert len(resources) == 1
        resource = resources[0]
        assert resource.protocol == "grpc"
        assert resource.name == "User Service"
        assert resource.endpoint == "localhost:50051"
        assert resource.metadata["use_reflection"] is True

    @pytest.mark.asyncio
    async def test_grpc_get_capabilities(self, mock_grpc_adapter, sample_grpc_resource):
        """Test getting gRPC method capabilities."""
        capabilities = await mock_grpc_adapter.get_capabilities(sample_grpc_resource)

        assert len(capabilities) >= 2

        # Check for expected methods
        method_names = [cap.name for cap in capabilities]
        assert "GetUser" in method_names
        assert "ListUsers" in method_names

        # Verify metadata includes gRPC details
        for cap in capabilities:
            assert "service" in cap.metadata
            assert "method" in cap.metadata
            assert "streaming" in cap.metadata

    @pytest.mark.asyncio
    async def test_grpc_invoke(self, mock_grpc_adapter, sample_invocation_request):
        """Test gRPC method invocation."""
        result = await mock_grpc_adapter.invoke(sample_invocation_request)

        assert result.success is True
        assert result.result is not None
        assert "user_id" in result.result
        assert result.metadata["adapter"] == "grpc"

    @pytest.mark.asyncio
    async def test_grpc_streaming_invoke(self, mock_grpc_adapter, sample_invocation_request):
        """Test gRPC streaming method invocation."""
        chunks = []
        async for chunk in mock_grpc_adapter.invoke_streaming(sample_invocation_request):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert all("index" in chunk for chunk in chunks)
        assert all("data" in chunk for chunk in chunks)

    @pytest.mark.asyncio
    async def test_grpc_health_check(self, mock_grpc_adapter, sample_grpc_resource):
        """Test gRPC service health check."""
        is_healthy = await mock_grpc_adapter.health_check(sample_grpc_resource)
        assert is_healthy is True

    def test_grpc_supports_streaming(self, mock_grpc_adapter):
        """Test that gRPC adapter supports streaming."""
        assert mock_grpc_adapter.supports_streaming() is True

    def test_grpc_adapter_info(self, mock_grpc_adapter):
        """Test gRPC adapter metadata."""
        info = mock_grpc_adapter.get_adapter_info()

        assert info["protocol_name"] == "grpc"
        assert info["protocol_version"] == "1.0"
        assert info["supports_streaming"] is True


# ============================================================================
# Cross-Adapter Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
@pytest.mark.requires_adapters
class TestCrossAdapterIntegration:
    """Test cross-adapter scenarios."""

    @pytest.mark.asyncio
    async def test_all_adapters_discover(self, populated_registry):
        """Test that all adapters can discover resources."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        mcp_resources = await mcp_adapter.discover_resources({"name": "mcp-test"})
        http_resources = await http_adapter.discover_resources({"base_url": "https://test.com"})
        grpc_resources = await grpc_adapter.discover_resources({"endpoint": "localhost:50051"})

        assert len(mcp_resources) > 0
        assert len(http_resources) > 0
        assert len(grpc_resources) > 0

    @pytest.mark.asyncio
    async def test_all_adapters_health_check(
        self,
        populated_registry,
        sample_mcp_resource,
        sample_http_resource,
        sample_grpc_resource
    ):
        """Test health checks across all adapters."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        mcp_healthy = await mcp_adapter.health_check(sample_mcp_resource)
        http_healthy = await http_adapter.health_check(sample_http_resource)
        grpc_healthy = await grpc_adapter.health_check(sample_grpc_resource)

        assert mcp_healthy is True
        assert http_healthy is True
        assert grpc_healthy is True

    @pytest.mark.asyncio
    async def test_adapter_capability_discovery(
        self,
        populated_registry,
        sample_mcp_resource,
        sample_http_resource,
        sample_grpc_resource
    ):
        """Test capability discovery across all adapters."""
        mcp_adapter = populated_registry.get("mcp")
        http_adapter = populated_registry.get("http")
        grpc_adapter = populated_registry.get("grpc")

        mcp_caps = await mcp_adapter.get_capabilities(sample_mcp_resource)
        http_caps = await http_adapter.get_capabilities(sample_http_resource)
        grpc_caps = await grpc_adapter.get_capabilities(sample_grpc_resource)

        # All adapters should discover at least some capabilities
        assert len(mcp_caps) >= 2
        assert len(http_caps) >= 2
        assert len(grpc_caps) >= 2

        # Verify all capabilities have required fields
        all_caps = mcp_caps + http_caps + grpc_caps
        for cap in all_caps:
            assert cap.id is not None
            assert cap.resource_id is not None
            assert cap.name is not None

    def test_adapter_feature_matrix(self, populated_registry):
        """Test adapter feature support matrix."""
        adapters = [
            populated_registry.get("mcp"),
            populated_registry.get("http"),
            populated_registry.get("grpc"),
        ]

        feature_matrix = {
            adapter.protocol_name: {
                "streaming": adapter.supports_streaming(),
                "batch": adapter.supports_batch(),
            }
            for adapter in adapters
        }

        # MCP and HTTP typically don't support streaming by default
        # gRPC supports streaming
        assert feature_matrix["grpc"]["streaming"] is True


# ============================================================================
# Adapter Lifecycle Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
class TestAdapterLifecycle:
    """Test adapter lifecycle hooks."""

    @pytest.mark.asyncio
    async def test_on_resource_registered(self, mock_mcp_adapter, sample_mcp_resource):
        """Test resource registration lifecycle hook."""
        # Mock adapters have default no-op implementation
        # This should not raise an error
        await mock_mcp_adapter.on_resource_registered(sample_mcp_resource)

    @pytest.mark.asyncio
    async def test_on_resource_unregistered(self, mock_mcp_adapter, sample_mcp_resource):
        """Test resource unregistration lifecycle hook."""
        # Mock adapters have default no-op implementation
        # This should not raise an error
        await mock_mcp_adapter.on_resource_unregistered(sample_mcp_resource)

    @pytest.mark.asyncio
    async def test_refresh_capabilities(self, mock_mcp_adapter, sample_mcp_resource):
        """Test capability refresh."""
        capabilities = await mock_mcp_adapter.refresh_capabilities(sample_mcp_resource)

        # Should return same result as get_capabilities
        expected_caps = await mock_mcp_adapter.get_capabilities(sample_mcp_resource)
        assert len(capabilities) == len(expected_caps)


# ============================================================================
# Adapter Error Handling Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
class TestAdapterErrorHandling:
    """Test adapter error handling."""

    @pytest.mark.asyncio
    async def test_unsupported_streaming(self, mock_mcp_adapter, sample_invocation_request):
        """Test that adapters without streaming support raise error."""
        # MCP adapter doesn't override invoke_streaming, so it raises UnsupportedOperationError
        # The base implementation raises directly in the async method
        with pytest.raises(UnsupportedOperationError, match="Streaming is not supported"):
            # The error is raised when trying to use the iterator
            await mock_mcp_adapter.invoke_streaming(sample_invocation_request).__anext__()

    @pytest.mark.asyncio
    async def test_batch_invocation_fallback(self, mock_mcp_adapter):
        """Test batch invocation falls back to sequential calls."""
        requests = [
            InvocationRequest(
                capability_id=f"cap-{i}",
                principal_id="test-principal",
                arguments={"index": i},
                context={}
            )
            for i in range(3)
        ]

        results = await mock_mcp_adapter.invoke_batch(requests)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_adapter_repr(self, mock_mcp_adapter):
        """Test adapter string representation."""
        repr_str = repr(mock_mcp_adapter)

        assert "MockMCPAdapter" in repr_str
        assert "mcp" in repr_str
        assert "2024-11-05" in repr_str


# ============================================================================
# Integration with SARK Core Tests
# ============================================================================


@pytest.mark.v2
@pytest.mark.adapter
@pytest.mark.integration
class TestAdapterSARKCoreIntegration:
    """Test adapter integration with SARK core components."""

    @pytest.mark.asyncio
    async def test_adapter_discovery_to_registration(
        self,
        populated_registry,
        mock_mcp_adapter
    ):
        """Test complete flow from discovery to registration."""
        # 1. Discover resources
        config = {
            "name": "test-server",
            "command": "test-command",
        }
        resources = await mock_mcp_adapter.discover_resources(config)
        assert len(resources) > 0

        resource = resources[0]

        # 2. Get capabilities
        capabilities = await mock_mcp_adapter.get_capabilities(resource)
        assert len(capabilities) > 0

        # 3. Validate and invoke a capability
        capability = capabilities[0]
        request = InvocationRequest(
            capability_id=capability.id,
            principal_id="test-user",
            arguments={},
            context={},
        )

        is_valid = await mock_mcp_adapter.validate_request(request)
        assert is_valid is True

        result = await mock_mcp_adapter.invoke(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_multi_adapter_resource_management(self, populated_registry):
        """Test managing resources from multiple protocols."""
        all_resources = []

        for protocol in ["mcp", "http", "grpc"]:
            adapter = populated_registry.get(protocol)
            config = {"name": f"{protocol}-service"}
            if protocol == "http":
                config["base_url"] = "https://test.com"
            elif protocol == "grpc":
                config["endpoint"] = "localhost:50051"

            resources = await adapter.discover_resources(config)
            all_resources.extend(resources)

        # Should have discovered resources from all 3 protocols
        assert len(all_resources) == 3
        protocols = {r.protocol for r in all_resources}
        assert protocols == {"mcp", "http", "grpc"}
