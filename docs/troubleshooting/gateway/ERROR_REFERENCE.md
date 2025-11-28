# SARK Gateway Integration - Error Reference

**Version**: 1.1.0
**Last Updated**: November 2025
**Audience**: Developers, Operations Engineers, Support Teams

---

## Table of Contents

1. [Error Format and Structure](#error-format-and-structure)
2. [HTTP Status Codes](#http-status-codes)
3. [Gateway Integration Errors (GW-xxx)](#gateway-integration-errors)
4. [Authorization Errors (AZ-xxx)](#authorization-errors)
5. [OPA Policy Errors (OPA-xxx)](#opa-policy-errors)
6. [Connection Errors (CN-xxx)](#connection-errors)
7. [Configuration Errors (CF-xxx)](#configuration-errors)
8. [Authentication Errors (AU-xxx)](#authentication-errors)
9. [Rate Limiting Errors (RL-xxx)](#rate-limiting-errors)
10. [Database Errors (DB-xxx)](#database-errors)
11. [Cache Errors (CA-xxx)](#cache-errors)
12. [Error Recovery Procedures](#error-recovery-procedures)

---

## Error Format and Structure

### Standard Error Response

All SARK Gateway errors follow this JSON format:

```json
{
  "error": {
    "code": "GW-001",
    "message": "Gateway integration is not enabled",
    "detail": "The GATEWAY_ENABLED configuration flag is set to false",
    "timestamp": "2025-11-28T10:30:00Z",
    "request_id": "req_abc123def456",
    "documentation_url": "https://docs.example.com/errors/GW-001",
    "suggestions": [
      "Set GATEWAY_ENABLED=true in your .env file",
      "Restart SARK service after configuration change",
      "Verify feature flag with /api/v1/version endpoint"
    ]
  }
}
```

### Error Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | String | Unique error identifier (e.g., "GW-001") |
| `message` | String | Human-readable error summary |
| `detail` | String | Detailed explanation of what went wrong |
| `timestamp` | ISO 8601 | When the error occurred |
| `request_id` | String | Unique request identifier for tracing |
| `documentation_url` | URL | Link to error-specific documentation |
| `suggestions` | Array | Actionable steps to resolve the error |

### Error Code Format

```
[PREFIX]-[NUMBER]

PREFIX:
  GW  = Gateway Integration
  AZ  = Authorization
  OPA = OPA Policy
  CN  = Connection
  CF  = Configuration
  AU  = Authentication
  RL  = Rate Limiting
  DB  = Database
  CA  = Cache

NUMBER: 001-999 (unique within prefix)
```

---

## HTTP Status Codes

### 400 Bad Request

**When it occurs:** Client sent invalid request data

**Common scenarios:**
- Missing required fields
- Invalid JSON format
- Invalid parameter types
- Malformed authorization header

**Example:**
```json
{
  "error": {
    "code": "GW-100",
    "message": "Invalid request format",
    "detail": "Missing required field: 'action'",
    "suggestions": [
      "Include 'action' field in request body",
      "Valid actions: gateway:tool:invoke, gateway:server:list, gateway:tool:discover"
    ]
  }
}
```

---

### 401 Unauthorized

**When it occurs:** Missing or invalid authentication credentials

**Common scenarios:**
- Missing Authorization header
- Expired JWT token
- Invalid API key
- Token signature verification failed

**Example:**
```json
{
  "error": {
    "code": "AU-001",
    "message": "Missing authentication token",
    "detail": "Authorization header is required",
    "suggestions": [
      "Include 'Authorization: Bearer <token>' header",
      "Obtain token from /api/v1/auth/token endpoint"
    ]
  }
}
```

---

### 403 Forbidden

**When it occurs:** Valid authentication but insufficient permissions

**Common scenarios:**
- OPA policy denied request
- User lacks required role
- Tool sensitivity level too high
- Time-based restriction (outside business hours)

**Example:**
```json
{
  "error": {
    "code": "AZ-001",
    "message": "Authorization denied",
    "detail": "User 'user_123' with role 'viewer' is not authorized to invoke tool 'execute_query' (sensitivity: high)",
    "suggestions": [
      "Request admin or developer role assignment",
      "Contact security team to update permissions",
      "Check OPA policy rules for role requirements"
    ]
  }
}
```

---

### 404 Not Found

**When it occurs:** Requested resource doesn't exist

**Common scenarios:**
- Endpoint not found (Gateway integration disabled)
- Server not registered
- Tool not found
- User not found

**Example:**
```json
{
  "error": {
    "code": "GW-404",
    "message": "Server not found",
    "detail": "MCP server 'postgres-mcp' is not registered in Gateway",
    "suggestions": [
      "List available servers with /api/v1/gateway/servers",
      "Verify server name spelling",
      "Check Gateway registration status"
    ]
  }
}
```

---

### 408 Request Timeout

**When it occurs:** Request exceeded configured timeout

**Common scenarios:**
- Gateway not responding
- OPA policy evaluation timeout
- Database query timeout
- Network latency issues

**Example:**
```json
{
  "error": {
    "code": "CN-408",
    "message": "Request timeout",
    "detail": "Gateway did not respond within 10.0 seconds",
    "suggestions": [
      "Check Gateway health: curl http://gateway:8080/health",
      "Increase GATEWAY_TIMEOUT_SECONDS if Gateway is slow",
      "Check network connectivity between SARK and Gateway"
    ]
  }
}
```

---

### 429 Too Many Requests

**When it occurs:** Rate limit exceeded

**Common scenarios:**
- User exceeded per-minute rate limit
- IP address rate limited
- Global rate limit exceeded
- Burst limit exceeded

**Example:**
```json
{
  "error": {
    "code": "RL-001",
    "message": "Rate limit exceeded",
    "detail": "User 'user_123' exceeded 60 requests/minute limit",
    "retry_after": 42,
    "suggestions": [
      "Wait 42 seconds before retrying",
      "Implement exponential backoff in client",
      "Request rate limit increase if needed"
    ]
  }
}
```

---

### 500 Internal Server Error

**When it occurs:** Unexpected server error

**Common scenarios:**
- Unhandled exception
- Database connection failed
- Redis connection failed
- OPA service unavailable

**Example:**
```json
{
  "error": {
    "code": "DB-500",
    "message": "Internal server error",
    "detail": "Failed to connect to PostgreSQL database",
    "request_id": "req_abc123",
    "suggestions": [
      "Check database health: docker logs postgres",
      "Verify DATABASE_URL configuration",
      "Contact support with request_id if issue persists"
    ]
  }
}
```

---

### 502 Bad Gateway

**When it occurs:** Upstream service (Gateway) returned invalid response

**Common scenarios:**
- Gateway returned non-JSON response
- Gateway returned 500 error
- Gateway service crashed
- Proxy configuration error

**Example:**
```json
{
  "error": {
    "code": "CN-502",
    "message": "Bad gateway response",
    "detail": "Gateway returned invalid JSON response",
    "suggestions": [
      "Check Gateway logs for errors",
      "Verify Gateway is running: docker ps | grep gateway",
      "Test Gateway directly: curl http://gateway:8080/health"
    ]
  }
}
```

---

### 503 Service Unavailable

**When it occurs:** Service is temporarily unavailable

**Common scenarios:**
- SARK is starting up
- OPA is not ready
- Database connection pool exhausted
- Maintenance mode enabled

**Example:**
```json
{
  "error": {
    "code": "GW-503",
    "message": "Service unavailable",
    "detail": "SARK is starting up, please retry in a few seconds",
    "retry_after": 10,
    "suggestions": [
      "Wait 10 seconds and retry request",
      "Check service health: curl http://localhost:8000/health"
    ]
  }
}
```

---

### 504 Gateway Timeout

**When it occurs:** Upstream service (Gateway) timed out

**Common scenarios:**
- Gateway processing took too long
- MCP server not responding
- Network issues between Gateway and MCP server

**Example:**
```json
{
  "error": {
    "code": "CN-504",
    "message": "Gateway timeout",
    "detail": "Gateway did not respond within timeout period",
    "suggestions": [
      "Increase GATEWAY_TIMEOUT_SECONDS if Gateway operations are slow",
      "Check Gateway performance metrics",
      "Verify MCP server health"
    ]
  }
}
```

---

## Gateway Integration Errors

### GW-001: Gateway Integration Not Enabled

**Error Message:**
```json
{
  "error": {
    "code": "GW-001",
    "message": "Gateway integration is not enabled",
    "detail": "The GATEWAY_ENABLED configuration flag is set to false"
  }
}
```

**Root Cause:**
- `GATEWAY_ENABLED` environment variable is `false` or not set
- Configuration not loaded properly
- Service not restarted after configuration change

**Resolution:**

1. **Enable Gateway integration:**
```bash
# Add to .env file
echo "GATEWAY_ENABLED=true" >> .env
```

2. **Restart SARK:**
```bash
docker compose -f docker-compose.gateway.yml restart sark
```

3. **Verify:**
```bash
curl http://localhost:8000/api/v1/version | jq '.features.gateway_integration'
# Expected: true
```

**Prevention:**
- Include feature verification in deployment checklist
- Monitor feature flags in production
- Use infrastructure-as-code for consistent configuration

**Related Errors:** CF-001, GW-002

---

### GW-002: Gateway URL Not Configured

**Error Message:**
```json
{
  "error": {
    "code": "GW-002",
    "message": "Gateway URL not configured",
    "detail": "GATEWAY_URL environment variable is missing or empty"
  }
}
```

**Root Cause:**
- Missing `GATEWAY_URL` in configuration
- Invalid URL format
- URL points to non-existent service

**Resolution:**

```bash
# Set Gateway URL
export GATEWAY_URL=http://gateway:8080

# Or in .env file
echo "GATEWAY_URL=http://gateway:8080" >> .env

# Restart SARK
docker compose restart sark
```

**Validation:**
```bash
# Test Gateway connectivity
curl $GATEWAY_URL/health
```

**Prevention:**
- Use configuration validation on startup
- Include all required variables in .env.example

**Related Errors:** CF-002, CN-001

---

### GW-003: Invalid Gateway Response

**Error Message:**
```json
{
  "error": {
    "code": "GW-003",
    "message": "Invalid response from Gateway",
    "detail": "Expected JSON response but received text/html"
  }
}
```

**Root Cause:**
- Gateway returned error page instead of JSON
- Gateway API endpoint changed
- Proxy or load balancer returning HTML error

**Resolution:**

1. **Check Gateway response:**
```bash
curl -v http://gateway:8080/api/servers

# Look for Content-Type header
# Expected: application/json
```

2. **Verify API compatibility:**
```bash
curl http://gateway:8080/api/version
# Check Gateway API version
```

3. **Check for proxy issues:**
```bash
# Test direct connection without proxy
curl --noproxy '*' http://gateway:8080/api/servers
```

**Prevention:**
- Use API versioning
- Implement response validation
- Monitor content-type metrics

**Related Errors:** GW-004, CN-502

---

### GW-100: Invalid Request Format

**Error Message:**
```json
{
  "error": {
    "code": "GW-100",
    "message": "Invalid request format",
    "detail": "Missing required field: 'action'"
  }
}
```

**Root Cause:**
- Missing required fields in request body
- Invalid JSON syntax
- Incorrect field types

**Resolution:**

**Correct request format:**
```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "parameters": {}
  }'
```

**Required fields:**
- `action` (string): One of `gateway:tool:invoke`, `gateway:server:list`, etc.
- `server_name` (string): For tool invocation actions
- `tool_name` (string): For tool invocation actions

**Prevention:**
- Use request validation libraries
- Implement JSON schema validation
- Provide clear API documentation

**Related Errors:** GW-101, GW-102

---

### GW-404: Server Not Found

**Error Message:**
```json
{
  "error": {
    "code": "GW-404",
    "message": "Server not found",
    "detail": "MCP server 'postgres-mcp' is not registered in Gateway"
  }
}
```

**Root Cause:**
- Server not registered in Gateway
- Server name misspelled
- Server was unregistered

**Resolution:**

1. **List available servers:**
```bash
curl http://localhost:8000/api/v1/gateway/servers \
  -H "Authorization: Bearer ${TOKEN}"
```

2. **Check Gateway registration:**
```bash
curl http://gateway:8080/api/servers | jq '.[] | .name'
```

3. **Register server if missing:**
```bash
# Via Gateway API
curl -X POST http://gateway:8080/api/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "postgres-mcp",
    "url": "http://postgres-mcp:3000",
    "transport": "http"
  }'
```

**Prevention:**
- Validate server names before requests
- Implement server registration monitoring
- Use autocomplete for server names in UI

**Related Errors:** GW-405, GW-406

---

### GW-405: Tool Not Found

**Error Message:**
```json
{
  "error": {
    "code": "GW-405",
    "message": "Tool not found",
    "detail": "Tool 'execute_query' not found on server 'postgres-mcp'"
  }
}
```

**Root Cause:**
- Tool not available on specified server
- Tool name misspelled
- Server capabilities changed

**Resolution:**

1. **List available tools:**
```bash
curl http://localhost:8000/api/v1/gateway/tools?server=postgres-mcp \
  -H "Authorization: Bearer ${TOKEN}" \
  | jq '.[] | .name'
```

2. **Check tool availability:**
```bash
curl http://gateway:8080/api/servers/postgres-mcp/tools
```

3. **Verify tool name spelling:**
```bash
# Common mistakes:
# execute_query vs executeQuery
# read_file vs readFile
```

**Prevention:**
- Use tool discovery API before invocation
- Implement tool name validation
- Cache tool lists with periodic refresh

**Related Errors:** GW-404, GW-406

---

## Authorization Errors

### AZ-001: Authorization Denied

**Error Message:**
```json
{
  "error": {
    "code": "AZ-001",
    "message": "Authorization denied",
    "detail": "User 'user_123' with role 'viewer' is not authorized to invoke tool 'execute_query' (sensitivity: high)",
    "policy_reason": "Tool sensitivity level 'high' requires role 'admin' or 'developer'"
  }
}
```

**Root Cause:**
- OPA policy denied request
- User lacks required role
- Tool sensitivity too high for user's permission level
- Time-based restrictions (outside allowed hours)

**Resolution:**

1. **Check user roles:**
```bash
curl http://localhost:8000/api/v1/users/user_123 \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  | jq '.role, .teams'
```

2. **Review OPA policy:**
```bash
# Check what the policy evaluated
curl http://localhost:8000/api/v1/audit/events?user_id=user_123&decision=deny \
  | jq '.events[0].metadata.policy_reason'
```

3. **Grant required permissions:**
```bash
# Option A: Update user role
curl -X PATCH http://localhost:8000/api/v1/users/user_123 \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"role": "developer"}'

# Option B: Add to authorized team
curl -X POST http://localhost:8000/api/v1/teams/developers/members \
  -d '{"user_id": "user_123"}'
```

4. **Or update policy (if appropriate):**
```rego
# opa/policies/custom.rego
allow if {
    input.user.id == "user_123"
    input.tool.name == "execute_query"
    # Add specific exception
}
```

**Prevention:**
- Implement self-service permission requests
- Document tool sensitivity levels
- Provide clear error messages with next steps

**Related Errors:** AZ-002, AZ-003

---

### AZ-002: Insufficient Permissions

**Error Message:**
```json
{
  "error": {
    "code": "AZ-002",
    "message": "Insufficient permissions",
    "detail": "Action 'gateway:tool:invoke' requires one of: admin, developer",
    "user_role": "viewer"
  }
}
```

**Root Cause:**
- User's role doesn't have permission for requested action
- Role hierarchy not configured properly
- Missing team membership

**Resolution:**

See [AZ-001](#az-001-authorization-denied) for similar resolution steps.

**Key difference:** This error is specifically about role-based access, while AZ-001 can be triggered by various policy rules.

**Related Errors:** AZ-001, AU-003

---

### AZ-003: Parameter Filtering Applied

**Note:** This is not an error but a warning/info message.

**Response Message:**
```json
{
  "allow": true,
  "warning": {
    "code": "AZ-003",
    "message": "Sensitive parameters filtered",
    "detail": "Parameters 'password', 'api_key' were removed from request",
    "filtered_count": 2
  },
  "filtered_parameters": {
    "host": "db.example.com",
    "database": "prod"
  }
}
```

**Root Cause:**
- OPA policy filtered sensitive parameters
- Request contained fields marked as sensitive
- Security policy enforcement

**Resolution:**

**This is expected behavior.** Gateway should use `filtered_parameters` instead of original parameters.

**To prevent filtering:**
- Don't include sensitive data in tool parameters
- Use secure credential storage (Vault, AWS Secrets Manager)
- Pass credential references instead of actual values

**Example secure approach:**
```json
{
  "tool": "db_connect",
  "parameters": {
    "host": "db.example.com",
    "credential_ref": "vault://prod/db/readonly"
  }
}
```

**Related Errors:** AZ-001

---

### AZ-010: Time-Based Restriction

**Error Message:**
```json
{
  "error": {
    "code": "AZ-010",
    "message": "Access denied: outside allowed time window",
    "detail": "Critical operations are only allowed during business hours (9 AM - 5 PM UTC, Monday-Friday)",
    "current_time": "2025-11-28T22:30:00Z",
    "current_day": "Thursday"
  }
}
```

**Root Cause:**
- Request made outside allowed time window
- Critical operation attempted after hours
- Time-based policy restriction

**Resolution:**

1. **Check current time:**
```bash
date -u
# Verify current UTC time
```

2. **Wait for allowed time window:**
```bash
# Business hours: 9 AM - 5 PM UTC, Mon-Fri
# Schedule operation during this window
```

3. **Request emergency override (if critical):**
```bash
# Contact security team for temporary override
# Provide justification and approval
```

4. **Update policy (if policy is incorrect):**
```rego
# opa/policies/time_restrictions.rego
is_business_hours(timestamp) if {
    hour := time.clock([timestamp, "UTC"])[0]
    # Update allowed hours if needed
    hour >= 8  # Changed from 9
    hour < 18  # Changed from 17
}
```

**Prevention:**
- Schedule critical operations during allowed hours
- Implement automated scheduling
- Configure alerts for time-based restrictions

**Related Errors:** AZ-011

---

## OPA Policy Errors

### OPA-001: OPA Service Unavailable

**Error Message:**
```json
{
  "error": {
    "code": "OPA-001",
    "message": "OPA policy service unavailable",
    "detail": "Failed to connect to OPA at http://opa:8181",
    "suggestions": [
      "Check OPA service: docker ps | grep opa",
      "Check OPA logs: docker logs opa",
      "Verify OPA_URL configuration"
    ]
  }
}
```

**Root Cause:**
- OPA container not running
- OPA crashed or restarting
- Network connectivity issues
- Incorrect OPA URL configuration

**Resolution:**

1. **Check OPA status:**
```bash
docker ps | grep opa
# Should show: Up (healthy)
```

2. **Check OPA logs:**
```bash
docker logs opa --tail=50

# Look for errors:
# - Port binding failures
# - Policy compilation errors
# - Memory issues
```

3. **Restart OPA:**
```bash
docker compose restart opa

# Wait for health check
sleep 10

# Verify health
curl http://localhost:8181/health
```

4. **Check connectivity:**
```bash
# From SARK container
docker exec sark-app curl http://opa:8181/health
```

**Prevention:**
- Monitor OPA health with alerts
- Use health checks in docker-compose
- Implement automatic restart policies
- Load test OPA before production deployment

**Related Errors:** OPA-002, CN-001

---

### OPA-002: Policy Evaluation Failed

**Error Message:**
```json
{
  "error": {
    "code": "OPA-002",
    "message": "Policy evaluation failed",
    "detail": "OPA returned error: rego_type_error: undefined ref: data.users",
    "policy_path": "data.mcp.gateway.allow"
  }
}
```

**Root Cause:**
- Policy syntax error
- Undefined reference in policy
- Missing policy data
- Policy compilation error

**Resolution:**

1. **Test policy syntax:**
```bash
# Validate policy file
opa check opa/policies/gateway_authorization.rego

# Expected: No errors
```

2. **Check for undefined references:**
```bash
# Review error details
# "undefined ref: data.users" means:
# - data.users is referenced but not defined
# - Either add data or fix reference
```

3. **Test policy evaluation:**
```bash
opa eval --data opa/policies/ \
  --input test_input.json \
  'data.mcp.gateway.allow' \
  --explain full
```

4. **Fix policy:**
```rego
# Before (broken):
allow if {
    input.user.id in data.users  # data.users not defined
}

# After (fixed):
allow if {
    input.user.id == "user_123"  # Direct comparison
}

# Or provide data:
{
  "users": ["user_123", "user_456"]
}
```

**Prevention:**
- Use OPA testing framework
- Run `opa check` in CI/CD
- Implement policy validation before deployment
- Use typed policy development

**Related Errors:** OPA-003, OPA-004

---

### OPA-003: Policy Timeout

**Error Message:**
```json
{
  "error": {
    "code": "OPA-003",
    "message": "Policy evaluation timeout",
    "detail": "OPA evaluation exceeded 5000ms timeout",
    "policy_complexity": "high"
  }
}
```

**Root Cause:**
- Policy too complex (deep recursion, many loops)
- Large data sets in policy evaluation
- External data lookup delays
- OPA performance issues

**Resolution:**

1. **Profile policy performance:**
```bash
opa eval --profile --data opa/policies/ \
  --input request.json \
  'data.mcp.gateway.allow'

# Look for slow operations:
# - eval_builtin_*: Built-in function calls
# - eval_rule: Rule evaluation time
```

2. **Optimize policy:**
```rego
# Before (slow - loops all users):
allow if {
    some user in data.users
    user.id == input.user.id
    user.role == "admin"
}

# After (fast - direct lookup):
allow if {
    user := data.users[input.user.id]
    user.role == "admin"
}
```

3. **Increase timeout (temporary):**
```bash
OPA_TIMEOUT_MS=10000  # Increase from 5000ms to 10000ms
```

4. **Cache external data:**
```rego
# Instead of calling external API in policy,
# cache data in OPA's data store
```

**Prevention:**
- Profile policies before production
- Set complexity limits
- Cache frequently accessed data
- Monitor policy evaluation time

**Related Errors:** OPA-002

---

### OPA-004: Policy Compilation Error

**Error Message:**
```json
{
  "error": {
    "code": "OPA-004",
    "message": "Policy compilation error",
    "detail": "rego_parse_error: unexpected '}' at line 25",
    "file": "gateway_authorization.rego",
    "line": 25
  }
}
```

**Root Cause:**
- Syntax error in Rego policy
- Mismatched braces or brackets
- Invalid Rego keywords
- Policy file not valid Rego

**Resolution:**

1. **Check syntax at reported line:**
```bash
# View policy around error line
sed -n '20,30p' opa/policies/gateway_authorization.rego
```

2. **Validate with OPA:**
```bash
opa check opa/policies/gateway_authorization.rego

# Output shows exact error location
```

3. **Common syntax errors:**
```rego
# Missing closing brace
allow if {
    input.user.role == "admin"
# Missing }

# Extra closing brace
allow if {
    input.user.role == "admin"
}}  # Extra }

# Invalid assignment
allow if {
    role = input.user.role  # Should use := for assignment
}

# Fixed:
allow if {
    role := input.user.role
    role == "admin"
}
```

4. **Use Rego formatter:**
```bash
opa fmt -w opa/policies/gateway_authorization.rego
```

**Prevention:**
- Use Rego formatter in development
- Enable Rego linting in IDE
- Run `opa check` in pre-commit hooks
- Use OPA testing framework

**Related Errors:** OPA-002

---

## Connection Errors

### CN-001: Gateway Connection Failed

**Error Message:**
```json
{
  "error": {
    "code": "CN-001",
    "message": "Failed to connect to Gateway",
    "detail": "Connection refused to http://gateway:8080",
    "timeout_ms": 10000
  }
}
```

**Root Cause:**
- Gateway service not running
- Network connectivity issues
- Firewall blocking connection
- Incorrect Gateway URL

**Resolution:**

See [TROUBLESHOOTING_GUIDE.md - Gateway Connection Failed](./TROUBLESHOOTING_GUIDE.md#error-gateway-connection-failed) for detailed resolution steps.

**Quick diagnosis:**
```bash
# 1. Check if Gateway is running
docker ps | grep gateway

# 2. Test connectivity
curl http://gateway:8080/health

# 3. Check from SARK container
docker exec sark-app curl http://gateway:8080/health

# 4. Check network
docker network inspect sark_default | jq '.[].Containers'
```

**Related Errors:** CN-002, CN-408

---

### CN-002: Network Timeout

**Error Message:**
```json
{
  "error": {
    "code": "CN-002",
    "message": "Network timeout",
    "detail": "Request to Gateway timed out after 10000ms",
    "gateway_url": "http://gateway:8080"
  }
}
```

**Root Cause:**
- High network latency
- Gateway processing slowly
- Network congestion
- Timeout value too low

**Resolution:**

1. **Measure network latency:**
```bash
# Ping Gateway
docker exec sark-app ping -c 5 gateway

# Measure HTTP latency
curl -w "time_total: %{time_total}s\n" \
  http://gateway:8080/health
```

2. **Check Gateway performance:**
```bash
# Check Gateway CPU/memory
docker stats gateway

# Check Gateway logs for slow operations
docker logs gateway --tail=100 | grep -E "slow|timeout"
```

3. **Increase timeout (if appropriate):**
```bash
# Increase from 10s to 30s
GATEWAY_TIMEOUT_SECONDS=30
```

4. **Optimize Gateway:**
```bash
# Scale Gateway horizontally
docker compose up -d --scale gateway=3
```

**Prevention:**
- Monitor network latency
- Set appropriate timeout values
- Use connection pooling
- Implement retry logic with exponential backoff

**Related Errors:** CN-001, CN-408

---

### CN-408: Request Timeout

**Error Message:**
```json
{
  "error": {
    "code": "CN-408",
    "message": "Request timeout",
    "detail": "Gateway authorization request exceeded 10.0 second timeout",
    "duration_ms": 10543
  }
}
```

**Root Cause:**
- OPA policy evaluation slow
- Database query slow
- Redis connection slow
- Gateway processing slow

**Resolution:**

1. **Check component latency:**
```bash
curl http://localhost:8000/health/detailed | jq '.dependencies'

# Output shows latency for each component:
# {
#   "postgresql": {"healthy": true, "latency_ms": 12.5},
#   "redis": {"healthy": true, "latency_ms": 3.2},
#   "opa": {"healthy": true, "latency_ms": 8.7},
#   "gateway": {"healthy": true, "latency_ms": 145.3}  # SLOW!
# }
```

2. **Identify slow component:**
- PostgreSQL >100ms: Check database performance
- Redis >50ms: Check Redis memory/CPU
- OPA >200ms: Optimize policies
- Gateway >1000ms: Check Gateway health

3. **Optimize slow component:**
```bash
# Example: Optimize OPA
opa eval --profile --data policies/ \
  'data.mcp.gateway.allow' \
  --input request.json
```

**Prevention:**
- Set latency SLOs
- Monitor component performance
- Implement circuit breakers
- Use caching aggressively

**Related Errors:** CN-002, OPA-003

---

## Configuration Errors

### CF-001: Missing Environment Variable

**Error Message:**
```json
{
  "error": {
    "code": "CF-001",
    "message": "Missing required configuration",
    "detail": "Environment variable 'GATEWAY_URL' is required but not set",
    "required_vars": ["GATEWAY_ENABLED", "GATEWAY_URL", "GATEWAY_API_KEY"]
  }
}
```

**Root Cause:**
- Required environment variable not set
- .env file not loaded
- Configuration file missing
- Typo in variable name

**Resolution:**

1. **Check current environment:**
```bash
docker exec sark-app env | grep GATEWAY
```

2. **Add missing variables:**
```bash
# Add to .env file
cat >> .env <<EOF
GATEWAY_ENABLED=true
GATEWAY_URL=http://gateway:8080
GATEWAY_API_KEY=your-api-key
EOF
```

3. **Restart service:**
```bash
docker compose restart sark
```

4. **Verify configuration:**
```bash
curl http://localhost:8000/api/v1/version | jq '.features'
```

**Prevention:**
- Use .env.example template
- Validate configuration on startup
- Use configuration management tools
- Document all required variables

**Related Errors:** CF-002, GW-001

---

## Authentication Errors

### AU-001: Missing Authentication Token

**Error Message:**
```json
{
  "error": {
    "code": "AU-001",
    "message": "Missing authentication token",
    "detail": "Authorization header is required"
  }
}
```

**Resolution:**
```bash
# Include Authorization header
curl -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8000/api/v1/gateway/authorize
```

**Related Errors:** AU-002, AU-003

---

### AU-002: Invalid Token

**Error Message:**
```json
{
  "error": {
    "code": "AU-002",
    "message": "Invalid authentication token",
    "detail": "JWT signature verification failed"
  }
}
```

**Root Cause:**
- Token signature invalid
- Token signed with wrong key
- Token tampered with

**Resolution:**
```bash
# Get fresh token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d '{"username": "user", "password": "pass"}'
```

**Related Errors:** AU-003

---

### AU-003: Token Expired

**Error Message:**
```json
{
  "error": {
    "code": "AU-003",
    "message": "Authentication token expired",
    "detail": "Token expired at 2025-11-28T10:00:00Z",
    "expired_at": "2025-11-28T10:00:00Z"
  }
}
```

**Resolution:**
```bash
# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer ${REFRESH_TOKEN}"
```

**Related Errors:** AU-002

---

## Rate Limiting Errors

### RL-001: Rate Limit Exceeded

**Error Message:**
```json
{
  "error": {
    "code": "RL-001",
    "message": "Rate limit exceeded",
    "detail": "User 'user_123' exceeded 60 requests/minute limit",
    "limit": 60,
    "window": "1m",
    "retry_after": 42
  }
}
```

**Root Cause:**
- Too many requests in time window
- Burst limit exceeded
- IP-based rate limit triggered

**Resolution:**

1. **Wait for reset:**
```bash
# Wait for retry_after seconds
sleep 42
```

2. **Implement backoff:**
```python
import time
import requests

def call_with_backoff(url, max_retries=3):
    for i in range(max_retries):
        response = requests.post(url)
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
        return response
    raise Exception("Max retries exceeded")
```

3. **Request limit increase:**
```bash
# Contact admin to increase rate limit
# Provide justification for higher limit
```

**Prevention:**
- Implement client-side rate limiting
- Use exponential backoff
- Cache responses when possible
- Batch requests

**Related Errors:** RL-002

---

## Database Errors

### DB-001: Database Connection Failed

**Error Message:**
```json
{
  "error": {
    "code": "DB-001",
    "message": "Database connection failed",
    "detail": "Could not connect to PostgreSQL at postgresql://postgres:5432/sark"
  }
}
```

**Resolution:**
See [TROUBLESHOOTING_GUIDE.md - Database Issues](./TROUBLESHOOTING_GUIDE.md#database-issues) for detailed steps.

**Related Errors:** DB-002, DB-003

---

## Cache Errors

### CA-001: Redis Connection Failed

**Error Message:**
```json
{
  "error": {
    "code": "CA-001",
    "message": "Cache connection failed",
    "detail": "Could not connect to Redis at redis://localhost:6379"
  }
}
```

**Resolution:**
```bash
# Check Redis status
docker ps | grep redis

# Test connection
redis-cli ping

# Restart if needed
docker compose restart redis
```

**Related Errors:** CA-002

---

## Error Recovery Procedures

### Automatic Recovery

**Circuit Breaker:**
- Opens after 5 consecutive failures
- Half-open state after 30 seconds
- Automatic retry with exponential backoff

**Retry Logic:**
```python
# Automatic retry for transient errors
retry_codes = [408, 429, 500, 502, 503, 504]

# Exponential backoff: 1s, 2s, 4s, 8s, 16s
backoff = [2**i for i in range(5)]
```

### Manual Recovery

**Database Issues:**
```bash
# Restart database
docker compose restart postgres

# Clear connection pool
curl -X POST http://localhost:8000/api/v1/admin/pool/reset
```

**Cache Issues:**
```bash
# Clear cache
curl -X POST http://localhost:8000/api/v1/cache/clear

# Restart Redis
docker compose restart redis
```

**Policy Issues:**
```bash
# Reload policies
curl -X POST http://localhost:8181/v1/policies \
  --data-binary @opa/policies/gateway_authorization.rego

# Clear policy cache
curl -X POST http://localhost:8000/api/v1/cache/invalidate
```

---

## Getting Help

**Documentation:**
- [Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md)
- [FAQ](./FAQ.md)
- [Performance Tuning](./PERFORMANCE_TUNING.md)

**Support:**
- GitHub Issues: https://github.com/your-org/sark/issues
- Email: support@example.com
- Slack: #sark-support

**When reporting errors:**
1. Include error code and full message
2. Provide request_id for tracing
3. Attach relevant logs
4. Include configuration (sanitized)
5. Describe steps to reproduce

---

**Last Updated**: November 2025 | **Version**: 1.1.0
