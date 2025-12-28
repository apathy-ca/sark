#!/usr/bin/env python3
"""
Performance Regression Detection

Compares current benchmark results against baseline to detect regressions.

Usage:
    python scripts/check_performance_regression.py --current output.json
    python scripts/check_performance_regression.py --current output.json --baseline baseline.json --threshold 0.10
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class PerformanceRegressionError(Exception):
    """Raised when a performance regression is detected."""
    pass


class RegressionDetector:
    """Detects performance regressions in benchmark results."""

    def __init__(self, threshold: float = 0.10):
        self.threshold = threshold
        self.regressions: List[Dict] = []
        self.improvements: List[Dict] = []

    def load_results(self, file_path: Path) -> Dict:
        """Load benchmark results from JSON file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Results file not found: {file_path}")
        with open(file_path) as f:
            return json.load(f)

    def compare_benchmarks(self, current: Dict, baseline: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Compare current benchmarks against baseline."""
        regressions = []
        improvements = []

        current_benchmarks = {b["name"]: b for b in current.get("benchmarks", [])}
        baseline_benchmarks = {b["name"]: b for b in baseline.get("benchmarks", [])}

        for name, current_bench in current_benchmarks.items():
            if name not in baseline_benchmarks:
                continue

            baseline_bench = baseline_benchmarks[name]
            current_mean = current_bench["stats"]["mean"]
            baseline_mean = baseline_bench["stats"]["mean"]

            if baseline_mean > 0:
                regression = (current_mean - baseline_mean) / baseline_mean
                result = {
                    "name": name,
                    "regression_percent": regression * 100,
                    "current_mean_ms": current_mean * 1000,
                    "baseline_mean_ms": baseline_mean * 1000,
                }

                if regression > self.threshold:
                    regressions.append(result)
                elif regression < -self.threshold:
                    improvements.append(result)

        return regressions, improvements

    def print_results(self):
        """Print regression detection results."""
        print(f"\n{'=' * 80}")
        print("PERFORMANCE REGRESSION ANALYSIS")
        print(f"{'=' * 80}\n")

        if not self.regressions and not self.improvements:
            print("✅ No significant performance changes detected")
            return

        if self.improvements:
            print(f"📈 IMPROVEMENTS ({len(self.improvements)} found):")
            for imp in self.improvements:
                print(f"\n✓ {imp['name']}: {abs(imp['regression_percent']):.1f}% faster")

        if self.regressions:
            print(f"\n⚠️  REGRESSIONS ({len(self.regressions)} found):")
            for reg in self.regressions:
                print(f"\n✗ {reg['name']}: {reg['regression_percent']:.1f}% slower")

    def run(self, current_file: Path, baseline_file: Path = None):
        """Run regression detection."""
        current = self.load_results(current_file)

        if baseline_file and baseline_file.exists():
            baseline = self.load_results(baseline_file)
            self.regressions, self.improvements = self.compare_benchmarks(current, baseline)
            self.print_results()

            if self.regressions:
                raise PerformanceRegressionError(f"Detected {len(self.regressions)} regression(s)")

        print("✅ All performance checks passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--threshold", type=float, default=0.10)
    args = parser.parse_args()

    try:
        detector = RegressionDetector(threshold=args.threshold)
        detector.run(args.current, args.baseline)
        sys.exit(0)
    except PerformanceRegressionError as e:
        print(f"\n❌ {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
