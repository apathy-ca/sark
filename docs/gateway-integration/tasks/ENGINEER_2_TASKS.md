# Engineer 2: Authorization API Endpoints

**Branch:** `feat/gateway-api`
**Duration:** 5-7 days
**Focus:** FastAPI endpoints for Gateway authorization
**Dependencies:** Shared models (Day 1 from Engineer 1)

---

## Setup

```bash
git checkout -b feat/gateway-api
git pull origin feat/gateway-client  # Get shared models
mkdir -p src/sark/api/routers
mkdir -p src/sark/api/middleware
mkdir -p src/sark/services/gateway
mkdir -p tests/unit/api/routers
```

---

## Tasks

### Day 1-2: Gateway Router & Authorization Endpoint

#### Task 1.1: Gateway Router Setup
**File:** `src/sark/api/routers/gateway.py`

```python
"""Gateway integration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Annotated
import structlog

from sark.services.auth import UserContext, get_current_user
from sark.services.gateway import GatewayClient
from sark.services.gateway.authorization import (
    authorize_gateway_request,
    authorize_a2a_request,
    filter_servers_by_permission,
    filter_tools_by_permission,
)
from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    A2AAuthorizationRequest,
    GatewayServerInfo,
    GatewayToolInfo,
    GatewayAuditEvent,
)
from sark.api.dependencies import get_gateway_client, verify_gateway_auth

logger = structlog.get_logger()
router = APIRouter(prefix="/gateway", tags=["Gateway Integration"])


@router.post("/authorize", response_model=GatewayAuthorizationResponse)
async def authorize_gateway_operation(
    request: GatewayAuthorizationRequest,
    user: Annotated[UserContext, Depends(get_current_user)],
) -> GatewayAuthorizationResponse:
    """
    Authorize Gateway request (called by Gateway before routing to MCP server).

    Flow:
    1. Extract user context from JWT
    2. Build OPA policy input
    3. Evaluate policy (with caching)
    4. Return decision + filtered parameters
    5. Log audit event

    Returns:
        Authorization decision with filtering
    """
    try:
        logger.info(
            "gateway_authorization_request",
            user_id=user.user_id,
            action=request.action,
            server=request.server_name,
            tool=request.tool_name,
        )

        # Authorize request
        decision = await authorize_gateway_request(
            user=user,
            request=request,
        )

        logger.info(
            "gateway_authorization_decision",
            user_id=user.user_id,
            action=request.action,
            decision=decision.allow,
            reason=decision.reason,
        )

        return decision

    except Exception as e:
        logger.error("gateway_authorization_failed", error=str(e))
        # Fail closed - deny on error
        return GatewayAuthorizationResponse(
            allow=False,
            reason=f"Authorization error: {str(e)}",
            cache_ttl=0,
        )


@router.post("/authorize-a2a", response_model=GatewayAuthorizationResponse)
async def authorize_a2a_communication(
    request: A2AAuthorizationRequest,
    agent: Annotated[str, Depends(get_current_agent)],
) -> GatewayAuthorizationResponse:
    """
    Authorize agent-to-agent communication (called by A2A Hub).

    Flow:
    1. Extract agent context from JWT
    2. Validate trust levels
    3. Check capability permissions
    4. Enforce restrictions (cross-env, rate limits)
    5. Return decision

    Returns:
        Authorization decision
    """
    try:
        logger.info(
            "a2a_authorization_request",
            source=request.source_agent_id,
            target=request.target_agent_id,
            capability=request.capability,
        )

        decision = await authorize_a2a_request(
            agent_id=agent,
            request=request,
        )

        return decision

    except Exception as e:
        logger.error("a2a_authorization_failed", error=str(e))
        return GatewayAuthorizationResponse(
            allow=False,
            reason=f"A2A authorization error: {str(e)}",
            cache_ttl=0,
        )


@router.get("/servers", response_model=list[GatewayServerInfo])
async def list_authorized_servers(
    user: Annotated[UserContext, Depends(get_current_user)],
    gateway_client: Annotated[GatewayClient, Depends(get_gateway_client)],
) -> list[GatewayServerInfo]:
    """
    List MCP servers available via Gateway, filtered by user permissions.

    Flow:
    1. Fetch all servers from Gateway
    2. Filter by user's authorization
    3. Return only authorized servers

    Returns:
        List of servers user can access
    """
    try:
        # Get all servers from Gateway
        all_servers = await gateway_client.list_servers()

        # Filter by user permissions
        authorized_servers = await filter_servers_by_permission(
            user=user,
            servers=all_servers,
        )

        logger.info(
            "gateway_list_servers",
            user_id=user.user_id,
            total_servers=len(all_servers),
            authorized_servers=len(authorized_servers),
        )

        return authorized_servers

    except Exception as e:
        logger.error("gateway_list_servers_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=list[GatewayToolInfo])
async def list_authorized_tools(
    server_name: str | None = None,
    user: Annotated[UserContext, Depends(get_current_user)],
    gateway_client: Annotated[GatewayClient, Depends(get_gateway_client)],
) -> list[GatewayToolInfo]:
    """
    List tools available via Gateway, filtered by authorization.

    Args:
        server_name: Optional server filter

    Returns:
        List of tools user can invoke
    """
    try:
        # Get tools from Gateway
        all_tools = await gateway_client.list_tools(server_name=server_name)

        # Filter by user permissions
        authorized_tools = await filter_tools_by_permission(
            user=user,
            tools=all_tools,
        )

        return authorized_tools

    except Exception as e:
        logger.error("gateway_list_tools_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audit")
async def log_gateway_audit_event(
    event: GatewayAuditEvent,
    gateway_id: Annotated[str, Depends(verify_gateway_auth)],
) -> dict[str, str]:
    """
    Log audit event from Gateway (requires Gateway API key).

    Used by Gateway to push audit events to SARK.

    Returns:
        Audit event ID
    """
    try:
        from sark.services.audit.gateway_audit import log_gateway_event

        audit_id = await log_gateway_event(event)

        return {"audit_id": audit_id, "status": "logged"}

    except Exception as e:
        logger.error("gateway_audit_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

**Checklist:**
- [ ] Router configured with prefix `/gateway`
- [ ] All 5 endpoints implemented
- [ ] Request/response models from Engineer 1
- [ ] Structured logging
- [ ] Error handling with fail-closed
- [ ] Dependencies injected via Depends()

---

### Day 2-3: Authorization Logic

#### Task 2.1: Authorization Service
**File:** `src/sark/services/gateway/authorization.py`

```python
"""Gateway authorization business logic."""

