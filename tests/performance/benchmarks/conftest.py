"""
Shared fixtures for performance benchmarks.

Provides fixtures for OPA clients (HTTP and Rust) and cache implementations
(Redis and Rust) for comparative performance testing.
"""

import asyncio
from collections.abc import AsyncGenerator
import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import (
    AuthorizationDecision,
    AuthorizationInput,
    OPAClient,
)

# ==============================================================================
# Test Data Fixtures
# ==============================================================================


@pytest.fixture
def simple_policy_input() -> AuthorizationInput:
    """Simple RBAC policy input for basic benchmarks."""
    return AuthorizationInput(
        user_id="user-alice",
        action="read",
        resource="document-123",
        context={"role": "viewer"},
    )


@pytest.fixture
def complex_policy_input() -> AuthorizationInput:
    """Complex multi-tenant policy input for advanced benchmarks."""
    return AuthorizationInput(
        user_id="user-alice",
        action="write",
        resource="tenant-1:project-42:document-123",
        context={
            "role": "admin",
            "tenant_id": "tenant-1",
            "project_id": "project-42",
            "ip_address": "192.168.1.100",
            "time_of_day": "business_hours",
            "sensitivity": "confidential",
        },
    )


@pytest.fixture
def sample_decision() -> dict:
    """Sample authorization decision for cache testing."""
    return {
        "allow": True,
        "reason": "User has required role",
        "metadata": {
            "policy_version": "1.0",
            "evaluated_rules": 5,
        },
    }


# ==============================================================================
# Mock Redis Client
# ==============================================================================


@pytest.fixture
async def mock_redis():
    """Mock Redis client for cache testing."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    redis.scan_iter = AsyncMock(return_value=iter([]))
    return redis


# ==============================================================================
# HTTP OPA Client (Python Implementation)
# ==============================================================================


@pytest.fixture
async def http_opa_client() -> AsyncGenerator[OPAClient, None]:
    """
    HTTP-based OPA client (Python implementation).

    This is the baseline Python implementation using httpx to communicate
    with an external OPA server.
    """
    # Mock httpx client
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock successful authorization response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "allow": True,
                "reason": "User authorized",
            }
        }
        mock_client.post.return_value = mock_response

        client = OPAClient(
            opa_url="http://localhost:8181",
            timeout=10.0,
        )

        yield client

        await client.close()


# ==============================================================================
# Rust OPA Client (Rust Implementation via PyO3)
# ==============================================================================


@pytest.fixture
async def rust_opa_client():
    """
    Rust-based OPA client using native Regorus engine.

    This is the high-performance Rust implementation that will be benchmarked
    against the HTTP client. Currently mocked until the opa-engine worker
    completes the actual implementation.
    """
    # Check if Rust implementation is available
    rust_available = os.getenv("RUST_ENABLED", "false").lower() == "true"

    if not rust_available:
        # Return a fast mock for benchmarking purposes
        mock_client = AsyncMock()
        mock_client.evaluate_policy = AsyncMock(
            return_value=AuthorizationDecision(
                allow=True,
                reason="User authorized (Rust mock)",
            )
        )
        mock_client.close = AsyncMock()

        yield mock_client
        await mock_client.close()
    else:
        # Use actual Rust implementation when available
        try:
            from sark.services.policy.factory import RustOPAClient

            client = RustOPAClient(opa_url=None)  # Native engine, no URL needed
            yield client
            await client.close()
        except (ImportError, RuntimeError) as e:
            pytest.skip(f"Rust OPA client not available: {e}")


# ==============================================================================
# Redis Cache (Python Implementation)
# ==============================================================================


@pytest.fixture
async def redis_cache(mock_redis) -> PolicyCache:
    """
    Redis-based policy cache (Python implementation).

    This is the baseline Python implementation using valkey/Redis.
    """
    cache = PolicyCache(
        redis_client=mock_redis,
        ttl_seconds=300,
        enabled=True,
    )
    return cache


# ==============================================================================
# Rust Cache (Rust Implementation via PyO3)
# ==============================================================================


@pytest.fixture
async def rust_cache():
    """
    Rust-based policy cache using DashMap/high-performance concurrent structures.

    This is the high-performance Rust implementation that will be benchmarked
    against Redis. Currently mocked until the cache-engine worker completes
    the actual implementation.
    """
    # Check if Rust implementation is available
    rust_available = os.getenv("RUST_ENABLED", "false").lower() == "true"

    if not rust_available:
        # Return a fast mock for benchmarking purposes
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value={"allow": True, "reason": "Cached (Rust mock)"})
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()

        yield mock_cache
    else:
        # Use actual Rust implementation when available
        try:
            from sark.services.policy.factory import RustPolicyCache

            cache = RustPolicyCache(max_size=10000)
            yield cache
        except (ImportError, RuntimeError) as e:
            pytest.skip(f"Rust policy cache not available: {e}")


# ==============================================================================
# Preloaded Data for Cache Testing
# ==============================================================================


@pytest.fixture
async def preloaded_cache_data(mock_redis) -> dict:
    """
    Preload cache with test data for warm cache benchmarks.

    Returns a dictionary mapping test keys to their cached decisions.
    """
    test_data = {}

    for i in range(1000):
        key = f"test-key-{i}"
        decision = {
            "allow": i % 2 == 0,  # Alternate allow/deny
            "reason": f"Cached decision {i}",
        }
        test_data[key] = decision

        # Mock Redis to return this data
        mock_redis.get = AsyncMock(return_value=json.dumps(decision))

    return test_data


# ==============================================================================
# Event Loop Configuration
# ==============================================================================


@pytest.fixture(scope="session")
def event_loop_policy():
    """Configure event loop policy for async benchmarks."""
    return asyncio.get_event_loop_policy()


# ==============================================================================
# Benchmark Configuration
# ==============================================================================


@pytest.fixture(autouse=True)
def benchmark_config():
    """
    Configure pytest-benchmark settings for all benchmarks.

    This ensures consistent benchmarking across all tests.
    """
    # These settings will be used by pytest-benchmark
    return {
        "min_rounds": 5,
        "max_time": 1.0,
        "warmup": True,
        "warmup_iterations": 3,
    }
