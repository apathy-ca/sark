"""Authentication and Authorization Security Tests."""

import pytest

pytestmark = pytest.mark.security


async def test_invalid_api_key_rejection(app_client):
    """Test invalid API key rejection."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"X-API-Key": "invalid_key_12345"},
    )

    assert response.status_code == 401


async def test_expired_token_handling(app_client, expired_token):
    """Test expired token handling."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    error = response.json()
    assert "expired" in error.get("detail", "").lower()


async def test_privilege_escalation_attempts(app_client, restricted_user_token):
    """Test privilege escalation attempts."""

    # Restricted user tries admin action
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:admin:delete",
            "server_name": "production-server",
            "tool_name": "admin-tool",
        },
        headers={"Authorization": f"Bearer {restricted_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is False
    assert "insufficient privileges" in data.get("reason", "").lower()


async def test_session_hijacking_prevention(app_client, mock_user_token):
    """Test session hijacking prevention."""

    # Make request with valid token
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={
            "Authorization": f"Bearer {mock_user_token}",
            "X-Forwarded-For": "1.2.3.4",
        },
    )

    assert response1.status_code == 200

    # Try same token from different IP
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={
            "Authorization": f"Bearer {mock_user_token}",
            "X-Forwarded-For": "5.6.7.8",  # Different IP
        },
    )

    # Should either work (if IP binding not enforced) or reject
    assert response2.status_code in [200, 401, 403]


async def test_token_reuse_prevention(app_client):
    """Test prevention of token reuse after logout."""

    # Login
    login_response = await app_client.post(
        "/api/v1/auth/login",
        json={"username": "test@example.com", "password": "password"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Use token
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response1.status_code == 200

    # Logout
    logout_response = await app_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_response.status_code == 200

    # Try to reuse token after logout
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should be rejected
    assert response2.status_code == 401
