"""Policy audit API endpoints.

Provides REST API for querying policy decisions, tracking changes,
and exporting audit data for compliance and analytics.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sark.db.session import get_db
from sark.models.policy_audit import PolicyChangeType, PolicyDecisionResult
from sark.services.policy.audit import PolicyAuditService

router = APIRouter(prefix="/policy/audit", tags=["policy-audit"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class PolicyDecisionLogResponse(BaseModel):
    """Response model for policy decision log."""

    id: str
    timestamp: datetime
    result: str
    allow: bool
    user_id: str
    user_role: str | None
    action: str
    resource_type: str | None
    tool_name: str | None
    sensitivity_level: str | None
    reason: str | None
    evaluation_duration_ms: float | None
    cache_hit: bool
    client_ip: str | None
    mfa_verified: bool | None

    class Config:
        from_attributes = True


class PolicyChangeLogResponse(BaseModel):
    """Response model for policy change log."""

    id: str
    timestamp: datetime
    change_type: str
    policy_name: str
    policy_version: int
    changed_by_user_id: str
    change_reason: str | None
    breaking_change: bool
    deployed_at: datetime | None

    class Config:
        from_attributes = True


class PolicyAnalyticsResponse(BaseModel):
    """Response model for policy analytics."""

    period: dict[str, str]
    summary: dict[str, Any]
    cache_performance: dict[str, Any]
    latency: dict[str, float]
    grouped: dict[str, Any] | None = None


class DenialReasonResponse(BaseModel):
    """Response model for denial reason statistics."""

    reason: str
    count: int


class ExportRequest(BaseModel):
    """Request model for export operations."""

    start_time: datetime | None = Field(
        None, description="Start of time range (defaults to 24h ago)"
    )
    end_time: datetime | None = Field(
        None, description="End of time range (defaults to now)"
    )
    format: str = Field("json", description="Export format: 'json' or 'csv'")
    filters: dict[str, Any] | None = Field(None, description="Additional filters")


# ============================================================================
# DECISION LOG ENDPOINTS
# ============================================================================


@router.get("/decisions", response_model=list[PolicyDecisionLogResponse])
async def get_decision_logs(
    start_time: datetime | None = Query(
        None, description="Start of time range (ISO 8601)"
    ),
    end_time: datetime | None = Query(None, description="End of time range (ISO 8601)"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action"),
    result: PolicyDecisionResult | None = Query(None, description="Filter by result"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """Get policy decision logs with filters.

    Returns a paginated list of policy evaluation decisions matching the filters.
    Useful for compliance audits and troubleshooting authorization issues.

    **Example:**
    ```
    GET /api/v1/policy/audit/decisions?user_id=user123&result=deny&limit=50
    ```
    """
    audit_service = PolicyAuditService(db)

    # Default time range: last 24 hours
    if not start_time and not end_time:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

    logs = await audit_service.get_decision_logs(
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        action=action,
        result=result,
        limit=limit,
        offset=offset,
    )

    return [
        PolicyDecisionLogResponse(
            id=str(log.id),
            timestamp=log.timestamp,
            result=log.result.value,
            allow=log.allow,
            user_id=log.user_id,
            user_role=log.user_role,
            action=log.action,
            resource_type=log.resource_type,
            tool_name=log.tool_name,
            sensitivity_level=log.sensitivity_level,
            reason=log.reason,
            evaluation_duration_ms=log.evaluation_duration_ms,
            cache_hit=log.cache_hit,
            client_ip=log.client_ip,
            mfa_verified=log.mfa_verified,
        )
        for log in logs
    ]


@router.get("/decisions/{decision_id}", response_model=dict[str, Any])
async def get_decision_detail(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific policy decision.

    Returns complete details including policy results, violations,
    and full evaluation context.

    **Example:**
    ```
    GET /api/v1/policy/audit/decisions/550e8400-e29b-41d4-a716-446655440000
    ```
    """
    PolicyAuditService(db)

    from uuid import UUID

    from sqlalchemy import select

    from sark.models.policy_audit import PolicyDecisionLog

    stmt = select(PolicyDecisionLog).where(PolicyDecisionLog.id == UUID(decision_id))
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="Decision log not found")

    return {
        "id": str(log.id),
        "timestamp": log.timestamp.isoformat(),
        "result": log.result.value,
        "allow": log.allow,
        "user": {
            "id": log.user_id,
            "role": log.user_role,
            "teams": log.user_teams,
        },
        "action": log.action,
        "resource": {
            "type": log.resource_type,
            "id": log.resource_id,
        },
        "tool": {
            "id": log.tool_id,
            "name": log.tool_name,
            "sensitivity_level": log.sensitivity_level,
        },
        "policies_evaluated": log.policies_evaluated,
        "policy_results": log.policy_results,
        "violations": log.violations,
        "reason": log.reason,
        "performance": {
            "evaluation_duration_ms": log.evaluation_duration_ms,
            "cache_hit": log.cache_hit,
        },
        "context": {
            "client_ip": log.client_ip,
            "request_id": log.request_id,
            "session_id": log.session_id,
            "mfa_verified": log.mfa_verified,
            "mfa_method": log.mfa_method,
        },
        "advanced_policy_checks": {
            "time_based_allowed": log.time_based_allowed,
            "ip_filtering_allowed": log.ip_filtering_allowed,
            "mfa_required_satisfied": log.mfa_required_satisfied,
        },
    }


