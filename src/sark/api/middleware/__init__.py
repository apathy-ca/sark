"""SARK API middleware."""

from sark.api.middleware.auth import AuthMiddleware
from sark.api.middleware.cache import (
    ResponseCacheMiddleware,
    invalidate_cache,
    invalidate_server_cache,
)
from sark.api.middleware.rate_limit import RateLimitMiddleware
from sark.api.middleware.security_headers import (
    CSRFProtectionMiddleware,
    SecurityHeadersMiddleware,
    add_security_middleware,
)

# Alias for backward compatibility
AuthenticationMiddleware = AuthMiddleware

__all__ = [
    "AuthMiddleware",
    "AuthenticationMiddleware",
    "CSRFProtectionMiddleware",
    "RateLimitMiddleware",
    "ResponseCacheMiddleware",
    "SecurityHeadersMiddleware",
    "add_security_middleware",
    "invalidate_cache",
    "invalidate_server_cache",
]
