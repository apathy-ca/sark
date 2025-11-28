# Gateway Integration API Reference

**Version:** 1.1.0
**Status:** Production Ready
**Last Updated:** 2025

---

## Overview

SARK v1.1.0 provides REST APIs for MCP Gateway authorization and management. These APIs enable the MCP Gateway Registry to authorize tool invocations, agent-to-agent communication, and server access before routing requests to MCP servers.

**Key Features:**
- Authorization decision API for Gateway requests
- Agent-to-Agent (A2A) authorization
- Server and tool enumeration
- Audit logging and event tracking
- Policy-based access control via OPA
- Parameter filtering and validation

---

## Base URL

```
http://<sark-host>:<sark-port>/api/v1/gateway
```

**Default:** `http://localhost:8000/api/v1/gateway`

---

## Authentication

All Gateway API endpoints require JWT authentication via Bearer token.

### Request Format

```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Authentication Methods

1. **User JWT Token** - Standard SARK user authentication
2. **Gateway API Key** - Dedicated API key for Gateway service (recommended)
3. **Agent JWT Token** - Agent-specific tokens for A2A authorization

See [AUTHENTICATION.md](./AUTHENTICATION.md) for detailed setup.

---

## Endpoints

### 1. POST /api/v1/gateway/authorize

Authorize a Gateway request before routing to an MCP server.

**Use Case:** Gateway calls this endpoint before invoking a tool on behalf of a user.

#### Request

```json
{
  "action": "gateway:tool:invoke",
  "server_name": "postgres-mcp",
  "tool_name": "execute_query",
  "parameters": {
    "query": "SELECT * FROM users WHERE id = ?",
    "params": [123]
  },
  "user": {
    "id": "user_abc123",
    "email": "alice@example.com",
    "roles": ["analyst"]
  },
  "gateway_metadata": {
    "request_id": "req_abc123",
    "timestamp": "2025-01-15T10:30:00Z",
    "source_ip": "10.0.1.5"
  }
}
```

#### Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | Action type: `gateway:tool:invoke`, `gateway:server:access`, `gateway:resource:read` |
| `server_name` | string | Yes | MCP server name (e.g., `postgres-mcp`, `github-mcp`) |
| `tool_name` | string | Conditional | Tool name (required for `gateway:tool:invoke`) |
| `parameters` | object | No | Tool parameters (subject to filtering) |
| `user` | object | Yes | User context (id, email, roles) |
| `gateway_metadata` | object | No | Gateway request metadata |

#### Response (Allow)

```json
{
  "allow": true,
  "reason": "Allowed by policy: users can query their own data",
  "filtered_parameters": {
    "query": "SELECT * FROM users WHERE id = ?",
    "params": [123]
  },
  "audit_id": "audit_789xyz",
  "cache_ttl": 60,
  "metadata": {
    "policy_version": "1.2.0",
    "evaluated_at": "2025-01-15T10:30:01Z"
  }
}
```

#### Response (Deny)

```json
{
  "allow": false,
  "reason": "Insufficient permissions: user lacks 'admin' role for DROP operations",
  "cache_ttl": 0,
  "metadata": {
    "policy_version": "1.2.0",
    "evaluated_at": "2025-01-15T10:30:01Z"
  }
}
```

#### Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `allow` | boolean | Authorization decision (true = allow, false = deny) |
| `reason` | string | Human-readable reason for the decision |
| `filtered_parameters` | object | Parameters after filtering (only if `allow: true`) |
| `audit_id` | string | Audit event ID for tracking (only if `allow: true`) |
| `cache_ttl` | integer | Cache TTL in seconds (0 = do not cache) |
| `metadata` | object | Additional metadata (policy version, timestamps) |

#### Status Codes

- `200 OK` - Authorization decision made (check `allow` field)
- `400 Bad Request` - Invalid request format
- `401 Unauthorized` - Missing or invalid authentication
- `503 Service Unavailable` - Gateway integration not enabled (`GATEWAY_ENABLED=false`)

---

### 2. POST /api/v1/gateway/authorize-a2a

Authorize Agent-to-Agent (A2A) communication.

**Use Case:** An agent requests authorization to call tools on another agent via the Gateway.

#### Request

```json
{
  "action": "a2a:invoke",
  "source_agent": {
    "id": "agent_123",
    "name": "research-agent",
    "trust_level": "high",
    "capabilities": ["research", "web_search"]
  },
  "target_agent": {
    "id": "agent_456",
    "name": "database-agent",
    "capabilities": ["query", "analytics"]
  },
  "tool_name": "query_database",
  "parameters": {
    "query": "SELECT COUNT(*) FROM events WHERE date > '2025-01-01'"
  },
  "context": {
    "workflow_id": "wf_789",
    "user_id": "user_abc123"
  }
}
```

#### Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | A2A action type: `a2a:invoke`, `a2a:delegate` |
| `source_agent` | object | Yes | Calling agent details (id, name, trust_level, capabilities) |
| `target_agent` | object | Yes | Target agent details (id, name, capabilities) |
| `tool_name` | string | Yes | Tool name to invoke on target agent |
| `parameters` | object | No | Tool parameters |
| `context` | object | No | Execution context (workflow_id, user_id) |

#### Response (Allow)

```json
{
  "allow": true,
  "reason": "A2A allowed: high-trust agent can query database agent",
  "filtered_parameters": {
    "query": "SELECT COUNT(*) FROM events WHERE date > '2025-01-01'"
  },
  "audit_id": "audit_a2a_xyz",
  "cache_ttl": 300,
  "max_delegation_depth": 2
}
```

#### Response (Deny)

```json
{
  "allow": false,
  "reason": "A2A denied: insufficient trust level (required: high, actual: medium)",
  "cache_ttl": 0
}
```

#### Status Codes

- `200 OK` - Authorization decision made
- `400 Bad Request` - Invalid request format
- `401 Unauthorized` - Missing or invalid authentication
- `503 Service Unavailable` - A2A authorization not enabled (`A2A_ENABLED=false`)

---

### 3. GET /api/v1/gateway/servers

List MCP servers the authenticated user is authorized to access.

**Use Case:** Gateway queries this endpoint to populate server dropdowns or validate access.

#### Request

```bash
curl -X GET http://localhost:8000/api/v1/gateway/servers \
  -H "Authorization: Bearer $TOKEN"
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | Filter servers by user ID (optional, defaults to authenticated user) |
| `include_tools` | boolean | Include tool list for each server (default: `false`) |

