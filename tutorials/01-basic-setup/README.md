# Tutorial 1: Basic Setup and First Tool Invocation

**Duration:** 15 minutes
**Difficulty:** Beginner
**Prerequisites:** Docker and Docker Compose v2 installed

## What You'll Learn

In this tutorial, you'll:
1. Start SARK with the minimal profile (5-minute setup)
2. Authenticate and get access tokens
3. Register your first MCP server
4. Invoke a tool through SARK's governance layer
5. View audit logs of your actions

By the end, you'll understand the complete flow from starting SARK to making governed MCP tool calls.

---

## Architecture Overview

```
┌──────────────┐
│  You (curl)  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────┐
│    SARK (Governance Layer)       │
│  ┌────────────────────────────┐  │
│  │ 1. Authenticate            │  │
│  │ 2. Authorize (OPA)         │  │
│  │ 3. Audit (TimescaleDB)     │  │
│  └────────────────────────────┘  │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│   MCP Server (Your Backend)      │
│  ┌────────────────────────────┐  │
│  │ Tool: execute_query        │  │
│  │ Tool: create_report        │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

SARK sits between you (or AI assistants) and MCP servers, providing:
- **Authentication** - Who are you?
- **Authorization** - What can you do?
- **Audit** - What did you do?

---

## Step 1: Start SARK (5 Minutes)

### Clone Repository

```bash
# Clone SARK
git clone https://github.com/apathy-ca/sark.git
cd sark
```

### Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# The defaults work for this tutorial - no changes needed!
# But let's verify key settings:
cat .env | grep -E "(POSTGRES_|REDIS_|OPA_|LDAP_)"
```

You should see:
```bash
POSTGRES_ENABLED=true
POSTGRES_MODE=managed
REDIS_ENABLED=true
REDIS_MODE=managed
OPA_ENABLED=true
LDAP_ENABLED=true
LDAP_SERVER=ldap://openldap:389
```

### Start Minimal Stack

```bash
# Start SARK with minimal profile (4 services: app, database, cache, OPA)
docker compose --profile minimal up -d

# This pulls images and starts containers
# First run takes 2-3 minutes (image downloads)
# Subsequent starts take ~30 seconds
```

### Verify Services

Wait 30 seconds for services to become healthy, then check:

```bash
# Check all services are running
docker compose ps
```

Expected output:
```
NAME           IMAGE                         STATUS
sark-app       sark-app:latest               Up (healthy)
sark-database  postgres:15-alpine            Up (healthy)
sark-cache     redis:7-alpine                Up (healthy)
sark-opa       openpolicyagent/opa:0.60.0    Up (healthy)
```

All services should show `Up (healthy)` status.

### Test API Health

```bash
# Simple health check
curl http://localhost:8000/health | jq

# Expected response:
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "environment": "development"
# }
```

```bash
# Detailed health check (includes dependencies)
curl http://localhost:8000/health/detailed | jq

# Expected response:
# {
#   "status": "healthy",
#   "overall_healthy": true,
#   "dependencies": {
#     "postgresql": {"healthy": true, "latency_ms": 12.5},
#     "redis": {"healthy": true, "latency_ms": 3.2},
#     "opa": {"healthy": true, "latency_ms": 8.7}
#   }
# }
```

🎉 **Success!** SARK is running. Let's authenticate.

---

## Step 2: Authenticate with LDAP

SARK supports multiple authentication methods (LDAP, OIDC, SAML, API keys). We'll use LDAP for simplicity.

### Default Test Users

The minimal stack includes an OpenLDAP server with pre-configured test users:

| Username | Password | Roles | Use Case |
|----------|----------|-------|----------|
| `john.doe` | `password` | `developer`, `team_lead` | Developer with elevated permissions |
| `jane.smith` | `password` | `developer` | Standard developer |
| `admin` | `admin` | `admin`, `security_admin` | Full admin access |

### Login as Developer

