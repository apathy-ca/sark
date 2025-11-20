"""Policy models for OPA integration."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
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
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False)

    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)  # Rego policy content

    is_active = Column(Boolean, default=False, nullable=False)
    tested = Column(Boolean, default=False, nullable=False)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    notes = Column(Text, nullable=True)

    # Relationships
    policy = relationship("Policy", back_populates="versions", foreign_keys=[policy_id])

    def __repr__(self) -> str:
        """String representation of policy version."""
        return f"<PolicyVersion(id={self.id}, policy_id={self.policy_id}, version={self.version})>"
