"""End-to-end Gateway authorization tests."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_full_authorization_flow_allow(app_client, mock_user):
    """Test complete authorization flow (allow)."""

    # Step 1: Authenticate user
    auth_response = await app_client.post(
        "/api/v1/auth/login",
        json={"username": "test@example.com", "password": "password"},
    )
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]

    # Step 2: Authorize Gateway request
    authz_response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "safe-tool",
            "parameters": {"key": "value"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert authz_response.status_code == 200
    data = authz_response.json()
    assert data["allow"] is True
    assert "filtered_parameters" in data
    assert "audit_id" in data

    # Step 3: Verify audit event logged
    # Query audit database
    # Verify event in SIEM (mock)


async def test_parameter_filtering(app_client, mock_user_token):
    """Test sensitive parameter filtering."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "db-server",
            "tool_name": "query",
            "parameters": {
                "query": "SELECT * FROM users",
                "password": "secret123",  # Should be filtered
                "api_key": "key_abc",  # Should be filtered
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Filtered parameters should not contain secrets
    assert "password" not in data["filtered_parameters"]
    assert "api_key" not in data["filtered_parameters"]
    assert "query" in data["filtered_parameters"]


async def test_cache_behavior(app_client, mock_user_token):
    """Test policy cache hit/miss."""

    # First request - cache miss
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Second identical request - cache hit
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Both should succeed
    assert response1.status_code == 200
    assert response2.status_code == 200

    # Check cache metrics (second request should be faster)
    # Verify cache hit counter incremented


async def test_authorization_deny(app_client, mock_user_token):
    """Test authorization denial flow."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:admin:delete",
            "server_name": "critical-server",
            "tool_name": "delete-all",
            "parameters": {},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is False
    assert "reason" in data


async def test_server_discovery(app_client, mock_user_token):
    """Test Gateway server discovery."""

    response = await app_client.get(
        "/api/v1/gateway/servers",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify server structure
    server = data[0]
    assert "server_id" in server
    assert "server_name" in server
    assert "server_url" in server
    assert "sensitivity_level" in server


async def test_tool_discovery(app_client, mock_user_token):
    """Test Gateway tool discovery."""

    response = await app_client.get(
        "/api/v1/gateway/servers/test-server/tools",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_audit_logging(app_client, mock_user_token):
    """Test audit logging for Gateway requests."""

    # Make authorization request
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "test-tool",
            "parameters": {"key": "value"},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    audit_id = response.json().get("audit_id")

    # Query audit logs
    audit_response = await app_client.get(
        f"/api/v1/audit/events/{audit_id}",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert audit_response.status_code == 200
    audit_event = audit_response.json()
    assert audit_event["event_type"] == "gateway_authorization"
    assert audit_event["action"] == "gateway:tool:invoke"
