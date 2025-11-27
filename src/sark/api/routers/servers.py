"""MCP Server registration and management endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.api.pagination import PaginatedResponse, PaginationParams
from sark.db import get_db, get_timescale_db
from sark.models.audit import AuditEventType, SeverityLevel
from sark.models.mcp_server import TransportType
from sark.services.audit import AuditService
from sark.services.auth import UserContext, get_current_user
from sark.services.discovery import DiscoveryService
from sark.services.policy import OPAClient

logger = structlog.get_logger()
router = APIRouter()


class ToolDefinition(BaseModel):
    """Tool definition schema."""

    name: str = Field(..., description="Tool name")
    description: str | None = Field(None, description="Tool description")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters schema")
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
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "name": "analytics-server",
                "description": "Analytics MCP server for querying metrics",
                "transport": "http",
                "endpoint": "https://analytics.example.com/mcp",
                "version": "2025-06-18",
                "capabilities": ["tools", "resources"],
                "tools": [
                    {
                        "name": "query_metrics",
                        "description": "Query system metrics",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "metric_name": {
                                    "type": "string",
                                    "enum": ["cpu_usage", "memory_usage", "request_count"]
                                },
                                "time_range": {
                                    "type": "string",
                                    "pattern": "^(1h|6h|24h|7d)$",
                                    "default": "1h"
                                }
                            },
                            "required": ["metric_name"]
                        },
                        "sensitivity_level": "medium",
                        "requires_approval": False
                    }
                ],
                "sensitivity_level": "medium",
                "metadata": {
                    "owner": "analytics-team@example.com",
                    "cost_center": "engineering",
                    "version": "2.1.0"
                }
            }
        }


class ServerResponse(BaseModel):
    """Server response schema."""

    server_id: UUID
    status: str
    consul_id: str | None


class ServerListItem(BaseModel):
    """Server list item schema."""

    id: str
    name: str
    transport: str
    status: str
    sensitivity_level: str
    created_at: str


class ToolDetailResponse(BaseModel):
    """Tool detail response schema."""

    id: str
    name: str
    description: str | None
    sensitivity_level: str


class ServerDetailResponse(BaseModel):
    """Server detail response schema."""

    id: str
    name: str
    description: str | None
    transport: str
    endpoint: str | None
    status: str
    sensitivity_level: str
    tools: list[ToolDetailResponse]
    metadata: dict[str, Any]
    created_at: str


@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def register_server(
    request: ServerRegistrationRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit_db: AsyncSession = Depends(get_timescale_db),
) -> ServerResponse:
    """
    Register a new MCP server.

    This endpoint allows registration of MCP servers with the governance system.
    The server will be added to the service registry and subject to policy controls.

    Requires authentication via JWT token.
    """
    try:
        discovery_service = DiscoveryService(db)
        audit_service = AuditService(audit_db)
        opa_client = OPAClient()

        # Check authorization via OPA
        authorization_allowed = await opa_client.authorize(
            user_id=str(user.user_id),
            action="server:register",
            resource=f"server:{request.name}",
            context={
                "user_role": user.role,
                "user_teams": user.teams,
                "server_name": request.name,
                "sensitivity_level": request.sensitivity_level,
                "transport": request.transport,
            },
        )

        if not authorization_allowed:
            logger.warning(
                "server_registration_denied",
                user_id=str(user.user_id),
                server_name=request.name,
                reason="policy_denied",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Server registration denied by policy",
            )

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
            user_id=user.user_id,
            user_email=user.email,
            server_id=server.id,
            details={
                "server_name": server.name,
                "transport": request.transport,
                "tool_count": len(request.tools),
                "sensitivity_level": request.sensitivity_level,
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


@router.get("/{server_id}", response_model=ServerDetailResponse)
async def get_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ServerDetailResponse:
    """
    Get detailed information about a specific MCP server.

    Returns complete server configuration including:
    - Server metadata and status
    - Transport configuration
    - All registered tools
    - Custom metadata
    - Sensitivity classification

    Requires authentication.
    """
    discovery_service = DiscoveryService(db)
    server = await discovery_service.get_server(server_id)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    # Get server tools
    tools = await discovery_service.get_server_tools(server_id)

    return ServerDetailResponse(
        id=str(server.id),
        name=server.name,
        description=server.description,
        transport=server.transport.value,
        endpoint=server.endpoint,
        status=server.status.value,
        sensitivity_level=server.sensitivity_level.value,
        tools=[
            ToolDetailResponse(
                id=str(tool.id),
                name=tool.name,
                description=tool.description,
                sensitivity_level=tool.sensitivity_level.value,
            )
            for tool in tools
        ],
        metadata=server.extra_metadata or {},
        created_at=server.created_at.isoformat(),
    )


@router.get("/", response_model=PaginatedResponse[ServerListItem])
async def list_servers(
    limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order"),
    status: str | None = Query(None, description="Filter by status (comma-separated)"),
    sensitivity: str | None = Query(
        None, description="Filter by sensitivity level (comma-separated)"
    ),
    team_id: str | None = Query(None, description="Filter by team UUID"),
    owner_id: str | None = Query(None, description="Filter by owner UUID"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    match_all_tags: bool = Query(default=False, description="Match all tags (AND) vs any tag (OR)"),
    search: str | None = Query(None, description="Full-text search on name/description"),
    include_total: bool = Query(
        default=False, description="Include total count (expensive operation)"
    ),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ServerListItem]:
    """
    List registered MCP servers with pagination and filtering.

    Supports cursor-based pagination for efficient querying of large datasets.
    Default page size is 50, maximum is 200.

    Filters can be combined - all filters use AND logic.
    Multiple values in status/sensitivity/tags use OR logic by default.

    Examples:
    - /api/servers/?status=active&sensitivity=high
    - /api/servers/?search=analytics&tags=production,critical
    - /api/servers/?team_id=<uuid>&limit=100
    """
    # Import search utilities
    from sark.services.discovery.search import (
        parse_sensitivity_list,
        parse_status_list,
        parse_tags_filter,
    )

    discovery_service = DiscoveryService(db)

    # Create pagination params
    pagination = PaginationParams(limit=limit, cursor=cursor, sort_order=sort_order)

    # Parse filters
    status_filter = parse_status_list(status)
    sensitivity_filter = parse_sensitivity_list(sensitivity)
    tags_filter = parse_tags_filter(tags)

    # Get paginated servers with filters
    servers, next_cursor, has_more, total = await discovery_service.list_servers_paginated(
        pagination=pagination,
        status=status_filter,
        sensitivity=sensitivity_filter,
        team_id=team_id,
        owner_id=owner_id,
        tags=tags_filter,
        match_all_tags=match_all_tags,
        search=search,
        count_total=include_total,
    )

    # Convert to response format
    items = [
        ServerListItem(
            id=str(server.id),
            name=server.name,
            transport=server.transport.value,
            status=server.status.value,
            sensitivity_level=server.sensitivity_level.value,
            created_at=server.created_at.isoformat(),
        )
        for server in servers
    ]

    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total=total,
    )
