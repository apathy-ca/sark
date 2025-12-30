"""Unit tests for Rate Limiter service."""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from sark.services.rate_limiter import RateLimiter, RateLimitInfo


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.pipeline = Mock(return_value=AsyncMock())
    redis.zremrangebyscore = AsyncMock()
    redis.zcard = AsyncMock()
    redis.zadd = AsyncMock()
    redis.expire = AsyncMock()
    redis.zrange = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    """Create a rate limiter instance with default config."""
    return RateLimiter(
        redis_client=mock_redis,
        default_limit=10,
        window_seconds=60,
    )


@pytest.fixture
def current_timestamp():
    """Get current timestamp for testing."""
    return time.time()


class TestRateLimiterInitialization:
    """Test rate limiter initialization."""

    def test_init_with_defaults(self, mock_redis):
        """Test initialization with default parameters."""
        limiter = RateLimiter(redis_client=mock_redis)
        assert limiter.redis == mock_redis
        assert limiter.default_limit == 1000
        assert limiter.window_seconds == 3600

    def test_init_with_custom_values(self, mock_redis):
        """Test initialization with custom parameters."""
        limiter = RateLimiter(
            redis_client=mock_redis,
            default_limit=50,
            window_seconds=300,
        )
        assert limiter.default_limit == 50
        assert limiter.window_seconds == 300