# ============================================================================
# POLICY CHANGE LOG ENDPOINTS
# ============================================================================


@router.get("/policy-changes", response_model=list[PolicyChangeLogResponse])
async def get_policy_changes(
    policy_name: str | None = Query(None, description="Filter by policy name"),
    start_time: datetime | None = Query(None, description="Start of time range"),
    end_time: datetime | None = Query(None, description="End of time range"),
    change_type: PolicyChangeType | None = Query(None, description="Filter by change type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Get policy change history.

    Returns version history and changes made to OPA policies.
    Useful for compliance audits and rollback operations.

    **Example:**
    ```
    GET /api/v1/policy/audit/policy-changes?policy_name=rbac&limit=20
    ```
    """
    audit_service = PolicyAuditService(db)

    # Default time range: last 30 days
    if not start_time and not end_time:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)

    changes = await audit_service.get_policy_changes(
        policy_name=policy_name,
        start_time=start_time,
        end_time=end_time,
        change_type=change_type,
        limit=limit,
    )

    return [
        PolicyChangeLogResponse(
            id=str(change.id),
            timestamp=change.timestamp,
            change_type=change.change_type.value,
            policy_name=change.policy_name,
            policy_version=change.policy_version,
            changed_by_user_id=change.changed_by_user_id,
            change_reason=change.change_reason,
            breaking_change=change.breaking_change,
            deployed_at=change.deployed_at,
        )
        for change in changes
    ]


@router.get("/policy-changes/{change_id}", response_model=dict[str, Any])
async def get_policy_change_detail(
    change_id: str,
    include_diff: bool = Query(False, description="Include policy diff"),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a policy change.

    Returns complete change information including policy content and diff.

    **Example:**
    ```
    GET /api/v1/policy/audit/policy-changes/550e8400-e29b-41d4-a716-446655440000?include_diff=true
    ```
    """
    from uuid import UUID

    from sqlalchemy import select

    from sark.models.policy_audit import PolicyChangeLog

    stmt = select(PolicyChangeLog).where(PolicyChangeLog.id == UUID(change_id))
    result = await db.execute(stmt)
    change = result.scalar_one_or_none()

    if not change:
        raise HTTPException(status_code=404, detail="Policy change not found")

    response = {
        "id": str(change.id),
        "timestamp": change.timestamp.isoformat(),
        "change_type": change.change_type.value,
        "policy_name": change.policy_name,
        "policy_version": change.policy_version,
        "changed_by_user_id": change.changed_by_user_id,
        "change_reason": change.change_reason,
        "breaking_change": change.breaking_change,
        "policy_hash": change.policy_hash,
        "approver_user_id": change.approver_user_id,
        "deployed_at": change.deployed_at.isoformat() if change.deployed_at else None,
        "deployment_status": change.deployment_status,
        "tags": change.tags,
    }

    if include_diff and change.policy_diff:
        response["policy_diff"] = change.policy_diff

    return response


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================


@router.post("/export/csv")
async def export_decisions_csv(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export policy decisions to CSV format.

    Downloads policy decision logs in CSV format for analysis in Excel
    or other tools. Supports filtering by time range and other criteria.

    **Example:**
    ```json
    POST /api/v1/policy/audit/export/csv
    {
      "start_time": "2024-01-01T00:00:00Z",
      "end_time": "2024-01-31T23:59:59Z",
      "filters": {
        "user_id": "user123",
        "result": "deny"
      }
    }
    ```
    """
    audit_service = PolicyAuditService(db)

    # Default time range
    start_time = request.start_time or (datetime.utcnow() - timedelta(days=7))
    end_time = request.end_time or datetime.utcnow()

    csv_content = await audit_service.export_decisions_csv(
        start_time=start_time,
        end_time=end_time,
        filters=request.filters,
    )

    filename = f"policy_decisions_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/export/json")
async def export_decisions_json(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export policy decisions to JSON format.

    Downloads policy decision logs in JSON format with complete details.

    **Example:**
    ```json
    POST /api/v1/policy/audit/export/json
    {
      "start_time": "2024-01-01T00:00:00Z",
      "end_time": "2024-01-31T23:59:59Z"
    }
    ```
    """
    audit_service = PolicyAuditService(db)

    # Default time range
    start_time = request.start_time or (datetime.utcnow() - timedelta(days=7))
    end_time = request.end_time or datetime.utcnow()

    json_content = await audit_service.export_decisions_json(
        start_time=start_time,
        end_time=end_time,
        filters=request.filters,
    )

    filename = f"policy_decisions_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================


@router.get("/analytics", response_model=PolicyAnalyticsResponse)
async def get_analytics(
    start_time: datetime | None = Query(None, description="Start of time range"),
    end_time: datetime | None = Query(None, description="End of time range"),
    group_by: list[str] | None = Query(
        None,
        description="Group by dimensions (action, sensitivity_level, user_role)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get policy evaluation analytics.

    Returns aggregated statistics including allow/deny rates, cache performance,
    and latency metrics. Supports grouping by various dimensions.

    **Example:**
    ```
    GET /api/v1/policy/audit/analytics?group_by=action&group_by=sensitivity_level
    ```
    """
    audit_service = PolicyAuditService(db)

    # Default time range: last 24 hours
    if not start_time:
        start_time = datetime.utcnow() - timedelta(days=1)
    if not end_time:
        end_time = datetime.utcnow()

    analytics = await audit_service.get_decision_analytics(
        start_time=start_time,
        end_time=end_time,
        group_by=group_by,
    )

    return PolicyAnalyticsResponse(**analytics)


@router.get("/analytics/denial-reasons", response_model=list[DenialReasonResponse])
async def get_top_denial_reasons(
    start_time: datetime | None = Query(None, description="Start of time range"),
    end_time: datetime | None = Query(None, description="End of time range"),
    limit: int = Query(10, ge=1, le=50, description="Number of top reasons to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get top denial reasons with counts.

    Returns the most common reasons for policy denials, useful for
    identifying access issues and improving policies.

    **Example:**
    ```
    GET /api/v1/policy/audit/analytics/denial-reasons?limit=20
    ```
    """
    audit_service = PolicyAuditService(db)

    # Default time range: last 7 days
    if not start_time:
        start_time = datetime.utcnow() - timedelta(days=7)
    if not end_time:
        end_time = datetime.utcnow()

    reasons = await audit_service.get_top_denial_reasons(
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    return [DenialReasonResponse(**reason) for reason in reasons]


@router.get("/analytics/trends")
async def get_analytics_trends(
    metric: str = Query(
        "allow_rate", description="Metric to analyze (allow_rate, deny_rate, cache_hit_rate)"
    ),
    interval: str = Query("1h", description="Time interval (1h, 6h, 1d)"),
    start_time: datetime | None = Query(None, description="Start of time range"),
    end_time: datetime | None = Query(None, description="End of time range"),
    db: AsyncSession = Depends(get_db),
):
    """Get trends for policy evaluation metrics over time.

    Returns time-series data for visualization and monitoring.

    **Example:**
    ```
    GET /api/v1/policy/audit/analytics/trends?metric=cache_hit_rate&interval=1h
    ```
    """
    audit_service = PolicyAuditService(db)

    # Default time range: last 7 days
    if not start_time:
        start_time = datetime.utcnow() - timedelta(days=7)
    if not end_time:
        end_time = datetime.utcnow()

    # Parse interval
    interval_map = {"1h": timedelta(hours=1), "6h": timedelta(hours=6), "1d": timedelta(days=1)}
    interval_delta = interval_map.get(interval, timedelta(hours=1))

    # Generate time buckets
    buckets = []
    current = start_time
    while current < end_time:
        bucket_end = min(current + interval_delta, end_time)

        # Get analytics for this bucket
        analytics = await audit_service.get_decision_analytics(
            start_time=current,
            end_time=bucket_end,
        )

        value = 0
        if metric == "allow_rate":
            value = analytics["summary"]["allow_rate"]
        elif metric == "deny_rate":
            value = analytics["summary"]["deny_rate"]
        elif metric == "cache_hit_rate":
            value = analytics["cache_performance"]["hit_rate"]
        elif metric == "avg_latency":
            value = analytics["latency"]["avg_ms"]

        buckets.append(
            {
                "timestamp": current.isoformat(),
                "value": value,
                "total_evaluations": analytics["summary"]["total_evaluations"],
            }
        )

        current = bucket_end

    return {"metric": metric, "interval": interval, "data": buckets}
