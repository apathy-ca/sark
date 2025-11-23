"""SIEM integration load testing - 10,000 events/min validation.

This test validates that the SIEM integration can handle the required
throughput of 10,000 events per minute (167 events/second) with all
optimizations enabled:
- Event batching
- Gzip compression
- Circuit breaker
- Health monitoring
- Error handling with fallback

Run against real SIEM instances to validate production readiness.

Setup:
    # For Splunk
    export SPLUNK_HEC_URL="https://your-instance.splunkcloud.com:8088/services/collector"
    export SPLUNK_HEC_TOKEN="your-hec-token"
    export SPLUNK_INDEX="sark_load_test"

    # For Datadog
    export DATADOG_API_KEY="your-api-key"
    export DATADOG_SITE="datadoghq.com"

Run tests:
    pytest tests/integration/test_siem_load.py -v -s

Run specific SIEM:
    pytest tests/integration/test_siem_load.py::TestSplunkLoad -v -s
    pytest tests/integration/test_siem_load.py::TestDatadogLoad -v -s
"""

from datetime import UTC, datetime
import os
from pathlib import Path
import time
from uuid import uuid4

import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem import (
    BatchConfig,
    BatchHandler,
    CircuitBreakerConfig,
    CompressionConfig,
    DatadogConfig,
    DatadogSIEM,
    ErrorAlert,
    HealthMonitorConfig,
    SIEMErrorHandler,
    SIEMOptimizer,
    SplunkConfig,
    SplunkSIEM,
    high_error_rate_condition,
)

# Test configuration
TOTAL_EVENTS = 10_000  # Target: 10k events
TARGET_DURATION_SECONDS = 60  # Should complete in ~60 seconds
MIN_THROUGHPUT_PER_MINUTE = 9_500  # Allow 5% margin (95% of 10k)
BATCH_SIZE = 100  # Optimal batch size
MAX_CONCURRENCY = 10  # Concurrent workers

# Check for credentials
HAS_SPLUNK = all([os.getenv("SPLUNK_HEC_URL"), os.getenv("SPLUNK_HEC_TOKEN")])
HAS_DATADOG = bool(os.getenv("DATADOG_API_KEY"))

requires_splunk = pytest.mark.skipif(not HAS_SPLUNK, reason="Splunk credentials not configured")
requires_datadog = pytest.mark.skipif(not HAS_DATADOG, reason="Datadog credentials not configured")


