"""
Test data generators for realistic E2E testing.

Provides factories and generators for creating realistic test data
including users, servers, policies, and audit events.
"""

from datetime import UTC, datetime, timedelta
import random
from uuid import UUID, uuid4

from faker import Faker

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.models.policy import Policy, PolicyStatus
from sark.models.principal import Principal, Team

# Initialize Faker for realistic data
fake = Faker()


# ============================================================================
# User Generators
# ============================================================================


def generate_user(
    role: str = "developer",
    is_admin: bool = False,
    is_active: bool = True,
    team_id: UUID | None = None,
) -> Principal:
    """
    Generate a single user with realistic data.

    Args:
        role: User role (developer, analyst, admin)
        is_admin: Whether user has admin privileges
        is_active: Whether user account is active
        team_id: Optional team ID for user metadata

    Returns:
        User object with realistic data
    """
    first_name = fake.first_name()
    last_name = fake.last_name()
    email = f"{first_name.lower()}.{last_name.lower()}@{fake.domain_name()}"

    extra_metadata = {}
    if team_id:
        extra_metadata["team_id"] = str(team_id)

    return Principal(
        id=uuid4(),
        email=email,
        full_name=f"{first_name} {last_name}",
        hashed_password=fake.sha256(),
        role=role,
        is_active=is_active,
        is_admin=is_admin,
        extra_metadata=extra_metadata,
        created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 365)),
        updated_at=datetime.now(UTC),
    )


def generate_users(count: int, **kwargs) -> list[User]:
    """
    Generate multiple users.

    Args:
        count: Number of users to generate
        **kwargs: Arguments passed to generate_user()

    Returns:
        List of User objects
    """
    return [generate_user(**kwargs) for _ in range(count)]


def generate_admin_user() -> Principal:
    """Generate an admin user."""
    return generate_user(role="admin", is_admin=True)


def generate_team(member_count: int = 0) -> Team:
    """
    Generate a team with optional members.

    Args:
        member_count: Number of members to generate for team

    Returns:
        Team object
    """
    team_names = [
        "Engineering",
        "Data Science",
        "DevOps",
        "Security",
        "Product",
        "Design",
        "QA",
        "Research",
    ]

    return Team(
        id=uuid4(),
        name=random.choice(team_names) + f" {random.randint(1, 10)}",
        description=fake.catch_phrase(),
        extra_metadata={
            "department": random.choice(["Tech", "Business", "Operations"]),
            "member_count": member_count,
        },
        created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 730)),
        updated_at=datetime.now(UTC),
    )


# ============================================================================
# Server Generators
# ============================================================================


def generate_mcp_server(
    owner_id: UUID | None = None,
    team_id: UUID | None = None,
    sensitivity_level: SensitivityLevel = SensitivityLevel.MEDIUM,
    server_status: ServerStatus = ServerStatus.ACTIVE,
    transport: TransportType = TransportType.HTTP,
) -> MCPServer:
    """
    Generate a single MCP server with realistic data.

    Args:
        owner_id: User ID who owns the server
        team_id: Team ID the server belongs to
        sensitivity_level: Security sensitivity level
        server_status: Server status
        transport: Transport protocol

    Returns:
        MCPServer object
    """
    server_types = [
        "api-gateway",
        "data-processor",
        "ml-model",
        "analytics",
        "monitoring",
        "logging",
        "auth-service",
        "notification",
    ]

    server_type = random.choice(server_types)
    server_name = f"{server_type}-{fake.word()}-{random.randint(1, 999)}"

    if not owner_id:
        owner_id = uuid4()
    if not team_id:
        team_id = uuid4()

    # Generate endpoint based on transport type
    if transport == TransportType.HTTP:
        endpoint = f"http://{server_name}.{fake.domain_name()}/mcp"
    elif transport == TransportType.STDIO:
        endpoint = f"/usr/local/bin/{server_name}"
    else:  # SSE
        endpoint = f"http://{server_name}.{fake.domain_name()}/events"

    return MCPServer(
        id=uuid4(),
        name=server_name,
        description=fake.sentence(),
        transport=transport,
        endpoint=endpoint,
        sensitivity_level=sensitivity_level,
        owner_id=owner_id,
        team_id=team_id,
        status=server_status,
        health_check_url=(
            f"http://{server_name}.{fake.domain_name()}/health"
            if transport == TransportType.HTTP
            else None
        ),
        created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 180)),
        updated_at=datetime.now(UTC),
    )


