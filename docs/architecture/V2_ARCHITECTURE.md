# SARK v2.0: System Architecture

**Version:** 2.0.0
**Last Updated:** December 2025
**Status:** Reference Architecture

---

## Table of Contents

- [Overview](#overview)
- [High-Level Architecture](#high-level-architecture)
- [Core Components](#core-components)
- [Protocol Adapter Layer](#protocol-adapter-layer)
- [Data Architecture](#data-architecture)
- [Federation Architecture](#federation-architecture)
- [Policy Evaluation Flow](#policy-evaluation-flow)
- [Security Architecture](#security-architecture)
- [Deployment Architectures](#deployment-architectures)
- [Performance Considerations](#performance-considerations)
- [Scalability](#scalability)

---

## Overview

SARK v2.0 is the canonical reference implementation of GRID Protocol v1.0 - a universal governance protocol for machine-to-machine interactions. It provides a protocol-agnostic governance layer that can govern any API, service, or protocol through a unified policy framework.

### Design Principles

1. **Protocol Agnostic**: Core logic is independent of specific protocols
2. **Adapter Pattern**: Protocol-specific logic isolated in adapters
3. **Policy-Driven**: All authorization decisions made by OPA policies
4. **Audit-First**: Complete audit trail for compliance and security
5. **Distributed**: Support for cross-organization federation
6. **Observable**: Comprehensive metrics and logging
7. **Secure by Default**: Zero-trust architecture with defense in depth

### Key Capabilities

- **Multi-Protocol Support**: MCP, HTTP/REST, gRPC, and extensible
- **Centralized Governance**: Unified policies across all protocols
- **Cross-Org Federation**: Secure collaboration between organizations
- **Cost Attribution**: Track and enforce resource usage costs
- **Real-Time Audit**: TimescaleDB for time-series audit logging
- **High Performance**: <5ms policy evaluation, >10,000 req/s throughput

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT APPLICATIONS                          │
│  (Claude Desktop, Custom Apps, Scripts, Services, etc.)             │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     │ HTTPS/REST API
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          SARK v2.0 CORE                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    API LAYER (FastAPI)                      │   │
│  │  • Authentication (API Keys, JWT, OAuth)                    │   │
│  │  • Request Validation                                       │   │
│  │  • Rate Limiting                                            │   │
│  │  • Metrics Collection                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   GOVERNANCE CORE                           │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐   │   │
│  │  │   Resource   │  │     Policy    │  │  Cost          │   │   │
│  │  │   Manager    │  │   Evaluator   │  │  Attribution   │   │   │
│  │  └──────────────┘  └───────────────┘  └────────────────┘   │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐   │   │
│  │  │   Audit      │  │   Federation  │  │   Adapter      │   │   │
│  │  │   Service    │  │   Manager     │  │   Registry     │   │   │
│  │  └──────────────┘  └───────────────┘  └────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 PROTOCOL ADAPTER LAYER                      │   │
│  │  ┌─────────┐     ┌─────────┐     ┌─────────┐    ┌────────┐ │   │
│  │  │   MCP   │     │  HTTP   │     │  gRPC   │    │ Custom │ │   │
│  │  │ Adapter │     │ Adapter │     │ Adapter │    │Adapters│ │   │
│  │  └─────────┘     └─────────┘     └─────────┘    └────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                     │          │           │
                     ↓          ↓           ↓
┌───────────────┐ ┌────────────────┐ ┌──────────────┐
│ MCP Servers   │ │  REST APIs     │ │ gRPC Services│
│ (stdio, SSE)  │ │ (HTTP/HTTPS)   │ │ (gRPC/mTLS)  │
└───────────────┘ └────────────────┘ └──────────────┘

         EXTERNAL DEPENDENCIES
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ PostgreSQL  │  │     OPA     │  │   Redis     │
│ TimescaleDB │  │  (Policies) │  │  (Cache)    │
└─────────────┘  └─────────────┘  └─────────────┘
```

---

## Core Components

### 1. API Layer

**Technology**: FastAPI (Python async framework)

**Responsibilities**:
- HTTP request handling
- Authentication & authorization
- Request validation (Pydantic models)
- Response formatting
- Rate limiting
- Metrics collection
- OpenAPI documentation

**Key Routers**:
- `/api/v2/resources` - Resource management
- `/api/v2/authorize` - Policy evaluation & execution
- `/api/v2/federation` - Cross-org federation
- `/api/v2/audit` - Audit log queries
- `/api/v2/policies` - Policy management
- `/api/v2/cost` - Cost tracking & budgets

### 2. Resource Manager

**Responsibilities**:
- Resource discovery via adapters
- Resource lifecycle management
- Capability caching
- Health monitoring

**Key Operations**:
```python
class ResourceManager:
    async def register_resource(protocol, config) -> Resource
    async def get_resource(resource_id) -> Resource
    async def list_resources(filters) -> List[Resource]
    async def refresh_capabilities(resource_id) -> List[Capability]
    async def health_check(resource_id) -> bool
```

### 3. Policy Evaluator

**Technology**: Open Policy Agent (OPA) integration

**Responsibilities**:
- Policy evaluation
- Decision caching
- Policy hot-reloading
- Performance monitoring

**Evaluation Flow**:
```python
1. Receive authorization request
2. Build OPA input document
3. Query OPA for decision
4. Cache result (if cacheable)
5. Return allow/deny + reason
```

**Performance**:
- Target: <5ms P95 latency
- Caching: 95%+ cache hit rate
- Concurrent evaluation via async

### 4. Audit Service

**Technology**: TimescaleDB (PostgreSQL extension)

**Responsibilities**:
- Real-time audit logging
- Time-series data storage
- Correlation tracking (for federation)
- SIEM integration
- Retention management

**Schema**:
```sql
CREATE TABLE audit_logs (
  timestamp TIMESTAMPTZ NOT NULL,
  event_id UUID PRIMARY KEY,
  correlation_id UUID,
  event_type VARCHAR(50),
  principal_id VARCHAR(255),
  resource_id VARCHAR(255),
  capability_id VARCHAR(255),
  decision VARCHAR(10),
  duration_ms FLOAT,
  cost NUMERIC(10, 4),
  metadata JSONB
);

-- Convert to hypertable for time-series
SELECT create_hypertable('audit_logs', 'timestamp');
```

### 5. Federation Manager

**Responsibilities**:
- mTLS connection management
- Cross-org authorization requests
- Trust anchor validation
- Rate limiting per org
- Audit correlation

**Architecture**:
```
┌─────────────────────────────────────┐
│      Federation Manager             │
├─────────────────────────────────────┤
│ ┌─────────────┐ ┌────────────────┐  │
│ │ mTLS Client │ │ mTLS Server    │  │
│ │ (outbound)  │ │ (inbound)      │  │
│ └─────────────┘ └────────────────┘  │
│ ┌─────────────┐ ┌────────────────┐  │
│ │   Trust     │ │ Rate Limiter   │  │
│ │  Manager    │ │ (per org)      │  │
│ └─────────────┘ └────────────────┘  │
│ ┌─────────────────────────────────┐ │
│ │  Correlation Tracker            │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 6. Adapter Registry

**Responsibilities**:
- Adapter registration & discovery
- Adapter lifecycle management
- Protocol routing

**Interface**:
```python
class AdapterRegistry:
    def register(adapter: ProtocolAdapter)
    def get(protocol: str) -> ProtocolAdapter
    def list_protocols() -> List[str]
    def get_adapter_info(protocol: str) -> Dict
```

---

## Protocol Adapter Layer

### Adapter Architecture

```
┌──────────────────────────────────────────────────┐
│           ProtocolAdapter Interface              │
│  (Abstract Base Class)                           │
├──────────────────────────────────────────────────┤
│  • discover_resources(config)                    │
│  • get_capabilities(resource)                    │
│  • validate_request(request)                     │
│  • invoke(request)                               │
│  • health_check(resource)                        │
│  • invoke_streaming(request) [optional]          │
│  • invoke_batch(requests) [optional]             │
└──────────────────────────────────────────────────┘
                    ↑
       ┌────────────┼───────────┐
       │            │           │
┌──────┴─────┐ ┌───┴────┐ ┌────┴──────┐
│MCP Adapter │ │  HTTP  │ │   gRPC    │
│            │ │ Adapter│ │  Adapter  │
├────────────┤ ├────────┤ ├───────────┤
│• stdio     │ │• OpenAPI│ │• Protobuf │
│• SSE       │ │• REST  │ │• Streaming│
│• JSON-RPC  │ │• OAuth │ │• mTLS     │
└────────────┘ └────────┘ └───────────┘
```

### MCP Adapter

**Capabilities**:
- stdio transport (subprocess)
- SSE transport (Server-Sent Events)
- Tool discovery via MCP protocol
- Streaming responses

**Implementation**:
```python
class MCPAdapter(ProtocolAdapter):
    async def discover_resources(self, config):
        # Start MCP server subprocess
        # Initialize MCP session
        # List available tools
        # Return Resource + Capabilities

    async def invoke(self, request):
        # Get MCP server connection
        # Call tool via JSON-RPC
        # Handle streaming if needed
        # Return result
```

### HTTP Adapter

**Capabilities**:
- OpenAPI spec parsing
- Multiple auth methods (Bearer, OAuth, API Key)
- REST endpoint discovery
- Batch requests

**Implementation**:
```python
class HTTPAdapter(ProtocolAdapter):
    async def discover_resources(self, config):
        # Fetch OpenAPI spec
        # Parse paths and operations
        # Generate capabilities from endpoints
        # Return Resource + Capabilities

    async def invoke(self, request):
        # Build HTTP request (method, URL, headers, body)
        # Apply authentication
        # Execute via httpx
        # Return response
```

### gRPC Adapter

**Capabilities**:
- gRPC reflection
- Protobuf parsing
- Streaming RPCs (unary, server, client, bidirectional)
- mTLS authentication

**Implementation**:
```python
class GRPCAdapter(ProtocolAdapter):
    async def discover_resources(self, config):
        # Connect to gRPC service
        # Use reflection to list methods
        # Parse protobuf schemas
        # Return Resource + Capabilities

    async def invoke(self, request):
        # Build gRPC request
        # Execute via grpc.aio
        # Handle streaming
        # Return response
```

---

## Data Architecture

### Database Schema

**PostgreSQL 14+ with TimescaleDB extension**

```sql
-- Core v2.0 tables
CREATE TABLE resources (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    protocol VARCHAR(50) NOT NULL,
    endpoint VARCHAR(1000) NOT NULL,
    sensitivity_level VARCHAR(20) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE TABLE capabilities (
    id VARCHAR(255) PRIMARY KEY,
    resource_id VARCHAR(255) REFERENCES resources(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    input_schema JSONB,
    output_schema JSONB,
    sensitivity_level VARCHAR(20),
    metadata JSONB
);

CREATE TABLE federation_nodes (
    id UUID PRIMARY KEY,
    node_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    endpoint VARCHAR(500),
    trust_anchor_cert TEXT,
    enabled BOOLEAN DEFAULT true,
    rate_limit_per_hour INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Time-series tables (TimescaleDB hypertables)
CREATE TABLE audit_logs (
    timestamp TIMESTAMPTZ NOT NULL,
    event_id UUID,
    correlation_id UUID,
    event_type VARCHAR(50),
    principal_id VARCHAR(255),
    resource_id VARCHAR(255),
    capability_id VARCHAR(255),
    decision VARCHAR(10),
    duration_ms FLOAT,
    cost NUMERIC(10, 4),
    metadata JSONB
);
SELECT create_hypertable('audit_logs', 'timestamp');

CREATE TABLE cost_tracking (
    timestamp TIMESTAMPTZ NOT NULL,
    id BIGSERIAL,
    principal_id VARCHAR(255),
    resource_id VARCHAR(255),
    capability_id VARCHAR(255),
    estimated_cost NUMERIC(10, 4),
    actual_cost NUMERIC(10, 4),
    metadata JSONB
);
SELECT create_hypertable('cost_tracking', 'timestamp');

-- Budget tracking
CREATE TABLE principal_budgets (
    principal_id VARCHAR(255) PRIMARY KEY,
    daily_budget NUMERIC(10, 2),
    monthly_budget NUMERIC(10, 2),
    daily_spent NUMERIC(10, 4),
    monthly_spent NUMERIC(10, 4),
    last_daily_reset TIMESTAMPTZ,
    last_monthly_reset TIMESTAMPTZ,
    currency VARCHAR(3) DEFAULT 'USD'
);
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_resources_protocol ON resources(protocol);
CREATE INDEX idx_resources_sensitivity ON resources(sensitivity_level);
CREATE INDEX idx_capabilities_resource ON capabilities(resource_id);
CREATE INDEX idx_capabilities_name ON capabilities(name);
CREATE INDEX idx_audit_principal ON audit_logs(principal_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_id, timestamp DESC);
CREATE INDEX idx_audit_correlation ON audit_logs(correlation_id);
CREATE INDEX idx_cost_principal ON cost_tracking(principal_id, timestamp DESC);
```

### Data Retention

```sql
-- Automatic data retention via TimescaleDB
SELECT add_retention_policy('audit_logs', INTERVAL '90 days');
SELECT add_retention_policy('cost_tracking', INTERVAL '365 days');
```

---

## Federation Architecture

### Federation Flow

```
 ORGANIZATION A                    ORGANIZATION B
┌─────────────────┐               ┌─────────────────┐
│   SARK Node A   │               │   SARK Node B   │
│                 │               │                 │
│  1. Alice makes │               │                 │
│     request     │               │                 │
│        ↓        │               │                 │
│  2. Node A sees │               │                 │
│     resource is │               │                 │
│     in Org B    │               │                 │
│        ↓        │               │                 │
│  3. mTLS query ─┼──────────────→│  4. Receive     │
│                 │               │     auth request│
│                 │               │        ↓        │
│                 │               │  5. Evaluate    │
│                 │               │     policy      │
│                 │               │        ↓        │
│  7. Receive    ←┼───────────────│  6. Send        │
│     decision    │               │     allow/deny  │
│        ↓        │               │                 │
│  8. Audit log   │               │  9. Audit log   │
│     (corr_id)   │               │     (corr_id)   │
│        ↓        │               │                 │
│  10. Return to  │               │                 │
│      Alice      │               │                 │
└─────────────────┘               └─────────────────┘
```

### mTLS Configuration

```
Node A Certificate:
  Subject: CN=sark.orga.com
  Issuer: Organization A CA
  SAN: sark.orga.com, *.orga.com

Node B Certificate:
  Subject: CN=sark.orgb.com
  Issuer: Organization B CA
  SAN: sark.orgb.com, *.orgb.com

Trust Anchors:
  Node A trusts: Org B CA, Org C CA
  Node B trusts: Org A CA, Org C CA
```

---

## Policy Evaluation Flow

```
1. Client Request
   ↓
2. API Layer (Authentication)
   ↓
3. Extract Policy Input
   {
     "principal": {...},
     "resource": {...},
     "capability": {...},
     "action": "execute",
     "context": {...}
   }
   ↓
4. Check Policy Cache
   Cache Hit? → Return cached decision
   Cache Miss? → Continue
   ↓
5. Query OPA
   POST /v1/data/grid/allow
   ↓
6. OPA Evaluates Policies
   • grid.base (base rules)
   • grid.custom (custom rules)
   • grid.federation (cross-org)
   ↓
7. OPA Returns Decision
   {
     "allow": true/false,
     "reason": "...",
     "metadata": {...}
   }
   ↓
8. Cache Decision (if cacheable)
   ↓
9. If Allowed → Invoke via Adapter
   ↓
10. Audit Log
    ↓
11. Return to Client
```

---

## Security Architecture

### Defense in Depth

```
Layer 1: Network Security
  • TLS 1.3 for all connections
  • mTLS for federation
  • Firewall rules
  • DDoS protection

Layer 2: Authentication
  • API Keys (SHA-256 hashed)
  • JWT tokens (RS256 signed)
  • OAuth 2.0 / OIDC
  • SAML 2.0

Layer 3: Authorization
  • OPA policy evaluation
  • Role-based access control
  • Attribute-based access control
  • Time-based restrictions

Layer 4: Audit & Compliance
  • Immutable audit logs
  • Correlation tracking
  • SIEM integration
  • Compliance reporting

Layer 5: Data Security
  • Encryption at rest (database)
  • Encryption in transit (TLS)
  • Secret management (HashiCorp Vault)
  • Key rotation
```

### Zero-Trust Model

```
No implicit trust:
  • Every request authenticated
  • Every action authorized
  • Every operation audited
  • Every connection encrypted
```

---

## Deployment Architectures

### Single-Node Deployment (Development)

```
┌────────────────────────────────┐
│       Docker Compose           │
│  ┌──────┐ ┌───────┐ ┌───────┐ │
│  │ SARK │ │  OPA  │ │ Redis │ │
│  └──────┘ └───────┘ └───────┘ │
│  ┌────────────────────────────┐│
│  │  PostgreSQL (TimescaleDB)  ││
│  └────────────────────────────┘│
└────────────────────────────────┘
```

### High-Availability Deployment (Production)

```
                  Load Balancer
                       │
         ┌─────────────┼─────────────┐
         │             │             │
     ┌───────┐     ┌───────┐     ┌───────┐
     │ SARK  │     │ SARK  │     │ SARK  │
     │ Node 1│     │ Node 2│     │ Node 3│
     └───────┘     └───────┘     └───────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
     ┌───────┐     ┌───────┐     ┌──────────┐
     │  OPA  │     │ Redis │     │PostgreSQL│
     │Cluster│     │Cluster│     │  (HA)    │
     └───────┘     └───────┘     └──────────┘
```

### Multi-Region Deployment (Global)

```
   Region 1 (US-East)         Region 2 (EU-West)
┌────────────────────┐     ┌────────────────────┐
│  SARK Cluster      │     │  SARK Cluster      │
│  (Active)          │     │  (Active)          │
│                    │     │                    │
│  PostgreSQL        │────▶│  PostgreSQL        │
│  (Primary)         │     │  (Read Replica)    │
└────────────────────┘     └────────────────────┘
         │                          │
         └────────┬─────────────────┘
                  │
            Global Traffic
              Manager
```

---

## Performance Considerations

### Latency Targets

- **API Response Time**: <100ms (P95)
- **Policy Evaluation**: <5ms (P95)
- **Adapter Overhead**: <10ms (P95)
- **Federation Latency**: <50ms (P95)
- **Audit Write**: <1ms (async)

### Throughput Targets

- **Authorization Requests**: 10,000+ req/s
- **Policy Evaluations**: 100,000+ eval/s (OPA)
- **Audit Events**: 50,000+ events/s

### Optimization Techniques

1. **Caching**:
   - Policy decisions (Redis)
   - Resource metadata (in-memory)
   - Adapter connections (pooling)

2. **Async Processing**:
   - Audit logging (fire-and-forget)
   - SIEM forwarding (batched)
   - Metrics collection (buffered)

3. **Database**:
   - Connection pooling (PgBouncer)
   - Read replicas for queries
   - Partitioning for time-series data

4. **Load Distribution**:
   - Horizontal scaling (multiple SARK nodes)
   - Load balancing (round-robin, least-connections)
   - Geographic distribution

---

## Scalability

### Horizontal Scaling

```
SARK is stateless and can scale horizontally:

1 node:      10,000 req/s
3 nodes:     30,000 req/s
10 nodes:   100,000 req/s
```

### Bottlenecks & Solutions

**Database**:
- Problem: High write load on audit logs
- Solution: TimescaleDB compression, read replicas

**OPA**:
- Problem: Policy evaluation latency
- Solution: OPA clustering, policy caching

**Adapters**:
- Problem: Slow external services
- Solution: Connection pooling, circuit breakers, timeouts

**Federation**:
- Problem: Cross-org latency
- Solution: Response caching, geographic distribution

---

## Diagram References

See `docs/architecture/diagrams/` for detailed visual diagrams:

- `system-overview.svg` - High-level system architecture
- `adapter-pattern.svg` - Protocol adapter pattern
- `federation-flow.svg` - Cross-org federation flow
- `policy-evaluation.svg` - Policy evaluation sequence
- `data-model.svg` - Database schema diagram
- `deployment-ha.svg` - High-availability deployment

---

**Document Version:** 1.0
**Last Updated:** December 2025
**Maintainer:** SARK Core Team