```bash
# Authenticate with LDAP
curl -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "password": "password"
  }' | jq

# Save the response to a file for easy access
curl -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "password": "password"
  }' > /tmp/sark-auth.json

# View the tokens
cat /tmp/sark-auth.json | jq
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
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

### Save Tokens

```bash
# Extract and save access token for subsequent requests
export ACCESS_TOKEN=$(cat /tmp/sark-auth.json | jq -r '.access_token')

# Verify it's set
echo $ACCESS_TOKEN
# Should print a long JWT string like: eyJhbGciOiJIUzI1NiIs...
```

### Verify Authentication

```bash
# Get current user info
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected response:
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

🎉 **Success!** You're authenticated. Now let's register an MCP server.

---

## Step 3: Register Your First MCP Server

MCP servers provide tools that AI assistants (or you) can invoke. Let's register a mock analytics database server.

### What is an MCP Server?

An MCP (Model Context Protocol) server exposes tools, resources, and prompts to AI assistants. For example:
- A database server might expose `execute_query` tool
- A ticketing server might expose `create_ticket` tool
- A search server might expose `semantic_search` tool

SARK governs access to these tools with policies.

### Register Analytics Database Server

```bash
# Register a mock analytics database MCP server
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "analytics-db-server",
    "description": "Analytics database server with query tools",
    "transport": "http",
    "endpoint": "http://analytics-db.internal.example.com:8080",
    "version": "2025-06-18",
    "capabilities": ["tools"],
    "tools": [
      {
        "name": "execute_query",
        "description": "Execute read-only SQL query on analytics database",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "SQL SELECT query to execute"
            },
            "database": {
              "type": "string",
              "description": "Database name",
              "enum": ["analytics", "reporting", "staging"]
            },
            "limit": {
              "type": "integer",
              "description": "Maximum rows to return",
              "minimum": 1,
              "maximum": 10000,
              "default": 1000
            }
          },
          "required": ["query", "database"]
        },
        "sensitivity_level": "high",
        "requires_approval": false
      },
      {
        "name": "create_report",
        "description": "Generate analytics report from query results",
        "parameters": {
          "type": "object",
          "properties": {
            "report_name": {"type": "string"},
            "query": {"type": "string"},
            "format": {
              "type": "string",
              "enum": ["pdf", "csv", "excel"]
            }
          },
          "required": ["report_name", "query"]
        },
        "sensitivity_level": "medium",
        "requires_approval": false
      }
    ],
    "sensitivity_level": "high",
    "metadata": {
      "team": "data-engineering",
      "owner": "john.doe@example.com",
      "environment": "production",
      "cost_center": "analytics"
    }
  }' | jq
```

Expected response:
```json
{
  "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "name": "analytics-db-server",
  "status": "registered",
  "created_at": "2025-11-27T10:30:00Z",
  "message": "Server registered successfully"
}
```

### Save Server ID

```bash
# Extract and save server ID
export SERVER_ID=$(curl -s -X GET "http://localhost:8000/api/v1/servers?search=analytics-db" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.servers[0].server_id')

# Verify
echo $SERVER_ID
# Should print UUID like: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
```

### List Registered Servers

```bash
# View all registered servers
curl -X GET "http://localhost:8000/api/v1/servers?limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

### Get Server Details

```bash
# Get specific server with full details
curl -X GET "http://localhost:8000/api/v1/servers/$SERVER_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

🎉 **Success!** Your MCP server is registered. Now let's invoke a tool.

---

## Step 4: Invoke a Tool (Governed by OPA)

Now comes the magic - invoking a tool through SARK's governance layer.

### Understanding the Flow

When you invoke a tool through SARK:

1. **Authentication:** SARK validates your JWT token
2. **Authorization:** OPA evaluates policies to decide allow/deny
3. **Audit:** SARK logs the decision and parameters
4. **Proxy:** (If allowed) SARK forwards request to MCP server
5. **Response:** SARK returns result or denial reason

### Policy Evaluation (Dry Run)

Before invoking, let's see if we're allowed:

```bash
# Evaluate policy WITHOUT actually invoking the tool
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "tool:invoke",
    "tool": "execute_query",
    "server_id": "'"$SERVER_ID"'",
    "parameters": {
      "query": "SELECT * FROM users WHERE status = '\''active'\'' LIMIT 100",
      "database": "analytics",
      "limit": 100
    }
  }' | jq
```

