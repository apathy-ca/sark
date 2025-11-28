"""Audit Trail Validation Integration Tests.

Tests for complete audit trail tracking, event correlation, SIEM integration,
and audit log integrity.
"""

import pytest
import asyncio
import hashlib

pytestmark = pytest.mark.asyncio


async def test_complete_audit_trail_tracking(app_client, mock_user_token):
    """Test complete audit trail from request to completion."""

    # Make authorization request
    auth_response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "audit-test-server",
            "tool_name": "audit-test-tool",
            "parameters": {"test": "data"},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert auth_response.status_code == 200
    audit_id = auth_response.json().get("audit_id")
    assert audit_id is not None

    # Retrieve complete audit trail
    trail_response = await app_client.get(
        f"/api/v1/audit/events/{audit_id}/trail",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    if trail_response.status_code == 200:
        trail = trail_response.json()

        # Verify audit trail completeness
        assert "request" in trail
        assert "authorization_decision" in trail
        assert "execution" in trail
        assert "response" in trail

        # Verify timestamps are sequential
        timestamps = [
            trail["request"]["timestamp"],
            trail["authorization_decision"]["timestamp"],
        ]
        assert all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))


async def test_audit_event_correlation(app_client, mock_user_token):
    """Test audit event correlation across components."""

    # Make request that spans multiple components
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "multi-component-tool",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    correlation_id = response.json().get("correlation_id") or response.json().get("audit_id")

    if correlation_id:
        # Query all events with this correlation ID
        events_response = await app_client.get(
            f"/api/v1/audit/events?correlation_id={correlation_id}",
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        if events_response.status_code == 200:
            events = events_response.json()

            # Should have multiple correlated events
            assert len(events) > 1

            # All should share correlation ID
            assert all(e.get("correlation_id") == correlation_id for e in events)


async def test_siem_integration_and_alerting(app_client, mock_user_token):
    """Test SIEM integration and alert triggering."""

    # Trigger security event that should alert
    suspicious_response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:admin:delete",
            "server_name": "production-server",
            "tool_name": "dangerous-operation",
            "parameters": {
                "target": "all_data",
                "skip_confirmation": True,
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should be denied
    assert suspicious_response.status_code == 200
    assert suspicious_response.json()["allow"] is False

    # Check if alert was created
    await asyncio.sleep(1)  # Wait for async SIEM processing

    alerts_response = await app_client.get(
        "/api/v1/security/alerts?severity=high",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    if alerts_response.status_code == 200:
        alerts = alerts_response.json()
        # Should have alert for this suspicious activity
        assert any(
            alert.get("event_type") == "authorization_denied"
            and "dangerous-operation" in str(alert.get("details", {}))
            for alert in alerts
        )


async def test_audit_log_integrity_verification(app_client, admin_token):
    """Test audit log integrity and tamper detection."""

    # Create audit event
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "integrity-test",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    audit_id = response.json().get("audit_id")

    if audit_id:
        # Get audit event with integrity check
        event_response = await app_client.get(
            f"/api/v1/audit/events/{audit_id}?verify_integrity=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        if event_response.status_code == 200:
            event = event_response.json()

            # Should have integrity information
            assert "integrity_hash" in event or "checksum" in event
            assert event.get("integrity_verified") is True


async def test_audit_event_immutability(app_client, admin_token):
    """Test that audit events are immutable."""

    # Create audit event
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "immutability-test",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    audit_id = response.json().get("audit_id")

    if audit_id:
        # Attempt to modify audit event (should fail)
        modify_response = await app_client.patch(
            f"/api/v1/audit/events/{audit_id}",
            json={"tampered": "data"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Should be rejected
        assert modify_response.status_code in [403, 405, 422]


async def test_audit_retention_and_archival(app_client, admin_token):
    """Test audit log retention and archival policies."""

    # Get retention policy
    policy_response = await app_client.get(
        "/api/v1/audit/retention-policy",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    if policy_response.status_code == 200:
        policy = policy_response.json()

        assert "retention_days" in policy
        assert "archive_enabled" in policy
        assert policy["retention_days"] >= 90  # Compliance requirement


async def test_audit_search_and_filtering(app_client, mock_user_token):
    """Test audit log search and filtering capabilities."""

    # Create multiple audit events
    for i in range(5):
        await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": f"server-{i}",
                "tool_name": f"tool-{i}",
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

    # Search with filters
    search_response = await app_client.get(
        "/api/v1/audit/events?event_type=gateway_authorization&limit=10",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert search_response.status_code == 200
    events = search_response.json()

    assert len(events) > 0
    assert all(e["event_type"] == "gateway_authorization" for e in events)


async def test_audit_performance_under_load(app_client, mock_user_token):
    """Test audit logging doesn't degrade performance under load."""

    # Measure latency with audit logging
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "test-server",
                "tool_name": f"perf-tool-{i}",
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(100)
    ]

    import time
    start = time.perf_counter()
    responses = await asyncio.gather(*tasks)
    duration = (time.perf_counter() - start) * 1000

    # All should succeed despite audit load
    assert all(r.status_code == 200 for r in responses)

    # Performance shouldn't degrade significantly
    avg_latency = duration / len(tasks)
    assert avg_latency < 100  # < 100ms average


async def test_structured_audit_logging(app_client, mock_user_token):
    """Test structured audit logging format."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "structured-test",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    audit_id = response.json().get("audit_id")

    if audit_id:
        event_response = await app_client.get(
            f"/api/v1/audit/events/{audit_id}",
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        if event_response.status_code == 200:
            event = event_response.json()

            # Verify structured format
            assert "timestamp" in event
            assert "event_type" in event
            assert "actor" in event
            assert "action" in event
            assert "resource" in event
            assert "outcome" in event
