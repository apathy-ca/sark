"""Health check endpoints for Kubernetes liveness and readiness probes."""

import logging
import os
import time
from typing import Any

from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Track application start time
START_TIME = time.time()


def get_uptime() -> float:
    """Calculate application uptime in seconds."""
    return time.time() - START_TIME


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint.

    This is a simple endpoint that returns 200 OK if the application is running.
    Used for basic smoke tests and service verification.

    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "uptime": get_uptime(),
        "version": os.getenv("APP_VERSION", "0.1.0"),
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(response: Response) -> dict[str, Any]:
    """
    Readiness probe endpoint for Kubernetes.

    This endpoint checks if the application is ready to accept traffic.
    Returns 200 if ready, 503 if not ready.

    In a real application, this should check:
    - Database connectivity
    - Required external services
    - Cache availability
    - Any other critical dependencies

    Returns:
        dict: Readiness status information
    """
    checks: dict[str, bool] = {
        "application": True,
        # Add more checks as needed:
        # "database": await check_database(),
        # "cache": await check_cache(),
        # "external_api": await check_external_api(),
    }

    all_ready = all(checks.values())

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning("Readiness check failed: %s", checks)

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "uptime": get_uptime(),
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check(response: Response) -> dict[str, Any]:
    """
    Liveness probe endpoint for Kubernetes.

    This endpoint checks if the application is alive and not deadlocked.
    Returns 200 if alive, 503 if the application should be restarted.

    In a real application, this should detect:
    - Deadlocks
    - Unrecoverable errors
    - Resource exhaustion
    - Thread pool exhaustion

    Returns:
        dict: Liveness status information
    """
    # Basic liveness check - if we can respond, we're alive
    # Add more sophisticated checks as needed
    is_alive = True

    # Example check: ensure we haven't exceeded max memory or other critical resources
    # is_alive = check_critical_resources()

    if not is_alive:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.error("Liveness check failed - application should be restarted")

    return {
        "status": "alive" if is_alive else "dead",
        "uptime": get_uptime(),
    }


@router.get("/startup", status_code=status.HTTP_200_OK)
async def startup_check(response: Response) -> dict[str, Any]:
    """
    Startup probe endpoint for Kubernetes.

    This endpoint checks if the application has completed initialization.
    Returns 200 once startup is complete, 503 during startup.

    Useful for applications with long initialization times.

    Returns:
        dict: Startup status information
    """
    # Simple time-based startup check (application is ready after 5 seconds)
    # In a real app, check actual initialization state
    startup_complete = get_uptime() > 5.0

    if not startup_complete:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "started" if startup_complete else "starting",
        "uptime": get_uptime(),
    }
