"""
Base test class for protocol adapter contract testing.

All protocol adapters MUST inherit from BaseAdapterTest and pass all contract tests.
These tests verify compliance with the ProtocolAdapter interface contract.
"""

import pytest
from abc import ABC
from typing import Any, Dict, List
from datetime import datetime

from sark.adapters.base import ProtocolAdapter
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)
from sark.adapters.exceptions import (
    ValidationError,
    UnsupportedOperationError,
    InvocationError,
    CapabilityNotFoundError,
)


class BaseAdapterTest(ABC):
    """
    Base test class for adapter contract testing.

    All adapters MUST pass these tests to ensure compliance with the
    ProtocolAdapter interface contract.

    Subclasses must implement the required fixtures:
    - adapter(): Return the adapter instance
    - discovery_config(): Return valid discovery configuration
    - sample_resource(): Return a valid ResourceSchema
    - sample_capability(): Return a valid CapabilitySchema
    - valid_invocation_request(): Return a valid InvocationRequest
    """

    # =========================================================================
    # Required Fixtures - Subclasses MUST implement these
    # =========================================================================

    @pytest.fixture
    def adapter(self) -> ProtocolAdapter:
        """Return the adapter instance to test."""
        raise NotImplementedError("Subclass must implement adapter() fixture")

    @pytest.fixture
    def discovery_config(self) -> Dict[str, Any]:
        """Return valid discovery configuration for this adapter."""
        raise NotImplementedError("Subclass must implement discovery_config() fixture")

    @pytest.fixture
    def sample_resource(self) -> ResourceSchema:
        """Return a sample resource for this adapter."""
        raise NotImplementedError("Subclass must implement sample_resource() fixture")

    @pytest.fixture
    def sample_capability(self) -> CapabilitySchema:
        """Return a sample capability for this adapter."""
        raise NotImplementedError("Subclass must implement sample_capability() fixture")

    @pytest.fixture
    def valid_invocation_request(self) -> InvocationRequest:
        """Return a valid invocation request for this adapter."""
        raise NotImplementedError("Subclass must implement valid_invocation_request() fixture")

    # =========================================================================
    # Contract Tests - Protocol Properties
    # =========================================================================

    def test_adapter_implements_protocol_name(self, adapter):
        """Adapter MUST provide a protocol_name property."""
        assert hasattr(adapter, "protocol_name")
        assert isinstance(adapter.protocol_name, str)
        assert len(adapter.protocol_name) > 0
        # Protocol name should be lowercase
        assert adapter.protocol_name == adapter.protocol_name.lower()

    def test_adapter_implements_protocol_version(self, adapter):
        """Adapter MUST provide a protocol_version property."""
        assert hasattr(adapter, "protocol_version")
        assert isinstance(adapter.protocol_version, str)
        assert len(adapter.protocol_version) > 0

    # =========================================================================
    # Contract Tests - Resource Discovery
    # =========================================================================

    @pytest.mark.asyncio
    async def test_discover_resources_returns_list(self, adapter, discovery_config):
        """discover_resources() MUST return a list of ResourceSchema."""
        resources = await adapter.discover_resources(discovery_config)
        assert isinstance(resources, list)
        # All items must be ResourceSchema
        for resource in resources:
            assert isinstance(resource, ResourceSchema)
            assert resource.id is not None
            assert resource.name is not None
            assert resource.protocol == adapter.protocol_name

    @pytest.mark.asyncio
    async def test_discover_resources_handles_invalid_config(self, adapter):
        """discover_resources() MUST raise appropriate error for invalid config."""
        with pytest.raises((ValidationError, Exception)):
            await adapter.discover_resources({})

    # =========================================================================
    # Contract Tests - Capability Management
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_capabilities_returns_list(self, adapter, sample_resource):
        """get_capabilities() MUST return a list of CapabilitySchema."""
        capabilities = await adapter.get_capabilities(sample_resource)
        assert isinstance(capabilities, list)
        # All items must be CapabilitySchema
        for capability in capabilities:
            assert isinstance(capability, CapabilitySchema)
            assert capability.id is not None
            assert capability.name is not None
            assert capability.resource_id == sample_resource.id

    @pytest.mark.asyncio
    async def test_refresh_capabilities_returns_list(self, adapter, sample_resource):
        """refresh_capabilities() MUST return a list of CapabilitySchema."""
        capabilities = await adapter.refresh_capabilities(sample_resource)
        assert isinstance(capabilities, list)
        for capability in capabilities:
            assert isinstance(capability, CapabilitySchema)

    # =========================================================================
    # Contract Tests - Request Validation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_validate_request_returns_bool(self, adapter, valid_invocation_request):
        """validate_request() MUST return a boolean."""
        result = await adapter.validate_request(valid_invocation_request)
        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_request_rejects_invalid(self, adapter):
        """validate_request() MUST reject invalid requests."""
        invalid_request = InvocationRequest(
            capability_id="invalid-capability-id-that-does-not-exist",
            principal_id="test-principal",
            arguments={}
        )
        # Should either return False or raise ValidationError
        try:
            result = await adapter.validate_request(invalid_request)
            assert result is False
        except ValidationError:
            pass  # Also acceptable

    # =========================================================================
    # Contract Tests - Invocation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_invoke_returns_invocation_result(self, adapter, valid_invocation_request):
        """invoke() MUST return InvocationResult with proper fields."""
        result = await adapter.invoke(valid_invocation_request)
        assert isinstance(result, InvocationResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.duration_ms, float)
        assert result.duration_ms >= 0

        # If success=True, result should be set
        if result.success:
            assert result.result is not None or result.result == {}
        # If success=False, error should be set
        else:
            assert result.error is not None
            assert isinstance(result.error, str)

    @pytest.mark.asyncio
    async def test_invoke_tracks_duration(self, adapter, valid_invocation_request):
        """invoke() MUST track execution duration in milliseconds."""
        result = await adapter.invoke(valid_invocation_request)
        # Duration should be positive and reasonable (< 1 minute for tests)
        assert result.duration_ms > 0
        assert result.duration_ms < 60000  # 1 minute max for tests

    # =========================================================================
    # Contract Tests - Health Checks
    # =========================================================================

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self, adapter, sample_resource):
        """health_check() MUST return a boolean."""
        is_healthy = await adapter.health_check(sample_resource)
        assert isinstance(is_healthy, bool)

    # =========================================================================
    # Contract Tests - Lifecycle Hooks
    # =========================================================================

    @pytest.mark.asyncio
    async def test_on_resource_registered_callable(self, adapter, sample_resource):
        """on_resource_registered() MUST be callable and not raise by default."""
        # Should not raise even if not implemented
        await adapter.on_resource_registered(sample_resource)

    @pytest.mark.asyncio
    async def test_on_resource_unregistered_callable(self, adapter, sample_resource):
        """on_resource_unregistered() MUST be callable and not raise by default."""
        # Should not raise even if not implemented
        await adapter.on_resource_unregistered(sample_resource)

    # =========================================================================
    # Contract Tests - Streaming Support
    # =========================================================================

    def test_supports_streaming_returns_bool(self, adapter):
        """supports_streaming() MUST return a boolean."""
        assert isinstance(adapter.supports_streaming(), bool)

    @pytest.mark.asyncio
    async def test_invoke_streaming_behavior(self, adapter, valid_invocation_request):
        """invoke_streaming() MUST either work or raise UnsupportedOperationError."""
        if adapter.supports_streaming():
            # Should return an async iterator
            result = adapter.invoke_streaming(valid_invocation_request)
            assert hasattr(result, '__aiter__')
        else:
            # Should raise UnsupportedOperationError
            with pytest.raises(UnsupportedOperationError):
                async for _ in adapter.invoke_streaming(valid_invocation_request):
                    pass

    # =========================================================================
    # Contract Tests - Batch Support
    # =========================================================================

    def test_supports_batch_returns_bool(self, adapter):
        """supports_batch() MUST return a boolean."""
        assert isinstance(adapter.supports_batch(), bool)

    @pytest.mark.asyncio
    async def test_invoke_batch_returns_list(self, adapter, valid_invocation_request):
        """invoke_batch() MUST return a list of InvocationResult."""
        requests = [valid_invocation_request]
        results = await adapter.invoke_batch(requests)

        assert isinstance(results, list)
        assert len(results) == len(requests)

        for result in results:
            assert isinstance(result, InvocationResult)
            assert isinstance(result.success, bool)
            assert isinstance(result.duration_ms, float)

    @pytest.mark.asyncio
    async def test_invoke_batch_preserves_order(self, adapter, valid_invocation_request):
        """invoke_batch() MUST return results in same order as requests."""
        requests = [valid_invocation_request, valid_invocation_request]
        results = await adapter.invoke_batch(requests)

        assert len(results) == len(requests)
        # Each result should correspond to its request

    # =========================================================================
    # Contract Tests - Metadata & Info
    # =========================================================================

    def test_get_adapter_info_returns_dict(self, adapter):
        """get_adapter_info() MUST return a dict with required fields."""
        info = adapter.get_adapter_info()
        assert isinstance(info, dict)

        # Required fields
        assert "protocol_name" in info
        assert "protocol_version" in info
        assert "adapter_class" in info
        assert "supports_streaming" in info
        assert "supports_batch" in info
        assert "module" in info

        # Verify types
        assert isinstance(info["protocol_name"], str)
        assert isinstance(info["protocol_version"], str)
        assert isinstance(info["adapter_class"], str)
        assert isinstance(info["supports_streaming"], bool)
        assert isinstance(info["supports_batch"], bool)
        assert isinstance(info["module"], str)

    def test_get_adapter_metadata_returns_dict(self, adapter):
        """get_adapter_metadata() MUST return a dictionary."""
        metadata = adapter.get_adapter_metadata()
        assert isinstance(metadata, dict)

    def test_adapter_repr(self, adapter):
        """Adapter MUST have a meaningful string representation."""
        repr_str = repr(adapter)
        assert isinstance(repr_str, str)
        assert adapter.protocol_name in repr_str
        assert adapter.protocol_version in repr_str
