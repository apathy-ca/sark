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
13. [Web UI Integration](#web-ui-integration)

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

## Session Management

SARK uses a dual-token authentication system for secure session management:
- **Access Tokens** (JWT): Short-lived (60 minutes), used for API requests
- **Refresh Tokens**: Long-lived (7 days), stored in Redis, used to obtain new access tokens

### Session Lifecycle

```
1. User authenticates (LDAP/OIDC/SAML)
   ↓
2. Receive access_token + refresh_token
   ↓
3. Use access_token for API requests
   ↓
4. When access_token expires, use refresh_token to get new access_token
   ↓
5. Repeat (refresh_token valid for 7 days)
```

### Session Security Features

**Token Rotation:**
When `REFRESH_TOKEN_ROTATION_ENABLED=true`, each token refresh invalidates the old refresh token and issues a new one, preventing token replay attacks.

**Concurrent Session Limits:**
- Default: 5 active sessions per user
- Configurable via `MAX_SESSIONS_PER_USER`
- Oldest sessions automatically revoked when limit exceeded

**Session Tracking:**
Each session stores:
- IP address of last use
- User agent
- Creation timestamp
- Last activity timestamp
- Expiration time

### Managing Sessions

**View Current Session:**
```bash
GET /api/v1/auth/me
```
Returns current user info from access token.

**Logout (Revoke Session):**
```bash
POST /api/v1/auth/revoke
```
Invalidates the refresh token, effectively logging out that session.

**Session Timeout:**
- **Access Token TTL**: 60 minutes (configurable via `JWT_EXPIRATION_MINUTES`)
- **Refresh Token TTL**: 7 days (configurable via `REFRESH_TOKEN_EXPIRATION_DAYS`)
- **Idle Timeout**: Not currently implemented (future enhancement)

### Best Practices

**For Web Applications:**
1. Store access token in memory (not localStorage)
2. Store refresh token in httpOnly cookie
3. Refresh access token before expiration
4. Handle 401 errors by refreshing token
5. Logout: Revoke refresh token and clear client state

**For Mobile/Desktop Apps:**
1. Store both tokens in secure storage (Keychain/Keystore)
2. Refresh token proactively before expiration
3. Implement automatic logout after inactivity
4. Clear tokens on explicit logout

**For Service-to-Service:**
1. Use API keys instead of JWT tokens
2. Rotate API keys regularly (90-day expiration recommended)
3. Use scoped API keys (minimum required permissions)

### Troubleshooting

**Problem: 401 Unauthorized after token refresh**
- **Cause**: Refresh token expired or revoked
- **Solution**: User must re-authenticate

**Problem: 401 Unauthorized on API call**
- **Cause**: Access token expired
- **Solution**: Refresh access token using refresh token endpoint

**Problem: Too many active sessions**
- **Cause**: User has exceeded concurrent session limit
- **Solution**: Older sessions are automatically revoked, or user can explicitly revoke sessions

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

### Advanced Policy Features

SARK supports advanced authorization policies beyond basic RBAC:

#### Time-Based Access Control

Policies can restrict access based on time of day or day of week:

**Request Example:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "server:register",
  "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "context": {
    "timestamp": "2025-11-22T23:30:00Z",
    "time_of_day": "23:30",
    "day_of_week": "friday"
  }
}
```

**Response (Deny - Outside Business Hours):**
```json
{
  "decision": "deny",
  "reason": "Server registration only allowed during business hours (9 AM - 5 PM Monday-Friday)",
  "filtered_parameters": null,
  "audit_id": "audit_789ghi"
}
```

#### IP-Based Access Control

Restrict access based on source IP address or IP ranges:

**Request Example:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "tool:invoke",
  "tool": "delete_production_database",
  "context": {
    "ip_address": "203.0.113.50",
    "network": "external"
  }
}
```

**Response (Deny - IP Not Whitelisted):**
```json
{
  "decision": "deny",
  "reason": "Critical operations require access from corporate network (IP range: 10.0.0.0/8)",
  "filtered_parameters": null,
  "audit_id": "audit_012jkl"
}
```

#### MFA Requirement

Require multi-factor authentication for sensitive operations:

