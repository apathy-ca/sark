"""MCP Server and Tool models."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from sark.db.base import Base


class ServerStatus(str, Enum):
    """MCP Server status enumeration."""

    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNHEALTHY = "unhealthy"
    DECOMMISSIONED = "decommissioned"


class TransportType(str, Enum):
    """MCP transport type enumeration."""

    HTTP = "http"
    STDIO = "stdio"
    SSE = "sse"


class SensitivityLevel(str, Enum):
    """Data sensitivity level for access control."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MCPServer(Base):
    """MCP Server registry model."""

    __tablename__ = "mcp_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)

    # Transport configuration
    transport = Column(SQLEnum(TransportType), nullable=False)
    endpoint = Column(String(500), nullable=True)  # For HTTP/SSE transport
    command = Column(String(500), nullable=True)  # For stdio transport

    # MCP protocol
    mcp_version = Column(String(20), nullable=False, default="2025-06-18")
    capabilities = Column(JSON, nullable=False, default=list)

    # Security and classification
    sensitivity_level = Column(
        SQLEnum(SensitivityLevel), nullable=False, default=SensitivityLevel.MEDIUM
    )
    signature = Column(String(1000), nullable=True)  # Cryptographic signature

    # Status and health
    status = Column(SQLEnum(ServerStatus), nullable=False, default=ServerStatus.REGISTERED)
    health_endpoint = Column(String(500), nullable=True)
    last_health_check = Column(DateTime(timezone=True), nullable=True)

    # Ownership and access
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("principals.id", ondelete="SET NULL"), nullable=True
    )
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Service discovery
    consul_id = Column(String(255), nullable=True, unique=True)
    tags = Column(JSON, nullable=False, default=list)
    extra_metadata = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    owner = relationship("Principal", back_populates="owned_servers")
    team = relationship("Team", back_populates="managed_servers")
    tools = relationship("MCPTool", back_populates="server", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of MCP server."""
        return f"<MCPServer(id={self.id}, name={self.name}, status={self.status})>"


class MCPTool(Base):
    """MCP Tool definition model."""

    __tablename__ = "mcp_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
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

    extra_metadata = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    server = relationship("MCPServer", back_populates="tools")

    def __repr__(self) -> str:
        """String representation of MCP tool."""
        return f"<MCPTool(id={self.id}, name={self.name}, server_id={self.server_id})>"
