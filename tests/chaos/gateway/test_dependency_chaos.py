"""Dependency Chaos Engineering Tests."""

import pytest

pytestmark = pytest.mark.chaos


async def test_opa_service_unavailable(app_client, mock_user_token, monkeypatch):
    """Test behavior when OPA service is down."""

    # Point to invalid OPA endpoint
    monkeypatch.setenv("OPA_URL", "http://invalid-opa:9999")

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should fail closed (deny)
    if response.status_code == 200:
        assert response.json()["allow"] is False
    else:
        assert response.status_code in [500, 503]


async def test_database_connection_failures(app_client, mock_user_token, monkeypatch):
    """Test handling of database connection failures."""

    # Simulate DB failure
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid:5432/invalid")

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should handle gracefully
    assert response.status_code in [200, 500, 503]


async def test_cache_service_failures(app_client, mock_user_token, monkeypatch):
    """Test handling of cache service failures."""

    # Point to invalid Redis
    monkeypatch.setenv("VALKEY_URL", "redis://invalid:6379/0")

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should work without cache (degraded mode)
    assert response.status_code in [200, 503]
