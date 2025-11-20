# SARK API Integration Guide

**Complete Integration Examples for MCP Governance**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Server Registration](#server-registration)
4. [Policy Evaluation](#policy-evaluation)
5. [Audit Log Queries](#audit-log-queries)
6. [SDK Examples](#sdk-examples)
7. [Webhooks & Events](#webhooks--events)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [Best Practices](#best-practices)

---

## Quick Start

### API Base URL

```
Development: http://localhost:8000
Production:  https://sark.company.com
```

### Authentication

All API requests require authentication via Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     https://sark.company.com/api/v1/servers
```

---

## Authentication

### OAuth 2.0 Flow

**1. Redirect user to authorization endpoint:**

```
GET https://sark.company.com/auth/authorize?
    client_id=YOUR_CLIENT_ID&
    redirect_uri=https://your-app.com/callback&
    response_type=code&
    scope=server:read server:write policy:evaluate
```

**2. Exchange authorization code for access token:**

```bash
curl -X POST https://sark.company.com/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=https://your-app.com/callback"
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_token": "8xLOxBtZp8...",
  "scope": "server:read server:write policy:evaluate"
}
```

### API Key Authentication

For server-to-server integrations:

```python
import requests

API_KEY = "sark_live_abc123xyz789"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://sark.company.com/api/v1/servers",
    headers=headers
)
```

---

## Server Registration

### Register MCP Server

**Request:**

```bash
curl -X POST https://sark.company.com/api/v1/servers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "finance-database-server",
    "transport": "http",
    "endpoint": "https://mcp-finance.internal:8080",
    "version": "2025-06-18",
    "capabilities": ["tools", "resources"],
    "tools": [
      {
        "name": "query_financial_data",
        "description": "Query financial database with SQL",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "SQL query to execute"
            },
            "limit": {
              "type": "integer",
              "description": "Maximum rows to return",
              "default": 100
            }
          },
          "required": ["query"]
        },
        "sensitivity_level": "high",
        "requires_approval": true
      },
      {
        "name": "get_account_balance",
        "description": "Get account balance for a customer",
        "parameters": {
          "type": "object",
          "properties": {
            "account_id": {
              "type": "string",
              "description": "Customer account ID"
            }
          },
          "required": ["account_id"]
        },
        "sensitivity_level": "medium"
      }
    ],
    "sensitivity_level": "high",
    "metadata": {
      "team": "finance",
      "environment": "production",
      "compliance": "SOC2"
    }
  }'
```

**Response (201 Created):**

```json
{
  "server_id": "srv_2N8h9Kj3L4m",
  "status": "registered",
  "consul_id": "mcp-finance-database-server-2N8h9Kj3L4m",
  "tools_registered": 2,
  "created_at": "2024-11-20T10:30:45.123Z"
}
```

### Python SDK Example

```python
from sark_sdk import SARKClient

client = SARKClient(api_key="sark_live_abc123")

# Register server
server = client.servers.create(
    name="finance-database-server",
    transport="http",
    endpoint="https://mcp-finance.internal:8080",
    tools=[
        {
            "name": "query_financial_data",
            "description": "Query financial database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            },
            "sensitivity_level": "high"
        }
    ],
    sensitivity_level="high",
    metadata={
        "team": "finance",
        "environment": "production"
    }
)

print(f"Server registered: {server.id}")
```

### TypeScript SDK Example

```typescript
import { SARKClient } from '@company/sark-sdk';

const client = new SARKClient({
  apiKey: 'sark_live_abc123',
  baseURL: 'https://sark.company.com'
});

// Register server
const server = await client.servers.create({
  name: 'finance-database-server',
  transport: 'http',
  endpoint: 'https://mcp-finance.internal:8080',
  tools: [
    {
      name: 'query_financial_data',
      description: 'Query financial database',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string' }
        }
      },
      sensitivityLevel: 'high'
    }
  ],
  sensitivityLevel: 'high',
  metadata: {
    team: 'finance',
    environment: 'production'
  }
});