def generate_servers(count: int, **kwargs) -> list[MCPServer]:
    """
    Generate multiple MCP servers.

    Args:
        count: Number of servers to generate
        **kwargs: Arguments passed to generate_mcp_server()

    Returns:
        List of MCPServer objects
    """
    return [generate_mcp_server(**kwargs) for _ in range(count)]


def generate_server_with_tools(
    tool_count: int = 5, prompt_count: int = 3, resource_count: int = 2, **kwargs
) -> MCPServer:
    """
    Generate MCP server with tools, prompts, and resources.

    Args:
        tool_count: Number of tools to generate
        prompt_count: Number of prompts to generate
        resource_count: Number of resources to generate
        **kwargs: Arguments passed to generate_mcp_server()

    Returns:
        MCPServer with tools, prompts, and resources
    """
    server = generate_mcp_server(**kwargs)

    # Add tools
    tools = []
    for i in range(tool_count):
        tools.append(
            {
                "name": f"{fake.word()}_tool_{i}",
                "description": fake.sentence(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            }
        )

    # Add prompts
    prompts = []
    for i in range(prompt_count):
        prompts.append(
            {
                "name": f"{fake.word()}_prompt_{i}",
                "description": fake.sentence(),
                "template": fake.paragraph(),
            }
        )

    # Add resources
    resources = []
    for i in range(resource_count):
        resources.append(
            {
                "name": f"{fake.word()}_resource_{i}",
                "description": fake.sentence(),
                "uri": fake.url(),
            }
        )

    # Update server metadata
    server.extra_metadata = {"tools": tools, "prompts": prompts, "resources": resources}

    return server


def generate_high_sensitivity_server(**kwargs) -> MCPServer:
    """Generate a high-sensitivity server."""
    return generate_mcp_server(
        sensitivity_level=SensitivityLevel.HIGH, server_status=ServerStatus.ACTIVE, **kwargs
    )


# ============================================================================
# Policy Generators
# ============================================================================


def generate_policy(
    policy_type: str = "authorization",
    status: PolicyStatus = PolicyStatus.DRAFT,
) -> Policy:
    """
    Generate a policy with realistic data.

    Args:
        policy_type: Type of policy (authorization, validation, etc.)
        status: Policy status

    Returns:
        Policy object
    """
    policy_names = [
        "server-registration-policy",
        "tool-invocation-policy",
        "data-access-policy",
        "admin-action-policy",
        "team-collaboration-policy",
    ]

    return Policy(
        id=uuid4(),
        name=random.choice(policy_names) + f"-{random.randint(1, 100)}",
        description=fake.paragraph(),
        policy_type=policy_type,
        status=status,
        created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 365)),
        updated_at=datetime.now(UTC),
    )


def generate_authorization_policy() -> Policy:
    """Generate an authorization policy with Rego code."""
    policy = generate_policy(policy_type="authorization")

    # Sample Rego code
    rego_code = """
    package sark.authorization

    default allow = false

    # Allow developers to register low/medium sensitivity servers
    allow {
        input.user.role == "developer"
        input.action == "register"
        input.resource.sensitivity in ["low", "medium"]
    }

    # Allow admins all actions
    allow {
        input.user.role == "admin"
    }
    """

    # Create policy version
    policy.extra_metadata = {"rego_code": rego_code, "version": 1}

    return policy


def generate_validation_policy() -> Policy:
    """Generate a validation policy."""
    policy = generate_policy(policy_type="validation")

    validation_rules = {
        "server_name": {"pattern": "^[a-z0-9-]+$", "min_length": 3, "max_length": 63},
        "endpoint": {"type": "url", "required": True},
    }

    policy.extra_metadata = {"validation_rules": validation_rules}

    return policy


# ============================================================================
# Audit Event Generators
# ============================================================================


