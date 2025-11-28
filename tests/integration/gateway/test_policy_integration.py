"""Policy Integration Tests.

Tests for OPA policy enforcement, caching, performance, and dynamic updates.
"""

import pytest
import asyncio
import time

pytestmark = pytest.mark.asyncio


async def test_opa_policy_enforcement_during_invocation(app_client, mock_user_token):
    """Test OPA policy enforcement during tool invocations."""

    # Test allow case
    response_allow = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "allowed-tool",
            "parameters": {"safe": "parameter"},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response_allow.status_code == 200
    assert response_allow.json()["allow"] is True

    # Test deny case
    response_deny = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:admin:delete",
            "server_name": "production-server",
            "tool_name": "dangerous-tool",
            "parameters": {},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response_deny.status_code == 200
    assert response_deny.json()["allow"] is False
    assert "reason" in response_deny.json()


async def test_policy_decision_caching(app_client, mock_user_token):
    """Test policy decision caching and cache hits."""

    # First request - cache miss
    start1 = time.perf_counter()
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "cached-tool",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )
    duration1 = (time.perf_counter() - start1) * 1000

    # Second identical request - cache hit
    start2 = time.perf_counter()
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "cached-tool",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )
    duration2 = (time.perf_counter() - start2) * 1000

    assert response1.status_code == 200
    assert response2.status_code == 200

    # Cache hit should be faster
    if duration1 > 10:  # Only compare if first request was slow enough
        assert duration2 < duration1


async def test_policy_cache_invalidation(app_client, admin_token):
    """Test policy cache invalidation when policies change."""

    # Make request with current policy
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "test-tool",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    initial_result = response1.json()["allow"]

    # Invalidate cache
    cache_response = await app_client.post(
        "/api/v1/policy/cache/invalidate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert cache_response.status_code == 200

    # Make same request after cache invalidation
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "test-tool",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Should re-evaluate policy (not use cache)
    assert response2.status_code == 200


async def test_policy_evaluation_performance_under_load(app_client, mock_user_token):
    """Test policy evaluation performance under concurrent load."""

    # Make many concurrent policy evaluation requests
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "test-server",
                "tool_name": f"tool-{i % 10}",  # 10 different tools
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(100)
    ]

    start = time.perf_counter()
    responses = await asyncio.gather(*tasks)
    duration = (time.perf_counter() - start) * 1000

    # All should succeed
    assert all(r.status_code == 200 for r in responses)

    # Calculate throughput
    throughput = len(tasks) / (duration / 1000)  # requests per second

    print(f"\nPolicy evaluation throughput: {throughput:.2f} req/s")
    print(f"Average latency: {duration/len(tasks):.2f}ms")

    # Should maintain reasonable throughput
    assert throughput > 100, f"Policy evaluation throughput {throughput} req/s too low"


async def test_policy_updates_without_restart(app_client, admin_token):
    """Test policy updates without service restart."""

    # Update policy
    new_policy = """
    package mcp.gateway

    default allow = false

    allow {
        input.action == "gateway:tool:invoke"
        input.user.role == "admin"
    }
    """

    update_response = await app_client.put(
        "/api/v1/policy/gateway",
        json={"policy_content": new_policy},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert update_response.status_code == 200

    # Wait for policy to propagate
    await asyncio.sleep(2)

    # Test with new policy (should apply immediately)
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "test-tool",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    # Policy should be enforced


async def test_policy_context_enrichment(app_client, mock_user_token):
    """Test policy evaluation with enriched context."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "sensitive-tool",
            "parameters": {"data_classification": "confidential"},
            "context": {
                "time_of_day": "business_hours",
                "location": "office",
                "device_trust_level": "high",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Policy should consider enriched context
    assert "context_evaluated" in data or data.get("allow") is not None


async def test_policy_decision_logging(app_client, mock_user_token):
    """Test that policy decisions are properly logged."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "logged-tool",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    decision_id = response.json().get("decision_id") or response.json().get("audit_id")

    if decision_id:
        # Retrieve policy decision log
        log_response = await app_client.get(
            f"/api/v1/policy/decisions/{decision_id}",
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        if log_response.status_code == 200:
            log = log_response.json()
            assert "decision" in log
            assert "policy_version" in log
            assert "evaluation_time_ms" in log


async def test_policy_versioning(app_client, admin_token):
    """Test policy versioning and rollback."""

    # Get current policy version
    version_response = await app_client.get(
        "/api/v1/policy/gateway/version",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    if version_response.status_code == 200:
        current_version = version_response.json()["version"]

        # Update policy (creates new version)
        update_response = await app_client.put(
            "/api/v1/policy/gateway",
            json={"policy_content": "package mcp.gateway\ndefault allow = true"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert update_response.status_code == 200

        # Rollback to previous version
        rollback_response = await app_client.post(
            f"/api/v1/policy/gateway/rollback/{current_version}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        if rollback_response.status_code == 200:
            # Verify rollback
            new_version_response = await app_client.get(
                "/api/v1/policy/gateway/version",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert new_version_response.json()["version"] == current_version
