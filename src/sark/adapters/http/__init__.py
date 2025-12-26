"""
HTTP/REST adapter package for SARK v2.0.

This package provides HTTP/REST API integration through the ProtocolAdapter interface.
Supports OpenAPI discovery, multiple authentication strategies, and advanced features
like rate limiting and circuit breakers.

Version: 2.0.0
Engineer: ENGINEER-2
"""

from sark.adapters.http.authentication import (
    APIKeyStrategy,
    AuthStrategy,
    BasicAuthStrategy,
    BearerAuthStrategy,
    NoAuthStrategy,
    OAuth2Strategy,
)
from sark.adapters.http.discovery import OpenAPIDiscovery
from sark.adapters.http.http_adapter import HTTPAdapter

__all__ = [
    "APIKeyStrategy",
    # Authentication
    "AuthStrategy",
    "BasicAuthStrategy",
    "BearerAuthStrategy",
    # Main adapter
    "HTTPAdapter",
    "NoAuthStrategy",
    "OAuth2Strategy",
    # Discovery
    "OpenAPIDiscovery",
]
