#!/usr/bin/env python3
"""
Performance Dashboard Generator

Generates an interactive HTML dashboard with performance trends and visualizations.

Usage:
    python tests/performance/dashboard.py
    python tests/performance/dashboard.py --days 30 --output reports/performance/dashboard.html
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict


def load_history(history_file: Path, days: int = 30) -> List[Dict[str, Any]]:
    """Load benchmark history for the last N days"""
    if not history_file.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    history = []

    with open(history_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            timestamp = datetime.fromisoformat(data['timestamp'])

            if timestamp >= cutoff:
                history.append(data)

    return history


def generate_dashboard_html(history: List[Dict[str, Any]], output_path: Path):
    """Generate interactive performance dashboard"""

    # Organize data by benchmark name
    benchmark_data = defaultdict(list)

    for run in history:
        timestamp = run['timestamp']
        commit = run.get('git_commit', 'unknown')

        for result in run.get('results', []):
            benchmark_data[result['name']].append({
                'timestamp': timestamp,
                'commit': commit,
                'p50': result['median_ms'],
                'p95': result['p95_ms'],
                'p99': result['p99_ms'],
                'passed': result['passed']
            })

    # Sort by timestamp
    for name in benchmark_data:
        benchmark_data[name].sort(key=lambda x: x['timestamp'])

    # Prepare chart data
    chart_datasets = []
    for name, data in benchmark_data.items():
        timestamps = [d['timestamp'] for d in data]
        p95_values = [d['p95'] for d in data]

        chart_datasets.append({
            'name': name,
            'timestamps': timestamps,
            'values': p95_values
        })

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SARK Performance Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}

        .header .subtitle {{
            color: #718096;
            font-size: 1.1em;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .stat-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
        }}

        .stat-card .label {{
            color: #718096;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .stat-card .value {{
            color: #2d3748;
            font-size: 2.5em;
            font-weight: bold;
        }}

        .stat-card .subvalue {{
            color: #a0aec0;
            font-size: 0.9em;
            margin-top: 5px;
        }}

        .stat-card.success {{
            border-left: 4px solid #48bb78;
        }}

        .stat-card.warning {{
            border-left: 4px solid #ed8936;
        }}

        .stat-card.error {{
            border-left: 4px solid #f56565;
        }}

        .chart-section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}

        .chart-section h2 {{
            color: #2d3748;
            margin-bottom: 20px;
        }}

        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 30px;
        }}

        .benchmark-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 15px;
        }}

        .benchmark-item {{
            background: #f7fafc;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #4299e1;
        }}

        .benchmark-item.passing {{
            border-left-color: #48bb78;
        }}

        .benchmark-item.failing {{
            border-left-color: #f56565;
        }}

        .benchmark-item h3 {{
            color: #2d3748;
            font-size: 1.1em;
            margin-bottom: 10px;
        }}

        .benchmark-metrics {{
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
        }}

        .metric {{
            text-align: center;
        }}

        .metric .metric-label {{
            color: #718096;
            font-size: 0.8em;
            text-transform: uppercase;
        }}

        .metric .metric-value {{
            color: #2d3748;
            font-size: 1.3em;
            font-weight: bold;
        }}

        .trend {{
            display: inline-block;
            margin-left: 5px;
            font-size: 0.9em;
        }}

        .trend.up {{
            color: #f56565;
        }}

        .trend.down {{
            color: #48bb78;
        }}

        .trend.stable {{
            color: #4299e1;
        }}

        footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SARK Performance Dashboard</h1>
            <p class="subtitle">v1.3.0 Security Features Performance Monitoring</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card success">
                <div class="label">Total Benchmarks</div>
                <div class="value" id="total-benchmarks">0</div>
                <div class="subvalue">Tracked performance metrics</div>
            </div>

            <div class="stat-card success">
                <div class="label">Passing Tests</div>
                <div class="value" id="passing-tests">0</div>
                <div class="subvalue" id="pass-rate">0% pass rate</div>
            </div>

            <div class="stat-card" id="avg-latency-card">
                <div class="label">Avg P95 Latency</div>
                <div class="value" id="avg-latency">0ms</div>
                <div class="subvalue">Across all benchmarks</div>
            </div>

            <div class="stat-card" id="regression-card">
                <div class="label">Regressions</div>
                <div class="value" id="regressions">0</div>
                <div class="subvalue">In last 5 runs</div>
            </div>
        </div>

        <div class="chart-section">
            <h2>📈 Performance Trends (P95 Latency)</h2>
            <div class="chart-container">
                <canvas id="trendsChart"></canvas>
            </div>
        </div>

        <div class="chart-section">
            <h2>📊 Current Benchmark Results</h2>
            <div class="benchmark-list" id="benchmark-list">
                <!-- Populated by JavaScript -->
            </div>
        </div>

        <footer>
            Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | SARK v1.3.0
        </footer>
    </div>

    <script>
        // Benchmark data from Python
        const benchmarkData = {json.dumps(dict(benchmark_data), indent=2)};
        const chartDatasets = {json.dumps(chart_datasets, indent=2)};

        // Calculate statistics
        const latestRun = Object.values(benchmarkData)[0]?.slice(-1)[0];
        const allBenchmarks = Object.keys(benchmarkData);
        const totalBenchmarks = allBenchmarks.length;

        let passingTests = 0;
        let totalLatency = 0;

        allBenchmarks.forEach(name => {{
            const latest = benchmarkData[name].slice(-1)[0];
            if (latest && latest.passed) passingTests++;
            if (latest) totalLatency += latest.p95;
        }});

        const avgLatency = totalBenchmarks > 0 ? (totalLatency / totalBenchmarks).toFixed(2) : 0;
        const passRate = totalBenchmarks > 0 ? ((passingTests / totalBenchmarks) * 100).toFixed(1) : 0;

        // Update stats
        document.getElementById('total-benchmarks').textContent = totalBenchmarks;
        document.getElementById('passing-tests').textContent = passingTests;
        document.getElementById('pass-rate').textContent = `${{passRate}}% pass rate`;
        document.getElementById('avg-latency').textContent = `${{avgLatency}}ms`;

        // Set card colors
        const avgLatencyCard = document.getElementById('avg-latency-card');
        if (avgLatency < 1.0) {{
            avgLatencyCard.classList.add('success');
        }} else if (avgLatency < 5.0) {{
            avgLatencyCard.classList.add('warning');
        }} else {{
            avgLatencyCard.classList.add('error');
        }}

        // Create trends chart
        const colors = [
            '#667eea', '#f56565', '#48bb78', '#ed8936', '#4299e1',
            '#9f7aea', '#38b2ac', '#f6ad55', '#fc8181', '#68d391'
        ];

        const datasets = chartDatasets.map((dataset, index) => ({{
            label: dataset.name,
            data: dataset.timestamps.map((ts, i) => ({{
                x: new Date(ts),
                y: dataset.values[i]
            }})),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
            tension: 0.4,
            fill: false
        }}));

        const ctx = document.getElementById('trendsChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                datasets: datasets
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            boxWidth: 12,
                            padding: 15
                        }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                scales: {{
                    x: {{
                        type: 'time',
                        time: {{
                            unit: 'day'
                        }},
                        title: {{
                            display: true,
                            text: 'Date'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Latency (ms)'
                        }},
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // Populate benchmark list
        const benchmarkList = document.getElementById('benchmark-list');

        allBenchmarks.forEach(name => {{
            const data = benchmarkData[name];
            const latest = data[data.length - 1];
            const previous = data.length > 1 ? data[data.length - 2] : null;

            let trend = '';
            let trendClass = 'stable';

            if (previous) {{
                const change = ((latest.p95 - previous.p95) / previous.p95) * 100;
                if (change > 5) {{
                    trend = `↑ +${{change.toFixed(1)}}%`;
                    trendClass = 'up';
                }} else if (change < -5) {{
                    trend = `↓ ${{change.toFixed(1)}}%`;
                    trendClass = 'down';
                }} else {{
                    trend = '→ Stable';
                }}
            }}

            const itemClass = latest.passed ? 'passing' : 'failing';
            const statusIcon = latest.passed ? '✅' : '❌';

            benchmarkList.innerHTML += `
                <div class="benchmark-item ${{itemClass}}">
                    <h3>${{statusIcon}} ${{name}}</h3>
                    <div class="benchmark-metrics">
                        <div class="metric">
                            <div class="metric-label">P50</div>
                            <div class="metric-value">${{latest.p50.toFixed(2)}}ms</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">P95</div>
                            <div class="metric-value">${{latest.p95.toFixed(2)}}ms</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">P99</div>
                            <div class="metric-value">${{latest.p99.toFixed(2)}}ms</div>
                        </div>
                    </div>
                    <div class="trend ${{trendClass}}">${{trend}}</div>
                </div>
            `;
        }});
    </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ Dashboard generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Generate performance dashboard')
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days of history to include (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='reports/performance/dashboard.html',
        help='Output HTML file path'
    )
    parser.add_argument(
        '--history',
        type=str,
        default='reports/performance/benchmark_history.jsonl',
        help='Path to benchmark history file'
    )
    args = parser.parse_args()

    history_file = Path(args.history)
    output_path = Path(args.output)

    if not history_file.exists():
        print(f"⚠️  No history file found at {history_file}")
        print("Run benchmarks first to generate data.")
        return 1

    print(f"Loading history from {history_file}...")
    history = load_history(history_file, args.days)

    if not history:
        print(f"⚠️  No benchmark data found for the last {args.days} days")
        return 1

    print(f"Found {len(history)} benchmark runs")
    print(f"Generating dashboard...")

    generate_dashboard_html(history, output_path)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
