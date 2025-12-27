"""Health check endpoints with dependency validation."""

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel
import valkey.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import structlog

from sark.config import get_settings
from sark.services.policy import OPAClient

router = APIRouter()
settings = get_settings()
logger = structlog.get_logger()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str


class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    healthy: bool
    latency_ms: float | None = None
    error: str | None = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with all dependencies."""

    status: str
    version: str
    environment: str
    dependencies: dict[str, DependencyStatus]
    overall_healthy: bool


class ReadyResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    database: bool
    redis: bool
    opa: bool


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint (liveness probe).

    Returns application status and version.
    This is a lightweight check that just verifies the app is running.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/live", response_model=HealthResponse)
async def liveness_check() -> HealthResponse:
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the application process is alive.
    """
    return HealthResponse(
        status="alive",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check() -> ReadyResponse:
    """
    Readiness check endpoint (readiness probe).

    Verifies all critical dependencies are available.
    Returns 200 only if all dependencies are healthy.
    """
    # Check all dependencies in parallel
    db_healthy, redis_healthy, opa_healthy = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        check_opa_health(),
        return_exceptions=True,
    )

    # Handle exceptions
    db_status = db_healthy if isinstance(db_healthy, bool) else False
    redis_status = redis_healthy if isinstance(redis_healthy, bool) else False
    opa_status = opa_healthy if isinstance(opa_healthy, bool) else False

    overall_ready = db_status and redis_status and opa_status

    return ReadyResponse(
        ready=overall_ready,
        database=db_status,
        redis=redis_status,
        opa=opa_status,
    )


@router.get("/startup", response_model=HealthResponse)
async def startup_check() -> HealthResponse:
    """
    Kubernetes startup probe endpoint.

    Returns 200 when the application has completed initialization.
    """
    # For now, same as liveness check
    # In production, might check if migrations are complete, etc.
    return HealthResponse(
        status="started",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check with individual dependency status.

    Checks all dependencies and returns individual status for each.
    Useful for debugging and monitoring dashboards.
    """
    import time

    dependencies: dict[str, DependencyStatus] = {}

    # Check PostgreSQL
    start = time.time()
    try:
        db_healthy = await check_database_health()
        latency = (time.time() - start) * 1000
        dependencies["postgresql"] = DependencyStatus(
            healthy=db_healthy,
            latency_ms=latency,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        dependencies["postgresql"] = DependencyStatus(
            healthy=False,
            latency_ms=latency,
            error=str(e),
        )

    # Check Redis
    start = time.time()
    try:
        redis_healthy = await check_redis_health()
        latency = (time.time() - start) * 1000
        dependencies["redis"] = DependencyStatus(
            healthy=redis_healthy,
            latency_ms=latency,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        dependencies["redis"] = DependencyStatus(
            healthy=False,
            latency_ms=latency,
            error=str(e),
        )

    # Check OPA
    start = time.time()
    try:
        opa_healthy = await check_opa_health()
        latency = (time.time() - start) * 1000
        dependencies["opa"] = DependencyStatus(
            healthy=opa_healthy,
            latency_ms=latency,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        dependencies["opa"] = DependencyStatus(
            healthy=False,
            latency_ms=latency,
            error=str(e),
        )

    overall_healthy = all(dep.healthy for dep in dependencies.values())

    return DetailedHealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        dependencies=dependencies,
        overall_healthy=overall_healthy,
    )


async def check_database_health() -> bool:
    """
    Check PostgreSQL database connectivity.

    Returns:
        True if database is healthy, False otherwise
    """
    try:
        # Create a temporary engine for health check
        engine = create_async_engine(
            settings.postgres_dsn,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )

        async with engine.connect() as conn:
            # Simple query to verify connection
            await conn.execute(text("SELECT 1"))

        await engine.dispose()
        return True

    except Exception as e:
        logger.warning("database_health_check_failed", error=str(e))
        return False


async def check_redis_health() -> bool:
    """
    Check Redis connectivity.

    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        # Create temporary Redis connection
        redis_client = aioredis.from_url(
            settings.redis_dsn,
            encoding="utf-8",
            decode_responses=True,
        )

        # Simple ping to verify connection
        await redis_client.ping()
        await redis_client.aclose()

        return True

    except Exception as e:
        logger.warning("redis_health_check_failed", error=str(e))
        return False


async def check_opa_health() -> bool:
    """
    Check OPA connectivity.

    Returns:
        True if OPA is healthy, False otherwise
    """
    try:
        opa_client = OPAClient()

        # Check if OPA is responding
        # The health_check method should exist on OPAClient
        is_healthy = await opa_client.health_check()

        await opa_client.close()

        return is_healthy

    except Exception as e:
        logger.warning("opa_health_check_failed", error=str(e))
        return False