class TestCheckRateLimit:
    """Test check_rate_limit functionality."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self, rate_limiter, mock_redis, current_timestamp):
        """Test that requests within rate limit are allowed."""
        # Arrange
        identifier = "user:123"
        current_count = 5  # Below limit of 10

        # Mock pipeline execution
        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, current_count, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        result = await rate_limiter.check_rate_limit(identifier)

        # Assert
        assert isinstance(result, RateLimitInfo)
        assert result.allowed is True
        assert result.limit == 10
        assert result.remaining == 4  # 10 - 5 - 1
        assert result.retry_after is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_at_limit(self, rate_limiter, mock_redis):
        """Test that requests at the rate limit are blocked."""
        # Arrange
        identifier = "user:456"
        current_count = 10  # At limit

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, current_count, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Mock oldest entry for retry_after calculation
        oldest_timestamp = time.time() - 30  # 30 seconds ago
        mock_redis.zrange.return_value = [("entry", oldest_timestamp)]

        # Act
        result = await rate_limiter.check_rate_limit(identifier)

        # Assert
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after >= 1  # At least 1 second

    @pytest.mark.asyncio
    async def test_check_rate_limit_with_custom_limit(self, rate_limiter, mock_redis):
        """Test rate limiting with custom limit for specific identifier."""
        # Arrange
        identifier = "api_key:premium"
        custom_limit = 100
        current_count = 50

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, current_count, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        result = await rate_limiter.check_rate_limit(identifier, limit=custom_limit)

        # Assert
        assert result.allowed is True
        assert result.limit == custom_limit
        assert result.remaining == 49  # 100 - 50 - 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_pipeline_operations(self, rate_limiter, mock_redis):
        """Test that check_rate_limit performs correct Redis pipeline operations."""
        # Arrange
        identifier = "user:789"
        current_count = 3

        pipe_mock = AsyncMock()
        pipe_mock.zremrangebyscore = AsyncMock()
        pipe_mock.zcard = AsyncMock()
        pipe_mock.zadd = AsyncMock()
        pipe_mock.expire = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, current_count, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        with patch("time.time", return_value=1000.0):
            await rate_limiter.check_rate_limit(identifier)

        # Assert
        pipe_mock.zremrangebyscore.assert_called_once()
        pipe_mock.zcard.assert_called_once()
        pipe_mock.zadd.assert_called_once()
        pipe_mock.expire.assert_called_once_with("rate_limit:user:789", 120)  # window + 60
        pipe_mock.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_uses_correct_redis_key(self, rate_limiter, mock_redis):
        """Test that correct Redis key is used for rate limiting."""
        # Arrange
        identifier = "ip:192.168.1.1"
        expected_key = "rate_limit:ip:192.168.1.1"

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 0, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        await rate_limiter.check_rate_limit(identifier)

        # Assert
        # The zremrangebyscore call should use the correct key
        call_args = pipe_mock.zremrangebyscore.call_args
        assert call_args[0][0] == expected_key

    @pytest.mark.asyncio
    async def test_check_rate_limit_calculates_reset_time(self, rate_limiter, mock_redis):
        """Test that reset_at is calculated correctly."""
        # Arrange
        identifier = "user:reset_test"
        current_time = 1000.0

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        with patch("time.time", return_value=current_time):
            result = await rate_limiter.check_rate_limit(identifier)

        # Assert
        expected_reset = int(current_time + 60)  # current_time + window_seconds
        assert result.reset_at == expected_reset

    @pytest.mark.asyncio
    async def test_check_rate_limit_retry_after_calculation(self, rate_limiter, mock_redis):
        """Test retry_after calculation when rate limited."""
        # Arrange
        identifier = "user:retry_test"
        current_time = 1000.0
        oldest_timestamp = 970.0  # 30 seconds ago

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 10, None, None])  # At limit
        mock_redis.pipeline.return_value = pipe_mock
        mock_redis.zrange.return_value = [("entry", oldest_timestamp)]

        # Act
        with patch("time.time", return_value=current_time):
            result = await rate_limiter.check_rate_limit(identifier)

        # Assert
        assert result.allowed is False
        # retry_after = oldest_timestamp + window_seconds - current_time
        # = 970 + 60 - 1000 = 30
        assert result.retry_after == 30

    @pytest.mark.asyncio
    async def test_check_rate_limit_minimum_retry_after(self, rate_limiter, mock_redis):
        """Test that retry_after has a minimum of 1 second."""
        # Arrange
        identifier = "user:min_retry"
        current_time = 1000.0
        oldest_timestamp = 940.5  # Should result in retry_after < 1

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 10, None, None])
        mock_redis.pipeline.return_value = pipe_mock
        mock_redis.zrange.return_value = [("entry", oldest_timestamp)]

        # Act
        with patch("time.time", return_value=current_time):
            result = await rate_limiter.check_rate_limit(identifier)

        # Assert
        assert result.retry_after >= 1


class TestRateLimiterErrorHandling:
    """Test error handling and fail-open behavior."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_fails_open_on_redis_error(self, rate_limiter, mock_redis):
        """Test that rate limiter fails open (allows request) when Redis is unavailable."""
        # Arrange
        identifier = "user:fail_open"
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")

        # Act
        result = await rate_limiter.check_rate_limit(identifier)

        # Assert - Should allow the request despite error
        assert result.allowed is True
        assert result.limit == 10
        assert result.remaining == 10

    @pytest.mark.asyncio
    async def test_reset_limit_handles_redis_error(self, rate_limiter, mock_redis):
        """Test that reset_limit handles Redis errors gracefully."""
        # Arrange
        identifier = "user:error"
        mock_redis.delete.side_effect = Exception("Redis error")

        # Act
        result = await rate_limiter.reset_limit(identifier)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_current_usage_handles_redis_error(self, rate_limiter, mock_redis):
        """Test that get_current_usage handles Redis errors gracefully."""
        # Arrange
        identifier = "user:error"
        mock_redis.zremrangebyscore.side_effect = Exception("Redis error")

        # Act
        result = await rate_limiter.get_current_usage(identifier)

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_increment_usage_handles_redis_error(self, rate_limiter, mock_redis):
        """Test that increment_usage handles Redis errors gracefully."""
        # Arrange
        identifier = "user:error"
        pipe_mock = AsyncMock()
        pipe_mock.execute.side_effect = Exception("Redis error")
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        result = await rate_limiter.increment_usage(identifier)

        # Assert
        assert result == 0


class TestResetLimit:
    """Test reset_limit functionality."""

    @pytest.mark.asyncio
    async def test_reset_limit_success(self, rate_limiter, mock_redis):
        """Test successful rate limit reset."""
        # Arrange
        identifier = "user:reset_success"
        mock_redis.delete.return_value = 1

        # Act
        result = await rate_limiter.reset_limit(identifier)

        # Assert
        assert result is True
        mock_redis.delete.assert_called_once_with("rate_limit:user:reset_success")

    @pytest.mark.asyncio
    async def test_reset_limit_correct_key(self, rate_limiter, mock_redis):
        """Test that reset_limit uses correct Redis key."""
        # Arrange
        identifier = "api_key:xyz789"
        expected_key = "rate_limit:api_key:xyz789"

        # Act
        await rate_limiter.reset_limit(identifier)

        # Assert
        mock_redis.delete.assert_called_once_with(expected_key)


