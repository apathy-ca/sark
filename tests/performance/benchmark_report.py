"""
Performance Benchmark Reporting

Generates detailed performance reports with historical tracking and regression detection.
"""

import json
import time
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys


@dataclass
class BenchmarkResult:
    """Single benchmark result"""
    name: str
    iterations: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float
    timestamp: str
    passed: bool
    target_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    suite_name: str
    results: List[BenchmarkResult]
    timestamp: str
    git_commit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "suite_name": self.suite_name,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "results": [r.to_dict() for r in self.results]
        }


class BenchmarkReporter:
    """Generate and track performance benchmark reports"""

    def __init__(self, output_dir: str = "reports/performance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.output_dir / "benchmark_history.jsonl"

    def create_result(
        self,
        name: str,
        latencies_ms: List[float],
        target_ms: Optional[float] = None
    ) -> BenchmarkResult:
        """
        Create benchmark result from latency measurements

        Args:
            name: Benchmark name
            latencies_ms: List of latency measurements in milliseconds
            target_ms: Target latency threshold (for pass/fail)

        Returns:
            BenchmarkResult object
        """
        if not latencies_ms:
            raise ValueError("No latency measurements provided")

        sorted_latencies = sorted(latencies_ms)
        n = len(sorted_latencies)

        # Calculate percentiles
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)

        result = BenchmarkResult(
            name=name,
            iterations=n,
            min_ms=min(sorted_latencies),
            max_ms=max(sorted_latencies),
            mean_ms=statistics.mean(sorted_latencies),
            median_ms=statistics.median(sorted_latencies),
            p95_ms=sorted_latencies[p95_idx] if p95_idx < n else sorted_latencies[-1],
            p99_ms=sorted_latencies[p99_idx] if p99_idx < n else sorted_latencies[-1],
            std_dev_ms=statistics.stdev(sorted_latencies) if n > 1 else 0.0,
            timestamp=datetime.now().isoformat(),
            passed=sorted_latencies[p95_idx] <= target_ms if target_ms else True,
            target_ms=target_ms
        )

        return result

    def save_suite(self, suite: BenchmarkSuite):
        """Save benchmark suite to history"""
        # Append to JSONL history file
        with open(self.history_file, 'a') as f:
            f.write(json.dumps(suite.to_dict()) + '\n')

        # Also save latest run as JSON
        latest_file = self.output_dir / "latest_benchmark.json"
        with open(latest_file, 'w') as f:
            json.dump(suite.to_dict(), f, indent=2)

    def load_history(self, limit: Optional[int] = None) -> List[BenchmarkSuite]:
        """Load benchmark history"""
        if not self.history_file.exists():
            return []

        suites = []
        with open(self.history_file, 'r') as f:
            for line in f:
                data = json.loads(line)
                # Reconstruct suite (simplified)
                suites.append(data)

        if limit:
            suites = suites[-limit:]

        return suites

    def detect_regressions(
        self,
        current: BenchmarkSuite,
        threshold_percent: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Detect performance regressions

        Args:
            current: Current benchmark suite
            threshold_percent: Regression threshold (e.g., 10.0 = 10% slower)

        Returns:
            List of regressions found
        """
        history = self.load_history(limit=5)
        if len(history) < 2:
            return []  # Need at least 2 runs to detect regressions

        # Get previous run
        previous = history[-2]

        regressions = []

        # Build lookup for previous results
        prev_results = {r['name']: r for r in previous['results']}

        for current_result in current.results:
            name = current_result.name
            if name not in prev_results:
                continue

            prev_p95 = prev_results[name]['p95_ms']
            curr_p95 = current_result.p95_ms

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

    def print_report(self, suite: BenchmarkSuite):
        """Print formatted benchmark report to console"""
        print("\n" + "=" * 80)
        print(f"SARK v1.3.0 Security Performance Benchmark Report")
        print(f"Suite: {suite.suite_name}")
        print(f"Timestamp: {suite.timestamp}")
        if suite.git_commit:
            print(f"Commit: {suite.git_commit}")
        print("=" * 80)

        # Results table
        print(f"\n{'Benchmark':<40} {'P50':>8} {'P95':>8} {'P99':>8} {'Target':>8} {'Status':>8}")
        print("-" * 80)

        for result in suite.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            target = f"{result.target_ms:.1f}" if result.target_ms else "N/A"

            print(f"{result.name:<40} {result.median_ms:>7.2f}  {result.p95_ms:>7.2f}  "
                  f"{result.p99_ms:>7.2f}  {target:>7}  {status:>8}")

        # Summary
        print("\n" + "-" * 80)
        passed = sum(1 for r in suite.results if r.passed)
        total = len(suite.results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"Summary: {passed}/{total} benchmarks passed ({pass_rate:.1f}%)")

        # Regression detection
        regressions = self.detect_regressions(suite)
        if regressions:
            print("\n⚠️  REGRESSIONS DETECTED:")
            for reg in regressions:
                print(f"  - {reg['name']}: {reg['previous_p95_ms']:.2f}ms → "
                      f"{reg['current_p95_ms']:.2f}ms (+{reg['percent_change']:.1f}%)")
        else:
            print("\n✅ No regressions detected")

        print("=" * 80 + "\n")

    def generate_html_report(self, suite: BenchmarkSuite) -> str:
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SARK Performance Benchmarks - {suite.timestamp}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 3px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background: #4CAF50;
                    color: white;
                }}
                tr:hover {{
                    background: #f5f5f5;
                }}
                .pass {{
                    color: #4CAF50;
                    font-weight: bold;
                }}
                .fail {{
                    color: #f44336;
                    font-weight: bold;
                }}
                .metric {{
                    text-align: right;
                }}
                .summary {{
                    background: #e8f5e9;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
                .regression {{
                    background: #ffebee;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>SARK v1.3.0 Security Performance Benchmarks</h1>
                <p><strong>Suite:</strong> {suite.suite_name}</p>
                <p><strong>Timestamp:</strong> {suite.timestamp}</p>
                {'<p><strong>Commit:</strong> ' + suite.git_commit + '</p>' if suite.git_commit else ''}

                <table>
                    <thead>
                        <tr>
                            <th>Benchmark</th>
                            <th class="metric">P50 (ms)</th>
                            <th class="metric">P95 (ms)</th>
                            <th class="metric">P99 (ms)</th>
                            <th class="metric">Target (ms)</th>
                            <th class="metric">Status</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for result in suite.results:
            status_class = "pass" if result.passed else "fail"
            status_text = "PASS" if result.passed else "FAIL"
            target = f"{result.target_ms:.1f}" if result.target_ms else "N/A"

            html += f"""
                        <tr>
                            <td>{result.name}</td>
                            <td class="metric">{result.median_ms:.2f}</td>
                            <td class="metric">{result.p95_ms:.2f}</td>
                            <td class="metric">{result.p99_ms:.2f}</td>
                            <td class="metric">{target}</td>
                            <td class="metric {status_class}">{status_text}</td>
                        </tr>
            """

        html += """
                    </tbody>
                </table>
        """

        # Summary
        passed = sum(1 for r in suite.results if r.passed)
        total = len(suite.results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        html += f"""
                <div class="summary">
                    <h2>Summary</h2>
                    <p><strong>{passed}/{total}</strong> benchmarks passed ({pass_rate:.1f}%)</p>
                </div>
        """

        # Regressions
        regressions = self.detect_regressions(suite)
        if regressions:
            html += '<div class="regression"><h2>⚠️ Regressions Detected</h2><ul>'
            for reg in regressions:
                html += f"""
                    <li><strong>{reg['name']}</strong>:
                    {reg['previous_p95_ms']:.2f}ms → {reg['current_p95_ms']:.2f}ms
                    (+{reg['percent_change']:.1f}%)</li>
                """
            html += '</ul></div>'

        html += """
            </div>
        </body>
        </html>
        """

        # Save HTML report
        html_file = self.output_dir / f"benchmark_{suite.timestamp.replace(':', '-')}.html"
        with open(html_file, 'w') as f:
            f.write(html)

        # Also save as latest
        latest_html = self.output_dir / "latest_benchmark.html"
        with open(latest_html, 'w') as f:
            f.write(html)

        return str(html_file)


def get_git_commit() -> Optional[str]:
    """Get current git commit hash"""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None