**Request Example:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "tool:invoke",
  "tool": "delete_user_account",
  "context": {
    "mfa_verified": false,
    "authentication_method": "password"
  }
}
```

**Response (Deny - MFA Required):**
```json
{
  "decision": "deny",
  "reason": "Multi-factor authentication required for critical operations",
  "filtered_parameters": null,
  "required_conditions": ["mfa_verified"],
  "audit_id": "audit_345mno"
}
```

**Request Example (with MFA):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "tool:invoke",
  "tool": "delete_user_account",
  "context": {
    "mfa_verified": true,
    "mfa_method": "totp",
    "mfa_timestamp": "2025-11-22T10:29:55Z"
  }
}
```

**Response (Allow - MFA Verified):**
```json
{
  "decision": "allow",
  "reason": "User authenticated with MFA and has required permissions",
  "filtered_parameters": null,
  "audit_id": "audit_678pqr"
}
```

#### Parameter Filtering

Policies can filter or redact sensitive parameters:

**Request Example:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "tool:invoke",
  "tool": "query_user_data",
  "parameters": {
    "user_id": "target-user-123",
    "fields": ["email", "phone", "ssn", "name"]
  }
}
```

**Response (Allow with Filtered Parameters):**
```json
{
  "decision": "allow",
  "reason": "User has read access, but sensitive fields filtered based on role",
  "filtered_parameters": {
    "user_id": "target-user-123",
    "fields": ["email", "name"]
  },
  "removed_parameters": ["phone", "ssn"],
  "audit_id": "audit_901stu"
}
```

#### Batch Policy Evaluation

For bulk operations, evaluate multiple policy decisions in a single request:

**Request:**
```json
{
  "batch": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "action": "server:register",
      "server_id": "server-1"
    },
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "action": "server:register",
      "server_id": "server-2"
    }
  ]
}
```

**Response:**
```json
{
  "decisions": [
    {
      "decision": "allow",
      "reason": "User has server:write permission",
      "audit_id": "audit_123"
    },
    {
      "decision": "deny",
      "reason": "Sensitivity level exceeds user's maximum",
      "audit_id": "audit_456"
    }
  ],
  "summary": {
    "total": 2,
    "allowed": 1,
    "denied": 1
  }
}
```

### Policy Caching

Policy decisions are cached in Redis for performance:

**Cache Behavior:**
- **Cache TTL**: Varies by sensitivity level (30s to 10min)
- **Cache Key**: `policy:decision:{user_id}:{action}:{resource}:{context_hash}`
- **Cache Hit**: Returns decision in <5ms
- **Cache Miss**: Evaluates via OPA in <50ms

**Cache Headers:**
```
X-Cache-Status: HIT | MISS
X-Cache-TTL: 300
```

To bypass cache for critical operations:
```bash
curl -H "X-Skip-Policy-Cache: true" https://sark.example.com/api/v1/policy/evaluate
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

## Web UI Integration

This section provides comprehensive guidance for integrating SARK's API into web applications, including common UI workflows, best practices, and complete implementation examples.

### UI Authentication Flow

Web applications should implement the following authentication pattern:

#### 1. Login Flow

**Step 1: User Login**
```javascript
// Login with LDAP
const loginResponse = await fetch('/api/v1/auth/login/ldap', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  credentials: 'include',
  body: JSON.stringify({
    username: formData.username,
    password: formData.password
  })
});

const authData = await loginResponse.json();

// Store access token in memory (NOT localStorage)
window.sarkAuth = {
  accessToken: authData.access_token,
  expiresAt: Date.now() + (authData.expires_in * 1000),
  user: authData.user
};

// Store refresh token in httpOnly cookie (handled by server)
// or secure storage for mobile apps
```

