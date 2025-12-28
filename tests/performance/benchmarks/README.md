# Performance Benchmarks

Microbenchmark suite comparing Rust vs Python implementations using `pytest-benchmark`.

## Overview

This benchmark suite validates the performance targets for SARK v1.4.0:

### Performance Targets

| Component | Metric | Target | Tool |
|-----------|--------|--------|------|
| OPA Engine | p95 latency | <5ms | pytest-benchmark |
| Cache | p95 latency | <0.5ms | pytest-benchmark |
| OPA Throughput | Improvement | 4-10x faster | pytest-benchmark |
| Cache Throughput | Improvement | 10-50x faster | pytest-benchmark |

## Benchmark Suites

### OPA Engine Benchmarks (`test_opa_benchmarks.py`)

Compares Rust-based Regorus engine vs HTTP-based Python OPA client:

- **Simple Policy**: Basic RBAC authorization
- **Complex Policy**: Multi-tenant with nested resources
- **Varying Complexity**: Small, medium, and large policies
- **Batch Evaluation**: Multiple policies evaluated sequentially
- **Concurrent Evaluation**: 10, 100, and 1000 concurrent requests

### Cache Benchmarks (`test_cache_benchmarks.py`)

Compares Rust-based in-memory cache vs Redis-based Python cache:

- **GET Operations**: Warm cache hits
- **SET Operations**: Write performance
- **DELETE Operations**: Deletion performance
- **MISS Operations**: Cold cache misses
- **Concurrent Operations**: Mixed read/write workloads
- **Size Scaling**: Small (100), medium (10K), large (1M) entries
- **Eviction**: LRU eviction performance

## Running Benchmarks

### Run all benchmarks

```bash
pytest tests/performance/benchmarks/ --benchmark-only
```

### Run specific benchmark group

```bash
# OPA simple policy benchmarks
pytest tests/performance/benchmarks/ --benchmark-only -k "opa-simple"

# Cache GET benchmarks
pytest tests/performance/benchmarks/ --benchmark-only -k "cache-get"

# Concurrent benchmarks
pytest tests/performance/benchmarks/ --benchmark-only -k "concurrent"
```

### Generate benchmark report

```bash
pytest tests/performance/benchmarks/ --benchmark-only --benchmark-json=output.json
```

### Compare Rust vs Python

```bash
# Run and save baseline (Python)
pytest tests/performance/benchmarks/ --benchmark-only -k "python" --benchmark-save=python-baseline

# Run and compare with Rust
pytest tests/performance/benchmarks/ --benchmark-only -k "rust" --benchmark-compare=python-baseline
```

## Test Scenarios

### OPA Benchmark Groups

- `opa-simple`: Simple RBAC policies
- `opa-complex`: Complex multi-tenant policies
- `opa-complexity-scaling`: Varying policy sizes
- `opa-batch`: Sequential batch evaluation
- `opa-concurrent`: Concurrent policy evaluation

### Cache Benchmark Groups

- `cache-get`: Cache hit operations
- `cache-set`: Cache write operations
- `cache-delete`: Cache deletion operations
- `cache-miss`: Cache miss operations
- `cache-concurrent`: Concurrent mixed operations
- `cache-scaling`: Scaling with different cache sizes
- `cache-eviction`: LRU eviction performance

## Fixtures

All benchmarks use shared fixtures from `conftest.py`:

- `http_opa_client`: Python HTTP-based OPA client (baseline)
- `rust_opa_client`: Rust Regorus-based OPA client
- `redis_cache`: Python Redis-based cache (baseline)
- `rust_cache`: Rust DashMap-based cache
- `simple_policy_input`: Basic RBAC test data
- `complex_policy_input`: Complex multi-tenant test data
- `sample_decision`: Sample authorization decision

## Environment Variables

- `RUST_ENABLED`: Set to `true` to use actual Rust implementations (default: `false`, uses mocks)

## Example Output

```
================================ test session starts =================================
...
test_opa_benchmarks.py::test_opa_rust_simple_policy         PASSED              [  1%]
test_opa_benchmarks.py::test_opa_python_simple_policy       PASSED              [  2%]

Name (time in ms)                         Min      Max    Mean  StdDev  Median     IQR  Outliers  OPS
-------------------------------------------------------------------------------------------------------
test_opa_rust_simple_policy             1.234    2.345   1.456    0.123   1.445   0.089       5  687.28
test_opa_python_simple_policy          12.345   18.567  14.234    1.234  14.123   1.456       3   70.25
-------------------------------------------------------------------------------------------------------

Comparison: Rust is 9.77x faster than Python
```

## Notes

- Benchmarks run with warm-up iterations for JIT/compilation
- Results are statistical (min, max, mean, median, stddev, IQR)
- Outliers are detected and reported
- Mocks are used when Rust implementations are not available
- Async functions require the `pytest-helpers-namespace` helper

## Dependencies

```toml
pytest-benchmark>=4.0.0
pytest-helpers-namespace>=2021.12.29
pytest-asyncio>=0.21.0
```

## See Also

- [Worker Instructions](../../../.czarina/workers/performance-testing.md)
- [Performance Testing Framework](../framework.py)
- [Load Testing with Locust](../locustfile.py)
