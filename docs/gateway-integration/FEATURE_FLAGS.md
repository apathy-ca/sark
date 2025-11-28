# Gateway Integration Feature Flags

**Version:** 1.1.0
**Status:** Production Ready
**Last Updated:** 2025

---

## Overview

Gateway integration in SARK v1.1.0 is **opt-in** and controlled by feature flags. This ensures zero impact on existing v1.0.0 deployments and allows gradual rollout of new capabilities.

**Key Principles:**
- Gateway features are **disabled by default**
- Zero performance impact when disabled
- Backwards compatible with v1.0.0
- Granular control over feature enablement

---

## Table of Contents

- [Feature Flags](#feature-flags)
- [Gradual Rollout Strategy](#gradual-rollout-strategy)
- [Runtime Behavior](#runtime-behavior)
- [Monitoring](#monitoring)
- [Best Practices](#best-practices)

---

## Feature Flags

### `GATEWAY_ENABLED`

**Default:** `false`

**Description:** Master toggle for Gateway integration.

#### When Disabled (Default - v1.0.0 Behavior)

- ✅ Zero performance impact
- ✅ Zero memory overhead
- ✅ Gateway endpoints return `503 Service Unavailable`
- ✅ No Gateway client initialization
- ✅ No Gateway audit logging
- ✅ Behaves identically to v1.0.0

#### When Enabled

- ✅ Gateway client initialized
- ✅ Gateway endpoints active (`/api/v1/gateway/*`)
- ✅ Authorization flow enabled
- ✅ Audit logging active
- ⚠️ Requires additional configuration (`GATEWAY_URL`, `GATEWAY_API_KEY`)

#### Configuration

```bash
# Disable (default - v1.0.0 behavior)
GATEWAY_ENABLED=false

# Enable Gateway integration
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
GATEWAY_API_KEY=sark_gw_1234567890abcdef
```

#### Validation

```bash
# Check if Gateway is enabled
curl http://localhost:8000/api/v1/version

# Output:
{
  "version": "1.1.0",
  "features": {
    "gateway_integration": true,  # or false
    "a2a_authorization": false
  }
}
```

---

### `A2A_ENABLED`

**Default:** `false`

**Description:** Enable Agent-to-Agent authorization.

**Requires:** `GATEWAY_ENABLED=true`

#### When Disabled (Default)

- ✅ A2A endpoints return `503 Service Unavailable`
- ✅ No A2A policy evaluation
- ✅ No A2A audit logging

#### When Enabled

- ✅ A2A authorization endpoint active (`/api/v1/gateway/authorize-a2a`)
- ✅ A2A policy evaluation
- ✅ Agent trust level enforcement
- ✅ A2A audit logging

#### Configuration

```bash
# Enable A2A authorization (requires GATEWAY_ENABLED=true)
GATEWAY_ENABLED=true
A2A_ENABLED=true
```

#### Validation

```bash
# Test A2A endpoint
curl -X POST http://localhost:8000/api/v1/gateway/authorize-a2a \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -d '{...}'

# If A2A is disabled:
{
  "error": {
    "code": "A2A_NOT_ENABLED",
    "message": "Agent-to-Agent authorization not enabled. Set A2A_ENABLED=true to enable."
  }
}
```

---

### Additional Configuration Flags

#### `GATEWAY_AUDIT_ENABLED`

**Default:** `true` (when `GATEWAY_ENABLED=true`)

**Description:** Enable Gateway audit logging.

```bash
# Disable audit logging (not recommended for production)
GATEWAY_AUDIT_ENABLED=false
```

#### `GATEWAY_CACHE_ENABLED`

**Default:** `true` (when `GATEWAY_ENABLED=true`)

**Description:** Enable caching of authorization decisions.

```bash
# Disable caching (reduced performance)
GATEWAY_CACHE_ENABLED=false
```

#### `GATEWAY_METRICS_ENABLED`

**Default:** `true` (when `GATEWAY_ENABLED=true`)

**Description:** Enable Prometheus metrics for Gateway operations.

```bash
# Disable metrics collection
GATEWAY_METRICS_ENABLED=false
```

---

## Gradual Rollout Strategy

### Phase 1: Upgrade to v1.1.0 (Gateway Disabled)

**Objective:** Verify backwards compatibility

**Duration:** 1-2 days

**Steps:**

```bash
# 1. Backup database
./scripts/backup-database.sh

# 2. Pull v1.1.0 image
docker pull sark:1.1.0

# 3. Run database migrations
docker run --rm sark:1.1.0 alembic upgrade head

# 4. Ensure Gateway is disabled (default)
echo "GATEWAY_ENABLED=false" >> .env

# 5. Restart SARK
docker compose up -d sark

# 6. Verify v1.0.0 behavior maintained
curl http://localhost:8000/api/v1/version
# Should show: gateway_integration: false

# 7. Run smoke tests
./scripts/smoke-test.sh

# 8. Monitor metrics for 24-48 hours
# - Error rate should be identical to v1.0.0
# - Latency should be identical to v1.0.0
# - Resource usage should be identical to v1.0.0
```

**Success Criteria:**
- ✅ All smoke tests pass
- ✅ Zero increase in error rate
- ✅ Zero increase in latency
- ✅ Zero increase in resource usage

---

### Phase 2: Enable Gateway on Single Instance (Staging)

**Objective:** Validate Gateway integration works

**Duration:** 2-3 days

**Steps:**

```bash
# 1. Deploy MCP Gateway (if not already deployed)
docker compose -f docker-compose.gateway.yml up -d

# 2. Generate SARK Gateway API key
docker exec -it sark python -m sark.cli.generate_api_key \
  --name "MCP Gateway Staging" \
  --type gateway \
  --permissions "gateway:*"

# Save output: sark_gw_...

# 3. Configure Gateway integration
cat >> .env << EOF
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
GATEWAY_API_KEY=sark_gw_1234567890abcdef
A2A_ENABLED=false
EOF

# 4. Restart SARK
docker compose restart sark

# 5. Verify Gateway is enabled
curl http://localhost:8000/api/v1/version
# Should show: gateway_integration: true

# 6. Test Gateway authorization endpoint
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "test-server",
    "tool_name": "test-tool",
    "user": {"id": "user_123", "email": "test@example.com", "roles": ["admin"]}
  }'

# Expected: {"allow": true, ...}

# 7. Monitor metrics
curl http://localhost:9090/metrics | grep gateway

# Key metrics:
# - sark_gateway_authorization_requests_total
# - sark_gateway_authorization_duration_seconds
# - sark_gateway_client_errors_total
```

**Success Criteria:**
- ✅ Gateway endpoints return `200 OK`
- ✅ Authorization decisions are correct
- ✅ Audit logs are generated
- ✅ Metrics are collected
- ✅ P95 latency < 50ms

---

### Phase 3: Enable Gateway on Production (Canary)

**Objective:** Gradual production rollout

**Duration:** 3-5 days

**Steps:**

#### Day 1: 10% Canary

```bash
# 1. Enable Gateway on 10% of production instances
# Update deployment with feature flag for canary group
kubectl set env deployment/sark GATEWAY_ENABLED=true -n sark-prod

# 2. Monitor for 24 hours
# - Error rate
# - Latency (P50, P95, P99)
# - Resource usage (CPU, memory)
# - Gateway-specific metrics
```

#### Day 2-3: 50% Rollout

```bash
# If canary is stable, expand to 50%
kubectl scale deployment/sark --replicas=10 -n sark-prod
kubectl set env deployment/sark GATEWAY_ENABLED=true -n sark-prod
```

#### Day 4-5: 100% Rollout

```bash
# If 50% is stable, expand to 100%
kubectl set env deployment/sark GATEWAY_ENABLED=true -n sark-prod
kubectl rollout status deployment/sark -n sark-prod
```

**Rollback Plan:**

```bash
# If issues occur, immediately disable Gateway
kubectl set env deployment/sark GATEWAY_ENABLED=false -n sark-prod
kubectl rollout restart deployment/sark -n sark-prod

# Or full rollback to v1.0.0
kubectl set image deployment/sark sark=sark:1.0.0 -n sark-prod
```

---

### Phase 4: Enable A2A Authorization (Optional)

**Objective:** Enable Agent-to-Agent authorization

**Duration:** 2-3 days

**Prerequisites:**
- ✅ Gateway integration stable in production
- ✅ A2A policies configured
- ✅ Agent tokens generated

**Steps:**

```bash
# 1. Test A2A in staging
echo "A2A_ENABLED=true" >> .env
docker compose restart sark

# 2. Test A2A authorization
curl -X POST http://localhost:8000/api/v1/gateway/authorize-a2a \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -d '{...}'

# 3. If stable, enable in production (gradual)
kubectl set env deployment/sark A2A_ENABLED=true -n sark-prod
```

---

## Runtime Behavior

### Feature Flag Checks

SARK performs runtime checks to skip disabled features:

```python
# Example: Gateway client initialization
from sark.config import get_settings

settings = get_settings()

if not settings.gateway_enabled:
    logger.info("Gateway integration disabled, skipping initialization")
    return None  # Zero overhead

# Only initialize if enabled
gateway_client = GatewayClient(
    url=settings.gateway_url,
    api_key=settings.gateway_api_key
)
```

### Endpoint Behavior

When features are disabled, endpoints return `503 Service Unavailable`:

```bash
# Gateway disabled
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "error": {
    "code": "GATEWAY_NOT_ENABLED",
    "message": "Gateway integration not enabled. Set GATEWAY_ENABLED=true to enable.",
    "details": {
      "feature_flag": "GATEWAY_ENABLED",
      "current_value": false,
      "documentation": "https://docs.sark.io/gateway-integration/QUICKSTART"
    }
  }
}
# HTTP Status: 503
```

---

## Monitoring

### Key Metrics

#### Gateway Enabled/Disabled Status

```promql
# Gauge: 1 if enabled, 0 if disabled
sark_gateway_enabled
```

#### Gateway Request Metrics (Only When Enabled)

```promql
# Counter: Total authorization requests
sark_gateway_authorization_requests_total{decision="allow|deny"}

# Histogram: Authorization latency
sark_gateway_authorization_duration_seconds

# Counter: Gateway client errors
sark_gateway_client_errors_total{error_type="timeout|connection|auth"}
```

#### A2A Metrics (Only When A2A_ENABLED=true)

```promql
# Counter: A2A authorization requests
sark_a2a_authorization_requests_total{decision="allow|deny"}

# Counter: A2A requests by trust level
sark_a2a_requests_by_trust_level{trust_level="low|medium|high|critical"}
```

### Grafana Dashboard

**Panel: Feature Status**

```json
{
  "title": "Gateway Integration Status",
  "targets": [
    {
      "expr": "sark_gateway_enabled",
      "legendFormat": "Gateway Enabled"
    },
    {
      "expr": "sark_a2a_enabled",
      "legendFormat": "A2A Enabled"
    }
  ]
}
```

When features are disabled, the panel shows: **"Feature Disabled"**

---

## Best Practices

### 1. Always Test with Feature Disabled First

```bash
# After upgrading to v1.1.0
GATEWAY_ENABLED=false  # Test v1.0.0 compatibility first
```

### 2. Enable Features Gradually

```bash
# Bad: Enable everything at once
GATEWAY_ENABLED=true
A2A_ENABLED=true
GATEWAY_CACHE_ENABLED=true

# Good: Enable one feature at a time
GATEWAY_ENABLED=true  # Test for 48 hours
# Then:
A2A_ENABLED=true      # Test for 48 hours
```

### 3. Monitor Feature-Specific Metrics

```bash
# Set up alerts for Gateway-specific errors
sark_gateway_client_errors_total > 10
```

### 4. Document Feature Flag Changes

```bash
# Git commit message
git commit -m "Enable Gateway integration in production

- Set GATEWAY_ENABLED=true
- Configured GATEWAY_URL=http://mcp-gateway:8080
- Generated API key: gw_key_abc123
- Tested authorization endpoint: OK
- Monitored for 48 hours: no issues
"
```

### 5. Use Configuration Management

```yaml
# Terraform/Ansible/Helm
sark:
  features:
    gateway_enabled: true
    a2a_enabled: false
  gateway:
    url: "http://mcp-gateway:8080"
    api_key: "{{ vault_sark_gateway_api_key }}"
```

---

## Troubleshooting

### Issue: Features Not Enabling

**Symptoms:**
- Set `GATEWAY_ENABLED=true` but `curl .../version` shows `false`

**Diagnosis:**
```bash
# Check environment variables
docker exec -it sark env | grep GATEWAY

# Check config file
docker exec -it sark cat /etc/sark/config.yaml
```

**Resolution:**
```bash
# Restart SARK after changing feature flags
docker compose restart sark
```

### Issue: Unexpected 503 Errors

**Symptoms:**
- Gateway endpoints return `503 Service Unavailable`

**Diagnosis:**
```bash
# Verify feature is enabled
curl http://localhost:8000/api/v1/version | jq '.features'
```

**Resolution:**
```bash
# Enable the feature
echo "GATEWAY_ENABLED=true" >> .env
docker compose restart sark
```

---

## Next Steps

- **Quick Start:** See [deployment/QUICKSTART.md](./deployment/QUICKSTART.md)
- **Migration Guide:** See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
- **Configuration:** See [configuration/GATEWAY_CONFIGURATION.md](./configuration/GATEWAY_CONFIGURATION.md)

---

**Feature Flags Documentation Version:** 1.1.0
**Last Updated:** 2025