**Step 2: Authenticated API Requests**
```javascript
async function authenticatedFetch(url, options = {}) {
  // Add authorization header
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${window.sarkAuth.accessToken}`
  };

  // Check if token needs refresh (before expiration)
  if (Date.now() > window.sarkAuth.expiresAt - 60000) {
    await refreshAccessToken();
  }

  return fetch(url, {...options, headers});
}
```

**Step 3: Token Refresh**
```javascript
async function refreshAccessToken() {
  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'include',
    body: JSON.stringify({
      refresh_token: getCookie('refresh_token')
    })
  });

  if (response.ok) {
    const data = await response.json();
    window.sarkAuth.accessToken = data.access_token;
    window.sarkAuth.expiresAt = Date.now() + (data.expires_in * 1000);
  } else {
    // Refresh failed - redirect to login
    window.location.href = '/login';
  }
}
```

**Step 4: Logout**
```javascript
async function logout() {
  await fetch('/api/v1/auth/revoke', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${window.sarkAuth.accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      refresh_token: getCookie('refresh_token')
    })
  });

  // Clear client-side state
  delete window.sarkAuth;
  window.location.href = '/login';
}
```

### Dashboard Data Loading

A typical dashboard needs multiple data sources. Use parallel requests for optimal performance:

```javascript
async function loadDashboardData() {
  const [metrics, servers, recentActivity] = await Promise.all([
    // Get server metrics summary
    authenticatedFetch('/api/v1/metrics/summary').then(r => r.json()),

    // Get active servers (first page)
    authenticatedFetch('/api/v1/servers?status=active&limit=10').then(r => r.json()),

    // Get time series data for last 24h
    authenticatedFetch('/api/v1/metrics/timeseries/servers?metric=server_count&time_range=24h').then(r => r.json())
  ]);

  return {
    summary: {
      totalServers: metrics.total_servers,
      activeServers: metrics.active_servers,
      unhealthyServers: metrics.unhealthy_servers,
      totalTools: metrics.total_tools
    },
    activeServers: servers.items,
    chartData: recentActivity.data_points
  };
}
```

### Server Management UI Endpoints

#### Server List View

**Endpoint:** `GET /api/v1/servers`

**UI Features:**
- Pagination (load more)
- Filtering by status, sensitivity
- Search by name/description
- Sorting

**Example Implementation:**
```javascript
class ServerListController {
  constructor() {
    this.servers = [];
    this.cursor = null;
    this.hasMore = true;
    this.filters = {
      status: null,
      sensitivity: null,
      search: null
    };
  }

  async loadServers(append = false) {
    const params = new URLSearchParams({
      limit: 20,
      ...(this.cursor && {cursor: this.cursor}),
      ...(this.filters.status && {status: this.filters.status}),
      ...(this.filters.sensitivity && {sensitivity: this.filters.sensitivity}),
      ...(this.filters.search && {search: this.filters.search})
    });

    const response = await authenticatedFetch(`/api/v1/servers?${params}`);
    const data = await response.json();

    if (append) {
      this.servers.push(...data.items);
    } else {
      this.servers = data.items;
    }

    this.cursor = data.next_cursor;
    this.hasMore = data.has_more;

    return this.servers;
  }

  async applyFilters(newFilters) {
    this.filters = {...this.filters, ...newFilters};
    this.cursor = null;
    return await this.loadServers(false);
  }

  async loadMore() {
    if (!this.hasMore) return;
    return await this.loadServers(true);
  }
}
```

#### Server Detail View

**Endpoint:** `GET /api/v1/servers/{server_id}`

**Additional Data:**
- Server metrics: `GET /api/v1/metrics/{server_id}`
- Server health: `GET /health/detailed`

**Example Implementation:**
```javascript
async function loadServerDetail(serverId) {
  const [server, metrics] = await Promise.all([
    authenticatedFetch(`/api/v1/servers/${serverId}`).then(r => r.json()),
    authenticatedFetch(`/api/v1/metrics/${serverId}`).then(r => r.json())
  ]);

  return {
    ...server,
    metrics: {
      totalTools: metrics.total_tools,
      toolsBySensitivity: metrics.tools_by_sensitivity,
      uptimePercentage: metrics.uptime_percentage,
      lastHealthCheck: metrics.last_health_check
    }
  };
}
```

#### Server Registration Form

**Endpoint:** `POST /api/v1/servers`

**Form Validation:**
```javascript
async function registerServer(formData) {
  // Client-side validation
  const errors = {};

  if (!formData.name || formData.name.length < 3) {
    errors.name = 'Server name must be at least 3 characters';
  }

  if (!formData.transport || !['http', 'stdio', 'sse'].includes(formData.transport)) {
    errors.transport = 'Invalid transport type';
  }

  if (formData.transport === 'http' && !formData.endpoint) {
    errors.endpoint = 'Endpoint required for HTTP transport';
  }

  if (Object.keys(errors).length > 0) {
    return {success: false, errors};
  }

  // Submit to API
  try {
    const response = await authenticatedFetch('/api/v1/servers', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(formData)
    });

    if (response.ok) {
      const result = await response.json();
      return {success: true, serverId: result.server_id};
    } else {
      const error = await response.json();
      return {success: false, errors: {_global: error.detail}};
    }
  } catch (error) {
    return {success: false, errors: {_global: 'Network error'}};
  }
}
```

### Policy Evaluation UI

**Use Case:** Show user if they can perform an action before they attempt it

**Endpoint:** `POST /api/v1/policy/evaluate`

**Example: Enable/Disable Action Buttons**
```javascript
async function checkUserPermissions(action, resourceId = null) {
  const response = await authenticatedFetch('/api/v1/policy/evaluate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      action: action,  // e.g., 'server:delete'
      server_id: resourceId
    })
  });

  const decision = await response.json();
  return decision.decision === 'allow';
}

