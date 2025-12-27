"""Unit tests for Cost Tracker."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from sark.models.base import InvocationRequest, InvocationResult
from sark.services.cost.estimator import CostEstimate, FixedCostEstimator, NoCostEstimator
from sark.services.cost.tracker import CostTracker


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def cost_tracker(mock_db):
    """Create cost tracker instance."""
    return CostTracker(db=mock_db)


@pytest.fixture
def sample_request():
    """Create sample invocation request."""
    return InvocationRequest(
        principal_id="user123",
        capability_id="cap_abc",
        resource_id="res_001",
        arguments={"messages": [{"role": "user", "content": "Hello"}]},
    )


@pytest.fixture
def sample_result():
    """Create sample invocation result."""
    return InvocationResult(
        invocation_id="inv_123",
        success=True,
        duration_ms=100,
        metadata={"usage": {"input_tokens": 10, "output_tokens": 20}},
    )


class TestCostTrackerInitialization:
    """Test cost tracker initialization."""

    def test_initialization(self, mock_db):
        """Test that cost tracker initializes with default estimators."""
        tracker = CostTracker(db=mock_db)

        assert tracker.db == mock_db
        assert tracker.attribution_service is not None
        assert "openai" in tracker._estimators
        assert "anthropic" in tracker._estimators
        assert "free" in tracker._estimators

    def test_has_openai_estimator(self, cost_tracker):
        """Test that OpenAI estimator is registered by default."""
        estimator = cost_tracker.get_estimator("openai")
        assert estimator is not None
        assert estimator.provider_name == "openai"

    def test_has_anthropic_estimator(self, cost_tracker):
        """Test that Anthropic estimator is registered by default."""
        estimator = cost_tracker.get_estimator("anthropic")
        assert estimator is not None
        assert estimator.provider_name == "anthropic"

    def test_has_free_estimator(self, cost_tracker):
        """Test that free estimator is registered by default."""
        estimator = cost_tracker.get_estimator("free")
        assert estimator is not None
        assert estimator.provider_name == "free"


class TestRegisterEstimator:
    """Test custom estimator registration."""

    def test_register_custom_estimator(self, cost_tracker):
        """Test registering a custom cost estimator."""
        custom_estimator = FixedCostEstimator(cost_per_call=Decimal("0.50"), provider="custom")

        cost_tracker.register_estimator("custom", custom_estimator)

        assert "custom" in cost_tracker._estimators
        assert cost_tracker.get_estimator("custom") == custom_estimator

    def test_register_overrides_existing(self, cost_tracker):
        """Test that registering an estimator overrides existing one."""
        new_free_estimator = FixedCostEstimator(cost_per_call=Decimal("0.01"), provider="free")

        cost_tracker.register_estimator("free", new_free_estimator)

        estimator = cost_tracker.get_estimator("free")
        assert estimator == new_free_estimator


class TestGetEstimator:
    """Test getting estimators."""

    def test_get_existing_estimator(self, cost_tracker):
        """Test getting an existing estimator."""
        estimator = cost_tracker.get_estimator("openai")
        assert estimator is not None

    def test_get_nonexistent_estimator(self, cost_tracker):
        """Test getting a non-existent estimator returns None."""
        estimator = cost_tracker.get_estimator("nonexistent")
        assert estimator is None


class TestEstimateInvocationCost:
    """Test invocation cost estimation."""

    @pytest.mark.asyncio
    async def test_estimate_cost_with_provider(self, cost_tracker, sample_request):
        """Test estimating cost with specified provider."""
        metadata = {"provider": "free"}

        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        assert isinstance(estimate, CostEstimate)
        assert estimate.provider == "free"
        assert estimate.estimated_cost == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_estimate_cost_with_cost_provider(self, cost_tracker, sample_request):
        """Test estimating cost with cost_provider metadata."""
        metadata = {"cost_provider": "free"}

        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        assert estimate.provider == "free"

    @pytest.mark.asyncio
    async def test_estimate_cost_default_to_free(self, cost_tracker, sample_request):
        """Test that missing provider defaults to free."""
        metadata = {}

        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        assert estimate.estimated_cost == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_estimate_cost_unknown_provider_uses_free(self, cost_tracker, sample_request):
        """Test that unknown provider falls back to free estimator."""
        metadata = {"provider": "unknown_provider"}

        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        assert estimate.estimated_cost == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_estimate_cost_handles_estimator_error(self, cost_tracker, sample_request):
        """Test that estimation errors are handled gracefully."""
        # Register an estimator that will raise an error
        bad_estimator = Mock()
        bad_estimator.estimate_cost = AsyncMock(side_effect=Exception("Estimation failed"))
        cost_tracker.register_estimator("bad", bad_estimator)

        metadata = {"provider": "bad"}

        # Should return zero cost estimate on error
        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        assert estimate.estimated_cost == Decimal("0.00")
        assert "error" in estimate.metadata
        assert estimate.metadata["fallback"] is True


class TestCheckBudgetBeforeInvocation:
    """Test budget checking before invocation."""

    @pytest.mark.asyncio
    async def test_budget_check_allowed(self, cost_tracker, sample_request):
        """Test budget check when budget is sufficient."""
        metadata = {"provider": "free"}

        # Mock attribution service to allow
        cost_tracker.attribution_service.check_budget = AsyncMock(return_value=(True, None))

        allowed, reason = await cost_tracker.check_budget_before_invocation(sample_request, metadata)

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_budget_check_denied(self, cost_tracker, sample_request):
        """Test budget check when budget is exceeded."""
        metadata = {"provider": "openai", "model": "gpt-4"}

        # Mock attribution service to deny
        cost_tracker.attribution_service.check_budget = AsyncMock(
            return_value=(False, "Budget exceeded")
        )

        allowed, reason = await cost_tracker.check_budget_before_invocation(sample_request, metadata)

        assert allowed is False
        assert reason == "Budget exceeded"

    @pytest.mark.asyncio
    async def test_budget_check_calls_attribution_service(self, cost_tracker, sample_request):
        """Test that budget check calls attribution service correctly."""
        metadata = {"provider": "free"}
        cost_tracker.attribution_service.check_budget = AsyncMock(return_value=(True, None))

        await cost_tracker.check_budget_before_invocation(sample_request, metadata)

        cost_tracker.attribution_service.check_budget.assert_called_once()
        call_args = cost_tracker.attribution_service.check_budget.call_args
        assert call_args[0][0] == sample_request.principal_id
        assert isinstance(call_args[0][1], Decimal)


class TestRecordInvocationCost:
    """Test recording invocation costs."""

    @pytest.mark.asyncio
    async def test_record_cost_with_actual_usage(self, cost_tracker, sample_request, sample_result):
        """Test recording cost with actual usage data."""
        metadata = {"provider": "anthropic", "model": "claude-3-haiku-20240307"}
        resource_id = "res_001"

        # Mock attribution service
        cost_tracker.attribution_service.record_cost = AsyncMock()

        await cost_tracker.record_invocation_cost(
            sample_request, sample_result, resource_id, metadata
        )

        # Should have called record_cost
        cost_tracker.attribution_service.record_cost.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_cost_without_usage_data(self, cost_tracker, sample_request):
        """Test recording cost when no usage data available."""
        result = InvocationResult(
            invocation_id="inv_123", success=True, duration_ms=100, metadata={}
        )
        metadata = {"provider": "free"}
        resource_id = "res_001"

        cost_tracker.attribution_service.record_cost = AsyncMock()

        await cost_tracker.record_invocation_cost(sample_request, result, resource_id, metadata)

        # Should still record estimated cost
        cost_tracker.attribution_service.record_cost.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_cost_handles_errors(self, cost_tracker, sample_request, sample_result):
        """Test that recording errors are handled gracefully."""
        metadata = {"provider": "free"}
        resource_id = "res_001"

        # Mock attribution service to raise error
        cost_tracker.attribution_service.record_cost = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Should not raise exception
        await cost_tracker.record_invocation_cost(
            sample_request, sample_result, resource_id, metadata
        )

    @pytest.mark.asyncio
    async def test_record_cost_with_unknown_provider(self, cost_tracker, sample_request, sample_result):
        """Test recording cost with unknown provider."""
        metadata = {"provider": "unknown"}
        resource_id = "res_001"

        cost_tracker.attribution_service.record_cost = AsyncMock()

        await cost_tracker.record_invocation_cost(
            sample_request, sample_result, resource_id, metadata
        )

        # Should use NoCostEstimator as fallback
        cost_tracker.attribution_service.record_cost.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_cost_includes_metadata(self, cost_tracker, sample_request, sample_result):
        """Test that recorded cost includes provider metadata."""
        metadata = {"provider": "anthropic", "model": "claude-3-haiku-20240307"}
        resource_id = "res_001"

        cost_tracker.attribution_service.record_cost = AsyncMock()

        await cost_tracker.record_invocation_cost(
            sample_request, sample_result, resource_id, metadata
        )

        call_args = cost_tracker.attribution_service.record_cost.call_args
        recorded_metadata = call_args[1]["metadata"]

        assert "provider" in recorded_metadata
        assert recorded_metadata["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_record_actual_cost_when_available(self, cost_tracker, sample_request, sample_result):
        """Test that actual cost is used when available from result."""
        metadata = {"provider": "anthropic", "model": "claude-3-haiku-20240307"}
        resource_id = "res_001"

        cost_tracker.attribution_service.record_cost = AsyncMock()

        await cost_tracker.record_invocation_cost(
            sample_request, sample_result, resource_id, metadata
        )

        call_args = cost_tracker.attribution_service.record_cost.call_args
        actual_cost = call_args[1].get("actual_cost")

        # Anthropic estimator supports actual cost extraction
        assert actual_cost is not None


class TestCostTrackerIntegration:
    """Test cost tracker integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_cost_tracking_flow(self, cost_tracker, sample_request):
        """Test complete cost tracking flow."""
        metadata = {"provider": "free"}
        resource_id = "res_001"

        # Mock attribution service
        cost_tracker.attribution_service.check_budget = AsyncMock(return_value=(True, None))
        cost_tracker.attribution_service.record_cost = AsyncMock()

        # 1. Check budget
        allowed, reason = await cost_tracker.check_budget_before_invocation(sample_request, metadata)
        assert allowed is True

        # 2. Record cost after invocation
        result = InvocationResult(invocation_id="inv_123", success=True, duration_ms=50, metadata={})
        await cost_tracker.record_invocation_cost(sample_request, result, resource_id, metadata)

        # Verify both calls happened
        cost_tracker.attribution_service.check_budget.assert_called_once()
        cost_tracker.attribution_service.record_cost.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_provider_support(self, cost_tracker, sample_request):
        """Test tracking costs across multiple providers."""
        providers = ["openai", "anthropic", "free"]

        for provider in providers:
            metadata = {"provider": provider}
            estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)
            assert estimate.provider in [provider, "free"]  # free is fallback

    @pytest.mark.asyncio
    async def test_custom_estimator_integration(self, cost_tracker, sample_request):
        """Test using a custom registered estimator."""
        # Register custom estimator
        custom = FixedCostEstimator(cost_per_call=Decimal("1.50"), provider="custom_api")
        cost_tracker.register_estimator("custom_api", custom)

        metadata = {"provider": "custom_api"}
        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        assert estimate.estimated_cost == Decimal("1.50")
        assert estimate.provider == "custom_api"
