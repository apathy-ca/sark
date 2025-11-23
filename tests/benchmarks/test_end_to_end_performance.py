"""End-to-End Performance Benchmarks.

Tests complete authorization workflow including:
- Tool sensitivity detection
- Policy cache lookup
- OPA policy evaluation
- Overall p95 latency <50ms
"""

import statistics
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.discovery.tool_registry import ToolRegistry
from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import AuthorizationInput, OPAClient


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=0)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()
    redis_mock.scan_iter = AsyncMock(return_value=iter([]))
    return redis_mock


@pytest.fixture
def tool_registry(db_session):
    """Create ToolRegistry instance."""
    return ToolRegistry(db_session)


@pytest.fixture
def opa_client(mock_redis):
    """Create OPA client with cache."""
    cache = PolicyCache(redis_client=mock_redis, enabled=True)
    return OPAClient(cache=cache, cache_enabled=True)


# ============================================================================
# END-TO-END LATENCY BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_end_to_end_tool_invocation_latency(
    mock_post, opa_client, tool_registry, mock_redis
):
    """Benchmark: Complete tool invocation flow should be <50ms p95.

    Flow:
    1. Detect tool sensitivity (if not cached)
    2. Build authorization input
    3. Check policy cache
    4. Evaluate OPA policy (on cache miss)
    5. Return authorization decision
    """
    import asyncio
    import json

    from sark.models.mcp_server import SensitivityLevel

    # Setup OPA response (simulated 30ms latency)
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

    # Test tools with various sensitivity levels
    test_tools = [
        ("read_data", "Reads user data", SensitivityLevel.LOW),
        ("update_config", "Updates configuration", SensitivityLevel.MEDIUM),
        ("delete_user", "Deletes user account", SensitivityLevel.HIGH),
        ("process_payment", "Processes payment", SensitivityLevel.CRITICAL),
    ]

    latencies_cache_miss = []
    latencies_cache_hit = []

    # Run 100 iterations (25 per tool)
    for iteration in range(25):
        for tool_name, tool_desc, _expected_level in test_tools:
            # === CACHE MISS FLOW ===
            mock_redis.get.return_value = None

            start = time.perf_counter()

            # Step 1: Detect sensitivity
            sensitivity = await tool_registry.detect_sensitivity(
                tool_name=tool_name,
                tool_description=tool_desc,
            )

            # Step 2: Build auth input
            auth_input = AuthorizationInput(
                user={"id": f"user-{iteration}", "role": "developer"},
                action="tool:invoke",
                tool={
                    "name": tool_name,
                    "sensitivity_level": sensitivity.value,
                },
                context={"timestamp": iteration},
            )

            # Step 3-4: Evaluate policy (cache miss -> OPA call)
            decision = await opa_client.evaluate_policy(auth_input)

            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies_cache_miss.append(latency_ms)

            assert decision.allow is not None

            # === CACHE HIT FLOW ===
            cached_decision = {
                "allow": True,
                "reason": "Cached",
                "filtered_parameters": None,
                "audit_id": None,
            }
            mock_redis.get.return_value = json.dumps(cached_decision)

            start = time.perf_counter()

            # Sensitivity already detected, reuse
            auth_input = AuthorizationInput(
                user={"id": f"user-{iteration}", "role": "developer"},
                action="tool:invoke",
                tool={
                    "name": tool_name,
                    "sensitivity_level": sensitivity.value,
                },
                context={"timestamp": iteration},
            )

            # Evaluate policy (cache hit - no OPA call)
            decision = await opa_client.evaluate_policy(auth_input)

            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies_cache_hit.append(latency_ms)

    # Calculate statistics for cache miss
    avg_miss = statistics.mean(latencies_cache_miss)
    p50_miss = statistics.median(latencies_cache_miss)
    p95_miss = statistics.quantiles(latencies_cache_miss, n=20)[18]
    p99_miss = statistics.quantiles(latencies_cache_miss, n=100)[98]
    max_miss = max(latencies_cache_miss)

    # Calculate statistics for cache hit
    avg_hit = statistics.mean(latencies_cache_hit)
    p50_hit = statistics.median(latencies_cache_hit)
    p95_hit = statistics.quantiles(latencies_cache_hit, n=20)[18]
    p99_hit = statistics.quantiles(latencies_cache_hit, n=100)[98]
    max_hit = max(latencies_cache_hit)

    print("\n" + "=" * 60)
    print("END-TO-END TOOL INVOCATION PERFORMANCE")
    print("=" * 60)
    print(f"Total iterations: {len(latencies_cache_miss) + len(latencies_cache_hit)}")
    print("")
    print("CACHE MISS (sensitivity detection + OPA evaluation):")
    print(f"  Average: {avg_miss:.2f}ms")
    print(f"  P50:     {p50_miss:.2f}ms")
    print(f"  P95:     {p95_miss:.2f}ms")
    print(f"  P99:     {p99_miss:.2f}ms")
    print(f"  Max:     {max_miss:.2f}ms")
    print("")
    print("CACHE HIT (sensitivity detection + cache lookup):")
    print(f"  Average: {avg_hit:.2f}ms")
    print(f"  P50:     {p50_hit:.2f}ms")
    print(f"  P95:     {p95_hit:.2f}ms")
    print(f"  P99:     {p99_hit:.2f}ms")
    print(f"  Max:     {max_hit:.2f}ms")
    print("=" * 60)

    # Assert performance targets
    assert p95_miss < 50.0, f"Cache miss P95 {p95_miss:.2f}ms exceeds 50ms target"
    assert p95_hit < 10.0, f"Cache hit P95 {p95_hit:.2f}ms exceeds 10ms target"


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_end_to_end_mixed_workload(
    mock_post, opa_client, tool_registry, mock_redis
):
    """Benchmark: Mixed workload (80% cache hit) should have good overall latency.

    Simulates realistic production scenario with 80% cache hit rate.
    """
    import asyncio
    import json

    # Setup OPA response
    async def mock_opa_call(*args, **kwargs):
        await asyncio.sleep(0.030)  # 30ms
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "result": {"allow": True, "audit_reason": "Test"}
        }
        response.raise_for_status = MagicMock()
        return response

    mock_post.side_effect = mock_opa_call

    cached_decision = {
        "allow": True,
        "reason": "Cached",
        "filtered_parameters": None,
        "audit_id": None,
    }

    latencies = []

    # Run 500 requests (80% hit, 20% miss)
    for i in range(500):
        # 80% cache hit
        if i % 5 != 0:
            mock_redis.get.return_value = json.dumps(cached_decision)
        else:
            mock_redis.get.return_value = None

        start = time.perf_counter()

        # Detect sensitivity
        sensitivity = await tool_registry.detect_sensitivity(
            tool_name=f"tool-{i % 10}",
            tool_description="Test tool operation",
        )

        # Evaluate policy
        auth_input = AuthorizationInput(
            user={"id": f"user-{i % 100}", "role": "developer"},
            action="tool:invoke",
            tool={"name": f"tool-{i % 10}", "sensitivity_level": sensitivity.value},
            context={"timestamp": i},
        )

        decision = await opa_client.evaluate_policy(auth_input)

        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        assert decision.allow is not None

    # Calculate statistics
    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]
    p99_latency = statistics.quantiles(latencies, n=100)[98]
    max_latency = max(latencies)

    print("\n" + "=" * 60)
    print("END-TO-END MIXED WORKLOAD (80% hit rate)")
    print("=" * 60)
    print(f"Iterations: {len(latencies)}")
    print(f"Average:    {avg_latency:.2f}ms")
    print(f"P50:        {p50_latency:.2f}ms")
    print(f"P95:        {p95_latency:.2f}ms")
    print(f"P99:        {p99_latency:.2f}ms")
    print(f"Max:        {max_latency:.2f}ms")
    print("=" * 60)

    # Get cache metrics
    metrics = opa_client.get_cache_metrics()
    print("\nCache Metrics:")
    print(f"  Hit Rate: {metrics['hit_rate']:.1f}%")
    print(f"  Hits:     {metrics['hits']}")
    print(f"  Misses:   {metrics['misses']}")

    # Assert performance targets
    assert p95_latency < 15.0, f"P95 latency {p95_latency:.2f}ms exceeds 15ms target"
    assert metrics["hit_rate"] >= 75.0, f"Hit rate {metrics['hit_rate']:.1f}% below 75%"


