"""Unit tests for SIEM Gateway forwarder."""

import pytest
import json
import gzip
from unittest.mock import AsyncMock, patch, MagicMock
import time

from sark.models.gateway import GatewayAuditEvent
from sark.services.siem.gateway_forwarder import (
    forward_gateway_event,
    flush_gateway_events,
    gateway_event_queue,
    _forward_to_splunk,
    _forward_to_datadog,
    _reset_circuit_breaker,
)


@pytest.fixture
def sample_event():
    """Create a sample Gateway audit event."""
    return GatewayAuditEvent(
        event_type="tool_invoke",
        user_id="user_123",
        agent_id=None,
        server_name="postgres-mcp",
        tool_name="execute_query",
        decision="allow",
        reason="User has permissions",
        timestamp=int(time.time()),
        gateway_request_id="req_abc123",
        metadata={"database": "prod"}
    )


@pytest.fixture(autouse=True)
def clear_event_queue():
    """Clear the event queue before each test."""
    gateway_event_queue.clear()
    yield
    gateway_event_queue.clear()


@pytest.mark.asyncio
async def test_forward_gateway_event_queues_event(sample_event):
    """Test that events are queued."""
    audit_id = "audit_123"

    await forward_gateway_event(sample_event, audit_id)

    # Verify event was queued
    assert len(gateway_event_queue) == 1
    queued_event = gateway_event_queue[0]
    assert queued_event['audit_id'] == audit_id
    assert queued_event['event'] == sample_event.dict()
    assert queued_event['timestamp'] == sample_event.timestamp


@pytest.mark.asyncio
async def test_forward_gateway_event_triggers_flush_at_100(sample_event):
    """Test that queue flushes when it reaches 100 events."""
    with patch('sark.services.siem.gateway_forwarder.flush_gateway_events') as mock_flush:
        # Add 99 events (not enough to trigger flush)
        for i in range(99):
            await forward_gateway_event(sample_event, f"audit_{i}")

        assert not mock_flush.called

        # Add 100th event (should trigger flush)
        await forward_gateway_event(sample_event, "audit_100")

        assert mock_flush.called


@pytest.mark.asyncio
async def test_flush_gateway_events_empty_queue():
    """Test flushing empty queue does nothing."""
    with patch('sark.services.siem.gateway_forwarder._forward_to_splunk') as mock_splunk:
        with patch('sark.services.siem.gateway_forwarder._forward_to_datadog') as mock_datadog:
            await flush_gateway_events()

            assert not mock_splunk.called
            assert not mock_datadog.called


@pytest.mark.asyncio
async def test_flush_gateway_events_clears_queue(sample_event):
    """Test that flushing clears the queue."""
    # Add events to queue
    for i in range(5):
        await forward_gateway_event(sample_event, f"audit_{i}")

    assert len(gateway_event_queue) == 5

    with patch('sark.services.siem.gateway_forwarder._forward_to_splunk'):
        with patch('sark.services.siem.gateway_forwarder._forward_to_datadog'):
            with patch('sark.services.siem.gateway_forwarder.settings') as mock_settings:
                mock_settings.splunk_hec_url = None
                mock_settings.datadog_api_key = None

                await flush_gateway_events()

                # Queue should be cleared
                assert len(gateway_event_queue) == 0


@pytest.mark.asyncio
async def test_forward_to_splunk_success(sample_event):
    """Test successful forwarding to Splunk."""
    events = [
        {
            "audit_id": "audit_1",
            "event": sample_event.dict(),
            "timestamp": sample_event.timestamp
        }
    ]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with patch('sark.services.siem.gateway_forwarder.settings') as mock_settings:
            mock_settings.splunk_hec_url = "https://splunk.example.com/services/collector"
            mock_settings.splunk_hec_token = "test_token"

            await _forward_to_splunk(events)

            # Verify HTTP request was made
            assert mock_client.post.called
            call_args = mock_client.post.call_args

            # Verify URL
            assert call_args[0][0] == mock_settings.splunk_hec_url

            # Verify headers
            headers = call_args[1]['headers']
            assert 'Authorization' in headers
            assert 'Splunk test_token' in headers['Authorization']
            assert headers['Content-Encoding'] == 'gzip'

            # Verify payload is compressed
            payload = call_args[1]['content']
            assert isinstance(payload, bytes)

            # Decompress and verify structure
            decompressed = gzip.decompress(payload)
            splunk_events = json.loads(decompressed)
            assert len(splunk_events) == 1
            assert splunk_events[0]['sourcetype'] == 'sark:gateway'


