"""
Protocol adapters for SARK v2.0.

This module provides the adapter infrastructure for supporting multiple protocols.

Version: 2.0.0
Status: Foundation complete (Week 1), MCP adapter complete (Week 2), HTTP adapter complete (Week 2-4), gRPC adapter complete (Week 2-4)
"""

from sark.adapters import exceptions
from sark.adapters.base import ProtocolAdapter
from sark.adapters.registry import AdapterRegistry, get_registry, reset_registry

# Import adapters (conditional to avoid import errors if deps missing)
try:
    from sark.adapters.mcp_adapter import MCPAdapter

    _mcp_available = True
except ImportError:
    _mcp_available = False

try:
    from sark.adapters.http import HTTPAdapter

    _http_available = True
except ImportError:
    _http_available = False

try:
    from sark.adapters.grpc_adapter import GRPCAdapter

    _grpc_available = True
except ImportError:
    _grpc_available = False

__all__ = [
    # Core interface
    "ProtocolAdapter",
    # Registry
    "AdapterRegistry",
    "get_registry",
    "reset_registry",
    # Exceptions module (import with: from sark.adapters.exceptions import ...)
    "exceptions",
]

# Conditionally export adapters
if _mcp_available:
    __all__.append("MCPAdapter")

if _http_available:
    __all__.append("HTTPAdapter")

if _grpc_available:
    __all__.append("GRPCAdapter")
