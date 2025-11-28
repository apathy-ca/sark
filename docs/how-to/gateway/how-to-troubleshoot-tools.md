# How to Troubleshoot MCP Tools

This guide provides systematic approaches to diagnose and fix common issues with MCP tool invocations through the SARK Gateway.

## Before You Begin

**Prerequisites:**
- Access to gateway logs and metrics
- Basic understanding of MCP protocol
- kubectl/docker access for container logs
- Familiarity with your authentication mechanism
- Network diagnostic tools (curl, netcat, nslookup)

**What You'll Learn:**
- Diagnose common tool invocation errors
- Debug authentication failures step-by-step
- Use decision flowcharts for policy denials
- Identify and fix performance issues
- Debug network connectivity problems
- Resolve timeout issues

## Quick Diagnostic Checklist

When a tool invocation fails, check these items in order:

```markdown
Tool Invocation Troubleshooting Checklist

□ Is the gateway running and healthy?
□ Is the MCP server registered and healthy?
□ Is the tool listed in discovery?
□ Does authentication work for other requests?
□ Are policies allowing the request?
□ Is the network path clear?
□ Are there any timeout issues?
□ Check gateway logs for errors
□ Check MCP server logs for errors
□ Verify input parameters match schema
```

## Common Tool Invocation Errors

### Error 1: Tool Not Found

**Symptom:**
```json
{
  "error": "tool_not_found",
  "message": "Tool 'analyze_data' not found",
  "status_code": 404
}
```

**Diagnosis Steps:**

**Step 1:** Check if tool exists in discovery:

```bash
curl http://gateway.example.com/api/v1/tools \
  -H "Authorization: Bearer ${TOKEN}" \
  | jq '.tools[] | select(.name=="analyze_data")'
```

**Expected Output (if tool exists):**
```json
{
  "name": "analyze_data",
  "server_id": "data-server",
  "description": "Analyzes dataset",
  "input_schema": {...}
}
```

**If empty:** Tool is not registered.

**Step 2:** Check server registration:

```bash
sark-cli server list | grep data-server
```

**Expected Output:**
```
data-server    Data Analysis Server    1.0.0    active    3
```

**If not found:** Server is not registered.

**Step 3:** Check tool on MCP server directly:

```bash
curl http://mcp-server.example.com:8080/mcp/tools
```

**Expected Output:**
```json
{
  "tools": [
    {
      "name": "analyze_data",
      "description": "Analyzes dataset"
    }
  ]
}
```

**Fixes:**

**Fix 1:** If server not registered, register it:
```bash
sark-cli server register \
  --server-id data-server \
  --endpoint http://mcp-server.example.com:8080/mcp
```

**Fix 2:** If tool not in MCP server response, check server implementation:
```bash
# View server logs
kubectl logs deployment/mcp-server -n mcp-servers | grep "tool registration"
```

**Fix 3:** If tool name mismatch, use exact name from discovery:
```bash
# Wrong
{"tool_name": "analyze_data"}

# Correct (check discovery for exact name)
{"tool_name": "analyze_dataset"}
```

**Fix 4:** Force gateway to refresh tool cache:
```bash
curl -X POST http://gateway.example.com/api/v1/servers/data-server/refresh \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

### Error 2: Invalid Arguments

**Symptom:**
```json
{
  "error": "invalid_arguments",
  "message": "Arguments validation failed",
  "validation_errors": [
    {
      "field": "dataset",
      "error": "required field missing"
    },
    {
      "field": "threshold",
      "error": "must be a number between 0 and 1"
    }
  ],
  "status_code": 400
}
```

**Diagnosis Steps:**

**Step 1:** Get tool's input schema:

```bash
curl http://gateway.example.com/api/v1/tools/analyze_data/schema \
  -H "Authorization: Bearer ${TOKEN}" \
  | jq '.inputSchema'
