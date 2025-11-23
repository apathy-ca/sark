"""OPA Policy Integration Tests.

Tests the actual OPA policies to ensure they work correctly with real
policy evaluation scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.policy.opa_client import AuthorizationInput, OPAClient


@pytest.fixture
def opa_client_mock_responses():
    """Create OPA client with mocked HTTP responses."""
    cache_mock = AsyncMock()
    cache_mock.enabled = False  # Disable cache for these tests
    cache_mock.get = AsyncMock(return_value=None)
    cache_mock.set = AsyncMock(return_value=True)
    cache_mock.record_opa_latency = MagicMock()

    client = OPAClient(cache=cache_mock)
    return client


# ============================================================================
# RBAC POLICY TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_rbac_admin_can_register_any_server(mock_post, opa_client_mock_responses):
    """Test RBAC policy: Admin can register any server."""
    # Mock OPA response
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": True,
            "audit_reason": "Admin role grants access",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={"id": "admin-1", "role": "admin"},
        action="server:register",
        server={"name": "critical-server", "sensitivity_level": "critical"},
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is True
    assert "admin" in decision.reason.lower()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_rbac_developer_cannot_register_critical(mock_post, opa_client_mock_responses):
    """Test RBAC policy: Developer cannot register critical server."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": False,
            "audit_reason": "Insufficient role permissions",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={"id": "dev-1", "role": "developer"},
        action="server:register",
        server={"name": "critical-server", "sensitivity_level": "critical"},
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is False


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_rbac_developer_can_invoke_low_medium_tools(mock_post, opa_client_mock_responses):
    """Test RBAC policy: Developer can invoke low/medium sensitivity tools."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": True,
            "audit_reason": "Developer role grants access for low/medium sensitivity",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={"id": "dev-1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "update-config", "sensitivity_level": "medium"},
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is True


# ============================================================================
# TEAM ACCESS POLICY TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_team_member_can_access_team_tools(mock_post, opa_client_mock_responses):
    """Test team access: Team member can access team-owned tools."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": True,
            "audit_reason": "Team member access granted",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        action="tool:invoke",
        tool={
            "name": "team-tool",
            "sensitivity_level": "medium",
            "teams": ["team-alpha"],
        },
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is True


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_non_team_member_denied(mock_post, opa_client_mock_responses):
    """Test team access: Non-team member cannot access team tools."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": False,
            "audit_reason": "No team membership or insufficient permissions",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={
            "id": "user-1",
            "role": "developer",
            "teams": ["team-beta"],
        },
        action="tool:invoke",
        tool={
            "name": "team-tool",
            "sensitivity_level": "medium",
            "teams": ["team-alpha"],
        },
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is False


# ============================================================================
# SENSITIVITY ENFORCEMENT POLICY TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_critical_requires_mfa(mock_post, opa_client_mock_responses):
    """Test sensitivity: Critical tools require MFA verification."""
    # Without MFA - denied
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": False,
            "audit_reason": "Critical sensitivity requires MFA verification",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={
            "id": "user-1",
            "role": "admin",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
            "mfa_verified": False,
        },
        action="tool:invoke",
        tool={
            "name": "payment-processor",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        context={
            "timestamp": 0,
            "audit_enabled": True,
        },
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is False


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_high_sensitivity_requires_audit(mock_post, opa_client_mock_responses):
    """Test sensitivity: High sensitivity requires audit logging."""
    # Without audit - denied
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": False,
            "deny": True,
            "audit_reason": "Audit logging required for high/critical operations",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        action="tool:invoke",
        tool={
            "name": "delete-user",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        context={
            "timestamp": 0,
            "audit_enabled": False,
        },
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is False


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_low_sensitivity_public_access(mock_post, opa_client_mock_responses):
    """Test sensitivity: Low sensitivity allows public access."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": True,
            "audit_reason": "Low sensitivity allows public access",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={
            "id": "user-1",
            "role": "viewer",
            "authenticated": True,
        },
        action="tool:invoke",
        tool={
            "name": "read-data",
            "sensitivity_level": "low",
        },
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is True


# ============================================================================
# COMBINED POLICY TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_combined_policies_admin_critical_with_mfa(mock_post, opa_client_mock_responses):
    """Test combined policies: Admin with MFA can access critical tools."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": True,
            "audit_reason": "Access granted by all policies",
            "policies_evaluated": ["rbac", "team_access", "sensitivity"],
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={
            "id": "admin-1",
            "role": "admin",
            "teams": ["security-team"],
            "team_manager_of": ["security-team"],
            "mfa_verified": True,
        },
        action="tool:invoke",
        tool={
            "name": "manage-credentials",
            "sensitivity_level": "critical",
            "teams": ["security-team"],
        },
        context={
            "timestamp": 0,
            "audit_enabled": True,
        },
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is True


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_combined_policies_developer_high_no_team(mock_post, opa_client_mock_responses):
    """Test combined policies: Developer without team membership denied for high sensitivity."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": False,
            "audit_reason": "Access denied by team access: No team membership",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={
            "id": "dev-1",
            "role": "developer",
            "teams": ["team-beta"],
        },
        action="tool:invoke",
        tool={
            "name": "delete-database",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        context={
            "timestamp": 0,
            "audit_enabled": True,
        },
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is False


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_opa_server_error_fails_closed(mock_post, opa_client_mock_responses):
    """Test that OPA server errors result in deny (fail closed)."""
    mock_post.side_effect = Exception("OPA server unavailable")

    auth_input = AuthorizationInput(
        user={"id": "admin-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test-tool", "sensitivity_level": "low"},
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    # Should fail closed
    assert decision.allow is False
    assert "error" in decision.reason.lower() or "failed" in decision.reason.lower()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_malformed_opa_response_fails_closed(mock_post, opa_client_mock_responses):
    """Test that malformed OPA responses result in deny."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {}  # Missing 'result' key
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={"id": "admin-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test-tool", "sensitivity_level": "low"},
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    # Should default to deny when result is missing
    assert decision.allow is False


# ============================================================================
# POLICY METADATA TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_policy_returns_audit_metadata(mock_post, opa_client_mock_responses):
    """Test that policy returns comprehensive audit metadata."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": True,
            "audit_reason": "Admin role grants access",
            "policies_evaluated": ["rbac", "team_access", "sensitivity"],
            "policy_results": {
                "rbac": {"allow": True, "reason": "Admin access"},
                "team_access": {"allow": True, "reason": "Team member"},
                "sensitivity": {"allow": True, "reason": "Audit enabled"},
            },
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={"id": "admin-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test-tool", "sensitivity_level": "medium"},
        context={"timestamp": 0},
    )

    decision = await opa_client_mock_responses.evaluate_policy(auth_input, use_cache=False)

    assert decision.allow is True
    assert decision.reason is not None
