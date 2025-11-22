# SARK Load Testing Guide

This directory contains comprehensive load testing tools for SARK policy evaluation performance testing.

## Quick Start

### Prerequisites

```bash
# Install Locust
pip install locust

# Install K6 (Linux)
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Or use Docker
docker pull grafana/k6:latest
```

## Locust Load Tests

### Basic Usage

```bash
# Start Locust web UI (recommended for interactive testing)
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Open browser to http://localhost:8089
# Set number of users and spawn rate in UI
```

### Headless Mode

```bash
# Run with 100 users for 5 minutes
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --users 100 --spawn-rate 10 --run-time 5m --headless

# Generate HTML report
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --users 100 --spawn-rate 10 --run-time 5m --headless \
       --html reports/locust_report.html

# Generate CSV data
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --users 100 --spawn-rate 10 --run-time 5m --headless \
       --csv reports/locust_data
```

### Load Shapes

```bash
# Step load (gradual increase)
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --headless --shape StepLoadShape

# Spike load (traffic spikes)
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --headless --shape SpikeLoadShape
```

### Test Scenarios

**PolicyEvaluationUser** (Normal Traffic):
- 50% cached policy evaluations (tools 1-10)
- 30% unique policy evaluations (tools 1-10,000)
- 15% critical tool evaluations
- 5% server registration

**BurstUser** (Burst Traffic):
- Rapid-fire requests (10-100ms between)
- Tests cache performance under load

## K6 Load Tests

### Basic Usage

```bash
# Run default scenario (10 VUs for 30s)
k6 run tests/load/policy_load_test.js

# Custom load
k6 run --vus 100 --duration 5m tests/load/policy_load_test.js
```

### Test Scenarios

```bash
# Staged load (gradual ramp-up)
k6 run tests/load/policy_load_test.js -e SCENARIO=staged

# Spike test (sudden load spikes)
k6 run tests/load/policy_load_test.js -e SCENARIO=spike

# Stress test (push to limits)
k6 run tests/load/policy_load_test.js -e SCENARIO=stress

# Soak test (30-minute sustained load)
k6 run tests/load/policy_load_test.js -e SCENARIO=soak
```

### Generate Reports

```bash
# JSON output
k6 run --out json=test_results.json tests/load/policy_load_test.js

# InfluxDB output (for Grafana)
k6 run --out influxdb=http://localhost:8086/k6 tests/load/policy_load_test.js

# Cloud output
k6 cloud tests/load/policy_load_test.js
```

### Custom Configuration

```bash
# Change target URL
k6 run tests/load/policy_load_test.js -e BASE_URL=http://staging.example.com:8000

# Combined
k6 run tests/load/policy_load_test.js \
   -e SCENARIO=staged \
   -e BASE_URL=http://localhost:8000 \
   --out json=results.json
```

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| P95 Latency | <50ms | End-to-end policy evaluation |
| P99 Latency | <100ms | End-to-end policy evaluation |
| Cache Hit Latency | <5ms | Redis cache lookup |
| Throughput | >500 req/s | Sustained throughput |
| Success Rate | >95% | Overall success rate |
| Cache Hit Rate | >80% | For realistic traffic |

## Interpreting Results

### Locust Output

```
Name                          # reqs  # fails  Avg    Min    Max    Median  P95    P99    req/s
evaluate_policy_cached        5000    0        8      3      45     7       15     25     166.67
evaluate_policy_unique        3000    5        38     10     120    35      68     95     100.00
evaluate_policy_critical      1500    0        42     15     95     40      75     88     50.00
```

**Good Indicators:**
- P95 < 50ms ✅
- Failure rate < 1% ✅
- Cache hit latency < 10ms ✅
- Throughput > 500 req/s ✅

**Warning Signs:**
- P95 > 75ms ⚠️
- Failure rate > 5% ⚠️
- High variance (max >> p95) ⚠️
- Declining throughput over time ⚠️

### K6 Output

```
     ✓ status is 200
     ✓ has allow field
     ✓ latency < 50ms

     checks.........................: 100.00% ✓ 15000     ✗ 0
     http_req_duration..............: avg=35ms    p95=48ms    p99=72ms
     policy_evaluation_success......: 98.5%
     cache_hits.....................: 8000
     cache_misses...................: 2000
```

