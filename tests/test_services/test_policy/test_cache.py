"""Tests for Policy Cache Service."""

import hashlib
import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from sark.services.policy.cache import CacheMetrics, PolicyCache, get_policy_cache


@pytest_asyncio.fixture
async def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()
    redis_mock.scan_iter = AsyncMock(return_value=iter([]))
    return redis_mock


@pytest.fixture
def cache(mock_redis):
    """Create PolicyCache instance with mock Redis."""
    return PolicyCache(redis_client=mock_redis, ttl_seconds=300, enabled=True)


@pytest.fixture
def cache_disabled():
    """Create PolicyCache instance with caching disabled."""
    return PolicyCache(enabled=False)


# ============================================================================
# CACHE KEY GENERATION TESTS
# ============================================================================


def test_generate_cache_key_basic(cache):
    """Test basic cache key generation."""
    key = cache._generate_cache_key(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:database_query",
    )

    assert key.startswith("policy:decision:")
    assert "user-123" in key
    assert "tool:invoke" in key
    assert "tool_database_query" in key  # Resource with special chars replaced


def test_generate_cache_key_with_context(cache):
    """Test cache key generation with context."""
    context = {"timestamp": 12345, "ip": "192.168.1.1"}
    key = cache._generate_cache_key(
        user_id="user-456",
        action="server:register",
        resource="server:test-server",
        context=context,
    )

    # Context should be hashed
    context_json = json.dumps(context, sort_keys=True)
    context_hash = hashlib.sha256(context_json.encode()).hexdigest()[:16]

    assert "user-456" in key
    assert context_hash in key


def test_generate_cache_key_consistent(cache):
    """Test that same inputs generate same key."""
    context = {"timestamp": 12345}

    key1 = cache._generate_cache_key(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
        context=context,
    )

    key2 = cache._generate_cache_key(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
        context=context,
    )

    assert key1 == key2


def test_generate_cache_key_special_chars(cache):
    """Test cache key generation with special characters in resource."""
    key = cache._generate_cache_key(
        user_id="user-123",
        action="tool:invoke",
        resource="server:my-server/v1/api",
    )

    # Special chars should be replaced
    assert ":" not in key.split("policy:decision:")[1].split(":", 3)[-1]
    assert "/" not in key


# ============================================================================
# CACHE GET TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_cache_get_hit(cache, mock_redis):
    """Test cache hit returns cached decision."""
    decision = {"allow": True, "reason": "Cached decision"}
    mock_redis.get.return_value = json.dumps(decision)

    result = await cache.get(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
    )

    assert result == decision
    assert cache.metrics.hits == 1
    assert cache.metrics.total_requests == 1
    assert cache.metrics.hit_rate == 100.0


@pytest.mark.asyncio
async def test_cache_get_miss(cache, mock_redis):
    """Test cache miss returns None."""
    mock_redis.get.return_value = None

    result = await cache.get(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
    )

    assert result is None
    assert cache.metrics.misses == 1
    assert cache.metrics.total_requests == 1
    assert cache.metrics.hit_rate == 0.0


@pytest.mark.asyncio
async def test_cache_get_disabled(cache_disabled):
    """Test that disabled cache always returns None."""
    result = await cache_disabled.get(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
    )

    assert result is None
    # No metrics should be updated
    assert cache_disabled.metrics.total_requests == 0


@pytest.mark.asyncio
async def test_cache_get_error_handling(cache, mock_redis):
    """Test cache gracefully handles Redis errors."""
    mock_redis.get.side_effect = Exception("Redis connection error")

    result = await cache.get(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
    )

    # Should return None on error
    assert result is None


# ============================================================================
# CACHE SET TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_cache_set_success(cache, mock_redis):
    """Test cache set stores decision."""
    decision = {"allow": True, "reason": "Test decision"}

    result = await cache.set(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
        decision=decision,
    )

    assert result is True
    mock_redis.setex.assert_called_once()

    # Verify TTL is correct (default 300s)
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 300  # TTL


@pytest.mark.asyncio
async def test_cache_set_custom_ttl(cache, mock_redis):
    """Test cache set with custom TTL."""
    decision = {"allow": True, "reason": "Test decision"}

    await cache.set(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
        decision=decision,
        ttl_seconds=60,
    )

    # Verify custom TTL is used
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 60


