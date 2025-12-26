"""
Cost estimation interface and base implementation.

This module provides the abstract CostEstimator interface that all provider-specific
cost estimators must implement. It enables cost tracking and budget management
across different AI/API providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import structlog

from sark.models.base import InvocationRequest, InvocationResult

logger = structlog.get_logger(__name__)


@dataclass
class CostEstimate:
    """
    Cost estimate for a capability invocation.

    Attributes:
        estimated_cost: Estimated cost in USD
        currency: Currency code (default: USD)
        provider: Provider name (e.g., 'openai', 'anthropic')
        model: Model identifier if applicable
        breakdown: Detailed cost breakdown (e.g., input tokens, output tokens)
        metadata: Additional provider-specific metadata
    """

    estimated_cost: Decimal
    currency: str = "USD"
    provider: str | None = None
    model: str | None = None
    breakdown: dict[str, Any] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.breakdown is None:
            self.breakdown = {}
        if self.metadata is None:
            self.metadata = {}


class CostEstimator(ABC):
    """
    Abstract base class for cost estimation.

    Provider-specific implementations (OpenAI, Anthropic, etc.) should inherit
    from this class and implement the estimate_cost method.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return the provider identifier (e.g., 'openai', 'anthropic', 'http').

        Returns:
            str: Provider name in lowercase
        """
        pass

    @abstractmethod
    async def estimate_cost(
        self, request: InvocationRequest, resource_metadata: dict[str, Any]
    ) -> CostEstimate:
        """
        Estimate the cost of an invocation request.

        Args:
            request: The invocation request to estimate
            resource_metadata: Resource-specific metadata (may contain model info, etc.)

        Returns:
            CostEstimate with estimated cost and breakdown

        Raises:
            CostEstimationError: If cost cannot be estimated
        """
        pass

    async def record_actual_cost(
        self,
        request: InvocationRequest,
        result: InvocationResult,
        resource_metadata: dict[str, Any],
    ) -> CostEstimate | None:
        """
        Record actual cost from invocation result.

        Some providers return actual usage information in the response
        (e.g., token counts). This method extracts and calculates actual cost.

        Args:
            request: The original invocation request
            result: The invocation result
            resource_metadata: Resource-specific metadata

        Returns:
            CostEstimate with actual cost if available, None otherwise

        Note:
            Default implementation returns None. Override to extract actual costs
            from provider-specific responses.
        """
        return None

    def supports_actual_cost(self) -> bool:
        """
        Check if this estimator can extract actual costs from responses.

        Returns:
            True if record_actual_cost is implemented, False otherwise
        """
        return self.__class__.record_actual_cost != CostEstimator.record_actual_cost

    def get_estimator_info(self) -> dict[str, Any]:
        """
        Get estimator metadata and capabilities.

        Returns:
            Dictionary with estimator information
        """
        return {
            "provider_name": self.provider_name,
            "estimator_class": self.__class__.__name__,
            "supports_actual_cost": self.supports_actual_cost(),
            "module": self.__class__.__module__,
        }


class NoCostEstimator(CostEstimator):
    """
    Default estimator for resources with no cost.

    Used for resources that don't incur usage-based costs (e.g., internal tools,
    free APIs, etc.).
    """

    @property
    def provider_name(self) -> str:
        return "free"

    async def estimate_cost(
        self, request: InvocationRequest, resource_metadata: dict[str, Any]
    ) -> CostEstimate:
        """Return zero cost estimate."""
        return CostEstimate(
            estimated_cost=Decimal("0.00"),
            currency="USD",
            provider="free",
            breakdown={"message": "No cost for this resource"},
        )


class FixedCostEstimator(CostEstimator):
    """
    Estimator for resources with fixed per-call costs.

    Useful for APIs that charge a flat rate per request.
    """

    def __init__(self, cost_per_call: Decimal, provider: str = "fixed"):
        """
        Initialize fixed cost estimator.

        Args:
            cost_per_call: Fixed cost per invocation
            provider: Provider name
        """
        self._cost_per_call = cost_per_call
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider

    async def estimate_cost(
        self, request: InvocationRequest, resource_metadata: dict[str, Any]
    ) -> CostEstimate:
        """Return fixed cost estimate."""
        return CostEstimate(
            estimated_cost=self._cost_per_call,
            currency="USD",
            provider=self._provider,
            breakdown={
                "cost_per_call": str(self._cost_per_call),
                "call_count": 1,
            },
        )


class CostEstimationError(Exception):
    """Raised when cost estimation fails."""

    def __init__(self, message: str, provider: str | None = None, **kwargs):
        super().__init__(message)
        self.provider = provider
        self.metadata = kwargs


__all__ = [
    "CostEstimate",
    "CostEstimationError",
    "CostEstimator",
    "FixedCostEstimator",
    "NoCostEstimator",
]
