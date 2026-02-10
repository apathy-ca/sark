"""Resource model - GRID-compliant generic resource abstraction."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from sark.db.base import Base


class ResourceType(str, Enum):
    """Resource type enumeration per GRID specification."""

    TOOL = "tool"
    DATA = "data"
    SERVICE = "service"
    DEVICE = "device"
    INFRASTRUCTURE = "infrastructure"


class Classification(str, Enum):
    """Data classification level per GRID specification."""

    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    SECRET = "Secret"


class ResourceStatus(str, Enum):
    """Resource status enumeration."""

    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNHEALTHY = "unhealthy"
    DECOMMISSIONED = "decommissioned"


# Association table for resource managers (many-to-many with principals)
resource_managers = Table(
    "resource_managers",
    Base.metadata,
    Column("resource_id", UUID(as_uuid=True), ForeignKey("grid_resources.id", ondelete="CASCADE")),
    Column("principal_id", UUID(as_uuid=True), ForeignKey("principals.id", ondelete="CASCADE")),
)


class GridResource(Base):
    """Generic resource model compliant with GRID specification.

    Replaces the MCP-specific MCPServer model with a generic abstraction
    that can represent tools, data sources, services, devices, and infrastructure.

    MCP-specific fields are stored in the metadata JSON column for backward compatibility.
    """

    __tablename__ = "grid_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)

    # GRID-compliant core fields
    type = Column(SQLEnum(ResourceType), nullable=False, index=True)
    classification = Column(
        SQLEnum(Classification), nullable=False, default=Classification.INTERNAL
    )
    provider_id = Column(String(255), nullable=True, index=True)
    parameters_schema = Column(JSON, nullable=True)

    # Status and health
    status = Column(SQLEnum(ResourceStatus), nullable=False, default=ResourceStatus.REGISTERED)
    health_endpoint = Column(String(500), nullable=True)
    last_health_check = Column(DateTime(timezone=True), nullable=True)

    # Ownership and access control
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("principals.id", ondelete="SET NULL"), nullable=True
    )
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Metadata and extensibility
    # MCP-specific fields stored here: transport, endpoint, command, mcp_version,
    # capabilities, consul_id, signature
    extra_metadata = Column(JSON, nullable=False, default=dict)
    tags = Column(JSON, nullable=False, default=list)

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    owner = relationship("Principal", foreign_keys=[owner_id], back_populates="owned_grid_resources")
    team = relationship("Team", foreign_keys=[team_id], back_populates="managed_grid_resources")
    managers = relationship("Principal", secondary=resource_managers, back_populates="managed_grid_resources")
    tools = relationship("ResourceTool", back_populates="grid_resource", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of resource."""
        return f"<GridResource(id={self.id}, name={self.name}, type={self.type}, status={self.status})>"


class SensitivityLevel(str, Enum):
    """Tool sensitivity level for access control.

    Maintained for backward compatibility with MCPTool.
    New code should use Classification enum on Resource instead.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceTool(Base):
    """Tool definition associated with a resource.

    Replaces MCPTool to work with the generic Resource model.
    Maintains backward compatibility with MCP-specific features.
    """

    __tablename__ = "resource_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(
        UUID(as_uuid=True), ForeignKey("grid_resources.id", ondelete="CASCADE"), nullable=False
    )

    name = Column(String(255), nullable=False, index=True)
    description = Column(String(2000), nullable=True)
    parameters = Column(JSON, nullable=False, default=dict)

    # Security
    sensitivity_level = Column(
        SQLEnum(SensitivityLevel), nullable=False, default=SensitivityLevel.MEDIUM
    )
    signature = Column(String(1000), nullable=True)
    requires_approval = Column(Boolean, default=False, nullable=False)

    # Usage tracking
    invocation_count = Column(Integer, default=0, nullable=False)
    last_invoked = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    extra_metadata = Column(JSON, nullable=False, default=dict)

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    grid_resource = relationship("GridResource", back_populates="tools")

    def __repr__(self) -> str:
        """String representation of resource tool."""
        return f"<ResourceTool(id={self.id}, name={self.name}, resource_id={self.resource_id})>"
