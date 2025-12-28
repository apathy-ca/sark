"""Background cleanup task for Rust policy cache.

Periodically removes expired cache entries to prevent memory buildup
and maintain cache health.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class CleanupMetrics:
    """Metrics for cache cleanup operations."""

    cleanups_run: int = 0
    total_entries_removed: int = 0
    last_cleanup_removed: int = 0
    last_cleanup_duration_ms: float = 0.0
    errors: int = 0

    @property
    def avg_entries_per_cleanup(self) -> float:
        """Calculate average entries removed per cleanup."""
        if self.cleanups_run == 0:
            return 0.0
        return self.total_entries_removed / self.cleanups_run

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "cleanups_run": self.cleanups_run,
            "total_entries_removed": self.total_entries_removed,
            "last_cleanup_removed": self.last_cleanup_removed,
            "last_cleanup_duration_ms": round(self.last_cleanup_duration_ms, 2),
            "avg_entries_per_cleanup": round(self.avg_entries_per_cleanup, 2),
            "errors": self.errors,
        }


class CacheCleanupTask:
    """Background task for periodic cache cleanup.

    This task runs in the background and periodically calls the cache's
    cleanup_expired() method to remove expired entries and free memory.

    Example:
        cache = get_rust_policy_cache()
        cleanup_task = CacheCleanupTask(cache, interval=60)
        await cleanup_task.start()

        # Later...
        await cleanup_task.stop()
    """

    def __init__(
        self,
        cache: Any,  # RustPolicyCache, avoiding circular import
        interval: int = 60,
        enabled: bool = True,
    ) -> None:
        """
        Initialize cache cleanup task.

        Args:
            cache: RustPolicyCache instance to clean
            interval: Cleanup interval in seconds (default: 60)
            enabled: Whether cleanup is enabled (default: True)
        """
        self.cache = cache
        self.interval = interval
        self.enabled = enabled
        self.running = False
        self.metrics = CleanupMetrics()
        self._task: asyncio.Task | None = None

        logger.info(
            "cache_cleanup_task_initialized",
            interval_seconds=interval,
            enabled=enabled,
        )

    async def start(self) -> None:
        """
        Start the background cleanup task.

        This method spawns an asyncio task that runs in the background.
        The task will continue until stop() is called.
        """
        if not self.enabled:
            logger.info("cache_cleanup_disabled")
            return

        if self.running:
            logger.warning("cache_cleanup_already_running")
            return

        self.running = True
        self._task = asyncio.create_task(self._cleanup_loop())

        logger.info("cache_cleanup_started", interval_seconds=self.interval)

    async def stop(self) -> None:
        """
        Stop the background cleanup task gracefully.

        Waits for the current cleanup cycle to complete before stopping.
        """
        if not self.running:
            logger.debug("cache_cleanup_not_running")
            return

        logger.info("cache_cleanup_stopping")
        self.running = False

        # Wait for cleanup task to finish
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("cache_cleanup_stop_timeout")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error("cache_cleanup_stop_error", error=str(e))

        logger.info("cache_cleanup_stopped")

    async def _cleanup_loop(self) -> None:
        """
        Main cleanup loop that runs periodically.

        This method runs until running is set to False.
        """
        while self.running:
            try:
                # Wait for interval
                await asyncio.sleep(self.interval)

                if not self.running:
                    break

                # Perform cleanup
                await self._perform_cleanup()

            except asyncio.CancelledError:
                logger.info("cache_cleanup_cancelled")
                break
            except Exception as e:
                logger.error("cache_cleanup_loop_error", error=str(e))
                self.metrics.errors += 1
                # Continue running despite errors
                await asyncio.sleep(1)  # Brief pause before retrying

    async def _perform_cleanup(self) -> None:
        """
        Perform a single cleanup operation.

        Calls the cache's cleanup_expired() method and updates metrics.
        """
        import time

        start_time = time.time()

        try:
            # Call cache cleanup
            removed = await self.cache.cleanup_expired()

            # Update metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.cleanups_run += 1
            self.metrics.total_entries_removed += removed
            self.metrics.last_cleanup_removed = removed
            self.metrics.last_cleanup_duration_ms = duration_ms

            if removed > 0:
                logger.info(
                    "cache_cleanup_completed",
                    entries_removed=removed,
                    duration_ms=round(duration_ms, 2),
                    total_cleanups=self.metrics.cleanups_run,
                    total_removed=self.metrics.total_entries_removed,
                )
            else:
                logger.debug(
                    "cache_cleanup_completed",
                    entries_removed=0,
                    duration_ms=round(duration_ms, 2),
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.errors += 1
            logger.error(
                "cache_cleanup_error",
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )

    async def trigger_cleanup(self) -> int:
        """
        Manually trigger a cleanup operation immediately.

        This does not affect the scheduled cleanup cycle.

        Returns:
            Number of entries removed
        """
        logger.debug("cache_cleanup_manual_trigger")
        await self._perform_cleanup()
        return self.metrics.last_cleanup_removed

    def get_metrics(self) -> dict[str, Any]:
        """
        Get cleanup metrics.

        Returns:
            Dictionary with cleanup statistics
        """
        return self.metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset cleanup metrics to zero."""
        self.metrics = CleanupMetrics()
        logger.info("cache_cleanup_metrics_reset")

    async def health_check(self) -> bool:
        """
        Check if cleanup task is healthy.

        Returns:
            True if task is running properly
        """
        if not self.enabled:
            return True  # Disabled is a valid state

        if not self.running:
            return False  # Should be running but isn't

        if self._task and self._task.done():
            # Task finished unexpectedly
            return False

        return True


# Global cleanup task instance
_cleanup_task: CacheCleanupTask | None = None


async def start_cache_cleanup(
    cache: Any,
    interval: int = 60,
    enabled: bool = True,
) -> CacheCleanupTask:
    """
    Start global cache cleanup task.

    Args:
        cache: RustPolicyCache instance
        interval: Cleanup interval in seconds
        enabled: Whether cleanup is enabled

    Returns:
        CacheCleanupTask instance
    """
    global _cleanup_task

    if _cleanup_task is not None:
        logger.warning("cache_cleanup_already_started")
        return _cleanup_task

    _cleanup_task = CacheCleanupTask(cache, interval, enabled)
    await _cleanup_task.start()

    return _cleanup_task


async def stop_cache_cleanup() -> None:
    """Stop global cache cleanup task."""
    global _cleanup_task

    if _cleanup_task is None:
        logger.debug("cache_cleanup_not_started")
        return

    await _cleanup_task.stop()
    _cleanup_task = None


def get_cleanup_task() -> CacheCleanupTask | None:
    """
    Get global cleanup task instance.

    Returns:
        CacheCleanupTask instance or None if not started
    """
    return _cleanup_task
