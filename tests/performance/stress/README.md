# Stress Testing

Stress tests to find system breaking points and validate failure recovery mechanisms.

## Overview

This directory contains stress tests that intentionally push the system to extreme conditions:

### Test Objectives

| Category | Purpose | Tests |
|----------|---------|-------|
| Breaking Points | Find maximum capacity | Extreme throughput, large policies/cache |
| Failure Modes | Understand failure behavior | Memory exhaustion, connection saturation |
| Recovery | Validate resilience | Component failures, network issues |
| Cascading Failures | Verify isolation | Multi-component failures |

## Test Files

### `test_breaking_points.py`

Tests to find system limits and failure modes:

- **Extreme Throughput (10,000 req/s)**: Find maximum RPS capacity
- **Large Policy (10MB)**: Test with huge policy files
- **Large Cache (1M entries)**: Memory and performance at scale
- **Memory Exhaustion**: Behavior under memory pressure
- **Connection Saturation**: Connection pool limits

### `test_recovery.py`

Tests for failure recovery and resilience:

- **OPA Server Failure**: Graceful degradation when OPA is unavailable
- **Redis Cache Failure**: Fallback when cache is down
- **Network Interruption**: Timeout and retry handling
- **Cascading Failures**: Verify isolated failures don't cascade
- **Partial Failures**: Handle partial success in batch operations
- **Recovery Time**: Measure time to restore service

## Running Stress Tests

### Run all stress tests

```bash
pytest tests/performance/stress/ -v -m stress
```

### Run specific test category

```bash
# Breaking points only
pytest tests/performance/stress/test_breaking_points.py -v

# Recovery tests only
pytest tests/performance/stress/test_recovery.py -v
```

### Run specific test

```bash
pytest tests/performance/stress/test_breaking_points.py::test_extreme_throughput_10k_rps -v
```

### Skip dangerous tests

Some tests (like memory exhaustion) are skipped by default:

```bash
# Run all including dangerous tests
pytest tests/performance/stress/ -v -m stress --run-dangerous
```

## Test Scenarios

### Breaking Point Tests

#### 1. Extreme Throughput (10,000 req/s)

```bash
pytest tests/performance/stress/test_breaking_points.py::test_extreme_throughput_10k_rps -v
```

**Purpose**: Find maximum sustained throughput

**What it tests**:
- Concurrent request handling
- Resource usage (CPU, memory)
- Error rates at capacity
- Performance degradation

**Expected outcomes**:
- Document maximum achievable RPS
- Identify bottleneck (CPU/memory/I/O)
- Graceful degradation, no crashes

#### 2. Large Policy (10MB)

```bash
pytest tests/performance/stress/test_breaking_points.py::test_large_policy_10mb -v
```

**Purpose**: Test with extremely large policy files

**What it tests**:
- Policy compilation time
- Memory usage during compilation
- Evaluation performance with large policies
- Cache behavior

**Expected outcomes**:
- Compilation time documented
- Memory impact measured
- Evaluation still meets SLAs

#### 3. Large Cache (1M entries)

```bash
pytest tests/performance/stress/test_breaking_points.py::test_large_cache_1m_entries -v
```

**Purpose**: Test cache performance at scale

**What it tests**:
- Memory usage with 1M entries
- Read/write performance at scale
- LRU eviction performance
- Memory stability

**Expected outcomes**:
- Memory per entry documented
- Performance remains acceptable
- No memory leaks

#### 4. Connection Saturation

```bash
pytest tests/performance/stress/test_breaking_points.py::test_connection_saturation -v
```

**Purpose**: Saturate connection pool

**What it tests**:
- Connection pooling limits
- Request queuing behavior
- Connection reuse
- Timeout handling

**Expected outcomes**:
- All requests eventually complete
- No connection leaks
- Proper queuing behavior

### Recovery Tests

#### 1. OPA Server Failure

```bash
pytest tests/performance/stress/test_recovery.py::test_opa_server_failure_and_recovery -v
```

**Purpose**: Verify graceful handling when OPA fails

**Phases**:
1. OPA healthy → requests succeed
2. OPA fails → graceful failure
3. OPA recovers → requests succeed again

**Expected outcomes**:
- No crashes when OPA fails
- Recovery time < 5 seconds
- Cached responses still served

#### 2. Redis Cache Failure

```bash
pytest tests/performance/stress/test_recovery.py::test_redis_cache_failure_and_recovery -v
```

**Purpose**: Fallback when cache is unavailable

**Phases**:
1. Redis healthy → cache hits work
2. Redis fails → fallback to OPA
3. Redis recovers → cache works again

**Expected outcomes**:
- System continues without cache
- Latency increases but acceptable
- Cache recovers automatically

