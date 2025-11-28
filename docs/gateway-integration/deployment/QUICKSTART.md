# Gateway Integration Quick Start

**Time Required:** 15 minutes
**Difficulty:** Beginner
**Version:** 1.1.0

---

## Overview

This quick start guide will help you enable Gateway integration in SARK v1.1.0 and connect to the MCP Gateway Registry.

**What You'll Accomplish:**
- Enable Gateway integration in SARK
- Configure Gateway connection
- Generate a Gateway API key
- Test the integration
- Verify authorization flow

---

## Prerequisites

Before starting, ensure you have:

- [ ] **SARK v1.1.0+** deployed and running
- [ ] **MCP Gateway Registry** deployed and accessible
- [ ] **Docker and Docker Compose** (if using Docker deployment)
- [ ] **kubectl** access (if using Kubernetes deployment)
- [ ] **Admin access** to SARK

---

## Step 1: Verify SARK Version

First, verify you're running SARK v1.1.0 or later:

```bash
# Check SARK version
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.1.0",
  "major": 1,
  "minor": 1,
  "patch": 0,
  "features": {
    "gateway_integration": false,  # Currently disabled
    "a2a_authorization": false
  }
}
```

**If you're on v1.0.0:** See [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) to upgrade to v1.1.0.

---

## Step 2: Obtain Gateway Connection Details

You'll need the following information from your MCP Gateway deployment:

1. **Gateway URL** - API endpoint (e.g., `http://mcp-gateway:8080`)
2. **Gateway API Key** - Authentication credential for SARK to connect to Gateway

### Get Gateway URL

```bash
# Docker Compose deployment
# Check docker-compose.yml for Gateway service
docker compose ps mcp-gateway

# Kubernetes deployment
kubectl get service mcp-gateway -n mcp-gateway
```

**Example Gateway URL:** `http://mcp-gateway:8080`

### Get Gateway API Key

Contact your Gateway administrator or generate one:

```bash
# Example: Generate Gateway API key (if you're the Gateway admin)
# This varies by Gateway implementation
curl -X POST http://mcp-gateway:8080/api/v1/api-keys \
  -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  -d '{
    "name": "SARK Authorization Service",
    "permissions": ["sark:callback"]
  }'
```

**Save the API key securely** - you'll need it in the next step.

---

## Step 3: Configure Gateway Integration

### Option A: Docker Compose Deployment

1. Create a `.env.gateway` file:

```bash
cat > .env.gateway << 'EOF'
# Gateway Integration Configuration
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
GATEWAY_API_KEY=your_gateway_api_key_here

# Optional: Agent-to-Agent Authorization
A2A_ENABLED=false

# Optional: Gateway Timeouts
GATEWAY_TIMEOUT_SECONDS=30
GATEWAY_RETRY_ATTEMPTS=3
EOF
```

2. Update your main `.env` file:

```bash
# Add Gateway configuration to .env
cat .env.gateway >> .env
```

3. **Edit `.env`** and replace `your_gateway_api_key_here` with your actual Gateway API key.

### Option B: Kubernetes Deployment

1. Create a Kubernetes Secret for the Gateway API key:

```bash
kubectl create secret generic sark-gateway-config \
  --from-literal=gateway-api-key='your_gateway_api_key_here' \
  -n sark
```

2. Update the SARK deployment ConfigMap:

```yaml
# sark-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sark-config
  namespace: sark
data:
  GATEWAY_ENABLED: "true"
  GATEWAY_URL: "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"
  A2A_ENABLED: "false"
  GATEWAY_TIMEOUT_SECONDS: "30"
  GATEWAY_RETRY_ATTEMPTS: "3"
```

3. Apply the ConfigMap:

```bash
kubectl apply -f sark-configmap.yaml
```

---

## Step 4: Generate SARK Gateway API Key

SARK needs its own API key for the Gateway to call back to SARK for authorization decisions.

```bash
# Docker deployment
docker exec -it sark python -m sark.cli.generate_api_key \
  --name "MCP Gateway Production" \
  --type gateway \
  --permissions "gateway:authorize,gateway:audit,gateway:servers:read,gateway:tools:read"

# Kubernetes deployment
kubectl exec -it deployment/sark -n sark -- \
  python -m sark.cli.generate_api_key \
  --name "MCP Gateway Production" \
  --type gateway \
  --permissions "gateway:authorize,gateway:audit,gateway:servers:read,gateway:tools:read"
```

