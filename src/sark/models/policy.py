"""Policy models for OPA integration."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from sark.db.base import Base


class PolicyStatus(str, Enum):
    """Policy status enumeration."""

    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class PolicyType(str, Enum):
    """Policy type enumeration."""

    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    AUDIT = "audit"


class Effect(str, Enum):
    """Policy rule effect enumeration."""

    ALLOW = "allow"
    DENY = "deny"
    CONSTRAIN = "constrain"


class Policy(Base):
    """Policy definition model."""

    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(1000), nullable=True)

    policy_type = Column(SQLEnum(PolicyType), nullable=False, default=PolicyType.AUTHORIZATION)
    status = Column(SQLEnum(PolicyStatus), nullable=False, default=PolicyStatus.DRAFT)

    # Current active version
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    versions = relationship(
        "PolicyVersion",
        back_populates="policy",
        foreign_keys="PolicyVersion.policy_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation of policy."""
        return f"<Policy(id={self.id}, name={self.name}, status={self.status})>"


class PolicyVersion(Base):
    """Policy version model for versioning and rollback."""

    __tablename__ = "policy_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    policy_id = Column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )

    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)  # Rego policy content

    is_active = Column(Boolean, default=False, nullable=False)
    tested = Column(Boolean, default=False, nullable=False)

    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    notes = Column(Text, nullable=True)

    # Relationships
    policy = relationship("Policy", back_populates="versions", foreign_keys=[policy_id])
    rules = relationship(
        "PolicyRule",
        back_populates="policy_version",
        cascade="all, delete-orphan",
        order_by="PolicyRule.priority",
    )

    def __repr__(self) -> str:
        """String representation of policy version."""
        return f"<PolicyVersion(id={self.id}, policy_id={self.policy_id}, version={self.version})>"


class PolicyRule(Base):
    """Structured policy rule metadata for introspection and composition.

    This model stores structured metadata alongside Rego content to enable
    programmatic policy introspection and composition. The Rego content in
    PolicyVersion is still used for actual OPA evaluation.
    """

    __tablename__ = "policy_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    policy_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False, default=0, index=True)
    effect = Column(SQLEnum(Effect), nullable=False)

    # Matchers stored as JSON arrays
    principal_matchers = Column(JSON, nullable=False, default=list)
    resource_matchers = Column(JSON, nullable=False, default=list)
    action_matchers = Column(JSON, nullable=False, default=list)

    # Conditions and constraints stored as JSON arrays
    conditions = Column(JSON, nullable=False, default=list)
    constraints = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    # Relationships
    policy_version = relationship("PolicyVersion", back_populates="rules")

    def __repr__(self) -> str:
        """String representation of policy rule."""
        return f"<PolicyRule(id={self.id}, name={self.name}, effect={self.effect}, priority={self.priority})>"
