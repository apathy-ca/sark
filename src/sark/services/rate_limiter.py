"""Rate limiting service using Redis."""

import logging
import time
from dataclasses import dataclass
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit information for a request."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: int | None = None  # Seconds until reset (if limited)


class RateLimiter:
    """Redis-backed rate limiter using sliding window algorithm.

    Tracks request counts per identifier (API key, user ID, IP address)
    within a configurable time window.

    Attributes:
        redis: Redis client instance
        default_limit: Default request limit per window
        window_seconds: Time window in seconds
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        default_limit: int = 1000,
        window_seconds: int = 3600,
    ):
        """Initialize rate limiter.

        Args:
            redis_client: Redis client instance
            default_limit: Default number of requests allowed per window
            window_seconds: Time window in seconds (default: 1 hour)
        """
        self.redis = redis_client
        self.default_limit = default_limit
        self.window_seconds = window_seconds

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int | None = None,
    ) -> RateLimitInfo:
        """Check if request is within rate limit.

        Uses sliding window algorithm with Redis sorted sets.
        Each request is stored with timestamp as score.

        Args:
            identifier: Unique identifier (e.g., "api_key:abc123", "user:uuid", "ip:1.2.3.4")
            limit: Custom limit for this identifier (uses default if None)

        Returns:
            RateLimitInfo with rate limit status and metadata
        """
        limit = limit or self.default_limit
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Redis key for this identifier
        key = f"rate_limit:{identifier}"

        try:
            # Start pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request with timestamp as score
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiry on the key (cleanup)
            pipe.expire(key, self.window_seconds + 60)

            # Execute pipeline
            results = await pipe.execute()

            # Get count (before adding current request)
            current_count = results[1]

            # Calculate remaining and reset time
            allowed = current_count < limit
            remaining = max(0, limit - current_count - (1 if allowed else 0))
            reset_at = int(current_time + self.window_seconds)

            # If limited, calculate retry_after
            retry_after = None
            if not allowed:
                # Get oldest entry timestamp
                oldest_entries = await self.redis.zrange(key, 0, 0, withscores=True)
                if oldest_entries:
                    oldest_timestamp = oldest_entries[0][1]
                    retry_after = int(oldest_timestamp + self.window_seconds - current_time)
                    retry_after = max(1, retry_after)  # At least 1 second

            return RateLimitInfo(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        except Exception as e:
            logger.error(f"Rate limiter error for {identifier}: {e}", exc_info=True)
            # Fail open - allow request if Redis is down
            return RateLimitInfo(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=int(current_time + self.window_seconds),
            )

    async def reset_limit(self, identifier: str) -> bool:
        """Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier to reset

        Returns:
            True if reset successful, False otherwise
        """
        try:
            key = f"rate_limit:{identifier}"
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit for {identifier}: {e}")
            return False

    async def get_current_usage(self, identifier: str) -> int:
        """Get current request count for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            Current request count within window
        """
        try:
            current_time = time.time()
            window_start = current_time - self.window_seconds
            key = f"rate_limit:{identifier}"

            # Remove old entries and count
            await self.redis.zremrangebyscore(key, 0, window_start)
            count = await self.redis.zcard(key)
            return count

        except Exception as e:
            logger.error(f"Failed to get usage for {identifier}: {e}")
            return 0

    async def increment_usage(
        self,
        identifier: str,
        amount: int = 1,
    ) -> int:
        """Increment usage counter for an identifier.

        Useful for tracking usage without enforcing limits.

        Args:
            identifier: Unique identifier
            amount: Amount to increment by (default: 1)

        Returns:
            New usage count
        """
        try:
            current_time = time.time()
            key = f"rate_limit:{identifier}"

            # Add multiple entries if amount > 1
            entries = {
                f"{current_time}:{i}": current_time for i in range(amount)
            }

            pipe = self.redis.pipeline()
            pipe.zadd(key, entries)
            pipe.expire(key, self.window_seconds + 60)
            pipe.zcard(key)
            results = await pipe.execute()

            return results[2]  # Return count

        except Exception as e:
            logger.error(f"Failed to increment usage for {identifier}: {e}")
            return 0
