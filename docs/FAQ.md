# SARK Frequently Asked Questions

**Common Questions About SARK MCP Governance**

---

## General Questions

### What is SARK?

SARK (Security Audit and Resource Kontroler) is an enterprise-grade governance system for Model Context Protocol (MCP) deployments. It provides:

- **Zero-trust security architecture** for MCP servers and tools
- **Automated discovery** and registration of MCP services
- **Fine-grained authorization** via Open Policy Agent
- **Comprehensive audit trails** for compliance
- **Centralized management** of thousands of MCP servers

**Target Scale:** 50,000+ employees, 10,000+ MCP servers

###What is MCP?

**Model Context Protocol (MCP)** is an open protocol that enables AI assistants to securely access external tools and data sources. Think of it as a standardized way for AI models to interact with your company's systems, databases, and APIs.

**Example:** An AI assistant using MCP could:
- Query your company's database
- Create tickets in Jira
- Search through documentation
- Analyze customer data

SARK ensures these interactions are **secure, governed, and auditable**.

### Why do I need SARK?

Without governance, MCP deployments face risks:

❌ **No visibility** - Don't know what MCP servers exist
❌ **No control** - Can't enforce who can access what
❌ **No audit** - Can't prove compliance
❌ **Shadow IT** - Unmanaged MCP servers proliferate
❌ **Security gaps** - No consistent security enforcement

With SARK:

✅ **Full visibility** - Discover all MCP servers automatically
✅ **Fine-grained control** - Policy-based authorization
✅ **Complete audit trail** - Every action logged
✅ **Shadow IT detection** - Find unmanaged servers
✅ **Zero-trust security** - Multi-layer enforcement

### How is SARK different from an API gateway?

| Feature | API Gateway (Kong/Nginx) | SARK |
|---------|-------------------------|------|
| **Protocol** | Generic HTTP/REST | MCP-specific |
| **Authorization** | Basic RBAC | ReBAC + ABAC + time-based |
| **Tool Validation** | ❌ No | ✅ Yes - validates MCP tool schemas |
| **Semantic Analysis** | ❌ No | ✅ Yes - understands tool intent |
| **Auto-Discovery** | ❌ No | ✅ Yes - finds MCP servers |
| **Audit Trail** | Basic logs | Immutable TimescaleDB audit |
| **Policy Language** | Limited | Full Rego (OPA) policies |
| **MCP-Specific Security** | ❌ No | ✅ Yes - prompt injection protection, etc. |

**SARK uses Kong as a component** but adds MCP-specific governance on top.

---

## MCP Protocol Questions

### What MCP protocol version does SARK support?

SARK supports **MCP 2025-06-18** (the latest stable version).

**Backward compatibility:**
- ✅ MCP 2024-11-05 - Fully supported
- ✅ MCP 2024-06-15 - Supported with warnings
- ⚠️ Earlier versions - May work but not tested

**Version detection:** SARK auto-detects the MCP version from server metadata and adapts accordingly.

### What MCP transports are supported?

SARK supports all standard MCP transports:

| Transport | Status | Use Case |
|-----------|--------|----------|
| **HTTP/HTTPS** | ✅ Fully supported | Production servers, microservices |
| **stdio** | ✅ Fully supported | Local tools, CLI integrations |
| **SSE (Server-Sent Events)** | ✅ Fully supported | Streaming responses, real-time updates |
| **WebSocket** | 🔄 Coming soon | Bidirectional streaming |

**Configuration examples:**

```json
// HTTP transport
{
  "name": "my-server",
  "transport": "http",
  "endpoint": "https://api.example.com/mcp"
}

// stdio transport
{
  "name": "local-tool",
  "transport": "stdio",
  "command": "/usr/local/bin/my-tool"
}

// SSE transport
{
  "name": "streaming-server",
  "transport": "sse",
  "endpoint": "https://api.example.com/mcp/stream"
}
```

### How does SARK validate MCP tool schemas?

**Three-level validation:**

1. **Syntax Validation** - Tool definitions must be valid JSON Schema
   ```json
   {
     "name": "search_database",
     "parameters": {
       "type": "object",
       "properties": {
         "query": {"type": "string"},
         "limit": {"type": "integer", "minimum": 1, "maximum": 100}
       },
       "required": ["query"]
     }
   }
   ```

