"""Unit tests for Rust-based Policy Cache."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from sark.services.policy import rust_cache


@pytest.fixture
def mock_rust_cache():
    """Mock RustCache for testing without Rust extensions."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = None
    mock.delete.return_value = False
    mock.clear.return_value = None
    mock.size.return_value = 0
    mock.cleanup_expired.return_value = 0
    return mock


@pytest.fixture
def cache_with_mock(mock_rust_cache):
    """Create RustPolicyCache with mocked Rust extension."""
    with patch.object(rust_cache, "RUST_AVAILABLE", True):
        with patch.object(rust_cache, "RustCache", return_value=mock_rust_cache):
            cache = rust_cache.RustPolicyCache(max_size=100, ttl_seconds=60)
            cache.cache = mock_rust_cache
            yield cache


class TestRustCacheAvailability:
    """Test Rust cache availability checking."""

    def test_is_rust_cache_available_when_available(self):
        """Test availability check when Rust extensions are available."""
        with patch.object(rust_cache, "RUST_AVAILABLE", True):
            assert rust_cache.is_rust_cache_available() is True

    def test_is_rust_cache_available_when_unavailable(self):
        """Test availability check when Rust extensions are unavailable."""
        with patch.object(rust_cache, "RUST_AVAILABLE", False):
            assert rust_cache.is_rust_cache_available() is False

    def test_initialization_fails_without_rust(self):
        """Test that initialization fails when Rust extensions are unavailable."""
        with patch.object(rust_cache, "RUST_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Rust cache extensions not available"):
                rust_cache.RustPolicyCache()


class TestRustPolicyCacheInitialization:
    """Test RustPolicyCache initialization."""

    def test_default_initialization(self, mock_rust_cache):
        """Test initialization with default parameters."""
        with patch.object(rust_cache, "RUST_AVAILABLE", True):
            with patch.object(rust_cache, "RustCache", return_value=mock_rust_cache) as mock_class:
                cache = rust_cache.RustPolicyCache()

                assert cache.max_size == rust_cache.RustPolicyCache.DEFAULT_MAX_SIZE
                assert cache.ttl_seconds == rust_cache.RustPolicyCache.DEFAULT_TTL_SECONDS
                assert cache.enabled is True
                assert cache.use_optimized_ttl is True

                # Verify RustCache was created with correct parameters
                mock_class.assert_called_once_with(
                    rust_cache.RustPolicyCache.DEFAULT_MAX_SIZE,
                    rust_cache.RustPolicyCache.DEFAULT_TTL_SECONDS,
                )

    def test_custom_initialization(self, mock_rust_cache):
        """Test initialization with custom parameters."""
        with patch.object(rust_cache, "RUST_AVAILABLE", True):
            with patch.object(rust_cache, "RustCache", return_value=mock_rust_cache) as mock_class:
                cache = rust_cache.RustPolicyCache(
                    max_size=500, ttl_seconds=120, enabled=False, use_optimized_ttl=False
                )

                assert cache.max_size == 500
                assert cache.ttl_seconds == 120
                assert cache.enabled is False
                assert cache.use_optimized_ttl is False

                mock_class.assert_called_once_with(500, 120)


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_generate_cache_key_without_context(self, cache_with_mock):
        """Test key generation without context."""
        key = cache_with_mock._generate_cache_key(
            "user-123", "execute", "tool:calculator", None
        )

        assert key.startswith("policy:decision:user-123:execute:tool_calculator:")
        assert key.endswith(":none")

    def test_generate_cache_key_with_context(self, cache_with_mock):
        """Test key generation with context."""
        context = {"param1": "value1", "param2": "value2"}
        key = cache_with_mock._generate_cache_key(
            "user-123", "execute", "tool:calculator", context
        )

        assert key.startswith("policy:decision:user-123:execute:tool_calculator:")
        assert not key.endswith(":none")
        # Context hash should be 16 characters
        hash_part = key.split(":")[-1]
        assert len(hash_part) == 16

    def test_generate_cache_key_consistent_with_same_context(self, cache_with_mock):
        """Test that same input generates same key."""
        context = {"param1": "value1", "param2": "value2"}

        key1 = cache_with_mock._generate_cache_key(
            "user-123", "execute", "tool:calculator", context
        )
        key2 = cache_with_mock._generate_cache_key(
            "user-123", "execute", "tool:calculator", context
        )

        assert key1 == key2

    def test_generate_cache_key_different_with_different_context(self, cache_with_mock):
        """Test that different context generates different key."""
        context1 = {"param1": "value1"}
        context2 = {"param1": "value2"}

        key1 = cache_with_mock._generate_cache_key(
            "user-123", "execute", "tool:calculator", context1
        )
        key2 = cache_with_mock._generate_cache_key(
            "user-123", "execute", "tool:calculator", context2
        )

        assert key1 != key2

    def test_generate_cache_key_handles_special_characters(self, cache_with_mock):
        """Test that special characters in resource are cleaned."""
        key = cache_with_mock._generate_cache_key(
            "user-123", "execute", "tool:calculator/v2", None
        )

        # Colons and slashes should be replaced with underscores
        assert "tool_calculator_v2" in key
        assert ":calculator/" not in key


