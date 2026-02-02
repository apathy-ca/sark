"""
Analytics models for home LLM usage tracking.

SQLite-optimized models for tracking token usage, costs, and analytics
in home deployment scenarios. Uses indexes optimized for time-series queries.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON

from sark.db.base import Base


class UsageEvent(Base):
    """
    Usage event model for tracking individual LLM requests.

    Stores per-request data including device, endpoint, tokens, and cost.
    Optimized for SQLite with indexes for common query patterns.
    """

    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    device_ip = Column(String(45), nullable=False, index=True)  # IPv6 max length
    device_name = Column(String(255), nullable=True)
    endpoint = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=True)
    tokens_prompt = Column(Integer, nullable=False, default=0)
    tokens_response = Column(Integer, nullable=False, default=0)
    cost_estimate = Column(Numeric(10, 6), nullable=True)
    request_id = Column(String(36), nullable=True, index=True)
    metadata_ = Column("metadata", JSON, nullable=False, default={})

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_usage_device_timestamp", "device_ip", "timestamp"),
        Index("idx_usage_endpoint_timestamp", "endpoint", "timestamp"),
        Index("idx_usage_provider_model", "provider", "model"),
    )

    def __repr__(self) -> str:
        return (
            f"<UsageEvent(id={self.id}, device_ip={self.device_ip}, "
            f"endpoint={self.endpoint}, tokens={self.tokens_prompt + self.tokens_response})>"
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens (prompt + response)."""
        return (self.tokens_prompt or 0) + (self.tokens_response or 0)


class DailyAggregate(Base):
    """
    Daily aggregate model for pre-computed daily statistics.

    Pre-aggregated data to speed up dashboard queries.
    Updated periodically via background job.
    """

    __tablename__ = "daily_aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD format
    device_ip = Column(String(45), nullable=False, index=True)
    endpoint = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    request_count = Column(Integer, nullable=False, default=0)
    tokens_prompt_total = Column(Integer, nullable=False, default=0)
    tokens_response_total = Column(Integer, nullable=False, default=0)
    cost_total = Column(Numeric(10, 4), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_daily_date_device", "date", "device_ip"),
        Index("idx_daily_date_endpoint", "date", "endpoint"),
        # Unique constraint to prevent duplicate aggregates
        Index(
            "idx_daily_unique",
            "date",
            "device_ip",
            "endpoint",
            "provider",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DailyAggregate(date={self.date}, device_ip={self.device_ip}, "
            f"requests={self.request_count})>"
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens (prompt + response)."""
        return (self.tokens_prompt_total or 0) + (self.tokens_response_total or 0)


class ProviderPricing(Base):
    """
    Provider pricing model for configurable cost rates.

    Stores current pricing for LLM providers. Rates can be updated
    without code changes.
    """

    __tablename__ = "provider_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    prompt_per_1m = Column(Numeric(10, 4), nullable=False)  # Cost per 1M prompt tokens
    response_per_1m = Column(
        Numeric(10, 4), nullable=False
    )  # Cost per 1M response tokens
    currency = Column(String(3), nullable=False, default="USD")
    effective_date = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_pricing_provider_model", "provider", "model", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ProviderPricing(provider={self.provider}, model={self.model})>"


# ============================================================================
# Pydantic Schemas for API
# ============================================================================


class UsageEventSchema(PydanticBaseModel):
    """Pydantic schema for usage events."""

    id: int
    timestamp: datetime
    device_ip: str
    device_name: str | None = None
    endpoint: str
    provider: str
    model: str | None = None
    tokens_prompt: int
    tokens_response: int
    total_tokens: int
    cost_estimate: Decimal | None = None
    request_id: str | None = None

    class Config:
        from_attributes = True


class DailyUsageSchema(PydanticBaseModel):
    """Schema for daily usage summary."""

    date: str
    device_ip: str
    device_name: str | None = None
    total_requests: int
    total_tokens: int
    tokens_prompt: int
    tokens_response: int
    cost_estimate: Decimal | None = None
    by_endpoint: dict[str, Any] = Field(default_factory=dict)
    by_provider: dict[str, Any] = Field(default_factory=dict)


class PeriodStatsSchema(PydanticBaseModel):
    """Schema for period statistics (today/week/month)."""

    period: str
    start_date: datetime
    end_date: datetime
    total_requests: int
    total_tokens: int
    tokens_prompt: int
    tokens_response: int
    cost_estimate: Decimal
    unique_devices: int
    top_endpoints: list[dict[str, Any]] = Field(default_factory=list)


class DashboardStatsSchema(PydanticBaseModel):
    """Schema for dashboard statistics."""

    today: PeriodStatsSchema
    week: PeriodStatsSchema
    month: PeriodStatsSchema
    top_devices: list[dict[str, Any]] = Field(default_factory=list)
    top_endpoints: list[dict[str, Any]] = Field(default_factory=list)
    peak_hours: list[dict[str, Any]] = Field(default_factory=list)
    recent_activity: list[UsageEventSchema] = Field(default_factory=list)


class TrendDataSchema(PydanticBaseModel):
    """Schema for trend analysis data."""

    period: str
    data_points: list[dict[str, Any]]
    trend_direction: str  # "up", "down", "stable"
    change_percent: float
    average_daily: float
    peak_value: float
    peak_date: str


class UsageReportSchema(PydanticBaseModel):
    """Schema for usage reports."""

    report_id: str
    generated_at: datetime
    period: str
    period_start: datetime
    period_end: datetime
    summary: dict[str, Any]
    by_device: list[dict[str, Any]]
    by_endpoint: list[dict[str, Any]]
    by_provider: list[dict[str, Any]]
    daily_breakdown: list[dict[str, Any]]
    cost_summary: dict[str, Any]


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # SQLAlchemy models
    "DailyAggregate",
    "ProviderPricing",
    "UsageEvent",
    # Pydantic schemas
    "DailyUsageSchema",
    "DashboardStatsSchema",
    "PeriodStatsSchema",
    "TrendDataSchema",
    "UsageEventSchema",
    "UsageReportSchema",
]
