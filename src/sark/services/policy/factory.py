"""
Client factories for OPA and cache with Rust/Python routing.

This module provides factory functions that route to either Rust or Python
implementations based on feature flags, with automatic fallback on errors.
"""

import os
from typing import Any, Protocol

import structlog

from sark.services.feature_flags import get_feature_flag_manager
from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import (
    AuthorizationDecision,
    AuthorizationInput,
    OPAClient,
)

# Import Rust implementations
from sark.services.policy.rust_cache import RustPolicyCache, is_rust_cache_available
from sark.services.policy.rust_opa_client import RustOPAClient, RUST_AVAILABLE as OPA_RUST_AVAILABLE

logger = structlog.get_logger()


# Check if Rust libraries are available (from environment variable for feature flag control)
RUST_ENABLED = os.getenv("RUST_ENABLED", "false").lower() == "true"


# Protocol definitions for type checking
class OPAClientProtocol(Protocol):
    """Protocol for OPA client implementations."""

    async def evaluate_policy(
        self, auth_input: AuthorizationInput, use_cache: bool = True
    ) -> AuthorizationDecision:
        """Evaluate authorization policy."""
        ...

    async def close(self) -> None:
        """Close client resources."""
        ...


class PolicyCacheProtocol(Protocol):
    """Protocol for policy cache implementations."""

    async def get(
        self,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Get cached policy decision."""
        ...

    async def set(
        self,
        user_id: str,
        action: str,
        resource: str,
        decision: dict[str, Any],
        context: dict[str, Any] | None = None,
        ttl: int | None = None,
    ) -> None:
        """Set cached policy decision."""
        ...

    async def delete(self, user_id: str, action: str, resource: str) -> None:
        """Delete cached policy decision."""
        ...


# Rust implementations are now imported from rust_opa_client.py and rust_cache.py
# These provide full PyO3 bindings to the grid-core Rust libraries


# Factory functions
def create_opa_client(
    user_id: str,
    opa_url: str | None = None,
    fallback_on_error: bool = True,
) -> OPAClientProtocol:
    """
    Create OPA client based on feature flags.

    Args:
        user_id: User identifier for feature flag routing
        opa_url: OPA server URL (for Python client)
        fallback_on_error: Whether to fallback to Python on Rust errors

    Returns:
        OPA client (Rust or Python implementation)
    """
    feature_flags = get_feature_flag_manager()

    # Always check feature flag for metrics/logging
    should_use_rust = feature_flags.should_use_rust("rust_opa", user_id)

    # Check if user should get Rust implementation
    if RUST_ENABLED and OPA_RUST_AVAILABLE and should_use_rust:
        try:
            logger.info(
                "Creating Rust OPA client",
                user_id=user_id,
                feature="rust_opa",
            )
            return RustOPAClient()
        except Exception as e:
            if fallback_on_error:
                logger.warning(
                    "Rust OPA client initialization failed, falling back to Python",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True,
                )
            else:
                raise

    # Use Python HTTP-based OPA client
    logger.info(
        "Creating Python OPA client",
        user_id=user_id,
        feature="rust_opa",
        rust_enabled=RUST_ENABLED,
        rust_available=OPA_RUST_AVAILABLE,
        should_use_rust=should_use_rust,
    )
    return OPAClient(opa_url=opa_url)


def create_policy_cache(
    user_id: str,
    fallback_on_error: bool = True,
) -> PolicyCacheProtocol:
    """
    Create policy cache based on feature flags.

    Args:
        user_id: User identifier for feature flag routing
        fallback_on_error: Whether to fallback to Python on Rust errors

    Returns:
        Policy cache (Rust or Python implementation)
    """
    feature_flags = get_feature_flag_manager()

    # Always check feature flag for metrics/logging
    should_use_rust = feature_flags.should_use_rust("rust_cache", user_id)

    # Check if user should get Rust implementation
    if RUST_ENABLED and is_rust_cache_available() and should_use_rust:
        try:
            logger.info(
                "Creating Rust policy cache",
                user_id=user_id,
                feature="rust_cache",
            )
            return RustPolicyCache()
        except Exception as e:
            if fallback_on_error:
                logger.warning(
                    "Rust cache initialization failed, falling back to Redis",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True,
                )
            else:
                raise

    # Use Python Redis-based cache
    logger.info(
        "Creating Redis policy cache",
        user_id=user_id,
        feature="rust_cache",
        rust_enabled=RUST_ENABLED,
        rust_available=is_rust_cache_available(),
        should_use_rust=should_use_rust,
    )
    return PolicyCache()


# Convenience functions for getting both clients together
def create_policy_clients(
    user_id: str,
    opa_url: str | None = None,
) -> tuple[OPAClientProtocol, PolicyCacheProtocol]:
    """
    Create both OPA client and policy cache for a user.

    Args:
        user_id: User identifier for feature flag routing
        opa_url: OPA server URL (for Python client)

    Returns:
        Tuple of (opa_client, policy_cache)
    """
    opa_client = create_opa_client(user_id, opa_url)
    policy_cache = create_policy_cache(user_id)

    logger.info(
        "Created policy clients",
        user_id=user_id,
        opa_impl=type(opa_client).__name__,
        cache_impl=type(policy_cache).__name__,
    )

    return opa_client, policy_cache
