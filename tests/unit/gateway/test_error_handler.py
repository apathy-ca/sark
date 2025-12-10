"""Comprehensive tests for Gateway error handler.

This module tests:
- Circuit breaker state transitions
- Retry logic with exponential backoff
- Timeout handling
- GatewayErrorHandler integration
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.gateway.error_handler import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    GatewayErrorHandler,
    RetryConfig,
    RetryExhaustedError,
    TimeoutError,
    with_retry,
    with_timeout,
)


class TestCircuitState:
    """Test CircuitState enum."""

    def test_circuit_states(self):
        """Test that all circuit states are defined."""
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"


class TestCircuitBreakerErrors:
    """Test custom exception classes."""

    def test_circuit_breaker_error(self):
        """Test CircuitBreakerError can be raised and caught."""
        with pytest.raises(CircuitBreakerError) as exc_info:
            raise CircuitBreakerError("Circuit is open")
        assert "Circuit is open" in str(exc_info.value)

    def test_retry_exhausted_error(self):
        """Test RetryExhaustedError can be raised and caught."""
        with pytest.raises(RetryExhaustedError) as exc_info:
            raise RetryExhaustedError("All retries failed")
        assert "All retries failed" in str(exc_info.value)

    def test_timeout_error(self):
        """Test TimeoutError can be raised and caught."""
        with pytest.raises(TimeoutError) as exc_info:
            raise TimeoutError("Operation timed out")
        assert "Operation timed out" in str(exc_info.value)


class TestCircuitBreaker:
    """Test CircuitBreaker implementation."""

    def test_initialization_defaults(self):
        """Test circuit breaker initializes with default values."""
        breaker = CircuitBreaker()

        assert breaker.failure_threshold == 5
        assert breaker.timeout_seconds == 30
        assert breaker.half_open_max_calls == 3
        assert breaker.success_threshold == 2
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open

    def test_initialization_custom_values(self):
        """Test circuit breaker initializes with custom values."""
        breaker = CircuitBreaker(
            failure_threshold=10,
            timeout_seconds=60,
            half_open_max_calls=5,
            success_threshold=3,
        )

        assert breaker.failure_threshold == 10
        assert breaker.timeout_seconds == 60
        assert breaker.half_open_max_calls == 5
        assert breaker.success_threshold == 3

    def test_initial_failure_rate_is_zero(self):
        """Test that initial failure rate is 0.0."""
        breaker = CircuitBreaker()
        assert breaker.failure_rate == 0.0

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful function call through circuit breaker."""
        breaker = CircuitBreaker()

        async def success_func():
            return "success"

        result = await breaker.call(success_func)

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._total_calls == 1
        assert breaker._total_successes == 1
        assert breaker._total_failures == 0

    @pytest.mark.asyncio
    async def test_failed_call(self):
        """Test failed function call through circuit breaker."""
        breaker = CircuitBreaker(failure_threshold=5)

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.CLOSED  # Still closed after 1 failure
        assert breaker._total_calls == 1
        assert breaker._total_successes == 0
        assert breaker._total_failures == 1
        assert breaker._failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after reaching failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3)

        async def failing_func():
            raise ValueError("Test error")

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open
        assert breaker._failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_blocks_when_open(self):
        """Test that circuit blocks calls when open."""
        breaker = CircuitBreaker(failure_threshold=2)

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Now circuit should block
        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(success_func)

        assert "Circuit breaker is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self):
        """Test that circuit transitions to half-open after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1)

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Check state updates to half-open
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Test that successful calls in half-open state close the circuit."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            timeout_seconds=1,
            success_threshold=2,
        )

        async def failing_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout to half-open
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Two successful calls should close circuit
        await breaker.call(success_func)
        await breaker.call(success_func)

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Test that failure in half-open state reopens circuit."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1)

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout to half-open
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Any failure in half-open should reopen circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_max_calls_limit(self):
        """Test that half-open state limits concurrent calls."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            timeout_seconds=1,
            half_open_max_calls=1,  # Only allow 1 concurrent call
        )

        async def failing_func():
            raise ValueError("Test error")

        async def slow_func():
            await asyncio.sleep(0.5)
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout to half-open
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Start 1 slow call (max allowed)
        task = asyncio.create_task(breaker.call(slow_func))

        # Give it time to start and increment counter
        await asyncio.sleep(0.1)

        # Try one more - should be blocked since we're at max
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(slow_func)

        assert "max concurrent calls reached" in str(exc_info.value)

        # Wait for task to complete
        await task

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test that success resets failure count."""
        breaker = CircuitBreaker(failure_threshold=5)

        async def failing_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # Fail a few times
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker._failure_count == 3

        # One success should reset failure count
        await breaker.call(success_func)

        assert breaker._failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    def test_reset_circuit_breaker(self):
        """Test manually resetting circuit breaker."""
        breaker = CircuitBreaker()
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 5
        breaker._last_failure_time = datetime.now(timezone.utc)

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 0
        assert breaker._last_failure_time is None

    def test_get_metrics(self):
        """Test getting circuit breaker metrics."""
        breaker = CircuitBreaker()
        breaker._total_calls = 10
        breaker._total_failures = 3
        breaker._total_successes = 7
        breaker._state_changes = 2

        metrics = breaker.get_metrics()

        assert metrics["state"] == CircuitState.CLOSED.value
        assert metrics["total_calls"] == 10
        assert metrics["total_failures"] == 3
        assert metrics["total_successes"] == 7
        assert metrics["failure_rate"] == 0.3
        assert metrics["state_changes"] == 2

    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        breaker = CircuitBreaker()
        breaker._total_calls = 20
        breaker._total_failures = 5

        assert breaker.failure_rate == 0.25


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_initialization_defaults(self):
        """Test retry config initializes with defaults."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_initialization_custom_values(self):
        """Test retry config initializes with custom values."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_get_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )

        # Attempt 0: 1.0 * 2^0 = 1.0
        assert config.get_delay(0) == 1.0

        # Attempt 1: 1.0 * 2^1 = 2.0
        assert config.get_delay(1) == 2.0

        # Attempt 2: 1.0 * 2^2 = 4.0
        assert config.get_delay(2) == 4.0

        # Attempt 3: 1.0 * 2^3 = 8.0
        assert config.get_delay(3) == 8.0

    def test_get_delay_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False,
        )

        # Attempt 10: 1.0 * 2^10 = 1024.0, but capped at 5.0
        assert config.get_delay(10) == 5.0

    def test_get_delay_with_jitter(self):
        """Test that jitter adds randomness to delay."""
        config = RetryConfig(
            initial_delay=4.0,
            exponential_base=2.0,
            jitter=True,
        )

        delays = [config.get_delay(0) for _ in range(10)]

        # All delays should be near 4.0 but with variance
        assert all(3.0 <= d <= 5.0 for d in delays)

        # Should have some variance (not all identical)
        assert len(set(delays)) > 1


class TestWithRetry:
    """Test with_retry function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful function call on first attempt."""
        async def success_func():
            return "success"

        result = await with_retry(success_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_success_after_failures(self):
        """Test successful function call after some failures."""
        call_count = 0

        async def eventually_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = await with_retry(
            eventually_success,
            config=RetryConfig(max_attempts=5, initial_delay=0.1),
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test that retry exhausted error is raised after max attempts."""
        async def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await with_retry(
                always_fails,
                config=RetryConfig(max_attempts=3, initial_delay=0.1),
            )

        assert "Failed after 3 attempts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0

        async def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise KeyError("Not retryable")

        with pytest.raises(KeyError):
            await with_retry(
                raises_non_retryable,
                config=RetryConfig(max_attempts=5, initial_delay=0.1),
                retryable_exceptions=(ValueError,),  # Only ValueError is retryable
            )

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_custom_config(self):
        """Test retry with custom configuration."""
        call_count = 0

        async def count_calls():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test")

        config = RetryConfig(max_attempts=5, initial_delay=0.05)

        with pytest.raises(RetryExhaustedError):
            await with_retry(count_calls, config=config)

        assert call_count == 5


