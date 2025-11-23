"""Integration tests for Splunk Cloud SIEM.

These tests require actual Splunk Cloud credentials and should be run
against a Splunk Cloud trial instance.

Setup:
1. Sign up for Splunk Cloud trial: https://www.splunk.com/en_us/download/splunk-cloud.html
2. Create HEC token in Splunk Web:
   Settings → Data Inputs → HTTP Event Collector → New Token
3. Set environment variables:
   export SPLUNK_HEC_URL="https://your-instance.splunkcloud.com:8088/services/collector"
   export SPLUNK_HEC_TOKEN="your-hec-token"
   export SPLUNK_INDEX="sark_test"

Run tests:
   pytest tests/integration/test_splunk_integration.py -v -s

Skip if no credentials:
   pytest tests/integration/test_splunk_integration.py -v -m "not requires_credentials"
"""

import asyncio
from datetime import UTC, datetime
import os
from uuid import uuid4

import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem import (
    BatchConfig,
    BatchHandler,
    CircuitBreakerConfig,
    CompressionConfig,
    ErrorAlert,
    HealthMonitorConfig,
    SIEMErrorHandler,
    SIEMOptimizer,
    SplunkConfig,
    SplunkSIEM,
    high_error_rate_condition,
)

# Check for credentials
HAS_CREDENTIALS = all([
    os.getenv("SPLUNK_HEC_URL"),
    os.getenv("SPLUNK_HEC_TOKEN"),
])

requires_credentials = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="Splunk credentials not configured. Set SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN."
)


@pytest.fixture
def splunk_config() -> SplunkConfig:
    """Create Splunk configuration from environment."""
    return SplunkConfig(
        hec_url=os.getenv("SPLUNK_HEC_URL", "https://localhost:8088/services/collector"),
        hec_token=os.getenv("SPLUNK_HEC_TOKEN", ""),
        index=os.getenv("SPLUNK_INDEX", "sark_test"),
        sourcetype="sark:audit:event",
        source="sark_integration_test",
        verify_ssl=os.getenv("SPLUNK_VERIFY_SSL", "true").lower() == "true",
    )


@pytest.fixture
def splunk_siem(splunk_config: SplunkConfig) -> SplunkSIEM:
    """Create Splunk SIEM instance."""
    return SplunkSIEM(splunk_config)


@pytest.fixture
def test_event() -> AuditEvent:
    """Create test audit event."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.TOOL_INVOKED,
        severity=SeverityLevel.MEDIUM,
        user_email="integration-test@example.com",
        tool_name="bash",
        server_id=uuid4(),
        decision="allow",
        ip_address="192.168.1.100",
        user_agent="IntegrationTest/1.0",
        request_id=str(uuid4()),
        details={
            "command": "ls -la /var/log",
            "exit_code": 0,
            "test_run": True,
            "test_timestamp": datetime.now(UTC).isoformat(),
        },
    )


class TestSplunkConnection:
    """Test Splunk connectivity."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_health_check(self, splunk_siem: SplunkSIEM):
        """Test Splunk health check."""
        health = await splunk_siem.health_check()

        assert health.healthy is True
        assert health.latency_ms is not None
        assert health.latency_ms < 5000  # Should be under 5 seconds
        assert health.error_message is None

        print("\n✅ Splunk health check passed")
        print(f"   Latency: {health.latency_ms:.2f}ms")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_connectivity_error_handling(self):
        """Test error handling for bad credentials."""
        bad_config = SplunkConfig(
            hec_url=os.getenv("SPLUNK_HEC_URL", "https://localhost:8088/services/collector"),
            hec_token="invalid-token-12345",
            index="test",
        )
        bad_siem = SplunkSIEM(bad_config)

        health = await bad_siem.health_check()
        assert health.healthy is False
        assert health.error_message is not None

        print("\n✅ Error handling works correctly")
        print(f"   Error: {health.error_message}")