from typing import Any
import structlog

from sark.services.auth import UserContext
from sark.services.policy import OPAClient
from sark.services.policy.opa_client import AuthorizationInput
from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    A2AAuthorizationRequest,
    GatewayServerInfo,
    GatewayToolInfo,
)

logger = structlog.get_logger()


async def authorize_gateway_request(
    user: UserContext,
    request: GatewayAuthorizationRequest,
) -> GatewayAuthorizationResponse:
    """
    Authorize Gateway request via OPA.

    Args:
        user: Authenticated user context
        request: Authorization request

    Returns:
        Authorization decision
    """
    opa_client = OPAClient()

    # Build OPA input
    auth_input = AuthorizationInput(
        user={
            "id": str(user.user_id),
            "email": user.email,
            "role": user.role,
            "teams": user.teams,
        },
        action=request.action,
        tool={
            "name": request.tool_name,
            "sensitivity_level": "medium",  # TODO: Get from Gateway metadata
            "sensitive_params": request.gateway_metadata.get("sensitive_params", []),
        } if request.tool_name else None,
        server={
            "name": request.server_name,
            "sensitivity_level": "medium",  # TODO: Get from Gateway
            "authorized_teams": request.gateway_metadata.get("authorized_teams", []),
        } if request.server_name else None,
        context={
            "timestamp": request.gateway_metadata.get("timestamp", 0),
            "gateway_request_id": request.gateway_metadata.get("request_id", ""),
        },
    )

    # Evaluate policy
    decision = await opa_client.evaluate_policy(auth_input)

    await opa_client.close()

    # Determine cache TTL based on sensitivity
    cache_ttl = _get_cache_ttl(request)

    return GatewayAuthorizationResponse(
        allow=decision.allow,
        reason=decision.reason,
        filtered_parameters=decision.filtered_parameters,
        audit_id=decision.audit_id,
        cache_ttl=cache_ttl,
    )


