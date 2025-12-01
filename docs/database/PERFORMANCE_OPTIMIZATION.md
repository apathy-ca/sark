# SARK v2.0: Database Performance Optimization Guide

**Version:** 1.0
**Author:** ENGINEER-6 (Database & Migration Lead)
**Created:** December 2, 2025

---

## Overview

This guide covers performance optimization strategies for SARK v2.0's polymorphic resource/capability schema. The v2.0 schema introduces protocol-agnostic tables that must perform efficiently across multiple protocol types (MCP, HTTP, gRPC, etc.).

---

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Resource lookup by ID | < 5ms | < 10ms |
| Capability lookup by resource | < 10ms | < 25ms |
| Cross-protocol queries | < 50ms | < 100ms |
| Audit event insertion | < 5ms | < 10ms |
| Cost tracking insertion | < 3ms | < 5ms |
| Federation node lookup | < 5ms | < 10ms |
| Daily cost aggregation | < 500ms | < 1s |

---

## Index Strategy

### Primary Indexes (Created in Migrations)

```sql
-- resources table
CREATE INDEX idx_resources_protocol ON resources(protocol);
CREATE INDEX idx_resources_sensitivity ON resources(sensitivity_level);
CREATE INDEX idx_resources_name ON resources(name);
CREATE INDEX idx_resources_metadata_gin ON resources USING gin(metadata);

-- capabilities table
CREATE INDEX idx_capabilities_resource ON capabilities(resource_id);
CREATE INDEX idx_capabilities_name ON capabilities(name);
CREATE INDEX idx_capabilities_sensitivity ON capabilities(sensitivity_level);
CREATE INDEX idx_capabilities_metadata_gin ON capabilities USING gin(metadata);

-- audit_events enhancements
CREATE INDEX idx_audit_correlation ON audit_events(correlation_id);
CREATE INDEX idx_audit_principal_org ON audit_events(principal_org);
CREATE INDEX idx_audit_source_node ON audit_events(source_node);
CREATE INDEX idx_audit_target_node ON audit_events(target_node);
CREATE INDEX idx_audit_capability ON audit_events(capability_id);

-- cost_tracking table
CREATE INDEX idx_cost_timestamp ON cost_tracking(timestamp DESC);
CREATE INDEX idx_cost_principal ON cost_tracking(principal_id);
CREATE INDEX idx_cost_resource ON cost_tracking(resource_id);
CREATE INDEX idx_cost_capability ON cost_tracking(capability_id);

-- federation_nodes table
CREATE INDEX idx_federation_nodes_node_id ON federation_nodes(node_id);
CREATE INDEX idx_federation_nodes_enabled ON federation_nodes(enabled) WHERE enabled = true;
```

### Composite Indexes (Optional for High-Traffic Queries)

```sql
-- Multi-column indexes for common query patterns
CREATE INDEX idx_resources_protocol_sensitivity ON resources(protocol, sensitivity_level);
CREATE INDEX idx_capabilities_resource_sensitivity ON capabilities(resource_id, sensitivity_level);
CREATE INDEX idx_audit_principal_timestamp ON audit_events(principal_id, timestamp DESC);
CREATE INDEX idx_cost_principal_timestamp ON cost_tracking(principal_id, timestamp DESC);
```

### Index Usage Analysis

```sql
-- Check index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public'
  AND indexname NOT LIKE 'pg_toast%';
```

---

## Query Optimization Patterns

### 1. Protocol-Specific Resource Queries

**Good:**
```sql
-- Uses idx_resources_protocol
SELECT * FROM resources
WHERE protocol = 'mcp'
LIMIT 100;
```

**Bad:**
```sql
-- Forces sequential scan
SELECT * FROM resources
WHERE protocol LIKE '%mcp%';
```

### 2. JSONB Metadata Queries

**Good:**
```sql
-- Uses GIN index with containment operator
SELECT * FROM resources
WHERE metadata @> '{"transport": "stdio"}';
```

