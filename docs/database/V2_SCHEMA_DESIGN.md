# SARK v2.0: Database Schema Design

**Version:** 1.0
**Author:** ENGINEER-6 (Database & Migration Lead)
**Status:** Implementation Document
**Created:** December 2, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Schema Evolution Strategy](#schema-evolution-strategy)
4. [Core Tables](#core-tables)
5. [Federation Tables](#federation-tables)
6. [Cost Tracking Tables](#cost-tracking-tables)
7. [Polymorphic Query Patterns](#polymorphic-query-patterns)
8. [Index Strategy](#index-strategy)
9. [Performance Considerations](#performance-considerations)
10. [Migration Path](#migration-path)

---

## Overview

SARK v2.0 transforms from an MCP-specific governance platform to a **protocol-agnostic** governance platform. This requires a fundamental database schema redesign to support:

- **Multiple Protocols**: MCP, HTTP/REST, gRPC, and future protocols
- **Polymorphic Resources**: Generic resource model supporting any protocol
- **Federation**: Cross-organization governance with mTLS trust
- **Cost Attribution**: Per-principal cost tracking and budgeting
- **Performance**: Efficient queries across protocol boundaries

### Key Changes from v1.x

| v1.x Concept | v2.0 Concept | Rationale |
|--------------|--------------|-----------|
| `mcp_servers` | `resources` | Generic resource abstraction |
| `mcp_tools` | `capabilities` | Generic capability abstraction |
| Protocol-specific columns | `metadata` JSONB | Flexible protocol storage |
| N/A | `federation_nodes` | Cross-org trust |
| N/A | `cost_tracking` | Budget management |
| N/A | `principal_budgets` | Cost limits |

---

## Design Principles

### 1. Protocol Agnosticism

All protocol-specific details are stored in JSONB `metadata` columns, allowing the core schema to remain stable as new protocols are added.

```sql
-- ✅ Good: Protocol-agnostic
SELECT * FROM resources WHERE protocol = 'grpc' AND name LIKE '%auth%';

-- ❌ Bad: Protocol-specific columns
SELECT * FROM resources WHERE grpc_host = 'auth.example.com';
```

### 2. Backward Compatibility

v1.x tables (`mcp_servers`, `mcp_tools`) will remain during the transition period:

- **Phase 1**: Create new v2.0 tables alongside v1.x tables
- **Phase 2**: Dual-write to both schemas during migration
- **Phase 3**: Deprecate v1.x tables after all data is migrated
- **Phase 4**: Drop v1.x tables in v2.1

### 3. Audit Completeness

All cross-organization access MUST be logged by both source and target nodes with correlation IDs for forensic analysis.

### 4. Performance at Scale

- TimescaleDB hypertables for time-series data (audit, cost)
- Strategic B-tree and GIN indexes
- Materialized views for complex aggregations
- Partitioning by timestamp for long-term storage

---

## Schema Evolution Strategy

### Phase 1: Foundation (Week 1)

Create new v2.0 tables:
- `resources`
- `capabilities`
- `federation_nodes`
- `cost_tracking`
- `principal_budgets`

Enhance existing tables:
- Add federation columns to `audit_events`

### Phase 2: Dual-Write (Weeks 2-3)

Application code writes to both v1.x and v2.0 tables during transition.

### Phase 3: Data Migration (Weeks 4-5)

Migrate all v1.x data to v2.0 schema using `scripts/migrate_v1_to_v2.py`.

### Phase 4: Cleanup (v2.1+)

Drop v1.x tables once all systems are migrated.

---

## Core Tables

### resources

Universal table for all governed entities (MCP servers, REST APIs, gRPC services, etc.).

```sql
CREATE TABLE resources (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    protocol VARCHAR NOT NULL,
    endpoint VARCHAR NOT NULL,
    sensitivity_level VARCHAR NOT NULL DEFAULT 'medium',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resources_protocol ON resources(protocol);
CREATE INDEX idx_resources_sensitivity ON resources(sensitivity_level);
CREATE INDEX idx_resources_name ON resources(name);
CREATE INDEX idx_resources_metadata_gin ON resources USING gin(metadata);
```

#### Column Details

| Column | Type | Description | Examples |
|--------|------|-------------|----------|
| `id` | VARCHAR | Unique resource identifier | `mcp-filesystem-1`, `https://api.github.com` |
| `name` | VARCHAR | Human-readable name | `GitHub API`, `Database Server` |
| `protocol` | VARCHAR | Protocol identifier | `mcp`, `http`, `grpc` |
| `endpoint` | VARCHAR | Generic endpoint/location | `npx -y @mcp/server-fs`, `https://api.example.com` |
| `sensitivity_level` | VARCHAR | Data classification | `low`, `medium`, `high`, `critical` |
| `metadata` | JSONB | Protocol-specific details | See examples below |
| `created_at` | TIMESTAMPTZ | Creation timestamp | |
| `updated_at` | TIMESTAMPTZ | Last modification timestamp | |

#### Metadata Examples

**MCP Resource:**
```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem"],
  "env": {"ROOT_PATH": "/data"},
  "mcp_version": "2024-11-05",
  "capabilities": ["tools", "resources"]
}
```

**HTTP Resource:**
```json
{
  "base_url": "https://api.github.com",
  "openapi_spec": "https://api.github.com/openapi.json",
  "auth_type": "bearer",
  "rate_limit": 5000
}
```

**gRPC Resource:**
```json
{
  "host": "grpc.example.com",
  "port": 50051,
  "tls_enabled": true,
  "reflection_enabled": true,
  "services": ["user.UserService", "auth.AuthService"]
}
```

### capabilities

Universal table for all executable capabilities (MCP tools, HTTP endpoints, gRPC methods, etc.).

```sql
CREATE TABLE capabilities (
    id VARCHAR PRIMARY KEY,
    resource_id VARCHAR NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    input_schema JSONB DEFAULT '{}',
    output_schema JSONB DEFAULT '{}',
    sensitivity_level VARCHAR NOT NULL DEFAULT 'medium',
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_capabilities_resource ON capabilities(resource_id);
CREATE INDEX idx_capabilities_name ON capabilities(name);
CREATE INDEX idx_capabilities_sensitivity ON capabilities(sensitivity_level);
CREATE INDEX idx_capabilities_metadata_gin ON capabilities USING gin(metadata);
```

#### Column Details

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR | Unique capability identifier |
| `resource_id` | VARCHAR | Parent resource (FK) |
| `name` | VARCHAR | Capability name |
| `description` | TEXT | Human-readable description |
| `input_schema` | JSONB | JSON Schema for inputs |
| `output_schema` | JSONB | JSON Schema for outputs |
| `sensitivity_level` | VARCHAR | Data classification |
| `metadata` | JSONB | Protocol-specific metadata |

#### Metadata Examples

**MCP Tool:**
```json
{
  "tool_type": "mcp",
  "requires_approval": false,
  "timeout_seconds": 30
}
```

**HTTP Endpoint:**
```json
{
  "http_method": "POST",
  "http_path": "/repos/{owner}/{repo}/issues",
  "content_type": "application/json"
}
```

**gRPC Method:**
```json
{
  "service": "user.UserService",
  "method": "CreateUser",
  "stream_type": "unary"
}
```

---

## Federation Tables

### federation_nodes

Trusted SARK nodes for cross-organization governance.

```sql
CREATE TABLE federation_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    endpoint VARCHAR NOT NULL,
    trust_anchor_cert TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    trusted_since TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rate_limit_per_hour INTEGER DEFAULT 10000,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_federation_nodes_node_id ON federation_nodes(node_id);
CREATE INDEX idx_federation_nodes_enabled ON federation_nodes(enabled);
```

#### Column Details

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Internal unique ID |
| `node_id` | VARCHAR | External node identifier (e.g., `orgb.com`) |
| `name` | VARCHAR | Human-readable name |
| `endpoint` | VARCHAR | Federation API endpoint |
| `trust_anchor_cert` | TEXT | PEM-encoded CA certificate |
| `enabled` | BOOLEAN | Trust status (can be revoked) |
| `trusted_since` | TIMESTAMPTZ | Trust establishment time |
| `rate_limit_per_hour` | INTEGER | Max requests/hour from this node |
| `metadata` | JSONB | Additional trust metadata |

### Enhanced audit_events

Extend existing audit table for federation support.

```sql
-- New columns added via migration
ALTER TABLE audit_events
    ADD COLUMN principal_org VARCHAR,
    ADD COLUMN resource_protocol VARCHAR,
    ADD COLUMN capability_id VARCHAR,
    ADD COLUMN correlation_id VARCHAR,
    ADD COLUMN source_node VARCHAR,
    ADD COLUMN target_node VARCHAR,
    ADD COLUMN estimated_cost DECIMAL(10,2),
    ADD COLUMN actual_cost DECIMAL(10,2);

CREATE INDEX idx_audit_correlation ON audit_events(correlation_id);
CREATE INDEX idx_audit_principal_org ON audit_events(principal_org);
CREATE INDEX idx_audit_source_node ON audit_events(source_node);
```

#### New Column Details

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `principal_org` | VARCHAR | Principal's organization | `orga.com` |
| `resource_protocol` | VARCHAR | Protocol used | `mcp`, `http`, `grpc` |
| `capability_id` | VARCHAR | Capability executed | `cap-123` |
| `correlation_id` | VARCHAR | Cross-org correlation ID | `corr-uuid` |
| `source_node` | VARCHAR | Requesting node | `orga.com` |
| `target_node` | VARCHAR | Resource-owning node | `orgb.com` |
| `estimated_cost` | DECIMAL | Pre-execution cost estimate | `0.05` |
| `actual_cost` | DECIMAL | Post-execution actual cost | `0.047` |

---

## Cost Tracking Tables

### cost_tracking

Time-series cost data (TimescaleDB hypertable).

```sql
CREATE TABLE cost_tracking (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    principal_id VARCHAR NOT NULL,
    resource_id VARCHAR NOT NULL,
    capability_id VARCHAR NOT NULL,
    estimated_cost DECIMAL(10,2),
    actual_cost DECIMAL(10,2),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_cost_timestamp ON cost_tracking(timestamp DESC);
CREATE INDEX idx_cost_principal ON cost_tracking(principal_id);
CREATE INDEX idx_cost_resource ON cost_tracking(resource_id);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('cost_tracking', 'timestamp', if_not_exists => TRUE);
```

#### Column Details

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGSERIAL | Auto-incrementing ID |
| `timestamp` | TIMESTAMPTZ | Execution timestamp (partition key) |
| `principal_id` | VARCHAR | User/service executing |
| `resource_id` | VARCHAR | Resource accessed |
| `capability_id` | VARCHAR | Capability executed |
| `estimated_cost` | DECIMAL | Pre-execution estimate (USD) |
| `actual_cost` | DECIMAL | Actual cost (USD) |
| `metadata` | JSONB | Provider-specific details |

### principal_budgets

Per-principal cost limits and tracking.

```sql
CREATE TABLE principal_budgets (
    principal_id VARCHAR PRIMARY KEY,
    daily_budget DECIMAL(10,2),
    monthly_budget DECIMAL(10,2),
    daily_spent DECIMAL(10,2) DEFAULT 0,
    monthly_spent DECIMAL(10,2) DEFAULT 0,
    last_daily_reset TIMESTAMPTZ,
    last_monthly_reset TIMESTAMPTZ,
    currency VARCHAR DEFAULT 'USD',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_budgets_principal ON principal_budgets(principal_id);
```

---

## Polymorphic Query Patterns

### Query Resources by Protocol

```sql
-- Find all HTTP resources
SELECT r.*, COUNT(c.id) AS capability_count
FROM resources r
LEFT JOIN capabilities c ON c.resource_id = r.id
WHERE r.protocol = 'http'
GROUP BY r.id;
```

### Query High-Sensitivity Capabilities Across All Protocols

```sql
SELECT
    r.protocol,
    r.name AS resource_name,
    c.name AS capability_name,
    c.sensitivity_level
FROM capabilities c
JOIN resources r ON r.id = c.resource_id
WHERE c.sensitivity_level IN ('high', 'critical')
ORDER BY r.protocol, c.sensitivity_level DESC;
```

### Federation Audit Trail

```sql
-- Find all cross-org requests with correlation
SELECT
    a1.timestamp AS source_timestamp,
    a1.source_node,
    a1.target_node,
    a1.principal_id,
    a1.decision AS source_decision,
    a2.decision AS target_decision,
    a1.correlation_id
FROM audit_events a1
LEFT JOIN audit_events a2 ON a2.correlation_id = a1.correlation_id AND a2.source_node != a1.source_node
WHERE a1.correlation_id IS NOT NULL
ORDER BY a1.timestamp DESC;
```

### Cost Analysis by Protocol

```sql
-- Daily cost breakdown by protocol
SELECT
    DATE(ct.timestamp) AS date,
    r.protocol,
    COUNT(*) AS invocation_count,
    SUM(ct.actual_cost) AS total_cost,
    AVG(ct.actual_cost) AS avg_cost
FROM cost_tracking ct
JOIN capabilities c ON c.id = ct.capability_id
JOIN resources r ON r.id = c.resource_id
WHERE ct.timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(ct.timestamp), r.protocol
ORDER BY date DESC, total_cost DESC;
```

---

## Index Strategy

### B-tree Indexes (Equality & Range Queries)

```sql
-- resources
CREATE INDEX idx_resources_protocol ON resources(protocol);
CREATE INDEX idx_resources_sensitivity ON resources(sensitivity_level);
CREATE INDEX idx_resources_name ON resources(name);

-- capabilities
CREATE INDEX idx_capabilities_resource ON capabilities(resource_id);
CREATE INDEX idx_capabilities_name ON capabilities(name);
CREATE INDEX idx_capabilities_sensitivity ON capabilities(sensitivity_level);

-- audit_events (existing + new)
CREATE INDEX idx_audit_correlation ON audit_events(correlation_id);
CREATE INDEX idx_audit_principal_org ON audit_events(principal_org);
CREATE INDEX idx_audit_source_node ON audit_events(source_node);

-- cost_tracking
CREATE INDEX idx_cost_timestamp ON cost_tracking(timestamp DESC);
CREATE INDEX idx_cost_principal ON cost_tracking(principal_id);
```

### GIN Indexes (JSONB Containment Queries)

```sql
-- For metadata queries
CREATE INDEX idx_resources_metadata_gin ON resources USING gin(metadata);
CREATE INDEX idx_capabilities_metadata_gin ON capabilities USING gin(metadata);

-- Example queries enabled:
SELECT * FROM resources WHERE metadata @> '{"transport": "stdio"}';
SELECT * FROM capabilities WHERE metadata @> '{"http_method": "POST"}';
```

### Partial Indexes (Filtered Queries)

```sql
-- Only index enabled federation nodes
CREATE INDEX idx_federation_enabled ON federation_nodes(enabled) WHERE enabled = TRUE;

-- Only index recent cost data
CREATE INDEX idx_cost_recent ON cost_tracking(timestamp DESC)
WHERE timestamp >= NOW() - INTERVAL '90 days';
```

---

## Performance Considerations

### 1. JSONB Query Optimization

**Good:**
```sql
-- Use GIN index containment
SELECT * FROM resources WHERE metadata @> '{"protocol": "mcp"}';
```

**Bad:**
```sql
-- Requires full table scan
SELECT * FROM resources WHERE metadata->>'protocol' = 'mcp';
```

### 2. TimescaleDB Hypertables

Cost and audit data are time-series optimized:

```sql
-- Automatic time-based partitioning
SELECT create_hypertable('cost_tracking', 'timestamp');
SELECT create_hypertable('audit_events', 'timestamp', if_not_exists => TRUE);

-- Retention policy (optional)
SELECT add_retention_policy('cost_tracking', INTERVAL '365 days');
```

### 3. Materialized Views

For expensive aggregations:

```sql
CREATE MATERIALIZED VIEW mv_daily_cost_by_protocol AS
SELECT
    DATE(timestamp) AS date,
    r.protocol,
    COUNT(*) AS invocations,
    SUM(ct.actual_cost) AS total_cost
FROM cost_tracking ct
JOIN capabilities c ON c.id = ct.capability_id
JOIN resources r ON r.id = c.resource_id
GROUP BY DATE(timestamp), r.protocol;

-- Refresh daily
CREATE INDEX ON mv_daily_cost_by_protocol(date DESC);
```

### 4. Connection Pooling

Recommended settings for high-throughput:

```
max_connections = 200
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 16MB
```

---

## Migration Path

### Step 1: Create v2.0 Tables (Migration 006)

```bash
alembic upgrade head  # Creates resources, capabilities
```

### Step 2: Create Federation Tables (Migration 007)

```bash
alembic upgrade head  # Creates federation_nodes, cost_tracking, budgets
```

### Step 3: Migrate v1.x Data

```bash
python scripts/migrate_v1_to_v2.py --dry-run
python scripts/migrate_v1_to_v2.py --execute
```

### Step 4: Verify Data Integrity

```bash
pytest tests/migrations/test_migration_safety.py
```

### Step 5: Update Application Code

Switch from v1.x models to v2.0 models:

```python
# Old (v1.x)
from sark.models import MCPServer, MCPTool

# New (v2.0)
from sark.models.resource import Resource, Capability
```

### Step 6: Drop v1.x Tables (v2.1+)

Once all systems migrated:

```sql
DROP TABLE mcp_tools;
DROP TABLE mcp_servers;
```

---

## Testing Strategy

### 1. Migration Safety Tests

```python
def test_v1_to_v2_migration_preserves_data():
    """Ensure all v1.x data appears in v2.0 schema"""
    assert count(mcp_servers) == count(resources.filter(protocol='mcp'))
    assert count(mcp_tools) == count(capabilities.filter(resource.protocol='mcp'))

def test_no_data_loss():
    """Verify every v1.x record has v2.0 equivalent"""
    for server in mcp_servers:
        assert exists(resources.filter(id=server.id))
```

### 2. Performance Tests

```python
def test_polymorphic_query_performance():
    """Ensure protocol-agnostic queries perform well"""
    start = time.time()
    results = db.query(Resource).filter(Resource.protocol.in_(['mcp', 'http', 'grpc'])).all()
    duration = time.time() - start
    assert duration < 0.1  # < 100ms for 10K resources
```

### 3. Index Coverage Tests

```python
def test_indexes_used():
    """Verify queries use indexes, not seq scans"""
    plan = db.execute("EXPLAIN SELECT * FROM resources WHERE protocol = 'mcp'")
    assert 'Index Scan' in str(plan)
    assert 'Seq Scan' not in str(plan)
```

---

## Summary

SARK v2.0 database schema provides:

✅ **Protocol Agnosticism**: Single schema for all protocols
✅ **Federation Support**: Cross-org trust and auditing
✅ **Cost Attribution**: Per-principal budgeting and tracking
✅ **Performance**: Strategic indexing and time-series optimization
✅ **Backward Compatibility**: Smooth migration from v1.x
✅ **Future-Proof**: JSONB metadata allows protocol evolution

### Key Metrics

- **Tables**: 6 core tables (resources, capabilities, federation_nodes, cost_tracking, principal_budgets, audit_events)
- **Indexes**: 20+ strategic indexes (B-tree, GIN, partial)
- **Migration Scripts**: 2 Alembic migrations (006, 007)
- **Data Migration**: Automated v1.x → v2.0 script
- **Performance Target**: <100ms adapter overhead

---

**Document Status:** ✅ Complete
**Next Steps:**
1. Create migration 006 (protocol adapter support)
2. Create migration 007 (federation support)
3. Implement data migration script
4. Write migration safety tests

**Questions/Feedback:** Contact ENGINEER-6 (Database & Migration Lead)
