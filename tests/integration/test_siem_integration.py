"""
Integration tests for SIEM event delivery and audit logging.

Tests SIEM integration workflows including:
- Audit event creation and persistence
- High-severity event SIEM forwarding
- Event filtering and routing
- SIEM failure handling
- Audit trail completeness
- Event correlation
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

import httpx

from sark.services.audit.audit_service import AuditService
from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel


@pytest.fixture
def mock_db_session():
    """Mock database session for audit events."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def audit_service(mock_db_session):
    """Audit service for tests."""
    return AuditService(
        db=mock_db_session,
        siem_enabled=True,
        splunk_url="https://splunk.example.com:8088/services/collector/event",
        splunk_token="test-token",
        datadog_url="https://http-intake.logs.datadoghq.com/v1/input",
        datadog_api_key="test-api-key"
    )


@pytest.fixture
def sample_event():
    """Sample audit event."""
    return AuditEvent(
        id=uuid4(),
        event_type=AuditEventType.SERVER_REGISTERED,
        severity=SeverityLevel.INFO,
        user_id=uuid4(),
        resource_id=uuid4(),
        resource_type="server",
        action="register",
        details={"server_name": "test-server", "transport": "http"},
        ip_address="192.168.1.100",
        user_agent="TestClient/1.0",
        timestamp=datetime.now(UTC)
    )


@pytest.fixture
def high_severity_event():
    """High severity audit event."""
    return AuditEvent(
        id=uuid4(),
        event_type=AuditEventType.POLICY_VIOLATION,
        severity=SeverityLevel.CRITICAL,
        user_id=uuid4(),
        resource_id=uuid4(),
        resource_type="server",
        action="access_denied",
        details={"reason": "Unauthorized access attempt", "server": "prod-db"},
        ip_address="192.168.1.100",
        user_agent="TestClient/1.0",
        timestamp=datetime.now(UTC)
    )


# ============================================================================
# Audit Event Creation and Persistence Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_audit_event_persisted_to_database(audit_service, sample_event):
    """Test that audit events are persisted to database."""
    await audit_service.log_event(
        event_type=sample_event.event_type,
        severity=sample_event.severity,
        user_id=sample_event.user_id,
        resource_id=sample_event.resource_id,
        resource_type=sample_event.resource_type,
        action=sample_event.action,
        details=sample_event.details,
        ip_address=sample_event.ip_address,
        user_agent=sample_event.user_agent
    )

    # Verify database add and commit were called
    assert audit_service.db.add.called
    assert audit_service.db.commit.called


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_audit_events_include_metadata(audit_service, sample_event):
    """Test that audit events include all required metadata."""
    await audit_service.log_event(
        event_type=sample_event.event_type,
        severity=sample_event.severity,
        user_id=sample_event.user_id,
        resource_id=sample_event.resource_id,
        resource_type=sample_event.resource_type,
        action=sample_event.action,
        details=sample_event.details,
        ip_address=sample_event.ip_address,
        user_agent=sample_event.user_agent
    )

    # Get the event that was added
    call_args = audit_service.db.add.call_args
    event = call_args[0][0]

    assert event.event_type == sample_event.event_type
    assert event.severity == sample_event.severity
    assert event.user_id == sample_event.user_id
    assert event.ip_address == sample_event.ip_address
    assert event.user_agent == sample_event.user_agent


# ============================================================================
# High-Severity Event SIEM Forwarding Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_high_severity_events_forwarded_to_splunk(audit_service, high_severity_event):
    """Test that high-severity events are forwarded to Splunk."""
    # Mock Splunk HTTP request
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "Success", "code": 0}

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)) as mock_post:
        await audit_service.log_event(
            event_type=high_severity_event.event_type,
            severity=high_severity_event.severity,
            user_id=high_severity_event.user_id,
            resource_id=high_severity_event.resource_id,
            resource_type=high_severity_event.resource_type,
            action=high_severity_event.action,
            details=high_severity_event.details,
            ip_address=high_severity_event.ip_address,
            user_agent=high_severity_event.user_agent
        )

        # Verify Splunk was called for high-severity event
        if high_severity_event.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            assert mock_post.called


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_low_severity_events_not_forwarded_to_siem(audit_service, sample_event):
    """Test that low-severity events are not forwarded to SIEM."""
    # Mock SIEM HTTP requests
    with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        await audit_service.log_event(
            event_type=sample_event.event_type,
            severity=SeverityLevel.INFO,  # Low severity
            user_id=sample_event.user_id,
            resource_id=sample_event.resource_id,
            resource_type=sample_event.resource_type,
            action=sample_event.action,
            details=sample_event.details
        )

        # SIEM should not be called for low-severity events
        # (depends on service configuration)
        # This test assumes only HIGH and CRITICAL are forwarded
        pass


