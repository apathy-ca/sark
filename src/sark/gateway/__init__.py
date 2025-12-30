"""SARK Gateway integration."""

from sark.gateway.client import (
    GatewayClient,
    GatewayClientError,
    LocalServerClient,
    TransportMode,
    TransportNotAvailableError,
    TransportType,
)
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

__all__ = [
    # Error handling classes
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitState",
    # Client classes
    "GatewayClient",
    "GatewayClientError",
    "GatewayErrorHandler",
    "LocalServerClient",
    "RetryConfig",
    "RetryExhaustedError",
    "TimeoutError",
    "TransportMode",
    "TransportNotAvailableError",
    "TransportType",
    "with_retry",
    "with_timeout",
]
