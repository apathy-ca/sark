"""Resource Chaos Engineering Tests."""

import pytest
import asyncio

pytestmark = pytest.mark.chaos


async def test_disk_space_exhaustion(app_client, mock_user_token):
    """Test behavior when disk space is exhausted."""

    # Attempt operations that would write to disk
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "tool_name": "disk-intensive-tool",
            "parameters": {"output_size": "large"},
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should either succeed or gracefully handle disk full
    assert response.status_code in [200, 500, 503]

    if response.status_code == 500:
        error = response.json()
        assert "disk" in str(error).lower() or "space" in str(error).lower()


async def test_file_descriptor_exhaustion(app_client, mock_user_token):
    """Test file descriptor exhaustion handling."""

    # Make many concurrent requests (may exhaust file descriptors)
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": f"tool-{i}"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(500)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Most should succeed, some may fail gracefully
    successful = sum(
        1 for r in results if not isinstance(r, Exception) and r.status_code == 200
    )

    # At least 80% should succeed
    assert successful >= len(tasks) * 0.80


async def test_thread_pool_saturation(app_client, mock_user_token):
    """Test thread pool saturation handling."""

    # Launch many blocking operations
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": "blocking-tool",
                "parameters": {"duration": 1},
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for _ in range(200)
    ]

    start_times = [asyncio.get_event_loop().time() for _ in tasks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Should handle gracefully
    successful = sum(
        1 for r in results if not isinstance(r, Exception) and r.status_code in [200, 429]
    )

    assert successful >= len(tasks) * 0.70  # 70% success acceptable


async def test_memory_pressure_scenarios(app_client, mock_user_token):
    """Test behavior under memory pressure."""

    # Request operations with large payloads
    large_payload = {"data": "X" * (1024 * 1024)}  # 1MB payload

    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": "memory-intensive",
                "parameters": large_payload,
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for _ in range(50)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Should handle or reject large payloads
    handled = sum(
        1 for r in results
        if not isinstance(r, Exception) and r.status_code in [200, 413, 422]
    )

    assert handled >= len(tasks) * 0.80
