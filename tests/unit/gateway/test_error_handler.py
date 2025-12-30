"""Comprehensive tests for Gateway error handler (circuit breaker, retry, timeout)."""

import asyncio
from datetime import UTC, datetime

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


class TestCircuitBreaker:
    """Test suite for Circuit Breaker implementation."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization with default values."""
        breaker = CircuitBreaker()

        assert breaker.failure_threshold == 5
        assert breaker.timeout_seconds == 30
        assert breaker.half_open_max_calls == 3
        assert breaker.success_threshold == 2
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 0
        assert breaker._total_calls == 0

    def test_circuit_breaker_custom_config(self):
        """Test circuit breaker with custom configuration."""
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

    def test_initial_state_is_closed(self):
        """Test initial state is CLOSED."""
        breaker = CircuitBreaker()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.is_open is False

    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        breaker = CircuitBreaker()

        # No calls yet
        assert breaker.failure_rate == 0.0

        # Simulate some calls
        breaker._total_calls = 10
        breaker._total_failures = 3
        assert breaker.failure_rate == 0.3

        breaker._total_failures = 5
        assert breaker.failure_rate == 0.5

    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Test successful call in CLOSED state."""
        breaker = CircuitBreaker()

        async def success_func():
            return "success"

        result = await breaker.call(success_func)

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._total_calls == 1
        assert breaker._total_successes == 1
        assert breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failure_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3)

        async def failing_func():
            raise ValueError("Test error")

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True
        assert breaker._failure_count == 3

        # Next call should be blocked
        with pytest.raises(CircuitBreakerError, match="Circuit breaker is OPEN"):
            await breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_stays_closed_below_threshold(self):
        """Test circuit stays closed below failure threshold."""
        breaker = CircuitBreaker(failure_threshold=5)

        async def failing_func():
            raise ValueError("Test error")

        # Fail 4 times (below threshold)
        for _ in range(4):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Circuit should still be CLOSED
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 4

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test that success resets failure count in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=5)

        async def failing_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # Fail 3 times
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker._failure_count == 3

        # Succeed once
        await breaker.call(success_func)

        # Failure count should be reset
        assert breaker._failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
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

        # State should transition to HALF_OPEN
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_closes_from_half_open_after_successes(self):
        """Test circuit closes from HALF_OPEN after success threshold."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1, success_threshold=2)

        async def failing_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout to transition to HALF_OPEN
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Succeed twice to reach success threshold
        await breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN  # Still half-open after 1 success

        await breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED  # Closed after 2 successes

    @pytest.mark.asyncio
    async def test_circuit_reopens_from_half_open_on_failure(self):
        """Test circuit reopens from HALF_OPEN on any failure."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1)

        async def failing_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # One failure should reopen the circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_concurrent_call_limit(self):
        """Test HALF_OPEN state limits concurrent calls."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1, half_open_max_calls=2)

        async def slow_func():
            await asyncio.sleep(0.5)
            return "success"

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Start 2 concurrent calls (should be allowed)
        task1 = asyncio.create_task(breaker.call(slow_func))
        task2 = asyncio.create_task(breaker.call(slow_func))
        await asyncio.sleep(0.1)  # Give tasks time to start

        # Third call should be blocked
        with pytest.raises(CircuitBreakerError, match="max concurrent calls reached"):
            await breaker.call(slow_func)

        # Wait for tasks to complete
        await asyncio.gather(task1, task2)

    def test_reset_circuit_breaker(self):
        """Test reset functionality."""
        breaker = CircuitBreaker(failure_threshold=2)

        # Manually set some state
        breaker._failure_count = 5
        breaker._state = CircuitState.OPEN
        breaker._last_failure_time = datetime.now(UTC)

        # Reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 0
        assert breaker._last_failure_time is None

    def test_get_metrics(self):
        """Test metrics collection."""
        breaker = CircuitBreaker()

        breaker._total_calls = 100
        breaker._total_failures = 20
        breaker._total_successes = 80
        breaker._state_changes = 3

        metrics = breaker.get_metrics()

        assert metrics["state"] == "closed"
        assert metrics["total_calls"] == 100
        assert metrics["total_failures"] == 20
        assert metrics["total_successes"] == 80
        assert metrics["failure_rate"] == 0.2
        assert metrics["state_changes"] == 3


