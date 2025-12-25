# SARK Performance Testing Framework

Complete guide to using the SARK performance testing framework for benchmarking and regression detection.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Framework Architecture](#framework-architecture)
3. [Creating Custom Benchmarks](#creating-custom-benchmarks)
4. [Running Benchmarks](#running-benchmarks)
5. [CI/CD Integration](#cicd-integration)
6. [Performance Dashboard](#performance-dashboard)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Run Existing Benchmarks

```bash
# Run comprehensive benchmark suite
pytest tests/performance/test_comprehensive_benchmarks.py::test_generate_full_report -v -s

# Run specific benchmark class
pytest tests/performance/test_comprehensive_benchmarks.py::TestComprehensiveSecurityBenchmarks -v

# View results
cat reports/performance/latest_benchmark.json
open reports/performance/latest_benchmark.html
```

### Create Your First Benchmark

```python
from tests.performance.framework import Benchmark, BenchmarkRunner

class MyBenchmark(Benchmark):
    def setup(self):
        # Run once before benchmarking
        self.data = {"key": "value"}

    def run(self):
        # This gets benchmarked
        process_data(self.data)

# Run it
runner = BenchmarkRunner()
runner.add_benchmark(MyBenchmark(
    name="My Feature",
    target_ms=5.0,
    iterations=1000
))
results = runner.run_all()
runner.generate_report(results)
```

---

## Framework Architecture

### Components

```
tests/performance/
├── framework.py              # Core framework (Benchmark, BenchmarkRunner)
├── benchmark_report.py       # Reporting & historical tracking
├── dashboard.py              # Interactive dashboard generator
├── benchmark_scenarios.yaml  # Configuration for benchmark scenarios
└── test_comprehensive_benchmarks.py  # Comprehensive test suite

scripts/
├── check_performance_regression.py  # CI/CD regression checker
└── compare_performance.py           # Compare baseline vs current

.github/workflows/
└── performance-benchmarks.yml  # GitHub Actions workflow
```

### Data Flow

```
┌─────────────┐
│  Benchmark  │ → Execute iterations with warmup
└─────────────┘
       ↓
┌─────────────┐
│  Latencies  │ → Raw timing measurements (ms)
└─────────────┘
       ↓
┌─────────────┐
│   Result    │ → Statistical analysis (P50/P95/P99)
└─────────────┘
       ↓
┌─────────────┐
│    Suite    │ → Collection of results + metadata
└─────────────┘
       ↓
┌─────────────┐
│   Reports   │ → JSON, HTML, Console, Dashboard
└─────────────┘
       ↓
┌─────────────┐
│   History   │ → JSONL append-only log
└─────────────┘
       ↓
┌─────────────┐
│ Regression  │ → Compare last 5 runs (10% threshold)
└─────────────┘
```

---

## Creating Custom Benchmarks

### Method 1: Extend Benchmark Class

**Best for**: Complex benchmarks with setup/teardown

```python
from tests.performance.framework import Benchmark

class DatabaseQueryBenchmark(Benchmark):
    def setup(self):
        """Run once before all iterations"""
        self.db = connect_database()
        self.query = prepare_query()

    def run(self):
        """This code gets timed (called N times)"""
        self.db.execute(self.query)

    def teardown(self):
        """Run once after all iterations"""
        self.db.close()

# Use it
benchmark = DatabaseQueryBenchmark(
    name="User Query Performance",
    target_ms=10.0,      # P95 target
    iterations=1000,     # Number of iterations
    warmup=100          # Warmup iterations
)
```

### Method 2: Use FunctionBenchmark

**Best for**: Simple function benchmarks

```python
from tests.performance.framework import FunctionBenchmark

def my_expensive_operation():
    # Code to benchmark
    result = complex_calculation()
    return result

benchmark = FunctionBenchmark(
    name="Complex Calculation",
    func=my_expensive_operation,
    target_ms=5.0,
    iterations=1000
)
```

### Method 3: Quick Benchmark

**Best for**: One-off quick tests

```python
from tests.performance.framework import quick_benchmark

def my_func():
    do_something()

stats = quick_benchmark(my_func, iterations=100)
print(f"P95: {stats['p95']:.2f}ms")
```

### Method 4: Async Benchmarks

**Best for**: Async functions

```python
from tests.performance.framework import AsyncBenchmark

class MyAsyncBenchmark(AsyncBenchmark):
    async def setup(self):
        self.client = await create_client()

    async def run(self):
        await self.client.fetch_data()

    async def teardown(self):
        await self.client.close()
```

---

## Running Benchmarks

### Using BenchmarkRunner

```python
from tests.performance.framework import BenchmarkRunner

runner = BenchmarkRunner(suite_name="My Benchmarks")

# Add multiple benchmarks
runner.add_benchmark(Benchmark1(...))
runner.add_benchmark(Benchmark2(...))
runner.add_async_benchmark(AsyncBenchmark1(...))

# Run all
suite = runner.run_all(verbose=True)

# Generate reports
paths = runner.generate_report(
    suite,
    console=True,  # Print to console
    html=True,     # Generate HTML report
    json_output=True  # Save JSON
)

print(f"HTML report: {paths['html']}")
print(f"JSON report: {paths['json']}")
```

### From Configuration File

```python
# Load scenarios from YAML
scenarios = runner.load_scenarios('tests/performance/benchmark_scenarios.yaml')

# Create benchmarks from scenarios
for scenario in scenarios:
    # Custom logic to create benchmark from scenario
    benchmark = create_benchmark_from_scenario(scenario)
    runner.add_benchmark(benchmark)
```

### Command Line

```bash
# Run comprehensive suite
pytest tests/performance/test_comprehensive_benchmarks.py -v

# Run specific test
pytest tests/performance/test_comprehensive_benchmarks.py::TestComprehensiveSecurityBenchmarks::test_injection_simple_params -v

# Generate full report
pytest tests/performance/test_comprehensive_benchmarks.py::test_generate_full_report -v -s

# Save as JSON for CI/CD
pytest tests/performance/test_comprehensive_benchmarks.py --json=results.json
```

---

## CI/CD Integration

### GitHub Actions

The framework includes a complete GitHub Actions workflow:

**.github/workflows/performance-benchmarks.yml**

**Triggers**:
- Push to `main` or `develop`
- Pull requests to `main`
- Daily at 2 AM UTC
- Manual trigger

**Features**:
- Runs comprehensive benchmark suite
- Checks for regressions (10% threshold)
- Posts results as PR comment
- Uploads artifacts (90-day retention)
- Publishes to GitHub Pages
- Compares with baseline

**Enable in your repo**:
```bash
# Workflow is already configured
# Just push to enable:
git add .github/workflows/performance-benchmarks.yml
git commit -m "Add performance benchmarking workflow"
git push
```

### Manual Regression Check

```bash
# Check for regressions
python scripts/check_performance_regression.py --threshold 10.0

# Exit codes:
# 0 = No regressions
# 1 = Regressions detected
# 2 = Error
```

### Compare Baseline vs Current

```bash
# Compare two benchmark runs
python scripts/compare_performance.py baseline.json current.json

# Or compare directories
python scripts/compare_performance.py ./reports/baseline ./reports/current

# Generates markdown comparison report
```

### Integration with Other CI Systems

**Jenkins**:
```groovy
stage('Performance Tests') {
    steps {
        sh 'pytest tests/performance/test_comprehensive_benchmarks.py'
        sh 'python scripts/check_performance_regression.py'

        publishHTML([
            reportName: 'Performance Report',
            reportDir: 'reports/performance',
            reportFiles: 'latest_benchmark.html'
        ])
    }
}
```

**GitLab CI**:
```yaml
performance_tests:
  stage: test
  script:
    - pytest tests/performance/test_comprehensive_benchmarks.py
    - python scripts/check_performance_regression.py
  artifacts:
    paths:
      - reports/performance/
    expire_in: 90 days
```

---

## Performance Dashboard

### Generate Dashboard

```bash
# Generate interactive dashboard
python tests/performance/dashboard.py

# Custom options
python tests/performance/dashboard.py \
    --days 30 \
    --output reports/performance/dashboard.html \
    --history reports/performance/benchmark_history.jsonl
```

### Features

- **Interactive Charts**: Historical trend visualization with Chart.js
- **Real-time Stats**: Total benchmarks, pass rate, avg latency
- **Trend Analysis**: Shows performance trends (↑ regression, ↓ improvement, → stable)
- **Responsive Design**: Works on desktop and mobile
- **Auto-refresh Data**: Reads from latest benchmark history

### Dashboard Sections

1. **Header**: Summary and metadata
2. **Stats Cards**: Key metrics at a glance
3. **Trends Chart**: Line chart showing P95 latency over time
4. **Benchmark List**: Detailed results for each benchmark

### Hosting

**GitHub Pages** (automatic via CI/CD):
- Dashboard published to `https://your-org.github.io/sark/performance/`

**Self-hosted**:
```bash
# Serve locally
python -m http.server 8000 --directory reports/performance
# Open http://localhost:8000/dashboard.html
```

---

## Best Practices

### Benchmark Design

✅ **DO**:
- Use warmup iterations (50-100) to stabilize JIT/caching
- Run enough iterations (500-1000) for statistical significance
- Test realistic scenarios, not synthetic edge cases
- Benchmark at the right level (not too granular, not too broad)
- Include both simple and complex scenarios

❌ **DON'T**:
- Benchmark trivial operations (< 0.01ms)
- Mix I/O-bound and CPU-bound benchmarks
- Use random data without seeding
- Benchmark in debug mode
- Ignore warmup phase

### Target Selection

```python
# Target guidelines (P95 latency):
injection_detection_simple: 2.0ms   # < 100 params
injection_detection_complex: 5.0ms  # > 100 params
secret_scan_small: 0.5ms            # < 10 fields
secret_scan_large: 5.0ms            # > 100 fields
anomaly_detection: 5.0ms            # async OK
combined_flow: 3.0ms                # full request cycle
```

**Rule of thumb**: Target should be 2-5x slower than current P95 to allow for variance.

### Regression Thresholds

```python
# Recommended thresholds:
threshold_percent: 10.0  # Default: 10% slower = regression
comparison_window: 5     # Compare against last 5 runs
```

**Rationale**: 10% allows for normal variance while catching real regressions.

### CI/CD Strategy

**When to run**:
- ✅ Every PR (with baseline comparison)
- ✅ Daily on main branch (track trends)
- ✅ Before releases (validation)
- ❌ On every commit (too noisy)

**Failure policy**:
- **Regressions > 10%**: Fail build (configurable)
- **Regressions < 10%**: Warn but pass
- **New benchmarks**: Always pass (no baseline)

---

## Troubleshooting

### Inconsistent Results

**Problem**: Benchmark results vary widely between runs

**Solutions**:
```python
# 1. Increase warmup iterations
benchmark = MyBenchmark(warmup=200)  # More warmup

# 2. Increase measurement iterations
benchmark = MyBenchmark(iterations=2000)  # More samples

# 3. Check for I/O interference
# Move I/O to setup(), only benchmark compute

# 4. Pin CPU (Linux)
import os
os.sched_setaffinity(0, {0})  # Pin to CPU 0
```

### Benchmarks Too Slow

**Problem**: Benchmark suite takes too long

**Solutions**:
```python
# 1. Reduce iterations for slow tests
benchmark = SlowBenchmark(iterations=100, warmup=10)

# 2. Run in parallel (careful with shared resources)
pytest tests/performance/ -n auto

# 3. Sample subset in CI
pytest tests/performance/ -k "simple or combined"
```

### Regressions Not Detected

**Problem**: Performance got worse but no regression flagged

**Checks**:
```bash
# 1. Verify history exists
ls reports/performance/benchmark_history.jsonl

# 2. Check threshold
python scripts/check_performance_regression.py --threshold 5.0  # Lower threshold

# 3. Manually compare
python scripts/compare_performance.py baseline.json current.json
```

### Dashboard Not Updating

**Problem**: Dashboard shows old data

**Solutions**:
```bash
# 1. Regenerate dashboard
python tests/performance/dashboard.py

# 2. Check history file
tail reports/performance/benchmark_history.jsonl

# 3. Clear browser cache
# Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
```

---

## Advanced Usage

### Custom Metrics

```python
from tests.performance.framework import Benchmark

class MemoryBenchmark(Benchmark):
    def setup(self):
        import tracemalloc
        self.tracemalloc = tracemalloc
        self.tracemalloc.start()

    def run(self):
        # Code to benchmark
        process_large_data()

    def teardown(self):
        current, peak = self.tracemalloc.get_traced_memory()
        self.tracemalloc.stop()
        print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
```

### Parameterized Benchmarks

```python
class ParameterizedBenchmark(Benchmark):
    def __init__(self, data_size, **kwargs):
        super().__init__(**kwargs)
        self.data_size = data_size

    def setup(self):
        self.data = generate_data(self.data_size)

    def run(self):
        process(self.data)

# Run with different parameters
for size in [100, 1000, 10000]:
    runner.add_benchmark(
        ParameterizedBenchmark(
            data_size=size,
            name=f"Process {size} records",
            target_ms=size * 0.01
        )
    )
```

### Load Testing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class LoadTestBenchmark(AsyncBenchmark):
    def __init__(self, concurrency=10, **kwargs):
        super().__init__(**kwargs)
        self.concurrency = concurrency

    async def run(self):
        tasks = [self.make_request() for _ in range(self.concurrency)]
        await asyncio.gather(*tasks)

    async def make_request(self):
        # Single request
        await api_call()
```

---

## Reference

### Benchmark Class API

```python
class Benchmark(ABC):
    def __init__(
        self,
        name: str,
        target_ms: Optional[float] = None,
        iterations: int = 1000,
        warmup: int = 100,
        description: str = ""
    )

    def setup(self) -> None
    def run(self) -> None  # Abstract - must implement
    def teardown(self) -> None
    def execute(self) -> List[float]
```

### BenchmarkRunner API

```python
class BenchmarkRunner:
    def __init__(
        self,
        reporter: Optional[BenchmarkReporter] = None,
        suite_name: str = "Performance Benchmarks"
    )

    def add_benchmark(self, benchmark: Benchmark) -> None
    def add_async_benchmark(self, benchmark: AsyncBenchmark) -> None
    def run_all(self, verbose: bool = True) -> BenchmarkSuite
    def generate_report(
        self,
        suite: BenchmarkSuite,
        console: bool = True,
        html: bool = True,
        json_output: bool = True
    ) -> Dict[str, str]
    def load_scenarios(self, config_path: str) -> List[BenchmarkScenario]
```

### BenchmarkResult Fields

```python
@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float      # P50
    p95_ms: float
    p99_ms: float
    std_dev_ms: float
    timestamp: str
    passed: bool
    target_ms: Optional[float]
```

---

## FAQ

**Q: What's the difference between P50, P95, and P99?**

A:
- **P50 (median)**: 50% of requests are faster than this
- **P95**: 95% of requests are faster (typical worst-case)
- **P99**: 99% of requests are faster (extreme worst-case)

We use **P95 as the target** because it represents typical worst-case performance without being skewed by rare outliers.

**Q: How many iterations should I use?**

A:
- **Fast operations (< 1ms)**: 1000+ iterations
- **Medium (1-10ms)**: 500-1000 iterations
- **Slow (> 10ms)**: 100-500 iterations
- **Very slow (> 100ms)**: 50-100 iterations

**Q: Why do I need warmup iterations?**

A: Warmup stabilizes:
- JIT compilation (Python bytecode optimization)
- Caching (file system, database, memory)
- Connection pooling
- OS scheduler

Without warmup, first iterations are artificially slow.

**Q: Should I benchmark in production?**

A: **No**. Use dedicated benchmark environments. Production has:
- Variable load
- Shared resources
- Different configuration
- Data privacy concerns

**Q: How do I benchmark multi-threaded code?**

A: Use realistic concurrency:
```python
from concurrent.futures import ThreadPoolExecutor

def benchmark_concurrent():
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(my_func) for _ in range(10)]
        [f.result() for f in futures]
```

---

## Support

- **Documentation**: `docs/performance/`
- **Examples**: `tests/performance/test_comprehensive_benchmarks.py`
- **Issues**: GitHub Issues
- **Slack**: #performance channel

---

**Last Updated**: 2025-12-24
**Version**: v1.3.0
**Maintainer**: QA Team (Czarina Stream 6)
