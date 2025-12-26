"""Injection detection response handler.

Handles responses to detected prompt injection attempts:
- Block: High risk injections (risk >= block_threshold)
- Alert: Medium risk injections (risk >= alert_threshold)
- Log: All detections logged to audit
"""

import os
import structlog
from typing import Any
from enum import Enum
from dataclasses import dataclass
from uuid import UUID

from src.sark.security.injection_detector import InjectionDetectionResult, Severity
from src.sark.models.audit import AuditEventType, SeverityLevel

logger = structlog.get_logger()


class ResponseAction(str, Enum):
    """Response action for injection detection."""

    BLOCK = "block"
    ALERT = "alert"
    LOG = "log"


@dataclass
class InjectionResponse:
    """Response to injection detection."""

    action: ResponseAction
    allow: bool
    reason: str
    risk_score: int
    detection_result: InjectionDetectionResult
    audit_id: str | None = None


class InjectionResponseHandler:
    """Handles responses to prompt injection detection results."""

    def __init__(
        self,
        block_threshold: int | None = None,
        alert_threshold: int | None = None,
        config: "InjectionDetectionConfig | None" = None,
    ):
        """
        Initialize response handler with configurable thresholds.

        Args:
            block_threshold: Risk score threshold for blocking (overrides config)
            alert_threshold: Risk score threshold for alerts (overrides config)
            config: Optional configuration. If not provided, loads from environment.
        """
        # Load config if not provided
        if config is None:
            from sark.security.config import get_injection_config
            config = get_injection_config()

        # Use explicit parameters if provided, otherwise use config
        self.block_threshold = block_threshold if block_threshold is not None else config.block_threshold
        self.alert_threshold = alert_threshold if alert_threshold is not None else config.alert_threshold
        self.config = config

        logger.info(
            "injection_response_handler_initialized",
            block_threshold=self.block_threshold,
            alert_threshold=self.alert_threshold,
        )

    async def handle_detection(
        self,
        detection_result: InjectionDetectionResult,
        user_id: UUID | None = None,
        user_email: str | None = None,
        tool_name: str | None = None,
        server_name: str | None = None,
        request_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> InjectionResponse:
        """
        Handle injection detection result and determine response action.

        Flow:
        1. Determine action based on risk score
        2. Log to audit system
        3. Send alerts if needed
        4. Return response with decision

        Args:
            detection_result: Detection result from PromptInjectionDetector
            user_id: User ID (if user request)
            user_email: User email
            tool_name: Tool being invoked
            server_name: Server name
            request_id: Request correlation ID
            parameters: Original request parameters

        Returns:
            InjectionResponse with action and decision
        """
        risk_score = detection_result.risk_score

        # Determine action based on risk score
        if risk_score >= self.block_threshold:
            action = ResponseAction.BLOCK
            allow = False
            reason = f"Blocked: Prompt injection detected (risk score: {risk_score})"
        elif risk_score >= self.alert_threshold:
            action = ResponseAction.ALERT
            allow = True
            reason = f"Alert: Suspicious patterns detected (risk score: {risk_score})"
        else:
            action = ResponseAction.LOG
            allow = True
            reason = f"Logged: Low risk patterns detected (risk score: {risk_score})"

        # Log to audit system
        audit_id = await self._log_to_audit(
            detection_result=detection_result,
            action=action,
            user_id=user_id,
            user_email=user_email,
            tool_name=tool_name,
            server_name=server_name,
            request_id=request_id,
            parameters=parameters,
        )

        # Send alerts for high risk
        if action in (ResponseAction.BLOCK, ResponseAction.ALERT):
            await self._send_alert(
                detection_result=detection_result,
                action=action,
                user_id=user_id,
                user_email=user_email,
                tool_name=tool_name,
                server_name=server_name,
                request_id=request_id,
            )

        logger.info(
            "injection_detection_handled",
            action=action.value,
            allow=allow,
            risk_score=risk_score,
            findings_count=len(detection_result.findings),
            user_id=str(user_id) if user_id else None,
            tool_name=tool_name,
        )

        return InjectionResponse(
            action=action,
            allow=allow,
            reason=reason,
            risk_score=risk_score,
            detection_result=detection_result,
            audit_id=audit_id,
        )

    async def _log_to_audit(
        self,
        detection_result: InjectionDetectionResult,
        action: ResponseAction,
        user_id: UUID | None,
        user_email: str | None,
        tool_name: str | None,
        server_name: str | None,
        request_id: str | None,
        parameters: dict[str, Any] | None,
    ) -> str | None:
        """
        Log injection detection to audit system.

        Args:
            detection_result: Detection result
            action: Response action taken
            user_id: User ID
            user_email: User email
            tool_name: Tool name
            server_name: Server name
            request_id: Request ID
            parameters: Request parameters

        Returns:
            Audit event ID if logging succeeded
        """
        try:
            # Determine audit severity based on action
            severity_map = {
                ResponseAction.BLOCK: SeverityLevel.CRITICAL,
                ResponseAction.ALERT: SeverityLevel.HIGH,
                ResponseAction.LOG: SeverityLevel.MEDIUM,
            }
            severity = severity_map.get(action, SeverityLevel.MEDIUM)

            # Build audit details
            details = {
                "detection_type": "prompt_injection",
                "risk_score": detection_result.risk_score,
                "action": action.value,
                "findings_count": len(detection_result.findings),
                "findings": [
                    {
                        "pattern": f.pattern_name,
                        "severity": f.severity.value,
                        "location": f.location,
                        "description": f.description,
                        "matched_text": f.matched_text[:50],  # Truncate for audit
                    }
                    for f in detection_result.findings[:10]  # Limit to 10 findings
                ],
                "high_entropy_strings": [
                    {"location": loc, "entropy": ent}
                    for loc, ent in detection_result.high_entropy_strings[:5]
                ],
                "server_name": server_name,
                "tool_name": tool_name,
                "request_id": request_id,
            }

            # Log via audit service (simplified - in production would use dependency injection)
            # For now, we'll use structlog with full details
            logger.warning(
                "prompt_injection_detected",
                event_type=AuditEventType.SECURITY_VIOLATION.value,
                severity=severity.value,
                user_id=str(user_id) if user_id else None,
                user_email=user_email,
                details=details,
            )

            # In production, would call:
            # from sark.services.audit.audit_service import AuditService
            # audit_service = AuditService(db)
            # event = await audit_service.log_event(
            #     event_type=AuditEventType.SECURITY_VIOLATION,
            #     severity=severity,
            #     user_id=user_id,
            #     user_email=user_email,
            #     tool_name=tool_name,
            #     decision="deny" if action == ResponseAction.BLOCK else "allow",
            #     request_id=request_id,
            #     details=details,
            # )
            # return str(event.id)

            # For now return a placeholder
            return f"audit_{request_id}" if request_id else None

        except Exception as e:
            logger.error(
                "audit_logging_failed",
                error=str(e),
                user_id=str(user_id) if user_id else None,
            )
            return None

    async def _send_alert(
        self,
        detection_result: InjectionDetectionResult,
        action: ResponseAction,
        user_id: UUID | None,
        user_email: str | None,
        tool_name: str | None,
        server_name: str | None,
        request_id: str | None,
    ) -> None:
        """
        Send alert for high-risk injection detection.

        In production, this would integrate with:
        - Slack/Teams notifications
        - PagerDuty/Opsgenie
        - Email alerts
        - SIEM forwarding

        Args:
            detection_result: Detection result
            action: Response action
            user_id: User ID
            user_email: User email
            tool_name: Tool name
            server_name: Server name
            request_id: Request ID
        """
        try:
            alert_message = (
                f"🚨 Prompt Injection Detected - {action.value.upper()}\n"
                f"Risk Score: {detection_result.risk_score}/100\n"
                f"User: {user_email or user_id}\n"
                f"Tool: {tool_name or 'N/A'}\n"
                f"Server: {server_name or 'N/A'}\n"
                f"Findings: {len(detection_result.findings)}\n"
                f"Request ID: {request_id or 'N/A'}"
            )

            # Log alert (in production would send to actual alert channels)
            logger.warning(
                "injection_alert_sent",
                action=action.value,
                risk_score=detection_result.risk_score,
                user_id=str(user_id) if user_id else None,
                user_email=user_email,
                tool_name=tool_name,
                server_name=server_name,
                request_id=request_id,
                alert_message=alert_message,
            )

            # In production, would integrate with alert manager:
            # await alert_manager.send_alert(
            #     severity="critical" if action == ResponseAction.BLOCK else "warning",
            #     title=f"Prompt Injection {action.value.upper()}",
            #     message=alert_message,
            #     tags=["security", "prompt-injection", action.value],
            # )

        except Exception as e:
            logger.error(
                "alert_sending_failed",
                error=str(e),
                user_id=str(user_id) if user_id else None,
            )


def is_injection_detection_enabled() -> bool:
    """
    Check if injection detection is enabled via configuration.

    Returns:
        True if enabled, False otherwise
    """
    from sark.security.config import get_injection_config
    return get_injection_config().enabled
