"""
Injection Response Handler

Handles detected prompt injection attempts based on policy configuration.
Actions: block, alert, or log based on risk score thresholds.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from .injection_detector import InjectionDetectionResult

logger = logging.getLogger(__name__)


class ResponseAction(str, Enum):
    """Action to take in response to injection detection"""
    BLOCK = "block"
    ALLOW_WITH_ALERT = "allow_with_alert"
    ALLOW = "allow"


@dataclass
class InjectionResponse:
    """Response action for detected injection"""
    action: ResponseAction
    message: str
    risk_score: int
    metadata: Dict[str, Any]


class InjectionPolicy:
    """Policy configuration for injection response"""

    def __init__(
        self,
        block_threshold: int = 60,
        alert_threshold: int = 30,
        auto_block_critical: bool = True
    ):
        """
        Initialize injection policy

        Args:
            block_threshold: Risk score threshold to block requests (default: 60)
            alert_threshold: Risk score threshold to send alerts (default: 30)
            auto_block_critical: Auto-block requests with CRITICAL findings (default: True)
        """
        self.block_threshold = block_threshold
        self.alert_threshold = alert_threshold
        self.auto_block_critical = auto_block_critical


class InjectionResponseHandler:
    """Handle detected injections based on policy"""

    def __init__(
        self,
        audit_logger: Optional[Any] = None,
        alert_manager: Optional[Any] = None,
        default_policy: Optional[InjectionPolicy] = None
    ):
        """
        Initialize response handler

        Args:
            audit_logger: Audit logging service
            alert_manager: Alert management service
            default_policy: Default policy (uses standard thresholds if not provided)
        """
        self.audit_logger = audit_logger
        self.alert_manager = alert_manager
        self.default_policy = default_policy or InjectionPolicy()

    async def handle(
        self,
        detection: InjectionDetectionResult,
        request_context: Dict[str, Any],
        policy: Optional[InjectionPolicy] = None
    ) -> InjectionResponse:
        """
        Handle a detection result

        Args:
            detection: Detection result from InjectionDetector
            request_context: Request context (user_id, server_id, tool_name, etc.)
            policy: Optional policy override

        Returns:
            InjectionResponse with action to take
        """
        policy = policy or self.default_policy

        # Check for CRITICAL findings
        has_critical = any(
            f.severity.value == "critical" for f in detection.findings
        )

        if has_critical and policy.auto_block_critical:
            return await self._block_request(
                detection,
                request_context,
                "Critical injection pattern detected"
            )

        # Check risk score thresholds
        if detection.risk_score >= policy.block_threshold:
            return await self._block_request(
                detection,
                request_context,
                f"Risk score {detection.risk_score} exceeds block threshold"
            )

        elif detection.risk_score >= policy.alert_threshold:
            return await self._allow_with_alert(
                detection,
                request_context
            )

        else:
            return await self._allow_with_log(
                detection,
                request_context
            )

    async def _block_request(
        self,
        detection: InjectionDetectionResult,
        request_context: Dict[str, Any],
        reason: str
    ) -> InjectionResponse:
        """Block the request and log event"""

        # Log to audit
        if self.audit_logger:
            try:
                await self.audit_logger.log_event(
                    event_type="injection_blocked",
                    user_id=request_context.get("user_id"),
                    server_id=request_context.get("server_id"),
                    tool_name=request_context.get("tool_name"),
                    risk_score=detection.risk_score,
                    findings=[
                        {
                            "severity": f.severity.value,
                            "pattern": f.pattern_name,
                            "location": f.location,
                        }
                        for f in detection.findings
                    ],
                    reason=reason,
                    action="blocked"
                )
            except Exception as e:
                logger.error(f"Failed to log injection block event: {e}")

        # Send alert
        if self.alert_manager:
            try:
                await self.alert_manager.send_alert(
                    severity="critical",
                    title=f"Prompt injection blocked: {request_context.get('user_id')}",
                    details={
                        "user_id": request_context.get("user_id"),
                        "tool": request_context.get("tool_name"),
                        "risk_score": detection.risk_score,
                        "findings_count": len(detection.findings),
                        "reason": reason
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send injection alert: {e}")

        return InjectionResponse(
            action=ResponseAction.BLOCK,
            message="Request blocked due to potential prompt injection attack",
            risk_score=detection.risk_score,
            metadata={
                "reason": reason,
                "findings_count": len(detection.findings),
                "highest_severity": max(
                    (f.severity.value for f in detection.findings),
                    default="unknown"
                )
            }
        )

    async def _allow_with_alert(
        self,
        detection: InjectionDetectionResult,
        request_context: Dict[str, Any]
    ) -> InjectionResponse:
        """Allow request but send alert"""

        # Log to audit
        if self.audit_logger:
            try:
                await self.audit_logger.log_event(
                    event_type="injection_detected",
                    user_id=request_context.get("user_id"),
                    server_id=request_context.get("server_id"),
                    tool_name=request_context.get("tool_name"),
                    risk_score=detection.risk_score,
                    findings=[
                        {
                            "severity": f.severity.value,
                            "pattern": f.pattern_name,
                            "location": f.location,
                        }
                        for f in detection.findings
                    ],
                    action="allowed_with_alert"
                )
            except Exception as e:
                logger.error(f"Failed to log injection detection event: {e}")

        # Send alert
        if self.alert_manager:
            try:
                await self.alert_manager.send_alert(
                    severity="warning",
                    title=f"Potential prompt injection: {request_context.get('user_id')}",
                    details={
                        "user_id": request_context.get("user_id"),
                        "tool": request_context.get("tool_name"),
                        "risk_score": detection.risk_score,
                        "findings_count": len(detection.findings),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send injection alert: {e}")

        return InjectionResponse(
            action=ResponseAction.ALLOW_WITH_ALERT,
            message="Request allowed but flagged for review",
            risk_score=detection.risk_score,
            metadata={
                "findings_count": len(detection.findings),
                "alert_sent": True
            }
        )

    async def _allow_with_log(
        self,
        detection: InjectionDetectionResult,
        request_context: Dict[str, Any]
    ) -> InjectionResponse:
        """Allow request with minimal logging"""

        # Log to audit (minimal)
        if self.audit_logger:
            try:
                await self.audit_logger.log_event(
                    event_type="injection_scanned",
                    user_id=request_context.get("user_id"),
                    server_id=request_context.get("server_id"),
                    tool_name=request_context.get("tool_name"),
                    risk_score=detection.risk_score,
                    findings_count=len(detection.findings),
                    action="allowed"
                )
            except Exception as e:
                logger.error(f"Failed to log injection scan event: {e}")

        return InjectionResponse(
            action=ResponseAction.ALLOW,
            message="Request allowed",
            risk_score=detection.risk_score,
            metadata={
                "findings_count": len(detection.findings),
            }
        )
