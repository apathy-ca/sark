"""Integration tests for advanced OPA policies.

Tests time-based access, IP filtering, and MFA requirements.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from sark.services.policy.opa_client import AuthorizationInput, OPAClient


@pytest.fixture
def opa_client():
    """Create OPA client without cache for testing."""
    return OPAClient(cache_enabled=False)


# ============================================================================
# TIME-BASED ACCESS CONTROL TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_critical_tool_business_hours_required(mock_post, opa_client):
    """Critical tools should be blocked outside business hours."""
    # Mock OPA response - denied due to time restriction
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "policy_results": {
                "time_based": {
                    "allow": False,
                    "reason": "Time restrictions violated: Critical tools require business hours access",
                    "violations": [
                        {
                            "type": "time_restriction",
                            "reason": "Critical tools require business hours access",
                        }
                    ],
                }
            },
            "reason": "Access denied by time restrictions: Time restrictions violated: Critical tools require business hours access",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    # Outside business hours
    auth_input = AuthorizationInput(
        user={"id": "dev1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={"timestamp": "2024-01-01T20:00:00Z"},  # 8 PM
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert not decision.allow
    assert "time restrictions" in decision.reason.lower()


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_admin_bypass_time_restrictions(mock_post, opa_client):
    """Admins should bypass time restrictions."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": True,
            "policy_results": {
                "time_based": {
                    "allow": True,
                    "reason": "Admin role exempt from time restrictions",
                }
            },
            "reason": "Access granted by all policies",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "admin1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={"timestamp": "2024-01-01T20:00:00Z"},  # 8 PM, off-hours
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow
    assert "granted" in decision.reason.lower()


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_emergency_override_time_restrictions(mock_post, opa_client):
    """Emergency override should allow access outside business hours."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": True,
            "policy_results": {
                "time_based": {"allow": True, "reason": "Emergency override approved"}
            },
            "reason": "Access granted by all policies",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "dev1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={
            "timestamp": "2024-01-06T20:00:00Z",  # Saturday 8 PM
            "emergency_override": True,
            "emergency_reason": "Production outage",
            "emergency_approver": "manager@company.com",
        },
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow


# ============================================================================
# IP FILTERING TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_ip_on_allowlist_allowed(mock_post, opa_client):
    """IP on allowlist should be allowed."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": True,
            "policy_results": {
                "ip_filtering": {
                    "allow": True,
                    "reason": "IP 192.168.1.100 allowed",
                    "client_ip": "192.168.1.100",
                }
            },
            "reason": "Access granted by all policies",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "dev1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "test_tool", "sensitivity_level": "medium"},
        context={
            "client_ip": "192.168.1.100",
        },
        policy_config={
            "ip_allowlist": ["192.168.1.0/24"],
            "ip_blocklist": [],
        },
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_ip_on_blocklist_blocked(mock_post, opa_client):
    """IP on blocklist should be blocked."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "policy_results": {
                "ip_filtering": {
                    "allow": False,
                    "reason": "IP filtering violations: IP address 192.168.1.100 is on blocklist",
                    "violations": [
                        {
                            "type": "ip_blocked",
                            "reason": "IP address 192.168.1.100 is on blocklist",
                        }
                    ],
                }
            },
            "reason": "Access denied by IP filtering: IP address 192.168.1.100 is on blocklist",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "dev1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "test_tool", "sensitivity_level": "medium"},
        context={"client_ip": "192.168.1.100"},
        policy_config={
            "ip_allowlist": ["192.168.1.0/24"],
            "ip_blocklist": ["192.168.1.100"],
        },
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert not decision.allow
    assert "blocklist" in decision.reason.lower()


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_critical_tool_requires_vpn(mock_post, opa_client):
    """Critical tools should require VPN (private IP)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "policy_results": {
                "ip_filtering": {
                    "allow": False,
                    "reason": "IP filtering violations: VPN connection required for this operation",
                    "violations": [
                        {
                            "type": "vpn_required",
                            "reason": "VPN connection required for this operation",
                        }
                    ],
                }
            },
            "reason": "Access denied by IP filtering: VPN connection required",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "dev1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={"client_ip": "1.2.3.4"},  # Public IP
        policy_config={
            "ip_allowlist": ["0.0.0.0/0"],  # Allow all IPs
            "ip_blocklist": [],
        },
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert not decision.allow
    assert "vpn" in decision.reason.lower() or "ip filtering" in decision.reason.lower()


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_geographic_restrictions(mock_post, opa_client):
    """Geographic restrictions should block access from unauthorized countries."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "policy_results": {
                "ip_filtering": {
                    "allow": False,
                    "reason": "IP filtering violations: Access from country CN not allowed",
                    "violations": [
                        {
                            "type": "geo_restriction",
                            "reason": "Access from country CN not allowed",
                        }
                    ],
                }
            },
            "reason": "Access denied by IP filtering: Geographic restrictions",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "dev1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={
            "client_ip": "1.2.3.4",
            "geo_country": "CN",
        },
        policy_config={
            "geo_restrictions_enabled": True,
            "allowed_countries": ["US", "CA", "GB"],
            "ip_allowlist": ["0.0.0.0/0"],
            "ip_blocklist": [],
        },
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert not decision.allow


# ============================================================================
# MFA REQUIREMENT TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_critical_tool_requires_mfa(mock_post, opa_client):
    """Critical tools should require MFA."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "policy_results": {
                "mfa_required": {
                    "allow": False,
                    "reason": "MFA requirements not met: Multi-factor authentication required but not verified",
                    "violations": [
                        {
                            "type": "mfa_not_verified",
                            "reason": "Multi-factor authentication required but not verified",
                        }
                    ],
                    "mfa_status": {
                        "required": True,
                        "verified": False,
                    },
                }
            },
            "reason": "Access denied by MFA requirements: Multi-factor authentication required",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "dev1", "role": "developer", "mfa_verified": False},
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert not decision.allow
    assert "mfa" in decision.reason.lower()


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_mfa_verified_allows_access(mock_post, opa_client):
    """MFA verified should allow access to critical tools."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": True,
            "policy_results": {
                "mfa_required": {
                    "allow": True,
                    "reason": "MFA verified and session valid",
                    "mfa_status": {
                        "required": True,
                        "verified": True,
                        "session_valid": True,
                    },
                }
            },
            "reason": "Access granted by all policies",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    current_time = int(time.time() * 1_000_000_000)  # Current time in nanoseconds
    mfa_time = current_time - (10 * 60 * 1_000_000_000)  # 10 minutes ago

    auth_input = AuthorizationInput(
        user={
            "id": "dev1",
            "role": "developer",
            "mfa_verified": True,
            "mfa_timestamp": mfa_time,
            "mfa_methods": ["totp"],
        },
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_mfa_session_expired(mock_post, opa_client):
    """Expired MFA session should deny access."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "policy_results": {
                "mfa_required": {
                    "allow": False,
                    "reason": "MFA requirements not met: MFA session expired",
                    "violations": [
                        {
                            "type": "mfa_session_expired",
                            "reason": "MFA session expired",
                        }
                    ],
                    "mfa_status": {
                        "required": True,
                        "verified": True,
                        "session_valid": False,
                        "session_expired": True,
                    },
                }
            },
            "reason": "Access denied by MFA requirements: MFA session expired",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    current_time = int(time.time() * 1_000_000_000)
    mfa_time = current_time - (2 * 3600 * 1_000_000_000)  # 2 hours ago

    auth_input = AuthorizationInput(
        user={
            "id": "dev1",
            "role": "developer",
            "mfa_verified": True,
            "mfa_timestamp": mfa_time,
            "mfa_methods": ["totp"],
        },
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert not decision.allow
    assert "mfa" in decision.reason.lower() or "session" in decision.reason.lower()


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_service_account_bypass_mfa(mock_post, opa_client):
    """Service accounts with API keys should bypass MFA."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": True,
            "policy_results": {
                "mfa_required": {
                    "allow": True,
                    "reason": "Service account with valid API key",
                }
            },
            "reason": "Access granted by all policies",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    auth_input = AuthorizationInput(
        user={"id": "service1", "role": "service"},
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={"api_key": "valid_api_key_123"},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_step_up_authentication_required(mock_post, opa_client):
    """Step-up authentication should be required for very sensitive operations."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "policy_results": {
                "mfa_required": {
                    "allow": False,
                    "reason": "MFA requirements not met: Additional authentication verification required",
                    "violations": [
                        {
                            "type": "step_up_required",
                            "reason": "Additional authentication verification required for this sensitive operation",
                        }
                    ],
                }
            },
            "reason": "Access denied by MFA requirements: Step-up authentication required",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    current_time = int(time.time() * 1_000_000_000)
    mfa_time = current_time - (6 * 60 * 1_000_000_000)  # 6 minutes ago (>5 min)

    auth_input = AuthorizationInput(
        user={
            "id": "dev1",
            "role": "developer",
            "mfa_verified": True,
            "mfa_timestamp": mfa_time,
            "mfa_methods": ["totp"],
        },
        action="tool:invoke",
        tool={"name": "critical_tool", "sensitivity_level": "critical"},
        context={},  # No step_up_verified
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert not decision.allow


# ============================================================================
# COMBINED POLICY TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_all_policies_must_pass(mock_post, opa_client):
    """All policies must pass for access to be granted."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "allow": True,
            "policy_results": {
                "rbac": {"allow": True},
                "team_access": {"allow": True},
                "sensitivity": {"allow": True},
                "time_based": {"allow": True},
                "ip_filtering": {"allow": True},
                "mfa_required": {"allow": True},
            },
            "reason": "Access granted by all policies",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    current_time = int(time.time() * 1_000_000_000)
    mfa_time = current_time - (5 * 60 * 1_000_000_000)  # 5 minutes ago

    auth_input = AuthorizationInput(
        user={
            "id": "dev1",
            "role": "developer",
            "mfa_verified": True,
            "mfa_timestamp": mfa_time,
            "mfa_methods": ["totp"],
        },
        action="tool:invoke",
        tool={"name": "test_tool", "sensitivity_level": "medium"},
        context={
            "client_ip": "10.0.0.100",  # Corporate network
            "timestamp": "2024-01-01T10:00:00Z",  # Business hours
        },
        policy_config={
            "ip_allowlist": ["10.0.0.0/8"],
            "ip_blocklist": [],
        },
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow
    assert "granted" in decision.reason.lower()