def generate_audit_event(
    user_id: UUID | None = None,
    resource_id: UUID | None = None,
    event_type: AuditEventType = AuditEventType.SERVER_REGISTERED,
    severity: SeverityLevel = SeverityLevel.LOW,
) -> AuditEvent:
    """
    Generate an audit event.

    Args:
        user_id: User who triggered the event
        resource_id: Resource the event relates to
        event_type: Type of audit event
        severity: Event severity level

    Returns:
        AuditEvent object
    """
    if not user_id:
        user_id = uuid4()
    if not resource_id:
        resource_id = uuid4()

    actions = {
        AuditEventType.SERVER_REGISTERED: "register",
        AuditEventType.SERVER_UPDATED: "update",
        AuditEventType.SERVER_DECOMMISSIONED: "decommission",
        AuditEventType.USER_LOGIN: "login",
        AuditEventType.USER_LOGOUT: "logout",
        AuditEventType.TOOL_INVOKED: "invoke",
        AuditEventType.AUTHORIZATION_ALLOWED: "allow",
        AuditEventType.AUTHORIZATION_DENIED: "deny",
    }

    return AuditEvent(
        id=uuid4(),
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resource_id=resource_id,
        resource_type="server",
        action=actions.get(event_type, "unknown"),
        details={"correlation_id": str(uuid4()), "message": fake.sentence()},
        ip_address=fake.ipv4(),
        user_agent=fake.user_agent(),
        timestamp=datetime.now(UTC) - timedelta(minutes=random.randint(1, 1440)),
    )


def generate_audit_trail(user_id: uuid4, event_count: int = 10) -> list[AuditEvent]:
    """
    Generate a series of related audit events (audit trail).

    Args:
        user_id: User ID for all events
        event_count: Number of events to generate

    Returns:
        List of AuditEvent objects in chronological order
    """
    correlation_id = str(uuid4())
    events = []

    event_types = [
        AuditEventType.USER_LOGIN,
        AuditEventType.SERVER_REGISTERED,
        AuditEventType.SERVER_UPDATED,
        AuditEventType.TOOL_INVOKED,
        AuditEventType.AUTHORIZATION_ALLOWED,
        AuditEventType.USER_LOGOUT,
    ]

    for i, event_type in enumerate(random.sample(event_types, min(event_count, len(event_types)))):
        event = generate_audit_event(
            user_id=user_id,
            event_type=event_type,
            severity=(
                SeverityLevel.LOW if i < event_count - 1 else random.choice(list(SeverityLevel))
            ),
        )
        event.details["correlation_id"] = correlation_id
        event.timestamp = datetime.now(UTC) - timedelta(minutes=event_count - i)
        events.append(event)

    return sorted(events, key=lambda e: e.timestamp)


# ============================================================================
# Bulk Data Generators
# ============================================================================


def generate_realistic_dataset(
    user_count: int = 100,
    team_count: int = 10,
    server_count: int = 500,
    policy_count: int = 20,
    audit_event_count: int = 1000,
) -> dict:
    """
    Generate a complete realistic dataset for testing.

    Args:
        user_count: Number of users to generate
        team_count: Number of teams to generate
        server_count: Number of servers to generate
        policy_count: Number of policies to generate
        audit_event_count: Number of audit events to generate

    Returns:
        Dictionary containing all generated data
    """
    # Generate teams
    teams = [generate_team() for _ in range(team_count)]

    # Generate users across teams
    users = []
    for _ in range(user_count):
        team_id = random.choice(teams).id if teams else None
        role = random.choices(
            ["developer", "analyst", "admin"], weights=[70, 25, 5], k=1  # Distribution
        )[0]
        is_admin = role == "admin"

        user = generate_user(role=role, is_admin=is_admin, team_id=team_id)
        users.append(user)

    # Generate servers owned by users
    servers = []
    for _ in range(server_count):
        owner = random.choice(users)
        team_id = (
            UUID(owner.extra_metadata.get("team_id"))
            if owner.extra_metadata.get("team_id")
            else uuid4()
        )

        sensitivity = random.choices(
            list(SensitivityLevel), weights=[30, 40, 20, 10], k=1  # low, medium, high, critical
        )[0]

        transport = random.choices(
            list(TransportType), weights=[70, 20, 10], k=1  # http, stdio, sse
        )[0]

        server = generate_mcp_server(
            owner_id=owner.id, team_id=team_id, sensitivity_level=sensitivity, transport=transport
        )
        servers.append(server)

    # Generate policies
    policies = []
    for _ in range(policy_count):
        policy = generate_policy()
        policies.append(policy)

    # Generate audit events
    audit_events = []
    for _ in range(audit_event_count):
        user = random.choice(users)
        event_type = random.choice(list(AuditEventType))
        severity = random.choices(
            list(SeverityLevel),
            weights=[40, 30, 20, 7, 3],  # info, low, medium, high, critical
            k=1,
        )[0]

        event = generate_audit_event(user_id=user.id, event_type=event_type, severity=severity)
        audit_events.append(event)

    return {
        "users": users,
        "teams": teams,
        "servers": servers,
        "policies": policies,
        "audit_events": audit_events,
        "summary": {
            "total_users": len(users),
            "total_teams": len(teams),
            "total_servers": len(servers),
            "total_policies": len(policies),
            "total_audit_events": len(audit_events),
            "admin_users": len([u for u in users if u.is_admin]),
            "active_servers": len(
                [s for s in servers if s.status in [ServerStatus.ACTIVE, ServerStatus.REGISTERED]]
            ),
            "high_severity_events": len(
                [
                    e
                    for e in audit_events
                    if e.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
                ]
            ),
        },
    }