2. **Semantic Validation** - Tools checked for dangerous patterns
   - SQL injection risks
   - Command injection risks
   - Excessive permissions
   - Sensitive data exposure

3. **Policy Validation** - OPA policies can enforce:
   - Required tool parameters
   - Allowed tool names
   - Sensitivity levels
   - Required signatures

**Validation happens at:**
- Server registration time
- Tool invocation time
- Policy evaluation time

### What happens if an MCP server goes offline?

**SARK's resilience strategy:**

1. **Health Monitoring**
   - Periodic health checks every 30 seconds
   - Marks server as "unhealthy" after 3 failed checks
   - Auto-recovery when server comes back online

2. **Graceful Degradation**
   - Requests to unhealthy servers return 503 Service Unavailable
   - Policy engine can route to backup servers
   - Audit logs record all failures

3. **Alerting**
   - Prometheus alert: `sark_server_unhealthy`
   - Notification to ops team
   - Dashboard shows server status

**Auto-decommission:**
- Servers unhealthy for >7 days marked as "decommissioned"
- Configurable via `SERVER_UNHEALTHY_THRESHOLD_DAYS`

### Can SARK work with custom MCP extensions?

**Yes!** SARK is extensible:

**1. Custom Tool Attributes:**
```json
{
  "name": "my_tool",
  "description": "Custom tool",
  "parameters": { /* standard */ },
  "x-company-cost-center": "engineering",
  "x-company-sla": "tier1",
  "x-company-pii": true
}
```

**2. Custom Transport Metadata:**
```json
{
  "transport": "http",
  "endpoint": "https://api.example.com",
  "metadata": {
    "circuit_breaker_enabled": true,
    "timeout_ms": 5000,
    "retry_policy": "exponential"
  }
}
```

**3. Policy Access to Extensions:**
```rego
# Access custom attributes in policies
allow if {
    input.tool.x-company-cost-center == "approved-center"
    input.tool.x-company-pii == false
}
```

**Note:** Custom extensions must start with `x-` prefix per MCP spec.

### How do I register an MCP server with SARK?

**Three methods:**

**1. REST API** (Recommended for automation):
```bash
curl -X POST https://sark.company.com/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "analytics-server",
    "transport": "http",
    "endpoint": "https://analytics.example.com/mcp",
    "version": "2025-06-18",
    "capabilities": ["tools"],
    "tools": [
      {
        "name": "query_metrics",
        "description": "Query system metrics",
        "parameters": { /* JSON Schema */ }
      }
    ],
    "sensitivity_level": "medium"
  }'
```

**2. CLI Tool**:
```bash
sark-cli servers register \
  --name analytics-server \
  --endpoint https://analytics.example.com/mcp \
  --tools-file tools.json
```

**3. Auto-Discovery** (Kubernetes):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-mcp-server
  annotations:
    sark.io/auto-register: "true"
    sark.io/sensitivity: "medium"
    sark.io/tools-endpoint: "/mcp/tools"
```

SARK's discovery agent automatically finds and registers the server.

### What's the difference between MCP tools and capabilities?

**Capabilities** - Server-level features:
```json
{
  "capabilities": ["tools", "resources", "prompts", "sampling"]
}
```

| Capability | Description | Support |
|------------|-------------|---------|
| **tools** | Exposes executable tools | ✅ Full |
| **resources** | Provides data resources | ✅ Full |
| **prompts** | Provides prompt templates | ✅ Full |
| **sampling** | Supports model sampling | ⚠️ Limited |

**Tools** - Individual functions the server provides:
```json
{
  "tools": [
    {
      "name": "search",
      "description": "Search the database",
      "parameters": { /* schema */ }
    }
  ]
}
```

**SARK governance:**
- Policies can restrict capabilities: `if "sampling" in server.capabilities { deny }`
- Policies can restrict individual tools: `if tool.name == "dangerous_tool" { deny }`
- Sensitivity levels apply to both servers and tools

### How does SARK handle MCP tool parameter validation?

**Validation pipeline:**

```
1. JSON Schema Validation
   ↓
2. Sensitivity Detection
   ↓
3. Policy Evaluation
   ↓
4. Parameter Filtering
   ↓
