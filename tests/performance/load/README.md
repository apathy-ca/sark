# Authorization Load Testing

Load testing suite for SARK authorization engine using [Locust](https://locust.io/).

## Overview

This directory contains Locust-based load tests to validate performance under sustained load:

### Performance Targets (v1.4.0)

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Throughput | 2,000+ req/s | 1,000 req/s |
| OPA p95 latency | <5ms | <10ms |
| Cache p95 latency | <0.5ms | <1ms |
| Error rate | <1% | <5% |
| CPU usage | <80% @ 2k req/s | <90% |

## Files

- **`locustfile.py`**: Main Locust test file with user classes
- **`scenarios.py`**: Load test scenario definitions and request patterns
- **`run_load_test.sh`**: Automated test runner script
- **`README.md`**: This file

## Load Test Scenarios

### Baseline (100 req/s)
Current production load level for comparison.

```bash
./run_load_test.sh baseline
```

- **Users**: 50
- **Spawn rate**: 5/s
- **Duration**: 30 minutes
- **Purpose**: Establish baseline performance metrics

### Target (2,000 req/s)
v1.4.0 performance goal.

```bash
./run_load_test.sh target
```

- **Users**: 1,000
- **Spawn rate**: 100/s
- **Duration**: 30 minutes
- **Purpose**: Validate v1.4.0 performance targets

### Stress (5,000 req/s)
Find system breaking point.

```bash
./run_load_test.sh stress
```

- **Users**: 2,500
- **Spawn rate**: 250/s
- **Duration**: 10 minutes
- **Purpose**: Identify maximum capacity and failure modes

### Cache Hit Test
Test cache performance with high hit rate.

```bash
./run_load_test.sh cache-hit
```

- **User class**: `ReadHeavyUser`
- **Users**: 500
- **Duration**: 10 minutes
- **Purpose**: Measure cache hit performance

### Cache Miss Test
Test OPA engine performance without cache.

```bash
./run_load_test.sh cache-miss
```

- **User class**: `CacheMissUser`
- **Users**: 200
- **Duration**: 10 minutes
- **Purpose**: Measure raw OPA engine latency

### Complex Policy Test
Test with complex multi-tenant policies.

```bash
./run_load_test.sh complex
```

- **User class**: `ComplexPolicyUser`
- **Users**: 300
- **Duration**: 10 minutes
- **Purpose**: Measure performance with complex policies

## User Classes

### SARKUser (Default)
Standard mixed workload:
- 60% read operations
- 30% write operations
- 10% admin operations

### ReadHeavyUser
High cache hit rate scenario:
- 100% read operations
- Small resource set (1-10)
- Fast request rate

### CacheMissUser
Cold cache scenario:
- 100% unique resources (cache miss)
- Tests raw OPA engine performance

### ComplexPolicyUser
Complex policy evaluation:
- Multi-tenant resources
- Rich context attributes
- Nested policy rules

## Quick Start

### 1. Install Dependencies

```bash
pip install locust
```

### 2. Start SARK Server

```bash
# In another terminal
uvicorn sark.main:app --reload
```

### 3. Run Load Test

```bash
# Run target scenario (2,000 req/s)
./run_load_test.sh target
```

### 4. View Results

Reports are saved to `./reports/` directory:
- HTML report: `target_YYYYMMDD_HHMMSS.html`
- CSV data: `target_YYYYMMDD_HHMMSS_stats.csv`

## Manual Execution

### With Web UI

```bash
locust -f locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser.

### Headless Mode

```bash
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users 1000 \
  --spawn-rate 100 \
  --run-time 30m \
  --headless \
  --html=reports/test.html
```

### Specific User Class

```bash
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users 500 \
  ReadHeavyUser \
  --headless \
  --run-time 10m
```

## Environment Variables

- **`SARK_URL`**: Server URL (default: `http://localhost:8000`)

Example:
```bash
SARK_URL=http://staging.example.com ./run_load_test.sh target
```

## Request Patterns

### Standard Pattern (SARKUser)
- **60% reads**: Common resources, cache-friendly
- **30% writes**: Mixed resources
- **10% admin**: High-privilege operations

### Read-Heavy Pattern
- **90% reads**: Maximum cache utilization
- **8% writes**: Minimal cache invalidation
- **2% admin**: Rare privileged operations

### Write-Heavy Pattern
- **30% reads**: Lower cache hit rate
- **60% writes**: Frequent cache invalidation
- **10% admin**: Normal admin load

## Metrics Collected

### Locust Metrics
- Requests per second (RPS)
- Response time percentiles (p50, p95, p99)
- Failure rate
- Request count
- Response size

### Custom Metrics
- Cache hit rate (if instrumented)
- OPA evaluation time (if instrumented)
- Error types and reasons

## Performance Analysis

### 1. Review HTML Report
Open the generated HTML report to see:
- Response time charts
- RPS over time
- Failure distribution
- Percentile statistics

### 2. Check CSV Data
Use CSV files for custom analysis:
```bash
cat reports/target_*_stats.csv | column -t -s,
```

### 3. Validate Targets
Check if performance targets are met:
- Throughput ≥ 2,000 req/s
- P95 latency < 5ms
- Error rate < 1%

## Troubleshooting

### Server Not Responsive
```bash
# Check if server is running
curl http://localhost:8000/health

# Start server if needed
uvicorn sark.main:app --reload
```

### Locust Not Installed
```bash
pip install locust
```

### Connection Errors
- Verify `SARK_URL` is correct
- Check firewall settings
- Ensure server can handle connection load

### High Error Rate
- Check server logs for errors
- Reduce load (fewer users)
- Increase server resources

## Test Duration Guidelines

| Scenario | Duration | Reason |
|----------|----------|--------|
| Baseline | 30 min | Establish stable baseline |
| Target | 30 min | Sustained load validation |
| Stress | 10 min | Find breaking point quickly |
| Cache Hit | 10 min | Quick cache validation |
| Cache Miss | 10 min | OPA engine validation |
| Complex | 10 min | Policy complexity check |

## See Also

- [Microbenchmarks](../benchmarks/README.md)
- [Worker Instructions](../../../.czarina/workers/performance-testing.md)
- [Locust Documentation](https://docs.locust.io/)
