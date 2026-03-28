"""Unit tests for Gateway audit service."""

from datetime import datetime
import time
from unittest.mock import AsyncMock, patch
import uuid

import pytest

from sark.models.gateway import GatewayAuditEvent
from sark.services.audit.gateway_audit import log_gateway_event


@pytest.fixture
def sample_gateway_event():
    """Create a sample Gateway audit event."""
    return GatewayAuditEvent(
        event_type="tool_invoke",
        user_id="user_123",
        agent_id=None,
        server_name="postgres-mcp",
        tool_name="execute_query",
        decision="allow",
        reason="User has required permissions",
        timestamp=int(time.time()),
        gateway_request_id="req_abc123",
        metadata={"database": "production", "query_type": "SELECT"},
    )


@pytest.fixture
def sample_a2a_event():
    """Create a sample A2A communication audit event."""
    return GatewayAuditEvent(
        event_type="a2a_communication",
        user_id=None,
        agent_id="agent_worker_001",
        server_name=None,
        tool_name=None,
        decision="allow",
        reason="Agent has execute capability",
        timestamp=int(time.time()),
        gateway_request_id="req_a2a_xyz789",
        metadata={"capability": "execute", "target_agent": "agent_service_002"},
    )


def make_mock_get_db(mock_session):
    """Create an async generator that yields the mock session."""

    async def mock_get_db():
        yield mock_session

    return mock_get_db


@pytest.mark.asyncio
async def test_log_gateway_event_success(sample_gateway_event):
    """Test successful Gateway event logging."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        audit_id = await log_gateway_event(sample_gateway_event)

        assert audit_id is not None
        assert isinstance(audit_id, str)
        uuid.UUID(audit_id)

        assert mock_session.execute.called
        assert mock_session.commit.called


@pytest.mark.asyncio
async def test_log_gateway_event_deny_decision(sample_gateway_event):
    """Test logging of denied authorization."""
    sample_gateway_event.decision = "deny"
    sample_gateway_event.reason = "User lacks required permissions"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        audit_id = await log_gateway_event(sample_gateway_event)

        assert audit_id is not None
        assert mock_session.execute.called

        call_args = mock_session.execute.call_args
        assert call_args is not None
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert params["decision"] == "deny"


@pytest.mark.asyncio
async def test_log_a2a_event(sample_a2a_event):
    """Test logging of A2A communication event."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        audit_id = await log_gateway_event(sample_a2a_event)

        assert audit_id is not None
        assert mock_session.execute.called

        call_args = mock_session.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert params["agent_id"] == "agent_worker_001"
        assert params["user_id"] is None


@pytest.mark.asyncio
async def test_log_gateway_event_with_metadata(sample_gateway_event):
    """Test that metadata is properly stored."""
    sample_gateway_event.metadata = {
        "ip_address": "192.168.1.100",
        "user_agent": "SARK-Client/1.0",
        "request_duration_ms": 45,
    }

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        audit_id = await log_gateway_event(sample_gateway_event)

        assert audit_id is not None

        call_args = mock_session.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert params["metadata"] == sample_gateway_event.metadata


@pytest.mark.asyncio
async def test_log_gateway_event_database_error(sample_gateway_event):
    """Test handling of database errors."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database connection failed")

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        with pytest.raises(Exception, match="Database connection failed"):
            await log_gateway_event(sample_gateway_event)


@pytest.mark.asyncio
async def test_log_gateway_event_triggers_siem_forwarding(sample_gateway_event):
    """Test that SIEM forwarding is triggered."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        with patch("sark.services.audit.gateway_audit.asyncio.create_task") as mock_create_task:
            with patch(
                "sark.services.siem.gateway_forwarder.forward_gateway_event"
            ) as mock_forward:
                await log_gateway_event(sample_gateway_event)

                assert mock_create_task.called or mock_forward.called


@pytest.mark.asyncio
async def test_log_gateway_event_with_missing_optional_fields():
    """Test logging with minimal required fields."""
    minimal_event = GatewayAuditEvent(
        event_type="discovery",
        user_id="user_456",
        agent_id=None,
        server_name=None,
        tool_name=None,
        decision="allow",
        reason="Discovery allowed for authenticated user",
        timestamp=int(time.time()),
        gateway_request_id="req_minimal_123",
        metadata={},
    )

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        audit_id = await log_gateway_event(minimal_event)

        assert audit_id is not None
        assert mock_session.execute.called

        call_args = mock_session.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert params["server_name"] is None
        assert params["tool_name"] is None


@pytest.mark.asyncio
async def test_timestamp_conversion(sample_gateway_event):
    """Test that Unix timestamp is properly converted to datetime."""
    unix_timestamp = 1700000000
    sample_gateway_event.timestamp = unix_timestamp

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("sark.services.audit.gateway_audit.get_db", make_mock_get_db(mock_session)):
        await log_gateway_event(sample_gateway_event)

        call_args = mock_session.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert isinstance(params["timestamp"], datetime)
        assert params["timestamp"] == datetime.fromtimestamp(unix_timestamp)