5. Invocation
```

**Example - SQL Query Tool:**

```json
{
  "name": "execute_query",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "maxLength": 10000,
        "pattern": "^SELECT.*"  // Only SELECT queries
      },
      "database": {
        "type": "string",
        "enum": ["analytics", "readonly"]  // Allowed DBs
      }
    }
  }
}
```

**Policy can further restrict:**
```rego
# Deny queries containing sensitive tables
deny if {
    contains(lower(input.parameters.query), "user_passwords")
}

# Filter out certain parameters
filter_parameters := {
    "query": redact_patterns(input.parameters.query),
    "database": input.parameters.database
}
```

### Can MCP servers be dynamically discovered?

**Yes! SARK supports multiple discovery mechanisms:**

**1. Kubernetes Service Discovery** (Recommended):
```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    sark.io/auto-register: "true"
    sark.io/mcp-port: "8080"
    sark.io/mcp-path: "/mcp"
```

SARK watches Kubernetes API for annotated services.

**2. Consul Service Discovery**:
```bash
# MCP servers register with Consul
consul services register -name=mcp-analytics \
  -tag=mcp \
  -tag=sensitivity:medium
```

SARK queries Consul for `tag=mcp` services.

**3. DNS Service Discovery**:
```bash
# DNS SRV records
_mcp._tcp.example.com. 86400 IN SRV 10 60 8080 server1.example.com.
```

**4. Network Scanning** (Development only):
```bash
# Scan internal network for MCP servers
sark-cli discover --network 10.0.0.0/24 --port 8080
```

**Discovery interval:** Every 5 minutes (configurable)

### How do I debug MCP communication issues?

**Debugging tools:**

**1. MCP Protocol Tracer**:
```bash
# Enable verbose MCP logging
export SARK_MCP_DEBUG=true
export SARK_LOG_LEVEL=debug

# See full MCP request/response in logs
tail -f /var/log/sark/mcp-trace.log
```

**2. Test MCP Endpoint**:
```bash
# Health check endpoint
curl -v https://mcp-server.example.com/health

# List tools endpoint
curl -v https://mcp-server.example.com/mcp/tools

# Test tool invocation
curl -X POST https://mcp-server.example.com/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search",
    "parameters": {"query": "test"}
  }'
```

**3. SARK Diagnostic Endpoint**:
```bash
# Test connectivity from SARK to MCP server
curl -X POST https://sark.company.com/api/v1/debug/test-connection \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "server_id": "uuid",
    "test_tool": "search",
    "test_parameters": {}
  }'
```

**4. Audit Logs**:
```bash
# Check recent MCP invocations
curl https://sark.company.com/api/v1/audit/events?event_type=tool_invocation&limit=50
```

**Common issues:**
- ❌ Network connectivity → Check firewalls, DNS
- ❌ Certificate errors → Verify TLS certificates
- ❌ Timeout → Increase `MCP_REQUEST_TIMEOUT_MS`
- ❌ Invalid response → Check MCP server compliance

### What MCP-specific security features does SARK provide?

**MCP Protocol Security:**

1. **Prompt Injection Detection**
   - Scans tool parameters for malicious prompts
   - Blocks common injection patterns
   - AI-powered anomaly detection

2. **Tool Signature Verification**
   - Cryptographic signatures on tools
   - Verify tool hasn't been tampered with
   - PKI integration

3. **Schema Validation**
   - Strict JSON Schema enforcement
   - Type validation
   - Range checking

4. **Content Filtering**
   - PII detection in responses
   - Redaction of sensitive data
   - Compliance with data policies

5. **Rate Limiting**
   - Per-tool rate limits
   - Per-user rate limits
   - Adaptive throttling

**Example policy:**
```rego
# Require tool signatures for high-sensitivity tools
deny if {
    input.tool.sensitivity_level == "critical"
    not input.tool.signature
}

