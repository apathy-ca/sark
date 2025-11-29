"""
Rate Limit Policy Plugin

Implements per-principal rate limiting using a sliding window algorithm.
Prevents abuse by limiting how many requests a user can make in a time period.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Deque

from sark.services.policy.plugins import PolicyPlugin, PolicyContext, PolicyDecision


class RateLimitPlugin(PolicyPlugin):
    """
    Policy plugin that enforces rate limits per principal.

    Uses a sliding window algorithm to track requests.
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_minutes: int = 60,
    ):
        """
        Initialize rate limit plugin.

        Args:
            max_requests: Maximum requests allowed in time window
            window_minutes: Time window in minutes
        """
        self.max_requests = max_requests
        self.window_minutes = window_minutes

        # In-memory request tracking (in production, use Redis or similar)
        # Structure: {principal_id: deque of timestamps}
        self._request_history: Dict[str, Deque[datetime]] = defaultdict(deque)

    @property
    def name(self) -> str:
        return "rate-limit"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return f"Rate limits principals to {self.max_requests} requests per {self.window_minutes} minutes"

    @property
    def priority(self) -> int:
        return 10  # Run very early to prevent expensive operations

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """
        Evaluate if principal has exceeded rate limit.

        Args:
            context: Policy evaluation context

        Returns:
            PolicyDecision allowing or denying based on rate limit
        """
        principal_id = context.principal_id
        now = context.timestamp or datetime.now()

        # Get request history for this principal
        history = self._request_history[principal_id]

        # Remove requests outside the time window
        cutoff_time = now - timedelta(minutes=self.window_minutes)
        while history and history[0] < cutoff_time:
            history.popleft()

        # Check if limit exceeded
        current_count = len(history)
        if current_count >= self.max_requests:
            # Calculate when the oldest request will expire
            oldest_request = history[0]
            retry_after_seconds = int((oldest_request - cutoff_time).total_seconds())

            return PolicyDecision(
                allowed=False,
                reason=f"Rate limit exceeded: {current_count}/{self.max_requests} requests "
                       f"in the last {self.window_minutes} minutes. Try again in {retry_after_seconds}s.",
                metadata={
                    "current_count": current_count,
                    "limit": self.max_requests,
                    "window_minutes": self.window_minutes,
                    "retry_after_seconds": retry_after_seconds,
                },
            )

        # Add this request to history
        history.append(now)

        # Calculate remaining quota
        remaining = self.max_requests - (current_count + 1)

        return PolicyDecision(
            allowed=True,
            reason=f"Rate limit check passed: {current_count + 1}/{self.max_requests} requests used",
            metadata={
                "current_count": current_count + 1,
                "remaining": remaining,
                "limit": self.max_requests,
                "window_minutes": self.window_minutes,
            },
        )

    async def on_load(self) -> None:
        """Initialize on plugin load."""
        # In production, might load state from Redis
        pass

    async def on_unload(self) -> None:
        """Cleanup on plugin unload."""
        # In production, might persist state to Redis
        self._request_history.clear()


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_rate_limit():
        """Test the rate limit plugin."""
        plugin = RateLimitPlugin(max_requests=5, window_minutes=1)

        base_time = datetime(2024, 12, 11, 14, 0)

        # Make 5 requests (should all succeed)
        for i in range(5):
            context = PolicyContext(
                principal_id="user-123",
                resource_id="api-resource",
                capability_id="api-call",
                action="invoke",
                arguments={},
                environment={},
                timestamp=base_time + timedelta(seconds=i * 10),
            )

            decision = await plugin.evaluate(context)
            print(f"Request {i + 1}: {decision.allowed} - {decision.reason}")

        # 6th request should be denied
        context = PolicyContext(
            principal_id="user-123",
            resource_id="api-resource",
            capability_id="api-call",
            action="invoke",
            arguments={},
            environment={},
            timestamp=base_time + timedelta(seconds=50),
        )

        decision = await plugin.evaluate(context)
        print(f"Request 6 (should be denied): {decision.allowed} - {decision.reason}")

        # After window expires, should succeed
        context = PolicyContext(
            principal_id="user-123",
            resource_id="api-resource",
            capability_id="api-call",
            action="invoke",
            arguments={},
            environment={},
            timestamp=base_time + timedelta(minutes=2),
        )

        decision = await plugin.evaluate(context)
        print(f"After window expiry: {decision.allowed} - {decision.reason}")

    asyncio.run(test_rate_limit())