class TestGetCurrentUsage:
    """Test get_current_usage functionality."""

    @pytest.mark.asyncio
    async def test_get_current_usage_returns_count(self, rate_limiter, mock_redis):
        """Test that get_current_usage returns current request count."""
        # Arrange
        identifier = "user:usage_test"
        expected_count = 7
        mock_redis.zcard.return_value = expected_count

        # Act
        result = await rate_limiter.get_current_usage(identifier)

        # Assert
        assert result == expected_count

    @pytest.mark.asyncio
    async def test_get_current_usage_removes_old_entries(self, rate_limiter, mock_redis):
        """Test that get_current_usage removes expired entries."""
        # Arrange
        identifier = "user:cleanup"
        current_time = 1000.0
        window_start = current_time - 60

        mock_redis.zcard.return_value = 5

        # Act
        with patch("time.time", return_value=current_time):
            await rate_limiter.get_current_usage(identifier)

        # Assert
        mock_redis.zremrangebyscore.assert_called_once_with(
            "rate_limit:user:cleanup", 0, window_start
        )


class TestIncrementUsage:
    """Test increment_usage functionality."""

    @pytest.mark.asyncio
    async def test_increment_usage_single(self, rate_limiter, mock_redis):
        """Test incrementing usage by 1."""
        # Arrange
        identifier = "user:increment"
        new_count = 8

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, None, new_count])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        result = await rate_limiter.increment_usage(identifier, amount=1)

        # Assert
        assert result == new_count

    @pytest.mark.asyncio
    async def test_increment_usage_multiple(self, rate_limiter, mock_redis):
        """Test incrementing usage by multiple."""
        # Arrange
        identifier = "user:bulk"
        amount = 5
        new_count = 12

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, None, new_count])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        result = await rate_limiter.increment_usage(identifier, amount=amount)

        # Assert
        assert result == new_count

    @pytest.mark.asyncio
    async def test_increment_usage_pipeline_operations(self, rate_limiter, mock_redis):
        """Test that increment_usage performs correct pipeline operations."""
        # Arrange
        identifier = "user:pipeline"

        pipe_mock = AsyncMock()
        pipe_mock.zadd = AsyncMock()
        pipe_mock.expire = AsyncMock()
        pipe_mock.zcard = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, None, 10])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        await rate_limiter.increment_usage(identifier, amount=3)

        # Assert
        pipe_mock.zadd.assert_called_once()
        pipe_mock.expire.assert_called_once()
        pipe_mock.zcard.assert_called_once()

        # Verify that zadd was called with 3 entries
        zadd_call = pipe_mock.zadd.call_args
        entries = zadd_call[0][1]  # Second argument to zadd (first is key)
        assert len(entries) == 3


class TestRateLimiterIntegrationScenarios:
    """Test realistic rate limiting scenarios."""

    @pytest.mark.asyncio
    async def test_progressive_rate_limiting(self, rate_limiter, mock_redis):
        """Test progressive requests consuming rate limit."""
        # Simulate 10 requests filling up the limit
        pipe_mock = AsyncMock()
        mock_redis.pipeline.return_value = pipe_mock

        for i in range(10):
            pipe_mock.execute = AsyncMock(return_value=[None, i, None, None])
            result = await rate_limiter.check_rate_limit("user:progressive")

            if i < 10:
                assert result.allowed is True
                assert result.remaining == 10 - i - 1

    @pytest.mark.asyncio
    async def test_different_identifiers_independent(self, rate_limiter, mock_redis):
        """Test that different identifiers have independent rate limits."""
        # Arrange
        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 0, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Act
        result1 = await rate_limiter.check_rate_limit("user:alice")
        result2 = await rate_limiter.check_rate_limit("user:bob")

        # Assert - Both should be allowed independently
        assert result1.allowed is True
        assert result2.allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_key_formats(self, rate_limiter, mock_redis):
        """Test various identifier formats for rate limiting."""
        # Arrange
        identifiers = [
            "user:123",
            "api_key:abc123",
            "ip:192.168.1.1",
            "session:xyz789",
        ]

        pipe_mock = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 0, None, None])
        mock_redis.pipeline.return_value = pipe_mock

        # Act & Assert
        for identifier in identifiers:
            result = await rate_limiter.check_rate_limit(identifier)
            assert result.allowed is True

            # Verify correct key was used
            call_args = pipe_mock.zremrangebyscore.call_args
            assert call_args[0][0] == f"rate_limit:{identifier}"
