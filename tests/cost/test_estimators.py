"""
Tests for cost estimators (OpenAI, Anthropic, etc.).
"""

import pytest
from decimal import Decimal

from sark.models.base import InvocationRequest, InvocationResult
from sark.services.cost.estimator import (
    NoCostEstimator,
    FixedCostEstimator,
    CostEstimationError,
)
from sark.services.cost.providers.openai import OpenAICostEstimator
from sark.services.cost.providers.anthropic import AnthropicCostEstimator


class TestNoCostEstimator:
    """Test the free/no-cost estimator."""

    @pytest.mark.asyncio
    async def test_always_returns_zero(self):
        """Test that NoCostEstimator always returns zero cost."""
        estimator = NoCostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={"prompt": "Hello, world!"},
        )

        estimate = await estimator.estimate_cost(request, {})

        assert estimate.estimated_cost == Decimal("0.00")
        assert estimate.provider == "free"


class TestFixedCostEstimator:
    """Test the fixed-cost estimator."""

    @pytest.mark.asyncio
    async def test_returns_fixed_cost(self):
        """Test that FixedCostEstimator returns the configured cost."""
        estimator = FixedCostEstimator(
            cost_per_call=Decimal("0.50"),
            provider="custom-api"
        )

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={},
        )

        estimate = await estimator.estimate_cost(request, {})

        assert estimate.estimated_cost == Decimal("0.50")
        assert estimate.provider == "custom-api"
        assert estimate.breakdown["cost_per_call"] == "0.50"


class TestOpenAICostEstimator:
    """Test OpenAI cost estimator."""

    @pytest.mark.asyncio
    async def test_estimate_chat_completion_cost(self):
        """Test estimating cost for chat completion."""
        estimator = OpenAICostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "messages": [
                    {"role": "user", "content": "What is the capital of France?"}
                ],
                "max_tokens": 100,
            },
        )

        resource_metadata = {"model": "gpt-4"}

        estimate = await estimator.estimate_cost(request, resource_metadata)

        assert estimate.estimated_cost > Decimal("0.00")
        assert estimate.provider == "openai"
        assert estimate.model == "gpt-4"
        assert "input_tokens" in estimate.breakdown
        assert "output_tokens" in estimate.breakdown

    @pytest.mark.asyncio
    async def test_estimate_multiple_messages(self):
        """Test estimating cost with multiple messages."""
        estimator = OpenAICostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Tell me about Python."},
                    {"role": "assistant", "content": "Python is a programming language."},
                    {"role": "user", "content": "What are its main features?"},
                ],
                "max_tokens": 500,
            },
        )

        resource_metadata = {"model": "gpt-3.5-turbo"}

        estimate = await estimator.estimate_cost(request, resource_metadata)

        assert estimate.estimated_cost > Decimal("0.00")
        assert estimate.breakdown["input_tokens"] > 0

    @pytest.mark.asyncio
    async def test_estimate_embeddings(self):
        """Test estimating cost for embeddings."""
        estimator = OpenAICostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "input": ["Hello world", "Goodbye world"],
            },
        )

        resource_metadata = {"model": "text-embedding-3-small"}

        estimate = await estimator.estimate_cost(request, resource_metadata)

        assert estimate.estimated_cost >= Decimal("0.00")
        assert estimate.model == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_missing_model_raises_error(self):
        """Test that missing model raises error."""
        estimator = OpenAICostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={"messages": [{"role": "user", "content": "Hi"}]},
        )

        with pytest.raises(CostEstimationError) as exc_info:
            await estimator.estimate_cost(request, {})

        assert "Missing 'model'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_actual_cost_from_usage(self):
        """Test extracting actual cost from API response."""
        estimator = OpenAICostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={"messages": [{"role": "user", "content": "Hi"}]},
        )

        result = InvocationResult(
            success=True,
            result={"content": "Hello!"},
            metadata={
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                }
            },
            duration_ms=500.0,
        )

        resource_metadata = {"model": "gpt-4"}

        actual_estimate = await estimator.record_actual_cost(
            request, result, resource_metadata
        )

        assert actual_estimate is not None
        assert actual_estimate.estimated_cost > Decimal("0.00")
        assert actual_estimate.breakdown["input_tokens"] == 10
        assert actual_estimate.breakdown["output_tokens"] == 20
        assert actual_estimate.breakdown["actual"] is True

    @pytest.mark.asyncio
    async def test_unknown_model_uses_default_pricing(self):
        """Test that unknown models use default pricing."""
        estimator = OpenAICostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 100,
            },
        )

        resource_metadata = {"model": "gpt-99-ultra-mega"}

        estimate = await estimator.estimate_cost(request, resource_metadata)

        # Should still return an estimate using default pricing
        assert estimate.estimated_cost > Decimal("0.00")


