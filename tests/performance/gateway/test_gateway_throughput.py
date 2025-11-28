"""Gateway Throughput Testing."""

import pytest
import asyncio
import time

pytestmark = pytest.mark.performance


async def test_requests_per_second_measurement(app_client, mock_user_token):
    """Measure requests/second for various tool types."""

    total_requests = 1000
    start_time = time.perf_counter()

    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": f"tool-{i % 10}",
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(total_requests)
    ]

    responses = await asyncio.gather(*tasks)
    duration = time.perf_counter() - start_time

    # Calculate throughput
    throughput = total_requests / duration

    print(f"\nThroughput: {throughput:.2f} req/s")
    print(f"Duration: {duration:.2f}s")

    # All should succeed
    assert all(r.status_code == 200 for r in responses)
    assert throughput > 100  # Minimum acceptable throughput


async def test_concurrent_connections_10(app_client, mock_user_token):
    """Test 10 concurrent client connections."""
    await _test_concurrent_connections(app_client, mock_user_token, 10)


async def test_concurrent_connections_100(app_client, mock_user_token):
    """Test 100 concurrent client connections."""
    await _test_concurrent_connections(app_client, mock_user_token, 100)


async def test_concurrent_connections_1000(app_client, mock_user_token):
    """Test 1000 concurrent client connections."""
    await _test_concurrent_connections(app_client, mock_user_token, 1000)


async def _test_concurrent_connections(app_client, token, concurrent):
    """Helper to test concurrent connections."""
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        for _ in range(concurrent)
    ]

    start = time.perf_counter()
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.perf_counter() - start

    successful = sum(
        1 for r in responses if not isinstance(r, Exception) and r.status_code == 200
    )

    print(f"\nConcurrent: {concurrent}")
    print(f"Successful: {successful}")
    print(f"Duration: {duration:.2f}s")
    print(f"Success rate: {(successful/concurrent)*100:.2f}%")

    assert successful >= concurrent * 0.95  # 95% success rate
