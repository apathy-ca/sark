"""Tests for SIEM optimizer with compression and health monitoring."""

import asyncio
from datetime import UTC, datetime
import gzip
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.base import SIEMHealth
from sark.services.audit.siem.circuit_breaker import CircuitBreakerConfig, CircuitBreakerError
from sark.services.audit.siem.optimizer import (
    CompressionConfig,
    HealthMonitorConfig,
    SIEMOptimizer,
    estimate_event_size,
    get_optimal_batch_size,
)


class TestCompressionConfig:
    """Tests for CompressionConfig."""

    def test_default_config(self):
        """Test default compression configuration."""
        config = CompressionConfig()
        assert config.enabled is True
        assert config.min_size_bytes == 1024
        assert config.compression_level == 6

    def test_custom_config(self):
        """Test custom compression configuration."""
        config = CompressionConfig(
            enabled=False,
            min_size_bytes=2048,
            compression_level=9,
        )
        assert config.enabled is False
        assert config.min_size_bytes == 2048
        assert config.compression_level == 9


class TestHealthMonitorConfig:
    """Tests for HealthMonitorConfig."""

    def test_default_config(self):
        """Test default health monitor configuration."""
        config = HealthMonitorConfig()
        assert config.enabled is True
        assert config.check_interval_seconds == 30
        assert config.failure_threshold == 3

    def test_custom_config(self):
        """Test custom health monitor configuration."""
        config = HealthMonitorConfig(
            enabled=False,
            check_interval_seconds=60,
            failure_threshold=5,
        )
        assert config.enabled is False
        assert config.check_interval_seconds == 60
        assert config.failure_threshold == 5


