"""Audit event capture and processing service."""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel

logger = structlog.get_logger()


class AuditService:
    """Service for capturing and processing audit events."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize audit service with TimescaleDB session."""
        self.db = db

    async def log_event(
        self,
        event_type: AuditEventType,
        severity: SeverityLevel = SeverityLevel.LOW,
        user_id: UUID | None = None,
        user_email: str | None = None,
        server_id: UUID | None = None,
        tool_name: str | None = None,
        decision: str | None = None,
        policy_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        details: dict[str, any] | None = None,
    ) -> AuditEvent:
        """
        Log an audit event to TimescaleDB.

        Args:
            event_type: Type of audit event
            severity: Event severity level
            user_id: User ID associated with event
            user_email: User email
            server_id: MCP server ID
            tool_name: Tool name for tool invocations
            decision: Authorization decision (allow/deny)
            policy_id: Policy ID used for decision
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request correlation ID
            details: Additional event details

        Returns:
            Created audit event
        """
        event = AuditEvent(
            timestamp=datetime.now(UTC),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            server_id=server_id,
            tool_name=tool_name,
            decision=decision,
            policy_id=policy_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details=details or {},
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logger.info(
            "audit_event_logged",
            event_id=str(event.id),
            event_type=event_type,
            severity=severity,
            user_id=str(user_id) if user_id else None,
        )

        # If high severity, trigger SIEM forwarding (in production)
        if severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
            await self._forward_to_siem(event)

        return event

    async def log_authorization_decision(
        self,
        user_id: UUID,
        user_email: str,
        tool_name: str,
        decision: str,
        policy_id: UUID | None = None,
        server_id: UUID | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
        details: dict[str, any] | None = None,
    ) -> AuditEvent:
        """
        Log an authorization decision (allow or deny).

        Args:
            user_id: User making the request
            user_email: User email
            tool_name: Tool being accessed
            decision: "allow" or "deny"
            policy_id: Policy that made the decision
            server_id: Server ID
            ip_address: Client IP
            request_id: Request ID
            details: Additional details

        Returns:
            Created audit event
        """
        event_type = (
            AuditEventType.AUTHORIZATION_ALLOWED
            if decision == "allow"
            else AuditEventType.AUTHORIZATION_DENIED
        )

        severity = SeverityLevel.MEDIUM if decision == "deny" else SeverityLevel.LOW

        return await self.log_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            server_id=server_id,
            tool_name=tool_name,
            decision=decision,
            policy_id=policy_id,
            ip_address=ip_address,
            request_id=request_id,
            details=details,
        )

    async def log_tool_invocation(
        self,
        user_id: UUID,
        user_email: str,
        server_id: UUID,
        tool_name: str,
        parameters: dict[str, any] | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> AuditEvent:
        """
        Log a tool invocation event.

        Args:
            user_id: User invoking the tool
            user_email: User email
            server_id: Server ID
            tool_name: Tool name
            parameters: Tool parameters (sensitive data should be filtered)
            ip_address: Client IP
            request_id: Request ID

        Returns:
            Created audit event
        """
        return await self.log_event(
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.LOW,
            user_id=user_id,
            user_email=user_email,
            server_id=server_id,
            tool_name=tool_name,
            ip_address=ip_address,
            request_id=request_id,
            details={"parameters": parameters} if parameters else {},
        )

    async def log_server_registration(
        self,
        user_id: UUID,
        user_email: str,
        server_id: UUID,
        server_name: str,
        details: dict[str, any] | None = None,
    ) -> AuditEvent:
        """
        Log MCP server registration.

        Args:
            user_id: User registering the server
            user_email: User email
            server_id: Server ID
            server_name: Server name
            details: Additional details

        Returns:
            Created audit event
        """
        return await self.log_event(
            event_type=AuditEventType.SERVER_REGISTERED,
            severity=SeverityLevel.MEDIUM,
            user_id=user_id,
            user_email=user_email,
            server_id=server_id,
            details={"server_name": server_name, **(details or {})},
        )

    async def log_security_violation(
        self,
        user_id: UUID | None,
        user_email: str | None,
        violation_type: str,
        ip_address: str | None = None,
        details: dict[str, any] | None = None,
    ) -> AuditEvent:
        """
        Log a security violation event.

        Args:
            user_id: User ID (if known)
            user_email: User email (if known)
            violation_type: Type of security violation
            ip_address: Client IP
            details: Violation details

        Returns:
            Created audit event
        """
        return await self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            details={"violation_type": violation_type, **(details or {})},
        )

    async def _forward_to_siem(self, event: AuditEvent) -> None:
        """
        Forward high-priority events to SIEM (placeholder for integration).

        Args:
            event: Audit event to forward
        """
        # TODO: Implement SIEM integration (Splunk, Datadog, etc.)
        logger.warning(
            "siem_forward_pending",
            event_id=str(event.id),
            event_type=event.event_type,
            severity=event.severity,
        )

        # Mark as forwarded
        event.siem_forwarded = datetime.now(UTC)
        await self.db.commit()
