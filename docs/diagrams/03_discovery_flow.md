# MCP Server Discovery Flow

## Overview
This diagram shows how SARK automatically discovers and registers MCP servers using multiple discovery methods: Kubernetes API, Consul service catalog, network scanning, and manual registration.

## Discovery Architecture

```mermaid
graph TB
    subgraph "Discovery Service (SARK)"
        SCHED[Discovery Scheduler<br/>Runs every 5 min]
        K8S_DISC[Kubernetes<br/>Discovery]
        CONSUL_DISC[Consul<br/>Discovery]
        NET_DISC[Network<br/>Scanner]
        MANUAL[Manual<br/>Registration API]
        VALIDATOR[Server Validator]
        REGISTRY[Server Registry<br/>PostgreSQL]
    end

    subgraph "Discovery Sources"
        K8S[Kubernetes API<br/>List Pods/Services]
        CONSUL[Consul Catalog<br/>Service Registry]
        NETWORK[Network Range<br/>10.0.0.0/8]
        API_CLIENT[API Client<br/>CLI/UI/SDK]
    end

    subgraph "MCP Servers"
        MCP1[MCP Server 1<br/>K8s Pod]
        MCP2[MCP Server 2<br/>Consul Service]
        MCP3[MCP Server 3<br/>Network Host]
        MCP4[MCP Server 4<br/>Manual Entry]
    end

    subgraph "Validation & Health"
        HEALTH[Health Check<br/>GET /health]
        SCHEMA[Schema Validator<br/>MCP Protocol]
        SIG[Signature Verifier<br/>Cryptographic]
    end

    %% Scheduler triggers
    SCHED -->|Trigger| K8S_DISC
    SCHED -->|Trigger| CONSUL_DISC
    SCHED -->|Trigger| NET_DISC

    %% Discovery methods
    K8S_DISC <-->|Watch API| K8S
    CONSUL_DISC <-->|Query Catalog| CONSUL
    NET_DISC -->|Port Scan| NETWORK
    MANUAL <-->|POST /servers| API_CLIENT

    %% Server discovery
    K8S -->|Found| MCP1
    CONSUL -->|Found| MCP2
    NETWORK -->|Found| MCP3
    API_CLIENT -->|Register| MCP4

    %% Validation flow
    K8S_DISC --> VALIDATOR
    CONSUL_DISC --> VALIDATOR
    NET_DISC --> VALIDATOR
    MANUAL --> VALIDATOR

    VALIDATOR --> HEALTH
    VALIDATOR --> SCHEMA
    VALIDATOR --> SIG

    HEALTH --> REGISTRY
    SCHEMA --> REGISTRY
    SIG --> REGISTRY

    %% Styling
    classDef discColor fill:#4a90e2,stroke:#2e5c8a,color:#fff
    classDef sourceColor fill:#ffd43b,stroke:#e6b800,color:#000
    classDef mcpColor fill:#50c878,stroke:#2d7a4a,color:#fff
    classDef validColor fill:#9775fa,stroke:#6741d9,color:#fff

    class SCHED,K8S_DISC,CONSUL_DISC,NET_DISC,MANUAL,VALIDATOR,REGISTRY discColor
    class K8S,CONSUL,NETWORK,API_CLIENT sourceColor
    class MCP1,MCP2,MCP3,MCP4 mcpColor
    class HEALTH,SCHEMA,SIG validColor
```

## Kubernetes Discovery Sequence

```mermaid
sequenceDiagram
    participant SCHED as Discovery Scheduler
    participant K8S_DISC as K8s Discovery Service
    participant K8S_API as Kubernetes API Server
    participant VALIDATOR as Server Validator
    participant MCP as MCP Server Pod
    participant DB as Server Registry (PostgreSQL)

    Note over SCHED,DB: Kubernetes-based Discovery (Every 5 minutes)

    SCHED->>K8S_DISC: Trigger K8s discovery
    K8S_DISC->>K8S_API: List pods with label:<br/>mcp.server=true

    K8S_API-->>K8S_DISC: Pod list:<br/>[{name: "finance-mcp", namespace: "finance", ...}]

    loop For each pod
        K8S_DISC->>K8S_DISC: Extract metadata:<br/>• Name, namespace<br/>• Labels, annotations<br/>• Service endpoints

        K8S_DISC->>DB: Check if already registered:<br/>SELECT * FROM mcp_servers<br/>WHERE consul_id = 'k8s://namespace/pod'

        alt Already Registered
            DB-->>K8S_DISC: Server exists
            K8S_DISC->>K8S_DISC: Update timestamp<br/>Mark as ACTIVE
        else New Server
            DB-->>K8S_DISC: Not found

            K8S_DISC->>VALIDATOR: Validate new server:<br/>{<br/>  endpoint: "http://pod-ip:8080",<br/>  name: "finance-mcp",<br/>  source: "k8s"<br/>}

            VALIDATOR->>MCP: GET /health
            MCP-->>VALIDATOR: 200 OK {status: "healthy"}

            VALIDATOR->>MCP: GET /mcp/v1/capabilities
            MCP-->>VALIDATOR: {<br/>  protocol_version: "2025-06-18",<br/>  capabilities: ["tools", "resources"],<br/>  server_info: {name: "Finance MCP"}  <br/>}

            VALIDATOR->>VALIDATOR: Validate schema
            VALIDATOR->>VALIDATOR: Extract tool definitions

            VALIDATOR-->>K8S_DISC: Valid server

            K8S_DISC->>DB: INSERT INTO mcp_servers<br/>{<br/>  name: "finance-mcp",<br/>  endpoint: "http://...",<br/>  transport: "http",<br/>  mcp_version: "2025-06-18",<br/>  capabilities: ["tools"],<br/>  consul_id: "k8s://finance/finance-mcp",<br/>  status: "active",<br/>  tags: ["k8s", "finance"]<br/>}

            DB-->>K8S_DISC: Server registered

            K8S_DISC->>DB: INSERT INTO mcp_tools<br/>(tool definitions)

            Note over K8S_DISC: Server discovered and registered
        end
    end

    K8S_DISC-->>SCHED: Discovery complete<br/>(found: 3 new, updated: 12)
```

