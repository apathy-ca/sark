"""Unit tests for Audit Service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit import AuditService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def audit_service(mock_db):
    """Audit service with mocked database."""
    return AuditService(mock_db)


@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        "user_id": uuid4(),
        "user_email": "test@example.com",
    }


@pytest.fixture
def sample_server():
    """Sample server data."""
    return {
        "server_id": uuid4(),
        "server_name": "test-server",
    }


class TestAuditServiceLogEvent:
    """Test log_event method."""

    @pytest.mark.asyncio
    async def test_log_event_minimal(self, audit_service, mock_db):
        """Test logging event with minimal parameters."""
        event = await audit_service.log_event(
            event_type=AuditEventType.USER_LOGIN,
            severity=SeverityLevel.LOW,
        )

        assert event.event_type == AuditEventType.USER_LOGIN
        assert event.severity == SeverityLevel.LOW
        assert event.details == {}
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_event_with_user_info(self, audit_service, mock_db, sample_user):
        """Test logging event with user information."""
        event = await audit_service.log_event(
            event_type=AuditEventType.USER_LOGIN,
            severity=SeverityLevel.LOW,
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
        )

        assert event.user_id == sample_user["user_id"]
        assert event.user_email == sample_user["user_email"]

    @pytest.mark.asyncio
    async def test_log_event_with_server_info(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test logging event with server information."""
        event = await audit_service.log_event(
            event_type=AuditEventType.SERVER_REGISTERED,
            severity=SeverityLevel.MEDIUM,
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            server_id=sample_server["server_id"],
        )

        assert event.server_id == sample_server["server_id"]
        assert event.event_type == AuditEventType.SERVER_REGISTERED

    @pytest.mark.asyncio
    async def test_log_event_with_tool_info(self, audit_service, mock_db, sample_user):
        """Test logging event with tool information."""
        event = await audit_service.log_event(
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.LOW,
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
        )

        assert event.tool_name == "test-tool"
        assert event.event_type == AuditEventType.TOOL_INVOKED

    @pytest.mark.asyncio
    async def test_log_event_with_authorization_decision(
        self, audit_service, mock_db, sample_user
    ):
        """Test logging event with authorization decision."""
        policy_id = uuid4()
        event = await audit_service.log_event(
            event_type=AuditEventType.AUTHORIZATION_ALLOWED,
            severity=SeverityLevel.LOW,
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
            decision="allow",
            policy_id=policy_id,
        )

        assert event.decision == "allow"
        assert event.policy_id == policy_id

    @pytest.mark.asyncio
    async def test_log_event_with_network_context(self, audit_service, mock_db, sample_user):
        """Test logging event with network context."""
        event = await audit_service.log_event(
            event_type=AuditEventType.USER_LOGIN,
            severity=SeverityLevel.LOW,
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            request_id="req-12345",
        )

        assert event.ip_address == "192.168.1.100"
        assert event.user_agent == "Mozilla/5.0"
        assert event.request_id == "req-12345"

    @pytest.mark.asyncio
    async def test_log_event_with_details(self, audit_service, mock_db):
        """Test logging event with additional details."""
        details = {
            "action": "create",
            "resource": "policy",
            "metadata": {"version": "1.0"},
        }

        event = await audit_service.log_event(
            event_type=AuditEventType.POLICY_CREATED,
            severity=SeverityLevel.MEDIUM,
            details=details,
        )

        assert event.details == details
        assert event.details["action"] == "create"

    @pytest.mark.asyncio
    async def test_log_event_none_details_defaults_to_empty_dict(
        self, audit_service, mock_db
    ):
        """Test that None details defaults to empty dict."""
        event = await audit_service.log_event(
            event_type=AuditEventType.USER_LOGOUT,
            severity=SeverityLevel.LOW,
            details=None,
        )

        assert event.details == {}

    @pytest.mark.asyncio
    async def test_log_event_all_event_types(self, audit_service, mock_db):
        """Test logging events for all event types."""
        event_types = [
            AuditEventType.SERVER_REGISTERED,
            AuditEventType.SERVER_UPDATED,
            AuditEventType.SERVER_DECOMMISSIONED,
            AuditEventType.TOOL_INVOKED,
            AuditEventType.AUTHORIZATION_ALLOWED,
            AuditEventType.AUTHORIZATION_DENIED,
            AuditEventType.POLICY_CREATED,
            AuditEventType.POLICY_UPDATED,
            AuditEventType.POLICY_ACTIVATED,
            AuditEventType.USER_LOGIN,
            AuditEventType.USER_LOGOUT,
            AuditEventType.SECURITY_VIOLATION,
        ]

        for event_type in event_types:
            event = await audit_service.log_event(
                event_type=event_type,
                severity=SeverityLevel.LOW,
            )
            assert event.event_type == event_type

    @pytest.mark.asyncio
    async def test_log_event_all_severity_levels(self, audit_service, mock_db):
        """Test logging events with all severity levels."""
        severity_levels = [
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]

        for severity in severity_levels:
            event = await audit_service.log_event(
                event_type=AuditEventType.USER_LOGIN,
                severity=severity,
            )
            assert event.severity == severity


