# SIEM Performance Optimizations

Comprehensive guide to performance optimization features for SIEM integrations including circuit breaker, compression, and health monitoring.

## Overview

The SIEM performance optimization suite provides production-ready reliability and efficiency features:

1. **Circuit Breaker**: Prevents cascading failures when SIEM endpoints are down
2. **Gzip Compression**: Reduces bandwidth for large payloads (>1KB)
3. **Health Monitoring**: Periodic health checks with automatic recovery
4. **Batch Optimization**: Intelligent batch sizing recommendations

## Components

### 1. Circuit Breaker Pattern

Implements the circuit breaker pattern to fail fast when SIEM endpoints are experiencing issues.

**States:**
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Circuit is open, requests fail fast (no SIEM calls)
- **HALF_OPEN**: Testing recovery with limited requests

**Configuration:**
```python
from sark.services.audit.siem import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,      # Failures before opening circuit
    recovery_timeout=60,       # Seconds to wait before attempting recovery
    success_threshold=2,       # Successes needed to close circuit
    timeout=30,                # Operation timeout in seconds
)
```

**Behavior:**
- After 5 consecutive failures → Circuit OPENS
- After 60 seconds → Transitions to HALF_OPEN
- After 2 successful requests in HALF_OPEN → Circuit CLOSES
- If failure in HALF_OPEN → Returns to OPEN

**Direct Usage:**
```python
from sark.services.audit.siem import CircuitBreaker, CircuitBreakerError

breaker = CircuitBreaker("splunk", config)

try:
    result = await breaker.call(send_to_splunk_async_function)
except CircuitBreakerError as e:
    logger.error("Circuit open", retry_after=e.retry_after)
    # Handle gracefully - event queued for later retry
```

### 2. Gzip Compression

Automatically compresses large payloads to reduce network bandwidth.

**Configuration:**
```python
from sark.services.audit.siem import CompressionConfig

config = CompressionConfig(
    enabled=True,              # Enable/disable compression
    min_size_bytes=1024,       # Compress only if payload > 1KB
    compression_level=6,       # Gzip level 0-9 (6 = balanced)
)
```

**Compression Levels:**
- **Level 1**: Fastest compression, lower ratio (~30% reduction)
- **Level 6**: Balanced (default) (~50% reduction)
- **Level 9**: Maximum compression, slower (~60% reduction)

**Behavior:**
- Payloads < 1KB: No compression (overhead not worth it)
- Payloads ≥ 1KB: Gzipped if result is smaller than original
- Metrics tracked: compression count, bytes saved, compression rate

**Compression Performance:**
- 1KB payload: ~500 bytes compressed (50% reduction)
- 10KB payload: ~2KB compressed (80% reduction)
- 100KB payload: ~10KB compressed (90% reduction)

**Example:**
```python
from sark.services.audit.siem import SIEMOptimizer, CompressionConfig

compression_config = CompressionConfig(
    enabled=True,
    min_size_bytes=1024,      # Compress if > 1KB
    compression_level=6,      # Balanced compression
)

optimizer = SIEMOptimizer(
    siem=splunk_siem,
    name="splunk",
    compression_config=compression_config,
)

# Compress payload manually (for custom scenarios)
data = json.dumps(large_batch_of_events)
compressed, metadata = optimizer.compress_payload(data)

print(f"Original: {metadata['original_size']} bytes")
print(f"Compressed: {metadata['compressed_size']} bytes")
print(f"Saved: {metadata['bytes_saved']} bytes")
print(f"Ratio: {metadata['compression_ratio']:.2%}")
```

### 3. Health Monitoring

Periodic health checks with automatic unhealthy detection and recovery.

**Configuration:**
```python
from sark.services.audit.siem import HealthMonitorConfig

config = HealthMonitorConfig(
    enabled=True,              # Enable health monitoring
    check_interval_seconds=30, # Health check every 30s
    failure_threshold=3,       # Mark unhealthy after 3 failures
)
```