class TestSplunkEventFormatting:
    """Test Splunk event formatting."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_single_event_format(self, splunk_siem: SplunkSIEM, test_event: AuditEvent):
        """Test single event formatting and sending."""
        result = await splunk_siem.send_event(test_event)

        assert result is True

        print("\n✅ Single event sent successfully")
        print(f"   Event ID: {test_event.id}")
        print(f"   Type: {test_event.event_type.value}")
        print(f"   Search in Splunk: index={splunk_siem.splunk_config.index} event_id={test_event.id}")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_batch_events_format(self, splunk_siem: SplunkSIEM):
        """Test batch event formatting and sending."""
        events = []
        for i in range(10):
            event = AuditEvent(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                event_type=AuditEventType.TOOL_INVOKED,
                severity=SeverityLevel.LOW,
                user_email=f"test-user-{i}@example.com",
                tool_name="bash",
                details={"batch_index": i, "test_batch": True},
            )
            events.append(event)

        result = await splunk_siem.send_batch(events)

        assert result is True

        print(f"\n✅ Batch of {len(events)} events sent successfully")
        print(f"   Search in Splunk: index={splunk_siem.splunk_config.index} test_batch=true")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_event_with_all_fields(self, splunk_siem: SplunkSIEM):
        """Test event with all possible fields populated."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.AUTHORIZATION_ALLOWED,
            severity=SeverityLevel.HIGH,
            user_id=uuid4(),
            user_email="full-test@example.com",
            server_id=uuid4(),
            tool_name="kubectl",
            decision="allow",
            policy_id=uuid4(),
            ip_address="10.0.0.1",
            user_agent="kubectl/1.28.0",
            request_id=str(uuid4()),
            details={
                "resource": "pods",
                "namespace": "production",
                "action": "create",
                "justification": "Deployment rollout",
                "approved_by": "security-team",
            },
        )

        result = await splunk_siem.send_event(event)

        assert result is True

        print("\n✅ Event with all fields sent successfully")
        print(f"   Event ID: {event.id}")


