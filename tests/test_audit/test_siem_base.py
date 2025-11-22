"""Tests for BaseSIEM abstract class and related components."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.base import BaseSIEM, SIEMConfig, SIEMHealth, SIEMMetrics


class ConcreteSIEM(BaseSIEM):
    """Concrete implementation of BaseSIEM for testing."""

    def __init__(self, config: SIEMConfig) -> None:
        super().__init__(config)
        self.send_event_mock = AsyncMock(return_value=True)
        self.send_batch_mock = AsyncMock(return_value=True)
        self.health_check_mock = AsyncMock(
            return_value=SIEMHealth(healthy=True, latency_ms=10.0)
        )

    async def send_event(self, event: AuditEvent) -> bool:
        return await self.send_event_mock(event)

    async def send_batch(self, events: list[AuditEvent]) -> bool:
        return await self.send_batch_mock(events)

    async def health_check(self) -> SIEMHealth:
        return await self.health_check_mock()

    def format_event(self, event: AuditEvent) -> dict:
        return self._convert_event_to_dict(event)


@pytest.fixture
def siem_config() -> SIEMConfig:
    """Create a test SIEM configuration."""
    return SIEMConfig(
        enabled=True,
        verify_ssl=True,
        timeout_seconds=30,
        batch_size=100,
        batch_timeout_seconds=5,
        retry_attempts=3,
        retry_backoff_base=2.0,
        retry_backoff_max=60.0,
    )


@pytest.fixture
def siem(siem_config: SIEMConfig) -> ConcreteSIEM:
    """Create a test SIEM instance."""
    return ConcreteSIEM(siem_config)


@pytest.fixture
def audit_event() -> AuditEvent:
    """Create a test audit event."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.SERVER_REGISTERED,
        severity=SeverityLevel.MEDIUM,
        user_id=uuid4(),
        user_email="test@example.com",
        server_id=uuid4(),
        tool_name="test_tool",
        decision="allow",
        policy_id=uuid4(),
        ip_address="192.168.1.1",
        user_agent="TestAgent/1.0",
        request_id="test-request-123",
        details={"key": "value"},
    )


