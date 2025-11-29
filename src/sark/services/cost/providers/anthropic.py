"""
Anthropic cost estimator implementation.

Calculates costs based on Anthropic's token-based pricing model for Claude models.
Pricing data as of December 2024.
"""

from decimal import Decimal
from typing import Any, Dict, Optional
import structlog

from sark.models.base import InvocationRequest, InvocationResult
from sark.services.cost.estimator import CostEstimator, CostEstimate, CostEstimationError

logger = structlog.get_logger(__name__)


# Anthropic pricing per 1M tokens (as of December 2024)
# Format: model_name -> (input_cost_per_1m, output_cost_per_1m)
ANTHROPIC_PRICING = {
    # Claude 3.5 Sonnet
    "claude-3-5-sonnet-20241022": (Decimal("3.00"), Decimal("15.00")),
    "claude-3-5-sonnet-20240620": (Decimal("3.00"), Decimal("15.00")),

    # Claude 3 Opus
    "claude-3-opus-20240229": (Decimal("15.00"), Decimal("75.00")),

    # Claude 3 Sonnet
    "claude-3-sonnet-20240229": (Decimal("3.00"), Decimal("15.00")),

    # Claude 3 Haiku
    "claude-3-haiku-20240307": (Decimal("0.25"), Decimal("1.25")),

    # Claude 2.1
    "claude-2.1": (Decimal("8.00"), Decimal("24.00")),

    # Claude 2.0
    "claude-2.0": (Decimal("8.00"), Decimal("24.00")),

    # Claude Instant
    "claude-instant-1.2": (Decimal("0.80"), Decimal("2.40")),

    # Default fallback (use Sonnet pricing)
    "default": (Decimal("3.00"), Decimal("15.00")),
}


class AnthropicCostEstimator(CostEstimator):
    """
    Cost estimator for Anthropic API calls.

    Estimates costs based on token usage and Claude model pricing.
    Can extract actual costs from API responses if usage data is included.
    """

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _get_pricing(self, model: str) -> tuple[Decimal, Decimal]:
        """
        Get pricing for a Claude model.

        Args:
            model: Model identifier

        Returns:
            Tuple of (input_cost_per_1m, output_cost_per_1m)
        """
        # Normalize model name
        model_lower = model.lower()

        # Exact match
        if model_lower in ANTHROPIC_PRICING:
            return ANTHROPIC_PRICING[model_lower]

        # Prefix match for versioned models
        for key, pricing in ANTHROPIC_PRICING.items():
            if model_lower.startswith(key):
                return pricing

        # Default pricing
        logger.warning(
            "anthropic_pricing_not_found",
            model=model,
            using_default=True
        )
        return ANTHROPIC_PRICING["default"]

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation for Claude.

        Uses simple heuristic: ~4 characters per token.
        This is a rough approximation; actual tokenization may vary.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)

    async def estimate_cost(
        self,
        request: InvocationRequest,
        resource_metadata: Dict[str, Any]
    ) -> CostEstimate:
        """
        Estimate Anthropic API call cost.

        Expects resource_metadata to contain:
        - model: Claude model name

        Expects request.arguments to contain:
        - messages: List of messages (Claude Messages API format)

        Args:
            request: Invocation request
            resource_metadata: Resource metadata

        Returns:
            Cost estimate with token breakdown

        Raises:
            CostEstimationError: If required metadata is missing
        """
        # Extract model
        model = resource_metadata.get("model")
        if not model:
            raise CostEstimationError(
                "Missing 'model' in resource metadata",
                provider="anthropic"
            )

        # Get pricing
        input_price, output_price = self._get_pricing(model)

        # Estimate input tokens
        input_tokens = 0
        args = request.arguments

        # System message
        if "system" in args:
            input_tokens += self._estimate_tokens(str(args["system"]))

        # Messages
        if "messages" in args:
            for msg in args["messages"]:
                # Handle both simple and complex content
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Complex content (text, images, etc.)
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            input_tokens += self._estimate_tokens(block.get("text", ""))
                        # Note: Image tokens would require special handling
                else:
                    # Simple text content
                    input_tokens += self._estimate_tokens(str(content))
        else:
            raise CostEstimationError(
                "Cannot estimate tokens: no 'messages' in arguments",
                provider="anthropic"
            )

        # Estimate output tokens
        max_tokens = args.get("max_tokens")
        if max_tokens:
            output_tokens = int(max_tokens)
        else:
            # Default estimate: Anthropic requires max_tokens, but estimate conservatively
            output_tokens = max(1024, int(input_tokens * 0.5))

        # Calculate cost
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * input_price
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * output_price
        total_cost = input_cost + output_cost

        return CostEstimate(
            estimated_cost=total_cost,
            currency="USD",
            provider="anthropic",
            model=model,
            breakdown={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost_per_1m": str(input_price),
                "output_cost_per_1m": str(output_price),
                "input_cost": str(input_cost),
                "output_cost": str(output_cost),
            },
        )

    async def record_actual_cost(
        self,
        request: InvocationRequest,
        result: InvocationResult,
        resource_metadata: Dict[str, Any]
    ) -> Optional[CostEstimate]:
        """
        Extract actual cost from Anthropic API response.

        Anthropic includes usage data in responses:
        {
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20
            }
        }

        Args:
            request: Original invocation request
            result: Invocation result
            resource_metadata: Resource metadata

        Returns:
            CostEstimate with actual cost if usage data available, None otherwise
        """
        if not result.success or not result.metadata:
            return None

        usage = result.metadata.get("usage")
        if not usage:
            return None

        # Extract model
        model = resource_metadata.get("model")
        if not model:
            return None

        # Get pricing
        input_price, output_price = self._get_pricing(model)

        # Extract token counts
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Calculate actual cost
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * input_price
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * output_price
        total_cost = input_cost + output_cost

        return CostEstimate(
            estimated_cost=total_cost,
            currency="USD",
            provider="anthropic",
            model=model,
            breakdown={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "input_cost_per_1m": str(input_price),
                "output_cost_per_1m": str(output_price),
                "input_cost": str(input_cost),
                "output_cost": str(output_cost),
                "actual": True,
            },
        )


__all__ = ["AnthropicCostEstimator", "ANTHROPIC_PRICING"]
