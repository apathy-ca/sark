"""Comprehensive tests for PolicyAuditService.

This module tests:
- Policy decision logging
- Policy change tracking with versioning
- Query and retrieval functionality
- Export capabilities (CSV, JSON)
- Analytics and reporting
"""

import csv
from datetime import UTC, datetime, timedelta
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.policy_audit import (
    PolicyChangeLog,
    PolicyChangeType,
    PolicyDecisionLog,
    PolicyDecisionResult,
)
from sark.services.policy.audit import PolicyAuditService
from sark.services.policy.opa_client import AuthorizationDecision, AuthorizationInput


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def audit_service(mock_db_session):
    """Create PolicyAuditService instance with mock session."""
    return PolicyAuditService(db_session=mock_db_session)


@pytest.fixture
def sample_auth_input():
    """Create sample authorization input."""
    return AuthorizationInput(
        user={
            "id": "user-123",
            "email": "test@example.com",
            "role": "developer",
            "teams": ["team-1", "team-2"],
            "mfa_verified": True,
            "mfa_methods": ["totp"],
        },
        action="tool:invoke",
        tool={
            "id": "tool-456",
            "name": "test_tool",
            "sensitivity_level": "medium",
            "owner": "user-123",
        },
        server={
            "id": "server-789",
            "name": "test_server",
        },
        context={
            "client_ip": "192.168.1.1",
            "request_id": "req-123",
            "timestamp": 1234567890,
        },
    )


@pytest.fixture
def sample_decision_allow():
    """Create sample allow decision."""
    return AuthorizationDecision(
        allow=True,
        reason="User has required permissions",
        filtered_parameters={"param1": "value1"},
        audit_id="audit-123",
    )


@pytest.fixture
def sample_decision_deny():
    """Create sample deny decision."""
    return AuthorizationDecision(
        allow=False,
        reason="Insufficient permissions",
    )


class TestPolicyAuditServiceInit:
    """Test PolicyAuditService initialization."""

    def test_initialization(self, mock_db_session):
        """Test audit service initializes correctly."""
        service = PolicyAuditService(db_session=mock_db_session)

        assert service.db == mock_db_session
        assert service.logger is not None