## Consul Discovery Sequence

```mermaid
sequenceDiagram
    participant SCHED as Discovery Scheduler
    participant CONSUL_DISC as Consul Discovery
    participant CONSUL as Consul Server
    participant MCP as MCP Server (Consul Service)
    participant DB as Server Registry

    SCHED->>CONSUL_DISC: Trigger Consul discovery

    CONSUL_DISC->>CONSUL: GET /v1/catalog/services?tag=mcp

    CONSUL-->>CONSUL_DISC: {<br/>  "finance-mcp-service": ["mcp", "finance"],<br/>  "hr-mcp-service": ["mcp", "hr"]<br/>}

    loop For each service
        CONSUL_DISC->>CONSUL: GET /v1/catalog/service/{service_name}

        CONSUL-->>CONSUL_DISC: {<br/>  ServiceID: "finance-mcp-01",<br/>  ServiceName: "finance-mcp-service",<br/>  ServiceAddress: "10.0.1.45",<br/>  ServicePort: 8080,<br/>  ServiceTags: ["mcp", "finance"],<br/>  ServiceMeta: {<br/>    mcp_version: "2025-06-18",<br/>    sensitivity: "high"<br/>  }<br/>}

        CONSUL_DISC->>DB: Check existing:<br/>WHERE consul_id = 'consul://finance-mcp-01'

        alt New Service
            DB-->>CONSUL_DISC: Not found

            CONSUL_DISC->>CONSUL_DISC: Build endpoint:<br/>http://10.0.1.45:8080

            CONSUL_DISC->>MCP: Health check + capability query

            alt Service Healthy
                MCP-->>CONSUL_DISC: Valid MCP server

                CONSUL_DISC->>DB: Register server + tools

                Note over CONSUL_DISC: Discovery successful
            else Service Unhealthy
                MCP-->>CONSUL_DISC: Timeout or error

                Note over CONSUL_DISC: Skip registration,<br/>log warning
            end
        else Existing Service
            DB-->>CONSUL_DISC: Server exists

            CONSUL_DISC->>DB: UPDATE mcp_servers<br/>SET updated_at = NOW(),<br/>    status = 'active'

            Note over CONSUL_DISC: Server refreshed
        end
    end
```

## Network Scanner Flow

