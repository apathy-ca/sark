"""
SARK Performance Testing Framework

Reusable framework for creating, running, and tracking performance benchmarks.

Usage:
    from tests.performance.framework import Benchmark, BenchmarkRunner

    class MyBenchmark(Benchmark):
        def setup(self):
            self.data = {"key": "value"}

        def run(self):
            # Code to benchmark
            process_data(self.data)

    runner = BenchmarkRunner()
    runner.add_benchmark(MyBenchmark(name="My Benchmark", target_ms=5.0))
    results = runner.run_all()
"""

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import statistics
import time
from typing import Any

import yaml

from .benchmark_report import BenchmarkReporter, BenchmarkResult, BenchmarkSuite


class Benchmark(ABC):
    """
    Base class for performance benchmarks

    Subclass this to create custom benchmarks:

    class MyBenchmark(Benchmark):
        def setup(self):
            self.detector = PromptInjectionDetector()

        def run(self):
            self.detector.detect({"query": "test"})
    """

    def __init__(
        self,
        name: str,
        target_ms: float | None = None,
        iterations: int = 1000,
        warmup: int = 100,
        description: str = "",
    ):
        """
        Args:
            name: Benchmark name
            target_ms: Target latency threshold (p95)
            iterations: Number of iterations to run
            warmup: Number of warmup iterations
            description: Human-readable description
        """
        self.name = name
        self.target_ms = target_ms
        self.iterations = iterations
        self.warmup = warmup
        self.description = description
        self._latencies: list[float] = []

    def setup(self):
        """Override to set up benchmark (called once before warmup)"""
        pass

    def teardown(self):
        """Override to clean up after benchmark (called once after all iterations)"""
        pass

    @abstractmethod
    def run(self):
        """Override with code to benchmark (called for each iteration)"""
        pass

    def execute(self) -> list[float]:
        """Execute benchmark and return latencies in milliseconds"""
        self.setup()

        # Warmup
        for _ in range(self.warmup):
            self.run()

        # Measure
        latencies = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            self.run()
            latencies.append((time.perf_counter() - start) * 1000)  # Convert to ms

        self.teardown()
        self._latencies = latencies
        return latencies


class AsyncBenchmark(ABC):
    """Base class for async benchmarks"""

    def __init__(
        self,
        name: str,
        target_ms: float | None = None,
        iterations: int = 1000,
        warmup: int = 100,
        description: str = "",
    ):
        self.name = name
        self.target_ms = target_ms
        self.iterations = iterations
        self.warmup = warmup
        self.description = description
        self._latencies: list[float] = []

    async def setup(self):
        """Override to set up benchmark"""
        pass

    async def teardown(self):
        """Override to clean up after benchmark"""
        pass

    @abstractmethod
    async def run(self):
        """Override with async code to benchmark"""
        pass

    async def execute(self) -> list[float]:
        """Execute async benchmark and return latencies"""
        await self.setup()

        # Warmup
        for _ in range(self.warmup):
            await self.run()

        # Measure
        latencies = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            await self.run()
            latencies.append((time.perf_counter() - start) * 1000)

        await self.teardown()
        self._latencies = latencies
        return latencies


@dataclass
class BenchmarkScenario:
    """Benchmark scenario loaded from configuration"""

    name: str
    target_ms: float
    iterations: int = 1000
    warmup: int = 100
    description: str = ""
    params: dict[str, Any] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