```

**Expected Output:**
```json
{
  "type": "object",
  "required": ["dataset"],
  "properties": {
    "dataset": {
      "type": "array",
      "description": "Array of data points"
    },
    "threshold": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Analysis threshold"
    }
  }
}
```

**Step 2:** Validate your request payload:

```bash
# Save your request
cat > request.json <<EOF
{
  "server_id": "data-server",
  "tool_name": "analyze_data",
  "arguments": {
    "threshold": 1.5
  }
}
EOF

# Validate against schema
sark-cli validate-request request.json
```

**Expected Output:**
```
Validation failed:
  ✗ Missing required field: dataset
  ✗ Field 'threshold' value 1.5 exceeds maximum of 1
```

**Fixes:**

**Fix 1:** Add missing required fields:
```json
{
  "server_id": "data-server",
  "tool_name": "analyze_data",
  "arguments": {
    "dataset": [1, 2, 3, 4, 5],
    "threshold": 0.8
  }
}
```

**Fix 2:** Fix data types:
```json
// Wrong
{"threshold": "0.8"}  // String instead of number

// Correct
{"threshold": 0.8}    // Number
```

**Fix 3:** Use schema defaults when available:
```bash
# Get schema with defaults
curl http://gateway.example.com/api/v1/tools/analyze_data/schema?include_defaults=true
```

### Error 3: Server Unavailable

**Symptom:**
```json
{
  "error": "server_unavailable",
  "message": "MCP server 'data-server' is not reachable",
  "details": {
    "server_id": "data-server",
    "last_health_check": "2024-01-15T14:30:00Z",
    "health_status": "unhealthy"
  },
  "status_code": 503
}
```

**Diagnosis Steps:**

**Step 1:** Check server health status:

```bash
sark-cli server health data-server
```

**Expected Output (unhealthy):**
```
Server: data-server
Status: unhealthy
Last Check: 2024-01-15T14:30:00Z
Consecutive Failures: 5
Error: Connection timeout
```

**Step 2:** Test direct connectivity:

```bash
# From gateway pod/container
kubectl exec -it deployment/sark-gateway -n sark-system -- \
  curl -v http://mcp-server.example.com:8080/health
```

**Possible Outputs:**

**Connection refused:**
```
* connect to mcp-server.example.com port 8080 failed: Connection refused
```
**Meaning:** Server not running or port not open.

**Timeout:**
```
* Connection timed out after 5001 milliseconds
```
**Meaning:** Network issue or firewall blocking.

**DNS error:**
```
* Could not resolve host: mcp-server.example.com
```
**Meaning:** DNS resolution failure.

**Step 3:** Check server logs:

```bash
kubectl logs deployment/mcp-server -n mcp-servers --tail=50
```

Look for:
- Crash/panic messages
- Port binding errors
- Database connection issues

**Fixes:**

**Fix 1:** If server is down, restart it:
```bash
kubectl rollout restart deployment/mcp-server -n mcp-servers
```

**Fix 2:** If network issue, check firewall rules:
```bash
# Test from gateway node
curl http://mcp-server.example.com:8080/health

# Check Kubernetes network policies
kubectl get networkpolicies -n mcp-servers
```

**Fix 3:** If DNS issue, verify service:
```bash
kubectl get svc -n mcp-servers | grep mcp-server
nslookup mcp-server.mcp-servers.svc.cluster.local
```

**Fix 4:** Adjust health check settings:
```bash
sark-cli server update data-server \
  --health-check-timeout 10s \
  --health-check-unhealthy-threshold 5
```

### Error 4: Execution Timeout

**Symptom:**
```json
{
  "error": "execution_timeout",
  "message": "Tool execution exceeded timeout",
  "details": {
    "timeout_seconds": 30,
    "elapsed_seconds": 30.1
  },
  "status_code": 504
}
```

**Diagnosis Steps:**

**Step 1:** Check execution time in logs:

```bash
kubectl logs deployment/sark-gateway -n sark-system \
  | grep "tool_execution" \
  | jq 'select(.tool_name=="analyze_data") | .duration_ms'
