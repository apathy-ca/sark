"""Unit tests for cost calculation functionality.

These tests cover:
- Cost estimation interface
- Provider-specific cost estimation
- Budget tracking and checking
- Cost attribution

Following AAA pattern: Arrange, Act, Assert
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from sark.models.base import InvocationRequest, InvocationResult
from sark.services.cost.estimator import (
    CostEstimate,
    CostEstimationError,
    CostEstimator,
    FixedCostEstimator,
    NoCostEstimator,
)


@pytest.fixture
def sample_request():
    """Create sample invocation request."""
    return InvocationRequest(
        principal_id="user_123",
        capability_id="cap_llm_001",
        resource_id="res_openai",
        arguments={"messages": [{"role": "user", "content": "Hello, world!"}]},
    )


@pytest.fixture
def sample_result():
    """Create sample invocation result."""
    return InvocationResult(
        invocation_id="inv_abc123",
        success=True,
        duration_ms=150,
        metadata={
            "usage": {
                "input_tokens": 10,
                "output_tokens": 50,
            }
        },
    )


class TestCostEstimate:
    """Test CostEstimate dataclass."""

    def test_create_cost_estimate(self):
        """Test creating a cost estimate."""
        # Arrange & Act
        estimate = CostEstimate(
            estimated_cost=Decimal("0.0015"),
            currency="USD",
            provider="openai",
            model="gpt-4",
            breakdown={"input_tokens": 10, "output_tokens": 50},
        )

        # Assert
        assert estimate.estimated_cost == Decimal("0.0015")
        assert estimate.currency == "USD"
        assert estimate.provider == "openai"
        assert estimate.model == "gpt-4"
        assert estimate.breakdown["input_tokens"] == 10

    def test_cost_estimate_default_values(self):
        """Test CostEstimate default values."""
        # Arrange & Act
        estimate = CostEstimate(estimated_cost=Decimal("1.00"))

        # Assert
        assert estimate.currency == "USD"
        assert estimate.provider is None
        assert estimate.breakdown == {}
        assert estimate.metadata == {}

    def test_cost_estimate_breakdown_initialization(self):
        """Test breakdown is properly initialized when None."""
        # Arrange & Act
        estimate = CostEstimate(
            estimated_cost=Decimal("0.50"),
            breakdown=None,
        )

        # Assert
        assert estimate.breakdown == {}


class TestNoCostEstimator:
    """Test NoCostEstimator for free resources."""

    @pytest.mark.asyncio
    async def test_provider_name(self):
        """Test NoCostEstimator has correct provider name."""
        # Arrange
        estimator = NoCostEstimator()

        # Act & Assert
        assert estimator.provider_name == "free"

    @pytest.mark.asyncio
    async def test_estimate_returns_zero_cost(self, sample_request):
        """Test NoCostEstimator returns zero cost."""
        # Arrange
        estimator = NoCostEstimator()
        metadata = {}

        # Act
        estimate = await estimator.estimate_cost(sample_request, metadata)

        # Assert
        assert estimate.estimated_cost == Decimal("0.00")
        assert estimate.provider == "free"

    @pytest.mark.asyncio
    async def test_does_not_support_actual_cost(self):
        """Test NoCostEstimator does not support actual cost extraction."""
        # Arrange
        estimator = NoCostEstimator()

        # Act & Assert
        assert estimator.supports_actual_cost() is False


class TestFixedCostEstimator:
    """Test FixedCostEstimator for flat-rate APIs."""

    @pytest.mark.asyncio
    async def test_provider_name(self):
        """Test FixedCostEstimator has configurable provider name."""
        # Arrange
        estimator = FixedCostEstimator(
            cost_per_call=Decimal("0.10"),
            provider="custom_api",
        )

        # Act & Assert
        assert estimator.provider_name == "custom_api"

    @pytest.mark.asyncio
    async def test_estimate_returns_fixed_cost(self, sample_request):
        """Test FixedCostEstimator returns configured fixed cost."""
        # Arrange
        estimator = FixedCostEstimator(
            cost_per_call=Decimal("0.25"),
            provider="premium_api",
        )
        metadata = {}

        # Act
        estimate = await estimator.estimate_cost(sample_request, metadata)

        # Assert
        assert estimate.estimated_cost == Decimal("0.25")
        assert estimate.provider == "premium_api"

    @pytest.mark.asyncio
    async def test_estimate_breakdown_includes_cost_per_call(self, sample_request):
        """Test FixedCostEstimator breakdown includes cost_per_call."""
        # Arrange
        estimator = FixedCostEstimator(
            cost_per_call=Decimal("1.00"),
            provider="expensive_api",
        )
        metadata = {}

        # Act
        estimate = await estimator.estimate_cost(sample_request, metadata)

        # Assert
        assert "cost_per_call" in estimate.breakdown
        assert estimate.breakdown["call_count"] == 1


class TestCostEstimatorInterface:
    """Test CostEstimator abstract interface."""

    def test_estimator_info(self):
        """Test get_estimator_info returns correct metadata."""
        # Arrange
        estimator = NoCostEstimator()

        # Act
        info = estimator.get_estimator_info()

        # Assert
        assert info["provider_name"] == "free"
        assert info["estimator_class"] == "NoCostEstimator"
        assert info["supports_actual_cost"] is False

    def test_supports_actual_cost_default(self):
        """Test supports_actual_cost returns False by default."""
        # Arrange
        estimator = FixedCostEstimator(cost_per_call=Decimal("0.10"))

        # Act & Assert
        assert estimator.supports_actual_cost() is False


class TestCostEstimationError:
    """Test CostEstimationError exception."""

    def test_error_with_provider(self):
        """Test CostEstimationError includes provider information."""
        # Arrange & Act
        error = CostEstimationError(
            message="Failed to estimate cost",
            provider="openai",
        )

        # Assert
        assert str(error) == "Failed to estimate cost"
        assert error.provider == "openai"

    def test_error_with_metadata(self):
        """Test CostEstimationError includes additional metadata."""
        # Arrange & Act
        error = CostEstimationError(
            message="Model not found",
            provider="anthropic",
            model="claude-4",
            request_id="req_123",
        )

        # Assert
        assert error.metadata["model"] == "claude-4"
        assert error.metadata["request_id"] == "req_123"


class TestCostTrackerIntegration:
    """Test CostTracker integration with estimators."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def cost_tracker(self, mock_db):
        """Create cost tracker instance."""
        from sark.services.cost.tracker import CostTracker

        return CostTracker(db=mock_db)

    @pytest.mark.asyncio
    async def test_tracker_has_default_estimators(self, cost_tracker):
        """Test CostTracker has default estimators registered."""
        # Assert
        assert cost_tracker.get_estimator("openai") is not None
        assert cost_tracker.get_estimator("anthropic") is not None
        assert cost_tracker.get_estimator("free") is not None

    @pytest.mark.asyncio
    async def test_tracker_estimate_with_openai(self, cost_tracker, sample_request):
        """Test cost estimation with OpenAI provider."""
        # Arrange
        metadata = {
            "provider": "openai",
            "model": "gpt-4",
        }

        # Act
        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        # Assert
        assert isinstance(estimate, CostEstimate)
        assert estimate.provider in ["openai", "free"]  # May fall back to free

    @pytest.mark.asyncio
    async def test_tracker_estimate_with_anthropic(self, cost_tracker, sample_request):
        """Test cost estimation with Anthropic provider."""
        # Arrange
        metadata = {
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
        }

        # Act
        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        # Assert
        assert isinstance(estimate, CostEstimate)
        assert estimate.provider in ["anthropic", "free"]

    @pytest.mark.asyncio
    async def test_tracker_estimate_unknown_provider_fallback(
        self, cost_tracker, sample_request
    ):
        """Test cost estimation falls back to free for unknown provider."""
        # Arrange
        metadata = {"provider": "unknown_provider"}

        # Act
        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        # Assert
        assert estimate.estimated_cost == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_tracker_register_custom_estimator(self, cost_tracker, sample_request):
        """Test registering a custom cost estimator."""
        # Arrange
        custom_estimator = FixedCostEstimator(
            cost_per_call=Decimal("2.50"),
            provider="custom_llm",
        )
        cost_tracker.register_estimator("custom_llm", custom_estimator)

        metadata = {"provider": "custom_llm"}

        # Act
        estimate = await cost_tracker.estimate_invocation_cost(sample_request, metadata)

        # Assert
        assert estimate.estimated_cost == Decimal("2.50")
        assert estimate.provider == "custom_llm"


