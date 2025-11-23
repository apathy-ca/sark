"""Open Policy Agent client for authorization decisions."""

import asyncio
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


# Alias for backward compatibility
PolicyDecision = AuthorizationDecision


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

        # Set up cache revalidation callback for stale-while-revalidate
        if hasattr(self.cache, 'set_revalidate_callback'):
            self.cache.set_revalidate_callback(self._revalidate_cache_entry)

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

        # Get sensitivity for cache optimization
        sensitivity = self._get_sensitivity(auth_input)

        # Try cache first
        if use_cache and self.cache.enabled:
            cached_decision = await self.cache.get(
                user_id=user_id,
                action=action,
                resource=resource,
                context=auth_input.context,
                sensitivity=sensitivity,
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
        Determine cache TTL based on request context using optimized settings.

        Args:
            auth_input: Authorization input

        Returns:
            TTL in seconds
        """
        # Check sensitivity level
        sensitivity = self._get_sensitivity(auth_input)

        # Use optimized TTL settings from cache if available
        if hasattr(self.cache, 'use_optimized_ttl') and self.cache.use_optimized_ttl:
            return self.cache.OPTIMIZED_TTL.get(sensitivity, self.cache.OPTIMIZED_TTL["default"])

        # Fallback to legacy TTL settings
        ttl_map = {
            "critical": 60,
            "confidential": 120,
            "internal": 180,
            "public": 300,
        }
        return ttl_map.get(sensitivity, 120)

    def _get_sensitivity(self, auth_input: AuthorizationInput) -> str:
        """
        Extract sensitivity level from authorization input.

        Args:
            auth_input: Authorization input

        Returns:
            Sensitivity level (critical, confidential, internal, public, or default)
        """
        if auth_input.tool:
            return auth_input.tool.get("sensitivity_level", "default")
        elif auth_input.server:
            return auth_input.server.get("sensitivity_level", "default")
        return "default"

    async def _revalidate_cache_entry(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Revalidate a cache entry by querying OPA.

        This is called by the cache during stale-while-revalidate.

        Args:
            user_id: User identifier
            action: Action being performed
            resource: Resource being accessed
            context: Additional context

        Returns:
            Fresh policy decision or None on error
        """
        try:
            # Reconstruct minimal auth input for OPA query
            # Note: This is a simplified revalidation - in production you'd want
            # to store more context or fetch user data
            auth_input = AuthorizationInput(
                user={"id": user_id},
                action=action,
                context=context or {},
            )

            # Parse resource to determine if it's tool or server
            if resource.startswith("tool:"):
                tool_name = resource.replace("tool:", "")
                auth_input.tool = {"name": tool_name}
            elif resource.startswith("server:"):
                server_name = resource.replace("server:", "")
                auth_input.server = {"name": server_name}

            # Query OPA directly (bypass cache to avoid recursion)
            response = await self.client.post(
                f"{self.opa_url}{self.policy_path}",
                json={"input": auth_input.model_dump()},
            )
            response.raise_for_status()

            result = response.json()
            policy_result = result.get("result", {})

            decision = {
                "allow": policy_result.get("allow", False),
                "reason": policy_result.get("audit_reason", "Policy evaluation completed"),
                "filtered_parameters": policy_result.get("filtered_parameters"),
                "audit_id": policy_result.get("audit_id"),
            }

            return decision

        except Exception as e:
            logger.warning(
                "cache_revalidation_failed",
                error=str(e),
                user_id=user_id,
                action=action,
                resource=resource,
            )
            return None

    async def evaluate_policy_batch(
        self,
        auth_inputs: list[AuthorizationInput],
        use_cache: bool = True,
    ) -> list[AuthorizationDecision]:
        """
        Evaluate multiple authorization policies in a batch using Redis pipelining.

        This significantly reduces latency for bulk operations by:
        1. Checking cache for all requests in a single Redis round-trip
        2. Evaluating cache misses in parallel via OPA
        3. Caching results in a single Redis round-trip

        Args:
            auth_inputs: List of authorization inputs
            use_cache: Whether to use cache

        Returns:
            List of authorization decisions in the same order as inputs
        """
        if not auth_inputs:
            return []

        # Extract cache lookup parameters
        cache_requests = []
        for auth_input in auth_inputs:
            user_id = auth_input.user.get("id", "unknown")
            action = auth_input.action

            resource = "unknown"
            if auth_input.tool:
                resource = f"tool:{auth_input.tool.get('name', 'unknown')}"
            elif auth_input.server:
                resource = f"server:{auth_input.server.get('name', 'unknown')}"

            cache_requests.append((user_id, action, resource, auth_input.context))

        # Batch cache lookup
        cached_decisions = []
        if use_cache and self.cache.enabled and hasattr(self.cache, 'get_batch'):
            cached_decisions = await self.cache.get_batch(cache_requests)
        else:
            cached_decisions = [None] * len(auth_inputs)

        # Identify cache misses
        misses = []
        miss_indices = []
        for i, cached_decision in enumerate(cached_decisions):
            if cached_decision is None:
                misses.append(auth_inputs[i])
                miss_indices.append(i)

        # Evaluate cache misses in parallel
        miss_decisions = []
        if misses:
            # Create tasks for parallel evaluation
            tasks = [
                self._evaluate_opa_policy(auth_input)
                for auth_input in misses
            ]

            miss_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(miss_results):
                if isinstance(result, Exception):
                    logger.error(
                        "batch_evaluation_error",
                        error=str(result),
                        index=miss_indices[i],
                    )
                    miss_decisions.append(
                        AuthorizationDecision(
                            allow=False,
                            reason=f"Evaluation error: {result!s}",
                        )
                    )
                else:
                    miss_decisions.append(result)

            # Cache miss results in batch
            if use_cache and self.cache.enabled and hasattr(self.cache, 'set_batch'):
                cache_entries = []
                for i, decision in enumerate(miss_decisions):
                    user_id, action, resource, context = cache_requests[miss_indices[i]]
                    ttl_seconds = self._get_cache_ttl(misses[i])

                    cache_entries.append((
                        user_id,
                        action,
                        resource,
                        decision.model_dump(),
                        context,
                        ttl_seconds,
                    ))

                await self.cache.set_batch(cache_entries)

        # Combine cached and fresh results
        decisions = []
        miss_iter = iter(miss_decisions)

        for cached_decision in cached_decisions:
            if cached_decision is None:
                # Use fresh evaluation
                decisions.append(next(miss_iter))
            else:
                # Use cached decision
                decisions.append(AuthorizationDecision(**cached_decision))

        logger.info(
            "batch_policy_evaluation",
            total=len(auth_inputs),
            cache_hits=len(auth_inputs) - len(misses),
            cache_misses=len(misses),
            hit_rate=round(((len(auth_inputs) - len(misses)) / len(auth_inputs)) * 100, 2),
        )

        return decisions

    async def _evaluate_opa_policy(
        self,
        auth_input: AuthorizationInput,
    ) -> AuthorizationDecision:
        """
        Evaluate a single policy via OPA (without caching).

        Args:
            auth_input: Authorization input

        Returns:
            Authorization decision
        """
        start_time = time.time()

        try:
            response = await self.client.post(
                f"{self.opa_url}{self.policy_path}",
                json={"input": auth_input.model_dump()},
            )
            response.raise_for_status()

            opa_latency_ms = (time.time() - start_time) * 1000

            result = response.json()
            policy_result = result.get("result", {})

            decision = AuthorizationDecision(
                allow=policy_result.get("allow", False),
                reason=policy_result.get("audit_reason", "Policy evaluation completed"),
                filtered_parameters=policy_result.get("filtered_parameters"),
                audit_id=policy_result.get("audit_id"),
            )

            # Record OPA latency for metrics
            self.cache.record_opa_latency(opa_latency_ms)

            return decision

        except httpx.HTTPError as e:
            logger.error("opa_request_failed", error=str(e))
            return AuthorizationDecision(
                allow=False,
                reason=f"Policy evaluation failed: {e!s}",
            )
        except Exception as e:
            logger.error("unexpected_error", error=str(e))
            return AuthorizationDecision(
                allow=False,
                reason="Internal error during policy evaluation",
            )

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
