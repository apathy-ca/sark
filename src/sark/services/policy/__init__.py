"""Policy Engine integration service."""

from sark.services.policy.cache import PolicyCache, get_policy_cache
from sark.services.policy.cache_cleanup import (
    CacheCleanupTask,
    get_cleanup_task,
    start_cache_cleanup,
    stop_cache_cleanup,
)
from sark.services.policy.opa_client import OPAClient
from sark.services.policy.policy_service import PolicyService
from sark.services.policy.rust_cache import (
    RustPolicyCache,
    get_rust_policy_cache,
    is_rust_cache_available,
)

# Import Rust OPA client if available
try:
    from sark.services.policy.rust_opa_client import RUST_AVAILABLE, RustOPAClient

    __all__ = [
        "RUST_AVAILABLE",
        "CacheCleanupTask",
        "OPAClient",
        "PolicyCache",
        "PolicyService",
        "RustOPAClient",
        "RustPolicyCache",
        "get_cleanup_task",
        "get_policy_cache",
        "get_rust_policy_cache",
        "is_rust_cache_available",
        "start_cache_cleanup",
        "stop_cache_cleanup",
    ]
except ImportError:
    RUST_AVAILABLE = False
    __all__ = [
        "CacheCleanupTask",
        "OPAClient",
        "PolicyCache",
        "PolicyService",
        "RustPolicyCache",
        "get_cleanup_task",
        "get_policy_cache",
        "get_rust_policy_cache",
        "is_rust_cache_available",
        "start_cache_cleanup",
        "stop_cache_cleanup",
    ]
