#!/usr/bin/env python3
"""
Performance Regression Checker

Checks if the latest benchmark results show any performance regressions
compared to historical data.

Exit codes:
    0: No regressions detected
    1: Regressions detected
    2: Error reading data

Usage:
    python scripts/check_performance_regression.py [--threshold 10.0]
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


def load_history(history_file: Path, limit: int = 5) -> List[Dict[str, Any]]:
    """Load benchmark history from JSONL file"""
    if not history_file.exists():
        return []

    history = []
    with open(history_file, 'r') as f:
        for line in f:
            history.append(json.loads(line))

    return history[-limit:] if limit else history


def check_regressions(
    current: Dict[str, Any],
    history: List[Dict[str, Any]],
    threshold_percent: float = 10.0
) -> List[Dict[str, Any]]:
    """
    Check for performance regressions

    Args:
        current: Current benchmark results
        history: Historical benchmark results
        threshold_percent: Regression threshold (e.g., 10.0 = 10% slower)

    Returns:
        List of regressions found
    """
    if len(history) < 2:
        print("⚠️  Not enough historical data for regression detection")
        return []

    # Get previous run
    previous = history[-2]

    regressions = []

    # Build lookup for previous results
    prev_results = {r['name']: r for r in previous.get('results', [])}

    for current_result in current.get('results', []):
        name = current_result['name']
        if name not in prev_results:
            continue

        prev_p95 = prev_results[name]['p95_ms']
        curr_p95 = current_result['p95_ms']

        # Calculate percent change
        if prev_p95 > 0:
            percent_change = ((curr_p95 - prev_p95) / prev_p95) * 100

            if percent_change > threshold_percent:
                regressions.append({
                    'name': name,
                    'previous_p95_ms': prev_p95,
                    'current_p95_ms': curr_p95,
                    'percent_change': percent_change,
                    'threshold_percent': threshold_percent
                })

    return regressions


def main():
    parser = argparse.ArgumentParser(description='Check for performance regressions')
    parser.add_argument(
        '--threshold',
        type=float,
        default=10.0,
        help='Regression threshold in percent (default: 10.0)'
    )
    parser.add_argument(
        '--report-dir',
        type=str,
        default='reports/performance',
        help='Performance reports directory'
    )
    args = parser.parse_args()

    # Paths
    report_dir = Path(args.report_dir)
    latest_file = report_dir / 'latest_benchmark.json'
    history_file = report_dir / 'benchmark_history.jsonl'

    # Load current results
    if not latest_file.exists():
        print(f"❌ Latest benchmark file not found: {latest_file}")
        return 2

    with open(latest_file, 'r') as f:
        current = json.load(f)

    # Load history
    history = load_history(history_file, limit=5)

    # Check for regressions
    regressions = check_regressions(current, history, args.threshold)

    # Report
    print("=" * 80)
    print("Performance Regression Check")
    print("=" * 80)
    print(f"Suite: {current.get('suite_name', 'Unknown')}")
    print(f"Timestamp: {current.get('timestamp', 'Unknown')}")
    print(f"Commit: {current.get('git_commit', 'Unknown')}")
    print(f"Threshold: {args.threshold}%")
    print("=" * 80)

    if not regressions:
        print("\n✅ No performance regressions detected\n")
        return 0

    print(f"\n❌ {len(regressions)} REGRESSION(S) DETECTED:\n")

    for reg in regressions:
        print(f"  {reg['name']}:")
        print(f"    Previous: {reg['previous_p95_ms']:.2f}ms")
        print(f"    Current:  {reg['current_p95_ms']:.2f}ms")
        print(f"    Change:   +{reg['percent_change']:.1f}% (threshold: {reg['threshold_percent']}%)")
        print()

    print("=" * 80)
    return 1


if __name__ == '__main__':
    sys.exit(main())