**Output:**
```json
{
  "api_key_id": "gw_key_abc123",
  "api_key": "sark_gw_1234567890abcdef1234567890abcdef",
  "name": "MCP Gateway Production",
  "type": "gateway",
  "permissions": [
    "gateway:authorize",
    "gateway:audit",
    "gateway:servers:read",
    "gateway:tools:read"
  ],
  "created_at": "2025-01-15T10:00:00Z",
  "expires_at": "2026-01-15T10:00:00Z"
}
```

**Important:** Copy the `api_key` value (`sark_gw_...`) and save it securely. You'll configure this in the Gateway in Step 6.

---

## Step 5: Restart SARK

Restart SARK to apply the Gateway configuration:

### Docker Compose

```bash
docker compose restart sark

# Watch logs to verify Gateway initialization
docker compose logs -f sark | grep -i gateway
```

**Expected log output:**
```
INFO: Gateway integration enabled
INFO: Gateway client initialized: http://mcp-gateway:8080
INFO: Gateway health check: OK
```

### Kubernetes

```bash
kubectl rollout restart deployment/sark -n sark

# Watch pod status
kubectl rollout status deployment/sark -n sark

# Check logs
kubectl logs -f deployment/sark -n sark | grep -i gateway
```

---

## Step 6: Configure Gateway to Call SARK

Now configure the MCP Gateway to use SARK for authorization.

### Update Gateway Configuration

Add SARK as the authorization service in your Gateway configuration:

```yaml
# Gateway configuration (example - varies by Gateway implementation)
authorization:
  provider: "sark"
  url: "http://sark:8000/api/v1/gateway"
  api_key: "sark_gw_1234567890abcdef1234567890abcdef"  # From Step 4
  endpoints:
    authorize: "/authorize"
    authorize_a2a: "/authorize-a2a"
    servers: "/servers"
    tools: "/tools"
    audit: "/audit"
  timeout_seconds: 30
  cache_ttl: 60
```

**Restart the Gateway service** after updating the configuration.

---

## Step 7: Verify Integration

Test the Gateway integration to ensure everything is working.

### Test 1: Check SARK Feature Status

```bash
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.1.0",
  "features": {
    "gateway_integration": true,  # ✅ Now enabled
    "a2a_authorization": false
  }
}
```

### Test 2: Test Authorization Endpoint

```bash
# First, get a user JWT token
USER_TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin_password"
  }' | jq -r '.access_token')

# Test the authorization endpoint
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "test-server",
    "tool_name": "test-tool",
    "user": {
      "id": "user_123",
      "email": "admin@example.com",
      "roles": ["admin"]
    }
  }'
```

**Expected output:**
```json
{
  "allow": true,
  "reason": "Allowed by policy",
  "audit_id": "audit_abc123",
  "cache_ttl": 60
}
```

### Test 3: Test via Gateway (End-to-End)

```bash
# Invoke a tool through the Gateway
# This will cause the Gateway to call SARK's authorization endpoint
curl -X POST http://mcp-gateway:8080/api/v1/tools/invoke \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server": "postgres-mcp",
    "tool": "execute_query",
    "parameters": {
      "query": "SELECT 1"
    }
  }'
```

**Check SARK audit logs:**
```bash
# Docker
docker compose logs sark | grep "gateway_authorize"

# Kubernetes
kubectl logs deployment/sark -n sark | grep "gateway_authorize"
```

**Expected log output:**
```
INFO: Gateway authorization request: server=postgres-mcp tool=execute_query user=admin@example.com decision=allow
```

---

## Step 8: Configure OPA Policies (Optional)

By default, SARK uses permissive Gateway policies. To implement fine-grained authorization:

1. Create a Gateway policy file:

```bash
mkdir -p /etc/sark/policies
cat > /etc/sark/policies/gateway.rego << 'EOF'
package mcp.gateway

# Default deny
default allow = false

# Allow admins to invoke any tool
allow {
    input.user.roles[_] == "admin"
    input.action == "gateway:tool:invoke"
}

# Allow analysts to query databases
allow {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "execute_query"
}

# Deny destructive operations for non-admins
deny {
    input.user.roles[_] != "admin"
    input.tool_name in ["execute_mutation", "drop_table", "delete_all"]
}
EOF
```

