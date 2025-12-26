"""
Anomaly Alert Management System

Processes detected anomalies and sends alerts based on severity and count.
Supports auto-suspend for critical anomalies.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from .behavioral_analyzer import Anomaly, BehavioralAuditEvent

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Configuration for anomaly alerting"""

    # Alert thresholds
    critical_high_count: int = 2  # >= 2 HIGH anomalies = critical alert
    warning_high_count: int = 1  # >= 1 HIGH anomaly = warning alert
    warning_medium_count: int = 3  # >= 3 MEDIUM anomalies = warning alert

    # Auto-suspend configuration
    auto_suspend_enabled: bool = False
    auto_suspend_on_critical: bool = True

    # Alert channels
    pagerduty_enabled: bool = False
    slack_enabled: bool = True
    email_enabled: bool = True


class AnomalyAlertManager:
    """Manages alerts for detected behavioral anomalies"""

    def __init__(
        self,
        audit_logger: Any | None = None,
        alert_service: Any | None = None,
        user_management: Any | None = None,
        config: AlertConfig | None = None,
    ):
        """
        Initialize anomaly alert manager

        Args:
            audit_logger: Audit logging service
            alert_service: Alert delivery service (Slack, PagerDuty, email)
            user_management: User management service for suspensions
            config: Alert configuration
        """
        self.audit_logger = audit_logger
        self.alert_service = alert_service
        self.user_management = user_management
        self.config = config or AlertConfig()

    async def process_anomalies(
        self,
        anomalies: list[Anomaly],
        event: BehavioralAuditEvent,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process detected anomalies and take appropriate actions

        Args:
            anomalies: List of detected anomalies
            event: The audit event that triggered the anomalies
            metadata: Additional metadata for logging

        Returns:
            Dict with processing results
        """
        if not anomalies:
            return {"action": "none", "reason": "no anomalies detected"}

        # Count anomalies by severity
        severity_counts = self._count_by_severity(anomalies)

        # Determine alert level
        alert_level = self._determine_alert_level(severity_counts)

        # Log all anomalies
        await self._log_anomalies(anomalies, event, alert_level, metadata)

        # Send alerts based on level
        if alert_level == "critical":
            await self._handle_critical_alert(anomalies, event, metadata)

            # Auto-suspend if configured
            if self.config.auto_suspend_enabled and self.config.auto_suspend_on_critical:
                await self._suspend_user(event.user_id, anomalies, event)
                return {
                    "action": "suspended",
                    "alert_level": "critical",
                    "anomaly_count": len(anomalies),
                    "severity_counts": severity_counts,
                }

        elif alert_level == "warning":
            await self._handle_warning_alert(anomalies, event, metadata)

        return {
            "action": "alerted" if alert_level != "none" else "logged",
            "alert_level": alert_level,
            "anomaly_count": len(anomalies),
            "severity_counts": severity_counts,
        }

    def _count_by_severity(self, anomalies: list[Anomaly]) -> dict[str, int]:
        """Count anomalies by severity"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for anomaly in anomalies:
            severity = anomaly.severity.value
            if severity in counts:
                counts[severity] += 1

        return counts

    def _determine_alert_level(self, severity_counts: dict[str, int]) -> str:
        """
        Determine alert level based on severity counts

        Returns:
            "critical", "warning", or "none"
        """
        # Critical: multiple high severity or any critical
        if severity_counts["critical"] > 0:
            return "critical"

        if severity_counts["high"] >= self.config.critical_high_count:
            return "critical"

        # Warning: single high or multiple medium
        if severity_counts["high"] >= self.config.warning_high_count:
            return "warning"

        if severity_counts["medium"] >= self.config.warning_medium_count:
            return "warning"

        # Low severity only - just log
        return "none"

    async def _log_anomalies(
        self,
        anomalies: list[Anomaly],
        event: BehavioralAuditEvent,
        alert_level: str,
        metadata: dict[str, Any] | None,
    ):
        """Log anomalies to audit system"""
        if not self.audit_logger:
            return

        try:
            await self.audit_logger.log_event(
                event_type="anomaly_detected",
                user_id=event.user_id,
                timestamp=event.timestamp,
                tool_name=event.tool_name,
                alert_level=alert_level,
                anomaly_count=len(anomalies),
                anomalies=[
                    {
                        "type": a.type.value,
                        "severity": a.severity.value,
                        "description": a.description,
                        "confidence": a.confidence,
                        "baseline": str(a.baseline_value)[:100] if a.baseline_value else None,
                        "observed": str(a.observed_value)[:100] if a.observed_value else None,
                    }
                    for a in anomalies
                ],
                request_id=event.request_id,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.error(f"Failed to log anomalies: {e}")

    async def _handle_critical_alert(
        self, anomalies: list[Anomaly], event: BehavioralAuditEvent, metadata: dict[str, Any] | None
    ):
        """Send critical severity alert"""
        if not self.alert_service:
            logger.warning("No alert service configured - critical alert not sent")
            return

        try:
            # Build alert message
            anomaly_summary = self._build_anomaly_summary(anomalies)

            alert_details = {
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "tool": event.tool_name,
                "anomaly_count": len(anomalies),
                "anomalies": anomaly_summary,
                "request_id": event.request_id,
            }

            if metadata:
                alert_details.update(metadata)

            # Send to PagerDuty for critical alerts
            if self.config.pagerduty_enabled:
                await self.alert_service.send_alert(
                    channel="pagerduty",
                    severity="critical",
                    title=f"CRITICAL: Multiple behavioral anomalies detected - {event.user_id}",
                    details=alert_details,
                )

            # Also send to Slack
            if self.config.slack_enabled:
                await self.alert_service.send_alert(
                    channel="slack",
                    severity="critical",
                    title="🚨 CRITICAL: Behavioral anomalies detected",
                    details=alert_details,
                )

        except Exception as e:
            logger.error(f"Failed to send critical alert: {e}")

    async def _handle_warning_alert(
        self, anomalies: list[Anomaly], event: BehavioralAuditEvent, metadata: dict[str, Any] | None
    ):
        """Send warning severity alert"""
        if not self.alert_service:
            logger.warning("No alert service configured - warning alert not sent")
            return

        try:
            anomaly_summary = self._build_anomaly_summary(anomalies)

            alert_details = {
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "tool": event.tool_name,
                "anomaly_count": len(anomalies),
                "anomalies": anomaly_summary,
                "request_id": event.request_id,
            }

            if metadata:
                alert_details.update(metadata)

            # Send to Slack for warnings
            if self.config.slack_enabled:
                await self.alert_service.send_alert(
                    channel="slack",
                    severity="warning",
                    title=f"⚠️  WARNING: Behavioral anomalies detected - {event.user_id}",
                    details=alert_details,
                )

            # Send email notification
            if self.config.email_enabled:
                await self.alert_service.send_alert(
                    channel="email",
                    severity="warning",
                    title=f"Behavioral anomalies detected for user {event.user_id}",
                    details=alert_details,
                )

        except Exception as e:
            logger.error(f"Failed to send warning alert: {e}")

    async def _suspend_user(
        self, user_id: str, anomalies: list[Anomaly], event: BehavioralAuditEvent
    ):
        """Suspend user account due to critical anomalies"""
        if not self.user_management:
            logger.warning(f"No user management service - cannot suspend user {user_id}")
            return

        try:
            reason = f"Auto-suspended due to {len(anomalies)} behavioral anomalies at {event.timestamp.isoformat()}"

            await self.user_management.suspend_user(
                user_id=user_id,
                reason=reason,
                suspended_by="system:anomaly_detection",
                metadata={
                    "anomaly_count": len(anomalies),
                    "anomaly_types": [a.type.value for a in anomalies],
                    "trigger_event": event.request_id,
                },
            )

            logger.warning(f"User {user_id} auto-suspended due to anomalies")

            # Log suspension
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type="user_auto_suspended",
                    user_id=user_id,
                    reason=reason,
                    anomaly_count=len(anomalies),
                    timestamp=datetime.now(),
                )

        except Exception as e:
            logger.error(f"Failed to suspend user {user_id}: {e}")

    def _build_anomaly_summary(self, anomalies: list[Anomaly]) -> list[dict[str, Any]]:
        """Build human-readable summary of anomalies"""
        summary = []

        for anomaly in anomalies:
            summary.append(
                {
                    "type": anomaly.type.value,
                    "severity": anomaly.severity.value,
                    "description": anomaly.description,
                    "confidence": f"{anomaly.confidence * 100:.0f}%",
                }
            )

        return summary