// Usage in UI
async function renderServerActions(server) {
  const canEdit = await checkUserPermissions('server:write', server.id);
  const canDelete = await checkUserPermissions('server:delete', server.id);

  return `
    <button ${!canEdit ? 'disabled' : ''}>Edit</button>
    <button ${!canDelete ? 'disabled' : ''}>Delete</button>
  `;
}
```

### Metrics and Monitoring UI

#### Real-Time Dashboard Updates

**Endpoint:** `GET /api/v1/metrics/summary`

**Polling Strategy:**
```javascript
class MetricsDashboard {
  constructor() {
    this.updateInterval = 30000; // 30 seconds
    this.intervalId = null;
  }

  async start() {
    await this.updateMetrics();
    this.intervalId = setInterval(() => this.updateMetrics(), this.updateInterval);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  async updateMetrics() {
    try {
      const metrics = await authenticatedFetch('/api/v1/metrics/summary')
        .then(r => r.json());

      this.renderMetrics(metrics);
    } catch (error) {
      console.error('Failed to update metrics:', error);
    }
  }

  renderMetrics(metrics) {
    document.getElementById('total-servers').textContent = metrics.total_servers;
    document.getElementById('active-servers').textContent = metrics.active_servers;
    document.getElementById('unhealthy-servers').textContent = metrics.unhealthy_servers;
    document.getElementById('total-tools').textContent = metrics.total_tools;
  }
}
```

#### Time Series Charts

**Endpoint:** `GET /api/v1/metrics/timeseries/servers`

**Chart.js Integration Example:**
```javascript
async function renderServerCountChart() {
  const response = await authenticatedFetch(
    '/api/v1/metrics/timeseries/servers?metric=server_count&time_range=7d&interval=1d'
  );
  const data = await response.json();

  const chartData = {
    labels: data.data_points.map(p => new Date(p.timestamp).toLocaleDateString()),
    datasets: [{
      label: 'Total Servers',
      data: data.data_points.map(p => p.value),
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  };

  new Chart(document.getElementById('serverChart'), {
    type: 'line',
    data: chartData,
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: 'Server Count (Last 7 Days)'
        }
      }
    }
  });
}
```

### Data Export UI

**Endpoints:**
- `GET /api/v1/export/servers.csv`
- `GET /api/v1/export/servers.json`
- `GET /api/v1/export/tools.csv`
- `GET /api/v1/export/tools.json`

**Download Implementation:**
```javascript
async function exportServers(format = 'csv') {
  const url = `/api/v1/export/servers.${format}`;

  try {
    const response = await authenticatedFetch(url);

    if (!response.ok) throw new Error('Export failed');

    // Get blob and trigger download
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = contentDisposition
      ? contentDisposition.split('filename=')[1].replace(/"/g, '')
      : `servers_export.${format}`;

    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    a.remove();

    return {success: true};
  } catch (error) {
    return {success: false, error: error.message};
  }
}

// Usage
document.getElementById('export-csv').addEventListener('click', () => {
  exportServers('csv');
});

document.getElementById('export-json').addEventListener('click', () => {
  exportServers('json');
});
```

### Policy Management UI

#### List Active Policies

**Endpoint:** `GET /api/v1/policy/list`

```javascript
async function loadPolicies() {
  const response = await authenticatedFetch('/api/v1/policy/list');
  const data = await response.json();

  return data.policies.map(policy => ({
    name: policy.name,
    description: policy.description,
    version: policy.version,
    active: policy.active
  }));
}
```

#### Policy Validation (Before Deployment)

**Endpoint:** `POST /api/v1/policy/validate`

```javascript
async function validatePolicy(policyContent, testCases = null) {
  const response = await authenticatedFetch('/api/v1/policy/validate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      policy_content: policyContent,
      test_cases: testCases
    })
  });

  const result = await response.json();

  return {
    valid: result.valid,
    errors: result.errors,
    warnings: result.warnings,
    testResults: result.test_results
  };
}