class TestRetryConfig:
    """Test suite for RetryConfig."""

    def test_retry_config_defaults(self):
        """Test RetryConfig with default values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_retry_config_custom_values(self):
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(initial_delay=1.0, max_delay=30.0, exponential_base=2.0, jitter=False)

        # Attempt 0: 1.0 * 2^0 = 1.0
        assert config.get_delay(0) == 1.0

        # Attempt 1: 1.0 * 2^1 = 2.0
        assert config.get_delay(1) == 2.0

        # Attempt 2: 1.0 * 2^2 = 4.0
        assert config.get_delay(2) == 4.0

        # Attempt 4: 1.0 * 2^4 = 16.0
        assert config.get_delay(4) == 16.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(initial_delay=1.0, max_delay=10.0, exponential_base=2.0, jitter=False)

        # Attempt 10: would be 1024, but capped at 10
        assert config.get_delay(10) == 10.0

    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delay."""
        config = RetryConfig(initial_delay=10.0, jitter=True, exponential_base=1.0)

        # Get multiple delays for the same attempt
        delays = [config.get_delay(0) for _ in range(10)]

        # All delays should be around 10.0 ±25%, but not all identical
        assert all(7.5 <= delay <= 12.5 for delay in delays)
        assert len(set(delays)) > 1  # Should have some variance

    def test_jitter_disabled(self):
        """Test that jitter can be disabled."""
        config = RetryConfig(initial_delay=10.0, jitter=False, exponential_base=1.0)

        # All delays should be exactly 10.0
        delays = [config.get_delay(0) for _ in range(10)]
        assert all(delay == 10.0 for delay in delays)


class TestWithRetry:
    """Test suite for with_retry function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful execution on first attempt."""

        async def success_func():
            return "success"

        result = await with_retry(success_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test successful execution after some retries."""
        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        config = RetryConfig(max_attempts=5)
        result = await with_retry(flaky_func, config=config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry exhausted after max attempts."""
        call_count = 0

        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")

        config = RetryConfig(max_attempts=3, initial_delay=0.01)

        with pytest.raises(RetryExhaustedError, match="Failed after 3 attempts"):
            await with_retry(always_failing_func, config=config)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0

        async def func_with_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Non-retryable error")

        config = RetryConfig(max_attempts=3)

        # Only retry ValueError
        with pytest.raises(TypeError, match="Non-retryable error"):
            await with_retry(
                func_with_type_error, config=config, retryable_exceptions=(ValueError,)
            )

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_specific_exceptions(self):
        """Test retrying only specific exceptions."""
        call_count = 0

        async def func_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Retryable error")

        config = RetryConfig(max_attempts=3, initial_delay=0.01)

        with pytest.raises(RetryExhaustedError):
            await with_retry(
                func_with_value_error,
                config=config,
                retryable_exceptions=(ValueError, RuntimeError),
            )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_delays(self):
        """Test that retry delays are applied."""
        call_times = []

        async def failing_func():
            call_times.append(datetime.now(UTC))
            raise ValueError("Error")

        config = RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False)

        with pytest.raises(RetryExhaustedError):
            await with_retry(failing_func, config=config)

        # Should have 3 calls with delays between them
        assert len(call_times) == 3

        # Check delays (with some tolerance)
        delay1 = (call_times[1] - call_times[0]).total_seconds()
        delay2 = (call_times[2] - call_times[1]).total_seconds()

        assert 0.08 < delay1 < 0.15  # ~0.1s
        assert 0.18 < delay2 < 0.25  # ~0.2s