class TestTTLManagement:
    """Test TTL management."""

    def test_get_ttl_default(self, cache_with_mock):
        """Test getting default TTL."""
        ttl = cache_with_mock._get_ttl_for_sensitivity(None)
        assert ttl == 60  # ttl_seconds from fixture

    def test_get_ttl_for_sensitivity_when_disabled(self, cache_with_mock):
        """Test TTL when optimized TTL is disabled."""
        cache_with_mock.use_optimized_ttl = False
        ttl = cache_with_mock._get_ttl_for_sensitivity("critical")
        assert ttl == 60  # Should use default

    def test_get_ttl_for_critical(self, cache_with_mock):
        """Test TTL for critical sensitivity."""
        ttl = cache_with_mock._get_ttl_for_sensitivity("critical")
        assert ttl == 60

    def test_get_ttl_for_confidential(self, cache_with_mock):
        """Test TTL for confidential sensitivity."""
        ttl = cache_with_mock._get_ttl_for_sensitivity("confidential")
        assert ttl == 120

    def test_get_ttl_for_public(self, cache_with_mock):
        """Test TTL for public sensitivity."""
        ttl = cache_with_mock._get_ttl_for_sensitivity("public")
        assert ttl == 300


@pytest.mark.asyncio
class TestCacheOperations:
    """Test cache get/set/delete operations."""

    async def test_get_cache_hit(self, cache_with_mock):
        """Test successful cache hit."""
        decision = {"allow": True, "reason": "test"}
        cache_with_mock.cache.get.return_value = json.dumps(decision)

        result = await cache_with_mock.get("user-123", "execute", "tool:calculator")

        assert result == decision
        assert cache_with_mock.metrics.hits == 1
        assert cache_with_mock.metrics.misses == 0
        assert cache_with_mock.metrics.total_requests == 1

    async def test_get_cache_miss(self, cache_with_mock):
        """Test cache miss."""
        cache_with_mock.cache.get.return_value = None

        result = await cache_with_mock.get("user-123", "execute", "tool:calculator")

        assert result is None
        assert cache_with_mock.metrics.hits == 0
        assert cache_with_mock.metrics.misses == 1
        assert cache_with_mock.metrics.total_requests == 1

    async def test_get_when_disabled(self, cache_with_mock):
        """Test get returns None when cache is disabled."""
        cache_with_mock.enabled = False

        result = await cache_with_mock.get("user-123", "execute", "tool:calculator")

        assert result is None
        cache_with_mock.cache.get.assert_not_called()

    async def test_get_with_invalid_json(self, cache_with_mock):
        """Test get handles invalid JSON gracefully."""
        cache_with_mock.cache.get.return_value = "invalid json {"

        result = await cache_with_mock.get("user-123", "execute", "tool:calculator")

        assert result is None

    async def test_set_success(self, cache_with_mock):
        """Test successful cache set."""
        decision = {"allow": True, "reason": "test"}

        result = await cache_with_mock.set(
            "user-123", "execute", "tool:calculator", decision
        )

        assert result is True
        cache_with_mock.cache.set.assert_called_once()

        # Verify JSON serialization
        call_args = cache_with_mock.cache.set.call_args
        assert call_args[0][1] == json.dumps(decision)

    async def test_set_with_custom_ttl(self, cache_with_mock):
        """Test set with custom TTL."""
        decision = {"allow": True}

        await cache_with_mock.set(
            "user-123", "execute", "tool:calculator", decision, ttl_seconds=300
        )

        # Verify TTL was passed correctly
        call_args = cache_with_mock.cache.set.call_args
        assert call_args[0][2] == 300  # ttl parameter

    async def test_set_with_sensitivity(self, cache_with_mock):
        """Test set with sensitivity-based TTL."""
        decision = {"allow": True}

        await cache_with_mock.set(
            "user-123", "execute", "tool:calculator", decision, sensitivity="critical"
        )

        # Verify TTL from sensitivity
        call_args = cache_with_mock.cache.set.call_args
        assert call_args[0][2] == 60  # critical TTL

    async def test_set_when_disabled(self, cache_with_mock):
        """Test set returns False when cache is disabled."""
        cache_with_mock.enabled = False
        decision = {"allow": True}

        result = await cache_with_mock.set(
            "user-123", "execute", "tool:calculator", decision
        )

        assert result is False
        cache_with_mock.cache.set.assert_not_called()

    async def test_set_tracks_evictions(self, cache_with_mock):
        """Test that set tracks evictions when at capacity."""
        cache_with_mock.cache.size.return_value = 100  # At max size
        decision = {"allow": True}

        await cache_with_mock.set("user-123", "execute", "tool:calculator", decision)

        assert cache_with_mock.metrics.evictions == 1

    async def test_delete_success(self, cache_with_mock):
        """Test successful delete."""
        cache_with_mock.cache.delete.return_value = True

        result = await cache_with_mock.delete("user-123", "execute", "tool:calculator")

        assert result is True
        cache_with_mock.cache.delete.assert_called_once()

    async def test_delete_key_not_found(self, cache_with_mock):
        """Test delete when key doesn't exist."""
        cache_with_mock.cache.delete.return_value = False

        result = await cache_with_mock.delete("user-123", "execute", "tool:calculator")

        assert result is False

    async def test_clear(self, cache_with_mock):
        """Test clear all entries."""
        result = await cache_with_mock.clear()

        assert result is True
        cache_with_mock.cache.clear.assert_called_once()

    async def test_size(self, cache_with_mock):
        """Test getting cache size."""
        cache_with_mock.cache.size.return_value = 42

        result = await cache_with_mock.size()

        assert result == 42

    async def test_cleanup_expired(self, cache_with_mock):
        """Test cleanup of expired entries."""
        cache_with_mock.cache.cleanup_expired.return_value = 5

        result = await cache_with_mock.cleanup_expired()

        assert result == 5
        cache_with_mock.cache.cleanup_expired.assert_called_once()


