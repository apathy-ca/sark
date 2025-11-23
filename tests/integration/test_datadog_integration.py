"""Integration tests for Datadog Logs API SIEM.

These tests require actual Datadog API credentials and should be run
against a Datadog free tier or trial account.

Setup:
1. Sign up for Datadog free tier: https://www.datadoghq.com/
2. Create API key in Datadog:
   Organization Settings → API Keys → New Key
3. (Optional) Create Application key:
   Organization Settings → Application Keys → New Key
4. Set environment variables:
   export DATADOG_API_KEY="your-api-key"
   export DATADOG_SITE="datadoghq.com"  # or datadoghq.eu, us3.datadoghq.com, etc.
   export DATADOG_SERVICE="sark_test"

Run tests:
   pytest tests/integration/test_datadog_integration.py -v -s

Skip if no credentials:
   pytest tests/integration/test_datadog_integration.py -v -m "not requires_credentials"
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
    DatadogConfig,
    DatadogSIEM,
    ErrorAlert,
    HealthMonitorConfig,
    SIEMErrorHandler,
    SIEMOptimizer,
    high_error_rate_condition,
)

# Check for credentials
HAS_CREDENTIALS = bool(os.getenv("DATADOG_API_KEY"))

requires_credentials = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="Datadog credentials not configured. Set DATADOG_API_KEY."
)


@pytest.fixture
def datadog_config() -> DatadogConfig:
    """Create Datadog configuration from environment."""
    return DatadogConfig(
        api_key=os.getenv("DATADOG_API_KEY", ""),
        app_key=os.getenv("DATADOG_APP_KEY", ""),
        site=os.getenv("DATADOG_SITE", "datadoghq.com"),
        service=os.getenv("DATADOG_SERVICE", "sark_test"),
        environment="integration_test",
        verify_ssl=os.getenv("DATADOG_VERIFY_SSL", "true").lower() == "true",
    )


@pytest.fixture
def datadog_siem(datadog_config: DatadogConfig) -> DatadogSIEM:
    """Create Datadog SIEM instance."""
    return DatadogSIEM(datadog_config)


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


class TestDatadogConnection:
    """Test Datadog connectivity."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_health_check(self, datadog_siem: DatadogSIEM):
        """Test Datadog health check."""
        health = await datadog_siem.health_check()

        assert health.healthy is True
        assert health.latency_ms is not None
        assert health.latency_ms < 5000  # Should be under 5 seconds
        assert health.error_message is None

        print("\n✅ Datadog health check passed")
        print(f"   Latency: {health.latency_ms:.2f}ms")
        print(f"   Site: {datadog_siem.datadog_config.site}")
        print(f"   Service: {datadog_siem.datadog_config.service}")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_connectivity_error_handling(self):
        """Test error handling for bad credentials."""
        bad_config = DatadogConfig(
            api_key="invalid-api-key-12345",
            site=os.getenv("DATADOG_SITE", "datadoghq.com"),
            service="test",
        )
        bad_siem = DatadogSIEM(bad_config)

        health = await bad_siem.health_check()
        assert health.healthy is False
        assert health.error_message is not None

        print("\n✅ Error handling works correctly")
        print(f"   Error: {health.error_message}")