```

**Expected Output:**
```
30124
30089
30156
```

**Meaning:** Tool consistently timing out at 30 seconds.

**Step 2:** Check if tool is actually slow or timeout too short:

```bash
# Invoke tool directly on MCP server
time curl -X POST http://mcp-server.example.com:8080/mcp/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "analyze_data",
    "arguments": {"dataset": [1,2,3]}
  }'
```

**Expected Output:**
```
real    0m45.234s  # Tool takes 45 seconds
user    0m0.012s
sys     0m0.008s
```

**Meaning:** Tool legitimately takes longer than 30s timeout.

**Step 3:** Check for resource constraints:

```bash
# Check CPU/memory usage
kubectl top pods -n mcp-servers | grep mcp-server
```

**Expected Output (resource constrained):**
```
NAME                CPU(cores)   MEMORY(bytes)
mcp-server-xxx      1000m        1900Mi
```

**Meaning:** Pod at resource limits (1 CPU, ~2GB RAM).

**Fixes:**

**Fix 1:** Increase gateway timeout:
```bash
sark-cli server update data-server --request-timeout 60s
```

**Fix 2:** Optimize tool implementation:
```python
# Add timeout to slow operations
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 second timeout

try:
    # Slow operation
    result = expensive_computation()
finally:
    signal.alarm(0)  # Cancel alarm
```

**Fix 3:** Increase server resources:
```yaml
# kubernetes/mcp-server.yaml
resources:
  limits:
    cpu: "2000m"
    memory: "4Gi"
  requests:
    cpu: "1000m"
    memory: "2Gi"
```

**Fix 4:** Implement async execution for long-running tasks:
```bash
# Start async job
curl -X POST http://gateway.example.com/api/v1/tools/invoke-async \
  -d '{
    "server_id": "data-server",
    "tool_name": "analyze_data",
    "arguments": {...}
  }'

# Response
{
  "job_id": "job-12345",
  "status": "running"
}

# Poll for completion
curl http://gateway.example.com/api/v1/jobs/job-12345
```

## Debugging Authentication Failures

### Authentication Error Decision Tree

```
Authentication Failed
│
├─ Error: "missing_credentials"
│  └─ Is Authorization header present?
│     ├─ No → Add Authorization header
│     └─ Yes → Check header format
│
├─ Error: "invalid_token"
│  └─ Token format correct?
│     ├─ Bearer token → Validate token
│     │  ├─ Expired? → Refresh token
│     │  ├─ Invalid signature? → Get new token
│     │  └─ Wrong audience? → Check token claims
│     ├─ API key → Verify key is active
│     └─ JWT → Decode and inspect claims
│
├─ Error: "insufficient_permissions"
│  └─ Check policy decision
│     ├─ Policy denied → Review policy rules
│     ├─ Missing scope → Request additional scopes
│     └─ Wrong role → Contact admin
│
└─ Error: "authentication_service_unavailable"
   └─ Check auth service health
      ├─ Service down → Check auth service logs
      └─ Service slow → Check auth service metrics
```

### Step-by-Step Authentication Debugging

**Step 1:** Verify authentication header format:

```bash
# Extract header from your request
REQUEST_HEADER=$(curl -v http://gateway.example.com/api/v1/tools \
  -H "Authorization: Bearer ${TOKEN}" 2>&1 \
  | grep "Authorization:")

echo $REQUEST_HEADER
```

**Expected Output:**
```
> Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Common Issues:**

