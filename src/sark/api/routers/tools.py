"""MCP Tool management and sensitivity classification endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.db import get_db, get_timescale_db
from sark.models.mcp_server import SensitivityLevel
from sark.services.auth import UserContext, get_current_user
from sark.services.discovery import ToolRegistry
from sark.services.policy import OPAClient

logger = structlog.get_logger()
router = APIRouter()


class SensitivityUpdateRequest(BaseModel):
    """Request to update tool sensitivity level."""

    sensitivity_level: str = Field(
        ...,
        pattern="^(low|medium|high|critical)$",
        description="New sensitivity level",
    )
    reason: str | None = Field(
        None,
        max_length=500,
        description="Reason for the change",
    )


class SensitivityDetectionRequest(BaseModel):
    """Request to detect sensitivity level."""

    tool_name: str = Field(..., min_length=1, max_length=255)
    tool_description: str | None = Field(None, max_length=2000)
    parameters: dict[str, Any] | None = Field(None)


class SensitivityResponse(BaseModel):
    """Response with tool sensitivity information."""

    tool_id: UUID
    tool_name: str
    sensitivity_level: str
    is_overridden: bool
    last_updated: str


class SensitivityDetectionResponse(BaseModel):
    """Response with detected sensitivity level."""

    detected_level: str
    keywords_matched: list[str] | None = None
    detection_method: str


@router.get("/{tool_id}/sensitivity", response_model=SensitivityResponse)
async def get_tool_sensitivity(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SensitivityResponse:
    """
    Get current sensitivity level for a tool.

    Returns the tool's current sensitivity level and whether it has been
    manually overridden from the auto-detected value.
    """
    tool_registry = ToolRegistry(db)
    tool = await tool_registry.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    # Check if sensitivity was manually overridden
    is_overridden = bool(tool.extra_metadata and "sensitivity_override" in tool.extra_metadata)

    return SensitivityResponse(
        tool_id=tool.id,
        tool_name=tool.name,
        sensitivity_level=tool.sensitivity_level.value,
        is_overridden=is_overridden,
        last_updated=tool.updated_at.isoformat(),
    )


@router.post("/{tool_id}/sensitivity", response_model=SensitivityResponse)
async def update_tool_sensitivity(
    tool_id: UUID,
    request: SensitivityUpdateRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit_db: AsyncSession = Depends(get_timescale_db),
) -> SensitivityResponse:
    """
    Manually update tool sensitivity level (override auto-detection).

    This endpoint allows administrators to manually override the auto-detected
    sensitivity level for a tool. All changes are audited.

    Requires admin role.
    """
    # Check authorization via OPA
    opa_client = OPAClient()
    authorization_allowed = await opa_client.authorize(
        user_id=str(user.user_id),
        action="tool:update_sensitivity",
        resource=f"tool:{tool_id}",
        context={
            "user_role": user.role,
            "new_sensitivity": request.sensitivity_level,
        },
    )

    if not authorization_allowed:
        logger.warning(
            "tool_sensitivity_update_denied",
            user_id=str(user.user_id),
            tool_id=str(tool_id),
            reason="policy_denied",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool sensitivity update denied by policy",
        )

    # Update sensitivity
    tool_registry = ToolRegistry(db, audit_db)
    try:
        new_sensitivity = SensitivityLevel(request.sensitivity_level)
        tool = await tool_registry.update_sensitivity(
            tool_id=tool_id,
            new_sensitivity=new_sensitivity,
            user_id=user.user_id,
            user_email=user.email,
            reason=request.reason,
        )

        return SensitivityResponse(
            tool_id=tool.id,
            tool_name=tool.name,
            sensitivity_level=tool.sensitivity_level.value,
            is_overridden=True,
            last_updated=tool.updated_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("tool_sensitivity_update_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tool sensitivity",
        ) from e


@router.post("/detect-sensitivity", response_model=SensitivityDetectionResponse)
async def detect_tool_sensitivity(
    request: SensitivityDetectionRequest,
    db: AsyncSession = Depends(get_db),
) -> SensitivityDetectionResponse:
    """
    Detect sensitivity level for a tool based on its name and description.

    This endpoint allows testing the auto-detection algorithm without
    creating a tool record.

    Useful for:
    - Testing sensitivity detection before tool registration
    - Understanding how keywords affect classification
    - Validating tool naming conventions
    """
    tool_registry = ToolRegistry(db)
    detected_level = await tool_registry.detect_sensitivity(
        tool_name=request.tool_name,
        tool_description=request.tool_description,
        parameters=request.parameters,
    )

    # Analyze which keywords were matched
    text = request.tool_name.lower()
    if request.tool_description:
        text += " " + request.tool_description.lower()

    matched_keywords = []
    detection_method = "default"

    # Check critical keywords
    for keyword in tool_registry.CRITICAL_KEYWORDS:
        if keyword in text:
            matched_keywords.append(keyword)
            detection_method = "critical_keywords"

    # Check high keywords
    if not matched_keywords:
        for keyword in tool_registry.HIGH_KEYWORDS:
            if keyword in text:
                matched_keywords.append(keyword)
                detection_method = "high_keywords"

    # Check medium keywords
    if not matched_keywords:
        for keyword in tool_registry.MEDIUM_KEYWORDS:
            if keyword in text:
                matched_keywords.append(keyword)
                detection_method = "medium_keywords"

    # Check low keywords
    if not matched_keywords:
        for keyword in tool_registry.LOW_KEYWORDS:
            if keyword in text:
                matched_keywords.append(keyword)
                detection_method = "low_keywords"

    return SensitivityDetectionResponse(
        detected_level=detected_level.value,
        keywords_matched=matched_keywords if matched_keywords else None,
        detection_method=detection_method,
    )


@router.get("/{tool_id}/sensitivity/history")
async def get_tool_sensitivity_history(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get sensitivity change history for a tool.

    Returns a list of all sensitivity level changes, including:
    - Manual overrides
    - Who made the change
    - When it was changed
    - Reason for the change
    """
    tool_registry = ToolRegistry(db)

    try:
        history = await tool_registry.get_sensitivity_history(tool_id)
        return history

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/statistics/sensitivity")
async def get_sensitivity_statistics(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get statistics about tool sensitivity distribution.

    Returns:
    - Total number of tools
    - Count by sensitivity level (low, medium, high, critical)
    - Number of manually overridden tools
    """
    tool_registry = ToolRegistry(db)
    stats = await tool_registry.get_sensitivity_statistics()
    return stats


@router.get("/sensitivity/{level}")
async def list_tools_by_sensitivity(
    level: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List all tools with a specific sensitivity level.

    Args:
        level: Sensitivity level (low, medium, high, critical)

    Returns:
        List of tools with the specified sensitivity level
    """
    # Validate sensitivity level
    try:
        sensitivity = SensitivityLevel(level)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sensitivity level: {level}. Must be one of: low, medium, high, critical",
        ) from e

    tool_registry = ToolRegistry(db)
    tools = await tool_registry.get_tools_by_sensitivity(sensitivity)

    return [
        {
            "id": str(tool.id),
            "name": tool.name,
            "description": tool.description,
            "server_id": str(tool.server_id),
            "sensitivity_level": tool.sensitivity_level.value,
            "is_overridden": bool(
                tool.extra_metadata and "sensitivity_override" in tool.extra_metadata
            ),
            "created_at": tool.created_at.isoformat(),
        }
        for tool in tools
    ]


@router.post("/servers/{server_id}/tools/detect-all")
async def bulk_detect_sensitivity(
    server_id: UUID,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Detect sensitivity for all tools on a server.

    This endpoint performs bulk sensitivity detection for all tools
    associated with a server. Useful for re-classifying tools after
    updating detection rules.

    Returns a mapping of tool IDs to detected sensitivity levels.
    """
    tool_registry = ToolRegistry(db)

    try:
        detections = await tool_registry.bulk_detect_sensitivity(server_id)

        return {
            "server_id": str(server_id),
            "tool_count": len(detections),
            "detections": {tool_id: level.value for tool_id, level in detections.items()},
        }

    except Exception as e:
        logger.error("bulk_sensitivity_detection_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect tool sensitivities",
        ) from e
