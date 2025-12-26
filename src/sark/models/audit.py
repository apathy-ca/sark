"""Audit event model for TimescaleDB."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from sark.db.base import Base


class AuditEventType(str, Enum):
    """Audit event type enumeration."""

    SERVER_REGISTERED = "server_registered"
    SERVER_UPDATED = "server_updated"
    SERVER_DECOMMISSIONED = "server_decommissioned"
    TOOL_INVOKED = "tool_invoked"
    AUTHORIZATION_ALLOWED = "authorization_allowed"
    AUTHORIZATION_DENIED = "authorization_denied"
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_ACTIVATED = "policy_activated"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SECURITY_VIOLATION = "security_violation"


class SeverityLevel(str, Enum):
    """Event severity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent(Base):
    """Audit event model stored in TimescaleDB."""

    __tablename__ = "audit_events"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Temporal (TimescaleDB hypertable partitioned on this column)
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    # Event classification
    event_type = Column(SQLEnum(AuditEventType), nullable=False, index=True)
    severity = Column(SQLEnum(SeverityLevel), nullable=False, default=SeverityLevel.LOW)

    # Actor information
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)

    # Subject information
    server_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    tool_name = Column(String(255), nullable=True, index=True)

    # Authorization decision
    decision = Column(String(20), nullable=True)  # "allow" or "deny"
    policy_id = Column(UUID(as_uuid=True), nullable=True)

    # Context and details
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True, index=True)

    # Flexible details storage
    details = Column(JSON, nullable=False, default=dict)

    # Retention metadata
    siem_forwarded = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """String representation of audit event."""
        return (
            f"<AuditEvent(id={self.id}, type={self.event_type}, "
            f"timestamp={self.timestamp}, severity={self.severity})>"
        )