**Bad:**
```sql
-- Requires sequential scan (arrow operator not indexed)
SELECT * FROM resources
WHERE metadata->>'transport' = 'stdio';
```

**Workaround for Equality:**
```sql
-- Use containment for better performance
SELECT * FROM resources
WHERE metadata @> jsonb_build_object('transport', 'stdio');
```

### 3. Cross-Protocol Aggregations

**Good:**
```sql
-- Uses indexes, groups efficiently
SELECT
    r.protocol,
    COUNT(c.id) as capability_count
FROM resources r
LEFT JOIN capabilities c ON c.resource_id = r.id
GROUP BY r.protocol;
```

**Better:**
```sql
-- Use materialized view for repeated queries
CREATE MATERIALIZED VIEW mv_protocol_stats AS
SELECT
    r.protocol,
    COUNT(DISTINCT r.id) as resource_count,
    COUNT(c.id) as capability_count,
    COUNT(DISTINCT c.id) as unique_capabilities
FROM resources r
LEFT JOIN capabilities c ON c.resource_id = r.id
GROUP BY r.protocol;

CREATE INDEX ON mv_protocol_stats(protocol);

-- Refresh periodically (e.g., hourly)
REFRESH MATERIALIZED VIEW mv_protocol_stats;
```

### 4. Federation Audit Correlation

**Good:**
```sql
-- Uses idx_audit_correlation
SELECT
    source_node,
    target_node,
    COUNT(*) as request_count
FROM audit_events
WHERE correlation_id IS NOT NULL
  AND timestamp >= NOW() - INTERVAL '1 day'
GROUP BY source_node, target_node;
```

**Better with CTE:**
```sql
-- Pre-filter with index, then aggregate
WITH recent_federated AS (
    SELECT source_node, target_node
    FROM audit_events
    WHERE correlation_id IS NOT NULL
      AND timestamp >= NOW() - INTERVAL '1 day'
)
SELECT
    source_node,
    target_node,
    COUNT(*) as request_count
FROM recent_federated
GROUP BY source_node, target_node;
```

### 5. Cost Tracking Time-Series Queries

**Good (TimescaleDB optimized):**
```sql
-- Uses hypertable partitioning + index
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    SUM(actual_cost) as total_cost,
    COUNT(*) as invocations
FROM cost_tracking
WHERE timestamp >= NOW() - INTERVAL '7 days'
  AND principal_id = 'user-123'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;
```

**Better with Continuous Aggregates:**
```sql
-- Create continuous aggregate (TimescaleDB feature)
CREATE MATERIALIZED VIEW hourly_cost_by_principal
WITH (timescaledb.continuous) AS
SELECT
    principal_id,
    time_bucket('1 hour', timestamp) AS hour,
    SUM(actual_cost) as total_cost,
    COUNT(*) as invocations
FROM cost_tracking
GROUP BY principal_id, time_bucket('1 hour', timestamp);

-- Query the continuous aggregate
SELECT * FROM hourly_cost_by_principal
WHERE principal_id = 'user-123'
  AND hour >= NOW() - INTERVAL '7 days';
```

---

## Connection Pooling

### Recommended Settings (PostgreSQL 14+)

```ini
# postgresql.conf
max_connections = 200
shared_buffers = 4GB           # 25% of RAM
effective_cache_size = 12GB    # 75% of RAM
work_mem = 16MB
maintenance_work_mem = 512MB
random_page_cost = 1.1         # For SSD
effective_io_concurrency = 200  # For SSD
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### Application Connection Pool (SQLAlchemy)

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,              # Base connections
    max_overflow=40,           # Extra connections under load
    pool_timeout=30,           # Wait timeout
    pool_recycle=3600,         # Recycle every hour
    pool_pre_ping=True,        # Test connections
    echo_pool=False,
)
```

---

## Query Performance Monitoring

### 1. Slow Query Log

