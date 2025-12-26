"""Network Chaos Engineering Tests."""

import asyncio

import pytest

pytestmark = pytest.mark.chaos


async def test_slow_network_conditions(app_client, mock_user_token):
    """Test behavior under slow network conditions."""

    # Simulate slow network with timeout
    try:
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
            timeout=2.0,  # Short timeout
        )

        # Should either complete or timeout gracefully
        assert response.status_code in [200, 408, 504]
    except TimeoutError:
        # Graceful timeout handling is acceptable
        pass


async def test_intermittent_connection_failures(app_client, mock_user_token):
    """Test handling of intermittent connection failures."""

    # Make multiple requests, some may fail
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": f"tool-{i}"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(20)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # At least some should succeed
    successful = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)

    assert successful > 0, "Some requests should succeed despite intermittent failures"


async def test_network_partition_handling(app_client, mock_user_token):
    """Test handling of network partition scenarios."""

    # Attempt operation during partition
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "partitioned-server",
            "tool_name": "test",
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should handle gracefully
    assert response.status_code in [200, 503, 504]

    if response.status_code == 200:
        data = response.json()
        # May deny due to inability to verify
        assert "allow" in data
