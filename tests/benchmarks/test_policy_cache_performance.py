"""Policy Cache Performance Benchmarks.

Tests cache performance to ensure <5ms cache hits and overall <50ms p95 latency.
"""

import pytest
import time
import statistics
from unittest.mock import AsyncMock, MagicMock, patch

from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import OPAClient, AuthorizationInput


@pytest.fixture
def redis_mock():
    """Create mock Redis client for benchmarking."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    redis.scan_iter = AsyncMock(return_value=iter([]))
    return redis


@pytest.fixture
def policy_cache(redis_mock):
    """Create PolicyCache with mock Redis."""
    return PolicyCache(redis_client=redis_mock, ttl_seconds=300, enabled=True)


# ============================================================================
# CACHE HIT PERFORMANCE BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_cache_hit_latency(policy_cache, redis_mock):
    """Benchmark: Cache hit latency should be <5ms."""
    import json

    # Setup cached decision
    decision = {"allow": True, "reason": "Test"}
    redis_mock.get.return_value = json.dumps(decision)

    latencies = []

    # Run 1000 cache hits
    for i in range(1000):
        start = time.perf_counter()
        result = await policy_cache.get(
            user_id=f"user-{i % 100}",
            action="tool:invoke",
            resource="tool:test",
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        assert result is not None

    # Calculate statistics
    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
    max_latency = max(latencies)

    print("\n" + "=" * 60)
    print("CACHE HIT LATENCY BENCHMARK")
    print("=" * 60)
    print(f"Iterations: 1000")
    print(f"Average:    {avg_latency:.2f}ms")
    print(f"P50:        {p50_latency:.2f}ms")
    print(f"P95:        {p95_latency:.2f}ms")
    print(f"P99:        {p99_latency:.2f}ms")
    print(f"Max:        {max_latency:.2f}ms")
    print("=" * 60)

    # Assert performance targets
    assert p95_latency < 5.0, f"P95 latency {p95_latency:.2f}ms exceeds 5ms target"
    assert avg_latency < 3.0, f"Average latency {avg_latency:.2f}ms exceeds 3ms target"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_cache_miss_latency(policy_cache, redis_mock):
    """Benchmark: Cache miss latency (Redis GET only)."""
    redis_mock.get.return_value = None

    latencies = []

    # Run 1000 cache misses
    for i in range(1000):
        start = time.perf_counter()
        result = await policy_cache.get(
            user_id=f"user-{i}",
            action="tool:invoke",
            resource="tool:test",
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        assert result is None

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("CACHE MISS LATENCY BENCHMARK")
    print("=" * 60)
    print(f"Iterations: 1000")
    print(f"Average:    {avg_latency:.2f}ms")
    print(f"P95:        {p95_latency:.2f}ms")
    print("=" * 60)

    assert p95_latency < 5.0, f"P95 latency {p95_latency:.2f}ms exceeds 5ms target"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_cache_set_latency(policy_cache, redis_mock):
    """Benchmark: Cache set latency."""
    decision = {"allow": True, "reason": "Test"}

    latencies = []

    # Run 1000 cache sets
    for i in range(1000):
        start = time.perf_counter()
        await policy_cache.set(
            user_id=f"user-{i}",
            action="tool:invoke",
            resource="tool:test",
            decision=decision,
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("CACHE SET LATENCY BENCHMARK")
    print("=" * 60)
    print(f"Iterations: 1000")
    print(f"Average:    {avg_latency:.2f}ms")
    print(f"P95:        {p95_latency:.2f}ms")
    print("=" * 60)

    assert p95_latency < 2.0, f"P95 latency {p95_latency:.2f}ms exceeds 2ms target"


# ============================================================================
# CACHE KEY GENERATION PERFORMANCE
# ============================================================================


@pytest.mark.benchmark
def test_cache_key_generation_performance(policy_cache):
    """Benchmark: Cache key generation should be very fast."""
    import hashlib
    import json

    context = {
        "timestamp": 1234567890,
        "ip": "192.168.1.1",
        "nested": {"key": "value"},
    }

    latencies = []

    # Run 10000 key generations
    for i in range(10000):
        start = time.perf_counter()
        key = policy_cache._generate_cache_key(
            user_id=f"user-{i % 100}",
            action="tool:invoke",
            resource="tool:test",
            context=context,
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        assert key is not None

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("CACHE KEY GENERATION BENCHMARK")
    print("=" * 60)
    print(f"Iterations: 10000")
    print(f"Average:    {avg_latency:.4f}ms")
    print(f"P95:        {p95_latency:.4f}ms")
    print("=" * 60)

    assert p95_latency < 0.1, f"P95 latency {p95_latency:.4f}ms exceeds 0.1ms target"


# ============================================================================
# OPA CLIENT WITH CACHE BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_opa_client_cache_hit_performance(mock_post, redis_mock):
    """Benchmark: OPA client with cache hit performance."""
    import json

    cache = PolicyCache(redis_client=redis_mock, enabled=True)
    opa_client = OPAClient(cache=cache)

    # Setup cached decision
    cached_decision = {
        "allow": True,
        "reason": "Cached decision",
        "filtered_parameters": None,
        "audit_id": None,
    }
    redis_mock.get.return_value = json.dumps(cached_decision)

    latencies = []

    # Run 1000 evaluations (all cache hits)
    for i in range(1000):
        auth_input = AuthorizationInput(
            user={"id": f"user-{i % 100}", "role": "developer"},
            action="tool:invoke",
            tool={"name": "test-tool", "sensitivity_level": "medium"},
            context={"timestamp": 0},
        )

        start = time.perf_counter()
        decision = await opa_client.evaluate_policy(auth_input)
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        assert decision.allow is True

    # Should not have called OPA
    mock_post.assert_not_called()

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]
    p99_latency = statistics.quantiles(latencies, n=100)[98]

    print("\n" + "=" * 60)
    print("OPA CLIENT CACHE HIT PERFORMANCE")
    print("=" * 60)
    print(f"Iterations: 1000")
    print(f"Average:    {avg_latency:.2f}ms")
    print(f"P50:        {p50_latency:.2f}ms")
    print(f"P95:        {p95_latency:.2f}ms")
    print(f"P99:        {p99_latency:.2f}ms")
    print("=" * 60)

    assert p95_latency < 5.0, f"P95 latency {p95_latency:.2f}ms exceeds 5ms target"


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_opa_client_cache_miss_performance(mock_post, redis_mock):
    """Benchmark: OPA client with cache miss (OPA call) performance."""
    cache = PolicyCache(redis_client=redis_mock, enabled=True)
    opa_client = OPAClient(cache=cache)

    # Setup OPA response (simulated 30ms latency)
    async def mock_opa_call(*args, **kwargs):
        await asyncio.sleep(0.030)  # Simulate 30ms OPA call
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "result": {
                "allow": True,
                "audit_reason": "Test",
            }
        }
        response.raise_for_status = MagicMock()
        return response

    mock_post.side_effect = mock_opa_call
    redis_mock.get.return_value = None  # Cache miss

    latencies = []

    import asyncio

    # Run 100 evaluations (all cache misses)
    for i in range(100):
        auth_input = AuthorizationInput(
            user={"id": f"user-{i}", "role": "developer"},
            action="tool:invoke",
            tool={"name": "test-tool", "sensitivity_level": "medium"},
            context={"timestamp": 0},
        )

        start = time.perf_counter()
        decision = await opa_client.evaluate_policy(auth_input)
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        assert decision.allow is True

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("OPA CLIENT CACHE MISS PERFORMANCE (with 30ms OPA)")
    print("=" * 60)
    print(f"Iterations: 100")
    print(f"Average:    {avg_latency:.2f}ms")
    print(f"P50:        {p50_latency:.2f}ms")
    print(f"P95:        {p95_latency:.2f}ms")
    print("=" * 60)

    # With 30ms OPA + overhead, should still be under 50ms
    assert p95_latency < 50.0, f"P95 latency {p95_latency:.2f}ms exceeds 50ms target"


# ============================================================================
# MIXED WORKLOAD BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_mixed_cache_hit_miss_workload(mock_post, redis_mock):
    """Benchmark: Mixed cache hit/miss workload (80% hit rate)."""
    import json
    import asyncio

    cache = PolicyCache(redis_client=redis_mock, enabled=True)
    opa_client = OPAClient(cache=cache)

    # Setup OPA response
    async def mock_opa_call(*args, **kwargs):
        await asyncio.sleep(0.030)  # 30ms OPA call
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "result": {"allow": True, "audit_reason": "Test"}
        }
        response.raise_for_status = MagicMock()
        return response

    mock_post.side_effect = mock_opa_call

    # Cached decision
    cached_decision = {
        "allow": True,
        "reason": "Cached",
        "filtered_parameters": None,
        "audit_id": None,
    }

    latencies_hit = []
    latencies_miss = []

    # Run 500 evaluations (80% hit, 20% miss)
    for i in range(500):
        # 80% cache hit
        if i % 5 != 0:
            redis_mock.get.return_value = json.dumps(cached_decision)
        else:
            redis_mock.get.return_value = None

        auth_input = AuthorizationInput(
            user={"id": f"user-{i % 100}", "role": "developer"},
            action="tool:invoke",
            tool={"name": "test-tool", "sensitivity_level": "medium"},
            context={"timestamp": 0},
        )

        start = time.perf_counter()
        decision = await opa_client.evaluate_policy(auth_input)
        end = time.perf_counter()

        latency_ms = (end - start) * 1000

        if i % 5 != 0:
            latencies_hit.append(latency_ms)
        else:
            latencies_miss.append(latency_ms)

    avg_latency_hit = statistics.mean(latencies_hit)
    p95_latency_hit = statistics.quantiles(latencies_hit, n=20)[18]

    avg_latency_miss = statistics.mean(latencies_miss)
    p95_latency_miss = statistics.quantiles(latencies_miss, n=20)[18]

    overall_latencies = latencies_hit + latencies_miss
    avg_overall = statistics.mean(overall_latencies)
    p95_overall = statistics.quantiles(overall_latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("MIXED WORKLOAD (80% HIT, 20% MISS)")
    print("=" * 60)
    print(f"Total iterations: 500")
    print(f"Hit iterations:   {len(latencies_hit)}")
    print(f"Miss iterations:  {len(latencies_miss)}")
    print("")
    print("CACHE HITS:")
    print(f"  Average: {avg_latency_hit:.2f}ms")
    print(f"  P95:     {p95_latency_hit:.2f}ms")
    print("")
    print("CACHE MISSES:")
    print(f"  Average: {avg_latency_miss:.2f}ms")
    print(f"  P95:     {p95_latency_miss:.2f}ms")
    print("")
    print("OVERALL:")
    print(f"  Average: {avg_overall:.2f}ms")
    print(f"  P95:     {p95_overall:.2f}ms")
    print("=" * 60)

    # Verify metrics
    metrics = opa_client.get_cache_metrics()
    print(f"\nCache Metrics:")
    print(f"  Hit Rate:  {metrics['hit_rate']:.1f}%")
    print(f"  Hits:      {metrics['hits']}")
    print(f"  Misses:    {metrics['misses']}")

    # Assert targets
    assert p95_latency_hit < 5.0, f"Cache hit P95 {p95_latency_hit:.2f}ms exceeds 5ms"
    assert p95_overall < 15.0, f"Overall P95 {p95_overall:.2f}ms exceeds 15ms target"
    assert metrics["hit_rate"] >= 75.0, f"Hit rate {metrics['hit_rate']:.1f}% below 75%"


# ============================================================================
# THROUGHPUT BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_cache_hit_throughput(policy_cache, redis_mock):
    """Benchmark: Cache hit throughput (requests/second)."""
    import json
    import asyncio

    decision = {"allow": True, "reason": "Test"}
    redis_mock.get.return_value = json.dumps(decision)

    start_time = time.perf_counter()
    iterations = 10000

    # Run concurrent cache hits
    tasks = []
    for i in range(iterations):
        task = policy_cache.get(
            user_id=f"user-{i % 100}",
            action="tool:invoke",
            resource="tool:test",
        )
        tasks.append(task)

    await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    duration = end_time - start_time

    throughput = iterations / duration

    print("\n" + "=" * 60)
    print("CACHE HIT THROUGHPUT BENCHMARK")
    print("=" * 60)
    print(f"Iterations:  {iterations}")
    print(f"Duration:    {duration:.2f}s")
    print(f"Throughput:  {throughput:.0f} req/s")
    print("=" * 60)

    # Should achieve >1000 req/s
    assert throughput > 1000, f"Throughput {throughput:.0f} req/s below 1000 req/s target"