# Block tools with dangerous parameters
deny if {
    some param in input.tool.parameters.properties
    param.type == "string"
    not param.maxLength  # Unbounded strings are risky
}
```

---

## Deployment Questions

### Can I run SARK in my existing Kubernetes cluster?

**Yes!** SARK is designed for Kubernetes-first deployment.

**Requirements:**
- Kubernetes 1.28+
- PostgreSQL 15+ (managed service recommended)
- Redis 7+ (managed service recommended)
- 3-5 nodes (for HA)

See [Deployment Runbook](runbooks/DEPLOYMENT.md) for details.

### Do I need Kong Gateway?

**For production: Yes, recommended.**
**For development: No, optional.**

Kong Gateway provides:
- Edge security and rate limiting
- MCP protocol validation
- Load balancing
- Request routing

You can start without Kong and add it later as you scale.

### What databases does SARK require?

**Required:**
1. **PostgreSQL 15+** - Policies, users, servers (can be managed service: RDS, Cloud SQL)
2. **TimescaleDB** - Audit logs (can be same PostgreSQL instance with TimescaleDB extension)
3. **Redis 7+** - Caching (can be managed service: ElastiCache, Memorystore)

**Optional:**
4. **Consul** - Service discovery (can use Kubernetes DNS instead)
5. **Vault** - Secrets management (recommended for production)

### Can I run SARK on-premises?

**Yes!** SARK supports:

- **On-premises Kubernetes** (bare metal, VMware)
- **Private cloud** (OpenStack, etc.)
- **Hybrid** (some components on-prem, some cloud)
- **Air-gapped environments** (with pre-built containers)

### What cloud providers are supported?

All major cloud providers:

- ✅ **AWS** - EKS, RDS, ElastiCache
- ✅ **Google Cloud** - GKE, Cloud SQL, Memorystore
- ✅ **Azure** - AKS, Azure Database, Azure Cache
- ✅ **Multi-cloud** - Can span multiple providers

---

## Security Questions

### How does SARK handle authentication?

SARK supports multiple authentication methods:

1. **OAuth 2.0 / OpenID Connect** (recommended for users)
   - Okta, Auth0, Azure AD, Google Workspace

2. **API Keys** (for server-to-server)
   - Scoped, rotatable, audited

3. **Mutual TLS** (for service mesh)
   - Certificate-based authentication

4. **JWT Tokens** (flexible)
   - Short-lived (15 min default)
   - Validated on every request

### What about data privacy (GDPR)?

SARK is **GDPR-compliant** out of the box:

✅ **Data Subject Rights:**
- Right to access (API endpoint for data export)
- Right to erasure (anonymization, not deletion of audit logs)
- Right to rectification (API for data updates)

✅ **Privacy by Design:**
- PII redaction in logs
- Encryption at rest and in transit
- Data minimization (collect only what's needed)

✅ **Audit Trail:**
- Who accessed what data, when
- 90-day retention by default (configurable)
- Immutable audit logs (TimescaleDB)

See [SECURITY.md](SECURITY.md) for details.

### How are secrets stored?

**Never in plaintext!**

SARK uses **HashiCorp Vault** for secrets:

1. **Dynamic credentials** - Generated on-demand, short-lived
2. **Encryption** - All secrets encrypted with Vault's transit engine
3. **Rotation** - Automatic rotation every 24-90 days
4. **Audit** - Every secret access logged
5. **Least privilege** - Workload identity-based access

**Alternative:** Kubernetes Secrets (for development only)

### Does SARK support SOC 2 compliance?

**Yes!** SARK implements SOC 2 Trust Service Criteria:

| Control | Implementation |
|---------|----------------|
| **CC6.1** - Access Controls | OAuth 2.0, MFA, policy-based authorization |
| **CC6.6** - Logging | Immutable audit trail, 90-day retention |
| **CC6.7** - Detection | Real-time anomaly detection, SIEM integration |
| **CC7.2** - Monitoring | Prometheus metrics, alerting |
| **CC7.3** - Evaluation | Automated compliance reports |

See [docs/COMPLIANCE.md](#) for full details.

---

## Performance Questions

### What are the performance targets?

| Metric | Phase 1 (100 servers) | Phase 4 (10,000+ servers) |
|--------|----------------------|---------------------------|
| **Policy Latency (p99)** | <50ms | <5ms |
| **API Response (p95)** | <200ms | <50ms |
| **Throughput** | 100 RPS | 10,000+ RPS |
| **Availability** | 99% | 99.95% |

See [PERFORMANCE.md](PERFORMANCE.md) for optimization guide.

### How does caching work?

**Multi-level caching:**

```
L1: Application Cache (in-memory LRU)
  ↓ (miss)