@pytest.mark.asyncio
async def test_cache_set_disabled(cache_disabled):
    """Test that disabled cache doesn't store anything."""
    decision = {"allow": True}

    result = await cache_disabled.set(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
        decision=decision,
    )

    assert result is False


@pytest.mark.asyncio
async def test_cache_set_error_handling(cache, mock_redis):
    """Test cache set handles Redis errors gracefully."""
    mock_redis.setex.side_effect = Exception("Redis write error")

    result = await cache.set(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:test",
        decision={"allow": True},
    )

    assert result is False


# ============================================================================
# CACHE INVALIDATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_invalidate_all(cache, mock_redis):
    """Test invalidating all cache entries."""
    # Mock scan_iter to return some keys
    keys = [
        "policy:decision:user-1:tool:invoke:res1:hash1",
        "policy:decision:user-2:tool:invoke:res2:hash2",
    ]

    async def async_iter(keys_list):
        for key in keys_list:
            yield key

    mock_redis.scan_iter.return_value = async_iter(keys)
    mock_redis.delete.return_value = len(keys)

    deleted = await cache.invalidate()

    assert deleted == 2
    mock_redis.delete.assert_called_once_with(*keys)


@pytest.mark.asyncio
async def test_invalidate_by_user(cache, mock_redis):
    """Test invalidating cache for specific user."""
    keys = ["policy:decision:user-123:tool:invoke:res1:hash1"]

    async def async_iter(keys_list):
        for key in keys_list:
            yield key

    mock_redis.scan_iter.return_value = async_iter(keys)
    mock_redis.delete.return_value = len(keys)

    deleted = await cache.invalidate(user_id="user-123")

    assert deleted == 1
    # Verify scan pattern includes user ID
    call_args = mock_redis.scan_iter.call_args
    assert "user-123" in call_args[1]["match"]


@pytest.mark.asyncio
async def test_invalidate_by_user_and_action(cache, mock_redis):
    """Test invalidating cache for user + action."""

    async def async_iter(keys_list):
        for key in keys_list:
            yield key

    mock_redis.scan_iter.return_value = async_iter([])

    await cache.invalidate(user_id="user-123", action="tool:invoke")

    # Verify pattern
    call_args = mock_redis.scan_iter.call_args
    pattern = call_args[1]["match"]
    assert "user-123" in pattern
    assert "tool:invoke" in pattern


@pytest.mark.asyncio
async def test_invalidate_pattern(cache, mock_redis):
    """Test invalidate by custom pattern."""
    keys = ["policy:decision:user-123:tool:invoke:res:hash"]

    async def async_iter(keys_list):
        for key in keys_list:
            yield key

    mock_redis.scan_iter.return_value = async_iter(keys)
    mock_redis.delete.return_value = len(keys)

    deleted = await cache.invalidate_pattern("policy:decision:user-123:*")

    assert deleted == 1


@pytest.mark.asyncio
async def test_clear_all(cache, mock_redis):
    """Test clearing all cache entries."""

    async def async_iter(keys_list):
        for key in keys_list:
            yield key

    mock_redis.scan_iter.return_value = async_iter(["policy:decision:key1", "policy:decision:key2"])
    mock_redis.delete.return_value = 2

    result = await cache.clear_all()

    assert result is True


# ============================================================================
# METRICS TESTS
# ============================================================================


def test_cache_metrics_hit_rate(cache):
    """Test cache metrics hit rate calculation."""
    # Simulate hits and misses
    cache.metrics.hits = 75
    cache.metrics.misses = 25
    cache.metrics.total_requests = 100

    assert cache.metrics.hit_rate == 75.0
    assert cache.metrics.miss_rate == 25.0


def test_cache_metrics_zero_requests():
    """Test metrics with zero requests."""
    metrics = CacheMetrics()

    assert metrics.hit_rate == 0.0
    assert metrics.miss_rate == 100.0


def test_get_metrics(cache):
    """Test getting metrics as dictionary."""
    cache.metrics.hits = 10
    cache.metrics.misses = 5
    cache.metrics.total_requests = 15
    cache.metrics.cache_latency_ms = 2.5
    cache.metrics.opa_latency_ms = 45.0

    metrics = cache.get_metrics()

    assert metrics["hits"] == 10
    assert metrics["misses"] == 5
    assert metrics["total_requests"] == 15
    assert metrics["hit_rate"] == pytest.approx(66.67, rel=0.1)
    assert metrics["avg_cache_latency_ms"] == 2.5
    assert metrics["avg_opa_latency_ms"] == 45.0


