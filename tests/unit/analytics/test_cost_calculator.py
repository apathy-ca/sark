"""Unit tests for CostCalculatorService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from sark.services.analytics.cost_calculator import (
    DEFAULT_RATES,
    CostCalculatorService,
    ProviderRate,
)


class TestCostCalculatorService:
    """Tests for CostCalculatorService."""

    @pytest.fixture
    def calculator(self) -> CostCalculatorService:
        """Create a cost calculator without DB."""
        return CostCalculatorService()

    @pytest.fixture
    def calculator_with_custom_rates(self) -> CostCalculatorService:
        """Create a cost calculator with custom rates."""
        custom_rates = {
            "test:test-model": ProviderRate(
                provider="test",
                model="test-model",
                prompt_per_1m=Decimal("1.00"),
                response_per_1m=Decimal("2.00"),
            ),
        }
        return CostCalculatorService(rates=custom_rates)

    @pytest.mark.asyncio
    async def test_estimate_openai_gpt4(self, calculator: CostCalculatorService) -> None:
        """Test cost estimation for OpenAI GPT-4."""
        result = await calculator.estimate(
            tokens_prompt=1000,
            tokens_response=500,
            provider="openai",
            model="gpt-4",
        )

        assert "cost_usd" in result
        assert result["cost_usd"] > 0
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4"
        assert "breakdown" in result
        assert result["breakdown"]["prompt_tokens"] == 1000
        assert result["breakdown"]["response_tokens"] == 500

    @pytest.mark.asyncio
    async def test_estimate_anthropic_claude(self, calculator: CostCalculatorService) -> None:
        """Test cost estimation for Anthropic Claude."""
        result = await calculator.estimate(
            tokens_prompt=1000,
            tokens_response=500,
            provider="anthropic",
            model="claude-3-sonnet",
        )

        assert result["cost_usd"] > 0
        assert result["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_estimate_unknown_model_uses_default(
        self, calculator: CostCalculatorService
    ) -> None:
        """Test that unknown models use default rate."""
        result = await calculator.estimate(
            tokens_prompt=1000,
            tokens_response=500,
            provider="unknown",
            model="unknown-model",
        )

        # Should still return a valid estimate using default rate
        assert result["cost_usd"] > 0

    @pytest.mark.asyncio
    async def test_estimate_zero_tokens(self, calculator: CostCalculatorService) -> None:
        """Test cost estimation with zero tokens."""
        result = await calculator.estimate(
            tokens_prompt=0,
            tokens_response=0,
            provider="openai",
            model="gpt-4",
        )

        assert result["cost_usd"] == 0

    @pytest.mark.asyncio
    async def test_estimate_with_custom_rates(
        self, calculator_with_custom_rates: CostCalculatorService
    ) -> None:
        """Test cost estimation with custom rates."""
        result = await calculator_with_custom_rates.estimate(
            tokens_prompt=1_000_000,
            tokens_response=1_000_000,
            provider="test",
            model="test-model",
        )

        # 1M tokens at $1/1M prompt + 1M tokens at $2/1M response = $3
        assert result["cost_usd"] == 3.0

    @pytest.mark.asyncio
    async def test_estimate_from_text(self, calculator: CostCalculatorService) -> None:
        """Test cost estimation from text."""
        result = await calculator.estimate_from_text(
            prompt_text="Hello, how are you today?",
            provider="openai",
            model="gpt-4",
        )

        assert result["cost_usd"] > 0
        assert "breakdown" in result

    @pytest.mark.asyncio
    async def test_get_rates(self, calculator: CostCalculatorService) -> None:
        """Test getting all rates."""
        rates = await calculator.get_rates()

        assert len(rates) > 0
        # Check structure
        for rate in rates:
            assert "provider" in rate
            assert "model" in rate
            assert "prompt_per_1m" in rate
            assert "response_per_1m" in rate

    @pytest.mark.asyncio
    async def test_get_rates_filtered_by_provider(
        self, calculator: CostCalculatorService
    ) -> None:
        """Test getting rates filtered by provider."""
        rates = await calculator.get_rates(provider="openai")

        assert len(rates) > 0
        for rate in rates:
            assert rate["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_calculate_period_cost(self, calculator: CostCalculatorService) -> None:
        """Test calculating cost for a period from usage data."""
        usage_data = [
            {
                "tokens_prompt": 1000,
                "tokens_response": 500,
                "provider": "openai",
                "model": "gpt-4",
            },
            {
                "tokens_prompt": 2000,
                "tokens_response": 1000,
                "provider": "anthropic",
                "model": "claude-3-sonnet",
            },
        ]

        result = await calculator.calculate_period_cost(usage_data)

        assert result["total_cost_usd"] > 0
        assert "by_provider" in result
        assert "openai" in result["by_provider"]
        assert "anthropic" in result["by_provider"]
        assert result["record_count"] == 2

    @pytest.mark.asyncio
    async def test_set_rate_in_memory(self, calculator: CostCalculatorService) -> None:
        """Test setting rate without database (in-memory only)."""
        result = await calculator.set_rate(
            provider="custom",
            model="custom-model",
            prompt_per_1m=Decimal("5.00"),
            response_per_1m=Decimal("10.00"),
        )

        # Without DB, returns None
        assert result is None

        # But the rate should be usable
        estimate = await calculator.estimate(
            tokens_prompt=1_000_000,
            tokens_response=1_000_000,
            provider="custom",
            model="custom-model",
        )

        assert estimate["cost_usd"] == 15.0


class TestDefaultRates:
    """Tests for default pricing rates."""

    def test_default_rates_have_openai(self) -> None:
        """Test that default rates include OpenAI models."""
        assert "openai:gpt-4" in DEFAULT_RATES
        assert "openai:gpt-3.5-turbo" in DEFAULT_RATES

    def test_default_rates_have_anthropic(self) -> None:
        """Test that default rates include Anthropic models."""
        assert "anthropic:claude-3-opus" in DEFAULT_RATES
        assert "anthropic:claude-3-sonnet" in DEFAULT_RATES

    def test_default_rates_have_google(self) -> None:
        """Test that default rates include Google models."""
        assert "google:gemini-1.5-pro" in DEFAULT_RATES
        assert "google:gemini-1.5-flash" in DEFAULT_RATES

    def test_default_rates_have_mistral(self) -> None:
        """Test that default rates include Mistral models."""
        assert "mistral:mistral-large" in DEFAULT_RATES

    def test_default_rates_have_fallback(self) -> None:
        """Test that default rates include a fallback."""
        assert "default:default" in DEFAULT_RATES

    def test_provider_rate_dataclass(self) -> None:
        """Test ProviderRate dataclass."""
        rate = ProviderRate(
            provider="test",
            model="test-model",
            prompt_per_1m=Decimal("1.00"),
            response_per_1m=Decimal("2.00"),
        )

        assert rate.provider == "test"
        assert rate.model == "test-model"
        assert rate.prompt_per_1m == Decimal("1.00")
        assert rate.response_per_1m == Decimal("2.00")
        assert rate.currency == "USD"