Expected response (Allow):
```json
{
  "decision": "allow",
  "reason": "User has role 'developer' and tool sensitivity 'high' is within allowed level",
  "requires_approval": false,
  "filtered_parameters": null,
  "audit_id": "audit_abc123"
}
```

The policy allowed us because:
- User has `developer` role
- Tool sensitivity is `high` (developers can access high-sensitivity tools)
- No parameter filtering needed

### Invoke the Tool

Now let's actually invoke the tool:

```bash
# Invoke execute_query tool on analytics database
curl -X POST "http://localhost:8000/api/v1/servers/$SERVER_ID/tools/execute_query/invoke" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT id, email, created_at FROM users WHERE status = '\''active'\'' ORDER BY created_at DESC",
    "database": "analytics",
    "limit": 10
  }' | jq
```

Expected response:
```json
{
  "success": true,
  "result": {
    "rows_returned": 10,
    "columns": ["id", "email", "created_at"],
    "execution_time_ms": 45,
    "data": [
      {"id": 1, "email": "user1@example.com", "created_at": "2025-01-15T10:30:00Z"},
      {"id": 2, "email": "user2@example.com", "created_at": "2025-01-14T09:15:00Z"}
    ]
  },
  "audit_id": "audit_def456",
  "policy_decision": "allow"
}
```

### Try a Medium-Sensitivity Tool

```bash
# Invoke create_report tool (medium sensitivity)
curl -X POST "http://localhost:8000/api/v1/servers/$SERVER_ID/tools/create_report/invoke" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_name": "Active Users Report - Nov 2025",
    "query": "SELECT COUNT(*) FROM users WHERE status = '\''active'\''",
    "format": "pdf"
  }' | jq
```

### What if Policy Denies?

Let's try something that should be denied. First, let's check the policy:

```bash
# Try to invoke with an invalid database
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "tool:invoke",
    "tool": "execute_query",
    "server_id": "'"$SERVER_ID"'",
    "parameters": {
      "query": "DELETE FROM users",
      "database": "production"
    }
  }' | jq
```

Expected response (Deny):
```json
{
  "decision": "deny",
  "reason": "Query contains forbidden keywords (DELETE). Only SELECT queries allowed.",
  "requires_approval": false,
  "filtered_parameters": null,
  "audit_id": "audit_ghi789"
}
```

🎉 **Success!** You've invoked tools through SARK's governance layer.

---

## Step 5: View Audit Logs

Everything you did was audited. Let's view the audit trail.

### Query Audit Events (API)

```bash
# Get recent audit events for current user
curl -X GET "http://localhost:8000/api/v1/audit/events?user_id=550e8400-e29b-41d4-a716-446655440000&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected response:
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
      "parameters": {"query": "SELECT ...", "database": "analytics"},
      "reason": "User has role 'developer'",
      "duration_ms": 45
    },
    {
      "event_id": "audit_abc123",
      "event_type": "policy_evaluation",
      "timestamp": "2025-11-27T10:34:50.123Z",
      "decision": "allow"
    }
  ],
  "total": 5,
  "limit": 10,
  "offset": 0
}
```

### Query Audit Database Directly

For advanced analysis, you can query TimescaleDB directly:

```bash
# Connect to audit database
docker compose exec timescaledb psql -U sark sark_audit

# Query recent policy decisions
sark_audit=# SELECT
  timestamp,
  event_type,
  user_email,
  tool_name,
  decision,
  reason
FROM audit_events
WHERE event_type IN ('tool_invocation', 'policy_decision')
ORDER BY timestamp DESC
LIMIT 10;

# Query authentication events
sark_audit=# SELECT
  timestamp,
  event_type,
  user_email,
  auth_method,
  success
FROM audit_events
WHERE event_type LIKE '%auth%'
ORDER BY timestamp DESC
LIMIT 10;

# Exit psql
\q
```

### Aggregate Metrics

