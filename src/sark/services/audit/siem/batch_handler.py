"""Batch handler for aggregating and forwarding audit events."""

import asyncio
from collections.abc import Callable
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from sark.models.audit import AuditEvent

logger = structlog.get_logger()


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 100
    batch_timeout_seconds: float = 5.0
    max_queue_size: int = 10000


class BatchHandler:
    """Handles batching of audit events for efficient SIEM forwarding.

    This class collects events and forwards them in batches based on either
    batch size or timeout, whichever occurs first.
    """

    def __init__(
        self,
        send_batch_callback: Callable[[list[AuditEvent]], bool],
        config: BatchConfig | None = None,
    ) -> None:
        """Initialize batch handler.

        Args:
            send_batch_callback: Async callback to send batch of events
            config: Batch configuration. Uses defaults if None.
        """
        self.config = config or BatchConfig()
        self._send_batch_callback = send_batch_callback
        self._logger = logger.bind(component="batch_handler")

        # Event queue and batch state
        self._event_queue: asyncio.Queue[AuditEvent] = asyncio.Queue(
            maxsize=self.config.max_queue_size
        )
        self._current_batch: list[AuditEvent] = []
        self._last_flush_time: datetime = datetime.now(UTC)
        self._running = False
        self._worker_task: asyncio.Task | None = None

        # Metrics
        self._batches_sent = 0
        self._batches_failed = 0
        self._events_queued = 0
        self._events_dropped = 0

    async def start(self) -> None:
        """Start the batch processing worker."""
        if self._running:
            self._logger.warning("batch_handler_already_running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._batch_worker())
        self._logger.info(
            "batch_handler_started",
            batch_size=self.config.batch_size,
            batch_timeout=self.config.batch_timeout_seconds,
        )

    async def stop(self, flush: bool = True) -> None:
        """Stop the batch processing worker.

        Args:
            flush: If True, flush remaining events before stopping
        """
        if not self._running:
            return

        self._running = False

        if flush:
            await self._flush_current_batch()

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

        self._logger.info(
            "batch_handler_stopped",
            batches_sent=self._batches_sent,
            batches_failed=self._batches_failed,
            events_queued=self._events_queued,
            events_dropped=self._events_dropped,
        )

    async def enqueue(self, event: AuditEvent) -> bool:
        """Add an event to the batch queue.

        Args:
            event: Audit event to enqueue

        Returns:
            True if event was queued, False if queue is full
        """
        try:
            self._event_queue.put_nowait(event)
            self._events_queued += 1
            return True
        except asyncio.QueueFull:
            self._events_dropped += 1
            self._logger.error(
                "batch_queue_full",
                max_queue_size=self.config.max_queue_size,
                events_dropped=self._events_dropped,
            )
            return False

    async def _batch_worker(self) -> None:
        """Background worker that processes batches."""
        self._logger.info("batch_worker_started")

        while self._running:
            try:
                # Check if we should flush based on timeout
                time_since_flush = (datetime.now(UTC) - self._last_flush_time).total_seconds()
                should_flush_timeout = (
                    time_since_flush >= self.config.batch_timeout_seconds
                    and len(self._current_batch) > 0
                )

                if should_flush_timeout:
                    await self._flush_current_batch()
                    continue

                # Calculate remaining timeout
                remaining_timeout = max(
                    0.1, self.config.batch_timeout_seconds - time_since_flush
                )

                # Wait for an event with timeout
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(), timeout=remaining_timeout
                    )
                    self._current_batch.append(event)

                    # Check if batch is full
                    if len(self._current_batch) >= self.config.batch_size:
                        await self._flush_current_batch()

                except TimeoutError:
                    # Timeout occurred, check if we should flush
                    if len(self._current_batch) > 0:
                        await self._flush_current_batch()

            except Exception as e:
                self._logger.error(
                    "batch_worker_error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                await asyncio.sleep(1)  # Brief pause before retrying

        self._logger.info("batch_worker_stopped")

    async def _flush_current_batch(self) -> None:
        """Flush the current batch of events."""
        if not self._current_batch:
            return

        batch_to_send = self._current_batch.copy()
        batch_size = len(batch_to_send)

        self._logger.info("flushing_batch", batch_size=batch_size)

        try:
            # Send the batch
            success = await self._send_batch_callback(batch_to_send)

            if success:
                self._batches_sent += 1
                self._logger.info(
                    "batch_sent_successfully",
                    batch_size=batch_size,
                    total_batches_sent=self._batches_sent,
                )
            else:
                self._batches_failed += 1
                self._logger.error(
                    "batch_send_failed",
                    batch_size=batch_size,
                    total_batches_failed=self._batches_failed,
                )

            # Clear the batch regardless of success/failure
            self._current_batch.clear()
            self._last_flush_time = datetime.now(UTC)

        except Exception as e:
            self._batches_failed += 1
            self._logger.error(
                "batch_send_exception",
                batch_size=batch_size,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            # Clear the batch to avoid retrying the same failed events infinitely
            self._current_batch.clear()
            self._last_flush_time = datetime.now(UTC)

    def get_metrics(self) -> dict[str, int]:
        """Get current batch handler metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "batches_sent": self._batches_sent,
            "batches_failed": self._batches_failed,
            "events_queued": self._events_queued,
            "events_dropped": self._events_dropped,
            "current_batch_size": len(self._current_batch),
            "queue_size": self._event_queue.qsize(),
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._batches_sent = 0
        self._batches_failed = 0
        self._events_queued = 0
        self._events_dropped = 0
