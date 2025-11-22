# SARK Quick Start Guide

Get up and running with SARK in under 15 minutes. This guide covers installation, authentication, server registration, policy evaluation, and session management.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup](#quick-setup)
3. [Authentication Workflows](#authentication-workflows)
4. [Server Management](#server-management)
5. [Policy Evaluation](#policy-evaluation)
6. [Session Management](#session-management)
7. [API Keys](#api-keys)
8. [Rate Limiting](#rate-limiting)
9. [Monitoring & Observability](#monitoring--observability)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker** 20.10+ and **Docker Compose** v2
- **Python** 3.11+ (for local development only)
- **curl** or **HTTPie** for API testing
- **8GB+ RAM** available for Docker

### Optional Tools

- **Postman** - Use the provided collection in `postman/`
- **jq** - For JSON formatting: `apt-get install jq` or `brew install jq`

### Verify Prerequisites

```bash
# Check Docker version
docker --version  # Should be 20.10+
docker compose version  # Should be v2+

# Check available memory
docker stats --no-stream

# Verify ports are available (8000, 5432, 6379, 8500, 8181)
netstat -tuln | grep -E ':(8000|5432|6379|8500|8181)'  # Should be empty
```

---

## Quick Setup

### Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/sark.git
cd sark

# Verify structure
ls -la
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if needed (default values work for development)
nano .env
```

**Key Environment Variables:**
```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Authentication
JWT_SECRET_KEY=dev-secret-change-in-production
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=7

# Redis (Session Store)
REDIS_DSN=redis://:password@redis:6379/0

# LDAP (Optional - for LDAP authentication)
LDAP_ENABLED=true
LDAP_SERVER=ldap://openldap:389

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_USER_REQUESTS_PER_MINUTE=5000
```

### Step 3: Start All Services

```bash
# Start services in detached mode
docker compose up -d

# Wait for services to be healthy (30-60 seconds)
docker compose ps
```

**Expected Services:**
```
NAME                STATUS      PORTS
sark-api            Up          0.0.0.0:8000->8000/tcp
sark-postgres       Up          5432/tcp
sark-timescaledb    Up          5432/tcp
sark-redis          Up          6379/tcp
sark-consul         Up          0.0.0.0:8500->8500/tcp
sark-opa            Up          0.0.0.0:8181->8181/tcp
sark-prometheus     Up          0.0.0.0:9090->9090/tcp
sark-grafana        Up          0.0.0.0:3000->3000/tcp
```

### Step 4: Verify Installation

```bash
# Check API health
curl http://localhost:8000/health | jq

# Expected output:
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "environment": "development"
# }

# Check detailed health (all dependencies)
curl http://localhost:8000/health/detailed | jq

# Expected output:
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

### Step 5: Access Web Interfaces

**API Documentation (Swagger UI):**
```bash
open http://localhost:8000/docs
```

**Consul UI (Service Discovery):**
```bash
open http://localhost:8500
```

**Grafana (Monitoring):**
```bash
open http://localhost:3000
# Login: admin / admin
```

**Prometheus (Metrics):**
```bash
open http://localhost:9090
```

---

## Authentication Workflows

SARK supports multiple authentication methods. Choose the one that fits your environment.

### Option 1: LDAP Authentication

**Use Case:** Corporate environments with Active Directory or LDAP servers

```bash
# Authenticate with LDAP credentials
curl -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "password": "secretpassword"
  }' | jq

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",
#   "token_type": "bearer",
#   "expires_in": 3600,
#   "refresh_token": "rt_abc123...",
#   "user": {
#     "user_id": "550e8400-e29b-41d4-a716-446655440000",
#     "username": "john.doe",
#     "email": "john.doe@example.com",
#     "roles": ["developer", "team_lead"],
#     "teams": ["engineering"]
#   }
# }

# Save tokens for later use
export ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIs..."
export REFRESH_TOKEN="rt_abc123..."
```

### Option 2: OIDC Authentication

**Use Case:** OAuth2/OpenID Connect providers (Google, Okta, Auth0)

```bash
# Initiate OIDC flow (browser-based)
# 1. Open browser to:
open http://localhost:8000/api/v1/auth/oidc/login

# 2. You'll be redirected to IdP (e.g., Google)
# 3. After successful login, redirected back with tokens
# 4. Tokens will be in callback response

# For programmatic access, use OIDC client credentials flow
# (Requires OIDC provider configuration)
```

### Option 3: SAML 2.0 Authentication

**Use Case:** Enterprise SSO with SAML identity providers

```bash
# Initiate SAML SSO flow
open "http://localhost:8000/api/auth/saml/login?relay_state=/"

# After successful SAML authentication:
# - User authenticated via IdP
# - Session created in SARK
# - Redirected back to application with tokens
```

### Option 4: API Keys (Service-to-Service)

**Use Case:** Automated scripts, CI/CD pipelines, service integrations

First, authenticate with a user account to create an API key:

```bash
# Create API key (requires authentication)
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Automation Key",
    "description": "For CI/CD pipeline",
    "scopes": ["server:read", "server:write"],
    "rate_limit": 1000,
    "expires_in_days": 90,
    "environment": "live"
  }' | jq

# Response:
# {
#   "api_key": {
#     "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
#     "name": "Automation Key",
#     "key_prefix": "sark_live_abc"
#   },
#   "key": "sark_live_abc123def456ghi789jkl012mno345",
#   "message": "API key created successfully. Save this key securely!"
# }

# Save API key
export API_KEY="sark_live_abc123def456ghi789jkl012mno345"

# Use API key for requests
curl -X GET http://localhost:8000/api/v1/servers \
  -H "X-API-Key: $API_KEY" | jq
```

### Get Current User Info

```bash
# Verify authentication and get user profile
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Response:
# {
#   "user_id": "550e8400-e29b-41d4-a716-446655440000",
#   "username": "john.doe",
#   "email": "john.doe@example.com",
#   "roles": ["developer", "team_lead"],
#   "teams": ["engineering", "platform"],
#   "permissions": ["server:read", "server:write", "policy:read"]
# }
```

---

## Server Management

### Register Your First MCP Server

```bash
# Register a sample database server
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "analytics-db-server",
    "transport": "http",
    "endpoint": "http://analytics.internal.example.com:8080",
    "version": "2025-06-18",
    "capabilities": ["tools"],
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
    "description": "Analytics database server with query tools",
    "sensitivity_level": "high",
    "metadata": {
      "team": "data-engineering",
      "owner": "john.doe@example.com",
      "environment": "production"
    }
  }' | jq

# Response:
# {
#   "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
#   "status": "registered",
#   "consul_id": "analytics-db-server-6ba7b810"
# }

# Save server ID
export SERVER_ID="6ba7b810-9dad-11d1-80b4-00c04fd430c8"
```

### List Registered Servers

```bash
# List all servers
curl -X GET "http://localhost:8000/api/v1/servers?limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Filter by status and sensitivity
curl -X GET "http://localhost:8000/api/v1/servers?status=active&sensitivity=high" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Search for servers
curl -X GET "http://localhost:8000/api/v1/servers?search=analytics" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

### Get Server Details

```bash
# Get specific server
curl -X GET "http://localhost:8000/api/v1/servers/$SERVER_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Response includes full details:
# - All tools with sensitivity levels
# - Metadata and tags
# - Creation/update timestamps
```

### Bulk Register Servers

```bash
# Register multiple servers in one request
curl -X POST http://localhost:8000/api/v1/bulk/servers/register \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "servers": [
      {
        "name": "ml-inference-server-1",
        "transport": "http",
        "endpoint": "http://ml-1.internal.example.com",
        "capabilities": ["tools"],
        "tools": [],
        "sensitivity_level": "critical"
      },
      {
        "name": "ml-inference-server-2",
        "transport": "http",
        "endpoint": "http://ml-2.internal.example.com",
        "capabilities": ["tools"],
        "tools": [],
        "sensitivity_level": "critical"
      }
    ],
    "fail_on_first_error": false
  }' | jq

# Response shows success/failure for each server
```

---

## Policy Evaluation

### Basic Policy Evaluation

```bash
# Evaluate if user can invoke a tool
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "tool:invoke",
    "tool": "execute_query",
    "server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "parameters": {
      "query": "SELECT * FROM users",
      "database": "analytics"
    }
  }' | jq

# Response (Allow):
# {
#   "decision": "allow",
#   "reason": "User has required role and tool sensitivity is within allowed level",
#   "filtered_parameters": null,
#   "audit_id": "audit_123abc"
# }

# Response (Deny):
# {
#   "decision": "deny",
#   "reason": "Tool sensitivity level 'critical' exceeds user's maximum allowed level 'high'",
#   "filtered_parameters": null,
#   "audit_id": "audit_456def"
# }
```

### Advanced Policy Features

#### Time-Based Access Control

```bash
# Evaluate policy with time constraints
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "server:register",
    "context": {
      "timestamp": "2025-11-22T23:30:00Z",
      "time_of_day": "23:30",
      "day_of_week": "friday"
    }
  }' | jq

# May be denied if outside business hours (9 AM - 5 PM Monday-Friday)
```

#### IP-Based Access Control

```bash
# Evaluate policy with IP restrictions
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "tool:invoke",
    "tool": "delete_production_database",
    "context": {
      "ip_address": "203.0.113.50",
      "network": "external"
    }
  }' | jq

# Denied if IP not in corporate network (10.0.0.0/8)
```

#### MFA Requirement

```bash
# Critical operations require MFA
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "tool:invoke",
    "tool": "delete_user_account",
    "context": {
      "mfa_verified": true,
      "mfa_method": "totp",
      "mfa_timestamp": "2025-11-22T10:29:55Z"
    }
  }' | jq

# Denied without MFA verification
```

### Policy Caching

Notice the cache headers in responses:

```bash
curl -v -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}' | jq