class TestAuditServiceSIEMForwarding:
    """Test SIEM forwarding functionality."""

    @pytest.mark.asyncio
    async def test_high_severity_triggers_siem_forward(self, audit_service, mock_db):
        """Test that high severity events trigger SIEM forwarding."""
        with patch.object(audit_service, "_forward_to_siem", new=AsyncMock()) as mock_siem:
            event = await audit_service.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                severity=SeverityLevel.HIGH,
            )

            mock_siem.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_critical_severity_triggers_siem_forward(self, audit_service, mock_db):
        """Test that critical severity events trigger SIEM forwarding."""
        with patch.object(audit_service, "_forward_to_siem", new=AsyncMock()) as mock_siem:
            event = await audit_service.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                severity=SeverityLevel.CRITICAL,
            )

            mock_siem.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_low_severity_does_not_trigger_siem(self, audit_service, mock_db):
        """Test that low severity events do not trigger SIEM forwarding."""
        with patch.object(audit_service, "_forward_to_siem", new=AsyncMock()) as mock_siem:
            await audit_service.log_event(
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )

            mock_siem.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_medium_severity_does_not_trigger_siem(self, audit_service, mock_db):
        """Test that medium severity events do not trigger SIEM forwarding."""
        with patch.object(audit_service, "_forward_to_siem", new=AsyncMock()) as mock_siem:
            await audit_service.log_event(
                event_type=AuditEventType.SERVER_REGISTERED,
                severity=SeverityLevel.MEDIUM,
            )

            mock_siem.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_forward_to_siem_updates_timestamp(self, audit_service, mock_db):
        """Test that _forward_to_siem updates siem_forwarded timestamp."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            details={},
        )

        assert event.siem_forwarded is None

        await audit_service._forward_to_siem(event)

        assert event.siem_forwarded is not None
        assert isinstance(event.siem_forwarded, datetime)
        mock_db.commit.assert_awaited_once()


class TestAuditServiceLogAuthorizationDecision:
    """Test log_authorization_decision method."""

    @pytest.mark.asyncio
    async def test_log_authorization_allow(self, audit_service, mock_db, sample_user):
        """Test logging authorization allow decision."""
        event = await audit_service.log_authorization_decision(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
            decision="allow",
        )

        assert event.event_type == AuditEventType.AUTHORIZATION_ALLOWED
        assert event.severity == SeverityLevel.LOW
        assert event.decision == "allow"

    @pytest.mark.asyncio
    async def test_log_authorization_deny(self, audit_service, mock_db, sample_user):
        """Test logging authorization deny decision."""
        event = await audit_service.log_authorization_decision(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
            decision="deny",
        )

        assert event.event_type == AuditEventType.AUTHORIZATION_DENIED
        assert event.severity == SeverityLevel.MEDIUM
        assert event.decision == "deny"

    @pytest.mark.asyncio
    async def test_log_authorization_with_policy_id(
        self, audit_service, mock_db, sample_user
    ):
        """Test logging authorization decision with policy ID."""
        policy_id = uuid4()

        event = await audit_service.log_authorization_decision(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
            decision="allow",
            policy_id=policy_id,
        )

        assert event.policy_id == policy_id

    @pytest.mark.asyncio
    async def test_log_authorization_with_server_id(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test logging authorization decision with server ID."""
        event = await audit_service.log_authorization_decision(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
            decision="allow",
            server_id=sample_server["server_id"],
        )

        assert event.server_id == sample_server["server_id"]

    @pytest.mark.asyncio
    async def test_log_authorization_with_network_context(
        self, audit_service, mock_db, sample_user
    ):
        """Test logging authorization decision with network context."""
        event = await audit_service.log_authorization_decision(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
            decision="allow",
            ip_address="10.0.0.1",
            request_id="req-auth-123",
        )

        assert event.ip_address == "10.0.0.1"
        assert event.request_id == "req-auth-123"

    @pytest.mark.asyncio
    async def test_log_authorization_with_details(
        self, audit_service, mock_db, sample_user
    ):
        """Test logging authorization decision with additional details."""
        details = {
            "reason": "user has required permissions",
            "evaluated_policies": ["policy-1", "policy-2"],
        }

        event = await audit_service.log_authorization_decision(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            tool_name="test-tool",
            decision="allow",
            details=details,
        )

        assert event.details == details


