# How to Register an MCP Server

This guide walks you through registering an MCP server with the SARK Gateway, enabling clients to discover and invoke your server's tools.

## Before You Begin

**Prerequisites:**
- SARK Gateway installed and running (see installation guide)
- MCP server implementation ready with at least one tool
- Server endpoint URL accessible from the gateway
- Authentication credentials (API key or JWT token)
- `curl` or `sark-cli` tool installed

**What You'll Learn:**
- Register a server using three different methods
- Verify successful registration
- Update server metadata
- Troubleshoot common registration errors
- Properly deregister servers

## Understanding Server Registration

When you register an MCP server, you're telling the gateway:
- **Where** the server is located (endpoint URL)
- **What** tools it provides (capabilities)
- **Who** can access it (authentication requirements)
- **How** to communicate with it (protocol version)

## Method 1: Register via REST API

### Step 1: Prepare the Registration Payload

Create a file named `server-registration.json`:

```json
{
  "server_id": "my-data-processor",
  "name": "Data Processing Server",
  "description": "Provides data transformation and analysis tools",
  "endpoint": "https://api.example.com/mcp",
  "version": "1.0.0",
  "protocol_version": "2024-11-05",
  "capabilities": {
    "tools": true,
    "resources": false,
    "prompts": false
  },
  "metadata": {
    "team": "data-platform",
    "environment": "production",
    "contact": "data-team@example.com"
  },
  "authentication": {
    "type": "bearer",
    "token_env_var": "MCP_SERVER_TOKEN"
  },
  "health_check": {
    "enabled": true,
    "interval": "30s",
    "timeout": "5s",
    "endpoint": "/health"
  },
  "rate_limits": {
    "requests_per_minute": 100,
    "concurrent_requests": 10
  }
}
```

**Expected Result:** A valid JSON configuration file.

### Step 2: Submit Registration Request

```bash
curl -X POST https://gateway.example.com/api/v1/servers \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @server-registration.json
```

**Expected Response:**

```json
{
  "status": "success",
  "server_id": "my-data-processor",
  "registered_at": "2024-01-15T10:30:00Z",
  "health_status": "healthy",
  "discovery_url": "https://gateway.example.com/api/v1/servers/my-data-processor"
}
```

**What This Means:** Your server is now registered and discoverable through the gateway.

### Step 3: Verify Registration

```bash
curl https://gateway.example.com/api/v1/servers/my-data-processor \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}"
```

**Expected Response:**

```json
{
  "server_id": "my-data-processor",
  "name": "Data Processing Server",
  "status": "active",
  "health": {
    "status": "healthy",
    "last_check": "2024-01-15T10:31:00Z",
    "response_time_ms": 45
  },
  "tools": [
    {
      "name": "transform_data",
      "description": "Transform data using specified rules"
    },
    {
      "name": "analyze_dataset",
      "description": "Perform statistical analysis on datasets"
    }
  ]
}
```

**What This Means:** Registration is active and the gateway can reach your server.

## Method 2: Register via CLI

### Step 1: Install SARK CLI

```bash
# Using npm
npm install -g @sark/cli

# Using pip
pip install sark-cli

# Verify installation
sark-cli --version
```

**Expected Output:**
```
SARK CLI v1.5.0
```

### Step 2: Configure CLI Authentication

```bash
sark-cli config set gateway-url https://gateway.example.com
sark-cli config set api-key ${GATEWAY_API_KEY}
```

**Expected Output:**
```
✓ Gateway URL configured
✓ API key configured
Configuration saved to ~/.sark/config.yaml
```

### Step 3: Register Server Using CLI

```bash
sark-cli server register \
  --server-id my-data-processor \
  --name "Data Processing Server" \
  --endpoint https://api.example.com/mcp \
  --version 1.0.0 \
  --capability tools \
  --metadata team=data-platform \
  --metadata environment=production \
  --auth-type bearer \
  --health-check
```

**Expected Output:**
```
Registering server 'my-data-processor'...
✓ Server configuration validated
✓ Endpoint connectivity verified
✓ Health check passed
✓ Server registered successfully

Server ID: my-data-processor
Status: active
Discovery URL: https://gateway.example.com/api/v1/servers/my-data-processor
Tools discovered: 2
```

### Step 4: List Registered Servers

```bash
sark-cli server list
```