class TestLogDecision:
    """Test policy decision logging."""

    @pytest.mark.asyncio
    async def test_log_allow_decision(
        self, audit_service, mock_db_session, sample_auth_input, sample_decision_allow
    ):
        """Test logging an allow decision."""
        # Mock the refresh to set ID
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        result = await audit_service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            duration_ms=15.5,
            cache_hit=False,
        )

        # Verify decision was added and committed
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # Verify the log entry
        added_log = mock_db_session.add.call_args[0][0]
        assert isinstance(added_log, PolicyDecisionLog)
        assert added_log.result == PolicyDecisionResult.ALLOW
        assert added_log.allow is True
        assert added_log.user_id == "user-123"
        assert added_log.user_role == "developer"
        assert added_log.user_teams == ["team-1", "team-2"]
        assert added_log.action == "tool:invoke"
        assert added_log.tool_id == "tool-456"
        assert added_log.tool_name == "test_tool"
        assert added_log.sensitivity_level == "medium"
        assert added_log.server_id == "server-789"
        assert added_log.server_name == "test_server"
        assert added_log.reason == "User has required permissions"
        assert added_log.evaluation_duration_ms == 15.5
        assert added_log.cache_hit is False
        assert added_log.client_ip == "192.168.1.1"
        assert added_log.request_id == "req-123"
        assert added_log.mfa_verified is True
        assert added_log.mfa_method == "totp"

    @pytest.mark.asyncio
    async def test_log_deny_decision(
        self, audit_service, mock_db_session, sample_auth_input, sample_decision_deny
    ):
        """Test logging a deny decision."""
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        result = await audit_service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_deny,
            duration_ms=10.2,
            cache_hit=True,
        )

        added_log = mock_db_session.add.call_args[0][0]
        assert added_log.result == PolicyDecisionResult.DENY
        assert added_log.allow is False
        assert added_log.denial_reason == "Insufficient permissions"
        assert added_log.cache_hit is True

    @pytest.mark.asyncio
    async def test_log_decision_with_request_context(
        self, audit_service, mock_db_session, sample_auth_input, sample_decision_allow
    ):
        """Test logging decision with additional request context."""
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        request_context = {
            "client_ip": "10.0.0.1",
            "request_id": "req-456",
            "session_id": "sess-789",
        }

        result = await audit_service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            request_context=request_context,
        )

        added_log = mock_db_session.add.call_args[0][0]
        assert added_log.client_ip == "10.0.0.1"
        assert added_log.request_id == "req-456"
        assert added_log.session_id == "sess-789"

    @pytest.mark.asyncio
    async def test_log_decision_determines_resource_type_from_action(
        self, audit_service, mock_db_session, sample_decision_allow
    ):
        """Test that resource type is determined from action."""
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        # Test server action
        server_input = AuthorizationInput(
            user={"id": "user-123", "role": "admin"},
            action="server:register",
            server={"id": "srv-123", "name": "test-server"},
            context={},
        )

        await audit_service.log_decision(
            auth_input=server_input,
            decision=sample_decision_allow,
        )

        added_log = mock_db_session.add.call_args[0][0]
        assert added_log.resource_type == "server"
        assert added_log.resource_id == "srv-123"

        # Test tool action
        tool_input = AuthorizationInput(
            user={"id": "user-123", "role": "developer"},
            action="tool:invoke",
            tool={"id": "tool-456", "name": "test-tool"},
            context={},
        )

        await audit_service.log_decision(
            auth_input=tool_input,
            decision=sample_decision_allow,
        )

        added_log = mock_db_session.add.call_args[0][0]
        assert added_log.resource_type == "tool"
        assert added_log.resource_id == "tool-456"

    @pytest.mark.asyncio
    async def test_log_decision_handles_missing_optional_fields(
        self, audit_service, mock_db_session, sample_decision_allow
    ):
        """Test logging decision with minimal fields."""
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        minimal_input = AuthorizationInput(
            user={"id": "user-123"},
            action="read",
            context={},
        )

        result = await audit_service.log_decision(
            auth_input=minimal_input,
            decision=sample_decision_allow,
        )

        added_log = mock_db_session.add.call_args[0][0]
        assert added_log.user_id == "user-123"
        assert added_log.user_role is None
        assert added_log.user_teams == []
        assert added_log.tool_id is None
        assert added_log.server_id is None

    @pytest.mark.asyncio
    async def test_log_decision_rollback_on_error(
        self, audit_service, mock_db_session, sample_auth_input, sample_decision_allow
    ):
        """Test that transaction is rolled back on error."""
        mock_db_session.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await audit_service.log_decision(
                auth_input=sample_auth_input,
                decision=sample_decision_allow,
            )

        assert "Database error" in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()


