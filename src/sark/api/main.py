"""SARK FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from sark.api.middleware import AuthMiddleware
from sark.api.routers import auth, health, policy, servers
from sark.config import get_settings
from sark.db import init_db

logger = structlog.get_logger()
settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="SARK API",
        description="Security Audit and Resource Kontroler for MCP Governance",
        version=settings.app_version,
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Authentication middleware
    # Note: Add middleware in reverse order - they execute in LIFO order
    app.add_middleware(AuthMiddleware, settings=settings)

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(servers.router, prefix="/api/v1/servers", tags=["servers"])
    app.include_router(policy.router, prefix="/api/v1/policy", tags=["policy"])

    # Prometheus metrics endpoint
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize application on startup."""
        logger.info(
            "application_startup",
            app_name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        )

        # Initialize database
        await init_db()

        logger.info("database_initialized")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Cleanup on shutdown."""
        logger.info("application_shutdown")

    return app


app = create_app()
