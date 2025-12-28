"""Rust-based OPA client for high-performance policy evaluation."""

import asyncio
import time
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

# Import the Rust extension
try:
    from sark._rust import sark_opa

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    sark_opa = None

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


class RustOPAClient:
    """
    High-performance Rust-based OPA client using embedded Regorus engine.

    This client provides 4-10x faster policy evaluation than HTTP-based OPA
    by running policies in-process using the Regorus library compiled to Rust.

    Performance characteristics:
    - <5ms p95 latency for policy evaluation
    - Zero network overhead
    - Thread-safe concurrent evaluations
    - Memory-efficient policy caching

    Example:
        >>> client = RustOPAClient()
        >>> auth_input = AuthorizationInput(
        ...     user={"id": "user1", "role": "admin"},
        ...     action="gateway:tool:invoke",
        ...     tool={"name": "db-query", "sensitivity_level": "medium"},
        ...     context={}
        ... )
        >>> decision = await client.evaluate_policy(auth_input)
        >>> print(decision.allow)
        True
    """

    def __init__(
        self,
        policy_dir: Path | None = None,
        cache: PolicyCache | None = None,
        cache_enabled: bool = True,
    ) -> None:
        """
        Initialize Rust OPA client.

        Args:
            policy_dir: Directory containing .rego policy files (defaults to ./opa/policies)
            cache: PolicyCache instance (creates default if None)
            cache_enabled: Whether to enable caching

        Raises:
            RuntimeError: If Rust extensions are not available
        """
        if not RUST_AVAILABLE:
            raise RuntimeError(
                "Rust extensions not available. "
                "Please run 'maturin develop' to build the sark_opa extension."
            )

        # Initialize the Rust engine
        self.engine = sark_opa.RustOPAEngine()

        # Set policy directory
        self.policy_dir = policy_dir or Path("opa/policies")

        # Track loaded policies to avoid reloading
        self._loaded_policies: set[str] = set()

        # Initialize cache
        if cache:
            self.cache = cache
        else:
            self.cache = get_policy_cache(enabled=cache_enabled)

        logger.info(
            "rust_opa_client_initialized",
            policy_dir=str(self.policy_dir),
            cache_enabled=self.cache.enabled,
        )

    async def load_policy(self, name: str, rego_code: str) -> None:
        """
        Preload a policy into the engine.

        Args:
            name: Unique identifier for this policy
            rego_code: The Rego policy source code

        Raises:
            OPACompilationError: If the policy cannot be compiled
        """
        try:
            self.engine.load_policy(name, rego_code)
            self._loaded_policies.add(name)

            logger.debug("policy_loaded", policy_name=name)

        except Exception as e:
            logger.error("policy_load_failed", policy_name=name, error=str(e))
            raise

    async def load_policy_from_file(self, policy_path: Path) -> None:
        """
        Load a policy from a .rego file.

        Args:
            policy_path: Path to the .rego file

        Raises:
            FileNotFoundError: If the policy file doesn't exist
            OPACompilationError: If the policy cannot be compiled
        """
        if not policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_path}")

        policy_name = policy_path.stem
        rego_code = policy_path.read_text()

        await self.load_policy(policy_name, rego_code)

    async def ensure_policy_loaded(self, policy_name: str) -> None:
        """
        Ensure a policy is loaded, loading from file if necessary.

        Args:
            policy_name: Name of the policy to load

        Raises:
            FileNotFoundError: If the policy file doesn't exist
        """
        if policy_name in self._loaded_policies:
            return

        # Try to find and load the policy file
        policy_file = self.policy_dir / f"{policy_name}.rego"

        if not policy_file.exists():
            # Try in subdirectories
            policy_files = list(self.policy_dir.rglob(f"{policy_name}.rego"))

            if not policy_files:
                raise FileNotFoundError(
                    f"Policy '{policy_name}' not found in {self.policy_dir}"
                )

            policy_file = policy_files[0]

        await self.load_policy_from_file(policy_file)

    async def evaluate_policy(
        self,
        auth_input: AuthorizationInput,
        use_cache: bool = True,
    ) -> AuthorizationDecision:
        """
        Evaluate authorization policy using the Rust engine.

        Args:
            auth_input: Authorization input containing user, action, tool, and context
            use_cache: Whether to use cache for this request (default: True)

        Returns:
            Authorization decision with allow/deny and reason
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
                logger.debug("cache_hit", user_id=user_id, action=action, resource=resource)
                return AuthorizationDecision(**cached_decision)

        # Cache miss - evaluate using Rust engine
        start_time = time.time()

        try:
            # Determine which policy to use based on action
            policy_query = self._get_policy_query(action)

            # Ensure the policy is loaded
            # For simplicity, we'll try to load gateway_authorization policy
            # In production, you'd have a mapping of action -> policy
            try:
                await self.ensure_policy_loaded("gateway_authorization")
            except FileNotFoundError:
                logger.warning(
                    "policy_not_found",
                    policy="gateway_authorization",
                    using_fallback=True,
                )

            # Prepare input for evaluation
            input_data = auth_input.model_dump()

            # Evaluate the policy using Rust engine
            result = self.engine.evaluate(policy_query, input_data)

            evaluation_latency_ms = (time.time() - start_time) * 1000

            # Parse the result
            # Regorus returns the raw evaluation result, which might be a boolean or object
            if isinstance(result, bool):
                allow = result
                reason = "Policy evaluation completed"
                filtered_parameters = None
                audit_id = None
            elif isinstance(result, dict):
                allow = result.get("allow", False)
                reason = result.get("reason", "Policy evaluation completed")
                filtered_parameters = result.get("filtered_parameters")
                audit_id = result.get("audit_id")
            else:
                # Unexpected result type, default to deny
                logger.warning("unexpected_result_type", result_type=type(result).__name__)
                allow = False
                reason = "Unexpected policy result format"
                filtered_parameters = None
                audit_id = None

            decision = AuthorizationDecision(
                allow=allow,
                reason=reason,
                filtered_parameters=filtered_parameters,
                audit_id=audit_id,
            )

            # Cache the decision
            if use_cache and self.cache.enabled:
                ttl_seconds = self._get_cache_ttl(auth_input)

                await self.cache.set(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    decision=decision.model_dump(),
                    context=auth_input.context,
                    ttl_seconds=ttl_seconds,
                )

            # Record evaluation latency
            self.cache.record_opa_latency(evaluation_latency_ms)

            logger.info(
                "policy_evaluated_rust",
                decision=decision.allow,
                user_id=user_id,
                action=action,
                resource=resource,
                rust_latency_ms=round(evaluation_latency_ms, 2),
            )

            return decision

        except Exception as e:
            logger.error(
                "policy_evaluation_failed",
                error=str(e),
                user_id=user_id,
                action=action,
            )
            # Fail closed - deny on error
            return AuthorizationDecision(
                allow=False,
                reason=f"Policy evaluation failed: {e!s}",
            )

    def _get_policy_query(self, action: str) -> str:
        """
        Determine the policy query path based on the action.

        Args:
            action: The action being performed

        Returns:
            OPA query path
        """
        # Map actions to policy queries
        # This is a simplified mapping - in production you'd have a more sophisticated system
        if action.startswith("gateway:"):
            return "data.sark.gateway.allow"
        elif action.startswith("a2a:"):
            return "data.mcp.gateway.a2a.result.allow"
        else:
            return "data.sark.gateway.allow"

    def _get_cache_ttl(self, auth_input: AuthorizationInput) -> int:
        """
        Determine cache TTL based on request context.

        Args:
            auth_input: Authorization input

        Returns:
            TTL in seconds
        """
        sensitivity = self._get_sensitivity(auth_input)

        # Use optimized TTL settings from cache if available
        if hasattr(self.cache, "use_optimized_ttl") and self.cache.use_optimized_ttl:
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
            Sensitivity level
        """
        if auth_input.tool:
            return auth_input.tool.get("sensitivity_level", "default")
        elif auth_input.server:
            return auth_input.server.get("sensitivity_level", "default")
        return "default"

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
        """Close cache connection."""
        await self.cache.close()

    async def health_check(self) -> dict[str, bool]:
        """
        Check Rust engine and cache health status.

        Returns:
            Dictionary with health status
        """
        engine_healthy = True
        cache_healthy = False

        try:
            # Simple health check - try to get loaded policies
            _ = self.engine.loaded_policies()
        except Exception as e:
            logger.error("rust_engine_health_check_failed", error=str(e))
            engine_healthy = False

        # Check cache health
        cache_healthy = await self.cache.health_check()

        return {
            "rust_engine": engine_healthy,
            "cache": cache_healthy,
            "overall": engine_healthy and cache_healthy,
        }

    def get_loaded_policies(self) -> list[str]:
        """
        Get list of loaded policies.

        Returns:
            List of policy names
        """
        return self.engine.loaded_policies()