# Headers in response:
# X-Cache-Status: HIT | MISS
# X-Cache-TTL: 300

# To bypass cache for critical operations:
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Skip-Policy-Cache: true" \
  -H "Content-Type: application/json" \
  -d '{...}' | jq
```

---

## Session Management

SARK uses a dual-token system for secure session management.

### Understanding Sessions

```
┌─────────────────┐
│  Access Token   │  JWT, short-lived (60 minutes)
│  (In Memory)    │  Used for all API requests
└─────────────────┘

┌─────────────────┐
│ Refresh Token   │  Redis-backed, long-lived (7 days)
│ (Secure Cookie) │  Used to get new access tokens
└─────────────────┘
```

### Refresh Access Token

```bash
# When access token expires, use refresh token to get new one
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }" | jq

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",  # New access token
#   "token_type": "bearer",
#   "expires_in": 3600,
#   "refresh_token": "rt_xyz789..."  # New refresh token (if rotation enabled)
# }

# Update your access token
export ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

### View Active Sessions

```bash
# Get current session info
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

### Logout (Revoke Session)

```bash
# Revoke refresh token (logout)
curl -X POST http://localhost:8000/api/v1/auth/revoke \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }" | jq

# Response:
# {
#   "success": true,
#   "message": "Refresh token revoked successfully"
# }
```

### Session Limits

SARK enforces concurrent session limits:
- Default: 5 active sessions per user
- Oldest sessions automatically revoked when limit exceeded
- Configurable via `MAX_SESSIONS_PER_USER` environment variable

---

## API Keys

API keys are ideal for service-to-service authentication and automation.

### Create API Key

```bash
# Create a new API key
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Pipeline Key",
    "description": "For automated server registration in staging",
    "scopes": ["server:read", "server:write"],
    "rate_limit": 1000,
    "expires_in_days": 90,
    "environment": "live"
  }' | jq
