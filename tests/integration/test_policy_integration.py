"""
Integration tests for policy enforcement across all operations.

Tests policy evaluation workflows including:
- Server registration with policy checks
- Tool invocation authorization
- Bulk operations policy evaluation
- Policy denials and error handling
- Multi-policy evaluation
- Fail-closed behavior verification
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from sark.models.mcp_server import MCPServer, SensitivityLevel, TransportType
from sark.models.policy import Policy, PolicyStatus, PolicyVersion
from sark.models.user import User
from sark.services.policy.opa_client import OPAClient
from sark.services.policy.policy_service import PolicyService


@pytest.fixture
async def opa_client():
    """OPA client for policy tests."""
    return OPAClient(base_url="http://localhost:8181")


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def policy_service(opa_client, mock_db_session):
    """Policy service for tests."""
    return PolicyService(opa_client=opa_client, db=mock_db_session)


@pytest.fixture
def test_policy():
    """Test policy fixture."""
    return Policy(
        id=uuid4(),
        name="test-policy",
        description="Test policy for integration tests",
        policy_type="authorization",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def test_server():
    """Test MCP server fixture."""
    return MCPServer(
        id=uuid4(),
        name="test-server",
        description="Test server",
        transport=TransportType.HTTP,
        endpoint="http://example.com",
        sensitivity_level=SensitivityLevel.MEDIUM,
        owner_id=uuid4(),
        team_id=uuid4(),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def test_user():
    """Test user fixture."""
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password_here",
        role="developer",
        is_active=True,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


# ============================================================================
# Server Registration Policy Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_allows_server_registration(opa_client, test_user, test_server):
    """Test that policy allows authorized server registration."""
    # Mock OPA to allow registration
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"allow": True}}

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {
                "type": "server",
                "name": test_server.name,
                "sensitivity": test_server.sensitivity_level.value
            }
        })

    assert decision.allow is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_denies_unauthorized_registration(opa_client, test_user):
    """Test that policy denies server registration for unauthorized users."""
    # Mock OPA to deny registration
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "reason": "User lacks permission to register high-sensitivity servers"
        }
    }

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {
                "type": "server",
                "sensitivity": "high"
            }
        })

    assert decision.allow is False
    assert "lacks permission" in decision.reason


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_enforces_sensitivity_levels(opa_client, test_user):
    """Test that policy enforces sensitivity level restrictions."""
    # Low sensitivity - should allow
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"allow": True}}

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {"type": "server", "sensitivity": "low"}
        })

    assert decision.allow is True

    # High sensitivity - should deny for regular user
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "reason": "Insufficient clearance for high sensitivity"
        }
    }

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {"type": "server", "sensitivity": "high"}
        })

    assert decision.allow is False


# ============================================================================
# Tool Invocation Authorization Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_allows_tool_invocation(opa_client, test_user):
    """Test that policy allows authorized tool invocation."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"allow": True}}

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "invoke",
            "resource": {
                "type": "tool",
                "name": "search_tool",
                "server": "test-server"
            }
        })

    assert decision.allow is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_denies_dangerous_tool_invocation(opa_client, test_user):
    """Test that policy denies invocation of dangerous tools."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "reason": "Tool classified as dangerous"
        }
    }

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "invoke",
            "resource": {
                "type": "tool",
                "name": "delete_all_tool",
                "dangerous": True
            }
        })

    assert decision.allow is False


# ============================================================================
# Bulk Operations Policy Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_evaluates_bulk_operations(opa_client, test_user):
    """Test that policy evaluates bulk operations correctly."""
    # Mock OPA to allow bulk registration
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"allow": True}}

    servers = [
        {"name": "server-1", "sensitivity": "low"},
        {"name": "server-2", "sensitivity": "low"},
        {"name": "server-3", "sensitivity": "medium"}
    ]

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        for server in servers:
            decision = await opa_client.evaluate_policy({
                "user": {"id": str(test_user.id), "role": "user"},
                "action": "register",
                "resource": {"type": "server", **server}
            })
            assert decision.allow is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_fails_bulk_on_single_denial(opa_client, test_user):
    """Test that bulk operation fails if any item is denied (transactional)."""
    servers = [
        {"name": "server-1", "sensitivity": "low"},
        {"name": "server-2", "sensitivity": "high"},  # This will be denied
        {"name": "server-3", "sensitivity": "medium"}
    ]

    # Mock responses - allow first, deny second
    responses = [
        {"result": {"allow": True}},
        {"result": {"allow": False, "reason": "High sensitivity not allowed"}},
        {"result": {"allow": True}}
    ]

    with patch.object(opa_client.client, "post", new=AsyncMock(side_effect=[
        MagicMock(json=MagicMock(return_value=resp)) for resp in responses
    ])):
        denied_found = False
        for server in servers:
            decision = await opa_client.evaluate_policy({
                "user": {"id": str(test_user.id), "role": "user"},
                "action": "register",
                "resource": {"type": "server", **server}
            })
            if not decision.allow:
                denied_found = True
                break

    assert denied_found is True


# ============================================================================
# Policy Denial Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_denial_provides_reason(opa_client, test_user):
    """Test that policy denials provide clear reasons."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "reason": "User does not belong to the required team"
        }
    }

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "access",
            "resource": {"type": "server", "team": "engineering"}
        })

    assert decision.allow is False
    assert decision.reason is not None
    assert "team" in decision.reason.lower()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_policy_handles_opa_errors_gracefully(opa_client, test_user):
    """Test that OPA errors are handled gracefully (fail-closed)."""
    # Simulate OPA error
    with patch.object(opa_client.client, "post", new=AsyncMock(side_effect=Exception("OPA connection failed"))):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {"type": "server"}
        })

    # Should fail closed
    assert decision.allow is False


