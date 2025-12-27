# SARK Gateway Integration - Troubleshooting Guide

**Version**: 1.1.0
**Last Updated**: November 2025
**Audience**: Developers, Operations Engineers, System Administrators

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Symptom-Based Troubleshooting](#symptom-based-troubleshooting)
3. [Common Error Messages](#common-error-messages)
4. [Debug Mode and Logging](#debug-mode-and-logging)
5. [Common Misconfigurations](#common-misconfigurations)
6. [Diagnostic Commands](#diagnostic-commands)
7. [When to File a Bug Report](#when-to-file-a-bug-report)
8. [Advanced Troubleshooting](#advanced-troubleshooting)

---

## Quick Start

### Health Check (30 Seconds)

Run these commands to quickly diagnose the most common issues:

```bash
# 1. Check if Gateway integration is enabled
curl http://localhost:8000/api/v1/version | jq '.features.gateway_integration'
# Expected: true

# 2. Check SARK health
curl http://localhost:8000/health/detailed | jq
# Expected: status "healthy"

# 3. Check Gateway connectivity
curl http://localhost:8080/health
# Expected: {"status": "healthy"}

# 4. Test authorization endpoint
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "test-server",
    "tool_name": "test-tool",
    "user": {"id": "user_123", "email": "test@example.com"}
  }'
# Expected: {"allow": true/false, ...}
```

### Most Common Issues (Top 5)

| Issue | Quick Fix | Section |
|-------|----------|---------|
| Gateway integration disabled | Set `GATEWAY_ENABLED=true` and restart | [#gateway-not-enabled](#error-gateway-integration-not-enabled) |
| Invalid SARK API key | Regenerate key with `generate_api_key` command | [#invalid-api-key](#error-invalid-sark-api-key) |
| Gateway connection failed | Check network connectivity and Gateway health | [#connection-failures](#gateway-connection-failures) |
| Policy denies request | Review OPA policies and user permissions | [#authorization-denied](#error-authorization-denied) |
| Missing configuration | Check `.env` file for required variables | [#missing-env-vars](#missing-environment-variables) |

---

## Symptom-Based Troubleshooting

### Decision Tree

```
Problem with Gateway Integration?
│
├─ Can't enable feature?
│  ├─ Feature flag disabled → See "Gateway Not Enabled"
│  └─ Environment variable missing → See "Missing Configuration"
│
├─ Connection issues?
│  ├─ Gateway unreachable → See "Gateway Connection Failed"
│  ├─ Timeout errors → See "Request Timeouts"
│  └─ TLS/SSL errors → See "Certificate Issues"
│
├─ Authorization failures?
│  ├─ All requests denied → See "Policy Configuration"
│  ├─ Some requests denied → See "Permission Issues"
│  └─ OPA errors → See "OPA Integration"
│
├─ Performance problems?
│  ├─ Slow responses → See "Performance Tuning Guide"
│  ├─ High latency → See "Latency Issues"
│  └─ Timeouts → See "Request Timeouts"
│
└─ Other errors?
   ├─ Check error messages → See "Common Error Messages"
   └─ Enable debug logging → See "Debug Mode"
```

### Symptoms and Solutions

#### Symptom: "Version endpoint shows gateway_integration: false"

**This is a common issue when first setting up Gateway integration.**

**Diagnosis:**
```bash
curl http://localhost:8000/api/v1/version | jq '.features.gateway_integration'
# Output: false (Expected: true)
```

**Root Cause:**
- Gateway integration is disabled in configuration
- Environment variable not set
- SARK not restarted after configuration change

**Solution:**
```bash
# 1. Check environment variable
docker exec -it sark-app env | grep GATEWAY_ENABLED
# Should output: GATEWAY_ENABLED=true

# 2. If not set, update .env file
echo "GATEWAY_ENABLED=true" >> .env

# 3. Restart SARK
docker compose -f docker compose.gateway.yml restart sark

# 4. Verify
curl http://localhost:8000/api/v1/version | jq '.features.gateway_integration'
# Output: true ✓
```

**Prevention:**
- Always verify `.env` contains `GATEWAY_ENABLED=true` before deployment
- Include feature verification in deployment checklists
- Monitor feature flags in production

---

#### Symptom: "Authorization endpoint returns 404 Not Found"

**This indicates Gateway API routes are not registered.**

**Diagnosis:**
```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Content-Type: application/json"
# Output: 404 Not Found
```

**Root Cause:**
- Gateway integration disabled (routes not registered)
- Incorrect API version in URL
- SARK not fully initialized

**Solution:**
```bash
# 1. Verify Gateway integration is enabled
curl http://localhost:8000/api/v1/version | jq '.features.gateway_integration'

# 2. Check SARK logs for route registration
docker logs sark-app | grep "Gateway integration enabled"
# Should see: "Gateway integration enabled - routes registered"

# 3. Check available routes
curl http://localhost:8000/docs | grep gateway
# Should list /api/v1/gateway/* endpoints

# 4. If still missing, restart SARK
docker compose -f docker compose.gateway.yml restart sark
```

**Related Issues:**
- [Gateway Not Enabled](#error-gateway-integration-not-enabled)
- [Invalid API Version](#error-invalid-api-version)

---

#### Symptom: "Gateway returns 401 Unauthorized"

**This means the Gateway cannot authenticate with SARK.**

**Diagnosis:**
```bash
# Check Gateway logs
docker logs mcp-gateway | grep -i "unauthorized\|401"

# Common errors:
# "Invalid API key"
# "API key missing"
# "Authentication failed"
```

**Root Cause:**
- SARK API key not configured in Gateway
- API key expired or invalid
- API key lacks required permissions

**Solution:**
```bash
# 1. Generate new SARK API key
docker exec -it sark-app python -m sark.cli.generate_api_key \
  --name "MCP Gateway" \
  --type gateway \
  --permissions "gateway:*"

# Output:
# API Key ID: key_abc123
# API Key: sark_gw_xyz789...
# Type: gateway
# Permissions: gateway:*

# 2. Update .env with new key
echo "SARK_API_KEY=sark_gw_xyz789..." >> .env

# 3. Restart Gateway to pick up new key
docker compose -f docker compose.gateway.yml restart mcp-gateway

# 4. Verify authentication works
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer YOUR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "gateway:tool:invoke", "server_name": "test"}'
# Should return 200 OK with authorization decision
```

**Prevention:**
- Use secure API key storage (secrets manager)
- Rotate API keys regularly (quarterly)
- Monitor API key usage and expiration
- Set up alerts for authentication failures

---

#### Symptom: "Request times out / Gateway not responding"

**Network connectivity or Gateway service issues.**

**Diagnosis:**
```bash
# 1. Check if Gateway is running
docker ps | grep mcp-gateway
# Should show: mcp-gateway ... Up X minutes

# 2. Check Gateway health
curl http://localhost:8080/health
# Expected: {"status": "healthy"}

# 3. Test from SARK container (checks internal networking)
docker exec -it sark-app curl http://mcp-gateway:8080/health
# Expected: {"status": "healthy"}

# 4. Check network latency
time curl http://localhost:8080/health
# Should be < 100ms
```

**Root Cause:**
- Gateway service not running
- Network connectivity issues
- Firewall blocking traffic
- Gateway overloaded or crashed

**Solution:**

**If Gateway is not running:**
```bash
# Start Gateway
docker compose -f docker compose.gateway.yml up -d mcp-gateway

# Check logs for startup errors
docker logs mcp-gateway
```

**If Gateway is running but unreachable:**
```bash
# Check Docker network
docker network inspect gateway-integration_default | jq '.[0].Containers'

# Both sark-app and mcp-gateway should be on the same network

# Restart both services if needed
docker compose -f docker compose.gateway.yml restart sark mcp-gateway
```

**If latency is high (> 1 second):**
- See [Performance Tuning Guide](PERFORMANCE_TUNING.md)
- Check Gateway resource usage: `docker stats mcp-gateway`
- Review Gateway logs for slow operations

---

#### Symptom: "All authorization requests are denied"

**This is often a policy configuration issue.**

**Diagnosis:**
```bash
# Test authorization
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_123",
      "email": "test@example.com",
      "roles": ["user"]
    }
  }' | jq

# Output: {"allow": false, "reason": "No matching policy"}
```

**Root Cause:**
- No policies configured in OPA
- Policies don't match request attributes
- Policy evaluation errors
- Default deny rule (secure default)

**Solution:**

**Check OPA policies:**
```bash
# 1. List loaded policies
curl http://localhost:8181/v1/policies | jq

# 2. Test policy directly
curl -X POST http://localhost:8181/v1/data/mcp/gateway/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "user_123", "roles": ["user"]},
      "action": "gateway:tool:invoke",
      "server_name": "postgres-mcp",
      "tool_name": "execute_query"
    }
  }' | jq

# Should return: {"result": true/false}
```

**Add a permissive policy (testing only):**
```bash
# Create test policy
cat > /tmp/test_policy.rego << 'EOF'
package mcp.gateway

# Allow all for testing - REMOVE IN PRODUCTION
allow {
    input.action == "gateway:tool:invoke"
}
EOF

# Upload to OPA
curl -X PUT http://localhost:8181/v1/policies/test_policy \
  -H "Content-Type: text/plain" \
  --data-binary @/tmp/test_policy.rego

# Test again - should now allow
```

**For production, create proper policies:**
```rego
package mcp.gateway

default allow = false

# Allow admins all access
allow {
    input.user.roles[_] == "admin"
    input.action == "gateway:tool:invoke"
}

# Allow analysts to query databases
allow {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name in ["execute_query", "list_tables"]
}
```

**Related:**
- [Policy Configuration](#policy-configuration-issues)
- [OPA Integration](#opa-integration-issues)

---

## Common Error Messages

### Error: "Gateway integration not enabled"

**Full Error:**
```json
{
  "error": "Gateway integration not enabled",
  "message": "This SARK instance does not have Gateway integration enabled. Set GATEWAY_ENABLED=true to enable.",
  "code": "GATEWAY_DISABLED"
}
```

**When It Happens:**
- Accessing `/api/v1/gateway/*` endpoints when feature is disabled
- Gateway trying to authorize requests against SARK v1.0.0

**Why This Happens:**
Gateway integration is an optional feature flag in SARK v1.1.0. The feature must be explicitly enabled.

**Solution:**
```bash
# 1. Enable in environment
export GATEWAY_ENABLED=true

# Or in .env file
echo "GATEWAY_ENABLED=true" >> .env

# 2. Restart SARK
docker compose restart sark

# 3. Verify enabled
curl http://localhost:8000/api/v1/version | jq '.features.gateway_integration'
# Should return: true
```

**Prevention:**
- Document feature requirements in deployment guides
- Add feature verification to health checks
- Use infrastructure-as-code with feature flags set

---

### Error: "Invalid SARK API key"

**Full Error:**
```json
{
  "error": "Invalid API key",
  "message": "The provided SARK API key is invalid or expired",
  "code": "INVALID_API_KEY"
}
```

**When It Happens:**
- Gateway authenticating to SARK
- API key rotation
- First-time setup

**Why This Happens:**
- API key not generated yet
- Wrong key copied to Gateway config
- API key revoked or expired
- Key lacks required permissions

**Solution:**
```bash
# 1. Generate new API key
docker exec -it sark-app python -m sark.cli.generate_api_key \
  --name "MCP Gateway Production" \
  --type gateway \
  --permissions "gateway:*"

# Save the output:
# API Key: sark_gw_abc123def456...

# 2. Update Gateway configuration
# In .env:
SARK_API_KEY=sark_gw_abc123def456...

# 3. Restart Gateway
docker compose restart mcp-gateway

# 4. Test authentication
docker logs mcp-gateway | grep "Authenticated successfully"
```

**Verification:**
```bash
# Test API key manually
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "X-API-Key: sark_gw_abc123def456..." \
  -H "Content-Type: application/json" \
  -d '{"action": "gateway:health:check"}'
# Should return 200 OK
```

---

### Error: "Authorization denied"

**Full Error:**
```json
{
  "allow": false,
  "reason": "Policy evaluation denied request",
  "decision": {
    "allow": false,
    "policy": "mcp.gateway.allow",
    "matched_rules": []
  }
}
```

**When It Happens:**
- User attempting to invoke MCP tool through Gateway
- Insufficient permissions
- Policy mismatch

**Why This Happens:**
This is actually correct behavior - the authorization system is working as designed. The request doesn't match any allow policies.

**Solution:**

**Option 1: Grant user required role**
```bash
# Update user roles
curl -X PATCH http://localhost:8000/api/v1/users/user_123 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["user", "analyst"]}'
```

**Option 2: Update policy to allow action**
```rego
# Add to opa/policies/gateway.rego
allow {
    input.user.id == "user_123"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
}
```

**Option 3: Verify request attributes match policy**
```bash
# Get decision details
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_123",
      "email": "user@example.com",
      "roles": ["user"]
    },
    "debug": true
  }' | jq '.decision'

# Check which policies were evaluated and why they didn't match
```

**Related:**
- [FAQ: Why are my requests denied?](FAQ.md#why-are-my-requests-denied)
- [Policy Examples](../../gateway-integration/policies/)

---

### Error: "Gateway connection failed"

**Full Error:**
```json
{
  "error": "Gateway connection failed",
  "message": "Failed to connect to MCP Gateway at http://mcp-gateway:8080",
  "code": "GATEWAY_CONNECTION_ERROR",
  "details": {
    "url": "http://mcp-gateway:8080/authorize",
    "error": "Connection refused"
  }
}
```

**When It Happens:**
- SARK trying to validate Gateway requests
- Network connectivity issues
- Gateway service down

**Why This Happens:**
- Gateway container not running
- Network misconfiguration
- Firewall blocking traffic
- Wrong Gateway URL in configuration

**Solution:**

**Check Gateway status:**
```bash
# Is Gateway running?
docker ps | grep mcp-gateway
# Should show: mcp-gateway ... Up X minutes (healthy)

# If not running, start it:
docker compose up -d mcp-gateway
```

**Check network connectivity:**
```bash
# From SARK container
docker exec -it sark-app curl http://mcp-gateway:8080/health
# Should return: {"status": "healthy"}

# If fails, check Docker network
docker network inspect gateway-integration_default
```

**Verify Gateway URL:**
```bash
# Check SARK configuration
docker exec -it sark-app env | grep GATEWAY_URL
# Should be: GATEWAY_URL=http://mcp-gateway:8080

# Update if wrong:
echo "GATEWAY_URL=http://mcp-gateway:8080" >> .env
docker compose restart sark
```

---

### Error: "OPA evaluation failed"

**Full Error:**
```json
{
  "error": "Policy evaluation failed",
  "message": "Failed to evaluate policy in OPA",
  "code": "OPA_EVALUATION_ERROR",
  "details": {
    "opa_error": "rego_parse_error: unexpected eof token",
    "policy": "mcp.gateway.allow"
  }
}
```

**When It Happens:**
- Evaluating authorization request
- Policy syntax error
- OPA service issue

**Why This Happens:**
- Syntax error in Rego policy
- OPA service not running
- Policy not loaded into OPA
- OPA connection issue

**Solution:**

**Check OPA health:**
```bash
# Is OPA running?
curl http://localhost:8181/health
# Should return: {"status": "ok"}

# If not running:
docker compose up -d opa
```

**Validate policy syntax:**
```bash
# Test policy file locally
opa check opa/policies/gateway.rego

# Should output: No errors found

# If errors, fix syntax and reload
```

**Reload policies:**
```bash
# Upload policy to OPA
curl -X PUT http://localhost:8181/v1/policies/gateway \
  -H "Content-Type: text/plain" \
  --data-binary @opa/policies/gateway.rego

# Verify loaded
curl http://localhost:8181/v1/policies/gateway
```

**Test policy directly:**
```bash
# Test with sample input
curl -X POST http://localhost:8181/v1/data/mcp/gateway/allow \
  -d '{
    "input": {
      "user": {"roles": ["admin"]},
      "action": "gateway:tool:invoke"
    }
  }' | jq

# Should return: {"result": true/false}
```

---

### Error: "Rate limit exceeded"

**Full Error:**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

**When It Happens:**
- High-volume API usage
- Automated scripts or tests
- DDoS or abuse attempts

**Why This Happens:**
SARK implements rate limiting to prevent abuse and ensure fair resource allocation.

**Solution:**

**Immediate (increase limits):**
```bash
# Check current limits
curl -I http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN"
# Look for: X-RateLimit-Limit, X-RateLimit-Remaining

# Increase user's rate limit (admin only)
curl -X PATCH http://localhost:8000/api/v1/users/user_123 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"rate_limit_per_minute": 10000}'

# Or increase global limits (requires restart)
export RATE_LIMIT_GATEWAY_REQUESTS_PER_MINUTE=10000
docker compose restart sark
```

**Long-term (optimize usage):**
- Implement request batching
- Add client-side caching
- Use exponential backoff for retries
- Review application logic for unnecessary requests

---

### Error: "Server not found"

**Full Error:**
```json
{
  "allow": false,
  "reason": "MCP server not registered",
  "code": "SERVER_NOT_FOUND",
  "server_name": "unknown-server"
}
```

**When It Happens:**
- Requesting authorization for unregistered MCP server
- Typo in server name
- Server deregistered

**Why This Happens:**
SARK validates that the requested MCP server exists in the registry before authorizing access.

**Solution:**

**List registered servers:**
```bash
# Get all servers
curl http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" | jq '.servers[] | .name'

# Search for specific server
curl http://localhost:8000/api/v1/servers?search=postgres \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Register missing server:**
```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "postgres-mcp",
    "endpoint": "http://postgres-mcp:8080",
    "description": "PostgreSQL MCP Server",
    "tags": ["database", "sql"]
  }'
```

**Verify server name in request:**
```bash
# Use exact server name from registry
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "server_name": "postgres-mcp",  # Must match exactly
    "action": "gateway:tool:invoke"
  }'
```

---

### Error: "Invalid request format"

**Full Error:**
```json
{
  "error": "Validation error",
  "message": "Invalid request format",
  "code": "INVALID_REQUEST",
  "details": [
    {
      "field": "user.id",
      "message": "Field required"
    }
  ]
}
```

**When It Happens:**
- Malformed authorization request
- Missing required fields
- Wrong data types

**Why This Happens:**
SARK validates all requests against defined schemas. This error means the request doesn't match the expected format.

**Solution:**

**Check required fields:**
```json
{
  "action": "gateway:tool:invoke",        // Required: action type
  "server_name": "postgres-mcp",          // Required: MCP server name
  "tool_name": "execute_query",           // Required for tool invocation
  "user": {                               // Required: user context
    "id": "user_123",                     // Required: user ID
    "email": "user@example.com",          // Required: user email
    "roles": ["user"]                     // Required: user roles
  },
  "context": {                            // Optional: additional context
    "request_id": "req_abc123"
  }
}
```

**Validate before sending:**
```bash
# Use jq to validate JSON
cat request.json | jq empty
# No output = valid JSON

# Check required fields
jq 'has("action") and has("server_name") and has("user")' request.json
# Should return: true
```

---

### Error: "Database connection failed"

**Full Error:**
```text
ERROR: Database connection failed: could not connect to server: Connection refused
  Is the server running on host "postgres" (172.18.0.2) and accepting
  TCP/IP connections on port 5432?
```

**When It Happens:**
- SARK startup
- Database queries
- Health checks

**Why This Happens:**
- PostgreSQL container not running
- Network configuration issue
- Wrong database credentials
- Database not initialized

**Solution:**

**Check PostgreSQL:**
```bash
# Is PostgreSQL running?
docker ps | grep postgres
# Should show: postgres ... Up X minutes (healthy)

# If not running:
docker compose up -d postgres

# Wait for PostgreSQL to be ready
docker compose logs -f postgres | grep "database system is ready"
```

**Test connection:**
```bash
# From SARK container
docker exec -it sark-app psql -h postgres -U sark -d sark -c "SELECT 1;"
# Should return: 1

# If authentication fails, check credentials
docker exec -it sark-app env | grep -E "DB_HOST|DB_USER|DB_PASSWORD|DB_NAME"
```

**Verify database initialized:**
```bash
# Check if tables exist
docker exec -it postgres psql -U sark -d sark -c "\dt"
# Should list: users, servers, policies, etc.

# If empty, run migrations
docker exec -it sark-app alembic upgrade head
```

---

### Error: "Redis connection failed"

**Full Error:**
```text
ERROR: Redis connection failed: Error 111 connecting to redis:6379. Connection refused.
```

**When It Happens:**
- Cache operations
- Session management
- Rate limiting

**Why This Happens:**
- Redis container not running
- Network issue
- Wrong Redis configuration

**Solution:**

**Check Redis:**
```bash
# Is Redis running?
docker ps | grep redis
# Should show: redis ... Up X minutes (healthy)

# If not running:
docker compose up -d redis

# Test connection
docker exec -it redis redis-cli PING
# Should return: PONG
```

**From SARK container:**
```bash
docker exec -it sark-app env | grep REDIS
# VALKEY_HOST=redis
# VALKEY_PORT=6379
# VALKEY_PASSWORD=...

# Test connection
docker exec -it sark-app curl http://redis:6379
# Or use redis-cli if available
```

**Clear cache if needed:**
```bash
# Flush all cached data (caution: loses all cache)
docker exec -it redis redis-cli FLUSHDB
```

---

### Error: "Tool not found"

**Full Error:**
```json
{
  "allow": false,
  "reason": "Tool not found on server",
  "code": "TOOL_NOT_FOUND",
  "server_name": "postgres-mcp",
  "tool_name": "invalid_tool"
}
```

**When It Happens:**
- Requesting authorization for non-existent tool
- Tool name typo
- Server doesn't support requested tool

**Why This Happens:**
SARK validates that the requested tool exists on the target MCP server.

**Solution:**

**List available tools:**
```bash
# Query Gateway for server tools
curl http://localhost:8080/servers/postgres-mcp/tools \
  -H "Authorization: Bearer $TOKEN" | jq '.tools[] | .name'

# Should list: execute_query, list_tables, describe_table, etc.
```

**Use correct tool name:**
```bash
# Authorize with valid tool name
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query"  # Valid tool name
  }'
```

---

### Additional Error Messages

#### Error: "Token expired"
```json
{"error": "Token expired", "code": "TOKEN_EXPIRED"}
```
**Solution:** Re-authenticate to get a new token
```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email": "user@example.com", "password": "password"}' | jq -r '.access_token')
```

#### Error: "Insufficient permissions"
```json
{"error": "Insufficient permissions", "code": "FORBIDDEN"}
```
**Solution:** Contact admin to grant required permissions

#### Error: "Internal server error"
```json
{"error": "Internal server error", "code": "INTERNAL_ERROR"}
```
**Solution:** Check SARK logs: `docker logs sark-app | tail -50`

---

## Debug Mode and Logging

### Enable Debug Logging

**For SARK:**
```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Or in .env
echo "LOG_LEVEL=DEBUG" >> .env

# Restart SARK
docker compose restart sark

# View debug logs
docker logs -f sark-app
```

**For Gateway:**
```bash
# Enable Gateway debug mode
export GATEWAY_LOG_LEVEL=debug

# Restart Gateway
docker compose restart mcp-gateway

# View debug logs
docker logs -f mcp-gateway
```

**For OPA:**
```bash
# Run OPA with decision logging
docker compose -f docker compose.gateway.yml exec opa opa run \
  --server \
  --addr :8181 \
  --log-level debug \
  --log-format json

# View OPA logs
docker logs -f opa
```

### Log Locations

```bash
# SARK logs
docker logs sark-app > /tmp/sark.log 2>&1

# Gateway logs
docker logs mcp-gateway > /tmp/gateway.log 2>&1

# OPA logs
docker logs opa > /tmp/opa.log 2>&1

# PostgreSQL logs
docker logs postgres > /tmp/postgres.log 2>&1

# Redis logs
docker logs redis > /tmp/redis.log 2>&1
```

### Log Filtering

**Find errors:**
```bash
docker logs sark-app | grep -i error | tail -20
```

**Find warnings:**
```bash
docker logs sark-app | grep -i warn | tail -20
```

**Find authorization decisions:**
```bash
docker logs sark-app | grep "authorization decision" | tail -10
```

**Find slow requests:**
```bash
docker logs sark-app | grep "duration" | awk '$NF > 1000' | tail -10
# Shows requests taking > 1000ms
```

### Structured Logging

SARK uses JSON structured logging in production:

```json
{
  "timestamp": "2025-11-22T10:30:45.123Z",
  "level": "INFO",
  "logger": "sark.gateway.authorize",
  "message": "Authorization request processed",
  "user_id": "user_123",
  "server_name": "postgres-mcp",
  "tool_name": "execute_query",
  "decision": "allow",
  "duration_ms": 45,
  "request_id": "req_abc123"
}
```

**Parse with jq:**
```bash
docker logs sark-app | grep "^{" | jq 'select(.level == "ERROR")'
docker logs sark-app | grep "^{" | jq 'select(.duration_ms > 1000)'
docker logs sark-app | grep "^{" | jq 'select(.decision == "deny")'
```

### Enable Request Tracing

**Add tracing headers:**
```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Request-ID: req-debug-001" \
  -H "X-Trace-Enabled: true" \
  -d '{...}'

# Check logs for trace ID
docker logs sark-app | grep "req-debug-001"
```

**Enable distributed tracing (OpenTelemetry):**
```bash
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318

docker compose restart sark

# View traces in Jaeger UI
open http://localhost:16686
```

---

## Common Misconfigurations

### Missing Environment Variables

**Symptom:** Service fails to start or features don't work

**Check required variables:**
```bash
# Required for Gateway integration
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
SARK_API_KEY=sark_gw_...

# Database
DB_HOST=postgres
DB_PORT=5432
DB_USER=sark
DB_PASSWORD=...
DB_NAME=sark

# Redis
VALKEY_HOST=redis
VALKEY_PORT=6379
VALKEY_PASSWORD=...

# OPA
OPA_URL=http://opa:8181

# Auth
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

**Validate configuration:**
```bash
# Create validation script
cat > validate-config.sh << 'EOF'
#!/bin/bash
REQUIRED_VARS=(
  "GATEWAY_ENABLED"
  "GATEWAY_URL"
  "DB_HOST"
  "VALKEY_HOST"
  "OPA_URL"
  "JWT_SECRET_KEY"
)

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var is not set"
  else
    echo "OK: $var is set"
  fi
done
EOF

chmod +x validate-config.sh
./validate-config.sh
```

### Authentication Configuration Issues

**Wrong JWT algorithm:**
```bash
# Error: Token verification fails
# Check: JWT_ALGORITHM must match what was used to sign tokens

# Default is HS256
export JWT_ALGORITHM=HS256

# If using RS256 (RSA), need public/private keys
export JWT_ALGORITHM=RS256
export JWT_PUBLIC_KEY_PATH=/path/to/public.pem
export JWT_PRIVATE_KEY_PATH=/path/to/private.pem
```

**Token expiration too short:**
```bash
# Users constantly re-authenticating
# Increase expiration time
export JWT_EXPIRATION_MINUTES=120  # 2 hours (default: 60)
```

### Network Configuration Issues

**Services can't communicate:**
```bash
# Symptom: "Connection refused" errors between services

# Check Docker network
docker network ls
docker network inspect gateway-integration_default

# All services should be on same network

# Fix: Update docker compose.yml
networks:
  default:
    name: gateway-integration_default
```

**Wrong service hostnames:**
```bash
# From SARK, use Docker service names, not localhost
GATEWAY_URL=http://mcp-gateway:8080  # Correct
GATEWAY_URL=http://localhost:8080     # Wrong (in Docker)

# From host machine, use localhost
curl http://localhost:8080/health     # Correct
curl http://mcp-gateway:8080/health   # Wrong (from host)
```

### Policy Configuration Issues

**Policy syntax errors:**
```rego
# Common mistakes:

# 1. Missing default rule
package mcp.gateway
allow {  # ERROR: Should have "default allow = false"
    ...
}

# Correct:
package mcp.gateway
default allow = false
allow {
    ...
}

# 2. Wrong package name
package gateway  # ERROR: Should be "mcp.gateway"

# 3. Incorrect field references
allow {
    input.user_id == "user_123"  # ERROR: Field is "user.id"
}

# Correct:
allow {
    input.user.id == "user_123"
}
```

**Policy not loaded:**
```bash
# Check loaded policies
curl http://localhost:8181/v1/policies | jq

# Should list your policies
# If not, upload manually:
curl -X PUT http://localhost:8181/v1/policies/gateway \
  --data-binary @opa/policies/gateway.rego
```

### Database Configuration Issues

**Connection pool exhausted:**
```bash
# Symptom: "connection pool timeout" errors

# Increase pool size
export DB_POOL_SIZE=20  # Default: 10
export DB_MAX_OVERFLOW=30  # Default: 10

docker compose restart sark
```

**Migration not run:**
```bash
# Symptom: "relation does not exist" errors

# Check migration status
docker exec -it sark-app alembic current

# Run pending migrations
docker exec -it sark-app alembic upgrade head
```

---

## Diagnostic Commands

### System Health Diagnostics

```bash
#!/bin/bash
# comprehensive-health-check.sh

echo "=== SARK Gateway Integration Health Check ==="
echo "Date: $(date)"
echo ""

# 1. Service Status
echo "1. Service Status"
echo "=================="
docker ps --filter "name=sark|gateway|opa|postgres|redis" \
  --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 2. SARK Health
echo "2. SARK Health"
echo "=============="
curl -s http://localhost:8000/health/detailed | jq '.'
echo ""

# 3. Gateway Health
echo "3. Gateway Health"
echo "================="
curl -s http://localhost:8080/health | jq '.'
echo ""

# 4. OPA Health
echo "4. OPA Health"
echo "============="
curl -s http://localhost:8181/health | jq '.'
echo ""

# 5. Feature Flags
echo "5. Feature Flags"
echo "================"
curl -s http://localhost:8000/api/v1/version | jq '.features'
echo ""

# 6. Database Connection
echo "6. Database Connection"
echo "======================"
docker exec sark-app psql -h postgres -U sark -d sark -c "SELECT COUNT(*) as tables FROM information_schema.tables WHERE table_schema = 'public';" 2>&1
echo ""

# 7. Redis Connection
echo "7. Redis Connection"
echo "==================="
docker exec redis redis-cli PING
echo ""

# 8. Resource Usage
echo "8. Resource Usage"
echo "================="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
  $(docker ps --filter "name=sark|gateway|opa|postgres|redis" -q)
echo ""

# 9. Recent Errors
echo "9. Recent Errors (last 5 min)"
echo "============================="
docker logs sark-app --since 5m 2>&1 | grep -i error | tail -5
echo ""

# 10. Network Connectivity
echo "10. Network Connectivity"
echo "========================"
docker exec sark-app curl -s -o /dev/null -w "SARK -> Gateway: %{http_code}\n" http://mcp-gateway:8080/health
docker exec sark-app curl -s -o /dev/null -w "SARK -> OPA: %{http_code}\n" http://opa:8181/health
echo ""

echo "=== Health Check Complete ==="
```

### Authorization Flow Diagnostics

```bash
#!/bin/bash
# test-authorization-flow.sh

USER_TOKEN="$1"
if [ -z "$USER_TOKEN" ]; then
  echo "Usage: $0 <user-token>"
  exit 1
fi

echo "=== Authorization Flow Test ==="
echo ""

# Test 1: Simple allow
echo "Test 1: Admin user (should allow)"
curl -s -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "admin_001",
      "email": "admin@example.com",
      "roles": ["admin"]
    }
  }' | jq '.'
echo ""

# Test 2: Regular user
echo "Test 2: Regular user (might deny)"
curl -s -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_001",
      "email": "user@example.com",
      "roles": ["user"]
    }
  }' | jq '.'
echo ""

# Test 3: Invalid server
echo "Test 3: Invalid server (should deny)"
curl -s -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "nonexistent-server",
    "tool_name": "some_tool",
    "user": {
      "id": "user_001",
      "email": "user@example.com",
      "roles": ["user"]
    }
  }' | jq '.'
echo ""

echo "=== Test Complete ==="
```

### Performance Diagnostics

```bash
#!/bin/bash
# performance-diagnostics.sh

echo "=== Performance Diagnostics ==="
echo ""

# Test latency
echo "1. API Latency Test (10 requests)"
echo "=================================="
for i in {1..10}; do
  curl -s -o /dev/null -w "Request $i: %{time_total}s\n" \
    http://localhost:8000/health
done
echo ""

# Database query performance
echo "2. Database Query Performance"
echo "============================="
docker exec postgres psql -U sark -d sark -c "
  SELECT
    query,
    calls,
    mean_exec_time,
    max_exec_time
  FROM pg_stat_statements
  WHERE query LIKE '%gateway%'
  ORDER BY mean_exec_time DESC
  LIMIT 5;
" 2>/dev/null || echo "pg_stat_statements not available"
echo ""

# Redis performance
echo "3. Redis Performance"
echo "===================="
docker exec redis redis-cli INFO stats | grep -E "instantaneous_ops_per_sec|keyspace_hits|keyspace_misses"
echo ""

# Resource usage over time
echo "4. Resource Usage (30 second sample)"
echo "====================================="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
  $(docker ps --filter "name=sark|gateway" -q)
echo ""

echo "=== Diagnostics Complete ==="
```

### Policy Diagnostics

```bash
#!/bin/bash
# policy-diagnostics.sh

echo "=== Policy Diagnostics ==="
echo ""

# List loaded policies
echo "1. Loaded Policies"
echo "=================="
curl -s http://localhost:8181/v1/policies | jq -r '.result[].id'
echo ""

# Get specific policy
echo "2. Gateway Policy Content"
echo "========================="
curl -s http://localhost:8181/v1/policies/gateway | jq -r '.result.raw'
echo ""

# Test policy evaluation
echo "3. Test Policy Evaluation"
echo "========================="
curl -s -X POST http://localhost:8181/v1/data/mcp/gateway/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "test", "roles": ["admin"]},
      "action": "gateway:tool:invoke",
      "server_name": "test-server"
    }
  }' | jq '.'
echo ""

# Policy metrics
echo "4. Policy Metrics"
echo "================="
curl -s http://localhost:8181/metrics | grep opa_policy
echo ""

echo "=== Diagnostics Complete ==="
```

---

## When to File a Bug Report

File a bug report when you encounter:

### Definite Bugs
1. **Crashes or exceptions** in SARK/Gateway code
2. **Data corruption** or inconsistent state
3. **Security vulnerabilities**
4. **Memory leaks** or resource exhaustion
5. **Incorrect authorization decisions** with valid policies

### Possible Bugs
6. **Unexpected behavior** not documented
7. **Performance degradation** without explanation
8. **Error messages** that don't help diagnose the issue
9. **API returning wrong status codes**
10. **Policies not working as documented**

### Bug Report Template

```markdown
## Bug Report

**SARK Version:** 1.1.0
**Deployment:** Docker Compose / Kubernetes / Other
**Environment:** Development / Staging / Production

### Description
[Clear description of the issue]

### Steps to Reproduce
1. [First step]
2. [Second step]
3. [...]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Error Messages
```
[Paste error messages and stack traces]
```

### Logs
```
[Relevant log excerpts]
```

### Configuration
- Gateway Enabled: Yes/No
- A2A Enabled: Yes/No
- OPA Version: X.Y.Z
- PostgreSQL Version: X.Y
- Redis Version: X.Y

### Diagnostic Output
```bash
# Run diagnostics
./comprehensive-health-check.sh > diagnostics.txt
```
[Attach diagnostics.txt]

### Additional Context
[Any other relevant information]
```

### Where to Report

- **GitHub Issues:** https://github.com/your-org/sark/issues
- **Security Issues:** security@example.com (do NOT file public issue)
- **Support:** support@example.com

---

## Advanced Troubleshooting

### Connection Pooling Issues

**Symptom:** "Connection pool timeout" errors

**Diagnosis:**
```bash
# Check active connections
docker exec postgres psql -U sark -c "
  SELECT
    count(*) FILTER (WHERE state = 'active') AS active,
    count(*) FILTER (WHERE state = 'idle') AS idle,
    count(*) AS total
  FROM pg_stat_activity
  WHERE datname = 'sark';
"
```

**Solution:**
```bash
# Increase pool size
export DB_POOL_SIZE=30
export DB_MAX_OVERFLOW=50
export DB_POOL_TIMEOUT=60

# Or kill idle connections
docker exec postgres psql -U sark -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'sark'
    AND state = 'idle'
    AND state_change < NOW() - INTERVAL '30 minutes';
"
```

### Circuit Breaker Triggered

**Symptom:** "Circuit breaker open - too many failures"

**Diagnosis:**
```bash
# Check circuit breaker state in Redis
docker exec redis redis-cli GET "circuit_breaker:gateway:state"
# Output: "open" or "closed"
```

**Solution:**
```bash
# Wait for automatic reset (default: 60 seconds)
# Or manually reset
docker exec redis redis-cli DEL "circuit_breaker:gateway:state"
docker exec redis redis-cli DEL "circuit_breaker:gateway:failures"

# Fix underlying issue causing failures
docker logs sark-app | grep -i "circuit breaker"
```

### Memory Leaks

**Symptom:** Memory usage grows over time

**Diagnosis:**
```bash
# Monitor memory over time
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" sark-app'

# Check for memory leaks in Python
docker exec sark-app python -m memory_profiler /path/to/script.py
```

**Solution:**
```bash
# Restart service (temporary)
docker compose restart sark

# Investigate with profiling (permanent fix)
# Add to code:
from memory_profiler import profile

@profile
def problematic_function():
    ...
```

### Database Lock Contention

**Symptom:** Slow queries, timeouts

**Diagnosis:**
```sql
-- Check locks
docker exec postgres psql -U sark -c "
  SELECT
    locktype,
    relation::regclass,
    mode,
    pid,
    query
  FROM pg_locks
  JOIN pg_stat_activity USING (pid)
  WHERE NOT granted;
"
```

**Solution:**
```sql
-- Kill blocking query
SELECT pg_terminate_backend(<pid>);

-- Or optimize query/add index
CREATE INDEX idx_servers_owner ON servers(owner_id);
```

---

## Summary

This troubleshooting guide covers:

✅ **Quick Start** - 30-second health check and top 5 issues
✅ **Symptom-Based Troubleshooting** - Decision tree and common symptoms
✅ **35+ Common Error Messages** - Full errors with solutions
✅ **Debug Mode & Logging** - Enable debug, log locations, filtering
✅ **Common Misconfigurations** - Environment, auth, network, policies
✅ **Diagnostic Commands** - Health checks, authorization tests, performance
✅ **Bug Reports** - When to file, template, where to report
✅ **Advanced Troubleshooting** - Connection pools, circuit breakers, memory

**Next Steps:**
- Bookmark this guide for quick reference
- Review [FAQ](FAQ.md) for common questions
- Check [Error Reference](ERROR_REFERENCE.md) for complete error catalog
- See [Performance Tuning](PERFORMANCE_TUNING.md) for optimization

**Still having issues?**
- Enable debug logging and collect diagnostics
- Search existing issues: https://github.com/your-org/sark/issues
- Ask in community: https://community.sark.io
- Contact support: support@example.com

---

**Document Version:** 1.0
**Covers:** SARK v1.1.0 Gateway Integration
**Last Updated:** November 2025
