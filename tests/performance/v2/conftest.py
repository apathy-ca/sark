"""
Pytest fixtures for v2.0 performance testing.

Provides reusable fixtures for adapter performance benchmarking,
load testing, and performance baseline measurements.
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import Mock, AsyncMock

import pytest
from sark.adapters.base import ProtocolAdapter
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)


@pytest.fixture
def performance_metrics():
    """Container for collecting performance metrics during tests."""
    return {
        "latencies": [],
        "throughputs": [],
        "errors": [],
        "cpu_usage": [],
        "memory_usage": [],
    }


@pytest.fixture
def mock_adapter():
    """Mock adapter for baseline performance testing."""

    class MockAdapter(ProtocolAdapter):
        @property
        def protocol_name(self) -> str:
            return "mock"

        @property
        def protocol_version(self) -> str:
            return "1.0"

        async def discover_resources(self, discovery_config: Dict[str, Any]) -> List[ResourceSchema]:
            await asyncio.sleep(0.001)  # Simulate network delay
            return [
                ResourceSchema(
                    id="mock-resource-1",
                    name="Mock Resource 1",
                    protocol="mock",
                    endpoint="mock://test",
                    capabilities=[],
                    metadata={},
                )
            ]

        async def get_capabilities(self, resource: ResourceSchema) -> List[CapabilitySchema]:
            await asyncio.sleep(0.001)
            return [
                CapabilitySchema(
                    id="mock-cap-1",
                    resource_id=resource.id,
                    name="mock_action",
                    description="Mock capability",
                    input_schema={},
                    output_schema={},
                )
            ]

        async def validate_request(self, request: InvocationRequest) -> bool:
            await asyncio.sleep(0.0001)  # Very fast validation
            return True

        async def invoke(self, request: InvocationRequest) -> InvocationResult:
            start = time.perf_counter()
            await asyncio.sleep(0.01)  # Simulate 10ms operation
            duration_ms = (time.perf_counter() - start) * 1000

            return InvocationResult(
                success=True,
                result={"status": "ok", "data": "mock result"},
                metadata={"adapter": "mock"},
                duration_ms=duration_ms,
            )

        async def health_check(self, resource: ResourceSchema) -> bool:
            await asyncio.sleep(0.001)
            return True

    return MockAdapter()


@pytest.fixture
def sample_resource():
    """Sample resource for testing."""
    return ResourceSchema(
        id="test-resource-1",
        name="Test Resource",
        protocol="test",
        endpoint="test://endpoint",
        capabilities=[],
        metadata={"test": True},
    )


@pytest.fixture
def sample_capability():
    """Sample capability for testing."""
    return CapabilitySchema(
        id="test-cap-1",
        resource_id="test-resource-1",
        name="test_action",
        description="Test capability",
        input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
        output_schema={"type": "object"},
    )


@pytest.fixture
def sample_invocation_request(sample_capability):
    """Sample invocation request for testing."""
    return InvocationRequest(
        capability_id=sample_capability.id,
        principal_id="test-principal",
        arguments={"param": "value"},
        context={"source": "test"},
    )


@pytest.fixture
async def load_test_requests(sample_capability):
    """Generate multiple invocation requests for load testing."""
    return [
        InvocationRequest(
            capability_id=sample_capability.id,
            principal_id=f"principal-{i}",
            arguments={"param": f"value-{i}"},
            context={"request_id": i},
        )
        for i in range(100)
    ]


@pytest.fixture
def benchmark_config():
    """Configuration for benchmark tests."""
    return {
        "warmup_iterations": 10,
        "benchmark_iterations": 100,
        "concurrency_levels": [1, 10, 50, 100],
        "acceptable_latency_ms": 100,  # SLA: <100ms adapter overhead
        "acceptable_error_rate": 0.01,  # 1% max error rate
    }


@pytest.fixture
def performance_thresholds():
    """Performance thresholds based on SARK v2.0 requirements."""
    return {
        "adapter_overhead_ms": 100,  # Max 100ms overhead per spec
        "discovery_time_ms": 5000,   # Max 5s for discovery
        "health_check_ms": 100,      # Max 100ms for health check
        "throughput_rps": 100,       # Min 100 requests/sec per adapter
        "p95_latency_ms": 150,       # P95 latency under 150ms
        "p99_latency_ms": 250,       # P99 latency under 250ms
        "concurrent_requests": 1000,  # Support 1000 concurrent requests
    }


@pytest.fixture
async def async_timer():
    """Context manager for timing async operations."""

    class AsyncTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed_ms = None

        async def __aenter__(self):
            self.start_time = time.perf_counter()
            return self

        async def __aexit__(self, *args):
            self.end_time = time.perf_counter()
            self.elapsed_ms = (self.end_time - self.start_time) * 1000

    return AsyncTimer


@pytest.fixture
def percentile_calculator():
    """Helper function to calculate percentiles."""

    def calculate(values: List[float], percentile: int) -> float:
        """Calculate percentile value from list."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

    return calculate
