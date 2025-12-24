#!/usr/bin/env python3
"""
Performance Comparison Tool

Compare two benchmark results and generate a comparison report.

Usage:
    python scripts/compare_performance.py baseline.json current.json
    python scripts/compare_performance.py ./baseline ./current
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List


def load_benchmark(path: Path) -> Dict[str, Any]:
    """Load benchmark from file or directory"""
    if path.is_dir():
        # Look for latest_benchmark.json in directory
        benchmark_file = path / 'latest_benchmark.json'
        if not benchmark_file.exists():
            raise FileNotFoundError(f"No latest_benchmark.json found in {path}")
        path = benchmark_file

    with open(path, 'r') as f:
        return json.load(f)


def compare_benchmarks(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two benchmark results"""
    baseline_results = {r['name']: r for r in baseline.get('results', [])}
    current_results = {r['name']: r for r in current.get('results', [])}

    comparisons = []

    for name in current_results.keys():
        curr = current_results[name]

        if name not in baseline_results:
            comparisons.append({
                'name': name,
                'status': 'new',
                'current_p95': curr['p95_ms'],
                'baseline_p95': None,
                'change_percent': None,
                'change_ms': None
            })
            continue

        base = baseline_results[name]

        change_ms = curr['p95_ms'] - base['p95_ms']
        change_percent = ((curr['p95_ms'] - base['p95_ms']) / base['p95_ms'] * 100) if base['p95_ms'] > 0 else 0

        # Determine status
        if change_percent > 10:
            status = 'regression'
        elif change_percent < -10:
            status = 'improvement'
        else:
            status = 'stable'

        comparisons.append({
            'name': name,
            'status': status,
            'current_p95': curr['p95_ms'],
            'baseline_p95': base['p95_ms'],
            'change_percent': change_percent,
            'change_ms': change_ms
        })

    return {
        'baseline': baseline,
        'current': current,
        'comparisons': comparisons
    }


def generate_markdown_report(comparison: Dict[str, Any]) -> str:
    """Generate markdown comparison report"""
    baseline = comparison['baseline']
    current = comparison['current']
    comparisons = comparison['comparisons']

    # Sort by change percent (worst first)
    comparisons.sort(key=lambda x: x['change_percent'] if x['change_percent'] is not None else -1000, reverse=True)

    md = "## 📊 Performance Comparison\n\n"

    # Summary
    md += f"**Baseline**: {baseline.get('git_commit', 'unknown')} ({baseline.get('timestamp', 'unknown')})\n"
    md += f"**Current**: {current.get('git_commit', 'unknown')} ({current.get('timestamp', 'unknown')})\n\n"

    # Statistics
    regressions = [c for c in comparisons if c['status'] == 'regression']
    improvements = [c for c in comparisons if c['status'] == 'improvement']
    stable = [c for c in comparisons if c['status'] == 'stable']
    new = [c for c in comparisons if c['status'] == 'new']

    md += f"- **Regressions**: {len(regressions)} ❌\n"
    md += f"- **Improvements**: {len(improvements)} ✅\n"
    md += f"- **Stable**: {len(stable)} ➡️\n"
    md += f"- **New**: {len(new)} 🆕\n\n"

    # Overall verdict
    if regressions:
        md += "### ⚠️ Regressions Detected\n\n"
        for comp in regressions:
            md += f"- **{comp['name']}**: {comp['baseline_p95']:.2f}ms → {comp['current_p95']:.2f}ms "
            md += f"(+{comp['change_percent']:.1f}%, +{comp['change_ms']:.2f}ms)\n"
        md += "\n"

    if improvements:
        md += "### 🎉 Improvements\n\n"
        for comp in improvements:
            md += f"- **{comp['name']}**: {comp['baseline_p95']:.2f}ms → {comp['current_p95']:.2f}ms "
            md += f"({comp['change_percent']:.1f}%, {comp['change_ms']:.2f}ms)\n"
        md += "\n"

    # Detailed table
    md += "### Detailed Results\n\n"
    md += "| Benchmark | Baseline (ms) | Current (ms) | Change | Status |\n"
    md += "|-----------|---------------|--------------|--------|--------|\n"

    for comp in comparisons:
        name = comp['name']
        baseline_p95 = f"{comp['baseline_p95']:.2f}" if comp['baseline_p95'] is not None else "N/A"
        current_p95 = f"{comp['current_p95']:.2f}"

        if comp['change_percent'] is not None:
            change = f"{comp['change_percent']:+.1f}%"
        else:
            change = "N/A"

        status_icons = {
            'regression': '❌',
            'improvement': '✅',
            'stable': '➡️',
            'new': '🆕'
        }
        status = status_icons.get(comp['status'], '❓')

        md += f"| {name} | {baseline_p95} | {current_p95} | {change} | {status} |\n"

    return md


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_performance.py <baseline> <current>")
        print("  baseline: Path to baseline benchmark JSON or directory")
        print("  current:  Path to current benchmark JSON or directory")
        return 1

    baseline_path = Path(sys.argv[1])
    current_path = Path(sys.argv[2])

    try:
        baseline = load_benchmark(baseline_path)
        current = load_benchmark(current_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}", file=sys.stderr)
        return 1

    comparison = compare_benchmarks(baseline, current)
    report = generate_markdown_report(comparison)

    print(report)

    # Exit with error code if regressions detected
    regressions = [c for c in comparison['comparisons'] if c['status'] == 'regression']
    return 1 if regressions else 0


if __name__ == '__main__':
    sys.exit(main())
