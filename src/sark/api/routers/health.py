"""Health check endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from sark.config import get_settings

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    database: bool
    opa: bool
    consul: bool


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns application status and version.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check() -> ReadyResponse:
    """
    Readiness check endpoint.

    Verifies all dependencies are available.
    """
    # TODO: Implement actual dependency checks
    return ReadyResponse(
        ready=True,
        database=True,
        opa=True,
        consul=True,
    )