console.log(`Server registered: ${server.id}`);
```

### List Servers

```bash
# List all servers
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/servers"

# Filter by status
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/servers?status=active"

# Pagination
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/servers?page=2&page_size=50"
```

**Response:**

```json
{
  "servers": [
    {
      "id": "srv_2N8h9Kj3L4m",
      "name": "finance-database-server",
      "transport": "http",
      "status": "active",
      "sensitivity_level": "high",
      "tools_count": 2,
      "created_at": "2024-11-20T10:30:45.123Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 150,
    "pages": 3
  }
}
```

### Get Server Details

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/servers/srv_2N8h9Kj3L4m"
```

**Response:**

```json
{
  "id": "srv_2N8h9Kj3L4m",
  "name": "finance-database-server",
  "description": null,
  "transport": "http",
  "endpoint": "https://mcp-finance.internal:8080",
  "status": "active",
  "sensitivity_level": "high",
  "tools": [
    {
      "id": "tool_Abc123",
      "name": "query_financial_data",
      "description": "Query financial database",
      "sensitivity_level": "high",
      "requires_approval": true
    },
    {
      "id": "tool_Def456",
      "name": "get_account_balance",
      "description": "Get account balance",
      "sensitivity_level": "medium",
      "requires_approval": false
    }
  ],
  "metadata": {
    "team": "finance",
    "environment": "production",
    "compliance": "SOC2"
  },
  "created_at": "2024-11-20T10:30:45.123Z",
  "updated_at": "2024-11-20T10:30:45.123Z"
}
```

---

## Policy Evaluation

### Evaluate Single Policy

```bash
curl -X POST https://sark.company.com/api/v1/policy/evaluate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_abc123",
    "action": "tool:invoke",
    "tool": "query_financial_data",
    "server_id": "srv_2N8h9Kj3L4m",
    "parameters": {
      "query": "SELECT * FROM accounts WHERE balance > 1000000"
    }
  }'
```

**Response (200 OK):**

```json
{
  "decision": "allow",
  "reason": "Allowed: User is team member with appropriate clearance",
  "filtered_parameters": {
    "query": "SELECT * FROM accounts WHERE balance > 1000000",
    "limit": 100
  },
  "audit_id": "audit_xyz789"
}
```

**Response (Denied):**

```json
{
  "decision": "deny",
  "reason": "Denied: Access to high-sensitivity tools not allowed after business hours",
  "filtered_parameters": null,
  "audit_id": "audit_xyz789"
}
```

### Batch Policy Evaluation

```bash
curl -X POST https://sark.company.com/api/v1/policy/batch-evaluate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "user_id": "user_abc123",
      "action": "tool:invoke",
      "tool": "query_financial_data"
    },
    {
      "user_id": "user_abc123",
      "action": "tool:invoke",
      "tool": "get_account_balance"
    },
    {
      "user_id": "user_def456",
      "action": "server:register"
    }
  ]'
```

**Response:**

```json
[
  {
    "decision": "allow",
    "reason": "Allowed: Team member access"
  },
  {
    "decision": "allow",
    "reason": "Allowed: Medium sensitivity, work hours"
  },
  {
    "decision": "deny",
    "reason": "Denied: Insufficient permissions"
  }
]
```

### Python SDK

```python
# Evaluate policy
decision = client.policy.evaluate(
    user_id="user_abc123",
    action="tool:invoke",
    tool="query_financial_data",
    parameters={"query": "SELECT * FROM accounts"}
)

if decision.allow:
    # Proceed with tool invocation
    result = invoke_tool(decision.filtered_parameters)
else:
    # Log denial and inform user
    log_denial(decision.reason)
    raise PermissionDenied(decision.reason)
```

---

## Audit Log Queries

### Query Audit Events

```bash
# Get recent audit events
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/audit/events?limit=100"

# Filter by user
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/audit/events?user_id=user_abc123"

# Filter by event type
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/audit/events?event_type=authorization_denied"

# Time range query
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/audit/events?start_time=2024-11-01T00:00:00Z&end_time=2024-11-20T23:59:59Z"
```

**Response:**

```json
{
  "events": [
    {
      "id": "evt_abc123",
      "timestamp": "2024-11-20T10:35:12.456Z",
      "event_type": "authorization_denied",
      "severity": "medium",
      "user": {
        "id": "user_abc123",
        "email": "alice@company.com"
      },
      "resource": {
        "type": "mcp_tool",
        "id": "tool_xyz789",
        "name": "query_financial_data"
      },
      "action": "tool:invoke",
      "decision": "deny",
      "reason": "After-hours access to sensitive tool denied",
      "context": {
        "ip_address": "10.0.1.45",
        "request_id": "req_987654"
      }
    }
  ],
  "pagination": {
    "limit": 100,
    "offset": 0,
    "total": 1523
  }
}
```

### Export Audit Data

```bash
# Export to CSV
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/audit/export?format=csv&start_time=2024-11-01T00:00:00Z" \
     -o audit-export.csv

# Export to JSON
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://sark.company.com/api/v1/audit/export?format=json" \
     -o audit-export.json
```

---

## SDK Examples

### Python SDK - Complete Example

```python
from sark_sdk import SARKClient
from sark_sdk.exceptions import SARKAPIError, PermissionDenied

# Initialize client
client = SARKClient(
    api_key="sark_live_abc123",
    base_url="https://sark.company.com"
)

# Register MCP server
try:
    server = client.servers.create(
        name="my-mcp-server",
        transport="http",
        endpoint="https://mcp.myapp.com",
        tools=[{
            "name": "search_database",
            "description": "Search product database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }]
    )
    print(f"Server registered: {server.id}")
except SARKAPIError as e:
    print(f"Registration failed: {e}")

# Evaluate policy before tool invocation
try:
    decision = client.policy.evaluate(
        user_id=current_user.id,
        action="tool:invoke",
        tool="search_database",
        parameters={"query": "SELECT * FROM products"}
    )

    if decision.allow:
        # Execute tool with filtered parameters
        result = execute_tool(decision.filtered_parameters)
        return result
    else:
        raise PermissionDenied(decision.reason)

except PermissionDenied as e:
    # Log denial
    logger.warning(f"Access denied: {e}")
    # Return user-friendly error
    return {"error": "You don't have permission to perform this action"}
```

### Go SDK Example

```go
package main

import (
    "context"
    "fmt"
    "github.com/company/sark-go-sdk"
)

func main() {
    client := sark.NewClient("sark_live_abc123")

    // Register server
    server, err := client.Servers.Create(context.Background(), &sark.ServerCreateParams{
        Name:      "my-mcp-server",
        Transport: "http",
        Endpoint:  "https://mcp.myapp.com",
        Tools: []sark.Tool{
            {
                Name:        "search_database",
                Description: "Search product database",
                Parameters: map[string]interface{}{
                    "type": "object",
                    "properties": map[string]interface{}{
                        "query": map[string]string{"type": "string"},
                    },
                },
            },
        },
    })

    if err != nil {
        panic(err)
    }

    fmt.Printf("Server registered: %s\n", server.ID)

    // Evaluate policy
    decision, err := client.Policy.Evaluate(context.Background(), &sark.PolicyEvaluateParams{
        UserID: "user_abc123",
        Action: "tool:invoke",
        Tool:   "search_database",
    })

    if err != nil {
        panic(err)
    }

    if decision.Allow {
        fmt.Println("Access granted")
    } else {
        fmt.Printf("Access denied: %s\n", decision.Reason)
    }
}
```

---

## Webhooks & Events

### Configure Webhook

```bash
curl -X POST https://sark.company.com/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhooks/sark",
    "events": [
      "server.registered",
      "authorization.denied",
      "policy.updated"
    ],
    "secret": "whsec_abc123xyz789"
  }'
```

### Webhook Payload Example

```json
{
  "id": "evt_webhook_abc123",
  "type": "authorization.denied",
  "timestamp": "2024-11-20T10:35:12.456Z",
  "data": {
    "user_id": "user_abc123",
    "user_email": "alice@company.com",
    "tool": "query_financial_data",
    "server_id": "srv_xyz789",
    "reason": "After-hours access denied",
    "severity": "medium"
  }
}
```

### Verify Webhook Signature

```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, f"sha256={expected_signature}")

# Flask example
@app.route('/webhooks/sark', methods=['POST'])
def handle_sark_webhook():
    signature = request.headers.get('X-SARK-Signature')
    payload = request.get_data()

    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        return 'Invalid signature', 401

    event = request.json
    # Process event...
    return '', 200
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "type": "validation_error",
    "message": "Invalid request parameters",
    "code": "INVALID_PARAMETERS",
    "details": {
      "field": "sensitivity_level",
      "issue": "must be one of: low, medium, high, critical"
    },
    "request_id": "req_abc123"
  }
}
```

### Common Error Codes

| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_REQUEST | Malformed request |
| 401 | UNAUTHORIZED | Missing/invalid authentication |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource already exists |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |
| 503 | SERVICE_UNAVAILABLE | Temporary unavailability |

### Python Error Handling

```python
from sark_sdk.exceptions import (
    SARKAPIError,
    ValidationError,
    RateLimitError,
    NotFoundError
)

try:
    server = client.servers.create(...)
except ValidationError as e:
    print(f"Invalid parameters: {e.details}")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}")
    time.sleep(e.retry_after)
    # Retry request
except NotFoundError:
    print("Server not found")
except SARKAPIError as e:
    print(f"API error: {e}")
```

---

## Rate Limiting

### Rate Limit Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1700500000
```

### Handling Rate Limits

```python
import time

def make_request_with_retry(client, endpoint, **kwargs):
    """Make request with automatic retry on rate limit."""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            return client.request(endpoint, **kwargs)
        except RateLimitError as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise

            # Wait until rate limit resets
            wait_time = e.retry_after
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
```

---

## Best Practices

### 1. Use SDK When Available

```python
# GOOD - Use SDK
from sark_sdk import SARKClient
client = SARKClient(api_key="...")
server = client.servers.create(...)

# AVOID - Manual HTTP requests
import requests
response = requests.post("https://sark.company.com/api/v1/servers", ...)
```

### 2. Handle Errors Gracefully

```python
try:
    decision = client.policy.evaluate(...)
    if not decision.allow:
        # Don't expose internal reasons to end users
        raise UserError("You don't have permission to perform this action")
except SARKAPIError as e:
    # Log for debugging
    logger.error(f"SARK API error: {e}")
    # Generic error to user
    raise UserError("Service temporarily unavailable")
```

### 3. Cache Policy Decisions (Carefully)

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
def get_policy_decision(user_id, tool_id, timestamp_hour):
    """Cache policy decisions for 1 hour."""
    return client.policy.evaluate(
        user_id=user_id,
        action="tool:invoke",
        tool=tool_id
    )

# Use with current hour for cache key
decision = get_policy_decision(
    user_id,
    tool_id,
    datetime.now().replace(minute=0, second=0, microsecond=0)
)
```

### 4. Use Batch APIs

```python
# GOOD - Batch evaluation
decisions = client.policy.batch_evaluate([
    {"user_id": user1, "tool": tool1},
    {"user_id": user2, "tool": tool2},
    # ... 100 evaluations
])

# AVOID - Multiple individual requests
for user_id, tool in combinations:
    decision = client.policy.evaluate(user_id, tool)  # 100 API calls!
```

### 5. Implement Idempotency

```python
import uuid

# Generate idempotency key for server registration
idempotency_key = str(uuid.uuid4())

try:
    server = client.servers.create(
        name="my-server",
        ...,
        headers={"Idempotency-Key": idempotency_key}
    )
except ConflictError:
    # Server already registered, fetch it
    server = client.servers.get_by_name("my-server")
```

---

**Document Version:** 1.0
**Last Updated:** November 2025
**API Version:** v1
**Support:** api-support@company.com