class BenchmarkRunner:
    """
    Run and manage collections of benchmarks

    Usage:
        runner = BenchmarkRunner()
        runner.add_benchmark(MyBenchmark(...))
        results = runner.run_all()
        runner.generate_report(results)
    """

    def __init__(
        self, reporter: BenchmarkReporter | None = None, suite_name: str = "Performance Benchmarks"
    ):
        """
        Args:
            reporter: BenchmarkReporter instance (creates default if None)
            suite_name: Name for the benchmark suite
        """
        self.reporter = reporter or BenchmarkReporter()
        self.suite_name = suite_name
        self.benchmarks: list[Benchmark] = []
        self.async_benchmarks: list[AsyncBenchmark] = []

    def add_benchmark(self, benchmark: Benchmark):
        """Add a synchronous benchmark"""
        self.benchmarks.append(benchmark)

    def add_async_benchmark(self, benchmark: AsyncBenchmark):
        """Add an async benchmark"""
        self.async_benchmarks.append(benchmark)

    def run_all(self, verbose: bool = True) -> BenchmarkSuite:
        """
        Run all benchmarks and return results

        Args:
            verbose: Print progress to console

        Returns:
            BenchmarkSuite with all results
        """
        from datetime import datetime

        from .benchmark_report import get_git_commit

        results = []

        # Run sync benchmarks
        for benchmark in self.benchmarks:
            if verbose:
                print(f"Running: {benchmark.name}...")

            latencies = benchmark.execute()
            result = self.reporter.create_result(
                name=benchmark.name, latencies_ms=latencies, target_ms=benchmark.target_ms
            )
            results.append(result)

            if verbose:
                status = "✅ PASS" if result.passed else "❌ FAIL"
                print(
                    f"  → P95: {result.p95_ms:.2f}ms | Target: {benchmark.target_ms:.1f}ms | {status}"
                )

        # Run async benchmarks
        if self.async_benchmarks:
            if verbose:
                print("\nRunning async benchmarks...")

            async def run_async():
                async_results = []
                for benchmark in self.async_benchmarks:
                    if verbose:
                        print(f"Running: {benchmark.name}...")

                    latencies = await benchmark.execute()
                    result = self.reporter.create_result(
                        name=benchmark.name, latencies_ms=latencies, target_ms=benchmark.target_ms
                    )
                    async_results.append(result)

                    if verbose:
                        status = "✅ PASS" if result.passed else "❌ FAIL"
                        print(
                            f"  → P95: {result.p95_ms:.2f}ms | Target: {benchmark.target_ms:.1f}ms | {status}"
                        )

                return async_results

            async_results = asyncio.run(run_async())
            results.extend(async_results)

        # Create suite
        suite = BenchmarkSuite(
            suite_name=self.suite_name,
            results=results,
            timestamp=datetime.now().isoformat(),
            git_commit=get_git_commit(),
        )

        return suite

    def generate_report(
        self,
        suite: BenchmarkSuite,
        console: bool = True,
        html: bool = True,
        json_output: bool = True,
    ) -> dict[str, str]:
        """
        Generate reports in multiple formats

        Args:
            suite: BenchmarkSuite to report
            console: Print to console
            html: Generate HTML report
            json_output: Save JSON report

        Returns:
            Dict with paths to generated files
        """
        paths = {}

        # Save to history
        self.reporter.save_suite(suite)
        paths["json"] = str(self.reporter.output_dir / "latest_benchmark.json")

        # Console report
        if console:
            self.reporter.print_report(suite)

        # HTML report
        if html:
            html_path = self.reporter.generate_html_report(suite)
            paths["html"] = html_path

        return paths

    def load_scenarios(self, config_path: str) -> list[BenchmarkScenario]:
        """
        Load benchmark scenarios from YAML/JSON configuration

        Args:
            config_path: Path to configuration file (.yaml or .json)

        Returns:
            List of BenchmarkScenario objects
        """
        path = Path(config_path)

        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        scenarios = []
        for scenario_data in data.get("scenarios", []):
            scenarios.append(BenchmarkScenario(**scenario_data))

        return scenarios


class FunctionBenchmark(Benchmark):
    """
    Benchmark a simple function

    Usage:
        def my_func():
            expensive_operation()

        benchmark = FunctionBenchmark(
            name="My Operation",
            func=my_func,
            target_ms=5.0
        )
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        target_ms: float | None = None,
        iterations: int = 1000,
        warmup: int = 100,
        setup_func: Callable | None = None,
        teardown_func: Callable | None = None,
    ):
        super().__init__(name, target_ms, iterations, warmup)
        self.func = func
        self.setup_func = setup_func
        self.teardown_func = teardown_func

    def setup(self):
        if self.setup_func:
            self.setup_func()

    def run(self):
        self.func()

    def teardown(self):
        if self.teardown_func:
            self.teardown_func()


class ComparisonBenchmark:
    """
    Compare multiple implementations

    Usage:
        comparison = ComparisonBenchmark("Sort Algorithms")
        comparison.add_implementation("Bubble Sort", bubble_sort)
        comparison.add_implementation("Quick Sort", quick_sort)
        results = comparison.run(runner)
    """

    def __init__(self, name: str, iterations: int = 1000, warmup: int = 100):
        self.name = name
        self.iterations = iterations
        self.warmup = warmup
        self.implementations: list[tuple[str, Callable]] = []

    def add_implementation(self, name: str, func: Callable):
        """Add an implementation to compare"""
        self.implementations.append((name, func))

    def run(self, runner: BenchmarkRunner) -> list[BenchmarkResult]:
        """Run all implementations and return results"""
        results = []

        for impl_name, func in self.implementations:
            benchmark = FunctionBenchmark(
                name=f"{self.name} - {impl_name}",
                func=func,
                iterations=self.iterations,
                warmup=self.warmup,
            )
            runner.add_benchmark(benchmark)

        return results


# Utility functions for common benchmark patterns


def benchmark_function(
    func: Callable,
    name: str,
    target_ms: float | None = None,
    iterations: int = 1000,
    warmup: int = 100,
) -> BenchmarkResult:
    """
    Quick benchmark a single function

    Args:
        func: Function to benchmark
        name: Benchmark name
        target_ms: Target threshold
        iterations: Number of iterations
        warmup: Warmup iterations

    Returns:
        BenchmarkResult
    """
    benchmark = FunctionBenchmark(name, func, target_ms, iterations, warmup)
    latencies = benchmark.execute()

    reporter = BenchmarkReporter()
    return reporter.create_result(name, latencies, target_ms)


def quick_benchmark(func: Callable, iterations: int = 100) -> dict[str, float]:
    """
    Quick and dirty benchmark - returns simple stats

    Args:
        func: Function to benchmark
        iterations: Number of iterations (default 100)

    Returns:
        Dict with p50, p95, p99 in milliseconds
    """
    latencies = []

    # Warmup
    for _ in range(10):
        func()

    # Measure
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        latencies.append((time.perf_counter() - start) * 1000)

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    return {
        "p50": sorted_latencies[int(n * 0.5)],
        "p95": sorted_latencies[int(n * 0.95)],
        "p99": sorted_latencies[int(n * 0.99)],
        "mean": statistics.mean(sorted_latencies),
    }
