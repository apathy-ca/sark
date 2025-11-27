# MCP Tool Invocation Flow

## Overview
This diagram shows the complete end-to-end sequence when an AI assistant invokes an MCP tool through SARK, including authentication, authorization, caching, audit, and error handling.

## Complete Invocation Sequence

```mermaid
sequenceDiagram
    participant AI as AI Assistant<br/>(Claude/GPT)
    participant Kong as Kong Gateway<br/>(Edge Security)
    participant API as SARK API<br/>(FastAPI)
    participant Auth as Auth Service<br/>(JWT/OIDC)
    participant Cache as Redis Cache<br/>(Policy Cache)
    participant OPA as Open Policy Agent<br/>(Authorization)
    participant Audit as Audit Service<br/>(TimescaleDB)
    participant MCP as MCP Server<br/>(Tool Provider)
    participant SIEM as SIEM<br/>(Splunk/Datadog)

    Note over AI,SIEM: Successful Tool Invocation Flow

    %% Request Phase
    rect rgb(220, 240, 255)
        Note over AI,API: Phase 1: Request & Authentication
        AI->>Kong: POST /api/v1/tools/invoke<br/>Authorization: Bearer {jwt}<br/>Body: {tool_id, parameters}
        Kong->>Kong: Rate limiting check<br/>(1000 req/min default)
        Kong->>Kong: WAF validation<br/>(SQL injection, XSS, etc.)
        Kong->>API: Forward request
    end

    %% Authentication Phase
    rect rgb(255, 240, 220)
        Note over API,Auth: Phase 2: Identity Verification
        API->>Auth: Validate JWT token
        Auth->>Auth: Verify signature (RS256)
        Auth->>Auth: Check expiration
        Auth->>Auth: Extract user context:<br/>{user_id, roles, teams, permissions}
        Auth-->>API: User context valid
    end

    %% Authorization Phase - Cache Hit
    rect rgb(220, 255, 220)
        Note over API,OPA: Phase 3: Authorization (Cache Hit Path)
        API->>Cache: GET policy:decision:{hash}<br/>hash = SHA256(user_id + tool_id + context)

        alt Cache Hit (>95% of requests)
            Cache-->>API: Cached decision:<br/>{allow: true, reason: "...", ttl: 60s}
            Note over API: Response time: <5ms
            API->>API: Validate TTL not expired
        else Cache Miss (<5% of requests)
            Cache-->>API: null (miss)

            API->>OPA: POST /v1/data/mcp/allow<br/>input: {<br/>  user: {id, roles, teams},<br/>  tool: {id, sensitivity, server},<br/>  action: "tool:invoke",<br/>  context: {time, ip, mfa_verified}<br/>}

            OPA->>OPA: Load policy bundle<br/>(mcp.authorization.rego)
            OPA->>OPA: Evaluate rules:<br/>• Role check (RBAC)<br/>• Sensitivity level check<br/>• Time-based restrictions<br/>• IP allowlist check<br/>• MFA requirement<br/>• Break-glass approval

            OPA-->>API: {<br/>  allow: true,<br/>  reason: "User role 'data_analyst' allowed for 'medium' sensitivity tools",<br/>  filtered_parameters: {...}<br/>}
            Note over OPA: Response time: <50ms

            API->>Cache: SETEX policy:decision:{hash}<br/>TTL: 60 seconds<br/>Value: {decision, reason}
        end
    end

    %% Tool Invocation Phase
    rect rgb(240, 220, 255)
        Note over API,MCP: Phase 4: Tool Execution
        API->>API: Validate tool exists<br/>Query: SELECT * FROM mcp_tools WHERE id = ?
        API->>API: Apply parameter filtering<br/>(from OPA decision)
        API->>API: Build MCP protocol request:<br/>{<br/>  jsonrpc: "2.0",<br/>  method: "tools/call",<br/>  params: {<br/>    name: "database_query",<br/>    arguments: {...}<br/>  }<br/>}

        API->>MCP: POST /mcp/v1<br/>Content-Type: application/json<br/>X-SARK-Request-ID: {uuid}<br/>Body: {MCP request}

        MCP->>MCP: Validate request schema<br/>(JSON-RPC 2.0)
        MCP->>MCP: Execute tool:<br/>database_query({...})
        MCP->>MCP: Query backend database
        MCP-->>API: {<br/>  jsonrpc: "2.0",<br/>  result: {<br/>    content: [{type: "text", text: "Query results..."}]<br/>  }<br/>}
    end

    %% Audit Phase
    rect rgb(255, 220, 220)
        Note over API,SIEM: Phase 5: Audit & Monitoring (Async)
        par Audit Logging
            API->>Audit: INSERT INTO audit_events<br/>{<br/>  event_type: "tool_invocation",<br/>  user_id, tool_id, decision: "allow",<br/>  timestamp, duration_ms,<br/>  parameters: {redacted},<br/>  result_summary: "success"<br/>}
            Audit-->>API: Event logged (async)
        and SIEM Forwarding
            API->>SIEM: POST /services/collector<br/>Batch: [audit_events]<br/>(async, batched every 5s)
            SIEM-->>API: 200 OK (async)
        and Metrics Update
            API->>API: Update metrics:<br/>• tool_invocation_total{tool=X}++<br/>• tool_invocation_duration{tool=X}<br/>• policy_cache_hit_ratio
        end
    end

    %% Response Phase
    rect rgb(220, 255, 240)
        Note over AI,API: Phase 6: Response
        API-->>Kong: 200 OK<br/>Headers:<br/>  X-Request-ID: {uuid}<br/>  X-Cache-Status: HIT<br/>  X-Policy-Decision: ALLOW<br/>Body:<br/>  {result: {...}, audit_id: {uuid}}
        Kong-->>AI: 200 OK + response
        Note over AI: Total latency: <100ms (p95)
    end
```

