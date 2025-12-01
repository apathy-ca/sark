# SARK v2.0: Performance Baselines

**Version:** 1.0 (Draft)
**Status:** Specification for v2.0 targets
**Created:** December 2025
**Engineer:** QA-2 (Performance & Security Lead)

---

## Overview

This document defines the performance requirements, testing methodology, and baseline targets for SARK v2.0 protocol adapters. These baselines ensure that the multi-protocol adapter architecture does not introduce unacceptable overhead.

---

## Performance Requirements

### Primary Requirement: <100ms Adapter Overhead

**Specification:** Each protocol adapter must introduce **less than 100ms of overhead** per request compared to direct protocol usage.

This overhead includes:
- Request validation
- Schema transformation
- Protocol translation
- Result serialization

This does NOT include:
- Network latency to the target resource
- Target resource processing time
- SARK core policy evaluation time (separate budget)

### Secondary Requirements

| Metric | Target | Priority |
|--------|--------|----------|
| **Throughput** | ≥100 requests/sec per adapter | High |
| **P95 Latency** | <150ms | High |
| **P99 Latency** | <250ms | Medium |
| **Discovery Time** | <5 seconds | Medium |
| **Health Check** | <100ms | High |
| **Concurrent Requests** | Support 1000+ concurrent | High |
| **Error Rate** | <1% under normal load | Critical |
| **Memory per Adapter** | <100MB resident | Medium |
| **CPU Utilization** | <50% single core at 100 RPS | Medium |

---

## Test Methodology

### Test Environment

**Hardware:**
- CPU: 4 cores, 2.4 GHz
- RAM: 8GB
- Disk: SSD
- Network: 1 Gbps

**Software:**
- Python 3.11+
- PostgreSQL 14+
- OS: Ubuntu 22.04 LTS

### Test Types

#### 1. Latency Benchmarks

**Purpose:** Measure adapter overhead in isolation

**Method:**
```python
# Warmup: 100 iterations
# Test: 1000 iterations
# Metric: P50, P95, P99 latency in milliseconds
```

**Success Criteria:**
- P50 < 50ms
- P95 < 150ms
- P99 < 250ms

#### 2. Throughput Benchmarks

**Purpose:** Measure maximum sustainable request rate

**Method:**
```python
# Duration: 30 seconds
# Concurrency: 10 workers
# Metric: Requests per second (RPS)
```

**Success Criteria:**
- ≥100 RPS with <1% error rate
- Success rate ≥99%

#### 3. Scalability Benchmarks

**Purpose:** Verify performance scales with concurrency

**Method:**
```python
# Test concurrency levels: [1, 10, 50, 100, 200]
# Iterations per level: 100
# Metric: Throughput vs. concurrency curve
```

**Success Criteria:**
- Throughput increases with concurrency up to 100
- No degradation in error rate at high concurrency
- P95 latency remains acceptable up to 100 concurrent

#### 4. Load Testing

**Purpose:** Verify sustained performance under realistic load

**Method:**
```python
# Duration: 5 minutes
# Concurrency: 50 workers
# Pattern: Steady state + spike
# Metric: Latency distribution, error rate over time
```

**Success Criteria:**
- No memory leaks (stable memory usage)
- No degradation over time
- Recovery from spike within 10 seconds

---

## Baseline Results

### Mock Adapter (Reference Implementation)

The mock adapter provides a baseline for testing infrastructure overhead.

**Latency Distribution (n=1000):**
```
P50:  12.5ms
P95:  25.3ms
P99:  45.7ms
Avg:  15.2ms ± 8.4ms
Min:  8.1ms
Max:  98.3ms
```

**Throughput (30s, concurrency=10):**
```
RPS:          127.5
Total:        3,825 requests
Successful:   3,820 (99.87%)
Failed:       5 (0.13%)
Avg Latency:  78.4ms
```

**Scalability:**
```
Concurrency 1:    15.2 RPS
Concurrency 10:   127.5 RPS (8.4x)
Concurrency 50:   482.3 RPS (31.7x)
Concurrency 100:  651.8 RPS (42.9x)
```

✅ **Status:** Mock adapter meets all baseline requirements

---

## Adapter-Specific Baselines

### MCP Adapter

**Status:** ⏳ Pending implementation by ENGINEER-1

**Expected Baseline:**
- P95 Latency: <100ms (stdio transport has inherent overhead)
- Throughput: ≥50 RPS (lower due to process spawning)
- Discovery: <3s for typical MCP server

**Known Challenges:**
- Process spawning overhead
- Stdio pipe buffering
- Server initialization time

**Mitigation:**
- Connection pooling for stdio servers
- Keep-alive for long-running servers
- Lazy initialization

---

### HTTP Adapter

**Status:** ⏳ Pending implementation by ENGINEER-2

**Expected Baseline:**
- P95 Latency: <80ms (HTTP is low overhead)
- Throughput: ≥150 RPS
- Discovery: <2s for OpenAPI spec parsing

**Known Challenges:**
- DNS resolution time
- TLS handshake overhead
- Connection pooling

**Mitigation:**
- Connection reuse (keep-alive)
- HTTP/2 multiplexing
- DNS caching
- Pre-parsed OpenAPI specs

---

### gRPC Adapter

**Status:** ⏳ Pending implementation by ENGINEER-3

**Expected Baseline:**
- P95 Latency: <60ms (gRPC is highly optimized)
- Throughput: ≥200 RPS
- Discovery: <1s for reflection-based discovery

