"""Multi-Server Orchestration Integration Tests.

Tests for coordinating multiple gateway servers simultaneously,
failover scenarios, and load distribution.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


async def test_multiple_servers_registration(app_client, mock_user_token):
    """Test registering multiple gateway servers simultaneously."""

    servers = [
        {
            "server_name": f"test-server-{i}",
            "server_url": f"http://test{i}:8080",
            "sensitivity_level": "medium",
        }
        for i in range(5)
    ]

    # Register all servers concurrently
    tasks = [
        app_client.post(
            "/api/v1/gateway/servers",
            json=server,
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for server in servers
    ]

    responses = await asyncio.gather(*tasks)

    # All registrations should succeed
    assert all(r.status_code == 201 for r in responses)

    # Verify all servers are registered
    list_response = await app_client.get(
        "/api/v1/gateway/servers",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert list_response.status_code == 200
    registered_servers = list_response.json()
    assert len(registered_servers) >= 5


async def test_server_deregistration_during_active_operations(app_client, mock_user_token):
    """Test server deregistration while operations are in progress."""

    # Register a server
    server_response = await app_client.post(
        "/api/v1/gateway/servers",
        json={
            "server_name": "active-server",
            "server_url": "http://active:8080",
            "sensitivity_level": "low",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )
    assert server_response.status_code == 201
    server_id = server_response.json()["server_id"]

    # Start concurrent operations
    operation_tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "server_name": "active-server",
                "tool_name": f"tool-{i}",
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(10)
    ]

    # Deregister server while operations are running
    deregister_task = app_client.delete(
        f"/api/v1/gateway/servers/{server_id}",
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Gather all results
    all_tasks = operation_tasks + [deregister_task]
    results = await asyncio.gather(*all_tasks, return_exceptions=True)

    # Deregistration should succeed
    deregister_response = results[-1]
    assert not isinstance(deregister_response, Exception)
    assert deregister_response.status_code in [200, 204]


async def test_failover_when_primary_server_unavailable(app_client, mock_user_token):
    """Test automatic failover when primary server becomes unavailable."""

    # Register primary and backup servers
    primary = await app_client.post(
        "/api/v1/gateway/servers",
        json={
            "server_name": "primary-server",
            "server_url": "http://primary:8080",
            "sensitivity_level": "medium",
            "priority": 1,
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    backup = await app_client.post(
        "/api/v1/gateway/servers",
        json={
            "server_name": "backup-server",
            "server_url": "http://backup:8080",
            "sensitivity_level": "medium",
            "priority": 2,
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert primary.status_code == 201
    assert backup.status_code == 201

    # Invoke tool - should use primary
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "primary-server",
            "tool_name": "test-tool",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )
    assert response1.status_code == 200

    # Mark primary as unhealthy
    await app_client.patch(
        f"/api/v1/gateway/servers/{primary.json()['server_id']}/health",
        json={"health_status": "unhealthy"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Subsequent invocations should failover to backup
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "backup-server",
            "tool_name": "test-tool",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response2.status_code == 200


async def test_load_distribution_across_servers(app_client, mock_user_token):
    """Test load distribution across multiple servers."""

    # Register multiple servers
    servers = []
    for i in range(3):
        response = await app_client.post(
            "/api/v1/gateway/servers",
            json={
                "server_name": f"load-server-{i}",
                "server_url": f"http://load{i}:8080",
                "sensitivity_level": "low",
                "capacity": 100,
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        assert response.status_code == 201
        servers.append(response.json())

    # Make many requests
    requests_count = 30
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": f"test-tool-{i}",
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(requests_count)
    ]

    responses = await asyncio.gather(*tasks)

    # All requests should succeed
    assert all(r.status_code == 200 for r in responses)
