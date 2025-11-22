"""Policy Decision Cache Service.

Implements Redis-based caching for OPA policy decisions to improve performance
and reduce load on the OPA server.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis
import structlog

from sark.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    hits: int = 0
    misses: int = 0
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
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage."""
        return 100.0 - self.hit_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 2),
            "miss_rate": round(self.miss_rate, 2),
            "avg_cache_latency_ms": round(self.cache_latency_ms, 2),
            "avg_opa_latency_ms": round(self.opa_latency_ms, 2),
        }


class PolicyCache:
    """Redis-based cache for OPA policy decisions."""

    # Cache key prefix
    KEY_PREFIX = "policy:decision"

    # Default TTL (5 minutes)
    DEFAULT_TTL_SECONDS = 300

    # Metrics key
    METRICS_KEY = "policy:cache:metrics"

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
        enabled: bool = True,
    ) -> None:
        """
        Initialize policy cache.

        Args:
            redis_client: Redis client instance (creates new if None)
            ttl_seconds: Time-to-live for cache entries (default: 300s)
            enabled: Whether caching is enabled (default: True)
        """
        self.ttl_seconds = ttl_seconds or self.DEFAULT_TTL_SECONDS
        self.enabled = enabled
        self.metrics = CacheMetrics()

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
    ) -> dict[str, Any] | None:
        """
        Get cached policy decision.

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            context: Additional context

        Returns:
            Cached decision or None if not found/expired
        """
        if not self.enabled:
            return None

        start_time = time.time()

        try:
            key = self._generate_cache_key(user_id, action, resource, context)
            cached_value = await self.redis.get(key)

            latency_ms = (time.time() - start_time) * 1000

            if cached_value:
                # Cache hit
                self.metrics.hits += 1
                self.metrics.total_requests += 1
                self.metrics.cache_latency_ms = (
                    (self.metrics.cache_latency_ms * (self.metrics.hits - 1))
                    + latency_ms
                ) / self.metrics.hits

                decision = json.loads(cached_value)

                logger.debug(
                    "cache_hit",
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    latency_ms=round(latency_ms, 2),
                )

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
            async for _ in self.redis.scan_iter(
                match=f"{self.KEY_PREFIX}:*", count=100
            ):
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
                (self.metrics.opa_latency_ms * (self.metrics.misses - 1))
                + latency_ms
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
