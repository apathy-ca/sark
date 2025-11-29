"""
Protocol adapters for SARK v2.0.

This module provides the adapter infrastructure for supporting multiple protocols.

Version: 2.0.0
Status: Foundation complete (Week 1)
"""

from sark.adapters.base import ProtocolAdapter
from sark.adapters.registry import AdapterRegistry, get_registry, reset_registry
from sark.adapters import exceptions

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