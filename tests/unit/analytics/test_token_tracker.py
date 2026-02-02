"""Unit tests for token/usage tracking via Policy Audit Service.

These tests cover:
- Policy decision logging (tracks API usage like token tracking)
- Analytics aggregation
- Export functionality
- Performance metrics

Following AAA pattern: Arrange, Act, Assert
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.models.policy_audit import PolicyDecisionResult


@pytest.fixture
def mock_db():
    """Create mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_auth_input():
    """Create sample authorization input."""
    from sark.services.policy.opa_client import AuthorizationInput

    return AuthorizationInput(
        user={"id": "user_123", "role": "developer", "teams": ["backend-team"]},
        action="gateway:tool:invoke",
        server={"id": "srv_001", "name": "postgres-mcp"},
        tool={"id": "tool_001", "name": "execute_query", "sensitivity_level": "high"},
        context={"client_ip": "192.168.1.100", "request_id": "req_abc123"},
    )


@pytest.fixture
def sample_decision_allow():
    """Create sample allow decision."""
    from sark.services.policy.opa_client import AuthorizationDecision

    return AuthorizationDecision(
        allow=True,
        reason="User has required permissions",
        policies_evaluated=["default_policy", "team_policy"],
        policy_results={
            "time_based": {"allow": True},
            "ip_filtering": {"allow": True},
        },
    )


@pytest.fixture
def sample_decision_deny():
    """Create sample deny decision."""
    from sark.services.policy.opa_client import AuthorizationDecision

    return AuthorizationDecision(
        allow=False,
        reason="User lacks required permissions for critical resource",
        policies_evaluated=["default_policy", "sensitivity_policy"],
        violations=["sensitivity_check_failed"],
        policy_results={
            "time_based": {"allow": True},
            "sensitivity": {"allow": False, "reason": "Critical resource access denied"},
        },
    )


class TestPolicyAuditServiceInit:
    """Test PolicyAuditService initialization."""

    def test_init_with_db_session(self, mock_db):
        """Test service initializes with database session."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange & Act
        service = PolicyAuditService(db_session=mock_db)

        # Assert
        assert service.db == mock_db


class TestDecisionLogging:
    """Test policy decision logging (usage tracking)."""

    @pytest.mark.asyncio
    async def test_log_decision_creates_entry(
        self, mock_db, sample_auth_input, sample_decision_allow
    ):
        """Test logging a policy decision creates database entry."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        # Mock the log entry creation
        mock_db.refresh = AsyncMock(
            side_effect=lambda x: setattr(x, "id", "log_001")
        )

        # Act
        log_entry = await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            duration_ms=15.5,
            cache_hit=False,
        )

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_decision_captures_user_info(
        self, mock_db, sample_auth_input, sample_decision_allow
    ):
        """Test decision log captures user information."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)
        captured_entry = None

        def capture_add(entry):
            nonlocal captured_entry
            captured_entry = entry

        mock_db.add = capture_add
        mock_db.refresh = AsyncMock()

        # Act
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            duration_ms=10.0,
        )

        # Assert
        assert captured_entry is not None
        assert captured_entry.user_id == "user_123"
        assert captured_entry.user_role == "developer"

    @pytest.mark.asyncio
    async def test_log_decision_captures_tool_info(
        self, mock_db, sample_auth_input, sample_decision_allow
    ):
        """Test decision log captures tool information."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)
        captured_entry = None

        def capture_add(entry):
            nonlocal captured_entry
            captured_entry = entry

        mock_db.add = capture_add
        mock_db.refresh = AsyncMock()

        # Act
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            duration_ms=10.0,
        )

        # Assert
        assert captured_entry.tool_id == "tool_001"
        assert captured_entry.tool_name == "execute_query"
        assert captured_entry.sensitivity_level == "high"

    @pytest.mark.asyncio
    async def test_log_decision_captures_duration(
        self, mock_db, sample_auth_input, sample_decision_allow
    ):
        """Test decision log captures evaluation duration (for performance tracking)."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)
        captured_entry = None

        def capture_add(entry):
            nonlocal captured_entry
            captured_entry = entry

        mock_db.add = capture_add
        mock_db.refresh = AsyncMock()

        # Act
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            duration_ms=15.5,
        )

        # Assert
        assert captured_entry.evaluation_duration_ms == 15.5

    @pytest.mark.asyncio
    async def test_log_decision_captures_cache_hit(
        self, mock_db, sample_auth_input, sample_decision_allow
    ):
        """Test decision log captures cache hit status."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)
        captured_entry = None

        def capture_add(entry):
            nonlocal captured_entry
            captured_entry = entry

        mock_db.add = capture_add
        mock_db.refresh = AsyncMock()

        # Act
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
            duration_ms=1.0,
            cache_hit=True,
        )

        # Assert
        assert captured_entry.cache_hit is True

    @pytest.mark.asyncio
    async def test_log_decision_allow_result(
        self, mock_db, sample_auth_input, sample_decision_allow
    ):
        """Test decision log correctly sets ALLOW result."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)
        captured_entry = None

        def capture_add(entry):
            nonlocal captured_entry
            captured_entry = entry

        mock_db.add = capture_add
        mock_db.refresh = AsyncMock()

        # Act
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_allow,
        )

        # Assert
        assert captured_entry.result == PolicyDecisionResult.ALLOW
        assert captured_entry.allow is True

    @pytest.mark.asyncio
    async def test_log_decision_deny_result(
        self, mock_db, sample_auth_input, sample_decision_deny
    ):
        """Test decision log correctly sets DENY result."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)
        captured_entry = None

        def capture_add(entry):
            nonlocal captured_entry
            captured_entry = entry

        mock_db.add = capture_add
        mock_db.refresh = AsyncMock()

        # Act
        await service.log_decision(
            auth_input=sample_auth_input,
            decision=sample_decision_deny,
        )

        # Assert
        assert captured_entry.result == PolicyDecisionResult.DENY
        assert captured_entry.allow is False
        assert captured_entry.denial_reason is not None


