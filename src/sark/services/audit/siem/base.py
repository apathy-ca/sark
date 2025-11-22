"""Abstract base class for SIEM integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from pydantic import BaseModel, Field

from sark.models.audit import AuditEvent

logger = structlog.get_logger()


class SIEMConfig(BaseModel):
    """Base SIEM configuration."""

    enabled: bool = Field(default=True, description="Enable SIEM forwarding")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    timeout_seconds: int = Field(default=30, ge=1, le=120, description="Request timeout")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size for events")
    batch_timeout_seconds: int = Field(
        default=5, ge=1, le=60, description="Max time to wait before sending partial batch"
    )
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    retry_backoff_base: float = Field(
        default=2.0, ge=1.0, le=10.0, description="Exponential backoff base"
    )
    retry_backoff_max: float = Field(
        default=60.0, ge=1.0, le=300.0, description="Maximum backoff time in seconds"
    )


class SIEMHealth(BaseModel):
    """SIEM health check status."""

    healthy: bool = Field(description="Overall health status")
    latency_ms: float | None = Field(default=None, description="Health check latency")
    last_check: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = Field(default=None, description="Error message if unhealthy")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional health details")


@dataclass
class SIEMMetrics:
    """Metrics for SIEM operations."""

    events_sent: int = 0
    events_failed: int = 0
    batches_sent: int = 0
    batches_failed: int = 0
    total_latency_ms: float = 0.0
    retry_count: int = 0
    last_success: datetime | None = None
    last_failure: datetime | None = None
    error_counts: dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        total = self.events_sent + self.events_failed
        if total == 0:
            return 0.0
        return (self.events_sent / total) * 100.0

    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.batches_sent == 0:
            return 0.0
        return self.total_latency_ms / self.batches_sent

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for export."""
        return {
            "events_sent": self.events_sent,
            "events_failed": self.events_failed,
            "batches_sent": self.batches_sent,
            "batches_failed": self.batches_failed,
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms,
            "retry_count": self.retry_count,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "error_counts": self.error_counts,
        }


class BaseSIEM(ABC):
    """Abstract base class for SIEM integrations.

    All SIEM implementations (Splunk, Datadog, etc.) must inherit from this class
    and implement the required abstract methods.
    """

    def __init__(self, config: SIEMConfig) -> None:
        """Initialize SIEM with configuration.

        Args:
            config: SIEM configuration settings
        """
        self.config = config
        self.metrics = SIEMMetrics()
        self._logger = logger.bind(siem=self.__class__.__name__)

    @abstractmethod
    async def send_event(self, event: AuditEvent) -> bool:
        """Send a single audit event to the SIEM.

        Args:
            event: Audit event to send

        Returns:
            True if event was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def send_batch(self, events: list[AuditEvent]) -> bool:
        """Send a batch of audit events to the SIEM.

        Args:
            events: List of audit events to send

        Returns:
            True if all events were sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> SIEMHealth:
        """Check connectivity and health of the SIEM.

        Returns:
            Health check results
        """
        pass

    @abstractmethod
    def format_event(self, event: AuditEvent) -> dict[str, Any]:
        """Format an audit event for the specific SIEM.

        Args:
            event: Audit event to format

        Returns:
            Formatted event as dictionary
        """
        pass

    def get_metrics(self) -> SIEMMetrics:
        """Get current metrics.

        Returns:
            Current SIEM metrics
        """
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self.metrics = SIEMMetrics()
        self._logger.info("siem_metrics_reset")

    async def _update_success_metrics(self, event_count: int, latency_ms: float) -> None:
        """Update metrics after successful operation.

        Args:
            event_count: Number of events sent
            latency_ms: Operation latency in milliseconds
        """
        self.metrics.events_sent += event_count
        self.metrics.batches_sent += 1
        self.metrics.total_latency_ms += latency_ms
        self.metrics.last_success = datetime.now(UTC)

    async def _update_failure_metrics(
        self, event_count: int, error_type: str = "unknown"
    ) -> None:
        """Update metrics after failed operation.

        Args:
            event_count: Number of events that failed
            error_type: Type of error that occurred
        """
        self.metrics.events_failed += event_count
        self.metrics.batches_failed += 1
        self.metrics.last_failure = datetime.now(UTC)
        self.metrics.error_counts[error_type] = self.metrics.error_counts.get(error_type, 0) + 1

    async def _update_retry_metrics(self) -> None:
        """Update retry counter."""
        self.metrics.retry_count += 1

    def _convert_event_to_dict(self, event: AuditEvent) -> dict[str, Any]:
        """Convert AuditEvent SQLAlchemy model to dictionary.

        Args:
            event: Audit event to convert

        Returns:
            Event as dictionary
        """
        return {
            "id": str(event.id) if isinstance(event.id, UUID) else event.id,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "event_type": event.event_type.value if event.event_type else None,
            "severity": event.severity.value if event.severity else None,
            "user_id": str(event.user_id) if event.user_id else None,
            "user_email": event.user_email,
            "server_id": str(event.server_id) if event.server_id else None,
            "tool_name": event.tool_name,
            "decision": event.decision,
            "policy_id": str(event.policy_id) if event.policy_id else None,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "request_id": event.request_id,
            "details": event.details or {},
            "siem_forwarded": event.siem_forwarded.isoformat() if event.siem_forwarded else None,
        }
