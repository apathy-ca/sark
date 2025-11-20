"""MCP Server registration and management endpoints."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sark.db import get_db, get_timescale_db
from sark.models.audit import AuditEventType, SeverityLevel
from sark.models.mcp_server import SensitivityLevel, TransportType
from sark.services.audit import AuditService
from sark.services.discovery import DiscoveryService

logger = structlog.get_logger()
router = APIRouter()


class ToolDefinition(BaseModel):
    """Tool definition schema."""

    name: str = Field(..., description="Tool name")
    description: str | None = Field(None, description="Tool description")
    parameters: dict[str, any] = Field(default_factory=dict, description="Tool parameters schema")
    sensitivity_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    signature: str | None = Field(None, description="Cryptographic signature")
    requires_approval: bool = Field(default=False)


class ServerRegistrationRequest(BaseModel):
    """Server registration request schema."""

    name: str = Field(..., min_length=1, max_length=255)
    transport: str = Field(..., pattern="^(http|stdio|sse)$")
    endpoint: str | None = Field(None, max_length=500)
    command: str | None = Field(None, max_length=500)
    version: str = Field(default="2025-06-18")
    capabilities: list[str] = Field(default_factory=list)
    tools: list[ToolDefinition]
    description: str | None = Field(None, max_length=1000)
    sensitivity_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    signature: str | None = None
    metadata: dict[str, any] = Field(default_factory=dict)


class ServerResponse(BaseModel):
    """Server response schema."""

    server_id: UUID
    status: str
    consul_id: str | None


@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def register_server(
    request: ServerRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    audit_db: AsyncSession = Depends(get_timescale_db),
) -> ServerResponse:
    """
    Register a new MCP server.

    This endpoint allows registration of MCP servers with the governance system.
    The server will be added to the service registry and subject to policy controls.
    """
    try:
        discovery_service = DiscoveryService(db)
        audit_service = AuditService(audit_db)

        # TODO: Extract user from authentication token
        # For now, using placeholder values
        user_id = UUID("00000000-0000-0000-0000-000000000000")
        user_email = "system@sark.local"

        # TODO: Check authorization via OPA
        # For MVP, allow all registrations

        # Register server
        server = await discovery_service.register_server(
            name=request.name,
            transport=TransportType(request.transport),
            mcp_version=request.version,
            capabilities=request.capabilities,
            tools=[tool.model_dump() for tool in request.tools],
            endpoint=request.endpoint,
            command=request.command,
            description=request.description,
            sensitivity_level=request.sensitivity_level,
            signature=request.signature,
            metadata=request.metadata,
        )

        # Log audit event
        await audit_service.log_event(
            event_type=AuditEventType.SERVER_REGISTERED,
            severity=SeverityLevel.MEDIUM,
            user_id=user_id,
            user_email=user_email,
            server_id=server.id,
            details={
                "server_name": server.name,
                "transport": request.transport,
                "tool_count": len(request.tools),
            },
        )

        return ServerResponse(
            server_id=server.id,
            status=server.status.value,
            consul_id=server.consul_id,
        )

    except Exception as e:
        logger.error("server_registration_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server registration failed",
        ) from e


@router.get("/{server_id}")
async def get_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, any]:
    """Get server details by ID."""
    discovery_service = DiscoveryService(db)
    server = await discovery_service.get_server(server_id)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    # Get server tools
    tools = await discovery_service.get_server_tools(server_id)

    return {
        "id": str(server.id),
        "name": server.name,
        "description": server.description,
        "transport": server.transport.value,
        "endpoint": server.endpoint,
        "status": server.status.value,
        "sensitivity_level": server.sensitivity_level.value,
        "tools": [
            {
                "id": str(tool.id),
                "name": tool.name,
                "description": tool.description,
                "sensitivity_level": tool.sensitivity_level.value,
            }
            for tool in tools
        ],
        "metadata": server.metadata,
        "created_at": server.created_at.isoformat(),
    }


@router.get("/")
async def list_servers(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, any]]:
    """List all registered MCP servers."""
    discovery_service = DiscoveryService(db)

    # TODO: Add pagination
    servers = await discovery_service.list_servers()

    return [
        {
            "id": str(server.id),
            "name": server.name,
            "transport": server.transport.value,
            "status": server.status.value,
            "sensitivity_level": server.sensitivity_level.value,
            "created_at": server.created_at.isoformat(),
        }
        for server in servers
    ]