class TestWithTimeout:
    """Test with_timeout function."""

    @pytest.mark.asyncio
    async def test_success_within_timeout(self):
        """Test successful function call within timeout."""
        async def quick_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await with_timeout(quick_func, timeout_seconds=1.0)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test that timeout error is raised when exceeded."""
        async def slow_func():
            await asyncio.sleep(2.0)
            return "too slow"

        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(slow_func, timeout_seconds=0.5)

        assert "timed out after 0.5 seconds" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_with_args_kwargs(self):
        """Test timeout with function arguments."""
        async def func_with_args(x, y, z=None):
            await asyncio.sleep(0.1)
            return x + y + (z or 0)

        result = await with_timeout(func_with_args, 1, 2, z=3, timeout_seconds=1.0)

        assert result == 6


class TestGatewayErrorHandler:
    """Test GatewayErrorHandler integration."""

    def test_initialization_defaults(self):
        """Test error handler initializes with defaults."""
        handler = GatewayErrorHandler()

        assert handler.circuit_breaker is not None
        assert handler.retry_config is not None
        assert handler.default_timeout == 30.0

    def test_initialization_custom_config(self):
        """Test error handler initializes with custom config."""
        handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 10},
            retry_config={"max_attempts": 5},
            default_timeout=60.0,
        )

        assert handler.circuit_breaker.failure_threshold == 10
        assert handler.retry_config.max_attempts == 5
        assert handler.default_timeout == 60.0

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful function execution through error handler."""
        handler = GatewayErrorHandler()

        async def success_func():
            return "success"

        result = await handler.execute(success_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execution_with_retry(self):
        """Test execution with retries."""
        handler = GatewayErrorHandler(
            retry_config={"max_attempts": 3, "initial_delay": 0.1}
        )

        call_count = 0

        async def eventually_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = await handler.execute(eventually_success)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execution_with_timeout(self):
        """Test execution with timeout."""
        handler = GatewayErrorHandler()

        async def slow_func():
            await asyncio.sleep(2.0)
            return "too slow"

        with pytest.raises(RetryExhaustedError):  # Retry wraps timeout error
            await handler.execute(slow_func, timeout=0.5)

    @pytest.mark.asyncio
    async def test_execution_opens_circuit_after_failures(self):
        """Test that circuit opens after repeated failures."""
        handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 2},
            retry_config={"max_attempts": 1, "initial_delay": 0.1},
        )

        async def always_fails():
            raise ValueError("Always fails")

        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(RetryExhaustedError):
                await handler.execute(always_fails)

        # Circuit should now be open
        assert handler.circuit_breaker.is_open

        # Next call should be blocked by circuit breaker
        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerError):
            await handler.execute(success_func)

    @pytest.mark.asyncio
    async def test_execution_with_custom_timeout(self):
        """Test execution with custom timeout."""
        handler = GatewayErrorHandler(default_timeout=30.0)

        async def quick_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await handler.execute(quick_func, timeout=1.0)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execution_with_retryable_exceptions(self):
        """Test execution with specific retryable exceptions."""
        handler = GatewayErrorHandler(
            retry_config={"max_attempts": 3, "initial_delay": 0.1}
        )

        call_count = 0

        async def specific_error():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")

        with pytest.raises(RetryExhaustedError):
            await handler.execute(
                specific_error,
                retryable_exceptions=(ConnectionError,),
            )

        # Should retry multiple times
        assert call_count == 3

    def test_reset_circuit_breaker(self):
        """Test resetting circuit breaker."""
        handler = GatewayErrorHandler()
        handler.circuit_breaker._state = CircuitState.OPEN

        handler.reset()

        assert handler.circuit_breaker.state == CircuitState.CLOSED

    def test_get_metrics(self):
        """Test getting error handler metrics."""
        handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 10},
            retry_config={"max_attempts": 5, "initial_delay": 2.0, "max_delay": 60.0},
            default_timeout=45.0,
        )

        metrics = handler.get_metrics()

        assert "circuit_breaker" in metrics
        assert "retry_config" in metrics
        assert metrics["retry_config"]["max_attempts"] == 5
        assert metrics["retry_config"]["initial_delay"] == 2.0
        assert metrics["retry_config"]["max_delay"] == 60.0
        assert metrics["default_timeout"] == 45.0

    @pytest.mark.asyncio
    async def test_execution_with_function_args(self):
        """Test execution with function arguments and kwargs."""
        handler = GatewayErrorHandler()

        async def func_with_params(a, b, c=0):
            return a + b + c

        result = await handler.execute(func_with_params, 1, 2, c=3)

        assert result == 6
