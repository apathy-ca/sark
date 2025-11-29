# SARK v2.0 API Reference

**Version:** 2.0.0
**Last Updated:** December 2025
**Status:** Reference Implementation for GRID Protocol v1.0

---

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Resources API](#resources-api)
- [Adapters API](#adapters-api)
- [Authorization API](#authorization-api)
- [Federation API](#federation-api)
- [Cost Attribution API](#cost-attribution-api)
- [Audit API](#audit-api)
- [Policy API](#policy-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Backward Compatibility](#backward-compatibility)

---

## Overview

SARK v2.0 provides a comprehensive REST API for governing machine-to-machine interactions across multiple protocols. The API is organized around resources (servers, APIs, services) and capabilities (tools, endpoints, methods) that can be governed through unified policies.

### Key Concepts

- **Resource**: Any governed entity (MCP server, REST API, gRPC service, etc.)
- **Capability**: An executable action on a resource (tool, endpoint, method)
- **Adapter**: Protocol-specific implementation that translates between protocols and GRID
- **Principal**: A user, service, or application making requests
- **Policy**: OPA (Open Policy Agent) rules governing access

---

## Base URL

```
Production:  https://sark.yourdomain.com/api/v2
Development: http://localhost:8000/api/v2
```

All endpoints in this document are relative to the base URL.

---

## Authentication

SARK v2.0 supports multiple authentication methods:

### API Key Authentication

```http
GET /api/v2/resources
X-API-Key: your-api-key-here
```

### Bearer Token (JWT)

```http
GET /api/v2/resources
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Session Cookie

```http
GET /api/v2/resources
Cookie: session=your-session-cookie
```

For details on obtaining authentication credentials, see [Authentication Guide](../../AUTHENTICATION.md).

---

## Resources API

Resources represent any governed entity (MCP servers, REST APIs, gRPC services, etc.).

### List Resources

```http
GET /api/v2/resources
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `protocol` | string | Filter by protocol (mcp, http, grpc) |
| `sensitivity_level` | string | Filter by sensitivity (low, medium, high, critical) |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 50, max: 100) |
| `search` | string | Search in name and endpoint |

**Example Request:**

```bash
curl -X GET "https://sark.yourdomain.com/api/v2/resources?protocol=mcp&page=1" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
{
  "items": [
    {
      "id": "mcp-filesystem-server",
      "name": "Filesystem Server",
      "protocol": "mcp",
      "endpoint": "npx -y @modelcontextprotocol/server-filesystem",
      "sensitivity_level": "high",
      "metadata": {
        "transport": "stdio",
        "allowed_directories": ["/home/user/documents"]
      },
      "created_at": "2025-12-01T10:00:00Z",
      "updated_at": "2025-12-01T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

### Get Resource

```http
GET /api/v2/resources/{resource_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `resource_id` | string | Unique resource identifier |

**Example Request:**

```bash
curl -X GET "https://sark.yourdomain.com/api/v2/resources/mcp-filesystem-server" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
{
  "id": "mcp-filesystem-server",
  "name": "Filesystem Server",
  "protocol": "mcp",
  "endpoint": "npx -y @modelcontextprotocol/server-filesystem",
  "sensitivity_level": "high",
  "metadata": {
    "transport": "stdio",
    "allowed_directories": ["/home/user/documents"]
  },
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-01T10:00:00Z",
  "capabilities": [
    {
      "id": "read_file",
      "resource_id": "mcp-filesystem-server",
      "name": "read_file",
      "description": "Read a file from the filesystem",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {"type": "string"}
        },
        "required": ["path"]
      },
      "sensitivity_level": "high",
      "metadata": {}
    }
  ]
}
```

### Register Resource

```http
POST /api/v2/resources
```

**Request Body:**

```json
{
  "protocol": "mcp",
  "discovery_config": {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    "env": {
      "ALLOWED_DIRECTORIES": "/home/user/documents"
    }
  },
  "sensitivity_level": "high"
}
```

**Protocol-Specific Discovery Configs:**

**MCP:**
```json
{
  "protocol": "mcp",
  "discovery_config": {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-name"]
  }
}
```

**HTTP/REST:**
```json
{
  "protocol": "http",
  "discovery_config": {
    "base_url": "https://api.example.com",
    "openapi_spec_url": "https://api.example.com/openapi.json",
    "auth": {
      "type": "bearer",
      "token": "your-api-token"
    }
  }
}
```

**gRPC:**
```json
{
  "protocol": "grpc",
  "discovery_config": {
    "host": "localhost:50051",
    "proto_file": "/path/to/service.proto",
    "tls": {
      "enabled": true,
      "cert": "/path/to/cert.pem"
    }
  }
}
```

**Example Response:**

```json
{
  "resources": [
    {
      "id": "mcp-filesystem-server",
      "name": "Filesystem Server",
      "protocol": "mcp",
      "endpoint": "npx -y @modelcontextprotocol/server-filesystem",
      "sensitivity_level": "high",
      "metadata": {...},
      "created_at": "2025-12-01T10:00:00Z",
      "updated_at": "2025-12-01T10:00:00Z"
    }
  ],
  "capabilities_discovered": 5
}
```

### Update Resource

```http
PATCH /api/v2/resources/{resource_id}
```

**Request Body:**

```json
{
  "sensitivity_level": "critical",
  "metadata": {
    "description": "Production filesystem server",
    "owner": "platform-team"
  }
}
```

### Delete Resource

```http
DELETE /api/v2/resources/{resource_id}
```

**Example Response:**

```json
{
  "deleted": true,
  "resource_id": "mcp-filesystem-server"
}
```

### Refresh Resource Capabilities

```http
POST /api/v2/resources/{resource_id}/refresh
```

Re-queries the resource to detect new or changed capabilities.

**Example Response:**

```json
{
  "resource_id": "mcp-filesystem-server",
  "capabilities_before": 5,
  "capabilities_after": 6,
  "new_capabilities": ["write_file"],
  "removed_capabilities": []
}
```

### Resource Health Check

```http
GET /api/v2/resources/{resource_id}/health
```

**Example Response:**

```json
{
  "resource_id": "mcp-filesystem-server",
  "healthy": true,
  "checked_at": "2025-12-01T12:00:00Z",
  "details": {
    "reachable": true,
    "response_time_ms": 45
  }
}
```

---

## Adapters API

Adapters are protocol-specific implementations that enable SARK to govern different types of resources.

### List Adapters

```http
GET /api/v2/adapters
```

**Example Response:**

```json
{
  "adapters": [
    {
      "protocol_name": "mcp",
      "protocol_version": "2024-11-05",
      "adapter_class": "MCPAdapter",
      "supports_streaming": true,
      "supports_batch": false,
      "module": "sark.adapters.mcp"
    },
    {
      "protocol_name": "http",
      "protocol_version": "1.1",
      "adapter_class": "HTTPAdapter",
      "supports_streaming": false,
      "supports_batch": true,
      "module": "sark.adapters.http"
    },
    {
      "protocol_name": "grpc",
      "protocol_version": "1.0",
      "adapter_class": "GRPCAdapter",
      "supports_streaming": true,
      "supports_batch": false,
      "module": "sark.adapters.grpc"
    }
  ]
}
```

### Get Adapter Details

```http
GET /api/v2/adapters/{protocol_name}
```

**Example Response:**

```json
{
  "protocol_name": "mcp",
  "protocol_version": "2024-11-05",
  "adapter_class": "MCPAdapter",
  "supports_streaming": true,
  "supports_batch": false,
  "module": "sark.adapters.mcp",
  "capabilities": {
    "authentication": ["none", "api_key"],
    "transports": ["stdio", "sse"],
    "streaming": true,
    "batch": false
  }
}
```

---

## Authorization API

Authorization endpoints handle policy evaluation and capability invocation.

### Authorize Request

```http
POST /api/v2/authorize
```

Evaluate policies and execute a capability if authorized.

**Request Body:**

```json
{
  "capability_id": "read_file",
  "principal_id": "user-123",
  "arguments": {
    "path": "/home/user/documents/file.txt"
  },
  "context": {
    "ip_address": "192.168.1.100",
    "user_agent": "MyApp/1.0"
  }
}
```

**Example Response (Allowed):**

```json
{
  "decision": "allow",
  "result": {
    "success": true,
    "result": {
      "content": "File contents here..."
    },
    "duration_ms": 123.45,
    "metadata": {}
  },
  "policy_evaluation": {
    "allowed": true,
    "policies_evaluated": ["grid.base.allow_developers"],
    "duration_ms": 2.1
  },
  "audit_id": "audit-789"
}
```

**Example Response (Denied):**

```json
{
  "decision": "deny",
  "reason": "Principal does not have required role: admin",
  "policy_evaluation": {
    "allowed": false,
    "policies_evaluated": ["grid.base.require_admin"],
    "duration_ms": 1.8
  },
  "audit_id": "audit-790"
}
```

### Batch Authorization

```http
POST /api/v2/authorize/batch
```

Authorize and execute multiple capabilities in one request.

**Request Body:**

```json
{
  "requests": [
    {
      "capability_id": "read_file",
      "principal_id": "user-123",
      "arguments": {"path": "/file1.txt"}
    },
    {
      "capability_id": "read_file",
      "principal_id": "user-123",
      "arguments": {"path": "/file2.txt"}
    }
  ]
}
```

**Example Response:**

```json
{
  "results": [
    {
      "index": 0,
      "decision": "allow",
      "result": {
        "success": true,
        "result": {"content": "..."},
        "duration_ms": 100
      }
    },
    {
      "index": 1,
      "decision": "deny",
      "reason": "Rate limit exceeded"
    }
  ],
  "total": 2,
  "allowed": 1,
  "denied": 1
}
```

### Pre-flight Check

```http
POST /api/v2/authorize/check
```

Check authorization without executing the capability.

**Request Body:**

```json
{
  "capability_id": "read_file",
  "principal_id": "user-123",
  "arguments": {
    "path": "/home/user/documents/file.txt"
  }
}
```

**Example Response:**

```json
{
  "allowed": true,
  "reason": null,
  "policies_evaluated": ["grid.base.allow_developers"],
  "estimated_cost": 0.001,
  "warnings": []
}
```

---

## Federation API

Federation enables cross-organization governance between multiple SARK instances.

### Get Federation Info

```http
GET /api/v2/federation/info
```

**Example Response:**

```json
{
  "node_id": "orga.com",
  "version": "2.0.0",
  "capabilities": ["authorization", "audit_query"],
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "trusted_nodes": ["orgb.com", "orgc.com"]
}
```

### Cross-Org Authorization

```http
POST /api/v2/federation/authorize
```

This endpoint is called by remote SARK nodes for cross-org authorization.

**Request Body:**

```json
{
  "request_id": "uuid-123",
  "timestamp": "2025-12-01T10:00:00Z",
  "source_node": "orgb.com",
  "principal": {
    "id": "alice@orgb.com",
    "type": "user",
    "attributes": {
      "role": "developer"
    },
    "source_org": "orgb.com"
  },
  "resource": {
    "id": "resource-123",
    "type": "mcp_server",
    "name": "database-server",
    "owner_org": "orga.com"
  },
  "action": "execute",
  "capability": {
    "id": "query_database",
    "name": "query_database"
  }
}
```

**Example Response:**

```json
{
  "request_id": "uuid-123",
  "timestamp": "2025-12-01T10:00:01Z",
  "decision": "allow",
  "reason": "Cross-org developer access permitted",
  "policy_id": "cross-org-dev-access",
  "ttl_seconds": 300,
  "conditions": [
    "rate_limit: 100 requests/hour",
    "audit_required: true"
  ]
}
```

### List Federation Nodes

```http
GET /api/v2/federation/nodes
```

**Example Response:**

```json
{
  "nodes": [
    {
      "node_id": "orgb.com",
      "name": "Organization B",
      "endpoint": "https://sark.orgb.com:8443",
      "enabled": true,
      "trusted_since": "2025-11-01T00:00:00Z",
      "rate_limit_per_hour": 10000
    }
  ]
}
```

### Register Federation Node

```http
POST /api/v2/federation/nodes
```

**Request Body:**

```json
{
  "node_id": "orgb.com",
  "name": "Organization B",
  "endpoint": "https://sark.orgb.com:8443",
  "trust_anchor_cert": "-----BEGIN CERTIFICATE-----\n...",
  "rate_limit_per_hour": 10000
}
```

---

## Cost Attribution API

Track and enforce resource usage costs.

### Estimate Cost

```http
POST /api/v2/cost/estimate
```

**Request Body:**

```json
{
  "capability_id": "query_database",
  "arguments": {
    "query": "SELECT * FROM large_table"
  }
}
```

**Example Response:**

```json
{
  "estimated_cost": 0.05,
  "currency": "USD",
  "breakdown": {
    "compute": 0.03,
    "data_transfer": 0.02
  },
  "confidence": "medium"
}
```

### Get Cost Report

```http
GET /api/v2/cost/report
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `principal_id` | string | Filter by principal |
| `resource_id` | string | Filter by resource |
| `start_date` | ISO 8601 | Start of date range |
| `end_date` | ISO 8601 | End of date range |
| `group_by` | string | Group by: day, week, month, principal, resource |

**Example Request:**

```bash
curl -X GET "https://sark.yourdomain.com/api/v2/cost/report?principal_id=user-123&start_date=2025-12-01&end_date=2025-12-31&group_by=day" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
{
  "total_cost": 12.45,
  "currency": "USD",
  "period": {
    "start": "2025-12-01T00:00:00Z",
    "end": "2025-12-31T23:59:59Z"
  },
  "breakdown": [
    {
      "date": "2025-12-01",
      "cost": 0.45,
      "invocations": 120
    },
    {
      "date": "2025-12-02",
      "cost": 0.52,
      "invocations": 135
    }
  ]
}
```

### Get Principal Budget

```http
GET /api/v2/cost/budget/{principal_id}
```

**Example Response:**

```json
{
  "principal_id": "user-123",
  "daily_budget": 10.00,
  "monthly_budget": 250.00,
  "daily_spent": 2.35,
  "monthly_spent": 45.67,
  "currency": "USD",
  "last_daily_reset": "2025-12-01T00:00:00Z",
  "last_monthly_reset": "2025-12-01T00:00:00Z"
}
```

### Update Principal Budget

```http
PUT /api/v2/cost/budget/{principal_id}
```

**Request Body:**

```json
{
  "daily_budget": 15.00,
  "monthly_budget": 300.00
}
```

---

## Audit API

Query and export audit logs.

### Query Audit Logs

```http
GET /api/v2/audit/logs
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `principal_id` | string | Filter by principal |
| `resource_id` | string | Filter by resource |
| `capability_id` | string | Filter by capability |
| `decision` | string | Filter by decision (allow, deny) |
| `start_time` | ISO 8601 | Start of time range |
| `end_time` | ISO 8601 | End of time range |
| `correlation_id` | string | Filter by correlation ID (for federation) |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

**Example Response:**

```json
{
  "items": [
    {
      "event_id": "evt-123",
      "timestamp": "2025-12-01T10:00:00Z",
      "event_type": "capability_invocation",
      "principal_id": "user-123",
      "resource_id": "mcp-filesystem-server",
      "capability_id": "read_file",
      "decision": "allow",
      "duration_ms": 123.45,
      "cost": 0.001,
      "metadata": {
        "ip_address": "192.168.1.100"
      }
    }
  ],
  "total": 1000,
  "page": 1,
  "page_size": 50
}
```

### Export Audit Logs

```http
POST /api/v2/audit/export
```

**Request Body:**

```json
{
  "format": "json",
  "filters": {
    "start_time": "2025-12-01T00:00:00Z",
    "end_time": "2025-12-31T23:59:59Z",
    "principal_id": "user-123"
  }
}
```

**Supported Formats:**
- `json` - JSON lines format
- `csv` - CSV format
- `parquet` - Apache Parquet format

**Example Response:**

```json
{
  "export_id": "export-456",
  "status": "processing",
  "download_url": null,
  "estimated_completion": "2025-12-01T10:05:00Z"
}
```

Check export status:

```http
GET /api/v2/audit/export/{export_id}
```

---

## Policy API

Manage OPA policies.

### List Policies

```http
GET /api/v2/policies
```

**Example Response:**

```json
{
  "policies": [
    {
      "id": "policy-123",
      "name": "base-access-control",
      "package": "grid.base",
      "version": "1.0.0",
      "enabled": true,
      "created_at": "2025-12-01T10:00:00Z"
    }
  ]
}
```

### Create Policy

```http
POST /api/v2/policies
```

**Request Body:**

```json
{
  "name": "developer-access",
  "package": "grid.custom",
  "rego_code": "package grid.custom\n\nallow if {\n    input.principal.role == \"developer\"\n}"
}
```

### Update Policy

```http
PUT /api/v2/policies/{policy_id}
```

### Delete Policy

```http
DELETE /api/v2/policies/{policy_id}
```

### Test Policy

```http
POST /api/v2/policies/test
```

Test a policy against sample input without saving it.

**Request Body:**

```json
{
  "rego_code": "package grid.test\n\nallow if {\n    input.principal.role == \"admin\"\n}",
  "input": {
    "principal": {
      "role": "admin"
    }
  }
}
```

---

## Error Handling

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource with id 'xyz' not found",
    "details": {
      "resource_id": "xyz"
    },
    "request_id": "req-789"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Policy denied access |
| `RESOURCE_NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `ADAPTER_ERROR` | 502 | Protocol adapter error |
| `POLICY_ERROR` | 500 | Policy evaluation error |

---

## Rate Limiting

API requests are rate limited per API key or principal:

- **Default**: 1000 requests/hour
- **Burst**: 50 requests/minute

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1733058000
```

When rate limited, you'll receive a `429 Too Many Requests` response:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 3600 seconds.",
    "retry_after": 3600
  }
}
```

---

## Backward Compatibility

SARK v2.0 maintains backward compatibility with v1.x endpoints:

### v1.x Endpoints (Deprecated)

```http
POST /api/v1/servers        → Use POST /api/v2/resources (protocol=mcp)
GET  /api/v1/servers        → Use GET /api/v2/resources?protocol=mcp
GET  /api/v1/servers/{id}   → Use GET /api/v2/resources/{id}
```

v1.x endpoints will be supported until v3.0 (estimated Q1 2027).

---

## SDK Examples

### Python SDK

```python
from sark_sdk import SARKClient

client = SARKClient(
    base_url="https://sark.yourdomain.com",
    api_key="your-api-key"
)

# Register a resource
resource = client.resources.register(
    protocol="mcp",
    discovery_config={
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
)

# Authorize and execute
result = client.authorize(
    capability_id="read_file",
    principal_id="user-123",
    arguments={"path": "/file.txt"}
)

print(result.decision)  # "allow" or "deny"
if result.decision == "allow":
    print(result.result)
```

### JavaScript SDK

```javascript
import { SARKClient } from '@sark/sdk';

const client = new SARKClient({
  baseURL: 'https://sark.yourdomain.com',
  apiKey: 'your-api-key'
});

// Register a resource
const resource = await client.resources.register({
  protocol: 'http',
  discoveryConfig: {
    base_url: 'https://api.example.com',
    openapi_spec_url: 'https://api.example.com/openapi.json'
  }
});

// Authorize and execute
const result = await client.authorize({
  capabilityId: 'getUser',
  principalId: 'user-123',
  arguments: { userId: '456' }
});

console.log(result.decision);
```

---

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:

```
GET /api/v2/openapi.json
```

Interactive API documentation (Swagger UI):

```
https://sark.yourdomain.com/docs
```

---

## Support

- **Documentation**: https://docs.sark.dev
- **GitHub**: https://github.com/yourusername/sark
- **Discord**: https://discord.gg/sark
- **Email**: support@sark.dev

---

**Document Version:** 1.0
**Last Updated:** December 2025
**Maintainer:** SARK Core Team