# ============================================================================
# Multi-Policy Evaluation Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
async def test_create_multiple_policy_versions(policy_service, test_policy):
    """Test creating multiple versions of a policy."""
    # Mock database responses
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = test_policy
    policy_service.db.execute = AsyncMock(return_value=mock_result)

    # Create first version
    version1 = await policy_service.create_version(
        policy_id=test_policy.id,
        rego_code="package test\nallow = true",
        change_description="Initial version"
    )

    assert version1.version_number == 1
    assert version1.status == PolicyStatus.DRAFT

    # Create second version
    policy_service.db.execute = AsyncMock(return_value=mock_result)
    version2 = await policy_service.create_version(
        policy_id=test_policy.id,
        rego_code="package test\nallow = false",
        change_description="Deny all"
    )

    assert version2.version_number == 2


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
async def test_activate_policy_version(policy_service, test_policy):
    """Test activating a policy version."""
    version = PolicyVersion(
        id=uuid4(),
        policy_id=test_policy.id,
        version_number=1,
        rego_code="package test\nallow = true",
        status=PolicyStatus.DRAFT,
        created_at=datetime.now(UTC)
    )

    # Mock database responses
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = version
    policy_service.db.execute = AsyncMock(return_value=mock_result)

    # Mock OPA upload
    with patch.object(policy_service.opa_client.client, "put", new=AsyncMock()):
        activated = await policy_service.activate_version(version.id)

    assert activated.status == PolicyStatus.ACTIVE


# ============================================================================
# Fail-Closed Behavior Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_fail_closed_on_network_error(opa_client, test_user):
    """Test fail-closed behavior on network errors."""
    import httpx

    # Simulate network timeout
    with patch.object(opa_client.client, "post", new=AsyncMock(side_effect=httpx.TimeoutException("Timeout"))):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {"type": "server"}
        })

    assert decision.allow is False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_fail_closed_on_invalid_response(opa_client, test_user):
    """Test fail-closed behavior on invalid OPA response."""
    # Mock invalid JSON response
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {"type": "server"}
        })

    assert decision.allow is False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.policy
@pytest.mark.requires_opa
async def test_fail_closed_on_missing_result(opa_client, test_user):
    """Test fail-closed behavior when OPA response is missing result."""
    # Mock response without result field
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "Policy not found"}

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "register",
            "resource": {"type": "server"}
        })

    assert decision.allow is False