```mermaid
sequenceDiagram
    participant SCHED as Discovery Scheduler
    participant NET_DISC as Network Scanner
    participant NETWORK as Network Range<br/>(10.0.0.0/8)
    participant MCP as Potential MCP Server
    participant DB as Server Registry

    Note over SCHED,DB: Network Scanning (Careful: Can be intrusive)

    SCHED->>NET_DISC: Trigger network scan

    NET_DISC->>NET_DISC: Load scan config:<br/>• IP ranges: [10.0.0.0/8]<br/>• Ports: [8080, 8443, 3000]<br/>• Timeout: 5s per host

    loop For each IP in range
        NET_DISC->>NETWORK: TCP SYN scan<br/>10.0.1.45:8080

        alt Port Open
            NETWORK-->>NET_DISC: SYN-ACK (port open)

            NET_DISC->>MCP: GET http://10.0.1.45:8080/health<br/>Timeout: 5s

            alt Responds with MCP Headers
                MCP-->>NET_DISC: 200 OK<br/>X-MCP-Version: 2025-06-18<br/>X-MCP-Server: data-analytics

                NET_DISC->>MCP: GET /mcp/v1/capabilities

                MCP-->>NET_DISC: Valid MCP response

                NET_DISC->>DB: Check if known:<br/>WHERE endpoint = 'http://10.0.1.45:8080'

                alt Unknown Server
                    DB-->>NET_DISC: Not found

                    NET_DISC->>DB: INSERT INTO mcp_servers<br/>{<br/>  name: "discovered-10-0-1-45",<br/>  endpoint: "http://10.0.1.45:8080",<br/>  consul_id: "scan://10.0.1.45:8080",<br/>  status: "registered",<br/>  tags: ["network-scan", "unverified"]<br/>}

                    Note over NET_DISC: ⚠️ Flag for manual review<br/>(potential shadow IT)
                else Known Server
                    DB-->>NET_DISC: Server exists

                    Note over NET_DISC: Already tracked, skip
                end
            else Not MCP Server
                MCP-->>NET_DISC: Wrong response format

                Note over NET_DISC: Skip (not an MCP server)
            end
        else Port Closed
            NETWORK-->>NET_DISC: RST (port closed)

            Note over NET_DISC: Skip to next IP
        end
    end

    NET_DISC-->>SCHED: Scan complete<br/>Found: 2 potential MCP servers<br/>Flagged for review: 2
```

## Manual Registration Flow

```mermaid
sequenceDiagram
    participant USER as Administrator/DevOps
    participant CLI as SARK CLI
    participant API as SARK API
    participant VALIDATOR as Server Validator
    participant MCP as MCP Server
    participant DB as Server Registry
    participant AUDIT as Audit Log

    Note over USER,AUDIT: Manual Server Registration

    USER->>CLI: sark-cli servers create \<br/>  --name "payment-mcp" \<br/>  --endpoint "https://pay.internal:8443" \<br/>  --transport http \<br/>  --sensitivity high \<br/>  --team finance

    CLI->>CLI: Validate input parameters
    CLI->>CLI: Read auth token from config

    CLI->>API: POST /api/v1/servers<br/>Authorization: Bearer {token}<br/>{<br/>  name: "payment-mcp",<br/>  endpoint: "https://pay.internal:8443",<br/>  transport: "http",<br/>  sensitivity_level: "high",<br/>  team_id: "team-finance-uuid"<br/>}

    API->>API: Authenticate user
    API->>API: Check permission:<br/>server:create

    alt Has Permission
        API->>VALIDATOR: Validate server registration

        VALIDATOR->>MCP: GET https://pay.internal:8443/health<br/>Timeout: 10s

        alt Server Reachable
            MCP-->>VALIDATOR: 200 OK {status: "healthy"}

            VALIDATOR->>MCP: GET /mcp/v1/capabilities

            MCP-->>VALIDATOR: {<br/>  protocol_version: "2025-06-18",<br/>  capabilities: ["tools"],<br/>  server_info: {<br/>    name: "Payment Processing MCP",<br/>    version: "1.0.0"<br/>  }<br/>}

            VALIDATOR->>MCP: POST /mcp/v1<br/>{method: "tools/list"}

            MCP-->>VALIDATOR: {<br/>  tools: [<br/>    {<br/>      name: "process_payment",<br/>      description: "Process credit card payment",<br/>      inputSchema: {...}<br/>    },<br/>    {<br/>      name: "refund_payment",<br/>      description: "Issue refund",<br/>      inputSchema: {...}<br/>    }<br/>  ]<br/>}

            VALIDATOR->>VALIDATOR: Validate tool schemas<br/>(JSON Schema compliance)

            VALIDATOR-->>API: Server valid:<br/>2 tools discovered

            API->>DB: BEGIN TRANSACTION

            API->>DB: INSERT INTO mcp_servers<br/>{<br/>  id: {generated-uuid},<br/>  name: "payment-mcp",<br/>  endpoint: "https://pay.internal:8443",<br/>  transport: "http",<br/>  mcp_version: "2025-06-18",<br/>  capabilities: ["tools"],<br/>  sensitivity_level: "high",<br/>  status: "active",<br/>  owner_id: {user_id},<br/>  team_id: "team-finance-uuid",<br/>  consul_id: "manual://payment-mcp",<br/>  tags: ["payment", "manual-registration"]<br/>}

            DB-->>API: Server created

            loop For each tool
                API->>DB: INSERT INTO mcp_tools<br/>{<br/>  server_id: {server_uuid},<br/>  name: "process_payment",<br/>  description: "...",<br/>  parameters: {...},<br/>  sensitivity_level: "high",<br/>  requires_approval: true<br/>}
            end

            DB-->>API: Tools created

            API->>DB: COMMIT TRANSACTION

            API->>AUDIT: Log event:<br/>server_registered

            AUDIT-->>API: Event logged

            API-->>CLI: 201 Created<br/>{<br/>  id: {server_uuid},<br/>  name: "payment-mcp",<br/>  status: "active",<br/>  tools_count: 2,<br/>  message: "Server registered successfully"<br/>}

            CLI-->>USER: ✅ Server registered successfully<br/>ID: {server_uuid}<br/>Tools discovered: 2

        else Server Unreachable
            MCP-->>VALIDATOR: Timeout or connection refused

            VALIDATOR-->>API: Validation failed:<br/>"Cannot reach MCP server"

            API-->>CLI: 400 Bad Request<br/>{<br/>  error: "Server validation failed",<br/>  detail: "Cannot connect to https://pay.internal:8443"<br/>}

            CLI-->>USER: ❌ Registration failed<br/>Server unreachable
        end
    else No Permission
        API-->>CLI: 403 Forbidden<br/>{<br/>  error: "Insufficient permissions",<br/>  required: "server:create"<br/>}

        CLI-->>USER: ❌ Permission denied
    end
```