# ============================================================================
# THROUGHPUT BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_end_to_end_throughput(mock_post, opa_client, tool_registry, mock_redis):
    """Benchmark: End-to-end throughput (requests/second).

    Tests how many complete authorization flows can be processed per second.
    """
    import asyncio
    import json

    # Setup fast OPA mock
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    # All cache hits for maximum throughput
    cached_decision = {
        "allow": True,
        "reason": "Cached",
        "filtered_parameters": None,
        "audit_id": None,
    }
    mock_redis.get.return_value = json.dumps(cached_decision)

    iterations = 1000
    start_time = time.perf_counter()

    # Run concurrent requests
    async def process_request(i):
        sensitivity = await tool_registry.detect_sensitivity(
            tool_name=f"tool-{i % 10}",
            tool_description="Test tool",
        )
        auth_input = AuthorizationInput(
            user={"id": f"user-{i % 100}", "role": "developer"},
            action="tool:invoke",
            tool={"name": f"tool-{i % 10}", "sensitivity_level": sensitivity.value},
            context={"timestamp": i},
        )
        return await opa_client.evaluate_policy(auth_input)

    tasks = [process_request(i) for i in range(iterations)]
    await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    duration = end_time - start_time
    throughput = iterations / duration

    print("\n" + "=" * 60)
    print("END-TO-END THROUGHPUT BENCHMARK")
    print("=" * 60)
    print(f"Iterations:  {iterations}")
    print(f"Duration:    {duration:.2f}s")
    print(f"Throughput:  {throughput:.0f} req/s")
    print("=" * 60)

    # Should achieve >500 req/s end-to-end
    assert throughput > 500, f"Throughput {throughput:.0f} req/s below 500 req/s target"


