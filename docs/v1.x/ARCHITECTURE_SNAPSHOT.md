# SARK v1.x Architecture Snapshot

**Version:** 1.0/1.1
**Purpose:** Document current architecture before v2.0 transformation
**Created:** November 28, 2025

---

## Overview

This document captures SARK's architecture as of v1.x (MCP-focused) to provide a baseline for understanding v2.0 changes.

---

## Current Architecture (v1.x)

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  API Routers                                                │
│  ├─ /api/v1/servers      (MCP server management)           │
│  ├─ /api/v1/tools        (MCP tool discovery)              │
│  ├─ /api/v1/sessions     (Session management)              │
│  ├─ /api/v1/policy       (Policy evaluation)               │
│  ├─ /api/v1/audit        (Audit queries)                   │
│  └─ /api/v1/auth         (Authentication)                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Core Services                                              │
│  ├─ MCP Discovery Service    (Find MCP servers)            │
│  ├─ Policy Service           (OPA integration)             │
│  ├─ Audit Service            (TimescaleDB logging)         │
│  ├─ Session Service          (Session tracking)            │
│  └─ Auth Service             (Multi-provider auth)         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Data Models (SQLAlchemy)                                   │
│  ├─ MCPServer               (MCP server metadata)          │
│  ├─ MCPTool                 (MCP tool definitions)         │
│  ├─ Session                 (Active sessions)              │
│  ├─ Principal               (Users/agents)                 │
│  ├─ Policy                  (Policy metadata)              │
│  └─ AuditEvent              (Audit logs)                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  External Integrations                                      │
│  ├─ OPA (Policy Engine)     (Rego evaluation)              │
│  ├─ Redis (Cache)           (Policy cache, sessions)       │
│  ├─ TimescaleDB             (Audit storage)                │
│  ├─ Consul (Optional)       (Service discovery)            │
│  └─ SIEM (Optional)         (Splunk, Datadog, Kafka)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. MCP Server Management

**File:** `src/sark/models/mcp_server.py`

```python
class MCPServer(Base):
    """MCP server registration"""
    id: str
    name: str
    transport: TransportType  # stdio, sse, websocket
    command: str
    args: List[str]
    env: Dict[str, str]
    sensitivity_level: str
    metadata: Dict[str, Any]
```

