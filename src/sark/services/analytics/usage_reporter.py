"""
Usage reporter service for home LLM analytics.

Generates human-readable usage reports with export capabilities.
Supports daily, weekly, and monthly reports in JSON and CSV formats.
"""

import csv
import io
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.analytics import DailyAggregate, UsageEvent
from sark.services.analytics.cost_calculator import CostCalculatorService

logger = structlog.get_logger(__name__)


class ReportPeriod(str, Enum):
    """Report time period."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report output format."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    JSON = "json"
    CSV = "csv"


class UsageReporterService:
    """
    Service for generating usage reports.

    Produces comprehensive reports with usage statistics,
    cost estimates, and exportable data formats.
    """

    def __init__(
        self,
        db: AsyncSession,
        cost_calculator: CostCalculatorService | None = None,
    ) -> None:
        """
        Initialize usage reporter service.

        Args:
            db: Async database session
            cost_calculator: Optional cost calculator for estimates
        """
        self.db = db
        self.cost_calculator = cost_calculator or CostCalculatorService(db)

    def _get_period_dates(
        self,
        period: ReportPeriod,
        reference_date: date | None = None,
    ) -> tuple[datetime, datetime]:
        """
        Calculate start and end dates for a period.

        Args:
            period: Report period
            reference_date: Reference date (defaults to today)

        Returns:
            Tuple of (start_datetime, end_datetime)
        """
        reference = reference_date or date.today()

        if period == ReportPeriod.DAY:
            start = datetime.combine(reference, datetime.min.time(), tzinfo=UTC)
            end = datetime.combine(reference, datetime.max.time(), tzinfo=UTC)
        elif period == ReportPeriod.WEEK:
            # Start of week (Monday)
            days_since_monday = reference.weekday()
            week_start = reference - timedelta(days=days_since_monday)
            start = datetime.combine(week_start, datetime.min.time(), tzinfo=UTC)
            end = datetime.combine(
                week_start + timedelta(days=6), datetime.max.time(), tzinfo=UTC
            )
        elif period == ReportPeriod.MONTH:
            # Start of month
            month_start = reference.replace(day=1)
            # End of month
            if reference.month == 12:
                next_month = reference.replace(year=reference.year + 1, month=1, day=1)
            else:
                next_month = reference.replace(month=reference.month + 1, day=1)
            month_end = next_month - timedelta(days=1)
            start = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC)
            end = datetime.combine(month_end, datetime.max.time(), tzinfo=UTC)
        else:
            # Default to today
            start = datetime.combine(reference, datetime.min.time(), tzinfo=UTC)
            end = datetime.combine(reference, datetime.max.time(), tzinfo=UTC)

        return start, end

    async def generate(
        self,
        period: ReportPeriod = ReportPeriod.WEEK,
        format: ReportFormat = ReportFormat.SUMMARY,
        device_ip: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Generate a usage report for a time period.

        Args:
            period: Report period (day, week, month)
            format: Report format (summary, detailed)
            device_ip: Optional device IP to filter by
            start_date: Custom start date (for CUSTOM period)
            end_date: Custom end date (for CUSTOM period)

        Returns:
            Report dictionary with usage statistics
        """
        # Determine date range
        if start_date and end_date:
            period_start = start_date
            period_end = end_date
        else:
            period_start, period_end = self._get_period_dates(period)

        report_id = str(uuid4())[:8]

        logger.info(
            "generating_usage_report",
            report_id=report_id,
            period=period.value,
            start=period_start.isoformat(),
            end=period_end.isoformat(),
            device_ip=device_ip,
        )

        # Build base query
        base_filter = [
            UsageEvent.timestamp >= period_start,
            UsageEvent.timestamp <= period_end,
        ]
        if device_ip:
            base_filter.append(UsageEvent.device_ip == device_ip)

        # Summary statistics
        summary_result = await self.db.execute(
            select(
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
                func.count(func.distinct(UsageEvent.device_ip)).label("unique_devices"),
            ).where(*base_filter)
        )
        summary = summary_result.one()

        # By device breakdown
        by_device_result = await self.db.execute(
            select(
                UsageEvent.device_ip,
                UsageEvent.device_name,
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            )
            .where(*base_filter)
            .group_by(UsageEvent.device_ip, UsageEvent.device_name)
            .order_by(func.sum(UsageEvent.tokens_prompt + UsageEvent.tokens_response).desc())
        )
        by_device = [
            {
                "device_ip": ip,
                "device_name": name,
                "request_count": cnt,
                "tokens_prompt": prompt or 0,
                "tokens_response": response or 0,
                "total_tokens": (prompt or 0) + (response or 0),
                "cost_estimate": float(cost) if cost else 0.0,
            }
            for ip, name, cnt, prompt, response, cost in by_device_result.fetchall()
        ]

        # By endpoint breakdown
        by_endpoint_result = await self.db.execute(
            select(
                UsageEvent.endpoint,
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            )
            .where(*base_filter)
            .group_by(UsageEvent.endpoint)
            .order_by(func.count(UsageEvent.id).desc())
        )
        by_endpoint = [
            {
                "endpoint": ep,
                "request_count": cnt,
                "tokens_prompt": prompt or 0,
                "tokens_response": response or 0,
                "total_tokens": (prompt or 0) + (response or 0),
                "cost_estimate": float(cost) if cost else 0.0,
            }
            for ep, cnt, prompt, response, cost in by_endpoint_result.fetchall()
        ]

        # By provider breakdown
        by_provider_result = await self.db.execute(
            select(
                UsageEvent.provider,
                UsageEvent.model,
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            )
            .where(*base_filter)
            .group_by(UsageEvent.provider, UsageEvent.model)
            .order_by(func.count(UsageEvent.id).desc())
        )
        by_provider = [
            {
                "provider": provider,
                "model": model,
                "request_count": cnt,
                "tokens_prompt": prompt or 0,
                "tokens_response": response or 0,
                "total_tokens": (prompt or 0) + (response or 0),
                "cost_estimate": float(cost) if cost else 0.0,
            }
            for provider, model, cnt, prompt, response, cost in by_provider_result.fetchall()
        ]

        # Daily breakdown
        daily_result = await self.db.execute(
            select(
                func.date(UsageEvent.timestamp).label("day"),
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            )
            .where(*base_filter)
            .group_by(func.date(UsageEvent.timestamp))
            .order_by(func.date(UsageEvent.timestamp))
        )
        daily_breakdown = [
            {
                "date": str(day),
                "request_count": cnt,
                "tokens_prompt": prompt or 0,
                "tokens_response": response or 0,
                "total_tokens": (prompt or 0) + (response or 0),
                "cost_estimate": float(cost) if cost else 0.0,
            }
            for day, cnt, prompt, response, cost in daily_result.fetchall()
        ]

        # Build report
        tokens_prompt = summary.tokens_prompt or 0
        tokens_response = summary.tokens_response or 0
        cost_total = float(summary.cost_total) if summary.cost_total else 0.0

        report = {
            "report_id": report_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "period": period.value,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "filter_device_ip": device_ip,
            "summary": {
                "request_count": summary.request_count or 0,
                "tokens_prompt": tokens_prompt,
                "tokens_response": tokens_response,
                "total_tokens": tokens_prompt + tokens_response,
                "cost_estimate": cost_total,
                "unique_devices": summary.unique_devices or 0,
                "avg_tokens_per_request": (
                    (tokens_prompt + tokens_response) / (summary.request_count or 1)
                ),
            },
            "by_device": by_device,
            "by_endpoint": by_endpoint,
            "by_provider": by_provider,
            "daily_breakdown": daily_breakdown,
            "cost_summary": {
                "total_cost_usd": cost_total,
                "currency": "USD",
                "by_provider": {
                    item["provider"]: item["cost_estimate"] for item in by_provider
                },
            },
        }

        logger.info(
            "usage_report_generated",
            report_id=report_id,
            request_count=summary.request_count,
            total_tokens=tokens_prompt + tokens_response,
        )

        return report

    async def export_csv(
        self,
        period: ReportPeriod = ReportPeriod.WEEK,
        device_ip: str | None = None,
        include_details: bool = False,
    ) -> str:
        """
        Export usage data as CSV string.

        Args:
            period: Report period
            device_ip: Optional device IP filter
            include_details: Include individual events (vs aggregates)

        Returns:
            CSV string
        """
        period_start, period_end = self._get_period_dates(period)

        output = io.StringIO()
        writer = csv.writer(output)

        if include_details:
            # Export individual events
            writer.writerow(
                [
                    "timestamp",
                    "device_ip",
                    "device_name",
                    "endpoint",
                    "provider",
                    "model",
                    "tokens_prompt",
                    "tokens_response",
                    "total_tokens",
                    "cost_estimate",
                    "request_id",
                ]
            )

            base_filter = [
                UsageEvent.timestamp >= period_start,
                UsageEvent.timestamp <= period_end,
            ]
            if device_ip:
                base_filter.append(UsageEvent.device_ip == device_ip)

            result = await self.db.execute(
                select(UsageEvent)
                .where(*base_filter)
                .order_by(UsageEvent.timestamp)
            )

            for event in result.scalars():
                writer.writerow(
                    [
                        event.timestamp.isoformat(),
                        event.device_ip,
                        event.device_name or "",
                        event.endpoint,
                        event.provider,
                        event.model or "",
                        event.tokens_prompt,
                        event.tokens_response,
                        event.total_tokens,
                        event.cost_estimate or 0,
                        event.request_id or "",
                    ]
                )
        else:
            # Export daily aggregates
            writer.writerow(
                [
                    "date",
                    "device_ip",
                    "endpoint",
                    "provider",
                    "request_count",
                    "tokens_prompt",
                    "tokens_response",
                    "total_tokens",
                    "cost_estimate",
                ]
            )

            # Get aggregated data
            base_filter = [
                UsageEvent.timestamp >= period_start,
                UsageEvent.timestamp <= period_end,
            ]
            if device_ip:
                base_filter.append(UsageEvent.device_ip == device_ip)

            result = await self.db.execute(
                select(
                    func.date(UsageEvent.timestamp).label("day"),
                    UsageEvent.device_ip,
                    UsageEvent.endpoint,
                    UsageEvent.provider,
                    func.count(UsageEvent.id).label("request_count"),
                    func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                    func.sum(UsageEvent.tokens_response).label("tokens_response"),
                    func.sum(UsageEvent.cost_estimate).label("cost_total"),
                )
                .where(*base_filter)
                .group_by(
                    func.date(UsageEvent.timestamp),
                    UsageEvent.device_ip,
                    UsageEvent.endpoint,
                    UsageEvent.provider,
                )
                .order_by(func.date(UsageEvent.timestamp))
            )

            for day, ip, ep, provider, cnt, prompt, response, cost in result.fetchall():
                writer.writerow(
                    [
                        str(day),
                        ip,
                        ep,
                        provider,
                        cnt,
                        prompt or 0,
                        response or 0,
                        (prompt or 0) + (response or 0),
                        float(cost) if cost else 0,
                    ]
                )

        return output.getvalue()

    async def export_json(
        self,
        period: ReportPeriod = ReportPeriod.WEEK,
        device_ip: str | None = None,
    ) -> str:
        """
        Export usage data as JSON string.

        Args:
            period: Report period
            device_ip: Optional device IP filter

        Returns:
            JSON string
        """
        report = await self.generate(period=period, device_ip=device_ip)
        return json.dumps(report, indent=2, default=str)

    async def get_quick_summary(
        self,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Get a quick summary for display.

        Args:
            device_ip: Optional device IP filter

        Returns:
            Dictionary with today/week/month summaries
        """
        today_start, today_end = self._get_period_dates(ReportPeriod.DAY)
        week_start, week_end = self._get_period_dates(ReportPeriod.WEEK)
        month_start, month_end = self._get_period_dates(ReportPeriod.MONTH)

        async def get_period_summary(start: datetime, end: datetime) -> dict[str, Any]:
            base_filter = [
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            ]
            if device_ip:
                base_filter.append(UsageEvent.device_ip == device_ip)

            result = await self.db.execute(
                select(
                    func.count(UsageEvent.id).label("requests"),
                    func.sum(UsageEvent.tokens_prompt + UsageEvent.tokens_response).label(
                        "tokens"
                    ),
                    func.sum(UsageEvent.cost_estimate).label("cost"),
                ).where(*base_filter)
            )
            row = result.one()

            return {
                "requests": row.requests or 0,
                "tokens": row.tokens or 0,
                "cost_estimate": float(row.cost) if row.cost else 0.0,
            }

        return {
            "today": await get_period_summary(today_start, today_end),
            "week": await get_period_summary(week_start, week_end),
            "month": await get_period_summary(month_start, month_end),
            "filter_device_ip": device_ip,
        }


__all__ = ["ReportFormat", "ReportPeriod", "UsageReporterService"]
