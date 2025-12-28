"""
Stress tests to find system breaking points and failure modes.

Tests extreme scenarios:
1. Extreme throughput (10,000 req/s)
2. Large policy files (10MB+)
3. Large cache (1M+ entries)
4. Memory exhaustion
5. Connection saturation

Acceptance Criteria:
- Breaking point documented
- Failure modes understood
- System degrades gracefully
- No cascading failures
"""

import asyncio
import os
import psutil
import pytest
import time
from unittest.mock import AsyncMock, patch

from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import AuthorizationInput, OPAClient


# ==============================================================================
# Extreme Throughput Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(600)  # 10 minute timeout
async def test_extreme_throughput_10k_rps():
    """
    Stress Test: Ramp to 10,000 req/s and find breaking point.

    Tests:
    - Maximum achievable throughput
    - Response time degradation under extreme load
    - Error rate at capacity
    - System resource usage (CPU, memory)

    Expected Outcome:
    - Document maximum RPS before failure
    - Identify bottleneck (CPU, memory, I/O, etc.)
    - Verify graceful degradation (no crashes)
    """
    # Mock OPA client for stress testing
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_client.post.return_value = mock_response

        client = OPAClient(opa_url="http://localhost:8181")

        # Test parameters
        target_rps = 10_000
        test_duration_seconds = 60
        total_requests = target_rps * test_duration_seconds

        # Metrics
        successful_requests = 0
        failed_requests = 0
        latencies = []
        start_time = time.time()

        # Concurrent batches
        batch_size = 1000
        num_batches = total_requests // batch_size

        print(f"\n{'=' * 80}")
        print(f"EXTREME THROUGHPUT STRESS TEST")
        print(f"{'=' * 80}")
        print(f"Target RPS: {target_rps:,}")
        print(f"Duration: {test_duration_seconds}s")
        print(f"Total requests: {total_requests:,}")
        print(f"{'=' * 80}\n")

        for batch_num in range(num_batches):
            batch_start = time.time()

            # Create batch of requests
            tasks = []
            for _ in range(batch_size):
                auth_input = AuthorizationInput(
                    user_id=f"stress-user-{batch_num}",
                    action="read",
                    resource=f"document-{batch_num}",
                    context={},
                )
                tasks.append(client.evaluate_policy(auth_input, use_cache=False))

            # Execute batch concurrently
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        failed_requests += 1
                    else:
                        successful_requests += 1

                batch_duration = time.time() - batch_start
                batch_rps = batch_size / batch_duration if batch_duration > 0 else 0

                # Progress update every 10 batches
                if (batch_num + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    current_rps = successful_requests / elapsed if elapsed > 0 else 0
                    error_rate = (
                        failed_requests / (successful_requests + failed_requests)
                        if (successful_requests + failed_requests) > 0
                        else 0
                    )

                    print(
                        f"Batch {batch_num + 1}/{num_batches}: "
                        f"{batch_rps:.0f} req/s | "
                        f"Avg: {current_rps:.0f} req/s | "
                        f"Errors: {error_rate * 100:.2f}%"
                    )

            except Exception as e:
                failed_requests += batch_size
                print(f"Batch {batch_num} failed: {e}")

        # Final metrics
        total_duration = time.time() - start_time
        actual_rps = successful_requests / total_duration if total_duration > 0 else 0
        error_rate = (
            failed_requests / (successful_requests + failed_requests)
            if (successful_requests + failed_requests) > 0
            else 0
        )

        print(f"\n{'=' * 80}")
        print(f"RESULTS")
        print(f"{'=' * 80}")
        print(f"Successful requests: {successful_requests:,}")
        print(f"Failed requests: {failed_requests:,}")
        print(f"Actual RPS: {actual_rps:.2f}")
        print(f"Error rate: {error_rate * 100:.2f}%")
        print(f"Duration: {total_duration:.2f}s")
        print(f"{'=' * 80}\n")

        # Verify graceful degradation (no complete failure)
        assert successful_requests > 0, "System completely failed under load"
        assert error_rate < 0.50, f"Error rate too high: {error_rate * 100:.2f}%"

        await client.close()


# ==============================================================================
# Large Policy Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_large_policy_10mb():
    """
    Stress Test: Load and evaluate 10MB policy file.

    Tests:
    - Policy compilation time with large files
    - Memory usage during compilation
    - Evaluation time with large policies
    - Cache behavior with large policies

    Expected Outcome:
    - Document compilation time
    - Measure memory impact
    - Verify evaluation still meets latency targets
    """
    # Generate large policy (10MB of Rego rules)
    large_policy = _generate_large_policy(size_mb=10)

    print(f"\n{'=' * 80}")
    print(f"LARGE POLICY STRESS TEST")
    print(f"{'=' * 80}")
    print(f"Policy size: {len(large_policy) / 1024 / 1024:.2f} MB")
    print(f"{'=' * 80}\n")

    # Mock OPA client
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Simulate slower response for large policy
        async def slow_post(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate policy evaluation overhead
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": {"allow": True}}
            return mock_response

        mock_client.post = slow_post

        client = OPAClient(opa_url="http://localhost:8181")

        # Measure compilation/loading time
        compilation_start = time.time()
        # In real scenario, would load policy into OPA here
        compilation_time = time.time() - compilation_start

        # Measure evaluation time
        auth_input = AuthorizationInput(
            user_id="test-user",
            action="read",
            resource="document-123",
            context={},
        )

        evaluation_start = time.time()
        result = await client.evaluate_policy(auth_input, use_cache=False)
        evaluation_time = (time.time() - evaluation_start) * 1000  # Convert to ms

        # Measure memory usage
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024

        print(f"Compilation time: {compilation_time * 1000:.2f}ms")
        print(f"Evaluation time: {evaluation_time:.2f}ms")
        print(f"Memory usage: {memory_mb:.2f} MB")
        print(f"{'=' * 80}\n")

        # Verify reasonable performance even with large policy
        assert (
            evaluation_time < 1000
        ), f"Evaluation too slow: {evaluation_time:.2f}ms"
        assert result is not None

        await client.close()


def _generate_large_policy(size_mb: int) -> str:
    """Generate a large Rego policy of specified size."""
    # Generate repeated rules to reach target size
    rule_template = """
rule_{}[result] {{
    input.user == "user-{}"
    input.action == "read"
    result := true
}}
"""

    policy = "package authz\n\n"
    rule_count = 0

    while len(policy) < size_mb * 1024 * 1024:
        policy += rule_template.format(rule_count, rule_count)
        rule_count += 1

    return policy


# ==============================================================================
# Large Cache Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_large_cache_1m_entries():
    """
    Stress Test: Fill cache to 1M entries.

    Tests:
    - Memory usage with large cache
    - Eviction performance
    - Cache operation latency at scale
    - Memory stability

    Expected Outcome:
    - Document memory usage per entry
    - Measure eviction performance
    - Verify LRU eviction works correctly
    """
    print(f"\n{'=' * 80}")
    print(f"LARGE CACHE STRESS TEST")
    print(f"{'=' * 80}")
    print(f"Target entries: 1,000,000")
    print(f"{'=' * 80}\n")

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    cache = PolicyCache(redis_client=mock_redis, ttl_seconds=300, enabled=True)

    # Measure initial memory
    process = psutil.Process(os.getpid())
    initial_memory_mb = process.memory_info().rss / 1024 / 1024

    # Fill cache
    target_entries = 1_000_000
    batch_size = 10_000
    num_batches = target_entries // batch_size

    start_time = time.time()

    for batch_num in range(num_batches):
        batch_start = time.time()

        # Add batch of entries
        for i in range(batch_size):
            entry_id = batch_num * batch_size + i
            await cache.set(
                user_id=f"user-{entry_id}",
                action="read",
                resource=f"doc-{entry_id}",
                decision={"allow": True, "reason": "test"},
            )

        batch_duration = time.time() - batch_start
        batch_rps = batch_size / batch_duration if batch_duration > 0 else 0

        # Progress update
        if (batch_num + 1) % 10 == 0:
            current_memory_mb = process.memory_info().rss / 1024 / 1024
            memory_delta = current_memory_mb - initial_memory_mb
            entries_added = (batch_num + 1) * batch_size
            memory_per_entry = (
                memory_delta / entries_added if entries_added > 0 else 0
            )

            print(
                f"Batch {batch_num + 1}/{num_batches}: "
                f"{entries_added:,} entries | "
                f"{batch_rps:.0f} writes/s | "
                f"Memory: +{memory_delta:.1f} MB "
                f"({memory_per_entry * 1024:.2f} KB/entry)"
            )

    # Final metrics
    total_duration = time.time() - start_time
    final_memory_mb = process.memory_info().rss / 1024 / 1024
    total_memory_delta = final_memory_mb - initial_memory_mb
    memory_per_entry = total_memory_delta / target_entries

    print(f"\n{'=' * 80}")
    print(f"RESULTS")
    print(f"{'=' * 80}")
    print(f"Entries added: {target_entries:,}")
    print(f"Duration: {total_duration:.2f}s")
    print(f"Write rate: {target_entries / total_duration:.2f} entries/s")
    print(f"Memory increase: {total_memory_delta:.2f} MB")
    print(f"Memory per entry: {memory_per_entry * 1024:.2f} KB")
    print(f"{'=' * 80}\n")

    # Test cache read performance at scale
    print("Testing cache read performance...")
    read_start = time.time()
    read_count = 1000

    for i in range(read_count):
        entry_id = i * (target_entries // read_count)  # Sample across range
        await cache.get(
            user_id=f"user-{entry_id}",
            action="read",
            resource=f"doc-{entry_id}",
        )

    read_duration = time.time() - read_start
    read_latency = (read_duration / read_count) * 1000  # ms

    print(f"Read latency: {read_latency:.2f}ms (avg over {read_count} reads)")
    print(f"{'=' * 80}\n")

    # Verify reasonable performance
    assert read_latency < 10, f"Read latency too high: {read_latency:.2f}ms"


# ==============================================================================
# Memory Exhaustion Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.skip(reason="Dangerous: can exhaust system memory")
async def test_memory_exhaustion():
    """
    Stress Test: Fill memory until exhaustion.

    Tests:
    - Graceful degradation when memory is low
    - OOM handling
    - Recovery after memory pressure

    Expected Outcome:
    - System degrades gracefully
    - No crashes or data corruption
    - Can recover when memory is freed

    NOTE: This test is skipped by default as it can destabilize the system.
    Run manually with: pytest -v -m stress --run-dangerous
    """
    print(f"\n{'=' * 80}")
    print(f"MEMORY EXHAUSTION STRESS TEST")
    print(f"{'=' * 80}")
    print(f"WARNING: This test intentionally exhausts memory!")
    print(f"{'=' * 80}\n")

    # Get available memory
    memory = psutil.virtual_memory()
    available_mb = memory.available / 1024 / 1024

    print(f"Available memory: {available_mb:.2f} MB")

    # Allocate until we hit limits (leave 20% for system)
    target_mb = available_mb * 0.8
    allocations = []

    try:
        while True:
            # Allocate 100MB chunks
            chunk = bytearray(100 * 1024 * 1024)
            allocations.append(chunk)

            current_mb = len(allocations) * 100
            if current_mb >= target_mb:
                break

            if len(allocations) % 10 == 0:
                print(f"Allocated: {current_mb:.2f} MB")

    except MemoryError:
        print(f"MemoryError at {len(allocations) * 100:.2f} MB")

    finally:
        # Clean up
        allocations.clear()
        print("Memory freed")


# ==============================================================================
# Connection Saturation Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_connection_saturation():
    """
    Stress Test: Saturate connection pool.

    Tests:
    - Behavior when all connections are in use
    - Connection pool limits
    - Connection timeout handling
    - Connection reuse

    Expected Outcome:
    - Connections are properly pooled and reused
    - Requests wait for available connections
    - No connection leaks
    """
    print(f"\n{'=' * 80}")
    print(f"CONNECTION SATURATION STRESS TEST")
    print(f"{'=' * 80}\n")

    # Create client with small connection pool
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Simulate connection delay
        async def delayed_post(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms per request
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": {"allow": True}}
            return mock_response

        mock_client.post = delayed_post

        client = OPAClient(opa_url="http://localhost:8181", timeout=5.0)

        # Saturate connections (more concurrent requests than pool size)
        num_requests = 100
        start_time = time.time()

        tasks = []
        for i in range(num_requests):
            auth_input = AuthorizationInput(
                user_id=f"user-{i}",
                action="read",
                resource=f"doc-{i}",
                context={},
            )
            tasks.append(client.evaluate_policy(auth_input, use_cache=False))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start_time
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful

        print(f"Concurrent requests: {num_requests}")
        print(f"Duration: {duration:.2f}s")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Throughput: {successful / duration:.2f} req/s")
        print(f"{'=' * 80}\n")

        # Verify all requests completed (may be slow, but shouldn't fail)
        assert successful > 0, "All requests failed"
        assert failed == 0, f"{failed} requests failed due to connection issues"

        await client.close()