class TestSplunkWithOptimizations:
    """Test Splunk with performance optimizations."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_with_optimizer(self, splunk_siem: SplunkSIEM, test_event: AuditEvent):
        """Test Splunk with optimizer (compression, circuit breaker, health monitoring)."""
        optimizer = SIEMOptimizer(
            siem=splunk_siem,
            name="splunk-integration-test",
            compression_config=CompressionConfig(
                enabled=True,
                min_size_bytes=1024,
            ),
            health_config=HealthMonitorConfig(
                enabled=True,
                check_interval_seconds=10,
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
            ),
        )

        await optimizer.start_health_monitoring()

        try:
            # Send event
            result = await optimizer.send_event(test_event)
            assert result is True

            # Wait for health check
            await asyncio.sleep(1)

            # Check metrics
            metrics = optimizer.get_metrics()
            assert metrics["health"]["is_healthy"] is True
            assert metrics["circuit_breaker"]["state"] == "closed"

            print("\n✅ Optimizer integration working")
            print(f"   Health: {metrics['health']['is_healthy']}")
            print(f"   Circuit: {metrics['circuit_breaker']['state']}")
            print(f"   Compression rate: {metrics['compression']['compression_rate']:.2%}")

        finally:
            await optimizer.stop_health_monitoring()

    @requires_credentials
    @pytest.mark.asyncio
    async def test_with_error_handler(self, splunk_siem: SplunkSIEM, test_event: AuditEvent, tmp_path):
        """Test Splunk with error handler and fallback."""
        error_handler = SIEMErrorHandler(
            fallback_log_dir=tmp_path,
            enable_fallback=True,
        )

        # Add alert for testing
        alert_fired = []

        def on_alert(errors):
            alert_fired.append(len(errors))

        error_handler.add_alert(ErrorAlert(
            name="test_alert",
            condition=lambda e: high_error_rate_condition(e, threshold=1),
            callback=on_alert,
        ))

        # Send event (should succeed)
        try:
            result = await splunk_siem.send_event(test_event)
            assert result is True
            print("\n✅ Event sent successfully with error handler")

        except Exception as e:
            # If it fails, error handler should handle it
            await error_handler.handle_error(e, event=test_event)

            # Check fallback
            metrics = error_handler.get_metrics()
            assert metrics["total_errors"] > 0

            print("\n⚠️  Error occurred but handled gracefully")
            print(f"   Total errors: {metrics['total_errors']}")
            print(f"   Fallback count: {metrics['fallback_count']}")


class TestSplunkLoadPerformance:
    """Test Splunk performance under load."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_batch_handler_throughput(self, splunk_siem: SplunkSIEM):
        """Test batch handler throughput (1000 events)."""
        events_sent = 0
        send_errors = 0

        async def send_batch(events):
            nonlocal events_sent, send_errors
            try:
                result = await splunk_siem.send_batch(events)
                if result:
                    events_sent += len(events)
                return result
            except Exception as e:
                send_errors += 1
                print(f"Error sending batch: {e}")
                return False

        batch_handler = BatchHandler(
            callback=send_batch,
            config=BatchConfig(
                batch_size=50,
                batch_timeout_seconds=2,
            ),
        )

        await batch_handler.start()

        try:
            # Send 1000 events
            import time
            start_time = time.time()

            for i in range(1000):
                event = AuditEvent(
                    id=uuid4(),
                    timestamp=datetime.now(UTC),
                    event_type=AuditEventType.TOOL_INVOKED,
                    severity=SeverityLevel.LOW,
                    user_email=f"load-test-{i % 10}@example.com",
                    tool_name="bash",
                    details={"index": i, "load_test": True},
                )
                await batch_handler.enqueue(event)

            # Flush remaining
            await batch_handler.stop(flush=True)

            elapsed = time.time() - start_time
            throughput = events_sent / elapsed * 60  # events per minute

            print("\n✅ Load test completed")
            print(f"   Events sent: {events_sent}/1000")
            print(f"   Time: {elapsed:.2f}s")
            print(f"   Throughput: {throughput:.0f} events/min")
            print(f"   Errors: {send_errors}")

            # Should successfully send most events
            assert events_sent >= 950  # Allow for some failures

        finally:
            if batch_handler._running:
                await batch_handler.stop(flush=False)


class TestSplunkQueries:
    """Test Splunk search queries to verify events."""

    @requires_credentials
    def test_search_query_examples(self, splunk_config: SplunkConfig):
        """Print example Splunk search queries."""
        print("\n📊 Splunk Search Queries:")
        print("\n1. View all SARK events:")
        print(f"   index={splunk_config.index} sourcetype={splunk_config.sourcetype}")

        print("\n2. View integration test events:")
        print(f"   index={splunk_config.index} source={splunk_config.source}")

        print("\n3. View recent events (last hour):")
        print(f"   index={splunk_config.index} earliest=-1h")

        print("\n4. Count events by type:")
        print(f"   index={splunk_config.index} | stats count by event_type")

        print("\n5. View high severity events:")
        print(f"   index={splunk_config.index} severity=high OR severity=critical")

        print("\n6. View events for specific user:")
        print(f"   index={splunk_config.index} user_email=integration-test@example.com")


if __name__ == "__main__":
    """Run integration tests manually."""
    import sys

    if not HAS_CREDENTIALS:
        print("❌ Splunk credentials not configured")
        print("\nPlease set environment variables:")
        print("  export SPLUNK_HEC_URL='https://your-instance.splunkcloud.com:8088/services/collector'")
        print("  export SPLUNK_HEC_TOKEN='your-hec-token'")
        print("  export SPLUNK_INDEX='sark_test'")
        sys.exit(1)

    print("🚀 Running Splunk integration tests...")
    print(f"   HEC URL: {os.getenv('SPLUNK_HEC_URL')}")
    print(f"   Index: {os.getenv('SPLUNK_INDEX', 'sark_test')}")

    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