**Behavior:**
- Background task runs health checks every 30 seconds
- After 3 consecutive failures → Marked UNHEALTHY
- On successful check after failures → Marked HEALTHY
- Health status tracked in metrics

**Integration:**
```python
from sark.services.audit.siem import SIEMOptimizer, HealthMonitorConfig

health_config = HealthMonitorConfig(
    enabled=True,
    check_interval_seconds=30,
    failure_threshold=3,
)

optimizer = SIEMOptimizer(
    siem=splunk_siem,
    name="splunk",
    health_config=health_config,
)

# Start monitoring
await optimizer.start_health_monitoring()

# Check health status
if optimizer.is_healthy():
    print("SIEM is healthy")
else:
    print("SIEM is unhealthy - investigate!")

# Stop monitoring (on shutdown)
await optimizer.stop_health_monitoring()
```

### 4. SIEM Optimizer

Unified wrapper combining all optimization features.

**Full Configuration:**
```python
from sark.services.audit.siem import (
    SIEMOptimizer,
    CompressionConfig,
    HealthMonitorConfig,
    CircuitBreakerConfig,
    SplunkSIEM,
    SplunkConfig,
)

# Create base SIEM
splunk_config = SplunkConfig(
    hec_url="https://splunk.example.com:8088/services/collector",
    hec_token="your-hec-token",
    index="sark_audit",
)
splunk = SplunkSIEM(splunk_config)

# Wrap with optimizer
optimizer = SIEMOptimizer(
    siem=splunk,
    name="splunk",
    compression_config=CompressionConfig(
        enabled=True,
        min_size_bytes=1024,
        compression_level=6,
    ),
    health_config=HealthMonitorConfig(
        enabled=True,
        check_interval_seconds=30,
        failure_threshold=3,
    ),
    circuit_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=2,
    ),
)

# Start health monitoring
await optimizer.start_health_monitoring()

# Send events (automatically optimized)
await optimizer.send_event(audit_event)
await optimizer.send_batch([event1, event2, event3])

# Get metrics
metrics = optimizer.get_metrics()
print(f"Compression rate: {metrics['compression']['compression_rate']:.2%}")
print(f"Circuit state: {metrics['circuit_breaker']['state']}")
print(f"Health: {metrics['health']['is_healthy']}")

# Cleanup
await optimizer.stop_health_monitoring()
```

## Batch Optimization

### Optimal Batch Size Calculator

Calculate optimal batch size based on event size and target payload size.

```python
from sark.services.audit.siem import get_optimal_batch_size, estimate_event_size

# Estimate event size
event = create_audit_event()
event_size = estimate_event_size(event)
print(f"Estimated event size: {event_size} bytes")

# Calculate optimal batch size for 100KB target
optimal_size = get_optimal_batch_size(
    avg_event_size_bytes=event_size,
    target_batch_size_kb=100,  # 100KB batches
)
print(f"Optimal batch size: {optimal_size} events")
```

**Recommendations:**
- **Small events (< 500 bytes)**: batch_size = 200-250
- **Medium events (500-2KB)**: batch_size = 50-100
- **Large events (2-10KB)**: batch_size = 10-50
- **Very large events (> 10KB)**: batch_size = 5-10

Target batch size depends on SIEM:
- **Splunk HEC**: 100KB-1MB recommended
- **Datadog Logs**: 100KB-5MB recommended

## Production Usage

### Complete Example