def test_reset_metrics(cache):
    """Test resetting cache metrics."""
    cache.metrics.hits = 100
    cache.metrics.misses = 50
    cache.reset_metrics()

    assert cache.metrics.hits == 0
    assert cache.metrics.misses == 0
    assert cache.metrics.total_requests == 0


def test_record_opa_latency(cache):
    """Test recording OPA latency."""
    # First miss
    cache.metrics.misses = 1
    cache.record_opa_latency(50.0)
    assert cache.metrics.opa_latency_ms == 50.0

    # Second miss
    cache.metrics.misses = 2
    cache.record_opa_latency(60.0)
    # Should be average: (50 + 60) / 2 = 55
    assert cache.metrics.opa_latency_ms == 55.0


# ============================================================================
# UTILITY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_cache_size(cache, mock_redis):
    """Test getting cache size."""

    async def async_iter(keys_list):
        for key in keys_list:
            yield key

    keys = [f"policy:decision:key{i}" for i in range(10)]
    mock_redis.scan_iter.return_value = async_iter(keys)

    size = await cache.get_cache_size()

    assert size == 10


@pytest.mark.asyncio
async def test_health_check_success(cache, mock_redis):
    """Test cache health check success."""
    mock_redis.ping.return_value = True

    is_healthy = await cache.health_check()

    assert is_healthy is True


@pytest.mark.asyncio
async def test_health_check_failure(cache, mock_redis):
    """Test cache health check failure."""
    mock_redis.ping.side_effect = Exception("Connection refused")

    is_healthy = await cache.health_check()

    assert is_healthy is False


@pytest.mark.asyncio
async def test_close(cache, mock_redis):
    """Test closing cache connection."""
    await cache.close()

    mock_redis.aclose.assert_called_once()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_cache_hit_miss_workflow(cache, mock_redis):
    """Test complete cache hit/miss workflow."""
    decision = {"allow": True, "reason": "Test"}

    # First request - cache miss
    mock_redis.get.return_value = None
    result1 = await cache.get("user-1", "tool:invoke", "tool:test")
    assert result1 is None
    assert cache.metrics.misses == 1

    # Store in cache
    await cache.set("user-1", "tool:invoke", "tool:test", decision)

    # Second request - cache hit
    mock_redis.get.return_value = json.dumps(decision)
    result2 = await cache.get("user-1", "tool:invoke", "tool:test")
    assert result2 == decision
    assert cache.metrics.hits == 1
    assert cache.metrics.hit_rate == 50.0


def test_get_policy_cache_singleton():
    """Test that get_policy_cache returns singleton instance."""
    cache1 = get_policy_cache()
    cache2 = get_policy_cache()

    # Should be same instance
    assert cache1 is cache2


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.asyncio
async def test_cache_with_complex_context(cache, mock_redis):
    """Test caching with complex context object."""
    context = {
        "timestamp": 12345,
        "nested": {"key": "value"},
        "list": [1, 2, 3],
    }

    key = cache._generate_cache_key(
        user_id="user-1",
        action="tool:invoke",
        resource="tool:test",
        context=context,
    )

    # Should not raise error
    assert "policy:decision:" in key


@pytest.mark.asyncio
async def test_cache_invalidate_no_keys(cache, mock_redis):
    """Test invalidation when no keys match."""

    async def async_iter(keys_list):
        for key in keys_list:
            yield key

    mock_redis.scan_iter.return_value = async_iter([])

    deleted = await cache.invalidate(user_id="nonexistent")

    assert deleted == 0


@pytest.mark.asyncio
async def test_concurrent_cache_operations(cache, mock_redis):
    """Test cache handles concurrent operations."""
    import asyncio

    # Simulate concurrent gets
    tasks = [cache.get("user-1", "tool:invoke", f"tool:{i}") for i in range(10)]

    results = await asyncio.gather(*tasks)

    # All should complete without error
    assert len(results) == 10
    assert cache.metrics.total_requests == 10