```bash
# Wrong: Missing "Bearer" prefix
Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Correct: Include "Bearer"
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Wrong: Extra space
Authorization: Bearer  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Correct: Single space
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Step 2:** Decode and inspect JWT token:

```bash
# Decode JWT (header.payload.signature)
echo $TOKEN | cut -d. -f2 | base64 -d | jq
```

**Expected Output:**
```json
{
  "sub": "user-123",
  "name": "Alice Developer",
  "role": "developer",
  "exp": 1705324800,
  "iat": 1705238400,
  "iss": "https://auth.example.com",
  "aud": "sark-gateway"
}
```

**Check for issues:**

```bash
# Check expiration
CURRENT_TIME=$(date +%s)
TOKEN_EXP=$(echo $TOKEN | cut -d. -f2 | base64 -d | jq -r '.exp')

if [ $CURRENT_TIME -gt $TOKEN_EXP ]; then
  echo "Token expired!"
else
  echo "Token valid for $((TOKEN_EXP - CURRENT_TIME)) more seconds"
fi
```

**Step 3:** Test token validation:

```bash
curl http://gateway.example.com/api/v1/auth/validate \
  -H "Authorization: Bearer ${TOKEN}"
```

**Expected Response (valid):**
```json
{
  "valid": true,
  "user_id": "user-123",
  "expires_at": "2024-01-15T18:00:00Z"
}
```

**Expected Response (invalid):**
```json
{
  "valid": false,
  "error": "token_expired",
  "message": "Token expired at 2024-01-15T14:00:00Z"
}
```

**Step 4:** Check gateway authentication logs:

```bash
kubectl logs deployment/sark-gateway -n sark-system \
  | grep "authentication_failed" \
  | jq '{timestamp, user_id, error, details}'
```

**Expected Output:**
```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "user_id": "user-123",
  "error": "token_expired",
  "details": {
    "expired_at": "2024-01-15T14:00:00Z",
    "current_time": "2024-01-15T14:30:00Z"
  }
}
```

**Step 5:** Refresh expired token:

```bash
# Get new token
NEW_TOKEN=$(curl -X POST https://auth.example.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "refresh_token",
    "refresh_token": "'"$REFRESH_TOKEN"'",
    "client_id": "sark-client"
  }' | jq -r '.access_token')

# Retry request with new token
curl http://gateway.example.com/api/v1/tools/invoke \
  -H "Authorization: Bearer ${NEW_TOKEN}" \
  -d '{...}'
```

## Policy Denial Troubleshooting Flowchart

```
Policy Denied Request
│
├─ Step 1: Check policy decision details
│  └─ curl /api/v1/policy/explain -d '{request_details}'
│
├─ Step 2: Identify denial reason
│  ├─ "role_not_allowed"
│  │  └─ User has wrong role
│  │     ├─ Request role change
│  │     └─ Or request policy update
│  │
│  ├─ "time_restriction"
│  │  └─ Outside allowed time window
│  │     ├─ Wait for allowed time
│  │     └─ Or request emergency access
│  │
│  ├─ "resource_not_allowed"
│  │  └─ Tool not in allowed list
│  │     └─ Request tool access
│  │
│  └─ "missing_attribute"
│     └─ User missing required attribute
│        └─ Update user attributes
│
└─ Step 3: Test policy in isolation
   └─ Use OPA REPL to test policy logic
```

### Policy Debugging Commands

**Step 1:** Get detailed policy decision:

```bash
curl -X POST http://gateway.example.com/api/v1/policy/explain \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "data-server",
    "tool_name": "analyze_data",
    "arguments": {}
  }' | jq
```

**Expected Response:**
```json
{
  "allowed": false,
  "policy_version": "1.0.0",
  "decision_id": "dec-12345",
  "reasons": [
    {
      "code": "role_not_allowed",
      "message": "User role 'viewer' not allowed to invoke write tools",
      "rule": "data.sark.gateway.authz.allow[2]"
    }
  ],
  "evaluation_time_ms": 5,
  "input": {
    "user": {
      "id": "user-123",
      "role": "viewer"
    },
    "tool": {
      "name": "analyze_data",
      "read_only": false
    }
  }
}
```

**Step 2:** Test policy locally with OPA:

```bash
# Create test input
cat > test_input.json <<EOF
{
  "user": {
    "id": "user-123",
    "role": "viewer"
  },
  "tool": {
    "name": "analyze_data",
    "read_only": false
  }
}
EOF