class TestSIEMOptimizer:
    """Tests for SIEMOptimizer."""

    @pytest.fixture
    def mock_siem(self) -> MagicMock:
        """Create mock SIEM."""
        siem = MagicMock()
        siem.send_event = AsyncMock(return_value=True)
        siem.send_batch = AsyncMock(return_value=True)
        siem.health_check = AsyncMock(return_value=SIEMHealth(healthy=True, latency_ms=10.0))
        return siem

    @pytest.fixture
    def audit_event(self) -> AuditEvent:
        """Create test audit event."""
        return AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test@example.com",
            tool_name="bash",
            details={"command": "ls -la", "exit_code": 0},
        )

    @pytest.fixture
    def optimizer(self, mock_siem: MagicMock) -> SIEMOptimizer:
        """Create optimizer for testing."""
        return SIEMOptimizer(
            siem=mock_siem,
            name="test",
            compression_config=CompressionConfig(min_size_bytes=100),
            health_config=HealthMonitorConfig(
                check_interval_seconds=1, failure_threshold=2  # Fast for testing
            ),
            circuit_config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1),
        )

    @pytest.mark.asyncio
    async def test_send_event_success(self, optimizer: SIEMOptimizer, audit_event: AuditEvent):
        """Test successful event send."""
        result = await optimizer.send_event(audit_event)
        assert result is True
        optimizer.siem.send_event.assert_called_once_with(audit_event)

    @pytest.mark.asyncio
    async def test_send_batch_success(self, optimizer: SIEMOptimizer, audit_event: AuditEvent):
        """Test successful batch send."""
        events = [audit_event]
        result = await optimizer.send_batch(events)
        assert result is True
        optimizer.siem.send_batch.assert_called_once_with(events)

    @pytest.mark.asyncio
    async def test_send_event_with_circuit_breaker(
        self, optimizer: SIEMOptimizer, audit_event: AuditEvent
    ):
        """Test event send triggers circuit breaker on failures."""
        optimizer.siem.send_event.side_effect = Exception("Network error")

        # Fail 3 times to open circuit
        for _i in range(3):
            with pytest.raises(Exception):
                await optimizer.send_event(audit_event)

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await optimizer.send_event(audit_event)

        metrics = optimizer.get_metrics()
        assert metrics["circuit_breaker_blocks"] == 1

    def test_compress_payload_small(self, optimizer: SIEMOptimizer):
        """Test small payload is not compressed."""
        data = "small data"
        compressed, metadata = optimizer.compress_payload(data)

        assert metadata["compressed"] is False
        assert metadata["original_size"] == len(data.encode("utf-8"))
        assert compressed == data.encode("utf-8")

    def test_compress_payload_large(self, optimizer: SIEMOptimizer):
        """Test large payload is compressed."""
        # Create data > 100 bytes (min_size_bytes in fixture)
        data = "x" * 200
        compressed, metadata = optimizer.compress_payload(data)

        assert metadata["compressed"] is True
        assert metadata["original_size"] == 200
        assert metadata["compressed_size"] < 200
        assert metadata["bytes_saved"] > 0
        assert 0 < metadata["compression_ratio"] < 1.0

        # Verify it's actually gzipped
        decompressed = gzip.decompress(compressed).decode("utf-8")
        assert decompressed == data

    def test_compress_payload_disabled(self, mock_siem: MagicMock):
        """Test compression can be disabled."""
        optimizer = SIEMOptimizer(
            siem=mock_siem,
            name="test",
            compression_config=CompressionConfig(enabled=False),
        )

        data = "x" * 2000  # Large data
        compressed, metadata = optimizer.compress_payload(data)

        assert metadata["compressed"] is False
        assert compressed == data.encode("utf-8")

    def test_compress_payload_bytes_input(self, optimizer: SIEMOptimizer):
        """Test compression with bytes input."""
        data = b"x" * 200
        _compressed, metadata = optimizer.compress_payload(data)

        assert metadata["compressed"] is True
        assert metadata["original_size"] == 200

    @pytest.mark.asyncio
    async def test_health_monitoring_start_stop(self, optimizer: SIEMOptimizer):
        """Test starting and stopping health monitoring."""
        await optimizer.start_health_monitoring()
        assert optimizer._health_check_running is True
        assert optimizer._health_monitor_task is not None

        await optimizer.stop_health_monitoring()
        assert optimizer._health_check_running is False

    @pytest.mark.asyncio
    async def test_health_monitoring_success(self, optimizer: SIEMOptimizer):
        """Test health monitoring with successful checks."""
        await optimizer.start_health_monitoring()

        # Wait for at least one health check
        await asyncio.sleep(1.2)

        assert optimizer.is_healthy() is True
        assert optimizer._last_health_check is not None
        assert optimizer._last_health_status is not None
        assert optimizer._consecutive_health_failures == 0

        await optimizer.stop_health_monitoring()

    @pytest.mark.asyncio
    async def test_health_monitoring_failure(self, optimizer: SIEMOptimizer):
        """Test health monitoring with failed checks."""
        # Make health check fail
        optimizer.siem.health_check.return_value = SIEMHealth(
            healthy=False, latency_ms=0, error_message="Connection failed"
        )

        await optimizer.start_health_monitoring()

        # Wait for 2 failed checks (threshold)
        await asyncio.sleep(2.5)

        assert optimizer.is_healthy() is False
        assert optimizer._consecutive_health_failures >= 2

        await optimizer.stop_health_monitoring()

    @pytest.mark.asyncio
    async def test_health_monitoring_recovery(self, optimizer: SIEMOptimizer):
        """Test health monitoring recovery after failures."""
        # Start with failures
        optimizer.siem.health_check.return_value = SIEMHealth(
            healthy=False, latency_ms=0, error_message="Error"
        )

        await optimizer.start_health_monitoring()
        await asyncio.sleep(2.5)  # Wait for 2 failures (threshold)

        assert optimizer.is_healthy() is False

        # Recover
        optimizer.siem.health_check.return_value = SIEMHealth(healthy=True, latency_ms=10.0)

        await asyncio.sleep(1.2)

        assert optimizer.is_healthy() is True
        assert optimizer._consecutive_health_failures == 0

        await optimizer.stop_health_monitoring()

    @pytest.mark.asyncio
    async def test_health_monitoring_disabled(self, mock_siem: MagicMock):
        """Test health monitoring can be disabled."""
        optimizer = SIEMOptimizer(
            siem=mock_siem,
            name="test",
            health_config=HealthMonitorConfig(enabled=False),
        )

        await optimizer.start_health_monitoring()
        assert optimizer._health_check_running is False

    def test_get_metrics(self, optimizer: SIEMOptimizer):
        """Test get_metrics returns complete information."""
        metrics = optimizer.get_metrics()

        assert metrics["siem"] == "test"
        assert "compression" in metrics
        assert "circuit_breaker" in metrics
        assert "health" in metrics

        # Compression metrics
        assert metrics["compression"]["enabled"] is True
        assert metrics["compression"]["count"] == 0
        assert metrics["compression"]["bytes_saved"] == 0

        # Circuit breaker metrics
        assert metrics["circuit_breaker"]["state"] == "closed"
        assert metrics["circuit_breaker"]["failure_count"] == 0

        # Health metrics
        assert metrics["health"]["enabled"] is True
        assert metrics["health"]["is_healthy"] is True

    def test_get_metrics_with_compression(self, optimizer: SIEMOptimizer):
        """Test metrics after compression."""
        data = "x" * 200
        optimizer.compress_payload(data)

        metrics = optimizer.get_metrics()
        assert metrics["compression"]["count"] == 1
        assert metrics["compression"]["bytes_saved"] > 0
        assert metrics["compression"]["total_sends"] == 1
        assert metrics["compression"]["compression_rate"] > 0

    def test_reset_metrics(self, optimizer: SIEMOptimizer):
        """Test reset_metrics clears counters."""
        # Generate some metrics
        data = "x" * 200
        optimizer.compress_payload(data)

        assert optimizer._compression_count == 1

        # Reset
        optimizer.reset_metrics()

        assert optimizer._compression_count == 0
        assert optimizer._compression_bytes_saved == 0
        assert optimizer._uncompressed_sends == 0


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_optimal_batch_size_small_events(self):
        """Test optimal batch size for small events."""
        # 500 byte events, 100KB target = ~200 events
        batch_size = get_optimal_batch_size(avg_event_size_bytes=500, target_batch_size_kb=100)
        assert 150 <= batch_size <= 250

    def test_get_optimal_batch_size_large_events(self):
        """Test optimal batch size for large events."""
        # 10KB events, 100KB target = ~10 events
        batch_size = get_optimal_batch_size(avg_event_size_bytes=10240, target_batch_size_kb=100)
        assert 10 <= batch_size <= 15

    def test_get_optimal_batch_size_clamping(self):
        """Test batch size is clamped to reasonable range."""
        # Very small events
        batch_size = get_optimal_batch_size(avg_event_size_bytes=10, target_batch_size_kb=100)
        assert batch_size <= 1000  # Max clamp

        # Very large events
        batch_size = get_optimal_batch_size(avg_event_size_bytes=100000, target_batch_size_kb=100)
        assert batch_size >= 10  # Min clamp

    def test_estimate_event_size(self):
        """Test event size estimation."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test@example.com",
            tool_name="bash",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            request_id="req-123",
            details={"key": "value"},
        )

        size = estimate_event_size(event)
        assert size > 200  # Base size + fields
        assert isinstance(size, int)

    def test_estimate_event_size_minimal(self):
        """Test size estimation for minimal event."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.LOW,
        )

        size = estimate_event_size(event)
        assert size >= 200  # Base size
        assert isinstance(size, int)

    def test_estimate_event_size_large_details(self):
        """Test size estimation with large details."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.LOW,
            details={"data": "x" * 1000},  # Large details
        )

        size = estimate_event_size(event)
        assert size > 1200  # Base + large details
