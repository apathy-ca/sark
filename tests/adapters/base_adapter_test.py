"""
Base test class for protocol adapter contract testing.

All protocol adapters MUST inherit from BaseAdapterTest and pass all contract tests.
"""

import pytest
from abc import ABC
from typing import Any, Dict
from datetime import datetime

from sark.adapters.base import ProtocolAdapter
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)
from sark.adapters.exceptions import ValidationError, UnsupportedOperationError


class BaseAdapterTest(ABC):
    """Base test class for adapter contract testing."""

    @pytest.fixture
    def adapter(self) -> ProtocolAdapter:
        raise NotImplementedError("Subclass must implement adapter() fixture")

    @pytest.fixture
    def discovery_config(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclass must implement discovery_config() fixture")

    @pytest.fixture
    def sample_resource(self) -> ResourceSchema:
        raise NotImplementedError("Subclass must implement sample_resource() fixture")

    @pytest.fixture
    def sample_capability(self) -> CapabilitySchema:
        raise NotImplementedError("Subclass must implement sample_capability() fixture")

    @pytest.fixture
    def valid_invocation_request(self) -> InvocationRequest:
        raise NotImplementedError("Subclass must implement valid_invocation_request() fixture")

    def test_adapter_implements_protocol_name(self, adapter):
        assert hasattr(adapter, "protocol_name")
        assert isinstance(adapter.protocol_name, str)
        assert len(adapter.protocol_name) > 0

    def test_adapter_implements_protocol_version(self, adapter):
        assert hasattr(adapter, "protocol_version")
        assert isinstance(adapter.protocol_version, str)

    @pytest.mark.asyncio
    async def test_discover_resources_returns_list(self, adapter, discovery_config):
        resources = await adapter.discover_resources(discovery_config)
        assert isinstance(resources, list)

    @pytest.mark.asyncio
    async def test_get_capabilities_returns_list(self, adapter, sample_resource):
        capabilities = await adapter.get_capabilities(sample_resource)
        assert isinstance(capabilities, list)

    @pytest.mark.asyncio
    async def test_validate_request_returns_bool(self, adapter, valid_invocation_request):
        result = await adapter.validate_request(valid_invocation_request)
        assert result is True

    @pytest.mark.asyncio
    async def test_invoke_returns_invocation_result(self, adapter, valid_invocation_request):
        result = await adapter.invoke(valid_invocation_request)
        assert isinstance(result, InvocationResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.duration_ms, float)

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self, adapter, sample_resource):
        is_healthy = await adapter.health_check(sample_resource)
        assert isinstance(is_healthy, bool)

    def test_supports_streaming_returns_bool(self, adapter):
        assert isinstance(adapter.supports_streaming(), bool)

    def test_supports_batch_returns_bool(self, adapter):
        assert isinstance(adapter.supports_batch(), bool)

    def test_get_adapter_info_returns_dict(self, adapter):
        info = adapter.get_adapter_info()
        assert isinstance(info, dict)
        assert "protocol_name" in info
        assert "protocol_version" in info
