"""SARK FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from sark.api.middleware import AuthMiddleware
from sark.api.middleware.security_headers import add_security_middleware
from sark.api.routers import auth, bulk, health, metrics, policy, servers, tools
from sark.config import get_settings
from sark.db import init_db

logger = structlog.get_logger()
settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="SARK API",
        description="""
# Security Audit and Resource Kontroler for MCP Governance

SARK provides enterprise-grade governance for Model Context Protocol (MCP) deployments,
offering centralized management, policy enforcement, and comprehensive audit trails.

## Key Features

- **Zero-trust security** - Multi-layer authorization and authentication
- **Automated discovery** - Find and register MCP servers automatically
- **Policy-based authorization** - Fine-grained control via Open Policy Agent
- **Comprehensive audit** - Immutable audit trails for compliance
- **Scalable architecture** - Supports 10,000+ MCP servers

## Authentication

SARK supports multiple authentication methods:
- **API Keys** - For automation and service-to-service communication
- **JWT Tokens** - For user sessions with automatic refresh
- **LDAP** - For enterprise Active Directory integration
- **OIDC/OAuth2** - For SSO with identity providers

## Getting Started

1. Create an API key: `POST /api/auth/api-keys`
2. Register an MCP server: `POST /api/v1/servers`
3. Query servers: `GET /api/v1/servers`

See the documentation for complete details.
        """,
        version=settings.app_version,
        debug=settings.debug,
        contact={
            "name": "SARK Team",
            "url": "https://github.com/apathy-ca/sark",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server",
            },
            {
                "url": "https://api.sark.example.com",
                "description": "Production server",
            },
        ],
        openapi_tags=[
            {
                "name": "health",
                "description": "Health check and readiness endpoints for Kubernetes probes",
            },
            {
                "name": "authentication",
                "description": "Multi-provider authentication (LDAP, OIDC, SAML) and session management",
            },
            {
                "name": "servers",
                "description": "MCP server registration, discovery, and management",
            },
            {
                "name": "policy",
                "description": "Policy evaluation and authorization decisions via OPA",
            },
            {
                "name": "tools",
                "description": "MCP tool sensitivity classification and management",
            },
            {
                "name": "bulk",
                "description": "Bulk operations for server registration and updates",
            },
            {
                "name": "metrics",
                "description": "Server metrics, statistics, and time-series data",
            },
        ],
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

    # Authentication middleware
    # Note: Add middleware in reverse order - they execute in LIFO order
    app.add_middleware(AuthMiddleware, settings=settings)

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(servers.router, prefix="/api/v1/servers", tags=["servers"])
    app.include_router(policy.router, prefix="/api/v1/policy", tags=["policy"])
    app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
    app.include_router(bulk.router, prefix="/api/v1/bulk", tags=["bulk"])
    app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])

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