## Denial Flow

```mermaid
sequenceDiagram
    participant AI as AI Assistant
    participant API as SARK API
    participant OPA as Open Policy Agent
    participant Audit as Audit Service
    participant SIEM as SIEM

    Note over AI,SIEM: Tool Invocation Denied

    AI->>API: POST /api/v1/tools/invoke<br/>{tool_id: "delete_database", ...}
    API->>OPA: Evaluate policy

    OPA->>OPA: Check rules:<br/>✗ User role 'viewer' cannot<br/>  invoke 'critical' sensitivity tools

    OPA-->>API: {<br/>  allow: false,<br/>  reason: "Insufficient permissions: 'viewer' role cannot access 'critical' sensitivity tools",<br/>  required_roles: ["admin", "dba"]<br/>}

    API->>Audit: Log denial event<br/>{event_type: "authorization_denied"}
    Audit-->>API: Event logged

    API->>SIEM: Forward security event<br/>(high priority)
    SIEM-->>API: Acknowledged

    API-->>AI: 403 Forbidden<br/>{<br/>  error: "Access denied",<br/>  reason: "Insufficient permissions",<br/>  required_roles: ["admin", "dba"],<br/>  audit_id: {uuid}<br/>}

    Note over AI: User receives clear denial reason<br/>Can request approval if needed
```

## Error Handling Flow

```mermaid
sequenceDiagram
    participant AI as AI Assistant
    participant API as SARK API
    participant MCP as MCP Server
    participant Audit as Audit Service

    Note over AI,Audit: MCP Server Error Handling

    AI->>API: POST /api/v1/tools/invoke
    API->>API: Authentication ✓
    API->>API: Authorization ✓

    API->>MCP: Invoke tool

    alt MCP Server Timeout
        MCP-->>API: (timeout after 30s)
        API->>API: Circuit breaker: OPEN<br/>Mark server as UNHEALTHY
        API->>Audit: Log error event
        API-->>AI: 504 Gateway Timeout<br/>{error: "MCP server timeout",<br/> server_status: "unhealthy"}

    else MCP Server Error
        MCP-->>API: 500 Internal Server Error<br/>{error: {code: -32603, message: "Database connection failed"}}
        API->>Audit: Log MCP error
        API-->>AI: 502 Bad Gateway<br/>{error: "MCP server error",<br/> details: "Database connection failed"}

    else Invalid Tool Parameters
        MCP-->>API: 400 Bad Request<br/>{error: {code: -32602, message: "Invalid params: 'limit' must be integer"}}
        API->>Audit: Log validation error
        API-->>AI: 400 Bad Request<br/>{error: "Invalid parameters",<br/> validation_errors: [...]}
    end
```

