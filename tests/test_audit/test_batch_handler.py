"""Tests for BatchHandler."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.batch_handler import BatchConfig, BatchHandler


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
        details={},
    )


@pytest.fixture
def batch_config() -> BatchConfig:
    """Create a batch configuration for testing."""
    return BatchConfig(
        batch_size=5,
        batch_timeout_seconds=0.5,  # Short timeout for faster tests
        max_queue_size=100,
    )


@pytest.fixture
def batch_handler(batch_config: BatchConfig) -> BatchHandler:
    """Create a batch handler with mock callback."""
    mock_callback = AsyncMock(return_value=True)
    handler = BatchHandler(mock_callback, batch_config)
    return handler


class TestBatchConfig:
    """Tests for BatchConfig."""

    def test_default_config(self):
        """Test default batch configuration."""
        config = BatchConfig()
        assert config.batch_size == 100
        assert config.batch_timeout_seconds == 5.0
        assert config.max_queue_size == 10000

    def test_custom_config(self):
        """Test custom batch configuration."""
        config = BatchConfig(
            batch_size=50,
            batch_timeout_seconds=10.0,
            max_queue_size=5000,
        )
        assert config.batch_size == 50
        assert config.batch_timeout_seconds == 10.0
        assert config.max_queue_size == 5000


class TestBatchHandler:
    """Tests for BatchHandler."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self, batch_handler: BatchHandler):
        """Test starting and stopping the batch handler."""
        assert not batch_handler._running

        await batch_handler.start()
        assert batch_handler._running
        assert batch_handler._worker_task is not None

        await batch_handler.stop(flush=False)
        assert not batch_handler._running

    @pytest.mark.asyncio
    async def test_double_start(self, batch_handler: BatchHandler):
        """Test that starting twice doesn't create issues."""
        await batch_handler.start()
        await batch_handler.start()  # Should log warning but not fail
        assert batch_handler._running
        await batch_handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_enqueue_event(self, batch_handler: BatchHandler, audit_event: AuditEvent):
        """Test enqueueing events."""
        await batch_handler.start()

        result = await batch_handler.enqueue(audit_event)
        assert result is True
        assert batch_handler._events_queued == 1

        await batch_handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_batch_size_trigger(self, audit_event: AuditEvent):
        """Test that batch is sent when size limit is reached."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=3, batch_timeout_seconds=10.0)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue 3 events to trigger batch send
        for _ in range(3):
            await handler.enqueue(audit_event)

        # Wait a bit for batch processing
        await asyncio.sleep(0.2)

        # Batch should have been sent
        assert mock_callback.call_count == 1
        assert len(mock_callback.call_args[0][0]) == 3

        await handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_batch_timeout_trigger(self, audit_event: AuditEvent):
        """Test that batch is sent when timeout is reached."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=100, batch_timeout_seconds=0.3)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue 2 events (less than batch size)
        await handler.enqueue(audit_event)
        await handler.enqueue(audit_event)

        # Wait for timeout
        await asyncio.sleep(0.5)

        # Batch should have been sent due to timeout
        assert mock_callback.call_count == 1
        assert len(mock_callback.call_args[0][0]) == 2

        await handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_multiple_batches(self, audit_event: AuditEvent):
        """Test sending multiple batches."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=2, batch_timeout_seconds=10.0)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue 5 events to trigger 2 full batches
        for _ in range(5):
            await handler.enqueue(audit_event)

        # Wait for processing
        await asyncio.sleep(0.3)

        # Should have sent 2 batches
        assert mock_callback.call_count >= 2

        await handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_flush_on_stop(self, audit_event: AuditEvent):
        """Test that remaining events are flushed on stop."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=100, batch_timeout_seconds=10.0)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue 2 events (less than batch size)
        await handler.enqueue(audit_event)
        await handler.enqueue(audit_event)

        # Give worker time to move events from queue to batch
        await asyncio.sleep(0.2)

        # Stop with flush=True
        await handler.stop(flush=True)

        # Should have flushed the remaining events
        assert mock_callback.call_count == 1
        assert len(mock_callback.call_args[0][0]) == 2

    @pytest.mark.asyncio
    async def test_no_flush_on_stop(self, audit_event: AuditEvent):
        """Test that events are not flushed when flush=False."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=100, batch_timeout_seconds=10.0)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue 2 events
        await handler.enqueue(audit_event)
        await handler.enqueue(audit_event)

        # Stop with flush=False
        await handler.stop(flush=False)

        # Should not have sent the batch
        assert mock_callback.call_count == 0

    @pytest.mark.asyncio
    async def test_queue_full(self, audit_event: AuditEvent):
        """Test behavior when queue is full."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=100, batch_timeout_seconds=10.0, max_queue_size=3)
        handler = BatchHandler(mock_callback, config)

        # Don't start the worker so queue fills up
        # Fill the queue
        for _i in range(3):
            result = await handler.enqueue(audit_event)
            assert result is True

        # Try to add one more - should fail
        result = await handler.enqueue(audit_event)
        assert result is False
        assert handler._events_dropped == 1

    @pytest.mark.asyncio
    async def test_callback_failure(self, audit_event: AuditEvent):
        """Test handling of callback failures."""
        mock_callback = AsyncMock(return_value=False)
        config = BatchConfig(batch_size=2, batch_timeout_seconds=10.0)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue events to trigger batch
        await handler.enqueue(audit_event)
        await handler.enqueue(audit_event)

        # Wait for processing
        await asyncio.sleep(0.2)

        # Callback was called but returned False
        assert mock_callback.call_count == 1
        assert handler._batches_failed == 1

        await handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_callback_exception(self, audit_event: AuditEvent):
        """Test handling of callback exceptions."""
        mock_callback = AsyncMock(side_effect=Exception("Callback error"))
        config = BatchConfig(batch_size=2, batch_timeout_seconds=10.0)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue events to trigger batch
        await handler.enqueue(audit_event)
        await handler.enqueue(audit_event)

        # Wait for processing
        await asyncio.sleep(0.2)

        # Exception should be caught and logged
        assert mock_callback.call_count == 1
        assert handler._batches_failed == 1

        await handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_get_metrics(self, batch_handler: BatchHandler, audit_event: AuditEvent):
        """Test getting batch handler metrics."""
        await batch_handler.start()

        await batch_handler.enqueue(audit_event)
        await batch_handler.enqueue(audit_event)

        metrics = batch_handler.get_metrics()

        assert metrics["events_queued"] == 2
        assert metrics["events_dropped"] == 0
        assert "batches_sent" in metrics
        assert "batches_failed" in metrics
        assert "current_batch_size" in metrics
        assert "queue_size" in metrics

        await batch_handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_reset_metrics(self, batch_handler: BatchHandler, audit_event: AuditEvent):
        """Test resetting metrics."""
        await batch_handler.start()

        await batch_handler.enqueue(audit_event)
        await batch_handler.enqueue(audit_event)

        assert batch_handler._events_queued == 2

        batch_handler.reset_metrics()

        assert batch_handler._events_queued == 0
        assert batch_handler._batches_sent == 0
        assert batch_handler._batches_failed == 0
        assert batch_handler._events_dropped == 0

        await batch_handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_empty_batch_not_sent(self):
        """Test that empty batches are not sent."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=100, batch_timeout_seconds=0.3)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Don't enqueue any events, just wait for timeout
        await asyncio.sleep(0.5)

        # No batch should have been sent
        assert mock_callback.call_count == 0

        await handler.stop(flush=False)

    @pytest.mark.asyncio
    async def test_concurrent_enqueue(self, audit_event: AuditEvent):
        """Test concurrent enqueueing from multiple tasks."""
        mock_callback = AsyncMock(return_value=True)
        config = BatchConfig(batch_size=50, batch_timeout_seconds=2.0)
        handler = BatchHandler(mock_callback, config)

        await handler.start()

        # Enqueue events concurrently
        async def enqueue_events(count: int):
            for _ in range(count):
                await handler.enqueue(audit_event)

        await asyncio.gather(
            enqueue_events(10),
            enqueue_events(10),
            enqueue_events(10),
        )

        # Wait for processing
        await asyncio.sleep(0.3)

        assert handler._events_queued == 30

        await handler.stop(flush=True)
