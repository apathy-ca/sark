"""
OPA policy evaluation helper module with Rust/Python routing.

This module provides a unified interface for OPA policy evaluation that
automatically routes to either Rust or Python implementation based on
feature flags.
"""

import time
from typing import Any

import structlog

from sark.services.policy.factory import create_opa_client, create_policy_cache
from sark.services.policy.opa_client import AuthorizationInput
from sark.api.metrics.rollout_metrics import (
    record_opa_evaluation,
    record_opa_error,
    record_feature_flag_assignment,
    record_cache_operation,
)

logger = structlog.get_logger()


async def evaluate_policy(
    policy_path: str,
    input_data: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate OPA policy with Rust/Python routing and metrics.

    This function routes to either Rust or Python OPA implementation based
    on feature flags, tracks metrics, and handles caching.

    Args:
        policy_path: OPA policy path (e.g., "/v1/data/mcp/gateway/allow")
        input_data: Policy input data
        user_id: User ID for feature flag routing (defaults to user from input_data)

    Returns:
        OPA evaluation result with format: {"result": {"allow": bool, "reason": str, ...}}
    """
    # Extract user_id if not provided
    if user_id is None:
        user_id = input_data.get("user", {}).get("id", "unknown")

    # Create clients via factory (routes based on feature flags)
    opa_client = create_opa_client(user_id)
    policy_cache = create_policy_cache(user_id)

    # Determine which implementation was selected
    impl = "rust" if "Rust" in type(opa_client).__name__ else "python"

    # Record feature flag assignment
    record_feature_flag_assignment("rust_opa", impl)
    record_feature_flag_assignment("rust_cache", impl)

    # Build cache key
    action = input_data.get("action", "unknown")
    resource = _extract_resource_id(input_data)

    # Try cache first
    cache_start = time.time()
    try:
        cached_decision = await policy_cache.get(
            user_id=user_id,
            action=action,
            resource=resource,
            context=input_data,
        )
        cache_duration = time.time() - cache_start

        if cached_decision:
            record_cache_operation(impl, "get", cache_duration, "hit")
            logger.info(
                "policy_cache_hit",
                user_id=user_id,
                action=action,
                resource=resource,
                implementation=impl,
            )
            return {"result": cached_decision}
        else:
            record_cache_operation(impl, "get", cache_duration, "miss")
    except Exception as e:
        cache_duration = time.time() - cache_start
        record_cache_operation(impl, "get", cache_duration, "error")
        logger.warning(
            "policy_cache_error",
            error=str(e),
            user_id=user_id,
        )

    # Evaluate with OPA
    opa_start = time.time()
    try:
        # Convert input_data to AuthorizationInput
        resource = input_data.get("resource", {})
        tool = resource.get("tool")

        # Ensure tool is a dict if provided
        if tool and not isinstance(tool, dict):
            tool = {"name": tool}

        auth_input = AuthorizationInput(
            user=input_data.get("user", {}),
            action=action,
            tool=tool,
            server=resource,
            context=input_data.get("context", {}),
        )

        # Evaluate policy
        decision = await opa_client.evaluate_policy(auth_input, use_cache=False)
        opa_duration = time.time() - opa_start

        # Record metrics
        result = "allow" if decision.allow else "deny"
        record_opa_evaluation(impl, opa_duration, result)

        # Cache the decision
        cache_start = time.time()
        try:
            decision_dict = {
                "allow": decision.allow,
                "reason": decision.reason,
                "filtered_parameters": decision.filtered_parameters,
            }

            await policy_cache.set(
                user_id=user_id,
                action=action,
                resource=resource,
                decision=decision_dict,
                context=input_data,
            )
            cache_duration = time.time() - cache_start
            record_cache_operation(impl, "set", cache_duration, "hit")
        except Exception as e:
            cache_duration = time.time() - cache_start
            record_cache_operation(impl, "set", cache_duration, "error")
            logger.warning(
                "policy_cache_set_error",
                error=str(e),
                user_id=user_id,
            )

        logger.info(
            "policy_evaluated",
            user_id=user_id,
            action=action,
            resource=resource,
            allow=decision.allow,
            implementation=impl,
            duration_ms=opa_duration * 1000,
        )

        return {
            "result": {
                "allow": decision.allow,
                "reason": decision.reason,
                "filtered_parameters": decision.filtered_parameters,
            }
        }

    except Exception as e:
        opa_duration = time.time() - opa_start

        # Determine error type
        error_type = type(e).__name__
        if "timeout" in str(e).lower():
            error_type = "timeout"
        elif "connection" in str(e).lower():
            error_type = "connection"
        else:
            error_type = "evaluation"

        record_opa_error(impl, error_type)

        logger.error(
            "policy_evaluation_error",
            error=str(e),
            error_type=error_type,
            user_id=user_id,
            action=action,
            resource=resource,
            implementation=impl,
            exc_info=True,
        )

        # Re-raise for proper error handling by caller
        raise


def _extract_resource_id(input_data: dict[str, Any]) -> str:
    """
    Extract a resource identifier from OPA input data.

    Args:
        input_data: OPA policy input data

    Returns:
        Resource identifier string
    """
    resource = input_data.get("resource", {})

    # Try different resource types (check type before server for precedence)
    if "tool" in resource:
        tool_name = resource.get("tool", {}).get("name") if isinstance(
            resource.get("tool"), dict
        ) else resource.get("tool")
        server = resource.get("server", "unknown")
        return f"tool:{server}/{tool_name}"
    elif "type" in resource:
        return f"{resource['type']}:{resource.get('server', 'unknown')}"
    elif "server" in resource:
        return f"server:{resource['server']}"
    else:
        return "unknown"
