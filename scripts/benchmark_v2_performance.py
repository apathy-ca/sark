#!/usr/bin/env python3
"""
SARK v2.0 Database Performance Benchmark

Benchmarks the performance of polymorphic resource/capability schema queries
to ensure they meet the performance targets defined in PERFORMANCE_OPTIMIZATION.md

Usage:
    python scripts/benchmark_v2_performance.py --full          # Full benchmark suite
    python scripts/benchmark_v2_performance.py --quick         # Quick benchmark
    python scripts/benchmark_v2_performance.py --report        # Generate report only
"""

import argparse
from datetime import UTC, datetime
from decimal import Decimal
import statistics
import time

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from sark.models.base import Capability, CostTracking, FederationNode, Resource


class BenchmarkResult:
    """Stores benchmark results for a single test."""

    def __init__(self, name: str, target_ms: float):
        self.name = name
        self.target_ms = target_ms
        self.measurements: list[float] = []
        self.passed = False

    def add_measurement(self, duration_ms: float):
        self.measurements.append(duration_ms)

    def analyze(self):
        """Calculate statistics and determine pass/fail."""
        if not self.measurements:
            return

        self.min_ms = min(self.measurements)
        self.max_ms = max(self.measurements)
        self.mean_ms = statistics.mean(self.measurements)
        self.median_ms = statistics.median(self.measurements)
        self.p95_ms = sorted(self.measurements)[int(len(self.measurements) * 0.95)]
        self.p99_ms = sorted(self.measurements)[int(len(self.measurements) * 0.99)]

        # Pass if p95 is under target
        self.passed = self.p95_ms < self.target_ms

    def report(self) -> str:
        """Generate text report."""
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"""
{self.name}
{'-' * len(self.name)}
Target: < {self.target_ms}ms
Iterations: {len(self.measurements)}
Min: {self.min_ms:.2f}ms
Max: {self.max_ms:.2f}ms
Mean: {self.mean_ms:.2f}ms
Median: {self.median_ms:.2f}ms
P95: {self.p95_ms:.2f}ms
P99: {self.p99_ms:.2f}ms
Status: {status}
"""


