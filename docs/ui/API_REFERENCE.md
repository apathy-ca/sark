# SARK API Reference for UI Development

This document provides a comprehensive reference of SARK's REST API endpoints for frontend developers building the React UI.

**Base URL:** `http://localhost:8000`

**API Version:** `v1`

**API Prefix:** `/api/v1`

---

## Table of Contents

1. [Authentication](#authentication)
2. [MCP Servers](#mcp-servers)
3. [Tools](#tools)
4. [Policies](#policies)
5. [Audit & Sessions](#audit--sessions)
6. [API Keys](#api-keys)
7. [Bulk Operations](#bulk-operations)
8. [Health](#health)
9. [Data Models](#data-models)
10. [Error Handling](#error-handling)

---

## Authentication

All endpoints (except `/health` and `/auth/login/*`) require authentication via JWT Bearer token.

### Auth Header Format

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### POST `/api/v1/auth/login/ldap`

Authenticate with LDAP credentials.

**Request:**
```json
{
  "username": "john.doe",
  "password": "password"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "rt_abc123...",
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john.doe",
    "email": "john.doe@example.com",
    "roles": ["developer", "team_lead"],
    "teams": ["engineering"]
  }
}
```

### POST `/api/v1/auth/login/oidc`

Initiate OIDC authentication flow.

**Response:** `302 Redirect` to IdP authorization URL

### POST `/api/v1/auth/refresh`

Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "rt_abc123..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "rt_xyz789..."
}
```

### GET `/api/v1/auth/me`

Get current authenticated user info.

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "roles": ["developer", "team_lead"],
  "teams": ["engineering", "platform"],
  "permissions": ["server:read", "server:write", "tool:invoke"]
}
```

### POST `/api/v1/auth/logout`

Logout and invalidate session.

**Request:**
```json
{
  "refresh_token": "rt_abc123..."
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## MCP Servers

### GET `/api/v1/servers`

List all registered MCP servers with pagination and filtering.

**Query Parameters:**
- `limit` (int, 1-200, default: 50) - Items per page
- `cursor` (string, optional) - Pagination cursor
- `sort_order` (string, "asc"|"desc", default: "desc") - Sort order
- `status` (string, optional) - Filter by status (comma-separated)
- `sensitivity` (string, optional) - Filter by sensitivity level (comma-separated)
- `team_id` (UUID, optional) - Filter by team
- `owner_id` (UUID, optional) - Filter by owner
- `tags` (string, optional) - Filter by tags (comma-separated)
- `match_all_tags` (boolean, default: false) - Match all tags (AND) vs any (OR)
- `search` (string, optional) - Full-text search on name/description
- `include_total` (boolean, default: false) - Include total count (expensive)

**Example:**
```http
GET /api/v1/servers?limit=20&status=active&sensitivity=high&search=analytics
```

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "name": "analytics-db-server",
      "transport": "http",
      "status": "active",
      "sensitivity_level": "high",
      "created_at": "2025-11-27T10:30:00Z"
    }
  ],
  "next_cursor": "eyJpZCI6IjZiYTdiODEw...",
  "has_more": true,
  "total": 150
}
```

### GET `/api/v1/servers/{server_id}`

Get detailed information about a specific MCP server.

**Path Parameters:**
- `server_id` (UUID) - Server identifier

**Response:** `200 OK`
```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "analytics-db-server",
  "description": "Analytics database server with query tools",
  "transport": "http",
  "endpoint": "http://analytics.internal.example.com:8080",
  "status": "active",
  "sensitivity_level": "high",
  "tools": [
    {
      "id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
      "name": "execute_query",
      "description": "Execute SQL query on analytics database",
      "sensitivity_level": "high"
    }
  ],
  "metadata": {
    "team": "data-engineering",
    "owner": "john.doe@example.com",
    "environment": "production"
  },
  "created_at": "2025-11-27T10:30:00Z"
}
```

### POST `/api/v1/servers`

Register a new MCP server.

**Request:**
```json
{
  "name": "analytics-db-server",
  "description": "Analytics database server with query tools",
  "transport": "http",
  "endpoint": "http://analytics.internal.example.com:8080",
  "version": "2025-06-18",
  "capabilities": ["tools"],
  "tools": [
    {
      "name": "execute_query",
      "description": "Execute SQL query on analytics database",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "database": {"type": "string"}
        }
      },
      "sensitivity_level": "high",
      "requires_approval": false
    }
  ],
  "sensitivity_level": "high",
  "metadata": {
    "team": "data-engineering",
    "owner": "john.doe@example.com"
  }
}
```

**Response:** `201 Created`
```json
{
  "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "registered",
  "consul_id": "analytics-db-server-6ba7b810"
}
```

### PUT `/api/v1/servers/{server_id}`

Update an existing MCP server (full update).

### PATCH `/api/v1/servers/{server_id}`

Partially update an MCP server.

### DELETE `/api/v1/servers/{server_id}`

Deregister an MCP server.

**Response:** `204 No Content`

---

## Tools

### GET `/api/v1/servers/{server_id}/tools`

List all tools for a specific MCP server.

**Response:** `200 OK`
```json
{
  "tools": [
    {
      "id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
      "name": "execute_query",
      "description": "Execute SQL query",
      "parameters": {...},
      "sensitivity_level": "high",
      "requires_approval": false
    }
  ],
  "total": 1
}
```

### GET `/api/v1/servers/{server_id}/tools/{tool_name}`

Get details about a specific tool.

**Response:** `200 OK`
```json
{
  "id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "name": "execute_query",
  "description": "Execute SQL query on analytics database",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "SQL query to execute"
      },
      "database": {
        "type": "string",
        "enum": ["analytics", "reporting"]
      }
    },
    "required": ["query", "database"]
  },
  "sensitivity_level": "high",
  "requires_approval": false,
  "created_at": "2025-11-27T10:30:00Z"
}
```

### POST `/api/v1/servers/{server_id}/tools/{tool_name}/invoke`

Invoke a tool through SARK's governance layer.

**Request:**
```json
{
  "query": "SELECT * FROM users WHERE status = 'active'",
  "database": "analytics",
  "limit": 100
}
```

**Response:** `200 OK` (if allowed)
```json
{
  "success": true,
  "result": {
    "rows_returned": 10,
    "columns": ["id", "email", "created_at"],
    "execution_time_ms": 45,
    "data": [...]
  },
  "audit_id": "audit_def456",
  "policy_decision": "allow"
}
```

**Response:** `403 Forbidden` (if denied)
```json
{
  "detail": {
    "decision": "deny",
    "reason": "Query contains forbidden keywords (DELETE)",
    "audit_id": "audit_ghi789"
  }
}
```

---

## Policies

### POST `/api/v1/policy/evaluate`

Evaluate a policy decision without invoking the tool (dry run).

**Request:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "tool:invoke",
  "tool": "execute_query",
  "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "parameters": {
    "query": "SELECT * FROM users",
    "database": "analytics"
  }
}
```

**Response:** `200 OK`
```json
{
  "decision": "allow",
  "reason": "User has required role and tool sensitivity is within allowed level",
  "requires_approval": false,
  "filtered_parameters": null,
  "audit_id": "audit_123abc"
}
```

### GET `/api/v1/policies`

List all OPA policies loaded in the system.

**Response:** `200 OK`
```json
{
  "policies": [
    {
      "id": "mcp.authorization",
      "name": "MCP Authorization Policy",
      "package": "mcp",
      "rules": ["allow", "deny", "audit_reason"]
    }
  ],
  "total": 1
}
```

### GET `/api/v1/policies/{policy_id}`

Get a specific OPA policy.

### POST `/api/v1/policies`

Upload a new OPA policy.

### PUT `/api/v1/policies/{policy_id}`

Update an existing OPA policy.

### DELETE `/api/v1/policies/{policy_id}`

Delete an OPA policy.

---

## Audit & Sessions

### GET `/api/v1/audit/events`

Query audit events with filtering.

**Query Parameters:**
- `limit` (int, default: 50) - Items per page
- `offset` (int, default: 0) - Pagination offset
- `user_id` (UUID, optional) - Filter by user
- `server_id` (UUID, optional) - Filter by server
- `event_type` (string, optional) - Filter by event type
- `start_time` (ISO 8601, optional) - Events after this time
- `end_time` (ISO 8601, optional) - Events before this time
- `decision` (string, optional) - Filter by policy decision ("allow"|"deny")

**Response:** `200 OK`
```json
{
  "events": [
    {
      "event_id": "audit_def456",
      "event_type": "tool_invocation",
      "timestamp": "2025-11-27T10:35:12.456Z",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_email": "john.doe@example.com",
      "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "server_name": "analytics-db-server",
      "tool_name": "execute_query",
      "decision": "allow",
      "parameters": {
        "query": "SELECT ...",
        "database": "analytics"
      },
      "reason": "User has role 'developer'",
      "duration_ms": 45
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

### GET `/api/v1/audit/metrics`

Get aggregated audit metrics.

**Query Parameters:**
- `period` (string) - Time period ("1h"|"24h"|"7d"|"30d")

**Response:** `200 OK`
```json
{
  "period": "1h",
  "total_events": 150,
  "by_event_type": {
    "tool_invocation": 120,
    "policy_evaluation": 20,
    "authentication_success": 10
  },
  "by_decision": {
    "allow": 140,
    "deny": 10
  },
  "top_tools": [
    {"tool_name": "execute_query", "invocations": 80},
    {"tool_name": "create_report", "invocations": 40}
  ],
  "top_users": [
    {"user_email": "john.doe@example.com", "actions": 50}
  ]
}
```

### GET `/api/v1/sessions`

List active sessions.

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-11-27T10:00:00Z",
      "expires_at": "2025-11-27T11:00:00Z",
      "last_activity": "2025-11-27T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

## API Keys

### GET `/api/auth/api-keys`

List all API keys for the current user.

**Query Parameters:**
- `include_revoked` (boolean, default: false) - Include revoked keys

**Response:** `200 OK`
```json
{
  "api_keys": [
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "name": "CI/CD Pipeline Key",
      "key_prefix": "sark_live_abc",
      "scopes": ["server:read", "server:write"],
      "rate_limit": 1000,
      "created_at": "2025-11-27T10:00:00Z",
      "expires_at": "2026-02-27T10:00:00Z",
      "last_used": "2025-11-27T10:30:00Z"
    }
  ],
  "total": 1
}
```

### POST `/api/auth/api-keys`

Create a new API key.

**Request:**
```json
{
  "name": "CI/CD Pipeline Key",
  "description": "For automated server registration",
  "scopes": ["server:read", "server:write"],
  "rate_limit": 1000,
  "expires_in_days": 90,
  "environment": "live"
}
```

**Response:** `201 Created`
```json
{
  "api_key": {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "name": "CI/CD Pipeline Key",
    "key_prefix": "sark_live_abc"
  },
  "key": "sark_live_abc123def456ghi789jkl012mno345",
  "message": "API key created successfully. Save this key securely!"
}
```

### POST `/api/auth/api-keys/{key_id}/rotate`

Rotate an API key (generate new credentials).

**Response:** `200 OK`
```json
{
  "api_key": {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "name": "CI/CD Pipeline Key",
    "key_prefix": "sark_live_xyz"
  },
  "key": "sark_live_xyz123abc456def789ghi012jkl345",
  "message": "API key rotated successfully. Update your systems immediately!"
}
```

### DELETE `/api/auth/api-keys/{key_id}`

Revoke an API key.

**Response:** `204 No Content`

---

## Bulk Operations

### POST `/api/v1/bulk/servers/register`

Register multiple MCP servers in one request.

**Request:**
```json
{
  "servers": [
    {
      "name": "server-1",
      "transport": "http",
      "endpoint": "http://server1.example.com",
      "capabilities": ["tools"],
      "tools": [],
      "sensitivity_level": "medium"
    },
    {
      "name": "server-2",
      "transport": "http",
      "endpoint": "http://server2.example.com",
      "capabilities": ["tools"],
      "tools": [],
      "sensitivity_level": "medium"
    }
  ],
  "fail_on_first_error": false
}
```

**Response:** `200 OK`
```json
{
  "results": [
    {
      "name": "server-1",
      "success": true,
      "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    },
    {
      "name": "server-2",
      "success": false,
      "error": "Server with this name already exists"
    }
  ],
  "total": 2,
  "successful": 1,
  "failed": 1
}
```

---

## Health

### GET `/health`

Basic health check (no auth required).

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

### GET `/health/detailed`

Detailed health check with dependency status.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "overall_healthy": true,
  "dependencies": {
    "postgresql": {"healthy": true, "latency_ms": 12.5},
    "redis": {"healthy": true, "latency_ms": 3.2},
    "opa": {"healthy": true, "latency_ms": 8.7}
  }
}
```

### GET `/metrics`

Prometheus metrics endpoint.

**Response:** `200 OK` (text/plain)
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/servers"} 1234
...
```

---

## Data Models

### Server

```typescript
interface Server {
  id: string;  // UUID
  name: string;
  description: string | null;
  transport: "http" | "stdio" | "sse";
  endpoint: string | null;
  command: string | null;
  status: "active" | "inactive" | "error";
  sensitivity_level: "low" | "medium" | "high" | "critical";
  tools: Tool[];
  metadata: Record<string, any>;
  created_at: string;  // ISO 8601
  updated_at: string;  // ISO 8601
}
```

### Tool

```typescript
interface Tool {
  id: string;  // UUID
  name: string;
  description: string | null;
  parameters: JSONSchema;
  sensitivity_level: "low" | "medium" | "high" | "critical";
  requires_approval: boolean;
  created_at: string;  // ISO 8601
}
```

### User

```typescript
interface User {
  user_id: string;  // UUID
  username: string;
  email: string;
  roles: string[];
  teams: string[];
  permissions: string[];
}
```

### AuditEvent

```typescript
interface AuditEvent {
  event_id: string;
  event_type: string;
  timestamp: string;  // ISO 8601
  user_id: string;  // UUID
  user_email: string;
  server_id: string | null;  // UUID
  server_name: string | null;
  tool_name: string | null;
  decision: "allow" | "deny";
  parameters: Record<string, any>;
  reason: string;
  duration_ms: number | null;
}
```

### Session

```typescript
interface Session {
  session_id: string;
  user_id: string;  // UUID
  provider: string;
  created_at: string;  // ISO 8601
  expires_at: string;  // ISO 8601
  last_activity: string;  // ISO 8601
}
```

### ApiKey

```typescript
interface ApiKey {
  id: string;  // UUID
  name: string;
  key_prefix: string;  // e.g., "sark_live_abc"
  scopes: string[];
  rate_limit: number;
  created_at: string;  // ISO 8601
  expires_at: string;  // ISO 8601
  last_used: string | null;  // ISO 8601
  revoked: boolean;
}
```

---

## Error Handling

### Standard Error Response

All errors follow this format:

```json
{
  "detail": "Error message here",
  "error_code": "ERROR_CODE",
  "request_id": "req_abc123"
}
```

### HTTP Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success with no body
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Authenticated but not authorized
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

### Common Error Codes

- `AUTH_INVALID_CREDENTIALS` - Invalid username/password
- `AUTH_TOKEN_EXPIRED` - JWT token expired
- `AUTH_INSUFFICIENT_PERMISSIONS` - User lacks required permissions
- `POLICY_DENIED` - OPA policy denied the action
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `VALIDATION_ERROR` - Request validation failed
- `SERVER_NOT_FOUND` - MCP server not found
- `TOOL_NOT_FOUND` - Tool not found
- `ALREADY_EXISTS` - Resource already exists

### Rate Limiting Headers

When rate limited, response includes:

```http
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1732708800
Retry-After: 45
```

---

## Pagination

SARK uses cursor-based pagination for efficient querying of large datasets.

### Request

```http
GET /api/v1/servers?limit=50&cursor=eyJpZCI6IjZiYTdiODEw...
```

### Response

```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6IjZiYTdiODEw...",
  "has_more": true,
  "total": 150  // Optional, only if include_total=true
}
```

### Cursor Format

Cursors are base64-encoded JSON objects containing pagination state. They are opaque to clients and should not be decoded or modified.

---

## Authentication Flow

### LDAP Flow

```
1. POST /api/v1/auth/login/ldap
   {username, password}

2. Response: {access_token, refresh_token, user}

3. All subsequent requests:
   Authorization: Bearer <access_token>

4. When access_token expires (60 min):
   POST /api/v1/auth/refresh
   {refresh_token}

5. On logout:
   POST /api/v1/auth/logout
   {refresh_token}
```

### OIDC Flow

```
1. GET /api/v1/auth/oidc/login
   → 302 Redirect to IdP

2. User authenticates at IdP
   → IdP redirects to /api/v1/auth/oidc/callback

3. SARK processes callback
   → Returns {access_token, refresh_token, user}

4. Same as LDAP flow from step 3 onwards
```

---

## WebSocket (Future)

**Note:** WebSocket support is planned for real-time updates (W6-E3-05).

### Connection

```
ws://localhost:8000/ws?token=<access_token>
```

### Messages

```json
{
  "type": "audit_event",
  "data": {
    "event_id": "audit_abc123",
    "event_type": "tool_invocation",
    "timestamp": "2025-11-27T10:35:12.456Z"
  }
}
```

---

## Development Tips

### Testing with curl

```bash
# Login
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username": "john.doe", "password": "password"}' | jq -r '.access_token')

# List servers
curl -X GET http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" | jq

# Register server
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @server.json | jq
```

### CORS Configuration

SARK API supports CORS for local development:

```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 86400
```

### Rate Limits (Development)

- Authenticated users: 5,000 requests/minute
- API keys: Configurable per key (default: 1,000/minute)
- Unauthenticated: 100 requests/minute per IP

---

## UI Requirements Summary

Based on the API analysis, the React UI needs to implement:

### Pages

1. **Login Page** - LDAP, OIDC, SAML authentication
2. **Dashboard** - Overview metrics and recent activity
3. **MCP Servers List** - Paginated table with search/filter
4. **Server Details** - View server info and tools
5. **Server Registration** - Form to register new servers
6. **Tool Invocation** - Interface to invoke tools
7. **Policy Viewer** - View and manage OPA policies
8. **Audit Log** - Query and view audit events
9. **API Keys** - Manage API keys
10. **Sessions** - View active sessions
11. **User Profile** - View current user info

### Core Features

- **Authentication** - JWT-based auth with token refresh
- **Data Fetching** - TanStack Query for server state
- **Global State** - Zustand for user/auth state
- **Forms** - Server registration, tool invocation
- **Tables** - Paginated, sortable, filterable
- **Search** - Full-text search for servers
- **Filtering** - Multi-select filters (status, sensitivity, tags)
- **Real-time** - WebSocket for live audit updates (future)
- **Error Handling** - Toast notifications for errors
- **Loading States** - Skeletons and spinners

### TypeScript Types

Generate types from the API response schemas above. Consider using `openapi-typescript` or defining types manually based on the data models section.

---

For questions or issues with the API, see:
- **API Documentation:** `docs/API_REFERENCE.md`
- **Tutorial 1:** `tutorials/01-basic-setup/README.md`
- **GitHub Issues:** https://github.com/apathy-ca/sark/issues
