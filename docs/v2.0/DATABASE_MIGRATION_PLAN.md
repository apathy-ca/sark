# SARK v2.0: Database Migration Plan

**Version:** 1.0
**Status:** Planning document
**Created:** November 28, 2025

---

## Overview

Database schema changes needed for SARK v2.0 to support protocol abstraction, federation, and cost attribution.

**Migration Strategy:** Clean migration (no production users to worry about)

---

## Key Schema Changes

### 1. Resources Table (Replaces `mcp_servers`)

**v2.0 Schema:**
```sql
CREATE TABLE resources (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    protocol VARCHAR NOT NULL,        -- 'mcp', 'http', 'grpc'
    endpoint VARCHAR NOT NULL,        -- Generic endpoint
    sensitivity_level VARCHAR NOT NULL DEFAULT 'medium',
    metadata JSONB DEFAULT '{}',      -- Protocol-specific data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resources_protocol ON resources(protocol);
CREATE INDEX idx_resources_sensitivity ON resources(sensitivity_level);
```

### 2. Capabilities Table (Replaces `mcp_tools`)

**v2.0 Schema:**
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
```

### 3. Enhanced Audit Events

**New Columns:**
```sql
ALTER TABLE audit_events ADD COLUMN principal_org VARCHAR;           -- Federation
ALTER TABLE audit_events ADD COLUMN resource_protocol VARCHAR;       -- Protocol type
ALTER TABLE audit_events ADD COLUMN capability_id VARCHAR;
ALTER TABLE audit_events ADD COLUMN correlation_id VARCHAR;          -- Cross-org tracking
ALTER TABLE audit_events ADD COLUMN source_node VARCHAR;             -- Federation
ALTER TABLE audit_events ADD COLUMN target_node VARCHAR;             -- Federation
ALTER TABLE audit_events ADD COLUMN estimated_cost DECIMAL(10,2);    -- Cost tracking
ALTER TABLE audit_events ADD COLUMN actual_cost DECIMAL(10,2);       -- Cost tracking

CREATE INDEX idx_audit_correlation ON audit_events(correlation_id);
```

### 4. Federation Nodes (NEW)

```sql
CREATE TABLE federation_nodes (
    id VARCHAR PRIMARY KEY,
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
```

### 5. Cost Tracking (NEW)

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

-- TimescaleDB hypertable
SELECT create_hypertable('cost_tracking', 'timestamp', if_not_exists => TRUE);
```

### 6. Principal Budgets (NEW)

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
```

---

## Migration Script Location

Alembic migration will be created at:
```
alembic/versions/005_v2_schema.py
```

---

## Data Migration

### MCP Servers → Resources

```sql
INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
SELECT 
    id,
    name,
    'mcp' as protocol,
    command as endpoint,
    COALESCE(sensitivity_level, 'medium'),
    jsonb_build_object(
        'transport', transport,
        'command', command,
        'args', args,
        'env', env
    ) || COALESCE(metadata, '{}'::jsonb),
    created_at,
    updated_at
FROM mcp_servers;
```

### MCP Tools → Capabilities

```sql
INSERT INTO capabilities (id, resource_id, name, description, input_schema, output_schema, sensitivity_level, metadata)
SELECT 
    id,
    server_id as resource_id,
    name,
    description,
    COALESCE(input_schema, '{}'::jsonb),
    '{}'::jsonb as output_schema,
    COALESCE(sensitivity_level, 'medium'),
    COALESCE(metadata, '{}'::jsonb)
FROM mcp_tools;
```

---

## Rollback Plan

Since there are no production users:
- Keep v1.x tables for reference during development
- Drop them once v2.0 is stable
- No need for complex rollback procedures

---

## Testing Checklist

- [ ] Create migration script
- [ ] Test migration on dev database
- [ ] Verify all data migrated correctly
- [ ] Test new schema with v2.0 code
- [ ] Verify indexes are created
- [ ] Test TimescaleDB hypertables
- [ ] Verify foreign key constraints
- [ ] Test cascade deletes

---

**Document Version:** 1.0
**Status:** Planning document for v2.0 implementation