class TestDecisionAnalytics:
    """Test decision analytics functionality (usage analytics)."""

    @pytest.mark.asyncio
    async def test_get_decision_analytics_returns_summary(self, mock_db):
        """Test analytics returns summary statistics."""
        from sark.services.policy.audit import PolicyAuditService
        from sark.models.policy_audit import PolicyDecisionLog, PolicyDecisionResult

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        # Create mock log entries
        mock_logs = [
            MagicMock(
                allow=True,
                cache_hit=True,
                evaluation_duration_ms=5.0,
            ),
            MagicMock(
                allow=True,
                cache_hit=False,
                evaluation_duration_ms=15.0,
            ),
            MagicMock(
                allow=False,
                cache_hit=False,
                evaluation_duration_ms=20.0,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        start_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = datetime.now(UTC)
        analytics = await service.get_decision_analytics(start_time, end_time)

        # Assert
        assert "summary" in analytics
        assert analytics["summary"]["total_evaluations"] == 3
        assert analytics["summary"]["total_allows"] == 2
        assert analytics["summary"]["total_denies"] == 1

    @pytest.mark.asyncio
    async def test_get_decision_analytics_returns_cache_performance(self, mock_db):
        """Test analytics returns cache performance metrics."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        mock_logs = [
            MagicMock(allow=True, cache_hit=True, evaluation_duration_ms=2.0),
            MagicMock(allow=True, cache_hit=True, evaluation_duration_ms=1.5),
            MagicMock(allow=False, cache_hit=False, evaluation_duration_ms=15.0),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        start_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = datetime.now(UTC)
        analytics = await service.get_decision_analytics(start_time, end_time)

        # Assert
        assert "cache_performance" in analytics
        assert analytics["cache_performance"]["total_hits"] == 2
        assert analytics["cache_performance"]["total_misses"] == 1

    @pytest.mark.asyncio
    async def test_get_decision_analytics_returns_latency_metrics(self, mock_db):
        """Test analytics returns latency percentile metrics."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        mock_logs = [
            MagicMock(allow=True, cache_hit=True, evaluation_duration_ms=5.0),
            MagicMock(allow=True, cache_hit=False, evaluation_duration_ms=10.0),
            MagicMock(allow=True, cache_hit=False, evaluation_duration_ms=15.0),
            MagicMock(allow=False, cache_hit=False, evaluation_duration_ms=20.0),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        start_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = datetime.now(UTC)
        analytics = await service.get_decision_analytics(start_time, end_time)

        # Assert
        assert "latency" in analytics
        assert "avg_ms" in analytics["latency"]
        assert "p50_ms" in analytics["latency"]
        assert "p95_ms" in analytics["latency"]
        assert "p99_ms" in analytics["latency"]


class TestTopDenialReasons:
    """Test top denial reasons analytics."""

    @pytest.mark.asyncio
    async def test_get_top_denial_reasons(self, mock_db):
        """Test retrieving top denial reasons."""
        from sark.services.policy.audit import PolicyAuditService

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        mock_rows = [
            MagicMock(denial_reason="Insufficient permissions", count=50),
            MagicMock(denial_reason="Time-based restriction", count=25),
            MagicMock(denial_reason="IP not in allowlist", count=10),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        start_time = datetime.now(UTC) - timedelta(days=1)
        end_time = datetime.now(UTC)
        reasons = await service.get_top_denial_reasons(start_time, end_time, limit=10)

        # Assert
        assert len(reasons) == 3
        assert reasons[0]["reason"] == "Insufficient permissions"
        assert reasons[0]["count"] == 50


class TestExportFunctionality:
    """Test export functionality (CSV/JSON)."""

    @pytest.mark.asyncio
    async def test_export_decisions_csv(self, mock_db):
        """Test exporting decisions to CSV format."""
        from sark.services.policy.audit import PolicyAuditService
        from sark.models.policy_audit import PolicyDecisionResult

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        mock_logs = [
            MagicMock(
                timestamp=datetime.now(UTC),
                result=PolicyDecisionResult.ALLOW,
                user_id="user_001",
                user_role="developer",
                action="gateway:tool:invoke",
                resource_type="tool",
                tool_name="execute_query",
                sensitivity_level="high",
                reason="Allowed",
                evaluation_duration_ms=10.0,
                cache_hit=False,
                client_ip="192.168.1.100",
                mfa_verified=True,
            ),
        ]

        # Mock the get_decision_logs method
        with patch.object(service, "get_decision_logs", AsyncMock(return_value=mock_logs)):
            # Act
            csv_content = await service.export_decisions_csv()

        # Assert
        assert "timestamp" in csv_content
        assert "result" in csv_content
        assert "user_id" in csv_content

    @pytest.mark.asyncio
    async def test_export_decisions_json(self, mock_db):
        """Test exporting decisions to JSON format."""
        from sark.services.policy.audit import PolicyAuditService
        from sark.models.policy_audit import PolicyDecisionResult
        import json

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        mock_logs = [
            MagicMock(
                id="log_001",
                timestamp=datetime.now(UTC),
                result=PolicyDecisionResult.ALLOW,
                allow=True,
                user_id="user_001",
                user_role="developer",
                user_teams=["backend-team"],
                action="gateway:tool:invoke",
                resource_type="tool",
                resource_id="tool_001",
                tool_id="tool_001",
                tool_name="execute_query",
                sensitivity_level="high",
                policies_evaluated=["default_policy"],
                policy_results={"time_based": {"allow": True}},
                violations=[],
                reason="Allowed",
                evaluation_duration_ms=10.0,
                cache_hit=False,
                client_ip="192.168.1.100",
                request_id="req_001",
                mfa_verified=True,
                mfa_method="totp",
                time_based_allowed=True,
                ip_filtering_allowed=True,
                mfa_required_satisfied=True,
            ),
        ]

        # Mock the get_decision_logs method
        with patch.object(service, "get_decision_logs", AsyncMock(return_value=mock_logs)):
            # Act
            json_content = await service.export_decisions_json()

        # Assert
        data = json.loads(json_content)
        assert "decisions" in data
        assert "count" in data
        assert data["count"] == 1


class TestPolicyChangeLogging:
    """Test policy change logging for compliance tracking."""

    @pytest.mark.asyncio
    async def test_log_policy_change_creates_entry(self, mock_db):
        """Test logging a policy change creates database entry."""
        from sark.services.policy.audit import PolicyAuditService
        from sark.models.policy_audit import PolicyChangeType

        # Arrange
        service = PolicyAuditService(db_session=mock_db)

        # Mock version query
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # No existing version
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.refresh = AsyncMock()

        # Act
        change_log = await service.log_policy_change(
            policy_name="bedtime_policy",
            change_type=PolicyChangeType.CREATED,
            changed_by_user_id="admin_001",
            policy_content="package bedtime\ndefault allow = false",
            change_reason="Initial bedtime policy",
        )

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_policy_change_increments_version(self, mock_db):
        """Test policy change logging increments version number."""
        from sark.services.policy.audit import PolicyAuditService
        from sark.models.policy_audit import PolicyChangeType

        # Arrange
        service = PolicyAuditService(db_session=mock_db)
        captured_entry = None

        def capture_add(entry):
            nonlocal captured_entry
            captured_entry = entry

        mock_db.add = capture_add

        # Mock version query to return existing version
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3  # Existing version is 3
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.refresh = AsyncMock()

        # Act
        await service.log_policy_change(
            policy_name="bedtime_policy",
            change_type=PolicyChangeType.UPDATED,
            changed_by_user_id="admin_001",
            policy_content="package bedtime\ndefault allow = true",
        )

        # Assert
        assert captured_entry.policy_version == 4  # Should be 3 + 1