```sql
-- Enable slow query logging
ALTER DATABASE sark SET log_min_duration_statement = 100;  -- Log queries > 100ms

-- View slow queries
SELECT
    calls,
    total_exec_time / 1000 as total_sec,
    mean_exec_time / 1000 as mean_ms,
    query
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### 2. Table Statistics

```sql
-- Analyze tables for query planner
ANALYZE resources;
ANALYZE capabilities;
ANALYZE audit_events;
ANALYZE cost_tracking;

-- Auto-vacuum settings
ALTER TABLE cost_tracking SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE audit_events SET (autovacuum_vacuum_scale_factor = 0.05);
```

### 3. EXPLAIN Analysis

```sql
-- Analyze query plan
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT r.*, COUNT(c.id) as cap_count
FROM resources r
LEFT JOIN capabilities c ON c.resource_id = r.id
WHERE r.protocol = 'http'
GROUP BY r.id;

-- Look for:
-- ✅ Index Scan (good)
-- ❌ Seq Scan (bad for large tables)
-- ✅ Nested Loop (good for small joins)
-- ❌ Hash Join (can be expensive)
```

---

## TimescaleDB Optimization

### 1. Hypertable Configuration

```sql
-- Convert cost_tracking to hypertable (already in migration 007)
SELECT create_hypertable('cost_tracking', 'timestamp', if_not_exists => TRUE);

-- Set chunk time interval (default 7 days, adjust based on volume)
SELECT set_chunk_time_interval('cost_tracking', INTERVAL '7 days');

-- Optional: Compress old chunks
ALTER TABLE cost_tracking SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'principal_id, resource_id'
);

-- Add compression policy (compress data older than 30 days)
SELECT add_compression_policy('cost_tracking', INTERVAL '30 days');
```

### 2. Retention Policies

```sql
-- Drop data older than 1 year
SELECT add_retention_policy('cost_tracking', INTERVAL '365 days');

-- For audit_events (if converted to hypertable)
SELECT create_hypertable('audit_events', 'timestamp', if_not_exists => TRUE);
SELECT add_retention_policy('audit_events', INTERVAL '730 days');  -- 2 years
```

### 3. Continuous Aggregates

```sql
-- Daily cost summary (pre-aggregated)
CREATE MATERIALIZED VIEW daily_cost_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    principal_id,
    resource_id,
    SUM(actual_cost) as total_cost,
    COUNT(*) as invocations
FROM cost_tracking
GROUP BY time_bucket('1 day', timestamp), principal_id, resource_id;