L2: Redis (distributed)
  ↓ (miss)
L3: PostgreSQL (source of truth)
```

- **Policy decisions:** Cached for 60 seconds
- **User attributes:** Cached for 5 minutes
- **Server metadata:** Cached for 1 hour

**Cache hit rate target:** >95%

### Can SARK handle 10,000 requests per second?

**Yes!** With proper scaling:

**Phase 4 Architecture:**
- 50+ API pods (Kubernetes HPA)
- 20+ OPA pods
- PostgreSQL with read replicas (5-10)
- Redis cluster (6-12 nodes)
- Load balancer (AWS ALB / GCP Load Balancer)

See [PERFORMANCE.md](PERFORMANCE.md) scaling section.

### What about latency in different regions?

**Multi-region deployment:**

- **Active-Active:** Deploy in each region (US, EU, APAC)
- **Data Replication:** PostgreSQL replication across regions
- **Local Caching:** Redis in each region
- **Target Latency:** <50ms p95 within region

See [docs/MULTI_REGION.md](#) for architecture.

---

## Policy Questions

### How do I write policies?

Policies are written in **Rego** (OPA policy language).

**Example - Basic Authorization:**

```rego
package mcp.authorization

# Default deny
default allow := false

# Tool owner can access
allow if {
    input.tool.owner == input.user.id
}

# Team members can access team tools
allow if {
    some team in input.user.teams
    team in input.tool.managers
}
```

See [OPA_POLICY_GUIDE.md](OPA_POLICY_GUIDE.md) for complete guide.

### Can policies change dynamically?

**Yes!** Policies can be updated without restarting services.

**Deployment:**
1. Write policy → Test → Review → Merge to Git
2. CI/CD builds policy bundle
3. OPA automatically loads new bundle
4. Policy active within seconds

**Rollback:** Instant - deploy previous policy version

### What about emergency access?

**Break-glass procedures:**

1. **Emergency Role** - Pre-approved emergency access role
2. **Time-Limited** - Access expires after 1-4 hours
3. **Fully Audited** - Every action logged with justification
4. **Auto-Alert** - Security team notified immediately

**Example policy:**

```rego
allow if {
    input.user.role == "emergency_access"
    input.context.justification != null
    time_since_activation(input.user.id) < 3600  # 1 hour
}
```

### Can I test policies before deploying?

**Yes! Multiple ways:**

1. **Unit Tests** (OPA built-in)
```bash
opa test opa/policies/ -v
```

2. **Policy Playground**
   - Interactive UI at https://play.openpolicyagent.org/

3. **Staging Environment**
   - Deploy to staging first
   - Shadow production traffic

4. **Canary Deployment**
   - Roll out to 1% of traffic
   - Monitor for issues
   - Gradually increase

---

## Integration Questions

### Can SARK integrate with our existing SIEM?

**Yes!** SARK supports:

- **Splunk** - HEC (HTTP Event Collector)
- **Datadog** - Log forwarding
- **Sumo Logic** - HTTP Source
- **ElasticSearch** - Direct indexing
- **Custom** - Webhook integration

**Configuration:**

```python
siem_config = {
    "provider": "splunk",
    "endpoint": "https://splunk.company.com:8088",
    "token": vault("siem/splunk-hec-token"),
    "severity_threshold": "MEDIUM"  # Forward MEDIUM+ events
}
```

### Does SARK work with existing identity providers?

**Yes!** SARK integrates with:

- ✅ Okta
- ✅ Auth0
- ✅ Azure Active Directory
- ✅ Google Workspace
- ✅ OneLogin
- ✅ PingIdentity
- ✅ Custom OIDC providers

**Standard OIDC/OAuth 2.0** - Works with any compliant provider.

### Can I use SARK with CI/CD pipelines?

**Yes!** Common integrations:

**Server Registration in CI/CD:**

```yaml
# GitHub Actions example
- name: Register MCP Server
  run: |
    sark-cli servers create \
      --name "my-service-mcp" \
      --endpoint "https://mcp.myservice.com" \
      --tools tools.json
  env:
    SARK_API_KEY: ${{ secrets.SARK_API_KEY }}
```

**Policy Validation:**

```yaml
- name: Validate OPA Policies
  run: |
    opa test policies/
    opa check policies/
