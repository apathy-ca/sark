"""Unit tests for cache cleanup task."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.policy import cache_cleanup


@pytest.fixture
def mock_cache():
    """Mock cache for testing."""
    cache = MagicMock()
    cache.cleanup_expired = AsyncMock(return_value=5)
    return cache


@pytest.fixture
def cleanup_task(mock_cache):
    """Create cleanup task for testing."""
    return cache_cleanup.CacheCleanupTask(mock_cache, interval=0.1, enabled=True)


class TestCleanupMetrics:
    """Test CleanupMetrics dataclass."""

    def test_initial_state(self):
        """Test initial metrics state."""
        metrics = cache_cleanup.CleanupMetrics()

        assert metrics.cleanups_run == 0
        assert metrics.total_entries_removed == 0
        assert metrics.last_cleanup_removed == 0
        assert metrics.last_cleanup_duration_ms == 0.0
        assert metrics.errors == 0
        assert metrics.avg_entries_per_cleanup == 0.0

    def test_avg_entries_per_cleanup(self):
        """Test average calculation."""
        metrics = cache_cleanup.CleanupMetrics(
            cleanups_run=10, total_entries_removed=50
        )

        assert metrics.avg_entries_per_cleanup == 5.0

    def test_avg_entries_per_cleanup_zero_cleanups(self):
        """Test average when no cleanups have run."""
        metrics = cache_cleanup.CleanupMetrics()

        assert metrics.avg_entries_per_cleanup == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = cache_cleanup.CleanupMetrics(
            cleanups_run=5,
            total_entries_removed=25,
            last_cleanup_removed=3,
            last_cleanup_duration_ms=1.234,
            errors=1,
        )

        result = metrics.to_dict()

        assert result["cleanups_run"] == 5
        assert result["total_entries_removed"] == 25
        assert result["last_cleanup_removed"] == 3
        assert result["last_cleanup_duration_ms"] == 1.23  # Rounded
        assert result["avg_entries_per_cleanup"] == 5.0
        assert result["errors"] == 1


class TestCacheCleanupTaskInitialization:
    """Test cleanup task initialization."""

    def test_default_initialization(self, mock_cache):
        """Test initialization with default parameters."""
        task = cache_cleanup.CacheCleanupTask(mock_cache)

        assert task.cache is mock_cache
        assert task.interval == 60  # Default
        assert task.enabled is True
        assert task.running is False
        assert task.metrics.cleanups_run == 0

    def test_custom_initialization(self, mock_cache):
        """Test initialization with custom parameters."""
        task = cache_cleanup.CacheCleanupTask(
            mock_cache, interval=30, enabled=False
        )

        assert task.interval == 30
        assert task.enabled is False


@pytest.mark.asyncio
class TestCleanupTaskLifecycle:
    """Test cleanup task start/stop lifecycle."""

    async def test_start_task(self, cleanup_task, mock_cache):
        """Test starting cleanup task."""
        await cleanup_task.start()

        assert cleanup_task.running is True
        assert cleanup_task._task is not None

        # Clean up
        await cleanup_task.stop()

    async def test_start_when_disabled(self, mock_cache):
        """Test that disabled task doesn't start."""
        task = cache_cleanup.CacheCleanupTask(mock_cache, enabled=False)

        await task.start()

        assert task.running is False
        assert task._task is None

    async def test_start_when_already_running(self, cleanup_task):
        """Test starting task when already running."""
        await cleanup_task.start()
        assert cleanup_task.running is True

        # Try to start again
        await cleanup_task.start()

        # Should still be running with same task
        assert cleanup_task.running is True

        # Clean up
        await cleanup_task.stop()

    async def test_stop_task(self, cleanup_task):
        """Test stopping cleanup task."""
        await cleanup_task.start()
        assert cleanup_task.running is True

        await cleanup_task.stop()

        assert cleanup_task.running is False

    async def test_stop_when_not_running(self, cleanup_task):
        """Test stopping task when not running."""
        assert cleanup_task.running is False

        # Should not raise error
        await cleanup_task.stop()

        assert cleanup_task.running is False

    async def test_stop_with_timeout(self, mock_cache):
        """Test stop timeout handling."""
        task = cache_cleanup.CacheCleanupTask(mock_cache, interval=100)

        await task.start()

        # Mock the task to not complete quickly

        # Stop should timeout and cancel
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            await task.stop()

        assert task.running is False


