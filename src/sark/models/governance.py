"""
SQLite models for home LLM governance.

These models are optimized for SQLite (home deployment) rather than PostgreSQL.
All models support async operations via SQLAlchemy's async extensions.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

# Use a separate base for governance models (SQLite)
GovernanceBase = declarative_base()


# =============================================================================
# Enums
# =============================================================================


class AllowlistEntryType(str, Enum):
    """Type of allowlist entry."""

    DEVICE = "device"  # IP-based device allowlist
    USER = "user"  # User ID allowlist
    MAC = "mac"  # MAC address allowlist


class TimeRuleAction(str, Enum):
    """Action to take when time rule matches."""

    BLOCK = "block"  # Block all requests
    ALERT = "alert"  # Allow but alert
    LOG = "log"  # Allow and log only


class ConsentStatus(str, Enum):
    """Status of a consent request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OverrideStatus(str, Enum):
    """Status of an override request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    USED = "used"


# =============================================================================
# SQLAlchemy ORM Models (SQLite)
# =============================================================================


class AllowlistEntry(GovernanceBase):
    """
    Device/user allowlist entry.

    Devices or users in the allowlist bypass all policy evaluation.
    """

    __tablename__ = "governance_allowlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_type = Column(String(20), nullable=False, default="device", index=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)  # IP, MAC, or user ID
    name = Column(String(100), nullable=True)  # Human-readable name
    reason = Column(String(500), nullable=True)  # Why this is allowlisted
    created_by = Column(String(100), nullable=True)  # Who added this
    active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<AllowlistEntry(id={self.id}, type={self.entry_type}, identifier={self.identifier})>"


class TimeRule(GovernanceBase):
    """
    Time-based access rule.

    Rules define time windows when specific actions (block, alert, log) apply.
    """

    __tablename__ = "governance_time_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    start_time = Column(String(5), nullable=False)  # "HH:MM" format
    end_time = Column(String(5), nullable=False)  # "HH:MM" format
    action = Column(String(20), nullable=False, default="block")
    days = Column(String(50), nullable=True)  # Comma-separated: "mon,tue,wed" or null for all days
    timezone = Column(String(50), nullable=False, default="UTC")
    priority = Column(Integer, nullable=False, default=100)  # Lower = higher priority
    active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<TimeRule(id={self.id}, name={self.name}, action={self.action})>"


class EmergencyOverride(GovernanceBase):
    """
    Emergency override record.

    When active, all policies are bypassed for the duration.
    """

    __tablename__ = "governance_emergency_overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean, default=True, nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    activated_by = Column(String(100), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_by = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<EmergencyOverride(id={self.id}, active={self.active}, expires_at={self.expires_at})>"


class ConsentRequest(GovernanceBase):
    """
    Consent tracking for policy changes.

    Tracks approval workflows for sensitive policy modifications.
    """

    __tablename__ = "governance_consent_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_type = Column(String(100), nullable=False, index=True)  # e.g., "enable_blocking"
    change_description = Column(Text, nullable=False)
    requester = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    required_approvers = Column(Integer, nullable=False, default=1)
    current_approvers = Column(String(500), nullable=True)  # Comma-separated approver IDs
    expires_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<ConsentRequest(id={self.id}, type={self.change_type}, status={self.status})>"


class OverrideRequest(GovernanceBase):
    """
    Per-request override with PIN/password.

    Allows bypassing policy for a specific request with authentication.
    """

    __tablename__ = "governance_override_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(100), unique=True, nullable=False, index=True)  # Original request ID
    pin_hash = Column(String(256), nullable=False)  # Hashed PIN
    status = Column(String(20), nullable=False, default="pending", index=True)
    reason = Column(String(500), nullable=True)
    requested_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<OverrideRequest(id={self.id}, request_id={self.request_id}, status={self.status})>"


class EnforcementDecisionLog(GovernanceBase):
    """
    Log of enforcement decisions.

    Tracks all policy enforcement decisions for audit purposes.
    """

    __tablename__ = "governance_enforcement_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(100), nullable=False, index=True)
    client_ip = Column(String(45), nullable=True, index=True)  # IPv4/IPv6
    allowed = Column(Boolean, nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    decision_source = Column(String(50), nullable=False)  # e.g., "emergency", "allowlist", "time_rule", "opa"
    rule_name = Column(String(100), nullable=True)  # Rule that triggered decision
    policy_name = Column(String(100), nullable=True)  # OPA policy name
    duration_ms = Column(Integer, nullable=True)  # Decision latency
    metadata = Column(Text, nullable=True)  # JSON metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)

    def __repr__(self) -> str:
        return f"<EnforcementDecisionLog(id={self.id}, allowed={self.allowed}, source={self.decision_source})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================


class AllowlistEntryCreate(PydanticBaseModel):
    """Request to add entry to allowlist."""

    entry_type: AllowlistEntryType = Field(default=AllowlistEntryType.DEVICE)
    identifier: str = Field(..., min_length=1, max_length=100, description="IP address, MAC, or user ID")
    name: str | None = Field(None, max_length=100, description="Human-readable name")
    reason: str | None = Field(None, max_length=500, description="Reason for allowlisting")
    expires_at: datetime | None = Field(None, description="Optional expiration time")

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str, info: Any) -> str:
        """Validate identifier based on entry type."""
        v = v.strip()
        if not v:
            raise ValueError("Identifier cannot be empty")
        return v


class AllowlistEntryResponse(PydanticBaseModel):
    """Allowlist entry response."""

    id: int
    entry_type: str
    identifier: str
    name: str | None
    reason: str | None
    active: bool
    expires_at: datetime | None
    created_at: datetime
    created_by: str | None

    class Config:
        from_attributes = True


class TimeRuleCreate(PydanticBaseModel):
    """Request to create time rule."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Start time in HH:MM format")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="End time in HH:MM format")
    action: TimeRuleAction = Field(default=TimeRuleAction.BLOCK)
    days: list[str] | None = Field(None, description="Days of week (mon,tue,wed,etc.) or null for all")
    timezone: str = Field(default="UTC")
    priority: int = Field(default=100, ge=0, le=1000)


