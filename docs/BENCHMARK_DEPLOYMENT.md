# Performance Benchmark Deployment Guide

## Status: Infrastructure Complete ✅

All benchmark code, infrastructure, and documentation has been implemented and is ready to run once deployed to an appropriate environment.

## What's Complete

### Rust Native Benchmarks (Criterion)
- ✅ `rust/sark-cache/benches/cache_benchmarks.rs` (261 lines)
  - GET/SET/DELETE operations (warm/cold cache)
  - Concurrent performance (1-16 threads)
  - Cache scaling (100-100K entries)
  - LRU eviction performance

- ✅ `rust/sark-opa/benches/opa_benchmarks.rs` (308 lines)
  - Simple & complex policy evaluation
  - Policy complexity scaling
  - Batch & concurrent evaluation
  - Compilation benchmarks

### Python Comparison Benchmarks
- ✅ `tests/performance/benchmarks/test_cache_benchmarks.py`
- ✅ `tests/performance/benchmarks/test_opa_benchmarks.py`
- ✅ `tests/performance/memory/test_memory_leaks.py`

### Infrastructure
- ✅ `scripts/run_benchmarks.sh` (489 lines)
- ✅ `docs/PERFORMANCE_BENCHMARKS.md` (347 lines)
- ✅ Benchmark reporting framework

## Deployment Requirements

### Environment Requirements

**For Full Benchmark Suite:**
```bash
# System packages
sudo apt-get update
sudo apt-get install -y build-essential gcc clang

# Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Python dependencies
pip install pytest pytest-benchmark pytest-asyncio psutil
```

**Minimum Specifications:**
- CPU: 4+ cores recommended
- RAM: 8GB minimum, 16GB recommended
- Storage: 2GB for build artifacts
- OS: Linux (Ubuntu 20.04+), macOS 11+, or WSL2 with build tools

### Build Process

```bash
# 1. Navigate to project root
cd /path/to/sark

# 2. Build Rust components with release optimizations
cargo build --release

# 3. Enable Rust integration
export RUST_ENABLED=true

# 4. Verify build
python3 -c "import sark_rust; print('Rust integration OK')"
```

### Running Benchmarks

```bash
# Run all benchmarks (recommended for full validation)
./scripts/run_benchmarks.sh

# Or run specific components:

# Rust Criterion benchmarks (requires compiled Rust)
cargo bench --package sark-cache
cargo bench --package sark-opa

# Python comparison benchmarks
pytest tests/performance/benchmarks/ --benchmark-only -v

# Memory profiling
pytest tests/performance/memory/ -m memory -v
```

## Performance Claims to Validate

| Claim | Target | Test | Status |
|-------|--------|------|--------|
| Cache p95 latency | <0.5ms | Criterion cache benchmarks | ⏳ Ready to run |
| Cache vs Redis | 10-50x faster | pytest cache comparison | ⏳ Ready to run |
| OPA vs HTTP | 4-10x faster | pytest OPA comparison | ⏳ Ready to run |
| No memory leaks | Stable growth | Memory profiling tests | ⏳ Ready to run |

## Expected Results Location

After running benchmarks, results will be in:
```
reports/performance/
├── benchmark_YYYYMMDD_HHMMSS.json    # pytest-benchmark results
├── benchmark_report_YYYYMMDD_HHMMSS.md  # Comprehensive report
├── latest_benchmark_report.md         # Latest results
└── criterion_YYYYMMDD_HHMMSS/        # Criterion HTML reports
    ├── cache_get_warm/
    ├── cache_set/
    ├── opa_simple_policy/
    └── ... (other benchmarks)
```

## Interpreting Results

### Criterion Reports (Rust)
- Open `target/criterion/*/report/index.html` in browser
- Look for:
  - **Mean**: Average latency
  - **p95/p99**: High percentile latencies
  - **Throughput**: Operations per second

### pytest-benchmark (Python)
- JSON results in `reports/performance/benchmark_*.json`
- Compare `min`, `mean`, `median` across Rust vs Python/Redis
- Calculate speedup ratios

### Memory Tests
- Console output shows:
  - Initial/final memory usage
  - Growth over time
  - PASS/FAIL against thresholds

## Validation Checklist

When running in proper environment:

- [ ] Rust components build successfully (`cargo build --release`)
- [ ] Rust integration imports in Python (`import sark_rust`)
- [ ] Criterion benchmarks run (`cargo bench`)
- [ ] Cache p95 latency <0.5ms (check Criterion reports)
- [ ] Cache shows 10-50x speedup vs Redis (check pytest results)
- [ ] OPA shows 4-10x speedup vs HTTP (check pytest results)
- [ ] Memory tests pass (no leaks detected)
- [ ] All reports generated successfully

## Troubleshooting

### Build Fails: "linker `cc` not found"
```bash
# Install build tools
sudo apt-get install build-essential

# Or on macOS
xcode-select --install
```

### Python Import Fails: "No module named 'sark_rust'"
```bash
# Rebuild and install
cargo build --release
export RUST_ENABLED=true

# Or use maturin for development
pip install maturin
maturin develop --release
```

### Benchmarks Highly Variable
- Close other applications
- Run on dedicated hardware if possible
- Use `--quick` mode for CI: `./scripts/run_benchmarks.sh --quick`
- Run multiple times and average results

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential
          pip install pytest pytest-benchmark pytest-asyncio psutil

      - name: Build Rust components
        run: cargo build --release

      - name: Run benchmarks
        env:
          RUST_ENABLED: true
        run: ./scripts/run_benchmarks.sh --quick

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: reports/performance/

      - name: Check for regressions
        run: |
          python tests/performance/analyze_results.py \
            --threshold 10 \
            --fail-on-regression
```

## Next Steps

1. **Deploy to proper environment** with C compiler and Rust toolchain
2. **Run full benchmark suite**: `./scripts/run_benchmarks.sh`
3. **Review results** in `reports/performance/`
4. **Validate claims** against acceptance criteria
5. **Integrate into CI/CD** for ongoing monitoring
6. **Track performance over time** using historical reports

## Contact

For issues or questions:
- Documentation: `docs/PERFORMANCE_BENCHMARKS.md`
- Worker instructions: `.czarina/workers/performance-benchmarks.md`
- Troubleshooting: See "Troubleshooting" section in main docs

---

**Status**: Ready to deploy and run ✅
**Last Updated**: 2026-01-17
**Worker**: performance-benchmarks
**Commit**: a40de4e
