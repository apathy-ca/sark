"""
Base test class for protocol adapters.

All adapter implementations should inherit from BaseAdapterTest
to ensure they implement the required interface correctly.
"""

import pytest
from abc import ABC, abstractmethod
from typing import Dict, Any

from sark.adapters.base import ProtocolAdapter
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)


class BaseAdapterTest(ABC):
    """
    Base test class for all protocol adapters.
    
    Adapter implementations should create a test class that inherits from this
    and implements the abstract methods to provide test fixtures.
    
    Example:
        class TestMCPAdapter(BaseAdapterTest):
            @pytest.fixture
            def adapter(self):
                return MCPAdapter()
            
            @pytest.fixture
            def discovery_config(self):
                return {
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"]
                }
    """
    
    @pytest.fixture
    @abstractmethod
    def adapter(self) -> ProtocolAdapter:
        """
        Provide the adapter instance to test.
        
        Returns:
            ProtocolAdapter instance
        """
        pass
    
    @pytest.fixture
    @abstractmethod
    def discovery_config(self) -> Dict[str, Any]:
        """
        Provide protocol-specific discovery configuration.
        
        Returns:
            Discovery configuration dict
        """
        pass
    
    @pytest.fixture
    @abstractmethod
    def sample_resource(self) -> ResourceSchema:
        """
        Provide a sample resource for testing.
        
        Returns:
            ResourceSchema instance
        """
        pass
    
    @pytest.fixture
    @abstractmethod
    def sample_capability(self) -> CapabilitySchema:
        """
        Provide a sample capability for testing.
        
        Returns:
            CapabilitySchema instance
        """
        pass
    
    @pytest.fixture
    @abstractmethod
    def valid_invocation_request(self) -> InvocationRequest:
        """
        Provide a valid invocation request for testing.
        
        Returns:
            InvocationRequest instance
        """
        pass
    
    # Required interface tests
    
    def test_protocol_name(self, adapter: ProtocolAdapter):
        """Test that adapter has a protocol name."""
        assert isinstance(adapter.protocol_name, str)
        assert len(adapter.protocol_name) > 0
        assert adapter.protocol_name.islower()  # Should be lowercase
    
    def test_protocol_version(self, adapter: ProtocolAdapter):
        """Test that adapter has a protocol version."""
        assert isinstance(adapter.protocol_version, str)
        assert len(adapter.protocol_version) > 0
    
    @pytest.mark.asyncio
    async def test_discover_resources(
        self,
        adapter: ProtocolAdapter,
        discovery_config: Dict[str, Any]
    ):
        """Test resource discovery."""
        resources = await adapter.discover_resources(discovery_config)
        
        assert isinstance(resources, list)
        # May be empty if no resources found, but should be a list
        
        if resources:
            for resource in resources:
                assert isinstance(resource, ResourceSchema)
                assert resource.protocol == adapter.protocol_name
                assert len(resource.id) > 0
                assert len(resource.name) > 0
    
    @pytest.mark.asyncio
    async def test_get_capabilities(
        self,
        adapter: ProtocolAdapter,
        sample_resource: ResourceSchema
    ):
        """Test capability listing."""
        capabilities = await adapter.get_capabilities(sample_resource)
        
        assert isinstance(capabilities, list)
        
        if capabilities:
            for capability in capabilities:
                assert isinstance(capability, CapabilitySchema)
                assert capability.resource_id == sample_resource.id
                assert len(capability.id) > 0
                assert len(capability.name) > 0
    
    @pytest.mark.asyncio
    async def test_validate_request(
        self,
        adapter: ProtocolAdapter,
        valid_invocation_request: InvocationRequest
    ):
        """Test request validation."""
        is_valid = await adapter.validate_request(valid_invocation_request)
        assert isinstance(is_valid, bool)
    
    @pytest.mark.asyncio
    async def test_invoke(
        self,
        adapter: ProtocolAdapter,
        valid_invocation_request: InvocationRequest
    ):
        """Test capability invocation."""
        result = await adapter.invoke(valid_invocation_request)
        
        assert isinstance(result, InvocationResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.duration_ms, (int, float))
        assert result.duration_ms >= 0
        
        if result.success:
            # Successful invocation should have a result
            assert result.result is not None
            assert result.error is None
        else:
            # Failed invocation should have an error
            assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_health_check(
        self,
        adapter: ProtocolAdapter,
        sample_resource: ResourceSchema
    ):
        """Test resource health check."""
        is_healthy = await adapter.health_check(sample_resource)
        assert isinstance(is_healthy, bool)
    
    @pytest.mark.asyncio
    async def test_lifecycle_hooks(
        self,
        adapter: ProtocolAdapter,
        sample_resource: ResourceSchema
    ):
        """Test lifecycle hooks don't raise errors."""
        # These are optional, so they should not raise errors
        await adapter.on_resource_registered(sample_resource)
        await adapter.on_resource_unregistered(sample_resource)
    
    # Performance tests
    
    @pytest.mark.asyncio
    async def test_invoke_performance(
        self,
        adapter: ProtocolAdapter,
        valid_invocation_request: InvocationRequest
    ):
        """Test that invocation completes in reasonable time."""
        result = await adapter.invoke(valid_invocation_request)
        
        # Adapter overhead should be minimal (<1ms target)
        # Total time depends on the actual operation, but adapter
        # overhead should be tracked
        assert result.duration_ms < 30000  # 30 seconds max (generous)
    
    # Error handling tests
    
    @pytest.mark.asyncio
    async def test_invalid_discovery_config(self, adapter: ProtocolAdapter):
        """Test that invalid discovery config is handled gracefully."""
        with pytest.raises(Exception):  # Should raise some exception
            await adapter.discover_resources({})
    
    @pytest.mark.asyncio
    async def test_invalid_invocation_request(self, adapter: ProtocolAdapter):
        """Test that invalid invocation request is handled."""
        invalid_request = InvocationRequest(
            capability_id="nonexistent",
            principal_id="test",
            arguments={}
        )
        
        # Should either return error result or raise exception
        try:
            result = await adapter.invoke(invalid_request)
            assert not result.success
            assert result.error is not None
        except Exception:
            pass  # Also acceptable to raise exception


