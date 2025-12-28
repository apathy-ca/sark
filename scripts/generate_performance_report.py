#!/usr/bin/env python3
"""
Performance Report Generator

Aggregates performance test results and generates comprehensive report.

Usage:
    python scripts/generate_performance_report.py
    python scripts/generate_performance_report.py --output docs/v1.4.0/PERFORMANCE_REPORT_FINAL.md
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class PerformanceReportGenerator:
    """Generates performance reports from test results."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.results = {
            "benchmarks": {},
            "load_tests": {},
            "stress_tests": {},
            "memory_tests": {},
        }

    def collect_benchmark_results(self):
        """Collect pytest-benchmark results."""
        benchmark_dir = self.base_dir / "tests/performance/benchmarks/reports"
        if not benchmark_dir.exists():
            print(f"⚠️  No benchmark results found in {benchmark_dir}")
            return

        # Look for .json files from pytest-benchmark
        json_files = list(benchmark_dir.glob("*.json"))
        if not json_files:
            print(f"⚠️  No benchmark JSON files found")
            return

        print(f"Found {len(json_files)} benchmark result files")

        # Parse most recent file
        latest = max(json_files, key=lambda p: p.stat().st_mtime)
        with open(latest) as f:
            data = json.load(f)
            self.results["benchmarks"] = data

        print(f"✓ Loaded benchmark results from {latest.name}")

    def collect_load_test_results(self):
        """Collect Locust load test results."""
        load_dir = self.base_dir / "tests/performance/load/reports"
        if not load_dir.exists():
            print(f"⚠️  No load test results found in {load_dir}")
            return

        # Look for CSV files from Locust
        csv_files = list(load_dir.glob("*_stats.csv"))
        if not csv_files:
            print(f"⚠️  No load test CSV files found")
            return

        print(f"Found {len(csv_files)} load test result files")

        # Parse most recent stats file
        latest = max(csv_files, key=lambda p: p.stat().st_mtime)
        self.results["load_tests"]["file"] = str(latest)

        print(f"✓ Found load test results at {latest.name}")

    def collect_memory_results(self):
        """Collect memory profiling results."""
        memory_dir = self.base_dir / "tests/performance/memory/reports"
        if not memory_dir.exists():
            print(f"⚠️  No memory test results found in {memory_dir}")
            return

        txt_files = list(memory_dir.glob("*.txt"))
        if not txt_files:
            print(f"⚠️  No memory test result files found")
            return

        print(f"Found {len(txt_files)} memory test result files")

        # Categorize by test type
        for f in txt_files:
            if "short" in f.name:
                self.results["memory_tests"]["short"] = str(f)
            elif "long" in f.name:
                self.results["memory_tests"]["long"] = str(f)
            elif "comparison" in f.name:
                self.results["memory_tests"]["comparison"] = str(f)

        print(f"✓ Found {len(self.results['memory_tests'])} memory test categories")

    def analyze_benchmarks(self) -> Dict[str, Any]:
        """Analyze benchmark data and extract key metrics."""
        if not self.results["benchmarks"]:
            return {}

        analysis = {
            "opa_simple": {"python": {}, "rust": {}},
            "opa_complex": {"python": {}, "rust": {}},
            "cache_get": {"redis": {}, "rust": {}},
            "cache_set": {"redis": {}, "rust": {}},
        }

        benchmarks = self.results["benchmarks"].get("benchmarks", [])

        for bench in benchmarks:
            name = bench.get("name", "")
            stats = bench.get("stats", {})

            # Categorize benchmark
            if "opa" in name and "simple" in name:
                if "python" in name or "http" in name:
                    analysis["opa_simple"]["python"] = stats
                elif "rust" in name:
                    analysis["opa_simple"]["rust"] = stats

            elif "opa" in name and "complex" in name:
                if "python" in name or "http" in name:
                    analysis["opa_complex"]["python"] = stats
                elif "rust" in name:
                    analysis["opa_complex"]["rust"] = stats

            elif "cache" in name and "get" in name:
                if "redis" in name:
                    analysis["cache_get"]["redis"] = stats
                elif "rust" in name:
                    analysis["cache_get"]["rust"] = stats

            elif "cache" in name and "set" in name:
                if "redis" in name:
                    analysis["cache_set"]["redis"] = stats
                elif "rust" in name:
                    analysis["cache_set"]["rust"] = stats

        return analysis

    def calculate_improvements(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance improvements."""
        improvements = {}

        for category, data in analysis.items():
            if not data:
                continue

            baseline_key = "python" if "opa" in category else "redis"
            improved_key = "rust"

            baseline = data.get(baseline_key, {})
            improved = data.get(improved_key, {})

            if baseline and improved:
                baseline_mean = baseline.get("mean", 0)
                improved_mean = improved.get("mean", 0)

                if improved_mean > 0:
                    speedup = baseline_mean / improved_mean
                    improvements[category] = {
                        "speedup": round(speedup, 2),
                        "baseline_ms": round(baseline_mean * 1000, 2),
                        "improved_ms": round(improved_mean * 1000, 2),
                    }

        return improvements

    def generate_report(self, output_file: Path):
        """Generate the performance report."""
        print(f"\n{'=' * 80}")
        print("GENERATING PERFORMANCE REPORT")
        print(f"{'=' * 80}\n")

        # Collect all results
        self.collect_benchmark_results()
        self.collect_load_test_results()
        self.collect_memory_results()

        # Analyze results
        analysis = self.analyze_benchmarks()
        improvements = self.calculate_improvements(analysis)

        # Read template
        template_path = self.base_dir / "docs/v1.4.0/PERFORMANCE_REPORT.md"
        if not template_path.exists():
            print(f"❌ Template not found: {template_path}")
            return False

        with open(template_path) as f:
            content = f.read()

        # Fill in data (basic replacement for now)
        content = content.replace("[Start Date]", datetime.now().strftime("%Y-%m-%d"))
        content = content.replace("[End Date]", datetime.now().strftime("%Y-%m-%d"))
        content = content.replace("[Environment Details]", "Test Environment")

        # Add improvement data
        if improvements:
            print("\n📊 Performance Improvements Found:")
            for category, data in improvements.items():
                print(f"  {category}: {data['speedup']}x faster")
                print(f"    Baseline: {data['baseline_ms']}ms")
                print(f"    Improved: {data['improved_ms']}ms")

        # Write output
        with open(output_file, "w") as f:
            f.write(content)

        print(f"\n✅ Report generated: {output_file}")
        print(f"\n{'=' * 80}")
        print("NEXT STEPS:")
        print(f"{'=' * 80}")
        print("1. Review the generated report")
        print("2. Fill in missing data with actual test results")
        print("3. Generate performance charts")
        print("4. Add detailed analysis and recommendations")
        print(f"{'=' * 80}\n")

        return True


def main():
    parser = argparse.ArgumentParser(description="Generate performance report")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/v1.4.0/PERFORMANCE_REPORT_GENERATED.md"),
        help="Output file path",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("."),
        help="Base directory of the project",
    )

    args = parser.parse_args()

    # Ensure we're in the right directory
    if not (args.base_dir / "tests/performance").exists():
        print("❌ Error: tests/performance directory not found")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Base directory: {args.base_dir.absolute()}")
        sys.exit(1)

    # Generate report
    generator = PerformanceReportGenerator(args.base_dir)
    success = generator.generate_report(args.output)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
