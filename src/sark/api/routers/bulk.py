"""Bulk operations API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.db import get_db, get_timescale_db
from sark.services.auth import UserContext, get_current_user
from sark.services.bulk import BulkOperationsService

logger = structlog.get_logger()
router = APIRouter()


class ServerRegistrationItem(BaseModel):
    """Single server registration item for bulk operation."""

    name: str = Field(..., min_length=1, max_length=255)
    transport: str = Field(..., pattern="^(http|stdio|sse)$")
    endpoint: str | None = Field(None, max_length=500)
    command: str | None = Field(None, max_length=500)
    version: str = Field(default="2025-06-18")
    capabilities: list[str] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    description: str | None = Field(None, max_length=1000)
    sensitivity_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    signature: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BulkServerRegistrationRequest(BaseModel):
    """Bulk server registration request."""

    servers: list[ServerRegistrationItem] = Field(..., min_length=1, max_length=100)
    fail_on_first_error: bool = Field(
        default=False,
        description="If true, rollback all on first error (transactional). "
        "If false, continue processing (best-effort).",
    )


class ServerStatusUpdateItem(BaseModel):
    """Single server status update item for bulk operation."""

    server_id: str = Field(..., description="Server UUID")
    status: str = Field(
        ...,
        pattern="^(registered|active|inactive|unhealthy|decommissioned)$",
        description="New server status",
    )


class BulkServerStatusUpdateRequest(BaseModel):
    """Bulk server status update request."""

    updates: list[ServerStatusUpdateItem] = Field(..., min_length=1, max_length=100)
    fail_on_first_error: bool = Field(
        default=False,
        description="If true, rollback all on first error (transactional). "
        "If false, continue processing (best-effort).",
    )


class BulkOperationResponse(BaseModel):
    """Bulk operation response."""

    total: int = Field(..., description="Total number of items processed")
    succeeded: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    succeeded_items: list[dict[str, Any]] = Field(default_factory=list)
    failed_items: list[dict[str, Any]] = Field(default_factory=list)


@router.post(
    "/servers/register",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def bulk_register_servers(
    request: BulkServerRegistrationRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit_db: AsyncSession = Depends(get_timescale_db),
) -> BulkOperationResponse:
    """
    Bulk register multiple MCP servers.

    This endpoint allows registration of multiple servers in a single request.
    Supports two modes:

    1. **Transactional** (fail_on_first_error=true):
       - All servers registered in a single transaction
       - If any server fails policy check or registration, ALL are rolled back
       - Use this for atomic operations where all-or-nothing is required

    2. **Best-effort** (fail_on_first_error=false, default):
       - Each server processed independently
       - Failures don't affect other servers
       - Use this for maximum throughput and partial success

    **Limits**: Maximum 100 servers per request

    **Policy Evaluation**: All servers are evaluated against OPA policies before registration

    Requires authentication via JWT token.

    Example request:
    ```json
    {
      "servers": [
        {
          "name": "analytics-server-1",
          "transport": "http",
          "endpoint": "http://analytics-1.example.com",
          "capabilities": ["tools"],
          "tools": [],
          "sensitivity_level": "high"
        },
        {
          "name": "ml-server-1",
          "transport": "http",
          "endpoint": "http://ml-1.example.com",
          "capabilities": ["tools"],
          "tools": [],
          "sensitivity_level": "critical"
        }
      ],
      "fail_on_first_error": false
    }
    ```
    """
    try:
        bulk_service = BulkOperationsService(
            db=db,
            audit_db=audit_db,
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            user_teams=user.teams,
        )

        # Convert to dict format
        servers_data = [server.model_dump() for server in request.servers]

        # Execute bulk registration
        result = await bulk_service.bulk_register_servers(
            servers=servers_data,
            fail_on_first_error=request.fail_on_first_error,
        )

        # Convert to response
        response = BulkOperationResponse(**result.to_dict())

        logger.info(
            "bulk_register_complete",
            user_id=str(user.user_id),
            total=response.total,
            succeeded=response.succeeded,
            failed=response.failed,
        )

        # Return 207 Multi-Status if there were partial failures
        if response.failed > 0 and response.succeeded > 0:
            # Cannot change status code in response model, so log it
            logger.info("partial_success", succeeded=response.succeeded, failed=response.failed)

        return response

    except Exception as e:
        logger.error("bulk_register_error", user_id=str(user.user_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk registration failed: {e!s}",
        ) from e


@router.patch(
    "/servers/status",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def bulk_update_server_status(
    request: BulkServerStatusUpdateRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit_db: AsyncSession = Depends(get_timescale_db),
) -> BulkOperationResponse:
    """
    Bulk update server statuses.

    This endpoint allows updating the status of multiple servers in a single request.
    Supports two modes:

    1. **Transactional** (fail_on_first_error=true):
       - All status updates in a single transaction
       - If any update fails, ALL are rolled back
       - Use this for coordinated state changes

    2. **Best-effort** (fail_on_first_error=false, default):
       - Each update processed independently
       - Failures don't affect other updates
       - Use this for maximum throughput

    **Limits**: Maximum 100 updates per request

    **Valid statuses**:
    - `registered` - Server registered but not yet active
    - `active` - Server is active and healthy
    - `inactive` - Server is temporarily inactive
    - `unhealthy` - Server failed health checks
    - `decommissioned` - Server is permanently decommissioned

    Requires authentication via JWT token.

    Example request:
    ```json
    {
      "updates": [
        {
          "server_id": "550e8400-e29b-41d4-a716-446655440000",
          "status": "active"
        },
        {
          "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
          "status": "inactive"
        }
      ],
      "fail_on_first_error": false
    }
    ```
    """
    try:
        bulk_service = BulkOperationsService(
            db=db,
            audit_db=audit_db,
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            user_teams=user.teams,
        )

        # Convert to dict format
        updates_data = [update.model_dump() for update in request.updates]

        # Execute bulk status update
        result = await bulk_service.bulk_update_server_status(
            updates=updates_data,
            fail_on_first_error=request.fail_on_first_error,
        )

        # Convert to response
        response = BulkOperationResponse(**result.to_dict())

        logger.info(
            "bulk_status_update_complete",
            user_id=str(user.user_id),
            total=response.total,
            succeeded=response.succeeded,
            failed=response.failed,
        )

        return response

    except Exception as e:
        logger.error("bulk_status_update_error", user_id=str(user.user_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk status update failed: {e!s}",
        ) from e
