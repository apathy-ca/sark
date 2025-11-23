"""Tests for rate limiter service."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.rate_limiter import RateLimiter

# Helper Functions


def create_pipeline_mock(execute_return=None):
    """Create a properly configured pipeline mock.

    Args:
        execute_return: Return value for execute() method

    Returns:
        MagicMock configured as a Redis pipeline
    """
    mock_pipeline = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=execute_return or [None, 0, None, None])
    mock_pipeline.zremrangebyscore = MagicMock(return_value=mock_pipeline)
    mock_pipeline.zcard = MagicMock(return_value=mock_pipeline)
    mock_pipeline.zadd = MagicMock(return_value=mock_pipeline)
    mock_pipeline.expire = MagicMock(return_value=mock_pipeline)
    return mock_pipeline


# Fixtures


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    # Set up default pipeline
    redis.pipeline = MagicMock(return_value=create_pipeline_mock())
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    """Create rate limiter instance."""
    return RateLimiter(
        redis_client=mock_redis,
        default_limit=100,
        window_seconds=3600,
    )


# Test Rate Limit Checking


class TestCheckRateLimit:
    """Test rate limit checking."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when allowed."""
        # Mock pipeline execution with 50 current requests
        mock_redis.pipeline.return_value = create_pipeline_mock([None, 50, None, None])

        result = await rate_limiter.check_rate_limit("test:user123")

        assert result.allowed is True
        assert result.limit == 100
        assert result.remaining == 49  # 100 - 50 - 1
        assert result.retry_after is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limit check when exceeded."""
        # Mock pipeline execution - 100 requests already made
        mock_redis.pipeline.return_value = create_pipeline_mock([None, 100, None, None])

        # Mock oldest entry for retry_after calculation
        current_time = time.time()
        mock_redis.zrange.return_value = [(b"entry", current_time - 3000)]

        result = await rate_limiter.check_rate_limit("test:user123")

        assert result.allowed is False
        assert result.limit == 100
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_custom_limit(self, rate_limiter, mock_redis):
        """Test rate limit with custom limit."""
        mock_redis.pipeline.return_value = create_pipeline_mock([None, 10, None, None])

        result = await rate_limiter.check_rate_limit("test:user123", limit=50)

        assert result.allowed is True
        assert result.limit == 50
        assert result.remaining == 39  # 50 - 10 - 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_error(self, rate_limiter, mock_redis):
        """Test rate limit fails open on Redis error."""
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")

        result = await rate_limiter.check_rate_limit("test:user123")

        # Should fail open and allow request
        assert result.allowed is True
        assert result.limit == 100
        assert result.remaining == 100

    @pytest.mark.asyncio
    async def test_check_rate_limit_key_format(self, rate_limiter, mock_redis):
        """Test rate limit uses correct Redis key format."""
        mock_pipeline = create_pipeline_mock([None, 0, None, None])
        mock_redis.pipeline.return_value = mock_pipeline

        await rate_limiter.check_rate_limit("api_key:abc123")

        # Verify zremrangebyscore was called with correct key
        calls = mock_pipeline.zremrangebyscore.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == "rate_limit:api_key:abc123"

    @pytest.mark.asyncio
    async def test_check_rate_limit_window_cleanup(self, rate_limiter, mock_redis):
        """Test old entries are removed from window."""
        mock_pipeline = create_pipeline_mock([None, 25, None, None])
        mock_redis.pipeline.return_value = mock_pipeline

        current_time = time.time()
        with patch("time.time", return_value=current_time):
            await rate_limiter.check_rate_limit("test:user123")

        # Verify old entries are removed (older than window_start)
        window_start = current_time - 3600
        mock_pipeline.zremrangebyscore.assert_called_once()
        args = mock_pipeline.zremrangebyscore.call_args[0]
        assert args[0] == "rate_limit:test:user123"
        assert args[1] == 0
        assert abs(args[2] - window_start) < 1  # Allow small float difference


# Test Reset Limit


class TestResetLimit:
    """Test rate limit reset."""

    @pytest.mark.asyncio
    async def test_reset_limit_success(self, rate_limiter, mock_redis):
        """Test successful rate limit reset."""
        mock_redis.delete.return_value = 1

        result = await rate_limiter.reset_limit("test:user123")

        assert result is True
        mock_redis.delete.assert_called_once_with("rate_limit:test:user123")

    @pytest.mark.asyncio
    async def test_reset_limit_error(self, rate_limiter, mock_redis):
        """Test rate limit reset with error."""
        mock_redis.delete.side_effect = Exception("Redis error")

        result = await rate_limiter.reset_limit("test:user123")

        assert result is False


# Test Get Current Usage


class TestGetCurrentUsage:
    """Test getting current usage."""

    @pytest.mark.asyncio
    async def test_get_usage_success(self, rate_limiter, mock_redis):
        """Test getting current usage."""
        mock_redis.zcard.return_value = 42

        usage = await rate_limiter.get_current_usage("test:user123")

        assert usage == 42
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zcard.assert_called_once_with("rate_limit:test:user123")

    @pytest.mark.asyncio
    async def test_get_usage_error(self, rate_limiter, mock_redis):
        """Test get usage with error."""
        mock_redis.zremrangebyscore.side_effect = Exception("Redis error")

        usage = await rate_limiter.get_current_usage("test:user123")

        assert usage == 0


# Test Increment Usage


class TestIncrementUsage:
    """Test incrementing usage."""

    @pytest.mark.asyncio
    async def test_increment_usage_single(self, rate_limiter, mock_redis):
        """Test incrementing usage by 1."""
        mock_pipeline = create_pipeline_mock([None, None, 43])
        mock_redis.pipeline.return_value = mock_pipeline

        count = await rate_limiter.increment_usage("test:user123")

        assert count == 43
        mock_pipeline.zadd.assert_called_once()
        mock_pipeline.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_usage_multiple(self, rate_limiter, mock_redis):
        """Test incrementing usage by multiple."""
        mock_pipeline = create_pipeline_mock([None, None, 45])
        mock_redis.pipeline.return_value = mock_pipeline

        count = await rate_limiter.increment_usage("test:user123", amount=5)

        assert count == 45
        # Should add 5 entries
        mock_pipeline.zadd.assert_called_once()
        zadd_args = mock_pipeline.zadd.call_args[0]
        entries = zadd_args[1]
        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_increment_usage_error(self, rate_limiter, mock_redis):
        """Test increment usage with error."""
        mock_redis.pipeline.side_effect = Exception("Redis error")

        count = await rate_limiter.increment_usage("test:user123")

        assert count == 0


# Test Concurrent Requests


class TestConcurrentRequests:
    """Test rate limiter with concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, rate_limiter, mock_redis):
        """Test rate limiter handles concurrent requests correctly."""
        # Setup mock to increment count each time
        request_count = 0

        def mock_execute():
            nonlocal request_count
            request_count += 1
            return [None, request_count - 1, None, None]

        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(side_effect=mock_execute)
        mock_redis.pipeline.return_value = mock_pipeline

        # Make 10 concurrent requests
        tasks = [
            rate_limiter.check_rate_limit("test:concurrent")
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # All should be allowed (under 100 limit)
        assert all(r.allowed for r in results)
        assert len(results) == 10


# Test Edge Cases


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_zero_remaining(self, rate_limiter, mock_redis):
        """Test when exactly at limit."""
        mock_redis.pipeline.return_value = create_pipeline_mock([None, 99, None, None])

        result = await rate_limiter.check_rate_limit("test:user123")

        # Should still be allowed (99 + current = 100)
        assert result.allowed is True
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_far_exceeded_limit(self, rate_limiter, mock_redis):
        """Test when far over limit."""
        mock_redis.pipeline.return_value = create_pipeline_mock([None, 500, None, None])
        mock_redis.zrange.return_value = [(b"entry", time.time() - 3000)]

        result = await rate_limiter.check_rate_limit("test:user123")

        assert result.allowed is False
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_different_identifiers_independent(self, rate_limiter, mock_redis):
        """Test different identifiers are tracked independently."""
        mock_redis.pipeline.return_value = create_pipeline_mock([None, 50, None, None])

        result1 = await rate_limiter.check_rate_limit("user:alice")
        result2 = await rate_limiter.check_rate_limit("user:bob")

        # Both should be independent
        assert result1.allowed is True
        assert result2.allowed is True

    @pytest.mark.asyncio
    async def test_empty_identifier(self, rate_limiter, mock_redis):
        """Test with empty identifier."""
        mock_pipeline = create_pipeline_mock([None, 0, None, None])
        mock_redis.pipeline.return_value = mock_pipeline

        result = await rate_limiter.check_rate_limit("")

        assert result.allowed is True
        # Should use key "rate_limit:"
        mock_pipeline.zremrangebyscore.assert_called()