```python
import asyncio
from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem import (
    SIEMOptimizer,
    BatchHandler,
    BatchConfig,
    SplunkSIEM,
    SplunkConfig,
    CompressionConfig,
    HealthMonitorConfig,
    CircuitBreakerConfig,
    get_optimal_batch_size,
    estimate_event_size,
)

async def setup_production_siem():
    """Setup production SIEM with all optimizations."""

    # 1. Create base SIEM
    splunk = SplunkSIEM(SplunkConfig(
        hec_url="https://splunk.prod.example.com:8088/services/collector",
        hec_token=os.environ["SPLUNK_HEC_TOKEN"],
        index="sark_audit_prod",
        verify_ssl=True,
    ))

    # 2. Wrap with optimizer
    optimizer = SIEMOptimizer(
        siem=splunk,
        name="splunk-prod",
        compression_config=CompressionConfig(
            enabled=True,
            min_size_bytes=1024,
            compression_level=6,
        ),
        health_config=HealthMonitorConfig(
            enabled=True,
            check_interval_seconds=30,
            failure_threshold=3,
        ),
        circuit_config=CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2,
            timeout=30,
        ),
    )

    # 3. Calculate optimal batch size
    sample_event = create_sample_audit_event()
    event_size = estimate_event_size(sample_event)
    optimal_batch_size = get_optimal_batch_size(
        avg_event_size_bytes=event_size,
        target_batch_size_kb=100,
    )

    print(f"Event size: {event_size} bytes")
    print(f"Optimal batch size: {optimal_batch_size} events")

    # 4. Setup batch handler with optimizer
    batch_handler = BatchHandler(
        callback=optimizer.send_batch,
        config=BatchConfig(
            batch_size=optimal_batch_size,
            batch_timeout_seconds=5,
            max_queue_size=10000,
        ),
    )

    # 5. Start monitoring and batching
    await optimizer.start_health_monitoring()
    await batch_handler.start()

    return optimizer, batch_handler

async def send_audit_event(event: AuditEvent, batch_handler: BatchHandler):
    """Send event through optimized pipeline."""
    try:
        await batch_handler.enqueue(event)
    except Exception as e:
        logger.error("Failed to enqueue event", error=str(e))
        # Fallback: log locally or queue for retry

async def shutdown(optimizer: SIEMOptimizer, batch_handler: BatchHandler):
    """Graceful shutdown with flush."""
    await batch_handler.stop(flush=True)
    await optimizer.stop_health_monitoring()

    # Log final metrics
    metrics = optimizer.get_metrics()
    logger.info("SIEM optimizer shutdown", metrics=metrics)

# Usage
async def main():
    optimizer, batch_handler = await setup_production_siem()

    # Send events
    for event in generate_audit_events():
        await send_audit_event(event, batch_handler)

    # Shutdown
    await shutdown(optimizer, batch_handler)

if __name__ == "__main__":
    asyncio.run(main())
```

## Monitoring and Metrics

### Available Metrics

```python
metrics = optimizer.get_metrics()

# Compression metrics
print(f"Compression enabled: {metrics['compression']['enabled']}")
print(f"Payloads compressed: {metrics['compression']['count']}")
print(f"Bytes saved: {metrics['compression']['bytes_saved']:,}")
print(f"Compression rate: {metrics['compression']['compression_rate']:.2%}")

# Circuit breaker metrics
print(f"Circuit state: {metrics['circuit_breaker']['state']}")
print(f"Failure count: {metrics['circuit_breaker']['failure_count']}")
print(f"Retry after: {metrics['circuit_breaker']['retry_after']}s")
print(f"Blocks: {metrics['circuit_breaker_blocks']}")

# Health metrics
print(f"Is healthy: {metrics['health']['is_healthy']}")
print(f"Last check: {metrics['health']['last_check']}")
print(f"Consecutive failures: {metrics['health']['consecutive_failures']}")
```

### Prometheus Integration

The circuit breaker and optimizer emit structured logs that can be scraped by Prometheus:

```yaml
# Example Prometheus queries
# Circuit breaker state
circuit_breaker_state{circuit="splunk"}

# Compression efficiency
siem_compression_bytes_saved_total{siem="splunk"}
siem_compression_rate{siem="splunk"}

# Health status
siem_health_status{siem="splunk"}
siem_health_consecutive_failures{siem="splunk"}
```

### Alerting Rules

**Recommended Alerts:**

1. **Circuit Open**
   ```yaml
   alert: SIEMCircuitOpen
   expr: circuit_breaker_state{state="open"} == 1
   for: 2m
   labels:
     severity: critical
   annotations:
     summary: "SIEM circuit breaker open for {{ $labels.circuit }}"
   ```

