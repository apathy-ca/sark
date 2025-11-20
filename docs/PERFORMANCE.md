# SARK Performance Optimization Guide

**Achieving Enterprise-Scale Performance for MCP Governance**

**Target:** <5ms p99 policy latency, 10,000+ servers, 10,000+ events/sec

---

## Table of Contents

1. [Performance Targets](#performance-targets)
2. [Benchmarking & Monitoring](#benchmarking--monitoring)
3. [Database Optimization](#database-optimization)
4. [Caching Strategy](#caching-strategy)
5. [API Performance](#api-performance)
6. [OPA Policy Optimization](#opa-policy-optimization)
7. [Network & Infrastructure](#network--infrastructure)
8. [Horizontal Scaling](#horizontal-scaling)
9. [Load Testing](#load-testing)
10. [Performance Troubleshooting](#performance-troubleshooting)

---

## Performance Targets

### Phase-by-Phase Targets

| Metric | Phase 1 (100 servers) | Phase 3 (5,000 servers) | Phase 4 (10,000+ servers) |
|--------|----------------------|-------------------------|---------------------------|
| **Policy Latency (p99)** | <50ms | <10ms | <5ms |
| **API Response Time (p95)** | <200ms | <100ms | <50ms |
| **Throughput** | 100 RPS | 5,000 RPS | 10,000+ RPS |
| **Audit Events/sec** | 1,000 | 5,000 | 10,000+ |
| **Database Queries/sec** | 500 | 5,000 | 10,000+ |
| **Cache Hit Rate** | 80% | 95% | 98% |
| **Availability** | 99% | 99.9% | 99.95% |

### SLA Commitments

```yaml
service_level_agreements:
  api_availability:
    target: 99.95%
    measurement: uptime over rolling 30 days

  api_latency:
    p50: 25ms
    p95: 50ms
    p99: 100ms
    measurement: server-side processing time

  policy_evaluation:
    p50: 2ms
    p95: 5ms
    p99: 10ms

  data_freshness:
    cache_ttl: 60s
    max_staleness: 300s
```

---

## Benchmarking & Monitoring

### Prometheus Metrics

**Key Metrics to Track:**

```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    'sark_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'sark_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Policy metrics
policy_evaluation_duration = Histogram(
    'sark_policy_evaluation_duration_seconds',
    'OPA policy evaluation time',
    ['policy', 'decision'],
    buckets=[0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# Database metrics
db_query_duration = Histogram(
    'sark_db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table']
)

db_pool_size = Gauge(
    'sark_db_pool_size',
    'Current database connection pool size'
)

db_pool_overflow = Gauge(
    'sark_db_pool_overflow',
    'Database connection pool overflow'
)

# Cache metrics
cache_hits = Counter(
    'sark_cache_hits_total',
    'Cache hit count',
    ['cache_name']
)

cache_misses = Counter(
    'sark_cache_misses_total',
    'Cache miss count',
    ['cache_name']
)
```

### Grafana Dashboards

**Dashboard: SARK Performance Overview**

```json
{
  "dashboard": {
    "title": "SARK Performance",
    "panels": [
      {
        "title": "API Latency (p50, p95, p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(sark_http_request_duration_seconds_bucket[5m]))"
          },
          {
            "expr": "histogram_quantile(0.95, rate(sark_http_request_duration_seconds_bucket[5m]))"
          },
          {
            "expr": "histogram_quantile(0.99, rate(sark_http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Throughput (RPS)",
        "targets": [
          {
            "expr": "rate(sark_http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "rate(sark_cache_hits_total[5m]) / (rate(sark_cache_hits_total[5m]) + rate(sark_cache_misses_total[5m]))"
          }
        ]
      }
    ]
  }
}
```

### Load Testing Setup

```bash
# Install k6 load testing tool
brew install k6  # macOS
# or
sudo apt install k6  # Linux

# Run load test
k6 run scripts/load-test.js
```

**Load Test Script:**

```javascript
// scripts/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp to 200 users
    { duration: '5m', target: 200 },   // Stay at 200 users
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<100', 'p(99)<200'],  // 95% < 100ms, 99% < 200ms
    http_req_failed: ['rate<0.01'],  // Error rate < 1%
  },
};

export default function () {
  // Test policy evaluation
  const policyRes = http.post(
    'http://sark-api:8000/api/v1/policy/evaluate',
    JSON.stringify({
      user_id: '00000000-0000-0000-0000-000000000000',
      action: 'tool:invoke',
      tool: 'test_tool',
      parameters: {}
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(policyRes, {
    'status is 200': (r) => r.status === 200,
    'response time < 100ms': (r) => r.timings.duration < 100,
  });

  sleep(1);
}
```

---

## Database Optimization

### PostgreSQL Tuning

**Configuration (postgresql.conf):**

```ini
# Connection pooling
max_connections = 200
shared_buffers = 8GB              # 25% of RAM
effective_cache_size = 24GB       # 75% of RAM
maintenance_work_mem = 2GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1            # For SSD
effective_io_concurrency = 200    # For SSD

# Query performance
work_mem = 64MB                   # Per operation
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
```

### Indexing Strategy

```sql
-- Core indexes for SARK tables

-- Users table
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_users_role ON users(role) WHERE is_active = true;

-- MCP Servers table
CREATE INDEX CONCURRENTLY idx_servers_status ON mcp_servers(status);
CREATE INDEX CONCURRENTLY idx_servers_owner ON mcp_servers(owner_id);
CREATE INDEX CONCURRENTLY idx_servers_team ON mcp_servers(team_id);
CREATE INDEX CONCURRENTLY idx_servers_name_trgm ON mcp_servers USING gin(name gin_trgm_ops);

-- Tools table
CREATE INDEX CONCURRENTLY idx_tools_server ON mcp_tools(server_id);
CREATE INDEX CONCURRENTLY idx_tools_name ON mcp_tools(name);
CREATE INDEX CONCURRENTLY idx_tools_sensitivity ON mcp_tools(sensitivity_level);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY idx_servers_team_status
    ON mcp_servers(team_id, status)
    WHERE status = 'active';

-- Audit events (TimescaleDB) - partition by time
CREATE INDEX idx_audit_user_time ON audit_events(user_id, timestamp DESC);
CREATE INDEX idx_audit_server_time ON audit_events(server_id, timestamp DESC);
CREATE INDEX idx_audit_type_time ON audit_events(event_type, timestamp DESC);
```

### Query Optimization

**Use EXPLAIN ANALYZE:**

```sql
-- Analyze query performance
EXPLAIN (ANALYZE, BUFFERS)
SELECT s.id, s.name, t.name as tool_name
FROM mcp_servers s
JOIN mcp_tools t ON t.server_id = s.id
WHERE s.team_id = 'team-123'
  AND s.status = 'active'
  AND t.sensitivity_level = 'high';

-- Look for:
-- 1. Seq Scan (bad) → Add index
-- 2. High "Execution Time" → Optimize query
-- 3. High "Buffers: shared hit" → Good (using cache)
-- 4. "Rows Removed by Filter" → Improve WHERE clause
```

**Optimize N+1 Queries:**

```python
# BAD - N+1 query problem
servers = await db.execute(select(MCPServer))
for server in servers:
    tools = await db.execute(select(MCPTool).where(MCPTool.server_id == server.id))
    # Executes 1 + N queries

# GOOD - Use eager loading
from sqlalchemy.orm import selectinload

servers = await db.execute(
    select(MCPServer).options(selectinload(MCPServer.tools))
)
# Executes 2 queries total
```

### Connection Pooling

```python
# Optimal pool configuration
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    postgres_dsn,
    pool_size=20,              # Base pool size
    max_overflow=10,           # Additional connections under load
    pool_pre_ping=True,        # Check connection health
    pool_recycle=3600,         # Recycle connections every hour
    pool_timeout=30,           # Wait 30s for connection
    echo=False,                # Disable SQL logging in production
)
```

### TimescaleDB Optimization

```sql
-- Create hypertable for audit events
SELECT create_hypertable('audit_events', 'timestamp');

-- Set chunk time interval (1 day chunks)
SELECT set_chunk_time_interval('audit_events', INTERVAL '1 day');

-- Enable compression
ALTER TABLE audit_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'user_id,event_type'
);

-- Compress chunks older than 7 days
SELECT add_compression_policy('audit_events', INTERVAL '7 days');

-- Retention policy - drop chunks older than 90 days
SELECT add_retention_policy('audit_events', INTERVAL '90 days');

-- Continuous aggregates for fast queries
CREATE MATERIALIZED VIEW audit_events_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', timestamp) AS hour,
       user_id,
       event_type,
       COUNT(*) as event_count
FROM audit_events
GROUP BY hour, user_id, event_type;

-- Refresh policy
SELECT add_continuous_aggregate_policy('audit_events_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

---

## Caching Strategy

### Redis Configuration

```bash
# redis.conf optimization
maxmemory 8gb
maxmemory-policy allkeys-lru
tcp-backlog 511
timeout 0
tcp-keepalive 300

# Persistence (for critical data only)
appendonly yes
appendfsync everysec

# Performance
save ""  # Disable RDB snapshots for better performance
```

### Multi-Level Caching

```
┌─────────────────────────────────────────┐
│ L1: Application Cache (Local)           │
│ - In-memory LRU cache                   │
│ - TTL: 10 seconds                       │
│ - Size: 1000 entries                    │
└─────────────┬───────────────────────────┘
              │ Miss
┌─────────────▼───────────────────────────┐
│ L2: Redis Cache (Distributed)           │
│ - Policy decisions                      │
│ - User attributes                       │
│ - TTL: 60 seconds                       │
└─────────────┬───────────────────────────┘
              │ Miss
┌─────────────▼───────────────────────────┐
│ L3: Database (PostgreSQL)               │
│ - Source of truth                       │
└─────────────────────────────────────────┘
```

**Implementation:**

```python
from functools import lru_cache
import redis
from typing import Optional

class CacheService:
    """Multi-level caching service."""

    def __init__(self):
        self.redis = redis.Redis(
            host='redis',
            port=6379,
            decode_responses=True
        )

    @lru_cache(maxsize=1000)  # L1: Local cache
    def get_policy_decision_local(self, cache_key: str) -> Optional[dict]:
        """Get from local cache."""
        return None  # LRU cache handles this

    def get_policy_decision_redis(self, cache_key: str) -> Optional[dict]:
        """Get from Redis cache."""
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    async def get_policy_decision(
        self,
        user_id: str,
        tool_id: str,
        action: str
    ) -> dict:
        """Get policy decision with multi-level caching."""
        cache_key = f"policy:{user_id}:{tool_id}:{action}"

        # L1: Check local cache
        result = self.get_policy_decision_local(cache_key)
        if result:
            return result

        # L2: Check Redis
        result = self.get_policy_decision_redis(cache_key)
        if result:
            return result

        # L3: Query OPA and database
        result = await self.evaluate_policy(user_id, tool_id, action)

        # Populate caches
        self.redis.setex(cache_key, 60, json.dumps(result))

        return result
```

### Cache Invalidation

```python
class CacheInvalidation:
    """Smart cache invalidation."""

    def invalidate_user_cache(self, user_id: str):
        """Invalidate all caches for a user."""
        # Pattern-based deletion
        pattern = f"policy:{user_id}:*"
        for key in self.redis.scan_iter(pattern):
            self.redis.delete(key)

    def invalidate_tool_cache(self, tool_id: str):
        """Invalidate all caches for a tool."""
        pattern = f"policy:*:{tool_id}:*"
        for key in self.redis.scan_iter(pattern):
            self.redis.delete(key)

    def invalidate_on_policy_update(self, policy_id: str):
        """Invalidate affected caches when policy changes."""
        # Flush all policy caches (conservative approach)
        self.redis.flushdb()

        # Better: Track policy dependencies and invalidate selectively
        affected_users = self.get_users_affected_by_policy(policy_id)
        for user_id in affected_users:
            self.invalidate_user_cache(user_id)
```

---

## API Performance

### Async Request Handling

```python
from fastapi import FastAPI
import asyncio

app = FastAPI()

# GOOD - Async handlers
@app.post("/api/v1/servers")
async def register_server(request: ServerRegistrationRequest):
    """Async allows concurrent request handling."""
    async with get_db() as db:
        server = await discovery_service.register_server(...)
    return server

# BAD - Blocking I/O
@app.post("/api/v1/servers")
def register_server_sync(request: ServerRegistrationRequest):
    """Blocks entire worker process."""
    db = get_db_sync()
    server = discovery_service.register_server_sync(...)
    return server
```

### Request Batching

```python
@app.post("/api/v1/policy/batch-evaluate")
async def batch_evaluate_policies(
    requests: list[PolicyEvaluationRequest]
) -> list[PolicyEvaluationResponse]:
    """Batch policy evaluations for efficiency."""
    # Single OPA query with multiple inputs
    results = await opa_client.batch_evaluate([
        req.to_opa_input() for req in requests
    ])

    return [
        PolicyEvaluationResponse.from_opa_result(result)
        for result in results
    ]

# Client usage:
# Instead of 100 individual requests, send 1 batch request
responses = await client.post(
    "/api/v1/policy/batch-evaluate",
    json=[{...}, {...}, ...]  # 100 evaluations
)
```

### Response Compression

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses > 1KB
```

### Pagination

```python
from fastapi import Query

@app.get("/api/v1/servers")
async def list_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Paginated server listing."""
    offset = (page - 1) * page_size

    query = select(MCPServer).offset(offset).limit(page_size)
    servers = await db.execute(query)

    total = await db.scalar(select(func.count(MCPServer.id)))

    return {
        "servers": [server.to_dict() for server in servers],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size
        }
    }
```

---

## OPA Policy Optimization

### Policy Compilation

```bash
# Compile policies for faster evaluation
opa build opa/policies/ \
    --bundle \
    --optimize=1 \
    --output optimized-bundle.tar.gz

# Deploy optimized bundle
curl -X PUT http://opa:8181/v1/policies/sark \
    --data-binary @optimized-bundle.tar.gz
```

### Early Termination

```rego
# GOOD - Fail fast
allow if {
    # Cheap checks first
    input.action == "tool:invoke"
    input.tool.sensitivity_level != "critical"

    # Expensive checks last
    user_has_permission(input.user.id, input.tool.id)
}

# BAD - Expensive operation always runs
allow if {
    user_has_permission(input.user.id, input.tool.id)
    input.action == "tool:invoke"
}
```

### Caching OPA Decisions

```python
class CachedOPAClient:
    """OPA client with decision caching."""

    async def evaluate_policy(
        self,
        auth_input: AuthorizationInput
    ) -> AuthorizationDecision:
        # Generate cache key
        cache_key = hash_auth_input(auth_input)

        # Check cache
        cached = await redis.get(f"opa_decision:{cache_key}")
        if cached:
            return AuthorizationDecision.parse_raw(cached)

        # Evaluate policy
        decision = await super().evaluate_policy(auth_input)

        # Cache decision (short TTL)
        await redis.setex(
            f"opa_decision:{cache_key}",
            30,  # 30 seconds
            decision.json()
        )

        return decision
```

---

## Network & Infrastructure

### CDN for Static Assets

```nginx
# nginx.conf
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location /api/ {
    proxy_pass http://sark-api:8000;
    proxy_cache api_cache;
    proxy_cache_valid 200 60s;
    proxy_cache_key "$request_uri|$http_authorization";
}
```

### HTTP/2 & Connection Reuse

```python
# Use HTTP/2 for better performance
import httpx

client = httpx.AsyncClient(http2=True)

# Connection pooling
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    )
)
```

---

## Horizontal Scaling

### Kubernetes HPA (Horizontal Pod Autoscaler)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sark-api-hpa
  namespace: sark-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark-api
  minReplicas: 3
  maxReplicas: 50
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
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Target Audience:** SRE, Platform Engineering
**Owner:** Platform Team