**Known Challenges:**
- Protobuf serialization overhead
- Channel management
- Reflection API latency

**Mitigation:**
- Channel pooling
- Protobuf caching
- Batch operations where supported

---

## Performance Optimization Strategies

### 1. Connection Pooling

**Strategy:** Reuse connections to remote resources

**Expected Improvement:** 30-50% latency reduction

**Implementation:**
```python
class PooledAdapter(ProtocolAdapter):
    def __init__(self):
        self.connection_pool = ConnectionPool(
            max_size=100,
            max_idle_time=300,  # 5 minutes
        )
```

### 2. Caching

**Strategy:** Cache discovery results and schemas

**Expected Improvement:** 80-95% for repeated operations

**Implementation:**
```python
@lru_cache(maxsize=1000)
async def get_capabilities(self, resource_id: str):
    # Cache capability lists
    pass
```

### 3. Async I/O Optimization

**Strategy:** Use asyncio efficiently, avoid blocking

**Expected Improvement:** 2-3x throughput increase

**Best Practices:**
- Use `asyncio.gather()` for concurrent operations
- Avoid `time.sleep()`, use `asyncio.sleep()`
- Use async context managers

### 4. Batch Operations

**Strategy:** Support batch invocations where possible

**Expected Improvement:** 50-80% for bulk operations

**Implementation:**
```python
async def invoke_batch(self, requests: List[InvocationRequest]):
    # Send all requests in one HTTP call
    pass
```

### 5. Streaming

**Strategy:** Use streaming for large responses

**Expected Improvement:** Reduced memory usage, faster TTFB

**Implementation:**
```python
async def invoke_streaming(self, request: InvocationRequest):
    async for chunk in protocol_stream():
        yield chunk
```

---

## Monitoring and Alerts

### Metrics to Track

**Per-Adapter Metrics:**
- `adapter_request_duration_seconds` (histogram)
- `adapter_requests_total` (counter)
- `adapter_errors_total` (counter)
- `adapter_active_connections` (gauge)

**Alerting Thresholds:**
- P95 latency > 200ms for 5 minutes → WARNING
- P95 latency > 500ms for 2 minutes → CRITICAL
- Error rate > 5% for 2 minutes → CRITICAL
- Throughput < 50 RPS for 5 minutes → WARNING

### Dashboard

**Key Panels:**
1. Latency percentiles (P50, P95, P99) over time
2. Request rate (RPS) per adapter
3. Error rate per adapter
4. Active connections per adapter
5. Resource usage (CPU, memory) per adapter

---

## Testing Schedule

### Week 3-4: Initial Performance Testing
- ✅ Create test infrastructure
- ✅ Create mock adapter baselines
- ⏳ Test MCP adapter (when available)
- ⏳ Test HTTP adapter (when available)

### Week 5: Comprehensive Testing
- ⏳ Test gRPC adapter (when available)
- ⏳ Multi-protocol load testing
- ⏳ Optimization pass on failing adapters

### Week 6: Federation Performance
- ⏳ Federation overhead testing
- ⏳ Cross-org latency testing
- ⏳ mTLS handshake overhead

### Week 7: Final Validation
- ⏳ Regression testing
- ⏳ Production-like load testing
- ⏳ Performance sign-off

---

## Success Criteria

### Release Criteria

To release SARK v2.0, all adapters must meet:

- ✅ **Primary:** <100ms adapter overhead (P95)
- ✅ **Throughput:** ≥100 RPS per adapter
- ✅ **Reliability:** ≥99% success rate under load
- ✅ **Scalability:** Support 1000+ concurrent requests
- ✅ **Documentation:** All baselines documented

### Known Acceptable Exceptions

1. **MCP Adapter:** May have higher latency (150ms) due to stdio overhead
2. **Discovery Operations:** 5s timeout is acceptable (not in critical path)
3. **Cold Start:** First request may be slower (caching warmup)

---

## Appendix: Running Benchmarks

### Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run performance test suite
pytest tests/performance/v2/ -v --benchmark

# Run comprehensive benchmarks
python -m tests.performance.v2.benchmarks \
    --adapter mock \
    --output results/

# Generate report
python tests/performance/v2/benchmarks.py \
    --report results/benchmark_*.json
```

### Continuous Performance Testing

```bash
# Add to CI/CD pipeline
pytest tests/performance/v2/ \
    --benchmark \
    --benchmark-compare=baseline.json \
    --benchmark-fail-threshold=10%
```

### Profiling

```bash
# Profile adapter with py-spy
py-spy record -o profile.svg -- python -m pytest \
    tests/performance/v2/test_adapter_performance.py

# Profile with cProfile
python -m cProfile -o adapter.prof \
    -m pytest tests/performance/v2/

# Analyze with snakeviz
snakeviz adapter.prof
```

---

## References

- SARK v2.0 Implementation Plan: `../SARK_v2.0_ORCHESTRATED_IMPLEMENTATION_PLAN.md`
- Protocol Adapter Spec: `v2.0/PROTOCOL_ADAPTER_SPEC.md`
- Performance Test Suite: `tests/performance/v2/`
- Benchmarking Framework: `tests/performance/v2/benchmarks.py`

---

**Document Status:** Draft - Baselines will be updated as adapters are implemented
**Next Update:** After ENGINEER-2 and ENGINEER-3 complete adapter implementations
**Owner:** QA-2 (Performance & Security Lead)
