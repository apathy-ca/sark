"""Gateway Latency Testing - Detailed P50/P95/P99 Analysis."""

import pytest
import time
import statistics

pytestmark = pytest.mark.performance


async def test_tool_invocation_latency_distribution(app_client, mock_user_token):
    """Measure P50, P95, P99 latencies for tool invocations."""

    latencies = []
    iterations = 1000

    for _ in range(iterations):
        start = time.perf_counter()

        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test-tool"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        assert response.status_code == 200

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"\nTool Invocation Latency:")
    print(f"  P50: {p50:.2f}ms")
    print(f"  P95: {p95:.2f}ms")
    print(f"  P99: {p99:.2f}ms")

    assert p95 < 100.0  # P95 target


async def test_cold_start_vs_warm_cache(app_client, mock_user_token):
    """Test cold start vs warm cache performance."""

    # Cold start - first request
    start = time.perf_counter()
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "cache-test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )
    cold_start = (time.perf_counter() - start) * 1000

    # Warm cache - same request
    start = time.perf_counter()
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "cache-test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )
    warm_cache = (time.perf_counter() - start) * 1000

    print(f"\nCold Start: {cold_start:.2f}ms")
    print(f"Warm Cache: {warm_cache:.2f}ms")
    print(f"Improvement: {((cold_start - warm_cache) / cold_start * 100):.1f}%")

    assert response1.status_code == 200
    assert response2.status_code == 200