class TestLogPolicyChange:
    """Test policy change logging."""

    @pytest.mark.asyncio
    async def test_log_policy_created(self, audit_service, mock_db_session):
        """Test logging a policy creation."""
        # Mock the version query to return 0
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db_session.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        policy_content = "package example\nallow { true }"

        result = await audit_service.log_policy_change(
            policy_name="test_policy",
            change_type=PolicyChangeType.CREATED,
            changed_by_user_id="user-123",
            policy_content=policy_content,
            change_reason="Initial policy creation",
        )

        # Verify change was added
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # Verify the change log entry
        added_change = mock_db_session.add.call_args[0][0]
        assert isinstance(added_change, PolicyChangeLog)
        assert added_change.policy_name == "test_policy"
        assert added_change.change_type == PolicyChangeType.CREATED
        assert added_change.policy_version == 1  # First version
        assert added_change.changed_by_user_id == "user-123"
        assert added_change.policy_content == policy_content
        assert added_change.change_reason == "Initial policy creation"
        assert added_change.policy_hash is not None

    @pytest.mark.asyncio
    async def test_log_policy_updated_with_diff(self, audit_service, mock_db_session):
        """Test logging a policy update with diff calculation."""
        # Mock existing version
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db_session.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        previous_content = "package example\nallow { false }"
        new_content = "package example\nallow { true }"

        result = await audit_service.log_policy_change(
            policy_name="test_policy",
            change_type=PolicyChangeType.UPDATED,
            changed_by_user_id="user-456",
            policy_content=new_content,
            previous_content=previous_content,
            change_reason="Allow all requests",
        )

        added_change = mock_db_session.add.call_args[0][0]
        assert added_change.policy_version == 2  # Incremented version
        assert added_change.policy_diff is not None
        assert "false" in added_change.policy_diff
        assert "true" in added_change.policy_diff

    @pytest.mark.asyncio
    async def test_log_policy_with_metadata(self, audit_service, mock_db_session):
        """Test logging policy change with metadata."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db_session.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        metadata = {
            "approver_user_id": "user-admin",
            "approval_id": "approval-123",
            "breaking_change": True,
            "tags": ["security", "critical"],
            "jira_ticket": "SEC-456",
        }

        result = await audit_service.log_policy_change(
            policy_name="security_policy",
            change_type=PolicyChangeType.UPDATED,
            changed_by_user_id="user-123",
            policy_content="package security\nallow { input.user.role == \"admin\" }",
            change_reason="Tighten security requirements",
            metadata=metadata,
        )

        added_change = mock_db_session.add.call_args[0][0]
        assert added_change.approver_user_id == "user-admin"
        assert added_change.approval_id == "approval-123"
        assert added_change.breaking_change is True
        assert added_change.tags == ["security", "critical"]
        assert added_change.details == metadata

    @pytest.mark.asyncio
    async def test_log_policy_change_types(self, audit_service, mock_db_session):
        """Test logging different policy change types."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db_session.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        # Test each change type
        change_types = [
            PolicyChangeType.CREATED,
            PolicyChangeType.UPDATED,
            PolicyChangeType.DELETED,
            PolicyChangeType.ACTIVATED,
            PolicyChangeType.DEACTIVATED,
        ]

        for change_type in change_types:
            await audit_service.log_policy_change(
                policy_name="test_policy",
                change_type=change_type,
                changed_by_user_id="user-123",
                policy_content="package test\nallow { true }",
            )

            added_change = mock_db_session.add.call_args[0][0]
            assert added_change.change_type == change_type

    @pytest.mark.asyncio
    async def test_log_policy_change_rollback_on_error(
        self, audit_service, mock_db_session
    ):
        """Test that transaction is rolled back on error."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await audit_service.log_policy_change(
                policy_name="test_policy",
                change_type=PolicyChangeType.CREATED,
                changed_by_user_id="user-123",
                policy_content="package test\nallow { true }",
            )

        assert "Database error" in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()


class TestCalculateDiff:
    """Test diff calculation."""

    def test_calculate_diff(self, audit_service):
        """Test calculating diff between policy versions."""
        old_content = """package example

default allow = false

allow {
    input.user.role == "admin"
}"""

        new_content = """package example

default allow = false