async def authorize_a2a_request(
    agent_id: str,
    request: A2AAuthorizationRequest,
) -> GatewayAuthorizationResponse:
    """
    Authorize agent-to-agent communication.

    Args:
        agent_id: Authenticated agent ID
        request: A2A authorization request

    Returns:
        Authorization decision
    """
    opa_client = OPAClient()

    # Build OPA input for A2A
    auth_input = AuthorizationInput(
        user={
            "id": agent_id,
            "type": "agent",
        },
        action=f"a2a:{request.capability}",
        context={
            "source_agent_id": request.source_agent_id,
            "target_agent_id": request.target_agent_id,
            "message_type": request.message_type,
            "payload_metadata": request.payload_metadata,
        },
    )

    decision = await opa_client.evaluate_policy(auth_input)
    await opa_client.close()

    return GatewayAuthorizationResponse(
        allow=decision.allow,
        reason=decision.reason,
        cache_ttl=30,  # Short cache for A2A
    )


async def filter_servers_by_permission(
    user: UserContext,
    servers: list[GatewayServerInfo],
) -> list[GatewayServerInfo]:
    """
    Filter servers by user's authorization.

    Args:
        user: User context
        servers: All servers

    Returns:
        Servers user can access
    """
    opa_client = OPAClient()
    authorized_servers = []

    for server in servers:
        # Check if user can access this server
        auth_input = AuthorizationInput(
            user={
                "id": str(user.user_id),
                "role": user.role,
                "teams": user.teams,
            },
            action="gateway:server:access",
            server={
                "name": server.server_name,
                "sensitivity_level": server.sensitivity_level.value,
                "authorized_teams": server.authorized_teams,
            },
            context={},
        )

        decision = await opa_client.evaluate_policy(auth_input)

        if decision.allow:
            authorized_servers.append(server)

    await opa_client.close()
    return authorized_servers


async def filter_tools_by_permission(
    user: UserContext,
    tools: list[GatewayToolInfo],
) -> list[GatewayToolInfo]:
    """Filter tools by user's authorization."""
    # Similar to filter_servers_by_permission
    # Check each tool against user permissions
    opa_client = OPAClient()
    authorized_tools = []

    for tool in tools:
        auth_input = AuthorizationInput(
            user={
                "id": str(user.user_id),
                "role": user.role,
                "teams": user.teams,
            },
            action="gateway:tool:discover",
            tool={
                "name": tool.tool_name,
                "sensitivity_level": tool.sensitivity_level.value,
            },
            context={},
        )

        decision = await opa_client.evaluate_policy(auth_input)

        if decision.allow:
            authorized_tools.append(tool)

    await opa_client.close()
    return authorized_tools


def _get_cache_ttl(request: GatewayAuthorizationRequest) -> int:
    """Determine cache TTL based on request."""
    # Critical actions: short cache
    if "critical" in request.action:
        return 30
    # High sensitivity: short cache
    elif "high" in str(request.gateway_metadata.get("sensitivity", "")):
        return 60
    # Default: medium cache
    return 180
```

**Checklist:**
- [ ] All authorization functions implemented
- [ ] OPA client integration
- [ ] User context properly formatted
- [ ] Cache TTL logic
- [ ] Batch filtering for servers/tools

---

### Day 3: Agent Authentication

#### Task 3.1: Agent Authentication Middleware
**File:** `src/sark/api/middleware/agent_auth.py`

```python
"""Agent authentication for A2A requests."""

from fastapi import Header, HTTPException
import jwt
from typing import Annotated
import structlog

from sark.config import get_settings
from sark.models.gateway import AgentContext, AgentType, TrustLevel

logger = structlog.get_logger()
settings = get_settings()


async def get_current_agent(
    authorization: Annotated[str, Header(description="Agent JWT token")]
) -> str:
    """
    Extract and validate agent from JWT.

    Args:
        authorization: Bearer token with agent JWT

    Returns:
        Agent ID

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")

    try:
        # Decode JWT (use same secret as user JWT for now)
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
        )

        agent_id = payload.get("agent_id")
        if not agent_id:
            raise HTTPException(status_code=401, detail="Invalid agent token")

        # Validate agent exists and is active
        # TODO: Check against agent registry

        logger.info("agent_authenticated", agent_id=agent_id)

        return agent_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Agent token expired")

    except jwt.InvalidTokenError as e:
        logger.warning("agent_authentication_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid agent token")


def extract_agent_context(token: str) -> AgentContext:
    """
    Extract full agent context from JWT.

    Args:
        token: JWT token

    Returns:
        Agent context with capabilities and trust level
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
        )

        return AgentContext(
            agent_id=payload["agent_id"],
            agent_type=AgentType(payload.get("type", "worker")),
            trust_level=TrustLevel(payload.get("trust_level", "limited")),
            capabilities=payload.get("capabilities", []),
            environment=payload.get("environment", "unknown"),
            rate_limited=payload.get("rate_limited", False),
        )

    except Exception as e:
        logger.error("extract_agent_context_failed", error=str(e))
        raise ValueError(f"Invalid agent token: {e}")
