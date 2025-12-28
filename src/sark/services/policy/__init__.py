"""Policy Engine integration service."""

from sark.services.policy.cache import PolicyCache, get_policy_cache
from sark.services.policy.cache_cleanup import (
    CacheCleanupTask,
    start_cache_cleanup,
    stop_cache_cleanup,
    get_cleanup_task,
)
from sark.services.policy.opa_client import OPAClient
from sark.services.policy.policy_service import PolicyService
from sark.services.policy.rust_cache import (
    RustPolicyCache,
    get_rust_policy_cache,
    is_rust_cache_available,
)

__all__ = [
    "OPAClient",
    "PolicyCache",
    "PolicyService",
    "get_policy_cache",
    "RustPolicyCache",
    "get_rust_policy_cache",
    "is_rust_cache_available",
    "CacheCleanupTask",
    "start_cache_cleanup",
    "stop_cache_cleanup",
    "get_cleanup_task",
]