```

### What SDKs are available?

**Official SDKs:**
- ✅ **Python** - `pip install sark-sdk`
- ✅ **TypeScript/JavaScript** - `npm install @company/sark-sdk`
- ✅ **Go** - `go get github.com/company/sark-go-sdk`

**Community SDKs:**
- Java (maintained by community)
- Ruby (maintained by community)
- Rust (experimental)

**REST API** - All SDKs wrap the standard REST API

---

## Operational Questions

### How do I monitor SARK?

**Built-in monitoring:**

1. **Prometheus Metrics**
   - Request latency, throughput, errors
   - Database performance
   - Cache hit rates

2. **Grafana Dashboards**
   - Pre-built dashboards included
   - Real-time visualization

3. **Health Checks**
   - `/health` - Basic health
   - `/health/ready` - Readiness (including dependencies)

4. **Alerts** (PagerDuty, Slack)
   - Policy evaluation failures
   - High error rates
   - Performance degradation

### What's the disaster recovery strategy?

**RPO (Recovery Point Objective):** <5 minutes
**RTO (Recovery Time Objective):** <30 minutes

**Backup Strategy:**
1. **Database** - Continuous WAL archiving + daily snapshots
2. **Policies** - Versioned in Git
3. **Configuration** - Infrastructure as Code (Terraform)

**Recovery Procedure:**
1. Deploy infrastructure (Terraform)
2. Restore database from backup
3. Deploy latest policy bundle
4. Verify health checks
5. Resume traffic

See [docs/DISASTER_RECOVERY.md](#) for runbook.

### How do I upgrade SARK?

**Rolling upgrades** (zero downtime):

```bash
# Deploy new version
kubectl set image deployment/sark-api \
    api=sark/api:v1.1.0 \
    -n sark-system

# Kubernetes gradually replaces pods
# Old version: 3 pods → 2 pods → 1 pod → 0 pods
# New version: 0 pods → 1 pod → 2 pods → 3 pods
```

**Rollback** (if needed):

```bash
kubectl rollout undo deployment/sark-api -n sark-system
```

**Database migrations:**

```bash
# Run migrations before deploying new version
kubectl exec -it deployment/sark-api -- alembic upgrade head
```

### What about multi-tenancy?

**SARK supports:**

1. **Soft multi-tenancy** (default)
   - Single deployment, logical separation
   - Teams isolated via policies
   - Shared infrastructure

2. **Hard multi-tenancy**
   - Separate namespace per tenant
   - Dedicated database per tenant
   - Full resource isolation

**Recommendation:** Start with soft, move to hard if needed.

---

## Cost Questions

### How much does SARK cost to run?

**Infrastructure costs (AWS example):**

| Phase | Servers | Monthly Cost |
|-------|---------|--------------|
| Phase 1 | 100 | $10-15K |
| Phase 3 | 5,000 | $60-80K |
| Phase 4 | 10,000+ | $100-120K |

**Breakdown:**
- Compute (EKS): 40%
- Database (RDS): 35%
- Cache (ElastiCache): 15%
- Networking: 10%

**ROI:**
- Prevent 1-2 security incidents/year: $500K-2M saved
- Reduce audit costs 50%: $200-500K/year
- Developer productivity: $1.2-2.4M/year (5,000 devs)

**Total ROI:** 10-20x investment

### Can I reduce costs?

**Cost optimization strategies:**

1. **Use managed services**
   - RDS instead of self-hosted PostgreSQL
   - ElastiCache instead of Redis on EC2
   - Reduces operational overhead

2. **Right-size resources**
   - Start small, scale as needed
   - Use HPA (Horizontal Pod Autoscaling)
   - Scale down during off-hours

3. **Use spot instances** (non-production)
   - 70% cost savings
   - Good for dev/staging

4. **Optimize database**
   - Enable compression (TimescaleDB)
   - Set retention policies (90 days default)
   - Use read replicas efficiently

See [docs/COST_OPTIMIZATION.md](#) for details.

---

## Troubleshooting Questions

### Policy evaluation is slow. What do I do?

**Diagnosis:**

```bash
# Check OPA metrics
curl http://opa:8181/metrics

