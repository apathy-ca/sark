"""
Cost-Aware Policy Plugin

Makes authorization decisions based on estimated costs and budget constraints.
Integrates with SARK's cost estimation system to prevent expensive operations
when users are close to budget limits.
"""

from decimal import Decimal
from typing import Optional

from sark.services.policy.plugins import PolicyPlugin, PolicyContext, PolicyDecision


class CostAwarePlugin(PolicyPlugin):
    """
    Policy plugin that considers costs when making authorization decisions.

    This plugin denies operations that would push a user over their budget,
    or warns when they're close to limits.
    """

    def __init__(
        self,
        warning_threshold_percent: float = 80.0,
        strict_mode: bool = False,
    ):
        """
        Initialize cost-aware plugin.

        Args:
            warning_threshold_percent: Warn when budget usage exceeds this percent
            strict_mode: If True, deny requests when warning threshold is exceeded
        """
        self.warning_threshold = warning_threshold_percent
        self.strict_mode = strict_mode

    @property
    def name(self) -> str:
        return "cost-aware"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        mode = "strict" if self.strict_mode else "permissive"
        return f"Cost-aware authorization ({mode} mode, warns at {self.warning_threshold}% budget)"

    @property
    def priority(self) -> int:
        return 30  # Run after rate limiting but before business logic

    def _get_budget_info(self, context: PolicyContext) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Extract budget information from context environment.

        In production, this would query the CostAttributionService.

        Args:
            context: Policy context

        Returns:
            Tuple of (budget_limit, current_spending)
        """
        # Budget info should be in environment (set by caller)
        budget_limit = context.environment.get("daily_budget")
        current_spending = context.environment.get("daily_spent")

        if budget_limit is not None:
            budget_limit = Decimal(str(budget_limit))
        if current_spending is not None:
            current_spending = Decimal(str(current_spending))

        return budget_limit, current_spending

    def _get_estimated_cost(self, context: PolicyContext) -> Optional[Decimal]:
        """
        Extract estimated cost from context environment.

        Args:
            context: Policy context

        Returns:
            Estimated cost or None
        """
        estimated_cost = context.environment.get("estimated_cost")
        if estimated_cost is not None:
            return Decimal(str(estimated_cost))
        return None

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """
        Evaluate if operation should be allowed based on cost.

        Args:
            context: Policy evaluation context

        Returns:
            PolicyDecision considering budget constraints
        """
        # Get budget info
        budget_limit, current_spending = self._get_budget_info(context)

        # If no budget configured, allow (no cost restrictions)
        if budget_limit is None or current_spending is None:
            return PolicyDecision(
                allowed=True,
                reason="No budget constraints configured",
                metadata={"budget_configured": False},
            )

        # Get estimated cost for this operation
        estimated_cost = self._get_estimated_cost(context)

        if estimated_cost is None:
            # Can't estimate cost - allow but warn
            return PolicyDecision(
                allowed=True,
                reason="Cost estimation unavailable, allowing operation",
                metadata={
                    "warning": "Unable to estimate cost",
                    "budget_limit": str(budget_limit),
                    "current_spending": str(current_spending),
                },
            )

        # Calculate projected spending
        projected_spending = current_spending + estimated_cost

        # Check if would exceed budget
        if projected_spending > budget_limit:
            return PolicyDecision(
                allowed=False,
                reason=f"Operation would exceed daily budget: "
                       f"${projected_spending} > ${budget_limit} "
                       f"(current: ${current_spending}, estimated: ${estimated_cost})",
                metadata={
                    "budget_limit": str(budget_limit),
                    "current_spending": str(current_spending),
                    "estimated_cost": str(estimated_cost),
                    "projected_spending": str(projected_spending),
                    "overage": str(projected_spending - budget_limit),
                },
            )

        # Calculate budget usage percentage
        usage_percent = float(projected_spending / budget_limit * 100)

        # Check warning threshold
        if usage_percent >= self.warning_threshold:
            if self.strict_mode:
                # Strict mode: deny when threshold exceeded
                return PolicyDecision(
                    allowed=False,
                    reason=f"Budget usage would exceed warning threshold: "
                           f"{usage_percent:.1f}% >= {self.warning_threshold}% "
                           f"(strict mode enabled)",
                    metadata={
                        "budget_limit": str(budget_limit),
                        "projected_spending": str(projected_spending),
                        "usage_percent": usage_percent,
                        "warning_threshold": self.warning_threshold,
                        "strict_mode": True,
                    },
                )
            else:
                # Permissive mode: allow but warn
                return PolicyDecision(
                    allowed=True,
                    reason=f"Warning: Budget usage at {usage_percent:.1f}% after this operation",
                    metadata={
                        "warning": "approaching_budget_limit",
                        "budget_limit": str(budget_limit),
                        "projected_spending": str(projected_spending),
                        "usage_percent": usage_percent,
                        "warning_threshold": self.warning_threshold,
                        "estimated_cost": str(estimated_cost),
                    },
                )

        # Well within budget - allow
        remaining = budget_limit - projected_spending
        return PolicyDecision(
            allowed=True,
            reason=f"Within budget: {usage_percent:.1f}% used, ${remaining} remaining",
            metadata={
                "budget_limit": str(budget_limit),
                "current_spending": str(current_spending),
                "estimated_cost": str(estimated_cost),
                "projected_spending": str(projected_spending),
                "usage_percent": usage_percent,
                "remaining_budget": str(remaining),
            },
        )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_cost_aware():
        """Test the cost-aware plugin."""
        plugin = CostAwarePlugin(warning_threshold_percent=80.0, strict_mode=False)

        # Test 1: Well within budget
        context1 = PolicyContext(
            principal_id="user-123",
            resource_id="gpt-4",
            capability_id="generate-text",
            action="invoke",
            arguments={},
            environment={
                "daily_budget": "10.00",
                "daily_spent": "2.00",
                "estimated_cost": "0.50",
            },
        )

        decision = await plugin.evaluate(context1)
        print(f"Test 1 (within budget): {decision.allowed} - {decision.reason}")

        # Test 2: Approaching threshold (warning)
        context2 = PolicyContext(
            principal_id="user-123",
            resource_id="gpt-4",
            capability_id="generate-text",
            action="invoke",
            arguments={},
            environment={
                "daily_budget": "10.00",
                "daily_spent": "7.50",
                "estimated_cost": "1.00",
            },
        )

        decision = await plugin.evaluate(context2)
        print(f"Test 2 (warning threshold): {decision.allowed} - {decision.reason}")

        # Test 3: Would exceed budget
        context3 = PolicyContext(
            principal_id="user-123",
            resource_id="gpt-4",
            capability_id="generate-text",
            action="invoke",
            arguments={},
            environment={
                "daily_budget": "10.00",
                "daily_spent": "9.50",
                "estimated_cost": "1.00",
            },
        )

        decision = await plugin.evaluate(context3)
        print(f"Test 3 (exceed budget): {decision.allowed} - {decision.reason}")

        # Test 4: No budget configured
        context4 = PolicyContext(
            principal_id="user-456",
            resource_id="gpt-4",
            capability_id="generate-text",
            action="invoke",
            arguments={},
            environment={},
        )

        decision = await plugin.evaluate(context4)
        print(f"Test 4 (no budget): {decision.allowed} - {decision.reason}")

    asyncio.run(test_cost_aware())
