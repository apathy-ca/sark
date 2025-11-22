# SARK Performance Tuning Guide

**Version:** 1.0
**Last Updated:** 2025-11-22
**Audience:** SRE, DevOps, Platform Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Performance Targets](#performance-targets)
3. [Policy Optimization](#policy-optimization)
4. [Cache Configuration](#cache-configuration)
5. [SIEM Throughput Optimization](#siem-throughput-optimization)
6. [Session Management at Scale](#session-management-at-scale)
7. [Database Optimization](#database-optimization)
8. [API Performance Tuning](#api-performance-tuning)
9. [Load Testing](#load-testing)
10. [Monitoring & Profiling](#monitoring--profiling)

---

## Overview

This guide provides comprehensive performance tuning recommendations for SARK deployments at scale. Follow these guidelines to achieve optimal performance for high-traffic production environments.

### Performance Philosophy

1. **Measure First**: Always benchmark before and after changes
2. **Optimize Bottlenecks**: Focus on the slowest components first
3. **Cache Aggressively**: But invalidate correctly
4. **Scale Horizontally**: Design for multi-pod deployments
5. **Monitor Continuously**: Track metrics in production

---

## Performance Targets

### Latency Targets

| Operation | Target (p95) | Warning (p95) | Critical (p95) |
|-----------|--------------|---------------|----------------|
| **API Response** | <100ms | <200ms | <500ms |
| **Server Registration** | <200ms | <500ms | <1000ms |
| **Policy Evaluation (cache hit)** | <5ms | <10ms | <20ms |
| **Policy Evaluation (cache miss)** | <50ms | <100ms | <200ms |
| **Database Query** | <20ms | <50ms | <100ms |
| **SIEM Event Forwarding** | <100ms | <200ms | <500ms |
| **Token Refresh** | <50ms | <100ms | <200ms |

### Throughput Targets

| Metric | Target | Recommended |
|--------|--------|-------------|
| **API Requests** | 1,000 req/s | 5,000+ req/s |
| **Policy Evaluations** | 1,000 eval/s | 5,000+ eval/s |
| **SIEM Events** | 10,000 events/min | 50,000+ events/min |
| **Concurrent Users** | 1,000 | 10,000+ |
| **Database Connections** | 50 per pod | 100 per pod (max) |

### Resource Targets

| Resource | Target | Warning | Critical |
|----------|--------|---------|----------|
| **CPU Usage** | <60% | <80% | <90% |
| **Memory Usage** | <70% | <85% | <95% |
| **Database Connections** | <50% pool | <80% pool | <95% pool |
| **Redis Memory** | <75% | <90% | <95% |

---

## Policy Optimization

OPA policy evaluation is critical for authorization performance.

### 1. Policy Caching Strategy

#### Optimal Cache TTL by Sensitivity

```bash
# Environment configuration
POLICY_CACHE_ENABLED=true

# TTL by sensitivity level
POLICY_CACHE_TTL_LOW=600        # 10 minutes (safe to cache longer)
POLICY_CACHE_TTL_MEDIUM=300     # 5 minutes
POLICY_CACHE_TTL_HIGH=60        # 1 minute
POLICY_CACHE_TTL_CRITICAL=30    # 30 seconds (minimal caching)
POLICY_CACHE_DEFAULT_TTL=120    # 2 minutes (fallback)
```

#### Cache Performance Tuning

**Target:** >80% cache hit rate

```bash
# Check current hit rate
kubectl exec -it <redis-pod> -- redis-cli INFO stats | grep keyspace_hits

# Calculate hit rate
hit_rate = hits / (hits + misses) * 100
```

**If hit rate < 80%:**

1. **Increase TTL for low-risk operations:**
```bash
POLICY_CACHE_TTL_LOW=1200  # 20 minutes
POLICY_CACHE_TTL_MEDIUM=600  # 10 minutes
```

2. **Pre-warm cache on deployment:**
```python
# Pre-warm script
async def prewarm_policy_cache():
    common_operations = [
        ("server:read", "LOW"),
        ("server:write", "MEDIUM"),
        ("tool:invoke", "HIGH"),
    ]
    for action, sensitivity in common_operations:
        await opa_client.evaluate_policy({
            "action": action,
            "resource": {"sensitivity": sensitivity}
        })
```

3. **Analyze cache misses:**
```bash
# Enable cache miss logging
POLICY_CACHE_LOG_MISSES=true

# Review logs
kubectl logs <sark-pod> | grep "policy_cache_miss" | jq '.context'
```

### 2. Optimize OPA Policies

#### Use Efficient Rego Patterns

**❌ Inefficient (nested loops):**
```rego
allow {
    some i
    input.user.roles[i] == role
    some j
    data.permissions[role][j].action == input.action
}
```

**✅ Efficient (sets and indexing):**
```rego
# Build indexed permission map
role_permissions[role] = permissions {
    permissions := {p | p := data.permissions[role][_]}
}

# Use indexed lookup
allow {
    role := input.user.roles[_]
    permission := role_permissions[role][_]
    permission.action == input.action
}
```

#### Minimize Policy Complexity

**Guidelines:**
- **Avoid nested loops**: Use set operations instead
- **Limit data bundle size**: Only include necessary data
- **Use early returns**: Fail fast on obvious denials
- **Cache expensive computations**: Reuse results within policy

**Example - Early Return Pattern:**
```rego
# Check critical conditions first
deny["user not authenticated"] {
    not input.user.authenticated
}

deny["insufficient role"] {
    not has_required_role
}

# Only evaluate expensive policies if basics pass
allow {
    has_required_role
    has_team_access
    within_time_window
    not blocked_by_ip
}
```

### 3. Batch Policy Evaluation

For bulk operations, use batch evaluation:

**❌ Individual Evaluations (slow):**
```python
for server in servers:
    decision = await opa.evaluate_policy({
        "action": "server:register",
        "resource": server
    })
```

**✅ Batch Evaluation (fast):**
```python
# Single OPA call for all servers
decisions = await opa.evaluate_batch([
    {
        "action": "server:register",
        "resource": server
    }
    for server in servers
])
```

**Performance Gain:** ~10x faster for batches of 100+ items

### 4. OPA Server Tuning

```bash
# OPA configuration
OPA_LOG_LEVEL=warn  # Reduce logging overhead

# Resource allocation
OPA_CPU_REQUEST=500m
OPA_CPU_LIMIT=2000m
OPA_MEMORY_REQUEST=512Mi
OPA_MEMORY_LIMIT=2Gi

# Connection pooling
OPA_HTTP_POOL_SIZE=100
OPA_TIMEOUT_SECONDS=30
```

---

## Cache Configuration

### Redis Optimization

#### Memory Management

```bash
# Redis configuration
REDIS_MAX_MEMORY=4gb
REDIS_MAX_MEMORY_POLICY=allkeys-lru  # Evict least recently used

# Persistence (disable for cache-only use)
REDIS_SAVE=""  # Disable RDB snapshots
REDIS_APPENDONLY=no  # Disable AOF
```

#### Connection Pooling

```python
# Redis connection pool settings
REDIS_POOL_SIZE=50  # Per pod
REDIS_POOL_TIMEOUT=5  # seconds
REDIS_SOCKET_KEEPALIVE=true
REDIS_SOCKET_TIMEOUT=5
```

#### Cache Key Design

**Efficient Keys:**
- Use consistent naming: `prefix:type:id`
- Keep keys short: `pol:dec:u123:act456:hash`
- Use hashes for related data: `HSET user:123 name "Alice" email "alice@example.com"`

**Avoid:**
- Long keys with redundant data
- Deeply nested JSON in values
- Storing large objects (>1MB)

### Cache Invalidation Strategy

```python
# Time-based invalidation (TTL)
await redis.setex("policy:decision:key", ttl=300, value=decision)

# Event-based invalidation
async def on_policy_update(policy_id):
    # Clear all decisions for this policy
    keys = await redis.keys(f"policy:decision:*:policy:{policy_id}:*")
    if keys:
        await redis.delete(*keys)

# Manual invalidation endpoint
@router.post("/admin/cache/clear")
async def clear_cache(pattern: str = "*"):
    keys = await redis.keys(f"policy:decision:{pattern}")
    deleted = await redis.delete(*keys)
    return {"deleted": deleted}
```

---

## SIEM Throughput Optimization

### Batch Configuration

Optimize for high throughput while maintaining low latency:

```bash
# Batch settings for 10,000+ events/min
SIEM_BATCH_SIZE=200              # Events per batch
SIEM_BATCH_TIMEOUT_SECONDS=5     # Max wait time
SIEM_MAX_QUEUE_SIZE=20000        # Event buffer

# Retry configuration
SIEM_RETRY_ATTEMPTS=3
SIEM_RETRY_BACKOFF_BASE=2.0
SIEM_RETRY_BACKOFF_MAX=60.0
```

### Performance by Batch Size

| Batch Size | Events/min | Avg Latency | Network | CPU | Recommendation |
|------------|------------|-------------|---------|-----|----------------|
| 50 | 5,000 | 35ms | 2 MB/min | Low | Small deployments |
| 100 | 10,000 | 42ms | 4 MB/min | Low | **Recommended** |
| 200 | 18,000 | 58ms | 7 MB/min | Medium | High throughput |
| 500 | 25,000 | 95ms | 12 MB/min | High | Maximum throughput |

**Recommendation:** Use batch size 100-200 for optimal balance.

### Compression

Enable compression for large payloads:

```python
# Enable gzip compression
SIEM_COMPRESS_PAYLOADS=true
SIEM_COMPRESSION_THRESHOLD=1024  # Compress if payload > 1KB

# Compression ratio: ~70% reduction for JSON
# Before: 10 KB/event → After: 3 KB/event
```

### Parallel SIEM Forwarding

For multiple SIEM destinations:

```python
# Send to multiple SIEMs in parallel
async def forward_to_all_siems(events):
    tasks = [
        splunk_client.send_batch(events),
        datadog_client.send_batch(events),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### SIEM Resource Allocation

```bash
# SARK pod resources
CPU_REQUEST=1000m       # 1 CPU
CPU_LIMIT=4000m         # 4 CPUs (for batch processing)
MEMORY_REQUEST=2Gi
MEMORY_LIMIT=8Gi

# Network bandwidth
# Estimate: 10,000 events/min × 500 bytes/event = 5 MB/min = 83 KB/s
# Recommendation: Ensure at least 1 Mbps network bandwidth
```

---

## Session Management at Scale

### Redis Session Store Optimization

```bash
# Session configuration
JWT_EXPIRATION_MINUTES=60                # Short-lived access tokens
REFRESH_TOKEN_EXPIRATION_DAYS=7          # Long-lived refresh tokens
REFRESH_TOKEN_ROTATION_ENABLED=true      # Security best practice

# Redis settings for sessions
REDIS_SESSION_DB=1  # Separate DB for sessions
REDIS_SESSION_POOL_SIZE=100
```

### Session Cleanup

**Problem:** Expired sessions accumulate in Redis, wasting memory.

**Solution 1: TTL-based Auto-Cleanup (Recommended)**
```python
# Set TTL on all refresh tokens
async def create_refresh_token(user_id: str):
    token_id = str(uuid.uuid4())
    key = f"refresh_token:user:{user_id}:{token_id}"
    ttl = settings.refresh_token_expiration_days * 86400
    await redis.setex(key, ttl, token_data)
```

**Solution 2: Periodic Cleanup Job**
```python
# Cron job to clean expired tokens
async def cleanup_expired_sessions():
    pattern = "refresh_token:*"
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=1000)
        for key in keys:
            ttl = await redis.ttl(key)
            if ttl == -1:  # No expiration set
                await redis.delete(key)
                deleted += 1
        if cursor == 0:
            break
    return deleted
```

### Scaling Sessions

**For 10,000+ concurrent users:**

```bash
# Redis cluster mode
REDIS_CLUSTER_ENABLED=true
REDIS_CLUSTER_NODES=3

# Connection pooling
REDIS_POOL_SIZE=200  # Higher for high session count

# Memory estimate
# 1000 bytes/session × 10,000 users = 10 MB
# Add 50% overhead = 15 MB
# Recommendation: Allocate 1 GB for session store
```

---

## Database Optimization

### Connection Pooling

```bash
# PostgreSQL connection pool
DATABASE_POOL_SIZE=20          # Per pod
DATABASE_MAX_OVERFLOW=10       # Additional connections if needed
DATABASE_POOL_TIMEOUT=30       # seconds
DATABASE_POOL_RECYCLE=3600     # Recycle connections every hour
DATABASE_ECHO=false            # Disable SQL logging in production
```

**Sizing Guide:**
- **Small deployment** (1-3 pods): 20 connections/pod
- **Medium deployment** (4-10 pods): 15 connections/pod
- **Large deployment** (10+ pods): 10 connections/pod

**Database Connection Limit:**
```sql
-- PostgreSQL max connections (default: 100)
-- Ensure: (pods × pool_size) < max_connections
ALTER SYSTEM SET max_connections = 300;
```

### Query Optimization

#### Add Indexes

```sql
-- Server queries
CREATE INDEX idx_servers_status ON servers(status);
CREATE INDEX idx_servers_team ON servers(team);
CREATE INDEX idx_servers_sensitivity ON servers(sensitivity_level);
CREATE INDEX idx_servers_created_at ON servers(created_at DESC);

-- Audit events
CREATE INDEX idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_user_id ON audit_events(user_id);
CREATE INDEX idx_audit_event_type ON audit_events(event_type);

-- Composite indexes for common queries
CREATE INDEX idx_servers_status_team ON servers(status, team);
CREATE INDEX idx_servers_search ON servers USING gin(to_tsvector('english', name || ' ' || description));
```

#### Optimize Pagination

**✅ Cursor-based pagination (efficient):**
```python
# Uses index on created_at
SELECT * FROM servers
WHERE created_at > :cursor
ORDER BY created_at
LIMIT 50;
```

**❌ Offset-based pagination (slow for large datasets):**
```python
# Scans all rows before offset
SELECT * FROM servers
ORDER BY created_at
LIMIT 50 OFFSET 10000;  # Slow!
```

#### Query Profiling

```sql
-- Enable query logging for slow queries
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries > 100ms

-- Analyze query plan
EXPLAIN ANALYZE
SELECT * FROM servers WHERE status = 'active' AND team = 'platform';

-- Vacuum and analyze regularly
VACUUM ANALYZE servers;
VACUUM ANALYZE audit_events;
```

### Database Scaling

**Vertical Scaling:**
```bash
# PostgreSQL resources
PG_CPU_REQUEST=2000m
PG_CPU_LIMIT=8000m
PG_MEMORY_REQUEST=4Gi
PG_MEMORY_LIMIT=16Gi
```

**Read Replicas:**
```bash
# Route read queries to replicas
DATABASE_READ_URL=postgresql://read-replica:5432/sark

# Use primary for writes, replica for reads
async def get_servers():
    # Read from replica
    async with read_engine.connect() as conn:
        result = await conn.execute(select(Server))
```

---

## API Performance Tuning

### Application Server Configuration

```bash
# Uvicorn workers (1 per CPU core)
UVICORN_WORKERS=4
UVICORN_WORKER_CONNECTIONS=1000
UVICORN_BACKLOG=2048

# Timeout settings
UVICORN_TIMEOUT_KEEP_ALIVE=75
UVICORN_TIMEOUT_NOTIFY=300
```

### Response Compression

```python
# Enable gzip compression in FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Response size reduction: ~70% for JSON
```

### Request Validation

**Optimize Pydantic Models:**
```python
# Use efficient validators
from pydantic import BaseModel, constr, conlist

class ServerCreate(BaseModel):
    # Constrained types for validation
    name: constr(min_length=1, max_length=255)
    tags: conlist(str, max_items=20)

    class Config:
        # Disable validation for better performance
        validate_assignment = False
        # Use orjson for faster JSON parsing
        json_loads = orjson.loads
```

### Async Optimization

**Use async/await correctly:**
```python
# ✅ Good - concurrent execution
async def handle_request():
    policy_task = opa_client.evaluate(...)
    db_task = database.fetch(...)

    policy_result, db_result = await asyncio.gather(
        policy_task,
        db_task
    )

# ❌ Bad - sequential execution
async def handle_request():
    policy_result = await opa_client.evaluate(...)
    db_result = await database.fetch(...)
```

### Horizontal Scaling

```bash
# Kubernetes HPA configuration
kubectl autoscale deployment sark \
  --cpu-percent=70 \
  --min=3 \
  --max=50

# Scale based on custom metrics (requests/second)
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
  maxReplicas: 50
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

---

## Load Testing

### Tools

**Recommended:**
- **Locust**: Python-based, flexible scenarios
- **k6**: JavaScript-based, Grafana integration
- **JMeter**: GUI-based, comprehensive features

### Sample Locust Test

```python
# locustfile.py
from locust import HttpUser, task, between

class SARKUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login once per user
        response = self.client.post("/api/auth/login/ldap", json={
            "username": "testuser",
            "password": "testpass"
        })
        self.token = response.json()["access_token"]
        self.client.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_servers(self):
        self.client.get("/api/servers?limit=50")

    @task(2)
    def get_server(self):
        self.client.get("/api/servers/test-server-id")

    @task(1)
    def register_server(self):
        self.client.post("/api/servers", json={
            "name": f"test-server-{self.random.randint(1, 1000)}",
            "mcp_version": "1.0",
            "endpoint_url": "http://test.example.com"
        })
```

**Run Load Test:**
```bash
# Test with 1000 users, 50 spawn rate
locust -f locustfile.py --host=https://sark.example.com \
  --users=1000 --spawn-rate=50 --run-time=10m
```

### Performance Benchmarks

**Target Load:**
- 1,000 concurrent users
- 5,000 requests/second
- 10-minute sustained test

**Success Criteria:**
- p95 latency < 200ms
- Error rate < 0.1%
- No memory leaks
- No connection pool exhaustion

---

## Monitoring & Profiling

### Key Metrics

**Application Metrics:**
```python
# Prometheus metrics
http_requests_total
http_request_duration_seconds_bucket
policy_evaluation_duration_seconds
policy_cache_hit_rate
siem_events_sent_total
siem_batch_send_duration_seconds
database_query_duration_seconds
```

**System Metrics:**
```bash
# CPU, Memory, Network
kubectl top pods -l app=sark
kubectl top nodes
```

### Profiling

**Python Profiling:**
```python
# Enable profiling in development
import cProfile
import pstats

def profile_endpoint():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run endpoint
    result = await handle_request()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

**APM Tools:**
- **Datadog APM**: Distributed tracing
- **New Relic**: Application performance monitoring
- **Elastic APM**: Open-source alternative

### Performance Dashboards

**Grafana Widgets:**
1. **Request Rate**: `rate(http_requests_total[1m])`
2. **Error Rate**: `rate(http_requests_total{status=~"5.."}[1m])`
3. **Latency**: `histogram_quantile(0.95, http_request_duration_seconds_bucket)`
4. **Cache Hit Rate**: `policy_cache_hit_rate`
5. **Database Connections**: `database_connections_active`

---

## Performance Checklist

### Pre-Deployment

- [ ] Load test with 2x expected traffic
- [ ] Profile slow endpoints
- [ ] Optimize database queries
- [ ] Configure caching (Redis)
- [ ] Enable response compression
- [ ] Set up horizontal pod autoscaling
- [ ] Configure database connection pooling
- [ ] Optimize OPA policies
- [ ] Enable SIEM batching
- [ ] Set resource limits (CPU/Memory)

### Post-Deployment

- [ ] Monitor p95 latency
- [ ] Track cache hit rate
- [ ] Review slow query logs
- [ ] Monitor error rates
- [ ] Check resource utilization
- [ ] Analyze SIEM throughput
- [ ] Review policy evaluation latency
- [ ] Validate auto-scaling triggers
- [ ] Check database connection pool usage
- [ ] Monitor Redis memory usage

### Continuous Optimization

- [ ] Weekly performance review
- [ ] Monthly load testing
- [ ] Quarterly capacity planning
- [ ] Regular index maintenance
- [ ] Cache eviction policy tuning
- [ ] OPA policy optimization
- [ ] Database vacuum and analyze

---

## Troubleshooting Performance Issues

### High Latency

**Diagnosis:**
```bash
# Check p95 latency by endpoint
kubectl logs <sark-pod> | grep request_duration_ms | jq -r '.endpoint' | sort | uniq -c

# Identify slow endpoints
kubectl logs <sark-pod> | jq 'select(.request_duration_ms > 200)'
```

**Common Causes:**
1. **Slow database queries** → Add indexes
2. **Low cache hit rate** → Increase TTL, pre-warm cache
3. **Slow OPA evaluation** → Optimize policies
4. **Network latency** → Check SIEM/OPA connectivity

### High CPU Usage

**Diagnosis:**
```bash
kubectl top pods -l app=sark
kubectl describe pod <sark-pod> | grep -A 5 "Limits"
```

**Common Causes:**
1. **Policy evaluation overhead** → Enable caching, optimize policies
2. **JSON serialization** → Use orjson for faster parsing
3. **Excessive logging** → Reduce log level to WARN
4. **High request rate** → Scale horizontally

### High Memory Usage

**Diagnosis:**
```bash
kubectl top pods -l app=sark
kubectl exec -it <sark-pod> -- python -m memory_profiler app.py
```

**Common Causes:**
1. **Redis cache growth** → Set `maxmemory-policy=allkeys-lru`
2. **Connection pool leaks** → Check pool size configuration
3. **Large response payloads** → Enable compression
4. **Memory leaks** → Profile with memory_profiler

---

## Recommended Configuration for Production

```bash
# Application
UVICORN_WORKERS=4
UVICORN_WORKER_CONNECTIONS=1000

# Database
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_RECYCLE=3600

# Redis
REDIS_POOL_SIZE=50
REDIS_MAX_MEMORY=4gb
REDIS_MAX_MEMORY_POLICY=allkeys-lru

# Policy Caching
POLICY_CACHE_ENABLED=true
POLICY_CACHE_TTL_LOW=600
POLICY_CACHE_TTL_MEDIUM=300
POLICY_CACHE_TTL_HIGH=60

# SIEM
SIEM_BATCH_SIZE=100
SIEM_BATCH_TIMEOUT_SECONDS=5
SIEM_MAX_QUEUE_SIZE=20000
SIEM_COMPRESS_PAYLOADS=true

# Session Management
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=7
REFRESH_TOKEN_ROTATION_ENABLED=true

# Kubernetes Resources (per pod)
CPU_REQUEST=1000m
CPU_LIMIT=4000m
MEMORY_REQUEST=2Gi
MEMORY_LIMIT=8Gi

# Horizontal Pod Autoscaler
HPA_MIN_REPLICAS=3
HPA_MAX_REPLICAS=50
HPA_TARGET_CPU_PERCENT=70
```

---

## Related Documentation

- [OPERATIONAL_RUNBOOK.md](./OPERATIONAL_RUNBOOK.md) - Operational procedures
- [MONITORING.md](./MONITORING.md) - Monitoring and alerting setup
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment configuration
- [POLICY_CACHING.md](./POLICY_CACHING.md) - Policy caching details
- [siem/SIEM_INTEGRATION.md](./siem/SIEM_INTEGRATION.md) - SIEM integration

---

**Document Maintenance:**
- Review after major releases
- Update benchmarks quarterly
- Version with performance targets