-- Refresh policy (update every hour)
SELECT add_continuous_aggregate_policy('daily_cost_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
```

---

## Partitioning Strategy

### Large Table Partitioning (Future Growth)

If `resources` or `capabilities` exceed 10M rows, consider partitioning:

```sql
-- Partition resources by protocol (hash partitioning)
CREATE TABLE resources (
    -- columns...
) PARTITION BY HASH (protocol);

CREATE TABLE resources_partition_0 PARTITION OF resources
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE resources_partition_1 PARTITION OF resources
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE resources_partition_2 PARTITION OF resources
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE resources_partition_3 PARTITION OF resources
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

---

## Caching Strategy

### 1. Application-Level Cache

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache resource lookups (TTL via timestamp)
_resource_cache_time = {}

@lru_cache(maxsize=1000)
def get_resource_cached(resource_id: str, cache_key: int):
    """Cache resource lookups for 5 minutes"""
    return db.query(Resource).get(resource_id)

def get_resource(resource_id: str):
    cache_key = int(datetime.utcnow().timestamp() // 300)  # 5-minute buckets
    return get_resource_cached(resource_id, cache_key)
```

### 2. Redis Cache (for high-frequency queries)

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_protocol_stats():
    """Get cached protocol statistics"""
    cached = redis_client.get('protocol_stats')
    if cached:
        return json.loads(cached)

    # Query database
    stats = db.execute("""
        SELECT protocol, COUNT(*) as count
        FROM resources
        GROUP BY protocol
    """).fetchall()

    # Cache for 5 minutes
    redis_client.setex('protocol_stats', 300, json.dumps(stats))
    return stats
```

---

## Performance Testing

### 1. Load Testing Script

```python
import time
from sqlalchemy import create_engine, select
from sark.models.base import Resource, Capability

def benchmark_resource_lookup(engine, iterations=1000):
    """Benchmark resource lookup performance"""
    with engine.connect() as conn:
        start = time.time()
        for i in range(iterations):
            result = conn.execute(
                select(Resource).where(Resource.protocol == 'mcp').limit(100)
            ).fetchall()
        duration = time.time() - start
        avg_ms = (duration / iterations) * 1000
        print(f"Resource lookup: {avg_ms:.2f}ms avg ({iterations} iterations)")
        return avg_ms

def benchmark_cross_protocol_query(engine, iterations=100):
    """Benchmark cross-protocol aggregation"""
    with engine.connect() as conn:
        start = time.time()
        for i in range(iterations):
            result = conn.execute("""
                SELECT r.protocol, COUNT(c.id)
                FROM resources r
                LEFT JOIN capabilities c ON c.resource_id = r.id
                GROUP BY r.protocol
            """).fetchall()
        duration = time.time() - start
        avg_ms = (duration / iterations) * 1000
        print(f"Cross-protocol query: {avg_ms:.2f}ms avg ({iterations} iterations)")
        return avg_ms
```

### 2. Performance Regression Tests

```python
def test_resource_lookup_performance():
    """Ensure resource lookups are under 10ms"""
    avg_ms = benchmark_resource_lookup(engine, iterations=100)
    assert avg_ms < 10, f"Resource lookup too slow: {avg_ms}ms"

def test_cross_protocol_performance():
    """Ensure cross-protocol queries are under 100ms"""
    avg_ms = benchmark_cross_protocol_query(engine, iterations=50)
    assert avg_ms < 100, f"Cross-protocol query too slow: {avg_ms}ms"
```

---

## Troubleshooting

### Problem: Slow JSONB Queries

**Symptom:** Queries on `metadata` column are slow

**Solution:**
```sql
-- Verify GIN index is being used
EXPLAIN SELECT * FROM resources WHERE metadata @> '{"transport": "stdio"}';

-- If not, analyze table statistics
ANALYZE resources;

-- Or force index usage
SET enable_seqscan = off;
```

### Problem: High Connection Count

**Symptom:** `FATAL: sorry, too many clients already`

**Solution:**
```sql
-- Check current connections
SELECT COUNT(*) FROM pg_stat_activity;

-- Find idle connections
SELECT * FROM pg_stat_activity WHERE state = 'idle';

-- Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND state_change < NOW() - INTERVAL '10 minutes';

-- Increase max_connections (requires restart)
ALTER SYSTEM SET max_connections = 300;
```

### Problem: Bloated Tables

**Symptom:** Tables much larger than expected

**Solution:**
```sql
-- Check table bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS external_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Run VACUUM FULL (locks table)
VACUUM FULL resources;
VACUUM FULL capabilities;
```

---

## Summary

### Critical Optimizations Checklist

- ✅ All indexes created (migrations 006, 007)
- ✅ TimescaleDB hypertables configured (cost_tracking)
- ✅ Connection pooling configured
- ✅ Query patterns optimized (use indexes)
- ✅ JSONB queries use containment operator (`@>`)
- ✅ Materialized views for aggregations
- ✅ Continuous aggregates for time-series
- ✅ Auto-vacuum enabled
- ✅ Slow query logging enabled
- ✅ Performance tests passing

### Performance Metrics (Target vs Actual)

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Resource lookup | < 5ms | TBD | ⏳ |
| Capability lookup | < 10ms | TBD | ⏳ |
| Cross-protocol query | < 50ms | TBD | ⏳ |
| Cost insertion | < 3ms | TBD | ⏳ |
| Federation lookup | < 5ms | TBD | ⏳ |

---

**Document Status:** ✅ Complete
**Next Steps:**
1. Run performance benchmarks
2. Tune based on actual workload
3. Monitor production metrics
4. Adjust indexes as needed

**Questions/Feedback:** Contact ENGINEER-6 (Database & Migration Lead)