#### 3. Network Interruption

```bash
pytest tests/performance/stress/test_recovery.py::test_network_interruption_recovery -v
```

**Purpose**: Handle network issues

**Phases**:
1. Network healthy → fast responses
2. Network degrades → slow but successful
3. Network timeout → graceful failure
4. Network recovers → normal operation

**Expected outcomes**:
- Timeouts handled gracefully
- Retry logic works
- Recovery is automatic

#### 4. Cascading Failure Prevention

```bash
pytest tests/performance/stress/test_recovery.py::test_cascading_failure_prevention -v
```

**Purpose**: Verify failure isolation

**Scenario**: Multiple components fail sequentially

**Expected outcomes**:
- Failures are isolated
- Other components continue working
- No death spiral
- Components can recover independently

#### 5. Partial Failure Handling

```bash
pytest tests/performance/stress/test_recovery.py::test_partial_failure_handling -v
```

**Purpose**: Handle partial success in batches

**Scenario**: Batch operation with some failures

**Expected outcomes**:
- Successful items are processed
- Failed items are reported
- No data corruption
- Batch doesn't abort completely

## Acceptance Criteria

### Breaking Points
- [ ] Maximum throughput documented
- [ ] Failure modes understood
- [ ] Graceful degradation verified
- [ ] No cascading failures

### Recovery
- [ ] Fallback mechanisms work
- [ ] Recovery time < 5 seconds
- [ ] System state remains consistent
- [ ] No crashes during failure/recovery

## Test Duration

| Test | Duration | Reason |
|------|----------|--------|
| Extreme Throughput | ~10 min | Run sustained load |
| Large Policy | ~5 min | Compilation and evaluation |
| Large Cache | ~10 min | Fill 1M entries |
| Connection Saturation | ~2 min | Test pool limits |
| OPA Failure | ~30 sec | Failure and recovery |
| Redis Failure | ~30 sec | Fallback test |
| Network Interruption | ~30 sec | Multiple phases |
| Cascading Prevention | ~30 sec | Sequential failures |

## Monitoring During Tests

### Metrics to Watch

1. **System Resources**:
   - CPU usage (`top`, `htop`)
   - Memory usage (`free -h`)
   - Disk I/O (`iostat`)
   - Network (`iftop`, `nethogs`)

2. **Application Metrics**:
   - Request rate (RPS)
   - Response time percentiles
   - Error rate
   - Cache hit rate

3. **Logs**:
   - Error messages
   - Warning signs
   - Recovery events

### Example Monitoring Setup

```bash
# Terminal 1: Run stress test
pytest tests/performance/stress/test_breaking_points.py::test_extreme_throughput_10k_rps -v -s

# Terminal 2: Monitor resources
watch -n 1 'free -h && echo && ps aux | grep sark | head -5'

# Terminal 3: Monitor logs
tail -f logs/sark.log | grep -E 'ERROR|WARNING'
```

## Dangerous Tests

Some tests are marked as "dangerous" and skipped by default:

### Memory Exhaustion Test

```bash
pytest tests/performance/stress/test_breaking_points.py::test_memory_exhaustion -v --run-dangerous
```

**⚠️ WARNING**: This test intentionally exhausts system memory!

- Can make system unresponsive
- May trigger OOM killer
- Can affect other processes
- Only run on dedicated test system

## Troubleshooting

### Test Times Out

- Increase timeout: `@pytest.mark.timeout(1200)`  # 20 minutes
- Reduce load parameters
- Check system resources

### Out of Memory

- Reduce test parameters (fewer entries, smaller batches)
- Increase system swap space
- Run on machine with more RAM

### Connection Errors

- Check if services are running (OPA, Redis, etc.)
- Verify firewall settings
- Increase connection pool size

### High Error Rates

- Check server logs
- Reduce load
- Verify system has sufficient resources

## Best Practices

### Before Running Stress Tests

1. **Dedicated Environment**: Use isolated test environment
2. **Baseline Metrics**: Record normal operating metrics
3. **Monitoring Setup**: Have monitoring ready
4. **Backups**: Ensure data is backed up

### During Stress Tests

1. **Watch Resources**: Monitor CPU, memory, disk, network
2. **Check Logs**: Watch for errors and warnings
3. **Document Observations**: Note when failures occur
4. **Take Snapshots**: Capture metrics at key points

### After Stress Tests

1. **Analyze Results**: Review metrics and logs
2. **Document Findings**: Record breaking points
3. **Update Capacity Plans**: Adjust based on findings
4. **Cleanup**: Reset test environment

## See Also

- [Microbenchmarks](../benchmarks/README.md)
- [Load Testing](../load/README.md)
- [Worker Instructions](../../../.czarina/workers/performance-testing.md)
