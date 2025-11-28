# Building a Complete MCP Gateway Server

**Level:** Intermediate
**Time:** 60-90 minutes
**Prerequisites:** [Tutorial 1: Quick Start Guide](./01-quickstart-guide.md)

---

## Overview

In this tutorial, you'll build a **production-ready MCP Gateway server** from scratch that integrates with SARK for authorization. You'll learn:

- 🏗️ **Architecture**: Design a scalable Gateway server structure
- 🔧 **Implementation**: Build multiple tool endpoints with type safety
- 🔐 **Security**: Implement authentication and authorization flow
- 📋 **OPA Integration**: Create and test custom policies
- 🚀 **Deployment**: Deploy to a development environment

By the end, you'll have a fully functional Gateway server that can:
- Authenticate users via JWT tokens
- Route requests to multiple MCP servers
- Enforce fine-grained authorization via SARK/OPA
- Log comprehensive audit trails
- Handle errors gracefully

---

## Project Structure

We'll build this directory structure:

```
gateway-server/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py      # JWT validation
│   │   └── sark_client.py      # SARK authorization client
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py           # Health check endpoints
│   │   ├── tools.py            # Tool invocation routes
│   │   └── servers.py          # Server discovery routes
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── client.py           # MCP client wrapper
│   │   └── registry.py         # Server registry
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py         # Request models
│   │   └── responses.py        # Response models
│   └── middleware/
│       ├── __init__.py
│       ├── logging.py          # Structured logging
│       └── error_handler.py    # Global error handling
├── policies/
│   ├── gateway.rego            # OPA policies
│   └── test_data/              # Policy test cases
├── tests/
│   ├── test_auth.py
│   ├── test_tools.py
│   └── test_integration.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Part 1: Project Setup

### Step 1.1: Create Project Directory

```bash
# Create project directory
mkdir -p gateway-server
cd gateway-server

# Create directory structure
mkdir -p src/{auth,routers,mcp,models,middleware}
mkdir -p policies/test_data
mkdir -p tests

# Create __init__.py files
touch src/__init__.py
touch src/auth/__init__.py
touch src/routers/__init__.py
touch src/mcp/__init__.py
touch src/models/__init__.py
touch src/middleware/__init__.py
```

### Step 1.2: Create requirements.txt

```bash
cat > requirements.txt << 'EOF'
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# HTTP Client
httpx==0.25.1
aiohttp==3.9.1

# Authentication
python-jose[cryptography]==3.3.0
pydantic[email]==2.5.0

# Logging & Monitoring
structlog==23.2.0
prometheus-client==0.19.0

# MCP SDK
mcp-sdk==0.1.0  # Placeholder - use actual MCP SDK

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.1

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
ruff==0.1.6
EOF
```

### Step 1.3: Create .env File

```bash
cat > .env << 'EOF'
# Gateway Configuration
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8080
GATEWAY_ENV=development
LOG_LEVEL=INFO

# SARK Integration
SARK_URL=http://localhost:8000
SARK_TIMEOUT=10.0

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_ISSUER=gateway-server

