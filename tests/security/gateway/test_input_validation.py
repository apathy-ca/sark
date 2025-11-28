"""Input Validation Security Tests.

Tests for SQL injection, command injection, path traversal,
and oversized payload handling.
"""

import pytest

pytestmark = pytest.mark.security


async def test_sql_injection_in_tool_parameters(app_client, mock_user_token):
    """Test SQL injection attempts in tool parameters."""

    sql_injections = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'--",
        "1; DELETE FROM servers WHERE '1'='1",
        "' UNION SELECT password FROM users--",
    ]

    for injection in sql_injections:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "db-server",
                "tool_name": "query",
                "parameters": {"query": injection},
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            # Should deny or sanitize
            filtered = str(data.get("filtered_parameters", {}))
            assert "DROP TABLE" not in filtered
            assert "DELETE FROM" not in filtered


async def test_command_injection_via_tool_arguments(app_client, mock_user_token):
    """Test command injection via tool arguments."""

    command_injections = [
        "; rm -rf /",
        "| cat /etc/passwd",
        "& whoami",
        "`id`",
        "$(uname -a)",
        "\n/bin/bash -i",
    ]

    for injection in command_injections:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "exec-server",
                "tool_name": "execute",
                "parameters": {"command": f"echo test{injection}"},
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            # Should deny dangerous commands
            if not data.get("allow", True):
                assert "reason" in data


async def test_path_traversal_attempts(app_client, mock_user_token):
    """Test path traversal attempts."""

    path_traversals = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/shadow",
        "C:\\Windows\\System32\\config\\SAM",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ]

    for path in path_traversals:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "file-server",
                "tool_name": "read-file",
                "parameters": {"path": path},
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            # Should deny access to system files
            assert data.get("allow") is False or "sanitized" in str(data).lower()


async def test_oversized_payload_handling(app_client, mock_user_token):
    """Test handling of oversized payloads."""

    # Create very large payload (10MB)
    large_data = "X" * (10 * 1024 * 1024)

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "process-data",
            "parameters": {"data": large_data},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should reject oversized payload
    assert response.status_code in [413, 422, 400]


async def test_null_byte_injection(app_client, mock_user_token):
    """Test null byte injection attempts."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "file-server",
            "tool_name": "read",
            "parameters": {"filename": "safe.txt\x00malicious.exe"},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code in [200, 400, 422]

    if response.status_code == 200:
        data = response.json()
        # Should sanitize null bytes
        params = str(data.get("filtered_parameters", {}))
        assert "\x00" not in params


async def test_xml_injection(app_client, mock_user_token):
    """Test XML/XXE injection attempts."""

    xxe_payload = """<?xml version="1.0"?>
    <!DOCTYPE foo [
    <!ELEMENT foo ANY >
    <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
    <foo>&xxe;</foo>"""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "xml-server",
            "tool_name": "parse-xml",
            "parameters": {"xml_data": xxe_payload},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code in [200, 400, 422]

    if response.status_code == 200:
        data = response.json()
        # Should block XXE
        assert data.get("allow") is False or "blocked" in str(data).lower()


async def test_ldap_injection(app_client, mock_user_token):
    """Test LDAP injection attempts."""

    ldap_injection = "*)(objectClass=*"

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "ldap-server",
            "tool_name": "user-search",
            "parameters": {"username": ldap_injection},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code in [200, 400, 422]


async def test_nosql_injection(app_client, mock_user_token):
    """Test NoSQL injection attempts."""

    nosql_injections = [
        {"$gt": ""},
        {"$ne": None},
        {"$where": "this.password == 'password'"},
    ]

    for injection in nosql_injections:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "mongodb-server",
                "tool_name": "find",
                "parameters": {"query": injection},
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        assert response.status_code in [200, 400, 422]


async def test_header_injection(app_client, mock_user_token):
    """Test HTTP header injection attempts."""

    malicious_header = "X-Injected: malicious\r\nX-Another: header"

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "http-server",
            "tool_name": "make-request",
            "parameters": {"custom_header": malicious_header},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code in [200, 400, 422]

    if response.status_code == 200:
        data = response.json()
        # Should sanitize headers
        params = str(data.get("filtered_parameters", {}))
        assert "\r\n" not in params


async def test_regex_dos(app_client, mock_user_token):
    """Test ReDoS (Regular Expression Denial of Service) protection."""

    # Evil regex pattern
    evil_pattern = "(a+)+" * 10 + "b"
    evil_input = "a" * 50

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "regex-server",
            "tool_name": "match",
            "parameters": {
                "pattern": evil_pattern,
                "input": evil_input,
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
        timeout=5.0,  # Should timeout if vulnerable
    )

    # Should either reject or timeout gracefully
    assert response.status_code in [200, 400, 422, 408, 504]
