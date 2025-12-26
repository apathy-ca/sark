"""SIEM forwarding for Gateway events."""

import asyncio
from collections import deque
import gzip
import json
from typing import Any

import httpx
import structlog

from sark.config.settings import get_settings
from sark.models.gateway import GatewayAuditEvent

logger = structlog.get_logger()
settings = get_settings()

# Event queue for batching
gateway_event_queue: deque[dict[str, Any]] = deque(maxlen=1000)

# Circuit breaker state
circuit_breaker_open = False
circuit_breaker_failures = 0
CIRCUIT_BREAKER_THRESHOLD = 5


async def forward_gateway_event(event: GatewayAuditEvent, audit_id: str):
    """
    Forward Gateway event to SIEM platforms.

    Batches events for efficiency. Events are queued and flushed
    when batch size reaches 100 or on periodic flush.

    Args:
        event: Gateway audit event
        audit_id: Audit event ID from database
    """
    gateway_event_queue.append(
        {
            "audit_id": audit_id,
            "event": event.dict(),
            "timestamp": event.timestamp,
        }
    )

    # Trigger batch if queue is full
    if len(gateway_event_queue) >= 100:
        await flush_gateway_events()


async def flush_gateway_events():
    """
    Flush queued events to SIEM.

    Sends events to all configured SIEM platforms:
    - Splunk (via HEC)
    - Datadog (via API)
    """
    global circuit_breaker_open, circuit_breaker_failures

    if not gateway_event_queue:
        return

    if circuit_breaker_open:
        logger.warning("siem_circuit_breaker_open_skipping_flush")
        return

    events = list(gateway_event_queue)
    gateway_event_queue.clear()

    # Send to Splunk if configured
    if hasattr(settings, "splunk_hec_url") and settings.splunk_hec_url:
        await _forward_to_splunk(events)

    # Send to Datadog if configured
    if hasattr(settings, "datadog_api_key") and settings.datadog_api_key:
        await _forward_to_datadog(events)


async def _forward_to_splunk(events: list[dict[str, Any]]):
    """
    Forward events to Splunk via HEC (HTTP Event Collector).

    Args:
        events: List of events to forward
    """
    global circuit_breaker_failures, circuit_breaker_open

    try:
        # Format for Splunk HEC
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

        # Compress payload
        payload = gzip.compress(json.dumps(splunk_events).encode())

        # Send to Splunk with circuit breaker
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.splunk_hec_url,
                headers={
                    "Authorization": f"Splunk {settings.splunk_hec_token}",
                    "Content-Encoding": "gzip",
                    "Content-Type": "application/json",
                },
                content=payload,
            )
            response.raise_for_status()

        logger.info(
            "gateway_events_forwarded_to_splunk",
            count=len(events),
            compressed_size=len(payload),
        )

        # Reset circuit breaker on success
        circuit_breaker_failures = 0

    except Exception as e:
        circuit_breaker_failures += 1
        logger.error(
            "splunk_forward_failed",
            error=str(e),
            failures=circuit_breaker_failures,
        )

        # Open circuit breaker if threshold exceeded
        if circuit_breaker_failures >= CIRCUIT_BREAKER_THRESHOLD:
            circuit_breaker_open = True
            logger.error("siem_circuit_breaker_opened")
            # Schedule circuit breaker reset after 60 seconds
            asyncio.create_task(_reset_circuit_breaker())


async def _forward_to_datadog(events: list[dict[str, Any]]):
    """
    Forward events to Datadog Logs API.

    Args:
        events: List of events to forward
    """
    try:
        # Format for Datadog
        datadog_events = [
            {
                "ddsource": "sark",
                "ddtags": f"service:sark,event_type:{e['event']['event_type']},decision:{e['event']['decision']}",
                "hostname": "sark-api",
                "message": json.dumps(e["event"]),
                "timestamp": e["timestamp"] * 1000,  # Datadog uses milliseconds
            }
            for e in events
        ]

        # Compress payload
        payload = gzip.compress(json.dumps(datadog_events).encode())

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.datadog_logs_url,
                headers={
                    "DD-API-KEY": settings.datadog_api_key,
                    "Content-Encoding": "gzip",
                    "Content-Type": "application/json",
                },
                content=payload,
            )
            response.raise_for_status()

        logger.info(
            "gateway_events_forwarded_to_datadog",
            count=len(events),
            compressed_size=len(payload),
        )

    except Exception as e:
        logger.error(
            "datadog_forward_failed",
            error=str(e),
        )


async def _reset_circuit_breaker():
    """Reset circuit breaker after cooldown period."""
    global circuit_breaker_open
    await asyncio.sleep(60)
    circuit_breaker_open = False
    logger.info("siem_circuit_breaker_reset")
