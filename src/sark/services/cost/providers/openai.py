"""
OpenAI cost estimator implementation.

Calculates costs based on OpenAI's token-based pricing model.
Pricing data as of December 2024.
"""

from decimal import Decimal
from typing import Any, Dict, Optional
import structlog

from sark.models.base import InvocationRequest, InvocationResult
from sark.services.cost.estimator import CostEstimator, CostEstimate, CostEstimationError

logger = structlog.get_logger(__name__)


# OpenAI pricing per 1M tokens (as of December 2024)
# Format: model_name -> (input_cost_per_1m, output_cost_per_1m)
OPENAI_PRICING = {
    # GPT-4 Turbo
    "gpt-4-turbo": (Decimal("10.00"), Decimal("30.00")),
    "gpt-4-turbo-preview": (Decimal("10.00"), Decimal("30.00")),
    "gpt-4-0125-preview": (Decimal("10.00"), Decimal("30.00")),
    "gpt-4-1106-preview": (Decimal("10.00"), Decimal("30.00")),

    # GPT-4
    "gpt-4": (Decimal("30.00"), Decimal("60.00")),
    "gpt-4-0613": (Decimal("30.00"), Decimal("60.00")),
    "gpt-4-32k": (Decimal("60.00"), Decimal("120.00")),
    "gpt-4-32k-0613": (Decimal("60.00"), Decimal("120.00")),

    # GPT-3.5 Turbo
    "gpt-3.5-turbo": (Decimal("0.50"), Decimal("1.50")),
    "gpt-3.5-turbo-0125": (Decimal("0.50"), Decimal("1.50")),
    "gpt-3.5-turbo-1106": (Decimal("1.00"), Decimal("2.00")),
    "gpt-3.5-turbo-16k": (Decimal("3.00"), Decimal("4.00")),

    # o1 models
    "o1-preview": (Decimal("15.00"), Decimal("60.00")),
    "o1-mini": (Decimal("3.00"), Decimal("12.00")),

    # Embeddings
    "text-embedding-3-small": (Decimal("0.02"), Decimal("0.00")),
    "text-embedding-3-large": (Decimal("0.13"), Decimal("0.00")),
    "text-embedding-ada-002": (Decimal("0.10"), Decimal("0.00")),

    # Default fallback
    "default": (Decimal("10.00"), Decimal("30.00")),
}


class OpenAICostEstimator(CostEstimator):
    """
    Cost estimator for OpenAI API calls.

    Estimates costs based on token usage and model pricing.
    Can extract actual costs from API responses if usage data is included.
    """

    @property
    def provider_name(self) -> str:
        return "openai"

    def _get_pricing(self, model: str) -> tuple[Decimal, Decimal]:
        """
        Get pricing for a model.

        Args:
            model: Model identifier

        Returns:
            Tuple of (input_cost_per_1m, output_cost_per_1m)
        """
        # Normalize model name
        model_lower = model.lower()

        # Exact match
        if model_lower in OPENAI_PRICING:
            return OPENAI_PRICING[model_lower]

        # Prefix match (e.g., "gpt-4-turbo-2024-04-09" -> "gpt-4-turbo")
        for key, pricing in OPENAI_PRICING.items():
            if model_lower.startswith(key):
                return pricing

        # Default pricing
        logger.warning(
            "openai_pricing_not_found",
            model=model,
            using_default=True
        )
        return OPENAI_PRICING["default"]

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation.

        Uses simple heuristic: ~4 characters per token.
        For production, consider using tiktoken library.

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
        Estimate OpenAI API call cost.

        Expects resource_metadata to contain:
        - model: OpenAI model name

        Expects request.arguments to contain one of:
        - messages: List of chat messages
        - prompt: Single prompt string
        - input: Input text (for embeddings)

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
                provider="openai"
            )

        # Get pricing
        input_price, output_price = self._get_pricing(model)

        # Estimate input tokens
        input_tokens = 0
        args = request.arguments

        if "messages" in args:
            # Chat completion
            for msg in args["messages"]:
                content = msg.get("content", "")
                input_tokens += self._estimate_tokens(str(content))
        elif "prompt" in args:
            # Legacy completion
            input_tokens = self._estimate_tokens(str(args["prompt"]))
        elif "input" in args:
            # Embeddings
            if isinstance(args["input"], list):
                for text in args["input"]:
                    input_tokens += self._estimate_tokens(str(text))
            else:
                input_tokens = self._estimate_tokens(str(args["input"]))
        else:
            # No recognizable input
            raise CostEstimationError(
                "Cannot estimate tokens: no 'messages', 'prompt', or 'input' in arguments",
                provider="openai"
            )

        # Estimate output tokens (use max_tokens if specified, else estimate 50% of input)
        max_tokens = args.get("max_tokens")
        if max_tokens:
            output_tokens = int(max_tokens)
        else:
            # Default estimate: 50% of input tokens for completion
            output_tokens = max(100, int(input_tokens * 0.5))

        # Calculate cost
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * input_price
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * output_price
        total_cost = input_cost + output_cost

        return CostEstimate(
            estimated_cost=total_cost,
            currency="USD",
            provider="openai",
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
        Extract actual cost from OpenAI API response.

        OpenAI includes usage data in responses:
        {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
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
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Calculate actual cost
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * input_price
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * output_price
        total_cost = input_cost + output_cost

        return CostEstimate(
            estimated_cost=total_cost,
            currency="USD",
            provider="openai",
            model=model,
            breakdown={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": usage.get("total_tokens", input_tokens + output_tokens),
                "input_cost_per_1m": str(input_price),
                "output_cost_per_1m": str(output_price),
                "input_cost": str(input_cost),
                "output_cost": str(output_cost),
                "actual": True,
            },
        )


__all__ = ["OpenAICostEstimator", "OPENAI_PRICING"]