**Expected Output:**
```
┌────────────────────┬─────────────────────────┬──────────┬──────────┬───────┐
│ Server ID          │ Name                    │ Version  │ Status   │ Tools │
├────────────────────┼─────────────────────────┼──────────┼──────────┼───────┤
│ my-data-processor  │ Data Processing Server  │ 1.0.0    │ active   │ 2     │
│ weather-api        │ Weather API Server      │ 2.1.0    │ active   │ 5     │
│ auth-service       │ Authentication Service  │ 1.3.2    │ degraded │ 3     │
└────────────────────┴─────────────────────────┴──────────┴──────────┴───────┘
```

## Method 3: Register via Configuration File

### Step 1: Create Gateway Configuration

Edit `/etc/sark/gateway/servers.yaml`:

```yaml
servers:
  - server_id: my-data-processor
    name: Data Processing Server
    description: Provides data transformation and analysis tools
    endpoint: https://api.example.com/mcp
    version: 1.0.0
    protocol_version: 2024-11-05

    capabilities:
      tools: true
      resources: false
      prompts: false

    metadata:
      team: data-platform
      environment: production
      contact: data-team@example.com
      tags:
        - data
        - analytics
        - production

    authentication:
      type: bearer
      token_env_var: MCP_SERVER_TOKEN

    health_check:
      enabled: true
      interval: 30s
      timeout: 5s
      endpoint: /health
      unhealthy_threshold: 3
      healthy_threshold: 2

    rate_limits:
      requests_per_minute: 100
      concurrent_requests: 10
      burst_size: 20

    retry_policy:
      max_attempts: 3
      backoff_multiplier: 2
      initial_interval: 1s
      max_interval: 30s

    circuit_breaker:
      enabled: true
      failure_threshold: 5
      timeout: 60s
      half_open_requests: 3

  - server_id: weather-api
    name: Weather API Server
    endpoint: https://weather.internal.example.com/mcp
    version: 2.1.0
    capabilities:
      tools: true
    authentication:
      type: mtls
      cert_path: /etc/sark/certs/weather-api.crt
      key_path: /etc/sark/certs/weather-api.key
      ca_path: /etc/sark/certs/ca.crt
```

**Expected Result:** Valid YAML configuration file.

### Step 2: Validate Configuration

```bash
sark-cli config validate /etc/sark/gateway/servers.yaml
```

**Expected Output:**
```
Validating configuration file...
✓ YAML syntax valid
✓ Schema validation passed
✓ 2 servers configured
✓ All endpoints are valid URLs
✓ Authentication configurations valid
⚠ Warning: server 'weather-api' uses mTLS - ensure certificates are valid

Configuration is valid and ready to use.
```

### Step 3: Reload Gateway Configuration

```bash
# Using systemd
sudo systemctl reload sark-gateway

# Using Docker
docker exec sark-gateway kill -HUP 1

# Using Kubernetes
kubectl rollout restart deployment/sark-gateway -n sark-system
```

**Expected Output:**
```
✓ Configuration reloaded successfully
✓ 2 servers registered
✓ 0 servers deregistered
✓ 0 servers updated
```

### Step 4: Verify Configuration Loaded

```bash
sark-cli server list --format json | jq '.servers[] | {id: .server_id, status: .status}'
```

**Expected Output:**
```json
{
  "id": "my-data-processor",
  "status": "active"
}
{
  "id": "weather-api",
  "status": "active"
}
```

## Updating Server Metadata

### Update via API

```bash
curl -X PATCH https://gateway.example.com/api/v1/servers/my-data-processor \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.1.0",
    "metadata": {
      "team": "data-platform",
      "environment": "production",
      "contact": "data-team@example.com",
      "changelog": "Added new data validation tools"
    }
  }'
```

**Expected Response:**
```json
{
  "status": "updated",
  "server_id": "my-data-processor",
  "version": "1.1.0",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

### Update via CLI

```bash
sark-cli server update my-data-processor \
  --version 1.1.0 \
  --metadata changelog="Added new data validation tools"
