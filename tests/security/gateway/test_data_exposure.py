"""Data Exposure Security Tests."""

import pytest

pytestmark = pytest.mark.security


async def test_sensitive_data_redaction_in_logs(app_client, mock_user_token, caplog):
    """Test sensitive data is redacted from logs."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "test",
            "parameters": {
                "password": "secret123",
                "api_key": "key_abc",
                "token": "bearer_xyz",
                "ssn": "123-45-6789",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200

    # Check logs don't contain sensitive data
    log_output = caplog.text.lower()
    assert "secret123" not in log_output
    assert "key_abc" not in log_output
    assert "123-45-6789" not in log_output


async def test_error_message_information_leakage(app_client, mock_user_token):
    """Test error messages don't leak sensitive information."""

    # Trigger various errors
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "nonexistent-server",
            "tool_name": "test",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    if response.status_code >= 400:
        error_data = response.json()
        error_msg = str(error_data)

        # Should not leak internal paths
        assert "/home/" not in error_msg
        assert "C:\\" not in error_msg
        # Should not leak database info
        assert "postgresql://" not in error_msg
        assert "connection string" not in error_msg.lower()


async def test_unauthorized_tool_enumeration(app_client, restricted_user_token):
    """Test unauthorized tool enumeration is prevented."""

    # Restricted user tries to list all tools
    response = await app_client.get(
        "/api/v1/gateway/servers/admin-server/tools",
        headers={"Authorization": f"Bearer {restricted_user_token}"},
    )

    # Should be denied or return filtered list
    if response.status_code == 200:
        tools = response.json()
        # Should only see allowed tools
        assert len(tools) == 0 or all(tool.get("visibility") == "public" for tool in tools)
    else:
        assert response.status_code in [403, 404]


async def test_metadata_exposure_risks(app_client, mock_user_token):
    """Test metadata doesn't expose sensitive information."""

    response = await app_client.get(
        "/api/v1/gateway/servers",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    if response.status_code == 200:
        servers = response.json()

        for server in servers:
            # Should not expose internal IPs
            server_url = server.get("server_url", "")
            assert not server_url.startswith("http://10.")
            assert not server_url.startswith("http://192.168.")
            assert not server_url.startswith("http://172.")

            # Should not expose credentials
            assert "password" not in server
            assert "api_key" not in server
            assert "secret" not in server
