"""Principal and team models."""

import enum
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from sark.db.base import Base


class PrincipalType(str, enum.Enum):
    """Types of principals that can authenticate to SARK."""

    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"
    DEVICE = "device"


# Association table for principal-team many-to-many relationship
principal_teams = Table(
    "principal_teams",
    Base.metadata,
    Column("principal_id", UUID(as_uuid=True), ForeignKey("principals.id", ondelete="CASCADE")),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE")),
)


class Principal(Base):
    """Principal model for authentication and authorization.

    A principal represents any entity that can authenticate to SARK:
    - HUMAN: Human users with passwords
    - AGENT: AI agents with API keys or tokens
    - SERVICE: Service accounts for system-to-system communication
    - DEVICE: IoT devices or hardware tokens
    """

    __tablename__ = "principals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), nullable=False, default="developer")
    extra_metadata = Column(JSON, nullable=False, default=dict)

    # Principal type system - distinguishes humans, agents, services, and devices
    principal_type = Column(Enum(PrincipalType), nullable=False, index=True, default=PrincipalType.HUMAN)
    identity_token_type = Column(String(50), nullable=False, default="jwt")
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    teams = relationship("Team", secondary=principal_teams, back_populates="members")
    owned_servers = relationship("MCPServer", back_populates="owner")

    def to_policy_input(self) -> dict:
        """Convert principal to OPA policy input format.

        Returns:
            dict: Principal data formatted for OPA policy evaluation with structure:
                {
                    "id": str,
                    "type": str (human/agent/service/device),
                    "attributes": {
                        "role": str,
                        "teams": list[str],
                        ...extra_metadata
                    }
                }
        """
        return {
            "id": str(self.id),
            "type": self.principal_type.value,
            "attributes": {
                "role": self.role,
                "teams": [t.name for t in self.teams],
                **(self.extra_metadata or {}),
            },
        }

    def __repr__(self) -> str:
        """String representation of principal."""
        return f"<Principal(id={self.id}, email={self.email}, type={self.principal_type.value}, role={self.role})>"


class Team(Base):
    """Team model for group-based access control."""

    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    extra_metadata = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    members = relationship("Principal", secondary=principal_teams, back_populates="teams")
    managed_servers = relationship("MCPServer", back_populates="team")

    def __repr__(self) -> str:
        """String representation of team."""
        return f"<Team(id={self.id}, name={self.name})>"