class TestBudgetChecking:
    """Test budget checking functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def cost_tracker(self, mock_db):
        """Create cost tracker instance."""
        from sark.services.cost.tracker import CostTracker

        return CostTracker(db=mock_db)

    @pytest.mark.asyncio
    async def test_check_budget_allowed(self, cost_tracker, sample_request):
        """Test budget check when budget is sufficient."""
        # Arrange
        metadata = {"provider": "free"}
        cost_tracker.attribution_service.check_budget = AsyncMock(return_value=(True, None))

        # Act
        allowed, reason = await cost_tracker.check_budget_before_invocation(
            sample_request, metadata
        )

        # Assert
        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_check_budget_exceeded(self, cost_tracker, sample_request):
        """Test budget check when budget is exceeded."""
        # Arrange
        metadata = {"provider": "openai", "model": "gpt-4"}
        cost_tracker.attribution_service.check_budget = AsyncMock(
            return_value=(False, "Daily budget exceeded")
        )

        # Act
        allowed, reason = await cost_tracker.check_budget_before_invocation(
            sample_request, metadata
        )

        # Assert
        assert allowed is False
        assert "budget" in reason.lower()


class TestCostRecording:
    """Test cost recording functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def cost_tracker(self, mock_db):
        """Create cost tracker instance."""
        from sark.services.cost.tracker import CostTracker

        return CostTracker(db=mock_db)

    @pytest.mark.asyncio
    async def test_record_cost_calls_attribution_service(
        self, cost_tracker, sample_request, sample_result
    ):
        """Test recording cost calls attribution service."""
        # Arrange
        metadata = {"provider": "free"}
        resource_id = "res_001"
        cost_tracker.attribution_service.record_cost = AsyncMock()

        # Act
        await cost_tracker.record_invocation_cost(
            sample_request, sample_result, resource_id, metadata
        )

        # Assert
        cost_tracker.attribution_service.record_cost.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_cost_handles_errors_gracefully(
        self, cost_tracker, sample_request, sample_result
    ):
        """Test recording cost handles errors without raising."""
        # Arrange
        metadata = {"provider": "openai"}
        resource_id = "res_001"
        cost_tracker.attribution_service.record_cost = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act - Should not raise
        await cost_tracker.record_invocation_cost(
            sample_request, sample_result, resource_id, metadata
        )

        # Assert - No exception raised


class TestCostCalculationPrecision:
    """Test cost calculation uses correct precision."""

    def test_cost_estimate_uses_decimal(self):
        """Test CostEstimate uses Decimal for precision."""
        # Arrange & Act
        estimate = CostEstimate(estimated_cost=Decimal("0.00001"))

        # Assert
        assert isinstance(estimate.estimated_cost, Decimal)

    def test_cost_estimate_preserves_precision(self):
        """Test CostEstimate preserves decimal precision."""
        # Arrange
        very_small_cost = Decimal("0.00000123")

        # Act
        estimate = CostEstimate(estimated_cost=very_small_cost)

        # Assert
        assert estimate.estimated_cost == Decimal("0.00000123")

    def test_fixed_estimator_uses_decimal(self):
        """Test FixedCostEstimator uses Decimal correctly."""
        # Arrange
        cost = Decimal("0.00015")
        estimator = FixedCostEstimator(cost_per_call=cost)

        # Assert
        assert estimator._cost_per_call == Decimal("0.00015")
