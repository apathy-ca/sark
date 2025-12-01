"""
Cost tracking service that integrates estimators with attribution.

This service coordinates between cost estimators and the cost attribution
system to provide comprehensive cost tracking.
"""

from decimal import Decimal
from typing import Any, Dict, Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.base import InvocationRequest, InvocationResult
from sark.models.cost_attribution import CostAttributionService
from sark.services.cost.estimator import CostEstimator, CostEstimate, NoCostEstimator
from sark.services.cost.providers.openai import OpenAICostEstimator
from sark.services.cost.providers.anthropic import AnthropicCostEstimator

logger = structlog.get_logger(__name__)


class CostTracker:
    """
    Central service for cost tracking and budget management.

    Coordinates cost estimation, budget checks, and cost attribution recording.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize cost tracker.

        Args:
            db: Async database session
        """
        self.db = db
        self.attribution_service = CostAttributionService(db)

        # Registry of cost estimators by provider
        self._estimators: Dict[str, CostEstimator] = {
            "openai": OpenAICostEstimator(),
            "anthropic": AnthropicCostEstimator(),
            "free": NoCostEstimator(),
        }

    def register_estimator(
        self,
        provider: str,
        estimator: CostEstimator
    ) -> None:
        """
        Register a custom cost estimator.

        Args:
            provider: Provider identifier
            estimator: Cost estimator instance
        """
        self._estimators[provider] = estimator
        logger.info(
            "cost_estimator_registered",
            provider=provider,
            estimator_class=estimator.__class__.__name__
        )

    def get_estimator(
        self,
        provider: str
    ) -> Optional[CostEstimator]:
        """
        Get cost estimator for a provider.

        Args:
            provider: Provider identifier

        Returns:
            CostEstimator instance or None if not found
        """
        return self._estimators.get(provider)

    async def estimate_invocation_cost(
        self,
        request: InvocationRequest,
        resource_metadata: Dict[str, Any]
    ) -> CostEstimate:
        """
        Estimate cost for an invocation request.

        Args:
            request: Invocation request
            resource_metadata: Resource metadata (should contain 'provider' or 'cost_provider')

        Returns:
            Cost estimate
        """
        # Determine provider
        provider = resource_metadata.get("cost_provider") or resource_metadata.get("provider", "free")

        # Get estimator
        estimator = self.get_estimator(provider)
        if not estimator:
            logger.warning(
                "cost_estimator_not_found",
                provider=provider,
                using_default=True
            )
            estimator = NoCostEstimator()

        # Estimate cost
        try:
            estimate = await estimator.estimate_cost(request, resource_metadata)
            logger.debug(
                "cost_estimated",
                provider=provider,
                estimated_cost=str(estimate.estimated_cost),
                principal_id=request.principal_id,
                capability_id=request.capability_id
            )
            return estimate
        except Exception as e:
            logger.error(
                "cost_estimation_failed",
                error=str(e),
                provider=provider,
                principal_id=request.principal_id,
                capability_id=request.capability_id
            )
            # Return zero cost estimate on failure
            return CostEstimate(
                estimated_cost=Decimal("0.00"),
                currency="USD",
                provider=provider,
                metadata={"error": str(e), "fallback": True}
            )

    async def check_budget_before_invocation(
        self,
        request: InvocationRequest,
        resource_metadata: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if principal has sufficient budget for an invocation.

        Args:
            request: Invocation request
            resource_metadata: Resource metadata

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        # Estimate cost
        estimate = await self.estimate_invocation_cost(request, resource_metadata)

        # Check budget
        allowed, reason = await self.attribution_service.check_budget(
            request.principal_id,
            estimate.estimated_cost
        )

        if not allowed:
            logger.warning(
                "budget_check_failed",
                principal_id=request.principal_id,
                estimated_cost=str(estimate.estimated_cost),
                reason=reason
            )

        return allowed, reason

    async def record_invocation_cost(
        self,
        request: InvocationRequest,
        result: InvocationResult,
        resource_id: str,
        resource_metadata: Dict[str, Any]
    ) -> None:
        """
        Record cost for a completed invocation.

        Attempts to extract actual cost from result, falls back to estimated cost.

        Args:
            request: Original invocation request
            result: Invocation result
            resource_id: Resource ID
            resource_metadata: Resource metadata
        """
        # Determine provider
        provider = resource_metadata.get("cost_provider") or resource_metadata.get("provider", "free")

        # Get estimator
        estimator = self.get_estimator(provider)
        if not estimator:
            estimator = NoCostEstimator()

        # Try to get actual cost from result
        actual_estimate = None
        if result.success and estimator.supports_actual_cost():
            try:
                actual_estimate = await estimator.record_actual_cost(
                    request,
                    result,
                    resource_metadata
                )
            except Exception as e:
                logger.warning(
                    "actual_cost_extraction_failed",
                    error=str(e),
                    provider=provider
                )

        # Get estimated cost if we don't have actual
        estimated_cost = None
        if not actual_estimate:
            try:
                estimate = await estimator.estimate_cost(request, resource_metadata)
                estimated_cost = estimate.estimated_cost
            except Exception as e:
                logger.error(
                    "cost_estimation_failed_on_record",
                    error=str(e),
                    provider=provider
                )

        # Prepare metadata
        metadata = {
            "provider": provider,
        }

        if actual_estimate:
            metadata.update({
                "model": actual_estimate.model,
                "breakdown": actual_estimate.breakdown,
                "actual": True,
            })

        # Record cost
        try:
            await self.attribution_service.record_cost(
                principal_id=request.principal_id,
                resource_id=resource_id,
                capability_id=request.capability_id,
                estimated_cost=estimated_cost,
                actual_cost=actual_estimate.estimated_cost if actual_estimate else None,
                metadata=metadata
            )

            logger.info(
                "cost_recorded",
                principal_id=request.principal_id,
                resource_id=resource_id,
                capability_id=request.capability_id,
                estimated_cost=str(estimated_cost) if estimated_cost else None,
                actual_cost=str(actual_estimate.estimated_cost) if actual_estimate else None,
                provider=provider
            )
        except Exception as e:
            logger.error(
                "cost_recording_failed",
                error=str(e),
                principal_id=request.principal_id,
                capability_id=request.capability_id
            )


__all__ = ["CostTracker"]
