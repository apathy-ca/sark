"""
Core analytics service for home LLM usage dashboard.

Aggregates data from token tracker, cost calculator, and trend analyzer
to provide comprehensive dashboard statistics.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.analytics import DailyAggregate, UsageEvent
from sark.services.analytics.cost_calculator import CostCalculatorService
from sark.services.analytics.token_tracker import TokenTrackerService
from sark.services.analytics.trend_analyzer import TrendAnalyzerService, TrendMetric
from sark.services.analytics.usage_reporter import ReportPeriod, UsageReporterService

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """
    Aggregated analytics service for dashboard.

    Provides unified interface for dashboard statistics, combining
    data from all analytics sub-services.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize analytics service.

        Args:
            db: Async database session
        """
        self.db = db
        self.token_tracker = TokenTrackerService(db)
        self.cost_calculator = CostCalculatorService(db)
        self.trend_analyzer = TrendAnalyzerService(db)
        self.usage_reporter = UsageReporterService(db, self.cost_calculator)

    async def get_dashboard_stats(
        self,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Get comprehensive dashboard statistics.

        Args:
            device_ip: Optional device IP to filter by

        Returns:
            Dictionary with dashboard statistics
        """
        logger.info("fetching_dashboard_stats", device_ip=device_ip)

        # Get period statistics
        today_stats = await self._get_period_stats("today", device_ip)
        week_stats = await self._get_period_stats("week", device_ip)
        month_stats = await self._get_period_stats("month", device_ip)

        # Get top devices
        top_devices = await self.token_tracker.get_top_devices(days=7, limit=5)

        # Get top endpoints
        top_endpoints = await self._get_top_endpoints(days=7, limit=5, device_ip=device_ip)

        # Get peak hours
        peak_hours_data = await self.trend_analyzer.get_peak_hours(days=7, device_ip=device_ip)
        peak_hours = peak_hours_data.get("peak_hours_by_requests", [])

        # Get recent activity
        recent_activity = await self._get_recent_activity(limit=10, device_ip=device_ip)

        return {
            "today": today_stats,
            "week": week_stats,
            "month": month_stats,
            "top_devices": top_devices,
            "top_endpoints": top_endpoints,
            "peak_hours": peak_hours,
            "recent_activity": recent_activity,
            "generated_at": datetime.now(UTC).isoformat(),
            "filter_device_ip": device_ip,
        }

    async def _get_period_stats(
        self,
        period: str,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Get statistics for a time period.

        Args:
            period: "today", "week", or "month"
            device_ip: Optional device IP filter

        Returns:
            Dictionary with period statistics
        """
        now = datetime.now(UTC)

        if period == "today":
            start = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)
            end = now
        elif period == "week":
            # Start of week (Monday)
            days_since_monday = now.weekday()
            week_start = date.today() - timedelta(days=days_since_monday)
            start = datetime.combine(week_start, datetime.min.time(), tzinfo=UTC)
            end = now
        else:  # month
            month_start = date.today().replace(day=1)
            start = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC)
            end = now

        # Build query
        query = select(
            func.count(UsageEvent.id).label("requests"),
            func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
            func.sum(UsageEvent.tokens_response).label("tokens_response"),
            func.sum(UsageEvent.cost_estimate).label("cost_total"),
            func.count(func.distinct(UsageEvent.device_ip)).label("unique_devices"),
        ).where(
            UsageEvent.timestamp >= start,
            UsageEvent.timestamp <= end,
        )

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        result = await self.db.execute(query)
        row = result.one()

        tokens_prompt = row.tokens_prompt or 0
        tokens_response = row.tokens_response or 0

        return {
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "requests": row.requests or 0,
            "tokens": tokens_prompt + tokens_response,
            "tokens_prompt": tokens_prompt,
            "tokens_response": tokens_response,
            "cost_estimate": float(row.cost_total) if row.cost_total else 0.0,
            "unique_devices": row.unique_devices or 0,
        }

    async def _get_top_endpoints(
        self,
        days: int = 7,
        limit: int = 5,
        device_ip: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get top endpoints by request count.

        Args:
            days: Number of days to analyze
            limit: Maximum endpoints to return
            device_ip: Optional device IP filter

        Returns:
            List of top endpoint statistics
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        query = select(
            UsageEvent.endpoint,
            func.count(UsageEvent.id).label("request_count"),
            func.sum(
                UsageEvent.tokens_prompt + UsageEvent.tokens_response
            ).label("total_tokens"),
            func.sum(UsageEvent.cost_estimate).label("cost_total"),
        ).where(
            UsageEvent.timestamp >= start,
            UsageEvent.timestamp <= end,
        )

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        query = query.group_by(UsageEvent.endpoint).order_by(
            func.count(UsageEvent.id).desc()
        ).limit(limit)

        result = await self.db.execute(query)

        return [
            {
                "endpoint": ep,
                "request_count": cnt,
                "total_tokens": tok or 0,
                "cost_estimate": float(cost) if cost else 0.0,
            }
            for ep, cnt, tok, cost in result.fetchall()
        ]

    async def _get_recent_activity(
        self,
        limit: int = 10,
        device_ip: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get recent usage events.

        Args:
            limit: Maximum events to return
            device_ip: Optional device IP filter

        Returns:
            List of recent usage events
        """
        query = select(UsageEvent).order_by(UsageEvent.timestamp.desc()).limit(limit)

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        result = await self.db.execute(query)

        return [
            {
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "device_ip": event.device_ip,
                "device_name": event.device_name,
                "endpoint": event.endpoint,
                "provider": event.provider,
                "model": event.model,
                "tokens_prompt": event.tokens_prompt,
                "tokens_response": event.tokens_response,
                "total_tokens": event.total_tokens,
                "cost_estimate": float(event.cost_estimate) if event.cost_estimate else 0.0,
            }
            for event in result.scalars()
        ]

    async def record_usage(
        self,
        device_ip: str,
        endpoint: str,
        provider: str,
        tokens_prompt: int,
        tokens_response: int,
        model: str | None = None,
        device_name: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageEvent:
        """
        Record a usage event with automatic cost calculation.

        Args:
            device_ip: Device IP address
            endpoint: API endpoint called
            provider: LLM provider
            tokens_prompt: Prompt tokens
            tokens_response: Response tokens
            model: Model name
            device_name: Human-readable device name
            request_id: Request ID
            metadata: Additional metadata

        Returns:
            Created usage event
        """
        # Calculate cost estimate
        cost_estimate = None
        if model:
            cost_data = await self.cost_calculator.estimate(
                tokens_prompt=tokens_prompt,
                tokens_response=tokens_response,
                provider=provider,
                model=model,
            )
            cost_estimate = cost_data.get("cost_usd")

        # Record event
        return await self.token_tracker.record(
            device_ip=device_ip,
            endpoint=endpoint,
            provider=provider,
            tokens_prompt=tokens_prompt,
            tokens_response=tokens_response,
            model=model,
            device_name=device_name,
            cost_estimate=cost_estimate,
            request_id=request_id,
            metadata=metadata,
        )

    async def get_usage_trend(
        self,
        days: int = 30,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Get usage trend data for charts.

        Args:
            days: Number of days to analyze
            device_ip: Optional device IP filter

        Returns:
            Trend analysis data
        """
        return await self.trend_analyzer.analyze_trend(
            metric=TrendMetric.TOKENS,
            days=days,
            device_ip=device_ip,
        )

    async def get_cost_trend(
        self,
        days: int = 30,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Get cost trend data for charts.

        Args:
            days: Number of days to analyze
            device_ip: Optional device IP filter

        Returns:
            Cost trend analysis data
        """
        return await self.trend_analyzer.analyze_trend(
            metric=TrendMetric.COST,
            days=days,
            device_ip=device_ip,
        )

    async def generate_report(
        self,
        period: ReportPeriod = ReportPeriod.WEEK,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a comprehensive usage report.

        Args:
            period: Report period
            device_ip: Optional device IP filter

        Returns:
            Usage report dictionary
        """
        return await self.usage_reporter.generate(
            period=period,
            device_ip=device_ip,
        )

    async def export_report_csv(
        self,
        period: ReportPeriod = ReportPeriod.WEEK,
        device_ip: str | None = None,
        include_details: bool = False,
    ) -> str:
        """
        Export usage data as CSV.

        Args:
            period: Report period
            device_ip: Optional device IP filter
            include_details: Include individual events

        Returns:
            CSV string
        """
        return await self.usage_reporter.export_csv(
            period=period,
            device_ip=device_ip,
            include_details=include_details,
        )

    async def cleanup_old_data(
        self,
        retention_days: int = 365,
    ) -> dict[str, int]:
        """
        Delete data older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Dictionary with deletion counts
        """
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)

        # Delete old usage events
        events_result = await self.db.execute(
            delete(UsageEvent).where(UsageEvent.timestamp < cutoff)
        )
        events_deleted = events_result.rowcount

        # Delete old daily aggregates
        cutoff_date = (date.today() - timedelta(days=retention_days)).isoformat()
        aggregates_result = await self.db.execute(
            delete(DailyAggregate).where(DailyAggregate.date < cutoff_date)
        )
        aggregates_deleted = aggregates_result.rowcount

        await self.db.commit()

        logger.info(
            "old_data_cleaned_up",
            retention_days=retention_days,
            events_deleted=events_deleted,
            aggregates_deleted=aggregates_deleted,
        )

        return {
            "events_deleted": events_deleted,
            "aggregates_deleted": aggregates_deleted,
            "cutoff_date": cutoff.isoformat(),
        }

    async def get_device_summary(
        self,
        device_ip: str,
    ) -> dict[str, Any]:
        """
        Get comprehensive summary for a specific device.

        Args:
            device_ip: Device IP address

        Returns:
            Device summary statistics
        """
        # Get basic stats
        stats = await self.token_tracker.get_device_stats(device_ip, days=30)

        # Get recent trend
        trend = await self.trend_analyzer.analyze_trend(
            metric=TrendMetric.TOKENS,
            days=14,
            device_ip=device_ip,
        )

        # Get peak hours for device
        peak_hours = await self.trend_analyzer.get_peak_hours(
            days=7,
            device_ip=device_ip,
        )

        # Get hourly distribution
        hourly = await self.token_tracker.get_hourly_distribution(
            device_ip=device_ip,
            days=7,
        )

        return {
            "device_ip": device_ip,
            "stats": stats,
            "trend": {
                "direction": trend.get("trend_direction"),
                "change_percent": trend.get("change_percent"),
                "average_daily_tokens": trend.get("average_daily"),
            },
            "peak_hours": peak_hours.get("peak_hours_by_requests", []),
            "hourly_distribution": hourly,
        }


__all__ = ["AnalyticsService"]