# MCP Server Registry
MCP_SERVERS_CONFIG=mcp_servers.yaml
EOF
```

---

## Part 2: Configuration Management

### Step 2.1: Create Configuration Module

Create `src/config.py`:

```python
"""Configuration management for Gateway server."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gateway server configuration."""

    # Server Configuration
    gateway_host: str = Field(default="0.0.0.0", description="Gateway host")
    gateway_port: int = Field(default=8080, description="Gateway port")
    gateway_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )

    # SARK Integration
    sark_url: str = Field(
        default="http://localhost:8000", description="SARK API base URL"
    )
    sark_timeout: float = Field(
        default=10.0, description="SARK API timeout in seconds"
    )

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="", description="JWT secret key for validation"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_issuer: str = Field(
        default="gateway-server", description="JWT issuer"
    )

    # MCP Configuration
    mcp_servers_config: str = Field(
        default="mcp_servers.yaml",
        description="Path to MCP servers configuration file",
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key is set."""
        if not v or v == "your-secret-key-here-change-in-production":
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure random value"
            )
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

**What this does:**
- ✅ Type-safe configuration with Pydantic
- ✅ Environment variable loading from `.env`
- ✅ Validation for critical settings (JWT secret)
- ✅ Cached for performance

---

## Part 3: Authentication & Authorization

### Step 3.1: JWT Token Validation

Create `src/auth/jwt_handler.py`:

```python
"""JWT token validation and user extraction."""

from datetime import datetime
from typing import Any

import structlog
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config import get_settings

logger = structlog.get_logger()
security = HTTPBearer()


class UserContext:
    """User context extracted from JWT token."""

    def __init__(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        teams: list[str] | None = None,
    ):
        self.user_id = user_id
        self.email = email
        self.roles = roles
        self.teams = teams or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for SARK authorization."""
        return {
            "id": self.user_id,
            "email": self.email,
            "roles": self.roles,
            "teams": self.teams,
        }


def validate_jwt_token(
    credentials: HTTPAuthorizationCredentials,
) -> UserContext:
    """
    Validate JWT token and extract user context.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        UserContext with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_iss": True},
            issuer=settings.jwt_issuer,
        )

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        # Extract user information
        user_id = payload.get("sub")
        email = payload.get("email")
        roles = payload.get("roles", [])
        teams = payload.get("teams", [])

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing required claims",
            )

        logger.info(
            "jwt_validated",
            user_id=user_id,
            email=email,
            roles=roles,
        )

        return UserContext(
            user_id=user_id,
            email=email,
            roles=roles,
            teams=teams,
        )

    except JWTError as e:
        logger.error("jwt_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
```

### Step 3.2: SARK Authorization Client

Create `src/auth/sark_client.py`:

```python
"""Client for SARK authorization API."""

import asyncio
from typing import Any

import httpx
import structlog

from src.auth.jwt_handler import UserContext
from src.config import get_settings

logger = structlog.get_logger()


class SARKAuthorizationError(Exception):
    """SARK authorization request failed."""

    pass


class SARKClient:
    """Client for SARK Gateway authorization API."""

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            base_url=self.settings.sark_url,
            timeout=self.settings.sark_timeout,
        )

    async def authorize_tool_invocation(
        self,
        user: UserContext,
        server_name: str,
        tool_name: str,
        parameters: dict[str, Any],
        gateway_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Request authorization from SARK for tool invocation.

        Args:
            user: User context from JWT token
            server_name: MCP server name
            tool_name: Tool name to invoke
            parameters: Tool parameters
            gateway_metadata: Additional Gateway metadata

        Returns:
            Authorization response from SARK

        Raises:
            SARKAuthorizationError: If authorization request fails
        """
        try:
            response = await self.client.post(
                "/api/v1/gateway/authorize",
                json={
                    "action": "gateway:tool:invoke",
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "user": user.to_dict(),
                    "gateway_metadata": gateway_metadata or {},
                },
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                "sark_authorization",
                user_id=user.user_id,
                server=server_name,
                tool=tool_name,
                decision=result.get("allow"),
            )

            return result

        except httpx.HTTPError as e:
            logger.error(
                "sark_authorization_failed",
                user_id=user.user_id,
                server=server_name,
                tool=tool_name,
                error=str(e),
            )
            raise SARKAuthorizationError(
                f"SARK authorization request failed: {str(e)}"
            )

    async def list_authorized_servers(
        self, user: UserContext
    ) -> list[dict[str, Any]]:
        """
        List MCP servers the user is authorized to access.

        Args:
            user: User context from JWT token

        Returns:
            List of authorized servers
        """
        try:
            response = await self.client.get(
                "/api/v1/gateway/servers",
                params={"user_id": user.user_id},
            )

            response.raise_for_status()
            result = response.json()

            return result.get("servers", [])

        except httpx.HTTPError as e:
            logger.error(
                "sark_list_servers_failed",
                user_id=user.user_id,
                error=str(e),
            )
            raise SARKAuthorizationError(
                f"Failed to list servers: {str(e)}"
            )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
```

**What this does:**
- ✅ Sends authorization requests to SARK
- ✅ Handles filtered parameters from policy
- ✅ Lists authorized servers for a user
- ✅ Comprehensive error handling and logging

---

## Part 4: Data Models

### Step 4.1: Request Models

Create `src/models/requests.py`:

```python
"""Request models for Gateway API."""

from typing import Any

from pydantic import BaseModel, Field


class ToolInvocationRequest(BaseModel):
    """Request to invoke a tool on an MCP server."""

    server_name: str = Field(
        ..., description="MCP server name", example="postgres-mcp"
    )
    tool_name: str = Field(
        ..., description="Tool name to invoke", example="execute_query"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool parameters",
        example={"query": "SELECT * FROM users", "params": []},
    )


class ServerListRequest(BaseModel):
    """Request to list available servers."""

    include_tools: bool = Field(
        default=False, description="Include tool list for each server"
    )
```

### Step 4.2: Response Models

Create `src/models/responses.py`:

```python
"""Response models for Gateway API."""

from typing import Any

from pydantic import BaseModel, Field


class ToolInvocationResponse(BaseModel):
    """Response from tool invocation."""

    success: bool = Field(..., description="Whether invocation succeeded")
    result: Any = Field(None, description="Tool execution result")
    error: str | None = Field(None, description="Error message if failed")
    audit_id: str | None = Field(
        None, description="SARK audit event ID"
    )


class ServerInfo(BaseModel):
    """Information about an MCP server."""

    name: str = Field(..., description="Server name")
    url: str = Field(..., description="Server URL")
    description: str | None = Field(None, description="Server description")
    allowed_actions: list[str] = Field(
        default_factory=list, description="Allowed actions for this server"
    )
    tools: list[dict[str, Any]] = Field(
        default_factory=list, description="Available tools"
    )


class ServerListResponse(BaseModel):
    """Response with list of servers."""

    servers: list[ServerInfo] = Field(..., description="List of servers")
    total: int = Field(..., description="Total number of servers")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Gateway version")
    components: dict[str, str] = Field(
        default_factory=dict, description="Component health statuses"
    )
```

---

## Part 5: MCP Client Integration

### Step 5.1: MCP Server Registry

Create `src/mcp/registry.py`:

```python
"""MCP server registry and configuration."""

import yaml
from pathlib import Path
from typing import Any

import structlog

from src.config import get_settings

logger = structlog.get_logger()


class MCPServer:
    """Represents an MCP server configuration."""

    def __init__(
        self,
        name: str,
        url: str,
        description: str = "",
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ):
        self.name = name
        self.url = url
        self.description = description
        self.enabled = enabled
        self.metadata = metadata or {}


class MCPServerRegistry:
    """Registry of MCP servers."""

    def __init__(self):
        self.servers: dict[str, MCPServer] = {}
        self._load_config()

    def _load_config(self):
        """Load MCP servers from configuration file."""
        settings = get_settings()
        config_path = Path(settings.mcp_servers_config)

        if not config_path.exists():
            logger.warning(
                "mcp_config_not_found",
                path=str(config_path),
                message="Creating default configuration",
            )
            self._create_default_config(config_path)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        for server_config in config.get("servers", []):
            server = MCPServer(
                name=server_config["name"],
                url=server_config["url"],
                description=server_config.get("description", ""),
                enabled=server_config.get("enabled", True),
                metadata=server_config.get("metadata", {}),
            )
            self.servers[server.name] = server

        logger.info(
            "mcp_registry_loaded", server_count=len(self.servers)
        )

    def _create_default_config(self, config_path: Path):
        """Create default MCP servers configuration."""
        default_config = {
            "servers": [
                {
                    "name": "postgres-mcp",
                    "url": "mcp://localhost:5000",
                    "description": "PostgreSQL database access",
                    "enabled": True,
                    "metadata": {"sensitivity_level": "high"},
                },
                {
                    "name": "github-mcp",
                    "url": "mcp://localhost:5001",
                    "description": "GitHub API access",
                    "enabled": True,
                    "metadata": {"sensitivity_level": "medium"},
                },
            ]
        }

        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

    def get_server(self, name: str) -> MCPServer | None:
        """Get server by name."""
        return self.servers.get(name)

    def list_servers(self, enabled_only: bool = True) -> list[MCPServer]:
        """List all servers."""
        servers = self.servers.values()
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return list(servers)
```

### Step 5.2: MCP Client Wrapper

Create `src/mcp/client.py`:

```python
"""MCP client wrapper for tool invocation."""

from typing import Any

import structlog

logger = structlog.get_logger()


class MCPClient:
    """
    Wrapper for MCP SDK client.

    NOTE: This is a simplified implementation.
    In production, use the actual MCP SDK.
    """

    async def invoke_tool(
        self, server_url: str, tool_name: str, parameters: dict[str, Any]
    ) -> Any:
        """
        Invoke a tool on an MCP server.

        Args:
            server_url: MCP server URL
            tool_name: Tool name
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        logger.info(
            "mcp_tool_invocation",
            server=server_url,
            tool=tool_name,
            params=parameters,
        )

        # TODO: Implement actual MCP SDK integration
        # Example:
        # async with mcp.connect(server_url) as connection:
        #     result = await connection.invoke_tool(tool_name, parameters)
        #     return result

        # Placeholder response
        return {
            "status": "success",
            "message": f"Tool {tool_name} invoked successfully",
            "data": {"simulated": True},
        }
```

---

## Part 6: API Routes

### Step 6.1: Health Check Endpoint

Create `src/routers/health.py`:

```python
"""Health check endpoints."""

from fastapi import APIRouter

from src.models.responses import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components={
            "api": "healthy",
            "mcp_registry": "healthy",
        },
    )
```

### Step 6.2: Tool Invocation Endpoint

Create `src/routers/tools.py`:

```python
"""Tool invocation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.auth.jwt_handler import UserContext, security, validate_jwt_token
from src.auth.sark_client import SARKAuthorizationError, SARKClient
from src.mcp.client import MCPClient
from src.mcp.registry import MCPServerRegistry
from src.models.requests import ToolInvocationRequest
from src.models.responses import ToolInvocationResponse

router = APIRouter(prefix="/tools", tags=["tools"])

# Dependencies
mcp_registry = MCPServerRegistry()
mcp_client = MCPClient()
sark_client = SARKClient()


@router.post("/invoke", response_model=ToolInvocationResponse)
async def invoke_tool(
    request: ToolInvocationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ToolInvocationResponse:
    """
    Invoke a tool on an MCP server.

    This endpoint:
    1. Validates JWT token
    2. Requests authorization from SARK
    3. Applies filtered parameters
    4. Invokes tool on MCP server
    5. Returns result
    """
    # Step 1: Validate JWT and extract user context
    user = validate_jwt_token(credentials)

    # Step 2: Get MCP server from registry
    server = mcp_registry.get_server(request.server_name)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server '{request.server_name}' not found",
        )

    if not server.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Server '{request.server_name}' is disabled",
        )

    # Step 3: Request authorization from SARK
    try:
        auth_response = await sark_client.authorize_tool_invocation(
            user=user,
            server_name=request.server_name,
            tool_name=request.tool_name,
            parameters=request.parameters,
            gateway_metadata={
                "gateway_version": "1.0.0",
                "endpoint": "/tools/invoke",
            },
        )
    except SARKAuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authorization service unavailable: {str(e)}",
        )

    # Step 4: Check authorization decision
    if not auth_response.get("allow"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_response.get(
                "reason", "Access denied by policy"
            ),
        )

    # Step 5: Use filtered parameters from SARK
    filtered_params = auth_response.get(
        "filtered_parameters", request.parameters
    )

    # Step 6: Invoke tool on MCP server
    try:
        result = await mcp_client.invoke_tool(
            server_url=server.url,
            tool_name=request.tool_name,
            parameters=filtered_params,
        )

        return ToolInvocationResponse(
            success=True,
            result=result,
            audit_id=auth_response.get("audit_id"),
        )

    except Exception as e:
        return ToolInvocationResponse(
            success=False,
            error=str(e),
            audit_id=auth_response.get("audit_id"),
        )
