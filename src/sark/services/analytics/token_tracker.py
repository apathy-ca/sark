"""
Token tracking service for home LLM usage.

Tracks token usage per device, endpoint, and time period.
Optimized for SQLite with efficient aggregation queries.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.analytics import DailyAggregate, UsageEvent

logger = structlog.get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage record for a single request."""

    device_ip: str
    endpoint: str
    provider: str
    tokens_prompt: int
    tokens_response: int
    model: str | None = None
    device_name: str | None = None
    cost_estimate: float | None = None
    request_id: str | None = None
    timestamp: datetime | None = None

    @property
    def total_tokens(self) -> int:
        """Total tokens (prompt + response)."""
        return self.tokens_prompt + self.tokens_response


class TokenTrackerService:
    """
    Service for tracking token usage per device.

    Provides methods for recording usage and retrieving aggregated statistics.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize token tracker service.

        Args:
            db: Async database session
        """
        self.db = db

    async def record(
        self,
        device_ip: str,
        endpoint: str,
        provider: str,
        tokens_prompt: int,
        tokens_response: int,
        model: str | None = None,
        device_name: str | None = None,
        cost_estimate: float | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageEvent:
        """
        Record token usage for a request.

        Args:
            device_ip: IP address of the requesting device
            endpoint: API endpoint called (e.g., "openai/chat/completions")
            provider: LLM provider (e.g., "openai", "anthropic")
            tokens_prompt: Number of prompt/input tokens
            tokens_response: Number of response/output tokens
            model: Model name if known
            device_name: Human-readable device name
            cost_estimate: Estimated cost in USD
            request_id: Unique request identifier
            metadata: Additional metadata

        Returns:
            Created usage event
        """
        event = UsageEvent(
            device_ip=device_ip,
            device_name=device_name,
            endpoint=endpoint,
            provider=provider,
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_response=tokens_response,
            cost_estimate=cost_estimate,
            request_id=request_id,
            metadata_=metadata or {},
            timestamp=datetime.now(UTC),
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logger.debug(
            "token_usage_recorded",
            event_id=event.id,
            device_ip=device_ip,
            endpoint=endpoint,
            total_tokens=tokens_prompt + tokens_response,
        )

        return event

    async def record_batch(self, usages: list[TokenUsage]) -> list[UsageEvent]:
        """
        Record multiple token usage records in a batch.

        Args:
            usages: List of TokenUsage records to save

        Returns:
            List of created usage events
        """
        events = []
        for usage in usages:
            event = UsageEvent(
                device_ip=usage.device_ip,
                device_name=usage.device_name,
                endpoint=usage.endpoint,
                provider=usage.provider,
                model=usage.model,
                tokens_prompt=usage.tokens_prompt,
                tokens_response=usage.tokens_response,
                cost_estimate=usage.cost_estimate,
                request_id=usage.request_id,
                timestamp=usage.timestamp or datetime.now(UTC),
            )
            self.db.add(event)
            events.append(event)

        await self.db.commit()

        logger.info(
            "token_usage_batch_recorded",
            count=len(events),
        )

        return events

    async def get_daily(
        self,
        device_ip: str,
        day: date | None = None,
    ) -> dict[str, Any]:
        """
        Get daily token usage for a specific device.

        Args:
            device_ip: Device IP address
            day: Date to query (defaults to today)

        Returns:
            Dictionary with daily usage statistics
        """
        day = day or date.today()
        start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
        end = datetime.combine(day, datetime.max.time(), tzinfo=UTC)

        result = await self.db.execute(
            select(
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            ).where(
                UsageEvent.device_ip == device_ip,
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            )
        )
        row = result.one()

        # Get breakdown by endpoint
        endpoint_result = await self.db.execute(
            select(
                UsageEvent.endpoint,
                func.count(UsageEvent.id).label("count"),
                func.sum(UsageEvent.tokens_prompt + UsageEvent.tokens_response).label(
                    "tokens"
                ),
            )
            .where(
                UsageEvent.device_ip == device_ip,
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            )
            .group_by(UsageEvent.endpoint)
        )
        by_endpoint = {
            ep: {"count": cnt, "tokens": tok}
            for ep, cnt, tok in endpoint_result.fetchall()
        }

        tokens_prompt = row.tokens_prompt or 0
        tokens_response = row.tokens_response or 0

        return {
            "date": day.isoformat(),
            "device_ip": device_ip,
            "request_count": row.request_count or 0,
            "total": tokens_prompt + tokens_response,
            "prompt": tokens_prompt,
            "response": tokens_response,
            "cost_estimate": float(row.cost_total) if row.cost_total else 0.0,
            "by_endpoint": by_endpoint,
        }

    async def get_device_stats(
        self,
        device_ip: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        Get usage statistics for a device over a period.

        Args:
            device_ip: Device IP address
            days: Number of days to include (default 7)

        Returns:
            Dictionary with device usage statistics
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            ).where(
                UsageEvent.device_ip == device_ip,
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            )
        )
        row = result.one()

        # Get daily breakdown
        daily_result = await self.db.execute(
            select(
                func.date(UsageEvent.timestamp).label("day"),
                func.count(UsageEvent.id).label("count"),
                func.sum(UsageEvent.tokens_prompt + UsageEvent.tokens_response).label(
                    "tokens"
                ),
            )
            .where(
                UsageEvent.device_ip == device_ip,
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            )
            .group_by(func.date(UsageEvent.timestamp))
            .order_by(func.date(UsageEvent.timestamp))
        )
        daily = [
            {"date": str(day), "requests": cnt, "tokens": tok}
            for day, cnt, tok in daily_result.fetchall()
        ]

        tokens_prompt = row.tokens_prompt or 0
        tokens_response = row.tokens_response or 0

        return {
            "device_ip": device_ip,
            "period_days": days,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "request_count": row.request_count or 0,
            "total_tokens": tokens_prompt + tokens_response,
            "tokens_prompt": tokens_prompt,
            "tokens_response": tokens_response,
            "cost_estimate": float(row.cost_total) if row.cost_total else 0.0,
            "daily": daily,
        }

    async def get_top_devices(
        self,
        days: int = 7,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get top devices by token usage.

        Args:
            days: Number of days to analyze
            limit: Maximum number of devices to return

        Returns:
            List of top devices with usage statistics
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        result = await self.db.execute(
            select(
                UsageEvent.device_ip,
                UsageEvent.device_name,
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt + UsageEvent.tokens_response).label(
                    "total_tokens"
                ),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            )
            .where(
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            )
            .group_by(UsageEvent.device_ip, UsageEvent.device_name)
            .order_by(
                func.sum(UsageEvent.tokens_prompt + UsageEvent.tokens_response).desc()
            )
            .limit(limit)
        )

        return [
            {
                "device_ip": ip,
                "device_name": name,
                "request_count": cnt,
                "total_tokens": tok,
                "cost_estimate": float(cost) if cost else 0.0,
            }
            for ip, name, cnt, tok, cost in result.fetchall()
        ]

    async def get_hourly_distribution(
        self,
        device_ip: str | None = None,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Get hourly distribution of token usage.

        Args:
            device_ip: Optional device IP to filter by
            days: Number of days to analyze

        Returns:
            List of hourly usage statistics (0-23)
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        query = select(
            func.strftime("%H", UsageEvent.timestamp).label("hour"),
            func.count(UsageEvent.id).label("request_count"),
            func.sum(UsageEvent.tokens_prompt + UsageEvent.tokens_response).label(
                "total_tokens"
            ),
        ).where(
            UsageEvent.timestamp >= start,
            UsageEvent.timestamp <= end,
        )

        if device_ip:
            query = query.where(UsageEvent.device_ip == device_ip)

        query = query.group_by(func.strftime("%H", UsageEvent.timestamp)).order_by(
            func.strftime("%H", UsageEvent.timestamp)
        )

        result = await self.db.execute(query)

        return [
            {
                "hour": int(hour),
                "request_count": cnt,
                "total_tokens": tok,
            }
            for hour, cnt, tok in result.fetchall()
        ]

    async def update_daily_aggregates(self, day: date | None = None) -> int:
        """
        Update daily aggregates for a specific day.

        Aggregates usage events into daily summary records for faster queries.

        Args:
            day: Date to aggregate (defaults to yesterday)

        Returns:
            Number of aggregates created/updated
        """
        day = day or (date.today() - timedelta(days=1))
        start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
        end = datetime.combine(day, datetime.max.time(), tzinfo=UTC)

        # Query aggregated data
        result = await self.db.execute(
            select(
                UsageEvent.device_ip,
                UsageEvent.endpoint,
                UsageEvent.provider,
                func.count(UsageEvent.id).label("request_count"),
                func.sum(UsageEvent.tokens_prompt).label("tokens_prompt"),
                func.sum(UsageEvent.tokens_response).label("tokens_response"),
                func.sum(UsageEvent.cost_estimate).label("cost_total"),
            )
            .where(
                UsageEvent.timestamp >= start,
                UsageEvent.timestamp <= end,
            )
            .group_by(
                UsageEvent.device_ip,
                UsageEvent.endpoint,
                UsageEvent.provider,
            )
        )

        count = 0
        for device_ip, endpoint, provider, req_cnt, tok_prompt, tok_response, cost in (
            result.fetchall()
        ):
            # Check if aggregate exists
            existing = await self.db.execute(
                select(DailyAggregate).where(
                    DailyAggregate.date == day.isoformat(),
                    DailyAggregate.device_ip == device_ip,
                    DailyAggregate.endpoint == endpoint,
                    DailyAggregate.provider == provider,
                )
            )
            agg = existing.scalar_one_or_none()

            if agg:
                agg.request_count = req_cnt
                agg.tokens_prompt_total = tok_prompt or 0
                agg.tokens_response_total = tok_response or 0
                agg.cost_total = cost
                agg.updated_at = datetime.now(UTC)
            else:
                agg = DailyAggregate(
                    date=day.isoformat(),
                    device_ip=device_ip,
                    endpoint=endpoint,
                    provider=provider,
                    request_count=req_cnt,
                    tokens_prompt_total=tok_prompt or 0,
                    tokens_response_total=tok_response or 0,
                    cost_total=cost,
                )
                self.db.add(agg)

            count += 1

        await self.db.commit()

        logger.info(
            "daily_aggregates_updated",
            date=day.isoformat(),
            aggregate_count=count,
        )

        return count


__all__ = ["TokenTrackerService", "TokenUsage"]
