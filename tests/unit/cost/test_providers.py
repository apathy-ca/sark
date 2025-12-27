"""Unit tests for Cost Provider Estimators (Anthropic and OpenAI)."""

from decimal import Decimal
from unittest.mock import Mock

import pytest

from sark.models.base import InvocationRequest, InvocationResult
from sark.services.cost.estimator import CostEstimationError
from sark.services.cost.providers.anthropic import ANTHROPIC_PRICING, AnthropicCostEstimator
from sark.services.cost.providers.openai import OPENAI_PRICING, OpenAICostEstimator


@pytest.fixture
def anthropic_estimator():
    """Create Anthropic cost estimator."""
    return AnthropicCostEstimator()


@pytest.fixture
def openai_estimator():
    """Create OpenAI cost estimator."""
    return OpenAICostEstimator()


class TestAnthropicCostEstimator:
    """Test Anthropic cost estimator."""

    def test_provider_name(self, anthropic_estimator):
        """Test that provider name is correct."""
        assert anthropic_estimator.provider_name == "anthropic"

    def test_get_pricing_exact_match(self, anthropic_estimator):
        """Test pricing retrieval for exact model match."""
        input_price, output_price = anthropic_estimator._get_pricing("claude-3-5-sonnet-20241022")
        assert input_price == Decimal("3.00")
        assert output_price == Decimal("15.00")

    def test_get_pricing_opus_model(self, anthropic_estimator):
        """Test pricing for Claude Opus model."""
        input_price, output_price = anthropic_estimator._get_pricing("claude-3-opus-20240229")
        assert input_price == Decimal("15.00")
        assert output_price == Decimal("75.00")

    def test_get_pricing_haiku_model(self, anthropic_estimator):
        """Test pricing for Claude Haiku model."""
        input_price, output_price = anthropic_estimator._get_pricing("claude-3-haiku-20240307")
        assert input_price == Decimal("0.25")
        assert output_price == Decimal("1.25")

    def test_get_pricing_default_fallback(self, anthropic_estimator):
        """Test default pricing for unknown model."""
        input_price, output_price = anthropic_estimator._get_pricing("claude-99-unknown")
        assert input_price == ANTHROPIC_PRICING["default"][0]
        assert output_price == ANTHROPIC_PRICING["default"][1]

    def test_estimate_tokens(self, anthropic_estimator):
        """Test token estimation heuristic."""
        # Simple heuristic: 4 characters per token
        assert anthropic_estimator._estimate_tokens("test") == 1  # 4 chars = 1 token
        assert anthropic_estimator._estimate_tokens("hello world") == 2  # 11 chars ~= 2 tokens
        assert anthropic_estimator._estimate_tokens("a" * 100) == 25  # 100 chars = 25 tokens

    def test_estimate_tokens_minimum(self, anthropic_estimator):
        """Test that token estimation has minimum of 1."""
        assert anthropic_estimator._estimate_tokens("") == 1
        assert anthropic_estimator._estimate_tokens("a") == 1

    @pytest.mark.asyncio
    async def test_estimate_cost_simple_message(self, anthropic_estimator):
        """Test cost estimation for simple message."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={"messages": [{"role": "user", "content": "Hello" * 100}]},
        )
        metadata = {"model": "claude-3-haiku-20240307"}

        estimate = await anthropic_estimator.estimate_cost(request, metadata)

        assert estimate.provider == "anthropic"
        assert estimate.model == "claude-3-haiku-20240307"
        assert estimate.estimated_cost > Decimal("0")
        assert "input_tokens" in estimate.breakdown
        assert "output_tokens" in estimate.breakdown

    @pytest.mark.asyncio
    async def test_estimate_cost_with_system_message(self, anthropic_estimator):
        """Test cost estimation with system message."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={
                "system": "You are a helpful assistant.",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        metadata = {"model": "claude-3-sonnet-20240229"}

        estimate = await anthropic_estimator.estimate_cost(request, metadata)

        assert estimate.breakdown["input_tokens"] > 0

    @pytest.mark.asyncio
    async def test_estimate_cost_complex_content(self, anthropic_estimator):
        """Test cost estimation with complex content blocks."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image"},
                            {"type": "image", "source": "..."},  # Image tokens not calculated
                        ],
                    }
                ],
            },
        )
        metadata = {"model": "claude-3-opus-20240229"}

        estimate = await anthropic_estimator.estimate_cost(request, metadata)

        assert estimate.breakdown["input_tokens"] > 0

    @pytest.mark.asyncio
    async def test_estimate_cost_missing_model(self, anthropic_estimator):
        """Test that missing model raises error."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={"messages": [{"role": "user", "content": "Hello"}]},
        )
        metadata = {}  # No model

        with pytest.raises(CostEstimationError) as exc_info:
            await anthropic_estimator.estimate_cost(request, metadata)

        assert "model" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_estimate_cost_missing_messages(self, anthropic_estimator):
        """Test that missing messages raises error."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={},  # No messages
        )
        metadata = {"model": "claude-3-haiku-20240307"}

        with pytest.raises(CostEstimationError) as exc_info:
            await anthropic_estimator.estimate_cost(request, metadata)

        assert "messages" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_record_actual_cost_from_usage(self, anthropic_estimator):
        """Test extracting actual cost from API response."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={"messages": [{"role": "user", "content": "Hello"}]},
        )
        result = InvocationResult(
            invocation_id="inv_123",
            success=True,
            duration_ms=100,
            metadata={"usage": {"input_tokens": 10, "output_tokens": 50}},
        )
        metadata = {"model": "claude-3-haiku-20240307"}

        actual = await anthropic_estimator.record_actual_cost(request, result, metadata)

        assert actual is not None
        assert actual.breakdown["input_tokens"] == 10
        assert actual.breakdown["output_tokens"] == 50
        assert actual.breakdown["actual"] is True

    @pytest.mark.asyncio
    async def test_record_actual_cost_no_usage_data(self, anthropic_estimator):
        """Test that missing usage data returns None."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={"messages": [{"role": "user", "content": "Hello"}]},
        )
        result = InvocationResult(invocation_id="inv_123", success=True, duration_ms=50, metadata={})
        metadata = {"model": "claude-3-haiku-20240307"}

        actual = await anthropic_estimator.record_actual_cost(request, result, metadata)

        assert actual is None

    def test_supports_actual_cost(self, anthropic_estimator):
        """Test that Anthropic estimator supports actual cost extraction."""
        assert anthropic_estimator.supports_actual_cost() is True


class TestOpenAICostEstimator:
    """Test OpenAI cost estimator."""

    def test_provider_name(self, openai_estimator):
        """Test that provider name is correct."""
        assert openai_estimator.provider_name == "openai"

    def test_get_pricing_gpt4_turbo(self, openai_estimator):
        """Test pricing for GPT-4 Turbo."""
        input_price, output_price = openai_estimator._get_pricing("gpt-4-turbo")
        assert input_price == Decimal("10.00")
        assert output_price == Decimal("30.00")

    def test_get_pricing_gpt4(self, openai_estimator):
        """Test pricing for GPT-4."""
        input_price, output_price = openai_estimator._get_pricing("gpt-4")
        assert input_price == Decimal("30.00")
        assert output_price == Decimal("60.00")

    def test_get_pricing_gpt35(self, openai_estimator):
        """Test pricing for GPT-3.5 Turbo."""
        input_price, output_price = openai_estimator._get_pricing("gpt-3.5-turbo")
        assert input_price == Decimal("0.50")
        assert output_price == Decimal("1.50")

    def test_get_pricing_o1_models(self, openai_estimator):
        """Test pricing for o1 models."""
        input_price, output_price = openai_estimator._get_pricing("o1-preview")
        assert input_price == Decimal("15.00")
        assert output_price == Decimal("60.00")

    def test_get_pricing_embeddings(self, openai_estimator):
        """Test pricing for embeddings model."""
        input_price, output_price = openai_estimator._get_pricing("text-embedding-3-small")
        assert input_price == Decimal("0.02")
        assert output_price == Decimal("0.00")  # No output cost for embeddings

    def test_estimate_tokens(self, openai_estimator):
        """Test token estimation heuristic."""
        assert openai_estimator._estimate_tokens("test") == 1
        assert openai_estimator._estimate_tokens("hello world") == 2
        assert openai_estimator._estimate_tokens("a" * 100) == 25

    @pytest.mark.asyncio
    async def test_estimate_cost_chat_completion(self, openai_estimator):
        """Test cost estimation for chat completion."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "How are you?"},
                ]
            },
        )
        metadata = {"model": "gpt-3.5-turbo"}

        estimate = await openai_estimator.estimate_cost(request, metadata)

        assert estimate.provider == "openai"
        assert estimate.model == "gpt-3.5-turbo"
        assert estimate.estimated_cost > Decimal("0")
        assert "input_tokens" in estimate.breakdown

    @pytest.mark.asyncio
    async def test_estimate_cost_with_max_tokens(self, openai_estimator):
        """Test cost estimation with explicit max_tokens."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 100},
        )
        metadata = {"model": "gpt-4"}

        estimate = await openai_estimator.estimate_cost(request, metadata)

        assert estimate.breakdown["output_tokens"] == 100

    @pytest.mark.asyncio
    async def test_estimate_cost_missing_model(self, openai_estimator):
        """Test that missing model raises error."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={"messages": [{"role": "user", "content": "Hello"}]},
        )
        metadata = {}

        with pytest.raises(CostEstimationError) as exc_info:
            await openai_estimator.estimate_cost(request, metadata)

        assert "model" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_record_actual_cost_from_usage(self, openai_estimator):
        """Test extracting actual cost from OpenAI response."""
        request = InvocationRequest(
            principal_id="user123",
            capability_id="cap_abc",
            resource_id="res_001",
            arguments={"messages": [{"role": "user", "content": "Hello"}]},
        )
        result = InvocationResult(
            invocation_id="inv_123",
            success=True,
            duration_ms=150,
            metadata={"usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}},
        )
        metadata = {"model": "gpt-4"}

        actual = await openai_estimator.record_actual_cost(request, result, metadata)

        assert actual is not None
        assert actual.breakdown["input_tokens"] == 15
        assert actual.breakdown["output_tokens"] == 25
        assert actual.breakdown["total_tokens"] == 40
        assert actual.breakdown["actual"] is True

    def test_supports_actual_cost(self, openai_estimator):
        """Test that OpenAI estimator supports actual cost extraction."""
        assert openai_estimator.supports_actual_cost() is True


class TestPricingData:
    """Test pricing data consistency."""

    def test_anthropic_pricing_structure(self):
        """Test that all Anthropic pricing entries have correct structure."""
        for model, pricing in ANTHROPIC_PRICING.items():
            assert isinstance(pricing, tuple)
            assert len(pricing) == 2
            assert isinstance(pricing[0], Decimal)
            assert isinstance(pricing[1], Decimal)

    def test_openai_pricing_structure(self):
        """Test that all OpenAI pricing entries have correct structure."""
        for model, pricing in OPENAI_PRICING.items():
            assert isinstance(pricing, tuple)
            assert len(pricing) == 2
            assert isinstance(pricing[0], Decimal)
            assert isinstance(pricing[1], Decimal)

    def test_anthropic_has_default_pricing(self):
        """Test that Anthropic pricing has default fallback."""
        assert "default" in ANTHROPIC_PRICING

    def test_openai_has_default_pricing(self):
        """Test that OpenAI pricing has default fallback."""
        assert "default" in OPENAI_PRICING
