"""
Cost calculator service for home LLM usage.

Provides cost estimation based on configurable provider rates.
Supports OpenAI, Anthropic, Google, and Mistral pricing.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.analytics import ProviderPricing

logger = structlog.get_logger(__name__)


@dataclass
class ProviderRate:
    """Pricing rate for a provider/model combination."""

    provider: str
    model: str
    prompt_per_1m: Decimal
    response_per_1m: Decimal
    currency: str = "USD"


# Default pricing rates (as of January 2025)
# Format: "provider:model" -> ProviderRate
DEFAULT_RATES: dict[str, ProviderRate] = {
    # OpenAI
    "openai:gpt-4-turbo": ProviderRate(
        "openai", "gpt-4-turbo", Decimal("10.00"), Decimal("30.00")
    ),
    "openai:gpt-4": ProviderRate(
        "openai", "gpt-4", Decimal("30.00"), Decimal("60.00")
    ),
    "openai:gpt-4o": ProviderRate(
        "openai", "gpt-4o", Decimal("2.50"), Decimal("10.00")
    ),
    "openai:gpt-4o-mini": ProviderRate(
        "openai", "gpt-4o-mini", Decimal("0.15"), Decimal("0.60")
    ),
    "openai:gpt-3.5-turbo": ProviderRate(
        "openai", "gpt-3.5-turbo", Decimal("0.50"), Decimal("1.50")
    ),
    "openai:o1-preview": ProviderRate(
        "openai", "o1-preview", Decimal("15.00"), Decimal("60.00")
    ),
    "openai:o1-mini": ProviderRate(
        "openai", "o1-mini", Decimal("3.00"), Decimal("12.00")
    ),
    # Anthropic
    "anthropic:claude-3-opus": ProviderRate(
        "anthropic", "claude-3-opus", Decimal("15.00"), Decimal("75.00")
    ),
    "anthropic:claude-3-sonnet": ProviderRate(
        "anthropic", "claude-3-sonnet", Decimal("3.00"), Decimal("15.00")
    ),
    "anthropic:claude-3.5-sonnet": ProviderRate(
        "anthropic", "claude-3.5-sonnet", Decimal("3.00"), Decimal("15.00")
    ),
    "anthropic:claude-3-haiku": ProviderRate(
        "anthropic", "claude-3-haiku", Decimal("0.25"), Decimal("1.25")
    ),
    "anthropic:claude-3.5-haiku": ProviderRate(
        "anthropic", "claude-3.5-haiku", Decimal("0.80"), Decimal("4.00")
    ),
    # Google
    "google:gemini-1.5-pro": ProviderRate(
        "google", "gemini-1.5-pro", Decimal("1.25"), Decimal("5.00")
    ),
    "google:gemini-1.5-flash": ProviderRate(
        "google", "gemini-1.5-flash", Decimal("0.075"), Decimal("0.30")
    ),
    "google:gemini-2.0-flash": ProviderRate(
        "google", "gemini-2.0-flash", Decimal("0.10"), Decimal("0.40")
    ),
    # Mistral
    "mistral:mistral-large": ProviderRate(
        "mistral", "mistral-large", Decimal("2.00"), Decimal("6.00")
    ),
    "mistral:mistral-small": ProviderRate(
        "mistral", "mistral-small", Decimal("0.20"), Decimal("0.60")
    ),
    "mistral:codestral": ProviderRate(
        "mistral", "codestral", Decimal("0.20"), Decimal("0.60")
    ),
    "mistral:mixtral-8x7b": ProviderRate(
        "mistral", "mixtral-8x7b", Decimal("0.45"), Decimal("0.70")
    ),
    # Default fallback
    "default:default": ProviderRate(
        "default", "default", Decimal("5.00"), Decimal("15.00")
    ),
}


class CostCalculatorService:
    """
    Service for calculating estimated costs from token usage.

    Uses configurable provider rates stored in the database, with
    fallback to default rates.
    """

    def __init__(
        self,
        db: AsyncSession | None = None,
        rates: dict[str, ProviderRate] | None = None,
    ) -> None:
        """
        Initialize cost calculator service.

        Args:
            db: Optional async database session for custom rates
            rates: Optional custom rates dictionary
        """
        self.db = db
        self._rates = rates or DEFAULT_RATES.copy()
        self._db_rates_loaded = False

    async def _load_db_rates(self) -> None:
        """Load pricing rates from database."""
        if not self.db or self._db_rates_loaded:
            return

        try:
            result = await self.db.execute(select(ProviderPricing))
            for pricing in result.scalars():
                key = f"{pricing.provider}:{pricing.model}"
                self._rates[key] = ProviderRate(
                    provider=pricing.provider,
                    model=pricing.model,
                    prompt_per_1m=pricing.prompt_per_1m,
                    response_per_1m=pricing.response_per_1m,
                    currency=pricing.currency,
                )
            self._db_rates_loaded = True
            logger.debug(
                "cost_rates_loaded_from_db",
                rate_count=len(self._rates),
            )
        except Exception as e:
            logger.warning(
                "cost_rates_db_load_failed",
                error=str(e),
                using_defaults=True,
            )

    def _get_rate(self, provider: str, model: str) -> ProviderRate:
        """
        Get pricing rate for a provider/model combination.

        Args:
            provider: Provider name (e.g., "openai")
            model: Model name (e.g., "gpt-4")

        Returns:
            ProviderRate with pricing information
        """
        # Normalize
        provider_lower = provider.lower()
        model_lower = model.lower()
        key = f"{provider_lower}:{model_lower}"

        # Exact match
        if key in self._rates:
            return self._rates[key]

        # Try prefix match for versioned models
        for rate_key, rate in self._rates.items():
            if rate_key.startswith(f"{provider_lower}:") and model_lower.startswith(
                rate.model.lower()
            ):
                return rate

        # Provider default
        provider_default = f"{provider_lower}:default"
        if provider_default in self._rates:
            return self._rates[provider_default]

        # Global default
        logger.warning(
            "cost_rate_not_found",
            provider=provider,
            model=model,
            using_default=True,
        )
        return self._rates["default:default"]

    async def estimate(
        self,
        tokens_prompt: int,
        tokens_response: int,
        provider: str,
        model: str,
    ) -> dict[str, Any]:
        """
        Estimate cost for token usage.

        Args:
            tokens_prompt: Number of prompt/input tokens
            tokens_response: Number of response/output tokens
            provider: LLM provider (e.g., "openai", "anthropic")
            model: Model name (e.g., "gpt-4", "claude-3-opus")

        Returns:
            Dictionary with cost estimate and breakdown
        """
        await self._load_db_rates()

        rate = self._get_rate(provider, model)

        prompt_cost = (Decimal(tokens_prompt) / Decimal(1_000_000)) * rate.prompt_per_1m
        response_cost = (
            Decimal(tokens_response) / Decimal(1_000_000)
        ) * rate.response_per_1m
        total_cost = prompt_cost + response_cost

        return {
            "cost_usd": float(total_cost),
            "currency": rate.currency,
            "provider": provider,
            "model": model,
            "breakdown": {
                "prompt_tokens": tokens_prompt,
                "response_tokens": tokens_response,
                "prompt_cost": float(prompt_cost),
                "response_cost": float(response_cost),
            },
            "rate": {
                "prompt_per_1m": float(rate.prompt_per_1m),
                "response_per_1m": float(rate.response_per_1m),
            },
        }

    async def estimate_from_text(
        self,
        prompt_text: str,
        expected_response_tokens: int | None = None,
        provider: str = "openai",
        model: str = "gpt-4",
    ) -> dict[str, Any]:
        """
        Estimate cost from text input.

        Uses rough token estimation (~4 chars per token).

        Args:
            prompt_text: Input prompt text
            expected_response_tokens: Expected response tokens (default: 50% of prompt)
            provider: LLM provider
            model: Model name

        Returns:
            Dictionary with cost estimate
        """
        # Rough token estimation
        prompt_tokens = max(1, len(prompt_text) // 4)

        if expected_response_tokens is None:
            expected_response_tokens = max(100, int(prompt_tokens * 0.5))

        return await self.estimate(
            tokens_prompt=prompt_tokens,
            tokens_response=expected_response_tokens,
            provider=provider,
            model=model,
        )

    async def get_rates(self, provider: str | None = None) -> list[dict[str, Any]]:
        """
        Get all configured pricing rates.

        Args:
            provider: Optional provider to filter by

        Returns:
            List of rate dictionaries
        """
        await self._load_db_rates()

        rates = []
        for key, rate in self._rates.items():
            if provider and rate.provider.lower() != provider.lower():
                continue
            rates.append(
                {
                    "provider": rate.provider,
                    "model": rate.model,
                    "prompt_per_1m": float(rate.prompt_per_1m),
                    "response_per_1m": float(rate.response_per_1m),
                    "currency": rate.currency,
                }
            )

        return sorted(rates, key=lambda r: (r["provider"], r["model"]))

    async def set_rate(
        self,
        provider: str,
        model: str,
        prompt_per_1m: Decimal,
        response_per_1m: Decimal,
        currency: str = "USD",
        notes: str | None = None,
    ) -> ProviderPricing | None:
        """
        Set or update a pricing rate in the database.

        Args:
            provider: Provider name
            model: Model name
            prompt_per_1m: Cost per 1M prompt tokens
            response_per_1m: Cost per 1M response tokens
            currency: Currency code
            notes: Optional notes about the rate

        Returns:
            Updated or created ProviderPricing record, or None if no DB
        """
        if not self.db:
            # Update in-memory only
            key = f"{provider.lower()}:{model.lower()}"
            self._rates[key] = ProviderRate(
                provider=provider,
                model=model,
                prompt_per_1m=prompt_per_1m,
                response_per_1m=response_per_1m,
                currency=currency,
            )
            logger.info(
                "cost_rate_updated_in_memory",
                provider=provider,
                model=model,
            )
            return None

        # Check for existing
        result = await self.db.execute(
            select(ProviderPricing).where(
                ProviderPricing.provider == provider.lower(),
                ProviderPricing.model == model.lower(),
            )
        )
        pricing = result.scalar_one_or_none()

        if pricing:
            pricing.prompt_per_1m = prompt_per_1m
            pricing.response_per_1m = response_per_1m
            pricing.currency = currency
            pricing.notes = notes
            pricing.effective_date = datetime.now(UTC)
        else:
            pricing = ProviderPricing(
                provider=provider.lower(),
                model=model.lower(),
                prompt_per_1m=prompt_per_1m,
                response_per_1m=response_per_1m,
                currency=currency,
                notes=notes,
            )
            self.db.add(pricing)

        await self.db.commit()
        await self.db.refresh(pricing)

        # Update in-memory cache
        key = f"{provider.lower()}:{model.lower()}"
        self._rates[key] = ProviderRate(
            provider=provider,
            model=model,
            prompt_per_1m=prompt_per_1m,
            response_per_1m=response_per_1m,
            currency=currency,
        )

        logger.info(
            "cost_rate_updated",
            provider=provider,
            model=model,
            prompt_per_1m=str(prompt_per_1m),
            response_per_1m=str(response_per_1m),
        )

        return pricing

    async def calculate_period_cost(
        self,
        usage_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculate total cost for a period from usage data.

        Args:
            usage_data: List of usage records with tokens and provider/model info

        Returns:
            Dictionary with total cost and breakdown by provider
        """
        await self._load_db_rates()

        total_cost = Decimal("0")
        by_provider: dict[str, Decimal] = {}
        by_model: dict[str, Decimal] = {}

        for usage in usage_data:
            estimate = await self.estimate(
                tokens_prompt=usage.get("tokens_prompt", 0),
                tokens_response=usage.get("tokens_response", 0),
                provider=usage.get("provider", "unknown"),
                model=usage.get("model", "unknown"),
            )

            cost = Decimal(str(estimate["cost_usd"]))
            total_cost += cost

            provider = usage.get("provider", "unknown")
            model = usage.get("model", "unknown")

            by_provider[provider] = by_provider.get(provider, Decimal("0")) + cost
            by_model[f"{provider}:{model}"] = (
                by_model.get(f"{provider}:{model}", Decimal("0")) + cost
            )

        return {
            "total_cost_usd": float(total_cost),
            "currency": "USD",
            "by_provider": {k: float(v) for k, v in by_provider.items()},
            "by_model": {k: float(v) for k, v in by_model.items()},
            "record_count": len(usage_data),
        }


__all__ = ["CostCalculatorService", "ProviderRate", "DEFAULT_RATES"]
