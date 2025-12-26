"""Audit and SIEM metrics for Gateway."""

from prometheus_client import Counter, Gauge, Histogram, Summary

# ============================================================================
# Audit Writing Metrics
# ============================================================================

audit_events_written_total = Counter(
    "sark_audit_events_written_total",
    "Total audit events written",
    ["event_type", "destination"],
)

audit_write_duration_seconds = Histogram(
    "sark_audit_write_duration_seconds",
    "Audit write duration in seconds",
    ["destination"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

audit_write_errors_total = Counter(
    "sark_audit_write_errors_total",
    "Audit write errors",
    ["destination", "error_type"],
)

audit_events_per_second = Summary(
    "sark_audit_events_per_second",
    "Audit events written per second",
)

# ============================================================================
# Audit Queue Metrics
# ============================================================================

audit_queue_depth = Gauge(
    "sark_audit_queue_depth",
    "Number of events in audit queue",
)

audit_queue_capacity = Gauge(
    "sark_audit_queue_capacity",
    "Audit queue capacity",
)

audit_queue_drops_total = Counter(
    "sark_audit_queue_drops_total",
    "Events dropped due to queue full",
)

# ============================================================================
# SIEM Integration Metrics
# ============================================================================

siem_forwards_total = Counter(
    "sark_siem_forwards_total",
    "Total SIEM forwards",
    ["siem_platform", "status"],
)

siem_forward_duration_seconds = Histogram(
    "sark_siem_forward_duration_seconds",
    "SIEM forward duration in seconds",
    ["siem_platform"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

siem_batch_size = Histogram(
    "sark_siem_batch_size",
    "Number of events per SIEM batch",
    ["siem_platform"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

siem_connection_status = Gauge(
    "sark_siem_connection_status",
    "SIEM connection status (1=connected, 0=disconnected)",
    ["siem_platform"],
)

siem_backpressure_events = Gauge(
    "sark_siem_backpressure_events",
    "Events waiting to be forwarded to SIEM",
    ["siem_platform"],
)

# ============================================================================
# Audit Log Management Metrics
# ============================================================================

audit_log_size_bytes = Gauge(
    "sark_audit_log_size_bytes",
    "Audit log size in bytes",
)

audit_log_rotations_total = Counter(
    "sark_audit_log_rotations_total",
    "Audit log rotations",
)

audit_retention_purges_total = Counter(
    "sark_audit_retention_purges_total",
    "Events purged due to retention policy",
)

audit_storage_utilization = Gauge(
    "sark_audit_storage_utilization",
    "Audit storage utilization percentage",
)


class AuditMetricsCollector:
    """Metrics collector for audit and SIEM operations."""

    def record_audit_write(
        self,
        event_type: str,
        destination: str,
        duration: float,
        success: bool = True,
        error_type: str | None = None,
    ):
        """
        Record an audit event write.

        Args:
            event_type: Type of audit event
            destination: database, file, siem
            duration: Write duration in seconds
            success: Whether write succeeded
            error_type: Type of error (if failed)
        """
        if success:
            audit_events_written_total.labels(
                event_type=event_type,
                destination=destination,
            ).inc()

        audit_write_duration_seconds.labels(
            destination=destination,
        ).observe(duration)

        if not success and error_type:
            audit_write_errors_total.labels(
                destination=destination,
                error_type=error_type,
            ).inc()

    def update_queue_depth(self, depth: int):
        """
        Update audit queue depth.

        Args:
            depth: Number of events in queue
        """
        audit_queue_depth.set(depth)

    def update_queue_capacity(self, capacity: int):
        """
        Update audit queue capacity.

        Args:
            capacity: Queue capacity
        """
        audit_queue_capacity.set(capacity)

    def record_queue_drop(self):
        """Record a queue drop event."""
        audit_queue_drops_total.inc()

    def record_siem_forward(
        self,
        siem_platform: str,
        duration: float,
        batch_size: int,
        success: bool = True,
    ):
        """
        Record SIEM forward.

        Args:
            siem_platform: splunk, datadog, elastic
            duration: Forward duration in seconds
            batch_size: Number of events in batch
            success: Whether forward succeeded
        """
        status = "success" if success else "error"

        siem_forwards_total.labels(
            siem_platform=siem_platform,
            status=status,
        ).inc()

        siem_forward_duration_seconds.labels(
            siem_platform=siem_platform,
        ).observe(duration)

        siem_batch_size.labels(
            siem_platform=siem_platform,
        ).observe(batch_size)

    def update_siem_connection(self, siem_platform: str, connected: bool):
        """
        Update SIEM connection status.

        Args:
            siem_platform: SIEM platform name
            connected: Connection status
        """
        siem_connection_status.labels(
            siem_platform=siem_platform,
        ).set(1 if connected else 0)

    def update_siem_backpressure(self, siem_platform: str, event_count: int):
        """
        Update SIEM backpressure metric.

        Args:
            siem_platform: SIEM platform name
            event_count: Number of events waiting
        """
        siem_backpressure_events.labels(
            siem_platform=siem_platform,
        ).set(event_count)

    def update_log_size(self, size_bytes: int):
        """
        Update audit log size.

        Args:
            size_bytes: Log size in bytes
        """
        audit_log_size_bytes.set(size_bytes)

    def record_log_rotation(self):
        """Record a log rotation."""
        audit_log_rotations_total.inc()

    def record_retention_purge(self, event_count: int = 1):
        """
        Record retention policy purge.

        Args:
            event_count: Number of events purged
        """
        audit_retention_purges_total.inc(event_count)

    def update_storage_utilization(self, utilization_percent: float):
        """
        Update storage utilization.

        Args:
            utilization_percent: Utilization percentage (0-100)
        """
        audit_storage_utilization.set(utilization_percent)


# Global instance
_collector = AuditMetricsCollector()


# Convenience functions
def record_audit_write(
    event_type: str,
    destination: str,
    duration: float,
    success: bool = True,
    error_type: str | None = None,
):
    """Record an audit write."""
    _collector.record_audit_write(event_type, destination, duration, success, error_type)


def record_siem_forward(
    siem_platform: str,
    duration: float,
    batch_size: int,
    success: bool = True,
):
    """Record a SIEM forward."""
    _collector.record_siem_forward(siem_platform, duration, batch_size, success)