# ============================================================================
# CONCURRENT USER BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_concurrent_users_performance(
    mock_post, opa_client, tool_registry, mock_redis
):
    """Benchmark: Performance under concurrent user load.

    Simulates 100 concurrent users making authorization requests.
    """
    import asyncio
    import json

    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    cached_decision = {
        "allow": True,
        "reason": "Cached",
        "filtered_parameters": None,
        "audit_id": None,
    }

    latencies = []

    async def simulate_user(user_id, requests_per_user=10):
        """Simulate a single user making multiple requests."""
        user_latencies = []

        for i in range(requests_per_user):
            # 70% cache hit for this simulation
            if i >= 3:
                mock_redis.get.return_value = json.dumps(cached_decision)
            else:
                mock_redis.get.return_value = None

            start = time.perf_counter()

            sensitivity = await tool_registry.detect_sensitivity(
                tool_name=f"user-{user_id}-tool-{i}",
                tool_description="User-specific tool",
            )

            auth_input = AuthorizationInput(
                user={"id": f"user-{user_id}", "role": "developer"},
                action="tool:invoke",
                tool={
                    "name": f"user-{user_id}-tool-{i}",
                    "sensitivity_level": sensitivity.value,
                },
                context={"request": i},
            )

            await opa_client.evaluate_policy(auth_input)

            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            user_latencies.append(latency_ms)

        return user_latencies

    # Simulate 100 concurrent users
    user_count = 100
    start_time = time.perf_counter()

    tasks = [simulate_user(user_id) for user_id in range(user_count)]
    results = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    total_duration = end_time - start_time

    # Flatten latencies
    for user_latencies in results:
        latencies.extend(user_latencies)

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]
    p99_latency = statistics.quantiles(latencies, n=100)[98]

    total_requests = len(latencies)
    throughput = total_requests / total_duration

    print("\n" + "=" * 60)
    print(f"CONCURRENT USERS BENCHMARK ({user_count} users)")
    print("=" * 60)
    print(f"Total requests:  {total_requests}")
    print(f"Total duration:  {total_duration:.2f}s")
    print(f"Throughput:      {throughput:.0f} req/s")
    print("")
    print("LATENCY:")
    print(f"  Average: {avg_latency:.2f}ms")
    print(f"  P50:     {p50_latency:.2f}ms")
    print(f"  P95:     {p95_latency:.2f}ms")
    print(f"  P99:     {p99_latency:.2f}ms")
    print("=" * 60)

    # Assert targets
    assert p95_latency < 20.0, f"P95 latency {p95_latency:.2f}ms exceeds 20ms target"
    assert throughput > 300, f"Throughput {throughput:.0f} req/s below 300 req/s target"


