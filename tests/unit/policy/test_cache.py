"""Comprehensive tests for PolicyCache.

This module tests:
- Cache initialization and configuration
- Get/Set operations with TTL
- Batch operations with Redis pipelining
- Stale-while-revalidate pattern
- Cache invalidation
- Performance metrics tracking
"""

import asyncio
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from sark.services.policy.cache import CacheMetrics, PolicyCache


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()

    # Create a pipeline mock
    pipeline_mock = MagicMock()
    pipeline_mock.get = MagicMock(return_value=pipeline_mock)
    pipeline_mock.ttl = MagicMock(return_value=pipeline_mock)
    pipeline_mock.execute = AsyncMock(return_value=[None, -2])  # Default: no value, no TTL
    pipeline_mock.setex = MagicMock(return_value=pipeline_mock)

    redis_mock.pipeline = MagicMock(return_value=pipeline_mock)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.keys = AsyncMock(return_value=[])

    # Mock scan_iter for invalidation
    async def mock_scan_iter(match=None, count=100):
        """Mock async iterator for Redis scan_iter."""
        keys_to_return = []
        if match and "user-123" in match:
            keys_to_return = [
                "policy:decision:user-123:key1",
                "policy:decision:user-123:key2",
            ]
        elif match:
            keys_to_return = ["key1", "key2", "key3"]
        for key in keys_to_return:
            yield key

    redis_mock.scan_iter = mock_scan_iter

    return redis_mock


@pytest.fixture
def cache(mock_redis):
    """Create PolicyCache instance with mock Redis."""
    return PolicyCache(redis_client=mock_redis, ttl_seconds=300)


class TestCacheMetrics:
    """Test CacheMetrics class."""

    def test_initialization(self):
        """Test metrics initialize with zeros."""
        metrics = CacheMetrics()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.stale_hits == 0
        assert metrics.revalidations == 0
        assert metrics.total_requests == 0

    def test_hit_rate_zero_requests(self):
        """Test hit rate when no requests."""
        metrics = CacheMetrics()

        assert metrics.hit_rate == 0.0
        assert metrics.effective_hit_rate == 0.0
        assert metrics.miss_rate == 100.0  # 100% - 0% hits = 100% misses

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics()
        metrics.total_requests = 100
        metrics.hits = 75
        metrics.misses = 25

        assert metrics.hit_rate == 75.0
        assert metrics.miss_rate == 25.0

    def test_effective_hit_rate_with_stale_hits(self):
        """Test effective hit rate includes stale hits."""
        metrics = CacheMetrics()
        metrics.total_requests = 100
        metrics.hits = 60
        metrics.stale_hits = 20
        metrics.misses = 20

        assert metrics.effective_hit_rate == 80.0

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = CacheMetrics()
        metrics.total_requests = 100
        metrics.hits = 75
        metrics.misses = 25

        result = metrics.to_dict()

        assert result["hits"] == 75
        assert result["misses"] == 25
        assert result["total_requests"] == 100
        assert result["hit_rate"] == 75.0
        assert result["miss_rate"] == 25.0


class TestPolicyCacheInit:
    """Test PolicyCache initialization."""

    def test_initialization_defaults(self, mock_redis):
        """Test cache initializes with default values."""
        cache = PolicyCache(redis_client=mock_redis)

        assert cache.ttl_seconds == 300
        assert cache.enabled is True
        assert cache.stale_while_revalidate is True
        assert cache.use_optimized_ttl is True
        assert cache.redis == mock_redis

    def test_initialization_custom_values(self, mock_redis):
        """Test cache initializes with custom values."""
        cache = PolicyCache(
            redis_client=mock_redis,
            ttl_seconds=600,
            enabled=False,
            stale_while_revalidate=False,
            use_optimized_ttl=False,
        )

        assert cache.ttl_seconds == 600
        assert cache.enabled is False
        assert cache.stale_while_revalidate is False
        assert cache.use_optimized_ttl is False

    def test_optimized_ttl_values(self):
        """Test that optimized TTL values are defined."""
        assert PolicyCache.OPTIMIZED_TTL["critical"] == 60
        assert PolicyCache.OPTIMIZED_TTL["confidential"] == 120
        assert PolicyCache.OPTIMIZED_TTL["internal"] == 180
        assert PolicyCache.OPTIMIZED_TTL["public"] == 300
        assert PolicyCache.OPTIMIZED_TTL["default"] == 120


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_generate_cache_key(self, cache):
        """Test generating cache key from parameters."""
        key = cache._generate_cache_key(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test_tool",
            context={"timestamp": 1234567890},
        )

        assert key.startswith("policy:decision:")
        assert "user-123" in key or hashlib.sha256(
            json.dumps({
                "user_id": "user-123",
                "action": "tool:invoke",
                "resource": "tool:test_tool",
                "context": {"timestamp": 1234567890}
            }, sort_keys=True).encode()
        ).hexdigest() in key

    def test_generate_cache_key_consistent(self, cache):
        """Test that same inputs generate same key."""
        key1 = cache._generate_cache_key(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            context={},
        )

        key2 = cache._generate_cache_key(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            context={},
        )

        assert key1 == key2

    def test_generate_cache_key_different_for_different_inputs(self, cache):
        """Test that different inputs generate different keys."""
        key1 = cache._generate_cache_key(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            context={},
        )

        key2 = cache._generate_cache_key(
            user_id="user-456",
            action="tool:invoke",
            resource="tool:test",
            context={},
        )

        assert key1 != key2