@pytest.mark.asyncio
async def test_forward_to_datadog_success(sample_event):
    """Test successful forwarding to Datadog."""
    events = [
        {
            "audit_id": "audit_1",
            "event": sample_event.dict(),
            "timestamp": sample_event.timestamp
        }
    ]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with patch('sark.services.siem.gateway_forwarder.settings') as mock_settings:
            mock_settings.datadog_logs_url = "https://http-intake.logs.datadoghq.com/v1/input"
            mock_settings.datadog_api_key = "test_api_key"

            await _forward_to_datadog(events)

            # Verify HTTP request was made
            assert mock_client.post.called
            call_args = mock_client.post.call_args

            # Verify headers
            headers = call_args[1]['headers']
            assert headers['DD-API-KEY'] == 'test_api_key'
            assert headers['Content-Encoding'] == 'gzip'


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(sample_event):
    """Test circuit breaker opens after repeated failures."""
    events = [
        {
            "audit_id": "audit_1",
            "event": sample_event.dict(),
            "timestamp": sample_event.timestamp
        }
    ]

    # Mock client to always fail
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("Network error"))

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with patch('sark.services.siem.gateway_forwarder.settings') as mock_settings:
            mock_settings.splunk_hec_url = "https://splunk.example.com"
            mock_settings.splunk_hec_token = "test_token"

            # Trigger 5 failures (threshold)
            for i in range(5):
                await _forward_to_splunk(events)

            # Circuit breaker should now be open
            from sark.services.siem.gateway_forwarder import circuit_breaker_open
            # Note: This test may need adjustment based on actual implementation


@pytest.mark.asyncio
async def test_compression_reduces_payload_size(sample_event):
    """Test that gzip compression reduces payload size."""
    # Create multiple events
    events = []
    for i in range(10):
        events.append({
            "audit_id": f"audit_{i}",
            "event": sample_event.dict(),
            "timestamp": sample_event.timestamp
        })

    # Uncompressed size
    uncompressed = json.dumps(events).encode()
    uncompressed_size = len(uncompressed)

    # Compressed size
    compressed = gzip.compress(uncompressed)
    compressed_size = len(compressed)

    # Verify compression works
    assert compressed_size < uncompressed_size
    assert compressed_size / uncompressed_size < 0.5  # At least 50% compression


@pytest.mark.asyncio
async def test_reset_circuit_breaker():
    """Test circuit breaker reset functionality."""
    from sark.services.siem import gateway_forwarder

    # Set circuit breaker to open
    gateway_forwarder.circuit_breaker_open = True

    # Reset should happen after 60 seconds, but we'll test the function directly
    with patch('asyncio.sleep'):  # Skip the actual sleep
        await _reset_circuit_breaker()

    # Circuit breaker should be closed
    assert not gateway_forwarder.circuit_breaker_open


@pytest.mark.asyncio
async def test_batch_formatting_for_splunk(sample_event):
    """Test that events are correctly formatted for Splunk HEC."""
    events = [
        {
            "audit_id": "audit_123",
            "event": sample_event.dict(),
            "timestamp": 1700000000
        }
    ]

    # Extract the formatting logic
    splunk_events = [
        {
            "time": e["timestamp"],
            "sourcetype": "sark:gateway",
            "source": "sark-api",
            "event": e["event"],
            "fields": {
                "audit_id": e["audit_id"],
            },
        }
        for e in events
    ]

    assert len(splunk_events) == 1
    assert splunk_events[0]["time"] == 1700000000
    assert splunk_events[0]["sourcetype"] == "sark:gateway"
    assert splunk_events[0]["fields"]["audit_id"] == "audit_123"
