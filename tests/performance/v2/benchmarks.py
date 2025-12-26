"""
Benchmarking framework for SARK v2.0 adapters.

Provides utilities for running comprehensive performance benchmarks,
collecting metrics, and generating performance baseline reports.

Engineer: QA-2
Deliverable: tests/performance/v2/benchmarks.py
"""

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import statistics
import time
from typing import Any

from sark.adapters.base import ProtocolAdapter
from sark.models.base import InvocationRequest


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    benchmark_name: str
    adapter_protocol: str
    timestamp: str
    iterations: int
    concurrency: int
    duration_sec: float

    # Latency metrics (milliseconds)
    latency_avg: float
    latency_median: float
    latency_p95: float
    latency_p99: float
    latency_min: float
    latency_max: float
    latency_stddev: float

    # Throughput metrics
    throughput_rps: float
    successful_requests: int
    failed_requests: int
    success_rate: float

    # Resource usage (if available)
    cpu_percent: float | None = None
    memory_mb: float | None = None

    # Additional metadata
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class BenchmarkRunner:
    """Runner for executing and collecting benchmark results."""

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize benchmark runner.

        Args:
            output_dir: Directory to save benchmark results
        """
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[BenchmarkResult] = []

    async def run_latency_benchmark(
        self,
        adapter: ProtocolAdapter,
        request: InvocationRequest,
        iterations: int = 1000,
        warmup_iterations: int = 100,
        benchmark_name: str = "latency_test",
    ) -> BenchmarkResult:
        """
        Run latency benchmark for an adapter.

        Args:
            adapter: Protocol adapter to benchmark
            request: Invocation request to use
            iterations: Number of benchmark iterations
            warmup_iterations: Number of warmup iterations
            benchmark_name: Name for this benchmark

        Returns:
            Benchmark results
        """
        # Warmup phase
        for _ in range(warmup_iterations):
            await adapter.invoke(request)

        # Benchmark phase
        latencies = []
        successful = 0
        failed = 0

        start_time = time.perf_counter()

        for _ in range(iterations):
            iter_start = time.perf_counter()
            try:
                result = await adapter.invoke(request)
                iter_elapsed = (time.perf_counter() - iter_start) * 1000
                latencies.append(iter_elapsed)

                if result.success:
                    successful += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                # Still record the time for failed requests
                iter_elapsed = (time.perf_counter() - iter_start) * 1000
                latencies.append(iter_elapsed)

        total_duration = time.perf_counter() - start_time

        # Calculate metrics
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)

        result = BenchmarkResult(
            benchmark_name=benchmark_name,
            adapter_protocol=adapter.protocol_name,
            timestamp=datetime.utcnow().isoformat(),
            iterations=iterations,
            concurrency=1,  # Sequential test
            duration_sec=total_duration,
            latency_avg=statistics.mean(latencies),
            latency_median=statistics.median(latencies),
            latency_p95=latencies_sorted[int(n * 0.95)] if n > 0 else 0,
            latency_p99=latencies_sorted[int(n * 0.99)] if n > 0 else 0,
            latency_min=min(latencies) if latencies else 0,
            latency_max=max(latencies) if latencies else 0,
            latency_stddev=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            throughput_rps=iterations / total_duration if total_duration > 0 else 0,
            successful_requests=successful,
            failed_requests=failed,
            success_rate=successful / iterations if iterations > 0 else 0,
        )

        self.results.append(result)
        return result

    async def run_throughput_benchmark(
        self,
        adapter: ProtocolAdapter,
        request: InvocationRequest,
        duration_sec: int = 30,
        concurrency: int = 10,
        benchmark_name: str = "throughput_test",
    ) -> BenchmarkResult:
        """
        Run throughput benchmark for an adapter.

        Args:
            adapter: Protocol adapter to benchmark
            request: Invocation request to use
            duration_sec: How long to run the test
            concurrency: Number of concurrent requests
            benchmark_name: Name for this benchmark

        Returns:
            Benchmark results
        """
        latencies = []
        successful = 0
        failed = 0

        async def worker():
            """Worker coroutine that continuously makes requests."""
            nonlocal successful, failed, latencies

            while True:
                start = time.perf_counter()
                try:
                    result = await adapter.invoke(request)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    latencies.append(elapsed_ms)

                    if result.success:
                        successful += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    latencies.append(elapsed_ms)

        # Run workers with timeout
        start_time = time.perf_counter()
        workers = [asyncio.create_task(worker()) for _ in range(concurrency)]

        await asyncio.sleep(duration_sec)

        # Cancel workers
        for w in workers:
            w.cancel()

        # Wait for cancellation
        await asyncio.gather(*workers, return_exceptions=True)

        total_duration = time.perf_counter() - start_time
        total_requests = successful + failed

        # Calculate metrics
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)

        result = BenchmarkResult(
            benchmark_name=benchmark_name,
            adapter_protocol=adapter.protocol_name,
            timestamp=datetime.utcnow().isoformat(),
            iterations=total_requests,
            concurrency=concurrency,
            duration_sec=total_duration,
            latency_avg=statistics.mean(latencies) if latencies else 0,
            latency_median=statistics.median(latencies) if latencies else 0,
            latency_p95=latencies_sorted[int(n * 0.95)] if n > 0 else 0,
            latency_p99=latencies_sorted[int(n * 0.99)] if n > 0 else 0,
            latency_min=min(latencies) if latencies else 0,
            latency_max=max(latencies) if latencies else 0,
            latency_stddev=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            throughput_rps=total_requests / total_duration if total_duration > 0 else 0,
            successful_requests=successful,
            failed_requests=failed,
            success_rate=successful / total_requests if total_requests > 0 else 0,
        )

        self.results.append(result)
        return result

    async def run_scalability_benchmark(
        self,
        adapter: ProtocolAdapter,
        request: InvocationRequest,
        concurrency_levels: list[int] | None = None,
        iterations_per_level: int = 100,
        benchmark_name: str = "scalability_test",
    ) -> list[BenchmarkResult]:
        """
        Run scalability benchmark across different concurrency levels.

        Args:
            adapter: Protocol adapter to benchmark
            request: Invocation request to use
            concurrency_levels: List of concurrency levels to test
            iterations_per_level: Iterations per concurrency level
            benchmark_name: Base name for benchmarks

        Returns:
            List of benchmark results for each concurrency level
        """
        if concurrency_levels is None:
            concurrency_levels = [1, 10, 50, 100, 200]
        results = []

        for concurrency in concurrency_levels:
            print(f"Testing concurrency level: {concurrency}")

            latencies = []
            successful = 0
            failed = 0

            # Create all requests for this level
            requests = [request] * (iterations_per_level * concurrency)

            start_time = time.perf_counter()

            # Process in batches of 'concurrency' size
            for i in range(0, len(requests), concurrency):
                batch = requests[i : i + concurrency]
                tasks = []

                for req in batch:

                    async def invoke_and_measure(r):
                        start = time.perf_counter()
                        try:
                            result = await adapter.invoke(r)
                            elapsed_ms = (time.perf_counter() - start) * 1000
                            return elapsed_ms, result.success
                        except Exception:
                            elapsed_ms = (time.perf_counter() - start) * 1000
                            return elapsed_ms, False

                    tasks.append(invoke_and_measure(req))

                batch_results = await asyncio.gather(*tasks)

                for elapsed_ms, success in batch_results:
                    latencies.append(elapsed_ms)
                    if success:
                        successful += 1
                    else:
                        failed += 1

            total_duration = time.perf_counter() - start_time
            total_requests = successful + failed

            # Calculate metrics
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)

            result = BenchmarkResult(
                benchmark_name=f"{benchmark_name}_c{concurrency}",
                adapter_protocol=adapter.protocol_name,
                timestamp=datetime.utcnow().isoformat(),
                iterations=total_requests,
                concurrency=concurrency,
                duration_sec=total_duration,
                latency_avg=statistics.mean(latencies) if latencies else 0,
                latency_median=statistics.median(latencies) if latencies else 0,
                latency_p95=latencies_sorted[int(n * 0.95)] if n > 0 else 0,
                latency_p99=latencies_sorted[int(n * 0.99)] if n > 0 else 0,
                latency_min=min(latencies) if latencies else 0,
                latency_max=max(latencies) if latencies else 0,
                latency_stddev=statistics.stdev(latencies) if len(latencies) > 1 else 0,
                throughput_rps=total_requests / total_duration if total_duration > 0 else 0,
                successful_requests=successful,
                failed_requests=failed,
                success_rate=successful / total_requests if total_requests > 0 else 0,
            )

            self.results.append(result)
            results.append(result)

        return results

    def save_results(self, filename: str | None = None) -> Path:
        """
        Save benchmark results to JSON file.

        Args:
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "results": [r.to_dict() for r in self.results],
                },
                f,
                indent=2,
            )

        return output_path

    def generate_summary(self) -> str:
        """
        Generate human-readable summary of benchmark results.

        Returns:
            Summary string
        """
        if not self.results:
            return "No benchmark results available."

        lines = ["=" * 80]
        lines.append("BENCHMARK SUMMARY")
        lines.append("=" * 80)

        # Group by adapter
        by_adapter = {}
        for result in self.results:
            protocol = result.adapter_protocol
            if protocol not in by_adapter:
                by_adapter[protocol] = []
            by_adapter[protocol].append(result)

        for protocol, results in by_adapter.items():
            lines.append(f"\nAdapter: {protocol}")
            lines.append("-" * 80)

            for result in results:
                lines.append(f"\n  Benchmark: {result.benchmark_name}")
                lines.append(f"    Timestamp: {result.timestamp}")
                lines.append(f"    Iterations: {result.iterations}")
                lines.append(f"    Concurrency: {result.concurrency}")
                lines.append(f"    Duration: {result.duration_sec:.2f}s")
                lines.append("\n  Latency:")
                lines.append(f"    Average: {result.latency_avg:.2f}ms")
                lines.append(f"    Median:  {result.latency_median:.2f}ms")
                lines.append(f"    P95:     {result.latency_p95:.2f}ms")
                lines.append(f"    P99:     {result.latency_p99:.2f}ms")
                lines.append(f"    Min:     {result.latency_min:.2f}ms")
                lines.append(f"    Max:     {result.latency_max:.2f}ms")
                lines.append(f"    StdDev:  {result.latency_stddev:.2f}ms")
                lines.append("\n  Throughput:")
                lines.append(f"    RPS:     {result.throughput_rps:.2f}")
                lines.append(f"    Success: {result.successful_requests}")
                lines.append(f"    Failed:  {result.failed_requests}")
                lines.append(f"    Rate:    {result.success_rate:.2%}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def print_summary(self):
        """Print summary to console."""
        print(self.generate_summary())


async def run_comprehensive_benchmarks(
    adapter: ProtocolAdapter,
    sample_request: InvocationRequest,
    output_dir: Path | None = None,
) -> BenchmarkRunner:
    """
    Run comprehensive benchmark suite for an adapter.

    Args:
        adapter: Protocol adapter to benchmark
        sample_request: Sample request to use for benchmarking
        output_dir: Directory to save results

    Returns:
        BenchmarkRunner with results
    """
    runner = BenchmarkRunner(output_dir)

    print(f"Running comprehensive benchmarks for {adapter.protocol_name} adapter...")

    # Latency benchmark
    print("\n1. Latency benchmark...")
    await runner.run_latency_benchmark(
        adapter=adapter,
        request=sample_request,
        iterations=1000,
        benchmark_name="latency_baseline",
    )

    # Throughput benchmark
    print("\n2. Throughput benchmark...")
    await runner.run_throughput_benchmark(
        adapter=adapter,
        request=sample_request,
        duration_sec=30,
        concurrency=10,
        benchmark_name="throughput_baseline",
    )

    # Scalability benchmark
    print("\n3. Scalability benchmark...")
    await runner.run_scalability_benchmark(
        adapter=adapter,
        request=sample_request,
        concurrency_levels=[1, 10, 50, 100],
        iterations_per_level=50,
        benchmark_name="scalability_test",
    )

    # Save and print results
    output_file = runner.save_results()
    print(f"\nResults saved to: {output_file}")
    runner.print_summary()

    return runner