class TestDatadogEventFormatting:
    """Test Datadog event formatting."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_single_event_format(self, datadog_siem: DatadogSIEM, test_event: AuditEvent):
        """Test single event formatting and sending."""
        result = await datadog_siem.send_event(test_event)

        assert result is True

        print("\n✅ Single event sent successfully")
        print(f"   Event ID: {test_event.id}")
        print(f"   Type: {test_event.event_type.value}")
        print(f"   Search in Datadog: service:{datadog_siem.datadog_config.service} @event_id:{test_event.id}")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_event_format_structure(self, datadog_siem: DatadogSIEM, test_event: AuditEvent):
        """Test event formatting structure."""
        formatted = datadog_siem._format_datadog_event(test_event)

        # Verify Datadog-specific fields
        assert "ddsource" in formatted
        assert "ddtags" in formatted
        assert "service" in formatted
        assert "message" in formatted
        assert "sark" in formatted  # Nested event data

        # Verify top-level searchable fields
        assert "event_id" in formatted
        assert "event_type" in formatted
        assert "severity" in formatted
        assert "user_email" in formatted
        assert "timestamp" in formatted

        # Verify tags format
        tags = formatted["ddtags"]
        assert "env:integration_test" in tags
        assert f"service:{datadog_siem.datadog_config.service}" in tags
        assert "event_type:" in tags
        assert "severity:" in tags

        print("\n✅ Event format structure verified")
        print(f"   Tags: {tags}")
        print(f"   Nested data keys: {list(formatted['sark'].keys())}")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_batch_events_format(self, datadog_siem: DatadogSIEM):
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

        result = await datadog_siem.send_batch(events)

        assert result is True

        print(f"\n✅ Batch of {len(events)} events sent successfully")
        print(f"   Search in Datadog: service:{datadog_siem.datadog_config.service} @sark.details.test_batch:true")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_event_with_all_fields(self, datadog_siem: DatadogSIEM):
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

        result = await datadog_siem.send_event(event)

        assert result is True

        print("\n✅ Event with all fields sent successfully")
        print(f"   Event ID: {event.id}")
        print(f"   Search: service:{datadog_siem.datadog_config.service} @event_id:{event.id}")


class TestDatadogWithOptimizations:
    """Test Datadog with performance optimizations."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_with_optimizer(self, datadog_siem: DatadogSIEM, test_event: AuditEvent):
        """Test Datadog with optimizer (compression, circuit breaker, health monitoring)."""
        optimizer = SIEMOptimizer(
            siem=datadog_siem,
            name="datadog-integration-test",
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
    async def test_compression_with_large_batch(self, datadog_siem: DatadogSIEM):
        """Test compression with large batch of events."""
        optimizer = SIEMOptimizer(
            siem=datadog_siem,
            name="datadog-compression-test",
            compression_config=CompressionConfig(
                enabled=True,
                min_size_bytes=512,  # Lower threshold to test compression
            ),
        )

        # Create large events with lots of details
        events = []
        for i in range(50):
            event = AuditEvent(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                event_type=AuditEventType.TOOL_INVOKED,
                severity=SeverityLevel.MEDIUM,
                user_email=f"compression-test-{i}@example.com",
                tool_name="bash",
                details={
                    "command": f"echo 'This is a test command with lots of output' | tee /tmp/test_{i}.log",
                    "output": "x" * 1000,  # Large output field
                    "environment": {"VAR1": "value1", "VAR2": "value2", "VAR3": "value3"},
                    "metadata": {"key1": "value1", "key2": "value2", "key3": "value3"},
                },
            )
            events.append(event)

        result = await optimizer.send_batch(events)
        assert result is True

        metrics = optimizer.get_metrics()
        print("\n✅ Compression test completed")
        print(f"   Events sent: {len(events)}")
        print(f"   Total bytes saved: {metrics['compression']['total_bytes_saved']}")
        print(f"   Compression rate: {metrics['compression']['compression_rate']:.2%}")

    @requires_credentials
    @pytest.mark.asyncio
    async def test_with_error_handler(self, datadog_siem: DatadogSIEM, test_event: AuditEvent, tmp_path):
        """Test Datadog with error handler and fallback."""
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
            result = await datadog_siem.send_event(test_event)
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


class TestDatadogLoadPerformance:
    """Test Datadog performance under load."""

    @requires_credentials
    @pytest.mark.asyncio
    async def test_batch_handler_throughput(self, datadog_siem: DatadogSIEM):
        """Test batch handler throughput (1000 events)."""
        events_sent = 0
        send_errors = 0

        async def send_batch(events):
            nonlocal events_sent, send_errors
            try:
                result = await datadog_siem.send_batch(events)
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

    @requires_credentials
    @pytest.mark.asyncio
    async def test_concurrent_sending(self, datadog_siem: DatadogSIEM):
        """Test concurrent event sending."""
        async def send_events(batch_id: int, count: int):
            """Send multiple events concurrently."""
            success_count = 0
            for i in range(count):
                event = AuditEvent(
                    id=uuid4(),
                    timestamp=datetime.now(UTC),
                    event_type=AuditEventType.TOOL_INVOKED,
                    severity=SeverityLevel.LOW,
                    user_email=f"concurrent-test-{batch_id}@example.com",
                    tool_name="bash",
                    details={"batch_id": batch_id, "index": i},
                )
                try:
                    result = await datadog_siem.send_event(event)
                    if result:
                        success_count += 1
                except Exception as e:
                    print(f"Error in batch {batch_id}, event {i}: {e}")
            return success_count

        # Send 10 concurrent batches of 10 events each
        import time
        start_time = time.time()

        tasks = [send_events(batch_id, 10) for batch_id in range(10)]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        total_sent = sum(results)

        print("\n✅ Concurrent sending test completed")
        print(f"   Total sent: {total_sent}/100")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Rate: {total_sent/elapsed:.1f} events/sec")

        assert total_sent >= 95  # Allow for some failures


class TestDatadogQueries:
    """Test Datadog log queries to verify events."""

    @requires_credentials
    def test_search_query_examples(self, datadog_config: DatadogConfig):
        """Print example Datadog log search queries."""
        print("\n📊 Datadog Log Search Queries:")
        print("\n1. View all SARK events:")
        print(f"   service:{datadog_config.service} source:sark")

        print("\n2. View integration test events:")
        print(f"   service:{datadog_config.service} env:integration_test")

        print("\n3. View recent events (last hour):")
        print(f"   service:{datadog_config.service} @sark.details.test_run:true")

        print("\n4. Count events by type:")
        print(f"   service:{datadog_config.service} | group by @event_type")

        print("\n5. View high severity events:")
        print(f"   service:{datadog_config.service} @severity:(high OR critical)")

        print("\n6. View events for specific user:")
        print(f"   service:{datadog_config.service} @user_email:integration-test@example.com")

        print("\n7. View load test events:")
        print(f"   service:{datadog_config.service} @sark.details.load_test:true")

        print("\n8. View batch test events:")
        print(f"   service:{datadog_config.service} @sark.details.test_batch:true")


if __name__ == "__main__":
    """Run integration tests manually."""
    import sys

    if not HAS_CREDENTIALS:
        print("❌ Datadog credentials not configured")
        print("\nPlease set environment variables:")
        print("  export DATADOG_API_KEY='your-api-key'")
        print("  export DATADOG_SITE='datadoghq.com'  # or datadoghq.eu, us3.datadoghq.com, etc.")
        print("  export DATADOG_SERVICE='sark_test'")
        sys.exit(1)

    print("🚀 Running Datadog integration tests...")
    print(f"   Site: {os.getenv('DATADOG_SITE', 'datadoghq.com')}")
    print(f"   Service: {os.getenv('DATADOG_SERVICE', 'sark_test')}")

    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