## Caching Strategy

```mermaid
graph TB
    Request[Tool Invocation Request]
    Hash[Compute Cache Key<br/>SHA256 user_id + tool_id + context]

    Request --> Hash
    Hash --> Check{Cache<br/>Hit?}

    Check -->|Yes >95%| Return[Return Cached Decision<br/>Latency: <5ms]
    Check -->|No <5%| OPA[Evaluate with OPA<br/>Latency: <50ms]

    OPA --> Store[Store in Cache<br/>TTL: 60s for Medium sensitivity<br/>TTL: 30s for High sensitivity<br/>TTL: 600s for Low sensitivity]

    Store --> Return2[Return Fresh Decision]

    Return --> Response[API Response]
    Return2 --> Response

    style Check fill:#4a90e2,color:#fff
    style Return fill:#50c878,color:#fff
    style OPA fill:#ffd43b,color:#000
```

## Performance Targets

| Metric | Target | Measurement Point |
|--------|--------|-------------------|
| **Authentication** | <10ms p95 | JWT validation |
| **Cache Hit** | <5ms p95 | Redis lookup + return |
| **Cache Miss** | <50ms p95 | OPA policy evaluation |
| **MCP Tool Call** | Variable | Depends on backend system |
| **Audit Logging** | <1ms | Async, non-blocking |
| **Total Latency** | <100ms p95 | End-to-end (excluding tool execution) |
| **Cache Hit Ratio** | >95% | Redis cache effectiveness |

## Security Checks

Each invocation passes through multiple security layers:

1. **Network Layer**
   - Rate limiting (1,000 req/min default)
   - WAF (Web Application Firewall)
   - DDoS protection

2. **Authentication Layer**
   - JWT signature validation
   - Token expiration check
   - User identity verification
   - MFA validation (if required)

3. **Authorization Layer**
   - Role-based access control (RBAC)
   - Sensitivity level matching
   - Time-based restrictions
   - IP allowlist validation
   - Break-glass approval workflow

4. **Protocol Layer**
   - MCP protocol validation
   - JSON-RPC 2.0 compliance
   - Tool parameter schema validation
   - Result sanitization

5. **Audit Layer**
   - Immutable event logging
   - SIEM forwarding
   - Metrics collection
   - Alerting on anomalies

## Audit Event Structure

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "tool_invocation",
  "timestamp": "2025-11-27T10:30:45.123Z",
  "user": {
    "id": "user-123",
    "email": "analyst@company.com",
    "roles": ["data_analyst"],
    "teams": ["analytics-team"]
  },
  "tool": {
    "id": "tool-456",
    "name": "database_query",
    "server": "mcp-data-server",
    "sensitivity": "medium"
  },
  "decision": {
    "allow": true,
    "reason": "User role 'data_analyst' allowed for 'medium' sensitivity tools",
    "policy_version": "v1.2.3",
    "cache_hit": true
  },
  "request": {
    "parameters": {
      "query": "SELECT *** REDACTED ***",
      "limit": 100
    },
    "ip_address": "10.0.1.45",
    "user_agent": "Claude-AI/1.0"
  },
  "response": {
    "status": "success",
    "duration_ms": 245,
    "result_size_bytes": 4096
  },
  "context": {
    "request_id": "req-789",
    "session_id": "sess-012",
    "mfa_verified": true,
    "compliance_tags": ["SOC2", "GDPR"]
  }
}
```

## Next Steps

For implementation details, see:
- [OPA Policy Guide](../OPA_POLICY_GUIDE.md) - Policy authoring
- [API Reference](../API_REFERENCE.md) - API endpoints
- [Audit Guide](../AUDIT.md) - Audit event schema
