# SARK API Reference

**Version:** 0.1.0
**Base URL:** `https://sark.example.com`
**API Prefix:** `/api/v1` or `/api`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health & Status](#health--status)
3. [Authentication Endpoints](#authentication-endpoints)
4. [API Key Management](#api-key-management)
5. [Server Management](#server-management)
6. [Bulk Operations](#bulk-operations)
7. [Tool Sensitivity Management](#tool-sensitivity-management)
8. [Policy Evaluation](#policy-evaluation)
9. [SAML Endpoints](#saml-endpoints)
10. [Pagination & Filtering](#pagination--filtering)
11. [Error Codes](#error-codes)
12. [Code Examples](#code-examples)

---

## Authentication

SARK supports multiple authentication methods:

- **JWT Bearer Tokens** - Include `Authorization: Bearer <token>` header
- **API Keys** - Include `X-API-Key: <key>` header
- **LDAP/Active Directory** - Authenticate and receive JWT tokens
- **OIDC (OpenID Connect)** - OAuth2 flow with supported providers
- **SAML 2.0** - Enterprise SSO integration

### Bearer Token Authentication

```bash
curl -H "Authorization: Bearer eyJhbGc..." https://sark.example.com/api/v1/servers
```

### API Key Authentication

```bash
curl -H "X-API-Key: sark_live_abc123..." https://sark.example.com/api/v1/servers
```

---

## Health & Status

### GET /health

Basic health check (liveness probe).

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "production"
}
```

### GET /health/live

Kubernetes liveness probe - returns 200 if app is alive.

### GET /health/ready

Readiness probe - checks all dependencies.

**Response:**
```json
{
  "ready": true,
  "database": true,
  "redis": true,
  "opa": true
}
```

### GET /health/detailed

Detailed health check with individual dependency status and latency.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "production",
  "overall_healthy": true,
  "dependencies": {
    "postgresql": {
      "healthy": true,
      "latency_ms": 12.5
    },
    "redis": {
      "healthy": true,
      "latency_ms": 3.2
    },
    "opa": {
      "healthy": true,
      "latency_ms": 8.7
    }
  }
}
```

---

## Authentication Endpoints

### POST /api/v1/auth/login/ldap

Authenticate user against LDAP/Active Directory and issue JWT tokens.

**Request:**
```json
{
  "username": "john.doe",
  "password": "secret123"
}
```

**Response (200 OK):**
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
    "name": "John Doe",
    "roles": ["developer", "team_lead"],
    "teams": ["engineering", "platform"]
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `503 Service Unavailable` - LDAP service unavailable

---

### GET /api/v1/auth/oidc/login

Initiate OIDC authentication flow. Redirects user to identity provider.

**Query Parameters:**
- None (redirect_uri configured in settings)

**Response:**
- `307 Temporary Redirect` - Redirects to IdP authorization endpoint

---

### GET /api/v1/auth/oidc/callback

Handle callback from OIDC identity provider after authentication.

**Query Parameters:**
- `code` (string, required) - Authorization code from IdP
- `state` (string, required) - State parameter for CSRF protection

**Response (200 OK):**
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
    "name": "John Doe",
    "roles": ["developer"],
    "teams": ["engineering"]
  }
}
```

---

### POST /api/v1/auth/refresh

Exchange refresh token for a new access token.

**Request:**
```json
{
  "refresh_token": "rt_abc123..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "rt_xyz789..."
}
```

**Note:** If `refresh_token_rotation_enabled` is true, a new refresh token is returned.

**Error Responses:**
- `401 Unauthorized` - Invalid or expired refresh token

---

### POST /api/v1/auth/revoke

Revoke a refresh token (logout).

**Authentication Required:** Yes (Bearer token)

**Request:**
```json
{
  "refresh_token": "rt_abc123..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Refresh token revoked successfully"
}
```

---

### GET /api/v1/auth/me

Get current authenticated user information.

**Authentication Required:** Yes (Bearer token)

**Response (200 OK):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "role": "developer",
  "roles": ["developer", "team_lead"],
  "teams": ["engineering", "platform"],
  "permissions": ["server:read", "server:write"]
}
```

---

## API Key Management

### POST /api/auth/api-keys

Create a new API key.

**Authentication Required:** Yes

**Request:**
```json
{
  "name": "Production Server Automation",
  "description": "API key for automated server registration",
  "scopes": ["server:read", "server:write"],
  "team_id": "550e8400-e29b-41d4-a716-446655440000",
  "rate_limit": 1000,
  "expires_in_days": 90,
  "environment": "live"
}
```

**Response (201 Created):**
```json
{
  "api_key": {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "team_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Production Server Automation",
    "description": "API key for automated server registration",
    "key_prefix": "sark_live_abc",
    "scopes": ["server:read", "server:write"],
    "rate_limit": 1000,
    "is_active": true,
    "expires_at": "2025-05-22T00:00:00Z",
    "last_used_at": null,
    "last_used_ip": null,
    "usage_count": 0,
    "created_at": "2025-02-22T10:00:00Z",
    "updated_at": "2025-02-22T10:00:00Z",
    "revoked_at": null
  },
  "key": "sark_live_abc123def456ghi789jkl012mno345",
  "message": "API key created successfully. Save this key securely - it won't be shown again!"
}
```

**Available Scopes:**
- `server:read` - Read server information
- `server:write` - Register/update servers
- `server:delete` - Delete servers
- `policy:read` - Read policies
- `policy:write` - Create/update policies
- `audit:read` - Read audit logs
- `admin` - Full admin access

---

### GET /api/auth/api-keys

List API keys for the current user or team.

**Query Parameters:**
- `team_id` (UUID, optional) - Filter by team
- `include_revoked` (boolean, default: false) - Include revoked keys

**Response (200 OK):**
```json
[
  {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Production Server Automation",
    "key_prefix": "sark_live_abc",
    "scopes": ["server:read", "server:write"],
    "rate_limit": 1000,
    "is_active": true,
    "expires_at": "2025-05-22T00:00:00Z",
    "last_used_at": "2025-02-22T09:30:00Z",
    "usage_count": 45,
    "created_at": "2025-02-22T10:00:00Z"
  }
]
```

---

### GET /api/auth/api-keys/{key_id}

Get a specific API key by ID.

**Response (200 OK):**
```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "Production Server Automation",
  "key_prefix": "sark_live_abc",
  "scopes": ["server:read", "server:write"],
  "is_active": true,
  "created_at": "2025-02-22T10:00:00Z"
}
```

---

### PATCH /api/auth/api-keys/{key_id}

Update an API key's metadata.

**Request:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "scopes": ["server:read"],
  "rate_limit": 500,
  "is_active": false
}
```

**Response (200 OK):**
```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "Updated Name",
  "scopes": ["server:read"],
  "rate_limit": 500,
  "is_active": false
}
```

---

### POST /api/auth/api-keys/{key_id}/rotate

Rotate an API key (generate new credentials).

**Request:**
Query parameter: `environment` (default: "live")

**Response (200 OK):**
```json
{
  "api_key": {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "key_prefix": "sark_live_xyz",
    "updated_at": "2025-02-22T11:00:00Z"
  },
  "key": "sark_live_xyz789new456key123rotated",
  "message": "API key rotated successfully. Update your applications with the new key."
}
```

---

### DELETE /api/auth/api-keys/{key_id}

Revoke an API key.

**Response:** 204 No Content

---

## Server Management

### POST /api/v1/servers

Register a new MCP server.

**Authentication Required:** Yes

**Request:**
```json
{
  "name": "analytics-server-1",
  "transport": "http",
  "endpoint": "http://analytics.example.com:8080",
  "version": "2025-06-18",
  "capabilities": ["tools", "resources"],
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
      "requires_approval": true
    }
  ],
  "description": "Analytics data server",
  "sensitivity_level": "high",
  "metadata": {
    "team": "data-engineering",
    "owner": "john.doe@example.com"
  }
}
```

**Transport Types:**
- `http` - HTTP/HTTPS endpoint
- `stdio` - Standard I/O (command-based)
- `sse` - Server-Sent Events

**Response (201 Created):**
```json
{
  "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "registered",
  "consul_id": "analytics-server-1-6ba7b810"
}
```

**Error Responses:**
- `403 Forbidden` - Registration denied by policy
- `422 Unprocessable Entity` - Invalid request data

---

### GET /api/v1/servers

List registered MCP servers with pagination and filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Items per page (1-200) |
| `cursor` | string | null | Pagination cursor |
| `sort_order` | string | desc | Sort order (asc/desc) |
| `status` | string | null | Filter by status (comma-separated) |
| `sensitivity` | string | null | Filter by sensitivity (comma-separated) |
| `team_id` | UUID | null | Filter by team |
| `owner_id` | UUID | null | Filter by owner |
| `tags` | string | null | Filter by tags (comma-separated) |
| `match_all_tags` | bool | false | Match all tags (AND) vs any (OR) |
| `search` | string | null | Full-text search on name/description |
| `include_total` | bool | false | Include total count (expensive) |

**Example Requests:**
```bash
# Get first 50 servers
GET /api/v1/servers?limit=50

# Filter by status and sensitivity
GET /api/v1/servers?status=active&sensitivity=high,critical

# Full-text search with pagination
GET /api/v1/servers?search=analytics&limit=20&cursor=eyJpZCI6ImFiYzEyMyJ9

# Filter by team and tags
GET /api/v1/servers?team_id=550e8400-e29b-41d4-a716-446655440000&tags=production,critical
```

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "name": "analytics-server-1",
      "transport": "http",
      "status": "active",
      "sensitivity_level": "high",
      "created_at": "2025-02-22T10:00:00Z"
    }
  ],
  "next_cursor": "eyJpZCI6IjZiYTdiODEwLTlkYWQtMTFkMS04MGI0LTAwYzA0ZmQ0MzBjOCJ9",
  "has_more": true,
  "total": null
}
```

**Valid Status Values:**
- `registered` - Server registered but not yet active
- `active` - Server is active and healthy
- `inactive` - Server is temporarily inactive
- `unhealthy` - Server failed health checks
- `decommissioned` - Server is permanently decommissioned

**Valid Sensitivity Levels:**
- `low` - Public or low-risk tools
- `medium` - Standard business tools
- `high` - Sensitive data access
- `critical` - High-impact operations

---

### GET /api/v1/servers/{server_id}

Get server details by ID.

**Response (200 OK):**
```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "analytics-server-1",
  "description": "Analytics data server",
  "transport": "http",
  "endpoint": "http://analytics.example.com:8080",
  "status": "active",
  "sensitivity_level": "high",
  "tools": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "execute_query",
      "description": "Execute SQL query on analytics database",
      "sensitivity_level": "high"
    }
  ],
  "metadata": {
    "team": "data-engineering",
    "owner": "john.doe@example.com"
  },
  "created_at": "2025-02-22T10:00:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Server not found

---

## Bulk Operations

### POST /api/v1/bulk/servers/register

Bulk register multiple MCP servers.

**Authentication Required:** Yes

**Request:**
```json
{
  "servers": [
    {
      "name": "analytics-server-1",
      "transport": "http",
      "endpoint": "http://analytics-1.example.com",
      "capabilities": ["tools"],
      "tools": [],
      "sensitivity_level": "high"
    },
    {
      "name": "ml-server-1",
      "transport": "http",
      "endpoint": "http://ml-1.example.com",
      "capabilities": ["tools"],
      "tools": [],
      "sensitivity_level": "critical"
    }
  ],
  "fail_on_first_error": false
}
```

**Modes:**
- `fail_on_first_error: true` - Transactional (all-or-nothing)
- `fail_on_first_error: false` - Best-effort (continue on errors)

**Response (200 OK):**
```json
{
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "succeeded_items": [
    {
      "name": "analytics-server-1",
      "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "status": "registered"
    },
    {
      "name": "ml-server-1",
      "server_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
      "status": "registered"
    }
  ],
  "failed_items": []
}
```

**Limits:** Maximum 100 servers per request

---

### PATCH /api/v1/bulk/servers/status

Bulk update server statuses.

**Request:**
```json
{
  "updates": [
    {
      "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "status": "active"
    },
    {
      "server_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
      "status": "inactive"
    }
  ],
  "fail_on_first_error": false
}
```

**Response (200 OK):**
```json
{
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "succeeded_items": [
    {
      "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "status": "active"
    },
    {
      "server_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
      "status": "inactive"
    }
  ],
  "failed_items": []
}
```

---

## Tool Sensitivity Management

### GET /api/v1/tools/{tool_id}/sensitivity

Get current sensitivity level for a tool.

**Response (200 OK):**
```json
{
  "tool_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "execute_query",
  "sensitivity_level": "high",
  "is_overridden": false,
  "last_updated": "2025-02-22T10:00:00Z"
}
```

---

### POST /api/v1/tools/{tool_id}/sensitivity

Manually update tool sensitivity level (admin only).

**Authentication Required:** Yes (admin role)

**Request:**
```json
{
  "sensitivity_level": "critical",
  "reason": "Tool now accesses PII data"
}
```

**Response (200 OK):**
```json
{
  "tool_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "execute_query",
  "sensitivity_level": "critical",
  "is_overridden": true,
  "last_updated": "2025-02-22T11:00:00Z"
}
```

---

### POST /api/v1/tools/detect-sensitivity

Detect sensitivity level for a tool based on name and description.

**Request:**
```json
{
  "tool_name": "execute_sql_query",
  "tool_description": "Execute raw SQL queries on production database",
  "parameters": {
    "query": "string",
    "database": "string"
  }
}
```

**Response (200 OK):**
```json
{
  "detected_level": "high",
  "keywords_matched": ["sql", "database", "execute"],
  "detection_method": "high_keywords"
}
```

---

### GET /api/v1/tools/statistics/sensitivity

Get statistics about tool sensitivity distribution.

**Response (200 OK):**
```json
{
  "total_tools": 250,
  "by_sensitivity": {
    "low": 50,
    "medium": 120,
    "high": 60,
    "critical": 20
  },
  "manually_overridden": 15
}
```

---

## Policy Evaluation

### POST /api/v1/policy/evaluate

Evaluate authorization policy for a request.

**Authentication Required:** Yes

**Request:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "tool:invoke",
  "tool": "execute_query",
  "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "parameters": {
    "query": "SELECT * FROM users",
    "database": "production"
  }
}
```

**Response (200 OK - Allow):**
```json
{
  "decision": "allow",
  "reason": "User has required role and tool sensitivity is within allowed level",
  "filtered_parameters": null,
  "audit_id": "audit_123abc"
}
```

**Response (200 OK - Deny):**
```json
{
  "decision": "deny",
  "reason": "Tool sensitivity level 'critical' exceeds user's maximum allowed level 'high'",
  "filtered_parameters": null,
  "audit_id": "audit_456def"
}
```

---

## SAML Endpoints

### GET /api/auth/saml/metadata

Get Service Provider SAML metadata XML.

**Response (200 OK):**
```xml
<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" ...>
  <!-- SP Metadata XML -->
</EntityDescriptor>
```

---

### GET /api/auth/saml/login

Initiate SAML SSO login.

**Query Parameters:**
- `relay_state` (string, default: "/") - Return URL after authentication

**Response:** 302 Redirect to IdP SSO URL

---

### POST /api/auth/saml/acs

Assertion Consumer Service (ACS) endpoint.

**Form Parameters:**
- `SAMLResponse` (string, required) - Base64-encoded SAML response
- `RelayState` (string, optional) - Application state

**Response:** HTML page with authentication result

---

## Pagination & Filtering

### Cursor-Based Pagination

SARK uses cursor-based pagination for efficient querying of large datasets.

**Benefits:**
- Consistent results even with concurrent modifications
- Better performance than offset-based pagination
- No page drift when data changes

**Parameters:**
- `limit` - Number of items per page (1-200, default: 50)
- `cursor` - Opaque cursor for next page
- `sort_order` - Sort order (asc/desc, default: desc)

**Example:**
```bash
# First page
GET /api/v1/servers?limit=50

# Next page (use cursor from previous response)
GET /api/v1/servers?limit=50&cursor=eyJpZCI6ImFiYzEyMyJ9
```

**Response Format:**
```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6ImFiYzEyMyJ9",
  "has_more": true,
  "total": null
}
```

### Filtering

Multiple filters can be combined using AND logic:

```bash
# Multiple filters
GET /api/v1/servers?status=active&sensitivity=high&team_id=550e8400-e29b-41d4-a716-446655440000
```

### Full-Text Search

Search across name and description fields:

```bash
GET /api/v1/servers?search=analytics
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no content to return |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

```json
{
  "detail": "Server not found",
  "status_code": 404,
  "error_type": "NotFoundError"
}
```

### Common Error Messages

**Authentication Errors:**
- `Invalid username or password` - LDAP authentication failed
- `Invalid or expired refresh token` - Token refresh failed
- `Authentication service temporarily unavailable` - Redis/LDAP down

**Authorization Errors:**
- `Server registration denied by policy` - OPA policy denied action
- `Tool sensitivity update denied by policy` - Insufficient permissions

**Validation Errors:**
- `Invalid sensitivity level` - Must be: low, medium, high, critical
- `Invalid pagination cursor` - Cursor format invalid

---

## Code Examples

### Python (using requests)

#### Authenticate and List Servers

```python
import requests

# LDAP Login
response = requests.post(
    "https://sark.example.com/api/v1/auth/login/ldap",
    json={
        "username": "john.doe",
        "password": "secret123"
    }
)
auth_data = response.json()
access_token = auth_data["access_token"]

# List servers with authentication
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(
    "https://sark.example.com/api/v1/servers",
    headers=headers,
    params={"limit": 50, "status": "active"}
)
servers = response.json()
print(f"Found {len(servers['items'])} active servers")
```

#### Register a Server

```python
import requests

headers = {"Authorization": f"Bearer {access_token}"}
server_data = {
    "name": "analytics-server-1",
    "transport": "http",
    "endpoint": "http://analytics.example.com:8080",
    "capabilities": ["tools"],
    "tools": [
        {
            "name": "execute_query",
            "description": "Execute SQL query",
            "parameters": {"type": "object"},
            "sensitivity_level": "high"
        }
    ],
    "sensitivity_level": "high"
}

response = requests.post(
    "https://sark.example.com/api/v1/servers",
    headers=headers,
    json=server_data
)
result = response.json()
print(f"Server registered: {result['server_id']}")
```

#### Using API Keys

```python
import requests

# Create API key
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post(
    "https://sark.example.com/api/auth/api-keys",
    headers=headers,
    json={
        "name": "Automation Key",
        "scopes": ["server:read", "server:write"],
        "rate_limit": 1000,
        "expires_in_days": 90
    }
)
key_data = response.json()
api_key = key_data["key"]
print(f"API Key created: {api_key}")

# Use API key for authentication
headers = {"X-API-Key": api_key}
response = requests.get(
    "https://sark.example.com/api/v1/servers",
    headers=headers
)
```

---

### cURL

#### LDAP Login

```bash
curl -X POST https://sark.example.com/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "password": "secret123"
  }'
```

#### List Servers with Filters

```bash
curl -X GET "https://sark.example.com/api/v1/servers?status=active&sensitivity=high&limit=20" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

#### Register Server

```bash
curl -X POST https://sark.example.com/api/v1/servers \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "analytics-server-1",
    "transport": "http",
    "endpoint": "http://analytics.example.com:8080",
    "capabilities": ["tools"],
    "tools": [],
    "sensitivity_level": "high"
  }'
```

#### Bulk Register Servers

```bash
curl -X POST https://sark.example.com/api/v1/bulk/servers/register \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "servers": [
      {
        "name": "server-1",
        "transport": "http",
        "endpoint": "http://server-1.example.com",
        "capabilities": ["tools"],
        "tools": [],
        "sensitivity_level": "medium"
      },
      {
        "name": "server-2",
        "transport": "http",
        "endpoint": "http://server-2.example.com",
        "capabilities": ["tools"],
        "tools": [],
        "sensitivity_level": "high"
      }
    ],
    "fail_on_first_error": false
  }'
```

---

### JavaScript (using fetch)

#### Authenticate and List Servers

```javascript
// LDAP Login
const authResponse = await fetch('https://sark.example.com/api/v1/auth/login/ldap', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    username: 'john.doe',
    password: 'secret123'
  })
});
const authData = await authResponse.json();
const accessToken = authData.access_token;

// List servers
const serversResponse = await fetch(
  'https://sark.example.com/api/v1/servers?limit=50&status=active',
  {
    headers: {'Authorization': `Bearer ${accessToken}`}
  }
);
const servers = await serversResponse.json();
console.log(`Found ${servers.items.length} active servers`);
```

#### Register Server

```javascript
const serverData = {
  name: 'analytics-server-1',
  transport: 'http',
  endpoint: 'http://analytics.example.com:8080',
  capabilities: ['tools'],
  tools: [
    {
      name: 'execute_query',
      description: 'Execute SQL query',
      parameters: {type: 'object'},
      sensitivity_level: 'high'
    }
  ],
  sensitivity_level: 'high'
};

const response = await fetch('https://sark.example.com/api/v1/servers', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(serverData)
});
const result = await response.json();
console.log(`Server registered: ${result.server_id}`);
```

---

## Rate Limiting

API keys have configurable rate limits (requests per minute). When exceeded:

**Response (429 Too Many Requests):**
```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds.",
  "retry_after": 45
}
```

**Headers:**
- `X-RateLimit-Limit: 1000` - Maximum requests per minute
- `X-RateLimit-Remaining: 0` - Remaining requests
- `X-RateLimit-Reset: 1645534800` - Unix timestamp when limit resets

---

## Versioning

API version is included in the URL path:
- Current: `/api/v1/`
- Future: `/api/v2/`

**Breaking changes** will result in a new API version. Non-breaking changes (new fields, new endpoints) will be added to existing versions.

---

## Support

For additional help:
- **Documentation:** https://docs.sark.example.com
- **GitHub Issues:** https://github.com/your-org/sark/issues
- **API Status:** https://status.sark.example.com
