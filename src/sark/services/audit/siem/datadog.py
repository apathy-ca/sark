"""Datadog Logs API integration."""

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

from sark.models.audit import AuditEvent
from sark.services.audit.siem.base import BaseSIEM, SIEMConfig, SIEMHealth

logger = structlog.get_logger()


class DatadogConfig(SIEMConfig):
    """Datadog-specific SIEM configuration."""

    api_key: str = Field(default="", description="Datadog API key")
    app_key: str = Field(default="", description="Datadog Application key (optional)")
    site: str = Field(default="datadoghq.com", description="Datadog site (datadoghq.com, datadoghq.eu, etc.)")
    service: str = Field(default="sark", description="Service name for tagging")
    environment: str = Field(default="production", description="Environment tag (dev, staging, production)")
    hostname: str | None = Field(default=None, description="Hostname for log attribution (optional)")


class DatadogSIEM(BaseSIEM):
    """Datadog SIEM integration using Logs API.

    This class provides integration with Datadog's Logs API
    for forwarding audit events. It supports:
    - Single event and batch forwarding
    - Tag-based categorization
    - Custom attributes
    - SSL/TLS validation
    - Automatic retry with exponential backoff
    - Health checks
    """

    def __init__(self, config: DatadogConfig) -> None:
        """Initialize Datadog SIEM integration.

        Args:
            config: Datadog configuration including API key and site
        """
        super().__init__(config)
        self.datadog_config = config
        self._logger = logger.bind(siem="datadog")

        # Validate configuration
        if not config.api_key:
            self._logger.warning("datadog_api_key_not_configured")

        # Construct API URL based on site
        self._logs_url = f"https://http-intake.logs.{config.site}/api/v2/logs"

        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=config.timeout_seconds,
            verify=config.verify_ssl,
            headers={
                "DD-API-KEY": config.api_key,
                "Content-Type": "application/json",
            },
        )

        self._logger.info(
            "datadog_siem_initialized",
            site=config.site,
            service=config.service,
            environment=config.environment,
            verify_ssl=config.verify_ssl,
        )

    async def send_event(self, event: AuditEvent) -> bool:
        """Send a single audit event to Datadog Logs.

        Args:
            event: Audit event to send

        Returns:
            True if event was sent successfully, False otherwise
        """
        try:
            start_time = datetime.now(UTC)

            # Format event for Datadog
            datadog_event = self._format_datadog_event(event)

            # Send to Datadog Logs API
            response = await self._client.post(
                self._logs_url,
                json=[datadog_event],  # Logs API expects an array
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 202:  # Datadog returns 202 Accepted
                await self._update_success_metrics(event_count=1, latency_ms=latency_ms)
                self._logger.debug(
                    "datadog_event_sent",
                    event_id=str(event.id),
                    latency_ms=latency_ms,
                )
                return True
            else:
                error_type = f"http_{response.status_code}"
                await self._update_failure_metrics(event_count=1, error_type=error_type)
                self._logger.error(
                    "datadog_event_send_failed",
                    event_id=str(event.id),
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return False

        except httpx.TimeoutException as e:
            await self._update_failure_metrics(event_count=1, error_type="timeout")
            self._logger.error(
                "datadog_event_timeout",
                event_id=str(event.id),
                error=str(e),
            )
            raise
        except httpx.ConnectError as e:
            await self._update_failure_metrics(event_count=1, error_type="connection_error")
            self._logger.error(
                "datadog_connection_error",
                event_id=str(event.id),
                error=str(e),
            )
            raise
        except Exception as e:
            await self._update_failure_metrics(event_count=1, error_type=type(e).__name__)
            self._logger.error(
                "datadog_event_send_exception",
                event_id=str(event.id),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def send_batch(self, events: list[AuditEvent]) -> bool:
        """Send a batch of audit events to Datadog Logs.

        Datadog Logs API supports batches of up to 1000 logs per request.

        Args:
            events: List of audit events to send

        Returns:
            True if all events were sent successfully, False otherwise
        """
        if not events:
            self._logger.warning("datadog_empty_batch")
            return True

        try:
            start_time = datetime.now(UTC)

            # Format events for Datadog batch
            datadog_events = [self._format_datadog_event(event) for event in events]

            # Send batch to Datadog Logs API
            response = await self._client.post(
                self._logs_url,
                json=datadog_events,
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 202:  # Datadog returns 202 Accepted
                await self._update_success_metrics(event_count=len(events), latency_ms=latency_ms)
                self._logger.info(
                    "datadog_batch_sent",
                    event_count=len(events),
                    latency_ms=latency_ms,
                )
                return True
            else:
                error_type = f"http_{response.status_code}"
                await self._update_failure_metrics(event_count=len(events), error_type=error_type)
                self._logger.error(
                    "datadog_batch_send_failed",
                    event_count=len(events),
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return False

        except httpx.TimeoutException as e:
            await self._update_failure_metrics(event_count=len(events), error_type="timeout")
            self._logger.error(
                "datadog_batch_timeout",
                event_count=len(events),
                error=str(e),
            )
            raise
        except httpx.ConnectError as e:
            await self._update_failure_metrics(
                event_count=len(events), error_type="connection_error"
            )
            self._logger.error(
                "datadog_batch_connection_error",
                event_count=len(events),
                error=str(e),
            )
            raise
        except Exception as e:
            await self._update_failure_metrics(
                event_count=len(events), error_type=type(e).__name__
            )
            self._logger.error(
                "datadog_batch_send_exception",
                event_count=len(events),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def health_check(self) -> SIEMHealth:
        """Check Datadog Logs API connectivity and health.

        Returns:
            Health check results
        """
        try:
            start_time = datetime.now(UTC)

            # Send a minimal test log to verify connectivity
            test_log = {
                "ddsource": self.datadog_config.service,
                "ddtags": f"env:{self.datadog_config.environment},service:{self.datadog_config.service},health_check:true",
                "message": "SARK health check",
                "service": self.datadog_config.service,
            }

            response = await self._client.post(
                self._logs_url,
                json=[test_log],
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 202:
                self._logger.debug(
                    "datadog_health_check_success",
                    latency_ms=latency_ms,
                )
                return SIEMHealth(
                    healthy=True,
                    latency_ms=latency_ms,
                    details={
                        "logs_url": self._logs_url,
                        "site": self.datadog_config.site,
                        "service": self.datadog_config.service,
                    },
                )
            else:
                self._logger.warning(
                    "datadog_health_check_failed",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return SIEMHealth(
                    healthy=False,
                    latency_ms=latency_ms,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "logs_url": self._logs_url,
                        "status_code": response.status_code,
                    },
                )

        except httpx.TimeoutException as e:
            self._logger.error("datadog_health_check_timeout", error=str(e))
            return SIEMHealth(
                healthy=False,
                error_message=f"Timeout: {str(e)}",
                details={"logs_url": self._logs_url},
            )
        except httpx.ConnectError as e:
            self._logger.error("datadog_health_check_connection_error", error=str(e))
            return SIEMHealth(
                healthy=False,
                error_message=f"Connection error: {str(e)}",
                details={"logs_url": self._logs_url},
            )
        except Exception as e:
            self._logger.error(
                "datadog_health_check_exception",
                error_type=type(e).__name__,
                error=str(e),
            )
            return SIEMHealth(
                healthy=False,
                error_message=f"{type(e).__name__}: {str(e)}",
                details={"logs_url": self._logs_url},
            )

    def format_event(self, event: AuditEvent) -> dict[str, Any]:
        """Format an audit event for Datadog.

        Args:
            event: Audit event to format

        Returns:
            Event formatted as a dictionary suitable for Datadog
        """
        return self._convert_event_to_dict(event)

    def _format_datadog_event(self, event: AuditEvent) -> dict[str, Any]:
        """Format an audit event for Datadog Logs API.

        Datadog expects logs with specific fields:
        - ddsource: Source of the log
        - ddtags: Comma-separated list of tags
        - hostname: Host that generated the log (optional)
        - service: Service name
        - message: Log message
        - Additional custom attributes

        Args:
            event: Audit event to format

        Returns:
            Event formatted for Datadog Logs API
        """
        event_dict = self.format_event(event)

        # Build tags list
        tags = [
            f"env:{self.datadog_config.environment}",
            f"service:{self.datadog_config.service}",
            f"event_type:{event.event_type.value if event.event_type else 'unknown'}",
            f"severity:{event.severity.value if event.severity else 'low'}",
        ]

        # Add user role tag if available (from details)
        if event.details and "user_role" in event.details:
            tags.append(f"user_role:{event.details['user_role']}")

        # Build the Datadog log entry
        datadog_log = {
            "ddsource": self.datadog_config.service,
            "ddtags": ",".join(tags),
            "service": self.datadog_config.service,
            "message": f"SARK audit event: {event.event_type.value if event.event_type else 'unknown'}",
            # Custom attributes
            "sark": event_dict,  # All SARK audit data nested under 'sark' key
            # Additional top-level fields for better searchability
            "event_id": event_dict["id"],
            "event_type": event_dict["event_type"],
            "severity": event_dict["severity"],
            "user_email": event_dict.get("user_email"),
            "decision": event_dict.get("decision"),
        }

        # Add hostname if configured
        if self.datadog_config.hostname:
            datadog_log["hostname"] = self.datadog_config.hostname

        # Add timestamp in milliseconds (Datadog format)
        if event.timestamp:
            datadog_log["timestamp"] = int(event.timestamp.timestamp() * 1000)

        return datadog_log

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        await self._client.aclose()
        self._logger.info("datadog_siem_closed")
