"""Open Policy Agent client for authorization decisions."""

import time
from typing import Any

import httpx
from pydantic import BaseModel
import structlog

from sark.config import get_settings
from sark.services.policy.cache import PolicyCache, get_policy_cache

logger = structlog.get_logger()
settings = get_settings()


class AuthorizationInput(BaseModel):
    """Authorization request input."""

    user: dict[str, Any]
    action: str
    tool: dict[str, Any] | None = None
    server: dict[str, Any] | None = None
    context: dict[str, Any]


class AuthorizationDecision(BaseModel):
    """Authorization decision response."""

    allow: bool
    reason: str
    filtered_parameters: dict[str, Any] | None = None
    audit_id: str | None = None


class OPAClient:
    """Client for interacting with Open Policy Agent."""

    def __init__(
        self,
        opa_url: str | None = None,
        timeout: float | None = None,
        cache: PolicyCache | None = None,
        cache_enabled: bool = True,
    ) -> None:
        """
        Initialize OPA client.

        Args:
            opa_url: OPA server URL
            timeout: Request timeout in seconds
            cache: PolicyCache instance (creates default if None)
            cache_enabled: Whether to enable caching
        """
        self.opa_url = opa_url or settings.opa_url
        self.timeout = timeout or settings.opa_timeout_seconds
        self.policy_path = settings.opa_policy_path
        self.client = httpx.AsyncClient(timeout=self.timeout)

        # Initialize cache
        if cache:
            self.cache = cache
        else:
            self.cache = get_policy_cache(enabled=cache_enabled)

    async def evaluate_policy(
        self,
        auth_input: AuthorizationInput,
        use_cache: bool = True,
    ) -> AuthorizationDecision:
        """
        Evaluate authorization policy via OPA with caching.

        Args:
            auth_input: Authorization input containing user, action, tool, and context
            use_cache: Whether to use cache for this request (default: True)

        Returns:
            Authorization decision with allow/deny and reason

        Raises:
            httpx.HTTPError: If OPA request fails
        """
        user_id = auth_input.user.get("id", "unknown")
        action = auth_input.action

        # Determine resource identifier
        resource = "unknown"
        if auth_input.tool:
            resource = f"tool:{auth_input.tool.get('name', 'unknown')}"
        elif auth_input.server:
            resource = f"server:{auth_input.server.get('name', 'unknown')}"

        # Try cache first
        if use_cache and self.cache.enabled:
            cached_decision = await self.cache.get(
                user_id=user_id,
                action=action,
                resource=resource,
                context=auth_input.context,
            )

            if cached_decision:
                # Return cached decision
                return AuthorizationDecision(**cached_decision)

        # Cache miss - query OPA
        start_time = time.time()

        try:
            response = await self.client.post(
                f"{self.opa_url}{self.policy_path}",
                json={"input": auth_input.model_dump()},
            )
            response.raise_for_status()

            opa_latency_ms = (time.time() - start_time) * 1000

            result = response.json()

            # OPA returns {"result": {"allow": true, "reason": "..."}}
            policy_result = result.get("result", {})

            decision = AuthorizationDecision(
                allow=policy_result.get("allow", False),
                reason=policy_result.get("audit_reason", "Policy evaluation completed"),
                filtered_parameters=policy_result.get("filtered_parameters"),
                audit_id=policy_result.get("audit_id"),
            )

            # Cache the decision if caching is enabled
            if use_cache and self.cache.enabled:
                # Determine TTL based on sensitivity or other factors
                ttl_seconds = self._get_cache_ttl(auth_input)

                await self.cache.set(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    decision=decision.model_dump(),
                    context=auth_input.context,
                    ttl_seconds=ttl_seconds,
                )

            # Record OPA latency for metrics
            self.cache.record_opa_latency(opa_latency_ms)

            logger.info(
                "policy_evaluated",
                decision=decision.allow,
                user_id=user_id,
                action=action,
                opa_latency_ms=round(opa_latency_ms, 2),
            )

            return decision

        except httpx.HTTPError as e:
            logger.error("opa_request_failed", error=str(e), opa_url=self.opa_url)
            # Fail closed - deny on error
            return AuthorizationDecision(
                allow=False,
                reason=f"Policy evaluation failed: {e!s}",
            )

        except Exception as e:
            logger.error("unexpected_error", error=str(e))
            # Fail closed
            return AuthorizationDecision(
                allow=False,
                reason="Internal error during policy evaluation",
            )

    def _get_cache_ttl(self, auth_input: AuthorizationInput) -> int:
        """
        Determine cache TTL based on request context.

        Lower TTL for high-sensitivity operations.

        Args:
            auth_input: Authorization input

        Returns:
            TTL in seconds
        """
        # Check sensitivity level
        sensitivity = None
        if auth_input.tool:
            sensitivity = auth_input.tool.get("sensitivity_level")
        elif auth_input.server:
            sensitivity = auth_input.server.get("sensitivity_level")

        # Adjust TTL based on sensitivity
        if sensitivity == "critical":
            return 30  # 30 seconds for critical
        elif sensitivity == "high":
            return 60  # 1 minute for high
        elif sensitivity == "medium":
            return 180  # 3 minutes for medium
        elif sensitivity == "low":
            return 300  # 5 minutes for low
        else:
            return 120  # Default 2 minutes

    async def check_tool_access(
        self,
        user_id: str,
        user_email: str,
        user_role: str,
        tool_name: str,
        tool_sensitivity: str,
        tool_owner_id: str | None = None,
        team_ids: list[str] | None = None,
    ) -> AuthorizationDecision:
        """
        Check if user has access to invoke a specific tool.

        Args:
            user_id: User identifier
            user_email: User email
            user_role: User role (developer, admin, etc.)
            tool_name: Tool name to check
            tool_sensitivity: Tool sensitivity level (low, medium, high, critical)
            tool_owner_id: Tool owner user ID
            team_ids: List of team IDs managing the tool

        Returns:
            Authorization decision
        """
        auth_input = AuthorizationInput(
            user={
                "id": user_id,
                "email": user_email,
                "role": user_role,
                "teams": team_ids or [],
            },
            action="tool:invoke",
            tool={
                "name": tool_name,
                "sensitivity_level": tool_sensitivity,
                "owner": tool_owner_id,
                "managers": team_ids or [],
            },
            context={
                "timestamp": (
                    httpx.get("https://worldtimeapi.org/api/ip").json()["unixtime"]
                    if settings.environment == "production"
                    else 0
                )
            },
        )

        return await self.evaluate_policy(auth_input)

    async def check_server_registration(
        self,
        user_id: str,
        user_email: str,
        user_role: str,
        server_name: str,
        server_sensitivity: str,
    ) -> AuthorizationDecision:
        """
        Check if user can register a new MCP server.

        Args:
            user_id: User identifier
            user_email: User email
            user_role: User role
            server_name: Server name to register
            server_sensitivity: Server sensitivity level

        Returns:
            Authorization decision
        """
        auth_input = AuthorizationInput(
            user={
                "id": user_id,
                "email": user_email,
                "role": user_role,
            },
            action="server:register",
            server={
                "name": server_name,
                "sensitivity_level": server_sensitivity,
            },
            context={"timestamp": 0},
        )

        return await self.evaluate_policy(auth_input)

    async def invalidate_cache(
        self,
        user_id: str | None = None,
        action: str | None = None,
        resource: str | None = None,
    ) -> int:
        """
        Invalidate cached policy decisions.

        Args:
            user_id: Invalidate for specific user (or all if None)
            action: Invalidate for specific action (or all if None)
            resource: Invalidate for specific resource (or all if None)

        Returns:
            Number of cache entries invalidated
        """
        return await self.cache.invalidate(
            user_id=user_id,
            action=action,
            resource=resource,
        )

    def get_cache_metrics(self) -> dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary with cache metrics including hit rate and latencies
        """
        return self.cache.get_metrics()

    async def get_cache_size(self) -> int:
        """
        Get number of cached policy decisions.

        Returns:
            Number of cache entries
        """
        return await self.cache.get_cache_size()

    async def close(self) -> None:
        """Close HTTP client and cache connection."""
        await self.client.aclose()
        await self.cache.close()

    async def health_check(self) -> dict[str, bool]:
        """
        Check OPA and cache health status.

        Returns:
            Dictionary with health status of OPA and cache
        """
        opa_healthy = False
        cache_healthy = False

        try:
            # OPA health endpoint
            response = await self.client.get(
                f"{self.opa_url}/health",
                timeout=self.timeout,
            )
            opa_healthy = response.status_code == 200
        except Exception as e:
            logger.warning("opa_health_check_failed", error=str(e))

        # Check cache health
        cache_healthy = await self.cache.health_check()

        return {
            "opa": opa_healthy,
            "cache": cache_healthy,
            "overall": opa_healthy and cache_healthy,
        }

    async def authorize(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Quick authorization check.

        Args:
            user_id: User ID
            action: Action to authorize
            resource: Resource to access
            context: Additional context

        Returns:
            True if authorized, False otherwise
        """
        user_context = context.get("user", {}) if context else {}
        auth_input = AuthorizationInput(
            user={"id": user_id, **user_context},
            action=action,
            context=context or {},
        )

        decision = await self.evaluate_policy(auth_input)
        return decision.allow