2. Load the policy into OPA:

```bash
# Docker
docker exec -it opa \
  curl -X PUT http://localhost:8181/v1/policies/gateway \
  --data-binary @/etc/sark/policies/gateway.rego

# Kubernetes
kubectl create configmap opa-gateway-policy \
  --from-file=gateway.rego=/etc/sark/policies/gateway.rego \
  -n sark
```

See [configuration/POLICY_CONFIGURATION.md](../configuration/POLICY_CONFIGURATION.md) for advanced policy examples.

---

## Troubleshooting

### Issue: "Gateway integration not enabled" (503 error)

**Cause:** `GATEWAY_ENABLED=false` or SARK not restarted.

**Fix:**
```bash
# Verify configuration
docker exec -it sark env | grep GATEWAY_ENABLED

# Should output: GATEWAY_ENABLED=true
# If not, update .env and restart SARK
```

### Issue: "Gateway connection failed"

**Cause:** Gateway URL incorrect or Gateway not running.

**Fix:**
```bash
# Test Gateway connectivity from SARK container
docker exec -it sark curl http://mcp-gateway:8080/health

# Should return: {"status": "healthy"}
```

### Issue: "Invalid Gateway API key"

**Cause:** API key mismatch between SARK and Gateway.

**Fix:**
```bash
# Regenerate Gateway API key
docker exec -it sark python -m sark.cli.generate_api_key \
  --name "MCP Gateway Production" \
  --type gateway \
  --permissions "gateway:*"

# Update Gateway configuration with new API key
```

### Issue: "Authorization always returns deny"

**Cause:** OPA policy too restrictive or not loaded.

**Fix:**
```bash
# Check OPA policy status
curl http://localhost:8181/v1/policies

# Test policy directly
curl -X POST http://localhost:8181/v1/data/mcp/gateway/allow \
  -d '{
    "input": {
      "action": "gateway:tool:invoke",
      "server_name": "test-server",
      "user": {"roles": ["admin"]}
    }
  }'
```

For more troubleshooting, see [runbooks/TROUBLESHOOTING.md](../runbooks/TROUBLESHOOTING.md).

---

## Next Steps

Congratulations! Your Gateway integration is now operational.

**Recommended Next Steps:**

1. **Configure Fine-Grained Policies**
   - See [configuration/POLICY_CONFIGURATION.md](../configuration/POLICY_CONFIGURATION.md)

2. **Enable A2A Authorization**
   - Set `A2A_ENABLED=true` in your configuration
   - See [configuration/A2A_CONFIGURATION.md](../configuration/A2A_CONFIGURATION.md)

3. **Production Deployment**
   - See [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
   - Set up monitoring and alerting
   - Configure high availability

4. **Kubernetes Deployment**
   - See [KUBERNETES_DEPLOYMENT.md](./KUBERNETES_DEPLOYMENT.md)
   - Deploy with Helm charts
   - Configure auto-scaling

5. **Review Architecture**
   - See [architecture/INTEGRATION_ARCHITECTURE.md](../architecture/INTEGRATION_ARCHITECTURE.md)
   - Understand data flows and security layers

---

## Quick Reference

### Key Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_ENABLED` | `false` | Enable Gateway integration |
| `GATEWAY_URL` | - | Gateway API endpoint |
| `GATEWAY_API_KEY` | - | Gateway authentication key |
| `A2A_ENABLED` | `false` | Enable Agent-to-Agent authorization |
| `GATEWAY_TIMEOUT_SECONDS` | `30` | Request timeout |
| `GATEWAY_RETRY_ATTEMPTS` | `3` | Retry failed requests |

### Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/gateway/authorize` | Authorize Gateway requests |
| `POST /api/v1/gateway/authorize-a2a` | Authorize A2A requests |
| `GET /api/v1/gateway/servers` | List authorized servers |
| `GET /api/v1/gateway/tools` | List authorized tools |
| `POST /api/v1/gateway/audit` | Log audit events |

### Useful Commands

```bash
# Check Gateway status
curl http://localhost:8000/api/v1/version

# View Gateway logs
docker compose logs -f sark | grep gateway

# Test authorization
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" -d '{...}'

# Generate API key
docker exec -it sark python -m sark.cli.generate_api_key \
  --type gateway --permissions "gateway:*"
```

---

**Quick Start Guide Version:** 1.1.0
**Last Updated:** 2025
