"""SARK Gateway integration."""

from sark.gateway.client import (
    GatewayClient,
    LocalServerClient,
    TransportType,
    TransportMode,
    GatewayClientError,
    TransportNotAvailableError,
)
from sark.gateway.error_handler import (
    GatewayErrorHandler,
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError,
    RetryConfig,
    RetryExhaustedError,
    TimeoutError,
    with_retry,
    with_timeout,
)

__all__ = [
    # Client classes
    "GatewayClient",
    "LocalServerClient",
    # Enums
    "TransportType",
    "TransportMode",
    "CircuitState",
    # Error handler
    "GatewayErrorHandler",
    "CircuitBreaker",
    "RetryConfig",
    # Exceptions
    "GatewayClientError",
    "TransportNotAvailableError",
    "CircuitBreakerError",
    "RetryExhaustedError",
    "TimeoutError",
    # Utility functions
    "with_retry",
    "with_timeout",
]