```

**Checklist:**
- [ ] Agent JWT validation
- [ ] Agent context extraction
- [ ] Error handling for invalid tokens
- [ ] Integration with existing JWT logic

---

### Day 4: Testing

#### Task 4.1: API Router Tests
**File:** `tests/unit/api/routers/test_gateway.py`

```python
"""Tests for Gateway API router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from sark.api.main import app
from sark.models.gateway import GatewayAuthorizationResponse


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "user_id": "user_123",
        "email": "test@example.com",
        "role": "developer",
        "teams": ["team1"],
    }


def test_authorize_gateway_allow(client, mock_user):
    """Test successful Gateway authorization."""
    with patch("sark.api.routers.gateway.authorize_gateway_request") as mock_authz:
        mock_authz.return_value = GatewayAuthorizationResponse(
            allow=True,
            reason="Allowed by policy",
            filtered_parameters={"query": "SELECT *"},
            cache_ttl=60,
        )

        response = client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "postgres-mcp",
                "tool_name": "execute_query",
                "parameters": {"query": "SELECT *"},
            },
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["allow"] is True
        assert data["reason"] == "Allowed by policy"
        assert data["cache_ttl"] == 60


def test_authorize_gateway_deny(client, mock_user):
    """Test denied Gateway authorization."""
    with patch("sark.api.routers.gateway.authorize_gateway_request") as mock_authz:
        mock_authz.return_value = GatewayAuthorizationResponse(
            allow=False,
            reason="Insufficient permissions",
            cache_ttl=0,
        )

        response = client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "critical-server",
                "tool_name": "admin_command",
            },
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["allow"] is False
        assert "Insufficient permissions" in data["reason"]


def test_list_servers_filtered(client):
    """Test server listing with permission filtering."""
    with patch("sark.api.routers.gateway.filter_servers_by_permission") as mock_filter:
        mock_filter.return_value = [
            {
                "server_id": "srv_1",
                "server_name": "allowed-server",
                "server_url": "http://test:8080",
                "health_status": "healthy",
                "tools_count": 5,
            }
        ]

        response = client.get(
            "/api/v1/gateway/servers",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        servers = response.json()
        assert len(servers) == 1
        assert servers[0]["server_name"] == "allowed-server"


# Add more tests: A2A authorization, tools listing, audit logging, etc.
```

**Checklist:**
- [ ] Test all endpoints (authorize, authorize-a2a, servers, tools, audit)
- [ ] Test success and error cases
- [ ] Test authentication failures
- [ ] Test parameter validation
- [ ] Mock OPA client
- [ ] Coverage >85%

---

## Integration with Main App

**File:** `src/sark/api/main.py` (modifications)

```python
from sark.api.routers import gateway as gateway_router

# Register Gateway router
app.include_router(
    gateway_router.router,
    prefix="/api/v1",
    dependencies=[Depends(rate_limit)],
)
```

---

## Delivery Checklist

- [ ] All endpoints implemented
- [ ] Authorization logic complete
- [ ] Agent authentication working
- [ ] Unit tests >85% coverage
- [ ] Integration with main app
- [ ] OpenAPI docs generated
- [ ] PR created

---

## PR Description

```markdown
## Gateway Authorization API Endpoints

### Summary
Implements FastAPI endpoints for MCP Gateway integration authorization.

### Features
- Gateway tool invocation authorization endpoint
- A2A communication authorization endpoint
- Server/tool discovery with permission filtering
- Audit event logging endpoint
- Agent JWT authentication

### Testing
```bash
pytest tests/unit/api/routers/test_gateway.py -v
pytest tests/unit/services/gateway/test_authorization.py -v
```

### API Examples

**Authorize tool invocation:**
```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"action":"gateway:tool:invoke","server_name":"postgres-mcp","tool_name":"query"}'
```
```

Ready! 🚀