@pytest.mark.asyncio
class TestMetrics:
    """Test cache metrics."""

    async def test_metrics_initial_state(self, cache_with_mock):
        """Test initial metrics state."""
        metrics = cache_with_mock.get_metrics()

        assert metrics["hits"] == 0
        assert metrics["misses"] == 0
        assert metrics["total_requests"] == 0
        assert metrics["hit_rate"] == 0.0
        assert metrics["miss_rate"] == 100.0

    async def test_metrics_after_operations(self, cache_with_mock):
        """Test metrics after various operations."""
        # 2 hits
        cache_with_mock.cache.get.return_value = json.dumps({"allow": True})
        await cache_with_mock.get("user-123", "execute", "tool1")
        await cache_with_mock.get("user-123", "execute", "tool2")

        # 1 miss
        cache_with_mock.cache.get.return_value = None
        await cache_with_mock.get("user-123", "execute", "tool3")

        metrics = cache_with_mock.get_metrics()

        assert metrics["hits"] == 2
        assert metrics["misses"] == 1
        assert metrics["total_requests"] == 3
        assert metrics["hit_rate"] == pytest.approx(66.67, rel=0.01)
        assert metrics["miss_rate"] == pytest.approx(33.33, rel=0.01)

    async def test_reset_metrics(self, cache_with_mock):
        """Test resetting metrics."""
        # Generate some metrics
        cache_with_mock.cache.get.return_value = json.dumps({"allow": True})
        await cache_with_mock.get("user-123", "execute", "tool1")

        # Reset
        cache_with_mock.reset_metrics()

        metrics = cache_with_mock.get_metrics()
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check functionality."""

    async def test_health_check_success(self, cache_with_mock):
        """Test successful health check."""
        # Mock successful get returning the test value
        test_value = {"status": "ok"}
        cache_with_mock.cache.get.return_value = json.dumps(test_value)

        result = await cache_with_mock.health_check()

        assert result is True

    async def test_health_check_failure(self, cache_with_mock):
        """Test health check failure."""
        cache_with_mock.cache.set.side_effect = Exception("Cache error")

        result = await cache_with_mock.health_check()

        assert result is False


class TestGlobalInstance:
    """Test global cache instance management."""

    def test_get_rust_policy_cache_creates_instance(self, mock_rust_cache):
        """Test that get_rust_policy_cache creates instance."""
        # Reset global instance
        rust_cache._cache_instance = None

        with patch.object(rust_cache, "RUST_AVAILABLE", True):
            with patch.object(rust_cache, "RustCache", return_value=mock_rust_cache):
                cache = rust_cache.get_rust_policy_cache(max_size=200, ttl_seconds=90)

                assert cache is not None
                assert cache.max_size == 200
                assert cache.ttl_seconds == 90

    def test_get_rust_policy_cache_returns_same_instance(self, mock_rust_cache):
        """Test that get_rust_policy_cache returns singleton."""
        # Reset global instance
        rust_cache._cache_instance = None

        with patch.object(rust_cache, "RUST_AVAILABLE", True):
            with patch.object(rust_cache, "RustCache", return_value=mock_rust_cache):
                cache1 = rust_cache.get_rust_policy_cache()
                cache2 = rust_cache.get_rust_policy_cache()

                assert cache1 is cache2

    def test_get_rust_policy_cache_without_rust_raises(self):
        """Test that get_rust_policy_cache raises without Rust."""
        rust_cache._cache_instance = None

        with patch.object(rust_cache, "RUST_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Rust cache extensions not available"):
                rust_cache.get_rust_policy_cache()


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in cache operations."""

    async def test_get_handles_exception(self, cache_with_mock):
        """Test that get handles exceptions gracefully."""
        cache_with_mock.cache.get.side_effect = Exception("Rust error")

        result = await cache_with_mock.get("user-123", "execute", "tool")

        assert result is None

    async def test_set_handles_exception(self, cache_with_mock):
        """Test that set handles exceptions gracefully."""
        cache_with_mock.cache.set.side_effect = Exception("Rust error")

        result = await cache_with_mock.set("user-123", "execute", "tool", {"allow": True})

        assert result is False

    async def test_delete_handles_exception(self, cache_with_mock):
        """Test that delete handles exceptions gracefully."""
        cache_with_mock.cache.delete.side_effect = Exception("Rust error")

        result = await cache_with_mock.delete("user-123", "execute", "tool")

        assert result is False

    async def test_clear_handles_exception(self, cache_with_mock):
        """Test that clear handles exceptions gracefully."""
        cache_with_mock.cache.clear.side_effect = Exception("Rust error")

        result = await cache_with_mock.clear()

        assert result is False

    async def test_size_handles_exception(self, cache_with_mock):
        """Test that size handles exceptions gracefully."""
        cache_with_mock.cache.size.side_effect = Exception("Rust error")

        result = await cache_with_mock.size()

        assert result == 0

    async def test_cleanup_handles_exception(self, cache_with_mock):
        """Test that cleanup_expired handles exceptions gracefully."""
        cache_with_mock.cache.cleanup_expired.side_effect = Exception("Rust error")

        result = await cache_with_mock.cleanup_expired()

        assert result == 0