#### Response

```json
{
  "servers": [
    {
      "name": "postgres-mcp",
      "description": "PostgreSQL database access",
      "url": "mcp://postgres-server:5000",
      "allowed_actions": ["query", "read"],
      "tools": [
        {
          "name": "execute_query",
          "description": "Execute SQL SELECT queries",
          "allowed": true
        },
        {
          "name": "execute_mutation",
          "description": "Execute INSERT/UPDATE/DELETE",
          "allowed": false
        }
      ]
    },
    {
      "name": "github-mcp",
      "description": "GitHub API access",
      "url": "mcp://github-server:5001",
      "allowed_actions": ["read", "write"],
      "tools": []
    }
  ]
}
```

#### Status Codes

- `200 OK` - Server list returned
- `401 Unauthorized` - Missing or invalid authentication
- `503 Service Unavailable` - Gateway integration not enabled

---

### 4. GET /api/v1/gateway/tools

List tools available on a specific MCP server for the authenticated user.

**Use Case:** Gateway queries this endpoint to show available tools for a server.

#### Request

```bash
curl -X GET "http://localhost:8000/api/v1/gateway/tools?server_name=postgres-mcp" \
  -H "Authorization: Bearer $TOKEN"
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_name` | string | Yes | MCP server name |
| `user_id` | string | No | Filter tools by user ID (defaults to authenticated user) |

#### Response

```json
{
  "server_name": "postgres-mcp",
  "tools": [
    {
      "name": "execute_query",
      "description": "Execute SQL SELECT queries",
      "allowed": true,
      "parameters": {
        "query": {
          "type": "string",
          "required": true,
          "description": "SQL query to execute"
        },
        "params": {
          "type": "array",
          "required": false,
          "description": "Query parameters"
        }
      }
    },
    {
      "name": "list_tables",
      "description": "List all database tables",
      "allowed": true,
      "parameters": {}
    },
    {
      "name": "execute_mutation",
      "description": "Execute INSERT/UPDATE/DELETE",
      "allowed": false,
      "reason": "User lacks 'admin' role"
    }
  ]
}
```

#### Status Codes

- `200 OK` - Tool list returned
- `400 Bad Request` - Missing `server_name` parameter
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Server not found
- `503 Service Unavailable` - Gateway integration not enabled

---

### 5. POST /api/v1/gateway/audit

Log a Gateway audit event for SIEM integration.

**Use Case:** Gateway logs authorization decisions, tool invocations, and errors.

#### Request

```json
{
  "event_type": "tool_invocation",
  "server_name": "postgres-mcp",
  "tool_name": "execute_query",
  "user_id": "user_abc123",
  "authorization_decision": "allow",
  "timestamp": "2025-01-15T10:30:00Z",
  "metadata": {
    "request_id": "req_abc123",
    "duration_ms": 45,
    "source_ip": "10.0.1.5"
  }
}
```

#### Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | Yes | Event type: `tool_invocation`, `authorization`, `error`, `a2a_request` |
| `server_name` | string | Conditional | MCP server name (required for `tool_invocation`) |
| `tool_name` | string | Conditional | Tool name (required for `tool_invocation`) |
| `user_id` | string | Yes | User ID associated with the event |
| `authorization_decision` | string | No | Authorization decision: `allow`, `deny` |
| `timestamp` | string | Yes | ISO 8601 timestamp |
| `metadata` | object | No | Additional event metadata |

