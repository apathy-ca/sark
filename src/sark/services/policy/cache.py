"""Policy Decision Cache Service.

Implements Redis-based caching for OPA policy decisions to improve performance
and reduce load on the OPA server.

Features:
- Sensitivity-based TTL tuning
- Stale-while-revalidate pattern for critical tools
- Redis pipelining for batch operations
- Cache preloading support
- Comprehensive performance metrics
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any, ClassVar

import valkey.asyncio as redis
import structlog

from sark.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    hits: int = 0
    misses: int = 0
    stale_hits: int = 0  # Stale-while-revalidate hits
    revalidations: int = 0  # Background revalidations
    batch_operations: int = 0  # Batch cache operations
    total_requests: int = 0
    cache_latency_ms: float = 0.0
    opa_latency_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100

    @property
    def effective_hit_rate(self) -> float:
        """Calculate effective hit rate including stale hits."""
        if self.total_requests == 0:
            return 0.0
        return ((self.hits + self.stale_hits) / self.total_requests) * 100

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage."""
        return 100.0 - self.hit_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "stale_hits": self.stale_hits,
            "revalidations": self.revalidations,
            "batch_operations": self.batch_operations,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 2),
            "effective_hit_rate": round(self.effective_hit_rate, 2),
            "miss_rate": round(self.miss_rate, 2),
            "avg_cache_latency_ms": round(self.cache_latency_ms, 2),
            "avg_opa_latency_ms": round(self.opa_latency_ms, 2),
        }


