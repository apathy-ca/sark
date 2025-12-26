"""
Federation services for SARK v2.0.

This package provides services for cross-organization governance:
- Node discovery (DNS-SD, mDNS)
- mTLS trust establishment
- Federated resource routing
"""

from sark.services.federation.discovery import DiscoveryService
from sark.services.federation.routing import RoutingService
from sark.services.federation.trust import TrustService

__all__ = [
    "DiscoveryService",
    "RoutingService",
    "TrustService",
]
