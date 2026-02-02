"""
Trend analyzer service for home LLM analytics.

Analyzes usage patterns and trends over time to identify
peak hours, growth rates, and anomalies.
"""

from datetime import UTC, date, datetime, timedelta
from enum import Enum
from statistics import mean, stdev
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.analytics import DailyAggregate, UsageEvent

logger = structlog.get_logger(__name__)


class TrendDirection(str, Enum):
    """Trend direction indicator."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class TrendMetric(str, Enum):
    """Metrics available for trend analysis."""

    REQUESTS = "requests"
    TOKENS = "tokens"
    COST = "cost"
    DEVICES = "devices"


class TrendAnalyzerService:
    """
    Service for analyzing usage trends.

    Provides trend analysis, peak hour detection, and usage pattern insights.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize trend analyzer service.

        Args:
            db: Async database session
        """
        self.db = db

    async def analyze_trend(
        self,
        metric: TrendMetric = TrendMetric.TOKENS,
        days: int = 30,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze usage trend over a time period.

        Args:
            metric: Metric to analyze (requests, tokens, cost, devices)
            days: Number of days to analyze
            device_ip: Optional device IP filter

        Returns:
            Dictionary with trend analysis results
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        # Build metric column selector
        if metric == TrendMetric.REQUESTS:
            metric_col = func.count(UsageEvent.id)
        elif metric == TrendMetric.TOKENS:
            metric_col = func.sum(
                UsageEvent.tokens_prompt + UsageEvent.tokens_response
            )
        elif metric == TrendMetric.COST:
            metric_col = func.sum(UsageEvent.cost_estimate)
        else:  # DEVICES
            metric_col = func.count(func.distinct(UsageEvent.device_ip))

        # Build query
        query = select(
            func.date(UsageEvent.timestamp).label("day"),
            metric_col.label("value"),
        ).where(
            UsageEvent.timestamp >= start,
            UsageEvent.timestamp <= end,
        )

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        query = query.group_by(func.date(UsageEvent.timestamp)).order_by(
            func.date(UsageEvent.timestamp)
        )

        result = await self.db.execute(query)
        data_points = [
            {"date": str(day), "value": float(val) if val else 0}
            for day, val in result.fetchall()
        ]

        if not data_points:
            return {
                "metric": metric.value,
                "period_days": days,
                "data_points": [],
                "trend_direction": TrendDirection.STABLE.value,
                "change_percent": 0.0,
                "average_daily": 0.0,
                "peak_value": 0.0,
                "peak_date": None,
                "min_value": 0.0,
                "min_date": None,
                "volatility": 0.0,
            }

        values = [dp["value"] for dp in data_points]

        # Calculate statistics
        avg_daily = mean(values) if values else 0
        peak_value = max(values) if values else 0
        peak_idx = values.index(peak_value) if values else 0
        min_value = min(values) if values else 0
        min_idx = values.index(min_value) if values else 0

        # Calculate volatility (coefficient of variation)
        volatility = 0.0
        if len(values) > 1 and avg_daily > 0:
            volatility = (stdev(values) / avg_daily) * 100

        # Determine trend direction
        # Compare average of first half to second half
        mid = len(values) // 2
        if mid > 0:
            first_half_avg = mean(values[:mid])
            second_half_avg = mean(values[mid:])

            if first_half_avg > 0:
                change_percent = (
                    (second_half_avg - first_half_avg) / first_half_avg
                ) * 100
            else:
                change_percent = 100.0 if second_half_avg > 0 else 0.0

            if change_percent > 10:
                trend_direction = TrendDirection.UP
            elif change_percent < -10:
                trend_direction = TrendDirection.DOWN
            else:
                trend_direction = TrendDirection.STABLE
        else:
            change_percent = 0.0
            trend_direction = TrendDirection.STABLE

        return {
            "metric": metric.value,
            "period_days": days,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "filter_device_ip": device_ip,
            "data_points": data_points,
            "trend_direction": trend_direction.value,
            "change_percent": round(change_percent, 2),
            "average_daily": round(avg_daily, 2),
            "total": sum(values),
            "peak_value": peak_value,
            "peak_date": data_points[peak_idx]["date"] if data_points else None,
            "min_value": min_value,
            "min_date": data_points[min_idx]["date"] if data_points else None,
            "volatility": round(volatility, 2),
        }

    async def get_peak_hours(
        self,
        days: int = 7,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Identify peak usage hours.

        Args:
            days: Number of days to analyze
            device_ip: Optional device IP filter

        Returns:
            Dictionary with peak hour analysis
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        query = select(
            func.strftime("%H", UsageEvent.timestamp).label("hour"),
            func.count(UsageEvent.id).label("request_count"),
            func.sum(
                UsageEvent.tokens_prompt + UsageEvent.tokens_response
            ).label("total_tokens"),
            func.avg(
                UsageEvent.tokens_prompt + UsageEvent.tokens_response
            ).label("avg_tokens"),
        ).where(
            UsageEvent.timestamp >= start,
            UsageEvent.timestamp <= end,
        )

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        query = query.group_by(
            func.strftime("%H", UsageEvent.timestamp)
        ).order_by(
            func.strftime("%H", UsageEvent.timestamp)
        )

        result = await self.db.execute(query)
        hourly_data = [
            {
                "hour": int(hour),
                "hour_label": f"{int(hour):02d}:00",
                "request_count": cnt,
                "total_tokens": tok or 0,
                "avg_tokens_per_request": round(avg or 0, 2),
            }
            for hour, cnt, tok, avg in result.fetchall()
        ]

        # Find peaks
        if hourly_data:
            max_requests = max(h["request_count"] for h in hourly_data)
            max_tokens = max(h["total_tokens"] for h in hourly_data)

            peak_hours_by_requests = [
                h["hour"] for h in hourly_data if h["request_count"] == max_requests
            ]
            peak_hours_by_tokens = [
                h["hour"] for h in hourly_data if h["total_tokens"] == max_tokens
            ]
        else:
            peak_hours_by_requests = []
            peak_hours_by_tokens = []

        return {
            "period_days": days,
            "filter_device_ip": device_ip,
            "hourly_data": hourly_data,
            "peak_hours_by_requests": peak_hours_by_requests,
            "peak_hours_by_tokens": peak_hours_by_tokens,
            "summary": {
                "most_active_hour": (
                    peak_hours_by_requests[0] if peak_hours_by_requests else None
                ),
                "least_active_hour": (
                    min(hourly_data, key=lambda h: h["request_count"])["hour"]
                    if hourly_data
                    else None
                ),
            },
        }

    async def get_weekday_patterns(
        self,
        days: int = 28,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze usage patterns by day of week.

        Args:
            days: Number of days to analyze (should be multiple of 7)
            device_ip: Optional device IP filter

        Returns:
            Dictionary with weekday usage patterns
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        query = select(
            func.strftime("%w", UsageEvent.timestamp).label("weekday"),
            func.count(UsageEvent.id).label("request_count"),
            func.sum(
                UsageEvent.tokens_prompt + UsageEvent.tokens_response
            ).label("total_tokens"),
        ).where(
            UsageEvent.timestamp >= start,
            UsageEvent.timestamp <= end,
        )

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        query = query.group_by(
            func.strftime("%w", UsageEvent.timestamp)
        ).order_by(
            func.strftime("%w", UsageEvent.timestamp)
        )

        result = await self.db.execute(query)

        weekday_names = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ]

        weekday_data = []
        for weekday, cnt, tok in result.fetchall():
            weekday_idx = int(weekday)
            weekday_data.append(
                {
                    "weekday": weekday_idx,
                    "weekday_name": weekday_names[weekday_idx],
                    "request_count": cnt,
                    "total_tokens": tok or 0,
                }
            )

        # Calculate weekday vs weekend comparison
        weekday_requests = sum(
            d["request_count"]
            for d in weekday_data
            if d["weekday"] in [1, 2, 3, 4, 5]
        )
        weekend_requests = sum(
            d["request_count"]
            for d in weekday_data
            if d["weekday"] in [0, 6]
        )

        return {
            "period_days": days,
            "filter_device_ip": device_ip,
            "weekday_data": weekday_data,
            "summary": {
                "busiest_day": (
                    max(weekday_data, key=lambda d: d["request_count"])["weekday_name"]
                    if weekday_data
                    else None
                ),
                "quietest_day": (
                    min(weekday_data, key=lambda d: d["request_count"])["weekday_name"]
                    if weekday_data
                    else None
                ),
                "weekday_total_requests": weekday_requests,
                "weekend_total_requests": weekend_requests,
                "weekday_vs_weekend_ratio": (
                    round(weekday_requests / weekend_requests, 2)
                    if weekend_requests > 0
                    else 0
                ),
            },
        }

    async def detect_anomalies(
        self,
        days: int = 30,
        threshold_std: float = 2.0,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Detect anomalous usage days.

        Uses standard deviation to identify days with unusual usage.

        Args:
            days: Number of days to analyze
            threshold_std: Standard deviation threshold for anomaly detection
            device_ip: Optional device IP filter

        Returns:
            Dictionary with anomaly analysis
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        query = select(
            func.date(UsageEvent.timestamp).label("day"),
            func.count(UsageEvent.id).label("request_count"),
            func.sum(
                UsageEvent.tokens_prompt + UsageEvent.tokens_response
            ).label("total_tokens"),
        ).where(
            UsageEvent.timestamp >= start,
            UsageEvent.timestamp <= end,
        )

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        query = query.group_by(func.date(UsageEvent.timestamp)).order_by(
            func.date(UsageEvent.timestamp)
        )

        result = await self.db.execute(query)
        daily_data = [
            {
                "date": str(day),
                "request_count": cnt,
                "total_tokens": tok or 0,
            }
            for day, cnt, tok in result.fetchall()
        ]

        if len(daily_data) < 3:
            return {
                "period_days": days,
                "filter_device_ip": device_ip,
                "anomalies": [],
                "summary": {
                    "insufficient_data": True,
                    "message": "Need at least 3 days of data for anomaly detection",
                },
            }

        # Calculate statistics for requests
        request_values = [d["request_count"] for d in daily_data]
        request_mean = mean(request_values)
        request_std = stdev(request_values) if len(request_values) > 1 else 0

        # Calculate statistics for tokens
        token_values = [d["total_tokens"] for d in daily_data]
        token_mean = mean(token_values)
        token_std = stdev(token_values) if len(token_values) > 1 else 0

        # Identify anomalies
        anomalies = []
        for day_data in daily_data:
            anomaly_types = []

            # Check request anomaly
            if request_std > 0:
                request_z = (
                    day_data["request_count"] - request_mean
                ) / request_std
                if abs(request_z) > threshold_std:
                    anomaly_types.append(
                        {
                            "type": "requests",
                            "z_score": round(request_z, 2),
                            "direction": "high" if request_z > 0 else "low",
                        }
                    )

            # Check token anomaly
            if token_std > 0:
                token_z = (day_data["total_tokens"] - token_mean) / token_std
                if abs(token_z) > threshold_std:
                    anomaly_types.append(
                        {
                            "type": "tokens",
                            "z_score": round(token_z, 2),
                            "direction": "high" if token_z > 0 else "low",
                        }
                    )

            if anomaly_types:
                anomalies.append(
                    {
                        "date": day_data["date"],
                        "request_count": day_data["request_count"],
                        "total_tokens": day_data["total_tokens"],
                        "anomaly_types": anomaly_types,
                    }
                )

        return {
            "period_days": days,
            "filter_device_ip": device_ip,
            "threshold_std": threshold_std,
            "statistics": {
                "request_mean": round(request_mean, 2),
                "request_std": round(request_std, 2),
                "token_mean": round(token_mean, 2),
                "token_std": round(token_std, 2),
            },
            "anomalies": anomalies,
            "summary": {
                "total_anomalous_days": len(anomalies),
                "anomaly_rate": round(len(anomalies) / len(daily_data) * 100, 2),
            },
        }

    async def compare_periods(
        self,
        current_days: int = 7,
        device_ip: str | None = None,
    ) -> dict[str, Any]:
        """
        Compare current period to previous period.

        Args:
            current_days: Number of days for current period
            device_ip: Optional device IP filter

        Returns:
            Dictionary with period comparison
        """
        now = datetime.now(UTC)
        current_start = now - timedelta(days=current_days)
        previous_start = current_start - timedelta(days=current_days)

        async def get_period_stats(
            start: datetime, end: datetime
        ) -> dict[str, Any]:
            query = select(
                func.count(UsageEvent.id).label("requests"),
                func.sum(
                    UsageEvent.tokens_prompt + UsageEvent.tokens_response
                ).label("tokens"),
                func.sum(UsageEvent.cost_estimate).label("cost"),
                func.count(func.distinct(UsageEvent.device_ip)).label("devices"),
            ).where(
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            )

            if device_ip:
                query = query.where(UsageEvent.device_ip == device_ip)

            result = await self.db.execute(query)
            row = result.one()

            return {
                "requests": row.requests or 0,
                "tokens": row.tokens or 0,
                "cost": float(row.cost) if row.cost else 0.0,
                "devices": row.devices or 0,
            }

        current_stats = await get_period_stats(current_start, now)
        previous_stats = await get_period_stats(previous_start, current_start)

        # Calculate changes
        def calc_change(current: float, previous: float) -> dict[str, Any]:
            if previous == 0:
                change_pct = 100.0 if current > 0 else 0.0
            else:
                change_pct = ((current - previous) / previous) * 100
            return {
                "current": current,
                "previous": previous,
                "change": current - previous,
                "change_percent": round(change_pct, 2),
            }

        return {
            "period_days": current_days,
            "filter_device_ip": device_ip,
            "current_period": {
                "start": current_start.isoformat(),
                "end": now.isoformat(),
            },
            "previous_period": {
                "start": previous_start.isoformat(),
                "end": current_start.isoformat(),
            },
            "comparison": {
                "requests": calc_change(
                    current_stats["requests"], previous_stats["requests"]
                ),
                "tokens": calc_change(
                    current_stats["tokens"], previous_stats["tokens"]
                ),
                "cost": calc_change(
                    current_stats["cost"], previous_stats["cost"]
                ),
                "devices": calc_change(
                    current_stats["devices"], previous_stats["devices"]
                ),
            },
        }


__all__ = ["TrendAnalyzerService", "TrendDirection", "TrendMetric"]
