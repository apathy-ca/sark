"""Gateway integration services.

Provides:
- Authorization for Gateway operations
- Gateway HTTP client (placeholder)
- Server and tool filtering
"""

from sark.services.gateway.authorization import (
    authorize_a2a_request,
    authorize_gateway_request,
    filter_servers_by_permission,
    filter_tools_by_permission,
)
from sark.services.gateway.client import GatewayClient, get_gateway_client

__all__ = [
    "GatewayClient",
    "authorize_a2a_request",
    "authorize_gateway_request",
    "filter_servers_by_permission",
    "filter_tools_by_permission",
    "get_gateway_client",
]
