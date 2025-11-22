"""Tests for policy audit service."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock

from sark.models.policy_audit import PolicyChangeType, PolicyDecisionResult
from sark.services.policy.audit import PolicyAuditService
from sark.services.policy.opa_client import AuthorizationInput, PolicyDecision


@pytest.fixture
def audit_service(db_session):
    """Create audit service instance."""
    return PolicyAuditService(db_session)


@pytest.fixture
def sample_auth_input():
    """Create sample authorization input."""
    return AuthorizationInput(
        user={
            "id": "user-123",
            "role": "developer",
            "teams": ["team-1", "team-2"],
            "mfa_verified": True,
            "mfa_methods": ["totp"],
        },
        action="tool:invoke",
        tool={
            "id": "tool-456",
            "name": "test_tool",
            "sensitivity_level": "high",
        },
        context={
            "client_ip": "10.0.0.100",
            "request_id": "req-789",
        },
    )


@pytest.fixture
def sample_policy_decision():
    """Create sample policy decision."""
    return PolicyDecision(
        allow=True,
        reason="All policies passed",
        policies_evaluated=["rbac", "team_access", "sensitivity"],
        policy_results={
            "rbac": {"allow": True, "reason": "Developer role allowed"},
            "team_access": {"allow": True, "reason": "User in team"},
            "sensitivity": {"allow": True, "reason": "High sensitivity allowed"},
        },
    )


# ============================================================================
# POLICY DECISION LOGGING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_log_decision_allow(audit_service, sample_auth_input, sample_policy_decision):
    """Test logging an allowed policy decision."""
    log_entry = await audit_service.log_decision(
        auth_input=sample_auth_input,
        decision=sample_policy_decision,
        duration_ms=25.5,
        cache_hit=False,
    )

    assert log_entry is not None
    assert log_entry.result == PolicyDecisionResult.ALLOW
    assert log_entry.allow is True
    assert log_entry.user_id == "user-123"
    assert log_entry.user_role == "developer"
    assert log_entry.action == "tool:invoke"
    assert log_entry.tool_id == "tool-456"
    assert log_entry.tool_name == "test_tool"
    assert log_entry.sensitivity_level == "high"
    assert log_entry.evaluation_duration_ms == 25.5
    assert log_entry.cache_hit is False
    assert log_entry.client_ip == "10.0.0.100"
    assert log_entry.request_id == "req-789"
    assert log_entry.mfa_verified is True


@pytest.mark.asyncio
async def test_log_decision_deny(audit_service, sample_auth_input):
    """Test logging a denied policy decision."""
    denial_decision = PolicyDecision(
        allow=False,
        reason="Access denied: RBAC policy violation",
        policies_evaluated=["rbac"],
        policy_results={
            "rbac": {"allow": False, "reason": "Insufficient permissions"},
        },
    )

    log_entry = await audit_service.log_decision(
        auth_input=sample_auth_input,
        decision=denial_decision,
        duration_ms=15.2,
        cache_hit=True,
    )

    assert log_entry is not None
    assert log_entry.result == PolicyDecisionResult.DENY
    assert log_entry.allow is False
    assert log_entry.denial_reason == "Access denied: RBAC policy violation"
    assert log_entry.cache_hit is True


@pytest.mark.asyncio
async def test_log_decision_with_server_resource(audit_service, sample_policy_decision):
    """Test logging decision for server resource."""
    auth_input = AuthorizationInput(
        user={"id": "user-123", "role": "admin"},
        action="server:delete",
        server={"id": "srv-123", "name": "test-server"},
        context={},
    )

    log_entry = await audit_service.log_decision(
        auth_input=auth_input,
        decision=sample_policy_decision,
    )

    assert log_entry.action == "server:delete"
    assert log_entry.resource_type == "server"
    assert log_entry.server_name == "test-server"


# ============================================================================
# POLICY CHANGE LOGGING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_log_policy_change_create(audit_service):
    """Test logging a policy creation."""
    policy_content = """
    package sark.test
    default allow = false
    allow if {
        input.user.role == "admin"
    }
    """

    change_log = await audit_service.log_policy_change(
        policy_name="test_policy",
        change_type=PolicyChangeType.CREATED,
        changed_by_user_id="admin-123",
        policy_content=policy_content,
        change_reason="Initial policy creation",
        metadata={"tags": ["test", "initial"]},
    )

    assert change_log is not None
    assert change_log.policy_name == "test_policy"
    assert change_log.policy_version == 1
    assert change_log.change_type == PolicyChangeType.CREATED
    assert change_log.changed_by_user_id == "admin-123"
    assert change_log.policy_content == policy_content
    assert change_log.policy_hash is not None
    assert change_log.change_reason == "Initial policy creation"


@pytest.mark.asyncio
async def test_log_policy_change_update(audit_service):
    """Test logging a policy update with version increment."""
    # Create initial version
    initial_content = "package sark.test\ndefault allow = false"
    await audit_service.log_policy_change(
        policy_name="test_policy_v2",
        change_type=PolicyChangeType.CREATED,
        changed_by_user_id="admin-123",
        policy_content=initial_content,
    )

    # Update policy
    updated_content = "package sark.test\ndefault allow = true"
    update_log = await audit_service.log_policy_change(
        policy_name="test_policy_v2",
        change_type=PolicyChangeType.UPDATED,
        changed_by_user_id="admin-456",
        policy_content=updated_content,
        previous_content=initial_content,
        change_reason="Enable access by default",
    )

    assert update_log.policy_version == 2
    assert update_log.change_type == PolicyChangeType.UPDATED
    assert update_log.policy_diff is not None
    assert "allow = true" in update_log.policy_diff


@pytest.mark.asyncio
async def test_log_policy_change_with_approval(audit_service):
    """Test logging policy change with approval metadata."""
    change_log = await audit_service.log_policy_change(
        policy_name="critical_policy",
        change_type=PolicyChangeType.UPDATED,
        changed_by_user_id="dev-123",
        policy_content="package sark.critical\nallow = true",
        change_reason="Security update",
        metadata={
            "approver_user_id": "manager-456",
            "approval_id": "apr-789",
            "breaking_change": True,
        },
    )

    assert change_log.approver_user_id == "manager-456"
    assert change_log.breaking_change is True


# ============================================================================
# QUERY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_decision_logs_with_filters(
    audit_service, sample_auth_input, sample_policy_decision
):
    """Test querying decision logs with filters."""
    # Create multiple log entries
    await audit_service.log_decision(sample_auth_input, sample_policy_decision)

    # Create a denial
    denial_input = sample_auth_input.model_copy()
    denial_input.user["id"] = "user-456"
    denial_decision = PolicyDecision(allow=False, reason="Denied")
    await audit_service.log_decision(denial_input, denial_decision)

    # Query all
    all_logs = await audit_service.get_decision_logs(limit=100)
    assert len(all_logs) >= 2

    # Query by user
    user_logs = await audit_service.get_decision_logs(user_id="user-123", limit=100)
    assert len(user_logs) >= 1
    assert all(log.user_id == "user-123" for log in user_logs)

    # Query by result
    denied_logs = await audit_service.get_decision_logs(
        result=PolicyDecisionResult.DENY, limit=100
    )
    assert len(denied_logs) >= 1
    assert all(log.result == PolicyDecisionResult.DENY for log in denied_logs)


@pytest.mark.asyncio
async def test_get_decision_logs_time_range(
    audit_service, sample_auth_input, sample_policy_decision
):
    """Test querying decision logs with time range."""
    now = datetime.now(UTC)
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=1)

    # Create log entry
    await audit_service.log_decision(sample_auth_input, sample_policy_decision)

    # Query within range
    logs = await audit_service.get_decision_logs(
        start_time=start_time, end_time=end_time, limit=100
    )
    assert len(logs) >= 1

    # Query outside range
    old_start = now - timedelta(days=10)
    old_end = now - timedelta(days=9)
    old_logs = await audit_service.get_decision_logs(
        start_time=old_start, end_time=old_end, limit=100
    )
    assert len(old_logs) == 0


@pytest.mark.asyncio
async def test_get_policy_changes(audit_service):
    """Test querying policy change logs."""
    # Create changes
    await audit_service.log_policy_change(
        policy_name="test_policy_query",
        change_type=PolicyChangeType.CREATED,
        changed_by_user_id="admin-123",
    )

    await audit_service.log_policy_change(
        policy_name="test_policy_query",
        change_type=PolicyChangeType.UPDATED,
        changed_by_user_id="admin-456",
    )

    # Query all changes for policy
    changes = await audit_service.get_policy_changes(policy_name="test_policy_query")
    assert len(changes) == 2
    assert changes[0].policy_version == 2  # Most recent first
    assert changes[1].policy_version == 1


# ============================================================================
# EXPORT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_export_decisions_csv(
    audit_service, sample_auth_input, sample_policy_decision
):
    """Test exporting decisions to CSV format."""
    # Create log entries
    await audit_service.log_decision(sample_auth_input, sample_policy_decision)

    csv_content = await audit_service.export_decisions_csv(
        start_time=datetime.now(UTC) - timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=1),
    )

    assert csv_content is not None
    assert "timestamp" in csv_content
    assert "result" in csv_content
    assert "user-123" in csv_content
    assert "tool:invoke" in csv_content
    assert "allow" in csv_content.lower()


@pytest.mark.asyncio
async def test_export_decisions_json(
    audit_service, sample_auth_input, sample_policy_decision
):
    """Test exporting decisions to JSON format."""
    import json

    # Create log entries
    await audit_service.log_decision(sample_auth_input, sample_policy_decision)

    json_content = await audit_service.export_decisions_json(
        start_time=datetime.now(UTC) - timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=1),
    )

    assert json_content is not None
    data = json.loads(json_content)
    assert "decisions" in data
    assert "count" in data
    assert len(data["decisions"]) >= 1

    decision = data["decisions"][0]
    assert decision["user_id"] == "user-123"
    assert decision["action"] == "tool:invoke"
    assert decision["allow"] is True


# ============================================================================
# ANALYTICS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_decision_analytics(
    audit_service, sample_auth_input, sample_policy_decision
):
    """Test getting decision analytics."""
    # Create multiple log entries
    for i in range(10):
        decision = (
            sample_policy_decision if i % 2 == 0 else PolicyDecision(allow=False, reason="Denied")
        )
        cache_hit = i % 3 == 0

        await audit_service.log_decision(
            sample_auth_input,
            decision,
            duration_ms=20 + i,
            cache_hit=cache_hit,
        )

    # Get analytics
    analytics = await audit_service.get_decision_analytics(
        start_time=datetime.now(UTC) - timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=1),
    )

    assert analytics is not None
    assert "summary" in analytics
    assert analytics["summary"]["total_evaluations"] >= 10
    assert analytics["summary"]["total_allows"] >= 5
    assert analytics["summary"]["total_denies"] >= 5
    assert "cache_performance" in analytics
    assert "latency" in analytics
    assert analytics["latency"]["avg_ms"] > 0


@pytest.mark.asyncio
async def test_get_decision_analytics_grouped(
    audit_service, sample_auth_input, sample_policy_decision
):
    """Test getting analytics grouped by dimensions."""
    # Create entries with different actions
    for action in ["tool:invoke", "server:register", "tool:invoke"]:
        auth_input = sample_auth_input.model_copy()
        auth_input.action = action
        await audit_service.log_decision(auth_input, sample_policy_decision)

    analytics = await audit_service.get_decision_analytics(
        start_time=datetime.now(UTC) - timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=1),
        group_by=["action"],
    )

    assert "grouped" in analytics
    assert "action" in analytics["grouped"]
    assert "tool:invoke" in analytics["grouped"]["action"]
    assert analytics["grouped"]["action"]["tool:invoke"]["total"] >= 2


@pytest.mark.asyncio
async def test_get_top_denial_reasons(
    audit_service, sample_auth_input
):
    """Test getting top denial reasons."""
    # Create denials with different reasons
    reasons = [
        "RBAC policy violation",
        "Team access denied",
        "RBAC policy violation",
        "Sensitivity level too high",
        "RBAC policy violation",
    ]

    for reason in reasons:
        decision = PolicyDecision(allow=False, reason=reason)
        await audit_service.log_decision(sample_auth_input, decision)

    # Get top denial reasons
    top_reasons = await audit_service.get_top_denial_reasons(
        start_time=datetime.now(UTC) - timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=1),
        limit=5,
    )

    assert len(top_reasons) > 0
    # RBAC should be top reason
    assert top_reasons[0]["reason"] == "RBAC policy violation"
    assert top_reasons[0]["count"] == 3


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_log_decision_with_minimal_data(audit_service):
    """Test logging decision with minimal required data."""
    auth_input = AuthorizationInput(
        user={"id": "user-minimal"},
        action="test:action",
        context={},
    )
    decision = PolicyDecision(allow=True, reason="Test")

    log_entry = await audit_service.log_decision(auth_input, decision)

    assert log_entry is not None
    assert log_entry.user_id == "user-minimal"
    assert log_entry.action == "test:action"
    assert log_entry.tool_id is None
    assert log_entry.server_id is None
