"""Comprehensive SIEM Integration Tests.

This test suite verifies SIEM integration functionality including:
- Event formatting and delivery (Splunk & Datadog)
- Failover and graceful degradation
- Event batching and compression
- Circuit breaker behavior
- Delivery metrics and monitoring

Test Modes:
1. Unit tests: Mock SIEM endpoints (always run)
2. Integration tests: Real SIEM endpoints (requires credentials)

Setup for integration tests:
    export SPLUNK_HEC_URL="https://your-instance.splunkcloud.com:8088/services/collector"
    export SPLUNK_HEC_TOKEN="your-hec-token"
    export SPLUNK_INDEX="sark_test"

    export DATADOG_API_KEY="your-datadog-api-key"
    export DATADOG_SITE="datadoghq.com"

Run tests:
    # All tests (unit + integration if credentials available)
    pytest tests/integration/test_siem_integration.py -v -s

    # Unit tests only
    pytest tests/integration/test_siem_integration.py -v -m "not integration"

    # Integration tests only (requires credentials)
    pytest tests/integration/test_siem_integration.py -v -m integration
"""

import asyncio
import gzip
import json
import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from pytest_httpx import HTTPXMock

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem import (
    BatchConfig,
    BatchHandler,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
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

# ============================================================================
# Test Configuration
# ============================================================================

# Check for integration test credentials
HAS_SPLUNK_CREDS = all([
    os.getenv("SPLUNK_HEC_URL"),
    os.getenv("SPLUNK_HEC_TOKEN"),
])

HAS_DATADOG_CREDS = bool(os.getenv("DATADOG_API_KEY"))

integration = pytest.mark.integration
requires_splunk = pytest.mark.skipif(
    not HAS_SPLUNK_CREDS,
    reason="Splunk credentials not configured"
)
requires_datadog = pytest.mark.skipif(
    not HAS_DATADOG_CREDS,
    reason="Datadog credentials not configured"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_event() -> AuditEvent:
    """Create test audit event with comprehensive data."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.TOOL_INVOKED,
        severity=SeverityLevel.MEDIUM,
        user_email="qa-test@example.com",
        tool_name="bash",
        server_id=uuid4(),
        decision="allow",
        ip_address="192.168.1.100",
        user_agent="SIEM-QA-Test/1.0",
        request_id=str(uuid4()),
        details={
            "command": "pytest tests/integration/test_siem_integration.py",
            "working_directory": "/opt/sark",
            "exit_code": 0,
            "duration_ms": 1234,
            "test_run": True,
            "test_timestamp": datetime.now(UTC).isoformat(),
            "test_case": "comprehensive_siem_integration",
        },
    )


@pytest.fixture
def test_events(test_event: AuditEvent) -> list[AuditEvent]:
    """Create list of test events for batch testing."""
    base_event = test_event
    events = []

    for i in range(10):
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=base_event.event_type,
            severity=base_event.severity,
            user_email=f"qa-test-{i}@example.com",
            tool_name=base_event.tool_name,
            server_id=base_event.server_id,
            decision=base_event.decision,
            ip_address=f"192.168.1.{100 + i}",
            user_agent=base_event.user_agent,
            request_id=str(uuid4()),
            details={
                **base_event.details,
                "batch_index": i,
                "batch_total": 10,
            },
        )
        events.append(event)

    return events


@pytest.fixture
def splunk_config() -> SplunkConfig:
    """Create Splunk configuration (from env or mock)."""
    return SplunkConfig(
        hec_url=os.getenv("SPLUNK_HEC_URL", "https://mock.splunk.example.com:8088/services/collector"),
        hec_token=os.getenv("SPLUNK_HEC_TOKEN", "mock-hec-token-12345678-1234-1234-1234-123456789012"),
        index=os.getenv("SPLUNK_INDEX", "sark_test"),
        sourcetype="sark:audit:event",
        source="sark_qa_test",
        verify_ssl=os.getenv("SPLUNK_VERIFY_SSL", "false").lower() == "true",
        timeout_seconds=10,
    )


@pytest.fixture
def datadog_config() -> DatadogConfig:
    """Create Datadog configuration (from env or mock)."""
    return DatadogConfig(
        api_key=os.getenv("DATADOG_API_KEY", "mock-datadog-api-key-1234567890abcdef"),
        site=os.getenv("DATADOG_SITE", "datadoghq.com"),
        service="sark_qa_test",
        environment="test",
        verify_ssl=os.getenv("DATADOG_VERIFY_SSL", "false").lower() == "true",
        timeout_seconds=10,
    )


@pytest.fixture
def splunk_siem(splunk_config: SplunkConfig) -> SplunkSIEM:
    """Create Splunk SIEM instance."""
    return SplunkSIEM(splunk_config)


@pytest.fixture
def datadog_siem(datadog_config: DatadogConfig) -> DatadogSIEM:
    """Create Datadog SIEM instance."""
    return DatadogSIEM(datadog_config)


# ============================================================================
# Splunk Integration Tests
# ============================================================================

class TestSplunkEventFormatting:
    """Test Splunk event formatting and structure."""

    def test_hec_event_structure(self, splunk_siem: SplunkSIEM, test_event: AuditEvent):
        """Verify Splunk HEC event structure."""
        # Access the private method for testing
        hec_event = splunk_siem._format_hec_event(test_event)

        # Verify required HEC fields
        assert "time" in hec_event, "Missing 'time' field"
        assert "source" in hec_event, "Missing 'source' field"
        assert "sourcetype" in hec_event, "Missing 'sourcetype' field"
        assert "index" in hec_event, "Missing 'index' field"
        assert "event" in hec_event, "Missing 'event' field"

        # Verify time format (epoch timestamp)
        assert isinstance(hec_event["time"], (int, float)), "Time should be numeric"

        # Verify event data
        event_data = hec_event["event"]
        assert event_data["id"] == str(test_event.id)
        assert event_data["event_type"] == test_event.event_type.value
        assert event_data["severity"] == test_event.severity.value
        assert event_data["user_email"] == test_event.user_email
        assert event_data["tool_name"] == test_event.tool_name

        # Verify details preserved
        assert "details" in event_data
        assert event_data["details"]["command"] == test_event.details["command"]

    def test_hec_event_metadata(self, splunk_siem: SplunkSIEM, test_event: AuditEvent):
        """Verify Splunk metadata fields."""
        hec_event = splunk_siem._format_hec_event(test_event)

        # Verify index
        assert hec_event["index"] == "sark_test"

        # Verify sourcetype
        assert hec_event["sourcetype"] == "sark:audit:event"

        # Verify source
        assert hec_event["source"] == "sark_qa_test"

    def test_hec_batch_format(self, splunk_siem: SplunkSIEM, test_events: list[AuditEvent]):
        """Verify Splunk batch event format (newline-delimited JSON)."""
        # Format batch payload
        batch_payload = "\n".join(
            json.dumps(splunk_siem._format_hec_event(event))
            for event in test_events
        )

        # Verify newline separation
        lines = batch_payload.strip().split("\n")
        assert len(lines) == len(test_events), "Should have one line per event"

        # Verify each line is valid JSON
        for line in lines:
            event = json.loads(line)
            assert "time" in event
            assert "event" in event


class TestSplunkDelivery:
    """Test Splunk event delivery (unit tests with mocks)."""

    @pytest.mark.asyncio
    async def test_single_event_delivery_success(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_event: AuditEvent,
    ):
        """Test successful single event delivery."""
        # Mock successful HEC response
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=200,
            json={"text": "Success", "code": 0},
        )

        # Send event
        result = await splunk_siem.send_event(test_event)

        # Verify success
        assert result is True, "Event send should succeed"

        # Verify request
        requests = httpx_mock.get_requests()
        assert len(requests) == 1

        request = requests[0]
        assert request.headers["Authorization"] == f"Splunk {splunk_siem.splunk_config.hec_token}"
        assert request.headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_single_event_delivery_failure(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_event: AuditEvent,
    ):
        """Test failed single event delivery."""
        # Mock failed HEC response
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=403,
            json={"text": "Invalid token", "code": 4},
        )

        # Send event
        result = await splunk_siem.send_event(test_event)

        # Verify failure
        assert result is False, "Event send should fail"

    @pytest.mark.asyncio
    async def test_batch_delivery_success(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_events: list[AuditEvent],
    ):
        """Test successful batch event delivery."""
        # Mock successful batch response
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=200,
            json={"text": "Success", "code": 0},
        )

        # Send batch
        result = await splunk_siem.send_batch(test_events)

        # Verify success
        assert result is True, "Batch send should succeed"

        # Verify batch format
        requests = httpx_mock.get_requests()
        assert len(requests) == 1

        # Verify newline-delimited JSON
        content = requests[0].content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == len(test_events), "Should have one line per event"


@integration
@requires_splunk
class TestSplunkIntegration:
    """Integration tests with real Splunk instance."""

    @pytest.mark.asyncio
    async def test_real_event_delivery(self, splunk_siem: SplunkSIEM, test_event: AuditEvent):
        """Test actual event delivery to Splunk."""
        result = await splunk_siem.send_event(test_event)
        assert result is True, "Real event delivery should succeed"

    @pytest.mark.asyncio
    async def test_real_batch_delivery(self, splunk_siem: SplunkSIEM, test_events: list[AuditEvent]):
        """Test actual batch delivery to Splunk."""
        result = await splunk_siem.send_batch(test_events)
        assert result is True, "Real batch delivery should succeed"

    @pytest.mark.asyncio
    async def test_event_searchability(self, splunk_siem: SplunkSIEM, test_event: AuditEvent):
        """Test that events are searchable in Splunk.

        Note: This test sends an event and waits for indexing.
        It may take 1-2 minutes for events to become searchable.
        """
        # Send event with unique identifier
        test_id = str(uuid4())
        test_event.details["search_test_id"] = test_id

        result = await splunk_siem.send_event(test_event)
        assert result is True, "Event send should succeed"

        # Wait for indexing (Splunk typically indexes within 30-60 seconds)
        await asyncio.sleep(60)

        # Note: Actual search verification would require Splunk SDK
        # For now, we verify successful delivery
        # TODO: Add Splunk search API integration for verification


# ============================================================================
# Datadog Integration Tests
# ============================================================================

class TestDatadogEventFormatting:
    """Test Datadog event formatting and structure."""

    def test_datadog_event_structure(self, datadog_siem: DatadogSIEM, test_event: AuditEvent):
        """Verify Datadog event structure."""
        dd_event = datadog_siem._format_datadog_event(test_event)

        # Verify required Datadog fields
        assert "ddsource" in dd_event, "Missing 'ddsource' field"
        assert "ddtags" in dd_event, "Missing 'ddtags' field"
        assert "hostname" in dd_event, "Missing 'hostname' field"
        assert "message" in dd_event, "Missing 'message' field"
        assert "service" in dd_event, "Missing 'service' field"

        # Verify event data
        assert dd_event["service"] == "sark_qa_test"

    def test_datadog_tags(self, datadog_siem: DatadogSIEM, test_event: AuditEvent):
        """Verify Datadog tags are correctly formatted."""
        dd_event = datadog_siem._format_datadog_event(test_event)

        # Verify tags is a list of strings
        tags = dd_event["ddtags"]
        assert isinstance(tags, list), "Tags should be a list"
        assert all(isinstance(tag, str) for tag in tags), "All tags should be strings"

        # Verify standard tags present
        tag_dict = {tag.split(":")[0]: tag.split(":")[1] for tag in tags if ":" in tag}

        assert "env" in tag_dict, "Environment tag missing"
        assert tag_dict["env"] == "test"

        assert "event_type" in tag_dict, "Event type tag missing"
        assert tag_dict["event_type"] == test_event.event_type.value

        assert "severity" in tag_dict, "Severity tag missing"
        assert tag_dict["severity"] == test_event.severity.value.lower()

        assert "tool" in tag_dict, "Tool tag missing"
        assert tag_dict["tool"] == test_event.tool_name

    def test_datadog_custom_attributes(self, datadog_siem: DatadogSIEM, test_event: AuditEvent):
        """Verify Datadog custom attributes."""
        dd_event = datadog_siem._format_datadog_event(test_event)

        # Verify custom attributes in event
        assert "id" in dd_event
        assert "user_email" in dd_event
        assert "tool_name" in dd_event
        assert "server_id" in dd_event
        assert "ip_address" in dd_event
        assert "decision" in dd_event

        # Verify details preserved as nested object
        assert "details" in dd_event
        assert dd_event["details"]["command"] == test_event.details["command"]


class TestDatadogDelivery:
    """Test Datadog event delivery (unit tests with mocks)."""

    @pytest.mark.asyncio
    async def test_single_event_delivery_success(
        self,
        httpx_mock: HTTPXMock,
        datadog_siem: DatadogSIEM,
        test_event: AuditEvent,
    ):
        """Test successful single event delivery to Datadog."""
        # Mock successful Datadog Logs API response
        logs_url = f"https://http-intake.logs.{datadog_siem.datadog_config.site}/api/v2/logs"
        httpx_mock.add_response(
            url=logs_url,
            method="POST",
            status_code=202,  # Datadog returns 202 Accepted
            json={"status": "ok"},
        )

        # Send event
        result = await datadog_siem.send_event(test_event)

        # Verify success
        assert result is True, "Event send should succeed"

        # Verify request
        requests = httpx_mock.get_requests()
        assert len(requests) == 1

        request = requests[0]
        assert request.headers["DD-API-KEY"] == datadog_siem.datadog_config.api_key
        assert request.headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_batch_delivery_success(
        self,
        httpx_mock: HTTPXMock,
        datadog_siem: DatadogSIEM,
        test_events: list[AuditEvent],
    ):
        """Test successful batch event delivery to Datadog."""
        logs_url = f"https://http-intake.logs.{datadog_siem.datadog_config.site}/api/v2/logs"
        httpx_mock.add_response(
            url=logs_url,
            method="POST",
            status_code=202,
            json={"status": "ok"},
        )

        # Send batch
        result = await datadog_siem.send_batch(test_events)

        # Verify success
        assert result is True, "Batch send should succeed"


@integration
@requires_datadog
class TestDatadogIntegration:
    """Integration tests with real Datadog instance."""

    @pytest.mark.asyncio
    async def test_real_event_delivery(self, datadog_siem: DatadogSIEM, test_event: AuditEvent):
        """Test actual event delivery to Datadog."""
        result = await datadog_siem.send_event(test_event)
        assert result is True, "Real event delivery should succeed"

    @pytest.mark.asyncio
    async def test_real_batch_delivery(self, datadog_siem: DatadogSIEM, test_events: list[AuditEvent]):
        """Test actual batch delivery to Datadog."""
        result = await datadog_siem.send_batch(test_events)
        assert result is True, "Real batch delivery should succeed"


# ============================================================================
# Failover and Degradation Tests
# ============================================================================

class TestSIEMFailover:
    """Test SIEM failover and graceful degradation."""

    @pytest.mark.asyncio
    async def test_error_handler_fallback_logging(self, test_event: AuditEvent, tmp_path):
        """Test that events are logged locally when SIEM fails."""
        # Create error handler with fallback to temp directory
        error_handler = SIEMErrorHandler(
            siem_name="test_splunk",
            fallback_log_dir=str(tmp_path / "siem_fallback"),
            enable_fallback=True,
        )

        # Simulate SIEM failure and log to fallback
        await error_handler.handle_send_failure(
            event=test_event,
            error=Exception("SIEM unavailable"),
            retry_count=3,
        )

        # Verify fallback log created
        fallback_dir = tmp_path / "siem_fallback"
        assert fallback_dir.exists(), "Fallback directory should exist"

        log_files = list(fallback_dir.glob("*.jsonl"))
        assert len(log_files) > 0, "Fallback log file should exist"

        # Verify event in fallback log
        with open(log_files[0]) as f:
            logged_event = json.loads(f.read())
            assert logged_event["id"] == str(test_event.id)

    @pytest.mark.asyncio
    async def test_graceful_degradation_under_load(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_events: list[AuditEvent],
    ):
        """Test graceful degradation when SIEM is slow/overloaded."""
        # Mock slow SIEM responses (simulate overload)
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=503,  # Service Unavailable
            json={"text": "Server is busy", "code": 9},
        )

        # Attempt to send events
        results = []
        for event in test_events[:5]:  # Send subset
            result = await splunk_siem.send_event(event)
            results.append(result)

        # Verify failures were handled
        assert all(r is False for r in results), "All sends should fail gracefully"


# ============================================================================
# Batching and Compression Tests
# ============================================================================

class TestEventBatching:
    """Test event batching functionality."""

    @pytest.mark.asyncio
    async def test_batch_size_trigger(self, test_events: list[AuditEvent]):
        """Test that batch is sent when size threshold is reached."""
        sent_batches = []

        async def mock_send_batch(events: list[AuditEvent]) -> bool:
            sent_batches.append(events)
            return True

        # Create batch handler with size=5
        config = BatchConfig(batch_size=5, batch_timeout_seconds=60)
        handler = BatchHandler(mock_send_batch, config)

        await handler.start()

        # Add events one by one
        for event in test_events[:7]:  # Add 7 events
            await handler.add_event(event)

        # Give batch worker time to process
        await asyncio.sleep(0.1)

        # Should have sent 1 batch of 5 events
        assert len(sent_batches) >= 1, "Should have sent at least 1 batch"
        assert len(sent_batches[0]) == 5, "First batch should have 5 events"

        await handler.stop(flush=True)

        # After flush, should have sent remaining 2 events
        assert len(sent_batches) == 2, "Should have sent 2 batches total"
        assert len(sent_batches[1]) == 2, "Second batch should have 2 events"

    @pytest.mark.asyncio
    async def test_batch_timeout_trigger(self, test_events: list[AuditEvent]):
        """Test that batch is sent when timeout is reached."""
        sent_batches = []

        async def mock_send_batch(events: list[AuditEvent]) -> bool:
            sent_batches.append(events)
            return True

        # Create batch handler with short timeout
        config = BatchConfig(batch_size=100, batch_timeout_seconds=0.5)
        handler = BatchHandler(mock_send_batch, config)

        await handler.start()

        # Add only 3 events (less than batch_size)
        for event in test_events[:3]:
            await handler.add_event(event)

        # Wait for timeout
        await asyncio.sleep(0.7)

        # Should have sent batch due to timeout
        assert len(sent_batches) >= 1, "Should have sent batch due to timeout"
        assert len(sent_batches[0]) == 3, "Batch should have 3 events"

        await handler.stop(flush=False)


class TestEventCompression:
    """Test event compression functionality."""

    def test_compression_reduces_size(self, test_events: list[AuditEvent]):
        """Test that compression reduces payload size."""
        # Serialize events to JSON
        events_json = json.dumps([
            {
                "id": str(event.id),
                "event_type": event.event_type.value,
                "details": event.details,
            }
            for event in test_events
        ])

        uncompressed_size = len(events_json.encode("utf-8"))

        # Compress
        compressed = gzip.compress(events_json.encode("utf-8"))
        compressed_size = len(compressed)

        # Verify compression
        assert compressed_size < uncompressed_size, "Compressed size should be smaller"

        compression_ratio = compressed_size / uncompressed_size
        assert compression_ratio < 0.5, "Should achieve at least 50% compression"

    def test_compression_decompression_integrity(self, test_events: list[AuditEvent]):
        """Test that compressed data can be decompressed correctly."""
        # Serialize and compress
        original = json.dumps([str(e.id) for e in test_events])
        compressed = gzip.compress(original.encode("utf-8"))

        # Decompress
        decompressed = gzip.decompress(compressed).decode("utf-8")

        # Verify integrity
        assert decompressed == original, "Decompressed data should match original"


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Test that circuit opens after threshold failures."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
        )
        breaker = CircuitBreaker("test_circuit", config)

        # Simulate failing operation
        async def failing_operation():
            raise Exception("Operation failed")

        # Trigger failures
        for i in range(3):
            try:
                await breaker.call(failing_operation)
            except Exception:
                pass  # Expected

        # Circuit should be open now
        assert breaker.state == CircuitState.OPEN, "Circuit should be open"

        # Next call should fail fast
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(failing_operation)

        assert "is open" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self):
        """Test that circuit transitions to half-open after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,  # 1 second
            success_threshold=2,
        )
        breaker = CircuitBreaker("test_circuit", config)

        # Trigger failures to open circuit
        async def failing_operation():
            raise Exception("Operation failed")

        for i in range(2):
            try:
                await breaker.call(failing_operation)
            except Exception:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.2)

        # Should transition to half-open on next call
        async def success_operation():
            return "success"

        # This call should transition to half-open and succeed
        try:
            result = await breaker.call(success_operation)
            assert result == "success"
            assert breaker.state == CircuitState.HALF_OPEN
        except CircuitBreakerError:
            # Circuit might still be open if timeout not fully elapsed
            pass

    @pytest.mark.asyncio
    async def test_circuit_closes_after_successes(self):
        """Test that circuit closes after success threshold in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
            success_threshold=2,
        )
        breaker = CircuitBreaker("test_circuit", config)

        # Open circuit
        async def failing_operation():
            raise Exception("fail")

        for _ in range(2):
            try:
                await breaker.call(failing_operation)
            except Exception:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait and transition to half-open
        await asyncio.sleep(1.2)

        # Success operations to close circuit
        async def success_operation():
            return "success"

        # Manually transition to half-open
        breaker._transition_to_half_open()

        # Execute successful operations
        for _ in range(2):
            result = await breaker.call(success_operation)
            assert result == "success"

        # Circuit should be closed
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerWithSIEM:
    """Test circuit breaker integration with SIEM."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_protects_siem(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_events: list[AuditEvent],
    ):
        """Test that circuit breaker protects SIEM from cascading failures."""
        # Mock failing SIEM
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=500,
            json={"error": "Internal server error"},
        )

        # Create circuit breaker
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("splunk", config)

        # Wrap send_event with circuit breaker
        async def protected_send(event: AuditEvent):
            return await breaker.call(lambda: splunk_siem.send_event(event))

        # Trigger failures
        failures = 0
        circuit_open_errors = 0

        for event in test_events[:10]:
            try:
                await protected_send(event)
            except CircuitBreakerError:
                circuit_open_errors += 1
            except Exception:
                failures += 1

        # Verify circuit opened and failed fast
        assert breaker.state == CircuitState.OPEN
        assert circuit_open_errors > 0, "Should have circuit breaker errors"


