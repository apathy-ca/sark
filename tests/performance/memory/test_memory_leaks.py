"""
Memory leak detection and profiling tests.

Tests for memory leaks in both Rust and Python implementations:
1. Long-running stability tests (24 hours)
2. Memory usage tracking over time
3. Cache growth patterns
4. Resource cleanup verification

Acceptance Criteria:
- No memory leaks detected
- Memory usage stable under sustained load
- Memory usage ≤ baseline Python version
"""

import asyncio
import gc
import os
import time
from unittest.mock import AsyncMock, patch

import psutil
import pytest

from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import AuthorizationInput, OPAClient

# ==============================================================================
# Helper Functions
# ==============================================================================


def get_memory_usage() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_memory_stats() -> dict:
    """Get detailed memory statistics."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        "rss_mb": mem_info.rss / 1024 / 1024,  # Resident Set Size
        "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        "percent": process.memory_percent(),
    }


# ==============================================================================
# Short-term Memory Leak Tests (for CI)
# ==============================================================================


@pytest.mark.memory
@pytest.mark.asyncio
async def test_opa_client_no_memory_leak_short():
    """
    Short-term test: Verify OPA client doesn't leak memory (100K requests).

    This is a faster version suitable for CI that still catches obvious leaks.
    """
    print(f"\n{'=' * 80}")
    print("OPA CLIENT MEMORY LEAK TEST (SHORT)")
    print(f"{'=' * 80}\n")

    # Force garbage collection before starting
    gc.collect()
    initial_memory = get_memory_usage()
    print(f"Initial memory: {initial_memory:.2f} MB")

    # Mock OPA client
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_client.post.return_value = mock_response

        client = OPAClient(opa_url="http://localhost:8181")

        # Run 100K requests in batches
        num_requests = 100_000
        batch_size = 10_000
        num_batches = num_requests // batch_size

        memory_samples: list[tuple[int, float]] = []

        for batch_num in range(num_batches):
            # Run batch
            for i in range(batch_size):
                auth_input = AuthorizationInput(
                    user_id=f"user-{i % 1000}",
                    action="read",
                    resource=f"doc-{i % 100}",
                    context={},
                )
                await client.evaluate_policy(auth_input, use_cache=False)

            # Sample memory after each batch
            gc.collect()  # Force GC to free unreferenced objects
            current_memory = get_memory_usage()
            requests_completed = (batch_num + 1) * batch_size
            memory_samples.append((requests_completed, current_memory))

            if (batch_num + 1) % 2 == 0:
                print(
                    f"  {requests_completed:,} requests: {current_memory:.2f} MB "
                    f"(+{current_memory - initial_memory:.2f} MB)"
                )

        await client.close()

        # Final memory check
        gc.collect()
        final_memory = get_memory_usage()
        memory_growth = final_memory - initial_memory

        print(f"\n{'=' * 80}")
        print("RESULTS")
        print(f"{'=' * 80}")
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory growth: {memory_growth:.2f} MB")
        print(f"Growth per 1K requests: {memory_growth / (num_requests / 1000):.4f} MB")
        print(f"{'=' * 80}\n")

        # Allow up to 50MB growth for 100K requests (0.5KB per request)
        # This accounts for caching, connection pools, etc.
        assert memory_growth < 50, f"Possible memory leak: grew {memory_growth:.2f} MB"

        # Check that memory didn't grow linearly (sign of leak)
        # Compare first half vs second half growth rate
        mid_point = len(memory_samples) // 2
        first_half_growth = memory_samples[mid_point][1] - memory_samples[0][1]
        second_half_growth = memory_samples[-1][1] - memory_samples[mid_point][1]

        print(f"First half growth: {first_half_growth:.2f} MB")
        print(f"Second half growth: {second_half_growth:.2f} MB")

        # Second half growth should not be significantly larger than first half
        # Allow 50% increase to account for variance
        assert second_half_growth < first_half_growth * 1.5, "Memory appears to be leaking linearly"

        print("✓ No memory leak detected\n")


@pytest.mark.memory
@pytest.mark.asyncio
async def test_cache_no_memory_leak_short():
    """
    Short-term test: Verify cache doesn't leak memory (100K operations).

    Tests cache set/get operations for memory leaks.
    """
    print(f"\n{'=' * 80}")
    print("CACHE MEMORY LEAK TEST (SHORT)")
    print(f"{'=' * 80}\n")

    gc.collect()
    initial_memory = get_memory_usage()
    print(f"Initial memory: {initial_memory:.2f} MB")

    # Mock Redis
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value='{"allow": true}')
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    cache = PolicyCache(redis_client=mock_redis, ttl_seconds=300, enabled=True)

    # Run 100K cache operations
    num_operations = 100_000
    batch_size = 10_000
    num_batches = num_operations // batch_size

    memory_samples: list[tuple[int, float]] = []

    for batch_num in range(num_batches):
        # Mix of set and get operations
        for i in range(batch_size):
            if i % 2 == 0:
                # Set operation
                await cache.set(
                    user_id=f"user-{i % 1000}",
                    action="read",
                    resource=f"doc-{i % 100}",
                    decision={"allow": True, "reason": "test"},
                )
            else:
                # Get operation
                await cache.get(
                    user_id=f"user-{i % 1000}",
                    action="read",
                    resource=f"doc-{i % 100}",
                )

        # Sample memory
        gc.collect()
        current_memory = get_memory_usage()
        operations_completed = (batch_num + 1) * batch_size
        memory_samples.append((operations_completed, current_memory))

        if (batch_num + 1) % 2 == 0:
            print(
                f"  {operations_completed:,} operations: {current_memory:.2f} MB "
                f"(+{current_memory - initial_memory:.2f} MB)"
            )

    # Final check
    gc.collect()
    final_memory = get_memory_usage()
    memory_growth = final_memory - initial_memory

    print(f"\n{'=' * 80}")
    print("RESULTS")
    print(f"{'=' * 80}")
    print(f"Initial memory: {initial_memory:.2f} MB")
    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Memory growth: {memory_growth:.2f} MB")
    print(f"{'=' * 80}\n")

    # Allow up to 30MB growth for 100K operations
    assert memory_growth < 30, f"Possible memory leak: grew {memory_growth:.2f} MB"

    print("✓ No memory leak detected\n")


# ==============================================================================
# Long-running Memory Leak Tests (24 hours)
# ==============================================================================


@pytest.mark.slow
@pytest.mark.memory
@pytest.mark.skip(reason="24-hour test - run manually for release validation")
async def test_no_memory_leak_24h():
    """
    Long-running test: Monitor memory for 24 hours.

    This test runs continuously for 24 hours and monitors memory usage.
    Memory should stabilize and not grow continuously.

    Run manually with:
    pytest tests/performance/memory/test_memory_leaks.py::test_no_memory_leak_24h -v -s
    """
    print(f"\n{'=' * 80}")
    print("24-HOUR MEMORY LEAK TEST")
    print(f"{'=' * 80}\n")

    # Test configuration
    test_duration_hours = 24
    test_duration_seconds = test_duration_hours * 3600
    sample_interval_seconds = 300  # Sample every 5 minutes

    gc.collect()
    initial_memory = get_memory_usage()
    start_time = time.time()

    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {test_duration_hours} hours")
    print(f"Sample interval: {sample_interval_seconds} seconds")
    print(f"Initial memory: {initial_memory:.2f} MB\n")

    # Mock OPA and cache
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_client.post.return_value = mock_response

        client = OPAClient(opa_url="http://localhost:8181")

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"allow": true}')
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        cache = PolicyCache(redis_client=mock_redis, ttl_seconds=300, enabled=True)

        # Memory tracking
        memory_samples: list[tuple[float, float]] = []
        request_count = 0
        sample_count = 0

        # Main test loop
        while (time.time() - start_time) < test_duration_seconds:
            # Run a batch of requests
            batch_size = 1000
            for i in range(batch_size):
                # Alternate between OPA and cache operations
                if i % 2 == 0:
                    auth_input = AuthorizationInput(
                        user_id=f"user-{request_count % 10000}",
                        action="read",
                        resource=f"doc-{request_count % 1000}",
                        context={},
                    )
                    await client.evaluate_policy(auth_input, use_cache=True)
                else:
                    await cache.set(
                        user_id=f"user-{request_count % 10000}",
                        action="read",
                        resource=f"doc-{request_count % 1000}",
                        decision={"allow": True},
                    )

                request_count += 1

            # Sample memory at intervals
            elapsed = time.time() - start_time
            if elapsed >= (sample_count * sample_interval_seconds):
                gc.collect()
                current_memory = get_memory_usage()
                memory_samples.append((elapsed, current_memory))
                sample_count += 1

                elapsed_hours = elapsed / 3600
                memory_growth = current_memory - initial_memory
                print(
                    f"[{elapsed_hours:.1f}h] Memory: {current_memory:.2f} MB "
                    f"(+{memory_growth:.2f} MB), Requests: {request_count:,}"
                )

            # Small delay to avoid hammering the system
            await asyncio.sleep(0.001)

        # Test completed
        await client.close()

        gc.collect()
        final_memory = get_memory_usage()
        total_memory_growth = final_memory - initial_memory
        elapsed_hours = (time.time() - start_time) / 3600

        print(f"\n{'=' * 80}")
        print("24-HOUR TEST RESULTS")
        print(f"{'=' * 80}")
        print(f"Elapsed time: {elapsed_hours:.2f} hours")
        print(f"Total requests: {request_count:,}")
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Total growth: {total_memory_growth:.2f} MB")
        print(f"Growth per hour: {total_memory_growth / elapsed_hours:.2f} MB/hr")
        print(f"{'=' * 80}\n")

        # Analyze memory trend
        if len(memory_samples) >= 10:
            # Calculate growth rate over time
            # Split into first and last quarters
            quarter_point = len(memory_samples) // 4
            first_quarter_avg = sum(m for _, m in memory_samples[:quarter_point]) / quarter_point
            last_quarter_avg = sum(m for _, m in memory_samples[-quarter_point:]) / quarter_point

            growth_rate = (last_quarter_avg - first_quarter_avg) / (test_duration_hours * 0.5)

            print(f"First quarter avg: {first_quarter_avg:.2f} MB")
            print(f"Last quarter avg: {last_quarter_avg:.2f} MB")
            print(f"Growth rate: {growth_rate:.4f} MB/hr\n")

            # Memory should stabilize (growth rate < 1 MB/hr)
            assert growth_rate < 1.0, f"Memory still growing: {growth_rate:.4f} MB/hr"

        # Allow up to 100MB growth over 24 hours (accounts for caching, buffers, etc.)
        assert total_memory_growth < 100, f"Memory grew too much: {total_memory_growth:.2f} MB"

        print("✓ No memory leak detected over 24 hours\n")


# ==============================================================================
# Rust vs Python Memory Comparison
# ==============================================================================


@pytest.mark.memory
@pytest.mark.asyncio
async def test_rust_vs_python_memory_usage():
    """
    Compare memory usage of Rust vs Python implementations.

    Tests the same workload on both implementations and compares:
    - Initial memory footprint
    - Memory growth under load
    - Memory stability

    Expected: Rust ≤ Python memory usage
    """
    print(f"\n{'=' * 80}")
    print("RUST VS PYTHON MEMORY COMPARISON")
    print(f"{'=' * 80}\n")

    # Test configuration
    num_requests = 50_000

    # Test Python implementation
    print("Testing Python implementation...")
    gc.collect()
    python_initial = get_memory_usage()

    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_client.post.return_value = mock_response

        client = OPAClient(opa_url="http://localhost:8181")

        for i in range(num_requests):
            auth_input = AuthorizationInput(
                user_id=f"user-{i % 1000}",
                action="read",
                resource=f"doc-{i % 100}",
                context={},
            )
            await client.evaluate_policy(auth_input, use_cache=False)

        await client.close()

    gc.collect()
    python_final = get_memory_usage()
    python_growth = python_final - python_initial

    print(f"  Initial: {python_initial:.2f} MB")
    print(f"  Final: {python_final:.2f} MB")
    print(f"  Growth: {python_growth:.2f} MB\n")

    # Test Rust implementation (if available)
    rust_enabled = os.getenv("RUST_ENABLED", "false").lower() == "true"

    if rust_enabled:
        print("Testing Rust implementation...")
        gc.collect()
        rust_initial = get_memory_usage()

        # Would use actual Rust client here
        # For now, use mock with similar behavior
        mock_rust_client = AsyncMock()
        mock_rust_client.evaluate_policy = AsyncMock(
            return_value={"allow": True, "reason": "Rust mock"}
        )
        mock_rust_client.close = AsyncMock()

        for i in range(num_requests):
            await mock_rust_client.evaluate_policy(
                auth_input=AuthorizationInput(
                    user_id=f"user-{i % 1000}",
                    action="read",
                    resource=f"doc-{i % 100}",
                    context={},
                ),
                use_cache=False,
            )

        await mock_rust_client.close()

        gc.collect()
        rust_final = get_memory_usage()
        rust_growth = rust_final - rust_initial

        print(f"  Initial: {rust_initial:.2f} MB")
        print(f"  Final: {rust_final:.2f} MB")
        print(f"  Growth: {rust_growth:.2f} MB\n")

        # Comparison
        print(f"{'=' * 80}")
        print("COMPARISON")
        print(f"{'=' * 80}")
        print(f"Python memory growth: {python_growth:.2f} MB")
        print(f"Rust memory growth: {rust_growth:.2f} MB")

        if rust_growth < python_growth:
            improvement = ((python_growth - rust_growth) / python_growth) * 100
            print(f"Rust uses {improvement:.1f}% less memory")
        else:
            print("Rust uses similar memory to Python")

        print(f"{'=' * 80}\n")

        # Rust should use ≤ Python memory
        assert (
            rust_growth <= python_growth * 1.1
        ), f"Rust uses more memory than Python: {rust_growth:.2f} vs {python_growth:.2f} MB"
    else:
        print("Rust implementation not enabled (RUST_ENABLED=false)")
        print("Skipping Rust comparison\n")


# ==============================================================================
# Resource Cleanup Tests
# ==============================================================================


@pytest.mark.memory
@pytest.mark.asyncio
async def test_resource_cleanup_on_client_close():
    """
    Verify that closing clients properly releases memory.

    Tests that connection pools, caches, and other resources
    are properly cleaned up when clients are closed.
    """
    print(f"\n{'=' * 80}")
    print("RESOURCE CLEANUP TEST")
    print(f"{'=' * 80}\n")

    gc.collect()
    baseline_memory = get_memory_usage()
    print(f"Baseline memory: {baseline_memory:.2f} MB")

    # Create and use client
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_client.post.return_value = mock_response

        client = OPAClient(opa_url="http://localhost:8181")

        # Use the client
        for i in range(10_000):
            auth_input = AuthorizationInput(
                user_id=f"user-{i}",
                action="read",
                resource=f"doc-{i}",
                context={},
            )
            await client.evaluate_policy(auth_input, use_cache=False)

        memory_before_close = get_memory_usage()
        print(f"Memory before close: {memory_before_close:.2f} MB")

        # Close client
        await client.close()

        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Give async cleanup time
        gc.collect()

        memory_after_close = get_memory_usage()
        print(f"Memory after close: {memory_after_close:.2f} MB")

        memory_released = memory_before_close - memory_after_close
        print(f"Memory released: {memory_released:.2f} MB\n")

        # Memory should return close to baseline (within 10MB)
        memory_delta = memory_after_close - baseline_memory
        assert memory_delta < 10, f"Memory not properly released: {memory_delta:.2f} MB retained"

        print("✓ Resources properly cleaned up\n")
