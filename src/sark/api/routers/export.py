"""Data export endpoints for CSV and JSON formats."""

import csv
from datetime import datetime
from io import StringIO
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.db import get_db
from sark.models.mcp_server import MCPServer, MCPTool
from sark.services.auth import UserContext, get_current_user

logger = structlog.get_logger()
router = APIRouter()


class ExportRequest(BaseModel):
    """Export request configuration."""

    format: Literal["json", "csv"] = Field(..., description="Export format (json or csv)")
    resource_type: Literal["servers", "tools", "audit"] = Field(
        ..., description="Type of resource to export"
    )
    filters: dict[str, str] | None = Field(
        None, description="Optional filters (status, sensitivity, etc.)"
    )
    fields: list[str] | None = Field(None, description="Specific fields to include (default: all)")


class ExportResponse(BaseModel):
    """Export response metadata."""

    format: str
    resource_type: str
    record_count: int
    exported_at: str
    download_url: str | None = None


@router.post("/", response_model=ExportResponse)
async def create_export(
    request: ExportRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """
    Create an export job for servers, tools, or audit logs.

    Returns metadata about the export. Use the download endpoint to retrieve the file.

    Requires authentication.
    """
    try:
        # Get data based on resource type
        if request.resource_type == "servers":
            query = select(MCPServer)
            result = await db.execute(query)
            records = result.scalars().all()
            record_count = len(records)
        elif request.resource_type == "tools":
            query = select(MCPTool)
            result = await db.execute(query)
            records = result.scalars().all()
            record_count = len(records)
        else:
            # Audit logs would need TimescaleDB query
            record_count = 0

        return ExportResponse(
            format=request.format,
            resource_type=request.resource_type,
            record_count=record_count,
            exported_at=datetime.now().isoformat(),
            download_url=f"/api/v1/export/download/{request.resource_type}.{request.format}",
        )

    except Exception as e:
        logger.error("export_create_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from e


@router.get("/servers.csv")
async def export_servers_csv(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, description="Filter by status"),
) -> Response:
    """
    Export all servers as CSV.

    Returns a CSV file containing server data with columns:
    - id, name, transport, endpoint, status, sensitivity_level, created_at

    Requires authentication.
    """
    try:
        # Query servers
        query = select(MCPServer)
        result = await db.execute(query)
        servers = result.scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "id",
                "name",
                "description",
                "transport",
                "endpoint",
                "status",
                "sensitivity_level",
                "created_at",
            ]
        )

        # Write data
        for server in servers:
            writer.writerow(
                [
                    str(server.id),
                    server.name,
                    server.description or "",
                    server.transport.value,
                    server.endpoint or "",
                    server.status.value,
                    server.sensitivity_level.value,
                    server.created_at.isoformat(),
                ]
            )

        # Return CSV response
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="servers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            },
        )

    except Exception as e:
        logger.error("csv_export_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export servers as CSV",
        ) from e


@router.get("/servers.json")
async def export_servers_json(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    pretty: bool = Query(default=False, description="Pretty-print JSON"),
) -> Response:
    """
    Export all servers as JSON.

    Returns a JSON file containing all server data.

    Query parameters:
    - pretty: If true, formats JSON with indentation

    Requires authentication.
    """
    try:
        # Query servers
        query = select(MCPServer)
        result = await db.execute(query)
        servers = result.scalars().all()

        # Convert to dictionaries
        data = {
            "export_type": "servers",
            "exported_at": datetime.now().isoformat(),
            "total_records": len(servers),
            "servers": [
                {
                    "id": str(server.id),
                    "name": server.name,
                    "description": server.description,
                    "transport": server.transport.value,
                    "endpoint": server.endpoint,
                    "status": server.status.value,
                    "sensitivity_level": server.sensitivity_level.value,
                    "created_at": server.created_at.isoformat(),
                    "updated_at": server.updated_at.isoformat(),
                    "metadata": server.extra_metadata,
                }
                for server in servers
            ],
        }

        # Format JSON
        if pretty:
            json_content = json.dumps(data, indent=2)
        else:
            json_content = json.dumps(data)

        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="servers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            },
        )

    except Exception as e:
        logger.error("json_export_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export servers as JSON",
        ) from e


@router.get("/tools.csv")
async def export_tools_csv(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export all tools as CSV.

    Returns a CSV file containing tool data with columns:
    - id, name, description, server_id, sensitivity_level, created_at

    Requires authentication.
    """
    try:
        # Query tools with server info
        query = select(MCPTool).join(MCPServer)
        result = await db.execute(query)
        tools = result.scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "id",
                "name",
                "description",
                "server_id",
                "server_name",
                "sensitivity_level",
                "requires_approval",
                "created_at",
            ]
        )

        # Write data
        for tool in tools:
            writer.writerow(
                [
                    str(tool.id),
                    tool.name,
                    tool.description or "",
                    str(tool.server_id),
                    "",  # Would need to join to get server name
                    tool.sensitivity_level.value,
                    (
                        tool.extra_metadata.get("requires_approval", False)
                        if tool.extra_metadata
                        else False
                    ),
                    tool.created_at.isoformat(),
                ]
            )

        # Return CSV response
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="tools_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            },
        )

    except Exception as e:
        logger.error("csv_export_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export tools as CSV",
        ) from e


@router.get("/tools.json")
async def export_tools_json(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    pretty: bool = Query(default=False, description="Pretty-print JSON"),
) -> Response:
    """
    Export all tools as JSON.

    Returns a JSON file containing all tool data.

    Requires authentication.
    """
    try:
        # Query tools
        query = select(MCPTool)
        result = await db.execute(query)
        tools = result.scalars().all()

        # Convert to dictionaries
        data = {
            "export_type": "tools",
            "exported_at": datetime.now().isoformat(),
            "total_records": len(tools),
            "tools": [
                {
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "server_id": str(tool.server_id),
                    "sensitivity_level": tool.sensitivity_level.value,
                    "parameters": (
                        tool.extra_metadata.get("parameters") if tool.extra_metadata else None
                    ),
                    "created_at": tool.created_at.isoformat(),
                }
                for tool in tools
            ],
        }

        # Format JSON
        if pretty:
            json_content = json.dumps(data, indent=2)
        else:
            json_content = json.dumps(data)

        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="tools_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            },
        )

    except Exception as e:
        logger.error("json_export_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export tools as JSON",
        ) from e