# Test policy
opa eval -i test_input.json \
  -d policies/authz.rego \
  --explain=full \
  "data.sark.gateway.authz"
```

**Step 3:** Trace policy execution:

```bash
# Enable policy tracing in gateway
kubectl set env deployment/sark-gateway \
  OPA_DECISION_LOGS_ENABLED=true \
  -n sark-system

# View decision logs
kubectl logs deployment/sark-gateway -n sark-system \
  | grep "policy_decision" \
  | jq '{user, tool, decision, reasons}'
```

**Step 4:** Modify policy to allow (if appropriate):

```rego
# Before: Only admins can invoke write tools
allow {
    input.user.role == "admin"
    not input.tool.read_only
}

# After: Developers can also invoke write tools
allow {
    input.user.role in ["admin", "developer"]
    not input.tool.read_only
}
```

Deploy updated policy:

```bash
sark-cli policy deploy --bundle updated-policy.tar.gz
```

## Performance Issue Diagnosis

### Slow Tool Invocation

**Symptom:** Tool invocations are consistently slow (>5 seconds).

**Diagnosis:**

**Step 1:** Measure where time is spent:

```bash
curl -X POST http://gateway.example.com/api/v1/tools/invoke \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Enable-Timing: true" \
  -d '{
    "server_id": "data-server",
    "tool_name": "analyze_data",
    "arguments": {...}
  }' | jq '.timing'
```

**Expected Response:**
```json
{
  "total_ms": 5234,
  "breakdown": {
    "authentication_ms": 45,
    "policy_evaluation_ms": 12,
    "server_lookup_ms": 3,
    "tool_execution_ms": 5150,
    "response_serialization_ms": 24
  }
}
```

**Analysis:**
- Total: 5.2 seconds
- Tool execution: 5.15 seconds (98% of time)
- Other overhead: 84ms (2%)

**Conclusion:** Slowness is in tool execution, not gateway overhead.

**Step 2:** Profile tool execution:

```bash
# Enable profiling on MCP server
curl -X POST http://mcp-server.example.com:8080/debug/pprof/profile?seconds=30 \
  > profile.pb.gz

# Analyze profile
go tool pprof -http=:8081 profile.pb.gz
```

**Step 3:** Check database query performance (if applicable):

```sql
-- Enable query logging
SET log_min_duration_statement = 100;  -- Log queries >100ms

-- Run tool invocation

-- View slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Fixes:**

**Fix 1:** Add database indexes:
```sql
CREATE INDEX idx_data_timestamp ON data_table(timestamp);
CREATE INDEX idx_data_user ON data_table(user_id);
```

**Fix 2:** Add caching:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def expensive_computation(key):
    # Cached result
    return result
```

**Fix 3:** Optimize algorithm:
```python
# Before: O(n²)
for item in items:
    for other in items:
        compare(item, other)

# After: O(n log n)
items.sort()
for i in range(len(items) - 1):
    compare(items[i], items[i+1])
```

## Network Connectivity Debugging

### Step-by-Step Network Diagnosis

**Step 1:** Test DNS resolution:

```bash
# From gateway pod
kubectl exec -it deployment/sark-gateway -n sark-system -- \
  nslookup mcp-server.mcp-servers.svc.cluster.local
```

**Expected Output (working):**
```
Server:    10.96.0.10
Address:   10.96.0.10#53

Name:   mcp-server.mcp-servers.svc.cluster.local
Address: 10.100.50.123
```

**Expected Output (broken):**
```
Server:    10.96.0.10
Address:   10.96.0.10#53

