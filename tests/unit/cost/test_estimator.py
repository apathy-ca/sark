"""Unit tests for Cost Estimator."""

from decimal import Decimal
from unittest.mock import Mock

import pytest

from sark.models.base import InvocationRequest
from sark.services.cost.estimator import (
    CostEstimate,
    CostEstimationError,
    CostEstimator,
    FixedCostEstimator,
    NoCostEstimator,
)


@pytest.fixture
def sample_request():
    """Create a sample invocation request."""
    return InvocationRequest(
        principal_id="user123",
        capability_id="cap_abc",
        arguments={"query": "test"},
        resource_id="res_001",
    )


@pytest.fixture
def sample_metadata():
    """Create sample resource metadata."""
    return {"provider": "test", "model": "gpt-4"}


class TestCostEstimate:
    """Test CostEstimate dataclass."""

    def test_cost_estimate_creation(self):
        """Test creating a cost estimate with required fields."""
        estimate = CostEstimate(
            estimated_cost=Decimal("0.50"),
            currency="USD",
            provider="openai",
            model="gpt-4",
        )

        assert estimate.estimated_cost == Decimal("0.50")
        assert estimate.currency == "USD"
        assert estimate.provider == "openai"
        assert estimate.model == "gpt-4"

    def test_cost_estimate_defaults(self):
        """Test that cost estimate initializes empty dicts for optional fields."""
        estimate = CostEstimate(estimated_cost=Decimal("1.00"))

        assert estimate.breakdown == {}
        assert estimate.metadata == {}

    def test_cost_estimate_with_breakdown(self):
        """Test cost estimate with breakdown."""
        breakdown = {"input_tokens": 100, "output_tokens": 50}
        estimate = CostEstimate(estimated_cost=Decimal("0.25"), breakdown=breakdown)

        assert estimate.breakdown == breakdown

    def test_cost_estimate_with_metadata(self):
        """Test cost estimate with metadata."""
        metadata = {"model_version": "2024-01", "region": "us-east-1"}
        estimate = CostEstimate(estimated_cost=Decimal("0.10"), metadata=metadata)

        assert estimate.metadata == metadata


class TestNoCostEstimator:
    """Test NoCostEstimator for free resources."""

    @pytest.mark.asyncio
    async def test_provider_name(self):
        """Test that NoCostEstimator has correct provider name."""
        estimator = NoCostEstimator()
        assert estimator.provider_name == "free"

    @pytest.mark.asyncio
    async def test_estimate_cost_returns_zero(self, sample_request, sample_metadata):
        """Test that NoCostEstimator returns zero cost."""
        estimator = NoCostEstimator()
        estimate = await estimator.estimate_cost(sample_request, sample_metadata)

        assert estimate.estimated_cost == Decimal("0.00")
        assert estimate.currency == "USD"
        assert estimate.provider == "free"

    @pytest.mark.asyncio
    async def test_estimate_cost_includes_message(self, sample_request, sample_metadata):
        """Test that NoCostEstimator includes a message in breakdown."""
        estimator = NoCostEstimator()
        estimate = await estimator.estimate_cost(sample_request, sample_metadata)

        assert "message" in estimate.breakdown
        assert estimate.breakdown["message"] == "No cost for this resource"

    @pytest.mark.asyncio
    async def test_supports_actual_cost(self):
        """Test that NoCostEstimator doesn't support actual cost extraction."""
        estimator = NoCostEstimator()
        # Default implementation returns None
        assert not estimator.supports_actual_cost() or estimator.supports_actual_cost() is False

    @pytest.mark.asyncio
    async def test_get_estimator_info(self):
        """Test getting estimator information."""
        estimator = NoCostEstimator()
        info = estimator.get_estimator_info()

        assert info["provider_name"] == "free"
        assert info["estimator_class"] == "NoCostEstimator"
        assert "supports_actual_cost" in info
        assert "module" in info