class TestAnthropicCostEstimator:
    """Test Anthropic (Claude) cost estimator."""

    @pytest.mark.asyncio
    async def test_estimate_messages_api_cost(self):
        """Test estimating cost for Claude Messages API."""
        estimator = AnthropicCostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "messages": [
                    {"role": "user", "content": "What is quantum computing?"}
                ],
                "max_tokens": 1024,
            },
        )

        resource_metadata = {"model": "claude-3-5-sonnet-20241022"}

        estimate = await estimator.estimate_cost(request, resource_metadata)

        assert estimate.estimated_cost > Decimal("0.00")
        assert estimate.provider == "anthropic"
        assert estimate.model == "claude-3-5-sonnet-20241022"
        assert "input_tokens" in estimate.breakdown
        assert "output_tokens" in estimate.breakdown

    @pytest.mark.asyncio
    async def test_estimate_with_system_message(self):
        """Test estimating with system message."""
        estimator = AnthropicCostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "system": "You are a helpful AI assistant specializing in physics.",
                "messages": [
                    {"role": "user", "content": "Explain relativity."}
                ],
                "max_tokens": 2000,
            },
        )

        resource_metadata = {"model": "claude-3-opus-20240229"}

        estimate = await estimator.estimate_cost(request, resource_metadata)

        assert estimate.estimated_cost > Decimal("0.00")
        # System message should contribute to input tokens
        assert estimate.breakdown["input_tokens"] > 0

    @pytest.mark.asyncio
    async def test_record_actual_cost_from_usage(self):
        """Test extracting actual cost from Claude API response."""
        estimator = AnthropicCostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 100,
            },
        )

        result = InvocationResult(
            success=True,
            result={"content": [{"type": "text", "text": "Hello!"}]},
            metadata={
                "usage": {
                    "input_tokens": 15,
                    "output_tokens": 8,
                }
            },
            duration_ms=400.0,
        )

        resource_metadata = {"model": "claude-3-haiku-20240307"}

        actual_estimate = await estimator.record_actual_cost(
            request, result, resource_metadata
        )

        assert actual_estimate is not None
        assert actual_estimate.estimated_cost > Decimal("0.00")
        assert actual_estimate.breakdown["input_tokens"] == 15
        assert actual_estimate.breakdown["output_tokens"] == 8
        assert actual_estimate.breakdown["actual"] is True

    @pytest.mark.asyncio
    async def test_missing_model_raises_error(self):
        """Test that missing model raises error."""
        estimator = AnthropicCostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={"messages": [{"role": "user", "content": "Hi"}]},
        )

        with pytest.raises(CostEstimationError) as exc_info:
            await estimator.estimate_cost(request, {})

        assert "Missing 'model'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_haiku_cheaper_than_opus(self):
        """Test that Haiku is cheaper than Opus for same input."""
        estimator = AnthropicCostEstimator()

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={
                "messages": [{"role": "user", "content": "Test message"}],
                "max_tokens": 100,
            },
        )

        haiku_estimate = await estimator.estimate_cost(
            request, {"model": "claude-3-haiku-20240307"}
        )

        opus_estimate = await estimator.estimate_cost(
            request, {"model": "claude-3-opus-20240229"}
        )

        assert haiku_estimate.estimated_cost < opus_estimate.estimated_cost


class TestCostEstimatorCapabilities:
    """Test cost estimator capability detection."""

    def test_no_cost_estimator_does_not_support_actual(self):
        """Test that NoCostEstimator doesn't support actual cost."""
        estimator = NoCostEstimator()
        assert estimator.supports_actual_cost() is False

    def test_openai_estimator_supports_actual(self):
        """Test that OpenAI estimator supports actual cost."""
        estimator = OpenAICostEstimator()
        assert estimator.supports_actual_cost() is True

    def test_anthropic_estimator_supports_actual(self):
        """Test that Anthropic estimator supports actual cost."""
        estimator = AnthropicCostEstimator()
        assert estimator.supports_actual_cost() is True

    def test_get_estimator_info(self):
        """Test getting estimator metadata."""
        estimator = OpenAICostEstimator()
        info = estimator.get_estimator_info()

        assert info["provider_name"] == "openai"
        assert info["supports_actual_cost"] is True
        assert "estimator_class" in info