#### Response

```json
{
  "audit_id": "audit_789xyz",
  "status": "logged",
  "timestamp": "2025-01-15T10:30:01Z"
}
```

#### Status Codes

- `201 Created` - Audit event logged
- `400 Bad Request` - Invalid event format
- `401 Unauthorized` - Missing or invalid authentication
- `503 Service Unavailable` - Gateway integration not enabled

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "GATEWAY_NOT_ENABLED",
    "message": "Gateway integration not enabled. Set GATEWAY_ENABLED=true to enable.",
    "details": {
      "feature_flag": "GATEWAY_ENABLED",
      "current_value": false
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `GATEWAY_NOT_ENABLED` | 503 | Gateway integration disabled (`GATEWAY_ENABLED=false`) |
| `A2A_NOT_ENABLED` | 503 | A2A authorization disabled (`A2A_ENABLED=false`) |
| `INVALID_REQUEST` | 400 | Malformed request body or missing required fields |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication token |
| `FORBIDDEN` | 403 | Valid authentication but insufficient permissions |
| `SERVER_NOT_FOUND` | 404 | MCP server not registered in SARK |
| `TOOL_NOT_FOUND` | 404 | Tool not available on the specified server |
| `POLICY_EVALUATION_ERROR` | 500 | OPA policy evaluation failed |
| `GATEWAY_TIMEOUT` | 504 | Gateway request timed out |

---

## Rate Limiting

Gateway API endpoints are rate-limited to prevent abuse:

- **User JWT**: 1000 requests/minute
- **Gateway API Key**: 10,000 requests/minute
- **Agent JWT**: 5000 requests/minute

Rate limit headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642252800
```

When rate limit is exceeded:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```

**HTTP Status:** `429 Too Many Requests`

---

## Caching

Authorization decisions can be cached by the Gateway to improve performance:

- `cache_ttl > 0` - Decision can be cached for the specified seconds
- `cache_ttl = 0` - Decision should NOT be cached (e.g., for denials or sensitive operations)

**Example:**

```json
{
  "allow": true,
  "cache_ttl": 60  // Cache for 60 seconds
}
```

**Cache Key:** `sha256(action + server_name + tool_name + user_id + parameters)`

---

## Versioning

The Gateway API follows semantic versioning:

- **Current Version:** `v1`
- **Base Path:** `/api/v1/gateway`
- **Version Header:** `X-API-Version: 1`

Future versions will be accessible via `/api/v2/gateway`, maintaining backwards compatibility.

---

## Examples

### Example 1: Authorize a Database Query

```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "parameters": {
      "query": "SELECT * FROM users WHERE department = ?",
      "params": ["engineering"]
    },
    "user": {
      "id": "user_123",
      "email": "alice@example.com",
      "roles": ["analyst"]
    }
  }'
```

**Response:**

```json
{
  "allow": true,
  "reason": "Allowed: user can query their department data",
  "filtered_parameters": {
    "query": "SELECT * FROM users WHERE department = ?",
    "params": ["engineering"]
  },
  "audit_id": "audit_abc",
  "cache_ttl": 60
}
```

### Example 2: List Authorized Servers

```bash
curl -X GET http://localhost:8000/api/v1/gateway/servers \
  -H "Authorization: Bearer $USER_TOKEN"
```

**Response:**

```json
{
  "servers": [
    {
      "name": "postgres-mcp",
      "description": "PostgreSQL database access",
      "url": "mcp://postgres-server:5000",
      "allowed_actions": ["query", "read"]
    },
    {
      "name": "github-mcp",
      "description": "GitHub API access",
      "url": "mcp://github-server:5001",
      "allowed_actions": ["read"]
    }
  ]
}
```

### Example 3: Agent-to-Agent Authorization

```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize-a2a \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "a2a:invoke",
    "source_agent": {
      "id": "agent_research",
      "name": "research-agent",
      "trust_level": "high"
    },
    "target_agent": {
      "id": "agent_db",
      "name": "database-agent"
    },
    "tool_name": "query_database",
    "parameters": {
      "query": "SELECT COUNT(*) FROM events"
    }
  }'
```

**Response:**

```json
{
  "allow": true,
  "reason": "A2A allowed: high-trust agent",
  "audit_id": "audit_a2a_123",
  "cache_ttl": 300
}
```

---

## Next Steps

- **Authentication Setup:** See [AUTHENTICATION.md](./AUTHENTICATION.md)
- **Policy Configuration:** See [configuration/POLICY_CONFIGURATION.md](./configuration/POLICY_CONFIGURATION.md)
- **Deployment Guide:** See [deployment/QUICKSTART.md](./deployment/QUICKSTART.md)
- **Troubleshooting:** See [runbooks/TROUBLESHOOTING.md](./runbooks/TROUBLESHOOTING.md)

---

**API Reference Version:** 1.1.0
**Last Updated:** 2025
