# MCP Architecture Diagram

## Overview
This diagram shows how SARK fits into the Model Context Protocol ecosystem, providing enterprise governance for MCP deployments.

## Diagram

```mermaid
graph TB
    subgraph "AI Layer"
        AI[AI Assistant<br/>Claude, GPT, etc.]
    end

    subgraph "SARK Governance Layer"
        direction TB
        API[SARK API Gateway<br/>Kong + FastAPI]
        AUTH[Authentication<br/>OIDC/LDAP/SAML]
        AUTHZ[Authorization<br/>Open Policy Agent]
        AUDIT[Audit System<br/>TimescaleDB]
        DISC[Discovery Service<br/>K8s/Consul/Network]
        CACHE[Policy Cache<br/>Redis]
    end

    subgraph "MCP Servers Layer"
        direction LR
        MCP1[MCP Server: Finance<br/>Tools: budget_query<br/>         expense_report]
        MCP2[MCP Server: HR<br/>Tools: employee_lookup<br/>         create_ticket]
        MCP3[MCP Server: Data<br/>Tools: database_query<br/>         analytics]
        MCP4[MCP Server: DevOps<br/>Tools: deploy_service<br/>         check_logs]
    end

    subgraph "Enterprise Systems"
        DB[(Financial DB)]
        HRMS[HR Management<br/>System]
        DW[(Data Warehouse)]
        K8S[Kubernetes<br/>Cluster]
    end

    subgraph "Security & Observability"
        direction TB
        SIEM[SIEM<br/>Splunk/Datadog]
        VAULT[Secrets<br/>HashiCorp Vault]
        PROM[Monitoring<br/>Prometheus]
    end

    %% AI to SARK
    AI -->|1. Tool Request| API
    API -->|2. Authenticate| AUTH
    AUTH -->|3. Check Policy| AUTHZ
    AUTHZ <-->|Cache Lookup| CACHE
    AUTHZ -->|4. Log Decision| AUDIT

    %% SARK to MCP Servers
    API -.->|Allowed| MCP1
    API -.->|Allowed| MCP2
    API -.->|Allowed| MCP3
    API -.->|Allowed| MCP4

    %% Discovery
    DISC -.->|Discovers| MCP1
    DISC -.->|Discovers| MCP2
    DISC -.->|Discovers| MCP3
    DISC -.->|Discovers| MCP4

    %% MCP Servers to Backend Systems
    MCP1 --> DB
    MCP2 --> HRMS
    MCP3 --> DW
    MCP4 --> K8S

    %% Security & Observability
    AUDIT --> SIEM
    AUTH --> VAULT
    API --> PROM
    AUTHZ --> PROM

    %% Styling
    classDef aiColor fill:#ff6b6b,stroke:#c92a2a,color:#fff
    classDef sarkColor fill:#4a90e2,stroke:#2e5c8a,color:#fff
    classDef mcpColor fill:#50c878,stroke:#2d7a4a,color:#fff
    classDef systemColor fill:#ffd43b,stroke:#e6b800,color:#000
    classDef secColor fill:#9775fa,stroke:#6741d9,color:#fff

    class AI aiColor
    class API,AUTH,AUTHZ,AUDIT,DISC,CACHE sarkColor
    class MCP1,MCP2,MCP3,MCP4 mcpColor
    class DB,HRMS,DW,K8S systemColor
    class SIEM,VAULT,PROM secColor
```

## Key Components

### AI Layer
- **AI Assistants**: Claude, GPT, or other LLMs that need to access enterprise tools
- **Request Flow**: AI sends tool invocation requests through SARK

### SARK Governance Layer
- **API Gateway**: Kong + FastAPI handling all MCP requests
- **Authentication**: Multi-protocol support (OIDC, LDAP, SAML, API Keys)
- **Authorization**: OPA-based policy decisions with caching
- **Audit System**: Immutable event log in TimescaleDB
- **Discovery**: Automated finding and registration of MCP servers
- **Cache**: Redis-based policy decision cache (>95% hit rate target)

### MCP Servers Layer
- **Finance MCP**: Financial tools (budgets, expenses, reporting)
- **HR MCP**: Human resources tools (employee data, ticketing)
- **Data MCP**: Data analysis and query tools
- **DevOps MCP**: Infrastructure and deployment tools

Each MCP server exposes tools that AI can invoke via the protocol.

### Enterprise Systems
- Backend systems that MCP servers integrate with
- May include databases, APIs, SaaS platforms, cloud services

### Security & Observability
- **SIEM**: Security events forwarded to Splunk or Datadog
- **Vault**: Dynamic secrets for MCP server credentials
- **Prometheus**: Metrics collection for monitoring

## Data Flow

1. **AI Request**: AI assistant requests to invoke a tool
2. **Authentication**: SARK validates user identity (JWT, OIDC, etc.)
3. **Authorization**: OPA evaluates policy (role, sensitivity, time, etc.)
4. **Cache Check**: Policy decision checked in Redis first
5. **Audit Log**: Decision logged to TimescaleDB and SIEM
6. **Tool Invocation**: If allowed, request proxied to MCP server
7. **Execution**: MCP server executes tool against backend system
8. **Response**: Result returned through SARK back to AI

## Security Layers

```
┌─────────────────────────────────────────┐
│ Layer 1: Network Security               │
│ - Firewall, VPC, Security Groups        │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Layer 2: API Gateway (Kong)             │
│ - Rate limiting, WAF, DDoS protection   │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Layer 3: Authentication                 │
│ - Identity verification, MFA            │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Layer 4: Authorization (OPA)            │
│ - Policy-based access control           │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Layer 5: MCP Protocol Validation        │
│ - Schema validation, signature check    │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Layer 6: Tool Execution                 │
│ - MCP server invokes tool                │
└─────────────────────────────────────────┘
```

## Discovery Mechanisms

SARK automatically discovers MCP servers through multiple methods:

1. **Kubernetes Discovery**: Watches K8s API for MCP server pods
2. **Consul Service Discovery**: Monitors Consul catalog for services
3. **Network Scanning**: Probes network ranges for MCP endpoints
4. **Manual Registration**: API endpoint for explicit registration
5. **Cloud Provider APIs**: AWS/GCP/Azure service discovery

## Scaling Patterns

- **Horizontal Scaling**: Multiple SARK API instances behind load balancer
- **Cache Replication**: Redis cluster for distributed caching
- **Database Sharding**: PostgreSQL read replicas for query distribution
- **Regional Deployment**: Multi-region for low latency globally

## Use Cases

1. **AI-Powered Analytics**: AI queries data warehouse via MCP Data server
2. **Automated HR Tasks**: AI creates tickets via MCP HR server
3. **Financial Reporting**: AI generates expense reports via MCP Finance server
4. **DevOps Automation**: AI deploys services via MCP DevOps server

All with enterprise governance, audit trails, and zero-trust security.
