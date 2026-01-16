# SARK Performance Benchmarks

## Overview

This document describes the comprehensive performance benchmarking suite for SARK v1.4.0, which validates the performance claims for Rust-based OPA and Cache components.

## Performance Claims

The SARK Rust integration makes the following performance claims:

1. **Cache Latency**: <0.5ms p95 latency
2. **Cache vs Redis**: 10-50x faster than Redis
3. **OPA vs HTTP**: 4-10x faster than HTTP-based OPA

This benchmark suite validates these claims through comprehensive testing.

## Benchmark Architecture

### 1. Rust Native Benchmarks (Criterion)

Located in:
- `rust/sark-cache/benches/cache_benchmarks.rs`
- `rust/sark-opa/benches/opa_benchmarks.rs`

**Purpose**: Measure raw Rust performance without Python overhead

**Metrics**:
- Latency (p50, p95, p99)
- Throughput (ops/sec)
- Concurrent performance
- Scaling characteristics

**Key Benchmarks**:
- Cache GET/SET/DELETE operations
- Cache miss scenarios
- Concurrent reads/writes (1, 2, 4, 8, 16 threads)
- Cache scaling (100, 1K, 10K, 100K entries)
- LRU eviction performance
- OPA simple policy evaluation
- OPA complex policy evaluation
- OPA batch evaluation
- OPA concurrent evaluation
- Policy compilation

### 2. Python Comparison Benchmarks (pytest-benchmark)

Located in:
- `tests/performance/benchmarks/test_cache_benchmarks.py`
- `tests/performance/benchmarks/test_opa_benchmarks.py`

**Purpose**: Compare Rust vs Python/Redis implementations

**Metrics**:
- Side-by-side latency comparison
- Speedup ratios
- Relative performance validation

**Key Benchmarks**:
- Rust cache vs Redis cache
- Rust OPA vs HTTP OPA
- Warm cache vs cold cache
- Various policy complexities

### 3. Memory Profiling Tests

Located in:
- `tests/performance/memory/test_memory_leaks.py`

**Purpose**: Verify memory safety and efficiency

**Tests**:
- Short-term memory leak detection (100K requests)
- Long-running stability tests (24 hours)
- Rust vs Python memory comparison
- Resource cleanup verification

## Running Benchmarks

### Quick Start

```bash
# Run all benchmarks
./scripts/run_benchmarks.sh

# Run with options
./scripts/run_benchmarks.sh --quick          # Quick mode
./scripts/run_benchmarks.sh --rust-only      # Rust benchmarks only
./scripts/run_benchmarks.sh --python-only    # Python benchmarks only
./scripts/run_benchmarks.sh --memory         # Include memory tests
```

### Prerequisites

**For Rust benchmarks**:
```bash
# Ensure Rust toolchain is installed
rustup --version

# Build in release mode
cargo build --release
```

**For Python benchmarks**:
```bash
# Install dependencies
pip install pytest pytest-benchmark pytest-asyncio psutil

# Enable Rust integration (if available)
export RUST_ENABLED=true
```

### Individual Benchmark Runs

**Cache Benchmarks**:
```bash
# Rust (Criterion)
cargo bench --package sark-cache

# Python (pytest-benchmark)
pytest tests/performance/benchmarks/test_cache_benchmarks.py --benchmark-only -v
```

**OPA Benchmarks**:
```bash
# Rust (Criterion)
cargo bench --package sark-opa

# Python (pytest-benchmark)
pytest tests/performance/benchmarks/test_opa_benchmarks.py --benchmark-only -v
```

**Memory Tests**:
```bash
# Quick memory tests
pytest tests/performance/memory/test_memory_leaks.py -m memory -v

# Long-running 24h test (manual)
pytest tests/performance/memory/test_memory_leaks.py::test_no_memory_leak_24h -v -s
```

## Interpreting Results

### Criterion Reports

Criterion generates HTML reports in `target/criterion/`:
- Each benchmark group has its own directory
- Open `report/index.html` in a browser
- View detailed statistics, plots, and comparisons

**Key Metrics**:
- **Mean**: Average execution time
- **Std Dev**: Variation in measurements
- **Median**: Middle value (less affected by outliers)
- **MAD**: Median Absolute Deviation (robust measure of spread)

### pytest-benchmark Results

Results are saved as JSON in `reports/performance/benchmark_*.json`

**Key Fields**:
- `min`, `max`: Range of measurements
- `mean`, `median`: Central tendency
- `stddev`: Standard deviation
- `ops`: Operations per second

**Example**:
```json
{
  "name": "test_cache_rust_get",
  "min": 0.0001234,
  "max": 0.0005678,
  "mean": 0.0002345,
  "median": 0.0002123,
  "stddev": 0.0000987,
  "ops": 4265.3
}
```

