# SARK Architecture

## Overview

SARK (Security Audit and Resource Kontroler) is an enterprise-grade governance system for Model Context Protocol (MCP) deployments. It provides comprehensive security, authorization, auditing, and operational controls for organizations deploying AI assistants at scale.

**Design Philosophy:** Zero-trust, defense-in-depth, fail-safe defaults, observable, cloud-native

## System Architecture

```
┌──────────────────────── ENTERPRISE PERIMETER ─────────────────────────┐
│                                                                         │
│  Users/Clients ──HTTPS──▶ Kong API Gateway (Edge Security)            │
│                               │                                         │
│  ┌────────────────────────────▼───────────────────────────────────┐   │
│  │                    SARK CONTROL PLANE                          │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│  │  │  Discovery  │  │   Policy    │  │    Audit    │           │   │
│  │  │   Service   │  │   Engine    │  │  Pipeline   │           │   │
│  │  │  (FastAPI)  │  │    (OPA)    │  │  (Python)   │           │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │   │
│  │         │                 │                 │                  │   │
│  │  ┌──────▼─────────────────▼─────────────────▼──────────────┐  │   │
│  │  │  Data Layer: PostgreSQL │ TimescaleDB │ Redis │ Consul │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                         │
│  ┌────────────────────────────▼───────────────────────────────────┐   │
│  │         Service Mesh (mTLS, Service Discovery, Observability) │   │
│  └────────────────────────────┬───────────────────────────────────┘   │
│                               │                                         │
│  ┌────────────────────────────▼───────────────────────────────────┐   │
│  │  MCP Servers (Remote HTTP + Local stdio)                       │   │
│  │    └──▶ Backend Tools & Resources (DBs, APIs, Files, Cloud)   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. API Gateway Layer

**Technology:** Kong Gateway 3.8+

**Responsibilities:**
- Edge security and rate limiting
- Protocol translation (HTTP/2, gRPC)
- Request routing and load balancing
- Initial authentication and authorization

**Custom Plugins:**
- `mcp-security`: MCP protocol validation and security enforcement
- Request/response logging with audit context injection

### 2. Discovery Service

**Technology:** Python (FastAPI) + Consul

**Responsibilities:**
- Automated MCP server discovery via multiple methods:
  - Network scanning (agentless)
  - Kubernetes API integration
  - Cloud API polling (AWS, Azure, GCP)
  - Manual registration via API
- Health monitoring and availability tracking
- Service registry management with Consul
- Metadata enrichment and tagging

**Key Features:**
- Continuous discovery with configurable intervals
- Deduplication across discovery sources
- Shadow IT detection via network anomalies

### 3. Policy Engine

**Technology:** Open Policy Agent (OPA) 0.60+

**Responsibilities:**
- Authorization decision making
- Policy evaluation (<10ms p99 latency target)
- Policy bundle management via GitOps
- Hybrid ReBAC+ABAC model support

**Policy Types:**
- Tool access control (ownership, team-based)
- Time-based restrictions (work hours, weekday)
- Sensitivity-based controls (data classification)
- Context-aware policies (user role, location, device)

### 4. Audit Pipeline

**Technology:** Python + Kafka (optional for scale)

**Responsibilities:**
- Real-time event capture and processing
- Batch writes to TimescaleDB for efficiency
- SIEM integration for high-priority events
- Immutable audit trail maintenance
- Compliance reporting data preparation

**Performance Targets:**
- 10,000 events/second processing capacity
- <5 second end-to-end event latency
- 100M+ events retention capability

### 5. Secrets Management

**Technology:** HashiCorp Vault integration

**Responsibilities:**
- Dynamic credential generation
- Short-lived token management (15min default)
- Automatic rotation and renewal
- Secure secret storage
- Workload identity binding

### 6. Data Layer

#### PostgreSQL 15+
- Policy definitions and versioning
- User and team management
- Server registry metadata
- Application configuration

#### TimescaleDB 2.14+
- Time-series audit event storage
- Performance metrics and telemetry
- Compliance reporting data
- Retention policies and compression

#### Redis Cluster 7+
- Policy evaluation caching (95%+ hit rate target)
- Session state management
- Rate limiting counters
- Temporary data buffering

#### Consul
- Service discovery and health checking
- Distributed configuration
- Leader election for active-active deployment

## Technology Stack

| Component        | Technology           | Purpose                     | Scale Target    |
|-----------------|----------------------|-----------------------------|-----------------|
| API Framework   | FastAPI 0.100+       | REST API endpoints          | 100k RPS        |
| API Gateway     | Kong Gateway 3.8+    | Edge security               | 100k RPS        |
| Policy Engine   | Open Policy Agent    | Authorization decisions     | <10ms p99       |
| Discovery       | Python + Consul      | MCP server inventory        | 10k+ servers    |
| Audit Storage   | TimescaleDB 2.14+    | Time-series logs            | 100M+ events    |
| Cache           | Redis Cluster 7+     | Hot data caching            | 1M ops/sec      |
| Secrets         | HashiCorp Vault      | Credential lifecycle        | 100k secrets    |
| Service Registry| Consul 1.16+         | Service discovery           | 10k services    |
| Observability   | Prometheus/Grafana   | Metrics/dashboards          | Full stack      |

## Security Architecture

### Defense in Depth

1. **Edge Layer** - Kong Gateway
   - TLS termination
   - Rate limiting
   - DDoS protection
   - Initial authentication

2. **Application Layer** - SARK Control Plane
   - Fine-grained authorization (OPA)
   - Input validation
   - Business logic enforcement

3. **Data Layer**
   - Encryption at rest
   - Connection pooling with TLS
   - Access control lists
   - Audit logging

4. **Network Layer**
   - mTLS between services
   - Network segmentation
   - Zero-trust networking

### Threat Mitigations

| Threat              | Mitigation Strategy                                    |
|---------------------|--------------------------------------------------------|
| Tool Poisoning      | Cryptographic signing, semantic analysis               |
| Confused Deputy     | RFC 8707 audience binding, per-client consent          |
| Prompt Injection    | Input segregation, multi-layer validation              |
| Credential Theft    | Short-lived tokens, dynamic secrets, immediate revoke  |
| Data Exfiltration   | DLP integration, anomaly detection, rate limiting      |
| Session Hijacking   | Secure random IDs, context binding, auto-expiration    |

## Data Flow

### Server Registration

```
1. MCP Server → API Gateway → Discovery Service
2. Discovery Service validates server metadata
3. Policy Engine evaluates registration policy
4. Server registered in PostgreSQL + Consul
5. Audit event recorded in TimescaleDB
6. Response returned to caller
```

### Authorization Request

```
1. Client → Kong Gateway (MCP request)
2. Kong extracts user + tool context
3. Kong queries OPA for authorization decision
4. OPA evaluates policies (checks Redis cache first)
5. Decision returned with filtered parameters
6. Kong allows/denies request accordingly
7. Audit event emitted to pipeline
```

### Audit Event Flow

```
1. Event emitted from service
2. Kafka topic (optional) or direct write
3. Batch processor aggregates events
4. Bulk write to TimescaleDB
5. High-priority events → SIEM (Splunk/etc)
6. Metrics updated in Prometheus
```

## Deployment Architecture

### Development Environment

- Docker Compose with all services
- Local PostgreSQL, Redis, OPA containers
- Hot-reload enabled for rapid iteration

### Production Environment

- Kubernetes 1.28+ (EKS/GKE/AKS)
- Multi-region active-active deployment
- Managed services for databases (RDS, ElastiCache)
- Vault in HA mode
- Service mesh for mTLS (Kong Mesh or Istio)

## Performance Targets

| Metric                        | Phase 1 | Phase 3 | Phase 4 |
|-------------------------------|---------|---------|---------|
| Policy Latency (p99)          | <50ms   | <10ms   | <5ms    |
| API Response Time (p95)       | <200ms  | <100ms  | <50ms   |
| Audit Processing              | 1k/sec  | 5k/sec  | 10k/sec |
| Availability                  | 99%     | 99.9%   | 99.95%  |
| Servers Managed               | 100     | 5,000   | 10,000+ |

## Design Principles

1. **Type Safety** - Strict type checking with MyPy and Pydantic
2. **Fail-Safe Defaults** - Deny on error, explicit allow required
3. **Observable** - Comprehensive metrics, logs, and traces
4. **Testable** - High test coverage (>80%), integration tests
5. **Scalable** - Horizontal scaling, stateless services
6. **Maintainable** - Clear code, documentation, runbooks

## Future Enhancements

- Machine learning for anomaly detection
- Predictive policy recommendations
- Cost optimization analytics
- Advanced compliance reporting (SOC 2, ISO 27001)
- Self-healing capabilities
- Multi-cloud federation

---

**Last Updated:** November 2025
**Version:** 1.0
**Status:** Implementation in Progress
