"""SARK API middleware."""

from sark.api.middleware.auth import AuthMiddleware

# Alias for backward compatibility
AuthenticationMiddleware = AuthMiddleware
from sark.api.middleware.cache import ResponseCacheMiddleware, invalidate_cache, invalidate_server_cache
from sark.api.middleware.rate_limit import RateLimitMiddleware
from sark.api.middleware.security_headers import (
    CSRFProtectionMiddleware,
    SecurityHeadersMiddleware,
    add_security_middleware,
)

__all__ = [
    "AuthenticationMiddleware",
    "AuthMiddleware",
    "RateLimitMiddleware",
    "ResponseCacheMiddleware",
    "invalidate_cache",
    "invalidate_server_cache",
    "CSRFProtectionMiddleware",
    "SecurityHeadersMiddleware",
    "add_security_middleware",
]
