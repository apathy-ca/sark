# Gateway Integration OPA Policies

This directory contains example OPA (Open Policy Agent) policies for SARK Gateway integration.

## Policy Files

### `gateway.rego`
Main Gateway authorization policy controlling which users can invoke which tools on MCP servers.

**Features:**
- Role-based access control (admin, analyst, developer)
- Granular tool permissions
- SQL query filtering (prevent destructive operations)
- Parameter filtering (remove sensitive data)
- Audit decision reasons

### `a2a.rego`
Agent-to-Agent (A2A) authorization policy controlling inter-agent communication.

**Features:**
- Trust level based authorization (critical > high > medium > low)
- Capability-based authorization
- Workflow context authorization
- Delegation controls
- Rate limiting by trust level
- Time-based restrictions

## Testing Policies

### Test Gateway Policy

```bash
# Test admin access (should allow)
opa eval -d gateway.rego -i test-data/admin-query.json "data.mcp.gateway.allow"

# Test analyst destructive query (should deny)
opa eval -d gateway.rego -i test-data/analyst-drop.json "data.mcp.gateway.allow"
```

### Test A2A Policy

```bash
# Test high trust agent invoking medium trust agent (should allow)
opa eval -d a2a.rego -i test-data/a2a-high-to-medium.json "data.mcp.gateway.a2a.allow"

# Test low trust agent invoking high trust agent (should deny)
opa eval -d a2a.rego -i test-data/a2a-low-to-high.json "data.mcp.gateway.a2a.allow"
```

## Test Data Examples

### `test-data/admin-query.json`
```json
{
  "input": {
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_123",
      "email": "admin@example.com",
      "roles": ["admin"]
    },
    "parameters": {
      "query": "SELECT * FROM users"
    }
  }
}
```

### `test-data/analyst-drop.json`
```json
{
  "input": {
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_456",
      "email": "analyst@example.com",
      "roles": ["analyst"]
    },
    "parameters": {
      "query": "DROP TABLE users"
    }
  }
}
```

### `test-data/a2a-high-to-medium.json`
```json
{
  "input": {
    "action": "a2a:invoke",
    "source_agent": {
      "id": "agent_research",
      "name": "research-agent",
      "trust_level": "high",
      "capabilities": ["research", "database_access"]
    },
    "target_agent": {
      "id": "agent_db",
      "name": "database-agent",
      "trust_level": "medium",
      "capabilities": ["query", "analytics"]
    },
    "tool_name": "query_database"
  }
}
```

## Deploying Policies

### Docker Compose

```bash
# 1. Bundle policies
cd examples/gateway-integration/policies
tar -czf ../opa/bundle/bundle.tar.gz .

# 2. Restart OPA
docker compose -f docker-compose.gateway.yml restart opa
```

### Kubernetes

```bash
# Create ConfigMap from policies
kubectl create configmap opa-gateway-policies \
  --from-file=gateway.rego \
  --from-file=a2a.rego \
  -n sark

# Mount in OPA deployment
kubectl patch deployment opa -n sark -p '
spec:
  template:
    spec:
      containers:
      - name: opa
        volumeMounts:
        - name: policies
          mountPath: /policies
      volumes:
      - name: policies
        configMap:
          name: opa-gateway-policies
'

# Restart OPA
kubectl rollout restart deployment/opa -n sark
```

## Customizing Policies

### Add a New Role

```rego
# In gateway.rego

# Allow "operator" role to restart services
allow if {
    input.user.roles[_] == "operator"
    input.action == "gateway:tool:invoke"
    input.server_name == "kubernetes-mcp"
    input.tool_name == "restart_pod"
}
```

### Add a New Trust Level Rule

```rego
# In a2a.rego

# Allow "verified" agents (custom trust level)
allow if {
    input.action == "a2a:invoke"
    input.source_agent.trust_level == "verified"
    input.target_agent.trust_level in ["verified", "medium", "low"]
}
```

### Add Time-Based Restrictions

```rego
# Only allow sensitive operations during business hours
allow if {
    input.action == "gateway:tool:invoke"
    input.tool_name == "execute_mutation"
    current_hour := time.clock(time.now_ns())[0]
    current_hour >= 9
    current_hour < 17
}
```

## Policy Structure

### Decision Flow

```
1. Evaluate `allow` rules
   └─> If any `allow` rule matches, authorization is granted

2. Evaluate `deny` rules
   └─> If any `deny` rule matches, authorization is denied
   └─> `deny` rules override `allow` rules

3. Collect `reason` for audit logging
   └─> Explain why authorization was granted or denied

4. Determine `cache_ttl`
   └─> How long can this decision be cached

5. (Optional) Apply `filtered_parameters`
   └─> Remove sensitive data from parameters
```

### Variables

| Variable | Type | Description |
|----------|------|-------------|
| `allow` | boolean | Authorization decision (true/false) |
| `deny` | set[string] | Set of denial reasons |
| `reason` | string | Human-readable reason for decision |
| `cache_ttl` | integer | Cache TTL in seconds (0 = no cache) |
| `filtered_parameters` | object | Filtered parameters (gateway policy only) |
| `max_delegation_depth_result` | integer | Max delegation depth (A2A policy only) |

## Best Practices

### 1. Default Deny
Always start with `default allow := false` to ensure secure-by-default behavior.

### 2. Explicit Denies
Use `deny` rules for critical security controls that should override any `allow` rule.

### 3. Audit Logging
Always provide a clear `reason` for both allow and deny decisions.

### 4. Caching Strategy
- Cache positive decisions for frequently-used paths
- Do not cache negative decisions (security posture may change)

### 5. Testing
Test policies with both positive and negative test cases before deploying.

```bash
# Run all policy tests
opa test gateway.rego a2a.rego
```

### 6. Versioning
Version your policies and track changes in git.

```bash
git add gateway.rego
git commit -m "Add operator role for service restarts"
```

## Monitoring Policy Decisions

### Prometheus Metrics

```promql
# Total authorization decisions
sark_gateway_authorization_requests_total{decision="allow|deny"}

# Decisions by policy
sark_gateway_authorization_requests_total{policy="gateway|a2a"}

# Policy evaluation duration
sark_opa_policy_evaluation_duration_seconds
```

### Grafana Dashboard

Query for policy decision rate:

```promql
rate(sark_gateway_authorization_requests_total[5m])
```

## Troubleshooting

### Issue: All requests denied

**Check:** Verify policy is loaded in OPA
```bash
curl http://localhost:8181/v1/policies
```

**Fix:** Reload policy bundle
```bash
tar -czf bundle.tar.gz gateway.rego a2a.rego
docker exec -it opa curl -X PUT http://localhost:8181/v1/bundles/bundle \
  --data-binary @/bundles/bundle.tar.gz
```

### Issue: Policy syntax error

**Check:** Validate policy syntax
```bash
opa check gateway.rego
```

**Fix:** Correct syntax errors and redeploy

### Issue: Unexpected allow/deny

**Debug:** Use OPA REPL to debug policy evaluation
```bash
opa run gateway.rego

# In REPL:
> data.mcp.gateway.allow with input as {...}
```

## Resources

- **OPA Documentation:** https://www.openpolicyagent.org/docs/latest/
- **Policy Language:** https://www.openpolicyagent.org/docs/latest/policy-language/
- **SARK Policy Guide:** ../../docs/gateway-integration/configuration/POLICY_CONFIGURATION.md

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/sark/issues
- Documentation: https://docs.sark.io/gateway-integration/policies
