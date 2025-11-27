# Documentation Engineer: Documentation & Deployment Guides

**Branch:** `feat/gateway-docs`
**Duration:** 7-9 days (parallel with engineering)
**Focus:** User docs, deployment guides, runbooks, examples
**Dependencies:** None (works from specs)

---

## Overview

Create comprehensive documentation for Gateway integration. Work from integration plan specs initially, then update with real implementation details as engineers complete work.

---

## Week 1: Core Documentation

### Day 1-2: API Documentation

**File:** `docs/gateway-integration/API_REFERENCE.md`

```markdown
# Gateway Integration API Reference

## Overview

SARK provides REST APIs for MCP Gateway authorization and management.

## Authentication

All endpoints require JWT authentication via Bearer token:

```bash
curl -H "Authorization: Bearer $TOKEN" ...
```

## Endpoints

### POST /api/v1/gateway/authorize

Authorize Gateway request before routing to MCP server.

**Request:**
```json
{
  "action": "gateway:tool:invoke",
  "server_name": "postgres-mcp",
  "tool_name": "execute_query",
  "parameters": {"query": "SELECT *"},
  "gateway_metadata": {"request_id": "req_123"}
}
```

**Response (Allow):**
```json
{
  "allow": true,
  "reason": "Allowed by policy",
  "filtered_parameters": {"query": "SELECT *"},
  "audit_id": "audit_789",
  "cache_ttl": 60
}
```

**Response (Deny):**
```json
{
  "allow": false,
  "reason": "Insufficient permissions",
  "cache_ttl": 0
}
```

[Continue for all endpoints...]
```

**Checklist:**
- [ ] All 5 Gateway endpoints documented
- [ ] Request/response schemas with examples
- [ ] Authentication requirements
- [ ] Error codes and messages
- [ ] Rate limiting details

---

**File:** `docs/gateway-integration/AUTHENTICATION.md`

Document Gateway API key setup, agent JWT format, trust levels.

---

### Day 3-4: Deployment Guides

**File:** `docs/gateway-integration/deployment/QUICKSTART.md`

```markdown
# Gateway Integration Quick Start (15 minutes)

## Prerequisites

- Docker and Docker Compose
- SARK deployed
- MCP Gateway Registry deployed

## Step 1: Configure Gateway Integration

Create `.env.gateway`:

```bash
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
GATEWAY_API_KEY=your_gateway_api_key
A2A_ENABLED=true
```

## Step 2: Update SARK Configuration

```bash
# Add Gateway settings to .env
cat .env.gateway >> .env
```

## Step 3: Restart SARK

```bash
docker compose restart sark
```

## Step 4: Verify Integration

```bash
# Test Gateway authorization endpoint
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"action":"gateway:tool:invoke","tool_name":"test"}'
```

Expected: `{"allow": true, ...}`

## Next Steps

- Configure OPA policies: See [Policy Configuration](../configuration/POLICY_CONFIGURATION.md)
- Deploy to Kubernetes: See [Kubernetes Deployment](KUBERNETES_DEPLOYMENT.md)
```

**Checklist:**
- [ ] 15-minute quickstart complete
- [ ] Docker Compose example
- [ ] Kubernetes deployment guide
- [ ] Production deployment guide

---

### Day 5-6: Configuration Guides

**Files:**
- `docs/gateway-integration/configuration/GATEWAY_CONFIGURATION.md`
- `docs/gateway-integration/configuration/POLICY_CONFIGURATION.md`
- `docs/gateway-integration/configuration/A2A_CONFIGURATION.md`

Cover:
- Environment variables reference
- Gateway URL/API key setup
- OPA policy authoring
- Agent trust level configuration
- Custom policy examples

---

### Day 7: Operational Runbooks

**File:** `docs/gateway-integration/runbooks/TROUBLESHOOTING.md`

```markdown
# Gateway Integration Troubleshooting

## Common Issues

### Issue: Gateway authorization failing with 503

**Symptoms:**
- Authorization requests return 503 Service Unavailable
- Logs show "Gateway client errors"

**Diagnosis:**
```bash
# Check Gateway connectivity
curl http://$GATEWAY_URL/health

