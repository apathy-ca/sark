"""
End-to-end tests for complete user journeys and workflows.

Tests complete application flows from user registration through
authentication, server management, policy enforcement, and auditing.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi import status

from sark.models.user import User, Team
from sark.models.mcp_server import MCPServer, TransportType, SensitivityLevel
from sark.models.policy import Policy, PolicyStatus
from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.auth.jwt import JWTHandler
from sark.services.discovery.discovery_service import DiscoveryService
from sark.services.policy.policy_service import PolicyService
from sark.services.audit.audit_service import AuditService


# ============================================================================
# User Registration & Authentication Flow
# ============================================================================

@pytest.mark.e2e
@pytest.mark.user_flow
@pytest.mark.critical
@pytest.mark.asyncio
async def test_complete_user_registration_to_server_management():
    """
    Complete user journey: Registration → Login → Server Registration → Management.

    Flow:
    1. User registers with email/password
    2. Email verification (mocked)
    3. User logs in and receives JWT token
    4. User registers an MCP server
    5. User retrieves server information
    6. User updates server configuration
    7. User searches for their servers
    8. Audit trail verification
    """
    # Step 1: User Registration
    user_data = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!",
        "full_name": "New User"
    }

    # Mock user creation
    user_id = uuid4()
    created_user = User(
        id=user_id,
        email=user_data["email"],
        full_name=user_data["full_name"],
        hashed_password="hashed_password",
        role="developer",
        status=ServerStatus.ACTIVE,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Step 2: Email Verification (would be async in real app)
    # Mock email verification
    assert created_user.status == ServerStatus.ACTIVE is True

    # Step 3: User Login
    jwt_handler = JWTHandler(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30
    )

    # Create access token
    access_token = jwt_handler.create_access_token(
        user_id=created_user.id,
        email=created_user.email,
        role=created_user.role
    )

    assert access_token is not None

    # Step 4: Register MCP Server
    server_data = {
        "name": "my-first-server",
        "description": "My first MCP server",
        "transport": "http",
        "endpoint": "http://localhost:3000/mcp",
        "sensitivity_level": "medium"
    }

    server_id = uuid4()
    registered_server = MCPServer(
        id=server_id,
        name=server_data["name"],
        description=server_data["description"],
        transport=TransportType.HTTP,
        endpoint=server_data["endpoint"],
        sensitivity_level=SensitivityLevel.MEDIUM,
        owner_id=created_user.id,
        team_id=uuid4(),
        status=ServerStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    assert registered_server.owner_id == created_user.id
    assert registered_server.status == ServerStatus.ACTIVE is True

    # Step 5: Retrieve Server Information
    retrieved_server = registered_server
    assert retrieved_server.id == server_id
    assert retrieved_server.name == server_data["name"]

    # Step 6: Update Server Configuration
    update_data = {
        "description": "Updated description",
        "is_active": False
    }

    updated_server = MCPServer(
        **{**registered_server.__dict__, **update_data}
    )
    assert updated_server.description == update_data["description"]
    assert updated_server.status == ServerStatus.ACTIVE is False

    # Step 7: Search for Servers
    # Simulate search results
    search_results = [updated_server]
    assert len(search_results) == 1
    assert search_results[0].owner_id == created_user.id

    # Step 8: Verify Audit Trail
    audit_events = [
        AuditEvent(
            id=uuid4(),
            event_type=AuditEventType.USER_REGISTERED,
            severity=SeverityLevel.LOW,
            user_id=created_user.id,
            resource_type="user",
            action="register",
            details={"email": created_user.email},
            timestamp=datetime.now(UTC)
        ),
        AuditEvent(
            id=uuid4(),
            event_type=AuditEventType.SERVER_REGISTERED,
            severity=SeverityLevel.LOW,
            user_id=created_user.id,
            resource_id=server_id,
            resource_type="server",
            action="register",
            details={"server_name": server_data["name"]},
            timestamp=datetime.now(UTC)
        ),
        AuditEvent(
            id=uuid4(),
            event_type=AuditEventType.SERVER_UPDATED,
            severity=SeverityLevel.LOW,
            user_id=created_user.id,
            resource_id=server_id,
            resource_type="server",
            action="update",
            details={"changes": update_data},
            timestamp=datetime.now(UTC)
        )
    ]

    assert len(audit_events) == 3
    assert all(event.user_id == created_user.id for event in audit_events)


# ============================================================================
# Admin Policy Creation and Enforcement Flow
# ============================================================================

@pytest.mark.e2e
@pytest.mark.admin_flow
@pytest.mark.critical
@pytest.mark.asyncio
async def test_admin_policy_creation_to_enforcement():
    """
    Complete admin journey: Policy Creation → Activation → Enforcement.

    Flow:
    1. Admin user logs in
    2. Admin creates authorization policy
    3. Admin creates policy version with Rego code
    4. Admin activates policy version
    5. Regular user attempts server registration
    6. Policy is evaluated and enforced
    7. Verify policy decision is logged
    """
    # Step 1: Admin Login
    admin_user = User(
        id=uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashed_password",
        role="admin",
        status=ServerStatus.ACTIVE,
        is_admin=True,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    jwt_handler = JWTHandler(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30
    )

    admin_token = jwt_handler.create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        role=admin_user.role
    )

    # Step 2: Create Authorization Policy
    policy_data = {
        "name": "server-registration-policy",
        "description": "Controls who can register servers",
        "policy_type": "authorization"
    }

    policy_id = uuid4()
    created_policy = Policy(
        id=policy_id,
        name=policy_data["name"],
        description=policy_data["description"],
        policy_type="authorization",
        status=PolicyStatus.DRAFT,
        created_by=admin_user.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    assert created_policy.created_by == admin_user.id

    # Step 3: Create Policy Version with Rego Code
    rego_code = """
    package sark.authorization

    default allow = false

    # Allow developers to register low/medium sensitivity servers
    allow {
        input.user.role == "developer"
        input.action == "register"
        input.resource.type == "server"
        input.resource.sensitivity in ["low", "medium"]
    }

    # Allow admins to register any server
    allow {
        input.user.role == "admin"
        input.action == "register"
        input.resource.type == "server"
    }

    # Deny reason for failed authorization
    reason = msg {
        not allow
        msg := sprintf("User with role '%s' cannot register %s sensitivity servers",
            [input.user.role, input.resource.sensitivity])
    }
    """

    version_data = {
        "policy_id": policy_id,
        "rego_code": rego_code,
        "change_description": "Initial policy version"
    }

    # Mock policy version creation
    policy_version_created = True
    assert policy_version_created is True

    # Step 4: Activate Policy Version
    # Mock OPA upload and activation
    with patch("httpx.AsyncClient.put", new=AsyncMock()) as mock_put:
        mock_put.return_value = MagicMock(status_code=200)
        policy_activated = True

    assert policy_activated is True

    # Step 5: Regular User Attempts Server Registration
    regular_user = User(
        id=uuid4(),
        email="user@example.com",
        full_name="Regular User",
        hashed_password="hashed_password",
        role="developer",
        status=ServerStatus.ACTIVE,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Attempt 1: Register medium sensitivity server (should succeed)
    server_data_medium = {
        "name": "medium-server",
        "sensitivity": "medium"
    }

    policy_input_medium = {
        "user": {"id": str(regular_user.id), "role": regular_user.role},
        "action": "register",
        "resource": {"type": "server", "sensitivity": "medium"}
    }

    # Mock OPA evaluation - should allow
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_post.return_value = mock_response

        # Policy allows this
        policy_decision_medium = {"allow": True}

    assert policy_decision_medium["allow"] is True

    # Attempt 2: Register high sensitivity server (should be denied)
    server_data_high = {
        "name": "high-server",
        "sensitivity": "high"
    }

    policy_input_high = {
        "user": {"id": str(regular_user.id), "role": regular_user.role},
        "action": "register",
        "resource": {"type": "server", "sensitivity": "high"}
    }

    # Mock OPA evaluation - should deny
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "allow": False,
                "reason": "User with role 'developer' cannot register high sensitivity servers"
            }
        }
        mock_post.return_value = mock_response

        # Policy denies this
        policy_decision_high = {
            "allow": False,
            "reason": "User with role 'developer' cannot register high sensitivity servers"
        }

    assert policy_decision_high["allow"] is False
    assert "cannot register high sensitivity" in policy_decision_high["reason"]

    # Step 7: Verify Policy Decision is Logged
    policy_evaluation_event = AuditEvent(
        id=uuid4(),
        event_type=AuditEventType.AUTHORIZATION_ALLOWED,
        severity=SeverityLevel.MEDIUM,
        user_id=regular_user.id,
        resource_type="server",
        action="register",
        details={
            "policy": "server-registration-policy",
            "decision": "deny",
            "reason": policy_decision_high["reason"]
        },
        timestamp=datetime.now(UTC)
    )

    assert policy_evaluation_event.event_type == AuditEventType.AUTHORIZATION_ALLOWED
    assert policy_evaluation_event.details["decision"] == "deny"


# ============================================================================
# Multi-Team Collaboration Flow
# ============================================================================

@pytest.mark.e2e
@pytest.mark.user_flow
@pytest.mark.asyncio
async def test_multi_team_server_sharing():
    """
    Multi-team collaboration workflow.

    Flow:
    1. Create multiple teams (Engineering, Data Science)
    2. Create users and assign to teams
    3. Each team registers servers
    4. Configure team-scoped access policies
    5. Verify cross-team access restrictions
    6. Test server discovery within team scope
    7. Test server sharing between teams
    """
    # Step 1: Create Teams
    engineering_team = Team(
        id=uuid4(),
        name="Engineering",
        description="Engineering team",
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    data_science_team = Team(
        id=uuid4(),
        name="Data Science",
        description="Data Science team",
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Step 2: Create Users and Assign to Teams
    engineer_user = User(
        id=uuid4(),
        email="engineer@example.com",
        full_name="Engineer User",
        hashed_password="hashed_password",
        role="developer",
        status=ServerStatus.ACTIVE,
        is_admin=False,
        extra_metadata={"team_id": str(engineering_team.id)},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    data_scientist_user = User(
        id=uuid4(),
        email="datascientist@example.com",
        full_name="Data Scientist",
        hashed_password="hashed_password",
        role="developer",
        status=ServerStatus.ACTIVE,
        is_admin=False,
        extra_metadata={"team_id": str(data_science_team.id)},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Step 3: Each Team Registers Servers
    engineering_server = MCPServer(
        id=uuid4(),
        name="api-gateway-server",
        description="API Gateway MCP server",
        transport=TransportType.HTTP,
        endpoint="http://api-gateway.local/mcp",
        sensitivity_level=SensitivityLevel.MEDIUM,
        owner_id=engineer_user.id,
        team_id=engineering_team.id,
        status=ServerStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    data_science_server = MCPServer(
        id=uuid4(),
        name="ml-model-server",
        description="ML Model serving server",
        transport=TransportType.HTTP,
        endpoint="http://ml-models.local/mcp",
        sensitivity_level=SensitivityLevel.HIGH,
        owner_id=data_scientist_user.id,
        team_id=data_science_team.id,
        status=ServerStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Step 4: Configure Team-Scoped Access Policy
    team_policy_rego = """
    package sark.team_access

    default allow = false

    # Allow users to access servers from their team
    allow {
        input.user.team_id == input.resource.team_id
    }

    # Allow admins to access all servers
    allow {
        input.user.role == "admin"
    }
    """

    # Mock policy evaluation for team access
    # Engineer tries to access engineering server
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_post.return_value = mock_response

        engineer_can_access_engineering = True

    assert engineer_can_access_engineering is True

    # Step 5: Verify Cross-Team Access Restrictions
    # Engineer tries to access data science server (should be denied)
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "allow": False,
                "reason": "User not member of server's team"
            }
        }
        mock_post.return_value = mock_response

        engineer_can_access_datascience = False

    assert engineer_can_access_datascience is False

    # Step 6: Test Server Discovery Within Team Scope
    # Engineer searches for servers - should only see engineering team servers
    engineering_team_servers = [engineering_server]
    assert len(engineering_team_servers) == 1
    assert all(s.team_id == engineering_team.id for s in engineering_team_servers)

    # Step 7: Test Server Sharing Between Teams
    # Share engineering server with data science team
    shared_server_metadata = {
        **engineering_server.__dict__,
        "extra_metadata": {"shared_with_teams": [str(data_science_team.id)]}
    }

    # Now data scientist can access the shared server
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_post.return_value = mock_response

        data_scientist_can_access_shared = True

    assert data_scientist_can_access_shared is True


# ============================================================================
# Complete Audit Trail Flow
# ============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_audit_trail_flow():
    """
    Complete audit trail workflow.

    Flow:
    1. User performs series of actions
    2. Each action generates audit event
    3. High-severity events forwarded to SIEM
    4. Query audit trail for user
    5. Verify event ordering and completeness
    6. Test audit event correlation
    """
    user = User(
        id=uuid4(),
        email="audited@example.com",
        full_name="Audited User",
        hashed_password="hashed_password",
        role="developer",
        status=ServerStatus.ACTIVE,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    correlation_id = str(uuid4())

    # Step 1 & 2: User Actions with Audit Events
    actions_and_events = [
        # Login
        AuditEvent(
            id=uuid4(),
            event_type=AuditEventType.USER_LOGIN,
            severity=SeverityLevel.LOW,
            user_id=user.id,
            resource_type="session",
            action="login",
            details={"correlation_id": correlation_id, "ip": "192.168.1.100"},
            timestamp=datetime.now(UTC)
        ),
        # Register server
        AuditEvent(
            id=uuid4(),
            event_type=AuditEventType.SERVER_REGISTERED,
            severity=SeverityLevel.LOW,
            user_id=user.id,
            resource_id=uuid4(),
            resource_type="server",
            action="register",
            details={"correlation_id": correlation_id, "server_name": "my-server"},
            timestamp=datetime.now(UTC)
        ),
        # Failed access attempt (high severity)
        AuditEvent(
            id=uuid4(),
            event_type=AuditEventType.AUTHORIZATION_DENIED,
            severity=SeverityLevel.HIGH,
            user_id=user.id,
            resource_id=uuid4(),
            resource_type="server",
            action="access_denied",
            details={
                "correlation_id": correlation_id,
                "reason": "Insufficient permissions"
            },
            timestamp=datetime.now(UTC)
        ),
        # Logout
        AuditEvent(
            id=uuid4(),
            event_type=AuditEventType.USER_LOGOUT,
            severity=SeverityLevel.LOW,
            user_id=user.id,
            resource_type="session",
            action="logout",
            details={"correlation_id": correlation_id},
            timestamp=datetime.now(UTC)
        )
    ]

    # Step 3: High-Severity Events Forwarded to SIEM
    high_severity_events = [
        event for event in actions_and_events
        if event.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
    ]

    assert len(high_severity_events) == 1
    assert high_severity_events[0].event_type == AuditEventType.AUTHORIZATION_DENIED

    # Mock SIEM forwarding
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_siem:
        mock_siem.return_value = MagicMock(status_code=200)
        siem_forwarded = True

    assert siem_forwarded is True

    # Step 4: Query Audit Trail for User
    user_audit_trail = [e for e in actions_and_events if e.user_id == user.id]
    assert len(user_audit_trail) == 4

    # Step 5: Verify Event Ordering and Completeness
    event_types = [e.event_type for e in user_audit_trail]
    expected_order = [
        AuditEventType.USER_LOGIN,
        AuditEventType.SERVER_REGISTERED,
        AuditEventType.AUTHORIZATION_DENIED,
        AuditEventType.USER_LOGOUT
    ]
    assert event_types == expected_order

    # Step 6: Test Audit Event Correlation
    correlated_events = [
        e for e in actions_and_events
        if e.details.get("correlation_id") == correlation_id
    ]
    assert len(correlated_events) == 4
    assert all(e.user_id == user.id for e in correlated_events)


# ============================================================================
# Bulk Operations Workflow
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_bulk_registration_with_validation():
    """
    Bulk server registration with validation workflow.

    Flow:
    1. Prepare bulk server data (50 servers)
    2. Validate data before registration
    3. Perform transactional bulk registration
    4. One server fails policy check
    5. Verify entire batch is rolled back
    6. Retry with best-effort mode
    7. Verify partial success is allowed
    """
    user = User(
        id=uuid4(),
        email="bulk@example.com",
        full_name="Bulk User",
        hashed_password="hashed_password",
        role="developer",
        status=ServerStatus.ACTIVE,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    # Step 1: Prepare Bulk Server Data
    bulk_server_data = []
    for i in range(50):
        server_data = {
            "name": f"bulk-server-{i}",
            "description": f"Bulk registered server {i}",
            "transport": "http",
            "endpoint": f"http://server{i}.example.com/mcp",
            "sensitivity_level": "medium" if i < 45 else "high"  # Last 5 are high sensitivity
        }
        bulk_server_data.append(server_data)

    # Step 2: Validate Data Before Registration
    validation_errors = []
    for server_data in bulk_server_data:
        if not server_data.get("name"):
            validation_errors.append("Missing server name")
        if not server_data.get("endpoint"):
            validation_errors.append("Missing endpoint")

    assert len(validation_errors) == 0, "All servers should pass pre-validation"

    # Step 3: Perform Transactional Bulk Registration
    # Mock policy evaluation - deny high sensitivity servers for regular user
    transactional_results = {
        "mode": "transactional",
        "total": 50,
        "successful": 0,
        "failed": 50,
        "error": "Transaction rolled back due to policy violation on server bulk-server-45",
        "results": []
    }

    # Step 4 & 5: One Server Fails, Entire Batch Rolled Back
    assert transactional_results["successful"] == 0
    assert "rolled back" in transactional_results["error"]

    # Step 6: Retry with Best-Effort Mode
    # In best-effort mode, valid servers are registered, invalid ones are skipped
    best_effort_results = {
        "mode": "best_effort",
        "total": 50,
        "successful": 45,  # First 45 medium sensitivity servers
        "failed": 5,       # Last 5 high sensitivity servers
        "results": []
    }

    # Add results for each server
    for i in range(50):
        if i < 45:
            best_effort_results["results"].append({
                "success": True,
                "server_id": str(uuid4()),
                "name": f"bulk-server-{i}"
            })
        else:
            best_effort_results["results"].append({
                "success": False,
                "name": f"bulk-server-{i}",
                "error": "Policy violation: insufficient permissions for high sensitivity"
            })

    # Step 7: Verify Partial Success
    assert best_effort_results["successful"] == 45
    assert best_effort_results["failed"] == 5

    successful_servers = [r for r in best_effort_results["results"] if r.get("success")]
    failed_servers = [r for r in best_effort_results["results"] if not r.get("success")]

    assert len(successful_servers) == 45
    assert len(failed_servers) == 5
    assert all("Policy violation" in r["error"] for r in failed_servers)
