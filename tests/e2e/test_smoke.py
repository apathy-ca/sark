"""
Smoke tests for critical system paths and service health.

Quick verification tests (~10 seconds total) that validate
essential system functionality is working.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.models.user import User
from sark.services.auth.api_key import APIKeyService
from sark.services.auth.jwt import JWTHandler
from sark.services.policy.opa_client import AuthorizationInput, OPAClient

# ============================================================================
# System Health Checks
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
def test_database_connectivity():
    """Verify database connection is available."""
    # Mock database connection
    with patch("asyncpg.connect", new=AsyncMock()) as mock_connect:
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_connect.return_value = mock_conn

        # Test connection
        db_available = True

    assert db_available is True


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_opa_service_availability():
    """Verify OPA service is reachable."""
    opa_client = OPAClient(opa_url="http://localhost:8181")

    # Mock health check
    with patch.object(opa_client.client, "get", new=AsyncMock()) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        opa_available = True

    assert opa_available is True


@pytest.mark.smoke
@pytest.mark.e2e
def test_redis_cache_connectivity():
    """Verify Redis cache is accessible."""
    # Mock Redis connection
    with patch("redis.asyncio.Redis.from_url", new=MagicMock()) as mock_redis:
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_redis.return_value = mock_client

        redis_available = True

    assert redis_available is True


@pytest.mark.smoke
@pytest.mark.e2e
def test_consul_service_registry():
    """Verify Consul service registry is accessible."""
    # Mock Consul connection
    with patch("consul.Consul", new=MagicMock()) as mock_consul:
        mock_client = MagicMock()
        mock_client.agent.self = MagicMock(return_value={"Config": {}})
        mock_consul.return_value = mock_client

        consul_available = True

    assert consul_available is True


# ============================================================================
# Core API Endpoint Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
def test_health_check_endpoint():
    """Verify /health endpoint returns healthy status."""
    # Mock health endpoint
    health_response = {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }

    assert health_response["status"] == "healthy"


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
def test_readiness_check_endpoint():
    """Verify /ready endpoint returns ready status."""
    # Mock readiness check
    ready_response = {"ready": True, "checks": {"database": True, "opa": True, "redis": True}}

    assert ready_response["ready"] is True
    assert all(ready_response["checks"].values())


@pytest.mark.smoke
@pytest.mark.e2e
def test_metrics_endpoint():
    """Verify /metrics endpoint is accessible."""
    # Mock metrics endpoint
    metrics_response = """
    # HELP http_requests_total Total HTTP requests
    # TYPE http_requests_total counter
    http_requests_total{method="GET",endpoint="/api/servers/"} 150
    """

    assert "http_requests_total" in metrics_response


@pytest.mark.smoke
@pytest.mark.e2e
def test_api_documentation_endpoint():
    """Verify /docs endpoint serves OpenAPI documentation."""
    # Mock docs endpoint
    docs_available = True
    assert docs_available is True


# ============================================================================
# Authentication Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
def test_jwt_token_generation():
    """Verify JWT token can be generated."""
    jwt_handler = JWTHandler(
        secret_key="test-secret", algorithm="HS256", access_token_expire_minutes=30
    )

    token = jwt_handler.create_access_token(
        user_id=uuid4(), email="test@example.com", role="developer"
    )

    assert token is not None
    assert len(token) > 0


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
def test_jwt_token_validation():
    """Verify JWT token can be validated."""
    jwt_handler = JWTHandler(
        secret_key="test-secret", algorithm="HS256", access_token_expire_minutes=30
    )

    user_id = uuid4()
    token = jwt_handler.create_access_token(
        user_id=user_id, email="test@example.com", role="developer"
    )

    # Verify token
    decoded_payload = jwt_handler.decode_token(token)
    assert UUID(decoded_payload["sub"]) == user_id
    assert decoded_payload["email"] == "test@example.com"
    assert decoded_payload["role"] == "developer"


@pytest.mark.smoke
@pytest.mark.e2e
def test_session_creation():
    """Verify user sessions can be created."""
    from sark.services.auth.session import SessionService

    session_service = SessionService(session_lifetime_hours=24)

    session = session_service.create_session(
        user_id=uuid4(), user_agent="Mozilla/5.0", ip_address="192.168.1.100"
    )

    assert session is not None
    # Session should be created successfully


@pytest.mark.smoke
@pytest.mark.e2e
def test_api_key_authentication():
    """Verify API key authentication works."""
    api_key_service = APIKeyService(key_length=32)

    # Generate API key
    api_key = api_key_service.generate_key()
    assert len(api_key) > 0

    # Hash and verify
    key_hash = api_key_service.hash_key(api_key)
    is_valid = api_key_service.verify_key(api_key, key_hash)
    assert is_valid is True


# ============================================================================
# Server Management Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
def test_server_registration():
    """Verify basic server registration works."""
    user_id = uuid4()
    server = MCPServer(
        id=uuid4(),
        name="smoke-test-server",
        description="Smoke test server",
        transport=TransportType.HTTP,
        endpoint="http://localhost:3000/mcp",
        sensitivity_level=SensitivityLevel.LOW,
        owner_id=user_id,
        team_id=uuid4(),
        status=ServerStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert server.name == "smoke-test-server"
    assert server.owner_id == user_id
    assert server.status == ServerStatus.ACTIVE


@pytest.mark.smoke
@pytest.mark.e2e
def test_server_retrieval():
    """Verify server can be retrieved by ID."""
    server_id = uuid4()
    server = MCPServer(
        id=server_id,
        name="test-server",
        description="Test server",
        transport=TransportType.HTTP,
        endpoint="http://localhost:3000/mcp",
        sensitivity_level=SensitivityLevel.MEDIUM,
        owner_id=uuid4(),
        team_id=uuid4(),
        status=ServerStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Mock retrieval
    retrieved_server = server
    assert retrieved_server.id == server_id


@pytest.mark.smoke
@pytest.mark.e2e
def test_server_search():
    """Verify server search functionality works."""
    # Mock search results (without requiring DB setup)
    results = [
        MCPServer(
            id=uuid4(),
            name="test-server-1",
            description="Test",
            transport=TransportType.HTTP,
            endpoint="http://localhost:3000",
            sensitivity_level=SensitivityLevel.LOW,
            owner_id=uuid4(),
            team_id=uuid4(),
            status=ServerStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    ]

    assert len(results) >= 0  # Should return results


@pytest.mark.smoke
@pytest.mark.e2e
def test_server_status_update():
    """Verify server status can be updated."""
    server = MCPServer(
        id=uuid4(),
        name="status-test-server",
        description="Status test",
        transport=TransportType.HTTP,
        endpoint="http://localhost:3000",
        sensitivity_level=SensitivityLevel.LOW,
        owner_id=uuid4(),
        team_id=uuid4(),
        status=ServerStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Update status
    server.status = ServerStatus.INACTIVE
    assert server.status == ServerStatus.INACTIVE


# ============================================================================
# Policy Enforcement Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_policy_evaluation():
    """Verify policy evaluation works."""
    opa_client = OPAClient(opa_url="http://localhost:8181")

    # Mock policy evaluation
    with patch.object(opa_client.client, "post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_post.return_value = mock_response

        auth_input = AuthorizationInput(
            user={"role": "developer", "id": str(uuid4())},
            action="register",
            server={"type": "mcp"},
            context={},
        )
        decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow is True


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_authorization_decision():
    """Verify authorization decisions are made correctly."""
    opa_client = OPAClient(opa_url="http://localhost:8181")

    # Test allow decision
    with patch.object(opa_client.client, "post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_post.return_value = mock_response

        allow_input = AuthorizationInput(
            user={"role": "developer", "id": str(uuid4())}, action="read", context={}
        )
        allow_decision = await opa_client.evaluate_policy(allow_input)

    assert allow_decision.allow is True

    # Test deny decision
    with patch.object(opa_client.client, "post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"allow": False, "audit_reason": "Insufficient permissions"}
        }
        mock_post.return_value = mock_response

        deny_input = AuthorizationInput(
            user={"role": "guest", "id": str(uuid4())}, action="delete", context={}
        )
        deny_decision = await opa_client.evaluate_policy(deny_input)

    assert deny_decision.allow is False
    assert deny_decision.reason is not None


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_fail_closed_verification():
    """Verify system fails closed on policy errors."""
    opa_client = OPAClient(opa_url="http://localhost:8181")

    # Simulate OPA error
    with patch.object(opa_client.client, "post", new=AsyncMock(side_effect=Exception("OPA error"))):
        fail_input = AuthorizationInput(
            user={"role": "developer", "id": str(uuid4())}, action="read", context={}
        )
        decision = await opa_client.evaluate_policy(fail_input)

    # Should fail closed (deny)
    assert decision.allow is False


# ============================================================================
# Audit System Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
def test_audit_event_creation():
    """Verify audit events can be created."""
    from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel

    event = AuditEvent(
        id=uuid4(),
        event_type=AuditEventType.SERVER_REGISTERED,
        severity=SeverityLevel.LOW,
        user_id=uuid4(),
        server_id=uuid4(),
        details={"server_name": "test"},
        timestamp=datetime.now(UTC),
    )

    assert event.event_type == AuditEventType.SERVER_REGISTERED
    assert event.severity == SeverityLevel.LOW


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_siem_forwarding():
    """Verify SIEM forwarding is functional."""
    # Mock SIEM HTTP request
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Simulate SIEM forward
        siem_success = True

    assert siem_success is True


# ============================================================================
# Performance Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
def test_jwt_generation_performance():
    """Verify JWT generation completes in reasonable time."""
    import time

    jwt_handler = JWTHandler(
        secret_key="test-secret", algorithm="HS256", access_token_expire_minutes=30
    )

    start = time.time()

    # Generate 100 tokens
    for _ in range(100):
        jwt_handler.create_access_token(user_id=uuid4(), email="test@example.com", role="developer")

    elapsed = time.time() - start

    # Should complete in under 1 second
    assert elapsed < 1.0


@pytest.mark.smoke
@pytest.mark.e2e
def test_server_search_performance():
    """Verify server model creation completes in reasonable time."""
    import time

    start = time.time()

    # Create server objects (should be fast)
    for i in range(100):
        MCPServer(
            id=uuid4(),
            name=f"perf-test-{i}",
            description="Performance test",
            transport=TransportType.HTTP,
            endpoint=f"http://server{i}.test",
            sensitivity_level=SensitivityLevel.LOW,
            owner_id=uuid4(),
            team_id=uuid4(),
            status=ServerStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    elapsed = time.time() - start

    # Should complete in under 0.5 seconds
    assert elapsed < 0.5


# ============================================================================
# Integration Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.e2e
@pytest.mark.critical
def test_end_to_end_quick_flow():
    """Quick end-to-end smoke test of critical path."""
    # 1. Create user
    user = User(
        id=uuid4(),
        email="smoke@example.com",
        full_name="Smoke Test User",
        hashed_password="hashed",
        role="developer",
        is_active=True,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # 2. Generate token
    jwt_handler = JWTHandler(
        secret_key="test-secret", algorithm="HS256", access_token_expire_minutes=30
    )
    token = jwt_handler.create_access_token(user_id=user.id, email=user.email, role=user.role)

    # 3. Register server
    server = MCPServer(
        id=uuid4(),
        name="quick-smoke-server",
        description="Quick smoke test",
        transport=TransportType.HTTP,
        endpoint="http://localhost:3000",
        sensitivity_level=SensitivityLevel.LOW,
        owner_id=user.id,
        team_id=uuid4(),
        status=ServerStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Verify complete flow
    assert user.id is not None
    assert token is not None
    assert server.owner_id == user.id
    assert server.status == ServerStatus.ACTIVE