# Look for high evaluation time
opa_decision_duration_seconds_p99 > 0.01  # >10ms is slow
```

**Solutions:**

1. **Optimize policy** - Move cheap checks first
2. **Add caching** - Cache decisions for 60s
3. **Scale OPA** - Add more OPA pods
4. **External data** - Reduce database lookups in policies

See [PERFORMANCE.md](PERFORMANCE.md) troubleshooting section.

### How do I debug policy denials?

**Check audit logs:**

```bash
# Query recent denials
curl -H "Authorization: Bearer $TOKEN" \
  "https://sark.company.com/api/v1/audit/events?event_type=authorization_denied&limit=10"
```

**Enable OPA trace:**

```bash
# Trace policy evaluation
opa run --server --log-level debug opa/policies/

# In logs, see which rules matched/didn't match
```

**Test policy locally:**

```bash
# Test with specific input
opa eval -d opa/policies/ \
         -i test-input.json \
         data.mcp.authorization.allow
```

### Server registration fails. Why?

**Common issues:**

1. **Network connectivity**
   ```bash
   # Test from SARK to MCP server
   curl -v https://mcp-server.internal:8080/health
   ```

2. **Invalid tool schema**
   ```json
   // Tool parameters must be valid JSON Schema
   "parameters": {
     "type": "object",  // Must specify type
     "properties": { ... }
   }
   ```

3. **Permissions**
   ```bash
   # Check if user has server:register permission
   curl -X POST /api/v1/policy/evaluate \
     -d '{"action": "server:register", "user_id": "..."}'
   ```

---

## Migration Questions

### Can I migrate from another MCP governance tool?

**Yes!** SARK provides migration tools:

```bash
# Export from existing tool
existing-tool export --format json > servers.json

# Import to SARK
sark-cli import --source servers.json --type generic
```

**Supported migrations:**
- Custom/homegrown solutions
- API Gateway-based governance
- Basic RBAC systems

See [docs/MIGRATION.md](#) for guides.

### How do I migrate policies?

**Policy migration:**

1. **Document existing policies** (if not code)
2. **Translate to Rego** (OPA policy language)
3. **Test thoroughly** (unit tests + staging)
4. **Gradual rollout** (canary deployment)

**We provide consulting** for complex migrations.

---

## Support Questions

### Where do I get help?

**Resources:**

1. **Documentation** - https://docs.sark.company.com
2. **Community Forum** - https://community.sark.company.com
3. **Slack Channel** - #sark-support
4. **Email Support** - support@company.com
5. **Enterprise Support** - Premium SLA available

### Is there training available?

**Yes!**

1. **Self-paced**
   - Online courses
   - Interactive tutorials
   - Video walkthroughs

2. **Instructor-led**
   - 2-day administrator training
   - 1-day developer workshop
   - Custom training for teams

3. **Certification**
   - SARK Certified Administrator
   - SARK Certified Developer

### What's the release schedule?

**Regular releases:**

- **Major (X.0.0):** Annual (breaking changes)
- **Minor (X.Y.0):** Quarterly (new features)
- **Patch (X.Y.Z):** Monthly (bug fixes)

**Security patches:** As needed (out-of-band)

**LTS versions:** 2-year support for enterprise customers

---

## Getting Started

### What's the quickest way to try SARK?

**10-minute quick start:**

```bash
# Clone repository
git clone https://github.com/company/sark.git
cd sark

# Start with Docker Compose
docker compose up -d

# Access UI
open http://localhost:8000/docs

# Register first server
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -d @examples/sample-server.json
```

See [QUICKSTART.md](QUICKSTART.md) for full tutorial.

### Where should I start learning?

**Recommended learning path:**

1. [QUICKSTART.md](QUICKSTART.md) - Get hands-on in 10 minutes
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand the system
3. [API_INTEGRATION.md](API_INTEGRATION.md) - Build integrations
4. [OPA_POLICY_GUIDE.md](OPA_POLICY_GUIDE.md) - Write policies
5. [DEPLOYMENT.md](runbooks/DEPLOYMENT.md) - Deploy to production

**For developers:** Focus on API Integration + Policy Guide
**For ops/SRE:** Focus on Deployment + Performance + Security

---

**Still have questions?**
- Check the [Glossary](GLOSSARY.md) for terminology
- Search the documentation
- Ask in community forum
- Contact support@company.com

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Maintained By:** SARK Team