allow {
    input.user.role == "admin"
    input.user.mfa_verified == true
}"""

        diff = audit_service._calculate_diff(old_content, new_content)

        assert diff is not None
        assert "---" in diff
        assert "+++" in diff
        assert "admin" in diff
        assert "mfa_verified" in diff

    def test_calculate_diff_no_changes(self, audit_service):
        """Test diff when no changes."""
        content = "package test\nallow { true }"

        diff = audit_service._calculate_diff(content, content)

        # No diff lines for identical content
        assert diff == ""


class TestGetDecisionLogs:
    """Test querying decision logs."""

    @pytest.mark.asyncio
    async def test_get_decision_logs_all(self, audit_service, mock_db_session):
        """Test getting all decision logs."""
        # Mock decision logs
        mock_logs = [
            PolicyDecisionLog(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                result=PolicyDecisionResult.ALLOW,
                allow=True,
                user_id="user-1",
                action="tool:invoke",
                reason="Allowed",
            ),
            PolicyDecisionLog(
                id=uuid4(),
                timestamp=datetime.now(UTC) - timedelta(hours=1),
                result=PolicyDecisionResult.DENY,
                allow=False,
                user_id="user-2",
                action="server:register",
                reason="Denied",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db_session.execute.return_value = mock_result

        logs = await audit_service.get_decision_logs()

        assert len(logs) == 2
        assert logs[0].user_id == "user-1"
        assert logs[1].user_id == "user-2"

    @pytest.mark.asyncio
    async def test_get_decision_logs_with_filters(self, audit_service, mock_db_session):
        """Test getting decision logs with filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        logs = await audit_service.get_decision_logs(
            start_time=start_time,
            end_time=end_time,
            user_id="user-123",
            action="tool:invoke",
            result=PolicyDecisionResult.ALLOW,
            limit=50,
            offset=10,
        )

        # Verify execute was called (query was built with filters)
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_decision_logs_pagination(self, audit_service, mock_db_session):
        """Test decision logs pagination."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # First page
        await audit_service.get_decision_logs(limit=10, offset=0)
        mock_db_session.execute.assert_called()

        # Second page
        await audit_service.get_decision_logs(limit=10, offset=10)
        assert mock_db_session.execute.call_count == 2


class TestGetPolicyChanges:
    """Test querying policy changes."""

    @pytest.mark.asyncio
    async def test_get_policy_changes_all(self, audit_service, mock_db_session):
        """Test getting all policy changes."""
        mock_changes = [
            PolicyChangeLog(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                change_type=PolicyChangeType.CREATED,
                policy_name="policy1",
                policy_version=1,
                changed_by_user_id="user-1",
            ),
            PolicyChangeLog(
                id=uuid4(),
                timestamp=datetime.now(UTC) - timedelta(hours=1),
                change_type=PolicyChangeType.UPDATED,
                policy_name="policy2",
                policy_version=2,
                changed_by_user_id="user-2",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_changes
        mock_db_session.execute.return_value = mock_result

        changes = await audit_service.get_policy_changes()

        assert len(changes) == 2
        assert changes[0].policy_name == "policy1"
        assert changes[1].policy_name == "policy2"

    @pytest.mark.asyncio
    async def test_get_policy_changes_with_filters(
        self, audit_service, mock_db_session
    ):
        """Test getting policy changes with filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.now(UTC) - timedelta(days=30)
        end_time = datetime.now(UTC)

        changes = await audit_service.get_policy_changes(
            policy_name="test_policy",
            start_time=start_time,
            end_time=end_time,
            change_type=PolicyChangeType.UPDATED,
            limit=20,
        )

        # Verify execute was called
        mock_db_session.execute.assert_called_once()