class TimeRuleResponse(PydanticBaseModel):
    """Time rule response."""

    id: int
    name: str
    description: str | None
    start_time: str
    end_time: str
    action: str
    days: str | None
    timezone: str
    priority: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TimeCheckResult(PydanticBaseModel):
    """Result of time rule check."""

    blocked: bool = Field(description="Whether request is blocked by time rules")
    rule: str | None = Field(None, description="Name of matching rule")
    action: str | None = Field(None, description="Action from matching rule")
    reason: str | None = Field(None, description="Human-readable reason")


class EmergencyOverrideCreate(PydanticBaseModel):
    """Request to activate emergency override."""

    duration_minutes: int = Field(..., ge=1, le=1440, description="Duration in minutes (max 24 hours)")
    reason: str = Field(..., min_length=1, max_length=500)


class EmergencyOverrideResponse(PydanticBaseModel):
    """Emergency override response."""

    id: int
    active: bool
    reason: str
    activated_by: str | None
    activated_at: datetime
    expires_at: datetime
    deactivated_at: datetime | None

    class Config:
        from_attributes = True


class ConsentRequestCreate(PydanticBaseModel):
    """Request to create consent request."""

    change_type: str = Field(..., min_length=1, max_length=100)
    change_description: str = Field(..., min_length=1)
    required_approvers: int = Field(default=1, ge=1, le=10)
    expires_in_hours: int | None = Field(None, ge=1, le=168, description="Hours until expiration")


class ConsentRequestResponse(PydanticBaseModel):
    """Consent request response."""

    id: int
    change_type: str
    change_description: str
    requester: str
    status: str
    required_approvers: int
    current_approvers: list[str]
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class OverrideRequestCreate(PydanticBaseModel):
    """Request to create per-request override."""

    request_id: str = Field(..., min_length=1, max_length=100)
    pin: str = Field(..., min_length=4, max_length=20, description="Override PIN")
    reason: str | None = Field(None, max_length=500)
    expires_in_minutes: int = Field(default=5, ge=1, le=60)


class OverrideRequestResponse(PydanticBaseModel):
    """Override request response."""

    id: int
    request_id: str
    status: str
    reason: str | None
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class EnforcementDecision(PydanticBaseModel):
    """Result of enforcement evaluation."""

    allowed: bool = Field(description="Whether the request is allowed")
    reason: str = Field(description="Reason for decision")
    decision_source: str = Field(description="Source of decision (emergency, allowlist, time_rule, opa)")
    rule: str | None = Field(None, description="Rule name if applicable")
    policy: str | None = Field(None, description="Policy name if applicable")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "AllowlistEntryType",
    "ConsentStatus",
    "OverrideStatus",
    "TimeRuleAction",
    # SQLAlchemy models
    "AllowlistEntry",
    "ConsentRequest",
    "EmergencyOverride",
    "EnforcementDecisionLog",
    "GovernanceBase",
    "OverrideRequest",
    "TimeRule",
    # Pydantic schemas
    "AllowlistEntryCreate",
    "AllowlistEntryResponse",
    "ConsentRequestCreate",
    "ConsentRequestResponse",
    "EmergencyOverrideCreate",
    "EmergencyOverrideResponse",
    "EnforcementDecision",
    "OverrideRequestCreate",
    "OverrideRequestResponse",
    "TimeCheckResult",
    "TimeRuleCreate",
    "TimeRuleResponse",
]