2. **Low Health**
   ```yaml
   alert: SIEMUnhealthy
   expr: siem_health_status{is_healthy="false"} == 1
   for: 5m
   labels:
     severity: warning
   annotations:
     summary: "SIEM {{ $labels.siem }} is unhealthy"
   ```

3. **High Circuit Breaker Blocks**
   ```yaml
   alert: HighCircuitBreakerBlocks
   expr: rate(siem_circuit_breaker_blocks_total[5m]) > 10
   for: 5m
   labels:
     severity: warning
   annotations:
     summary: "High rate of circuit breaker blocks for {{ $labels.siem }}"
   ```

## Performance Characteristics

### Circuit Breaker

**Overhead:**
- Closed state: <0.1ms per operation (minimal)
- Open state: <0.01ms (immediate fail)
- Lock contention: Minimal (async lock, non-blocking)

**Throughput Impact:**
- Closed: No impact
- Open: Saves latency by failing fast (30-60s saved per call)

### Compression

**CPU Impact:**
- Level 1: ~0.5ms per 10KB payload
- Level 6: ~2ms per 10KB payload
- Level 9: ~10ms per 10KB payload

**Network Savings:**
- 10KB JSON: ~2KB compressed (80% reduction)
- 100KB JSON: ~10KB compressed (90% reduction)

**Recommendation:** Level 6 provides best balance of CPU vs. bandwidth

### Health Monitoring

**Overhead:**
- One health check every 30s
- Typical health check latency: 10-50ms
- Background task: Minimal CPU usage

**Network Impact:**
- ~1 request per 30s per SIEM
- ~2 requests/min = 2,880 requests/day
- Negligible compared to event traffic

## Troubleshooting

### Circuit Breaker Stuck Open

**Symptoms:**
- Circuit permanently open
- `CircuitBreakerError` on all requests
- Metrics show `state="open"` with high `retry_after`

**Diagnosis:**
```python
state = optimizer.circuit_breaker.get_state()
print(f"State: {state['state']}")
print(f"Failures: {state['failure_count']}")
print(f"Retry after: {state['retry_after']}s")
```

**Solutions:**
1. Check SIEM connectivity: `await siem.health_check()`
2. Verify SIEM credentials/tokens
3. Check network/firewall rules
4. Manual reset (temporary): `optimizer.circuit_breaker.reset()`
5. Increase `recovery_timeout` if SIEM needs more time
6. Reduce `failure_threshold` if too sensitive

### Compression Not Working

**Symptoms:**
- `compression_count=0` in metrics
- No bandwidth savings observed

**Diagnosis:**
```python
metrics = optimizer.get_metrics()
comp = metrics['compression']
print(f"Enabled: {comp['enabled']}")
print(f"Count: {comp['count']}")
print(f"Uncompressed: {comp['uncompressed_sends']}")
```

**Solutions:**
1. Check if enabled: `compression_config.enabled=True`
2. Verify payload size > `min_size_bytes` (default 1KB)
3. Check if compressed size is actually smaller (may skip if not beneficial)
4. Lower `min_size_bytes` if events are small

### Health Monitoring Not Running

**Symptoms:**
- `last_check=None` in metrics
- No health status updates

**Diagnosis:**
```python
metrics = optimizer.get_metrics()
health = metrics['health']
print(f"Enabled: {health['enabled']}")
print(f"Last check: {health['last_check']}")
print(f"Is healthy: {health['is_healthy']}")
```

**Solutions:**
1. Verify enabled: `health_config.enabled=True`
2. Start monitoring: `await optimizer.start_health_monitoring()`
3. Check for exceptions in health check loop (see logs)
4. Verify SIEM implements `health_check()` method

## Best Practices

### 1. Always Use Circuit Breaker

Prevent cascading failures in production:

```python
# ✅ GOOD - With circuit breaker
optimizer = SIEMOptimizer(
    siem=splunk,
    circuit_config=CircuitBreakerConfig(failure_threshold=5),
)

# ❌ BAD - Without circuit breaker (can cascade failures)
# Direct SIEM usage in production
```

