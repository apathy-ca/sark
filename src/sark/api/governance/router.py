"""
Governance API router.

REST API endpoints for home LLM governance management.
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.governance import (
    AllowlistEntryCreate,
    AllowlistEntryResponse,
    AllowlistEntryType,
    ConsentRequestCreate,
    ConsentRequestResponse,
    ConsentStatus,
    EmergencyOverrideCreate,
    EmergencyOverrideResponse,
    EnforcementDecision,
    OverrideRequestCreate,
    OverrideRequestResponse,
    OverrideStatus,
    TimeCheckResult,
    TimeRuleAction,
    TimeRuleCreate,
    TimeRuleResponse,
)
from sark.services.governance import (
    AllowlistService,
    ConsentService,
    EmergencyService,
    EnforcementService,
    OverrideService,
    TimeRulesService,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/governance", tags=["governance"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ListResponse(BaseModel):
    """Generic list response."""

    items: list[Any]
    total: int
    limit: int
    offset: int


class EvaluationRequest(BaseModel):
    """Policy evaluation request."""

    device_ip: str | None = Field(None, description="Client IP address")
    user_id: str | None = Field(None, description="User identifier")
    override_pin: str | None = Field(None, description="Optional override PIN")
    action: str | None = Field(None, description="Action being performed")
    resource: str | None = Field(None, description="Resource being accessed")


class StatisticsResponse(BaseModel):
    """Statistics response."""

    data: dict[str, Any]


# =============================================================================
# Dependency Injection
# =============================================================================


async def get_db() -> AsyncSession:
    """Get database session - placeholder for actual implementation."""
    # In real implementation, this would use SARK's database session management
    # For now, we raise an error to indicate proper setup is needed
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database session not configured. Set up governance database.",
    )


async def get_allowlist_service(db: AsyncSession = Depends(get_db)) -> AllowlistService:
    """Get allowlist service instance."""
    return AllowlistService(db)


async def get_time_rules_service(db: AsyncSession = Depends(get_db)) -> TimeRulesService:
    """Get time rules service instance."""
    return TimeRulesService(db)


async def get_emergency_service(db: AsyncSession = Depends(get_db)) -> EmergencyService:
    """Get emergency service instance."""
    return EmergencyService(db)


async def get_consent_service(db: AsyncSession = Depends(get_db)) -> ConsentService:
    """Get consent service instance."""
    return ConsentService(db)


async def get_override_service(db: AsyncSession = Depends(get_db)) -> OverrideService:
    """Get override service instance."""
    return OverrideService(db)


async def get_enforcement_service(
    db: AsyncSession = Depends(get_db),
    allowlist: AllowlistService = Depends(get_allowlist_service),
    time_rules: TimeRulesService = Depends(get_time_rules_service),
    emergency: EmergencyService = Depends(get_emergency_service),
    override: OverrideService = Depends(get_override_service),
) -> EnforcementService:
    """Get enforcement service instance."""
    return EnforcementService(
        db=db,
        allowlist=allowlist,
        time_rules=time_rules,
        emergency=emergency,
        override=override,
    )


# =============================================================================
# Allowlist Endpoints
# =============================================================================


@router.post("/allowlist", response_model=AllowlistEntryResponse, status_code=status.HTTP_201_CREATED)
async def add_allowlist_entry(
    entry: AllowlistEntryCreate,
    service: AllowlistService = Depends(get_allowlist_service),
) -> AllowlistEntryResponse:
    """
    Add entry to allowlist.

    Devices or users in the allowlist bypass all policy evaluation.
    """
    try:
        result = await service.add_entry(
            identifier=entry.identifier,
            entry_type=entry.entry_type,
            name=entry.name,
            reason=entry.reason,
            expires_at=entry.expires_at,
        )
        return AllowlistEntryResponse.model_validate(result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/allowlist", response_model=list[AllowlistEntryResponse])
async def list_allowlist_entries(
    entry_type: AllowlistEntryType | None = None,
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: AllowlistService = Depends(get_allowlist_service),
) -> list[AllowlistEntryResponse]:
    """List allowlist entries."""
    entries = await service.list_entries(
        entry_type=entry_type,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return [AllowlistEntryResponse.model_validate(e) for e in entries]


@router.get("/allowlist/check/{identifier}")
async def check_allowlist(
    identifier: str,
    service: AllowlistService = Depends(get_allowlist_service),
) -> dict[str, bool]:
    """Check if identifier is allowlisted."""
    is_allowed = await service.is_allowed(identifier)
    return {"allowed": is_allowed}


@router.delete("/allowlist/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_allowlist_entry(
    identifier: str,
    service: AllowlistService = Depends(get_allowlist_service),
) -> None:
    """Remove entry from allowlist."""
    removed = await service.remove_entry(identifier)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")


# =============================================================================
# Time Rules Endpoints
# =============================================================================


@router.post("/time-rules", response_model=TimeRuleResponse, status_code=status.HTTP_201_CREATED)
async def add_time_rule(
    rule: TimeRuleCreate,
    service: TimeRulesService = Depends(get_time_rules_service),
) -> TimeRuleResponse:
    """
    Add time-based rule.

    Rules define time windows when specific actions apply (block, alert, log).
    """
    try:
        result = await service.add_rule(
            name=rule.name,
            start=rule.start_time,
            end=rule.end_time,
            action=rule.action,
            days=rule.days,
            description=rule.description,
            timezone=rule.timezone,
            priority=rule.priority,
        )
        return TimeRuleResponse.model_validate(result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/time-rules", response_model=list[TimeRuleResponse])
async def list_time_rules(
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: TimeRulesService = Depends(get_time_rules_service),
) -> list[TimeRuleResponse]:
    """List time rules."""
    rules = await service.list_rules(
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return [TimeRuleResponse.model_validate(r) for r in rules]


@router.get("/time-rules/check", response_model=TimeCheckResult)
async def check_time_rules(
    check_time: datetime | None = None,
    device_ip: str | None = None,
    service: TimeRulesService = Depends(get_time_rules_service),
) -> TimeCheckResult:
    """Check if any time rules apply at the given time."""
    return await service.check_rules(check_time=check_time, device_ip=device_ip)


@router.delete("/time-rules/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_time_rule(
    name: str,
    service: TimeRulesService = Depends(get_time_rules_service),
) -> None:
    """Remove time rule."""
    removed = await service.remove_rule(name)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")


# =============================================================================
# Emergency Override Endpoints
# =============================================================================


@router.post("/emergency", response_model=EmergencyOverrideResponse, status_code=status.HTTP_201_CREATED)
async def activate_emergency_override(
    override: EmergencyOverrideCreate,
    service: EmergencyService = Depends(get_emergency_service),
) -> EmergencyOverrideResponse:
    """
    Activate emergency override.

    When active, all policies are bypassed for the specified duration.
    """
    try:
        result = await service.activate(
            duration_minutes=override.duration_minutes,
            reason=override.reason,
        )
        return EmergencyOverrideResponse.model_validate(result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/emergency/status")
async def get_emergency_status(
    service: EmergencyService = Depends(get_emergency_service),
) -> dict[str, Any]:
    """Get current emergency override status."""
    is_active = await service.is_active()
    current = await service.get_current() if is_active else None
    return {
        "active": is_active,
        "override": EmergencyOverrideResponse.model_validate(current) if current else None,
    }


@router.delete("/emergency", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_emergency_override(
    service: EmergencyService = Depends(get_emergency_service),
) -> None:
    """Manually deactivate emergency override."""
    deactivated = await service.deactivate()
    if not deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active override")


@router.get("/emergency/history", response_model=list[EmergencyOverrideResponse])
async def get_emergency_history(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: EmergencyService = Depends(get_emergency_service),
) -> list[EmergencyOverrideResponse]:
    """Get history of emergency overrides."""
    history = await service.get_history(limit=limit, offset=offset)
    return [EmergencyOverrideResponse.model_validate(h) for h in history]


# =============================================================================
# Consent Endpoints
# =============================================================================


@router.post("/consent", response_model=ConsentRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_consent_request(
    request: ConsentRequestCreate,
    requester: str = Query(..., description="Who is requesting the change"),
    service: ConsentService = Depends(get_consent_service),
) -> ConsentRequestResponse:
    """
    Create consent request for a policy change.

    Sensitive changes may require approval from multiple parties.
    """
    try:
        result = await service.request_change(
            change_type=request.change_type,
            description=request.change_description,
            requester=requester,
            required_approvers=request.required_approvers,
            expires_in_hours=request.expires_in_hours,
        )
        approvers = result.current_approvers.split(",") if result.current_approvers else []
        return ConsentRequestResponse(
            id=result.id,
            change_type=result.change_type,
            change_description=result.change_description,
            requester=result.requester,
            status=result.status,
            required_approvers=result.required_approvers,
            current_approvers=approvers,
            expires_at=result.expires_at,
            created_at=result.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/consent/{request_id}/approve")
async def approve_consent_request(
    request_id: int,
    approver: str = Query(..., description="Who is approving"),
    service: ConsentService = Depends(get_consent_service),
) -> ConsentRequestResponse:
    """Approve a consent request."""
    try:
        result = await service.approve(request_id, approver)
        approvers = result.current_approvers.split(",") if result.current_approvers else []
        return ConsentRequestResponse(
            id=result.id,
            change_type=result.change_type,
            change_description=result.change_description,
            requester=result.requester,
            status=result.status,
            required_approvers=result.required_approvers,
            current_approvers=approvers,
            expires_at=result.expires_at,
            created_at=result.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/consent/{request_id}/reject")
async def reject_consent_request(
    request_id: int,
    rejector: str = Query(..., description="Who is rejecting"),
    reason: str | None = Query(None, description="Reason for rejection"),
    service: ConsentService = Depends(get_consent_service),
) -> ConsentRequestResponse:
    """Reject a consent request."""
    try:
        result = await service.reject(request_id, rejector, reason)
        approvers = result.current_approvers.split(",") if result.current_approvers else []
        return ConsentRequestResponse(
            id=result.id,
            change_type=result.change_type,
            change_description=result.change_description,
            requester=result.requester,
            status=result.status,
            required_approvers=result.required_approvers,
            current_approvers=approvers,
            expires_at=result.expires_at,
            created_at=result.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/consent/pending", response_model=list[ConsentRequestResponse])
async def list_pending_consent_requests(
    service: ConsentService = Depends(get_consent_service),
) -> list[ConsentRequestResponse]:
    """List pending consent requests."""
    requests = await service.get_pending_requests()
    return [
        ConsentRequestResponse(
            id=r.id,
            change_type=r.change_type,
            change_description=r.change_description,
            requester=r.requester,
            status=r.status,
            required_approvers=r.required_approvers,
            current_approvers=r.current_approvers.split(",") if r.current_approvers else [],
            expires_at=r.expires_at,
            created_at=r.created_at,
        )
        for r in requests
    ]


# =============================================================================
# Per-Request Override Endpoints
# =============================================================================


@router.post("/override", response_model=OverrideRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_override_request(
    request: OverrideRequestCreate,
    requested_by: str | None = Query(None, description="Who is requesting"),
    service: OverrideService = Depends(get_override_service),
) -> OverrideRequestResponse:
    """
    Create per-request override with PIN.

    Allows bypassing policy for a specific request with authentication.
    """
    try:
        result = await service.create_override(
            request_id=request.request_id,
            pin=request.pin,
            reason=request.reason,
            requested_by=requested_by,
            expires_in_minutes=request.expires_in_minutes,
        )
        return OverrideRequestResponse.model_validate(result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/override/validate")
async def validate_override(
    request_id: str = Query(..., description="Request ID to validate"),
    pin: str = Query(..., description="Override PIN"),
    service: OverrideService = Depends(get_override_service),
) -> dict[str, bool]:
    """Validate and use an override."""
    valid = await service.validate_override(request_id, pin)
    return {"valid": valid}


@router.get("/override/{request_id}/exists")
async def check_override_exists(
    request_id: str,
    service: OverrideService = Depends(get_override_service),
) -> dict[str, bool]:
    """Check if override exists for request (without using it)."""
    exists = await service.check_override_exists(request_id)
    return {"exists": exists}


# =============================================================================
# Enforcement Endpoints
# =============================================================================


@router.post("/evaluate", response_model=EnforcementDecision)
async def evaluate_request(
    request: EvaluationRequest,
    service: EnforcementService = Depends(get_enforcement_service),
) -> EnforcementDecision:
    """
    Evaluate request against all governance policies.

    Returns allow/deny decision with reason and source.
    """
    return await service.evaluate(request.model_dump())


@router.get("/evaluate/simple")
async def evaluate_simple(
    device_ip: str = Query(..., description="Client IP address"),
    user_id: str | None = Query(None, description="Optional user ID"),
    service: EnforcementService = Depends(get_enforcement_service),
) -> dict[str, bool]:
    """Simple evaluation returning just allow/deny."""
    allowed = await service.evaluate_simple(device_ip, user_id=user_id)
    return {"allowed": allowed}


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    since: datetime | None = Query(None, description="Start time for statistics"),
    service: EnforcementService = Depends(get_enforcement_service),
) -> StatisticsResponse:
    """Get enforcement statistics."""
    stats = await service.get_statistics(since=since)
    return StatisticsResponse(data=stats)
