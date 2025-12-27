# SARK Gateway Integration - Frequently Asked Questions (FAQ)

**Version**: 1.1.0
**Last Updated**: November 2025
**Audience**: Developers, Operations Engineers, End Users

---

## Table of Contents

1. [Setup & Installation](#setup--installation)
2. [Usage & Operations](#usage--operations)
3. [Policies & Authorization](#policies--authorization)
4. [Performance & Scaling](#performance--scaling)
5. [Security & Authentication](#security--authentication)
6. [Integration & Compatibility](#integration--compatibility)
7. [Troubleshooting & Debugging](#troubleshooting--debugging)

---

## Setup & Installation

### Q1: How do I enable Gateway integration in SARK?

**This is one of the most common setup questions.**

**A:** Add the following to your `.env` file and restart SARK:

```bash
# Enable Gateway Integration
GATEWAY_ENABLED=true
GATEWAY_URL=http://gateway:8080
GATEWAY_API_KEY=your-api-key-here
GATEWAY_TIMEOUT_SECONDS=10.0
```

Then restart:
```bash
docker compose -f docker-compose.gateway.yml restart sark
```

Verify it's enabled:
```bash
curl http://localhost:8000/api/v1/version | jq '.features.gateway_integration'
# Should return: true
```

**📚 Learn more:** [Gateway Integration Plan](../../MCP_GATEWAY_INTEGRATION_PLAN.md)

---

### Q2: What are the minimum system requirements for Gateway integration?

**A:** The Gateway integration adds minimal overhead to SARK:

**Minimum Requirements:**
- **CPU**: +1 vCPU (total 3 vCPU recommended)
- **Memory**: +512 MB RAM (total 2 GB recommended)
- **Network**: 100 Mbps with <10ms latency to Gateway
- **Storage**: +5 GB for audit logs

**Recommended for Production:**
- **CPU**: 4-8 vCPUs
- **Memory**: 4-8 GB RAM
- **Network**: 1 Gbps with <5ms latency
- **Storage**: 50+ GB with SSD

**Why this matters:** Gateway integration performs authorization checks on every request, so adequate resources ensure <50ms authorization latency.

---

### Q3: Can I run SARK and Gateway on the same server?

**A:** Yes, but it's not recommended for production.

**Development/Testing:**
```yaml
# docker-compose.gateway.yml
services:
  sark:
    ports:
      - "8000:8000"

  gateway:
    ports:
      - "8080:8080"

  # They can share Redis, PostgreSQL, OPA
```

**Production:**
- Run SARK and Gateway on separate infrastructure
- Use service mesh (Istio, Linkerd) for secure communication
- Implement proper network isolation and firewalls

**Why separate?** Fault isolation, independent scaling, and security boundaries.

---

### Q4: How do I generate a Gateway API key?

**A:** Use the SARK CLI to generate a secure API key:

```bash
# Generate new Gateway API key
docker exec -it sark-app python -m sark.cli generate-api-key \
  --type gateway \
  --name "production-gateway" \
  --expires-days 365

# Output:
# API Key: gw_sk_live_abc123def456...
# Store this securely - it won't be shown again!
```

Store it in your `.env` file:
```bash
GATEWAY_API_KEY=gw_sk_live_abc123def456...
```

**Security tip:** Rotate API keys every 90-180 days and use different keys for dev/staging/prod.

---

### Q5: What happens if I deploy SARK without configuring Gateway integration?

**A:** SARK will work normally, but Gateway integration features will be disabled:

- ✅ **Still works**: All standard SARK features (auth, policies, audit)
- ❌ **Won't work**: Gateway authorization endpoints return 404
- ⚠️ **Warning**: Logs will show "Gateway integration disabled" messages

You can enable it anytime by adding configuration and restarting.

---

### Q6: Can I migrate existing SARK deployments to use Gateway integration?

**A:** Yes! Gateway integration is backward-compatible.

**Migration Steps:**

1. **Update configuration** (add Gateway variables to `.env`)
2. **Deploy OPA policies** for Gateway authorization
3. **Restart SARK** (zero-downtime with rolling restart)
4. **Verify health** (`/health/detailed` should show Gateway connectivity)
5. **Configure Gateway** to call SARK authorization endpoint
6. **Test authorization flow** with sample requests
7. **Monitor metrics** for the first 24 hours

**Rollback:** Simply set `GATEWAY_ENABLED=false` and restart.

**📚 Migration guide:** [OPERATIONS_RUNBOOK.md](../../OPERATIONS_RUNBOOK.md#migration-procedures)

---

### Q7: What OPA policies do I need for Gateway integration?

**A:** The minimum policy set includes:

```rego
# opa/policies/gateway_authorization.rego
package mcp.gateway

default allow := false

# Basic tool invocation
allow if {
    input.action == "gateway:tool:invoke"
    input.user.role in ["admin", "developer"]
    input.tool.sensitivity_level in ["low", "medium"]
}
```

**Pre-built policies** are included in `opa/policies/gateway_*.rego`.

**📚 Learn more:** [ADVANCED_OPA_POLICIES.md](../../ADVANCED_OPA_POLICIES.md)

---

### Q8: How do I test Gateway integration locally?

**A:** Use the included Docker Compose setup:

```bash
# 1. Start all services
docker compose -f docker-compose.gateway.yml up -d

# 2. Check health
curl http://localhost:8000/health/detailed | jq

# 3. Test authorization
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat test_token.txt)" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "test-server",
    "tool_name": "read-file"
  }'

# Expected: {"allow": true, "reason": "...", ...}
```

**📚 Testing guide:** [INTEGRATION_TESTING.md](../../INTEGRATION_TESTING.md)

---

### Q9: Do I need to modify my existing MCP servers?

**A:** No! MCP servers don't need any modifications.

**How it works:**
1. Gateway receives request from client
2. Gateway calls SARK for authorization
3. SARK evaluates policies and returns decision
4. Gateway forwards approved requests to MCP server
5. MCP server processes request normally

MCP servers are unaware of the authorization layer.

---

### Q10: Can I use Gateway integration with Kubernetes?

**A:** Yes! Kubernetes is fully supported.

**Quick deployment:**
```bash
# Apply Gateway-enabled SARK deployment
kubectl apply -f k8s/gateway-integration/

# Verify pods
kubectl get pods -n sark -l app=sark-gateway

# Check logs
kubectl logs -n sark -l app=sark-gateway --tail=100
```

**📚 Kubernetes guide:** [deployment/KUBERNETES.md](../../deployment/KUBERNETES.md)

---

### Q11: How do I upgrade SARK with Gateway integration enabled?

**A:** Use rolling updates to ensure zero downtime:

```bash
# 1. Pull latest image
docker compose -f docker-compose.gateway.yml pull sark

# 2. Update with zero downtime
docker compose -f docker-compose.gateway.yml up -d --no-deps --scale sark=2 sark

# 3. Wait for health check
sleep 30

# 4. Remove old container
docker compose -f docker-compose.gateway.yml up -d --no-deps --scale sark=1 sark

# 5. Verify
curl http://localhost:8000/api/v1/version | jq '.version'
```

**Kubernetes:** Use `kubectl rollout` for automated rolling updates.

---

## Usage & Operations

### Q12: How do I authorize a Gateway request?

**A:** Gateway calls SARK's authorization endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer ${USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "parameters": {
      "query": "SELECT * FROM users",
      "database": "production"
    }
  }'
```

**Response (allowed):**
```json
{
  "allow": true,
  "reason": "User has developer role with access to medium-sensitivity tools",
  "filtered_parameters": {
    "query": "SELECT * FROM users",
    "database": "production"
  },
  "audit_id": "aud_abc123",
  "cache_ttl": 60
}
```

**📚 API Reference:** [API_REFERENCE.md](../../API_REFERENCE.md#gateway-authorization)

---

### Q13: What actions can be authorized through Gateway integration?

**A:** SARK supports these Gateway actions:

| Action | Description | Example Use Case |
|--------|-------------|------------------|
| `gateway:tool:invoke` | Authorize tool execution | Execute database query |
| `gateway:tool:discover` | Authorize tool discovery | List available tools |
| `gateway:server:list` | Authorize server listing | View registered servers |
| `gateway:server:info` | Authorize server details | Get server metadata |
| `a2a:communicate` | Agent-to-agent communication | Agent requests capability from another agent |

Each action has specific policy rules in OPA.

---

### Q14: How do I view Gateway authorization audit logs?

**A:** Audit logs are stored in PostgreSQL and can be queried via API:

```bash
# Get recent Gateway authorization events
curl http://localhost:8000/api/v1/audit/events \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -G \
  --data-urlencode "event_type=gateway:tool:invoke" \
  --data-urlencode "limit=100" \
  | jq '.events[] | {timestamp, user, decision, tool}'
```

**Direct database query:**
```sql
SELECT
  timestamp,
  user_id,
  event_type,
  decision,
  metadata->>'server_name' as server,
  metadata->>'tool_name' as tool
FROM audit_events
WHERE event_type LIKE 'gateway:%'
ORDER BY timestamp DESC
LIMIT 100;
```

**📚 Audit guide:** [POLICY_AUDIT_TRAIL.md](../../POLICY_AUDIT_TRAIL.md)

---

### Q15: Can I override authorization decisions manually?

**A:** Not directly, but you can temporarily modify policies:

**Option 1: Emergency override policy**
```rego
# Add to OPA policies
allow if {
    input.user.id == "emergency-admin"
    input.metadata.override_reason != ""
}
```

**Option 2: Update user roles/permissions**
```bash
# Grant temporary admin access
curl -X PATCH http://localhost:8000/api/v1/users/user_123 \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"role": "admin"}'
```

**Best practice:** Use time-limited role assignments with audit logging.

---

### Q16: How do I handle Gateway failover scenarios?

**A:** SARK includes built-in resilience:

**Circuit Breaker:**
- After 5 consecutive Gateway failures, circuit opens
- Requests fast-fail for 30 seconds
- Half-open state tries 1 request after timeout
- Auto-recovery when Gateway is healthy

**Configuration:**
```bash
GATEWAY_CIRCUIT_BREAKER_ENABLED=true
GATEWAY_CIRCUIT_BREAKER_THRESHOLD=5
GATEWAY_CIRCUIT_BREAKER_TIMEOUT=30
```

**Monitoring:**
```bash
# Check circuit breaker status
curl http://localhost:8000/api/v1/gateway/health | jq '.circuit_breaker'
```

**📚 Reliability guide:** [OPERATIONS_RUNBOOK.md](../../OPERATIONS_RUNBOOK.md#failover-procedures)

---

### Q17: What metrics should I monitor for Gateway integration?

**A:** Key metrics to track:

**Authorization Performance:**
- `sark_gateway_authz_latency_seconds` (P50, P95, P99)
- `sark_gateway_authz_requests_total` (by decision: allow/deny)
- `sark_gateway_cache_hit_rate`

**Gateway Health:**
- `sark_gateway_connection_errors_total`
- `sark_gateway_timeout_errors_total`
- `sark_gateway_circuit_breaker_state`

**Grafana Dashboard:**
```bash
# Import pre-built dashboard
curl http://localhost:3000/api/dashboards/db \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d @dashboards/gateway-integration.json
```

**📚 Monitoring guide:** [MONITORING.md](../../MONITORING.md)

---

### Q18: How do I debug why a request was denied?

**A:** Enable detailed audit logging:

```bash
# 1. Check audit log for request
curl http://localhost:8000/api/v1/audit/events \
  -H "Authorization: Bearer ${TOKEN}" \
  -G \
  --data-urlencode "user_id=user_123" \
  --data-urlencode "decision=deny" \
  | jq '.events[0]'

# 2. Check OPA policy evaluation
docker exec -it opa opa eval \
  --data /policies \
  --input <(echo '{
    "action": "gateway:tool:invoke",
    "user": {"id": "user_123", "role": "viewer"},
    "tool": {"sensitivity_level": "high"}
  }') \
  'data.mcp.gateway.allow'

# 3. Enable verbose logging
export LOG_LEVEL=DEBUG
docker compose -f docker-compose.gateway.yml restart sark
```

**📚 Debug guide:** [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md#debug-mode-and-logging)

---

### Q19: Can I batch authorize multiple requests?

**A:** Not currently, but you can optimize with caching:

**Current approach (N requests):**
```bash
for tool in tool1 tool2 tool3; do
  curl -X POST http://localhost:8000/api/v1/gateway/authorize \
    -d "{\"action\": \"gateway:tool:invoke\", \"tool_name\": \"$tool\"}"
done
```

**Optimized (cache results):**
- First request: 50ms (policy evaluation)
- Subsequent requests: 5ms (cache hit)
- Cache TTL: 60-300 seconds (configurable)

**Future:** Batch authorization API is planned for v1.2.0.

---

### Q20: How do I rotate Gateway API keys?

**A:** Use the zero-downtime rotation procedure:

```bash
# 1. Generate new key
NEW_KEY=$(docker exec sark-app python -m sark.cli generate-api-key \
  --type gateway --name "gateway-prod-v2")

# 2. Configure Gateway to use both old and new keys (dual-key mode)
# Update Gateway config to accept both keys

# 3. Update SARK to return new key
export GATEWAY_API_KEY=$NEW_KEY

# 4. Restart SARK (rolling restart)
docker compose -f docker-compose.gateway.yml restart sark

# 5. After 24 hours, remove old key from Gateway
# Gateway now only accepts new key

# 6. Revoke old key in SARK
docker exec sark-app python -m sark.cli revoke-api-key --key OLD_KEY
```

**Automation:** Set up monthly rotation with monitoring alerts.

---

### Q21: What happens if OPA is unavailable?

**A:** SARK's behavior depends on configuration:

**Fail-closed (default, secure):**
```bash
OPA_FAIL_CLOSED=true  # All requests denied if OPA is down
```

**Fail-open (permissive, risky):**
```bash
OPA_FAIL_CLOSED=false  # Requests allowed if OPA is down
```

**Recommendation:** Always use fail-closed in production.

**Monitoring:**
```bash
# Alert when OPA is unhealthy
sark_opa_health_status == 0
```

---

## Policies & Authorization

### Q22: How do I write a custom Gateway authorization policy?

**A:** Create a new `.rego` file in `opa/policies/`:

```rego
# opa/policies/custom_gateway.rego
package mcp.gateway.custom

import future.keywords.if

# Allow data scientists to query analytics tools
allow if {
    input.action == "gateway:tool:invoke"
    "data-science" in input.user.teams
    input.server.name == "analytics-mcp"
    input.tool.sensitivity_level in ["low", "medium"]
}

# Deny critical database operations after hours
deny if {
    input.tool.name in ["drop_table", "delete_database"]
    not is_work_hours(input.context.timestamp)
}

is_work_hours(timestamp) if {
    hour := time.clock([timestamp, "UTC"])[0]
    hour >= 9
    hour < 17
}
```

**Test the policy:**
```bash
opa test opa/policies/custom_gateway_test.rego
```

**Deploy:**
```bash
# Reload OPA policies
curl -X POST http://localhost:8181/v1/policies/custom_gateway \
  --data-binary @opa/policies/custom_gateway.rego
```

**📚 Policy guide:** [ADVANCED_OPA_POLICIES.md](../../ADVANCED_OPA_POLICIES.md)

---

### Q23: What's the difference between SARK policies and Gateway policies?

**A:** They serve different purposes:

| Aspect | SARK Policies | Gateway Policies |
|--------|---------------|------------------|
| **Scope** | Direct SARK API access | Gateway-routed requests |
| **Location** | `mcp.allow` | `mcp.gateway.allow` |
| **Input** | SARK request context | Gateway request + metadata |
| **Use Case** | Tool registration, user management | Tool invocation via Gateway |

**Example:**
```rego
# SARK policy (direct access)
package mcp
allow if {
    input.action == "tool:invoke"
    input.user.role == "admin"
}

# Gateway policy (via Gateway)
package mcp.gateway
allow if {
    input.action == "gateway:tool:invoke"
    input.user.role == "admin"
}
```

Both policies can coexist and are evaluated independently.

---

### Q24: How do I grant a user access to specific Gateway servers?

**A:** Use team-based access control:

**1. Add user to team:**
```bash
curl -X POST http://localhost:8000/api/v1/teams/data-science/members \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"user_id": "user_123"}'
```

**2. Create policy for team:**
```rego
# Allow data-science team to access specific servers
allow if {
    input.action == "gateway:tool:invoke"
    "data-science" in input.user.teams
    input.server.name in ["analytics-mcp", "ml-mcp"]
}
```

**3. Verify access:**
```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer ${USER_TOKEN}" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "analytics-mcp"
  }'
# Should return: {"allow": true}
```

---

### Q25: Can I filter sensitive parameters in Gateway requests?

**A:** Yes! Use parameter filtering in OPA policies:

```rego
# Filter password from database connection
filtered_parameters := sanitized if {
    input.action == "gateway:tool:invoke"
    input.tool.name == "db_connect"
    sanitized := object.remove(input.parameters, ["password", "secret"])
}
```

**SARK returns filtered parameters:**
```json
{
  "allow": true,
  "filtered_parameters": {
    "host": "db.example.com",
    "database": "prod"
    // "password" removed
  }
}
```

Gateway uses `filtered_parameters` instead of original request.

**📚 Security guide:** [SECURITY_BEST_PRACTICES.md](../../SECURITY_BEST_PRACTICES.md)

---

### Q26: How do I implement time-based access restrictions?

**A:** Use OPA's time functions:

```rego
package mcp.gateway

import future.keywords.if

# Allow only during business hours
allow if {
    input.action == "gateway:tool:invoke"
    is_business_hours(time.now_ns())
}

is_business_hours(timestamp) if {
    hour := time.clock([timestamp, "UTC"])[0]
    weekday := time.weekday(timestamp)

    # Monday-Friday, 9 AM - 5 PM UTC
    weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    hour >= 9
    hour < 17
}
```

**Test:**
```bash
# During business hours
opa eval --data policies/ \
  'data.mcp.gateway.is_business_hours(time.now_ns())'
# Returns: true or false
```

---

### Q27: What are sensitivity levels and how do they work?

**A:** Sensitivity levels classify tools by risk:

| Level | Description | Examples | Default Access |
|-------|-------------|----------|----------------|
| **low** | Read-only, safe operations | List files, read logs | All authenticated users |
| **medium** | Write operations, limited scope | Create file, update config | Developers, admins |
| **high** | Sensitive data, system changes | Read database, restart service | Admins only |
| **critical** | Destructive, irreversible | Delete database, format disk | Explicit approval required |

**Policy example:**
```rego
allow if {
    input.user.role == "developer"
    input.tool.sensitivity_level in ["low", "medium"]
}

allow if {
    input.user.role == "admin"
    input.tool.sensitivity_level in ["low", "medium", "high"]
}

# Critical tools require explicit approval
allow if {
    input.tool.sensitivity_level == "critical"
    input.metadata.approval_id != ""
    is_approved(input.metadata.approval_id)
}
```

**📚 Classification guide:** [TOOL_SENSITIVITY_CLASSIFICATION.md](../../TOOL_SENSITIVITY_CLASSIFICATION.md)

---

### Q28: How do I handle A2A (agent-to-agent) authorization?

**A:** Use the dedicated A2A endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/gateway/authorize-a2a \
  -H "Authorization: Bearer ${AGENT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "source_agent_id": "agent-service-1",
    "target_agent_id": "agent-worker-2",
    "capability": "execute",
    "message_type": "request"
  }'
```

**Response:**
```json
{
  "allow": true,
  "reason": "Trusted service agent can execute on worker agents"
}
```

**A2A Policy:**
```rego
package mcp.gateway.a2a

allow if {
    input.source_agent.type == "service"
    input.target_agent.type == "worker"
    input.capability == "execute"
    input.source_agent.trust_level == "trusted"
}
```

**📚 A2A guide:** See [MCP_GATEWAY_INTEGRATION_PLAN.md](../../MCP_GATEWAY_INTEGRATION_PLAN.md#agent-to-agent-authorization)

---

### Q29: Can I test policies without deploying to production?

**A:** Yes! Use the OPA testing framework:

```rego
# opa/policies/gateway_test.rego
package mcp.gateway

test_developer_can_invoke_medium_tools if {
    allow with input as {
        "action": "gateway:tool:invoke",
        "user": {"id": "user_123", "role": "developer"},
        "tool": {"sensitivity_level": "medium"}
    }
}

test_viewer_cannot_invoke_high_tools if {
    not allow with input as {
        "action": "gateway:tool:invoke",
        "user": {"id": "user_456", "role": "viewer"},
        "tool": {"sensitivity_level": "high"}
    }
}
```

**Run tests:**
```bash
opa test opa/policies/ -v

# Output:
# PASS: 12/12
```

**📚 Testing guide:** [POLICY_PERFORMANCE_VALIDATION.md](../../POLICY_PERFORMANCE_VALIDATION.md)

---

### Q30: How do I implement rate limiting per user?

**A:** Use Redis-backed rate limiting:

```python
# Rate limiting is built into SARK
# Configure in .env:
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

**Per-user limits in OPA:**
```rego
allow if {
    input.action == "gateway:tool:invoke"
    not is_rate_limited(input.user.id)
}

is_rate_limited(user_id) := limited if {
    key := sprintf("rate_limit:%s", [user_id])
    count := redis.get(key)
    limited := count > 100  # Max 100 requests/hour
}
```

**Monitor:**
```bash
# Check rate limit status
curl http://localhost:8000/api/v1/users/user_123/rate-limit
```

---

### Q31: What happens when policies conflict?

**A:** OPA uses explicit precedence rules:

**Rule 1: Explicit deny wins**
```rego
deny if {
    input.tool.name == "dangerous_tool"
}

allow if {
    input.user.role == "admin"
}

# Result: Denied (explicit deny takes precedence)
```

**Rule 2: First matching rule (OR logic)**
```rego
allow if { input.user.role == "admin" }
allow if { input.user.role == "developer" }

# Either rule allows access
```

**Best practice:**
- Use `default allow := false` for fail-secure
- Write explicit deny rules for sensitive operations
- Test policies with `opa test`

---

## Performance & Scaling

### Q32: What is the expected latency for authorization requests?

**A:** Latency targets vary by cache state:

| Scenario | P50 | P95 | P99 |
|----------|-----|-----|-----|
| **Cache HIT** | <5ms | <10ms | <20ms |
| **Cache MISS** | <30ms | <50ms | <100ms |
| **Cold start** | <100ms | <200ms | <500ms |

**Actual benchmarks** (3-node SARK cluster):
```
Requests: 10,000
Duration: 60s
RPS: 166

Latency Distribution:
  P50: 8.2ms
  P75: 12.5ms
  P90: 28.3ms
  P95: 45.7ms
  P99: 89.4ms
```

**📚 Benchmarks:** [PERFORMANCE_REPORT.md](../../PERFORMANCE_REPORT.md)

---

### Q33: How do I optimize cache hit rates?

**A:** Increase cache TTL for stable policies:

```bash
# Default cache TTL by sensitivity
GATEWAY_CACHE_TTL_LOW=300      # 5 minutes
GATEWAY_CACHE_TTL_MEDIUM=180   # 3 minutes
GATEWAY_CACHE_TTL_HIGH=60      # 1 minute
GATEWAY_CACHE_TTL_CRITICAL=30  # 30 seconds
```

**Monitor cache performance:**
```bash
# Check cache hit rate
curl http://localhost:8000/api/v1/metrics | grep cache_hit_rate

# Expected: >90% for production workloads
```

**Cache invalidation:**
```bash
# Clear cache after policy update
curl -X POST http://localhost:8000/api/v1/cache/invalidate \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

**📚 Caching guide:** See [PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md)

---

### Q34: How many requests per second can SARK handle?

**A:** Throughput depends on deployment configuration:

| Configuration | RPS (P95 <50ms) | Notes |
|---------------|-----------------|-------|
| **Single instance** | ~500 RPS | Dev/testing only |
| **3-node cluster + Redis** | ~5,000 RPS | Production baseline |
| **10-node cluster + Redis** | ~20,000 RPS | High-traffic production |
| **Kubernetes HPA** | ~50,000+ RPS | Auto-scaling enabled |

**Bottlenecks:**
- OPA policy evaluation: ~2-10ms
- Redis cache lookup: ~1-3ms
- PostgreSQL audit log: ~5-15ms (async)

**Optimization:**
- Enable Redis caching (10x improvement)
- Use read replicas for PostgreSQL
- Scale OPA horizontally

---

### Q35: How do I scale SARK for high-traffic Gateway deployments?

**A:** Use horizontal scaling with load balancing:

**Docker Compose:**
```bash
# Scale SARK to 5 instances
docker compose -f docker-compose.gateway.yml up -d --scale sark=5

# Add NGINX load balancer
upstream sark_backend {
    least_conn;
    server sark-1:8000;
    server sark-2:8000;
    server sark-3:8000;
    server sark-4:8000;
    server sark-5:8000;
}
```

**Kubernetes HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sark-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: sark_gateway_authz_latency_p95
      target:
        type: AverageValue
        averageValue: "50m"  # 50ms
```

**📚 Scaling guide:** [PERFORMANCE_OPTIMIZATION.md](../../PERFORMANCE_OPTIMIZATION.md)

---

### Q36: Should I use Redis Cluster or Redis Sentinel?

**A:** Choose based on your requirements:

**Redis Cluster (recommended for >100K RPS):**
```yaml
# High throughput, automatic sharding
VALKEY_MODE=cluster
REDIS_CLUSTER_NODES=redis-1:6379,redis-2:6379,redis-3:6379
```

**Redis Sentinel (recommended for high availability):**
```yaml
# Automatic failover, simpler setup
VALKEY_MODE=sentinel
VALKEY_SENTINEL_MASTER=mymaster
REDIS_SENTINEL_NODES=sentinel-1:26379,sentinel-2:26379
```

**Single Redis (dev/small deployments):**
```yaml
VALKEY_MODE=standalone
VALKEY_URL=redis://localhost:6379
```

**Benchmark:** Cluster provides 3-5x throughput of single Redis.

---

### Q37: How do I reduce database load from audit logs?

**A:** Use these optimization strategies:

**1. Async audit logging (enabled by default):**
```python
# Audit writes don't block authorization responses
AUDIT_ASYNC_ENABLED=true
AUDIT_BATCH_SIZE=100
AUDIT_FLUSH_INTERVAL_SECONDS=5
```

**2. Use TimescaleDB for time-series data:**
```sql
-- Compress old audit logs
SELECT add_compression_policy('audit_events', INTERVAL '7 days');

-- Automatically archive old data
SELECT add_retention_policy('audit_events', INTERVAL '90 days');
```

**3. Separate read replica for queries:**
```bash
DATABASE_WRITE_URL=postgresql://sark:pass@primary:5432/sark
DATABASE_READ_URL=postgresql://sark:pass@replica:5432/sark
```

**Result:** 80% reduction in primary database load.

**📚 Database optimization:** [PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md#database-optimization)

---

### Q38: What are the performance implications of complex OPA policies?

**A:** Policy complexity affects latency:

| Policy Complexity | Evaluation Time | Example |
|-------------------|-----------------|---------|
| **Simple** (1-3 conditions) | <1ms | Role check only |
| **Medium** (5-10 conditions) | 2-5ms | Role + team + time check |
| **Complex** (15+ conditions) | 10-30ms | Multiple data lookups, nested rules |
| **Very Complex** (50+ conditions) | 50-100ms+ | Recursive rules, external data |

**Optimization tips:**
- Cache external data lookups
- Use indexed data structures
- Avoid deep recursion
- Profile with `opa eval --profile`

**Example profiling:**
```bash
opa eval --profile --data policies/ \
  'data.mcp.gateway.allow' \
  --input request.json \
  | jq '.profile'
```

---

### Q39: How do I monitor Gateway integration performance?

**A:** Use the built-in Prometheus metrics:

**Key metrics:**
```promql
# Authorization latency (P95)
histogram_quantile(0.95,
  rate(sark_gateway_authz_latency_seconds_bucket[5m])
)

# Cache hit rate
rate(sark_gateway_cache_hits_total[5m]) /
rate(sark_gateway_authz_requests_total[5m])

# Error rate
rate(sark_gateway_errors_total[5m])
```

**Grafana dashboard:**
```bash
# Import dashboard
curl -X POST http://localhost:3000/api/dashboards/import \
  -d @dashboards/gateway-performance.json
```

**Alerts:**
```yaml
# High latency alert
- alert: HighGatewayLatency
  expr: histogram_quantile(0.95, sark_gateway_authz_latency_seconds) > 0.1
  for: 5m
  annotations:
    summary: "Gateway authorization latency >100ms"
```

**📚 Monitoring:** [MONITORING.md](../../MONITORING.md)

---

### Q40: Can I use CDN caching for Gateway responses?

**A:** Authorization responses should NOT be cached by CDN:

**Why not:**
- Authorization decisions are user-specific
- Cache may serve stale decisions
- Security risk (user A sees user B's permissions)

**What you CAN cache:**
- Gateway server list (public data)
- Tool discovery results (with short TTL)
- Static documentation

**Use Redis for authorization caching** (user-aware, encrypted).

---

## Security & Authentication

### Q41: How are Gateway API keys secured?

**A:** Multi-layer security:

**Storage:**
- Keys stored as bcrypt hashes in PostgreSQL
- Plain-text keys shown only once at generation
- Encrypted at rest with database encryption

**Transmission:**
- TLS 1.3 required for all API calls
- Keys in `Authorization: Bearer` header (never in URL)

**Rotation:**
- 90-day expiration recommended
- Automatic rotation with overlap period
- Audit log tracks all key usage

**Monitoring:**
```bash
# Alert on suspicious key usage
sark_gateway_api_key_errors_total > 10
```

**📚 Security guide:** [SECURITY_HARDENING.md](../../SECURITY_HARDENING.md)

---

### Q42: What authentication methods are supported?

**A:** Multiple methods for different use cases:

| Method | Use Case | Configuration |
|--------|----------|---------------|
| **JWT (OIDC)** | User authentication | `AUTH_METHOD=oidc` |
| **API Keys** | Gateway service auth | `GATEWAY_API_KEY=...` |
| **SAML** | Enterprise SSO | `AUTH_METHOD=saml` |
| **LDAP** | Legacy systems | `AUTH_METHOD=ldap` |
| **mTLS** | Service-to-service | Mutual TLS certificates |

**Example OIDC config:**
```bash
AUTH_METHOD=oidc
OIDC_PROVIDER_URL=https://auth.example.com
OIDC_CLIENT_ID=sark-gateway
OIDC_CLIENT_SECRET=secret123
```

**📚 Auth setup:** [SAML_SETUP.md](../../SAML_SETUP.md), [LDAP_SETUP.md](../../LDAP_SETUP.md)

---

### Q43: How do I implement zero-trust security for Gateway integration?

**A:** Follow these principles:

**1. Verify every request:**
```rego
# No implicit trust
default allow := false

# Explicit verification
allow if {
    valid_token(input.token)
    authorized_user(input.user)
    allowed_action(input.action)
}
```

**2. Mutual TLS between services:**
```yaml
# Gateway → SARK: mTLS required
GATEWAY_MTLS_ENABLED=true
GATEWAY_CLIENT_CERT=/certs/gateway-client.pem
GATEWAY_CLIENT_KEY=/certs/gateway-client-key.pem
GATEWAY_CA_CERT=/certs/ca.pem
```

**3. Network segmentation:**
```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sark-gateway-ingress
spec:
  podSelector:
    matchLabels:
      app: sark
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: gateway
```

**4. Audit everything:**
```bash
AUDIT_ALL_REQUESTS=true
SIEM_ENABLED=true
```

**📚 Zero-trust guide:** [SECURITY_BEST_PRACTICES.md](../../SECURITY_BEST_PRACTICES.md#zero-trust-architecture)

---

### Q44: How are secrets managed in Gateway integration?

**A:** Use external secret management:

**Kubernetes Secrets (basic):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: sark-gateway-secret
type: Opaque
stringData:
  GATEWAY_API_KEY: "gw_sk_..."
```

**HashiCorp Vault (recommended):**
```bash
# Store in Vault
vault kv put secret/sark/gateway \
  api_key="gw_sk_..." \
  opa_secret="..."

# SARK reads from Vault
VAULT_ENABLED=true
VAULT_ADDR=https://vault.example.com
VAULT_PATH=secret/sark/gateway
```

**AWS Secrets Manager:**
```bash
AWS_SECRETS_ENABLED=true
AWS_SECRET_NAME=sark/gateway/prod
AWS_REGION=us-east-1
```

**Never:**
- Commit secrets to Git
- Log secrets
- Return secrets in API responses

---

### Q45: What security headers should be configured?

**A:** Essential security headers:

```python
# Configured in SARK API
SECURE_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

**Test headers:**
```bash
curl -I http://localhost:8000/api/v1/gateway/authorize | grep -E "^(Strict|X-|Content-Security)"
```

**Security scan:**
```bash
# Mozilla Observatory
https://observatory.mozilla.org/analyze/your-sark-domain.com
```

---

### Q46: How do I prevent replay attacks?

**A:** Use nonce and timestamp validation:

```rego
# OPA policy with replay prevention
allow if {
    input.action == "gateway:tool:invoke"

    # Validate timestamp (±5 minutes)
    timestamp_valid(input.metadata.timestamp)

    # Validate nonce (single use)
    nonce_fresh(input.metadata.nonce)

    # Standard authorization
    authorized_user(input.user)
}

timestamp_valid(ts) if {
    now := time.now_ns()
    diff := abs(now - ts)
    diff < 300000000000  # 5 minutes in nanoseconds
}
```

**Gateway implementation:**
```python
# Gateway adds metadata
request_metadata = {
    "timestamp": int(time.time() * 1e9),
    "nonce": secrets.token_urlsafe(32),
    "request_id": str(uuid.uuid4()),
}
```

---

### Q47: How are audit logs protected from tampering?

**A:** Multiple protection layers:

**1. Immutable database columns:**
```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    decision VARCHAR(10) NOT NULL,
    metadata JSONB,

    -- Immutable: INSERT only, no UPDATE/DELETE
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prevent updates
CREATE TRIGGER prevent_audit_update
BEFORE UPDATE ON audit_events
FOR EACH ROW
EXECUTE FUNCTION prevent_update();
```

**2. Cryptographic signatures:**
```python
# Each audit event is signed
audit_event = {
    "id": "aud_123",
    "timestamp": "2025-11-28T10:00:00Z",
    "event": "gateway:tool:invoke",
    "signature": hmac_sha256(event_data, secret_key)
}
```

**3. External SIEM forwarding:**
```bash
# Real-time copy to Splunk/Datadog
SIEM_ENABLED=true
SIEM_PROVIDER=splunk
SIEM_HEC_URL=https://splunk.example.com:8088
```

**4. Blockchain audit trail (optional):**
```bash
# Tamper-proof blockchain
BLOCKCHAIN_AUDIT_ENABLED=true
BLOCKCHAIN_PROVIDER=hyperledger
```

**Verification:**
```bash
# Verify audit log integrity
python -m sark.cli verify-audit-logs --start-date 2025-11-01
```

---

### Q48: What compliance standards does Gateway integration support?

**A:** SARK Gateway integration supports:

| Standard | Features | Documentation |
|----------|----------|---------------|
| **SOC 2** | Audit logs, access control, encryption | Compliance report available |
| **HIPAA** | PHI protection, audit trails, encryption at rest | [SECURITY_HARDENING.md](../../SECURITY_HARDENING.md) |
| **GDPR** | Data privacy, right to erasure, audit logs | [GDPR_COMPLIANCE.md](../../GDPR_COMPLIANCE.md) |
| **PCI-DSS** | Encryption, access controls, logging | Contact for questionnaire |
| **ISO 27001** | ISMS controls, risk management | [ISO_27001_CONTROLS.md](../../ISO_27001_CONTROLS.md) |

**Compliance features:**
- Full audit trail of all access
- Encryption in transit (TLS 1.3) and at rest
- Role-based access control (RBAC)
- Data retention policies
- Incident response procedures

---

### Q49: How do I implement IP allowlisting for Gateway?

**A:** Use network policies and OPA rules:

**OPA policy:**
```rego
package mcp.gateway

# Allow only from trusted IP ranges
allow if {
    input.action == "gateway:tool:invoke"
    ip_allowed(input.metadata.client_ip)
}

ip_allowed(ip) if {
    # Office network
    net.cidr_contains("10.0.0.0/8", ip)
}

ip_allowed(ip) if {
    # VPN endpoints
    ip in ["203.0.113.50", "203.0.113.51"]
}
```

**Kubernetes NetworkPolicy:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sark-ip-allowlist
spec:
  podSelector:
    matchLabels:
      app: sark
  ingress:
  - from:
    - ipBlock:
        cidr: 10.0.0.0/8
    - ipBlock:
        cidr: 203.0.113.0/24
```

---

### Q50: How do I audit who accessed sensitive data?

**A:** Query the audit log with filters:

```sql
-- All access to sensitive tools in the last 24 hours
SELECT
    timestamp,
    user_id,
    metadata->>'server_name' as server,
    metadata->>'tool_name' as tool,
    decision,
    metadata->>'sensitivity_level' as sensitivity
FROM audit_events
WHERE
    event_type = 'gateway:tool:invoke'
    AND metadata->>'sensitivity_level' IN ('high', 'critical')
    AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

**API query:**
```bash
curl http://localhost:8000/api/v1/audit/events \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -G \
  --data-urlencode "event_type=gateway:tool:invoke" \
  --data-urlencode "sensitivity_level=high,critical" \
  --data-urlencode "since=24h" \
  | jq '.events[] | {user: .user_id, tool: .metadata.tool_name, time: .timestamp}'
```

**Export for compliance:**
```bash
# Generate compliance report
python -m sark.cli generate-compliance-report \
  --start-date 2025-11-01 \
  --end-date 2025-11-30 \
  --format pdf \
  --output compliance-november-2025.pdf
```

---

## Integration & Compatibility

### Q51: Is Gateway integration compatible with existing MCP servers?

**A:** Yes, 100% compatible! No server modifications needed.

**Why it works:**
- Authorization happens at Gateway layer
- MCP servers receive standard MCP protocol requests
- SARK is transparent to servers

**Supported MCP versions:**
- MCP Protocol: v1.0.0+
- All transport types: stdio, SSE, HTTP

---

### Q52: Can I use Gateway integration with Claude Desktop?

**A:** Not directly. Claude Desktop connects to local MCP servers.

**Workaround:**
1. Run local Gateway instance
2. Configure Claude Desktop to connect to Gateway
3. Gateway routes through SARK for authorization

**Configuration:**
```json
{
  "mcpServers": {
    "gateway": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/gateway-client"],
      "env": {
        "GATEWAY_URL": "http://localhost:8080",
        "SARK_TOKEN": "your-token"
      }
    }
  }
}
```

**Better approach:** Use SARK for server-side MCP deployments.

---

### Q53: Does Gateway integration work with Kubernetes Ingress?

**A:** Yes, with proper configuration:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sark-gateway-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "30"
spec:
  tls:
  - hosts:
    - sark.example.com
    secretName: sark-tls
  rules:
  - host: sark.example.com
    http:
      paths:
      - path: /api/v1/gateway
        pathType: Prefix
        backend:
          service:
            name: sark-gateway
            port:
              number: 8000
```

**Test:**
```bash
curl https://sark.example.com/api/v1/gateway/health
```

---

## Troubleshooting & Debugging

### Q54: Why are my authorization requests timing out?

**Common causes and solutions in order of likelihood:**

1. **OPA slow/unavailable** → Check `docker logs opa`
2. **Database connection pool exhausted** → Increase pool size
3. **Redis connection issues** → Check `redis-cli ping`
4. **Network latency** → Measure with `curl -w "@curl-format.txt"`

**Quick diagnosis:**
```bash
curl -w "time_total: %{time_total}s\n" \
  -X POST http://localhost:8000/api/v1/gateway/authorize \
  -d '{"action": "gateway:tool:invoke"}'

# If >1s, check component latency:
curl http://localhost:8000/health/detailed | jq '.dependencies'
```

**📚 See:** [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md#request-timeouts)

---

### Q55: How do I enable debug logging?

**A:** Set log level to DEBUG:

```bash
# Environment variable
export LOG_LEVEL=DEBUG

# Restart SARK
docker compose -f docker-compose.gateway.yml restart sark

# View logs
docker compose logs -f sark | grep gateway
```

**Structured logging output:**
```json
{
  "timestamp": "2025-11-28T10:00:00Z",
  "level": "DEBUG",
  "logger": "sark.gateway.authorize",
  "message": "Evaluating authorization request",
  "user_id": "user_123",
  "action": "gateway:tool:invoke",
  "server": "postgres-mcp",
  "duration_ms": 45.2
}
```

**📚 Debug guide:** [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md#debug-mode-and-logging)

---

### Q56: Where can I find help and support?

**Documentation:**
- [Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md)
- [Operations Runbook](../../OPERATIONS_RUNBOOK.md)
- [API Reference](../../API_REFERENCE.md)

**Community:**
- GitHub Discussions: https://github.com/your-org/sark/discussions
- Slack Channel: #sark-support
- Stack Overflow: Tag `sark-gateway`

**Enterprise Support:**
- Email: support@example.com
- Support Portal: https://support.example.com
- SLA: 4-hour response for P1 issues

**Bug Reports:**
- GitHub Issues: https://github.com/your-org/sark/issues
- Use template: [Bug Report Template](./TROUBLESHOOTING_GUIDE.md#bug-report-template)

---

## Additional Resources

- **[TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)** - Comprehensive troubleshooting procedures
- **[ERROR_REFERENCE.md](./ERROR_REFERENCE.md)** - Complete error code catalog
- **[PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md)** - Performance optimization guide
- **[MCP_GATEWAY_INTEGRATION_PLAN.md](../../MCP_GATEWAY_INTEGRATION_PLAN.md)** - Integration architecture
- **[OPERATIONS_RUNBOOK.md](../../OPERATIONS_RUNBOOK.md)** - Operational procedures
- **[SECURITY_BEST_PRACTICES.md](../../SECURITY_BEST_PRACTICES.md)** - Security hardening

---

**Last Updated**: November 2025 | **Version**: 1.1.0
**Questions or feedback?** Open an issue or contact support@example.com
