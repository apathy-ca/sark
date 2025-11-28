"""Stress Testing - Extreme Load and Recovery."""

import pytest
import asyncio
import time

pytestmark = pytest.mark.performance


async def test_extreme_load_behavior(app_client, mock_user_token):
    """Test behavior under extreme load."""

    # Extreme load - 5000 concurrent requests
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": f"stress-{i}"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(5000)
    ]

    start = time.perf_counter()
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.perf_counter() - start

    successful = sum(
        1 for r in responses if not isinstance(r, Exception) and r.status_code == 200
    )
    failed = len(responses) - successful

    print(f"\nExtreme Load Results:")
    print(f"  Total: {len(responses)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Success Rate: {(successful/len(responses))*100:.2f}%")

    # At least 80% should succeed under extreme load
    assert successful >= len(responses) * 0.80


async def test_graceful_degradation(app_client, mock_user_token):
    """Test graceful degradation under load."""

    # Gradually increase load
    for batch_size in [100, 500, 1000, 2000]:
        tasks = [
            app_client.post(
                "/api/v1/gateway/authorize",
                json={"action": "gateway:tool:invoke", "tool_name": "test"},
                headers={"Authorization": f"Bearer {mock_user_token}"},
            )
            for _ in range(batch_size)
        ]

        start = time.perf_counter()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.perf_counter() - start

        successful = sum(
            1 for r in responses if not isinstance(r, Exception) and r.status_code == 200
        )
        success_rate = (successful / batch_size) * 100

        print(f"\nBatch size {batch_size}:")
        print(f"  Success rate: {success_rate:.2f}%")
        print(f"  Duration: {duration:.2f}s")

        # Should maintain reasonable success rate
        assert success_rate >= 70


async def test_recovery_after_resource_exhaustion(app_client, mock_user_token):
    """Test recovery after resource exhaustion."""

    # Cause resource exhaustion
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for _ in range(2000)
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    # Wait for recovery
    await asyncio.sleep(5)

    # System should recover and accept new requests
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code in [200, 429]  # Either works or rate limited
