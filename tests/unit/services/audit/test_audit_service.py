"""Unit tests for Audit Service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.audit_service import AuditService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def audit_service(mock_db_session):
    """Create an audit service instance."""
    return AuditService(db=mock_db_session)


@pytest.fixture
def sample_user_id():
    """Sample user ID for tests."""
    return uuid4()


@pytest.fixture
def sample_server_id():
    """Sample server ID for tests."""
    return uuid4()


@pytest.fixture
def sample_policy_id():
    """Sample policy ID for tests."""
    return uuid4()


class TestAuditServiceBasic:
    """Test basic audit service functionality."""

    @pytest.mark.asyncio
    async def test_log_event_creates_audit_event(
        self, audit_service, mock_db_session, sample_user_id
    ):
        """Test that log_event creates an audit event."""
        # Arrange
        event_type = AuditEventType.TOOL_INVOKED
        severity = SeverityLevel.LOW
        user_email = "test@example.com"
        tool_name = "execute_query"

        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_event(
                event_type=event_type,
                severity=severity,
                user_id=sample_user_id,
                user_email=user_email,
                tool_name=tool_name,
            )

        # Assert
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called

        # Verify the event passed to add
        added_event = mock_db_session.add.call_args[0][0]
        assert isinstance(added_event, AuditEvent)
        assert added_event.event_type == event_type
        assert added_event.severity == severity
        assert added_event.user_id == sample_user_id
        assert added_event.user_email == user_email
        assert added_event.tool_name == tool_name

    @pytest.mark.asyncio
    async def test_log_event_with_optional_fields(
        self,
        audit_service,
        mock_db_session,
        sample_user_id,
        sample_server_id,
        sample_policy_id,
    ):
        """Test log_event with all optional fields populated."""
        # Arrange
        event_data = {
            "event_type": AuditEventType.AUTHORIZATION_ALLOWED,
            "severity": SeverityLevel.MEDIUM,
            "user_id": sample_user_id,
            "user_email": "user@example.com",
            "server_id": sample_server_id,
            "tool_name": "read_file",
            "decision": "allow",
            "policy_id": sample_policy_id,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
            "request_id": "req_123456",
            "details": {"reason": "Policy match", "policy_name": "dev_access"},
        }

        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_event(**event_data)

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.user_id == sample_user_id
        assert added_event.server_id == sample_server_id
        assert added_event.policy_id == sample_policy_id
        assert added_event.ip_address == "192.168.1.100"
        assert added_event.user_agent == "Mozilla/5.0"
        assert added_event.request_id == "req_123456"
        assert added_event.details == event_data["details"]

    @pytest.mark.asyncio
    async def test_log_event_defaults_empty_details(self, audit_service, mock_db_session):
        """Test that log_event defaults to empty dict for details."""
        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_event(event_type=AuditEventType.USER_LOGIN)

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.details == {}


class TestAuthorizationDecisionLogging:
    """Test authorization decision logging."""

    @pytest.mark.asyncio
    async def test_log_authorization_allow(
        self,
        audit_service,
        mock_db_session,
        sample_user_id,
        sample_server_id,
        sample_policy_id,
    ):
        """Test logging an authorization allow decision."""
        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_authorization_decision(
                user_id=sample_user_id,
                user_email="user@example.com",
                tool_name="execute_sql",
                decision="allow",
                policy_id=sample_policy_id,
                server_id=sample_server_id,
                ip_address="10.0.0.1",
                request_id="req_allow_123",
                details={"policy_matched": True},
            )

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.event_type == AuditEventType.AUTHORIZATION_ALLOWED
        assert added_event.severity == SeverityLevel.LOW
        assert added_event.decision == "allow"
        assert added_event.user_id == sample_user_id
        assert added_event.policy_id == sample_policy_id

    @pytest.mark.asyncio
    async def test_log_authorization_deny(
        self,
        audit_service,
        mock_db_session,
        sample_user_id,
    ):
        """Test logging an authorization deny decision."""
        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_authorization_decision(
                user_id=sample_user_id,
                user_email="user@example.com",
                tool_name="delete_database",
                decision="deny",
                details={"reason": "Insufficient permissions"},
            )

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.event_type == AuditEventType.AUTHORIZATION_DENIED
        assert added_event.severity == SeverityLevel.MEDIUM  # Deny is MEDIUM severity
        assert added_event.decision == "deny"


class TestToolInvocationLogging:
    """Test tool invocation logging."""

    @pytest.mark.asyncio
    async def test_log_tool_invocation(
        self,
        audit_service,
        mock_db_session,
        sample_user_id,
        sample_server_id,
    ):
        """Test logging a tool invocation."""
        # Arrange
        parameters = {"query": "SELECT * FROM users", "limit": 100}

        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_tool_invocation(
                user_id=sample_user_id,
                user_email="analyst@example.com",
                server_id=sample_server_id,
                tool_name="run_query",
                parameters=parameters,
                ip_address="172.16.0.5",
                request_id="req_tool_invoke_456",
            )

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.event_type == AuditEventType.TOOL_INVOKED
        assert added_event.severity == SeverityLevel.LOW
        assert added_event.user_id == sample_user_id
        assert added_event.server_id == sample_server_id
        assert added_event.tool_name == "run_query"
        assert added_event.details == {"parameters": parameters}

    @pytest.mark.asyncio
    async def test_log_tool_invocation_no_parameters(
        self,
        audit_service,
        mock_db_session,
        sample_user_id,
        sample_server_id,
    ):
        """Test logging a tool invocation without parameters."""
        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_tool_invocation(
                user_id=sample_user_id,
                user_email="user@example.com",
                server_id=sample_server_id,
                tool_name="health_check",
            )

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.details == {}


class TestServerRegistrationLogging:
    """Test server registration logging."""

    @pytest.mark.asyncio
    async def test_log_server_registration(
        self,
        audit_service,
        mock_db_session,
        sample_user_id,
        sample_server_id,
    ):
        """Test logging MCP server registration."""
        # Arrange
        server_name = "postgres-mcp-server"
        details = {"endpoint": "http://localhost:8080", "transport": "http"}

        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_server_registration(
                user_id=sample_user_id,
                user_email="admin@example.com",
                server_id=sample_server_id,
                server_name=server_name,
                details=details,
            )

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.event_type == AuditEventType.SERVER_REGISTERED
        assert added_event.severity == SeverityLevel.MEDIUM
        assert added_event.user_id == sample_user_id
        assert added_event.server_id == sample_server_id
        assert added_event.details["server_name"] == server_name
        assert added_event.details["endpoint"] == "http://localhost:8080"


class TestSecurityViolationLogging:
    """Test security violation logging."""

    @pytest.mark.asyncio
    async def test_log_security_violation_with_user(
        self,
        audit_service,
        mock_db_session,
        sample_user_id,
    ):
        """Test logging a security violation with user information."""
        # Arrange
        violation_type = "sql_injection_attempt"
        details = {"payload": "'; DROP TABLE users--", "blocked": True}

        # Act
        mock_forward_siem = AsyncMock()
        with patch.object(audit_service, "_forward_to_siem", mock_forward_siem):
            await audit_service.log_security_violation(
                user_id=sample_user_id,
                user_email="attacker@example.com",
                violation_type=violation_type,
                ip_address="203.0.113.45",
                details=details,
            )

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.event_type == AuditEventType.SECURITY_VIOLATION
        assert added_event.severity == SeverityLevel.CRITICAL
        assert added_event.user_id == sample_user_id
        assert added_event.ip_address == "203.0.113.45"
        assert added_event.details["violation_type"] == violation_type
        assert added_event.details["blocked"] is True

        # Security violations are CRITICAL, so SIEM forwarding should be called
        mock_forward_siem.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_security_violation_anonymous(
        self,
        audit_service,
        mock_db_session,
    ):
        """Test logging a security violation without user information."""
        # Act
        mock_forward_siem = AsyncMock()
        with patch.object(audit_service, "_forward_to_siem", mock_forward_siem):
            await audit_service.log_security_violation(
                user_id=None,
                user_email=None,
                violation_type="brute_force_attempt",
                ip_address="198.51.100.99",
                details={"attempts": 50, "timeframe": "5 minutes"},
            )

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.user_id is None
        assert added_event.user_email is None
        assert added_event.ip_address == "198.51.100.99"


class TestSIEMForwarding:
    """Test SIEM forwarding functionality."""

    @pytest.mark.asyncio
    async def test_forward_to_siem_on_high_severity(
        self,
        audit_service,
        mock_db_session,
    ):
        """Test that HIGH severity events trigger SIEM forwarding."""
        # Act
        mock_forward_siem = AsyncMock()
        with patch.object(audit_service, "_forward_to_siem", mock_forward_siem):
            await audit_service.log_event(
                event_type=AuditEventType.POLICY_UPDATED,
                severity=SeverityLevel.HIGH,
            )

        # Assert
        mock_forward_siem.assert_called_once()

    @pytest.mark.asyncio
    async def test_forward_to_siem_on_critical_severity(
        self,
        audit_service,
        mock_db_session,
    ):
        """Test that CRITICAL severity events trigger SIEM forwarding."""
        # Act
        mock_forward_siem = AsyncMock()
        with patch.object(audit_service, "_forward_to_siem", mock_forward_siem):
            await audit_service.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                severity=SeverityLevel.CRITICAL,
            )

        # Assert
        mock_forward_siem.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_siem_forward_on_low_severity(
        self,
        audit_service,
        mock_db_session,
    ):
        """Test that LOW severity events do NOT trigger SIEM forwarding."""
        # Act
        mock_forward_siem = AsyncMock()
        with patch.object(audit_service, "_forward_to_siem", mock_forward_siem):
            await audit_service.log_event(
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )

        # Assert
        mock_forward_siem.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_siem_forward_on_medium_severity(
        self,
        audit_service,
        mock_db_session,
    ):
        """Test that MEDIUM severity events do NOT trigger SIEM forwarding."""
        # Act
        mock_forward_siem = AsyncMock()
        with patch.object(audit_service, "_forward_to_siem", mock_forward_siem):
            await audit_service.log_event(
                event_type=AuditEventType.SERVER_UPDATED,
                severity=SeverityLevel.MEDIUM,
            )

        # Assert
        mock_forward_siem.assert_not_called()

    @pytest.mark.asyncio
    async def test_siem_forward_implementation(
        self,
        audit_service,
        mock_db_session,
    ):
        """Test the _forward_to_siem implementation."""
        # Arrange
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.CRITICAL,
        )

        # Act
        await audit_service._forward_to_siem(event)

        # Assert
        assert event.siem_forwarded is not None
        assert isinstance(event.siem_forwarded, datetime)
        mock_db_session.commit.assert_called_once()


class TestEventTimestamps:
    """Test event timestamp handling."""

    @pytest.mark.asyncio
    async def test_event_has_timestamp(self, audit_service, mock_db_session):
        """Test that events are created with a timestamp."""
        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_event(event_type=AuditEventType.USER_LOGIN)

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.timestamp is not None
        assert isinstance(added_event.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_timestamp_is_utc(self, audit_service, mock_db_session):
        """Test that event timestamps are in UTC."""
        # Act
        with patch.object(audit_service, "_forward_to_siem", new_callable=AsyncMock):
            await audit_service.log_event(event_type=AuditEventType.USER_LOGOUT)

        # Assert
        added_event = mock_db_session.add.call_args[0][0]
        assert added_event.timestamp.tzinfo is not None