## Discovery Method Comparison

```mermaid
graph TB
    subgraph "Comparison Matrix"
        direction TB

        K8S_BOX[Kubernetes Discovery]
        CONSUL_BOX[Consul Discovery]
        NET_BOX[Network Scanning]
        MANUAL_BOX[Manual Registration]
    end

    K8S_BOX -.->|Pros| K8S_PROS["✅ Automatic<br/>✅ Real-time (watch API)<br/>✅ Metadata rich<br/>✅ Reliable"]
    K8S_BOX -.->|Cons| K8S_CONS["❌ K8s only<br/>❌ Requires RBAC setup"]
    K8S_BOX -.->|Use Case| K8S_USE["Cloud-native deployments"]

    CONSUL_BOX -.->|Pros| CONSUL_PROS["✅ Automatic<br/>✅ Cross-platform<br/>✅ Service health checks<br/>✅ Tags and metadata"]
    CONSUL_BOX -.->|Cons| CONSUL_CONS["❌ Requires Consul<br/>❌ Manual service registration"]
    CONSUL_BOX -.->|Use Case| CONSUL_USE["Multi-cloud, hybrid cloud"]

    NET_BOX -.->|Pros| NET_PROS["✅ No dependencies<br/>✅ Finds shadow IT<br/>✅ Works anywhere"]
    NET_BOX -.->|Cons| NET_CONS["❌ Slow (scanning)<br/>❌ May be intrusive<br/>❌ False positives"]
    NET_BOX -.->|Use Case| NET_USE["Security audit, compliance"]

    MANUAL_BOX -.->|Pros| MANUAL_PROS["✅ Full control<br/>✅ Pre-validated<br/>✅ Works always"]
    MANUAL_BOX -.->|Cons| MANUAL_CONS["❌ Manual effort<br/>❌ Human error risk<br/>❌ Doesn't scale"]
    MANUAL_BOX -.->|Use Case| MANUAL_USE["Legacy systems, initial setup"]

    style K8S_BOX fill:#4a90e2,color:#fff
    style CONSUL_BOX fill:#50c878,color:#fff
    style NET_BOX fill:#ffd43b,color:#000
    style MANUAL_BOX fill:#9775fa,color:#fff
```

## Discovery Configuration

Example configuration in `.env`:

```bash
# Discovery Service Configuration
DISCOVERY_INTERVAL_SECONDS=300  # Run every 5 minutes

# Enable/disable discovery methods
DISCOVERY_K8S_ENABLED=true
DISCOVERY_CONSUL_ENABLED=true
DISCOVERY_NETWORK_SCAN_ENABLED=false  # Disabled by default (intrusive)

# Kubernetes Discovery
K8S_NAMESPACE=all  # or specific namespace
K8S_LABEL_SELECTOR=mcp.server=true

# Consul Discovery
CONSUL_HOST=localhost
CONSUL_PORT=8500
CONSUL_SERVICE_TAG=mcp

# Network Scanner
NETWORK_SCAN_RANGES=10.0.0.0/8,172.16.0.0/12
NETWORK_SCAN_PORTS=8080,8443,3000
NETWORK_SCAN_TIMEOUT_SECONDS=5
NETWORK_SCAN_THREADS=10  # Parallel scan threads
```

## Best Practices

1. **Use Kubernetes Discovery** for cloud-native deployments
2. **Use Consul Discovery** for hybrid/multi-cloud environments
3. **Avoid Network Scanning** in production (use only for audits)
4. **Manual Registration** for legacy systems or one-off servers
5. **Regular Health Checks** to mark stale servers as INACTIVE
6. **Signature Verification** for critical/high-sensitivity servers
7. **Audit All Discoveries** for security review

## Next Steps

- [Server Management](../API_REFERENCE.md#servers) - API documentation
- [Health Checks](../OPERATIONS_RUNBOOK.md#health-checks) - Monitoring guide
- [Security](../SECURITY.md) - Security best practices