@pytest.mark.asyncio
class TestCleanupExecution:
    """Test cleanup execution."""

    async def test_perform_cleanup_success(self, cleanup_task, mock_cache):
        """Test successful cleanup execution."""
        mock_cache.cleanup_expired.return_value = 10

        await cleanup_task._perform_cleanup()

        mock_cache.cleanup_expired.assert_called_once()
        assert cleanup_task.metrics.cleanups_run == 1
        assert cleanup_task.metrics.total_entries_removed == 10
        assert cleanup_task.metrics.last_cleanup_removed == 10
        assert cleanup_task.metrics.last_cleanup_duration_ms > 0

    async def test_perform_cleanup_no_entries(self, cleanup_task, mock_cache):
        """Test cleanup when no entries removed."""
        mock_cache.cleanup_expired.return_value = 0

        await cleanup_task._perform_cleanup()

        assert cleanup_task.metrics.cleanups_run == 1
        assert cleanup_task.metrics.total_entries_removed == 0
        assert cleanup_task.metrics.last_cleanup_removed == 0

    async def test_perform_cleanup_error(self, cleanup_task, mock_cache):
        """Test cleanup error handling."""
        mock_cache.cleanup_expired.side_effect = Exception("Test error")

        # Should not raise exception
        await cleanup_task._perform_cleanup()

        assert cleanup_task.metrics.errors == 1

    async def test_manual_trigger_cleanup(self, cleanup_task, mock_cache):
        """Test manually triggering cleanup."""
        mock_cache.cleanup_expired.return_value = 7

        removed = await cleanup_task.trigger_cleanup()

        assert removed == 7
        assert cleanup_task.metrics.last_cleanup_removed == 7
        mock_cache.cleanup_expired.assert_called_once()

    async def test_cleanup_loop_runs_periodically(self, mock_cache):
        """Test that cleanup loop runs multiple times."""
        task = cache_cleanup.CacheCleanupTask(mock_cache, interval=0.05)
        mock_cache.cleanup_expired.return_value = 3

        await task.start()

        # Wait for multiple cleanup cycles
        await asyncio.sleep(0.2)

        await task.stop()

        # Should have run at least 2-3 times
        assert task.metrics.cleanups_run >= 2
        assert mock_cache.cleanup_expired.call_count >= 2

    async def test_cleanup_loop_handles_errors(self, mock_cache):
        """Test cleanup loop continues after errors."""
        task = cache_cleanup.CacheCleanupTask(mock_cache, interval=0.05)

        # First call fails, subsequent calls succeed
        mock_cache.cleanup_expired.side_effect = [
            Exception("Error"),
            5,
            5,
        ]

        await task.start()
        await asyncio.sleep(0.2)
        await task.stop()

        # Should have errors but also successful cleanups
        assert task.metrics.errors > 0
        assert task.metrics.cleanups_run > 1

    async def test_cleanup_loop_cancellation(self, cleanup_task):
        """Test cleanup loop handles cancellation."""
        await cleanup_task.start()

        # Cancel the task
        cleanup_task._task.cancel()

        # Wait a bit for cancellation
        await asyncio.sleep(0.1)

        # Should handle cancellation gracefully
        assert cleanup_task._task.done()