# Check SARK logs
docker logs sark | grep gateway_client
```

**Resolution:**
1. Verify `GATEWAY_URL` is correct
2. Verify Gateway is running and healthy
3. Check network connectivity between SARK and Gateway
4. Verify `GATEWAY_API_KEY` is valid

### Issue: All authorization requests denied

**Symptoms:**
- All requests return `{"allow": false}`
- OPA policy appears correct

**Diagnosis:**
```bash
# Test OPA directly
curl -X POST http://opa:8181/v1/data/mcp/gateway/allow \
  -d '{"input": {...}}'
```

**Resolution:**
1. Check OPA policy is loaded
2. Verify policy bundle is up-to-date
3. Test policy with `opa test`
4. Check policy cache isn't stale

[Continue for 10+ common scenarios...]
```

**Checklist:**
- [ ] Troubleshooting guide (10+ scenarios)
- [ ] Incident response runbook
- [ ] Maintenance procedures

---

## Week 2: Examples & Advanced Guides

### Day 8: Examples

**File:** `examples/gateway-integration/docker-compose.gateway.yml`

```yaml
version: '3.8'

services:
  # SARK with Gateway integration
  sark:
    image: sark:latest
    environment:
      GATEWAY_ENABLED: "true"
      GATEWAY_URL: "http://mcp-gateway:8080"
      GATEWAY_API_KEY: "${GATEWAY_API_KEY}"
      A2A_ENABLED: "true"
    depends_on:
      - mcp-gateway
      - opa
      - postgres
      - redis

  # MCP Gateway (mock for example)
  mcp-gateway:
    image: mcp-gateway:latest
    ports:
      - "8080:8080"

  # OPA for policies
  opa:
    image: openpolicyagent/opa:latest
    command:
      - "run"
      - "--server"
      - "--bundle"
      - "/bundles/bundle.tar.gz"
    volumes:
      - ./opa/bundle:/bundles

  # Other services...
```

**Create:**
- [ ] docker-compose.gateway.yml
- [ ] Kubernetes manifests (`examples/gateway-integration/kubernetes/`)
- [ ] OPA policy examples
- [ ] Helper scripts (setup, test, generate-api-key)

---

### Day 9: Architecture & Guides

**Files:**
- `docs/gateway-integration/architecture/INTEGRATION_ARCHITECTURE.md`
- `docs/gateway-integration/architecture/SECURITY_ARCHITECTURE.md`
- `docs/gateway-integration/guides/DEVELOPER_GUIDE.md`
- `docs/gateway-integration/guides/OPERATOR_GUIDE.md`

**Include:**
- System architecture diagrams (Mermaid)
- Data flow diagrams
- Security layers and controls
- Developer best practices
- Operator procedures

---

### Day 10: Final Documentation

**File:** `docs/gateway-integration/MIGRATION_GUIDE.md`

How to migrate from standalone Gateway to Gateway+SARK.

**File:** `docs/gateway-integration/RELEASE_NOTES.md`

Document new features, breaking changes, upgrade instructions.

**Update:** `README.md`

Add Gateway integration section to main README.

---

## Delivery Checklist

- [ ] API documentation complete
- [ ] Deployment guides (quickstart, k8s, production)
- [ ] Configuration guides (Gateway, policies, A2A)
- [ ] Runbooks (troubleshooting, incidents, maintenance)
- [ ] Architecture documentation
- [ ] User guides (developer, operator)
- [ ] Examples (docker-compose, k8s, policies)
- [ ] Migration guide
- [ ] Release notes
- [ ] README updated
- [ ] All diagrams clear and professional
- [ ] Code examples tested
- [ ] PR created

---

## Documentation Standards

- Use clear, concise language
- Include code examples for all procedures
- Add diagrams where helpful (Mermaid preferred)
- Test all code examples
- Follow SARK documentation style
- Cross-reference related docs

Ready! 📚