class LoadTestMetrics:
    """Track load test metrics."""

    def __init__(self):
        """Initialize metrics tracking."""
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.events_sent = 0
        self.events_failed = 0
        self.batches_sent = 0
        self.batches_failed = 0
        self.total_bytes_sent = 0
        self.total_bytes_compressed = 0
        self.errors: list[str] = []
        self.latencies: list[float] = []

    def start(self):
        """Start timing."""
        self.start_time = time.time()

    def stop(self):
        """Stop timing."""
        self.end_time = time.time()

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def events_per_second(self) -> float:
        """Get events per second."""
        if self.duration_seconds == 0:
            return 0.0
        return self.events_sent / self.duration_seconds

    @property
    def events_per_minute(self) -> float:
        """Get events per minute."""
        return self.events_per_second * 60

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        total = self.events_sent + self.events_failed
        if total == 0:
            return 0.0
        return (self.events_sent / total) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Get average latency in milliseconds."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p95_latency_ms(self) -> float:
        """Get 95th percentile latency in milliseconds."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    def print_report(self, siem_name: str):
        """Print detailed load test report."""
        print(f"\n{'='*70}")
        print(f"📊 {siem_name} Load Test Report")
        print(f"{'='*70}")
        print("\n⏱️  Timing:")
        print(f"   Duration: {self.duration_seconds:.2f}s")
        print("\n📈 Throughput:")
        print(f"   Events sent: {self.events_sent:,}")
        print(f"   Events failed: {self.events_failed:,}")
        print(f"   Success rate: {self.success_rate:.2f}%")
        print(f"   Events/second: {self.events_per_second:.1f}")
        print(f"   Events/minute: {self.events_per_minute:.0f} {'✅' if self.events_per_minute >= MIN_THROUGHPUT_PER_MINUTE else '❌'}")
        print(f"   Target: {TOTAL_EVENTS:,} events in ~{TARGET_DURATION_SECONDS}s")
        print("\n📦 Batching:")
        print(f"   Batches sent: {self.batches_sent:,}")
        print(f"   Batches failed: {self.batches_failed:,}")
        print(f"   Avg batch size: {self.events_sent / self.batches_sent if self.batches_sent > 0 else 0:.1f}")
        print("\n🗜️  Compression:")
        if self.total_bytes_compressed > 0:
            compression_rate = (
                (self.total_bytes_sent - self.total_bytes_compressed) / self.total_bytes_sent * 100
            )
            print(f"   Original size: {self.total_bytes_sent:,} bytes")
            print(f"   Compressed size: {self.total_bytes_compressed:,} bytes")
            print(f"   Compression rate: {compression_rate:.1f}%")
        else:
            print(f"   Total bytes sent: {self.total_bytes_sent:,}")
        print("\n⚡ Latency:")
        print(f"   Average: {self.avg_latency_ms:.2f}ms")
        print(f"   P95: {self.p95_latency_ms:.2f}ms")
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                print(f"   - {error}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more")
        print(f"\n{'='*70}\n")


def create_realistic_event(index: int) -> AuditEvent:
    """Create a realistic audit event for load testing.

    Args:
        index: Event index for uniqueness

    Returns:
        Realistic audit event
    """
    # Vary event types
    event_types = [
        AuditEventType.TOOL_INVOKED,
        AuditEventType.AUTHORIZATION_ALLOWED,
        AuditEventType.AUTHORIZATION_DENIED,
        AuditEventType.SESSION_STARTED,
    ]
    event_type = event_types[index % len(event_types)]

    # Vary severity
    severities = [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH]
    severity = severities[index % len(severities)]

    # Create realistic details based on type
    if event_type == AuditEventType.TOOL_INVOKED:
        details = {
            "command": f"kubectl get pods -n namespace-{index % 10}",
            "exit_code": 0,
            "duration_ms": 50 + (index % 200),
            "output_lines": 10 + (index % 50),
        }
    elif event_type in (AuditEventType.AUTHORIZATION_ALLOWED, AuditEventType.AUTHORIZATION_DENIED):
        details = {
            "resource": f"deployment-{index % 100}",
            "namespace": f"namespace-{index % 10}",
            "action": "create" if index % 2 == 0 else "update",
            "policy_evaluation_ms": 5 + (index % 20),
        }
    else:
        details = {
            "session_id": str(uuid4()),
            "client_version": "1.0.0",
        }

    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=event_type,
        severity=severity,
        user_id=uuid4() if index % 3 == 0 else None,
        user_email=f"load-test-user-{index % 100}@example.com",
        server_id=uuid4(),
        tool_name="kubectl" if event_type == AuditEventType.TOOL_INVOKED else None,
        decision="allow" if index % 4 != 0 else "deny",
        policy_id=uuid4() if index % 2 == 0 else None,
        ip_address=f"10.0.{(index // 256) % 256}.{index % 256}",
        user_agent=f"kubectl/1.{index % 30}.0",
        request_id=str(uuid4()),
        details=details,
    )


@requires_splunk
class TestSplunkLoad:
    """Load test for Splunk SIEM integration."""

    @pytest.fixture
    def splunk_config(self) -> SplunkConfig:
        """Create Splunk configuration."""
        return SplunkConfig(
            hec_url=os.getenv("SPLUNK_HEC_URL", ""),
            hec_token=os.getenv("SPLUNK_HEC_TOKEN", ""),
            index=os.getenv("SPLUNK_INDEX", "sark_load_test"),
            sourcetype="sark:audit:event:load",
            source="sark_load_test",
        )

    @pytest.fixture
    def splunk_siem(self, splunk_config: SplunkConfig) -> SplunkSIEM:
        """Create Splunk SIEM instance."""
        return SplunkSIEM(splunk_config)

    @pytest.mark.asyncio
    async def test_splunk_10k_events_per_minute(self, splunk_siem: SplunkSIEM, tmp_path: Path):
        """Test Splunk can handle 10,000 events per minute with all optimizations."""
        metrics = LoadTestMetrics()

        # Create optimized SIEM with all features
        optimizer = SIEMOptimizer(
            siem=splunk_siem,
            name="splunk-load-test",
            compression_config=CompressionConfig(
                enabled=True,
                min_size_bytes=1024,
                compression_level=6,
            ),
            health_config=HealthMonitorConfig(
                enabled=True,
                check_interval_seconds=30,
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
            ),
        )

        # Create error handler with fallback
        error_handler = SIEMErrorHandler(
            fallback_log_dir=tmp_path / "splunk_fallback",
            enable_fallback=True,
        )

        # Add error alert
        def on_error_alert(errors):
            metrics.errors.append(f"High error rate: {len(errors)} errors")

        error_handler.add_alert(
            ErrorAlert(
                name="high_error_rate",
                condition=lambda e: high_error_rate_condition(e, threshold=10),
                callback=on_error_alert,
            )
        )

        # Create batch handler
        async def send_batch(events):
            try:
                batch_start = time.time()
                result = await optimizer.send_batch(events)
                batch_latency = (time.time() - batch_start) * 1000
                metrics.latencies.append(batch_latency)

                if result:
                    metrics.events_sent += len(events)
                    metrics.batches_sent += 1
                else:
                    metrics.events_failed += len(events)
                    metrics.batches_failed += 1
                return result
            except Exception as e:
                metrics.events_failed += len(events)
                metrics.batches_failed += 1
                metrics.errors.append(str(e))
                await error_handler.handle_error(e)
                return False

        batch_handler = BatchHandler(
            callback=send_batch,
            config=BatchConfig(
                batch_size=BATCH_SIZE,
                batch_timeout_seconds=2,
            ),
        )

        # Start health monitoring and batch handler
        await optimizer.start_health_monitoring()
        await batch_handler.start()

        try:
            print(f"\n🚀 Starting Splunk load test: {TOTAL_EVENTS:,} events")
            metrics.start()

            # Send events
            for i in range(TOTAL_EVENTS):
                event = create_realistic_event(i)
                await batch_handler.enqueue(event)

                # Progress update every 1000 events
                if (i + 1) % 1000 == 0:
                    elapsed = time.time() - metrics.start_time
                    current_rate = (i + 1) / elapsed * 60
                    print(f"   Progress: {i + 1:,}/{TOTAL_EVENTS:,} events ({current_rate:.0f}/min)")

            # Flush remaining batches
            await batch_handler.stop(flush=True)
            metrics.stop()

            # Collect final metrics
            optimizer_metrics = optimizer.get_metrics()
            metrics.total_bytes_sent = optimizer_metrics["compression"]["total_bytes_before"]
            metrics.total_bytes_compressed = optimizer_metrics["compression"]["total_bytes_after"]

            # Print report
            metrics.print_report("Splunk")

            # Assertions
            assert metrics.events_per_minute >= MIN_THROUGHPUT_PER_MINUTE, (
                f"Throughput {metrics.events_per_minute:.0f}/min below target {MIN_THROUGHPUT_PER_MINUTE:,}/min"
            )
            assert metrics.success_rate >= 95.0, f"Success rate {metrics.success_rate:.2f}% below 95%"
            assert optimizer_metrics["health"]["is_healthy"], "SIEM should be healthy"
            assert optimizer_metrics["circuit_breaker"]["state"] == "closed", "Circuit should be closed"

        finally:
            await optimizer.stop_health_monitoring()
            if batch_handler._running:
                await batch_handler.stop(flush=False)


@requires_datadog
class TestDatadogLoad:
    """Load test for Datadog SIEM integration."""

    @pytest.fixture
    def datadog_config(self) -> DatadogConfig:
        """Create Datadog configuration."""
        return DatadogConfig(
            api_key=os.getenv("DATADOG_API_KEY", ""),
            site=os.getenv("DATADOG_SITE", "datadoghq.com"),
            service="sark_load_test",
            environment="load_test",
        )

    @pytest.fixture
    def datadog_siem(self, datadog_config: DatadogConfig) -> DatadogSIEM:
        """Create Datadog SIEM instance."""
        return DatadogSIEM(datadog_config)

    @pytest.mark.asyncio
    async def test_datadog_10k_events_per_minute(self, datadog_siem: DatadogSIEM, tmp_path: Path):
        """Test Datadog can handle 10,000 events per minute with all optimizations."""
        metrics = LoadTestMetrics()

        # Create optimized SIEM with all features
        optimizer = SIEMOptimizer(
            siem=datadog_siem,
            name="datadog-load-test",
            compression_config=CompressionConfig(
                enabled=True,
                min_size_bytes=1024,
                compression_level=6,
            ),
            health_config=HealthMonitorConfig(
                enabled=True,
                check_interval_seconds=30,
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
            ),
        )

        # Create error handler with fallback
        error_handler = SIEMErrorHandler(
            fallback_log_dir=tmp_path / "datadog_fallback",
            enable_fallback=True,
        )

        # Add error alert
        def on_error_alert(errors):
            metrics.errors.append(f"High error rate: {len(errors)} errors")

        error_handler.add_alert(
            ErrorAlert(
                name="high_error_rate",
                condition=lambda e: high_error_rate_condition(e, threshold=10),
                callback=on_error_alert,
            )
        )

        # Create batch handler
        async def send_batch(events):
            try:
                batch_start = time.time()
                result = await optimizer.send_batch(events)
                batch_latency = (time.time() - batch_start) * 1000
                metrics.latencies.append(batch_latency)

                if result:
                    metrics.events_sent += len(events)
                    metrics.batches_sent += 1
                else:
                    metrics.events_failed += len(events)
                    metrics.batches_failed += 1
                return result
            except Exception as e:
                metrics.events_failed += len(events)
                metrics.batches_failed += 1
                metrics.errors.append(str(e))
                await error_handler.handle_error(e)
                return False

        batch_handler = BatchHandler(
            callback=send_batch,
            config=BatchConfig(
                batch_size=BATCH_SIZE,
                batch_timeout_seconds=2,
            ),
        )

        # Start health monitoring and batch handler
        await optimizer.start_health_monitoring()
        await batch_handler.start()

        try:
            print(f"\n🚀 Starting Datadog load test: {TOTAL_EVENTS:,} events")
            metrics.start()

            # Send events
            for i in range(TOTAL_EVENTS):
                event = create_realistic_event(i)
                await batch_handler.enqueue(event)

                # Progress update every 1000 events
                if (i + 1) % 1000 == 0:
                    elapsed = time.time() - metrics.start_time
                    current_rate = (i + 1) / elapsed * 60
                    print(f"   Progress: {i + 1:,}/{TOTAL_EVENTS:,} events ({current_rate:.0f}/min)")

            # Flush remaining batches
            await batch_handler.stop(flush=True)
            metrics.stop()

            # Collect final metrics
            optimizer_metrics = optimizer.get_metrics()
            metrics.total_bytes_sent = optimizer_metrics["compression"]["total_bytes_before"]
            metrics.total_bytes_compressed = optimizer_metrics["compression"]["total_bytes_after"]

            # Print report
            metrics.print_report("Datadog")

            # Assertions
            assert metrics.events_per_minute >= MIN_THROUGHPUT_PER_MINUTE, (
                f"Throughput {metrics.events_per_minute:.0f}/min below target {MIN_THROUGHPUT_PER_MINUTE:,}/min"
            )
            assert metrics.success_rate >= 95.0, f"Success rate {metrics.success_rate:.2f}% below 95%"
            assert optimizer_metrics["health"]["is_healthy"], "SIEM should be healthy"
            assert optimizer_metrics["circuit_breaker"]["state"] == "closed", "Circuit should be closed"

        finally:
            await optimizer.stop_health_monitoring()
            if batch_handler._running:
                await batch_handler.stop(flush=False)


if __name__ == "__main__":
    """Run load tests manually."""
    import sys

    print("="*70)
    print("SIEM Load Testing - 10,000 events/minute validation")
    print("="*70)

    if not HAS_SPLUNK and not HAS_DATADOG:
        print("\n❌ No SIEM credentials configured")
        print("\nPlease configure at least one SIEM:")
        print("\nSplunk:")
        print("  export SPLUNK_HEC_URL='https://your-instance.splunkcloud.com:8088/services/collector'")
        print("  export SPLUNK_HEC_TOKEN='your-hec-token'")
        print("  export SPLUNK_INDEX='sark_load_test'")
        print("\nDatadog:")
        print("  export DATADOG_API_KEY='your-api-key'")
        print("  export DATADOG_SITE='datadoghq.com'")
        sys.exit(1)

    if HAS_SPLUNK:
        print(f"\n✅ Splunk configured: {os.getenv('SPLUNK_HEC_URL')}")
    if HAS_DATADOG:
        print(f"\n✅ Datadog configured: {os.getenv('DATADOG_SITE', 'datadoghq.com')}")

    print("\nTest configuration:")
    print(f"  Total events: {TOTAL_EVENTS:,}")
    print(f"  Target duration: ~{TARGET_DURATION_SECONDS}s")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Min throughput: {MIN_THROUGHPUT_PER_MINUTE:,}/min")

    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