class MockAdapter(ProtocolAdapter):
    """
    Mock adapter for testing the base test class itself.
    
    This is a minimal implementation that can be used to test
    the BaseAdapterTest framework.
    """
    
    @property
    def protocol_name(self) -> str:
        return "mock"
    
    @property
    def protocol_version(self) -> str:
        return "1.0.0"
    
    async def discover_resources(self, discovery_config: Dict[str, Any]):
        return [
            ResourceSchema(
                id="mock-resource-1",
                name="Mock Resource",
                protocol="mock",
                endpoint="mock://localhost",
                sensitivity_level="low",
                metadata={},
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z"
            )
        ]
    
    async def get_capabilities(self, resource: ResourceSchema):
        return [
            CapabilitySchema(
                id="mock-capability-1",
                resource_id=resource.id,
                name="mock_action",
                description="A mock capability",
                sensitivity_level="low",
                metadata={}
            )
        ]
    
    async def validate_request(self, request: InvocationRequest) -> bool:
        return request.capability_id.startswith("mock-")
    
    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        import time
        start = time.time()
        
        if not request.capability_id.startswith("mock-"):
            return InvocationResult(
                success=False,
                error="Invalid capability ID",
                duration_ms=(time.time() - start) * 1000
            )
        
        return InvocationResult(
            success=True,
            result={"message": "Mock invocation successful"},
            duration_ms=(time.time() - start) * 1000
        )
    
    async def health_check(self, resource: ResourceSchema) -> bool:
        return resource.protocol == "mock"


__all__ = ["BaseAdapterTest", "MockAdapter"]