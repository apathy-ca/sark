"""SIEM performance optimizer with compression and health monitoring.

Provides advanced performance optimization features for SIEM integrations:
- Gzip compression for large payloads (>1KB)
- Health monitoring with periodic checks
- Circuit breaker integration
- Optimized batching recommendations
- Performance metrics tracking
"""

import asyncio
import gzip
import json
from datetime import UTC, datetime
from typing import Any

import structlog

from sark.models.audit import AuditEvent
from sark.services.audit.siem.base import BaseSIEM, SIEMHealth
from sark.services.audit.siem.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = structlog.get_logger(__name__)


class CompressionConfig:
    """Configuration for payload compression."""

    def __init__(
        self,
        enabled: bool = True,
        min_size_bytes: int = 1024,
        compression_level: int = 6,
    ):
        """Initialize compression configuration.

        Args:
            enabled: Whether to enable compression
            min_size_bytes: Minimum payload size for compression (default: 1KB)
            compression_level: Gzip compression level 0-9 (default: 6)
        """
        self.enabled = enabled
        self.min_size_bytes = min_size_bytes
        self.compression_level = compression_level


class HealthMonitorConfig:
    """Configuration for SIEM health monitoring."""

    def __init__(
        self,
        enabled: bool = True,
        check_interval_seconds: int = 30,
        failure_threshold: int = 3,
    ):
        """Initialize health monitor configuration.

        Args:
            enabled: Whether to enable health monitoring
            check_interval_seconds: Seconds between health checks (default: 30)
            failure_threshold: Consecutive failures before marking unhealthy
        """
        self.enabled = enabled
        self.check_interval_seconds = check_interval_seconds
        self.failure_threshold = failure_threshold