class TestFixedCostEstimator:
    """Test FixedCostEstimator for fixed-rate resources."""

    def test_initialization(self):
        """Test FixedCostEstimator initialization."""
        cost = Decimal("0.10")
        estimator = FixedCostEstimator(cost_per_call=cost, provider="fixed_api")

        assert estimator.provider_name == "fixed_api"

    def test_default_provider_name(self):
        """Test default provider name."""
        estimator = FixedCostEstimator(cost_per_call=Decimal("0.05"))
        assert estimator.provider_name == "fixed"

    @pytest.mark.asyncio
    async def test_estimate_cost(self, sample_request, sample_metadata):
        """Test estimating fixed cost."""
        cost_per_call = Decimal("0.25")
        estimator = FixedCostEstimator(cost_per_call=cost_per_call)

        estimate = await estimator.estimate_cost(sample_request, sample_metadata)

        assert estimate.estimated_cost == cost_per_call
        assert estimate.currency == "USD"
        assert estimate.provider == "fixed"

    @pytest.mark.asyncio
    async def test_estimate_cost_breakdown(self, sample_request, sample_metadata):
        """Test that fixed cost estimate includes breakdown."""
        cost_per_call = Decimal("1.50")
        estimator = FixedCostEstimator(cost_per_call=cost_per_call, provider="api_xyz")

        estimate = await estimator.estimate_cost(sample_request, sample_metadata)

        assert "cost_per_call" in estimate.breakdown
        assert "call_count" in estimate.breakdown
        assert estimate.breakdown["cost_per_call"] == str(cost_per_call)
        assert estimate.breakdown["call_count"] == 1

    @pytest.mark.asyncio
    async def test_different_cost_values(self, sample_request, sample_metadata):
        """Test fixed estimator with different cost values."""
        test_costs = [Decimal("0.01"), Decimal("1.00"), Decimal("10.50"), Decimal("100.00")]

        for cost in test_costs:
            estimator = FixedCostEstimator(cost_per_call=cost)
            estimate = await estimator.estimate_cost(sample_request, sample_metadata)
            assert estimate.estimated_cost == cost

    @pytest.mark.asyncio
    async def test_get_estimator_info(self):
        """Test getting fixed estimator information."""
        estimator = FixedCostEstimator(cost_per_call=Decimal("0.50"), provider="test_api")
        info = estimator.get_estimator_info()

        assert info["provider_name"] == "test_api"
        assert info["estimator_class"] == "FixedCostEstimator"


class TestCostEstimationError:
    """Test CostEstimationError exception."""

    def test_error_creation(self):
        """Test creating a cost estimation error."""
        error = CostEstimationError("Failed to estimate cost")
        assert str(error) == "Failed to estimate cost"

    def test_error_with_provider(self):
        """Test error with provider information."""
        error = CostEstimationError("API error", provider="openai")
        assert error.provider == "openai"

    def test_error_with_metadata(self):
        """Test error with metadata."""
        error = CostEstimationError(
            "Model not found", provider="anthropic", model="claude-5", region="us-west"
        )
        assert error.metadata["model"] == "claude-5"
        assert error.metadata["region"] == "us-west"

    def test_error_raised(self):
        """Test that error can be raised and caught."""
        with pytest.raises(CostEstimationError) as exc_info:
            raise CostEstimationError("Test error", provider="test")

        assert "Test error" in str(exc_info.value)
        assert exc_info.value.provider == "test"


class TestCostEstimatorBaseClass:
    """Test CostEstimator abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that CostEstimator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CostEstimator()

    def test_subclass_must_implement_provider_name(self):
        """Test that subclasses must implement provider_name."""

        class IncompleteEstimator(CostEstimator):
            async def estimate_cost(self, request, metadata):
                return CostEstimate(estimated_cost=Decimal("0"))

        with pytest.raises(TypeError):
            IncompleteEstimator()

    def test_subclass_must_implement_estimate_cost(self):
        """Test that subclasses must implement estimate_cost."""

        class IncompleteEstimator(CostEstimator):
            @property
            def provider_name(self):
                return "test"

        with pytest.raises(TypeError):
            IncompleteEstimator()

    @pytest.mark.asyncio
    async def test_record_actual_cost_default_implementation(self, sample_request, sample_metadata):
        """Test default implementation of record_actual_cost."""

        class MinimalEstimator(CostEstimator):
            @property
            def provider_name(self):
                return "minimal"

            async def estimate_cost(self, request, metadata):
                return CostEstimate(estimated_cost=Decimal("1.00"))

        estimator = MinimalEstimator()
        result = Mock()
        actual_cost = await estimator.record_actual_cost(sample_request, result, sample_metadata)

        assert actual_cost is None

    def test_supports_actual_cost_default(self):
        """Test supports_actual_cost for default implementation."""

        class DefaultEstimator(CostEstimator):
            @property
            def provider_name(self):
                return "default"

            async def estimate_cost(self, request, metadata):
                return CostEstimate(estimated_cost=Decimal("0.50"))

        estimator = DefaultEstimator()
        # Default implementation doesn't support actual cost
        assert not estimator.supports_actual_cost()

    def test_supports_actual_cost_custom_implementation(self):
        """Test supports_actual_cost for custom implementation."""

        class CustomEstimator(CostEstimator):
            @property
            def provider_name(self):
                return "custom"

            async def estimate_cost(self, request, metadata):
                return CostEstimate(estimated_cost=Decimal("0.75"))

            async def record_actual_cost(self, request, result, metadata):
                return CostEstimate(estimated_cost=Decimal("0.80"))

        estimator = CustomEstimator()
        # Custom implementation supports actual cost
        assert estimator.supports_actual_cost()

    def test_get_estimator_info_includes_all_fields(self):
        """Test that get_estimator_info returns all expected fields."""

        class TestEstimator(CostEstimator):
            @property
            def provider_name(self):
                return "test"

            async def estimate_cost(self, request, metadata):
                return CostEstimate(estimated_cost=Decimal("1.00"))

        estimator = TestEstimator()
        info = estimator.get_estimator_info()

        assert "provider_name" in info
        assert "estimator_class" in info
        assert "supports_actual_cost" in info
        assert "module" in info
        assert info["provider_name"] == "test"
        assert info["estimator_class"] == "TestEstimator"