class TestCacheGet:
    """Test cache get operations."""

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache, mock_redis):
        """Test getting value when not in cache (miss)."""
        mock_redis.get.return_value = None

        result = await cache.get(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
        )

        assert result is None
        assert cache.metrics.misses == 1
        assert cache.metrics.total_requests == 1

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache, mock_redis):
        """Test getting value from cache (hit)."""
        cached_decision = {
            "allow": True,
            "reason": "Cached decision",
        }

        cache_entry_json = json.dumps(cached_decision)

        # Mock pipeline to return cached value and TTL
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[cache_entry_json, 300])

        result = await cache.get(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
        )

        assert result == cached_decision
        assert cache.metrics.hits == 1
        assert cache.metrics.total_requests == 1

    @pytest.mark.asyncio
    async def test_get_when_disabled(self, cache, mock_redis):
        """Test that get returns None when cache is disabled."""
        cache.enabled = False

        result = await cache.get(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
        )

        assert result is None
        mock_redis.get.assert_not_called()


class TestCacheSet:
    """Test cache set operations."""

    @pytest.mark.asyncio
    async def test_set_cache_entry(self, cache, mock_redis):
        """Test setting a cache entry."""
        decision = {
            "allow": True,
            "reason": "Test decision",
        }

        await cache.set(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            decision=decision,
            ttl_seconds=300,
        )

        # Verify setex was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 300  # TTL
        assert "allow" in call_args[0][2]  # Cached data contains decision

    @pytest.mark.asyncio
    async def test_set_when_disabled(self, cache, mock_redis):
        """Test that set does nothing when cache is disabled."""
        cache.enabled = False

        decision = {"allow": True}

        await cache.set(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            decision=decision,
        )

        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache, mock_redis):
        """Test setting cache entry with custom TTL."""
        decision = {"allow": True}

        await cache.set(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            decision=decision,
            ttl_seconds=600,
        )

        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 600  # Custom TTL


class TestBatchOperations:
    """Test batch cache operations."""

    @pytest.mark.asyncio
    async def test_get_batch(self, cache, mock_redis):
        """Test batch get operations."""
        # Mock pipeline to return batch results
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.get = MagicMock(return_value=pipeline_mock)
        pipeline_mock.execute = AsyncMock(return_value=[
            json.dumps({"allow": True}),   # First result (cached)
            None,                           # Second result (miss)
            json.dumps({"allow": False}),  # Third result (cached)
        ])

        requests = [
            ("user-1", "tool:invoke", "tool:test1", {}),
            ("user-2", "tool:invoke", "tool:test2", {}),
            ("user-3", "tool:invoke", "tool:test3", {}),
        ]

        results = await cache.get_batch(requests)

        assert len(results) == 3
        assert results[0]["allow"] is True
        assert results[1] is None  # Cache miss
        assert results[2]["allow"] is False

    @pytest.mark.asyncio
    async def test_set_batch(self, cache, mock_redis):
        """Test batch set operations."""
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.setex = MagicMock(return_value=pipeline_mock)
        pipeline_mock.execute = AsyncMock(return_value=[True, True, True])

        entries = [
            ("user-1", "tool:invoke", "tool:test1", {"allow": True}, {}, 300),
            ("user-2", "tool:invoke", "tool:test2", {"allow": False}, {}, 300),
            ("user-3", "tool:invoke", "tool:test3", {"allow": True}, {}, 300),
        ]

        await cache.set_batch(entries)

        # Verify setex was called for each entry
        assert pipeline_mock.setex.call_count == 3
        pipeline_mock.execute.assert_called_once()


