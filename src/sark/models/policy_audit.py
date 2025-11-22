"""Policy audit trail models for tracking decisions and changes."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from sark.db.base import Base


class PolicyDecisionResult(str, Enum):
    """Policy decision result enumeration."""

    ALLOW = "allow"
    DENY = "deny"
    ERROR = "error"


class PolicyChangeType(str, Enum):
    """Policy change type enumeration."""

    CREATED = "created"
    UPDATED = "updated"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    DELETED = "deleted"


class PolicyDecisionLog(Base):
    """Policy decision audit log stored in TimescaleDB.

    Tracks all policy evaluation decisions for compliance and analytics.
    Partitioned by timestamp for efficient time-series queries.
    """

    __tablename__ = "policy_decision_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Temporal (TimescaleDB hypertable partitioned on this column)
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    # Decision outcome
    result = Column(SQLEnum(PolicyDecisionResult), nullable=False, index=True)
    allow = Column(Boolean, nullable=False, index=True)

    # User context
    user_id = Column(String(255), nullable=False, index=True)
    user_role = Column(String(50), nullable=True, index=True)
    user_teams = Column(JSON, nullable=True)

    # Action and resource
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)

    # Tool information (if applicable)
    tool_id = Column(String(255), nullable=True, index=True)
    tool_name = Column(String(255), nullable=True, index=True)
    sensitivity_level = Column(String(20), nullable=True, index=True)

    # Server information (if applicable)
    server_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    server_name = Column(String(255), nullable=True)

    # Policy evaluation details
    policies_evaluated = Column(JSON, nullable=True)  # List of policy names
    policy_results = Column(JSON, nullable=True)  # Detailed results from each policy
    violations = Column(JSON, nullable=True)  # List of violations if denied

    # Reason and audit trail
    reason = Column(Text, nullable=True)
    denial_reason = Column(String(500), nullable=True)

    # Performance metrics
    evaluation_duration_ms = Column(Float, nullable=True)
    cache_hit = Column(Boolean, default=False, index=True)

    # Request context
    client_ip = Column(String(45), nullable=True, index=True)
    geo_country = Column(String(2), nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)

    # MFA and security context
    mfa_verified = Column(Boolean, nullable=True, index=True)
    mfa_method = Column(String(50), nullable=True)
    is_business_hours = Column(Boolean, nullable=True)
    vpn_connection = Column(Boolean, nullable=True)

    # Advanced policy checks
    time_based_allowed = Column(Boolean, nullable=True)
    ip_filtering_allowed = Column(Boolean, nullable=True)
    mfa_required_satisfied = Column(Boolean, nullable=True)

    # Compliance and retention
    compliance_tags = Column(JSON, nullable=True)  # For compliance categorization
    siem_exported = Column(DateTime(timezone=True), nullable=True)
    retention_category = Column(String(50), nullable=True)

    def __repr__(self) -> str:
        """String representation of policy decision log."""
        return (
            f"<PolicyDecisionLog(id={self.id}, result={self.result}, "
            f"user={self.user_id}, action={self.action}, timestamp={self.timestamp})>"
        )


class PolicyChangeLog(Base):
    """Policy change audit log for versioning and compliance.

    Tracks all changes to OPA policies including creation, updates,
    activation, and deletion.
    """

    __tablename__ = "policy_change_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Temporal
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    # Change type
    change_type = Column(SQLEnum(PolicyChangeType), nullable=False, index=True)

    # Policy identification
    policy_name = Column(String(255), nullable=False, index=True)
    policy_version = Column(Integer, nullable=False, index=True)
    policy_bundle = Column(String(100), nullable=True)

    # Change actor
    changed_by_user_id = Column(String(255), nullable=False, index=True)
    changed_by_email = Column(String(255), nullable=True)

    # Policy content (full policy or diff)
    policy_content = Column(Text, nullable=True)  # Full Rego policy content
    policy_diff = Column(Text, nullable=True)  # Diff from previous version
    policy_hash = Column(String(64), nullable=True)  # SHA-256 hash

    # Metadata
    change_reason = Column(Text, nullable=True)
    approval_id = Column(UUID(as_uuid=True), nullable=True)
    approver_user_id = Column(String(255), nullable=True)

    # Deployment info
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    deployment_status = Column(String(50), nullable=True)
    rollback_from_version = Column(Integer, nullable=True)

    # Impact tracking
    affected_users_count = Column(Integer, nullable=True)
    affected_resources_count = Column(Integer, nullable=True)
    breaking_change = Column(Boolean, default=False)

    # Testing and validation
    test_coverage_percent = Column(Float, nullable=True)
    validation_errors = Column(JSON, nullable=True)

    # Additional context
    tags = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        """String representation of policy change log."""
        return (
            f"<PolicyChangeLog(id={self.id}, policy={self.policy_name}, "
            f"version={self.policy_version}, change={self.change_type}, "
            f"timestamp={self.timestamp})>"
        )


class PolicyAnalyticsSummary(Base):
    """Aggregated policy analytics for performance monitoring.

    Pre-computed hourly statistics for fast dashboard queries.
    """

    __tablename__ = "policy_analytics_summary"

    # Composite primary key (time bucket + dimensions)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    time_bucket = Column(DateTime(timezone=True), nullable=False, index=True)

    # Dimensions
    action = Column(String(100), nullable=True, index=True)
    sensitivity_level = Column(String(20), nullable=True, index=True)
    user_role = Column(String(50), nullable=True, index=True)

    # Counts
    total_evaluations = Column(Integer, nullable=False, default=0)
    total_allows = Column(Integer, nullable=False, default=0)
    total_denies = Column(Integer, nullable=False, default=0)
    total_errors = Column(Integer, nullable=False, default=0)

    # Cache statistics
    cache_hits = Column(Integer, nullable=False, default=0)
    cache_misses = Column(Integer, nullable=False, default=0)
    cache_hit_rate = Column(Float, nullable=True)

    # Performance metrics
    avg_duration_ms = Column(Float, nullable=True)
    p50_duration_ms = Column(Float, nullable=True)
    p95_duration_ms = Column(Float, nullable=True)
    p99_duration_ms = Column(Float, nullable=True)
    max_duration_ms = Column(Float, nullable=True)

    # Denial reasons (top 5)
    top_denial_reasons = Column(JSON, nullable=True)

    # Violation counts by policy
    rbac_violations = Column(Integer, default=0)
    team_access_violations = Column(Integer, default=0)
    sensitivity_violations = Column(Integer, default=0)
    time_based_violations = Column(Integer, default=0)
    ip_filtering_violations = Column(Integer, default=0)
    mfa_violations = Column(Integer, default=0)

    # Unique users and resources
    unique_users = Column(Integer, default=0)
    unique_tools = Column(Integer, default=0)
    unique_servers = Column(Integer, default=0)

    # Updated timestamp
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        """String representation of analytics summary."""
        return (
            f"<PolicyAnalyticsSummary(bucket={self.time_bucket}, "
            f"evaluations={self.total_evaluations}, "
            f"allows={self.total_allows}, denies={self.total_denies})>"
        )
