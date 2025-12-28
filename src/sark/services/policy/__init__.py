"""Policy Engine integration service."""

from sark.services.policy.cache import PolicyCache, get_policy_cache
from sark.services.policy.opa_client import OPAClient
from sark.services.policy.policy_service import PolicyService

# Import Rust OPA client if available
try:
    from sark.services.policy.rust_opa_client import RustOPAClient, RUST_AVAILABLE

    __all__ = [
        "OPAClient",
        "RustOPAClient",
        "PolicyCache",
        "PolicyService",
        "get_policy_cache",
        "RUST_AVAILABLE",
    ]
except ImportError:
    RUST_AVAILABLE = False
    __all__ = ["OPAClient", "PolicyCache", "PolicyService", "get_policy_cache"]