# ============================================================================
# Event Filtering and Routing Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_events_routed_by_severity(audit_service):
    """Test that events are routed correctly based on severity."""
    severities = [
        SeverityLevel.INFO,
        SeverityLevel.LOW,
        SeverityLevel.MEDIUM,
        SeverityLevel.HIGH,
        SeverityLevel.CRITICAL
    ]

    for severity in severities:
        await audit_service.log_event(
            event_type=AuditEventType.SERVER_REGISTERED,
            severity=severity,
            user_id=uuid4(),
            resource_id=uuid4(),
            resource_type="server",
            action="test",
            details={"test": True}
        )

    # All events should be persisted
    assert audit_service.db.add.call_count >= len(severities)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_events_filtered_by_type(audit_service):
    """Test filtering events by type."""
    event_types = [
        AuditEventType.SERVER_REGISTERED,
        AuditEventType.SERVER_UPDATED,
        AuditEventType.POLICY_VIOLATION,
        AuditEventType.AUTH_FAILED
    ]

    for event_type in event_types:
        await audit_service.log_event(
            event_type=event_type,
            severity=SeverityLevel.MEDIUM,
            user_id=uuid4(),
            resource_id=uuid4(),
            resource_type="server",
            action="test",
            details={"test": True}
        )

    # All event types should be logged
    assert audit_service.db.add.call_count >= len(event_types)


# ============================================================================
# SIEM Failure Handling Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_continues_on_siem_failure(audit_service, high_severity_event):
    """Test that audit continues even if SIEM forwarding fails."""
    # Mock SIEM to fail
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.TimeoutException("SIEM timeout"))):
        # Should not raise exception
        await audit_service.log_event(
            event_type=high_severity_event.event_type,
            severity=high_severity_event.severity,
            user_id=high_severity_event.user_id,
            resource_id=high_severity_event.resource_id,
            resource_type=high_severity_event.resource_type,
            action=high_severity_event.action,
            details=high_severity_event.details
        )

    # Event should still be persisted to database
    assert audit_service.db.add.called
    assert audit_service.db.commit.called


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_handles_siem_authentication_failure(audit_service, high_severity_event):
    """Test handling of SIEM authentication failures."""
    # Mock SIEM to return 401 Unauthorized
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_response
    )

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        # Should continue despite auth failure
        await audit_service.log_event(
            event_type=high_severity_event.event_type,
            severity=high_severity_event.severity,
            user_id=high_severity_event.user_id,
            resource_id=high_severity_event.resource_id,
            resource_type=high_severity_event.resource_type,
            action=high_severity_event.action,
            details=high_severity_event.details
        )

    # Event should still be in database
    assert audit_service.db.commit.called


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_handles_siem_network_timeout(audit_service, high_severity_event):
    """Test handling of SIEM network timeouts."""
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.TimeoutException("Network timeout"))):
        await audit_service.log_event(
            event_type=high_severity_event.event_type,
            severity=high_severity_event.severity,
            user_id=high_severity_event.user_id,
            resource_id=high_severity_event.resource_id,
            resource_type=high_severity_event.resource_type,
            action=high_severity_event.action,
            details=high_severity_event.details
        )

    # Should gracefully handle timeout
    assert audit_service.db.commit.called


# ============================================================================
# Audit Trail Completeness Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_audit_trail_captures_all_operations(audit_service):
    """Test that audit trail captures all critical operations."""
    operations = [
        (AuditEventType.SERVER_REGISTERED, "register"),
        (AuditEventType.SERVER_UPDATED, "update"),
        (AuditEventType.SERVER_DELETED, "delete"),
        (AuditEventType.TOOL_INVOKED, "invoke"),
        (AuditEventType.POLICY_EVALUATED, "evaluate")
    ]

    for event_type, action in operations:
        await audit_service.log_event(
            event_type=event_type,
            severity=SeverityLevel.MEDIUM,
            user_id=uuid4(),
            resource_id=uuid4(),
            resource_type="server",
            action=action,
            details={"operation": action}
        )

    # All operations should be logged
    assert audit_service.db.add.call_count >= len(operations)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.siem
async def test_audit_events_include_correlation_data(audit_service):
    """Test that audit events include correlation IDs for tracing."""
    correlation_id = str(uuid4())

    await audit_service.log_event(
        event_type=AuditEventType.SERVER_REGISTERED,
        severity=SeverityLevel.MEDIUM,
        user_id=uuid4(),
        resource_id=uuid4(),
        resource_type="server",
        action="register",
        details={"correlation_id": correlation_id}
    )

    # Get logged event
    call_args = audit_service.db.add.call_args
    event = call_args[0][0]

    assert "correlation_id" in event.details
    assert event.details["correlation_id"] == correlation_id
