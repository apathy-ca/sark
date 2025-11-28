# Gateway Integration Performance Baselines

## Overview

This document establishes performance baselines for Gateway Integration components. These baselines serve as:

1. **Acceptance Criteria** - Minimum performance requirements for production
2. **Regression Detection** - Automated alerts when performance degrades
3. **Capacity Planning** - Understanding system limits and scaling needs

## Performance Targets Summary

| Metric | Target | P50 | P95 | P99 |
|--------|--------|-----|-----|-----|
| Authorization Latency | < 50ms P95 | < 20ms | < 50ms | < 100ms |
| Tool Invocation Latency | < 100ms P95 | < 50ms | < 100ms | < 200ms |
| Policy Evaluation | < 10ms P95 | < 5ms | < 10ms | < 20ms |
| Cache Hit Latency | < 10ms P95 | < 2ms | < 10ms | < 15ms |
| Audit Logging Overhead | < 5ms | < 2ms | < 5ms | < 10ms |

## Throughput Targets

| Operation | Target | Measured | Status |
|-----------|--------|----------|--------|
| Authorization Requests | > 1,000 req/s | TBD | ⏳ |
| Concurrent Connections | > 100 | TBD | ⏳ |
| Policy Evaluations | > 5,000 req/s | TBD | ⏳ |
| Cache Operations | > 10,000 req/s | TBD | ⏳ |

## Detailed Performance Benchmarks

### 1. Authorization Flow Latency

**Test**: `test_authorization_latency_p95`

**Baseline Measurements**:
```
Iterations: 1,000
Concurrency: Single-threaded
Environment: Local development

Results (to be measured):
- P50: __ ms
- P95: __ ms
- P99: __ ms
- Max: __ ms
- Min: __ ms
```

**Target Validation**:
- ✅ P95 < 50ms
- ✅ P99 < 100ms
- ✅ Success rate > 99.9%

### 2. Concurrent Request Handling

**Test**: `test_concurrent_requests`

**Baseline Measurements**:
```
Concurrent Requests: 100
Total Requests: 1,000
Environment: Local development

Results (to be measured):
- Total Duration: __ seconds
- Throughput: __ req/s
- Success Rate: __ %
- Error Rate: __ %
```

**Target Validation**:
- ✅ Handle 100+ concurrent requests
- ✅ Success rate > 99%
- ✅ No connection pool exhaustion

### 3. Sustained Load

**Test**: `test_sustained_load`

**Baseline Measurements**:
```
Total Requests: 5,000
Duration: __ seconds
Batch Size: 100
Environment: Local development

Results (to be measured):
- Throughput: __ req/s
- Average Latency: __ ms
- P95 Latency: __ ms
- Success Rate: __ %
```

**Target Validation**:
- ✅ Sustained throughput > 1,000 req/s
- ✅ Latency stable throughout test
- ✅ Success rate > 99%

### 4. Spike Load

**Test**: `test_spike_load`

**Baseline Measurements**:
```
Baseline Load: 10 req/s
Spike Load: 1,000 concurrent requests
Environment: Local development

Results (to be measured):
- Spike Duration: __ seconds
- Success Rate: __ %
- Recovery Time: __ seconds
```

**Target Validation**:
- ✅ Handle 0→1000 req/s spike
- ✅ Success rate > 95% during spike
- ✅ No cascading failures

### 5. Cache Performance

**Test**: `test_cache_performance`

**Baseline Measurements**:
```
Unique Cache Keys: 100
Total Requests: 1,000
Cache Hit Ratio: __ %

Cache Hit Latency:
- P50: __ ms
- P95: __ ms
- P99: __ ms

Cache Miss Latency:
- P50: __ ms
- P95: __ ms
- P99: __ ms
```

**Target Validation**:
- ✅ Cache hit latency P95 < 10ms
- ✅ Cache miss latency P95 < 50ms
- ✅ Cache hit ratio > 80%

## Resource Usage Expectations

### Memory Usage

| Component | Idle | Light Load | Heavy Load | Max |
|-----------|------|------------|------------|-----|
| Gateway Service | < 100MB | < 200MB | < 500MB | 1GB |
| Policy Cache | < 50MB | < 100MB | < 200MB | 500MB |
| Audit Buffer | < 20MB | < 50MB | < 100MB | 200MB |

### CPU Usage

| Component | Idle | Light Load | Heavy Load | Target |
|-----------|------|------------|------------|--------|
| Gateway Service | < 5% | < 20% | < 60% | < 80% |
| Policy Evaluation | < 2% | < 10% | < 30% | < 50% |
| Audit Logging | < 1% | < 5% | < 10% | < 15% |

### Connection Pools