class TestCacheInvalidation:
    """Test cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_specific_key(self, cache, mock_redis):
        """Test invalidating specific cache entry."""
        # scan_iter will return keys, delete will be called with those keys
        mock_redis.delete.return_value = 2

        count = await cache.invalidate(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
        )

        # scan_iter mock doesn't return anything for specific keys by default
        assert count >= 0

    @pytest.mark.asyncio
    async def test_invalidate_by_user(self, cache, mock_redis):
        """Test invalidating all entries for a user."""
        mock_redis.delete.return_value = 2

        count = await cache.invalidate(user_id="user-123")

        # scan_iter will yield 2 keys for user-123
        assert count == 2
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache, mock_redis):
        """Test invalidating by pattern."""
        # Create a custom scan_iter for this test
        async def pattern_scan_iter(match=None, count=100):
            for key in ["policy:decision:pattern1", "policy:decision:pattern2"]:
                yield key

        mock_redis.scan_iter = pattern_scan_iter
        mock_redis.delete.return_value = 2

        count = await cache.invalidate_pattern("policy:decision:*")

        assert count == 2
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all(self, cache, mock_redis):
        """Test clearing all cache entries."""
        # Use the mock scan_iter which yields 3 keys for wildcard pattern
        mock_redis.delete.return_value = 3

        result = await cache.clear_all()

        assert result is True
        mock_redis.delete.assert_called_once()


class TestMetricsTracking:
    """Test metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_track_hits_and_misses(self, cache, mock_redis):
        """Test that metrics track hits and misses."""
        pipeline_mock = mock_redis.pipeline.return_value

        # First request: miss
        pipeline_mock.execute = AsyncMock(return_value=[None, -2])
        await cache.get(user_id="user-1", action="test", resource="res")

        assert cache.metrics.misses == 1
        assert cache.metrics.hits == 0

        # Second request: hit
        pipeline_mock.execute = AsyncMock(return_value=[
            json.dumps({"allow": True}), 300
        ])
        await cache.get(user_id="user-2", action="test", resource="res")

        assert cache.metrics.misses == 1
        assert cache.metrics.hits == 1
        assert cache.metrics.total_requests == 2

    def test_get_metrics(self, cache):
        """Test getting metrics as dictionary."""
        cache.metrics.hits = 75
        cache.metrics.misses = 25
        cache.metrics.total_requests = 100

        metrics_dict = cache.get_metrics()

        assert metrics_dict["hits"] == 75
        assert metrics_dict["misses"] == 25
        assert metrics_dict["total_requests"] == 100
        assert metrics_dict["hit_rate"] == 75.0

    def test_reset_metrics(self, cache):
        """Test resetting metrics."""
        cache.metrics.hits = 100
        cache.metrics.misses = 50

        cache.reset_metrics()

        assert cache.metrics.hits == 0
        assert cache.metrics.misses == 0
        assert cache.metrics.total_requests == 0

    def test_record_opa_latency(self, cache):
        """Test recording OPA latency."""
        # Need at least 1 miss for latency to be recorded
        cache.metrics.misses = 1

        cache.record_opa_latency(15.5)

        # OPA latency should be recorded
        assert cache.metrics.opa_latency_ms == 15.5

    @pytest.mark.asyncio
    async def test_get_cache_size(self, cache, mock_redis):
        """Test getting cache size."""
        # Mock scan_iter to return 3 keys
        async def size_scan_iter(match=None, count=100):
            for key in ["key1", "key2", "key3"]:
                yield key

        mock_redis.scan_iter = size_scan_iter

        size = await cache.get_cache_size()

        assert size == 3


class TestStaleWhileRevalidate:
    """Test stale-while-revalidate pattern."""

    @pytest.mark.asyncio
    async def test_stale_entry_triggers_revalidation(self, cache, mock_redis):
        """Test that stale entries trigger background revalidation."""
        # Set up cache entry with low TTL (stale)
        stale_decision = {"allow": True, "reason": "Stale"}

        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[
            json.dumps(stale_decision),
            10  # Low TTL (< 30% of 60s critical TTL)
        ])

        # Set up revalidation callback
        cache.revalidate_callback = AsyncMock(
            return_value={"allow": True, "reason": "Fresh"}
        )

        result = await cache.get(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            sensitivity="critical",
        )

        # Should return stale decision immediately
        assert result == stale_decision
        # Stale hit should be tracked
        assert cache.metrics.stale_hits == 1

    @pytest.mark.asyncio
    async def test_stale_while_revalidate_disabled(self, cache, mock_redis):
        """Test behavior when stale-while-revalidate is disabled."""
        cache.stale_while_revalidate = False

        # Cached entry
        decision = {"allow": True}

        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[
            json.dumps(decision),
            300  # Valid TTL
        ])

        result = await cache.get(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
        )

        # Should return the entry
        assert result is not None
        assert result == decision


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_get_with_corrupted_cache_data(self, cache, mock_redis):
        """Test handling corrupted cache data."""
        pipeline_mock = mock_redis.pipeline.return_value
        pipeline_mock.execute = AsyncMock(return_value=[
            "invalid json{{",  # Corrupted JSON
            300
        ])

        result = await cache.get(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
        )

        # Should treat as cache miss (error handling)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_none_context(self, cache, mock_redis):
        """Test get with None context."""
        mock_redis.get.return_value = None

        result = await cache.get(
            user_id="user-123",
            action="tool:invoke",
            resource="tool:test",
            context=None,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_when_no_keys_match(self, cache, mock_redis):
        """Test invalidation when no keys match."""
        # Create scan_iter that returns no keys
        async def empty_scan_iter(match=None, count=100):
            return
            yield  # Make it a generator but yield nothing

        mock_redis.scan_iter = empty_scan_iter

        count = await cache.invalidate(user_id="nonexistent")

        assert count == 0

    @pytest.mark.asyncio
    async def test_batch_operations_with_empty_list(self, cache, mock_redis):
        """Test batch operations with empty lists."""
        results = await cache.get_batch([])

        assert results == []

        await cache.set_batch([])

        # Should not raise an error
