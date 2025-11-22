"""SARK FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from sark.api.routers import health, policy, servers
from sark.api.middleware.security_headers import add_security_middleware
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

    # Security headers and CSRF protection
    add_security_middleware(
        app,
        enable_hsts=(settings.environment == "production"),
        enable_csrf=True,
        csp_policy="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        csrf_exempt_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
    )

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
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