**Good Indicators:**
- All checks passing ✅
- P95 < 50ms ✅
- Success rate > 95% ✅
- Cache hit rate > 75% ✅

## Common Issues

### High Latency

**Symptoms:**
- P95 > 100ms
- Increasing latency over time

**Troubleshooting:**
1. Check Redis connection pool size
2. Verify OPA is not CPU-bound
3. Check network latency to Redis/OPA
4. Review cache hit rate
5. Check for database slow queries

```bash
# Monitor Redis
redis-cli INFO stats
redis-cli --latency-history

# Monitor OPA CPU
docker stats opa

# Check cache metrics
curl http://localhost:8000/metrics | grep cache
```

### Low Throughput

**Symptoms:**
- < 300 req/s sustained
- Declining RPS over time

**Troubleshooting:**
1. Check connection pool exhaustion
2. Verify async operations are truly async
3. Check for blocking operations
4. Review resource limits (CPU, memory, connections)

```bash
# Check system resources
htop
docker stats

# Check connection pool
redis-cli CLIENT LIST | wc -l
```

### High Error Rate

**Symptoms:**
- > 5% failures
- Timeout errors

**Troubleshooting:**
1. Check for OPA errors in logs
2. Verify Redis availability
3. Check network connectivity
4. Review resource exhaustion

```bash
# Check logs
docker logs sark-api --tail=100
docker logs opa --tail=100
docker logs redis --tail=100

# Check connectivity
redis-cli PING
curl http://localhost:8181/health
```

## Best Practices

### 1. Start Small

```bash
# Baseline test (10 users)
k6 run --vus 10 --duration 1m tests/load/policy_load_test.js

# Then gradually increase
k6 run tests/load/policy_load_test.js -e SCENARIO=staged
```

### 2. Monitor During Tests

```bash
# Terminal 1: Run load test
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Terminal 2: Monitor metrics
watch -n 1 'curl -s http://localhost:8000/metrics | grep policy_evaluation'

# Terminal 3: Monitor Redis
watch -n 1 'redis-cli INFO stats | grep instantaneous'

# Terminal 4: Monitor system
htop
```

### 3. Warm-Up Period

Always include a warm-up period before measuring:

```bash
# K6 with warm-up
k6 run tests/load/policy_load_test.js -e SCENARIO=staged
# First stage (1m, 10 users) is warm-up

# Locust: Ignore first 30s of metrics
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --run-time 5m30s  # 30s warm-up + 5m test
```

### 4. Realistic Traffic Patterns

Use the default test distribution:
- 50% cached (common tools)
- 30% unique (diverse tools)
- 15% critical (high security)
- 5% admin operations

### 5. Soak Testing

Test for extended periods to catch memory leaks:

```bash
# 30-minute soak test
k6 run tests/load/policy_load_test.js -e SCENARIO=soak

# Monitor memory over time
while true; do
  docker stats --no-stream sark-api redis opa | ts
  sleep 60
done
```

## Example Workflow

### Pre-Production Performance Validation

```bash
# 1. Baseline test
k6 run --vus 10 --duration 2m tests/load/policy_load_test.js

# 2. Staged load test
k6 run tests/load/policy_load_test.js -e SCENARIO=staged \
   --out json=results/staged.json

# 3. Spike test
k6 run tests/load/policy_load_test.js -e SCENARIO=spike \
   --out json=results/spike.json

# 4. Soak test (if time permits)
k6 run tests/load/policy_load_test.js -e SCENARIO=soak \
   --out json=results/soak.json

# 5. Generate report
python scripts/analyze_performance.py results/
```

### CI/CD Performance Gate

```yaml
# .github/workflows/performance-test.yml
- name: Performance Test
  run: |
    k6 run --vus 50 --duration 2m tests/load/policy_load_test.js
    # Fail if P95 > 50ms or success rate < 95%
```

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [K6 Documentation](https://k6.io/docs/)
- [SARK Performance Report](../../docs/POLICY_PERFORMANCE_REPORT.md)
- [Prometheus Metrics Guide](../../docs/MONITORING.md)

## Support

For issues or questions:
1. Check the [Performance Report](../../docs/POLICY_PERFORMANCE_REPORT.md)
2. Review [Optimization Recommendations](../../docs/POLICY_PERFORMANCE_REPORT.md#optimization-recommendations)
3. Open an issue with test results and logs
