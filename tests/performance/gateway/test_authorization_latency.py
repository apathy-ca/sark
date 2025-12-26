"""Gateway authorization latency tests."""

import asyncio
import statistics
import time

import pytest


@pytest.mark.performance
async def test_authorization_latency_p95(app_client, mock_user_token):
    """Test P95 authorization latency < 50ms."""

    latencies = []
    iterations = 1000

    for _ in range(iterations):
        start = time.perf_counter()

        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test-tool"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        latency = (time.perf_counter() - start) * 1000  # Convert to ms
        latencies.append(latency)

        assert response.status_code == 200

    # Calculate percentiles
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print("\nLatency Results (ms):")
    print(f"  P50: {p50:.2f}")
    print(f"  P95: {p95:.2f}")
    print(f"  P99: {p99:.2f}")

    # Assert performance targets
    assert p95 < 50.0, f"P95 latency {p95:.2f}ms exceeds 50ms target"


@pytest.mark.performance
async def test_concurrent_requests(app_client, mock_user_token):
    """Test authorization under concurrent load."""

    async def make_request():
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        return response.status_code

    # Run 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(status == 200 for status in results)


@pytest.mark.performance
async def test_sustained_load(app_client, mock_user_token):
    """Test sustained load handling (1000+ req/s)."""

    total_requests = 5000
    start_time = time.perf_counter()

    async def make_request():
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        return response.status_code == 200

    # Run requests in batches to simulate sustained load
    batch_size = 100
    batches = total_requests // batch_size

    success_count = 0
    for _ in range(batches):
        tasks = [make_request() for _ in range(batch_size)]
        results = await asyncio.gather(*tasks)
        success_count += sum(results)

    end_time = time.perf_counter()
    duration = end_time - start_time
    throughput = total_requests / duration

    print("\nSustained Load Results:")
    print(f"  Total Requests: {total_requests}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Throughput: {throughput:.2f} req/s")
    print(f"  Success Rate: {(success_count/total_requests)*100:.2f}%")

    # Assert throughput target
    assert throughput > 1000, f"Throughput {throughput:.2f} req/s below 1000 req/s target"
    assert success_count / total_requests > 0.99, "Success rate below 99%"


@pytest.mark.performance
async def test_spike_load(app_client, mock_user_token):
    """Test spike load handling (0→1000 req/s)."""

    # Baseline: small load
    baseline_tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for _ in range(10)
    ]
    baseline_results = await asyncio.gather(*baseline_tasks)
    assert all(r.status_code == 200 for r in baseline_results)

    # Spike: sudden large load
    spike_tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for _ in range(1000)
    ]

    start_time = time.perf_counter()
    spike_results = await asyncio.gather(*spike_tasks, return_exceptions=True)
    end_time = time.perf_counter()

    # Count successes
    success_count = sum(
        1 for r in spike_results if not isinstance(r, Exception) and r.status_code == 200
    )
    success_rate = success_count / len(spike_tasks)

    duration = end_time - start_time
    print("\nSpike Load Results:")
    print(f"  Spike Size: {len(spike_tasks)} requests")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Success Rate: {success_rate*100:.2f}%")

    # Should handle spike with >95% success rate
    assert success_rate > 0.95, f"Spike success rate {success_rate*100:.2f}% below 95%"


@pytest.mark.performance
async def test_cache_performance(app_client, mock_user_token):
    """Test policy cache performance under load."""

    # Prime cache with unique requests
    unique_requests = 100
    for i in range(unique_requests):
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": f"test-tool-{i}",
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        assert response.status_code == 200

    # Measure cache hit performance
    cache_hit_latencies = []
    iterations = 1000

    for i in range(iterations):
        start = time.perf_counter()

        # Use same tool to hit cache
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": f"test-tool-{i % unique_requests}",
            },
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )

        latency = (time.perf_counter() - start) * 1000
        cache_hit_latencies.append(latency)

        assert response.status_code == 200

    # Calculate statistics
    avg_latency = statistics.mean(cache_hit_latencies)
    p95_latency = sorted(cache_hit_latencies)[int(len(cache_hit_latencies) * 0.95)]

    print("\nCache Performance Results:")
    print(f"  Average Latency: {avg_latency:.2f}ms")
    print(f"  P95 Latency: {p95_latency:.2f}ms")

    # Cache hits should be very fast
    assert p95_latency < 10.0, f"Cache P95 latency {p95_latency:.2f}ms exceeds 10ms"
