"""
Tests for cost attribution service.

Tests budget tracking, cost recording, and reporting.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from sark.db.base import Base
from sark.models.base import CostTracking, PrincipalBudget
from sark.models.cost_attribution import (
    CostAttributionService,
)

# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session_maker = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def cost_service(db_session):
    """Create cost attribution service."""
    return CostAttributionService(db_session)


class TestCostRecording:
    """Test cost recording functionality."""

    @pytest.mark.asyncio
    async def test_record_cost(self, cost_service, db_session):
        """Test basic cost recording."""
        record = await cost_service.record_cost(
            principal_id="user-123",
            resource_id="resource-456",
            capability_id="capability-789",
            estimated_cost=Decimal("0.05"),
            actual_cost=Decimal("0.048"),
            metadata={"provider": "openai", "model": "gpt-4"},
        )

        assert record.principal_id == "user-123"
        assert record.resource_id == "resource-456"
        assert record.capability_id == "capability-789"
        assert record.estimated_cost == Decimal("0.05")
        assert record.actual_cost == Decimal("0.048")
        assert record.metadata["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_record_cost_without_actual(self, cost_service):
        """Test recording estimated cost only."""
        record = await cost_service.record_cost(
            principal_id="user-123",
            resource_id="resource-456",
            capability_id="capability-789",
            estimated_cost=Decimal("0.05"),
        )

        assert record.estimated_cost == Decimal("0.05")
        assert record.actual_cost is None

    @pytest.mark.asyncio
    async def test_record_multiple_costs(self, cost_service):
        """Test recording multiple costs."""
        for i in range(5):
            await cost_service.record_cost(
                principal_id="user-123",
                resource_id="resource-456",
                capability_id=f"capability-{i}",
                estimated_cost=Decimal("0.01") * (i + 1),
            )

        # Verify budget was updated
        status = await cost_service.get_budget_status("user-123")
        assert status is not None
        assert status.daily_spent == Decimal("0.15")  # 0.01 + 0.02 + 0.03 + 0.04 + 0.05


class TestBudgetManagement:
    """Test budget management functionality."""

    @pytest.mark.asyncio
    async def test_set_budget(self, cost_service):
        """Test setting principal budget."""
        budget = await cost_service.set_budget(
            principal_id="user-123",
            daily_budget=Decimal("10.00"),
            monthly_budget=Decimal("300.00"),
        )

        assert budget.principal_id == "user-123"
        assert budget.daily_budget == Decimal("10.00")
        assert budget.monthly_budget == Decimal("300.00")
        assert budget.daily_spent == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_check_budget_within_limits(self, cost_service):
        """Test budget check when within limits."""
        await cost_service.set_budget(
            principal_id="user-123",
            daily_budget=Decimal("10.00"),
        )

        allowed, reason = await cost_service.check_budget(
            principal_id="user-123",
            estimated_cost=Decimal("5.00"),
        )

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_check_budget_exceeds_daily(self, cost_service):
        """Test budget check when exceeding daily limit."""
        await cost_service.set_budget(
            principal_id="user-123",
            daily_budget=Decimal("10.00"),
        )

        # Spend close to limit
        await cost_service.record_cost(
            principal_id="user-123",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("9.00"),
        )

        # Try to exceed
        allowed, reason = await cost_service.check_budget(
            principal_id="user-123",
            estimated_cost=Decimal("2.00"),
        )

        assert allowed is False
        assert "Daily budget exceeded" in reason

    @pytest.mark.asyncio
    async def test_check_budget_exceeds_monthly(self, cost_service):
        """Test budget check when exceeding monthly limit."""
        await cost_service.set_budget(
            principal_id="user-123",
            monthly_budget=Decimal("100.00"),
        )

        # Spend close to limit
        await cost_service.record_cost(
            principal_id="user-123",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("99.00"),
        )

        # Try to exceed
        allowed, reason = await cost_service.check_budget(
            principal_id="user-123",
            estimated_cost=Decimal("2.00"),
        )

        assert allowed is False
        assert "Monthly budget exceeded" in reason

    @pytest.mark.asyncio
    async def test_get_budget_status(self, cost_service):
        """Test retrieving budget status."""
        await cost_service.set_budget(
            principal_id="user-123",
            daily_budget=Decimal("10.00"),
            monthly_budget=Decimal("300.00"),
        )

        await cost_service.record_cost(
            principal_id="user-123",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("3.00"),
        )

        status = await cost_service.get_budget_status("user-123")

        assert status.daily_budget == Decimal("10.00")
        assert status.monthly_budget == Decimal("300.00")
        assert status.daily_spent == Decimal("3.00")
        assert status.daily_remaining == Decimal("7.00")
        assert status.daily_percent_used == 30.0

    @pytest.mark.asyncio
    async def test_no_budget_constraints(self, cost_service):
        """Test operations without budget constraints."""
        # No budget set
        allowed, reason = await cost_service.check_budget(
            principal_id="user-999",
            estimated_cost=Decimal("1000.00"),
        )

        assert allowed is True
        assert reason is None


class TestCostReporting:
    """Test cost reporting and summaries."""

    @pytest.mark.asyncio
    async def test_get_cost_summary_by_principal(self, cost_service):
        """Test cost summary filtered by principal."""
        # Record costs for multiple principals
        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("1.00"),
        )
        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-1",
            capability_id="cap-2",
            estimated_cost=Decimal("2.00"),
        )
        await cost_service.record_cost(
            principal_id="user-2",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("5.00"),
        )

        summary = await cost_service.get_cost_summary(principal_id="user-1")

        assert summary.total_cost == Decimal("3.00")
        assert summary.record_count == 2
        assert summary.principal_id == "user-1"

    @pytest.mark.asyncio
    async def test_get_cost_summary_by_resource(self, cost_service):
        """Test cost summary filtered by resource."""
        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-A",
            capability_id="cap-1",
            estimated_cost=Decimal("1.50"),
        )
        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-A",
            capability_id="cap-2",
            estimated_cost=Decimal("2.50"),
        )
        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-B",
            capability_id="cap-1",
            estimated_cost=Decimal("10.00"),
        )

        summary = await cost_service.get_cost_summary(resource_id="resource-A")

        assert summary.total_cost == Decimal("4.00")
        assert summary.record_count == 2

    @pytest.mark.asyncio
    async def test_get_cost_summary_by_time_period(self, cost_service, db_session):
        """Test cost summary filtered by time period."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)

        # Create old cost record manually
        old_record = CostTracking(
            timestamp=yesterday,
            principal_id="user-1",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("100.00"),
        )
        db_session.add(old_record)
        await db_session.commit()

        # Create recent cost
        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("5.00"),
        )

        # Query for today only
        summary = await cost_service.get_cost_summary(
            period_start=now.replace(hour=0, minute=0, second=0),
        )

        assert summary.total_cost == Decimal("5.00")
        assert summary.record_count == 1

    @pytest.mark.asyncio
    async def test_get_cost_summary_no_records(self, cost_service):
        """Test cost summary with no records."""
        summary = await cost_service.get_cost_summary(principal_id="nonexistent")

        assert summary.total_cost == Decimal("0.00")
        assert summary.record_count == 0


class TestBudgetReset:
    """Test budget reset functionality."""

    @pytest.mark.asyncio
    async def test_daily_budget_reset(self, cost_service, db_session):
        """Test that daily budget resets after 24 hours."""
        # Set budget and spend some
        await cost_service.set_budget(
            principal_id="user-1",
            daily_budget=Decimal("10.00"),
        )

        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-1",
            capability_id="cap-1",
            estimated_cost=Decimal("5.00"),
        )

        # Manually set last reset to yesterday
        budget = await db_session.get(PrincipalBudget, "user-1")
        budget.last_daily_reset = datetime.now(UTC) - timedelta(days=1)
        await db_session.commit()

        # Record new cost (should trigger reset)
        await cost_service.record_cost(
            principal_id="user-1",
            resource_id="resource-1",
            capability_id="cap-2",
            estimated_cost=Decimal("2.00"),
        )

        status = await cost_service.get_budget_status("user-1")
        assert status.daily_spent == Decimal("2.00")  # Reset, only new cost counted