class TestSIEMConfig:
    """Tests for SIEMConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SIEMConfig()
        assert config.enabled is True
        assert config.verify_ssl is True
        assert config.timeout_seconds == 30
        assert config.batch_size == 100
        assert config.batch_timeout_seconds == 5
        assert config.retry_attempts == 3
        assert config.retry_backoff_base == 2.0
        assert config.retry_backoff_max == 60.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SIEMConfig(
            enabled=False,
            verify_ssl=False,
            timeout_seconds=60,
            batch_size=50,
            retry_attempts=5,
        )
        assert config.enabled is False
        assert config.verify_ssl is False
        assert config.timeout_seconds == 60
        assert config.batch_size == 50
        assert config.retry_attempts == 5

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            SIEMConfig(timeout_seconds=0)  # Should be >= 1

        with pytest.raises(ValueError):
            SIEMConfig(batch_size=0)  # Should be >= 1

        with pytest.raises(ValueError):
            SIEMConfig(retry_attempts=-1)  # Should be >= 0


class TestSIEMHealth:
    """Tests for SIEMHealth."""

    def test_healthy_status(self):
        """Test healthy status."""
        health = SIEMHealth(healthy=True, latency_ms=10.5)
        assert health.healthy is True
        assert health.latency_ms == 10.5
        assert health.error_message is None

    def test_unhealthy_status(self):
        """Test unhealthy status."""
        health = SIEMHealth(
            healthy=False,
            latency_ms=None,
            error_message="Connection refused",
        )
        assert health.healthy is False
        assert health.latency_ms is None
        assert health.error_message == "Connection refused"

    def test_health_with_details(self):
        """Test health status with additional details."""
        health = SIEMHealth(
            healthy=True,
            latency_ms=15.0,
            details={"endpoint": "https://example.com", "version": "1.0"},
        )
        assert health.details["endpoint"] == "https://example.com"
        assert health.details["version"] == "1.0"


class TestSIEMMetrics:
    """Tests for SIEMMetrics."""

    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = SIEMMetrics()
        assert metrics.events_sent == 0
        assert metrics.events_failed == 0
        assert metrics.batches_sent == 0
        assert metrics.batches_failed == 0
        assert metrics.total_latency_ms == 0.0
        assert metrics.retry_count == 0
        assert metrics.last_success is None
        assert metrics.last_failure is None
        assert metrics.error_counts == {}

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = SIEMMetrics()
        assert metrics.success_rate == 0.0

        metrics.events_sent = 80
        metrics.events_failed = 20
        assert metrics.success_rate == 80.0

        metrics.events_sent = 100
        metrics.events_failed = 0
        assert metrics.success_rate == 100.0

    def test_average_latency_calculation(self):
        """Test average latency calculation."""
        metrics = SIEMMetrics()
        assert metrics.average_latency_ms == 0.0

        metrics.batches_sent = 10
        metrics.total_latency_ms = 500.0
        assert metrics.average_latency_ms == 50.0

    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = SIEMMetrics(
            events_sent=100,
            events_failed=5,
            batches_sent=10,
            batches_failed=1,
            total_latency_ms=500.0,
            retry_count=3,
        )

        metrics_dict = metrics.to_dict()
        assert metrics_dict["events_sent"] == 100
        assert metrics_dict["events_failed"] == 5
        assert metrics_dict["batches_sent"] == 10
        assert metrics_dict["batches_failed"] == 1
        assert metrics_dict["success_rate"] == pytest.approx(95.24, rel=0.01)
        assert metrics_dict["average_latency_ms"] == 50.0
        assert metrics_dict["retry_count"] == 3


class TestBaseSIEM:
    """Tests for BaseSIEM."""

    @pytest.mark.asyncio
    async def test_send_event(self, siem: ConcreteSIEM, audit_event: AuditEvent):
        """Test sending a single event."""
        result = await siem.send_event(audit_event)
        assert result is True
        siem.send_event_mock.assert_called_once_with(audit_event)

    @pytest.mark.asyncio
    async def test_send_batch(self, siem: ConcreteSIEM, audit_event: AuditEvent):
        """Test sending a batch of events."""
        events = [audit_event, audit_event]
        result = await siem.send_batch(events)
        assert result is True
        siem.send_batch_mock.assert_called_once_with(events)

    @pytest.mark.asyncio
    async def test_health_check(self, siem: ConcreteSIEM):
        """Test health check."""
        health = await siem.health_check()
        assert health.healthy is True
        assert health.latency_ms == 10.0
        siem.health_check_mock.assert_called_once()

    def test_format_event(self, siem: ConcreteSIEM, audit_event: AuditEvent):
        """Test event formatting."""
        formatted = siem.format_event(audit_event)
        assert isinstance(formatted, dict)
        assert formatted["event_type"] == AuditEventType.SERVER_REGISTERED.value
        assert formatted["severity"] == SeverityLevel.MEDIUM.value
        assert formatted["user_email"] == "test@example.com"
        assert formatted["tool_name"] == "test_tool"
        assert formatted["decision"] == "allow"

    def test_get_metrics(self, siem: ConcreteSIEM):
        """Test getting metrics."""
        metrics = siem.get_metrics()
        assert isinstance(metrics, SIEMMetrics)
        assert metrics.events_sent == 0
        assert metrics.events_failed == 0

    def test_reset_metrics(self, siem: ConcreteSIEM):
        """Test resetting metrics."""
        siem.metrics.events_sent = 100
        siem.metrics.events_failed = 5
        siem.reset_metrics()
        assert siem.metrics.events_sent == 0
        assert siem.metrics.events_failed == 0

    @pytest.mark.asyncio
    async def test_update_success_metrics(self, siem: ConcreteSIEM):
        """Test updating success metrics."""
        await siem._update_success_metrics(event_count=10, latency_ms=50.0)
        assert siem.metrics.events_sent == 10
        assert siem.metrics.batches_sent == 1
        assert siem.metrics.total_latency_ms == 50.0
        assert siem.metrics.last_success is not None

    @pytest.mark.asyncio
    async def test_update_failure_metrics(self, siem: ConcreteSIEM):
        """Test updating failure metrics."""
        await siem._update_failure_metrics(event_count=5, error_type="connection_error")
        assert siem.metrics.events_failed == 5
        assert siem.metrics.batches_failed == 1
        assert siem.metrics.last_failure is not None
        assert siem.metrics.error_counts["connection_error"] == 1

    @pytest.mark.asyncio
    async def test_update_retry_metrics(self, siem: ConcreteSIEM):
        """Test updating retry metrics."""
        await siem._update_retry_metrics()
        assert siem.metrics.retry_count == 1
        await siem._update_retry_metrics()
        assert siem.metrics.retry_count == 2

    def test_convert_event_to_dict(self, siem: ConcreteSIEM, audit_event: AuditEvent):
        """Test converting audit event to dictionary."""
        event_dict = siem._convert_event_to_dict(audit_event)
        assert isinstance(event_dict, dict)
        assert "id" in event_dict
        assert "timestamp" in event_dict
        assert "event_type" in event_dict
        assert "severity" in event_dict
        assert event_dict["user_email"] == "test@example.com"
        assert event_dict["details"] == {"key": "value"}

    def test_convert_event_with_none_values(self, siem: ConcreteSIEM):
        """Test converting event with None values."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.CRITICAL,
        )
        event_dict = siem._convert_event_to_dict(event)
        assert event_dict["user_id"] is None
        assert event_dict["server_id"] is None
        assert event_dict["tool_name"] is None