### 2. Enable Compression for High-Volume

For deployments with >1k events/min:

```python
# ✅ GOOD - Compression enabled
optimizer = SIEMOptimizer(
    siem=splunk,
    compression_config=CompressionConfig(
        enabled=True,
        min_size_bytes=1024,  # Compress if > 1KB
    ),
)
```

### 3. Monitor Health in Production

Always enable health monitoring:

```python
# ✅ GOOD - Health monitoring enabled
optimizer = SIEMOptimizer(
    siem=splunk,
    health_config=HealthMonitorConfig(
        enabled=True,
        check_interval_seconds=30,
    ),
)
await optimizer.start_health_monitoring()
```

### 4. Use Optimal Batch Sizes

Calculate based on event size:

```python
# ✅ GOOD - Calculated batch size
event_size = estimate_event_size(sample_event)
batch_size = get_optimal_batch_size(event_size, target_batch_size_kb=100)

batch_handler = BatchHandler(
    callback=optimizer.send_batch,
    config=BatchConfig(batch_size=batch_size),
)

# ❌ BAD - Hardcoded arbitrary batch size
batch_handler = BatchHandler(
    callback=optimizer.send_batch,
    config=BatchConfig(batch_size=42),  # Why 42?
)
```

### 5. Graceful Shutdown

Always flush and cleanup:

```python
# ✅ GOOD - Proper shutdown
await batch_handler.stop(flush=True)  # Flush pending events
await optimizer.stop_health_monitoring()
metrics = optimizer.get_metrics()
logger.info("Shutdown complete", metrics=metrics)

# ❌ BAD - Abrupt shutdown (loses pending events)
# Just exit without flush
```

## Testing

### Unit Tests

The optimizations include comprehensive test coverage:

- **Circuit Breaker**: 17 tests, 94.78% coverage
- **SIEM Optimizer**: 25 tests, 89.69% coverage
- **Total**: 42 tests covering all features

Run tests:
```bash
pytest tests/test_audit/test_circuit_breaker.py -v
pytest tests/test_audit/test_siem_optimizer.py -v
```

### Integration Testing

Test with actual SIEM endpoints:

```python
import asyncio
from sark.services.audit.siem import SIEMOptimizer, SplunkSIEM, SplunkConfig

async def test_production_siem():
    """Integration test with real Splunk."""

    splunk = SplunkSIEM(SplunkConfig(
        hec_url="https://splunk-test.example.com:8088/services/collector",
        hec_token=os.environ["SPLUNK_TEST_TOKEN"],
        index="sark_test",
    ))

    optimizer = SIEMOptimizer(siem=splunk, name="splunk-test")
    await optimizer.start_health_monitoring()

    # Test sending
    test_event = create_test_audit_event()
    result = await optimizer.send_event(test_event)
    assert result is True

    # Check health
    assert optimizer.is_healthy() is True

    # Check metrics
    metrics = optimizer.get_metrics()
    print(f"Metrics: {metrics}")

    await optimizer.stop_health_monitoring()

if __name__ == "__main__":
    asyncio.run(test_production_siem())
```

## Migration Guide

### From Direct SIEM Usage

**Before:**
```python
splunk = SplunkSIEM(config)
await splunk.send_event(event)
```

**After:**
```python
splunk = SplunkSIEM(config)
optimizer = SIEMOptimizer(
    siem=splunk,
    name="splunk",
    # All optimizations enabled by default
)
await optimizer.start_health_monitoring()
await optimizer.send_event(event)
```

### Backward Compatibility

The optimizer is fully backward compatible - all existing code works:

```python
# Old code still works
await splunk.send_event(event)

# New code uses optimizer
await optimizer.send_event(event)  # Wraps splunk.send_event()
```

---

**Version:** 1.0
**Last Updated:** 2025-11-22
**Maintainer:** Engineer 3 (SIEM Lead)
