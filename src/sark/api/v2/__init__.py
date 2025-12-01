"""
SARK API v2 - Protocol-agnostic governance endpoints.

This module provides the v2 API for SARK, which supports multiple protocols
through the adapter architecture.

In v1.x, these endpoints are stubs that return "coming soon" messages.
In v2.0, they will be fully implemented.
"""

from fastapi import APIRouter

# Create v2 router
router = APIRouter(prefix="/api/v2", tags=["v2"])


@router.get("/status")
async def v2_status():
    """
    Get v2 API status.
    
    Returns information about v2 API availability and features.
    """
    return {
        "status": "preview",
        "message": "SARK v2 API is in development. Full implementation coming in v2.0.",
        "version": "2.0.0-preview",
        "features": {
            "protocol_adapters": "planned",
            "federation": "planned",
            "cost_attribution": "planned",
            "programmatic_policies": "planned"
        },
        "available_endpoints": [
            "GET /api/v2/status",
            "GET /api/v2/adapters (coming soon)",
            "POST /api/v2/resources (coming soon)",
            "GET /api/v2/resources (coming soon)",
        ]
    }


@router.get("/adapters")
async def list_adapters():
    """
    List available protocol adapters.
    
    In v2.0, this will return all registered adapters.
    For v1.x, this is a preview endpoint.
    """
    from sark.adapters import get_registry
    
    registry = get_registry()
    info = registry.get_info()
    
    return {
        "status": "preview",
        "message": "Adapter registry is ready but no adapters are implemented yet",
        "registry": info,
        "note": "Full adapter implementation coming in v2.0"
    }


__all__ = ["router"]