### Memory Test Results

Memory tests output to console:
- Initial/final memory usage
- Memory growth over time
- Growth rates
- Pass/fail status

**Acceptance Criteria**:
- Total growth < 50MB for 100K requests (short test)
- Growth rate < 1 MB/hour (long test)
- No linear growth pattern (indicates leak)

## Performance Acceptance Criteria

### Cache Performance

| Metric | Target | Test |
|--------|--------|------|
| GET p95 latency | <0.5ms | `test_cache_rust_get` |
| SET p95 latency | <0.5ms | `test_cache_rust_set` |
| DELETE p95 latency | <0.5ms | `test_cache_rust_delete` |
| Speedup vs Redis | ≥10x | Compare `test_cache_rust_*` vs `test_cache_redis_*` |

### OPA Performance

| Metric | Target | Test |
|--------|--------|------|
| Simple policy p95 | <5ms | `test_opa_rust_simple_policy` |
| Complex policy p95 | <5ms | `test_opa_rust_complex_policy` |
| Speedup vs HTTP | ≥4x | Compare `test_opa_rust_*` vs `test_opa_python_*` |

### Memory Requirements

| Metric | Target | Test |
|--------|--------|------|
| Memory leak | None | `test_opa_client_no_memory_leak_short` |
| Memory vs Python | ≤1.1x | `test_rust_vs_python_memory_usage` |
| Resource cleanup | Complete | `test_resource_cleanup_on_client_close` |

## Benchmark Maintenance

### Adding New Benchmarks

**Rust (Criterion)**:
1. Add benchmark function in `benches/*.rs`
2. Add to `criterion_group!` macro
3. Run with `cargo bench`

**Python (pytest-benchmark)**:
1. Add test function in `tests/performance/benchmarks/`
2. Use `@pytest.mark.benchmark` decorator
3. Call `benchmark(lambda: ...)` in test
4. Run with `pytest --benchmark-only`

### Continuous Integration

Benchmarks should be run:
- On every release
- When performance-critical code changes
- Weekly for regression detection

**CI Configuration** (example):
```yaml
performance-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Setup Rust
      uses: actions-rs/toolchain@v1
    - name: Setup Python
      uses: actions/setup-python@v2
    - name: Run Benchmarks
      run: ./scripts/run_benchmarks.sh --quick
    - name: Upload Results
      uses: actions/upload-artifact@v2
      with:
        name: benchmark-results
        path: reports/performance/
```

### Regression Detection

The benchmark reporter includes regression detection:
- Compares current run vs last 5 runs
- Alerts if p95 latency increases >10%
- Tracks performance trends over time

## Troubleshooting

### Rust Benchmarks Won't Compile

**Issue**: `error: linker 'cc' not found`

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install build-essential

# macOS
xcode-select --install

# WSL
sudo apt-get update && sudo apt-get install build-essential
```

### Python Benchmarks Fail

**Issue**: `ImportError: No module named 'pytest_benchmark'`

**Solution**:
```bash
pip install pytest-benchmark pytest-asyncio
```

### Inconsistent Results

**Issue**: High variance in benchmark results

**Solutions**:
- Close other applications
- Run on dedicated hardware if possible
- Increase benchmark iterations
- Use `--quick` mode for CI
- Run multiple times and average

### Rust Implementation Not Found

**Issue**: Tests skip because `RUST_ENABLED=false`

**Solution**:
```bash
# Build Rust components
cargo build --release

# Enable in Python
export RUST_ENABLED=true

# Run tests
pytest tests/performance/benchmarks/ --benchmark-only
```

## Best Practices

1. **Consistent Environment**: Run benchmarks on similar hardware
2. **Warm-up**: All benchmarks include warm-up iterations
3. **Statistical Rigor**: Minimum 5 rounds, use median/MAD
4. **Realistic Workloads**: Use production-like data patterns
5. **Version Control**: Track results in git for trend analysis
6. **Documentation**: Update this doc when adding benchmarks

## Resources

- [Criterion.rs Documentation](https://bheisler.github.io/criterion.rs/)
- [pytest-benchmark Documentation](https://pytest-benchmark.readthedocs.io/)
- [Regorus Documentation](https://github.com/microsoft/regorus)
- [DashMap Documentation](https://docs.rs/dashmap/)

## Contact

For questions about the benchmark suite:
- See: `docs/ROADMAP_STATUS_INTEGRATED.md`
- Worker: `.czarina/workers/performance-benchmarks.md`
- GitHub: Open an issue in the SARK repository

---

*Last Updated: 2026-01-16*
*Version: 1.4.0*
