"""Circuit breaker pattern for SIEM integrations.

Implements the circuit breaker pattern to prevent cascading failures when SIEM
endpoints are experiencing issues. The circuit breaker monitors failure rates
and automatically opens the circuit after a threshold is reached, allowing the
system to fail fast and recover gracefully.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit is open, requests fail fast without attempting
- HALF_OPEN: Testing if service has recovered, limited requests allowed

Configuration:
- failure_threshold: Number of failures before opening circuit (default: 5)
- recovery_timeout: Seconds to wait before attempting recovery (default: 60)
- success_threshold: Successful requests needed to close circuit (default: 2)
"""

import asyncio
import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit open, failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str, retry_after: float):
        """Initialize circuit breaker error.

        Args:
            message: Error message
            retry_after: Seconds until circuit may close
        """
        super().__init__(message)
        self.retry_after = retry_after


class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        timeout: int = 30,
    ):
        """Initialize circuit breaker configuration.

        Args:
            failure_threshold: Number of consecutive failures before opening
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Consecutive successes needed to close circuit
            timeout: Operation timeout in seconds
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout


class CircuitBreaker:
    """Circuit breaker for SIEM operations.

    Monitors operation success/failure and opens circuit when failure
    threshold is exceeded. Automatically attempts recovery after timeout.

    Example:
        ```python
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2,
        )
        breaker = CircuitBreaker("splunk", config)

        try:
            result = await breaker.call(send_to_splunk, event)
        except CircuitBreakerError as e:
            logger.error("Circuit open", retry_after=e.retry_after)
        ```
    """

    def __init__(self, name: str, config: CircuitBreakerConfig):
        """Initialize circuit breaker.

        Args:
            name: Name of the circuit (for logging)
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.opened_at: float | None = None
        self._lock = asyncio.Lock()

        logger.info(
            "circuit_breaker_initialized",
            circuit=name,
            failure_threshold=config.failure_threshold,
            recovery_timeout=config.recovery_timeout,
        )

    async def call(self, operation: Callable[[], Any]) -> T:
        """Execute operation through circuit breaker.

        Args:
            operation: Async callable to execute

        Returns:
            Result of operation

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If operation fails
        """
        async with self._lock:
            # Check if we should transition to half-open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    retry_after = self._get_retry_after()
                    logger.warning(
                        "circuit_breaker_open",
                        circuit=self.name,
                        retry_after=retry_after,
                        failures=self.failure_count,
                    )
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is open", retry_after=retry_after
                    )

        # Execute operation
        try:
            # Apply timeout
            result = await asyncio.wait_for(operation(), timeout=self.config.timeout)

            # Record success
            async with self._lock:
                self._on_success()

            return result

        except asyncio.TimeoutError as e:
            async with self._lock:
                self._on_failure()
            logger.error(
                "circuit_breaker_timeout",
                circuit=self.name,
                timeout=self.config.timeout,
                state=self.state.value,
            )
            raise

        except Exception as e:
            async with self._lock:
                self._on_failure()
            logger.error(
                "circuit_breaker_failure",
                circuit=self.name,
                error=str(e),
                state=self.state.value,
                failures=self.failure_count,
            )
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.opened_at is None:
            return False
        elapsed = time.time() - self.opened_at
        return elapsed >= self.config.recovery_timeout

    def _get_retry_after(self) -> float:
        """Get seconds until circuit may attempt reset."""
        if self.opened_at is None:
            return 0
        elapsed = time.time() - self.opened_at
        remaining = max(0, self.config.recovery_timeout - elapsed)
        return remaining

    def _transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info(
            "circuit_breaker_half_open",
            circuit=self.name,
            previous_failures=self.failure_count,
        )

    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                "circuit_breaker_success_in_half_open",
                circuit=self.name,
                successes=self.success_count,
                threshold=self.config.success_threshold,
            )

            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.info(
                    "circuit_breaker_failure_count_reset",
                    circuit=self.name,
                    previous_failures=self.failure_count,
                )
                self.failure_count = 0
                self.last_failure_time = None

    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.last_failure_time = time.time()
        self.failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open state, reopen circuit
            logger.warning(
                "circuit_breaker_half_open_failure",
                circuit=self.name,
                failures=self.failure_count,
            )
            self._open_circuit()

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.error(
                    "circuit_breaker_threshold_exceeded",
                    circuit=self.name,
                    failures=self.failure_count,
                    threshold=self.config.failure_threshold,
                )
                self._open_circuit()

    def _open_circuit(self) -> None:
        """Open the circuit."""
        self.state = CircuitState.OPEN
        self.opened_at = time.time()
        logger.error(
            "circuit_breaker_opened",
            circuit=self.name,
            failures=self.failure_count,
            recovery_timeout=self.config.recovery_timeout,
            opened_at=datetime.fromtimestamp(self.opened_at, UTC).isoformat(),
        )

    def _close_circuit(self) -> None:
        """Close the circuit."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        self.last_failure_time = None
        logger.info("circuit_breaker_closed", circuit=self.name)

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count if self.state == CircuitState.HALF_OPEN else 0,
            "failure_threshold": self.config.failure_threshold,
            "success_threshold": self.config.success_threshold,
            "recovery_timeout": self.config.recovery_timeout,
            "opened_at": (
                datetime.fromtimestamp(self.opened_at, UTC).isoformat()
                if self.opened_at
                else None
            ),
            "retry_after": self._get_retry_after() if self.state == CircuitState.OPEN else 0,
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        self.last_failure_time = None
        logger.info("circuit_breaker_manually_reset", circuit=self.name)
