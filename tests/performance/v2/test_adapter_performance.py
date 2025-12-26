"""
Performance tests for protocol adapters in SARK v2.0.

Tests adapter overhead, throughput, latency distribution, and scalability
to ensure <100ms adapter overhead requirement is met.

Engineer: QA-2
Deliverable: tests/performance/v2/test_adapter_performance.py
"""

import asyncio
import statistics
import time

import pytest

from sark.models.base import InvocationRequest, InvocationResult


class TestAdapterOverhead:
    """Test adapter overhead meets <100ms requirement."""

    @pytest.mark.asyncio
    async def test_single_invocation_overhead(
        self, mock_adapter, sample_invocation_request, performance_thresholds
    ):
        """Test that a single invocation completes within acceptable overhead."""
        start = time.perf_counter()
        result = await mock_adapter.invoke(sample_invocation_request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.success, "Invocation should succeed"
        assert elapsed_ms < performance_thresholds["adapter_overhead_ms"], (
            f"Adapter overhead {elapsed_ms:.2f}ms exceeds threshold "
            f"{performance_thresholds['adapter_overhead_ms']}ms"
        )

    @pytest.mark.asyncio
    async def test_discovery_performance(self, mock_adapter, performance_thresholds):
        """Test resource discovery completes within acceptable time."""
        start = time.perf_counter()
        resources = await mock_adapter.discover_resources({"test": True})
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(resources) > 0, "Should discover at least one resource"
        assert elapsed_ms < performance_thresholds["discovery_time_ms"], (
            f"Discovery took {elapsed_ms:.2f}ms, exceeds threshold "
            f"{performance_thresholds['discovery_time_ms']}ms"
        )

    @pytest.mark.asyncio
    async def test_health_check_performance(
        self, mock_adapter, sample_resource, performance_thresholds
    ):
        """Test health check completes within acceptable time."""
        start = time.perf_counter()
        healthy = await mock_adapter.health_check(sample_resource)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert healthy, "Health check should pass"
        assert elapsed_ms < performance_thresholds["health_check_ms"], (
            f"Health check took {elapsed_ms:.2f}ms, exceeds threshold "
            f"{performance_thresholds['health_check_ms']}ms"
        )

    @pytest.mark.asyncio
    async def test_validation_overhead(self, mock_adapter, sample_invocation_request):
        """Test request validation has minimal overhead."""
        latencies = []
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            valid = await mock_adapter.validate_request(sample_invocation_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            assert valid, "Validation should pass"

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

        assert avg_latency < 1.0, f"Avg validation latency {avg_latency:.2f}ms too high"
        assert p95_latency < 2.0, f"P95 validation latency {p95_latency:.2f}ms too high"


class TestAdapterThroughput:
    """Test adapter throughput and scalability."""

    @pytest.mark.asyncio
    async def test_sequential_throughput(
        self, mock_adapter, load_test_requests, performance_thresholds
    ):
        """Test sequential request processing throughput."""
        start = time.perf_counter()
        results = []

        for request in load_test_requests[:50]:  # Test with 50 requests
            result = await mock_adapter.invoke(request)
            results.append(result)

        elapsed_sec = time.perf_counter() - start
        throughput = len(results) / elapsed_sec

        assert all(r.success for r in results), "All requests should succeed"
        # Note: Sequential throughput will be lower, this tests baseline
        assert throughput > 10, f"Sequential throughput {throughput:.2f} RPS too low"

    @pytest.mark.asyncio
    async def test_concurrent_throughput(
        self, mock_adapter, load_test_requests, performance_thresholds
    ):
        """Test concurrent request processing throughput."""
        start = time.perf_counter()

        # Process 100 requests concurrently
        tasks = [mock_adapter.invoke(req) for req in load_test_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_sec = time.perf_counter() - start
        throughput = len(results) / elapsed_sec

        successful_results = [r for r in results if isinstance(r, InvocationResult) and r.success]
        success_rate = len(successful_results) / len(results)

        assert success_rate > 0.99, f"Success rate {success_rate:.2%} below 99%"
        assert throughput > performance_thresholds["throughput_rps"], (
            f"Throughput {throughput:.2f} RPS below threshold "
            f"{performance_thresholds['throughput_rps']} RPS"
        )

    @pytest.mark.asyncio
    async def test_scalability_under_load(
        self, mock_adapter, sample_invocation_request, benchmark_config
    ):
        """Test adapter performance scales with concurrency."""
        results = {}

        for concurrency in benchmark_config["concurrency_levels"]:
            requests = [sample_invocation_request] * concurrency
            start = time.perf_counter()

            tasks = [mock_adapter.invoke(req) for req in requests]
            invocation_results = await asyncio.gather(*tasks, return_exceptions=True)

            elapsed_sec = time.perf_counter() - start
            throughput = len(invocation_results) / elapsed_sec

            results[concurrency] = {
                "throughput": throughput,
                "elapsed_sec": elapsed_sec,
                "success_rate": sum(
                    1 for r in invocation_results if isinstance(r, InvocationResult) and r.success
                )
                / len(invocation_results),
            }

        # Verify throughput improves with concurrency (up to a point)
        assert (
            results[10]["throughput"] > results[1]["throughput"]
        ), "Throughput should improve with concurrency"

        # All concurrency levels should maintain high success rate
        for concurrency, metrics in results.items():
            assert (
                metrics["success_rate"] > 0.95
            ), f"Success rate at concurrency {concurrency} is {metrics['success_rate']:.2%}"


class TestLatencyDistribution:
    """Test adapter latency distribution and percentiles."""

    @pytest.mark.asyncio
    async def test_latency_percentiles(
        self, mock_adapter, sample_invocation_request, performance_thresholds, percentile_calculator
    ):
        """Test P50, P95, P99 latency meet requirements."""
        latencies = []
        iterations = 1000

        for _ in range(iterations):
            start = time.perf_counter()
            result = await mock_adapter.invoke(sample_invocation_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            assert result.success

        p50 = percentile_calculator(latencies, 50)
        p95 = percentile_calculator(latencies, 95)
        p99 = percentile_calculator(latencies, 99)
        avg = statistics.mean(latencies)
        stddev = statistics.stdev(latencies)

        print(f"\nLatency Distribution (n={iterations}):")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  Avg: {avg:.2f}ms ± {stddev:.2f}ms")

        assert (
            p95 < performance_thresholds["p95_latency_ms"]
        ), f"P95 latency {p95:.2f}ms exceeds threshold {performance_thresholds['p95_latency_ms']}ms"
        assert (
            p99 < performance_thresholds["p99_latency_ms"]
        ), f"P99 latency {p99:.2f}ms exceeds threshold {performance_thresholds['p99_latency_ms']}ms"

    @pytest.mark.asyncio
    async def test_latency_consistency(self, mock_adapter, sample_invocation_request):
        """Test latency is consistent (low variance)."""
        latencies = []
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            result = await mock_adapter.invoke(sample_invocation_request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        avg = statistics.mean(latencies)
        stddev = statistics.stdev(latencies)
        coefficient_of_variation = stddev / avg

        # Coefficient of variation should be low (<0.5 means consistent)
        assert (
            coefficient_of_variation < 0.5
        ), f"Latency variance too high (CV={coefficient_of_variation:.2f})"


class TestBatchOperations:
    """Test batch operation performance if adapter supports it."""

    @pytest.mark.asyncio
    async def test_batch_vs_sequential(self, mock_adapter, load_test_requests):
        """Compare batch operation performance vs sequential."""
        test_requests = load_test_requests[:20]

        # Test sequential
        start_seq = time.perf_counter()
        sequential_results = []
        for req in test_requests:
            result = await mock_adapter.invoke(req)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - start_seq

        # Test batch (if supported)
        if mock_adapter.supports_batch():
            start_batch = time.perf_counter()
            batch_results = await mock_adapter.invoke_batch(test_requests)
            batch_time = time.perf_counter() - start_batch

            speedup = sequential_time / batch_time

            assert len(batch_results) == len(test_requests)
            assert all(r.success for r in batch_results)
            assert speedup > 1.2, f"Batch speedup {speedup:.2f}x too low (should be >1.2x)"
        else:
            # If batch not supported, that's OK for some adapters
            pytest.skip(f"{mock_adapter.protocol_name} adapter doesn't support batch operations")


class TestStreamingPerformance:
    """Test streaming operation performance if adapter supports it."""

    @pytest.mark.asyncio
    async def test_streaming_overhead(self, mock_adapter, sample_invocation_request):
        """Test streaming has acceptable overhead vs regular invocation."""
        if not mock_adapter.supports_streaming():
            pytest.skip(f"{mock_adapter.protocol_name} adapter doesn't support streaming")

        # Test regular invocation
        start = time.perf_counter()
        regular_result = await mock_adapter.invoke(sample_invocation_request)
        regular_time = (time.perf_counter() - start) * 1000

        # Test streaming invocation
        start = time.perf_counter()
        chunks = []
        async for chunk in mock_adapter.invoke_streaming(sample_invocation_request):
            chunks.append(chunk)
        streaming_time = (time.perf_counter() - start) * 1000

        # Streaming overhead should be reasonable (<50% more than regular)
        overhead_ratio = streaming_time / regular_time
        assert overhead_ratio < 1.5, f"Streaming overhead {overhead_ratio:.2f}x too high"


@pytest.mark.benchmark
class TestAdapterBenchmarks:
    """Comprehensive benchmarks for performance baselines."""

    @pytest.mark.asyncio
    async def test_benchmark_full_cycle(self, mock_adapter, benchmark_config, performance_metrics):
        """Benchmark full discovery -> invoke -> health check cycle."""
        metrics = {}

        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            await mock_adapter.discover_resources({"test": True})

        # Benchmark discovery
        discovery_times = []
        for _ in range(50):
            start = time.perf_counter()
            resources = await mock_adapter.discover_resources({"test": True})
            elapsed_ms = (time.perf_counter() - start) * 1000
            discovery_times.append(elapsed_ms)

        metrics["discovery"] = {
            "avg_ms": statistics.mean(discovery_times),
            "p95_ms": statistics.quantiles(discovery_times, n=20)[18],
        }

        # Benchmark invocations

        request = InvocationRequest(
            capability_id="test",
            principal_id="bench",
            arguments={},
            context={},
        )

        invocation_times = []
        for _ in range(benchmark_config["benchmark_iterations"]):
            start = time.perf_counter()
            result = await mock_adapter.invoke(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            invocation_times.append(elapsed_ms)

        metrics["invocation"] = {
            "avg_ms": statistics.mean(invocation_times),
            "p95_ms": statistics.quantiles(invocation_times, n=20)[18],
            "p99_ms": statistics.quantiles(invocation_times, n=100)[98],
        }

        # Store in performance_metrics for reporting
        performance_metrics["benchmarks"] = metrics

        print(f"\n{'='*60}")
        print(f"Benchmark Results for {mock_adapter.protocol_name} adapter:")
        print(f"{'='*60}")
        for operation, timings in metrics.items():
            print(f"\n{operation.upper()}:")
            for metric, value in timings.items():
                print(f"  {metric}: {value:.2f}ms")