class PolicyCache:
    """Redis-based cache for OPA policy decisions with advanced optimization features."""

    # Cache key prefix
    KEY_PREFIX = "policy:decision"

    # Default TTL (5 minutes)
    DEFAULT_TTL_SECONDS = 300

    # Optimized TTL settings based on performance analysis
    OPTIMIZED_TTL: ClassVar[dict[str, int]] = {
        "critical": 60,  # Increased from 30s to reduce revalidation overhead
        "confidential": 120,  # Increased from 60s
        "internal": 180,  # Same as medium
        "public": 300,  # 5 minutes
        "default": 120,  # Default 2 minutes
    }

    # Stale-while-revalidate threshold (30% of TTL)
    STALE_THRESHOLD_RATIO = 0.3

    # Metrics key
    METRICS_KEY = "policy:cache:metrics"

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
        enabled: bool = True,
        stale_while_revalidate: bool = True,
        use_optimized_ttl: bool = True,
    ) -> None:
        """
        Initialize policy cache with optimization features.

        Args:
            redis_client: Redis client instance (creates new if None)
            ttl_seconds: Time-to-live for cache entries (default: 300s)
            enabled: Whether caching is enabled (default: True)
            stale_while_revalidate: Enable stale-while-revalidate pattern (default: True)
            use_optimized_ttl: Use optimized TTL settings (default: True)
        """
        self.ttl_seconds = ttl_seconds or self.DEFAULT_TTL_SECONDS
        self.enabled = enabled
        self.stale_while_revalidate = stale_while_revalidate
        self.use_optimized_ttl = use_optimized_ttl
        self.metrics = CacheMetrics()

        # Revalidation callback (set by OPA client)
        self.revalidate_callback: Callable[[str, str, str, dict], Awaitable[dict]] | None = None

        # Initialize Redis client
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
                max_connections=settings.redis_pool_size,
            )

        logger.info(
            "policy_cache_initialized",
            ttl_seconds=self.ttl_seconds,
            enabled=self.enabled,
            stale_while_revalidate=self.stale_while_revalidate,
            use_optimized_ttl=self.use_optimized_ttl,
            redis_host=settings.redis_host,
            redis_port=settings.redis_port,
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

    async def get(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
        sensitivity: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get cached policy decision with stale-while-revalidate support.

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            context: Additional context
            sensitivity: Sensitivity level for determining revalidation threshold

        Returns:
            Cached decision or None if not found/expired
        """
        if not self.enabled:
            return None

        start_time = time.time()

        try:
            key = self._generate_cache_key(user_id, action, resource, context)

            # Use Redis pipeline to get value and TTL in single round-trip
            pipe = self.redis.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            cached_value, ttl_remaining = await pipe.execute()

            latency_ms = (time.time() - start_time) * 1000

            if cached_value:
                decision = json.loads(cached_value)

                # Check if we should trigger background revalidation
                if (
                    self.stale_while_revalidate
                    and self.revalidate_callback
                    and sensitivity in ["critical", "confidential"]
                    and ttl_remaining > 0
                ):
                    # Get full TTL for this sensitivity
                    full_ttl = self.OPTIMIZED_TTL.get(sensitivity, self.ttl_seconds)
                    stale_threshold = full_ttl * self.STALE_THRESHOLD_RATIO

                    # If TTL is in the last 30%, trigger background revalidation
                    if ttl_remaining < stale_threshold:
                        # Serve stale cache, revalidate in background
                        self.metrics.stale_hits += 1
                        asyncio.create_task(
                            self._background_revalidate(user_id, action, resource, context)
                        )

                        logger.debug(
                            "cache_stale_hit",
                            user_id=user_id,
                            action=action,
                            resource=resource,
                            ttl_remaining=ttl_remaining,
                            latency_ms=round(latency_ms, 2),
                        )
                    else:
                        # Fresh cache hit
                        self.metrics.hits += 1

                        logger.debug(
                            "cache_hit",
                            user_id=user_id,
                            action=action,
                            resource=resource,
                            latency_ms=round(latency_ms, 2),
                        )
                else:
                    # Standard cache hit (no revalidation)
                    self.metrics.hits += 1

                    logger.debug(
                        "cache_hit",
                        user_id=user_id,
                        action=action,
                        resource=resource,
                        latency_ms=round(latency_ms, 2),
                    )

                self.metrics.total_requests += 1
                self.metrics.cache_latency_ms = (
                    (
                        self.metrics.cache_latency_ms
                        * (self.metrics.hits + self.metrics.stale_hits - 1)
                    )
                    + latency_ms
                ) / (self.metrics.hits + self.metrics.stale_hits)

                return decision

            # Cache miss
            self.metrics.misses += 1
            self.metrics.total_requests += 1

            logger.debug(
                "cache_miss",
                user_id=user_id,
                action=action,
                resource=resource,
                latency_ms=round(latency_ms, 2),
            )

            return None

        except Exception as e:
            logger.warning(
                "cache_get_error",
                error=str(e),
                user_id=user_id,
                action=action,
            )
            # On error, return None (cache miss)
            return None

    async def _background_revalidate(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Background task to revalidate stale cache entries.

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            context: Additional context
        """
        if not self.revalidate_callback:
            return

        try:
            # Call revalidation callback (OPA evaluation)
            new_decision = await self.revalidate_callback(user_id, action, resource, context)

            # Update cache with fresh decision
            if new_decision:
                key = self._generate_cache_key(user_id, action, resource, context)
                decision_json = json.dumps(new_decision)
                await self.redis.setex(key, self.ttl_seconds, decision_json)

                self.metrics.revalidations += 1

                logger.debug(
                    "cache_revalidated",
                    user_id=user_id,
                    action=action,
                    resource=resource,
                )

        except Exception as e:
            logger.warning(
                "cache_revalidation_error",
                error=str(e),
                user_id=user_id,
                action=action,
            )

    async def set(
        self,
        user_id: str,
        action: str,
        resource: str,
        decision: dict[str, Any],
        context: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
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

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_cache_key(user_id, action, resource, context)
            decision_json = json.dumps(decision)

            ttl = ttl_seconds or self.ttl_seconds

            await self.redis.setex(key, ttl, decision_json)

            logger.debug(
                "cache_set",
                user_id=user_id,
                action=action,
                resource=resource,
                ttl_seconds=ttl,
            )

            return True

        except Exception as e:
            logger.warning(
                "cache_set_error",
                error=str(e),
                user_id=user_id,
                action=action,
            )
            return False

    async def get_batch(
        self,
        requests: list[tuple[str, str, str, dict[str, Any] | None]],
    ) -> list[dict[str, Any] | None]:
        """
        Get multiple cached policy decisions in a single round-trip using Redis pipelining.

        Args:
            requests: List of (user_id, action, resource, context) tuples

        Returns:
            List of cached decisions (None for cache misses) in same order as requests
        """
        if not self.enabled or not requests:
            return [None] * len(requests)

        start_time = time.time()

        try:
            # Generate all cache keys
            keys = [
                self._generate_cache_key(user_id, action, resource, context)
                for user_id, action, resource, context in requests
            ]

            # Use pipeline to get all values in single round-trip
            pipe = self.redis.pipeline()
            for key in keys:
                pipe.get(key)

            cached_values = await pipe.execute()

            latency_ms = (time.time() - start_time) * 1000

            # Parse results
            results = []
            hits = 0
            misses = 0

            for cached_value in cached_values:
                if cached_value:
                    results.append(json.loads(cached_value))
                    hits += 1
                else:
                    results.append(None)
                    misses += 1

            # Update metrics
            self.metrics.hits += hits
            self.metrics.misses += misses
            self.metrics.total_requests += len(requests)
            self.metrics.batch_operations += 1

            logger.debug(
                "cache_batch_get",
                requests=len(requests),
                hits=hits,
                misses=misses,
                hit_rate=round((hits / len(requests)) * 100, 2),
                latency_ms=round(latency_ms, 2),
            )

            return results

        except Exception as e:
            logger.warning("cache_batch_get_error", error=str(e))
            return [None] * len(requests)

    async def set_batch(
        self,
        entries: list[tuple[str, str, str, dict[str, Any], dict[str, Any] | None, int | None]],
    ) -> int:
        """
        Set multiple cached policy decisions in a single round-trip using Redis pipelining.

        Args:
            entries: List of (user_id, action, resource, decision, context, ttl_seconds) tuples

        Returns:
            Number of entries successfully cached
        """
        if not self.enabled or not entries:
            return 0

        try:
            # Use pipeline to set all values
            pipe = self.redis.pipeline()

            for user_id, action, resource, decision, context, ttl_seconds in entries:
                key = self._generate_cache_key(user_id, action, resource, context)
                decision_json = json.dumps(decision)
                ttl = ttl_seconds or self.ttl_seconds
                pipe.setex(key, ttl, decision_json)

            results = await pipe.execute()

            # Count successes (setex returns True on success)
            success_count = sum(1 for r in results if r)

            self.metrics.batch_operations += 1

            logger.debug(
                "cache_batch_set",
                entries=len(entries),
                successful=success_count,
            )

            return success_count

        except Exception as e:
            logger.warning("cache_batch_set_error", error=str(e))
            return 0

    async def invalidate(
        self,
        user_id: str | None = None,
        action: str | None = None,
        resource: str | None = None,
    ) -> int:
        """
        Invalidate cached decisions.

        Args:
            user_id: Invalidate for specific user (or all if None)
            action: Invalidate for specific action (or all if None)
            resource: Invalidate for specific resource (or all if None)

        Returns:
            Number of keys invalidated
        """
        try:
            # Build pattern for key matching
            if user_id and action and resource:
                # Specific invalidation
                pattern = f"{self.KEY_PREFIX}:{user_id}:{action}:{resource}:*"
            elif user_id and action:
                # User + action
                pattern = f"{self.KEY_PREFIX}:{user_id}:{action}:*"
            elif user_id:
                # All for user
                pattern = f"{self.KEY_PREFIX}:{user_id}:*"
            else:
                # All cache entries
                pattern = f"{self.KEY_PREFIX}:*"

            # Find matching keys
            keys = []
            async for key in self.redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            # Delete keys
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(
                    "cache_invalidated",
                    pattern=pattern,
                    keys_deleted=deleted,
                )
                return deleted

            return 0

        except Exception as e:
            logger.warning("cache_invalidate_error", error=str(e), pattern=pattern)
            return 0

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "policy:decision:user-123:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(
                    "cache_invalidated_by_pattern",
                    pattern=pattern,
                    keys_deleted=deleted,
                )
                return deleted

            return 0

        except Exception as e:
            logger.warning("cache_invalidate_pattern_error", error=str(e))
            return 0

    async def clear_all(self) -> bool:
        """
        Clear all policy cache entries.

        WARNING: This clears ALL policy cache entries.

        Returns:
            True if successful
        """
        try:
            deleted = await self.invalidate()
            logger.warning("cache_cleared_all", keys_deleted=deleted)
            return True

        except Exception as e:
            logger.error("cache_clear_all_error", error=str(e))
            return False

    def get_metrics(self) -> dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary with cache metrics
        """
        return self.metrics.to_dict()

    async def get_cache_size(self) -> int:
        """
        Get approximate number of cached policy decisions.

        Returns:
            Number of cache entries
        """
        try:
            count = 0
            async for _ in self.redis.scan_iter(match=f"{self.KEY_PREFIX}:*", count=100):
                count += 1
            return count

        except Exception as e:
            logger.warning("cache_size_error", error=str(e))
            return 0

    def reset_metrics(self) -> None:
        """Reset cache metrics to zero."""
        self.metrics = CacheMetrics()
        logger.info("cache_metrics_reset")

    def record_opa_latency(self, latency_ms: float) -> None:
        """
        Record OPA query latency for metrics.

        Args:
            latency_ms: OPA query latency in milliseconds
        """
        # Calculate running average
        if self.metrics.misses > 0:
            self.metrics.opa_latency_ms = (
                (self.metrics.opa_latency_ms * (self.metrics.misses - 1)) + latency_ms
            ) / self.metrics.misses

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is accessible
        """
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error("cache_health_check_failed", error=str(e))
            return False

    async def preload_cache(
        self,
        preload_data: list[tuple[str, str, str, dict[str, Any], dict[str, Any] | None]],
    ) -> int:
        """
        Preload cache with frequently accessed policy decisions on startup.

        This improves cold-start performance by pre-populating the cache with
        common user-tool combinations.

        Args:
            preload_data: List of (user_id, action, resource, decision, context) tuples

        Returns:
            Number of entries successfully preloaded
        """
        if not self.enabled or not preload_data:
            return 0

        try:
            # Convert to batch set format (add TTL)
            entries = [
                (user_id, action, resource, decision, context, self.ttl_seconds)
                for user_id, action, resource, decision, context in preload_data
            ]

            # Use batch set for efficient preloading
            success_count = await self.set_batch(entries)

            logger.info(
                "cache_preloaded",
                total_entries=len(preload_data),
                successful=success_count,
            )

            return success_count

        except Exception as e:
            logger.warning("cache_preload_error", error=str(e))
            return 0

    def set_revalidate_callback(
        self,
        callback: Callable[[str, str, str, dict], Awaitable[dict]],
    ) -> None:
        """
        Set callback function for cache revalidation.

        Args:
            callback: Async function that takes (user_id, action, resource, context)
                     and returns fresh policy decision
        """
        self.revalidate_callback = callback
        logger.info("cache_revalidate_callback_set")

    async def close(self) -> None:
        """Close Redis connection."""
        try:
            await self.redis.aclose()
            logger.info("cache_connection_closed")
        except Exception as e:
            logger.warning("cache_close_error", error=str(e))


# Global cache instance
_cache_instance: PolicyCache | None = None


def get_policy_cache(
    ttl_seconds: int | None = None,
    enabled: bool = True,
) -> PolicyCache:
    """
    Get or create global policy cache instance.

    Args:
        ttl_seconds: Cache TTL in seconds
        enabled: Whether caching is enabled

    Returns:
        PolicyCache instance
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = PolicyCache(
            ttl_seconds=ttl_seconds,
            enabled=enabled,
        )

    return _cache_instance