```

### List API Keys

```bash
# List all API keys
curl -X GET http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Include revoked keys
curl -X GET "http://localhost:8000/api/auth/api-keys?include_revoked=true" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```

### Rotate API Key

```bash
# Rotate key (generates new credentials)
curl -X POST "http://localhost:8000/api/auth/api-keys/$KEY_ID/rotate" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Returns new key - update your systems immediately
```

### Revoke API Key

```bash
# Revoke key (can't be undone)
curl -X DELETE "http://localhost:8000/api/auth/api-keys/$KEY_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Returns: 204 No Content
```

---

## Rate Limiting

SARK implements tiered rate limiting to prevent abuse.

### Rate Limit Tiers

**Authenticated Users (JWT):**
- 5,000 requests/minute
- Burst: 100 requests
- Admin users: Unlimited (bypass enabled)

**API Keys:**
- Configurable per key (default: 1,000 requests/minute)
- Burst: 50 requests
- Set during key creation

**Unauthenticated (Public Endpoints):**
- 100 requests/minute per IP
- Burst: 20 requests

### Check Rate Limit Status

```bash
# Rate limit info included in response headers
curl -v -X GET http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Response headers:
# X-RateLimit-Limit: 5000
# X-RateLimit-Remaining: 4987
# X-RateLimit-Reset: 1638360000
```

### Handle Rate Limit Exceeded

```bash
# When limit exceeded (HTTP 429):
# {
#   "detail": "Rate limit exceeded. Try again in 45 seconds.",
#   "retry_after": 45
# }