```

**Expected Output:**
```
✓ Server 'my-data-processor' updated successfully
Version: 1.0.0 → 1.1.0
```

## Testing Registration Success

### Step 1: Test Tool Discovery

```bash
curl https://gateway.example.com/api/v1/servers/my-data-processor/tools \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}"
```

**Expected Response:**
```json
{
  "server_id": "my-data-processor",
  "tools": [
    {
      "name": "transform_data",
      "description": "Transform data using specified rules",
      "input_schema": {
        "type": "object",
        "properties": {
          "data": {"type": "array"},
          "rules": {"type": "object"}
        }
      }
    },
    {
      "name": "analyze_dataset",
      "description": "Perform statistical analysis on datasets",
      "input_schema": {
        "type": "object",
        "properties": {
          "dataset": {"type": "array"},
          "metrics": {"type": "array"}
        }
      }
    }
  ]
}
```

### Step 2: Test Tool Invocation

```bash
curl -X POST https://gateway.example.com/api/v1/tools/invoke \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "my-data-processor",
    "tool_name": "transform_data",
    "arguments": {
      "data": [1, 2, 3, 4, 5],
      "rules": {"operation": "square"}
    }
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "result": {
    "transformed_data": [1, 4, 9, 16, 25]
  },
  "execution_time_ms": 123,
  "server_id": "my-data-processor"
}
```

### Step 3: Check Health Status

```bash
sark-cli server health my-data-processor
```

**Expected Output:**
```
Server: my-data-processor
Status: healthy
Last Check: 2024-01-15T11:05:00Z
Response Time: 45ms
Uptime: 99.98%
Failed Checks (24h): 0
```

## Deregistering Servers

### Graceful Deregistration via API

```bash
curl -X DELETE https://gateway.example.com/api/v1/servers/my-data-processor \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Migrating to new endpoint",
    "graceful_period": "5m"
  }'
```

**Expected Response:**
```json
{
  "status": "deregistering",
  "server_id": "my-data-processor",
  "graceful_period": "5m",
  "deregistration_time": "2024-01-15T11:10:00Z",
  "message": "Server will stop accepting new requests and complete in-flight requests"
}
```

**What This Means:** The server will complete existing requests but reject new ones for 5 minutes before full deregistration.

### Immediate Deregistration via CLI

```bash
sark-cli server deregister my-data-processor --force
```

**Expected Output:**
```
⚠ Warning: Force deregistration will immediately stop all requests
Continue? (y/N): y
✓ Server 'my-data-processor' deregistered
In-flight requests terminated: 3
```

### Verify Deregistration

```bash
sark-cli server list | grep my-data-processor
```

**Expected Output:**
```
(no output - server not found)
```

## Common Registration Errors and Fixes

### Error 1: Endpoint Not Reachable

**Error Message:**
```json
{
  "error": "server_unreachable",
  "message": "Failed to connect to https://api.example.com/mcp",
  "details": "Connection timeout after 5s"
}
```

**Diagnosis:**
```bash
# Test endpoint connectivity
curl -v https://api.example.com/mcp/health

# Check DNS resolution
nslookup api.example.com

# Test from gateway server
kubectl exec -it sark-gateway-0 -- curl https://api.example.com/mcp/health
```

**Fix:**
1. Verify server is running: `systemctl status my-mcp-server`
2. Check firewall rules allow gateway IP
3. Verify DNS resolution works from gateway
4. Check SSL/TLS certificates are valid

### Error 2: Invalid Protocol Version

**Error Message:**
```json
{
  "error": "protocol_mismatch",
  "message": "Server protocol version '2023-05-15' not supported",
  "supported_versions": ["2024-11-05", "2024-09-15"]
}
```

**Fix:**
Update your server registration:
```bash
sark-cli server update my-data-processor --protocol-version 2024-11-05
```

### Error 3: Authentication Failure

**Error Message:**
```json
{
  "error": "authentication_failed",
  "message": "Failed to authenticate with MCP server",
  "details": "Invalid bearer token"
}
```

**Diagnosis:**
```bash
# Verify token is set
echo $MCP_SERVER_TOKEN

# Test authentication manually
curl https://api.example.com/mcp/tools \
  -H "Authorization: Bearer ${MCP_SERVER_TOKEN}"
```

**Fix:**
1. Regenerate authentication token
2. Update environment variable in gateway config
3. Restart gateway to load new token:
```bash
kubectl set env deployment/sark-gateway \
  MCP_SERVER_TOKEN="${NEW_TOKEN}" \
  -n sark-system
```

### Error 4: Duplicate Server ID

**Error Message:**
```json
{
  "error": "duplicate_server_id",
  "message": "Server with ID 'my-data-processor' already registered"
}
```

**Fix Option 1:** Use different server ID
```bash
sark-cli server register \
  --server-id my-data-processor-v2 \
  --endpoint https://api.example.com/mcp
