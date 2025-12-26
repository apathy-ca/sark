"""Resource Usage Testing - Memory, CPU, Connection Pools."""

import asyncio
import os

import psutil
import pytest

pytestmark = pytest.mark.performance


async def test_memory_usage_under_load(app_client, mock_user_token):
    """Monitor memory usage under load."""

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Generate load
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": f"tool-{i}"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(1000)
    ]

    await asyncio.gather(*tasks)

    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory

    print("\nMemory Usage:")
    print(f"  Initial: {initial_memory:.2f} MB")
    print(f"  Final: {final_memory:.2f} MB")
    print(f"  Increase: {memory_increase:.2f} MB")

    # Should not increase significantly (< 100MB for 1000 requests)
    assert memory_increase < 100


async def test_memory_leak_detection(app_client, mock_user_token):
    """Test for memory leaks in long-running operations."""

    process = psutil.Process(os.getpid())

    # Baseline
    await asyncio.sleep(1)
    baseline = process.memory_info().rss / 1024 / 1024

    # Multiple iterations
    for iteration in range(5):
        tasks = [
            app_client.post(
                "/api/v1/gateway/authorize",
                json={"action": "gateway:tool:invoke", "tool_name": "test"},
                headers={"Authorization": f"Bearer {mock_user_token}"},
            )
            for _ in range(100)
        ]
        await asyncio.gather(*tasks)

        current = process.memory_info().rss / 1024 / 1024
        increase = current - baseline

        print(f"Iteration {iteration+1}: {current:.2f} MB (+{increase:.2f} MB)")

        # Memory should stabilize, not grow linearly
        if iteration > 2:
            assert increase < 50  # Max 50MB growth after warmup