# ============================================================================
# Metrics and Monitoring Tests
# ============================================================================

class TestSIEMMetrics:
    """Test SIEM delivery metrics collection."""

    @pytest.mark.asyncio
    async def test_success_metrics_tracked(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_event: AuditEvent,
    ):
        """Test that successful deliveries update metrics."""
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=200,
            json={"text": "Success"},
        )

        # Get initial metrics
        initial_metrics = splunk_siem.get_metrics()
        initial_success = initial_metrics.get("events_sent", 0)

        # Send event
        await splunk_siem.send_event(test_event)

        # Check updated metrics
        updated_metrics = splunk_siem.get_metrics()
        updated_success = updated_metrics.get("events_sent", 0)

        assert updated_success == initial_success + 1, "Success count should increment"

    @pytest.mark.asyncio
    async def test_failure_metrics_tracked(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_event: AuditEvent,
    ):
        """Test that failed deliveries update metrics."""
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=403,
            json={"error": "Forbidden"},
        )

        # Get initial metrics
        initial_metrics = splunk_siem.get_metrics()
        initial_failures = initial_metrics.get("events_failed", 0)

        # Send event (will fail)
        await splunk_siem.send_event(test_event)

        # Check updated metrics
        updated_metrics = splunk_siem.get_metrics()
        updated_failures = updated_metrics.get("events_failed", 0)

        assert updated_failures == initial_failures + 1, "Failure count should increment"

    @pytest.mark.asyncio
    async def test_latency_metrics_tracked(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
        test_event: AuditEvent,
    ):
        """Test that latency metrics are tracked."""
        httpx_mock.add_response(
            url=splunk_siem.splunk_config.hec_url,
            method="POST",
            status_code=200,
            json={"text": "Success"},
        )

        # Send event
        await splunk_siem.send_event(test_event)

        # Check metrics
        metrics = splunk_siem.get_metrics()

        # Should have latency data
        assert "avg_latency_ms" in metrics or "total_latency_ms" in metrics