| Pool | Min | Max | Idle Timeout | Target |
|------|-----|-----|--------------|--------|
| Database | 5 | 20 | 300s | No exhaustion |
| Redis | 5 | 50 | 300s | No exhaustion |
| OPA | 10 | 100 | 60s | No exhaustion |

## Performance Regression Detection

### Automated Monitoring

Performance tests run nightly with results compared to baselines:

```yaml
regression_thresholds:
  latency_p95_increase: 10%  # Alert if P95 latency increases by 10%
  throughput_decrease: 15%    # Alert if throughput drops by 15%
  error_rate_increase: 1%     # Alert if error rate increases by 1%
  memory_increase: 20%        # Alert if memory usage increases by 20%
```

### Alert Conditions

**Warning** (Yellow):
- Latency increase: 5-10%
- Throughput decrease: 10-15%
- Error rate increase: 0.5-1%

**Critical** (Red):
- Latency increase: >10%
- Throughput decrease: >15%
- Error rate increase: >1%
- Any target threshold violation

## Optimization History

### v1.0 Baseline (Initial Implementation)
- Date: TBD
- Authorization P95: __ ms
- Throughput: __ req/s

### v1.1 Optimizations (Future)
- Policy caching improvements
- Connection pool tuning
- Database query optimization

## Testing Methodology

### Load Generation

**Tools**:
- pytest-benchmark for microbenchmarks
- asyncio.gather for concurrent testing
- Locust for distributed load testing

**Environment**:
- Local: Development machine
- CI: GitHub Actions (2-core, 7GB RAM)
- Staging: Production-like environment
- Production: Real traffic monitoring

### Measurement Approach

1. **Warm-up**: 100 requests to prime caches
2. **Measurement**: 1,000 requests for statistical significance
3. **Cool-down**: 10 seconds between test runs
4. **Isolation**: Each test runs independently

### Statistical Significance

- Minimum 1,000 samples per test
- Outlier removal: Remove top/bottom 1%
- Percentile calculation: Sorted array method
- Confidence: 95% confidence interval

## Scaling Guidelines

### Horizontal Scaling

| Throughput Target | Instances | Load Balancer | Database Connections |
|-------------------|-----------|---------------|---------------------|
| 1,000 req/s | 1 | Optional | 20 |
| 5,000 req/s | 3-5 | Required | 50 |
| 10,000 req/s | 10+ | Required | 100 |

### Vertical Scaling

| CPU Cores | Memory | Max Throughput | Concurrent Requests |
|-----------|--------|----------------|-------------------|
| 2 | 4GB | ~1,000 req/s | 100 |
| 4 | 8GB | ~3,000 req/s | 300 |
| 8 | 16GB | ~6,000 req/s | 600 |

## Performance Tuning Recommendations

### Quick Wins
1. **Enable policy caching** - 10x latency improvement for cached decisions
2. **Connection pooling** - Reuse database connections
3. **Async I/O** - Non-blocking operations throughout
4. **Batch audit logging** - Reduce I/O overhead

### Advanced Optimizations
1. **CDN for static assets** - Reduce latency for UI
2. **Read replicas** - Offload read-heavy queries
3. **Redis clustering** - Horizontal cache scaling
4. **OPA bundle caching** - Reduce policy evaluation overhead

## Monitoring in Production

### Key Metrics

**Latency**:
- Authorization latency (P50, P95, P99)
- End-to-end request latency
- Database query latency

**Throughput**:
- Requests per second
- Concurrent connections
- Queue depth

**Errors**:
- HTTP 5xx rate
- Timeout rate
- Rejection rate

**Resources**:
- CPU utilization
- Memory utilization
- Network bandwidth

### Dashboards

**Grafana Dashboards**:
- Gateway Overview
- Performance Metrics
- Resource Usage
- Error Rates

**Alert Rules**:
- P95 latency > 50ms (Warning)
- P95 latency > 100ms (Critical)
- Error rate > 1% (Warning)
- Error rate > 5% (Critical)

## Benchmarking Commands

### Run Performance Suite
```bash
# All performance tests
pytest tests/performance/gateway/ -m performance -v

# With detailed output
pytest tests/performance/gateway/ -m performance -v -s

# Generate benchmark report
pytest tests/performance/gateway/ --benchmark-only --benchmark-autosave
```

### Analyze Results
```bash
# Compare with baseline
pytest tests/performance/gateway/ --benchmark-compare=0001

# Generate HTML report
pytest tests/performance/gateway/ --benchmark-histogram
```

## Next Steps

1. **Establish Baselines** - Run tests in production-like environment
2. **Monitor Trends** - Track performance over time
3. **Optimize** - Address bottlenecks identified
4. **Validate** - Ensure optimizations meet targets
5. **Document** - Update baselines after improvements

---

**Last Updated**: November 27, 2025
**Baseline Version**: 1.0 (Initial)
**Status**: Targets Defined, Measurements Pending
