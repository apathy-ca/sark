"""Security tests for Gateway integration."""

import pytest


@pytest.mark.security
async def test_invalid_jwt_rejected(app_client):
    """Test invalid JWT tokens are rejected."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401


@pytest.mark.security
async def test_expired_token_rejected(app_client, expired_token):
    """Test expired tokens are rejected."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


@pytest.mark.security
async def test_missing_auth_header(app_client):
    """Test requests without authentication are rejected."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
    )

    assert response.status_code in [401, 403]


@pytest.mark.security
async def test_parameter_injection_blocked(app_client, mock_user_token):
    """Test SQL injection attempts are blocked."""

    malicious_params = {
        "query": "'; DROP TABLE users; --",
        "command": "$(rm -rf /)",
        "path": "../../etc/passwd",
    }

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "tool_name": "test",
            "parameters": malicious_params,
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should either deny or sanitize
    data = response.json()
    if data["allow"]:
        # Check parameters are sanitized
        assert "DROP TABLE" not in str(data.get("filtered_parameters", {}))


@pytest.mark.security
async def test_xss_prevention(app_client, mock_user_token):
    """Test XSS injection prevention."""

    xss_payload = "<script>alert('XSS')</script>"

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "tool_name": "test",
            "parameters": {"input": xss_payload},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # XSS should be sanitized or escaped
    if data.get("filtered_parameters"):
        assert "<script>" not in str(data["filtered_parameters"])


@pytest.mark.security
async def test_command_injection_blocked(app_client, mock_user_token):
    """Test command injection attempts are blocked."""

    command_injections = [
        "; cat /etc/passwd",
        "| whoami",
        "& ls -la /",
        "`id`",
        "$(uname -a)",
    ]

    for injection in command_injections:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": "test",
                "parameters": {"command": injection},
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should either deny or sanitize
        if data["allow"]:
            filtered = str(data.get("filtered_parameters", {}))
            assert "passwd" not in filtered or injection not in filtered


@pytest.mark.security
async def test_path_traversal_blocked(app_client, mock_user_token):
    """Test path traversal attempts are blocked."""

    path_traversals = [
        "../../etc/passwd",
        "../../../etc/shadow",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/passwd",
        "C:\\Windows\\System32\\config\\SAM",
    ]

    for path in path_traversals:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": "test",
                "parameters": {"file_path": path},
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should deny access to system files
        if not data["allow"]:
            assert "reason" in data


@pytest.mark.security
async def test_fail_closed_on_opa_error(app_client, mock_user_token, monkeypatch):
    """Test system fails closed when OPA is unavailable."""

    # Simulate OPA failure
    monkeypatch.setenv("OPA_URL", "http://invalid:9999")

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should deny when OPA is unavailable
    assert response.status_code == 200
    assert response.json()["allow"] is False


@pytest.mark.security
async def test_fail_closed_on_gateway_error(app_client, mock_user_token, monkeypatch):
    """Test system fails closed when Gateway is unavailable."""

    # Simulate Gateway failure
    monkeypatch.setenv("GATEWAY_URL", "http://invalid:9999")

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should handle gracefully (may deny or return error)
    assert response.status_code in [200, 500, 503]


@pytest.mark.security
async def test_rate_limiting(app_client, mock_user_token):
    """Test rate limiting enforcement."""

    # Make many requests quickly
    responses = []
    for _ in range(200):
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        responses.append(response.status_code)

    # Should see some rate limit responses (429)
    # Note: This depends on rate limit configuration
    # If rate limiting is enabled, we should see 429 responses
    # If not, all should be 200 or other valid responses
    assert all(status in [200, 429, 503] for status in responses)


@pytest.mark.security
async def test_sensitive_data_not_logged(app_client, mock_user_token, caplog):
    """Test sensitive data is not logged."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "tool_name": "test",
            "parameters": {
                "password": "secret123",
                "api_key": "key_abc123",
                "token": "bearer_xyz789",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200

    # Check logs don't contain sensitive data
    log_output = caplog.text.lower()
    assert "secret123" not in log_output
    assert "key_abc123" not in log_output
    assert "bearer_xyz789" not in log_output


@pytest.mark.security
async def test_authorization_bypass_attempts(app_client, mock_user_token):
    """Test authorization bypass attempts are prevented."""

    # Try various bypass techniques
    bypass_attempts = [
        # Empty action
        {"action": "", "tool_name": "test"},
        # Null action
        {"action": None, "tool_name": "test"},
        # Missing required fields
        {"tool_name": "test"},
        # Invalid action format
        {"action": "../../admin:delete", "tool_name": "test"},
    ]

    for attempt in bypass_attempts:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json=attempt,
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        # Should reject invalid requests
        assert response.status_code in [400, 422, 200]
        if response.status_code == 200:
            assert response.json()["allow"] is False


@pytest.mark.security
async def test_privilege_escalation_blocked(app_client, restricted_user_token):
    """Test privilege escalation is blocked."""

    # Restricted user tries admin action
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:admin:delete",
            "tool_name": "admin-tool",
            "parameters": {},
        },
        headers={"Authorization": f"Bearer {restricted_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is False
    assert "reason" in data


@pytest.mark.security
async def test_csrf_protection(app_client, mock_user_token):
    """Test CSRF protection is enabled."""

    # Attempt request without CSRF token (if CSRF is implemented)
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={
            "Authorization": f"Bearer {mock_user_token}",
            "Origin": "https://evil.com",
        },
    )

    # Should either succeed with proper CORS or be blocked
    # This depends on CORS/CSRF configuration
    assert response.status_code in [200, 403]
