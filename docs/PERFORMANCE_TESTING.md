# SARK Performance Testing Guide

**Comprehensive Performance Testing Methodology and Best Practices**

**Version:** 1.0
**Last Updated:** 2025-11-22
**Audience:** QA Engineers, Performance Engineers, DevOps Teams

---

## Table of Contents

1. [Overview](#overview)
2. [Performance Testing Strategy](#performance-testing-strategy)
3. [Testing Tools](#testing-tools)
4. [Load Testing](#load-testing)
5. [Stress Testing](#stress-testing)
6. [Endurance Testing](#endurance-testing)
7. [Spike Testing](#spike-testing)
8. [Scalability Testing](#scalability-testing)
9. [Benchmarking](#benchmarking)
10. [Performance Profiling](#performance-profiling)
11. [Database Performance Testing](#database-performance-testing)
12. [Cache Performance Testing](#cache-performance-testing)
13. [API Performance Testing](#api-performance-testing)
14. [Policy Evaluation Performance](#policy-evaluation-performance)
15. [SIEM Integration Performance](#siem-integration-performance)
16. [Monitoring & Metrics](#monitoring--metrics)
17. [Performance Test Automation](#performance-test-automation)
18. [Reporting & Analysis](#reporting--analysis)

---

## Overview

### Purpose

This guide provides comprehensive methodologies and best practices for performance testing SARK across all components and workloads. Performance testing ensures SARK meets production SLAs and scales to enterprise requirements.

### Performance Goals

| Component | Metric | Target | Critical Threshold |
|-----------|--------|--------|-------------------|
| **API Response Time** | p95 latency | <100ms | <200ms |
| **API Response Time** | p99 latency | <200ms | <500ms |
| **Policy Evaluation (cache hit)** | p95 latency | <5ms | <10ms |
| **Policy Evaluation (cache miss)** | p95 latency | <50ms | <100ms |
| **SIEM Event Forwarding** | Throughput | >10,000 events/min | >5,000 events/min |
| **SIEM Event Forwarding** | Latency | <100ms (p95) | <500ms (p95) |
| **Database Queries** | p95 latency | <20ms | <50ms |
| **Redis Operations** | p95 latency | <2ms | <5ms |
| **Concurrent Users** | Support | 1,000 concurrent | 500 concurrent |
| **Requests Per Second** | Throughput | >1,000 RPS | >500 RPS |
| **Error Rate** | Percentage | <0.1% | <1% |
| **Availability** | Uptime | 99.9% | 99.5% |

### SLA Definitions

**Response Time SLAs:**
- **Critical APIs** (auth, policy eval): p95 <100ms, p99 <200ms
- **Standard APIs** (CRUD operations): p95 <200ms, p99 <500ms
- **Bulk Operations**: p95 <1s, p99 <3s

**Throughput SLAs:**
- **Authentication**: >100 logins/sec
- **Policy Evaluation**: >500 evaluations/sec
- **Server Registration**: >50 registrations/sec
- **SIEM Forwarding**: >10,000 events/min

**Availability SLAs:**
- **Production**: 99.9% (8.76 hours downtime/year)
- **Staging**: 99.5% (43.8 hours downtime/year)

---

## Performance Testing Strategy

### Testing Pyramid

```
           /\
          /  \  Production Testing (5%)
         /────\  - Canary releases
        /      \ - Synthetic monitoring
       /────────\
      /          \ Performance Testing (15%)
     /────────────\ - Load tests
    /              \ - Stress tests
   /────────────────\ - Endurance tests
  /                  \
 /──────────────────────\ Development Testing (80%)
/                        \ - Unit benchmarks
──────────────────────────── - Integration benchmarks
                             - Local profiling
```

### Test Types

#### 1. Load Testing
**Purpose:** Validate system behavior under expected load
**Frequency:** Every release
**Duration:** 30-60 minutes
**Load:** 70% of expected peak load

#### 2. Stress Testing
**Purpose:** Find breaking point and failure modes
**Frequency:** Monthly
**Duration:** 30 minutes
**Load:** Gradually increase from 100% to 200%+ of peak

#### 3. Endurance Testing (Soak Testing)
**Purpose:** Detect memory leaks and degradation over time
**Frequency:** Before major releases
**Duration:** 24-72 hours
**Load:** 70% of expected peak load

#### 4. Spike Testing
**Purpose:** Validate behavior under sudden traffic spikes
**Frequency:** Quarterly
**Duration:** 15-30 minutes
**Load:** Sudden spike to 200% for 5 minutes

#### 5. Scalability Testing
**Purpose:** Validate horizontal/vertical scaling
**Frequency:** Quarterly
**Duration:** 2-4 hours
**Load:** Test with increasing resources (pods, memory, CPU)

---

## Testing Tools

### Load Testing Frameworks

#### Locust (Primary)

**Why Locust:**
- Python-based (matches SARK tech stack)
- Distributed load generation
- Real-time web UI
- Easy to write custom scenarios

**Installation:**
```bash
pip install locust
```

**Example Locust Test:**
```python
# locustfile.py
from locust import HttpUser, task, between
import random

class SARKUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        """Authenticate and get token"""
        response = self.client.post("/api/v1/auth/login/ldap", json={
            "username": "testuser",
            "password": "password"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            self.token = None

    @task(5)
    def list_servers(self):
        """List servers (most common operation - 50% of traffic)"""
        if self.token:
            self.client.get(
                "/api/v1/servers?limit=50",
                headers={"Authorization": f"Bearer {self.token}"},
                name="/api/v1/servers"
            )

    @task(2)
    def get_server(self):
        """Get specific server (20% of traffic)"""
        if self.token:
            server_id = random.choice(self.server_ids)
            self.client.get(
                f"/api/v1/servers/{server_id}",
                headers={"Authorization": f"Bearer {self.token}"},
                name="/api/v1/servers/{id}"
            )

    @task(2)
    def evaluate_policy(self):
        """Evaluate policy (20% of traffic)"""
        if self.token:
            self.client.post(
                "/api/v1/policy/evaluate",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "user_id": "test-user-id",
                    "action": "tool:invoke",
                    "tool": "execute_query"
                },
                name="/api/v1/policy/evaluate"
            )

    @task(1)
    def register_server(self):
        """Register server (10% of traffic)"""
        if self.token:
            self.client.post(
                "/api/v1/servers",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": f"loadtest-server-{random.randint(1, 10000)}",
                    "transport": "http",
                    "endpoint": f"http://server{random.randint(1, 100)}.example.com",
                    "capabilities": ["tools"],
                    "tools": [],
                    "sensitivity_level": random.choice(["low", "medium", "high"])
                },
                name="/api/v1/servers [POST]"
            )
```

**Run Load Test:**
```bash
# Web UI mode
locust -f locustfile.py

# Headless mode (CI/CD)
locust -f locustfile.py \
  --headless \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 30m \
  --host http://sark.example.com

# Distributed mode (multiple workers)
# Master
locust -f locustfile.py --master

# Workers (run on multiple machines)
locust -f locustfile.py --worker --master-host=master-ip
```

---

#### k6 (Alternative)

**Why k6:**
- JavaScript-based (familiar to many developers)
- Built-in checks and thresholds
- Excellent for CI/CD integration
- Powerful metrics and tags

**Installation:**
```bash
# macOS
brew install k6

# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Example k6 Test:**
```javascript
// loadtest.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Ramp up to 200 users
    { duration: '5m', target: 200 },  // Stay at 200 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<200'],  // 95% of requests < 200ms
    'errors': ['rate<0.01'],             // Error rate < 1%
    'http_req_duration{name:auth}': ['p(95)<100'],
    'http_req_duration{name:policy}': ['p(95)<50'],
  },
};

const BASE_URL = 'http://localhost:8000';
let token = '';

export function setup() {
  // Authenticate once
  const loginRes = http.post(`${BASE_URL}/api/v1/auth/login/ldap`, JSON.stringify({
    username: 'testuser',
    password: 'password',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  return { token: loginRes.json('access_token') };
}

export default function(data) {
  token = data.token;

  // List servers
  const serversRes = http.get(`${BASE_URL}/api/v1/servers?limit=50`, {
    headers: { 'Authorization': `Bearer ${token}` },
    tags: { name: 'list_servers' },
  });

  check(serversRes, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  }) || errorRate.add(1);

  sleep(1);

  // Evaluate policy
  const policyRes = http.post(`${BASE_URL}/api/v1/policy/evaluate`, JSON.stringify({
    user_id: 'test-user-id',
    action: 'tool:invoke',
    tool: 'execute_query',
  }), {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    tags: { name: 'policy' },
  });

  check(policyRes, {
    'status is 200': (r) => r.status === 200,
    'response time < 50ms': (r) => r.timings.duration < 50,
  }) || errorRate.add(1);

  sleep(1);
}
```

**Run k6 Test:**
```bash
# Run test
k6 run loadtest.js

# Output to InfluxDB + Grafana
k6 run --out influxdb=http://localhost:8086/k6 loadtest.js

# Cloud execution
k6 cloud loadtest.js
```

---

### Apache JMeter

**Use Cases:**
- Complex test scenarios with many steps
- Recording browser interactions
- Testing non-HTTP protocols

**Installation:**
```bash
# Download from https://jmeter.apache.org/
wget https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.2.tgz
tar -xzf apache-jmeter-5.6.2.tgz
cd apache-jmeter-5.6.2/bin
./jmeter
```

---

### Artillery

**Use Cases:**
- Quick load tests
- Serverless testing
- CI/CD integration

**Installation:**
```bash
npm install -g artillery
```

**Example Artillery Test:**
```yaml
# artillery-test.yml
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 300
      arrivalRate: 50
      name: "Sustained load"
    - duration: 60
      arrivalRate: 100
      name: "Peak load"
  plugins:
    expect: {}
  processor: "./custom-functions.js"

scenarios:
  - name: "User flow"
    flow:
      - post:
          url: "/api/v1/auth/login/ldap"
          json:
            username: "testuser"
            password: "password"
          capture:
            - json: "$.access_token"
              as: "token"
      - get:
          url: "/api/v1/servers"
          headers:
            Authorization: "Bearer {{ token }}"
          expect:
            - statusCode: 200
            - contentType: json
      - post:
          url: "/api/v1/policy/evaluate"
          headers:
            Authorization: "Bearer {{ token }}"
          json:
            user_id: "test-user"
            action: "tool:invoke"
            tool: "test_tool"
```

**Run Artillery Test:**
```bash
artillery run artillery-test.yml
```

---

## Load Testing

### Load Test Planning

#### 1. Define Test Scenarios

**Scenario 1: Normal Business Hours**
- **Users:** 500 concurrent
- **Duration:** 1 hour
- **Ramp-up:** 5 minutes
- **Traffic Mix:**
  - 50% List servers
  - 20% Get server details
  - 20% Policy evaluation
  - 10% Server registration

**Scenario 2: Peak Traffic**
- **Users:** 1,000 concurrent
- **Duration:** 30 minutes
- **Ramp-up:** 10 minutes
- **Traffic Mix:** Same as Scenario 1

**Scenario 3: Burst Traffic**
- **Users:** 2,000 concurrent (spike)
- **Duration:** 5 minutes spike, then back to 500
- **Ramp-up:** Immediate (spike)

#### 2. Environment Preparation

```bash
# Scale up resources before testing
kubectl scale deployment sark --replicas=5 -n production

# Verify resources
kubectl get pods -n production
kubectl top pods -n production

# Clear caches (if testing cold performance)
kubectl exec -it redis-pod -- redis-cli FLUSHDB

# Warm up caches (if testing warm performance)
# Run small load test first to populate caches
```

#### 3. Execute Load Test

```bash
# Run Locust load test
locust -f locustfile.py \
  --headless \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 60m \
  --host https://sark.example.com \
  --csv=results/load-test \
  --html=results/load-test-report.html
```

#### 4. Monitor During Test

**Watch Key Metrics:**
```bash
# Watch Prometheus metrics
watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=rate(http_requests_total[1m]) | jq'

# Watch pod metrics
watch -n 5 'kubectl top pods -n production'

# Watch database connections
watch -n 5 'kubectl exec -it postgres-pod -- psql -U sark -c "SELECT count(*) FROM pg_stat_activity;"'

# Watch Redis memory
watch -n 5 'kubectl exec -it redis-pod -- redis-cli INFO memory | grep used_memory_human'
```

**Grafana Dashboards:**
- Open Grafana during test
- Watch "SARK Load Testing" dashboard
- Monitor CPU, memory, request rate, latency, error rate

#### 5. Analyze Results

**Locust Results:**
```
Type     Name                      # requests  # fails  Median  95%ile  99%ile  Avg    Min  Max
──────────────────────────────────────────────────────────────────────────────────────────────
GET      /api/v1/servers           45000       12       65      120     180     75     25   500
GET      /api/v1/servers/{id}      18000       5        50      95      140     60     20   350
POST     /api/v1/policy/evaluate   18000       8        35      70      110     45     15   280
POST     /api/v1/servers           9000        15       250     450     650     300    100  1200
──────────────────────────────────────────────────────────────────────────────────────────────
Total                              90000       40       70      150     200     85     15   1200

Response time percentiles (milliseconds):
 50%    70
 66%    95
 75%    115
 80%    130
 90%    160
 95%    200
 98%    280
 99%    350
100%    1200 (longest request)

Error rate: 0.044% (40 / 90000)
Requests per second: 25.0
```

**Pass/Fail Criteria:**
- ✅ p95 latency < 200ms for all endpoints (PASS: 200ms)
- ✅ Error rate < 0.1% (PASS: 0.044%)
- ✅ RPS > 20 (PASS: 25 RPS)
- ❌ POST /api/v1/servers p95 > 200ms (FAIL: 450ms) → Investigate

---

## Stress Testing

### Purpose
Find the breaking point and understand failure modes.

### Methodology

```python
# stress_test.py
from locust import HttpUser, task, between, events
import logging

class StressTestUser(HttpUser):
    wait_time = between(0.5, 1)  # Aggressive wait time

    @task
    def stress_endpoint(self):
        self.client.get("/api/v1/servers?limit=100")

# Custom load shape for stress test
from locust import LoadTestShape

class StressTestShape(LoadTestShape):
    """
    Gradually increase load until system breaks
    """
    def tick(self):
        run_time = self.get_run_time()

        if run_time < 300:  # 0-5 min: 100 users
            return (100, 10)
        elif run_time < 600:  # 5-10 min: 200 users
            return (200, 20)
        elif run_time < 900:  # 10-15 min: 400 users
            return (400, 40)
        elif run_time < 1200:  # 15-20 min: 800 users
            return (800, 80)
        elif run_time < 1500:  # 20-25 min: 1600 users
            return (1600, 160)
        elif run_time < 1800:  # 25-30 min: 3200 users (breaking point)
            return (3200, 320)
        else:
            return None  # Stop test

# Run with:
# locust -f stress_test.py --headless --host https://sark.example.com
```

### Identify Breaking Point

**Signs of System Failure:**
1. **Error rate spikes** above 1%
2. **Response times** exceed 5x normal (>500ms for standard APIs)
3. **Timeouts** start occurring
4. **Database connection pool** exhaustion
5. **Redis max clients** reached
6. **OOM (Out of Memory)** kills
7. **CPU throttling** at 100%

**Example Stress Test Results:**
```
Time    Users  RPS    p95 Latency  Error Rate  CPU   Memory
────────────────────────────────────────────────────────────
0-5m    100    25     120ms        0.02%       30%   1.2GB
5-10m   200    50     150ms        0.05%       45%   1.5GB
10-15m  400    100    200ms        0.10%       65%   2.0GB
15-20m  800    180    350ms        0.50%       85%   2.8GB
20-25m  1600   280    800ms        2.50%       95%   3.5GB  ← Degrading
25-30m  3200   320    2000ms       15.0%       100%  4.0GB  ← Breaking point!

Breaking point: ~1600 concurrent users
Recommendation: Set max capacity at 1200 users (75% of breaking point)
```

---

## Endurance Testing

### Purpose
Detect memory leaks, resource leaks, and performance degradation over time.

### Methodology

```python
# endurance_test.py
from locust import HttpUser, task, between, constant

class EnduranceTestUser(HttpUser):
    wait_time = constant(2)  # Constant 2-second delay (predictable load)

    @task
    def steady_load(self):
        self.client.get("/api/v1/servers")
        self.client.post("/api/v1/policy/evaluate", json={
            "user_id": "test",
            "action": "tool:invoke",
            "tool": "test"
        })
```

**Run for 24-72 hours:**
```bash
locust -f endurance_test.py \
  --headless \
  --users 500 \
  --spawn-rate 50 \
  --run-time 72h \
  --host https://sark.example.com
```

### Monitor for Memory Leaks

**Check Memory Growth:**
```bash
# Monitor pod memory every 5 minutes for 24 hours
while true; do
  kubectl top pods -n production | grep sark >> memory-usage.log
  date >> memory-usage.log
  sleep 300
done
```

**Analyze Memory Growth:**
```bash
# Plot memory usage over time
cat memory-usage.log | grep sark | awk '{print $3}' | sed 's/Mi//' > memory.dat

# If using gnuplot
gnuplot << EOF
set terminal png
set output 'memory-growth.png'
set title 'Memory Usage Over 24 Hours'
set xlabel 'Time (5-min intervals)'
set ylabel 'Memory (Mi)'
plot 'memory.dat' with lines
EOF
```

**Expected Result:**
- ✅ Memory usage should stabilize (e.g., 1.5GB ± 100MB)
- ❌ Continuous growth indicates memory leak

**If Memory Leak Detected:**
```python
# Use memory_profiler to find leak
from memory_profiler import profile

@profile
def suspected_function():
    # Function suspected of leaking memory
    pass

# Run with: python -m memory_profiler script.py
```

---

## Spike Testing

### Purpose
Validate system behavior under sudden traffic spikes.

### Methodology

```python
# spike_test.py
from locust import LoadTestShape

class SpikeTestShape(LoadTestShape):
    """
    Simulate sudden traffic spike
    """
    def tick(self):
        run_time = self.get_run_time()

        if run_time < 300:  # 0-5 min: Normal load (200 users)
            return (200, 20)
        elif run_time < 600:  # 5-10 min: SPIKE! (1000 users)
            if run_time == 300:
                # Immediate spike
                return (1000, 800)  # High spawn rate for sudden spike
            return (1000, 0)
        elif run_time < 900:  # 10-15 min: Back to normal (200 users)
            return (200, 50)
        else:
            return None
```

**Run Spike Test:**
```bash
locust -f spike_test.py --headless --host https://sark.example.com
```

### Validate Auto-Scaling

**Kubernetes HPA (Horizontal Pod Autoscaler):**
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sark-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
      - type: Pods
        value: 4
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 300
```

**Monitor Scaling During Spike:**
```bash
# Watch pod count
watch -n 5 'kubectl get pods -n production | grep sark'

# Watch HPA
watch -n 5 'kubectl get hpa -n production'
```

**Expected Behavior:**
- Pods should scale up within 1-2 minutes of spike
- Error rate should remain <1% during scaling
- Latency should recover to normal within 5 minutes

---

## Scalability Testing

### Horizontal Scaling

**Test increasing pod count:**
```bash
# Test with 1, 3, 5, 10, 20 pods
for replicas in 1 3 5 10 20; do
  echo "Testing with $replicas replicas"
  kubectl scale deployment sark --replicas=$replicas -n production
  sleep 120  # Wait for pods to be ready

  # Run load test
  locust -f loadtest.py --headless --users 500 --run-time 10m --host https://sark.example.com --csv=results/scale-${replicas}

  sleep 60  # Cool down
done

# Analyze results
# Plot RPS vs replicas, latency vs replicas
```

**Expected Results:**
```
Replicas  RPS    p95 Latency  CPU/Pod  Memory/Pod
──────────────────────────────────────────────────
1         50     250ms        95%      2.5GB
3         150    120ms        70%      1.8GB
5         250    95ms         55%      1.5GB
10        480    80ms         45%      1.3GB
20        950    75ms         42%      1.2GB

Optimal: 10 replicas (good RPS, low latency, reasonable resource usage)
```

### Vertical Scaling

**Test with different resource limits:**
```yaml
# small-resources.yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

# medium-resources.yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

# large-resources.yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

**Test Each Configuration:**
```bash
for size in small medium large; do
  kubectl apply -f ${size}-resources.yaml
  kubectl rollout status deployment/sark -n production

  # Run load test
  locust -f loadtest.py --headless --users 500 --run-time 10m --csv=results/vertical-${size}
done
```

---

## Benchmarking

### API Endpoint Benchmarks

**Use `wrk` for quick benchmarks:**
```bash
# Install wrk
git clone https://github.com/wg/wrk.git
cd wrk && make

# Benchmark GET /api/v1/servers
./wrk -t12 -c400 -d30s \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/servers

# Output:
# Running 30s test @ http://localhost:8000/api/v1/servers
#   12 threads and 400 connections
#   Thread Stats   Avg      Stdev     Max   +/- Stdev
#     Latency    75.23ms   15.42ms   250.11ms   82.45%
#     Req/Sec    440.12     85.23     650.00     71.25%
#   158432 requests in 30.01s, 125.23MB read
# Requests/sec:   5279.44
# Transfer/sec:      4.17MB
```

**Benchmark Policy Evaluation:**
```bash
# Create POST request script
cat > policy-eval.lua << 'EOF'
wrk.method = "POST"
wrk.body   = '{"user_id":"test","action":"tool:invoke","tool":"test"}'
wrk.headers["Content-Type"] = "application/json"
wrk.headers["Authorization"] = "Bearer YOUR_TOKEN"
EOF

# Run benchmark
./wrk -t12 -c400 -d30s -s policy-eval.lua \
  http://localhost:8000/api/v1/policy/evaluate
```

### Component Benchmarks

**PostgreSQL Benchmark:**
```bash
# Using pgbench
pgbench -i -s 100 sark  # Initialize with scale factor 100
pgbench -c 10 -j 2 -t 1000 sark  # 10 clients, 2 threads, 1000 transactions each

# Custom benchmark
pgbench -c 10 -j 2 -T 60 -f custom-query.sql sark
```

**Redis Benchmark:**
```bash
# Using redis-benchmark
redis-benchmark -h localhost -p 6379 -a password -q -n 100000

# Specific operations
redis-benchmark -h localhost -p 6379 -a password -t set,get -n 100000 -q

# Pipeline mode
redis-benchmark -h localhost -p 6379 -a password -n 1000000 -t set,get -P 16 -q
```

---

## Performance Profiling

### Python Profiling

**cProfile:**
```python
# profile_endpoint.py
import cProfile
import pstats
from io import StringIO

def profile_function():
    # Your code here
    pass

pr = cProfile.Profile()
pr.enable()

# Run code
profile_function()

pr.disable()
s = StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats()
print(s.getvalue())
```

**py-spy (sampling profiler):**
```bash
# Install
pip install py-spy

# Profile running process
py-spy top --pid <PID>

# Record flamegraph
py-spy record -o profile.svg --pid <PID> --duration 60

# Profile script
py-spy record -o profile.svg -- python your_script.py
```

**memory_profiler:**
```python
from memory_profiler import profile

@profile
def my_function():
    large_list = [i for i in range(1000000)]
    return large_list

# Run with: python -m memory_profiler script.py
```

### Database Query Profiling

**Enable slow query log:**
```sql
-- PostgreSQL
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries >1s
SELECT pg_reload_conf();

-- View slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**EXPLAIN ANALYZE:**
```sql
EXPLAIN ANALYZE
SELECT * FROM servers WHERE status = 'active' AND sensitivity_level = 'high';

-- Output shows:
-- - Execution plan
-- - Actual time taken
-- - Rows scanned vs returned
-- - Index usage
```

---

## Database Performance Testing

### Connection Pool Testing

```python
# test_db_pool.py
import asyncio
import asyncpg
from concurrent.futures import ThreadPoolExecutor

async def test_connection_pool():
    pool = await asyncpg.create_pool(
        dsn='postgresql://user:pass@localhost/sark',
        min_size=10,
        max_size=100,
        max_inactive_connection_lifetime=300
    )

    async def query():
        async with pool.acquire() as conn:
            result = await conn.fetch('SELECT COUNT(*) FROM servers')
            return result

    # Simulate 1000 concurrent queries
    tasks = [query() for _ in range(1000)]
    start = asyncio.get_event_loop().time()
    results = await asyncio.gather(*tasks)
    end = asyncio.get_event_loop().time()

    print(f"1000 queries completed in {end - start:.2f}s")
    print(f"QPS: {1000 / (end - start):.2f}")

    await pool.close()

asyncio.run(test_connection_pool())
```

### Query Performance

**Test with increasing data volumes:**
```sql
-- Insert test data
INSERT INTO servers (name, transport, endpoint, sensitivity_level, status)
SELECT
    'server-' || generate_series || '-' || md5(random()::text),
    'http',
    'http://server-' || generate_series || '.example.com',
    (ARRAY['low', 'medium', 'high', 'critical'])[floor(random() * 4 + 1)],
    (ARRAY['active', 'inactive', 'unhealthy'])[floor(random() * 3 + 1)]
FROM generate_series(1, 100000);

-- Benchmark query performance
\timing
SELECT * FROM servers WHERE status = 'active' LIMIT 100;
SELECT * FROM servers WHERE sensitivity_level = 'high' AND status = 'active';
```

---

## Cache Performance Testing

### Redis Performance

**Test cache hit rate:**
```python
# test_cache_performance.py
import redis
import random
import time

r = redis.Redis(host='localhost', port=6379, password='password', decode_responses=True)

# Populate cache
keys = [f"policy:decision:{i}" for i in range(10000)]
for key in keys:
    r.setex(key, 300, f"cached_value_{key}")

# Test hit rate
hits = 0
misses = 0
start = time.time()

for _ in range(100000):
    # 80% hit rate (access keys that exist)
    if random.random() < 0.8:
        key = random.choice(keys)
    else:
        key = f"policy:decision:missing_{random.randint(100000, 200000)}"

    result = r.get(key)
    if result:
        hits += 1
    else:
        misses += 1

end = time.time()

print(f"Hits: {hits}, Misses: {misses}")
print(f"Hit rate: {hits / (hits + misses) * 100:.2f}%")
print(f"Total time: {end - start:.2f}s")
print(f"Operations/sec: {100000 / (end - start):.2f}")
```

---

## API Performance Testing

### Detailed API Testing

**Test each endpoint:**
```bash
# Authentication endpoints
ab -n 1000 -c 10 -p login.json -T application/json \
  http://localhost:8000/api/v1/auth/login/ldap

# Server endpoints
ab -n 10000 -c 100 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/servers

# Policy evaluation
ab -n 5000 -c 50 -p policy.json -T application/json \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/policy/evaluate
```

---

## Policy Evaluation Performance

### OPA Performance Testing

```python
# test_opa_performance.py
import requests
import time
import statistics

OPA_URL = "http://localhost:8181/v1/data/mcp/allow"

def evaluate_policy():
    response = requests.post(OPA_URL, json={
        "input": {
            "user": {"id": "test", "role": "developer"},
            "action": "tool:invoke",
            "tool": {"name": "test", "sensitivity_level": "medium"}
        }
    })
    return response.elapsed.total_seconds() * 1000  # Convert to ms

# Run 1000 evaluations
latencies = [evaluate_policy() for _ in range(1000)]

print(f"Min latency: {min(latencies):.2f}ms")
print(f"Max latency: {max(latencies):.2f}ms")
print(f"Mean latency: {statistics.mean(latencies):.2f}ms")
print(f"Median latency: {statistics.median(latencies):.2f}ms")
print(f"p95 latency: {statistics.quantiles(latencies, n=20)[18]:.2f}ms")
print(f"p99 latency: {statistics.quantiles(latencies, n=100)[98]:.2f}ms")

# Target: p95 < 50ms, p99 < 100ms
```

---

## SIEM Integration Performance

### SIEM Throughput Testing

```python
# test_siem_throughput.py
import asyncio
import time
from sark.services.siem import SIEMForwarder

async def test_siem_throughput():
    forwarder = SIEMForwarder()

    # Generate 100,000 events
    events = [
        {
            "event_type": "policy_decision",
            "decision": "allow",
            "user_id": f"user-{i}",
            "timestamp": time.time()
        }
        for i in range(100000)
    ]

    start = time.time()

    # Forward events (batched internally)
    await forwarder.forward_batch(events)

    end = time.time()
    duration = end - start

    print(f"Forwarded 100,000 events in {duration:.2f}s")
    print(f"Throughput: {100000 / duration:.2f} events/sec")
    print(f"Throughput: {(100000 / duration) * 60:.2f} events/min")

    # Target: > 10,000 events/min

asyncio.run(test_siem_throughput())
```

---

## Monitoring & Metrics

### Key Metrics to Track

**During Performance Tests:**
1. **Request Rate** (RPS)
2. **Response Time** (p50, p95, p99)
3. **Error Rate** (%)
4. **CPU Usage** (%)
5. **Memory Usage** (MB/GB)
6. **Network I/O** (MB/s)
7. **Database Connections**
8. **Cache Hit Rate** (%)
9. **Disk I/O** (MB/s)
10. **Queue Depth**

**Prometheus Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Cache hit rate
rate(policy_cache_hits_total[5m]) / (rate(policy_cache_hits_total[5m]) + rate(policy_cache_misses_total[5m]))
```

---

## Performance Test Automation

### CI/CD Integration

**GitHub Actions Workflow:**
```yaml
# .github/workflows/performance-test.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM
  workflow_dispatch:  # Manual trigger

jobs:
  performance-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install locust

      - name: Start SARK (Docker Compose)
        run: |
          docker-compose up -d
          sleep 30  # Wait for services

      - name: Run Load Test
        run: |
          locust -f tests/performance/loadtest.py \
            --headless \
            --users 500 \
            --spawn-rate 50 \
            --run-time 10m \
            --host http://localhost:8000 \
            --csv=results/perf-test \
            --html=results/perf-test.html

      - name: Check SLA
        run: |
          python tests/performance/check_sla.py results/perf-test_stats.csv

      - name: Upload Results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: performance-test-results
          path: results/

      - name: Comment PR with Results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = fs.readFileSync('results/perf-test_stats.csv', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Performance Test Results\n\`\`\`\n${results}\n\`\`\``
            });
```

**SLA Check Script:**
```python
# check_sla.py
import sys
import csv

def check_sla(stats_file):
    with open(stats_file, 'r') as f:
        reader = csv.DictReader(f)
        failed = False

        for row in reader:
            name = row['Name']
            p95 = float(row['95%'])
            error_rate = float(row['Failure Count']) / float(row['Request Count']) * 100

            # Check p95 latency SLA
            if p95 > 200:  # 200ms SLA
                print(f"❌ FAIL: {name} p95 latency {p95}ms exceeds 200ms SLA")
                failed = True
            else:
                print(f"✅ PASS: {name} p95 latency {p95}ms within SLA")

            # Check error rate SLA
            if error_rate > 0.1:  # 0.1% error rate SLA
                print(f"❌ FAIL: {name} error rate {error_rate:.2f}% exceeds 0.1% SLA")
                failed = True
            else:
                print(f"✅ PASS: {name} error rate {error_rate:.2f}% within SLA")

        if failed:
            sys.exit(1)
        else:
            print("\n✅ All SLAs met!")
            sys.exit(0)

if __name__ == '__main__':
    check_sla(sys.argv[1])
```

---

## Reporting & Analysis

### Performance Test Report Template

```markdown
# Performance Test Report

**Date:** 2025-11-22
**Environment:** Staging
**Version:** 0.1.0
**Test Duration:** 60 minutes
**Test Type:** Load Test

## Executive Summary

- **Overall Result:** ✅ PASS
- **Peak Load:** 1,000 concurrent users
- **Peak RPS:** 250 requests/second
- **p95 Latency:** 120ms (Target: <200ms)
- **Error Rate:** 0.04% (Target: <0.1%)
- **Availability:** 99.96%

## Test Configuration

- **Tool:** Locust
- **Concurrent Users:** 1,000
- **Ramp-up Time:** 10 minutes
- **Test Duration:** 60 minutes
- **Target System:** https://staging.sark.example.com

## Results Summary

| Endpoint | Requests | p50 | p95 | p99 | Error Rate | SLA Met |
|----------|----------|-----|-----|-----|------------|---------|
| GET /api/v1/servers | 45,000 | 65ms | 120ms | 180ms | 0.03% | ✅ |
| GET /api/v1/servers/{id} | 18,000 | 50ms | 95ms | 140ms | 0.02% | ✅ |
| POST /api/v1/policy/evaluate | 18,000 | 35ms | 70ms | 110ms | 0.04% | ✅ |
| POST /api/v1/servers | 9,000 | 250ms | 450ms | 650ms | 0.16% | ❌ |

## Infrastructure Metrics

| Metric | Average | Peak | Notes |
|--------|---------|------|-------|
| CPU Usage | 65% | 85% | Healthy |
| Memory Usage | 2.1GB | 2.8GB | Stable |
| Database Connections | 35 | 62 | Within pool limits (100) |
| Redis Memory | 1.2GB | 1.5GB | Stable |
| Network I/O | 15MB/s | 28MB/s | Acceptable |

## Issues Identified

### 1. POST /api/v1/servers - High Latency

**Severity:** Medium
**Impact:** Server registration endpoint exceeds SLA (p95: 450ms vs 200ms target)

**Root Cause:**
- Database transaction time for server insertion is high
- Policy evaluation during registration adds latency
- No caching for duplicate server checks

**Recommendation:**
- Add database index on `servers(name, endpoint)` for duplicate checks
- Implement async policy evaluation for registration
- Add Redis caching for recent server lookups

### 2. Error Rate on POST /api/v1/servers

**Severity:** Low
**Impact:** 0.16% error rate slightly exceeds 0.1% SLA

**Root Cause:**
- Duplicate server name conflicts (422 errors)
- Transient database connection timeouts during peak load

**Recommendation:**
- Implement retry logic with exponential backoff
- Increase database connection pool size
- Add better error handling for duplicate entries

## Recommendations

1. **Scale API Pods:** Increase from 5 to 7 replicas for peak traffic
2. **Optimize Database Queries:** Add missing indexes identified in slow query log
3. **Increase Connection Pool:** Increase from 20 to 30 connections
4. **Implement Caching:** Cache server lookups for 5 minutes
5. **Monitor Memory:** Set up alerts for memory usage >80%

## Conclusion

The system meets most SLAs under load but has room for improvement in server registration latency. Recommended optimizations should be implemented before production deployment.

**Sign-off:** Performance Engineering Team
**Next Test:** 2025-11-29 (post-optimization)
```

---

## Appendix: Quick Reference

### Quick Commands

```bash
# Locust load test
locust -f loadtest.py --headless --users 1000 --run-time 30m --host https://sark.example.com

# k6 load test
k6 run --vus 1000 --duration 30m loadtest.js

# wrk benchmark
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/servers

# PostgreSQL benchmark
pgbench -c 10 -j 2 -t 1000 sark

# Redis benchmark
redis-benchmark -h localhost -p 6379 -a password -q

# Python profiling
py-spy record -o profile.svg --pid <PID> --duration 60

# Monitor during test
watch -n 5 'kubectl top pods -n production'
```

### Performance Targets Quick Reference

| Component | Metric | Target |
|-----------|--------|--------|
| API (standard) | p95 latency | <200ms |
| API (auth/policy) | p95 latency | <100ms |
| Policy (cache hit) | p95 latency | <5ms |
| Policy (cache miss) | p95 latency | <50ms |
| Database queries | p95 latency | <20ms |
| Redis ops | p95 latency | <2ms |
| SIEM throughput | events/min | >10,000 |
| Error rate | percentage | <0.1% |
| Availability | uptime | 99.9% |

---

**For questions or support, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or contact the Performance Engineering team.**