```bash
# Query audit API for aggregated metrics
curl -X GET "http://localhost:8000/api/v1/audit/metrics?period=1h" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

Expected response:
```json
{
  "period": "1h",
  "total_events": 5,
  "by_event_type": {
    "tool_invocation": 2,
    "policy_evaluation": 2,
    "authentication_success": 1
  },
  "by_decision": {
    "allow": 4,
    "deny": 1
  },
  "top_tools": [
    {"tool_name": "execute_query", "invocations": 2}
  ]
}
```

🎉 **Success!** You've completed the basic tutorial.

---

## Summary

You've learned how to:

✅ Start SARK with the minimal profile (4 services)
✅ Authenticate with LDAP and manage tokens
✅ Register an MCP server with tools
✅ Evaluate policies before invoking tools
✅ Invoke tools through SARK's governance layer
✅ View comprehensive audit logs

### What Actually Happened?

1. **Authentication:** You proved your identity with LDAP credentials
2. **Server Registration:** You registered an MCP server with two tools
3. **Policy Evaluation:** OPA checked if you're allowed to invoke tools
4. **Tool Invocation:** SARK proxied your request to the MCP server
5. **Audit:** Every action was logged to TimescaleDB with full context

### The Value of SARK

Without SARK, your AI assistant would:
- Need direct credentials to every backend system
- Have unrestricted access to all tools
- Leave no audit trail of actions

With SARK, you get:
- **Centralized Authentication:** One login for all MCP servers
- **Policy-Based Access Control:** Fine-grained permissions via OPA
- **Complete Audit Trail:** Every action logged with context
- **Rate Limiting:** Prevent abuse and DOS attacks
- **Approval Workflows:** Break-glass access for critical operations

---

## Next Steps

### Tutorial 2: Authentication Deep Dive
Learn about:
- OIDC authentication (Google, Okta)
- SAML SSO
- API keys for automation
- Session management and token refresh

### Tutorial 3: Policy Development
Learn how to:
- Write Rego policies for OPA
- Implement time-based access control
- Add IP-based restrictions
- Require MFA for critical tools
- Filter sensitive parameters

### Explore Documentation

- **[Quick Start Guide](../../docs/QUICK_START.md)** - Comprehensive getting started
- **[API Reference](../../docs/API_REFERENCE.md)** - Complete API documentation
- **[Architecture](../../docs/ARCHITECTURE.md)** - System design and components
- **[OPA Policies](../../opa/policies/README.md)** - Policy development guide

### Production Deployment

Ready to deploy to production?
- **[Deployment Guide](../../docs/DEPLOYMENT.md)** - Kubernetes, cloud providers
- **[Operational Runbook](../../docs/OPERATIONAL_RUNBOOK.md)** - Day 2 operations
- **[Performance Tuning](../../docs/PERFORMANCE_TUNING.md)** - Scale and optimize

---

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker compose ps

# View logs
docker compose logs api
docker compose logs database
docker compose logs opa

# Restart services
docker compose --profile minimal down
docker compose --profile minimal up -d
```

### Authentication Fails

```bash
# Check LDAP server
docker compose logs openldap

# Test LDAP connection
docker compose exec api curl ldap://openldap:389
```

### Policy Denials

```bash
# Check OPA service
curl http://localhost:8181/health

# Test policy directly
curl -X POST http://localhost:8181/v1/data/mcp/allow \
  -H "Content-Type: application/json" \
  -d '{"input": {"user": {"roles": ["developer"]}, "tool": {"sensitivity_level": "high"}}}'
```

### Need Help?

- Check the [FAQ](../../docs/FAQ.md)
- Review [Common Issues](../../docs/TROUBLESHOOTING.md)
- Open an issue on [GitHub](https://github.com/apathy-ca/sark/issues)

---

## Clean Up

When you're done with the tutorial:

```bash
# Stop services (preserves data)
docker compose --profile minimal down

# Stop and remove all data (fresh start next time)
docker compose --profile minimal down -v
```

---

**Congratulations!** 🎉 You've mastered SARK basics. You're ready to govern MCP deployments at scale.