** server can't find mcp-server.mcp-servers.svc.cluster.local: NXDOMAIN
```

**Fix:** Check service exists:
```bash
kubectl get svc -n mcp-servers mcp-server
```

**Step 2:** Test TCP connectivity:

```bash
# Test port is reachable
kubectl exec -it deployment/sark-gateway -n sark-system -- \
  nc -zv mcp-server.mcp-servers.svc.cluster.local 8080
```

**Expected Output (working):**
```
Connection to mcp-server.mcp-servers.svc.cluster.local 8080 port [tcp/http] succeeded!
```

**Expected Output (blocked):**
```
nc: connect to mcp-server.mcp-servers.svc.cluster.local port 8080 (tcp) failed: Connection refused
```

**Step 3:** Check network policies:

```bash
kubectl get networkpolicies -n mcp-servers
kubectl describe networkpolicy mcp-server-policy -n mcp-servers
```

**Look for:**
```yaml
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: sark-system  # Gateway must be in this namespace
      ports:
        - protocol: TCP
          port: 8080
```

**Fix:** Update network policy to allow gateway:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-policy
  namespace: mcp-servers
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: sark-system
        - podSelector:
            matchLabels:
              app: sark-gateway
      ports:
        - protocol: TCP
          port: 8080
```

**Step 4:** Trace network path:

```bash
# Traceroute to server
kubectl exec -it deployment/sark-gateway -n sark-system -- \
  traceroute mcp-server.mcp-servers.svc.cluster.local
```

**Step 5:** Check firewall logs:

```bash
# On gateway node
sudo iptables -L -v -n | grep 8080

# Check drops
sudo iptables -L INPUT -v -n | grep DROP
```

## Timeout Troubleshooting

### Connection Timeout

**Symptom:**
```json
{
  "error": "connection_timeout",
  "message": "Failed to connect to MCP server within 5s"
}
```

**Diagnosis:**

```bash
# Measure connection time
time kubectl exec deployment/sark-gateway -n sark-system -- \
  curl -v --connect-timeout 10 http://mcp-server:8080/health
```

**Expected Output (slow):**
```
* Connected to mcp-server (10.100.50.123) port 8080 (#0) after 8234ms
```

**Fixes:**

**Fix 1:** Increase connection timeout:
```bash
sark-cli server update data-server --connection-timeout 10s
```

**Fix 2:** Check for network congestion:
```bash
# Check network latency
kubectl exec deployment/sark-gateway -n sark-system -- \
  ping -c 10 mcp-server.mcp-servers.svc.cluster.local
```

**Fix 3:** Scale server to handle load:
```bash
kubectl scale deployment/mcp-server --replicas=3 -n mcp-servers
```

### Read Timeout

**Symptom:**
```json
{
  "error": "read_timeout",
  "message": "Server did not respond within 30s"
}
```

**Diagnosis:**

```bash
# Check if server is responding but slow
curl -v --max-time 60 http://mcp-server:8080/mcp/tools/invoke \
  -d '{...}'
```

**Fixes:**

**Fix 1:** Increase read timeout:
```bash
sark-cli server update data-server --read-timeout 60s
```

**Fix 2:** Optimize server response time (see Performance section above).

## Related Resources

- [Gateway Error Codes Reference](../reference/error-codes.md)
- [MCP Protocol Debugging](https://modelcontextprotocol.io/docs/debugging)
- [Policy Debugging Guide](./how-to-write-policies.md#debugging)
- [Network Troubleshooting](../runbooks/network-issues.md)
- [Performance Tuning](../tutorials/performance-tuning.md)
- [Monitoring Guide](./how-to-monitor-gateway.md)

## Next Steps

1. **Set up monitoring** to catch issues early
   - See: [How to Monitor Gateway](./how-to-monitor-gateway.md)

2. **Review security settings** if auth issues persist
   - See: [How to Secure Gateway](./how-to-secure-gateway.md)

3. **Optimize policies** for better performance
   - See: [How to Write Policies](./how-to-write-policies.md)

4. **Create runbooks** for your team
   - See: [Runbook Template](../templates/runbook-template.md)