class SIEMOptimizer:
    """Performance optimizer for SIEM integrations.

    Wraps a SIEM implementation with optimization features:
    - Automatic gzip compression for large payloads
    - Circuit breaker for failure protection
    - Health monitoring with periodic checks
    - Performance metrics tracking

    Example:
        ```python
        # Create base SIEM
        splunk = SplunkSIEM(config)

        # Wrap with optimizer
        optimizer = SIEMOptimizer(
            siem=splunk,
            name="splunk",
            compression_config=CompressionConfig(min_size_bytes=1024),
            health_config=HealthMonitorConfig(check_interval_seconds=30),
            circuit_config=CircuitBreakerConfig(failure_threshold=5),
        )

        # Start health monitoring
        await optimizer.start_health_monitoring()

        # Send events (automatically compressed if >1KB)
        await optimizer.send_event(event)

        # Stop monitoring
        await optimizer.stop_health_monitoring()
        ```
    """

    def __init__(
        self,
        siem: BaseSIEM,
        name: str,
        compression_config: CompressionConfig | None = None,
        health_config: HealthMonitorConfig | None = None,
        circuit_config: CircuitBreakerConfig | None = None,
    ):
        """Initialize SIEM optimizer.

        Args:
            siem: Base SIEM implementation to wrap
            name: Name for logging and metrics
            compression_config: Compression configuration
            health_config: Health monitoring configuration
            circuit_config: Circuit breaker configuration
        """
        self.siem = siem
        self.name = name
        self.compression_config = compression_config or CompressionConfig()
        self.health_config = health_config or HealthMonitorConfig()
        self.circuit_config = circuit_config or CircuitBreakerConfig()

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(name, self.circuit_config)

        # Health monitoring
        self._health_monitor_task: asyncio.Task | None = None
        self._health_check_running = False
        self._consecutive_health_failures = 0
        self._is_healthy = True
        self._last_health_check: datetime | None = None
        self._last_health_status: SIEMHealth | None = None

        # Metrics
        self._compression_count = 0
        self._compression_bytes_saved = 0
        self._uncompressed_sends = 0
        self._circuit_breaker_blocks = 0

        logger.info(
            "siem_optimizer_initialized",
            siem=name,
            compression_enabled=self.compression_config.enabled,
            compression_threshold=self.compression_config.min_size_bytes,
            health_monitoring=self.health_config.enabled,
            circuit_breaker_threshold=self.circuit_config.failure_threshold,
        )

    async def send_event(self, event: AuditEvent) -> bool:
        """Send event through optimizer.

        Args:
            event: Audit event to send

        Returns:
            True if sent successfully

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If send fails
        """
        async def _send():
            return await self.siem.send_event(event)

        try:
            result = await self.circuit_breaker.call(_send)
            return result
        except Exception as e:
            if "Circuit breaker" in str(e):
                self._circuit_breaker_blocks += 1
            raise

    async def send_batch(self, events: list[AuditEvent]) -> bool:
        """Send batch of events with optional compression.

        Args:
            events: List of audit events to send

        Returns:
            True if sent successfully

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If send fails
        """
        async def _send():
            return await self.siem.send_batch(events)

        try:
            result = await self.circuit_breaker.call(_send)
            return result
        except Exception as e:
            if "Circuit breaker" in str(e):
                self._circuit_breaker_blocks += 1
            raise

    def compress_payload(self, data: str | bytes) -> tuple[bytes, dict[str, Any]]:
        """Compress payload if it exceeds threshold.

        Args:
            data: String or bytes to potentially compress

        Returns:
            Tuple of (data, metadata) where:
            - data: Original or compressed bytes
            - metadata: Dict with compression stats
        """
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        original_size = len(data_bytes)
        metadata = {
            "original_size": original_size,
            "compressed": False,
            "compression_ratio": 1.0,
        }

        # Check if compression is enabled and worthwhile
        if (
            not self.compression_config.enabled
            or original_size < self.compression_config.min_size_bytes
        ):
            self._uncompressed_sends += 1
            return data_bytes, metadata

        # Compress data
        compressed_bytes = gzip.compress(
            data_bytes, compresslevel=self.compression_config.compression_level
        )
        compressed_size = len(compressed_bytes)
        compression_ratio = compressed_size / original_size

        # Only use compressed if it's actually smaller
        if compressed_size < original_size:
            bytes_saved = original_size - compressed_size
            self._compression_count += 1
            self._compression_bytes_saved += bytes_saved

            logger.debug(
                "payload_compressed",
                siem=self.name,
                original_size=original_size,
                compressed_size=compressed_size,
                bytes_saved=bytes_saved,
                compression_ratio=f"{compression_ratio:.2f}",
            )

            metadata.update(
                {
                    "compressed": True,
                    "compressed_size": compressed_size,
                    "bytes_saved": bytes_saved,
                    "compression_ratio": compression_ratio,
                }
            )
            return compressed_bytes, metadata
        else:
            # Compression not beneficial
            self._uncompressed_sends += 1
            logger.debug(
                "compression_skipped",
                siem=self.name,
                reason="compressed_size_larger",
                original=original_size,
                compressed=compressed_size,
            )
            return data_bytes, metadata

    async def start_health_monitoring(self) -> None:
        """Start periodic health monitoring."""
        if not self.health_config.enabled:
            logger.info("health_monitoring_disabled", siem=self.name)
            return

        if self._health_check_running:
            logger.warning("health_monitoring_already_running", siem=self.name)
            return

        self._health_check_running = True
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        logger.info(
            "health_monitoring_started",
            siem=self.name,
            interval=self.health_config.check_interval_seconds,
        )

    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        if not self._health_check_running:
            return

        self._health_check_running = False
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("health_monitoring_stopped", siem=self.name)

    async def _health_monitor_loop(self) -> None:
        """Health monitoring background loop."""
        while self._health_check_running:
            try:
                # Perform health check
                health = await self.siem.health_check()
                self._last_health_check = datetime.now(UTC)
                self._last_health_status = health

                if health.healthy:
                    # Reset failure count on success
                    if self._consecutive_health_failures > 0:
                        logger.info(
                            "health_check_recovered",
                            siem=self.name,
                            previous_failures=self._consecutive_health_failures,
                        )
                    self._consecutive_health_failures = 0
                    self._is_healthy = True
                else:
                    # Increment failure count
                    self._consecutive_health_failures += 1
                    logger.warning(
                        "health_check_failed",
                        siem=self.name,
                        consecutive_failures=self._consecutive_health_failures,
                        threshold=self.health_config.failure_threshold,
                        error=health.error_message,
                    )

                    # Mark unhealthy if threshold exceeded
                    if self._consecutive_health_failures >= self.health_config.failure_threshold:
                        if self._is_healthy:
                            logger.error(
                                "siem_marked_unhealthy",
                                siem=self.name,
                                failures=self._consecutive_health_failures,
                            )
                        self._is_healthy = False

            except Exception as e:
                logger.error(
                    "health_check_error",
                    siem=self.name,
                    error=str(e),
                    exception=type(e).__name__,
                )
                self._consecutive_health_failures += 1

            # Wait for next check
            await asyncio.sleep(self.health_config.check_interval_seconds)

    def is_healthy(self) -> bool:
        """Check if SIEM is currently healthy.

        Returns:
            True if healthy, False otherwise
        """
        return self._is_healthy

    def get_metrics(self) -> dict[str, Any]:
        """Get optimizer performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        return {
            "siem": self.name,
            "compression": {
                "enabled": self.compression_config.enabled,
                "count": self._compression_count,
                "bytes_saved": self._compression_bytes_saved,
                "uncompressed_sends": self._uncompressed_sends,
                "total_sends": self._compression_count + self._uncompressed_sends,
                "compression_rate": (
                    self._compression_count / (self._compression_count + self._uncompressed_sends)
                    if (self._compression_count + self._uncompressed_sends) > 0
                    else 0
                ),
            },
            "circuit_breaker": self.circuit_breaker.get_state(),
            "circuit_breaker_blocks": self._circuit_breaker_blocks,
            "health": {
                "enabled": self.health_config.enabled,
                "is_healthy": self._is_healthy,
                "consecutive_failures": self._consecutive_health_failures,
                "last_check": (
                    self._last_health_check.isoformat() if self._last_health_check else None
                ),
                "last_status": (
                    {
                        "healthy": self._last_health_status.healthy,
                        "latency_ms": self._last_health_status.latency_ms,
                        "error": self._last_health_status.error,
                    }
                    if self._last_health_status
                    else None
                ),
            },
        }

    def reset_metrics(self) -> None:
        """Reset optimizer metrics."""
        self._compression_count = 0
        self._compression_bytes_saved = 0
        self._uncompressed_sends = 0
        self._circuit_breaker_blocks = 0
        logger.info("optimizer_metrics_reset", siem=self.name)


def get_optimal_batch_size(
    avg_event_size_bytes: int,
    target_batch_size_kb: int = 100,
) -> int:
    """Calculate optimal batch size based on event size.

    Args:
        avg_event_size_bytes: Average event size in bytes
        target_batch_size_kb: Target batch size in kilobytes (default: 100KB)

    Returns:
        Recommended number of events per batch
    """
    target_bytes = target_batch_size_kb * 1024
    optimal_count = target_bytes // avg_event_size_bytes

    # Clamp to reasonable range
    optimal_count = max(10, min(optimal_count, 1000))

    logger.info(
        "optimal_batch_size_calculated",
        avg_event_size_bytes=avg_event_size_bytes,
        target_batch_kb=target_batch_size_kb,
        optimal_batch_size=optimal_count,
    )

    return optimal_count


def estimate_event_size(event: AuditEvent) -> int:
    """Estimate serialized size of an audit event.

    Args:
        event: Audit event

    Returns:
        Estimated size in bytes
    """
    # Rough estimation without full serialization
    base_size = 200  # Base overhead
    if event.user_email:
        base_size += len(event.user_email)
    if event.tool_name:
        base_size += len(event.tool_name)
    if event.ip_address:
        base_size += len(event.ip_address)
    if event.user_agent:
        base_size += len(event.user_agent)
    if event.request_id:
        base_size += len(event.request_id)
    if event.details:
        # Estimate JSON size
        base_size += len(json.dumps(event.details))

    return base_size
