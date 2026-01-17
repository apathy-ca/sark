"""Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from sark.config import get_settings
from sark.health import router as health_router
from sark.logging_config import setup_logging
from sark.metrics import PrometheusMiddleware, get_metrics, initialize_metrics
from sark.api.routers import admin, export, health as health_v2, websocket

settings = get_settings()

# Setup logging
setup_logging(level=settings.log_level, json_logs=settings.json_logs)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Starting %s version %s in %s environment",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )

    # Initialize metrics
    if settings.enable_metrics:
        initialize_metrics(
            version=settings.app_version,
            environment=settings.environment,
        )
        logger.info("Prometheus metrics initialized")

    yield

    # Shutdown
    logger.info("Shutting down %s", settings.app_name)


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A cloud-ready Python application",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics middleware
if settings.enable_metrics:
    app.add_middleware(PrometheusMiddleware)

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(admin.router, tags=["admin"])
app.include_router(export.router, tags=["export"])
app.include_router(health_v2.router, prefix="/health", tags=["health-v2"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    This endpoint exposes application metrics in Prometheus format.
    Should be scraped by Prometheus or similar monitoring systems.
    """
    if not settings.enable_metrics:
        return Response(content="Metrics disabled", status_code=404)

    metrics_data, content_type = get_metrics()
    return Response(content=metrics_data, media_type=content_type)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "sark.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
    )