// Usage in policy editor
async function onPolicyValidate() {
  const policyCode = editor.getValue();
  const validation = await validatePolicy(policyCode);

  if (!validation.valid) {
    showErrors(validation.errors);
  } else {
    showSuccess('Policy is valid');
    if (validation.warnings.length > 0) {
      showWarnings(validation.warnings);
    }
  }
}
```

### Error Handling for UI

**Comprehensive Error Handler:**
```javascript
async function apiRequest(url, options = {}) {
  try {
    const response = await authenticatedFetch(url, options);

    // Success responses
    if (response.ok) {
      return {success: true, data: await response.json()};
    }

    // Handle specific error codes
    const errorData = await response.json();

    switch (response.status) {
      case 400:
        return {
          success: false,
          error: 'Invalid request',
          details: errorData.detail
        };

      case 401:
        // Token expired or invalid
        await refreshAccessToken();
        // Retry request once
        return apiRequest(url, options);

      case 403:
        return {
          success: false,
          error: 'Access denied',
          details: 'You do not have permission to perform this action'
        };

      case 404:
        return {
          success: false,
          error: 'Not found',
          details: errorData.detail
        };

      case 422:
        return {
          success: false,
          error: 'Validation error',
          validationErrors: errorData.detail
        };

      case 429:
        return {
          success: false,
          error: 'Rate limit exceeded',
          retryAfter: response.headers.get('Retry-After')
        };

      case 500:
      case 503:
        return {
          success: false,
          error: 'Server error',
          details: 'Please try again later'
        };

      default:
        return {
          success: false,
          error: `Unexpected error (${response.status})`,
          details: errorData.detail
        };
    }
  } catch (error) {
    // Network error
    return {
      success: false,
      error: 'Network error',
      details: 'Unable to connect to server'
    };
  }
}
```

### Performance Best Practices

#### 1. Request Caching

```javascript
class APICache {
  constructor(ttl = 60000) { // 60 second default TTL
    this.cache = new Map();
    this.ttl = ttl;
  }

