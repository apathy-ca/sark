"""
Analytics API router for home LLM usage dashboard.

Provides REST endpoints for dashboard statistics, usage reports,
trend analysis, and data export.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.api.dependencies import UserContext, get_current_user
from sark.db import get_db
from sark.services.analytics import (
    AnalyticsService,
    CostCalculatorService,
    ReportPeriod,
    TokenTrackerService,
    TrendAnalyzerService,
    UsageReporterService,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ============================================================================
# Request/Response Models
# ============================================================================


class RecordUsageRequest(BaseModel):
    """Request to record a usage event."""

    device_ip: str = Field(..., description="IP address of the requesting device")
    endpoint: str = Field(..., description="API endpoint called")
    provider: str = Field(..., description="LLM provider (openai, anthropic, etc.)")
    tokens_prompt: int = Field(..., ge=0, description="Number of prompt tokens")
    tokens_response: int = Field(..., ge=0, description="Number of response tokens")
    model: str | None = Field(None, description="Model name")
    device_name: str | None = Field(None, description="Human-readable device name")
    request_id: str | None = Field(None, description="Unique request identifier")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class UsageEventResponse(BaseModel):
    """Response for a recorded usage event."""

    id: int
    timestamp: str
    device_ip: str
    endpoint: str
    provider: str
    model: str | None
    tokens_prompt: int
    tokens_response: int
    total_tokens: int
    cost_estimate: float | None


class PeriodStats(BaseModel):
    """Statistics for a time period."""

    period: str
    start_date: str
    end_date: str
    requests: int
    tokens: int
    tokens_prompt: int
    tokens_response: int
    cost_estimate: float
    unique_devices: int


class DashboardStatsResponse(BaseModel):
    """Response for dashboard statistics."""

    today: PeriodStats
    week: PeriodStats
    month: PeriodStats
    top_devices: list[dict[str, Any]]
    top_endpoints: list[dict[str, Any]]
    peak_hours: list[int]
    recent_activity: list[dict[str, Any]]
    generated_at: str
    filter_device_ip: str | None


class TrendResponse(BaseModel):
    """Response for trend analysis."""

    metric: str
    period_days: int
    start_date: str
    end_date: str
    data_points: list[dict[str, Any]]
    trend_direction: str
    change_percent: float
    average_daily: float
    total: float
    peak_value: float
    peak_date: str | None


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    tokens_prompt: int = Field(..., ge=0, description="Number of prompt tokens")
    tokens_response: int = Field(..., ge=0, description="Number of response tokens")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")


class CostEstimateResponse(BaseModel):
    """Response for cost estimation."""

    cost_usd: float
    currency: str
    provider: str
    model: str
    breakdown: dict[str, Any]
    rate: dict[str, float]


class ProviderRateResponse(BaseModel):
    """Response for provider rates."""

    rates: list[dict[str, Any]]


class SetRateRequest(BaseModel):
    """Request to set a provider rate."""

    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model name")
    prompt_per_1m: float = Field(..., gt=0, description="Cost per 1M prompt tokens")
    response_per_1m: float = Field(..., gt=0, description="Cost per 1M response tokens")
    currency: str = Field(default="USD", description="Currency code")
    notes: str | None = Field(None, description="Optional notes")


# ============================================================================
# Dashboard Endpoints
# ============================================================================


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> DashboardStatsResponse:
    """
    Get comprehensive dashboard statistics.

    Returns aggregate statistics for today, this week, and this month,
    along with top devices, top endpoints, peak hours, and recent activity.
    """
    analytics = AnalyticsService(db)
    stats = await analytics.get_dashboard_stats(device_ip=device_ip)

    return DashboardStatsResponse(
        today=PeriodStats(**stats["today"]),
        week=PeriodStats(**stats["week"]),
        month=PeriodStats(**stats["month"]),
        top_devices=stats["top_devices"],
        top_endpoints=stats["top_endpoints"],
        peak_hours=stats["peak_hours"],
        recent_activity=stats["recent_activity"],
        generated_at=stats["generated_at"],
        filter_device_ip=stats["filter_device_ip"],
    )


@router.get("/summary")
async def get_quick_summary(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> dict[str, Any]:
    """
    Get a quick summary of usage for today, week, and month.

    Lighter-weight alternative to the full dashboard endpoint.
    """
    reporter = UsageReporterService(db)
    return await reporter.get_quick_summary(device_ip=device_ip)


# ============================================================================
# Usage Recording Endpoints
# ============================================================================


@router.post("/usage", response_model=UsageEventResponse, status_code=status.HTTP_201_CREATED)
async def record_usage(
    request: RecordUsageRequest,
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UsageEventResponse:
    """
    Record a usage event.

    Creates a new usage record with automatic cost estimation
    based on the provider and model.
    """
    analytics = AnalyticsService(db)

    try:
        event = await analytics.record_usage(
            device_ip=request.device_ip,
            endpoint=request.endpoint,
            provider=request.provider,
            tokens_prompt=request.tokens_prompt,
            tokens_response=request.tokens_response,
            model=request.model,
            device_name=request.device_name,
            request_id=request.request_id,
            metadata=request.metadata,
        )

        return UsageEventResponse(
            id=event.id,
            timestamp=event.timestamp.isoformat(),
            device_ip=event.device_ip,
            endpoint=event.endpoint,
            provider=event.provider,
            model=event.model,
            tokens_prompt=event.tokens_prompt,
            tokens_response=event.tokens_response,
            total_tokens=event.total_tokens,
            cost_estimate=float(event.cost_estimate) if event.cost_estimate else None,
        )

    except Exception as e:
        logger.error("record_usage_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record usage",
        ) from e


@router.get("/usage/daily")
async def get_daily_usage(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_ip: str = Query(..., description="Device IP address"),
    date: str | None = Query(None, description="Date (YYYY-MM-DD), defaults to today"),
) -> dict[str, Any]:
    """
    Get daily usage statistics for a specific device.
    """
    tracker = TokenTrackerService(db)

    day = None
    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )

    return await tracker.get_daily(device_ip=device_ip, day=day)


@router.get("/usage/device/{device_ip}")
async def get_device_stats(
    device_ip: str,
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=7, ge=1, le=90, description="Number of days"),
) -> dict[str, Any]:
    """
    Get usage statistics for a specific device over a time period.
    """
    analytics = AnalyticsService(db)
    return await analytics.get_device_summary(device_ip=device_ip)


@router.get("/usage/devices")
async def get_top_devices(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=7, ge=1, le=90, description="Number of days"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum devices to return"),
) -> list[dict[str, Any]]:
    """
    Get top devices by token usage.
    """
    tracker = TokenTrackerService(db)
    return await tracker.get_top_devices(days=days, limit=limit)


# ============================================================================
# Trend Analysis Endpoints
# ============================================================================


@router.get("/trends/usage", response_model=TrendResponse)
async def get_usage_trend(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=7, le=365, description="Number of days"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> TrendResponse:
    """
    Get usage trend analysis.

    Analyzes token usage over time and returns trend direction,
    change percentage, and daily data points for charting.
    """
    analytics = AnalyticsService(db)
    trend = await analytics.get_usage_trend(days=days, device_ip=device_ip)
    return TrendResponse(**trend)


@router.get("/trends/cost", response_model=TrendResponse)
async def get_cost_trend(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=7, le=365, description="Number of days"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> TrendResponse:
    """
    Get cost trend analysis.

    Analyzes estimated costs over time and returns trend direction,
    change percentage, and daily data points for charting.
    """
    analytics = AnalyticsService(db)
    trend = await analytics.get_cost_trend(days=days, device_ip=device_ip)
    return TrendResponse(**trend)


@router.get("/trends/peak-hours")
async def get_peak_hours(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=7, ge=1, le=90, description="Number of days"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> dict[str, Any]:
    """
    Get peak usage hours analysis.
    """
    analyzer = TrendAnalyzerService(db)
    return await analyzer.get_peak_hours(days=days, device_ip=device_ip)


@router.get("/trends/weekdays")
async def get_weekday_patterns(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=28, ge=7, le=90, description="Number of days"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> dict[str, Any]:
    """
    Get usage patterns by day of week.
    """
    analyzer = TrendAnalyzerService(db)
    return await analyzer.get_weekday_patterns(days=days, device_ip=device_ip)


@router.get("/trends/anomalies")
async def detect_anomalies(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=7, le=90, description="Number of days"),
    threshold: float = Query(default=2.0, ge=1.0, le=3.0, description="Std deviation threshold"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> dict[str, Any]:
    """
    Detect anomalous usage days.
    """
    analyzer = TrendAnalyzerService(db)
    return await analyzer.detect_anomalies(
        days=days,
        threshold_std=threshold,
        device_ip=device_ip,
    )


@router.get("/trends/compare")
async def compare_periods(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=7, ge=1, le=30, description="Period length in days"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> dict[str, Any]:
    """
    Compare current period to previous period.
    """
    analyzer = TrendAnalyzerService(db)
    return await analyzer.compare_periods(current_days=days, device_ip=device_ip)


# ============================================================================
# Reports Endpoints
# ============================================================================


@router.get("/reports")
async def generate_report(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: ReportPeriod = Query(default=ReportPeriod.WEEK, description="Report period"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> dict[str, Any]:
    """
    Generate a comprehensive usage report.
    """
    analytics = AnalyticsService(db)
    return await analytics.generate_report(period=period, device_ip=device_ip)


@router.get("/reports/export/csv")
async def export_csv(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: ReportPeriod = Query(default=ReportPeriod.WEEK, description="Report period"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
    detailed: bool = Query(default=False, description="Include individual events"),
) -> Response:
    """
    Export usage data as CSV file.
    """
    analytics = AnalyticsService(db)
    csv_content = await analytics.export_report_csv(
        period=period,
        device_ip=device_ip,
        include_details=detailed,
    )

    filename = f"usage_report_{period.value}_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/reports/export/json")
async def export_json(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: ReportPeriod = Query(default=ReportPeriod.WEEK, description="Report period"),
    device_ip: str | None = Query(None, description="Filter by device IP"),
) -> Response:
    """
    Export usage data as JSON file.
    """
    reporter = UsageReporterService(db)
    json_content = await reporter.export_json(period=period, device_ip=device_ip)

    filename = f"usage_report_{period.value}_{datetime.now().strftime('%Y%m%d')}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================================================
# Cost Calculation Endpoints
# ============================================================================


@router.post("/cost/estimate", response_model=CostEstimateResponse)
async def estimate_cost(
    request: CostEstimateRequest,
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CostEstimateResponse:
    """
    Estimate cost for a given token usage.
    """
    calculator = CostCalculatorService(db)
    estimate = await calculator.estimate(
        tokens_prompt=request.tokens_prompt,
        tokens_response=request.tokens_response,
        provider=request.provider,
        model=request.model,
    )
    return CostEstimateResponse(**estimate)


@router.get("/cost/rates", response_model=ProviderRateResponse)
async def get_provider_rates(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    provider: str | None = Query(None, description="Filter by provider"),
) -> ProviderRateResponse:
    """
    Get configured provider pricing rates.
    """
    calculator = CostCalculatorService(db)
    rates = await calculator.get_rates(provider=provider)
    return ProviderRateResponse(rates=rates)


@router.post("/cost/rates")
async def set_provider_rate(
    request: SetRateRequest,
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Set or update a provider pricing rate.

    Requires admin role.
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to modify pricing rates",
        )

    calculator = CostCalculatorService(db)
    await calculator.set_rate(
        provider=request.provider,
        model=request.model,
        prompt_per_1m=Decimal(str(request.prompt_per_1m)),
        response_per_1m=Decimal(str(request.response_per_1m)),
        currency=request.currency,
        notes=request.notes,
    )

    return {
        "status": "success",
        "message": f"Rate set for {request.provider}:{request.model}",
    }


# ============================================================================
# Maintenance Endpoints
# ============================================================================


@router.post("/maintenance/cleanup")
async def cleanup_old_data(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    retention_days: int = Query(default=365, ge=30, le=730, description="Retention period"),
) -> dict[str, Any]:
    """
    Clean up data older than the retention period.

    Requires admin role.
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for data cleanup",
        )

    analytics = AnalyticsService(db)
    result = await analytics.cleanup_old_data(retention_days=retention_days)

    logger.info(
        "data_cleanup_requested",
        user_id=user.user_id,
        retention_days=retention_days,
        **result,
    )

    return result


@router.post("/maintenance/aggregate")
async def update_aggregates(
    user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date: str | None = Query(None, description="Date to aggregate (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """
    Update daily aggregates for faster queries.

    Requires admin role.
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for aggregate updates",
        )

    tracker = TokenTrackerService(db)

    day = None
    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )

    count = await tracker.update_daily_aggregates(day=day)

    return {
        "status": "success",
        "aggregates_updated": count,
        "date": (day or (datetime.now().date())).isoformat(),
    }


__all__ = ["router"]
