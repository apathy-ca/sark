"""Retry handler with exponential backoff for SIEM operations."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    backoff_base: float = 2.0
    backoff_max: float = 60.0
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )


class RetryHandler:
    """Handles retry logic with exponential backoff.

    This class provides retry functionality for async operations with
    configurable exponential backoff and maximum retry attempts.
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize retry handler.

        Args:
            config: Retry configuration. Uses defaults if None.
        """
        self.config = config or RetryConfig()
        self._logger = logger.bind(component="retry_handler")

    async def execute_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str = "operation",
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> T:
        """Execute an async operation with retry logic.

        Args:
            operation: Async callable to execute
            operation_name: Name of operation for logging
            on_retry: Optional callback called on each retry with attempt number and exception

        Returns:
            Result of the operation

        Raises:
            Exception: The last exception if all retries are exhausted
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                self._logger.debug(
                    "retry_attempt_start",
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=self.config.max_attempts,
                )

                result = await operation()

                if attempt > 1:
                    self._logger.info(
                        "retry_success",
                        operation=operation_name,
                        attempt=attempt,
                        total_attempts=attempt,
                    )

                return result

            except Exception as e:
                last_exception = e
                is_retryable = isinstance(e, self.config.retryable_exceptions)

                self._logger.warning(
                    "retry_attempt_failed",
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=self.config.max_attempts,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    retryable=is_retryable,
                )

                # If not retryable or last attempt, raise immediately
                if not is_retryable or attempt >= self.config.max_attempts:
                    self._logger.error(
                        "retry_exhausted",
                        operation=operation_name,
                        total_attempts=attempt,
                        error_type=type(e).__name__,
                    )
                    raise

                # Call the on_retry callback if provided
                if on_retry:
                    try:
                        on_retry(attempt, e)
                    except Exception as callback_error:
                        self._logger.warning(
                            "retry_callback_error",
                            error=str(callback_error),
                        )

                # Calculate backoff delay with exponential increase
                backoff_delay = min(
                    self.config.backoff_base ** (attempt - 1),
                    self.config.backoff_max,
                )

                self._logger.info(
                    "retry_backoff",
                    operation=operation_name,
                    attempt=attempt,
                    backoff_seconds=backoff_delay,
                )

                await asyncio.sleep(backoff_delay)

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Retry failed for {operation_name} with no exception recorded")

    async def execute_with_timeout(
        self,
        operation: Callable[[], Any],
        timeout_seconds: float,
        operation_name: str = "operation",
    ) -> T:
        """Execute an async operation with a timeout.

        Args:
            operation: Async callable to execute
            timeout_seconds: Timeout in seconds
            operation_name: Name of operation for logging

        Returns:
            Result of the operation

        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        try:
            return await asyncio.wait_for(operation(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            self._logger.error(
                "operation_timeout",
                operation=operation_name,
                timeout_seconds=timeout_seconds,
            )
            raise

    async def execute_with_retry_and_timeout(
        self,
        operation: Callable[[], Any],
        timeout_seconds: float,
        operation_name: str = "operation",
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> T:
        """Execute an async operation with both retry logic and timeout.

        Args:
            operation: Async callable to execute
            timeout_seconds: Timeout in seconds for each attempt
            operation_name: Name of operation for logging
            on_retry: Optional callback called on each retry

        Returns:
            Result of the operation

        Raises:
            Exception: The last exception if all retries are exhausted
            asyncio.TimeoutError: If operation exceeds timeout
        """

        async def operation_with_timeout() -> T:
            return await self.execute_with_timeout(operation, timeout_seconds, operation_name)

        return await self.execute_with_retry(operation_with_timeout, operation_name, on_retry)