  get(key) {
    const cached = this.cache.get(key);
    if (!cached) return null;

    if (Date.now() > cached.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  set(key, data) {
    this.cache.set(key, {
      data,
      expiresAt: Date.now() + this.ttl
    });
  }

  clear() {
    this.cache.clear();
  }
}

// Usage
const metricsCache = new APICache(30000); // 30 seconds

async function getMetricsSummary() {
  const cacheKey = 'metrics:summary';
  const cached = metricsCache.get(cacheKey);

  if (cached) return cached;

  const data = await authenticatedFetch('/api/v1/metrics/summary')
    .then(r => r.json());

  metricsCache.set(cacheKey, data);
  return data;
}
```

#### 2. Debounced Search

```javascript
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Usage for search input
const searchServers = debounce(async (searchTerm) => {
  const response = await authenticatedFetch(
    `/api/v1/servers?search=${encodeURIComponent(searchTerm)}&limit=20`
  );
  const results = await response.json();
  renderSearchResults(results.items);
}, 300); // Wait 300ms after user stops typing

document.getElementById('search').addEventListener('input', (e) => {
  searchServers(e.target.value);
});
```

#### 3. Infinite Scroll

```javascript
class InfiniteScrollList {
  constructor(containerElement, loadFunction) {
    this.container = containerElement;
    this.loadFunction = loadFunction;
    this.loading = false;
    this.hasMore = true;
    this.cursor = null;

    this.setupScrollListener();
  }

  setupScrollListener() {
    this.container.addEventListener('scroll', () => {
      if (this.loading || !this.hasMore) return;

      const scrollPosition = this.container.scrollTop + this.container.clientHeight;
      const scrollHeight = this.container.scrollHeight;

      // Load more when 90% scrolled
      if (scrollPosition >= scrollHeight * 0.9) {
        this.loadMore();
      }
    });
  }

  async loadMore() {
    this.loading = true;
    this.showLoadingIndicator();

    const response = await this.loadFunction(this.cursor);

    this.appendItems(response.items);
    this.cursor = response.next_cursor;
    this.hasMore = response.has_more;

    this.loading = false;
    this.hideLoadingIndicator();
  }

  appendItems(items) {
    const fragment = document.createDocumentFragment();
    items.forEach(item => {
      const element = this.createItemElement(item);
      fragment.appendChild(element);
    });
    this.container.appendChild(fragment);
  }

  createItemElement(item) {
    // Override in implementation
  }

  showLoadingIndicator() {
    document.getElementById('loading').style.display = 'block';
  }

  hideLoadingIndicator() {
    document.getElementById('loading').style.display = 'none';
  }
}

// Usage
const serverList = new InfiniteScrollList(
  document.getElementById('server-list'),
  async (cursor) => {
    const params = new URLSearchParams({limit: 20});
    if (cursor) params.append('cursor', cursor);

    return await authenticatedFetch(`/api/v1/servers?${params}`)
      .then(r => r.json());
  }
);
```

### Common UI Workflows

#### Workflow 1: User Registration to Server Access

```javascript
// Step 1: New user logs in
const loginResult = await login('new.user', 'password');

// Step 2: Load user profile and permissions
const user = await authenticatedFetch('/api/v1/auth/me').then(r => r.json());

// Step 3: Check what servers user can access
const servers = await authenticatedFetch(
  `/api/v1/servers?team_id=${user.teams[0]}&limit=50`
).then(r => r.json());

// Step 4: For each server, check tool permissions
const serverPermissions = await Promise.all(
  servers.items.map(async (server) => {
    const canInvoke = await checkUserPermissions('tool:invoke', server.id);
    return {serverId: server.id, canInvoke};
  })
);
```

#### Workflow 2: Admin Dashboard

```javascript
async function loadAdminDashboard() {
  // Load all critical data in parallel
  const [
    metrics,
    unhealthyServers,
    recentPolicyDenials,
    topUsers
  ] = await Promise.all([
    authenticatedFetch('/api/v1/metrics/summary').then(r => r.json()),
    authenticatedFetch('/api/v1/servers?status=unhealthy&limit=10').then(r => r.json()),
    authenticatedFetch('/api/v1/audit/policy-denials?limit=20').then(r => r.json()),
    authenticatedFetch('/api/v1/audit/top-users?limit=10').then(r => r.json())
  ]);

  return {
    overview: {
      totalServers: metrics.total_servers,
      activeServers: metrics.active_servers,
      unhealthyCount: metrics.unhealthy_servers,
      totalTools: metrics.total_tools
    },
    alerts: unhealthyServers.items,
    securityEvents: recentPolicyDenials,
    topUsers
  };
}
```

### WebSocket Alternative (Server-Sent Events)

For real-time updates without WebSocket complexity:

```javascript
class ServerHealthMonitor {
  constructor(serverId) {
    this.serverId = serverId;
    this.eventSource = null;
  }

  start() {
    // Note: This is conceptual - actual implementation depends on SSE support
    this.eventSource = new EventSource(
      `/api/v1/servers/${this.serverId}/health/stream`,
      {
        headers: {
          'Authorization': `Bearer ${window.sarkAuth.accessToken}`
        }
      }
    );

    this.eventSource.addEventListener('health-update', (event) => {
      const data = JSON.parse(event.data);
      this.onHealthUpdate(data);
    });

    this.eventSource.addEventListener('error', (error) => {
      console.error('SSE error:', error);
      this.stop();
    });
  }

  stop() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  onHealthUpdate(data) {
    // Update UI with new health status
    document.getElementById('server-status').textContent = data.status;
    document.getElementById('last-check').textContent = data.last_check;
  }
}
```

### Accessibility Considerations

**Loading States:**
```javascript
function setLoadingState(loading, elementId = 'main-content') {
  const element = document.getElementById(elementId);

  if (loading) {
    element.setAttribute('aria-busy', 'true');
    element.setAttribute('aria-live', 'polite');
  } else {
    element.setAttribute('aria-busy', 'false');
    element.removeAttribute('aria-live');
  }
}
```

**Error Announcements:**
```javascript
function announceError(message) {
  const announcement = document.getElementById('sr-announcements');
  announcement.textContent = message;
  announcement.setAttribute('role', 'alert');

  // Clear after announcement
  setTimeout(() => {
    announcement.textContent = '';
  }, 3000);
}
```

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