# Response headers:
# X-RateLimit-Limit: 1000
# X-RateLimit-Remaining: 0
# X-RateLimit-Reset: 1638360000
# Retry-After: 45

# Wait and retry
sleep 45
curl -X GET http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## Monitoring & Observability

### Metrics Endpoint

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Key metrics:
# - http_requests_total{method="GET",endpoint="/api/v1/servers"}
# - http_request_duration_seconds{method="POST",endpoint="/api/v1/policy/evaluate"}
# - policy_cache_hits_total
# - policy_cache_misses_total
# - siem_events_forwarded_total{siem="splunk"}
```

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health | jq

# Liveness probe (K8s)
curl http://localhost:8000/health/live

# Readiness probe (K8s)
curl http://localhost:8000/health/ready | jq

# Detailed health with dependency status
curl http://localhost:8000/health/detailed | jq
```

### Audit Logs

```bash
# View recent audit events in TimescaleDB
docker compose exec timescaledb psql -U sark sark_audit

# Query policy decisions
sark_audit=# SELECT event_type, decision, user_email, tool_name, reason
             FROM audit_events
             WHERE event_type = 'policy_decision'
             ORDER BY timestamp DESC
             LIMIT 20;

# Query authentication events
sark_audit=# SELECT event_type, severity, user_email, auth_method
             FROM audit_events
             WHERE event_type IN ('authentication_success', 'authentication_failure')
             ORDER BY timestamp DESC
             LIMIT 20;
```

### Grafana Dashboards

```bash
# Access Grafana
open http://localhost:3000
# Login: admin / admin

# Pre-configured dashboards:
# 1. SARK Overview - API metrics, request rates, latencies
# 2. Policy Evaluation - Decision rates, cache hit rate, OPA latency
# 3. Session Management - Active sessions, token refresh rate
# 4. SIEM Integration - Events forwarded, success rate, retry stats
```

---

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

```bash
# Check service status
docker compose ps

# View logs
docker compose logs

# Common causes:
# - Port conflicts (8000, 5432, 6379, 8500, 8181)
# - Insufficient memory (need 8GB+)
# - Docker network issues

# Fix port conflicts
netstat -tuln | grep -E ':(8000|5432|6379|8500|8181)'
# Kill processes using these ports or change ports in docker-compose.yml

# Restart services
docker compose down
docker compose up -d
```

#### 2. Authentication Fails