class TestWithTimeout:
    """Test suite for with_timeout function."""

    @pytest.mark.asyncio
    async def test_successful_execution_within_timeout(self):
        """Test successful execution within timeout."""

        async def fast_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await with_timeout(fast_func, timeout_seconds=1.0)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test timeout error when execution exceeds timeout."""

        async def slow_func():
            await asyncio.sleep(2.0)
            return "success"

        with pytest.raises(TimeoutError, match="Operation timed out after 0.5 seconds"):
            await with_timeout(slow_func, timeout_seconds=0.5)

    @pytest.mark.asyncio
    async def test_timeout_with_function_args(self):
        """Test timeout with function arguments."""

        async def func_with_args(a, b, c=None):
            await asyncio.sleep(0.1)
            return a + b + (c or 0)

        result = await with_timeout(func_with_args, 1, 2, c=3, timeout_seconds=1.0)

        assert result == 6

    @pytest.mark.asyncio
    async def test_timeout_propagates_function_errors(self):
        """Test that function errors are propagated, not timeout errors."""

        async def failing_func():
            await asyncio.sleep(0.1)
            raise ValueError("Function error")

        # Should raise ValueError, not TimeoutError
        with pytest.raises(ValueError, match="Function error"):
            await with_timeout(failing_func, timeout_seconds=1.0)


class TestGatewayErrorHandler:
    """Test suite for GatewayErrorHandler."""

    def test_error_handler_initialization_defaults(self):
        """Test error handler initialization with defaults."""
        handler = GatewayErrorHandler()

        assert handler.circuit_breaker is not None
        assert handler.retry_config is not None
        assert handler.default_timeout == 30.0

    def test_error_handler_custom_config(self):
        """Test error handler with custom configuration."""
        handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 10},
            retry_config={"max_attempts": 5},
            default_timeout=60.0,
        )

        assert handler.circuit_breaker.failure_threshold == 10
        assert handler.retry_config.max_attempts == 5
        assert handler.default_timeout == 60.0

    @pytest.mark.asyncio
    async def test_execute_successful_call(self):
        """Test execute with successful call."""
        handler = GatewayErrorHandler()

        async def success_func():
            return "success"

        result = await handler.execute(success_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_custom_timeout(self):
        """Test execute with custom timeout."""
        # Use max_attempts=1 to minimize retry attempts
        handler = GatewayErrorHandler(default_timeout=1.0, retry_config={"max_attempts": 1})

        async def slow_func():
            await asyncio.sleep(2.0)
            return "success"

        # With max_attempts=1, timeout errors are wrapped in RetryExhaustedError
        with pytest.raises(RetryExhaustedError, match="Operation timed out"):
            await handler.execute(slow_func, timeout=0.5)

    @pytest.mark.asyncio
    async def test_execute_with_retry_on_failure(self):
        """Test execute retries on failure."""
        handler = GatewayErrorHandler(retry_config={"max_attempts": 3, "initial_delay": 0.01})

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"

        result = await handler.execute(flaky_func, retryable_exceptions=(ValueError,))

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_circuit_breaker_opens(self):
        """Test execute opens circuit breaker after failures."""
        handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 2},
            retry_config={"max_attempts": 1},
        )

        async def failing_func():
            raise ValueError("Error")

        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises((ValueError, RetryExhaustedError)):
                await handler.execute(failing_func, retryable_exceptions=(ValueError,))

        # Circuit should be open
        assert handler.circuit_breaker.is_open

        # Next call should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerError):
            await handler.execute(failing_func)

    @pytest.mark.asyncio
    async def test_execute_integration_all_features(self):
        """Test execute with all error handling features working together."""
        handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 3, "timeout_seconds": 1},
            retry_config={"max_attempts": 2, "initial_delay": 0.01},
            default_timeout=1.0,
        )

        call_count = 0

        async def complex_func():
            nonlocal call_count
            call_count += 1

            # First call: slow (triggers timeout)
            if call_count == 1:
                await asyncio.sleep(2.0)
                return "too slow"

            # Second call (retry): succeeds
            return "success"

        result = await handler.execute(complex_func, retryable_exceptions=(TimeoutError,))

        assert result == "success"
        assert call_count == 2

    def test_reset_error_handler(self):
        """Test reset functionality."""
        handler = GatewayErrorHandler()

        # Manually open circuit
        handler.circuit_breaker._state = CircuitState.OPEN
        handler.circuit_breaker._failure_count = 5

        # Reset
        handler.reset()

        assert handler.circuit_breaker.is_closed
        assert handler.circuit_breaker._failure_count == 0

    def test_get_metrics(self):
        """Test metrics aggregation."""
        handler = GatewayErrorHandler(retry_config={"max_attempts": 5}, default_timeout=60.0)

        metrics = handler.get_metrics()

        assert "circuit_breaker" in metrics
        assert "retry_config" in metrics
        assert metrics["retry_config"]["max_attempts"] == 5
        assert metrics["default_timeout"] == 60.0

    @pytest.mark.asyncio
    async def test_execute_with_function_arguments(self):
        """Test execute passes through function arguments correctly."""
        handler = GatewayErrorHandler()

        async def func_with_args(a, b, c=0):
            return a + b + c

        result = await handler.execute(func_with_args, 1, 2, c=3)

        assert result == 6
