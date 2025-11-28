"""Tests for RetryHandler with exponential backoff."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from sark.services.audit.siem.retry_handler import RetryConfig, RetryHandler


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.backoff_base == 2.0
        assert config.backoff_max == 60.0
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            backoff_base=3.0,
            backoff_max=120.0,
            retryable_exceptions=(ValueError,),
        )
        assert config.max_attempts == 5
        assert config.backoff_base == 3.0
        assert config.backoff_max == 120.0
        assert config.retryable_exceptions == (ValueError,)


class TestRetryHandler:
    """Tests for RetryHandler."""

    @pytest.fixture
    def retry_handler(self) -> RetryHandler:
        """Create a retry handler with fast backoff for testing."""
        config = RetryConfig(
            max_attempts=3,
            backoff_base=1.1,  # Fast backoff for tests
            backoff_max=1.0,
            retryable_exceptions=(ConnectionError, TimeoutError, ValueError),
        )
        return RetryHandler(config)

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self, retry_handler: RetryHandler):
        """Test successful operation on first attempt."""
        mock_operation = AsyncMock(return_value="success")

        result = await retry_handler.execute_with_retry(mock_operation, "test_operation")

        assert result == "success"
        assert mock_operation.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_retryable_exception(self, retry_handler: RetryHandler):
        """Test retry behavior on retryable exception."""
        mock_operation = AsyncMock(side_effect=[ConnectionError("Connection failed"), "success"])

        result = await retry_handler.execute_with_retry(mock_operation, "test_operation")

        assert result == "success"
        assert mock_operation.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, retry_handler: RetryHandler):
        """Test behavior when all retries are exhausted."""
        mock_operation = AsyncMock(side_effect=ConnectionError("Connection failed"))

        with pytest.raises(ConnectionError, match="Connection failed"):
            await retry_handler.execute_with_retry(mock_operation, "test_operation")

        assert mock_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self, retry_handler: RetryHandler):
        """Test immediate failure on non-retryable exception."""
        mock_operation = AsyncMock(side_effect=RuntimeError("Fatal error"))

        with pytest.raises(RuntimeError, match="Fatal error"):
            await retry_handler.execute_with_retry(mock_operation, "test_operation")

        # Should not retry for non-retryable exceptions
        assert mock_operation.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, retry_handler: RetryHandler):
        """Test exponential backoff timing."""
        call_times = []

        async def failing_operation():
            call_times.append(asyncio.get_event_loop().time())
            raise ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            await retry_handler.execute_with_retry(failing_operation, "test_operation")

        # Verify we had 3 attempts
        assert len(call_times) == 3

        # Verify increasing delays between attempts
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert delay1 > 0  # Some delay after first failure

        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            # Second delay should be longer due to exponential backoff
            # (with some tolerance for timing variance)
            assert delay2 >= delay1 * 0.8

    @pytest.mark.asyncio
    async def test_on_retry_callback(self, retry_handler: RetryHandler):
        """Test on_retry callback is called on each retry."""
        callback_calls = []

        def on_retry_callback(attempt: int, exception: Exception):
            callback_calls.append((attempt, type(exception).__name__))

        mock_operation = AsyncMock(
            side_effect=[
                ConnectionError("Fail 1"),
                ValueError("Fail 2"),
                "success",
            ]
        )

        result = await retry_handler.execute_with_retry(
            mock_operation,
            "test_operation",
            on_retry=on_retry_callback,
        )

        assert result == "success"
        assert len(callback_calls) == 2
        assert callback_calls[0] == (1, "ConnectionError")
        assert callback_calls[1] == (2, "ValueError")

    @pytest.mark.asyncio
    async def test_on_retry_callback_exception(self, retry_handler: RetryHandler):
        """Test that callback exceptions don't break retry logic."""

        def failing_callback(attempt: int, exception: Exception):
            raise RuntimeError("Callback error")

        mock_operation = AsyncMock(side_effect=[ConnectionError("Fail"), "success"])

        # Should still succeed despite callback error
        result = await retry_handler.execute_with_retry(
            mock_operation,
            "test_operation",
            on_retry=failing_callback,
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self, retry_handler: RetryHandler):
        """Test operation completing within timeout."""

        async def fast_operation():
            await asyncio.sleep(0.01)
            return "success"

        result = await retry_handler.execute_with_timeout(
            fast_operation,
            timeout_seconds=1.0,
            operation_name="test_operation",
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_exceeded(self, retry_handler: RetryHandler):
        """Test operation exceeding timeout."""

        async def slow_operation():
            await asyncio.sleep(2.0)
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await retry_handler.execute_with_timeout(
                slow_operation,
                timeout_seconds=0.1,
                operation_name="test_operation",
            )

    @pytest.mark.asyncio
    async def test_execute_with_retry_and_timeout_success(self, retry_handler: RetryHandler):
        """Test combined retry and timeout with success."""
        call_count = 0

        async def operation_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Fail first time")
            await asyncio.sleep(0.01)
            return "success"

        result = await retry_handler.execute_with_retry_and_timeout(
            operation_with_retry,
            timeout_seconds=1.0,
            operation_name="test_operation",
        )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_and_timeout_exhausted(self, retry_handler: RetryHandler):
        """Test combined retry and timeout with all retries exhausted."""

        async def failing_operation():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await retry_handler.execute_with_retry_and_timeout(
                failing_operation,
                timeout_seconds=1.0,
                operation_name="test_operation",
            )

    @pytest.mark.asyncio
    async def test_execute_with_retry_and_timeout_timeout(self, retry_handler: RetryHandler):
        """Test combined retry and timeout with timeout occurring."""

        async def slow_operation():
            await asyncio.sleep(2.0)
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await retry_handler.execute_with_retry_and_timeout(
                slow_operation,
                timeout_seconds=0.1,
                operation_name="test_operation",
            )

    @pytest.mark.asyncio
    async def test_backoff_max_limit(self):
        """Test that backoff doesn't exceed max value."""
        config = RetryConfig(
            max_attempts=5,
            backoff_base=10.0,  # Very aggressive backoff
            backoff_max=1.0,  # Low max to test capping
        )
        handler = RetryHandler(config)

        call_times = []

        async def failing_operation():
            call_times.append(asyncio.get_event_loop().time())
            raise ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            await handler.execute_with_retry(failing_operation, "test_operation")

        # Check that delays don't exceed backoff_max
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i - 1]
            # Allow some tolerance for timing variance
            assert delay <= config.backoff_max + 0.1

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """Test with zero retry attempts."""
        config = RetryConfig(max_attempts=1)  # No retries, just one attempt
        handler = RetryHandler(config)

        mock_operation = AsyncMock(side_effect=ConnectionError("Connection failed"))

        with pytest.raises(ConnectionError):
            await handler.execute_with_retry(mock_operation, "test_operation")

        assert mock_operation.call_count == 1