```bash
# Check LDAP connectivity
docker compose exec api curl ldap://openldap:389

# View authentication logs
docker compose logs api | grep -i "auth"

# Test LDAP bind
docker compose exec api ldapsearch -x -H ldap://openldap:389 \
  -D "cn=admin,dc=example,dc=com" \
  -w admin \
  -b "dc=example,dc=com"
```

#### 3. Policy Evaluation Errors

```bash
# Check OPA service
curl http://localhost:8181/health

# Test OPA directly
curl -X POST http://localhost:8181/v1/data/mcp/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "test", "role": "developer"},
      "action": "tool:invoke",
      "tool": {"name": "test", "sensitivity_level": "low"}
    }
  }' | jq

# Validate policies
docker compose exec opa opa test /policies -v

# View OPA logs
docker compose logs opa
```

#### 4. Redis Connection Issues

```bash
# Check Redis
docker compose exec redis redis-cli ping
# Should respond: PONG

# Test Redis connection
docker compose exec redis redis-cli
127.0.0.1:6379> AUTH password
127.0.0.1:6379> PING
127.0.0.1:6379> INFO stats

# View session count
127.0.0.1:6379> KEYS "refresh_token:*" | wc -l
```

#### 5. Database Connection Errors

```bash
# Check PostgreSQL
docker compose exec postgres pg_isready -U sark

# Connect to database
docker compose exec postgres psql -U sark -d sark

# Check connections
sark=# SELECT count(*) FROM pg_stat_activity;

# Restart database if needed
docker compose restart postgres
```

#### 6. High Latency

```bash
# Check detailed health
curl http://localhost:8000/health/detailed | jq

# View metrics
curl http://localhost:8000/metrics | grep latency

# Check policy cache hit rate
curl http://localhost:8000/metrics | grep policy_cache

# Increase cache TTL if hit rate is low (edit .env)
POLICY_CACHE_TTL_HIGH=120  # Increase from 60
```

### Getting Help

1. **Check logs:** `docker compose logs -f api`
2. **Review health endpoints:** `/health/detailed`
3. **Check metrics:** `/metrics`
4. **Search documentation:** See [docs/](../docs/) directory
5. **Open an issue:** https://github.com/your-org/sark/issues

---

## Next Steps

### Explore Documentation

- **[API Reference](API_REFERENCE.md)** - Complete API endpoint documentation
- **[Architecture](ARCHITECTURE.md)** - System architecture and design
- **[Authentication Guide](AUTHENTICATION.md)** - Detailed auth methods
- **[Authorization Guide](AUTHORIZATION.md)** - OPA policy development
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment
- **[Operational Runbook](OPERATIONAL_RUNBOOK.md)** - Operations procedures
- **[Performance Tuning](PERFORMANCE_TUNING.md)** - Optimization guide
- **[Testing Strategy](TESTING_STRATEGY.md)** - Testing frameworks

### Production Deployment

Ready to deploy to production? See:
- [Deployment Guide](DEPLOYMENT.md) - Kubernetes, Helm, cloud providers
- [Operational Runbook](OPERATIONAL_RUNBOOK.md) - Day 2 operations
- [Performance Tuning](PERFORMANCE_TUNING.md) - Optimize for scale

### Development

Want to contribute or customize SARK?

```bash
# Install Python dependencies
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run with hot reload
uvicorn sark.api.main:app --reload

# Check code quality
black .
ruff check .
mypy src/
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for full development guide.

### Import Postman Collection

```bash
# Import collection into Postman
# File: postman/SARK_API.postman_collection.json

# Import environments:
# - postman/SARK_Local.postman_environment.json
# - postman/SARK_Staging.postman_environment.json
# - postman/SARK_Production.postman_environment.json

# See postman/README.md for usage instructions
```

---

## Clean Up

To stop and remove all services:

```bash
# Stop services (preserves data)
docker compose down

# Stop and remove all data (WARNING: irreversible!)
docker compose down -v

# Remove images
docker compose down --rmi all
```

---

**🎉 Congratulations!** You're now ready to govern MCP deployments at scale with SARK.

For questions or issues, please open a GitHub issue or contact the team.
