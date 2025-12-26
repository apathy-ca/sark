"""
Cost attribution models for SARK v2.0.

Extends the base CostTracking model with rich attribution and reporting capabilities.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.base import CostTracking, PrincipalBudget


class CostAttributionRecord(BaseModel):
    """
    Pydantic model for cost attribution records.

    Used for API responses and reporting.
    """

    timestamp: datetime
    principal_id: str
    resource_id: str
    capability_id: str
    estimated_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    provider: str | None = None
    model: str | None = None
    breakdown: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class BudgetStatus(BaseModel):
    """
    Budget status for a principal.
    """

    principal_id: str
    daily_budget: Decimal | None = None
    monthly_budget: Decimal | None = None
    daily_spent: Decimal = Decimal("0.00")
    monthly_spent: Decimal = Decimal("0.00")
    daily_remaining: Decimal | None = None
    monthly_remaining: Decimal | None = None
    daily_percent_used: float | None = None
    monthly_percent_used: float | None = None
    currency: str = "USD"

    class Config:
        from_attributes = True


class CostSummary(BaseModel):
    """
    Aggregated cost summary.
    """

    total_cost: Decimal
    record_count: int
    principal_id: str | None = None
    resource_id: str | None = None
    capability_id: str | None = None
    provider: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    breakdown: dict[str, Any] = Field(default_factory=dict)


class CostAttributionService:
    """
    Service for managing cost attribution and budget tracking.

    Provides methods for recording costs, checking budgets, and generating reports.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize cost attribution service.

        Args:
            db: Async database session
        """
        self.db = db

    async def record_cost(
        self,
        principal_id: str,
        resource_id: str,
        capability_id: str,
        estimated_cost: Decimal | None = None,
        actual_cost: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CostTracking:
        """
        Record a cost attribution entry.

        Args:
            principal_id: Principal who invoked the capability
            resource_id: Resource ID
            capability_id: Capability ID
            estimated_cost: Estimated cost
            actual_cost: Actual cost (if available)
            metadata: Additional metadata (provider, model, breakdown, etc.)

        Returns:
            Created cost tracking record
        """
        record = CostTracking(
            timestamp=datetime.now(UTC),
            principal_id=principal_id,
            resource_id=resource_id,
            capability_id=capability_id,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            metadata=metadata or {},
        )
        self.db.add(record)
        await self.db.flush()

        # Update principal budget spending
        await self._update_principal_spending(
            principal_id, actual_cost or estimated_cost or Decimal("0.00")
        )

        await self.db.commit()
        return record

    async def _update_principal_spending(self, principal_id: str, cost: Decimal) -> None:
        """
        Update principal's daily and monthly spending.

        Args:
            principal_id: Principal ID
            cost: Cost to add
        """
        # Get or create budget record
        budget = await self.db.get(PrincipalBudget, principal_id)
        if not budget:
            budget = PrincipalBudget(
                principal_id=principal_id,
                daily_spent=Decimal("0.00"),
                monthly_spent=Decimal("0.00"),
            )
            self.db.add(budget)
            await self.db.flush()

        # Check if we need to reset daily/monthly counters
        now = datetime.now(UTC)

        # Daily reset
        if budget.last_daily_reset:
            days_since_reset = (now - budget.last_daily_reset).days
            if days_since_reset >= 1:
                budget.daily_spent = Decimal("0.00")
                budget.last_daily_reset = now
        else:
            budget.last_daily_reset = now

        # Monthly reset (simple: reset on day 1 of month)
        if budget.last_monthly_reset:
            if (
                now.month != budget.last_monthly_reset.month
                or now.year != budget.last_monthly_reset.year
            ):
                budget.monthly_spent = Decimal("0.00")
                budget.last_monthly_reset = now
        else:
            budget.last_monthly_reset = now

        # Add cost
        budget.daily_spent += cost
        budget.monthly_spent += cost

    async def check_budget(
        self, principal_id: str, estimated_cost: Decimal
    ) -> tuple[bool, str | None]:
        """
        Check if a principal has sufficient budget for an operation.

        Args:
            principal_id: Principal ID
            estimated_cost: Estimated cost of the operation

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        budget = await self.db.get(PrincipalBudget, principal_id)
        if not budget:
            # No budget constraints
            return True, None

        # Check daily budget
        if budget.daily_budget is not None:
            if budget.daily_spent + estimated_cost > budget.daily_budget:
                return (
                    False,
                    f"Daily budget exceeded (limit: {budget.daily_budget} {budget.currency})",
                )

        # Check monthly budget
        if budget.monthly_budget is not None:
            if budget.monthly_spent + estimated_cost > budget.monthly_budget:
                return (
                    False,
                    f"Monthly budget exceeded (limit: {budget.monthly_budget} {budget.currency})",
                )

        return True, None

    async def get_budget_status(self, principal_id: str) -> BudgetStatus | None:
        """
        Get budget status for a principal.

        Args:
            principal_id: Principal ID

        Returns:
            BudgetStatus or None if no budget exists
        """
        budget = await self.db.get(PrincipalBudget, principal_id)
        if not budget:
            return None

        # Calculate remaining budgets
        daily_remaining = None
        monthly_remaining = None
        daily_percent = None
        monthly_percent = None

        if budget.daily_budget is not None:
            daily_remaining = budget.daily_budget - budget.daily_spent
            daily_percent = (
                float(budget.daily_spent / budget.daily_budget * 100)
                if budget.daily_budget > 0
                else 0.0
            )

        if budget.monthly_budget is not None:
            monthly_remaining = budget.monthly_budget - budget.monthly_spent
            monthly_percent = (
                float(budget.monthly_spent / budget.monthly_budget * 100)
                if budget.monthly_budget > 0
                else 0.0
            )

        return BudgetStatus(
            principal_id=principal_id,
            daily_budget=budget.daily_budget,
            monthly_budget=budget.monthly_budget,
            daily_spent=budget.daily_spent,
            monthly_spent=budget.monthly_spent,
            daily_remaining=daily_remaining,
            monthly_remaining=monthly_remaining,
            daily_percent_used=daily_percent,
            monthly_percent_used=monthly_percent,
            currency=budget.currency,
        )

    async def get_cost_summary(
        self,
        principal_id: str | None = None,
        resource_id: str | None = None,
        capability_id: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> CostSummary:
        """
        Get aggregated cost summary with optional filters.

        Args:
            principal_id: Filter by principal
            resource_id: Filter by resource
            capability_id: Filter by capability
            period_start: Start of time period
            period_end: End of time period

        Returns:
            Cost summary
        """
        query = select(
            func.sum(func.coalesce(CostTracking.actual_cost, CostTracking.estimated_cost)).label(
                "total"
            ),
            func.count(CostTracking.id).label("count"),
        )

        # Apply filters
        if principal_id:
            query = query.where(CostTracking.principal_id == principal_id)
        if resource_id:
            query = query.where(CostTracking.resource_id == resource_id)
        if capability_id:
            query = query.where(CostTracking.capability_id == capability_id)
        if period_start:
            query = query.where(CostTracking.timestamp >= period_start)
        if period_end:
            query = query.where(CostTracking.timestamp <= period_end)

        result = await self.db.execute(query)
        row = result.one()

        total_cost = row.total or Decimal("0.00")
        record_count = row.count or 0

        return CostSummary(
            total_cost=total_cost,
            record_count=record_count,
            principal_id=principal_id,
            resource_id=resource_id,
            capability_id=capability_id,
            period_start=period_start,
            period_end=period_end,
        )

    async def set_budget(
        self,
        principal_id: str,
        daily_budget: Decimal | None = None,
        monthly_budget: Decimal | None = None,
        currency: str = "USD",
    ) -> PrincipalBudget:
        """
        Set or update budget for a principal.

        Args:
            principal_id: Principal ID
            daily_budget: Daily budget limit
            monthly_budget: Monthly budget limit
            currency: Currency code

        Returns:
            Updated budget record
        """
        budget = await self.db.get(PrincipalBudget, principal_id)
        if not budget:
            budget = PrincipalBudget(
                principal_id=principal_id,
                daily_spent=Decimal("0.00"),
                monthly_spent=Decimal("0.00"),
                currency=currency,
            )
            self.db.add(budget)

        if daily_budget is not None:
            budget.daily_budget = daily_budget
        if monthly_budget is not None:
            budget.monthly_budget = monthly_budget
        if currency:
            budget.currency = currency

        await self.db.commit()
        await self.db.refresh(budget)
        return budget


__all__ = [
    "BudgetStatus",
    "CostAttributionRecord",
    "CostAttributionService",
    "CostSummary",
]