# ============================================================================
# Test Functions
# ============================================================================


def test_generate_user():
    """Test user generation."""
    user = generate_user()
    assert user.id is not None
    assert user.email is not None
    assert "@" in user.email
    assert user.full_name is not None


def test_generate_users():
    """Test multiple user generation."""
    users = generate_users(10)
    assert len(users) == 10
    assert all(u.id is not None for u in users)

    # All emails should be unique
    emails = [u.email for u in users]
    assert len(emails) == len(set(emails))


def test_generate_mcp_server():
    """Test server generation."""
    server = generate_mcp_server()
    assert server.id is not None
    assert server.name is not None
    assert server.transport in list(TransportType)
    assert server.sensitivity_level in list(SensitivityLevel)


def test_generate_servers():
    """Test multiple server generation."""
    servers = generate_servers(20)
    assert len(servers) == 20
    assert all(s.id is not None for s in servers)


def test_generate_server_with_tools():
    """Test server with tools generation."""
    server = generate_server_with_tools(tool_count=5, prompt_count=3)
    assert "tools" in server.extra_metadata
    assert len(server.extra_metadata["tools"]) == 5
    assert len(server.extra_metadata["prompts"]) == 3


def test_generate_policy():
    """Test policy generation."""
    policy = generate_policy()
    assert policy.id is not None
    assert policy.name is not None
    assert policy.policy_type == "authorization"


def test_generate_audit_event():
    """Test audit event generation."""
    event = generate_audit_event()
    assert event.id is not None
    assert event.user_id is not None
    assert event.event_type in list(AuditEventType)
    assert event.severity in list(SeverityLevel)


def test_generate_audit_trail():
    """Test audit trail generation."""
    user_id = uuid4()
    trail = generate_audit_trail(user_id, event_count=5)
    assert len(trail) <= 5
    assert all(e.user_id == user_id for e in trail)

    # All events should have same correlation ID
    correlation_ids = [e.details.get("correlation_id") for e in trail]
    assert len(set(correlation_ids)) == 1

    # Events should be chronologically ordered
    timestamps = [e.timestamp for e in trail]
    assert timestamps == sorted(timestamps)


def test_generate_realistic_dataset():
    """Test complete dataset generation."""
    dataset = generate_realistic_dataset(
        user_count=50, team_count=5, server_count=100, policy_count=10, audit_event_count=200
    )

    assert len(dataset["users"]) == 50
    assert len(dataset["teams"]) == 5
    assert len(dataset["servers"]) == 100
    assert len(dataset["policies"]) == 10
    assert len(dataset["audit_events"]) == 200

    # Verify summary
    summary = dataset["summary"]
    assert summary["total_users"] == 50
    assert summary["admin_users"] > 0
    assert summary["active_servers"] > 0
