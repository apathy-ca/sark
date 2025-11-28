# Gateway Integration Authentication

**Version:** 1.1.0
**Status:** Production Ready
**Last Updated:** 2025

---

## Overview

This guide covers authentication methods for the SARK Gateway Integration API. Three authentication methods are supported:

1. **User JWT Tokens** - For user-initiated requests via Gateway
2. **Gateway API Keys** - For Gateway service authentication (recommended)
3. **Agent JWT Tokens** - For Agent-to-Agent (A2A) authorization

---

## Table of Contents

- [User JWT Tokens](#user-jwt-tokens)
- [Gateway API Keys](#gateway-api-keys)
- [Agent JWT Tokens](#agent-jwt-tokens)
- [Trust Levels](#trust-levels)
- [Token Validation](#token-validation)
- [Security Best Practices](#security-best-practices)

---

## User JWT Tokens

User JWT tokens are standard SARK authentication tokens issued when users log in.

### Use Case

- User authenticates to Gateway UI
- Gateway forwards authorization requests to SARK on behalf of the user
- SARK validates the user's permissions and returns an authorization decision

### Token Format

```json
{
  "sub": "user_abc123",
  "email": "alice@example.com",
  "roles": ["analyst", "user"],
  "iss": "sark-auth",
  "aud": "sark-api",
  "exp": 1642252800,
  "iat": 1642249200
}
```

### Required Claims

| Claim | Description |
|-------|-------------|
| `sub` | User ID (subject) |
| `email` | User email address |
| `roles` | Array of user roles |
| `iss` | Issuer (must be `sark-auth`) |
| `aud` | Audience (must be `sark-api`) |
| `exp` | Expiration timestamp |
| `iat` | Issued at timestamp |

### Obtaining a User Token

```bash
# Login to SARK
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "secure_password"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Using a User Token

```bash
# Use token in Gateway API request
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_abc123",
      "email": "alice@example.com",
      "roles": ["analyst"]
    }
  }'
```

---

## Gateway API Keys

Gateway API Keys are dedicated authentication credentials for the MCP Gateway service.

### Use Case

- MCP Gateway authenticates to SARK using a long-lived API key
- Recommended for production deployments
- Supports high throughput (10,000 requests/minute vs 1,000 for user tokens)

### Generating a Gateway API Key

#### Method 1: CLI Tool

```bash
# Generate a new Gateway API key
docker exec -it sark python -m sark.cli.generate_api_key \
  --name "MCP Gateway Production" \
  --type gateway \
  --permissions "gateway:authorize,gateway:audit"

# Output
{
  "api_key_id": "gw_key_abc123",
  "api_key": "sark_gw_1234567890abcdef1234567890abcdef",
  "name": "MCP Gateway Production",
  "type": "gateway",
  "permissions": ["gateway:authorize", "gateway:audit"],
  "created_at": "2025-01-15T10:00:00Z",
  "expires_at": "2026-01-15T10:00:00Z"
}
```

**Important:** Save the `api_key` value securely. It cannot be retrieved later.

#### Method 2: SARK Admin UI

1. Navigate to **Settings** → **API Keys**
2. Click **Generate New API Key**
3. Select **Type:** Gateway
4. Set **Permissions:** `gateway:authorize`, `gateway:audit`
5. Set **Expiration:** 1 year (or custom)
6. Click **Generate**
7. Copy the API key and store it securely

### API Key Format

```
sark_gw_<32-character-hex-string>
```

**Example:** `sark_gw_1234567890abcdef1234567890abcdef`

### Using a Gateway API Key

#### Environment Variable (Recommended)

```bash
# Set in Gateway service environment
export SARK_API_KEY="sark_gw_1234567890abcdef1234567890abcdef"
```

#### Request Header

```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer sark_gw_1234567890abcdef1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### API Key Permissions

API keys can have granular permissions:

| Permission | Description |
|------------|-------------|
| `gateway:authorize` | Authorize Gateway requests (`/gateway/authorize`) |
| `gateway:authorize-a2a` | Authorize A2A requests (`/gateway/authorize-a2a`) |
| `gateway:audit` | Log audit events (`/gateway/audit`) |
| `gateway:servers:read` | List servers (`/gateway/servers`) |
| `gateway:tools:read` | List tools (`/gateway/tools`) |
| `gateway:*` | All Gateway permissions (admin) |

### Rotating API Keys

```bash
# Generate a new API key
NEW_KEY=$(docker exec -it sark python -m sark.cli.generate_api_key \
  --name "MCP Gateway Production (Rotated)" \
  --type gateway \
  --permissions "gateway:*" | jq -r '.api_key')

# Update Gateway configuration
# In Gateway .env or Kubernetes secret
SARK_API_KEY=$NEW_KEY

# Restart Gateway service
kubectl rollout restart deployment/mcp-gateway

# Verify new key works
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $NEW_KEY" \
  -d '{...}'

# Revoke old key
docker exec -it sark python -m sark.cli.revoke_api_key \
  --api_key_id "gw_key_abc123"
```

**Recommended Rotation Schedule:** Every 90 days

---

## Agent JWT Tokens

Agent JWT tokens are used for Agent-to-Agent (A2A) authorization.

### Use Case

- Agent A requests authorization to call Agent B via Gateway
- Agent A includes its JWT token in the request
- SARK validates the agent's trust level and capabilities

### Token Format

```json
{
  "sub": "agent_research_123",
  "agent_name": "research-agent",
  "agent_id": "agent_research_123",
  "trust_level": "high",
  "capabilities": ["research", "web_search", "data_analysis"],
  "iss": "sark-agent-auth",
  "aud": "sark-a2a",
  "exp": 1642252800,
  "iat": 1642249200
}
```

### Required Claims

| Claim | Description |
|-------|-------------|
| `sub` | Agent ID (subject) |
| `agent_name` | Human-readable agent name |
| `agent_id` | Unique agent identifier |
| `trust_level` | Trust level: `low`, `medium`, `high`, `critical` |
| `capabilities` | Array of agent capabilities |
| `iss` | Issuer (must be `sark-agent-auth`) |
| `aud` | Audience (must be `sark-a2a`) |
| `exp` | Expiration timestamp |
| `iat` | Issued at timestamp |

### Generating an Agent Token

```bash
# Register an agent and get a token
curl -X POST http://localhost:8000/api/v1/agents/register \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "research-agent",
    "trust_level": "high",
    "capabilities": ["research", "web_search", "data_analysis"],
    "owner_user_id": "user_abc123"
  }'

# Response
{
  "agent_id": "agent_research_123",
  "agent_token": "eyJhbGciOiJIUzI1NiIs...",
  "trust_level": "high",
  "capabilities": ["research", "web_search", "data_analysis"],
  "expires_at": "2025-02-15T10:00:00Z"
}
```

### Using an Agent Token

```bash
# Agent-to-Agent authorization request
curl -X POST http://localhost:8000/api/v1/gateway/authorize-a2a \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "action": "a2a:invoke",
    "source_agent": {
      "id": "agent_research_123",
      "name": "research-agent",
      "trust_level": "high"
    },
    "target_agent": {
      "id": "agent_db_456",
      "name": "database-agent"
    },
    "tool_name": "query_database"
  }'
```

---

## Trust Levels

Agent trust levels determine authorization capabilities in A2A scenarios.

### Trust Level Hierarchy

| Level | Value | Description | Allowed Actions |
|-------|-------|-------------|-----------------|
| **Critical** | 4 | Highest trust, system agents | All A2A operations, delegate to any agent |
| **High** | 3 | Trusted agents, verified owners | Most A2A operations, delegate to high/medium/low |
| **Medium** | 2 | Standard agents | Basic A2A operations, delegate to medium/low |
| **Low** | 1 | Untrusted or new agents | Limited A2A operations, no delegation |

### Trust Level Policy Example

```rego
# In OPA policy
package mcp.gateway.a2a

allow {
    # High-trust agents can call medium/low trust agents
    input.source_agent.trust_level == "high"
    input.target_agent.trust_level in ["medium", "low"]
}

deny {
    # Low-trust agents cannot call high-trust agents
    input.source_agent.trust_level == "low"
    input.target_agent.trust_level in ["high", "critical"]
}
```

### Setting Agent Trust Level

```bash
# Update agent trust level
curl -X PATCH http://localhost:8000/api/v1/agents/agent_research_123 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trust_level": "high"
  }'
```

**Note:** Trust level changes require admin privileges and trigger token regeneration.

---

## Token Validation

SARK validates all tokens before processing Gateway API requests.

### Validation Steps

1. **Signature Verification** - Verify JWT signature using secret key
2. **Expiration Check** - Ensure token is not expired
3. **Issuer/Audience Check** - Verify `iss` and `aud` claims
4. **Permission Check** - Verify token has required permissions
5. **Revocation Check** - Check if token/API key has been revoked

### Token Validation Example

```python
# Internal SARK token validation logic
from sark.auth import validate_token

try:
    token_data = validate_token(
        token="eyJhbGciOiJIUzI1NiIs...",
        expected_iss="sark-auth",
        expected_aud="sark-api",
        required_permissions=["gateway:authorize"]
    )
    # Token is valid
except TokenExpiredError:
    # Token has expired
    return {"error": "Token expired"}
except InvalidTokenError:
    # Token is invalid
    return {"error": "Invalid token"}
```

### Token Caching

SARK caches validated tokens for performance:

- **Cache TTL:** 5 minutes
- **Cache Key:** `sha256(token)`
- **Cache Invalidation:** On token revocation or expiration

---

## Security Best Practices

### 1. Use Gateway API Keys for Production

- **DO:** Use dedicated Gateway API keys for production deployments
- **DON'T:** Use user JWT tokens for high-volume Gateway traffic

```bash
# Good (production)
SARK_API_KEY=sark_gw_1234567890abcdef1234567890abcdef

# Avoid (high-volume production)
# Using user tokens for Gateway service authentication
```

### 2. Rotate API Keys Regularly

```bash
# Rotate every 90 days
docker exec -it sark python -m sark.cli.rotate_api_key \
  --api_key_id "gw_key_abc123" \
  --new_expiration "90d"
```

### 3. Use Least Privilege Permissions

```bash
# Good: Only grant necessary permissions
--permissions "gateway:authorize,gateway:audit"

# Avoid: Granting excessive permissions
--permissions "gateway:*"
```

### 4. Store API Keys Securely

- **DO:** Use secret management systems (Kubernetes Secrets, AWS Secrets Manager, HashiCorp Vault)
- **DON'T:** Commit API keys to version control

```yaml
# Good: Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: sark-gateway-api-key
type: Opaque
stringData:
  api-key: sark_gw_1234567890abcdef1234567890abcdef
```

### 5. Monitor Token Usage

```bash
# Check API key usage metrics
curl http://localhost:9090/api/v1/query \
  -d 'query=sark_gateway_api_key_requests_total{api_key_id="gw_key_abc123"}'
```

### 6. Enable Token Revocation Checks

```bash
# Ensure token revocation is enabled
SARK_TOKEN_REVOCATION_ENABLED=true
SARK_TOKEN_REVOCATION_CACHE_TTL=60
```

### 7. Use Short-Lived Tokens for Agents

```bash
# Generate agent tokens with 24-hour expiration
--expiration "24h"
```

### 8. Implement Rate Limiting

```bash
# Configure rate limits per token type
SARK_RATE_LIMIT_USER_JWT=1000
SARK_RATE_LIMIT_GATEWAY_API_KEY=10000
SARK_RATE_LIMIT_AGENT_JWT=5000
```

---

## Troubleshooting

### Issue: "Invalid token" error

**Symptoms:**
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Token signature verification failed"
  }
}
```

**Resolution:**
1. Verify token is correctly formatted
2. Check JWT secret key matches SARK configuration
3. Ensure token has not been revoked
4. Verify `iss` and `aud` claims

### Issue: "Token expired" error

**Symptoms:**
```json
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "Token has expired"
  }
}
```

**Resolution:**
1. Generate a new token
2. Update Gateway configuration with new token
3. For API keys, rotate using CLI tool

### Issue: "Insufficient permissions" error

**Symptoms:**
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Token lacks required permission: gateway:authorize"
  }
}
```

**Resolution:**
1. Check API key permissions: `docker exec -it sark python -m sark.cli.list_api_keys`
2. Regenerate API key with correct permissions
3. For user tokens, verify user has required roles

---

## Next Steps

- **API Reference:** See [API_REFERENCE.md](./API_REFERENCE.md)
- **Configuration:** See [configuration/GATEWAY_CONFIGURATION.md](./configuration/GATEWAY_CONFIGURATION.md)
- **Deployment:** See [deployment/QUICKSTART.md](./deployment/QUICKSTART.md)
- **Troubleshooting:** See [runbooks/TROUBLESHOOTING.md](./runbooks/TROUBLESHOOTING.md)

---

**Authentication Guide Version:** 1.1.0
**Last Updated:** 2025
