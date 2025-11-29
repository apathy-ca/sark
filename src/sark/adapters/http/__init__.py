"""
HTTP/REST adapter package for SARK v2.0.

This package provides HTTP/REST API integration through the ProtocolAdapter interface.
Supports OpenAPI discovery, multiple authentication strategies, and advanced features
like rate limiting and circuit breakers.

Version: 2.0.0
Engineer: ENGINEER-2
"""

from sark.adapters.http.http_adapter import HTTPAdapter
from sark.adapters.http.authentication import (
    AuthStrategy,
    NoAuthStrategy,
    BasicAuthStrategy,
    BearerAuthStrategy,
    OAuth2Strategy,
    APIKeyStrategy,
)
from sark.adapters.http.discovery import OpenAPIDiscovery

__all__ = [
    # Main adapter
    "HTTPAdapter",

    # Authentication
    "AuthStrategy",
    "NoAuthStrategy",
    "BasicAuthStrategy",
    "BearerAuthStrategy",
    "OAuth2Strategy",
    "APIKeyStrategy",

    # Discovery
    "OpenAPIDiscovery",
]
