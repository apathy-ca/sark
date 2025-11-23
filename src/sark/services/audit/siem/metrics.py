"""Prometheus metrics for SIEM operations."""

from prometheus_client import Counter, Gauge, Histogram

# Event forwarding metrics
siem_events_sent_total = Counter(
    "siem_events_sent_total",
    "Total number of events successfully sent to SIEM",
    ["siem_type"],
)

siem_events_failed_total = Counter(
    "siem_events_failed_total",
    "Total number of events that failed to send to SIEM",
    ["siem_type", "error_type"],
)

siem_batches_sent_total = Counter(
    "siem_batches_sent_total",
    "Total number of batches successfully sent to SIEM",
    ["siem_type"],
)

siem_batches_failed_total = Counter(
    "siem_batches_failed_total",
    "Total number of batches that failed to send to SIEM",
    ["siem_type", "error_type"],
)

# Retry metrics
siem_retry_attempts_total = Counter(
    "siem_retry_attempts_total",
    "Total number of retry attempts for SIEM operations",
    ["siem_type"],
)

# Latency metrics
siem_send_latency_seconds = Histogram(
    "siem_send_latency_seconds",
    "Latency of SIEM send operations in seconds",
    ["siem_type", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Health check metrics
siem_health_status = Gauge(
    "siem_health_status",
    "SIEM health status (1=healthy, 0=unhealthy)",
    ["siem_type"],
)

siem_health_check_latency_seconds = Histogram(
    "siem_health_check_latency_seconds",
    "Latency of SIEM health checks in seconds",
    ["siem_type"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Queue metrics (for batch handler)
siem_queue_size = Gauge(
    "siem_queue_size",
    "Current size of SIEM event queue",
    ["siem_type"],
)

siem_events_dropped_total = Counter(
    "siem_events_dropped_total",
    "Total number of events dropped due to queue full",
    ["siem_type"],
)

siem_current_batch_size = Gauge(
    "siem_current_batch_size",
    "Current size of pending batch",
    ["siem_type"],
)


def record_event_sent(siem_type: str, count: int = 1) -> None:
    """Record successful event send.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        count: Number of events sent
    """
    siem_events_sent_total.labels(siem_type=siem_type).inc(count)


def record_event_failed(siem_type: str, error_type: str, count: int = 1) -> None:
    """Record failed event send.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        error_type: Type of error that occurred
        count: Number of events that failed
    """
    siem_events_failed_total.labels(siem_type=siem_type, error_type=error_type).inc(count)


def record_batch_sent(siem_type: str) -> None:
    """Record successful batch send.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
    """
    siem_batches_sent_total.labels(siem_type=siem_type).inc()


def record_batch_failed(siem_type: str, error_type: str) -> None:
    """Record failed batch send.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        error_type: Type of error that occurred
    """
    siem_batches_failed_total.labels(siem_type=siem_type, error_type=error_type).inc()


def record_retry_attempt(siem_type: str) -> None:
    """Record a retry attempt.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
    """
    siem_retry_attempts_total.labels(siem_type=siem_type).inc()


def observe_send_latency(siem_type: str, operation: str, latency_seconds: float) -> None:
    """Record send operation latency.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        operation: Operation type (single, batch)
        latency_seconds: Latency in seconds
    """
    siem_send_latency_seconds.labels(siem_type=siem_type, operation=operation).observe(
        latency_seconds
    )


def set_health_status(siem_type: str, healthy: bool) -> None:
    """Set health status.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        healthy: True if healthy, False otherwise
    """
    siem_health_status.labels(siem_type=siem_type).set(1 if healthy else 0)


def observe_health_check_latency(siem_type: str, latency_seconds: float) -> None:
    """Record health check latency.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        latency_seconds: Latency in seconds
    """
    siem_health_check_latency_seconds.labels(siem_type=siem_type).observe(latency_seconds)


def set_queue_size(siem_type: str, size: int) -> None:
    """Set current queue size.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        size: Current queue size
    """
    siem_queue_size.labels(siem_type=siem_type).set(size)


def record_event_dropped(siem_type: str, count: int = 1) -> None:
    """Record dropped events.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        count: Number of events dropped
    """
    siem_events_dropped_total.labels(siem_type=siem_type).inc(count)


def set_current_batch_size(siem_type: str, size: int) -> None:
    """Set current batch size.

    Args:
        siem_type: Type of SIEM (splunk, datadog, etc.)
        size: Current batch size
    """
    siem_current_batch_size.labels(siem_type=siem_type).set(size)
