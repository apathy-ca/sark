"""Audit event capture and processing service."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

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
        details: dict[str, Any] | None = None,
        # GRID spec compliance fields
        principal_type: str | None = None,
        principal_attributes: dict[str, Any] | None = None,
        resource_type: str | None = None,
        action_operation: str | None = None,
        action_parameters: dict[str, Any] | None = None,
        policy_version: str | None = None,
        environment: str | None = None,
        success: bool | None = None,
        error_message: str | None = None,
        latency_ms: float | None = None,
        cost: float | None = None,
        retention_days: int | None = None,
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
            principal_type: Type of principal (user, service, system)
            principal_attributes: Structured principal data
            resource_type: Type of resource (tool, server, policy)
            action_operation: Specific operation performed
            action_parameters: Sanitized action parameters
            policy_version: Version of policy evaluated
            environment: Environment (production, staging, development)
            success: Operation success/failure
            error_message: Error details if failed
            latency_ms: Operation latency in milliseconds
            cost: Cost tracking for billing/analytics
            retention_days: Number of days to retain this event

        Returns:
            Created audit event
        """
        # Calculate retention_until from retention_days (default: 90 days)
        retention_until = None
        if retention_days is not None:
            retention_until = datetime.now(UTC) + timedelta(days=retention_days)
        else:
            # Default retention: 90 days
            retention_until = datetime.now(UTC) + timedelta(days=90)

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
            # GRID spec fields
            principal_type=principal_type,
            principal_attributes=principal_attributes,
            resource_type=resource_type,
            action_operation=action_operation,
            action_parameters=action_parameters,
            policy_version=policy_version,
            environment=environment,
            success=success,
            error_message=error_message,
            latency_ms=latency_ms,
            cost=cost,
            retention_until=retention_until,
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
        details: dict[str, Any] | None = None,
        policy_version: str | None = None,
        environment: str | None = None,
        latency_ms: float | None = None,
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
            policy_version: Version of policy that made the decision
            environment: Environment where decision was made
            latency_ms: Time taken to make the decision

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
            # GRID spec fields for authorization decisions
            principal_type="user",
            principal_attributes={"user_id": str(user_id), "email": user_email},
            resource_type="tool",
            action_operation="authorization_check",
            policy_version=policy_version,
            environment=environment,
            success=(decision == "allow"),
            latency_ms=latency_ms,
        )

    async def log_tool_invocation(
        self,
        user_id: UUID,
        user_email: str,
        server_id: UUID,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
        success: bool | None = None,
        error_message: str | None = None,
        latency_ms: float | None = None,
        environment: str | None = None,
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
            success: Whether the invocation succeeded
            error_message: Error message if invocation failed
            latency_ms: Time taken to execute the tool
            environment: Environment where tool was invoked

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
            # GRID spec fields for tool invocations
            principal_type="user",
            principal_attributes={"user_id": str(user_id), "email": user_email},
            resource_type="tool",
            action_operation="invoke",
            action_parameters=parameters,
            environment=environment,
            success=success,
            error_message=error_message,
            latency_ms=latency_ms,
        )

    async def log_server_registration(
        self,
        user_id: UUID,
        user_email: str,
        server_id: UUID,
        server_name: str,
        details: dict[str, Any] | None = None,
        environment: str | None = None,
    ) -> AuditEvent:
        """
        Log MCP server registration.

        Args:
            user_id: User registering the server
            user_email: User email
            server_id: Server ID
            server_name: Server name
            details: Additional details
            environment: Environment where server is registered

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
            # GRID spec fields for server registration
            principal_type="user",
            principal_attributes={"user_id": str(user_id), "email": user_email},
            resource_type="server",
            action_operation="register",
            environment=environment,
            success=True,
        )

    async def log_security_violation(
        self,
        user_id: UUID | None,
        user_email: str | None,
        violation_type: str,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
        environment: str | None = None,
    ) -> AuditEvent:
        """
        Log a security violation event.

        Args:
            user_id: User ID (if known)
            user_email: User email (if known)
            violation_type: Type of security violation
            ip_address: Client IP
            details: Violation details
            environment: Environment where violation occurred

        Returns:
            Created audit event
        """
        principal_attrs = None
        if user_id and user_email:
            principal_attrs = {"user_id": str(user_id), "email": user_email}

        return await self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            details={"violation_type": violation_type, **(details or {})},
            # GRID spec fields for security violations
            principal_type="user" if user_id else "anonymous",
            principal_attributes=principal_attrs,
            action_operation="security_violation",
            environment=environment,
            success=False,  # Security violations are always failures
            error_message=violation_type,
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