```

**Fix Option 2:** Deregister existing server first
```bash
sark-cli server deregister my-data-processor --force
sark-cli server register --server-id my-data-processor --endpoint https://api.example.com/mcp
```

### Error 5: Health Check Failures

**Error Message:**
```json
{
  "error": "health_check_failed",
  "message": "Server failed health check",
  "details": "Health endpoint returned 503 Service Unavailable"
}
```

**Diagnosis:**
```bash
# Check health endpoint
curl https://api.example.com/mcp/health

# View health check logs
kubectl logs deployment/sark-gateway -n sark-system | grep health_check
```

**Fix:**
1. Ensure health endpoint returns 200 status
2. Adjust health check thresholds:
```bash
sark-cli server update my-data-processor \
  --health-check-timeout 10s \
  --health-check-unhealthy-threshold 5
```

### Error 6: Schema Validation Failure

**Error Message:**
```json
{
  "error": "invalid_schema",
  "message": "Registration payload validation failed",
  "validation_errors": [
    {
      "field": "endpoint",
      "error": "must be a valid HTTPS URL"
    }
  ]
}
```

**Fix:**
1. Validate JSON schema:
```bash
sark-cli config validate server-registration.json
```

2. Common schema fixes:
   - Endpoint must use HTTPS (not HTTP)
   - Server ID must match pattern: `^[a-z0-9-]+$`
   - Version must follow semver: `X.Y.Z`

## Common Pitfalls

### Pitfall 1: Missing Environment Variables

**Problem:** Gateway can't authenticate because `MCP_SERVER_TOKEN` isn't set.

**Solution:**
```bash
# Set in systemd service
sudo systemctl edit sark-gateway
# Add:
[Service]
Environment="MCP_SERVER_TOKEN=your-token-here"

# Set in Docker
docker run -e MCP_SERVER_TOKEN=your-token-here sark/gateway

# Set in Kubernetes
kubectl create secret generic mcp-tokens \
  --from-literal=data-processor-token=your-token-here \
  -n sark-system
```

### Pitfall 2: Registering Non-Existent Endpoints

**Problem:** Registering server before it's deployed.

**Solution:** Always test endpoint first:
```bash
# Test endpoint exists and responds
curl https://api.example.com/mcp/tools

# Then register
sark-cli server register --endpoint https://api.example.com/mcp
```

### Pitfall 3: Ignoring Health Check Status

**Problem:** Server registered but unhealthy, causing tool invocation failures.

**Solution:** Monitor health status:
```bash
# Set up alert for unhealthy servers
sark-cli server watch my-data-processor --alert-on-unhealthy
```

### Pitfall 4: Not Using Namespaces

**Problem:** Server ID conflicts across different environments.

**Solution:** Use naming conventions:
```bash
# Development
sark-cli server register --server-id dev-data-processor

# Staging
sark-cli server register --server-id staging-data-processor

# Production
sark-cli server register --server-id prod-data-processor
```

### Pitfall 5: Hardcoding Credentials

**Problem:** API keys in configuration files committed to git.

**Solution:** Use environment variables and secret management:
```yaml
# Bad
authentication:
  type: bearer
  token: "sk-1234567890abcdef"

# Good
authentication:
  type: bearer
  token_env_var: MCP_SERVER_TOKEN
```

## Related Resources

- [MCP Server Implementation Guide](../tutorials/building-mcp-server.md)
- [Gateway Configuration Reference](../reference/gateway-configuration.md)
- [Authentication Methods](../explanation/gateway-authentication.md)
- [Health Check Configuration](../reference/health-checks.md)
- [Troubleshooting Server Registration](./how-to-troubleshoot-tools.md)
- [Security Best Practices](./how-to-secure-gateway.md)

## Next Steps

After registering your server:

1. **Implement policies** - Control who can access your tools
   - See: [How to Write Policies](./how-to-write-policies.md)

2. **Set up monitoring** - Track server performance and health
   - See: [How to Monitor Gateway](./how-to-monitor-gateway.md)

3. **Test tool invocation** - Verify tools work through the gateway
   - See: [How to Implement Tools](./how-to-implement-tool.md)

4. **Secure your deployment** - Implement authentication and rate limiting
   - See: [How to Secure Gateway](./how-to-secure-gateway.md)
