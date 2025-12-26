"""
Base models for SARK v2.0 protocol abstraction.

These base classes will be used by all protocol adapters in v2.0.
For v1.x, they serve as a foundation for gradual migration.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from sark.db.base import Base


class ResourceBase:
    """
    Base class for all resource types (MCP servers, HTTP APIs, gRPC services, etc.).

    In v2.0, this will be the parent class for protocol-specific resource models.
    For v1.x, MCPServer can optionally inherit from this to prepare for migration.
    """

    @declared_attr
    def id(cls):
        """Unique resource identifier"""
        return Column(String, primary_key=True)

    @declared_attr
    def name(cls):
        """Human-readable resource name"""
        return Column(String, nullable=False, index=True)

    @declared_attr
    def protocol(cls):
        """Protocol type: 'mcp', 'http', 'grpc', etc."""
        return Column(String, nullable=False, index=True, default="mcp")

    @declared_attr
    def endpoint(cls):
        """Resource endpoint (command, URL, host:port, etc.)"""
        return Column(String, nullable=False)

    @declared_attr
    def sensitivity_level(cls):
        """Sensitivity classification: 'low', 'medium', 'high', 'critical'"""
        return Column(String, nullable=False, default="medium", index=True)

    @declared_attr
    def metadata(cls):
        """Protocol-specific metadata (JSON)"""
        return Column(JSON, default={})

    @declared_attr
    def created_at(cls):
        """Resource creation timestamp"""
        return Column(DateTime, nullable=False, default=datetime.utcnow)

    @declared_attr
    def updated_at(cls):
        """Resource last update timestamp"""
        return Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CapabilityBase:
    """
    Base class for all capability types (MCP tools, HTTP endpoints, gRPC methods, etc.).

    In v2.0, this will be the parent class for protocol-specific capability models.
    For v1.x, MCPTool can optionally inherit from this to prepare for migration.
    """

    @declared_attr
    def id(cls):
        """Unique capability identifier"""
        return Column(String, primary_key=True)

    @declared_attr
    def resource_id(cls):
        """ID of the resource this capability belongs to"""
        return Column(String, nullable=False, index=True)

    @declared_attr
    def name(cls):
        """Capability name"""
        return Column(String, nullable=False, index=True)

    @declared_attr
    def description(cls):
        """Capability description"""
        return Column(Text, nullable=True)

    @declared_attr
    def input_schema(cls):
        """Input schema (JSON Schema or protocol-specific)"""
        return Column(JSON, default={})

    @declared_attr
    def output_schema(cls):
        """Output schema (JSON Schema or protocol-specific)"""
        return Column(JSON, default={})

    @declared_attr
    def sensitivity_level(cls):
        """Sensitivity classification: 'low', 'medium', 'high', 'critical'"""
        return Column(String, nullable=False, default="medium", index=True)

    @declared_attr
    def metadata(cls):
        """Protocol-specific metadata (JSON)"""
        return Column(JSON, default={})


# Pydantic models for API requests/responses (v2.0 preview)


class ResourceSchema(PydanticBaseModel):
    """Generic resource schema for API"""

    id: str
    name: str
    protocol: str
    endpoint: str
    sensitivity_level: str = "medium"
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CapabilitySchema(PydanticBaseModel):
    """Generic capability schema for API"""

    id: str
    resource_id: str
    name: str
    description: str | None = None
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}
    sensitivity_level: str = "medium"
    metadata: dict[str, Any] = {}

    class Config:
        from_attributes = True


class InvocationRequest(PydanticBaseModel):
    """Universal invocation request (v2.0)"""

    capability_id: str
    principal_id: str
    arguments: dict[str, Any]
    context: dict[str, Any] = {}


class InvocationResult(PydanticBaseModel):
    """Universal invocation result (v2.0)"""

    success: bool
    result: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = {}
    duration_ms: float


# ============================================================================
# SQLAlchemy ORM Models (v2.0)
# ============================================================================


class Resource(Base):
    """
    Universal resource model for v2.0.

    Represents any governed entity: MCP servers, REST APIs, gRPC services, etc.
    Protocol-specific details are stored in the metadata_ JSONB column.
    """

    __tablename__ = "resources"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    protocol = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(1000), nullable=False)
    sensitivity_level = Column(String(20), nullable=False, default="medium", index=True)
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default={}
    )  # Use metadata_ to avoid SQLAlchemy reserved name
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    capabilities = relationship(
        "Capability", back_populates="resource", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resource(id={self.id}, name={self.name}, protocol={self.protocol})>"


class Capability(Base):
    """
    Universal capability model for v2.0.

    Represents any executable capability: MCP tools, HTTP endpoints, gRPC methods, etc.
    Protocol-specific details are stored in the metadata_ JSONB column.
    """

    __tablename__ = "capabilities"

    id = Column(String(255), primary_key=True)
    resource_id = Column(
        String(255), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    input_schema = Column(JSONB, nullable=False, default={})
    output_schema = Column(JSONB, nullable=False, default={})
    sensitivity_level = Column(String(20), nullable=False, default="medium", index=True)
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default={}
    )  # Use metadata_ to avoid SQLAlchemy reserved name

    # Relationships
    resource = relationship("Resource", back_populates="capabilities")

    def __repr__(self) -> str:
        return f"<Capability(id={self.id}, name={self.name}, resource_id={self.resource_id})>"


class FederationNode(Base):
    """
    Federation node model for cross-organization governance.

    Represents a trusted SARK instance in another organization.
    mTLS trust is established via the trust_anchor_cert.
    """

    __tablename__ = "federation_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    endpoint = Column(String(500), nullable=False)
    trust_anchor_cert = Column(Text, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    trusted_since = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    rate_limit_per_hour = Column(Integer, nullable=True, default=10000)
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default={}
    )  # Use metadata_ to avoid SQLAlchemy reserved name
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<FederationNode(node_id={self.node_id}, name={self.name}, enabled={self.enabled})>"


class CostTracking(Base):
    """
    Cost tracking model for time-series cost attribution.

    Stores per-invocation cost data for budget management and analytics.
    This table is converted to a TimescaleDB hypertable for efficient time-series queries.
    """

    __tablename__ = "cost_tracking"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    principal_id = Column(String(255), nullable=False, index=True)
    resource_id = Column(String(255), nullable=False, index=True)
    capability_id = Column(String(255), nullable=False, index=True)
    estimated_cost = Column(Numeric(10, 4), nullable=True)
    actual_cost = Column(Numeric(10, 4), nullable=True)
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default={}
    )  # Use metadata_ to avoid SQLAlchemy reserved name

    def __repr__(self) -> str:
        return f"<CostTracking(id={self.id}, principal_id={self.principal_id}, cost={self.actual_cost})>"


class PrincipalBudget(Base):
    """
    Principal budget model for cost limits and tracking.

    Stores daily/monthly budget limits and current spending for each principal.
    Budgets are automatically reset based on last_daily_reset and last_monthly_reset timestamps.
    """

    __tablename__ = "principal_budgets"

    principal_id = Column(String(255), primary_key=True, index=True)
    daily_budget = Column(Numeric(10, 2), nullable=True)
    monthly_budget = Column(Numeric(10, 2), nullable=True)
    daily_spent = Column(Numeric(10, 4), nullable=False, default=0)
    monthly_spent = Column(Numeric(10, 4), nullable=False, default=0)
    last_daily_reset = Column(DateTime(timezone=True), nullable=True)
    last_monthly_reset = Column(DateTime(timezone=True), nullable=True)
    currency = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<PrincipalBudget(principal_id={self.principal_id}, daily={self.daily_budget}, monthly={self.monthly_budget})>"


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "Capability",
    "CapabilityBase",
    "CapabilitySchema",
    "CostTracking",
    "FederationNode",
    "InvocationRequest",
    "InvocationResult",
    "PrincipalBudget",
    # v2.0 SQLAlchemy models
    "Resource",
    # Legacy mixin classes (for backward compatibility)
    "ResourceBase",
    # Pydantic schemas
    "ResourceSchema",
]