**Limitations:**
- ❌ MCP-specific (can't govern HTTP APIs, gRPC, etc.)
- ❌ Tightly coupled to MCP protocol
- ❌ Hard to extend to other protocols

---

### 2. Policy Evaluation

**File:** `src/sark/services/policy.py`

```python
class PolicyService:
    async def evaluate(
        self,
        principal: Principal,
        action: str,
        resource: MCPServer,  # MCP-specific!
        tool: Optional[MCPTool] = None
    ) -> PolicyDecision:
        # Build OPA input
        opa_input = {
            "principal": {...},
            "action": action,
            "resource": {...},  # MCP-specific fields
            "tool": {...}       # MCP-specific fields
        }
        
        # Evaluate with OPA
        result = await self.opa_client.evaluate(opa_input)
        return result
```

**Limitations:**
- ❌ Hardcoded MCP concepts (server, tool)
- ❌ Can't evaluate policies for other protocols
- ✅ OPA integration is protocol-agnostic (good!)

---

### 3. Audit Logging

**File:** `src/sark/services/audit.py`

```python
class AuditService:
    async def log_tool_invocation(
        self,
        principal: Principal,
        server: MCPServer,
        tool: MCPTool,
        decision: PolicyDecision,
        result: Optional[Any] = None
    ):
        event = AuditEvent(
            event_type="tool_invocation",
            principal_id=principal.id,
            resource_id=server.id,
            resource_type="mcp_server",  # MCP-specific
            action="invoke_tool",
            decision=decision.allow,
            metadata={
                "tool_name": tool.name,  # MCP-specific
                "server_name": server.name
            }
        )
        await self.db.add(event)
```

**Limitations:**
- ❌ MCP-specific event types
- ❌ Hardcoded field names
- ✅ TimescaleDB storage is protocol-agnostic (good!)

---

### 4. Authentication

**File:** `src/sark/services/auth.py`

**Supported Methods:**
- ✅ Local (username/password)
- ✅ OIDC (OAuth 2.0)
- ✅ SAML 2.0
- ✅ LDAP
- ✅ API Keys

**Status:** ✅ Already protocol-agnostic! No changes needed for v2.0

---

### 5. Database Schema

**Current Tables:**
```sql
-- MCP-specific
CREATE TABLE mcp_servers (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    transport VARCHAR NOT NULL,  -- MCP-specific
    command VARCHAR NOT NULL,
    args JSONB,
    env JSONB,
    sensitivity_level VARCHAR,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE mcp_tools (
    id VARCHAR PRIMARY KEY,
    server_id VARCHAR REFERENCES mcp_servers(id),
    name VARCHAR NOT NULL,
    description TEXT,
    input_schema JSONB,  -- MCP-specific
    metadata JSONB,
    sensitivity_level VARCHAR
);

-- Protocol-agnostic (good!)
CREATE TABLE principals (
    id VARCHAR PRIMARY KEY,
    type VARCHAR NOT NULL,
    attributes JSONB,
    created_at TIMESTAMP
);

CREATE TABLE audit_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    event_type VARCHAR NOT NULL,
    principal_id VARCHAR,
    resource_id VARCHAR,
    resource_type VARCHAR,  -- Could be generic
    action VARCHAR,
    decision BOOLEAN,
    metadata JSONB,
    forwarded_to_siem BOOLEAN
);
```

---

## What Works Well (Keep for v2.0)

### ✅ Authentication System
- Multi-provider support
- Pluggable architecture
- Well-tested
- **Action:** Keep as-is

### ✅ OPA Integration
- Policy engine is protocol-agnostic
- Rego policies are flexible
- Caching works well
- **Action:** Keep as-is

### ✅ Audit Storage
- TimescaleDB for time-series
- Immutable logs
- SIEM forwarding
- **Action:** Keep as-is, extend event types

### ✅ API Design
- RESTful
- Well-documented
- Versioned (/api/v1)
- **Action:** Add /api/v2 for new features

---

## What Needs to Change (v2.0)

### ❌ MCP-Specific Models

**Current:**
```python
class MCPServer(Base):
    transport: TransportType  # MCP-specific
    command: str              # MCP-specific
```

**v2.0:**
```python
class Resource(Base):
    """Generic resource (MCP, HTTP, gRPC, etc.)"""
    protocol: str  # "mcp", "http", "grpc"
    endpoint: str  # Generic endpoint
    metadata: Dict[str, Any]  # Protocol-specific data

class MCPResource(Resource):
    """MCP-specific resource (inherits from Resource)"""
    # MCP-specific fields in metadata
```

---

### ❌ Hardcoded MCP Logic

**Current:**
```python
# In API router
@router.post("/servers")
async def register_server(server: MCPServerCreate):
    # MCP-specific validation
    # MCP-specific discovery
    # MCP-specific storage
```

**v2.0:**
```python
# In API router
@router.post("/resources")
async def register_resource(
    protocol: str,
    config: Dict[str, Any]
):
    # Get adapter for protocol
    adapter = registry.get(protocol)
    
    # Protocol-agnostic discovery
    resources = await adapter.discover_resources(config)
    
    # Generic storage
    for resource in resources:
        db.add(resource)
```

---

### ❌ No Federation Support

**Current:** Single SARK instance only

**v2.0:** Multiple SARK instances can federate
- Cross-org authorization
- Audit correlation
- Trust establishment (mTLS)

---

### ❌ No Cost Attribution

**Current:** No cost tracking

**v2.0:** Cost estimation and enforcement
- Estimate before execution
- Track in audit logs
- Budget policies

---

## File Structure Changes

### Current (v1.x)
```
src/sark/
├── api/
│   └── routers/
│       ├── servers.py      # MCP-specific
│       ├── tools.py        # MCP-specific
│       └── sessions.py
├── models/
│   ├── mcp_server.py       # MCP-specific
│   └── principal.py
├── services/
│   ├── discovery.py        # MCP-specific
│   ├── policy.py
│   └── audit.py
```

### Future (v2.0)
```
src/sark/
├── api/
│   ├── v1/                 # Backward compat
│   └── v2/                 # New endpoints
│       ├── resources.py    # Generic
│       ├── adapters.py     # New
│       └── federation.py   # New
├── models/
│   ├── base.py             # Generic base classes
│   ├── resource.py         # Generic Resource
│   └── principal.py        # Unchanged
├── adapters/               # NEW
│   ├── base.py
│   ├── mcp_adapter.py
│   ├── http_adapter.py
│   └── grpc_adapter.py
├── federation/             # NEW
│   ├── discovery.py
│   ├── trust.py
│   └── protocol.py
├── cost/                   # NEW
│   ├── estimator.py
│   └── tracker.py
├── services/
│   ├── policy.py           # Updated for generic resources
│   └── audit.py            # Updated for generic events
```

---

## Performance Baseline (v1.x)

**Policy Evaluation:**
- P50: 2ms
- P95: 4ms
- P99: 8ms

**Throughput:**
- 5,000 requests/second (single instance)
- 95% cache hit rate

**Database:**
- 1M audit events/day
- Query performance: <100ms for recent events

**Target for v2.0:**
- Maintain <5ms P95 policy evaluation
- Increase throughput to 10,000 req/s
- Add adapter overhead budget: <1ms

---

## Configuration (v1.x)

```yaml
# Current config structure
database:
  url: postgresql://...
  
redis:
  url: redis://...
  
opa:
  url: http://opa:8181
  
mcp:                        # MCP-specific section
  discovery_enabled: true
  default_transport: stdio
  
auth:
  providers:
    - type: oidc
      issuer: https://...
```

**v2.0 Changes:**
```yaml
# v2.0 config structure
protocols:                  # NEW: Protocol section
  enabled: ["mcp", "http", "grpc"]
  mcp:
    discovery_enabled: true
  http:
    openapi_validation: true
  grpc:
    reflection_enabled: true

federation:                 # NEW: Federation section
  enabled: true
  node_id: "org.example"
  nodes:
    - name: "partner"
      endpoint: "https://..."
```

---

## Summary

### Strengths (Keep)
- ✅ Authentication system
- ✅ OPA integration
- ✅ Audit logging
- ✅ API design
- ✅ Performance

### Weaknesses (Fix in v2.0)
- ❌ MCP-specific models
- ❌ Hardcoded protocol logic
- ❌ No federation
- ❌ No cost attribution
- ❌ Limited extensibility

### v2.0 Transformation
- Extract MCP logic → MCP Adapter
- Generic models → Resource, Capability
- Add adapters → HTTP, gRPC, custom
- Add federation → Cross-org governance
- Add cost tracking → Budget enforcement

---

**Document Version:** 1.0
**Created:** November 28, 2025
**Purpose:** Baseline for v2.0 planning