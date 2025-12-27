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
    # Client classes
    "GatewayClient",
    "LocalServerClient",
    "GatewayClientError",
    "TransportNotAvailableError",
    "TransportType",
    "TransportMode",
    # Error handling classes
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitState",
    "GatewayErrorHandler",
    "RetryConfig",
    "RetryExhaustedError",
    "TimeoutError",
    "with_retry",
    "with_timeout",
]