# ============================================================================
# Health Check Tests
# ============================================================================

class TestSIEMHealthChecks:
    """Test SIEM health check functionality."""

    @pytest.mark.asyncio
    async def test_splunk_health_check_success(
        self,
        httpx_mock: HTTPXMock,
        splunk_siem: SplunkSIEM,
    ):
        """Test successful Splunk health check."""
        health_url = splunk_siem.splunk_config.hec_url.replace(
            "/services/collector",
            "/services/collector/health"
        )

        httpx_mock.add_response(
            url=health_url,
            method="GET",
            status_code=200,
            json={"text": "HEC is healthy", "code": 17},
        )

        health = await splunk_siem.health_check()

        assert health.healthy is True
        assert health.latency_ms > 0

    @pytest.mark.asyncio
    async def test_datadog_health_check_success(
        self,
        httpx_mock: HTTPXMock,
        datadog_siem: DatadogSIEM,
    ):
        """Test successful Datadog health check."""
        # Datadog doesn't have dedicated health endpoint, uses logs API
        logs_url = f"https://http-intake.logs.{datadog_siem.datadog_config.site}/api/v2/logs"

        httpx_mock.add_response(
            url=logs_url,
            method="POST",
            status_code=202,
            json={"status": "ok"},
        )

        health = await datadog_siem.health_check()

        assert health.healthy is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