# ============================================================================
# SCALABILITY BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_sensitivity_detection_scalability(tool_registry):
    """Benchmark: Sensitivity detection scales linearly with tool count."""
    import asyncio

    # Test with increasing tool counts
    tool_counts = [100, 500, 1000, 5000]
    results = []

    for count in tool_counts:
        tools = [
            (f"tool-{i}", f"Tool {i} description with various operations")
            for i in range(count)
        ]

        start = time.perf_counter()

        # Detect all concurrently
        tasks = [
            tool_registry.detect_sensitivity(name, desc) for name, desc in tools
        ]
        await asyncio.gather(*tasks)

        end = time.perf_counter()
        duration = end - start
        throughput = count / duration

        results.append((count, duration, throughput))

    print("\n" + "=" * 60)
    print("SENSITIVITY DETECTION SCALABILITY")
    print("=" * 60)
    print(f"{'Tools':<10} {'Duration':<12} {'Throughput':<15}")
    print("-" * 60)
    for count, duration, throughput in results:
        print(f"{count:<10} {duration:>8.2f}s    {throughput:>10.0f} tools/s")
    print("=" * 60)

    # Verify scalability - throughput should remain consistent
    throughputs = [t for _, _, t in results]
    # Allow 50% variance in throughput across scales
    min_throughput = min(throughputs)
    max_throughput = max(throughputs)
    variance = (max_throughput - min_throughput) / min_throughput

    assert variance < 0.5, f"Throughput variance {variance:.1%} exceeds 50%"


# ============================================================================
# STRESS TESTS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_sustained_load(mock_post, opa_client, tool_registry, mock_redis):
    """Benchmark: Performance under sustained load over time.

    Tests that performance remains consistent over 10,000 requests.
    """
    import json

    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    cached_decision = {
        "allow": True,
        "reason": "Cached",
        "filtered_parameters": None,
        "audit_id": None,
    }

    # Track latencies in batches
    batch_size = 1000
    total_requests = 10000
    batches = []

    for batch_num in range(total_requests // batch_size):
        batch_latencies = []

        for i in range(batch_size):
            request_num = batch_num * batch_size + i

            # 80% cache hit
            if request_num % 5 != 0:
                mock_redis.get.return_value = json.dumps(cached_decision)
            else:
                mock_redis.get.return_value = None

            start = time.perf_counter()

            sensitivity = await tool_registry.detect_sensitivity(
                tool_name=f"tool-{request_num % 100}",
                tool_description="Test tool",
            )

            auth_input = AuthorizationInput(
                user={"id": f"user-{request_num % 200}", "role": "developer"},
                action="tool:invoke",
                tool={
                    "name": f"tool-{request_num % 100}",
                    "sensitivity_level": sensitivity.value,
                },
                context={"request": request_num},
            )

            await opa_client.evaluate_policy(auth_input)

            end = time.perf_counter()
            latency_ms = (end - start) * 1000
            batch_latencies.append(latency_ms)

        p95 = statistics.quantiles(batch_latencies, n=20)[18]
        avg = statistics.mean(batch_latencies)
        batches.append((batch_num + 1, avg, p95))

    print("\n" + "=" * 60)
    print(f"SUSTAINED LOAD TEST ({total_requests} requests)")
    print("=" * 60)
    print(f"{'Batch':<10} {'Avg (ms)':<12} {'P95 (ms)':<12}")
    print("-" * 60)
    for batch_num, avg, p95 in batches:
        print(f"{batch_num:<10} {avg:>8.2f}    {p95:>8.2f}")
    print("=" * 60)

    # Verify performance stability - P95 should remain consistent
    p95_values = [p95 for _, _, p95 in batches]
    max_p95 = max(p95_values)
    min_p95 = min(p95_values)

    # All P95s should be within 50% of each other
    variation = (max_p95 - min_p95) / min_p95

    assert variation < 0.5, f"P95 variation {variation:.1%} exceeds 50%"
    assert max_p95 < 20.0, f"Max P95 {max_p95:.2f}ms exceeds 20ms target"
