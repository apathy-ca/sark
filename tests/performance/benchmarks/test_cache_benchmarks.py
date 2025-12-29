"""
Policy Cache Performance Benchmarks.

Compares performance of Rust-based in-memory cache vs Redis-based Python cache.

Acceptance Criteria:
- Cache Rust p95 latency <0.5ms
- Rust 10-50x faster than Redis
"""

import pytest

# ==============================================================================
# Cache GET Benchmarks (Warm Cache)
# ==============================================================================


@pytest.mark.benchmark(group="cache-get")
@pytest.mark.asyncio
async def test_cache_rust_get(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache GET operation (warm cache).

    Target: <0.5ms p95 latency
    Expected: 10-50x faster than Redis
    """
    # Preload cache
    await rust_cache.set("test-key-1", sample_decision)

    # Benchmark GET operation
    async def get_from_cache():
        return await rust_cache.get("test-key-1")

    result = benchmark(lambda: pytest.helpers.run_async(get_from_cache))

    # Verify result
    assert result is not None


@pytest.mark.benchmark(group="cache-get")
@pytest.mark.asyncio
async def test_cache_redis_get(benchmark, redis_cache, sample_decision, mock_redis):
    """
    Benchmark Redis cache GET operation (warm cache).

    Baseline for comparison with Rust implementation.
    Expected to be 10-50x slower than Rust.
    """
    import json

    # Mock Redis to return cached data
    mock_redis.get.return_value = json.dumps(sample_decision)

    # Benchmark GET operation
    async def get_from_cache():
        return await redis_cache.get(
            user_id="test-user",
            action="read",
            resource="test-resource",
        )

    result = benchmark(lambda: pytest.helpers.run_async(get_from_cache))

    # Verify result
    assert result is not None


# ==============================================================================
# Cache SET Benchmarks
# ==============================================================================


@pytest.mark.benchmark(group="cache-set")
@pytest.mark.asyncio
async def test_cache_rust_set(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache SET operation.

    Target: <0.5ms p95 latency
    """
    key_counter = [0]  # Mutable counter for unique keys

    async def set_to_cache():
        key = f"test-key-{key_counter[0]}"
        key_counter[0] += 1
        await rust_cache.set(key, sample_decision)

    benchmark(lambda: pytest.helpers.run_async(set_to_cache))


@pytest.mark.benchmark(group="cache-set")
@pytest.mark.asyncio
async def test_cache_redis_set(benchmark, redis_cache, sample_decision):
    """
    Benchmark Redis cache SET operation.

    Baseline for comparison with Rust implementation.
    """
    key_counter = [0]  # Mutable counter for unique keys

    async def set_to_cache():
        user_id = f"user-{key_counter[0]}"
        key_counter[0] += 1
        await redis_cache.set(
            user_id=user_id,
            action="read",
            resource="test-resource",
            decision=sample_decision,
        )

    benchmark(lambda: pytest.helpers.run_async(set_to_cache))


# ==============================================================================
# Cache DELETE Benchmarks
# ==============================================================================


@pytest.mark.benchmark(group="cache-delete")
@pytest.mark.asyncio
async def test_cache_rust_delete(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache DELETE operation.

    Target: <0.5ms p95 latency
    """
    # Preload cache with data
    await rust_cache.set("test-key-delete", sample_decision)

    async def delete_from_cache():
        await rust_cache.delete("test-key-delete")
        # Re-add for next iteration
        await rust_cache.set("test-key-delete", sample_decision)

    benchmark(lambda: pytest.helpers.run_async(delete_from_cache))


@pytest.mark.benchmark(group="cache-delete")
@pytest.mark.asyncio
async def test_cache_redis_delete(benchmark, redis_cache):
    """
    Benchmark Redis cache DELETE operation.

    Baseline for comparison with Rust implementation.
    """

    async def delete_from_cache():
        await redis_cache.delete(
            user_id="test-user",
            action="read",
            resource="test-resource",
        )

    benchmark(lambda: pytest.helpers.run_async(delete_from_cache))


# ==============================================================================
# Cache MISS Benchmarks (Cold Cache)
# ==============================================================================


@pytest.mark.benchmark(group="cache-miss")
@pytest.mark.asyncio
async def test_cache_rust_miss(benchmark, rust_cache):
    """
    Benchmark Rust cache MISS (key doesn't exist).

    Should still be fast even on cache miss.
    Target: <0.5ms p95 latency
    """
    key_counter = [0]

    async def get_missing_key():
        key = f"nonexistent-key-{key_counter[0]}"
        key_counter[0] += 1
        return await rust_cache.get(key)

    result = benchmark(lambda: pytest.helpers.run_async(get_missing_key))

    # Should return None for missing key
    assert result is None


@pytest.mark.benchmark(group="cache-miss")
@pytest.mark.asyncio
async def test_cache_redis_miss(benchmark, redis_cache, mock_redis):
    """
    Benchmark Redis cache MISS (key doesn't exist).

    Baseline for comparison with Rust implementation.
    """
    # Mock Redis to return None (cache miss)
    mock_redis.get.return_value = None

    async def get_missing_key():
        return await redis_cache.get(
            user_id="nonexistent-user",
            action="read",
            resource="nonexistent-resource",
        )

    result = benchmark(lambda: pytest.helpers.run_async(get_missing_key))

    # Should return None for missing key
    assert result is None


# ==============================================================================
# Concurrent Cache Operations
# ==============================================================================


@pytest.mark.benchmark(group="cache-concurrent")
@pytest.mark.asyncio
async def test_cache_rust_concurrent_reads_10(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache with 10 concurrent reads.

    Tests thread-safety and concurrent performance.
    """
    import asyncio

    # Preload cache
    for i in range(10):
        await rust_cache.set(f"key-{i}", sample_decision)

    async def concurrent_reads():
        tasks = [rust_cache.get(f"key-{i}") for i in range(10)]
        return await asyncio.gather(*tasks)

    results = benchmark(lambda: pytest.helpers.run_async(concurrent_reads))
    assert len(results) == 10


@pytest.mark.benchmark(group="cache-concurrent")
@pytest.mark.asyncio
async def test_cache_rust_concurrent_reads_100(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache with 100 concurrent reads.

    Tests scalability under heavy concurrent load.
    """
    import asyncio

    # Preload cache
    for i in range(100):
        await rust_cache.set(f"key-{i}", sample_decision)

    async def concurrent_reads():
        tasks = [rust_cache.get(f"key-{i}") for i in range(100)]
        return await asyncio.gather(*tasks)

    results = benchmark(lambda: pytest.helpers.run_async(concurrent_reads))
    assert len(results) == 100


@pytest.mark.benchmark(group="cache-concurrent")
@pytest.mark.asyncio
async def test_cache_rust_concurrent_writes_10(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache with 10 concurrent writes.

    Tests write performance and lock contention.
    """
    import asyncio

    async def concurrent_writes():
        tasks = [rust_cache.set(f"key-{i}", sample_decision) for i in range(10)]
        await asyncio.gather(*tasks)

    benchmark(lambda: pytest.helpers.run_async(concurrent_writes))


@pytest.mark.benchmark(group="cache-concurrent")
@pytest.mark.asyncio
async def test_cache_rust_concurrent_writes_100(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache with 100 concurrent writes.

    Tests write scalability.
    """
    import asyncio

    async def concurrent_writes():
        tasks = [rust_cache.set(f"key-{i}", sample_decision) for i in range(100)]
        await asyncio.gather(*tasks)

    benchmark(lambda: pytest.helpers.run_async(concurrent_writes))


@pytest.mark.benchmark(group="cache-concurrent")
@pytest.mark.asyncio
async def test_cache_rust_concurrent_mixed_100(benchmark, rust_cache, sample_decision):
    """
    Benchmark Rust cache with 100 mixed concurrent operations (reads + writes).

    Tests real-world concurrent workload with mixed operations.
    """
    import asyncio

    # Preload some data
    for i in range(50):
        await rust_cache.set(f"key-{i}", sample_decision)

    async def concurrent_mixed():
        tasks = []
        # 50 reads, 30 writes, 20 deletes
        for i in range(50):
            tasks.append(rust_cache.get(f"key-{i}"))
        for i in range(50, 80):
            tasks.append(rust_cache.set(f"key-{i}", sample_decision))
        for i in range(80, 100):
            tasks.append(rust_cache.delete(f"key-{i}"))

        await asyncio.gather(*tasks)

    benchmark(lambda: pytest.helpers.run_async(concurrent_mixed))


# ==============================================================================
# Cache Size Scaling Benchmarks
# ==============================================================================


@pytest.mark.benchmark(group="cache-scaling")
@pytest.mark.asyncio
async def test_cache_rust_small_size(benchmark, sample_decision):
    """
    Benchmark Rust cache with small size (100 entries).

    Tests performance with minimal memory footprint.
    """
    # Create small cache
    from sark.services.policy.factory import RustPolicyCache

    cache = RustPolicyCache(max_size=100)

    # Fill cache
    for i in range(100):
        await cache.set(f"key-{i}", sample_decision)

    # Benchmark random access
    async def get_from_cache():
        return await cache.get("key-50")

    result = benchmark(lambda: pytest.helpers.run_async(get_from_cache))
    assert result is not None


@pytest.mark.benchmark(group="cache-scaling")
@pytest.mark.asyncio
async def test_cache_rust_medium_size(benchmark, sample_decision):
    """
    Benchmark Rust cache with medium size (10,000 entries).

    Tests performance with typical production workload.
    """
    from sark.services.policy.factory import RustPolicyCache

    cache = RustPolicyCache(max_size=10_000)

    # Fill cache
    for i in range(10_000):
        await cache.set(f"key-{i}", sample_decision)

    # Benchmark random access
    async def get_from_cache():
        return await cache.get("key-5000")

    result = benchmark(lambda: pytest.helpers.run_async(get_from_cache))
    assert result is not None


@pytest.mark.benchmark(group="cache-scaling")
@pytest.mark.asyncio
async def test_cache_rust_large_size(benchmark, sample_decision):
    """
    Benchmark Rust cache with large size (1,000,000 entries).

    Tests performance under heavy memory load.
    Note: This test may be slow to set up and may skip if memory is constrained.
    """
    from sark.services.policy.factory import RustPolicyCache

    try:
        cache = RustPolicyCache(max_size=1_000_000)

        # Fill cache (only partial fill to save time)
        for i in range(0, 1_000_000, 100):  # Every 100th entry
            await cache.set(f"key-{i}", sample_decision)

        # Benchmark random access
        async def get_from_cache():
            return await cache.get("key-500000")

        result = benchmark(lambda: pytest.helpers.run_async(get_from_cache))
        assert result is not None
    except MemoryError:
        pytest.skip("Insufficient memory for large cache test")


# ==============================================================================
# Cache Eviction Benchmarks
# ==============================================================================


@pytest.mark.benchmark(group="cache-eviction")
@pytest.mark.asyncio
async def test_cache_rust_eviction_lru(benchmark, sample_decision):
    """
    Benchmark Rust cache LRU eviction performance.

    Tests how efficiently the cache handles evictions when full.
    """
    from sark.services.policy.factory import RustPolicyCache

    # Create small cache to force evictions
    cache = RustPolicyCache(max_size=100)

    # Fill cache to capacity
    for i in range(100):
        await cache.set(f"key-{i}", sample_decision)

    key_counter = [100]

    # Benchmark adding new entries that trigger eviction
    async def set_with_eviction():
        key = f"key-{key_counter[0]}"
        key_counter[0] += 1
        await cache.set(key, sample_decision)

    benchmark(lambda: pytest.helpers.run_async(set_with_eviction))


# ==============================================================================
# Helpers
# ==============================================================================


@pytest.helpers.register
def run_async(coro):
    """Helper to run async functions in benchmarks."""
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro())
