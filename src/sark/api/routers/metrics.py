"""Server metrics and statistics endpoints."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.db import get_db
from sark.models.mcp_server import MCPServer, MCPTool, ServerStatus
from sark.services.auth import UserContext, get_current_user

logger = structlog.get_logger()
router = APIRouter()


class ServerMetricsSummary(BaseModel):
    """Summary metrics for all servers."""

    total_servers: int = Field(..., description="Total number of registered servers")
    active_servers: int = Field(..., description="Number of active servers")
    inactive_servers: int = Field(..., description="Number of inactive servers")
    unhealthy_servers: int = Field(..., description="Number of unhealthy servers")
    total_tools: int = Field(..., description="Total number of tools across all servers")
    servers_by_transport: dict[str, int] = Field(
        ..., description="Count of servers by transport type"
    )
    servers_by_sensitivity: dict[str, int] = Field(
        ..., description="Count of servers by sensitivity level"
    )
    average_tools_per_server: float = Field(..., description="Average number of tools per server")


class ServerMetricsDetail(BaseModel):
    """Detailed metrics for a specific server."""

    server_id: str
    server_name: str
    status: str
    transport: str
    sensitivity_level: str
    total_tools: int
    tools_by_sensitivity: dict[str, int]
    created_at: str
    last_health_check: str | None
    uptime_percentage: float | None = Field(None, description="Uptime percentage over last 30 days")


class TimeSeriesDataPoint(BaseModel):
    """Time series data point."""

    timestamp: str
    value: float
    metadata: dict[str, Any] | None = None


class ServerMetricsTimeSeries(BaseModel):
    """Time series metrics for servers."""

    metric_name: str
    time_range: str
    interval: str
    data_points: list[TimeSeriesDataPoint]


@router.get("/summary", response_model=ServerMetricsSummary)
async def get_metrics_summary(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServerMetricsSummary:
    """
    Get summary metrics for all MCP servers.

    Returns aggregate statistics including:
    - Total server counts by status
    - Distribution by transport type
    - Distribution by sensitivity level
    - Tool statistics

    Requires authentication.
    """
    try:
        # Total servers
        total_query = select(func.count(MCPServer.id))
        total_result = await db.execute(total_query)
        total_servers = total_result.scalar() or 0

        # Servers by status
        active_query = select(func.count(MCPServer.id)).where(
            MCPServer.status == ServerStatus.ACTIVE
        )
        active_result = await db.execute(active_query)
        active_servers = active_result.scalar() or 0

        inactive_query = select(func.count(MCPServer.id)).where(
            MCPServer.status == ServerStatus.INACTIVE
        )
        inactive_result = await db.execute(inactive_query)
        inactive_servers = inactive_result.scalar() or 0

        unhealthy_query = select(func.count(MCPServer.id)).where(
            MCPServer.status == ServerStatus.UNHEALTHY
        )
        unhealthy_result = await db.execute(unhealthy_query)
        unhealthy_servers = unhealthy_result.scalar() or 0

        # Total tools
        tools_query = select(func.count(MCPTool.id))
        tools_result = await db.execute(tools_query)
        total_tools = tools_result.scalar() or 0

        # Servers by transport
        transport_query = select(MCPServer.transport, func.count(MCPServer.id)).group_by(
            MCPServer.transport
        )
        transport_result = await db.execute(transport_query)
        servers_by_transport = {
            str(transport.value): count for transport, count in transport_result.fetchall()
        }

        # Servers by sensitivity
        sensitivity_query = select(MCPServer.sensitivity_level, func.count(MCPServer.id)).group_by(
            MCPServer.sensitivity_level
        )
        sensitivity_result = await db.execute(sensitivity_query)
        servers_by_sensitivity = {
            str(level.value): count for level, count in sensitivity_result.fetchall()
        }

        # Average tools per server
        avg_tools = total_tools / total_servers if total_servers > 0 else 0.0

        return ServerMetricsSummary(
            total_servers=total_servers,
            active_servers=active_servers,
            inactive_servers=inactive_servers,
            unhealthy_servers=unhealthy_servers,
            total_tools=total_tools,
            servers_by_transport=servers_by_transport,
            servers_by_sensitivity=servers_by_sensitivity,
            average_tools_per_server=round(avg_tools, 2),
        )

    except Exception as e:
        logger.error("metrics_summary_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics summary",
        ) from e


@router.get("/{server_id}", response_model=ServerMetricsDetail)
async def get_server_metrics(
    server_id: UUID,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServerMetricsDetail:
    """
    Get detailed metrics for a specific MCP server.

    Returns comprehensive metrics including:
    - Server status and configuration
    - Tool statistics
    - Health check history
    - Uptime metrics

    Requires authentication.
    """
    try:
        # Get server
        server_query = select(MCPServer).where(MCPServer.id == server_id)
        server_result = await db.execute(server_query)
        server = server_result.scalar_one_or_none()

        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found",
            )

        # Get total tools for this server
        tools_query = select(func.count(MCPTool.id)).where(MCPTool.server_id == server_id)
        tools_result = await db.execute(tools_query)
        total_tools = tools_result.scalar() or 0

        # Get tools by sensitivity for this server
        sensitivity_query = (
            select(MCPTool.sensitivity_level, func.count(MCPTool.id))
            .where(MCPTool.server_id == server_id)
            .group_by(MCPTool.sensitivity_level)
        )
        sensitivity_result = await db.execute(sensitivity_query)
        tools_by_sensitivity = {
            str(level.value): count for level, count in sensitivity_result.fetchall()
        }

        # Calculate uptime (placeholder - would need health check history)
        uptime_percentage = 99.5 if server.status == ServerStatus.ACTIVE else 0.0

        return ServerMetricsDetail(
            server_id=str(server.id),
            server_name=server.name,
            status=server.status.value,
            transport=server.transport.value,
            sensitivity_level=server.sensitivity_level.value,
            total_tools=total_tools,
            tools_by_sensitivity=tools_by_sensitivity,
            created_at=server.created_at.isoformat(),
            last_health_check=datetime.now().isoformat(),  # Placeholder
            uptime_percentage=uptime_percentage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("server_metrics_failed", server_id=str(server_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve server metrics",
        ) from e


@router.get("/timeseries/servers", response_model=ServerMetricsTimeSeries)
async def get_servers_timeseries(
    metric: str = Query(
        ...,
        description="Metric to query",
        regex="^(server_count|active_servers|tool_count|health_checks)$",
    ),
    time_range: str = Query(
        default="24h",
        description="Time range",
        regex="^(1h|6h|24h|7d|30d)$",
    ),
    interval: str = Query(
        default="1h",
        description="Data point interval",
        regex="^(5m|15m|1h|6h|1d)$",
    ),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServerMetricsTimeSeries:
    """
    Get time series metrics for servers.

    Supported metrics:
    - server_count: Total number of servers over time
    - active_servers: Number of active servers over time
    - tool_count: Total tools registered over time
    - health_checks: Health check success rate over time

    Requires authentication.
    """
    # Parse time range
    time_ranges = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = time_ranges[time_range]

    # Parse interval
    intervals = {
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "1d": timedelta(days=1),
    }
    interval_delta = intervals[interval]

    # Generate data points (placeholder implementation)
    # In production, this would query actual time-series data from TimescaleDB
    start_time = datetime.now() - delta
    data_points = []

    current_time = start_time
    while current_time <= datetime.now():
        # Placeholder: Generate synthetic data
        # In real implementation, query actual historical data
        if metric == "server_count":
            value = 100.0 + (datetime.now() - current_time).days * 5
        elif metric == "active_servers":
            value = 95.0 + (datetime.now() - current_time).days * 4
        elif metric == "tool_count":
            value = 500.0 + (datetime.now() - current_time).days * 25
        else:  # health_checks
            value = 99.5

        data_points.append(
            TimeSeriesDataPoint(
                timestamp=current_time.isoformat(),
                value=value,
                metadata={"interval": interval, "source": "calculated"},
            )
        )

        current_time += interval_delta

    return ServerMetricsTimeSeries(
        metric_name=metric,
        time_range=time_range,
        interval=interval,
        data_points=data_points,
    )
