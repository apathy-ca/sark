#!/usr/bin/env python3
"""
Performance Test Results Analyzer

This script analyzes performance test results from Locust CSV output
and checks against defined thresholds.

Usage:
    python analyze_results.py --csv reports/performance_stats_stats.csv
    python analyze_results.py --csv reports/performance_stats_stats.csv --p95-threshold 100
    python analyze_results.py --csv reports/performance_stats_stats.csv --fail-on-threshold
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PerformanceThresholds:
    """Performance thresholds for different operations."""

    api_p95_ms: float = 100.0
    server_registration_p95_ms: float = 200.0
    policy_evaluation_p95_ms: float = 50.0
    error_rate_percent: float = 1.0
    min_throughput_rps: float = 100.0


@dataclass
class PerformanceMetrics:
    """Performance metrics from test results."""

    name: str
    requests: int
    failures: int
    median_ms: float
    p95_ms: float
    p99_ms: float
    average_ms: float
    min_ms: float
    max_ms: float
    rps: float
    failure_rate: float


class ResultsAnalyzer:
    """Analyze performance test results."""

    def __init__(self, thresholds: PerformanceThresholds):
        """Initialize analyzer with thresholds."""
        self.thresholds = thresholds
        self.metrics: list[PerformanceMetrics] = []

    def load_locust_csv(self, csv_path: Path) -> None:
        """Load Locust CSV stats file."""
        print(f"Loading results from {csv_path}...")

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Skip aggregated rows
                if row["Name"] == "Aggregated":
                    continue

                # Parse metrics
                try:
                    metric = PerformanceMetrics(
                        name=row["Name"],
                        requests=int(row["Request Count"]),
                        failures=int(row["Failure Count"]),
                        median_ms=float(row["Median Response Time"]),
                        p95_ms=float(row["95%"]),
                        p99_ms=float(row["99%"]) if row["99%"] else 0,
                        average_ms=float(row["Average Response Time"]),
                        min_ms=float(row["Min Response Time"]),
                        max_ms=float(row["Max Response Time"]),
                        rps=float(row["Requests/s"]) if row["Requests/s"] else 0,
                        failure_rate=float(row["Failure Count"]) / float(row["Request Count"]) * 100
                        if int(row["Request Count"]) > 0
                        else 0,
                    )
                    self.metrics.append(metric)
                except (ValueError, KeyError) as e:
                    print(f"Warning: Could not parse row: {e}")
                    continue

        print(f"Loaded {len(self.metrics)} endpoints\n")

    def print_summary(self) -> None:
        """Print results summary."""
        print("=" * 80)
        print("PERFORMANCE TEST RESULTS SUMMARY")
        print("=" * 80)
        print()

        # Overall statistics
        total_requests = sum(m.requests for m in self.metrics)
        total_failures = sum(m.failures for m in self.metrics)
        overall_failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0

        print(f"Total Requests:    {total_requests:,}")
        print(f"Total Failures:    {total_failures:,}")
        print(f"Overall Error Rate: {overall_failure_rate:.2f}%")
        print()

        # Per-endpoint results
        print("-" * 80)
        print(f"{'Endpoint':<40} {'Requests':>10} {'p50':>8} {'p95':>8} {'p99':>8} {'RPS':>8}")
        print("-" * 80)

        for metric in sorted(self.metrics, key=lambda m: m.p95_ms, reverse=True):
            print(
                f"{metric.name[:40]:<40} "
                f"{metric.requests:>10,} "
                f"{metric.median_ms:>8.0f} "
                f"{metric.p95_ms:>8.0f} "
                f"{metric.p99_ms:>8.0f} "
                f"{metric.rps:>8.1f}"
            )

        print("-" * 80)
        print()

    def check_thresholds(self) -> dict[str, Any]:
        """Check results against thresholds."""
        print("=" * 80)
        print("THRESHOLD CHECKS")
        print("=" * 80)
        print()

        results = {
            "passed": [],
            "failed": [],
            "warnings": [],
            "overall_pass": True,
        }

        # Check overall error rate
        total_requests = sum(m.requests for m in self.metrics)
        total_failures = sum(m.failures for m in self.metrics)
        overall_failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0

        print(f"Overall Error Rate: {overall_failure_rate:.2f}% (threshold: {self.thresholds.error_rate_percent}%)")

        if overall_failure_rate <= self.thresholds.error_rate_percent:
            print("  ✅ PASS: Error rate within threshold")
            results["passed"].append("Overall error rate")
        else:
            print("  ❌ FAIL: Error rate exceeds threshold")
            results["failed"].append("Overall error rate")
            results["overall_pass"] = False

        print()

        # Check specific endpoints
        for metric in self.metrics:
            endpoint_name = metric.name.lower()

            # Determine threshold based on endpoint
            if "server" in endpoint_name and "register" in endpoint_name:
                threshold = self.thresholds.server_registration_p95_ms
                threshold_name = "Server Registration p95"
            elif "policy" in endpoint_name and "evaluate" in endpoint_name:
                threshold = self.thresholds.policy_evaluation_p95_ms
                threshold_name = "Policy Evaluation p95"
            else:
                threshold = self.thresholds.api_p95_ms
                threshold_name = "API p95"

            # Check p95 latency
            print(f"{metric.name}:")
            print(f"  p95: {metric.p95_ms:.0f}ms (threshold: {threshold}ms)")

            if metric.p95_ms <= threshold:
                print(f"  ✅ PASS: {threshold_name}")
                results["passed"].append(f"{metric.name} - {threshold_name}")
            else:
                print(f"  ❌ FAIL: {threshold_name}")
                results["failed"].append(f"{metric.name} - {threshold_name}")
                results["overall_pass"] = False

            # Check failure rate
            if metric.failure_rate > 0:
                if metric.failure_rate <= self.thresholds.error_rate_percent:
                    print(f"  ⚠️  WARNING: {metric.failure_rate:.2f}% error rate")
                    results["warnings"].append(f"{metric.name} - error rate")
                else:
                    print(f"  ❌ FAIL: {metric.failure_rate:.2f}% error rate exceeds threshold")
                    results["failed"].append(f"{metric.name} - error rate")
                    results["overall_pass"] = False

            print()

        return results

    def generate_report(self, output_path: Path) -> None:
        """Generate JSON report."""
        report = {
            "summary": {
                "total_requests": sum(m.requests for m in self.metrics),
                "total_failures": sum(m.failures for m in self.metrics),
                "overall_failure_rate": (
                    sum(m.failures for m in self.metrics) / sum(m.requests for m in self.metrics) * 100
                    if sum(m.requests for m in self.metrics) > 0
                    else 0
                ),
                "total_endpoints": len(self.metrics),
            },
            "endpoints": [
                {
                    "name": m.name,
                    "requests": m.requests,
                    "failures": m.failures,
                    "failure_rate": m.failure_rate,
                    "latency": {
                        "min": m.min_ms,
                        "median": m.median_ms,
                        "average": m.average_ms,
                        "p95": m.p95_ms,
                        "p99": m.p99_ms,
                        "max": m.max_ms,
                    },
                    "throughput_rps": m.rps,
                }
                for m in self.metrics
            ],
            "thresholds": {
                "api_p95_ms": self.thresholds.api_p95_ms,
                "server_registration_p95_ms": self.thresholds.server_registration_p95_ms,
                "policy_evaluation_p95_ms": self.thresholds.policy_evaluation_p95_ms,
                "error_rate_percent": self.thresholds.error_rate_percent,
            },
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Report saved to {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze performance test results")
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to Locust stats CSV file",
    )
    parser.add_argument(
        "--p95-threshold",
        type=float,
        default=100.0,
        help="Default p95 threshold in milliseconds (default: 100)",
    )
    parser.add_argument(
        "--server-reg-p95",
        type=float,
        default=200.0,
        help="Server registration p95 threshold in milliseconds (default: 200)",
    )
    parser.add_argument(
        "--policy-eval-p95",
        type=float,
        default=50.0,
        help="Policy evaluation p95 threshold in milliseconds (default: 50)",
    )
    parser.add_argument(
        "--error-rate",
        type=float,
        default=1.0,
        help="Maximum acceptable error rate percentage (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--fail-on-threshold",
        action="store_true",
        help="Exit with error code if thresholds are exceeded",
    )

    args = parser.parse_args()

    # Validate CSV file exists
    if not args.csv.exists():
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)

    # Create thresholds
    thresholds = PerformanceThresholds(
        api_p95_ms=args.p95_threshold,
        server_registration_p95_ms=args.server_reg_p95,
        policy_evaluation_p95_ms=args.policy_eval_p95,
        error_rate_percent=args.error_rate,
    )

    # Analyze results
    analyzer = ResultsAnalyzer(thresholds)
    analyzer.load_locust_csv(args.csv)
    analyzer.print_summary()

    # Check thresholds
    threshold_results = analyzer.check_thresholds()

    # Generate JSON report if requested
    if args.output:
        analyzer.generate_report(args.output)

    # Print final summary
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Checks Passed: {len(threshold_results['passed'])}")
    print(f"Checks Failed: {len(threshold_results['failed'])}")
    print(f"Warnings:      {len(threshold_results['warnings'])}")
    print()

    if threshold_results["overall_pass"]:
        print("✅ ALL CHECKS PASSED")
        exit_code = 0
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        print("Failed checks:")
        for failure in threshold_results["failed"]:
            print(f"  - {failure}")
        exit_code = 1 if args.fail_on_threshold else 0

    print("=" * 80)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
