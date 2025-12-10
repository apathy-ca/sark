"""Error handling for Gateway client with circuit breaker and retry logic.

This module provides comprehensive error handling for Gateway operations including:
- Circuit breaker pattern (5 failures → open state)
- Retry logic with exponential backoff (3 attempts)
- Timeout handling (30s default)
- Connection pool management
- Health monitoring
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, TypeVar
import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Circuit breaker is open and blocking requests."""

    pass


class RetryExhaustedError(Exception):
    """All retry attempts have been exhausted."""

    pass


class TimeoutError(Exception):
    """Operation timed out."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service recovered

    State transitions:
    - CLOSED → OPEN: After failure_threshold consecutive failures
    - OPEN → HALF_OPEN: After timeout_seconds elapsed
    - HALF_OPEN → CLOSED: If test request succeeds
    - HALF_OPEN → OPEN: If test request fails

    Example:
        ```python
        breaker = CircuitBreaker(
            failure_threshold=5,
            timeout_seconds=30,
            half_open_max_calls=3,
        )

        try:
            result = await breaker.call(some_async_function, arg1, arg2)
        except CircuitBreakerError:
            # Circuit is open, service is unavailable
            pass
        ```
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 30,
        half_open_max_calls: int = 3,
        success_threshold: int = 2,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit (default: 5)
            timeout_seconds: Seconds to wait before half-open state (default: 30)
            half_open_max_calls: Max concurrent calls in half-open state (default: 3)
            success_threshold: Successes needed to close from half-open (default: 2)
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold

        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0

        # Metrics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_changes = 0

        logger.info(
            "circuit_breaker_initialized",
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        self._update_state()
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate (0.0 to 1.0)."""
        if self._total_calls == 0:
            return 0.0
        return self._total_failures / self._total_calls

    def _update_state(self) -> None:
        """Update circuit state based on elapsed time and counters."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = datetime.now(timezone.utc) - self._last_failure_time
                if elapsed.total_seconds() >= self.timeout_seconds:
                    self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new circuit state."""
        old_state = self._state
        self._state = new_state
        self._state_changes += 1

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0

        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0

        logger.info(
            "circuit_breaker_state_transition",
            old_state=old_state,
            new_state=new_state,
            failure_count=self._failure_count,
            success_count=self._success_count,
        )

    def _record_success(self) -> None:
        """Record a successful call."""
        self._total_successes += 1
        self._failure_count = 0  # Reset failure count on success

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)

    def _record_failure(self) -> None:
        """Record a failed call."""
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)

        if self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state reopens the circuit
            self._transition_to(CircuitState.OPEN)

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function raises an exception
        """
        self._total_calls += 1

        # Check circuit state
        if self.state == CircuitState.OPEN:
            logger.warning(
                "circuit_breaker_blocked_request",
                failure_count=self._failure_count,
                last_failure=self._last_failure_time,
            )
            raise CircuitBreakerError(
                f"Circuit breaker is OPEN after {self._failure_count} failures. "
                f"Last failure: {self._last_failure_time}"
            )

        # Limit concurrent calls in half-open state
        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                logger.warning(
                    "circuit_breaker_half_open_limit_reached",
                    concurrent_calls=self._half_open_calls,
                )
                raise CircuitBreakerError(
                    "Circuit breaker is HALF_OPEN and max concurrent calls reached"
                )
            self._half_open_calls += 1

        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            logger.error(
                "circuit_breaker_call_failed",
                error=str(e),
                state=self._state,
                failure_count=self._failure_count,
            )
            raise

        finally:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        logger.info("circuit_breaker_reset")
        self._transition_to(CircuitState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def get_metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "failure_rate": self.failure_rate,
            "state_changes": self._state_changes,
            "last_failure_time": self._last_failure_time.isoformat()
            if self._last_failure_time
            else None,
        }


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ) -> None:
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum retry attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 30.0)
            exponential_base: Base for exponential backoff (default: 2.0)
            jitter: Add random jitter to delays (default: True)
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt using exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        import random

        # Calculate exponential delay
        delay = min(
            self.initial_delay * (self.exponential_base**attempt), self.max_delay
        )

        # Add jitter (±25% random variance)
        if self.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


async def with_retry(
    func: Callable[..., Any],
    *args: Any,
    config: RetryConfig | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    """
    Execute async function with retry logic and exponential backoff.

    Args:
        func: Async function to execute
        *args: Positional arguments for function
        config: Retry configuration (uses default if None)
        retryable_exceptions: Tuple of exceptions that trigger retries
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        RetryExhaustedError: If all retry attempts fail
        Exception: If non-retryable exception occurs

    Example:
        ```python
        result = await with_retry(
            api_call,
            endpoint="/servers",
            config=RetryConfig(max_attempts=5),
            retryable_exceptions=(httpx.NetworkError, httpx.TimeoutException),
        )
        ```
    """
    config = config or RetryConfig()
    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(
                    "retry_succeeded",
                    attempt=attempt + 1,
                    total_attempts=config.max_attempts,
                )
            return result

        except retryable_exceptions as e:
            last_exception = e
            is_last_attempt = attempt == config.max_attempts - 1

            if is_last_attempt:
                logger.error(
                    "retry_exhausted",
                    attempts=config.max_attempts,
                    error=str(e),
                )
                raise RetryExhaustedError(
                    f"Failed after {config.max_attempts} attempts: {str(e)}"
                ) from e

            # Calculate delay and retry
            delay = config.get_delay(attempt)
            logger.warning(
                "retry_attempt",
                attempt=attempt + 1,
                max_attempts=config.max_attempts,
                delay_seconds=delay,
                error=str(e),
            )
            await asyncio.sleep(delay)

        except Exception as e:
            # Non-retryable exception
            logger.error(
                "non_retryable_exception",
                error=str(e),
                exception_type=type(e).__name__,
            )
            raise

    # Should never reach here, but satisfy type checker
    if last_exception:
        raise last_exception
    raise RetryExhaustedError("Retry logic error")


async def with_timeout(
    func: Callable[..., Any], *args: Any, timeout_seconds: float = 30.0, **kwargs: Any
) -> T:
    """
    Execute async function with timeout.

    Args:
        func: Async function to execute
        *args: Positional arguments for function
        timeout_seconds: Timeout in seconds (default: 30.0)
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        TimeoutError: If function exceeds timeout

    Example:
        ```python
        result = await with_timeout(slow_api_call, timeout_seconds=10.0)
        ```
    """
    try:
        result = await asyncio.wait_for(
            func(*args, **kwargs), timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError as e:
        logger.error(
            "operation_timeout",
            timeout_seconds=timeout_seconds,
            function=func.__name__,
        )
        raise TimeoutError(
            f"Operation timed out after {timeout_seconds} seconds"
        ) from e


class GatewayErrorHandler:
    """
    Unified error handler for Gateway operations.

    Combines circuit breaker, retry logic, and timeout handling into a
    single convenient interface.

    Example:
        ```python
        error_handler = GatewayErrorHandler(
            circuit_breaker_config={"failure_threshold": 5},
            retry_config={"max_attempts": 3},
            default_timeout=30.0,
        )

        result = await error_handler.execute(
            api_client.get_servers,
            timeout=10.0,
        )
        ```
    """

    def __init__(
        self,
        circuit_breaker_config: dict[str, Any] | None = None,
        retry_config: dict[str, Any] | None = None,
        default_timeout: float = 30.0,
    ) -> None:
        """
        Initialize Gateway error handler.

        Args:
            circuit_breaker_config: Circuit breaker configuration
            retry_config: Retry configuration
            default_timeout: Default timeout in seconds
        """
        self.circuit_breaker = CircuitBreaker(**(circuit_breaker_config or {}))
        self.retry_config = RetryConfig(**(retry_config or {}))
        self.default_timeout = default_timeout

        logger.info(
            "gateway_error_handler_initialized",
            circuit_breaker_threshold=self.circuit_breaker.failure_threshold,
            retry_max_attempts=self.retry_config.max_attempts,
            default_timeout=default_timeout,
        )

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
        **kwargs: Any,
    ) -> T:
        """
        Execute function with full error handling (circuit breaker + retry + timeout).

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            timeout: Timeout in seconds (uses default if None)
            retryable_exceptions: Exceptions that trigger retries
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            RetryExhaustedError: If all retries fail
            TimeoutError: If operation times out
        """
        timeout = timeout or self.default_timeout

        async def wrapped_call() -> T:
            return await with_retry(
                with_timeout,
                func,
                *args,
                timeout_seconds=timeout,
                **kwargs,
                config=self.retry_config,
                retryable_exceptions=retryable_exceptions,
            )

        return await self.circuit_breaker.call(wrapped_call)

    def reset(self) -> None:
        """Reset circuit breaker."""
        self.circuit_breaker.reset()

    def get_metrics(self) -> dict[str, Any]:
        """Get error handler metrics."""
        return {
            "circuit_breaker": self.circuit_breaker.get_metrics(),
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "initial_delay": self.retry_config.initial_delay,
                "max_delay": self.retry_config.max_delay,
            },
            "default_timeout": self.default_timeout,
        }