@pytest.mark.asyncio
class TestMetricsAndMonitoring:
    """Test metrics and monitoring functionality."""

    async def test_get_metrics(self, cleanup_task):
        """Test getting metrics."""
        # Perform some cleanups
        await cleanup_task._perform_cleanup()
        await cleanup_task._perform_cleanup()

        metrics = cleanup_task.get_metrics()

        assert metrics["cleanups_run"] == 2
        assert metrics["total_entries_removed"] == 10  # 5 + 5
        assert metrics["avg_entries_per_cleanup"] == 5.0

    async def test_reset_metrics(self, cleanup_task):
        """Test resetting metrics."""
        # Perform cleanup
        await cleanup_task._perform_cleanup()
        assert cleanup_task.metrics.cleanups_run == 1

        # Reset
        cleanup_task.reset_metrics()

        assert cleanup_task.metrics.cleanups_run == 0
        assert cleanup_task.metrics.total_entries_removed == 0

    async def test_health_check_running(self, cleanup_task):
        """Test health check when task is running."""
        await cleanup_task.start()

        is_healthy = await cleanup_task.health_check()

        assert is_healthy is True

        await cleanup_task.stop()

    async def test_health_check_not_running(self, cleanup_task):
        """Test health check when task is not running."""
        assert cleanup_task.running is False

        is_healthy = await cleanup_task.health_check()

        assert is_healthy is False

    async def test_health_check_disabled(self, mock_cache):
        """Test health check when task is disabled."""
        task = cache_cleanup.CacheCleanupTask(mock_cache, enabled=False)

        is_healthy = await task.health_check()

        # Disabled is a valid state
        assert is_healthy is True

    async def test_health_check_task_finished(self, cleanup_task):
        """Test health check when task finished unexpectedly."""
        await cleanup_task.start()

        # Simulate task finishing
        cleanup_task.running = True
        cleanup_task._task.cancel()
        await asyncio.sleep(0.05)

        is_healthy = await cleanup_task.health_check()

        assert is_healthy is False

        # Clean up properly
        cleanup_task.running = False


@pytest.mark.asyncio
class TestGlobalInstance:
    """Test global cleanup task management."""

    async def test_start_cache_cleanup(self, mock_cache):
        """Test starting global cleanup task."""
        # Reset global state
        cache_cleanup._cleanup_task = None

        task = await cache_cleanup.start_cache_cleanup(
            mock_cache, interval=60, enabled=True
        )

        assert task is not None
        assert task.running is True
        assert cache_cleanup._cleanup_task is task

        # Clean up
        await cache_cleanup.stop_cache_cleanup()

    async def test_start_cache_cleanup_already_started(self, mock_cache):
        """Test starting global cleanup when already started."""
        cache_cleanup._cleanup_task = None

        task1 = await cache_cleanup.start_cache_cleanup(mock_cache)
        task2 = await cache_cleanup.start_cache_cleanup(mock_cache)

        # Should return same instance
        assert task1 is task2

        await cache_cleanup.stop_cache_cleanup()

    async def test_stop_cache_cleanup(self, mock_cache):
        """Test stopping global cleanup task."""
        cache_cleanup._cleanup_task = None

        await cache_cleanup.start_cache_cleanup(mock_cache)
        assert cache_cleanup._cleanup_task is not None

        await cache_cleanup.stop_cache_cleanup()

        assert cache_cleanup._cleanup_task is None

    async def test_stop_cache_cleanup_not_started(self):
        """Test stopping when not started."""
        cache_cleanup._cleanup_task = None

        # Should not raise error
        await cache_cleanup.stop_cache_cleanup()

        assert cache_cleanup._cleanup_task is None

    async def test_get_cleanup_task(self, mock_cache):
        """Test getting global cleanup task."""
        cache_cleanup._cleanup_task = None

        # Initially None
        task = cache_cleanup.get_cleanup_task()
        assert task is None

        # After starting
        await cache_cleanup.start_cache_cleanup(mock_cache)
        task = cache_cleanup.get_cleanup_task()
        assert task is not None

        await cache_cleanup.stop_cache_cleanup()


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    async def test_full_lifecycle(self, mock_cache):
        """Test complete lifecycle: start, cleanup, metrics, stop."""
        task = cache_cleanup.CacheCleanupTask(mock_cache, interval=0.05)

        # Start
        await task.start()
        assert task.running is True

        # Wait for cleanups
        await asyncio.sleep(0.15)

        # Check metrics
        metrics = task.get_metrics()
        assert metrics["cleanups_run"] >= 2

        # Manual trigger
        removed = await task.trigger_cleanup()
        assert removed == 5

        # Health check
        is_healthy = await task.health_check()
        assert is_healthy is True

        # Stop
        await task.stop()
        assert task.running is False

    async def test_concurrent_operations(self, mock_cache):
        """Test concurrent manual triggers."""
        task = cache_cleanup.CacheCleanupTask(mock_cache, interval=1.0)

        # Trigger multiple cleanups concurrently
        results = await asyncio.gather(
            task.trigger_cleanup(),
            task.trigger_cleanup(),
            task.trigger_cleanup(),
        )

        # All should complete successfully
        assert len(results) == 3
        assert task.metrics.cleanups_run == 3
