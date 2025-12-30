"""Comprehensive tests for policy audit service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from sark.models.policy_audit import PolicyChangeType, PolicyDecisionResult
from sark.services.policy.audit import PolicyAuditService
from sark.services.policy.opa_client import AuthorizationDecision, AuthorizationInput


class TestPolicyAuditService:
    """Test suite for PolicyAuditService class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        """Create a PolicyAuditService instance with mocked session."""
        return PolicyAuditService(db_session=mock_db_session)

    @pytest.fixture
    def sample_auth_input(self):
        """Sample authorization input for testing."""
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
            },
            server={
                "id": "server-789",
                "name": "test_server",
            },
            context={
                "client_ip": "192.168.1.1",
                "request_id": "req-abc-123",
            },
        )

    @pytest.fixture
    def sample_decision_allow(self):
        """Sample allow decision."""
        return AuthorizationDecision(
            allow=True,
            reason="User has required permissions",
            filtered_parameters={"param1": "filtered"},
            audit_id="audit-xyz-789",
        )

    @pytest.fixture
    def sample_decision_deny(self):
        """Sample deny decision."""
        return AuthorizationDecision(
            allow=False,
            reason="Insufficient permissions",
        )

    # ===== Decision Logging Tests =====

    @pytest.mark.asyncio
    async def test_log_decision_allow(
        self, service, mock_db_session, sample_auth_input, sample_decision_allow
    ):
        """Test logging an allow decision."""
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            duration_ms=12.5,
            cache_hit=False,
        )

        # Verify database operations
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called

        # Verify log entry passed to add()
        added_entry = mock_db_session.add.call_args[0][0]
        assert added_entry.result == PolicyDecisionResult.ALLOW
        assert added_entry.allow is True
        assert added_entry.user_id == "user-123"
        assert added_entry.user_role == "developer"
        assert added_entry.user_teams == ["team-1", "team-2"]
        assert added_entry.action == "tool:invoke"
        assert added_entry.tool_id == "tool-456"
        assert added_entry.tool_name == "test_tool"
        assert added_entry.sensitivity_level == "medium"
        assert added_entry.server_id == "server-789"
        assert added_entry.server_name == "test_server"
        assert added_entry.reason == "User has required permissions"
        assert added_entry.evaluation_duration_ms == 12.5
        assert added_entry.cache_hit is False
        assert added_entry.client_ip == "192.168.1.1"
        assert added_entry.request_id == "req-abc-123"
        assert added_entry.mfa_verified is True
        assert added_entry.mfa_method == "totp"

    @pytest.mark.asyncio
    async def test_log_decision_deny(
        self, service, mock_db_session, sample_auth_input, sample_decision_deny
    ):
        """Test logging a deny decision."""
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_deny,
            duration_ms=8.3,
            cache_hit=True,
        )

        added_entry = mock_db_session.add.call_args[0][0]
        assert added_entry.result == PolicyDecisionResult.DENY
        assert added_entry.allow is False
        assert added_entry.denial_reason == "Insufficient permissions"
        assert added_entry.cache_hit is True

    @pytest.mark.asyncio
    async def test_log_decision_with_request_context(
        self, service, mock_db_session, sample_auth_input, sample_decision_allow
    ):
        """Test logging decision with additional request context."""
        request_context = {
            "client_ip": "10.0.0.1",
            "request_id": "custom-req-id",
            "session_id": "session-abc",
        }

        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            request_context=request_context,
        )

        added_entry = mock_db_session.add.call_args[0][0]
        assert added_entry.client_ip == "10.0.0.1"
        assert added_entry.request_id == "custom-req-id"
        assert added_entry.session_id == "session-abc"

    @pytest.mark.asyncio
    async def test_log_decision_minimal_auth_input(
        self, service, mock_db_session, sample_decision_allow
    ):
        """Test logging decision with minimal authorization input."""
        minimal_input = AuthorizationInput(
            user={"id": "user-minimal"},
            action="read",
            context={},
        )

        await service.log_decision(
            auth_input=minimal_input,
            decision=sample_decision_allow,
        )

        added_entry = mock_db_session.add.call_args[0][0]
        assert added_entry.user_id == "user-minimal"
        assert added_entry.action == "read"
        assert added_entry.user_role is None
        assert added_entry.tool_id is None
        assert added_entry.server_id is None

    @pytest.mark.asyncio
    async def test_log_decision_database_error(
        self, service, mock_db_session, sample_auth_input, sample_decision_allow
    ):
        """Test that database errors are handled and re-raised."""
        mock_db_session.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await service.log_decision(
                auth_input=sample_auth_input,
                decision=sample_decision_allow,
            )

        assert "Database error" in str(exc_info.value)
        assert mock_db_session.rollback.called

    # ===== Policy Change Logging Tests =====

    @pytest.mark.asyncio
    async def test_log_policy_change_created(self, service, mock_db_session):
        """Test logging a policy creation."""
        # Mock the version query
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # No previous version
        mock_db_session.execute.return_value = mock_result

        policy_content = "package test\nallow = true"

        await service.log_policy_change(
            policy_name="test.policy",
            change_type=PolicyChangeType.CREATED,
            changed_by_user_id="user-admin",
            policy_content=policy_content,
            change_reason="Initial policy creation",
        )

        # Verify version query was made
        assert mock_db_session.execute.called

        # Verify change log entry
        added_entry = mock_db_session.add.call_args[0][0]
        assert added_entry.change_type == PolicyChangeType.CREATED
        assert added_entry.policy_name == "test.policy"
        assert added_entry.policy_version == 1  # First version
        assert added_entry.changed_by_user_id == "user-admin"
        assert added_entry.policy_content == policy_content
        assert added_entry.change_reason == "Initial policy creation"
        assert added_entry.policy_hash is not None  # SHA256 hash

    @pytest.mark.asyncio
    async def test_log_policy_change_updated_with_diff(self, service, mock_db_session):
        """Test logging a policy update with diff calculation."""
        # Mock existing version
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3  # Version 3 exists
        mock_db_session.execute.return_value = mock_result

        previous_content = "package test\nallow = false"
        new_content = "package test\nallow = true"

        await service.log_policy_change(
            policy_name="test.policy",
            change_type=PolicyChangeType.UPDATED,
            changed_by_user_id="user-admin",
            policy_content=new_content,
            previous_content=previous_content,
            change_reason="Enable access",
        )

        added_entry = mock_db_session.add.call_args[0][0]
        assert added_entry.policy_version == 4  # Incremented from 3
        assert added_entry.policy_diff is not None
        assert (
            "allow = false" in added_entry.policy_diff or "allow = true" in added_entry.policy_diff
        )

    @pytest.mark.asyncio
    async def test_log_policy_change_with_metadata(self, service, mock_db_session):
        """Test logging policy change with additional metadata."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db_session.execute.return_value = mock_result

        metadata = {
            "approver_user_id": "user-approver",
            "approval_id": "approval-123",
            "breaking_change": True,
            "tags": ["rbac", "sensitive"],
        }

        await service.log_policy_change(
            policy_name="critical.policy",
            change_type=PolicyChangeType.UPDATED,
            changed_by_user_id="user-admin",
            policy_content="new content",
            metadata=metadata,
        )

        added_entry = mock_db_session.add.call_args[0][0]
        assert added_entry.approver_user_id == "user-approver"
        assert added_entry.approval_id == "approval-123"
        assert added_entry.breaking_change is True
        assert added_entry.tags == ["rbac", "sensitive"]

    @pytest.mark.asyncio
    async def test_log_policy_change_database_error(self, service, mock_db_session):
        """Test that database errors in policy change logging are handled."""
        mock_db_session.execute.side_effect = Exception("Query failed")

        with pytest.raises(Exception):
            await service.log_policy_change(
                policy_name="test.policy",
                change_type=PolicyChangeType.CREATED,
                changed_by_user_id="user-admin",
            )

        assert mock_db_session.rollback.called

    # ===== Query and Retrieval Tests =====

    @pytest.mark.asyncio
    async def test_get_decision_logs_no_filters(self, service, mock_db_session):
        """Test retrieving decision logs without filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        logs = await service.get_decision_logs()

        assert logs == []
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_decision_logs_with_filters(self, service, mock_db_session):
        """Test retrieving decision logs with filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        await service.get_decision_logs(
            start_time=start_time,
            end_time=end_time,
            user_id="user-123",
            action="tool:invoke",
            result=PolicyDecisionResult.DENY,
            limit=50,
            offset=10,
        )

        # Query should have been executed with filters
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_policy_changes(self, service, mock_db_session):
        """Test retrieving policy change logs."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        await service.get_policy_changes(
            policy_name="test.policy",
            change_type=PolicyChangeType.UPDATED,
            limit=100,
        )

        assert mock_db_session.execute.called

    # ===== Export Tests =====

    @pytest.mark.asyncio
    async def test_export_decisions_csv_empty(self, service, mock_db_session):
        """Test exporting decisions to CSV with no data."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        csv_output = await service.export_decisions_csv()

        assert "timestamp" in csv_output
        assert "result" in csv_output
        assert "user_id" in csv_output
        # Should have headers but no data rows

    @pytest.mark.asyncio
    async def test_export_decisions_json_empty(self, service, mock_db_session):
        """Test exporting decisions to JSON with no data."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        json_output = await service.export_decisions_json()

        assert '"decisions":' in json_output
        assert '"count": 0' in json_output

    # ===== Analytics Tests =====

    @pytest.mark.asyncio
    async def test_get_decision_analytics_empty(self, service, mock_db_session):
        """Test analytics with no data."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.now(UTC) - timedelta(days=1)
        end_time = datetime.now(UTC)

        analytics = await service.get_decision_analytics(start_time, end_time)

        assert analytics["summary"]["total_evaluations"] == 0
        assert analytics["summary"]["total_allows"] == 0
        assert analytics["summary"]["total_denies"] == 0
        assert analytics["summary"]["allow_rate"] == 0
        assert analytics["cache_performance"]["hit_rate"] == 0

    @pytest.mark.asyncio
    async def test_get_top_denial_reasons(self, service, mock_db_session):
        """Test getting top denial reasons."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.now(UTC) - timedelta(days=7)
        end_time = datetime.now(UTC)

        reasons = await service.get_top_denial_reasons(start_time, end_time, limit=10)

        assert reasons == []
        assert mock_db_session.execute.called

    # ===== Diff Calculation Tests =====

    def test_calculate_diff(self, service):
        """Test diff calculation between policy versions."""
        old_content = "package test\nallow = false\nrole = user"
        new_content = "package test\nallow = true\nrole = admin"

        diff = service._calculate_diff(old_content, new_content)

        assert isinstance(diff, str)
        assert "-allow = false" in diff or "+allow = true" in diff
        assert "previous" in diff
        assert "current" in diff

    def test_calculate_diff_empty_old(self, service):
        """Test diff calculation with empty old content."""
        old_content = ""
        new_content = "package test\nallow = true"

        diff = service._calculate_diff(old_content, new_content)

        assert "+package test" in diff or "allow = true" in diff

    def test_calculate_diff_identical(self, service):
        """Test diff calculation with identical content."""
        content = "package test\nallow = true"

        diff = service._calculate_diff(content, content)

        # Should be minimal/empty since no changes
        assert diff is not None
