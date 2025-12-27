# SARK Gateway Integration - Performance Tuning Guide

**Version**: 1.1.0
**Last Updated**: November 2025
**Audience**: DevOps Engineers, SREs, Performance Engineers

---

## Table of Contents

1. [Performance Overview](#performance-overview)
2. [Bottleneck Identification](#bottleneck-identification)
3. [Configuration Tuning](#configuration-tuning)
4. [Caching Strategies](#caching-strategies)
5. [Database Optimization](#database-optimization)
6. [OPA Performance](#opa-performance)
7. [Resource Sizing](#resource-sizing)
8. [Network Optimization](#network-optimization)
9. [Load Testing](#load-testing)
10. [Benchmark Results](#benchmark-results)

---

## Performance Overview

### Performance Targets

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| **Authorization Latency (P95)** | <50ms | <100ms | >100ms |
| **Authorization Latency (P99)** | <100ms | <200ms | >200ms |
| **Throughput (per instance)** | >500 RPS | >200 RPS | <200 RPS |
| **Cache Hit Rate** | >90% | >75% | <75% |
| **CPU Utilization** | 50-70% | 70-85% | >85% |
| **Memory Utilization** | <2GB | <4GB | >4GB |
| **Error Rate** | <0.1% | <1% | >1% |

### Key Performance Indicators (KPIs)

**Latency Breakdown:**
```
Total Authorization Time (50ms P95)
├── Network (5ms)        - 10%
├── Auth validation (8ms) - 16%
├── Redis lookup (3ms)    - 6%
├── OPA evaluation (15ms) - 30%
├── DB audit log (12ms)   - 24%
└── Overhead (7ms)        - 14%
```

**Optimization Priority:**
1. **OPA evaluation** (30% of latency) - Highest impact
2. **DB audit log** (24% of latency) - Use async writes
3. **Auth validation** (16% of latency) - Cache JWT validation
4. **Network** (10% of latency) - Use connection pooling
5. **Redis lookup** (6% of latency) - Already optimized

---

## Bottleneck Identification

### Performance Profiling

#### 1. Use Health Endpoint for Component Latency

```bash
# Check component-level latency
curl http://localhost:8000/health/detailed | jq '.dependencies'
```

**Sample output:**
```json
{
  "dependencies": {
    "postgresql": {"healthy": true, "latency_ms": 12.5},
    "redis": {"healthy": true, "latency_ms": 3.2},
    "opa": {"healthy": true, "latency_ms": 8.7},
    "gateway": {"healthy": true, "latency_ms": 145.3}
  }
}
```

**Analysis:**
- PostgreSQL: 12.5ms ✓ (target: <20ms)
- Redis: 3.2ms ✓ (target: <5ms)
- OPA: 8.7ms ✓ (target: <50ms)
- Gateway: **145.3ms** ⚠️ (target: <100ms) - **BOTTLENECK**

---

#### 2. Profile Individual Requests

```bash
# Add timing headers to requests
curl -w "@curl-format.txt" \
  -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "test-server",
    "tool_name": "test-tool"
  }'
```

**curl-format.txt:**
```
    time_namelookup:  %{time_namelookup}s
       time_connect:  %{time_connect}s
    time_appconnect:  %{time_appconnect}s
   time_pretransfer:  %{time_pretransfer}s
      time_redirect:  %{time_redirect}s
 time_starttransfer:  %{time_starttransfer}s
                    ----------
         time_total:  %{time_total}s
```

---

#### 3. Application-Level Profiling

**Enable detailed logging:**
```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG
export ENABLE_PROFILING=true

# Restart SARK
docker compose restart sark
```

**View profiling data:**
```bash
# Check logs for timing information
docker logs sark --tail=100 | jq 'select(.profiling)'

# Sample output:
{
  "timestamp": "2025-11-28T10:00:00Z",
  "profiling": {
    "total_ms": 45.3,
    "breakdown": {
      "auth_validation": 8.2,
      "cache_lookup": 3.1,
      "opa_evaluation": 15.4,
      "db_audit": 12.3,
      "overhead": 6.3
    }
  }
}
```

---

#### 4. Database Query Analysis

```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries >100ms
SELECT pg_reload_conf();

-- View slow queries
SELECT
  calls,
  mean_exec_time,
  max_exec_time,
  query
FROM pg_stat_statements
WHERE mean_exec_time > 50
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

#### 5. OPA Policy Profiling

```bash
# Profile OPA policy evaluation
opa eval --profile \
  --data opa/policies/ \
  --input request.json \
  'data.mcp.gateway.allow' \
  | jq '.profile'
```

**Sample output:**
```json
{
  "profile": [
    {
      "location": {"file": "gateway.rego", "row": 15},
      "num_eval": 1,
      "num_redo": 0,
      "time_ns": 15234000  // 15.2ms
    }
  ]
}
```

---

### Common Bottlenecks

| Symptom | Likely Bottleneck | Investigation |
|---------|-------------------|---------------|
| P95 latency >200ms | OPA policy too complex | Profile with `opa eval --profile` |
| P95 latency 100-200ms | Database slow queries | Check `pg_stat_statements` |
| Cache hit rate <70% | Cache TTL too short | Increase cache TTL |
| CPU >90% | Too many concurrent requests | Scale horizontally |
| Memory growth over time | Memory leak | Check container memory metrics |
| High error rate | Dependency failures | Check health endpoint |

---

## Configuration Tuning

### 1. Connection Pool Tuning

**PostgreSQL Connection Pool:**
```bash
# Default settings
DATABASE_POOL_SIZE=20              # Connection pool size
DATABASE_MAX_OVERFLOW=10           # Additional connections during spikes
DATABASE_POOL_TIMEOUT=30           # Seconds to wait for connection
DATABASE_POOL_RECYCLE=3600         # Recycle connections after 1 hour

# High-traffic settings
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=10
DATABASE_POOL_RECYCLE=1800
```

**Calculation:**
```
Pool Size = (Expected concurrent requests) / (Request duration in seconds)

Example:
- 1000 RPS expected
- Average request duration: 50ms = 0.05s
- Concurrent requests: 1000 * 0.05 = 50
- Pool size: 50 connections
```

---

**Redis Connection Pool:**
```bash
# Default settings
VALKEY_POOL_SIZE=50                 # Max connections
VALKEY_MAX_CONNECTIONS=100          # Hard limit
VALKEY_SOCKET_TIMEOUT=5             # Socket timeout (seconds)
VALKEY_SOCKET_CONNECT_TIMEOUT=2     # Connection timeout

# High-traffic settings
VALKEY_POOL_SIZE=100
VALKEY_MAX_CONNECTIONS=200
VALKEY_SOCKET_TIMEOUT=3
VALKEY_SOCKET_CONNECT_TIMEOUT=1
```

---

### 2. Timeout Configuration

```bash
# Gateway request timeout
GATEWAY_TIMEOUT_SECONDS=10.0       # Default: 10s
GATEWAY_CONNECT_TIMEOUT=5.0        # Connection timeout: 5s
GATEWAY_READ_TIMEOUT=10.0          # Read timeout: 10s

# OPA evaluation timeout
OPA_TIMEOUT_MS=5000                # 5 seconds

# Database query timeout
DATABASE_STATEMENT_TIMEOUT=5000    # 5 seconds

# Redis operation timeout
REDIS_TIMEOUT=3                    # 3 seconds
```

**Tuning recommendations:**

| Load Level | Gateway Timeout | OPA Timeout | DB Timeout |
|------------|----------------|-------------|------------|
| **Low** (<100 RPS) | 15s | 10s | 10s |
| **Medium** (100-1000 RPS) | 10s | 5s | 5s |
| **High** (>1000 RPS) | 5s | 3s | 3s |

**Why lower timeouts at high load?**
- Fail fast to prevent cascading failures
- Free up resources quickly
- Better user experience (fast failure vs slow timeout)

---

### 3. Worker Processes and Threads

**Gunicorn (SARK API) Configuration:**
```bash
# Worker calculation
WORKERS=4                          # CPU cores * 2 + 1

# Thread pool for async operations
WORKER_THREADS=10                  # Threads per worker
WORKER_CONNECTIONS=1000            # Max concurrent connections

# Example for 8-core machine:
WORKERS=17                         # (8 * 2) + 1
WORKER_THREADS=10
WORKER_CONNECTIONS=2000
```

**Docker Compose:**
```yaml
services:
  sark:
    environment:
      - WORKERS=17
      - WORKER_THREADS=10
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 8G
```

---

### 4. Async Processing

**Enable async audit logging:**
```bash
# Async audit writes (don't block authorization response)
AUDIT_ASYNC_ENABLED=true
AUDIT_BATCH_SIZE=100               # Batch writes
AUDIT_FLUSH_INTERVAL_SECONDS=5     # Flush every 5 seconds
```

**Impact:**
- **Before (sync):** Authorization latency P95 = 80ms
- **After (async):** Authorization latency P95 = 45ms
- **Improvement:** 44% reduction

---

### 5. Circuit Breaker Configuration

```bash
# Circuit breaker for Gateway calls
GATEWAY_CIRCUIT_BREAKER_ENABLED=true
GATEWAY_CIRCUIT_BREAKER_THRESHOLD=5       # Open after 5 failures
GATEWAY_CIRCUIT_BREAKER_TIMEOUT=30        # Try again after 30s
GATEWAY_CIRCUIT_BREAKER_HALF_OPEN=1       # 1 request in half-open state
```

**State transitions:**
```
CLOSED (normal)
  ├─> OPEN (5 failures) ────> HALF_OPEN (after 30s) ────> CLOSED (1 success)
  └─> OPEN (5 failures) ────> HALF_OPEN (after 30s) ────> OPEN (1 failure)
```

---

## Caching Strategies

### 1. Redis Cache Configuration

**Cache TTL by Sensitivity Level:**
```bash
# Different TTLs for different sensitivity levels
GATEWAY_CACHE_TTL_LOW=300          # 5 minutes
GATEWAY_CACHE_TTL_MEDIUM=180       # 3 minutes
GATEWAY_CACHE_TTL_HIGH=60          # 1 minute
GATEWAY_CACHE_TTL_CRITICAL=30      # 30 seconds

# Why different TTLs?
# - Low sensitivity: Less likely to change, cache longer
# - Critical: Security-sensitive, cache shorter
```

**Impact on cache hit rate:**

| TTL | Cache Hit Rate | Authorization Latency (P95) |
|-----|----------------|----------------------------|
| 30s | 75% | 35ms |
| 60s | 85% | 25ms |
| 180s | 92% | 18ms |
| 300s | 95% | 15ms |

---

### 2. Cache Key Design

**Effective cache key structure:**
```python
# Good: Includes all relevant context
cache_key = f"authz:{user_id}:{action}:{server}:{tool}:{sensitivity}"

# Example:
"authz:user_123:gateway:tool:invoke:postgres-mcp:execute_query:high"

# Bad: Too generic (different users get same result)
cache_key = f"authz:{action}:{tool}"
```

**Cache key compression:**
```python
# Use hash for long keys
import hashlib

def get_cache_key(request):
    key_data = f"{request.user_id}:{request.action}:{request.server}:{request.tool}"
    key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
    return f"authz:{key_hash}"
```

---

### 3. Cache Warming

**Pre-populate cache for common requests:**
```bash
# Cache warming script
curl -X POST http://localhost:8000/api/v1/admin/cache/warm \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "patterns": [
      {"action": "gateway:tool:invoke", "tool": "read_file", "users": ["user_123", "user_456"]},
      {"action": "gateway:server:list", "users": ["*"]}
    ]
  }'
```

**Schedule warming:**
```bash
# Cron job to warm cache every morning
0 6 * * * curl -X POST http://localhost:8000/api/v1/admin/cache/warm
```

---

### 4. Cache Invalidation Strategy

**Invalidate on policy changes:**
```bash
# After deploying new OPA policies
curl -X POST http://localhost:8000/api/v1/cache/invalidate \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"pattern": "authz:*"}'
```

**Selective invalidation:**
```bash
# Invalidate only for specific user
curl -X POST http://localhost:8000/api/v1/cache/invalidate \
  -d '{"pattern": "authz:user_123:*"}'

# Invalidate only for specific tool
curl -X POST http://localhost:8000/api/v1/cache/invalidate \
  -d '{"pattern": "authz:*:execute_query:*"}'
```

---

### 5. Multi-Layer Caching

**Architecture:**
```
Request
  ├─> L1: In-memory cache (100ms TTL) ─── Ultra-fast, small capacity
  ├─> L2: Redis cache (60-300s TTL) ───── Fast, large capacity
  └─> L3: OPA + DB (authoritative) ────── Slow, always correct
```

**Configuration:**
```bash
# Enable multi-layer caching
CACHE_L1_ENABLED=true
CACHE_L1_SIZE=10000               # 10K entries in memory
CACHE_L1_TTL=100                  # 100ms TTL

CACHE_L2_ENABLED=true
CACHE_L2_TTL=180                  # 3 minutes in Redis
```

**Performance improvement:**
- L1 hit: <1ms (99.9% of repeated requests)
- L2 hit: ~3ms (90% of requests)
- L3 (OPA): ~15ms (10% of requests)

---

## Database Optimization

### 1. Index Optimization

**Critical indexes for Gateway audit queries:**
```sql
-- Index on user_id for user-specific queries
CREATE INDEX CONCURRENTLY idx_audit_user_id
ON audit_events(user_id);

-- Composite index for time-based queries
CREATE INDEX CONCURRENTLY idx_audit_timestamp_user
ON audit_events(timestamp DESC, user_id);

-- Index for event type filtering
CREATE INDEX CONCURRENTLY idx_audit_event_type
ON audit_events(event_type);

-- GIN index for JSONB metadata queries
CREATE INDEX CONCURRENTLY idx_audit_metadata
ON audit_events USING GIN(metadata);
```

**Verify index usage:**
```sql
EXPLAIN ANALYZE
SELECT * FROM audit_events
WHERE user_id = 'user_123'
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC
LIMIT 100;

-- Look for "Index Scan" not "Seq Scan"
```

---

### 2. Partitioning for Large Tables

**Partition audit_events by month:**
```sql
-- Convert to partitioned table
CREATE TABLE audit_events_partitioned (
    LIKE audit_events INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE audit_events_2025_11
PARTITION OF audit_events_partitioned
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE audit_events_2025_12
PARTITION OF audit_events_partitioned
FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

**Automatic partition management:**
```sql
-- Create function to auto-create partitions
CREATE OR REPLACE FUNCTION create_audit_partition()
RETURNS void AS $$
DECLARE
  partition_date DATE;
  partition_name TEXT;
BEGIN
  partition_date := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
  partition_name := 'audit_events_' || TO_CHAR(partition_date, 'YYYY_MM');

  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_events_partitioned
     FOR VALUES FROM (%L) TO (%L)',
    partition_name,
    partition_date,
    partition_date + INTERVAL '1 month'
  );
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly
SELECT create_audit_partition();
```

---

### 3. Connection Pooling with PgBouncer

**Why use PgBouncer:**
- Reduces connection overhead
- Enables connection reuse
- Protects database from connection storms

**Configuration:**
```ini
# pgbouncer.ini
[databases]
sark = host=postgres port=5432 dbname=sark

[pgbouncer]
pool_mode = transaction           # Connection reuse per transaction
max_client_conn = 1000             # Max client connections
default_pool_size = 25             # Pool size per database
reserve_pool_size = 5              # Reserve connections
```

**Docker Compose:**
```yaml
services:
  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      - DATABASES_HOST=postgres
      - DATABASES_PORT=5432
      - DATABASES_DBNAME=sark
      - PGBOUNCER_POOL_MODE=transaction
      - PGBOUNCER_MAX_CLIENT_CONN=1000
      - PGBOUNCER_DEFAULT_POOL_SIZE=25

  sark:
    environment:
      - DATABASE_URL=postgresql://sark:pass@pgbouncer:6432/sark
```

**Performance impact:**
- **Before:** 1000 connections to PostgreSQL (high overhead)
- **After:** 25 connections to PostgreSQL (low overhead)
- **Result:** 40% reduction in database CPU usage

---

### 4. Read Replicas for Query Offloading

**Separate read and write connections:**
```bash
# Write to primary
DATABASE_WRITE_URL=postgresql://sark:pass@postgres-primary:5432/sark

# Read from replica
DATABASE_READ_URL=postgresql://sark:pass@postgres-replica:5432/sark
```

**Application configuration:**
```python
# Use write connection for audit writes
audit_engine = create_engine(settings.database_write_url)

# Use read connection for audit queries
query_engine = create_engine(settings.database_read_url)
```

---

### 5. Query Optimization

**Optimize slow audit queries:**
```sql
-- Before (slow - 250ms):
SELECT * FROM audit_events
WHERE metadata->>'server_name' = 'postgres-mcp'
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- After (fast - 15ms):
-- Create functional index
CREATE INDEX idx_audit_server_name
ON audit_events ((metadata->>'server_name'));

-- Or use materialized view for common queries
CREATE MATERIALIZED VIEW audit_events_summary AS
SELECT
  DATE_TRUNC('hour', timestamp) as hour,
  metadata->>'server_name' as server,
  COUNT(*) as event_count,
  COUNT(*) FILTER (WHERE decision = 'allow') as allowed,
  COUNT(*) FILTER (WHERE decision = 'deny') as denied
FROM audit_events
GROUP BY 1, 2;

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY audit_events_summary;
```

---

## OPA Performance

### 1. Policy Optimization

**Avoid expensive operations:**
```rego
# Slow (loops through all users):
allow if {
    some user in data.users
    user.id == input.user.id
    user.role == "admin"
}

# Fast (direct lookup):
allow if {
    user := data.users[input.user.id]
    user.role == "admin"
}
```

---

**Use indexing for large datasets:**
```rego
# Slow (linear search):
allow if {
    some team in input.user.teams
    team in ["team1", "team2", "team3", ..., "team1000"]  # Large array
}

# Fast (use sets):
allowed_teams := {"team1", "team2", "team3", ..., "team1000"}

allow if {
    some team in input.user.teams
    team in allowed_teams
}
```

---

**Cache computed values:**
```rego
# Slow (recomputes for each rule):
allow if {
    is_work_hours(time.now_ns())
    input.user.role == "admin"
}

allow if {
    is_work_hours(time.now_ns())
    input.user.role == "developer"
}

# Fast (compute once):
current_hour := time.clock([time.now_ns(), "UTC"])[0]
is_work_hour := current_hour >= 9 && current_hour < 17

allow if {
    is_work_hour
    input.user.role == "admin"
}

allow if {
    is_work_hour
    input.user.role == "developer"
}
```

---

### 2. OPA Bundle Optimization

**Compress OPA bundles:**
```bash
# Create compressed bundle
opa build \
  --bundle opa/policies/ \
  --output bundle.tar.gz \
  --optimize=2  # Level 2 optimization

# Reduction: 5MB → 800KB (84% smaller)
```

**Use partial evaluation:**
```bash
# Pre-compile policies with known data
opa build \
  --bundle opa/policies/ \
  --partial \
  --data data.json \
  --output optimized-bundle.tar.gz
```

---

### 3. OPA Horizontal Scaling

**Run multiple OPA instances:**
```yaml
# docker-compose.yml
services:
  opa-1:
    image: openpolicyagent/opa:latest
    command: run --server --addr :8181 /policies

  opa-2:
    image: openpolicyagent/opa:latest
    command: run --server --addr :8181 /policies

  opa-3:
    image: openpolicyagent/opa:latest
    command: run --server --addr :8181 /policies

  opa-lb:
    image: nginx:latest
    volumes:
      - ./opa-nginx.conf:/etc/nginx/nginx.conf
```

**NGINX load balancer config:**
```nginx
upstream opa_backend {
    least_conn;
    server opa-1:8181;
    server opa-2:8181;
    server opa-3:8181;
}

server {
    listen 8181;

    location / {
        proxy_pass http://opa_backend;
    }
}
```

---

### 4. OPA Profiling and Monitoring

**Enable OPA metrics:**
```bash
# Start OPA with metrics
docker run -p 8181:8181 openpolicyagent/opa:latest \
  run --server \
  --addr :8181 \
  --diagnostic-addr :8282 \
  /policies

# View metrics
curl http://localhost:8282/metrics
```

**Key OPA metrics:**
```promql
# Policy evaluation time
opa_http_request_duration_seconds{handler="v1/data"}

# Query throughput
rate(opa_http_request_duration_seconds_count[5m])

# Cache hit rate
rate(opa_decision_cache_hits_total[5m]) /
rate(opa_decision_cache_misses_total[5m] + opa_decision_cache_hits_total[5m])
```

---

## Resource Sizing

### 1. CPU Requirements

**Single SARK instance:**

| Load Level | vCPUs | Notes |
|------------|-------|-------|
| **Low** (<100 RPS) | 2 vCPUs | Development/testing |
| **Medium** (100-500 RPS) | 4 vCPUs | Small production |
| **High** (500-2000 RPS) | 8 vCPUs | Production |
| **Very High** (>2000 RPS) | 16+ vCPUs | Large-scale production |

**Kubernetes HPA (Horizontal Pod Autoscaler):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sark-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Scale when CPU >70%
```

---

### 2. Memory Requirements

**SARK memory usage:**

| Component | Base Memory | Per-request | Max Memory |
|-----------|-------------|-------------|------------|
| **Python runtime** | 200 MB | - | 200 MB |
| **Gunicorn workers** | 50 MB × workers | - | 850 MB (17 workers) |
| **Request processing** | - | 5 MB | 500 MB (100 concurrent) |
| **Cache (L1)** | 100 MB | - | 100 MB |
| **Connections** | 10 MB | - | 10 MB |
| **Total** | ~1.3 GB | - | ~2 GB |

**Recommended memory allocation:**
```yaml
resources:
  requests:
    memory: "2Gi"
  limits:
    memory: "4Gi"  # 2x headroom for spikes
```

---

### 3. Storage Requirements

**Audit log growth:**
```
Average audit event size: 2 KB
Events per day (at 1000 RPS): 86,400,000
Daily storage: 172 GB
Monthly storage: 5.2 TB
```

**Storage optimization:**
- Use PostgreSQL partitioning
- Archive old data to cold storage (S3, Glacier)
- Enable compression (reduces by 70-80%)

**Recommended storage:**
```yaml
volumes:
  postgres-data:
    size: 500Gi  # 3 months of data
    type: SSD    # Fast storage for active data

  postgres-archive:
    size: 10Ti   # Long-term archive
    type: HDD    # Cheaper storage for old data
```

---

### 4. Network Bandwidth

**Bandwidth calculation:**
```
Request size: 2 KB
Response size: 1 KB
Total per request: 3 KB

At 1000 RPS:
Bandwidth = 1000 RPS × 3 KB × 8 bits = 24 Mbps

Recommended: 100 Mbps (4x headroom)
```

---

## Network Optimization

### 1. Connection Keep-Alive

**Enable HTTP keep-alive:**
```bash
# SARK configuration
HTTP_KEEPALIVE_ENABLED=true
HTTP_KEEPALIVE_TIMEOUT=65        # 65 seconds
HTTP_KEEPALIVE_MAX_REQUESTS=100  # Max requests per connection
```

**Impact:**
- **Before:** New TCP connection per request (~5ms overhead)
- **After:** Connection reuse (~0.1ms overhead)
- **Improvement:** 50x faster

---

### 2. Response Compression

**Enable gzip compression:**
```bash
# Compress responses >1KB
ENABLE_GZIP=true
GZIP_MIN_LENGTH=1024
GZIP_LEVEL=6  # Compression level (1-9)
```

**Compression ratio:**
- JSON responses: 70-80% reduction
- 10 KB response → 2 KB compressed
- Reduces network transfer time by 5-10ms

---

### 3. Connection Pooling

**HTTP connection pool for Gateway calls:**
```python
# httpx configuration
import httpx

client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=100,
        max_connections=200,
        keepalive_expiry=30.0
    ),
    timeout=httpx.Timeout(10.0)
)
```

---

## Load Testing

### 1. Load Testing Setup

**Install tools:**
```bash
# Install k6 (modern load testing tool)
brew install k6

# Or using Docker
docker pull grafana/k6
```

**Basic load test script:**
```javascript
// k6-gateway-load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 RPS
    { duration: '5m', target: 100 },   // Sustain 100 RPS
    { duration: '2m', target: 500 },   // Ramp up to 500 RPS
    { duration: '5m', target: 500 },   // Sustain 500 RPS
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<100'],  // 95% of requests <100ms
    http_req_failed: ['rate<0.01'],    // Error rate <1%
  },
};

const BASE_URL = 'http://localhost:8000';
const TOKEN = 'YOUR_AUTH_TOKEN';

export default function () {
  const payload = JSON.stringify({
    action: 'gateway:tool:invoke',
    server_name: 'test-server',
    tool_name: 'test-tool',
    parameters: {}
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN}`,
    },
  };

  const res = http.post(`${BASE_URL}/api/v1/gateway/authorize`, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'latency < 100ms': (r) => r.timings.duration < 100,
  });

  sleep(1);
}
```

**Run load test:**
```bash
k6 run k6-gateway-load-test.js

# Output:
#   ✓ status is 200
#   ✓ latency < 100ms
#
#   http_req_duration..........: avg=45ms min=12ms med=42ms max=180ms p(90)=65ms p(95)=82ms
#   http_reqs..................: 50000
```

---

### 2. Stress Testing

**Find breaking point:**
```javascript
export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 500 },
    { duration: '5m', target: 1000 },
    { duration: '5m', target: 2000 },  // Stress level
    { duration: '5m', target: 5000 },  // Beyond capacity
  ],
};
```

**Monitor during stress test:**
```bash
# Watch system metrics
docker stats

# Watch application metrics
watch -n 1 'curl -s http://localhost:8000/health/detailed | jq'
```

---

### 3. Soak Testing (Endurance)

**Test for memory leaks:**
```javascript
export let options = {
  stages: [
    { duration: '10m', target: 200 },  // Ramp up
    { duration: '4h', target: 200 },   // Soak for 4 hours
    { duration: '10m', target: 0 },    // Ramp down
  ],
};
```

**Monitor memory growth:**
```bash
# Check for memory leaks
docker stats sark --format "table {{.MemUsage}}" --no-stream

# Every 5 minutes for 4 hours
while true; do
  docker stats sark --no-stream --format "{{.MemUsage}}" >> memory-log.txt
  sleep 300
done
```

---

## Benchmark Results

### Baseline Performance (Single Instance)

**Test environment:**
- Instance: 4 vCPUs, 8 GB RAM
- Database: PostgreSQL 15 (2 vCPUs, 4 GB RAM)
- Cache: Redis 7 (1 vCPU, 2 GB RAM)
- OPA: 1 vCPU, 1 GB RAM

**Results:**

| Metric | Value |
|--------|-------|
| **Throughput** | 550 RPS |
| **Latency (P50)** | 28 ms |
| **Latency (P95)** | 48 ms |
| **Latency (P99)** | 89 ms |
| **Cache Hit Rate** | 88% |
| **Error Rate** | 0.02% |
| **CPU Usage** | 65% |
| **Memory Usage** | 1.8 GB |

---

### Optimized Performance (Single Instance)

**Optimizations applied:**
- Async audit logging
- Connection pooling (PgBouncer)
- Redis cache TTL tuning
- OPA policy optimization
- HTTP keep-alive

**Results:**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Throughput** | 550 RPS | **850 RPS** | +55% |
| **Latency (P50)** | 28 ms | **18 ms** | -36% |
| **Latency (P95)** | 48 ms | **32 ms** | -33% |
| **Latency (P99)** | 89 ms | **58 ms** | -35% |
| **Cache Hit Rate** | 88% | **94%** | +7% |
| **CPU Usage** | 65% | **58%** | -11% |

---

### Scaled Performance (3 Instances)

**Test environment:**
- 3× SARK instances (4 vCPUs, 8 GB RAM each)
- NGINX load balancer
- Shared PostgreSQL and Redis

**Results:**

| Metric | Value |
|--------|-------|
| **Throughput** | **2,400 RPS** (800 RPS per instance) |
| **Latency (P50)** | 19 ms |
| **Latency (P95)** | 35 ms |
| **Latency (P99)** | 62 ms |
| **Cache Hit Rate** | 93% |
| **Error Rate** | 0.03% |

---

### Kubernetes Auto-Scaling

**Test scenario:**
- Start: 3 pods
- Load: Gradual increase to 5,000 RPS
- HPA target: 70% CPU utilization

**Results:**

| Time | Load (RPS) | Pods | Avg CPU | P95 Latency |
|------|-----------|------|---------|-------------|
| 0m | 500 | 3 | 35% | 28 ms |
| 5m | 1,500 | 3 | 72% | 38 ms |
| 6m | 1,500 | 5 | 48% | 32 ms |
| 10m | 3,000 | 5 | 74% | 42 ms |
| 11m | 3,000 | 8 | 51% | 35 ms |
| 15m | 5,000 | 8 | 82% | 48 ms |
| 16m | 5,000 | 12 | 58% | 38 ms |

**Key findings:**
- HPA responds within 1-2 minutes
- Maintains P95 latency <50ms
- Scales efficiently to 12 pods for 5,000 RPS

---

## Performance Monitoring Dashboard

### Grafana Dashboard Panels

**1. Authorization Latency:**
```promql
histogram_quantile(0.95,
  rate(sark_gateway_authz_latency_seconds_bucket[5m])
)
```

**2. Throughput:**
```promql
rate(sark_gateway_authz_requests_total[5m])
```

**3. Cache Hit Rate:**
```promql
rate(sark_gateway_cache_hits_total[5m]) /
(rate(sark_gateway_cache_hits_total[5m]) +
 rate(sark_gateway_cache_misses_total[5m]))
```

**4. Error Rate:**
```promql
rate(sark_gateway_errors_total[5m]) /
rate(sark_gateway_authz_requests_total[5m])
```

---

## Tuning Checklist

**Before Production Deployment:**

- [ ] Enable async audit logging
- [ ] Configure connection pooling (PgBouncer)
- [ ] Tune Redis cache TTLs (60-300s)
- [ ] Optimize OPA policies (profile with `--profile`)
- [ ] Enable HTTP keep-alive
- [ ] Set up database indexes
- [ ] Configure resource limits (CPU, memory)
- [ ] Enable circuit breakers
- [ ] Set appropriate timeouts
- [ ] Configure horizontal pod autoscaling (HPA)
- [ ] Set up monitoring and alerting
- [ ] Run load tests (target: P95 <100ms at expected load)
- [ ] Perform soak test (4+ hours at 80% capacity)
- [ ] Document baseline performance metrics

---

## Additional Resources

- **[TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)** - Comprehensive troubleshooting
- **[FAQ.md](./FAQ.md)** - Frequently asked questions
- **[ERROR_REFERENCE.md](./ERROR_REFERENCE.md)** - Error code reference
- **[MONITORING.md](../../MONITORING.md)** - Monitoring and observability
- **[PERFORMANCE_REPORT.md](../../PERFORMANCE_REPORT.md)** - Detailed performance analysis

---

**Last Updated**: November 2025 | **Version**: 1.1.0
**Questions or feedback?** performance-team@example.com
