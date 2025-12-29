"""Rust-based Policy Decision Cache Service.

High-performance in-memory LRU+TTL cache using Rust with PyO3 bindings.
Provides <0.5ms p95 latency and 10-50x performance improvement over Redis.

Features:
- Thread-safe concurrent access via DashMap
- TTL expiration with automatic cleanup
- LRU eviction under memory pressure
- Sub-millisecond latency
- No network I/O overhead
"""

import asyncio
from dataclasses import dataclass
import hashlib
import json
from typing import Any

import structlog

logger = structlog.get_logger()

# Try to import Rust cache extension
try:
    from sark_cache import RustCache

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    RustCache = None
    logger.warning(
        "rust_cache_unavailable",
        reason="sark_cache extension not built",
        suggestion="Run 'maturin develop --release' in rust/sark-cache/",
    )


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    evictions: int = 0  # Tracked when size is at max and set is called
    cache_latency_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage."""
        return 100.0 - self.hit_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "evictions": self.evictions,
            "hit_rate": round(self.hit_rate, 2),
            "miss_rate": round(self.miss_rate, 2),
            "avg_cache_latency_ms": round(self.cache_latency_ms, 2),
        }


class RustPolicyCache:
    """High-performance Rust-based cache for OPA policy decisions.

    This cache provides sub-millisecond latency by storing policy decisions
    in an in-memory LRU+TTL cache implemented in Rust, eliminating network
    I/O overhead from Redis.

    Performance Targets:
    - <0.5ms p95 latency for get/set operations
    - 10-50x faster than Redis cache
    - Thread-safe concurrent access
    """

    # Cache key prefix (same as PolicyCache for consistency)
    KEY_PREFIX = "policy:decision"

    # Default settings
    DEFAULT_MAX_SIZE = 10000
    DEFAULT_TTL_SECONDS = 300

    # Optimized TTL settings based on sensitivity (matching PolicyCache)
    OPTIMIZED_TTL: dict[str, int] = {
        "critical": 60,
        "confidential": 120,
        "internal": 180,
        "public": 300,
        "default": 120,
    }

    def __init__(
        self,
        max_size: int | None = None,
        ttl_seconds: int | None = None,
        enabled: bool = True,
        use_optimized_ttl: bool = True,
    ) -> None:
        """
        Initialize Rust policy cache.

        Args:
            max_size: Maximum number of entries in cache (default: 10000)
            ttl_seconds: Default TTL for cache entries in seconds (default: 300)
            enabled: Whether caching is enabled (default: True)
            use_optimized_ttl: Use sensitivity-based TTL optimization (default: True)

        Raises:
            RuntimeError: If Rust extensions are not available
        """
        if not RUST_AVAILABLE:
            raise RuntimeError(
                "Rust cache extensions not available. "
                "Build with 'maturin develop --release' in rust/sark-cache/"
            )

        self.max_size = max_size or self.DEFAULT_MAX_SIZE
        self.ttl_seconds = ttl_seconds or self.DEFAULT_TTL_SECONDS
        self.enabled = enabled
        self.use_optimized_ttl = use_optimized_ttl
        self.metrics = CacheMetrics()

        # Initialize Rust cache
        self.cache = RustCache(self.max_size, self.ttl_seconds)

        logger.info(
            "rust_policy_cache_initialized",
            max_size=self.max_size,
            ttl_seconds=self.ttl_seconds,
            enabled=self.enabled,
            use_optimized_ttl=self.use_optimized_ttl,
        )

    def _generate_cache_key(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate cache key for policy decision.

        Format: policy:decision:{user_id}:{action}:{resource}:{context_hash}

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            context: Additional context (optional)

        Returns:
            Cache key string
        """
        # Generate hash of context for consistent key generation
        context_hash = "none"
        if context:
            # Sort keys for consistent hashing
            context_json = json.dumps(context, sort_keys=True)
            context_hash = hashlib.sha256(context_json.encode()).hexdigest()[:16]

        # Clean up resource string (remove special characters)
        resource_clean = resource.replace(":", "_").replace("/", "_")

        key = f"{self.KEY_PREFIX}:{user_id}:{action}:{resource_clean}:{context_hash}"
        return key

    def _get_ttl_for_sensitivity(self, sensitivity: str | None) -> int:
        """
        Get TTL based on sensitivity level.

        Args:
            sensitivity: Sensitivity level (critical, confidential, internal, public)

        Returns:
            TTL in seconds
        """
        if not self.use_optimized_ttl or not sensitivity:
            return self.ttl_seconds

        return self.OPTIMIZED_TTL.get(sensitivity, self.ttl_seconds)

    async def get(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
        sensitivity: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get cached policy decision.

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            context: Additional context
            sensitivity: Sensitivity level (not used for TTL in get, but kept for API compatibility)

        Returns:
            Cached decision or None if not found/expired
        """
        if not self.enabled:
            return None

        import time

        start_time = time.time()

        try:
            key = self._generate_cache_key(user_id, action, resource, context)

            # Get from Rust cache (sync operation, but fast enough for async context)
            cached_value = await asyncio.to_thread(self.cache.get, key)

            latency_ms = (time.time() - start_time) * 1000

            if cached_value:
                # Deserialize JSON
                decision = json.loads(cached_value)

                self.metrics.hits += 1
                self.metrics.total_requests += 1

                # Update running average latency
                self.metrics.cache_latency_ms = (
                    (self.metrics.cache_latency_ms * (self.metrics.hits - 1)) + latency_ms
                ) / self.metrics.hits

                logger.debug(
                    "rust_cache_hit",
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    latency_ms=round(latency_ms, 3),
                )

                return decision

            # Cache miss
            self.metrics.misses += 1
            self.metrics.total_requests += 1

            logger.debug(
                "rust_cache_miss",
                user_id=user_id,
                action=action,
                resource=resource,
                latency_ms=round(latency_ms, 3),
            )

            return None

        except Exception as e:
            logger.warning(
                "rust_cache_get_error",
                error=str(e),
                user_id=user_id,
                action=action,
            )
            return None

    async def set(
        self,
        user_id: str,
        action: str,
        resource: str,
        decision: dict[str, Any],
        context: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        sensitivity: str | None = None,
    ) -> bool:
        """
        Cache a policy decision.

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            decision: Policy decision to cache
            context: Additional context
            ttl_seconds: Custom TTL (uses default if None)
            sensitivity: Sensitivity level for TTL optimization

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_cache_key(user_id, action, resource, context)

            # Serialize decision to JSON
            decision_json = json.dumps(decision)

            # Determine TTL (sensitivity takes precedence over explicit TTL)
            if ttl_seconds is not None:
                ttl = ttl_seconds
            else:
                ttl = self._get_ttl_for_sensitivity(sensitivity)

            # Track if we're at capacity (will trigger eviction)
            current_size = await asyncio.to_thread(self.cache.size)
            if current_size >= self.max_size:
                self.metrics.evictions += 1

            # Set in Rust cache (sync operation)
            await asyncio.to_thread(self.cache.set, key, decision_json, ttl)

            logger.debug(
                "rust_cache_set",
                user_id=user_id,
                action=action,
                resource=resource,
                ttl_seconds=ttl,
            )

            return True

        except Exception as e:
            logger.warning(
                "rust_cache_set_error",
                error=str(e),
                user_id=user_id,
                action=action,
            )
            return False

    async def delete(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Delete a cached policy decision.

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            context: Additional context

        Returns:
            True if key existed and was deleted
        """
        try:
            key = self._generate_cache_key(user_id, action, resource, context)
            deleted = await asyncio.to_thread(self.cache.delete, key)

            logger.debug(
                "rust_cache_delete",
                user_id=user_id,
                action=action,
                resource=resource,
                deleted=deleted,
            )

            return deleted

        except Exception as e:
            logger.warning(
                "rust_cache_delete_error",
                error=str(e),
                user_id=user_id,
                action=action,
            )
            return False

    async def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if successful
        """
        try:
            await asyncio.to_thread(self.cache.clear)
            logger.warning("rust_cache_cleared")
            return True

        except Exception as e:
            logger.error("rust_cache_clear_error", error=str(e))
            return False

    async def size(self) -> int:
        """
        Get current cache size.

        Returns:
            Number of entries in cache
        """
        try:
            return await asyncio.to_thread(self.cache.size)
        except Exception as e:
            logger.warning("rust_cache_size_error", error=str(e))
            return 0

    async def cleanup_expired(self) -> int:
        """
        Manually trigger cleanup of expired entries.

        Returns:
            Number of entries removed
        """
        try:
            removed = await asyncio.to_thread(self.cache.cleanup_expired)
            logger.debug("rust_cache_cleanup", removed=removed)
            return removed

        except Exception as e:
            logger.warning("rust_cache_cleanup_error", error=str(e))
            return 0

    def get_metrics(self) -> dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary with cache metrics
        """
        return self.metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset cache metrics to zero."""
        self.metrics = CacheMetrics()
        logger.info("rust_cache_metrics_reset")

    async def health_check(self) -> bool:
        """
        Check cache health.

        Returns:
            True if cache is operational
        """
        try:
            # Test basic operations
            test_key = "_health_check_"
            test_value = {"status": "ok"}

            await self.set("_system_", "health_check", test_key, test_value, None, 1)
            result = await self.get("_system_", "health_check", test_key, None)
            await self.delete("_system_", "health_check", test_key, None)

            return result == test_value

        except Exception as e:
            logger.error("rust_cache_health_check_failed", error=str(e))
            return False


# Global cache instance
_cache_instance: RustPolicyCache | None = None


def get_rust_policy_cache(
    max_size: int | None = None,
    ttl_seconds: int | None = None,
    enabled: bool = True,
) -> RustPolicyCache:
    """
    Get or create global Rust policy cache instance.

    Args:
        max_size: Maximum cache size
        ttl_seconds: Cache TTL in seconds
        enabled: Whether caching is enabled

    Returns:
        RustPolicyCache instance

    Raises:
        RuntimeError: If Rust extensions are not available
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = RustPolicyCache(
            max_size=max_size,
            ttl_seconds=ttl_seconds,
            enabled=enabled,
        )

    return _cache_instance


def is_rust_cache_available() -> bool:
    """
    Check if Rust cache extensions are available.

    Returns:
        True if Rust cache can be used
    """
    return RUST_AVAILABLE
