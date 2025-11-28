"""
Protocol adapters for SARK v2.0.

This module provides the adapter infrastructure for supporting multiple protocols.
In v1.x, this is a stub that will be fully implemented in v2.0.
"""

from sark.adapters.registry import AdapterRegistry, get_registry

__all__ = [
    "AdapterRegistry",
    "get_registry",
]