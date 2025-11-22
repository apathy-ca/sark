"""Splunk HTTP Event Collector (HEC) integration."""

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

from sark.models.audit import AuditEvent
from sark.services.audit.siem.base import BaseSIEM, SIEMConfig, SIEMHealth

logger = structlog.get_logger()


class SplunkConfig(SIEMConfig):
    """Splunk-specific SIEM configuration."""

    hec_url: str = Field(
        default="https://localhost:8088/services/collector",
        description="Splunk HEC endpoint URL",
    )
    hec_token: str = Field(default="", description="Splunk HEC authentication token")
    index: str = Field(default="sark_audit", description="Splunk index name")
    sourcetype: str = Field(
        default="sark:audit:event", description="Splunk sourcetype for events"
    )
    source: str = Field(default="sark", description="Splunk source field")
    host: str | None = Field(default=None, description="Splunk host field (optional)")


class SplunkSIEM(BaseSIEM):
    """Splunk SIEM integration using HTTP Event Collector (HEC).

    This class provides integration with Splunk's HTTP Event Collector (HEC)
    for forwarding audit events. It supports:
    - Single event and batch forwarding
    - Custom index and sourcetype configuration
    - SSL/TLS validation
    - Automatic retry with exponential backoff
    - Health checks
    """

    def __init__(self, config: SplunkConfig) -> None:
        """Initialize Splunk SIEM integration.

        Args:
            config: Splunk configuration including HEC URL and token
        """
        super().__init__(config)
        self.splunk_config = config
        self._logger = logger.bind(siem="splunk")

        # Validate configuration
        if not config.hec_token:
            self._logger.warning("splunk_hec_token_not_configured")

        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=config.timeout_seconds,
            verify=config.verify_ssl,
            headers={
                "Authorization": f"Splunk {config.hec_token}",
                "Content-Type": "application/json",
            },
        )

        self._logger.info(
            "splunk_siem_initialized",
            hec_url=config.hec_url,
            index=config.index,
            sourcetype=config.sourcetype,
            verify_ssl=config.verify_ssl,
        )

    async def send_event(self, event: AuditEvent) -> bool:
        """Send a single audit event to Splunk HEC.

        Args:
            event: Audit event to send

        Returns:
            True if event was sent successfully, False otherwise
        """
        try:
            start_time = datetime.now(UTC)

            # Format event for Splunk
            splunk_event = self._format_hec_event(event)

            # Send to HEC
            response = await self._client.post(
                self.splunk_config.hec_url,
                json=splunk_event,
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                await self._update_success_metrics(event_count=1, latency_ms=latency_ms)
                self._logger.debug(
                    "splunk_event_sent",
                    event_id=str(event.id),
                    latency_ms=latency_ms,
                )
                return True
            else:
                error_type = f"http_{response.status_code}"
                await self._update_failure_metrics(event_count=1, error_type=error_type)
                self._logger.error(
                    "splunk_event_send_failed",
                    event_id=str(event.id),
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return False

        except httpx.TimeoutException as e:
            await self._update_failure_metrics(event_count=1, error_type="timeout")
            self._logger.error(
                "splunk_event_timeout",
                event_id=str(event.id),
                error=str(e),
            )
            raise
        except httpx.ConnectError as e:
            await self._update_failure_metrics(event_count=1, error_type="connection_error")
            self._logger.error(
                "splunk_connection_error",
                event_id=str(event.id),
                error=str(e),
            )
            raise
        except Exception as e:
            await self._update_failure_metrics(event_count=1, error_type=type(e).__name__)
            self._logger.error(
                "splunk_event_send_exception",
                event_id=str(event.id),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def send_batch(self, events: list[AuditEvent]) -> bool:
        """Send a batch of audit events to Splunk HEC.

        Splunk HEC supports multiple events in a single request by
        concatenating JSON objects separated by newlines.

        Args:
            events: List of audit events to send

        Returns:
            True if all events were sent successfully, False otherwise
        """
        if not events:
            self._logger.warning("splunk_empty_batch")
            return True

        try:
            start_time = datetime.now(UTC)

            # Format events for batch HEC request
            # Splunk HEC batch format: multiple JSON objects separated by newlines
            import json
            batch_payload = "\n".join(
                json.dumps(self._format_hec_event(event))
                for event in events
            )

            # Send batch to HEC
            response = await self._client.post(
                self.splunk_config.hec_url,
                content=batch_payload,
                headers={
                    "Authorization": f"Splunk {self.splunk_config.hec_token}",
                    "Content-Type": "application/json",
                },
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                await self._update_success_metrics(event_count=len(events), latency_ms=latency_ms)
                self._logger.info(
                    "splunk_batch_sent",
                    event_count=len(events),
                    latency_ms=latency_ms,
                )
                return True
            else:
                error_type = f"http_{response.status_code}"
                await self._update_failure_metrics(event_count=len(events), error_type=error_type)
                self._logger.error(
                    "splunk_batch_send_failed",
                    event_count=len(events),
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return False

        except httpx.TimeoutException as e:
            await self._update_failure_metrics(event_count=len(events), error_type="timeout")
            self._logger.error(
                "splunk_batch_timeout",
                event_count=len(events),
                error=str(e),
            )
            raise
        except httpx.ConnectError as e:
            await self._update_failure_metrics(
                event_count=len(events), error_type="connection_error"
            )
            self._logger.error(
                "splunk_batch_connection_error",
                event_count=len(events),
                error=str(e),
            )
            raise
        except Exception as e:
            await self._update_failure_metrics(
                event_count=len(events), error_type=type(e).__name__
            )
            self._logger.error(
                "splunk_batch_send_exception",
                event_count=len(events),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def health_check(self) -> SIEMHealth:
        """Check Splunk HEC connectivity and health.

        Returns:
            Health check results
        """
        try:
            start_time = datetime.now(UTC)

            # Use HEC health endpoint
            health_url = self.splunk_config.hec_url.replace("/services/collector", "/services/collector/health")

            response = await self._client.get(health_url)

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                self._logger.debug(
                    "splunk_health_check_success",
                    latency_ms=latency_ms,
                )
                return SIEMHealth(
                    healthy=True,
                    latency_ms=latency_ms,
                    details={
                        "hec_url": self.splunk_config.hec_url,
                        "index": self.splunk_config.index,
                        "response": response.text,
                    },
                )
            else:
                self._logger.warning(
                    "splunk_health_check_failed",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return SIEMHealth(
                    healthy=False,
                    latency_ms=latency_ms,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "hec_url": self.splunk_config.hec_url,
                        "status_code": response.status_code,
                    },
                )

        except httpx.TimeoutException as e:
            self._logger.error("splunk_health_check_timeout", error=str(e))
            return SIEMHealth(
                healthy=False,
                error_message=f"Timeout: {str(e)}",
                details={"hec_url": self.splunk_config.hec_url},
            )
        except httpx.ConnectError as e:
            self._logger.error("splunk_health_check_connection_error", error=str(e))
            return SIEMHealth(
                healthy=False,
                error_message=f"Connection error: {str(e)}",
                details={"hec_url": self.splunk_config.hec_url},
            )
        except Exception as e:
            self._logger.error(
                "splunk_health_check_exception",
                error_type=type(e).__name__,
                error=str(e),
            )
            return SIEMHealth(
                healthy=False,
                error_message=f"{type(e).__name__}: {str(e)}",
                details={"hec_url": self.splunk_config.hec_url},
            )

    def format_event(self, event: AuditEvent) -> dict[str, Any]:
        """Format an audit event for Splunk.

        Args:
            event: Audit event to format

        Returns:
            Event formatted as a dictionary suitable for Splunk
        """
        return self._convert_event_to_dict(event)

    def _format_hec_event(self, event: AuditEvent) -> dict[str, Any]:
        """Format an audit event for Splunk HEC.

        Splunk HEC expects events in a specific format with metadata
        (time, source, sourcetype, index, host) and the event data.

        Args:
            event: Audit event to format

        Returns:
            Event formatted for HEC
        """
        event_dict = self.format_event(event)

        # HEC event format
        hec_event = {
            "time": event.timestamp.timestamp() if event.timestamp else None,
            "source": self.splunk_config.source,
            "sourcetype": self.splunk_config.sourcetype,
            "index": self.splunk_config.index,
            "event": event_dict,
        }

        # Add host if configured
        if self.splunk_config.host:
            hec_event["host"] = self.splunk_config.host

        return hec_event

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        await self._client.aclose()
        self._logger.info("splunk_siem_closed")
