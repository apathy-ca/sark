"""
Action model for GRID v2.0 protocol abstraction.

Formalizes the Action abstraction as a first-class model per GRID specification.
An Action represents an operation that a principal wants to perform on a resource.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field
from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID

from sark.db.base import Base


class OperationType(str, Enum):
    """
    Operation type enumeration per GRID specification.

    Defines the six core operation types that can be performed on resources:
    - READ: Access information (query, search, retrieve)
    - WRITE: Modify information (create, update, delete)
    - EXECUTE: Run a capability (invoke tool, trigger process)
    - CONTROL: Change behavior (start, stop, reconfigure)
    - MANAGE: Change governance (grant access, revoke, update policy)
    - AUDIT: Access audit logs or compliance data
    """

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    CONTROL = "control"
    MANAGE = "manage"
    AUDIT = "audit"


class ActionContext(PydanticBaseModel):
    """Context information for an action."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="User agent string")
    request_id: str | None = Field(None, description="Request correlation ID")
    environment: str | None = Field(None, description="Environment (dev, staging, prod)")


class ActionRequest(PydanticBaseModel):
    """
    Action request schema for API.

    Represents a request to perform an action on a resource.
    Used in authorization and policy evaluation workflows.
    """

    model_config = ConfigDict(from_attributes=True)

    resource_id: str = Field(..., description="Target resource identifier")
    operation: OperationType = Field(..., description="Operation type to perform")
    parameters: dict = Field(default_factory=dict, description="Action parameters")
    context: ActionContext = Field(default_factory=ActionContext, description="Action context")


class Action(Base):
    """
    Action model for storing historical actions and audit trail.

    This model serves dual purposes:
    1. Historical record of actions performed (audit trail)
    2. Formal representation of Action abstraction per GRID spec

    While actions are often evaluated transiently during authorization,
    this model allows persisting action history for compliance and analytics.
    """

    __tablename__ = "actions"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Core action fields per GRID specification
    resource_id = Column(String(255), nullable=False, index=True)
    operation = Column(SQLEnum(OperationType), nullable=False, index=True)

    # Action parameters and context
    parameters = Column(JSONB, nullable=False, default={})

    # Context fields (optimized for queries)
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
    environment = Column(String(50), nullable=True, index=True)

    # Additional context stored as flexible JSON
    context_metadata = Column(JSONB, nullable=False, default={})

    # Actor information (principal who performed the action)
    principal_id = Column(String(255), nullable=True, index=True)

    # Authorization decision
    authorized = Column(String(20), nullable=True)  # "allow" or "deny"
    policy_id = Column(UUID(as_uuid=True), nullable=True)

    # Performance metadata
    duration_ms = Column(String(20), nullable=True)

    def __repr__(self) -> str:
        """String representation of action."""
        return (
            f"<Action(id={self.id}, resource_id={self.resource_id}, "
            f"operation={self.operation}, timestamp={self.timestamp})>"
        )


__all__ = [
    "Action",
    "ActionContext",
    "ActionRequest",
    "OperationType",
]
