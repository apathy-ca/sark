"""
Business Hours Policy Plugin

Restricts resource access to business hours only (9 AM - 5 PM, Monday-Friday).
Useful for controlling costs by preventing expensive operations outside work hours.
"""

from datetime import datetime
from typing import Optional

from sark.services.policy.plugins import PolicyContext, PolicyDecision, PolicyPlugin


class BusinessHoursPlugin(PolicyPlugin):
    """
    Policy plugin that enforces business hours restrictions.

    Configuration:
    - start_hour: Business day start (default: 9)
    - end_hour: Business day end (default: 17)
    - allowed_days: List of allowed weekdays (0=Monday, 6=Sunday)
    - timezone: Timezone for evaluation (default: UTC)
    """

    def __init__(
        self,
        start_hour: int = 9,
        end_hour: int = 17,
        allowed_days: Optional[list] = None,
    ):
        """
        Initialize business hours plugin.

        Args:
            start_hour: Start of business day (0-23)
            end_hour: End of business day (0-23)
            allowed_days: Allowed weekdays (0=Mon, 6=Sun). Default: Mon-Fri
        """
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.allowed_days = allowed_days or [0, 1, 2, 3, 4]  # Mon-Fri

    @property
    def name(self) -> str:
        return "business-hours"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return f"Restricts access to business hours ({self.start_hour}:00-{self.end_hour}:00, weekdays only)"

    @property
    def priority(self) -> int:
        return 50  # Run early in the evaluation chain

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """
        Evaluate if current time is within business hours.

        Args:
            context: Policy evaluation context

        Returns:
            PolicyDecision allowing or denying based on current time
        """
        # Use timestamp from context (or current time if not set)
        now = context.timestamp or datetime.now()

        # Check if it's a business day
        if now.weekday() not in self.allowed_days:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            return PolicyDecision(
                allowed=False,
                reason=f"Access denied: Today is {day_names[now.weekday()]}, "
                       f"but access is only allowed on business days",
                metadata={
                    "current_day": now.weekday(),
                    "allowed_days": self.allowed_days,
                },
            )

        # Check if it's within business hours
        current_hour = now.hour
        if not (self.start_hour <= current_hour < self.end_hour):
            return PolicyDecision(
                allowed=False,
                reason=f"Access denied: Current time {now.hour}:00 is outside "
                       f"business hours ({self.start_hour}:00-{self.end_hour}:00)",
                metadata={
                    "current_hour": current_hour,
                    "business_start": self.start_hour,
                    "business_end": self.end_hour,
                },
            )

        # Within business hours - allow
        return PolicyDecision(
            allowed=True,
            reason="Access granted: Within business hours",
            metadata={
                "evaluated_at": now.isoformat(),
            },
        )


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_business_hours():
        """Test the business hours plugin."""
        plugin = BusinessHoursPlugin()

        # Test during business hours (Wednesday at 2 PM)
        business_hour_context = PolicyContext(
            principal_id="user-123",
            resource_id="expensive-model",
            capability_id="generate-text",
            action="invoke",
            arguments={},
            environment={},
            timestamp=datetime(2024, 12, 11, 14, 0),  # Wednesday 2 PM
        )

        decision = await plugin.evaluate(business_hour_context)
        print(f"Business hours test: {decision.allowed} - {decision.reason}")

        # Test outside business hours (Wednesday at 8 PM)
        after_hours_context = PolicyContext(
            principal_id="user-123",
            resource_id="expensive-model",
            capability_id="generate-text",
            action="invoke",
            arguments={},
            environment={},
            timestamp=datetime(2024, 12, 11, 20, 0),  # Wednesday 8 PM
        )

        decision = await plugin.evaluate(after_hours_context)
        print(f"After hours test: {decision.allowed} - {decision.reason}")

        # Test on weekend (Saturday at 10 AM)
        weekend_context = PolicyContext(
            principal_id="user-123",
            resource_id="expensive-model",
            capability_id="generate-text",
            action="invoke",
            arguments={},
            environment={},
            timestamp=datetime(2024, 12, 14, 10, 0),  # Saturday 10 AM
        )

        decision = await plugin.evaluate(weekend_context)
        print(f"Weekend test: {decision.allowed} - {decision.reason}")

    asyncio.run(test_business_hours())