class DatabaseBenchmark:
    """Main benchmark runner."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.results: list[BenchmarkResult] = []

    def setup_test_data(self, num_resources: int = 1000, num_capabilities_per_resource: int = 10):
        """Create test data for benchmarking."""
        print(f"Setting up test data: {num_resources} resources, {num_capabilities_per_resource} capabilities each...")

        # Check if test data already exists
        existing_count = self.session.query(Resource).filter(Resource.id.like('bench-%')).count()
        if existing_count > 0:
            print(f"  Found {existing_count} existing test resources, skipping setup...")
            return

        protocols = ['mcp', 'http', 'grpc']
        sensitivity_levels = ['low', 'medium', 'high', 'critical']

        start = time.time()

        for i in range(num_resources):
            protocol = protocols[i % len(protocols)]
            resource = Resource(
                id=f"bench-{protocol}-{i}",
                name=f"Benchmark {protocol.upper()} Resource {i}",
                protocol=protocol,
                endpoint=f"endpoint-{i}",
                sensitivity_level=sensitivity_levels[i % len(sensitivity_levels)],
                metadata_={
                    "benchmark": True,
                    "index": i,
                    "protocol_specific": f"data-{i}",
                },
            )
            self.session.add(resource)

            # Add capabilities
            for j in range(num_capabilities_per_resource):
                capability = Capability(
                    id=f"bench-cap-{i}-{j}",
                    resource_id=resource.id,
                    name=f"capability_{j}",
                    description=f"Benchmark capability {j}",
                    input_schema={"type": "object", "properties": {}},
                    sensitivity_level=sensitivity_levels[(i + j) % len(sensitivity_levels)],
                    metadata_={"benchmark": True},
                )
                self.session.add(capability)

            if (i + 1) % 100 == 0:
                self.session.commit()
                print(f"  Created {i + 1}/{num_resources} resources...")

        self.session.commit()
        duration = time.time() - start
        print(f"✓ Test data created in {duration:.2f}s")

    def cleanup_test_data(self):
        """Remove benchmark test data."""
        print("Cleaning up test data...")
        self.session.execute(
            text("DELETE FROM capabilities WHERE id LIKE 'bench-%'")
        )
        self.session.execute(
            text("DELETE FROM resources WHERE id LIKE 'bench-%'")
        )
        self.session.commit()
        print("✓ Test data cleaned up")

    def benchmark_resource_lookup_by_id(self, iterations: int = 1000) -> BenchmarkResult:
        """Benchmark: Resource lookup by ID."""
        result = BenchmarkResult("Resource lookup by ID", target_ms=5.0)

        # Get a sample resource ID
        sample_id = self.session.query(Resource.id).filter(Resource.id.like('bench-%')).first()[0]

        for _ in range(iterations):
            start = time.time()
            self.session.query(Resource).get(sample_id)
            duration_ms = (time.time() - start) * 1000
            result.add_measurement(duration_ms)

        result.analyze()
        self.results.append(result)
        return result

    def benchmark_capabilities_by_resource(self, iterations: int = 500) -> BenchmarkResult:
        """Benchmark: Capability lookup by resource."""
        result = BenchmarkResult("Capabilities by resource", target_ms=10.0)

        sample_id = self.session.query(Resource.id).filter(Resource.id.like('bench-%')).first()[0]

        for _ in range(iterations):
            start = time.time()
            (
                self.session.query(Capability)
                .filter(Capability.resource_id == sample_id)
                .all()
            )
            duration_ms = (time.time() - start) * 1000
            result.add_measurement(duration_ms)

        result.analyze()
        self.results.append(result)
        return result

    def benchmark_cross_protocol_query(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark: Cross-protocol aggregation."""
        result = BenchmarkResult("Cross-protocol aggregation", target_ms=50.0)

        for _ in range(iterations):
            start = time.time()
            (
                self.session.query(
                    Resource.protocol,
                    func.count(Capability.id).label('capability_count')
                )
                .outerjoin(Capability, Capability.resource_id == Resource.id)
                .filter(Resource.id.like('bench-%'))
                .group_by(Resource.protocol)
                .all()
            )
            duration_ms = (time.time() - start) * 1000
            result.add_measurement(duration_ms)

        result.analyze()
        self.results.append(result)
        return result

    def benchmark_high_sensitivity_query(self, iterations: int = 200) -> BenchmarkResult:
        """Benchmark: High-sensitivity capability search across protocols."""
        result = BenchmarkResult("High-sensitivity capability search", target_ms=25.0)

        for _ in range(iterations):
            start = time.time()
            (
                self.session.query(Capability, Resource)
                .join(Resource, Resource.id == Capability.resource_id)
                .filter(Capability.sensitivity_level.in_(['high', 'critical']))
                .filter(Resource.id.like('bench-%'))
                .limit(100)
                .all()
            )
            duration_ms = (time.time() - start) * 1000
            result.add_measurement(duration_ms)

        result.analyze()
        self.results.append(result)
        return result

    def benchmark_metadata_jsonb_query(self, iterations: int = 200) -> BenchmarkResult:
        """Benchmark: JSONB metadata containment query."""
        result = BenchmarkResult("JSONB metadata containment", target_ms=15.0)

        for _ in range(iterations):
            start = time.time()
            (
                self.session.query(Resource)
                .filter(Resource.metadata_.op('@>')({"benchmark": True}))
                .limit(100)
                .all()
            )
            duration_ms = (time.time() - start) * 1000
            result.add_measurement(duration_ms)

        result.analyze()
        self.results.append(result)
        return result

    def benchmark_cost_insertion(self, iterations: int = 1000) -> BenchmarkResult:
        """Benchmark: Cost tracking insertion."""
        result = BenchmarkResult("Cost tracking insertion", target_ms=3.0)

        sample_resource = self.session.query(Resource).filter(Resource.id.like('bench-%')).first()
        sample_capability = (
            self.session.query(Capability)
            .filter(Capability.resource_id == sample_resource.id)
            .first()
        )

        for i in range(iterations):
            start = time.time()
            cost = CostTracking(
                principal_id=f"bench-user-{i % 10}",
                resource_id=sample_resource.id,
                capability_id=sample_capability.id,
                estimated_cost=Decimal("0.05"),
                actual_cost=Decimal("0.047"),
                metadata_={"benchmark": True},
            )
            self.session.add(cost)
            if (i + 1) % 100 == 0:
                self.session.commit()
            duration_ms = (time.time() - start) * 1000
            result.add_measurement(duration_ms)

        self.session.commit()
        result.analyze()
        self.results.append(result)

        # Cleanup
        self.session.execute(text("DELETE FROM cost_tracking WHERE metadata->>'benchmark' = 'true'"))
        self.session.commit()

        return result

    def benchmark_federation_node_lookup(self, iterations: int = 500) -> BenchmarkResult:
        """Benchmark: Federation node lookup by node_id."""
        result = BenchmarkResult("Federation node lookup", target_ms=5.0)

        # Create test federation node if it doesn't exist
        existing = self.session.query(FederationNode).filter(FederationNode.node_id == 'bench-org.com').first()
        if not existing:
            node = FederationNode(
                node_id="bench-org.com",
                name="Benchmark Org",
                endpoint="https://bench.example.com",
                trust_anchor_cert="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
                enabled=True,
            )
            self.session.add(node)
            self.session.commit()

        for _ in range(iterations):
            start = time.time()
            node = (
                self.session.query(FederationNode)
                .filter(FederationNode.node_id == 'bench-org.com')
                .first()
            )
            duration_ms = (time.time() - start) * 1000
            result.add_measurement(duration_ms)

        result.analyze()
        self.results.append(result)

        # Cleanup
        self.session.execute(text("DELETE FROM federation_nodes WHERE node_id = 'bench-org.com'"))
        self.session.commit()

        return result

    def run_all_benchmarks(self, quick: bool = False):
        """Run all benchmarks."""
        print("\n" + "=" * 70)
        print("SARK v2.0 Database Performance Benchmark")
        print("=" * 70 + "\n")

        iterations_multiplier = 0.1 if quick else 1.0

        benchmarks = [
            ("Resource lookup by ID", lambda: self.benchmark_resource_lookup_by_id(int(1000 * iterations_multiplier))),
            ("Capabilities by resource", lambda: self.benchmark_capabilities_by_resource(int(500 * iterations_multiplier))),
            ("Cross-protocol aggregation", lambda: self.benchmark_cross_protocol_query(int(100 * iterations_multiplier))),
            ("High-sensitivity search", lambda: self.benchmark_high_sensitivity_query(int(200 * iterations_multiplier))),
            ("JSONB metadata query", lambda: self.benchmark_metadata_jsonb_query(int(200 * iterations_multiplier))),
            ("Cost tracking insertion", lambda: self.benchmark_cost_insertion(int(1000 * iterations_multiplier))),
            ("Federation node lookup", lambda: self.benchmark_federation_node_lookup(int(500 * iterations_multiplier))),
        ]

        for name, bench_fn in benchmarks:
            print(f"\nRunning: {name}...")
            result = bench_fn()
            print(f"  Mean: {result.mean_ms:.2f}ms, P95: {result.p95_ms:.2f}ms, Target: < {result.target_ms}ms")
            print(f"  Status: {'✓ PASS' if result.passed else '✗ FAIL'}")

        print("\n" + "=" * 70)
        print("Benchmark Complete")
        print("=" * 70 + "\n")

    def generate_report(self) -> str:
        """Generate comprehensive benchmark report."""
        report = """
╔══════════════════════════════════════════════════════════════════════╗
║          SARK v2.0 Database Performance Benchmark Report             ║
╚══════════════════════════════════════════════════════════════════════╝

"""
        for result in self.results:
            report += result.report()

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        report += f"""
╔══════════════════════════════════════════════════════════════════════╗
║                            SUMMARY                                   ║
╚══════════════════════════════════════════════════════════════════════╝

Total Tests: {total}
Passed: {passed}
Failed: {total - passed}
Pass Rate: {pass_rate:.1f}%

Status: {'✓ ALL TESTS PASSED' if passed == total else '✗ SOME TESTS FAILED'}

"""
        return report

    def close(self):
        """Close database connection."""
        self.session.close()


def main():
    parser = argparse.ArgumentParser(description="SARK v2.0 database performance benchmark")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full benchmark suite (default)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick benchmark (fewer iterations)",
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Only set up test data",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test data",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env var)",
    )

    args = parser.parse_args()

    import os
    database_url = args.database_url or os.getenv(
        "DATABASE_URL",
        "postgresql://sark:sark@localhost:5432/sark",
    )

    benchmark = DatabaseBenchmark(database_url)

    try:
        if args.cleanup:
            benchmark.cleanup_test_data()
            return

        if args.setup_only:
            benchmark.setup_test_data()
            return

        # Set up test data
        benchmark.setup_test_data()

        # Run benchmarks
        quick = args.quick
        benchmark.run_all_benchmarks(quick=quick)

        # Generate report
        report = benchmark.generate_report()
        print(report)

        # Save report to file
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        report_file = f"benchmark_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n✓ Report saved to: {report_file}")

    finally:
        benchmark.close()


if __name__ == "__main__":
    main()
