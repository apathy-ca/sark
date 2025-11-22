# SARK Performance Load Testing

This directory contains comprehensive performance and load testing infrastructure for the SARK API using both **Locust** and **k6**.

## Table of Contents

- [Overview](#overview)
- [Performance Targets](#performance-targets)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Test Scenarios](#test-scenarios)
- [Running Tests](#running-tests)
- [Analyzing Results](#analyzing-results)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)

## Overview

We use two complementary load testing tools:

- **Locust**: Python-based, developer-friendly, excellent for complex user behaviors
- **k6**: JavaScript-based, high performance, excellent for CI/CD integration

### Why Two Tools?

- **Locust** is great for:
  - Complex test scenarios with stateful behavior
  - Python developers familiar with the codebase
  - Real-time monitoring via web UI

- **k6** is great for:
  - High-performance load generation
  - CI/CD pipeline integration
  - Consistent test execution environments
  - Better reporting and metrics

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| API Response Time (p95) | < 100ms | < 200ms |
| Server Registration (p95) | < 200ms | < 500ms |
| Policy Evaluation (p95) | < 50ms | < 100ms |
| Database Queries | < 20ms | < 50ms |
| Error Rate | < 1% | < 5% |
| Throughput (Server Registration) | 1000 req/s | 500 req/s |
| Throughput (Policy Evaluation) | 2000 req/s | 1000 req/s |
| Availability | 99.9% | 99.5% |

## Installation

### Prerequisites

- Python 3.11+
- Node.js 16+ (for k6 HTML reports)
- Docker (optional, for isolated testing)

### Install Locust

```bash
# Install Locust and dependencies
pip install -r requirements-dev.txt

# Verify installation
locust --version
```

### Install k6

#### macOS
```bash
brew install k6
```

#### Linux (Debian/Ubuntu)
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

#### Windows
```powershell
choco install k6
```

#### Docker
```bash
docker pull grafana/k6:latest
```

Verify installation:
```bash
k6 version
```

## Quick Start

### 1. Start SARK API

Ensure the SARK API is running:

```bash
# From project root
uvicorn sark.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Create API Key for Testing

```bash
# Create a test API key (requires admin access)
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "load-test-key",
    "description": "API key for load testing",
    "scopes": ["server:read", "server:write", "policy:evaluate"],
    "rate_limit": 10000,
    "environment": "test"
  }'

# Save the returned API key
export TEST_API_KEY="sk_live_xxxxxxxxxxxxx"
```

### 3. Run Smoke Test

#### Locust
```bash
cd tests/performance
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1 --spawn-rate 1 --run-time 30s --headless \
  MixedWorkloadUser
```

#### k6
```bash
cd tests/performance
k6 run --vus 1 --duration 30s k6_script.js
```

## Test Scenarios

### Available Scenarios

| Scenario | Description | Users | Duration | Purpose |
|----------|-------------|-------|----------|---------|
| `smoke_test` | Basic functionality check | 1 | 30s | Verify API is working |
| `load_test_moderate` | Moderate sustained load | 100 | 5m | Baseline performance |
| `load_test_high` | High sustained load | 500 | 10m | High traffic performance |
| `server_registration_focused` | Server registration stress | 200 | 5m | Test registration at 1000 req/s |
| `policy_evaluation_focused` | Policy evaluation stress | 500 | 5m | Test policy eval at high load |
| `stress_test` | Find breaking point | 1000 | 15m | Determine max capacity |
| `spike_test` | Sudden traffic spike | 500 | 5m | Test auto-scaling/recovery |
| `soak_test` | Long-running stability | 50 | 30m | Detect memory leaks |
| `rate_limit_test` | Rate limiting behavior | 100 | 2m | Verify rate limits work |
| `database_stress` | Database performance | 200 | 10m | Test DB query performance |
| `concurrent_operations` | Concurrency & race conditions | 300 | 5m | Test data consistency |

## Running Tests

### Locust Tests

#### Using Web UI (Recommended for Development)

```bash
cd tests/performance

# Start Locust web UI
locust -f locustfile.py --host=http://localhost:8000

# Open browser to http://localhost:8089
# Configure users and spawn rate in the UI
```

#### Headless Mode (Recommended for CI/CD)

```bash
# Moderate load test
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m \
  --headless --html=reports/locust_report.html

# Server registration focused test
locust -f locustfile.py --host=http://localhost:8000 \
  --users 200 --spawn-rate 20 --run-time 5m \
  --headless --html=reports/server_reg_test.html \
  ServerRegistrationUser

# Policy evaluation focused test
locust -f locustfile.py --host=http://localhost:8000 \
  --users 500 --spawn-rate 50 --run-time 5m \
  --headless --html=reports/policy_eval_test.html \
  PolicyEvaluationUser

# Stress test
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 100 --run-time 15m \
  --headless --html=reports/stress_test.html

# Soak test (30 minutes)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 10 --run-time 30m \
  --headless --html=reports/soak_test.html
```

#### Using Configuration File

```bash
locust --config=config/locust.conf
```

#### Distributed Testing

For very high load, run Locust in distributed mode:

```bash
# Start master
locust -f locustfile.py --master --host=http://localhost:8000

# Start workers (in separate terminals or machines)
locust -f locustfile.py --worker --master-host=localhost
locust -f locustfile.py --worker --master-host=localhost
locust -f locustfile.py --worker --master-host=localhost
```

### k6 Tests

#### Basic Tests

```bash
cd tests/performance

# Smoke test
k6 run --vus 1 --duration 30s k6_script.js

# Load test
k6 run --vus 100 --duration 5m k6_script.js

# Stress test with stages
k6 run --stage 1m:100,3m:500,1m:100,1m:0 k6_script.js
```

#### Specific Scenarios

```bash
# Server registration test
k6 run --env SCENARIO=server_registration --vus 200 --duration 5m k6_script.js

# Policy evaluation test
k6 run --env SCENARIO=policy_evaluation --vus 500 --duration 5m k6_script.js
```

#### Generate Reports

```bash
# Run test and save results
k6 run --out json=reports/k6_results.json k6_script.js

# Convert to HTML (requires k6-to-junit or custom script)
# Install: npm install -g k6-to-junit
k6 run --out json=reports/k6_results.json k6_script.js

# Or use Docker for HTML reports
docker run -i grafana/k6 run --out json=/dev/stdout - < k6_script.js > reports/k6_results.json
```

#### Cloud Testing

```bash
# Sign up at k6.io/cloud
k6 login cloud

# Run in k6 cloud
k6 cloud k6_script.js
```

## Analyzing Results

### Locust Reports

Locust generates three types of reports:

1. **HTML Report** (`--html=reports/report.html`)
   - Request statistics
   - Response time charts
   - Failures breakdown
   - RPS over time

2. **CSV Reports** (`--csv=reports/stats`)
   - `*_stats.csv`: Request statistics
   - `*_stats_history.csv`: Statistics over time
   - `*_failures.csv`: All failures

3. **Real-time Web UI** (http://localhost:8089)
   - Live charts and metrics
   - Current RPS and response times
   - Failure monitoring

### k6 Reports

k6 provides detailed terminal output with:

- Request duration (min, avg, median, max, p90, p95)
- Success rate
- Throughput (requests/second)
- Data transferred
- Custom metrics

#### Key Metrics to Monitor

```
http_req_duration..............: avg=45.2ms min=12ms med=38ms max=892ms p(90)=78ms p(95)=105ms
http_req_failed................: 0.12%  ✗ 124  ✓ 99876
http_reqs......................: 100000  1666.67/s
server_registration_duration...: avg=156ms min=45ms med=142ms max=1.2s p(90)=245ms p(95)=312ms
policy_evaluation_duration.....: avg=38ms min=8ms med=34ms max=456ms p(90)=62ms p(95)=78ms
```

### Performance Analysis Checklist

After running load tests, analyze:

1. **Response Times**
   - [ ] p50 (median) within targets
   - [ ] p95 within targets
   - [ ] p99 acceptable
   - [ ] Max response time reasonable

2. **Throughput**
   - [ ] Requests per second meets targets
   - [ ] Consistent throughout test duration
   - [ ] No degradation over time (soak test)

3. **Error Rate**
   - [ ] Total errors < 1%
   - [ ] No 5xx errors (server errors)
   - [ ] Expected 4xx errors (validation, auth)

4. **Resource Utilization** (monitor separately)
   - [ ] CPU usage < 80%
   - [ ] Memory stable (no leaks)
   - [ ] Database connections healthy
   - [ ] Redis connections healthy

5. **Bottleneck Identification**
   - [ ] Identify slowest endpoints
   - [ ] Check database query times
   - [ ] Review external service calls
   - [ ] Analyze rate limiting impact

## Bottleneck Analysis

### Common Bottlenecks

1. **Database**
   - **Symptom**: High p95 latency, slow queries
   - **Check**: `SELECT * FROM pg_stat_activity;`
   - **Solutions**: Add indexes, optimize queries, increase connection pool

2. **OPA Policy Engine**
   - **Symptom**: Policy evaluation > 50ms
   - **Check**: OPA response times
   - **Solutions**: Optimize policies, cache decisions, increase OPA resources

3. **Redis**
   - **Symptom**: Session/rate limit operations slow
   - **Check**: `redis-cli --latency`
   - **Solutions**: Increase Redis memory, use Redis cluster

4. **Application**
   - **Symptom**: All endpoints slow
   - **Check**: CPU/memory usage
   - **Solutions**: Increase workers, optimize code, add caching

### Monitoring During Tests

```bash
# Terminal 1: Run load test
locust -f locustfile.py --users 100 --spawn-rate 10

# Terminal 2: Monitor API logs
tail -f /var/log/sark/api.log

# Terminal 3: Monitor database
psql -U sark -d sark -c "SELECT * FROM pg_stat_activity;"

# Terminal 4: Monitor system resources
htop

# Terminal 5: Monitor Redis
redis-cli --latency-history
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution**: Ensure SARK API is running on the correct host/port.

```bash
# Check if API is running
curl http://localhost:8000/health/

# Start API if not running
uvicorn sark.api.main:app --host 0.0.0.0 --port 8000
```

#### 2. Authentication Failures

```
401 Unauthorized: Missing or invalid API key
```

**Solution**: Set valid API key in test configuration.

```bash
# Update in locustfile.py
TEST_API_KEY = "sk_live_your_actual_key"

# Or pass as environment variable
export TEST_API_KEY="sk_live_your_actual_key"
```

#### 3. Rate Limiting Hits

```
429 Too Many Requests
```

**Solution**: This may be expected behavior. Check if:
- You're testing rate limits (expected)
- Need to increase rate limits for testing
- Need to disable rate limiting for load tests

```python
# Temporarily disable rate limiting in settings
RATE_LIMIT_ENABLED=false
```

#### 4. Database Connection Pool Exhausted

```
OperationalError: connection pool exhausted
```

**Solution**: Increase database connection pool size.

```python
# In settings.py
POSTGRES_POOL_SIZE = 50
POSTGRES_MAX_OVERFLOW = 20
```

#### 5. OOM (Out of Memory) Errors

**Solution**:
- Reduce number of concurrent users
- Increase server memory
- Check for memory leaks (run soak test)

```bash
# Monitor memory during test
watch -n 1 'free -h'
```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/performance-test.yml`:

```yaml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM
  workflow_dispatch:     # Allow manual trigger

jobs:
  performance-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg15
        env:
          POSTGRES_USER: sark
          POSTGRES_PASSWORD: sark
          POSTGRES_DB: sark
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .[dev]

      - name: Start SARK API
        run: |
          uvicorn sark.api.main:app --host 0.0.0.0 --port 8000 &
          sleep 10

      - name: Run Locust Load Test
        run: |
          cd tests/performance
          locust -f locustfile.py --host=http://localhost:8000 \
            --users 100 --spawn-rate 10 --run-time 5m \
            --headless --html=../../reports/performance_report.html \
            --csv=../../reports/performance_stats

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: performance-reports
          path: reports/

      - name: Check Performance Thresholds
        run: |
          python tests/performance/check_thresholds.py \
            --csv reports/performance_stats_stats.csv \
            --p95-threshold 100
```

### GitLab CI Example

Create `.gitlab-ci.yml`:

```yaml
performance-test:
  stage: test
  image: python:3.11

  services:
    - name: timescale/timescaledb:latest-pg15
      alias: postgres
    - name: redis:7-alpine
      alias: redis

  variables:
    POSTGRES_HOST: postgres
    REDIS_HOST: redis

  before_script:
    - pip install -e .[dev]
    - uvicorn sark.api.main:app --host 0.0.0.0 --port 8000 &
    - sleep 10

  script:
    - cd tests/performance
    - locust -f locustfile.py --host=http://localhost:8000
        --users 100 --spawn-rate 10 --run-time 5m
        --headless --html=../../reports/performance.html

  artifacts:
    paths:
      - reports/
    expire_in: 30 days

  only:
    - schedules
    - web
```

## Best Practices

### 1. Test Environment

- **Use dedicated test environment**: Don't run load tests against production
- **Match production specs**: Use similar hardware/resources as production
- **Isolate tests**: Run tests on dedicated infrastructure
- **Clean data**: Reset database between test runs for consistency

### 2. Test Design

- **Start small**: Begin with smoke tests, gradually increase load
- **Realistic scenarios**: Model actual user behavior patterns
- **Ramp up gradually**: Don't spike to max users immediately
- **Monitor everything**: Track API, database, Redis, system metrics

### 3. Analysis

- **Baseline first**: Establish baseline performance before optimization
- **Compare runs**: Track performance over time
- **Percentiles matter**: Focus on p95/p99, not just averages
- **Identify bottlenecks**: Use profiling to find root causes

### 4. Continuous Testing

- **Automate tests**: Run performance tests in CI/CD
- **Track trends**: Monitor performance degradation over time
- **Set alerts**: Alert on performance threshold violations
- **Review regularly**: Include performance reviews in sprint planning

## Performance Optimization Tips

Based on test results, consider these optimizations:

### 1. Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_servers_status ON mcp_servers(status);
CREATE INDEX idx_servers_sensitivity ON mcp_servers(sensitivity_level);
CREATE INDEX idx_audit_user_timestamp ON audit_events(user_id, timestamp DESC);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM mcp_servers WHERE status = 'active';

-- Increase connection pool
ALTER SYSTEM SET max_connections = 200;
```

### 2. Redis Optimization

```bash
# Increase memory limit
redis-cli CONFIG SET maxmemory 2gb

# Use Redis pipeline for batch operations
# (already implemented in rate_limiter.py)
```

### 3. Application Optimization

```python
# Add caching for frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_server_cached(server_id: str):
    return get_server(server_id)

# Use connection pooling
# (already implemented in db/session.py)

# Increase worker count
uvicorn sark.api.main:app --workers 8
```

### 4. OPA Optimization

```bash
# Cache policy decisions
# Enable OPA decision logging
# Use OPA bundles for faster policy loading
```

## Report Templates

### Performance Test Report Template

```markdown
# Performance Test Report - YYYY-MM-DD

## Test Configuration
- **Date**: YYYY-MM-DD
- **Duration**: 5 minutes
- **Users**: 100 concurrent
- **Spawn Rate**: 10 users/second
- **Scenario**: Mixed Workload

## Results Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| API p95 | <100ms | 87ms | ✅ PASS |
| Server Reg p95 | <200ms | 156ms | ✅ PASS |
| Policy Eval p95 | <50ms | 38ms | ✅ PASS |
| Error Rate | <1% | 0.12% | ✅ PASS |
| Throughput | 1000 req/s | 1245 req/s | ✅ PASS |

## Key Findings

1. **Performance**: All metrics within targets
2. **Bottlenecks**: None identified
3. **Errors**: Minimal errors, all related to validation

## Recommendations

1. Current capacity supports up to 150 concurrent users
2. Consider caching for server listing endpoint
3. Monitor database connection pool during peak hours

## Attachments
- [Locust HTML Report](./locust_report.html)
- [CSV Statistics](./performance_stats.csv)
```

## Additional Resources

- [Locust Documentation](https://docs.locust.io/)
- [k6 Documentation](https://k6.io/docs/)
- [Performance Testing Best Practices](https://k6.io/docs/testing-guides/load-testing/)
- [SARK API Documentation](../../docs/API.md)

## Support

For questions or issues with performance testing:

1. Check this README and troubleshooting section
2. Review Locust/k6 documentation
3. Check application logs and metrics
4. Contact the infrastructure team

---

**Last Updated**: 2024-11-22
**Maintained By**: SARK Infrastructure Team