```

### Step 6.3: Server Discovery Endpoint

Create `src/routers/servers.py`:

```python
"""Server discovery endpoints."""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from src.auth.jwt_handler import security, validate_jwt_token
from src.auth.sark_client import SARKClient
from src.models.requests import ServerListRequest
from src.models.responses import ServerInfo, ServerListResponse

router = APIRouter(prefix="/servers", tags=["servers"])

sark_client = SARKClient()


@router.get("", response_model=ServerListResponse)
async def list_servers(
    include_tools: bool = False,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ServerListResponse:
    """
    List MCP servers the authenticated user can access.

    This endpoint queries SARK to get only servers the user
    is authorized to access based on their role and permissions.
    """
    # Validate JWT and extract user context
    user = validate_jwt_token(credentials)

    # Query SARK for authorized servers
    servers_data = await sark_client.list_authorized_servers(user)

    # Convert to response models
    servers = [
        ServerInfo(
            name=s["name"],
            url=s["url"],
            description=s.get("description", ""),
            allowed_actions=s.get("allowed_actions", []),
            tools=s.get("tools", []) if include_tools else [],
        )
        for s in servers_data
    ]

    return ServerListResponse(servers=servers, total=len(servers))
```

---

## Part 7: Main Application

### Step 7.1: Create FastAPI Application

Create `src/main.py`:

```python
"""Gateway server FastAPI application."""

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.sark_client import SARKClient
from src.config import get_settings
from src.routers import health, servers, tools

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the application."""
    # Startup
    logger.info("gateway_starting", env=settings.gateway_env)
    yield
    # Shutdown
    logger.info("gateway_shutting_down")


# Get settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="MCP Gateway Server",
    description="Gateway server with SARK authorization integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(tools.router)
app.include_router(servers.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MCP Gateway Server",
        "version": "1.0.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=(settings.gateway_env == "development"),
        log_level=settings.log_level.lower(),
    )
```

---

## Part 8: OPA Policies

### Step 8.1: Create Gateway Policy

Create `policies/gateway.rego`:

```rego
package mcp.gateway

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# ============================================================================
# Admin Access
# ============================================================================

# Admins can invoke any tool
allow if {
    input.user.roles[_] == "admin"
    input.action == "gateway:tool:invoke"
}

# ============================================================================
# Developer Access
# ============================================================================

# Developers can query databases
allow if {
    input.user.roles[_] == "developer"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name in ["execute_query", "list_tables"]
    not is_destructive_query(input.parameters.query)
}

# Developers can read from GitHub
allow if {
    input.user.roles[_] == "developer"
    input.action == "gateway:tool:invoke"
    input.server_name == "github-mcp"
    input.tool_name in ["get_repo", "list_issues", "get_pull_request"]
}

# ============================================================================
# Analyst Access
# ============================================================================

# Analysts can execute read-only queries
allow if {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "execute_query"
    is_select_query(input.parameters.query)
}

# ============================================================================
# Helper Functions
# ============================================================================

is_destructive_query(query) if {
    lower_query := lower(query)
    destructive_keywords := ["drop", "delete", "truncate", "alter"]
    some keyword in destructive_keywords
    contains(lower_query, keyword)
}

is_select_query(query) if {
    lower_query := lower(query)
    startswith(lower_query, "select")
    not is_destructive_query(query)
}

# ============================================================================
# Audit Reason
# ============================================================================

reason := sprintf("Allowed: %s role can invoke %s:%s",
    [input.user.roles[0], input.server_name, input.tool_name]) if {
    allow
}

reason := sprintf("Denied: %s role cannot invoke %s:%s",
    [input.user.roles[0], input.server_name, input.tool_name]) if {
    not allow
}

# ============================================================================
# Cache TTL
# ============================================================================

cache_ttl := 60 if {
    allow
}

cache_ttl := 0 if {
    not allow
}
```

### Step 8.2: Create Test Data

Create `policies/test_data/admin_query.json`:

```json
{
  "input": {
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_123",
      "email": "admin@example.com",
      "roles": ["admin"]
    },
    "parameters": {
      "query": "SELECT * FROM users"
    }
  }
}
```

Create `policies/test_data/analyst_drop.json`:

```json
{
  "input": {
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_456",
      "email": "analyst@example.com",
      "roles": ["analyst"]
    },
    "parameters": {
      "query": "DROP TABLE users"
    }
  }
}
```

---

## Part 9: Testing

### Step 9.1: Test OPA Policies

```bash
# Install OPA CLI
brew install opa  # macOS
# or download from https://www.openpolicyagent.org/docs/latest/#running-opa

# Test admin query (should allow)
opa eval -d policies/gateway.rego \
  -i policies/test_data/admin_query.json \
  "data.mcp.gateway.allow"

# Expected: true

# Test analyst drop (should deny)
opa eval -d policies/gateway.rego \
  -i policies/test_data/analyst_drop.json \
  "data.mcp.gateway.allow"

# Expected: false
```

### Step 9.2: Unit Tests

Create `tests/test_auth.py`:

```python
"""Tests for authentication module."""

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from src.auth.jwt_handler import UserContext, validate_jwt_token
from src.config import get_settings


def test_validate_jwt_token_success():
    """Test successful JWT token validation."""
    settings = get_settings()

    # Create test token
    payload = {
        "sub": "user_123",
        "email": "test@example.com",
        "roles": ["developer"],
        "teams": ["engineering"],
        "exp": 9999999999,  # Far future
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=token
    )

    user = validate_jwt_token(credentials)

    assert user.user_id == "user_123"
    assert user.email == "test@example.com"
    assert "developer" in user.roles
    assert "engineering" in user.teams


def test_validate_jwt_token_expired():
    """Test expired JWT token."""
    settings = get_settings()

    # Create expired token
    payload = {
        "sub": "user_123",
        "email": "test@example.com",
        "roles": ["developer"],
        "exp": 1,  # Past timestamp
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=token
    )

    with pytest.raises(Exception):  # HTTPException
        validate_jwt_token(credentials)
```

---

## Part 10: Deployment

### Step 10.1: Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY policies/ ./policies/

# Create non-root user
RUN useradd -m -u 1000 gateway && \
    chown -R gateway:gateway /app

USER gateway

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Step 10.2: Create docker-compose.yml

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  gateway:
    build: .
    ports:
      - "8080:8080"
    environment:
      - GATEWAY_HOST=0.0.0.0
      - GATEWAY_PORT=8080
      - GATEWAY_ENV=development
      - SARK_URL=http://sark:8000
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    volumes:
      - ./mcp_servers.yaml:/app/mcp_servers.yaml
    depends_on:
      - sark
    networks:
      - gateway-network

  sark:
    image: sark:latest
    ports:
      - "8000:8000"
    environment:
      - GATEWAY_ENABLED=true
    networks:
      - gateway-network

networks:
  gateway-network:
    driver: bridge
```

### Step 10.3: Deploy

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f gateway

# Test health endpoint
curl http://localhost:8080/health
```

---

## Part 11: Integration Testing

### Step 11.1: End-to-End Test

```bash
# 1. Get JWT token from SARK
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }' | jq -r '.access_token')

# 2. List available servers
curl -X GET http://localhost:8080/servers \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Invoke a tool
curl -X POST http://localhost:8080/tools/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "parameters": {
      "query": "SELECT * FROM users LIMIT 10"
    }
  }' | jq

# 4. Try a denied operation
curl -X POST http://localhost:8080/tools/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "parameters": {
      "query": "DROP TABLE users"
    }
  }' | jq
```

**Expected Output:**
- ✅ Server list returned
- ✅ SELECT query allowed
- ❌ DROP query denied with 403 Forbidden

---

## What You Learned

Congratulations! You've built a production-ready MCP Gateway server. You now know:

✅ **Architecture**: How to design a scalable Gateway structure
✅ **Authentication**: JWT token validation and user context extraction
✅ **Authorization**: SARK integration for policy-based access control
✅ **OPA Policies**: Writing and testing custom authorization policies
✅ **API Design**: Building RESTful endpoints with FastAPI
✅ **Error Handling**: Graceful error handling and logging
✅ **Testing**: Unit testing and integration testing strategies
✅ **Deployment**: Docker containerization and orchestration

---

## Next Steps

### Tutorial 3: Production Deployment
Learn to deploy your Gateway in production with:
- High availability and load balancing
- Kubernetes deployment
- Monitoring and alerting
- Security hardening

👉 **[Continue to Tutorial 3 →](./03-production-deployment.md)**

### Extend Your Gateway
- Add custom authentication providers
- Implement rate limiting
- Add circuit breakers
- Integrate with SIEM systems

👉 **[See Tutorial 4: Extending Gateway →](./04-extending-gateway.md)**

---

## Troubleshooting

See the [Troubleshooting Guide](../../gateway-integration/runbooks/TROUBLESHOOTING.md) for common issues and solutions.

---

*Last Updated: 2025-01-15*
*SARK Version: 1.1.0+*
*Tutorial Version: 1.0*
