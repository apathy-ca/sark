"""SIEM integration framework for audit event forwarding."""

from sark.services.audit.siem.base import BaseSIEM, SIEMConfig, SIEMHealth, SIEMMetrics
from sark.services.audit.siem.batch_handler import BatchConfig, BatchHandler
from sark.services.audit.siem.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
)
from sark.services.audit.siem.datadog import DatadogConfig, DatadogSIEM
from sark.services.audit.siem.optimizer import (
    CompressionConfig,
    HealthMonitorConfig,
    SIEMOptimizer,
    estimate_event_size,
    get_optimal_batch_size,
)
from sark.services.audit.siem.retry_handler import RetryConfig, RetryHandler
from sark.services.audit.siem.splunk import SplunkConfig, SplunkSIEM

__all__ = [
    "BaseSIEM",
    "SIEMConfig",
    "SIEMHealth",
    "SIEMMetrics",
    "BatchHandler",
    "BatchConfig",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitState",
    "CompressionConfig",
    "DatadogConfig",
    "DatadogSIEM",
    "HealthMonitorConfig",
    "RetryHandler",
    "RetryConfig",
    "SIEMOptimizer",
    "SplunkConfig",
    "SplunkSIEM",
    "estimate_event_size",
    "get_optimal_batch_size",
]
