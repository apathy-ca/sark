"""Tests for database models."""

from datetime import UTC, datetime
from uuid import uuid4

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.models.policy import Effect, Policy, PolicyRule, PolicyStatus, PolicyType, PolicyVersion
from sark.models.user import User


class TestMCPServerModel:
    """Tests for MCP Server model."""

    def test_server_creation(self) -> None:
        """Test creating MCP server instance."""
        server = MCPServer(
            name="test-server",
            description="Test MCP server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8080",
            mcp_version="2025-06-18",
            capabilities=["tools", "resources"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.REGISTERED,
        )

        assert server.name == "test-server"
        assert server.transport == TransportType.HTTP
        assert server.status == ServerStatus.REGISTERED
        assert server.sensitivity_level == SensitivityLevel.MEDIUM

    def test_server_repr(self) -> None:
        """Test server string representation."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.HTTP,
            mcp_version="2025-06-18",
            capabilities=[],
        )

        repr_str = repr(server)
        assert "MCPServer" in repr_str
        assert "test-server" in repr_str


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self) -> None:
        """Test creating user instance."""
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            is_active=True,
            is_admin=False,
            role="developer",
        )

        assert user.email == "test@example.com"
        assert user.role == "developer"
        assert user.is_active is True
        assert user.is_admin is False


class TestAuditEventModel:
    """Tests for Audit Event model."""

    def test_audit_event_creation(self) -> None:
        """Test creating audit event."""
        event = AuditEvent(
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.LOW,
            user_email="test@example.com",
            tool_name="test_tool",
            decision="allow",
            details={"test": "data"},
        )

        assert event.event_type == AuditEventType.TOOL_INVOKED
        assert event.severity == SeverityLevel.LOW
        assert event.decision == "allow"
        assert event.details["test"] == "data"


class TestPolicyModel:
    """Tests for Policy model."""

    def test_policy_creation(self) -> None:
        """Test creating policy instance."""
        policy = Policy(
            name="test-policy",
            description="Test policy description",
            policy_type=PolicyType.AUTHORIZATION,
            status=PolicyStatus.DRAFT,
        )

        assert policy.name == "test-policy"
        assert policy.description == "Test policy description"
        assert policy.policy_type == PolicyType.AUTHORIZATION
        assert policy.status == PolicyStatus.DRAFT

    def test_policy_repr(self) -> None:
        """Test policy string representation."""
        policy = Policy(
            name="test-policy",
            status=PolicyStatus.ACTIVE,
        )

        repr_str = repr(policy)
        assert "Policy" in repr_str
        assert "test-policy" in repr_str
        assert "ACTIVE" in repr_str

    def test_policy_with_explicit_defaults(self) -> None:
        """Test policy with explicitly set default values."""
        policy = Policy(
            name="minimal-policy",
            policy_type=PolicyType.AUTHORIZATION,
            status=PolicyStatus.DRAFT,
        )

        assert policy.name == "minimal-policy"
        assert policy.policy_type == PolicyType.AUTHORIZATION
        assert policy.status == PolicyStatus.DRAFT


class TestPolicyVersionModel:
    """Tests for PolicyVersion model."""

    def test_policy_version_creation(self) -> None:
        """Test creating policy version instance."""
        policy_id = uuid4()
        version = PolicyVersion(
            policy_id=policy_id,
            version=1,
            content="package example.policy\n\ndefault allow = false",
            is_active=True,
            tested=True,
            notes="Initial version",
        )

        assert version.policy_id == policy_id
        assert version.version == 1
        assert "package example.policy" in version.content
        assert version.is_active is True
        assert version.tested is True
        assert version.notes == "Initial version"

    def test_policy_version_repr(self) -> None:
        """Test policy version string representation."""
        policy_id = uuid4()
        version = PolicyVersion(
            policy_id=policy_id,
            version=2,
            content="package test",
        )

        repr_str = repr(version)
        assert "PolicyVersion" in repr_str
        assert str(policy_id) in repr_str
        assert "version=2" in repr_str

    def test_policy_version_with_explicit_defaults(self) -> None:
        """Test policy version with explicitly set default values."""
        version = PolicyVersion(
            policy_id=uuid4(),
            version=1,
            content="test content",
            is_active=False,
            tested=False,
        )

        assert version.is_active is False
        assert version.tested is False
        assert version.content == "test content"


class TestPolicyRuleModel:
    """Tests for PolicyRule model."""

    def test_policy_rule_creation(self) -> None:
        """Test creating policy rule instance."""
        version_id = uuid4()
        rule = PolicyRule(
            policy_version_id=version_id,
            name="allow-admin-access",
            priority=100,
            effect=Effect.ALLOW,
            principal_matchers=[{"type": "role", "value": "admin"}],
            resource_matchers=[{"type": "resource", "value": "*"}],
            action_matchers=[{"type": "action", "value": "read"}],
            conditions=[{"type": "time", "value": "business_hours"}],
            constraints=[{"type": "rate_limit", "value": 100}],
        )

        assert rule.policy_version_id == version_id
        assert rule.name == "allow-admin-access"
        assert rule.priority == 100
        assert rule.effect == Effect.ALLOW
        assert len(rule.principal_matchers) == 1
        assert rule.principal_matchers[0]["type"] == "role"
        assert len(rule.resource_matchers) == 1
        assert len(rule.action_matchers) == 1
        assert len(rule.conditions) == 1
        assert len(rule.constraints) == 1

    def test_policy_rule_repr(self) -> None:
        """Test policy rule string representation."""
        rule = PolicyRule(
            policy_version_id=uuid4(),
            name="test-rule",
            priority=50,
            effect=Effect.DENY,
        )

        repr_str = repr(rule)
        assert "PolicyRule" in repr_str
        assert "test-rule" in repr_str
        assert "DENY" in repr_str
        assert "priority=50" in repr_str

    def test_policy_rule_with_explicit_defaults(self) -> None:
        """Test policy rule with explicitly set default values."""
        rule = PolicyRule(
            policy_version_id=uuid4(),
            name="minimal-rule",
            effect=Effect.ALLOW,
            priority=0,
            principal_matchers=[],
            resource_matchers=[],
            action_matchers=[],
            conditions=[],
            constraints=[],
        )

        assert rule.name == "minimal-rule"
        assert rule.priority == 0
        assert rule.principal_matchers == []
        assert rule.resource_matchers == []
        assert rule.action_matchers == []
        assert rule.conditions == []
        assert rule.constraints == []

    def test_policy_rule_effects(self) -> None:
        """Test all policy rule effect types."""
        version_id = uuid4()

        allow_rule = PolicyRule(
            policy_version_id=version_id,
            name="allow-rule",
            effect=Effect.ALLOW,
        )
        assert allow_rule.effect == Effect.ALLOW

        deny_rule = PolicyRule(
            policy_version_id=version_id,
            name="deny-rule",
            effect=Effect.DENY,
        )
        assert deny_rule.effect == Effect.DENY

        constrain_rule = PolicyRule(
            policy_version_id=version_id,
            name="constrain-rule",
            effect=Effect.CONSTRAIN,
        )
        assert constrain_rule.effect == Effect.CONSTRAIN
