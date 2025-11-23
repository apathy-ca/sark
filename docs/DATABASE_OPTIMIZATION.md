# Database Optimization Guide

**Document Version**: 1.0
**Last Updated**: November 22, 2025
**Audience**: Database Administrators, DevOps Engineers, Backend Developers

---

## Table of Contents

1. [Overview](#overview)
2. [Database Architecture](#database-architecture)
3. [Indexing Strategy](#indexing-strategy)
4. [Query Optimization](#query-optimization)
5. [Connection Pooling](#connection-pooling)
6. [PostgreSQL Configuration](#postgresql-configuration)
7. [TimescaleDB Optimization](#timescaledb-optimization)
8. [Performance Monitoring](#performance-monitoring)
9. [Backup and Maintenance](#backup-and-maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Overview

SARK uses two PostgreSQL databases:
- **Primary Database (PostgreSQL)**: Application data (users, servers, policies)
- **Audit Database (TimescaleDB)**: Time-series audit logs and events

This guide covers optimization techniques for both databases to ensure optimal performance under production workloads.

### Performance Goals

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Query Response Time (p95) | < 50ms | < 100ms |
| Query Response Time (p99) | < 100ms | < 200ms |
| Connection Acquisition | < 5ms | < 10ms |
| Transaction Throughput | > 1,000 TPS | > 500 TPS |
| Connection Pool Utilization | 60-80% | < 90% |
| Active Connections | < 80% of max | < 90% of max |
| Long-Running Queries | 0 (> 30s) | < 5 (> 30s) |

---

## Database Architecture

### Database Schemas

```
┌─────────────────────────────────────────────────────────────────┐
│                         SARK Database                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Primary Database (PostgreSQL 14+)                               │
│  ├── public schema                                               │
│  │   ├── users                      (Authentication data)        │
│  │   ├── servers                    (Server registry)            │
│  │   ├── policies                   (Authorization policies)     │
│  │   ├── api_keys                   (API key management)         │
│  │   ├── sessions                   (User sessions)              │
│  │   └── rate_limits                (Rate limiting state)        │
│  │                                                                │
│  └── Extensions                                                  │
│      ├── pgcrypto                   (Encryption functions)       │
│      ├── uuid-ossp                  (UUID generation)            │
│      └── pg_stat_statements         (Query statistics)           │
│                                                                   │
│  Audit Database (TimescaleDB)                                    │
│  ├── public schema                                               │
│  │   ├── audit_events               (Hypertable - time-series)   │
│  │   ├── policy_evaluations         (Hypertable - time-series)   │
│  │   └── siem_events                (Hypertable - time-series)   │
│  │                                                                │
│  └── Continuous Aggregates                                       │
│      ├── hourly_audit_summary                                    │
│      └── daily_policy_stats                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Indexing Strategy

### Index Types Overview

| Index Type | Use Case | Performance | Storage Cost |
|------------|----------|-------------|--------------|
| **B-Tree** | Equality, range queries | Fast | Medium |
| **Hash** | Equality only | Very fast | Low |
| **GIN** | Full-text search, JSONB | Slow writes, fast reads | High |
| **GiST** | Geometric, full-text | Medium | Medium |
| **BRIN** | Large tables, sequential data | Very fast writes | Very low |

### Primary Database Indexes

#### Users Table

```sql
-- Table definition
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT,
    ldap_dn TEXT,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret TEXT,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_ldap_dn ON users(ldap_dn) WHERE ldap_dn IS NOT NULL;
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;
CREATE INDEX idx_users_last_login ON users(last_login_at DESC) WHERE last_login_at IS NOT NULL;

-- Composite index for common query pattern
CREATE INDEX idx_users_active_admin ON users(is_active, is_admin)
  WHERE is_active = true;
```

**Index Rationale**:
- `idx_users_username`: Login queries (username lookup)
- `idx_users_email`: Email-based authentication
- `idx_users_ldap_dn`: LDAP authentication (partial index - only when LDAP is used)
- `idx_users_active`: Filter active users (partial index for efficiency)
- `idx_users_last_login`: Admin dashboards showing recent logins
- `idx_users_active_admin`: Multi-column index for admin user queries

#### Servers Table

```sql
-- Table definition
CREATE TABLE servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    endpoint TEXT NOT NULL,
    api_key_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    owner_id UUID REFERENCES users(id),
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_servers_name ON servers(name);
CREATE INDEX idx_servers_owner ON servers(owner_id);
CREATE INDEX idx_servers_active ON servers(is_active) WHERE is_active = true;
CREATE INDEX idx_servers_last_seen ON servers(last_seen_at DESC NULLS LAST);

-- GIN index for JSONB tag searches
CREATE INDEX idx_servers_tags ON servers USING GIN(tags);
CREATE INDEX idx_servers_metadata ON servers USING GIN(metadata);

-- Composite index for common query
CREATE INDEX idx_servers_active_owner ON servers(is_active, owner_id)
  WHERE is_active = true;
```

**Index Rationale**:
- `idx_servers_name`: Server name searches
- `idx_servers_owner`: List servers by owner
- `idx_servers_active`: Filter active servers only
- `idx_servers_last_seen`: Recently active servers
- `idx_servers_tags`: JSONB tag searches (e.g., `tags @> '["production"]'`)
- `idx_servers_metadata`: JSONB metadata queries

#### Sessions Table

```sql
-- Table definition
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    access_token_jti VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_hash TEXT UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_access_token ON sessions(access_token_jti);
CREATE INDEX idx_sessions_refresh_token ON sessions(refresh_token_hash);
CREATE INDEX idx_sessions_expires ON sessions(expires_at)
  WHERE expires_at > NOW();

-- Composite index for session cleanup
CREATE INDEX idx_sessions_expired ON sessions(expires_at, created_at)
  WHERE expires_at <= NOW();
```

**Index Rationale**:
- `idx_sessions_user`: List user's active sessions
- `idx_sessions_access_token`: Token validation (frequent queries)
- `idx_sessions_refresh_token`: Refresh token lookup
- `idx_sessions_expires`: Active sessions only (partial index)
- `idx_sessions_expired`: Cleanup of expired sessions

#### Policies Table

```sql
-- Table definition
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    rego_code TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_policies_name ON policies(name);
CREATE INDEX idx_policies_active ON policies(is_active) WHERE is_active = true;
CREATE INDEX idx_policies_created_by ON policies(created_by);
CREATE INDEX idx_policies_version ON policies(name, version DESC);
```

### TimescaleDB Hypertable Indexes

#### Audit Events Hypertable

```sql
-- Create hypertable
CREATE TABLE audit_events (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    event_id UUID DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    user_id UUID,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    action VARCHAR(100),
    status VARCHAR(50),
    ip_address INET,
    details JSONB,
    PRIMARY KEY (time, event_id)
);

-- Convert to hypertable (1-day chunks)
SELECT create_hypertable('audit_events', 'time', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_audit_events_user ON audit_events(user_id, time DESC);
CREATE INDEX idx_audit_events_type ON audit_events(event_type, time DESC);
CREATE INDEX idx_audit_events_status ON audit_events(status, time DESC);
CREATE INDEX idx_audit_events_resource ON audit_events(resource_type, resource_id, time DESC);

-- GIN index for JSONB details
CREATE INDEX idx_audit_events_details ON audit_events USING GIN(details);
```

**Hypertable Configuration**:
- **Chunk Interval**: 1 day (balances query performance and chunk management)
- **Retention Policy**: 90 days (automatic deletion of old chunks)
- **Compression**: Enable after 7 days

```sql
-- Add retention policy (90 days)
SELECT add_retention_policy('audit_events', INTERVAL '90 days');

-- Add compression policy (compress chunks older than 7 days)
ALTER TABLE audit_events SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'event_type, user_id',
  timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('audit_events', INTERVAL '7 days');
```

#### Policy Evaluations Hypertable

```sql
-- Create hypertable
CREATE TABLE policy_evaluations (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    evaluation_id UUID DEFAULT uuid_generate_v4(),
    policy_name VARCHAR(255),
    user_id UUID,
    action VARCHAR(100),
    resource VARCHAR(255),
    decision BOOLEAN,
    cache_hit BOOLEAN,
    duration_ms INTEGER,
    PRIMARY KEY (time, evaluation_id)
);

-- Convert to hypertable (1-hour chunks for high volume)
SELECT create_hypertable('policy_evaluations', 'time', chunk_time_interval => INTERVAL '1 hour');

-- Indexes
CREATE INDEX idx_policy_evals_user ON policy_evaluations(user_id, time DESC);
CREATE INDEX idx_policy_evals_policy ON policy_evaluations(policy_name, time DESC);
CREATE INDEX idx_policy_evals_decision ON policy_evaluations(decision, time DESC);

-- Continuous aggregate for hourly statistics
CREATE MATERIALIZED VIEW hourly_policy_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS hour,
    policy_name,
    COUNT(*) AS total_evaluations,
    SUM(CASE WHEN decision THEN 1 ELSE 0 END) AS allowed,
    SUM(CASE WHEN NOT decision THEN 1 ELSE 0 END) AS denied,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
    AVG(duration_ms) AS avg_duration_ms,
    MAX(duration_ms) AS max_duration_ms
FROM policy_evaluations
GROUP BY hour, policy_name;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('hourly_policy_stats',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### Index Maintenance

#### Automatic Index Maintenance

```sql
-- Enable autovacuum (should be on by default)
ALTER TABLE users SET (autovacuum_enabled = true);
ALTER TABLE servers SET (autovacuum_enabled = true);
ALTER TABLE sessions SET (autovacuum_enabled = true);

-- Aggressive autovacuum for high-write tables
ALTER TABLE sessions SET (
    autovacuum_vacuum_scale_factor = 0.05,  -- Vacuum when 5% changed
    autovacuum_analyze_scale_factor = 0.02  -- Analyze when 2% changed
);
```

#### Manual Index Maintenance

```sql
-- Reindex bloated indexes (run during maintenance window)
REINDEX INDEX CONCURRENTLY idx_users_username;
REINDEX INDEX CONCURRENTLY idx_servers_tags;

-- Reindex entire table
REINDEX TABLE CONCURRENTLY users;

-- Vacuum and analyze
VACUUM ANALYZE users;
VACUUM ANALYZE servers;
VACUUM ANALYZE sessions;
```

#### Index Health Monitoring

```sql
-- Check index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Find unused indexes (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexname NOT LIKE '%pkey%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check index usage ratio
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    CASE
        WHEN idx_scan > 0 THEN ROUND((idx_tup_read::numeric / idx_scan), 2)
        ELSE 0
    END AS avg_tuples_per_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

---

## Query Optimization

### Query Analysis Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Query Optimization Workflow                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  1. Identify Slow   │
                    │     Queries         │
                    │  (pg_stat_statements)│
                    └──────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  2. Analyze Query   │
                    │     Plan            │
                    │  (EXPLAIN ANALYZE)  │
                    └──────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  3. Apply           │
                    │     Optimization    │
                    │  (Index/Rewrite)    │
                    └──────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  4. Verify          │
                    │     Improvement     │
                    │  (Re-run EXPLAIN)   │
                    └──────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  5. Monitor in      │
                    │     Production      │
                    └─────────────────────┘
```

### Enable Query Statistics

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure in postgresql.conf
-- shared_preload_libraries = 'pg_stat_statements'
-- pg_stat_statements.track = all
-- pg_stat_statements.max = 10000
```

### Identify Slow Queries

```sql
-- Top 10 slowest queries by total time
SELECT
    query,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
    ROUND(max_exec_time::numeric, 2) AS max_time_ms,
    ROUND((100 * total_exec_time / SUM(total_exec_time) OVER ())::numeric, 2) AS percent_total
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 10;

-- Queries with high mean execution time
SELECT
    query,
    calls,
    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
    ROUND(stddev_exec_time::numeric, 2) AS stddev_time_ms
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- > 100ms
  AND calls > 100           -- Called frequently
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Reset statistics
SELECT pg_stat_statements_reset();
```

### Query Plan Analysis

```sql
-- EXPLAIN ANALYZE (actual execution)
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT u.username, COUNT(s.id) AS server_count
FROM users u
LEFT JOIN servers s ON s.owner_id = u.id
WHERE u.is_active = true
GROUP BY u.id, u.username
ORDER BY server_count DESC
LIMIT 10;

-- Example output analysis:
-- ✓ Good: "Index Scan using idx_users_active"
-- ✗ Bad: "Seq Scan on users" (missing index)
-- ✓ Good: "Nested Loop" with small result set
-- ✗ Bad: "Hash Join" with full table scan
```

### Common Query Optimizations

#### 1. Use Indexes Effectively

**Bad: Missing WHERE clause index**
```sql
-- Slow: Full table scan
SELECT * FROM servers WHERE name LIKE '%prod%';

-- Fast: Use trigram index
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_servers_name_trgm ON servers USING GIN(name gin_trgm_ops);

SELECT * FROM servers WHERE name LIKE '%prod%';
```

**Bad: Function prevents index usage**
```sql
-- Slow: Function on column prevents index
SELECT * FROM users WHERE LOWER(email) = 'user@example.com';

-- Fast: Functional index
CREATE INDEX idx_users_email_lower ON users(LOWER(email));

SELECT * FROM users WHERE LOWER(email) = 'user@example.com';
```

#### 2. Optimize Joins

**Bad: Joining on unindexed columns**
```sql
-- Slow: No index on servers.owner_id
SELECT u.username, s.name
FROM users u
JOIN servers s ON s.owner_id = u.id;

-- Fast: Add index
CREATE INDEX idx_servers_owner ON servers(owner_id);
```

**Bad: Unnecessary joins**
```sql
-- Slow: Join just to check existence
SELECT u.*
FROM users u
JOIN sessions s ON s.user_id = u.id
WHERE u.is_active = true;

-- Fast: Use EXISTS
SELECT u.*
FROM users u
WHERE u.is_active = true
  AND EXISTS (SELECT 1 FROM sessions WHERE user_id = u.id);
```

#### 3. Optimize Aggregations

**Bad: COUNT(*) on large table**
```sql
-- Slow: Full table scan
SELECT COUNT(*) FROM audit_events;

-- Fast: Use approximate count
SELECT reltuples::bigint AS approximate_count
FROM pg_class
WHERE relname = 'audit_events';
```

**Bad: Multiple aggregations in subqueries**
```sql
-- Slow: Multiple scans
SELECT
    u.username,
    (SELECT COUNT(*) FROM servers WHERE owner_id = u.id) AS server_count,
    (SELECT COUNT(*) FROM sessions WHERE user_id = u.id) AS session_count
FROM users u;

-- Fast: Single scan with JOINs
SELECT
    u.username,
    COUNT(DISTINCT s.id) AS server_count,
    COUNT(DISTINCT sess.id) AS session_count
FROM users u
LEFT JOIN servers s ON s.owner_id = u.id
LEFT JOIN sessions sess ON sess.user_id = u.id
GROUP BY u.id, u.username;
```

#### 4. Optimize LIMIT and OFFSET

**Bad: Large OFFSET**
```sql
-- Slow: Skips 10,000 rows
SELECT * FROM servers
ORDER BY created_at DESC
LIMIT 20 OFFSET 10000;

-- Fast: Keyset pagination
SELECT * FROM servers
WHERE created_at < '2025-11-01'  -- Last value from previous page
ORDER BY created_at DESC
LIMIT 20;
```

#### 5. Use Partial Indexes

**Bad: Index includes inactive records**
```sql
-- Large index includes is_active = false rows
CREATE INDEX idx_servers_all ON servers(is_active);

-- Better: Partial index for active only
CREATE INDEX idx_servers_active ON servers(is_active)
  WHERE is_active = true;
```

#### 6. Optimize JSONB Queries

**Bad: Extract then filter**
```sql
-- Slow: Extracts all values first
SELECT * FROM servers
WHERE (metadata->>'environment') = 'production';

-- Fast: Use JSONB operators with GIN index
CREATE INDEX idx_servers_metadata ON servers USING GIN(metadata);

SELECT * FROM servers
WHERE metadata @> '{"environment": "production"}'::jsonb;
```

### Query Rewrite Examples

#### Example 1: User Authentication Query

**Original (Slow)**:
```sql
SELECT * FROM users
WHERE LOWER(username) = LOWER('john.doe')
  AND is_active = true;
```

**Optimized**:
```sql
-- Add functional index
CREATE INDEX idx_users_username_lower ON users(LOWER(username));

-- Rewrite query
SELECT * FROM users
WHERE LOWER(username) = 'john.doe'  -- Already lowercase
  AND is_active = true;

-- Even better: Store username in lowercase
ALTER TABLE users ADD COLUMN username_lower VARCHAR(255)
  GENERATED ALWAYS AS (LOWER(username)) STORED;
CREATE INDEX idx_users_username_lower ON users(username_lower);

SELECT * FROM users WHERE username_lower = 'john.doe' AND is_active = true;
```

#### Example 2: Server Search Query

**Original (Slow)**:
```sql
SELECT * FROM servers
WHERE name LIKE '%production%'
   OR endpoint LIKE '%production%'
ORDER BY created_at DESC
LIMIT 20;
```

**Optimized**:
```sql
-- Add full-text search
ALTER TABLE servers ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(endpoint, ''))
  ) STORED;

CREATE INDEX idx_servers_search ON servers USING GIN(search_vector);

-- Rewrite query
SELECT * FROM servers
WHERE search_vector @@ to_tsquery('english', 'production')
ORDER BY created_at DESC
LIMIT 20;
```

#### Example 3: Audit Log Query

**Original (Slow)**:
```sql
SELECT * FROM audit_events
WHERE user_id = 'abc-123'
  AND time >= NOW() - INTERVAL '7 days'
ORDER BY time DESC;
```

**Optimized**:
```sql
-- Composite index with time first (for hypertable)
CREATE INDEX idx_audit_events_user_time ON audit_events(user_id, time DESC);

-- Query uses index efficiently
SELECT * FROM audit_events
WHERE user_id = 'abc-123'
  AND time >= NOW() - INTERVAL '7 days'
ORDER BY time DESC;

-- Even better: Use time_bucket for aggregations
SELECT
    time_bucket('1 hour', time) AS hour,
    COUNT(*) AS event_count,
    COUNT(DISTINCT event_type) AS event_types
FROM audit_events
WHERE user_id = 'abc-123'
  AND time >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour DESC;
```

---

## Connection Pooling

### Connection Pool Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Connection Pool Architecture                 │
└─────────────────────────────────────────────────────────────────┘

         Application Servers (4 pods × 25 connections = 100)
         ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
         │   Pod 1  │  │   Pod 2  │  │   Pod 3  │  │   Pod 4  │
         │  Pool:25 │  │  Pool:25 │  │  Pool:25 │  │  Pool:25 │
         └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
              │             │             │             │
              └──────────┬──┴─────┬───────┴──────────┬──┘
                         │        │                  │
                         ▼        ▼                  ▼
                    ┌────────────────────────────────────┐
                    │         PgBouncer (Optional)       │
                    │         Pool Mode: Transaction     │
                    │         Max Connections: 200       │
                    └──────────────────┬─────────────────┘
                                       │
                                       ▼
                    ┌────────────────────────────────────┐
                    │      PostgreSQL Database           │
                    │      max_connections = 200         │
                    │      Reserved: 20 (admin)          │
                    │      Available: 180 (apps)         │
                    └────────────────────────────────────┘
```

### Application-Level Connection Pooling (SQLAlchemy)

**Configuration** (`src/sark/db.py`):
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Database URL
DATABASE_URL = "postgresql://sark:password@postgres:5432/sark"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,              # Normal pool size (per pod)
    max_overflow=10,           # Extra connections during spikes (total 30)
    pool_timeout=30,           # Wait 30s for connection before error
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Check connection health before use
    echo_pool=False,           # Set True for debugging
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30s query timeout
    }
)

# For read-heavy workloads, use separate read replica pool
READ_REPLICA_URL = "postgresql://sark:password@postgres-replica:5432/sark"

read_engine = create_engine(
    READ_REPLICA_URL,
    poolclass=QueuePool,
    pool_size=30,              # Larger pool for read replicas
    max_overflow=20,           # More overflow for reads
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)
```

**Environment Variables**:
```bash
# Primary database
DATABASE_URL=postgresql://sark:password@postgres:5432/sark
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# Audit database (TimescaleDB)
AUDIT_DATABASE_URL=postgresql://sark:password@timescaledb:5432/sark_audit
AUDIT_DATABASE_POOL_SIZE=10
AUDIT_DATABASE_MAX_OVERFLOW=5
```

### Connection Pool Sizing

**Formula**:
```
Total Connections = (Application Pods × Pool Size) + (Pods × Max Overflow) + Reserved

Example:
- Application Pods: 4
- Pool Size per Pod: 20
- Max Overflow per Pod: 10
- Reserved (admin, monitoring): 20

Maximum Connections = (4 × 20) + (4 × 10) + 20 = 140
PostgreSQL max_connections = 200 (provides 43% headroom)
```

**Recommended Sizing by Load**:

| Workload Type | Pool Size | Max Overflow | Total (4 pods) | PostgreSQL max_connections |
|---------------|-----------|--------------|----------------|---------------------------|
| **Low** (< 100 req/s) | 10 | 5 | 60 | 100 |
| **Medium** (100-500 req/s) | 20 | 10 | 120 | 200 |
| **High** (500-1000 req/s) | 30 | 15 | 180 | 250 |
| **Very High** (> 1000 req/s) | 40 | 20 | 240 | 300 |

### PgBouncer (Optional External Pooler)

**Use Cases**:
- Many application pods (> 10)
- Connection pooling for multiple applications
- Reduce database connection overhead
- Transaction-level pooling

**PgBouncer Configuration** (`pgbouncer.ini`):
```ini
[databases]
sark = host=postgres port=5432 dbname=sark
sark_audit = host=timescaledb port=5432 dbname=sark_audit

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pool configuration
pool_mode = transaction          # transaction, session, or statement
max_client_conn = 1000           # Max client connections
default_pool_size = 25           # Connections per pool
reserve_pool_size = 5            # Emergency connections
reserve_pool_timeout = 3         # Seconds to wait for reserve pool

# Connection limits
max_db_connections = 100         # Max connections to database
max_user_connections = 100       # Max connections per user

# Timeouts
server_idle_timeout = 600        # Close idle server connections after 10 min
server_lifetime = 3600           # Close server connections after 1 hour
server_connect_timeout = 15      # Connection timeout
query_timeout = 30               # Query timeout (30 seconds)

# Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
```

**Application Configuration with PgBouncer**:
```python
# Connect to PgBouncer instead of PostgreSQL directly
DATABASE_URL = "postgresql://sark:password@pgbouncer:6432/sark"

# Reduce pool size (PgBouncer handles pooling)
engine = create_engine(
    DATABASE_URL,
    pool_size=5,               # Small pool (PgBouncer pools)
    max_overflow=2,            # Minimal overflow
    pool_timeout=30,
    pool_pre_ping=True
)
```

### Connection Pool Monitoring

```sql
-- Current connections by state
SELECT
    state,
    COUNT(*) AS connections,
    MAX(EXTRACT(EPOCH FROM (NOW() - state_change))) AS max_duration_seconds
FROM pg_stat_activity
WHERE datname = 'sark'
GROUP BY state;

-- Connection pool utilization
SELECT
    COUNT(*) AS active_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections,
    ROUND(100.0 * COUNT(*) / (SELECT setting::int FROM pg_settings WHERE name = 'max_connections'), 2) AS utilization_percent
FROM pg_stat_activity;

-- Connections by application
SELECT
    application_name,
    state,
    COUNT(*) AS connections
FROM pg_stat_activity
WHERE datname = 'sark'
GROUP BY application_name, state
ORDER BY connections DESC;

-- Long-running connections
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    NOW() - backend_start AS connection_age,
    NOW() - state_change AS state_age,
    query
FROM pg_stat_activity
WHERE datname = 'sark'
  AND state != 'idle'
  AND NOW() - state_change > INTERVAL '30 seconds'
ORDER BY state_change;
```

**Kill Idle Connections**:
```sql
-- Kill idle connections older than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'sark'
  AND state = 'idle'
  AND NOW() - state_change > INTERVAL '10 minutes';

-- Kill long-running queries (> 5 minutes)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'sark'
  AND state = 'active'
  AND NOW() - query_start > INTERVAL '5 minutes';
```

---

## PostgreSQL Configuration

### Critical Settings

**File**: `postgresql.conf`

```ini
# ===========================
# Memory Settings
# ===========================

# Total memory: 8 GB (example)
# Rule of thumb: 25% for shared_buffers, rest for OS cache

shared_buffers = 2GB                    # 25% of RAM (1-4 GB typical)
effective_cache_size = 6GB              # 75% of RAM (OS cache estimate)
work_mem = 16MB                         # Per-operation memory (sort, hash)
maintenance_work_mem = 512MB            # VACUUM, CREATE INDEX memory
temp_buffers = 8MB                      # Temp table memory

# ===========================
# Query Planner
# ===========================

random_page_cost = 1.1                  # SSD: 1.1, HDD: 4.0
effective_io_concurrency = 200          # SSD: 200, HDD: 2
default_statistics_target = 100         # Statistics sampling (default: 100)

# ===========================
# Write Ahead Log (WAL)
# ===========================

wal_level = replica                     # For replication
max_wal_size = 4GB                      # Checkpoint threshold
min_wal_size = 1GB                      # Minimum WAL size
checkpoint_completion_target = 0.9      # Spread checkpoint I/O
wal_buffers = 16MB                      # WAL buffer size

# ===========================
# Connection Settings
# ===========================

max_connections = 200                   # Maximum connections
superuser_reserved_connections = 3      # Reserved for superuser
shared_preload_libraries = 'pg_stat_statements'

# ===========================
# Logging
# ===========================

logging_collector = on
log_directory = '/var/log/postgresql'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB

log_min_duration_statement = 1000       # Log queries > 1 second
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0                      # Log all temp files
log_autovacuum_min_duration = 0         # Log all autovacuum activity

# ===========================
# Autovacuum
# ===========================

autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min               # Check frequency
autovacuum_vacuum_scale_factor = 0.1    # Vacuum when 10% changed
autovacuum_analyze_scale_factor = 0.05  # Analyze when 5% changed

# ===========================
# Performance Optimization
# ===========================

# Enable parallel query execution
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_worker_processes = 8

# JIT compilation (PostgreSQL 11+)
jit = on
```

### Apply Configuration

```bash
# Edit configuration
sudo nano /var/lib/postgresql/data/postgresql.conf

# Reload configuration (no downtime)
sudo -u postgres psql -c "SELECT pg_reload_conf();"

# Restart PostgreSQL (required for some settings)
sudo systemctl restart postgresql

# Verify settings
sudo -u postgres psql -c "SHOW shared_buffers;"
sudo -u postgres psql -c "SHOW max_connections;"
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
  namespace: production
data:
  postgresql.conf: |
    shared_buffers = 2GB
    effective_cache_size = 6GB
    work_mem = 16MB
    maintenance_work_mem = 512MB
    max_connections = 200
    wal_level = replica
    max_wal_size = 4GB
    checkpoint_completion_target = 0.9
    random_page_cost = 1.1
    effective_io_concurrency = 200
    log_min_duration_statement = 1000
    shared_preload_libraries = 'pg_stat_statements'
```

---

## TimescaleDB Optimization

### Hypertable Configuration

```sql
-- Create hypertable with optimal chunk interval
CREATE TABLE metrics (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    metric_name VARCHAR(100),
    value DOUBLE PRECISION
);

-- 1-day chunks for moderate data volume
SELECT create_hypertable('metrics', 'time', chunk_time_interval => INTERVAL '1 day');

-- 1-hour chunks for high-volume data
SELECT create_hypertable('high_volume_metrics', 'time', chunk_time_interval => INTERVAL '1 hour');

-- 7-day chunks for low-volume data
SELECT create_hypertable('low_volume_metrics', 'time', chunk_time_interval => INTERVAL '7 days');
```

### Compression

```sql
-- Enable compression (reduces storage by 90-95%)
ALTER TABLE audit_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'event_type, user_id',  -- Group by these
    timescaledb.compress_orderby = 'time DESC'                -- Order within groups
);

-- Add compression policy (compress after 7 days)
SELECT add_compression_policy('audit_events', INTERVAL '7 days');

-- Manually compress specific chunk
SELECT compress_chunk('_timescaledb_internal._hyper_1_1_chunk');

-- Check compression status
SELECT
    chunk_schema,
    chunk_name,
    pg_size_pretty(before_compression_total_bytes) AS before,
    pg_size_pretty(after_compression_total_bytes) AS after,
    ROUND(100 - (after_compression_total_bytes::numeric / before_compression_total_bytes * 100), 2) AS compression_ratio
FROM timescaledb_information.chunk_compression_stats
ORDER BY before_compression_total_bytes DESC;
```

### Data Retention

```sql
-- Add retention policy (delete data older than 90 days)
SELECT add_retention_policy('audit_events', INTERVAL '90 days');

-- Manually drop old chunks
SELECT drop_chunks('audit_events', INTERVAL '90 days');

-- Check retention policy
SELECT * FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention';
```

### Continuous Aggregates

```sql
-- Create continuous aggregate for dashboard queries
CREATE MATERIALIZED VIEW hourly_api_metrics
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS hour,
    COUNT(*) AS total_requests,
    AVG(duration_ms) AS avg_duration,
    MAX(duration_ms) AS max_duration,
    SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) AS error_count
FROM api_logs
GROUP BY hour;

-- Add refresh policy
SELECT add_continuous_aggregate_policy('hourly_api_metrics',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Query continuous aggregate (fast!)
SELECT * FROM hourly_api_metrics
WHERE hour >= NOW() - INTERVAL '7 days'
ORDER BY hour DESC;
```

---

## Performance Monitoring

### Key Metrics Dashboard

```sql
-- Database size
SELECT
    datname,
    pg_size_pretty(pg_database_size(datname)) AS size
FROM pg_database
WHERE datname IN ('sark', 'sark_audit');

-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Cache hit ratio (should be > 95%)
SELECT
    'Index Hit Rate' AS metric,
    ROUND(100.0 * idx_blks_hit / NULLIF(idx_blks_hit + idx_blks_read, 0), 2) AS hit_ratio
FROM pg_statio_user_indexes
UNION ALL
SELECT
    'Table Hit Rate',
    ROUND(100.0 * heap_blks_hit / NULLIF(heap_blks_hit + heap_blks_read, 0), 2)
FROM pg_statio_user_tables;

-- Transaction throughput
SELECT
    datname,
    xact_commit AS commits,
    xact_rollback AS rollbacks,
    xact_commit + xact_rollback AS total_transactions,
    ROUND(100.0 * xact_rollback / NULLIF(xact_commit + xact_rollback, 0), 2) AS rollback_percent
FROM pg_stat_database
WHERE datname = 'sark';
```

### Prometheus Metrics

**PostgreSQL Exporter** (`docker-compose.yml`):
```yaml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter:latest
  environment:
    DATA_SOURCE_NAME: "postgresql://exporter:password@postgres:5432/sark?sslmode=disable"
  ports:
    - "9187:9187"
```

**Key Prometheus Queries**:
```promql
# Connection pool utilization
100 * pg_stat_activity_count / pg_settings_max_connections

# Cache hit ratio
100 * rate(pg_stat_database_blks_hit[5m]) / (rate(pg_stat_database_blks_hit[5m]) + rate(pg_stat_database_blks_read[5m]))

# Query duration p95
histogram_quantile(0.95, rate(pg_stat_statements_mean_time_bucket[5m]))

# Active connections
pg_stat_activity_count{state="active"}

# Transaction rate
rate(pg_stat_database_xact_commit[5m])
```

---

## Backup and Maintenance

### Backup Strategy

```bash
# Daily full backup
pg_dump -h postgres -U sark -Fc sark > /backups/sark-$(date +%Y%m%d).dump

# Continuous archiving (Point-in-Time Recovery)
# In postgresql.conf:
# archive_mode = on
# archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'

# Base backup
pg_basebackup -h postgres -U replication -D /backups/base -Fp -Xs -P

# Restore from backup
pg_restore -h postgres -U sark -d sark -Fc /backups/sark-20251122.dump
```

### Routine Maintenance

```bash
# Weekly VACUUM ANALYZE
sudo -u postgres psql -d sark -c "VACUUM ANALYZE;"

# Monthly REINDEX
sudo -u postgres psql -d sark -c "REINDEX DATABASE sark;"

# Update statistics
sudo -u postgres psql -d sark -c "ANALYZE;"
```

---

## Best Practices

### Development Best Practices

1. **Always use parameterized queries** (prevent SQL injection)
2. **Add indexes before loading large datasets**
3. **Use EXPLAIN ANALYZE for new queries**
4. **Avoid SELECT * (specify columns)**
5. **Use connection pooling**
6. **Set query timeouts**
7. **Monitor query performance in production**

### Production Best Practices

1. **Set max_connections appropriately**
2. **Configure connection pooling (PgBouncer or SQLAlchemy)**
3. **Enable pg_stat_statements**
4. **Monitor cache hit ratio (> 95%)**
5. **Schedule regular VACUUM and ANALYZE**
6. **Configure automated backups**
7. **Set up replication for high availability**
8. **Use read replicas for read-heavy workloads**
9. **Implement data retention policies**
10. **Monitor disk space and I/O**

---

## Summary

This guide covers comprehensive database optimization for SARK:

- **Indexing**: Strategic indexes on all key columns, partial indexes, GIN indexes for JSONB
- **Query Optimization**: EXPLAIN ANALYZE, query rewriting, avoiding common pitfalls
- **Connection Pooling**: SQLAlchemy pooling, PgBouncer, proper sizing
- **PostgreSQL Configuration**: Memory, WAL, autovacuum, logging
- **TimescaleDB**: Hypertables, compression, retention, continuous aggregates
- **Monitoring**: pg_stat_statements, Prometheus metrics, performance dashboards

Following these practices will ensure SARK's database performs optimally under production workloads.