class TestAuditServiceLogToolInvocation:
    """Test log_tool_invocation method."""

    @pytest.mark.asyncio
    async def test_log_tool_invocation_minimal(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test logging tool invocation with minimal parameters."""
        event = await audit_service.log_tool_invocation(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            server_id=sample_server["server_id"],
            tool_name="query-database",
        )

        assert event.event_type == AuditEventType.TOOL_INVOKED
        assert event.severity == SeverityLevel.LOW
        assert event.tool_name == "query-database"
        assert event.server_id == sample_server["server_id"]

    @pytest.mark.asyncio
    async def test_log_tool_invocation_with_parameters(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test logging tool invocation with parameters."""
        parameters = {
            "query": "SELECT * FROM users",
            "limit": 100,
        }

        event = await audit_service.log_tool_invocation(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            server_id=sample_server["server_id"],
            tool_name="query-database",
            parameters=parameters,
        )

        assert event.details == {"parameters": parameters}
        assert event.details["parameters"]["query"] == "SELECT * FROM users"

    @pytest.mark.asyncio
    async def test_log_tool_invocation_with_network_context(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test logging tool invocation with network context."""
        event = await audit_service.log_tool_invocation(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            server_id=sample_server["server_id"],
            tool_name="execute-command",
            ip_address="192.168.1.50",
            request_id="req-tool-456",
        )

        assert event.ip_address == "192.168.1.50"
        assert event.request_id == "req-tool-456"

    @pytest.mark.asyncio
    async def test_log_tool_invocation_none_parameters(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test that None parameters defaults to empty dict."""
        event = await audit_service.log_tool_invocation(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            server_id=sample_server["server_id"],
            tool_name="simple-tool",
            parameters=None,
        )

        assert event.details == {}


class TestAuditServiceLogServerRegistration:
    """Test log_server_registration method."""

    @pytest.mark.asyncio
    async def test_log_server_registration_minimal(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test logging server registration with minimal parameters."""
        event = await audit_service.log_server_registration(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            server_id=sample_server["server_id"],
            server_name=sample_server["server_name"],
        )

        assert event.event_type == AuditEventType.SERVER_REGISTERED
        assert event.severity == SeverityLevel.MEDIUM
        assert event.server_id == sample_server["server_id"]
        assert event.details["server_name"] == sample_server["server_name"]

    @pytest.mark.asyncio
    async def test_log_server_registration_with_details(
        self, audit_service, mock_db, sample_user, sample_server
    ):
        """Test logging server registration with additional details."""
        details = {
            "transport": "http",
            "capabilities": ["tools", "prompts"],
            "sensitivity_level": "high",
        }

        event = await audit_service.log_server_registration(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            server_id=sample_server["server_id"],
            server_name=sample_server["server_name"],
            details=details,
        )

        assert "server_name" in event.details
        assert "transport" in event.details
        assert event.details["transport"] == "http"


class TestAuditServiceLogSecurityViolation:
    """Test log_security_violation method."""

    @pytest.mark.asyncio
    async def test_log_security_violation_with_user(
        self, audit_service, mock_db, sample_user
    ):
        """Test logging security violation with user information."""
        event = await audit_service.log_security_violation(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            violation_type="brute_force_attempt",
        )

        assert event.event_type == AuditEventType.SECURITY_VIOLATION
        assert event.severity == SeverityLevel.CRITICAL
        assert event.user_id == sample_user["user_id"]
        assert event.details["violation_type"] == "brute_force_attempt"

    @pytest.mark.asyncio
    async def test_log_security_violation_anonymous(self, audit_service, mock_db):
        """Test logging security violation without user information."""
        event = await audit_service.log_security_violation(
            user_id=None,
            user_email=None,
            violation_type="unauthorized_access_attempt",
            ip_address="203.0.113.42",
        )

        assert event.user_id is None
        assert event.user_email is None
        assert event.ip_address == "203.0.113.42"
        assert event.details["violation_type"] == "unauthorized_access_attempt"

    @pytest.mark.asyncio
    async def test_log_security_violation_with_details(
        self, audit_service, mock_db, sample_user
    ):
        """Test logging security violation with additional details."""
        details = {
            "attempted_resource": "/admin/users",
            "failure_count": 5,
            "blocked": True,
        }

        event = await audit_service.log_security_violation(
            user_id=sample_user["user_id"],
            user_email=sample_user["user_email"],
            violation_type="privilege_escalation",
            details=details,
        )

        assert "violation_type" in event.details
        assert "attempted_resource" in event.details
        assert event.details["failure_count"] == 5

    @pytest.mark.asyncio
    async def test_log_security_violation_triggers_siem(self, audit_service, mock_db):
        """Test that security violations trigger SIEM forwarding."""
        with patch.object(audit_service, "_forward_to_siem", new=AsyncMock()) as mock_siem:
            event = await audit_service.log_security_violation(
                user_id=None,
                user_email=None,
                violation_type="sql_injection_attempt",
            )

            # Critical severity should trigger SIEM
            mock_siem.assert_awaited_once_with(event)


class TestAuditServiceErrorScenarios:
    """Test error handling and failure scenarios."""

    @pytest.mark.asyncio
    async def test_log_event_database_commit_failure(self, audit_service, mock_db):
        """Test handling of database commit failure."""
        mock_db.commit.side_effect = Exception("Database connection lost")

        with pytest.raises(Exception, match="Database connection lost"):
            await audit_service.log_event(
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )

    @pytest.mark.asyncio
    async def test_log_event_database_refresh_failure(self, audit_service, mock_db):
        """Test handling of database refresh failure."""
        mock_db.refresh.side_effect = Exception("Refresh failed")

        with pytest.raises(Exception, match="Refresh failed"):
            await audit_service.log_event(
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )

    @pytest.mark.asyncio
    async def test_siem_forward_failure_does_not_block_logging(
        self, audit_service, mock_db
    ):
        """Test that SIEM forwarding failure doesn't prevent event logging."""

        async def failing_siem_forward(event):
            raise Exception("SIEM unavailable")

        with patch.object(
            audit_service, "_forward_to_siem", new=failing_siem_forward
        ):
            # Should raise because we're not catching the exception
            with pytest.raises(Exception, match="SIEM unavailable"):
                await audit_service.log_event(
                    event_type=AuditEventType.SECURITY_VIOLATION,
                    severity=SeverityLevel.HIGH,
                )

    @pytest.mark.asyncio
    async def test_forward_to_siem_commit_failure(self, audit_service, mock_db):
        """Test handling of commit failure in SIEM forwarding."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            details={},
        )

        # Make commit fail for _forward_to_siem
        mock_db.commit.side_effect = Exception("Commit failed")

        with pytest.raises(Exception, match="Commit failed"):
            await audit_service._forward_to_siem(event)


class TestAuditServiceTimestamps:
    """Test timestamp handling."""

    @pytest.mark.asyncio
    async def test_log_event_sets_timestamp(self, audit_service, mock_db):
        """Test that log_event sets current timestamp."""
        before = datetime.now(UTC)
        event = await audit_service.log_event(
            event_type=AuditEventType.USER_LOGIN,
            severity=SeverityLevel.LOW,
        )
        after = datetime.now(UTC)

        assert event.timestamp is not None
        assert before <= event.timestamp <= after

    @pytest.mark.asyncio
    async def test_siem_forward_sets_timestamp(self, audit_service, mock_db):
        """Test that SIEM forwarding sets siem_forwarded timestamp."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.HIGH,
            details={},
        )

        before = datetime.now(UTC)
        await audit_service._forward_to_siem(event)
        after = datetime.now(UTC)

        assert event.siem_forwarded is not None
        assert before <= event.siem_forwarded <= after
