"""
Test suite for MockAdapter - validates that the adapter contract tests work.

This also serves as a reference implementation for adapter developers.
"""

from datetime import datetime
from typing import Any

import pytest

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import (
    DiscoveryError,
)
from sark.models.base import (
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
    ResourceSchema,
)
from tests.adapters.base_adapter_test import BaseAdapterTest

# ============================================================================
# Mock Adapter Implementation
# ============================================================================


class MockAdapter(ProtocolAdapter):
    """
    Mock adapter for testing.

    This is a minimal reference implementation that passes all contract tests.
    """

    @property
    def protocol_name(self) -> str:
        return "mock"

    @property
    def protocol_version(self) -> str:
        return "1.0.0"

    async def discover_resources(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """Discover mock resources."""
        if not discovery_config:
            raise DiscoveryError(
                "Discovery config cannot be empty", adapter_name=self.protocol_name
            )

        endpoint = discovery_config.get("endpoint", "mock://localhost")

        resource = ResourceSchema(
            id=f"mock-{discovery_config.get('name', 'test')}",
            name=discovery_config.get("name", "Mock Resource"),
            protocol="mock",
            endpoint=endpoint,
            sensitivity_level="medium",
            metadata=discovery_config,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        return [resource]

    async def get_capabilities(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """Get capabilities for a resource."""
        return [
            CapabilitySchema(
                id=f"{resource.id}-capability-1",
                resource_id=resource.id,
                name="test_capability",
                description="A test capability",
                input_schema={"type": "object", "properties": {"arg": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
                sensitivity_level="medium",
                metadata={},
            )
        ]

    async def validate_request(self, request: InvocationRequest) -> bool:
        """Validate an invocation request."""
        # Simple validation: check if capability_id starts with "mock-"
        return request.capability_id.startswith("mock-")

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        """Execute a capability invocation."""
        import time

        start = time.time()

        try:
            # Simulate some work
            result_data = {
                "capability_id": request.capability_id,
                "principal_id": request.principal_id,
                "arguments": request.arguments,
                "status": "success",
            }

            return InvocationResult(
                success=True,
                result=result_data,
                metadata={"mock": True},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return InvocationResult(
                success=False,
                error=str(e),
                metadata={"mock": True},
                duration_ms=(time.time() - start) * 1000,
            )

    async def health_check(self, resource: ResourceSchema) -> bool:
        """Check if resource is healthy."""
        # Mock resources are always healthy
        return True


# ============================================================================
# Contract Tests for MockAdapter
# ============================================================================


class TestMockAdapter(BaseAdapterTest):
    """Test suite for MockAdapter - validates the contract tests work."""

    @pytest.fixture
    def adapter(self) -> ProtocolAdapter:
        """Return a MockAdapter instance."""
        return MockAdapter()

    @pytest.fixture
    def discovery_config(self) -> dict[str, Any]:
        """Return valid discovery configuration."""
        return {
            "name": "test-resource",
            "endpoint": "mock://test",
            "features": ["capability1", "capability2"],
        }

    @pytest.fixture
    def sample_resource(self) -> ResourceSchema:
        """Return a sample resource."""
        return ResourceSchema(
            id="mock-test-resource",
            name="Test Mock Resource",
            protocol="mock",
            endpoint="mock://test",
            sensitivity_level="medium",
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.fixture
    def sample_capability(self) -> CapabilitySchema:
        """Return a sample capability."""
        return CapabilitySchema(
            id="mock-test-resource-capability-1",
            resource_id="mock-test-resource",
            name="test_capability",
            description="A test capability",
            input_schema={},
            output_schema={},
            sensitivity_level="medium",
            metadata={},
        )

    @pytest.fixture
    def valid_invocation_request(self) -> InvocationRequest:
        """Return a valid invocation request."""
        return InvocationRequest(
            capability_id="mock-test-resource-capability-1",
            principal_id="test-user",
            arguments={"arg": "value"},
        )

    # All contract tests are inherited from BaseAdapterTest
    # This ensures MockAdapter complies with the ProtocolAdapter contract


# ============================================================================
# Additional Adapter-Specific Tests
# ============================================================================


class TestMockAdapterSpecific:
    """Additional tests specific to MockAdapter (not part of contract)."""

    @pytest.mark.asyncio
    async def test_mock_adapter_discovery_requires_config(self):
        """MockAdapter should raise error for empty config."""
        adapter = MockAdapter()

        with pytest.raises(DiscoveryError):
            await adapter.discover_resources({})

    @pytest.mark.asyncio
    async def test_mock_adapter_validation_checks_prefix(self):
        """MockAdapter validation should check capability_id prefix."""
        adapter = MockAdapter()

        valid_request = InvocationRequest(
            capability_id="mock-something", principal_id="user", arguments={}
        )
        assert await adapter.validate_request(valid_request) is True

        invalid_request = InvocationRequest(
            capability_id="other-something", principal_id="user", arguments={}
        )
        assert await adapter.validate_request(invalid_request) is False

    @pytest.mark.asyncio
    async def test_mock_adapter_invocation_returns_arguments(self):
        """MockAdapter should echo back the arguments in result."""
        adapter = MockAdapter()

        request = InvocationRequest(
            capability_id="mock-test", principal_id="user", arguments={"key": "value"}
        )

        result = await adapter.invoke(request)

        assert result.success is True
        assert result.result["arguments"] == {"key": "value"}
        assert result.result["principal_id"] == "user"