class TestExportFunctionality:
    """Test export functionality."""

    @pytest.mark.asyncio
    async def test_export_decisions_csv(self, audit_service, mock_db_session):
        """Test exporting decisions to CSV."""
        mock_logs = [
            PolicyDecisionLog(
                id=uuid4(),
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                result=PolicyDecisionResult.ALLOW,
                allow=True,
                user_id="user-1",
                action="tool:invoke",
                tool_name="test_tool",
                reason="Allowed by policy",
            ),
            PolicyDecisionLog(
                id=uuid4(),
                timestamp=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
                result=PolicyDecisionResult.DENY,
                allow=False,
                user_id="user-2",
                action="server:register",
                server_name="test_server",
                reason="Insufficient permissions",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db_session.execute.return_value = mock_result

        csv_data = await audit_service.export_decisions_csv()

        assert csv_data is not None
        assert "user-1" in csv_data
        assert "user-2" in csv_data
        assert "tool:invoke" in csv_data
        assert "server:register" in csv_data

        # Verify CSV format
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["user_id"] == "user-1"
        assert rows[1]["user_id"] == "user-2"

    @pytest.mark.asyncio
    async def test_export_decisions_json(self, audit_service, mock_db_session):
        """Test exporting decisions to JSON."""
        mock_logs = [
            PolicyDecisionLog(
                id=uuid4(),
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                result=PolicyDecisionResult.ALLOW,
                allow=True,
                user_id="user-1",
                action="tool:invoke",
                reason="Allowed",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db_session.execute.return_value = mock_result

        json_data = await audit_service.export_decisions_json()

        assert json_data is not None

        # Verify JSON format
        data = json.loads(json_data)
        assert "decisions" in data
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["user_id"] == "user-1"
        assert data["decisions"][0]["action"] == "tool:invoke"


class TestAnalytics:
    """Test analytics functionality."""

    @pytest.mark.asyncio
    async def test_get_decision_analytics(self, audit_service, mock_db_session):
        """Test getting decision analytics."""
        # Mock analytics data
        mock_analytics = {
            "total_decisions": 100,
            "allow_count": 75,
            "deny_count": 25,
            "allow_rate": 0.75,
            "deny_rate": 0.25,
            "unique_users": 20,
            "unique_tools": 15,
            "avg_duration_ms": 12.5,
        }

        # Create mock results for different queries
        mock_results = []
        for key, value in mock_analytics.items():
            mock_result = MagicMock()
            if isinstance(value, (int, float)):
                mock_result.scalar.return_value = value
            else:
                mock_result.scalar.return_value = None
            mock_results.append(mock_result)

        mock_db_session.execute.side_effect = mock_results

        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        analytics = await audit_service.get_decision_analytics(
            start_time=start_time, end_time=end_time
        )

        assert analytics is not None
        # Verify execute was called multiple times for different metrics
        assert mock_db_session.execute.call_count > 0

    @pytest.mark.asyncio
    async def test_get_top_denial_reasons(self, audit_service, mock_db_session):
        """Test getting top denial reasons."""
        # Mock denial reasons with counts as named tuples
        from collections import namedtuple
        ReasonRow = namedtuple('ReasonRow', ['denial_reason', 'count'])

        mock_reasons = [
            ReasonRow("Insufficient permissions", 50),
            ReasonRow("MFA not verified", 30),
            ReasonRow("Outside allowed time window", 20),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_reasons
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        reasons = await audit_service.get_top_denial_reasons(
            start_time=start_time,
            end_time=end_time,
            limit=5
        )

        assert reasons is not None
        assert len(reasons) == 3
        assert reasons[0]["reason"] == "Insufficient permissions"
        assert reasons[0]["count"] == 50
        mock_db_session.execute.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_log_decision_with_unknown_user(
        self, audit_service, mock_db_session, sample_decision_allow
    ):
        """Test logging decision with unknown user ID."""
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        auth_input = AuthorizationInput(
            user={},  # No ID
            action="test",
            context={},
        )

        result = await audit_service.log_decision(
            auth_input=auth_input, decision=sample_decision_allow
        )

        added_log = mock_db_session.add.call_args[0][0]
        assert added_log.user_id == "unknown"

    @pytest.mark.asyncio
    async def test_log_policy_change_first_version(
        self, audit_service, mock_db_session
    ):
        """Test logging policy change when no previous version exists."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # No previous version
        mock_db_session.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db_session.refresh.side_effect = mock_refresh

        result = await audit_service.log_policy_change(
            policy_name="new_policy",
            change_type=PolicyChangeType.CREATED,
            changed_by_user_id="user-123",
            policy_content="package new\nallow { true }",
        )

        added_change = mock_db_session.add.call_args[0][0]
        assert added_change.policy_version == 1

    @pytest.mark.asyncio
    async def test_empty_decision_logs_query(self, audit_service, mock_db_session):
        """Test querying decision logs when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        logs = await audit_service.get_decision_logs()

        assert logs == []

    @pytest.mark.asyncio
    async def test_empty_policy_changes_query(self, audit_service, mock_db_session):
        """Test querying policy changes when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        changes = await audit_service.get_policy_changes()

        assert changes == []
