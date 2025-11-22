# SARK Authorization Guide

This guide covers the authorization and policy enforcement framework in SARK, including OPA integration, policy-based access control, caching, and tool sensitivity classification.

---

## Table of Contents

1. [Overview](#overview)
2. [Policy-Based Access Control](#policy-based-access-control)
3. [Default Policies](#default-policies)
4. [Policy Authoring](#policy-authoring)
5. [Policy Caching](#policy-caching)
6. [Tool Sensitivity Classification](#tool-sensitivity-classification)
7. [Testing & Validation](#testing--validation)
8. [Performance](#performance)

---

## Overview

SARK uses [Open Policy Agent (OPA)](https://www.openpolicyagent.org/) for fine-grained authorization decisions. All access control decisions are evaluated through declarative policies written in Rego.

### Architecture

```
┌──────────────┐
│    Request   │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│  Policy Enforcement  │
│  Point (PEP)         │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐    ┌────────────┐
│  Policy Decision     │───>│   Redis    │ (Cache)
│  Point (OPA)         │<───│   Cache    │
└──────┬───────────────┘    └────────────┘
       │
       ▼
┌──────────────────────┐
│  Policy Bundles      │
│  - RBAC              │
│  - Sensitivity Rules │
│  - Team Access       │
│  - Time Restrictions │
└──────────────────────┘
```

### Key Features

- **Policy-as-Code**: Policies versioned in Git and deployed as bundles
- **Real-Time Decisions**: Sub-50ms policy evaluation (with caching <5ms)
- **Context-Aware**: Decisions based on user, resource, time, and environment
- **Audit Trail**: All decisions logged for compliance
- **Caching**: Redis-backed caching for performance

---

## Policy-Based Access Control

### Authorization Input

Every authorization request includes:

```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "developer",
    "teams": ["engineering", "platform"]
  },
  "action": "tool:invoke",
  "resource": {
    "type": "tool",
    "name": "execute_query",
    "sensitivity_level": "high",
    "team": "engineering"
  },
  "context": {
    "timestamp": 1700000000,
    "ip_address": "10.0.1.50",
    "mfa_verified": false,
    "environment": "production"
  }
}
```

### Authorization Output

OPA returns a decision:

```json
{
  "allow": true,
  "reason": "User has required role and tool sensitivity is within allowed level",
  "filtered_parameters": null,
  "audit_required": true
}
```

Or denies:

```json
{
  "allow": false,
  "reason": "Tool sensitivity level 'critical' exceeds user's maximum allowed level 'high'",
  "filtered_parameters": null,
  "audit_required": true
}
```

---

## Default Policies

### 1. Role-Based Access Control (RBAC)

SARK implements role-based access control with the following roles:

| Role | Permissions | Description |
|------|-------------|-------------|
| **admin** | Full access to all resources | System administrators |
| **developer** | Read/write servers, tools | Development teams |
| **operator** | Read/write servers, read tools | Operations teams |
| **viewer** | Read-only access | Auditors, stakeholders |

**Policy Example:**
```rego
# File: opa/policies/defaults/rbac.rego
package mcp.authorization

# Admins can do everything
allow if {
    input.user.role == "admin"
}

# Developers can register/update servers
allow if {
    input.user.role == "developer"
    input.action in ["server:read", "server:write", "server:register"]
}

# Viewers have read-only access
allow if {
    input.user.role == "viewer"
    startswith(input.action, "read") or endswith(input.action, ":read")
}
```

### 2. Sensitivity-Based Access Control

Tools are classified by sensitivity level (LOW, MEDIUM, HIGH, CRITICAL):

**Policy Example:**
```rego
# File: opa/policies/defaults/sensitivity.rego
package mcp.authorization

# Map roles to maximum allowed sensitivity
max_sensitivity := {
    "admin": "critical",
    "developer": "high",
    "operator": "medium",
    "viewer": "low"
}

# Deny if tool sensitivity exceeds user's allowed level
deny_reasons contains reason if {
    input.action == "tool:invoke"
    user_max := max_sensitivity[input.user.role]
    tool_level := input.tool.sensitivity_level
    sensitivity_exceeds(tool_level, user_max)
    reason := sprintf(
        "Tool sensitivity %v exceeds role %v maximum %v",
        [tool_level, input.user.role, user_max]
    )
}

# Helper: Check if sensitivity exceeds limit
sensitivity_exceeds(level, max_level) if {
    levels := ["low", "medium", "high", "critical"]
    level_idx := indexof(levels, level)
    max_idx := indexof(levels, max_level)
    level_idx > max_idx
}
```

### 3. Team-Based Access Control

Users can only access resources owned by their teams:

**Policy Example:**
```rego
# File: opa/policies/defaults/teams.rego
package mcp.authorization

# Allow if user is in resource's team
allow if {
    input.action in ["server:read", "tool:invoke"]
    some team_id in input.user.teams
    team_id == input.resource.team
}

# Team managers can manage team resources
allow if {
    input.action in ["server:update", "server:delete"]
    some team_id in input.user.teams
    team_id == input.resource.team
    user_is_team_manager(input.user.id, team_id)
}
```

### 4. Time-Based Restrictions

High-sensitivity operations restricted to work hours:

**Policy Example:**
```rego
# File: opa/policies/defaults/time.rego
package mcp.authorization

# Require work hours for high/critical operations
deny_reasons contains reason if {
    input.tool.sensitivity_level in ["high", "critical"]
    not is_work_hours(input.context.timestamp)
    reason := "High-sensitivity operations restricted to work hours (9am-5pm)"
}

# Check if timestamp is during work hours
is_work_hours(timestamp) if {
    time_hour := time.clock([timestamp, "America/New_York"])[0]
    time_hour >= 9
    time_hour < 17
}
```

---

## Policy Authoring

See detailed guide: **[OPA_POLICY_GUIDE.md](./OPA_POLICY_GUIDE.md)**

### Quick Start

1. **Create policy file** in `opa/policies/custom/`
2. **Write Rego rules** using declarative syntax
3. **Test policies** with `opa test`
4. **Deploy bundle** to OPA server

**Example Custom Policy:**

```rego
# File: opa/policies/custom/my_policy.rego
package mcp.custom

# Require MFA for critical tools
deny_reasons contains "MFA verification required for critical tools" if {
    input.tool.sensitivity_level == "critical"
    input.context.mfa_verified != true
}

# Restrict production access
allow if {
    input.context.environment == "production"
    input.user.role in ["admin", "operator"]
}
```

### Testing Policies

```bash
# Run policy tests
opa test opa/policies/

# Test specific package
opa test opa/policies/defaults/rbac_test.rego

# Evaluate policy interactively
opa eval -d opa/policies/ -i input.json 'data.mcp.authorization.allow'
```

---

## Policy Caching

See detailed guide: **[POLICY_CACHING.md](./POLICY_CACHING.md)**

### Overview

Policy decisions are cached in Redis for performance:

- **Cache hit latency**: <5ms
- **Cache miss + OPA**: 50-100ms
- **Target hit rate**: 80%+

### TTL by Sensitivity

| Sensitivity | TTL | Rationale |
|-------------|-----|-----------|
| LOW | 300s (5 min) | Safe to cache longer |
| MEDIUM | 180s (3 min) | Moderate caching |
| HIGH | 60s (1 min) | Shorter TTL |
| CRITICAL | 30s (30 sec) | Minimal caching |

### Cache Invalidation

```python
from sark.services.policy import OPAClient

opa_client = OPAClient()

# Invalidate all cached decisions
await opa_client.invalidate_cache()

# Invalidate by user
await opa_client.invalidate_cache(user_id="user-123")

# Invalidate by action
await opa_client.invalidate_cache(
    user_id="user-123",
    action="tool:invoke"
)
```

### Cache Metrics

```python
metrics = opa_client.get_cache_metrics()

print(f"Hit rate: {metrics['hit_rate']}%")
print(f"Avg cache latency: {metrics['avg_cache_latency_ms']}ms")
print(f"Avg OPA latency: {metrics['avg_opa_latency_ms']}ms")
```

**Example Output:**
```
Hit rate: 85.0%
Avg cache latency: 2.3ms
Avg OPA latency: 45.7ms
```

---

## Tool Sensitivity Classification

See detailed guide: **[TOOL_SENSITIVITY_CLASSIFICATION.md](./TOOL_SENSITIVITY_CLASSIFICATION.md)**

### Automatic Detection

Tools are automatically classified based on keywords:

**CRITICAL keywords**: `payment`, `password`, `secret`, `credential`, `encrypt`

**HIGH keywords**: `delete`, `drop`, `exec`, `admin`, `destroy`

**MEDIUM keywords**: `write`, `update`, `create`, `modify`

**LOW keywords**: `read`, `get`, `list`, `query`

### Examples

| Tool Name | Keywords | Detected Level |
|-----------|----------|----------------|
| `get_user` | get | LOW |
| `update_config` | update | MEDIUM |
| `delete_database` | delete, drop | HIGH |
| `process_payment` | payment | CRITICAL |

### Manual Override

```bash
curl -X POST https://sark.example.com/api/v1/tools/{tool_id}/sensitivity \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "sensitivity_level": "critical",
    "reason": "Handles PII data"
  }'
```

### API Endpoints

- `GET /api/v1/tools/{tool_id}/sensitivity` - Get sensitivity level
- `POST /api/v1/tools/{tool_id}/sensitivity` - Update sensitivity (admin only)
- `POST /api/v1/tools/detect-sensitivity` - Test auto-detection
- `GET /api/v1/tools/statistics/sensitivity` - Get statistics
- `GET /api/v1/tools/sensitivity/{level}` - List tools by level

---

## Testing & Validation

### Unit Testing Policies

```bash
# Run all policy tests
opa test opa/policies/

# With coverage
opa test --coverage opa/policies/

# Verbose output
opa test -v opa/policies/
```

**Example Test:**
```rego
# File: opa/policies/defaults/rbac_test.rego
package mcp.authorization

test_admin_full_access if {
    allow with input as {
        "user": {"role": "admin"},
        "action": "server:delete"
    }
}

test_viewer_read_only if {
    not allow with input as {
        "user": {"role": "viewer"},
        "action": "server:delete"
    }
}

test_developer_can_register if {
    allow with input as {
        "user": {"role": "developer"},
        "action": "server:register"
    }
}
```

### Integration Testing

```python
import pytest
from sark.services.policy import OPAClient

@pytest.mark.asyncio
async def test_policy_decision():
    """Test policy evaluation."""
    opa_client = OPAClient()

    decision = await opa_client.authorize(
        user_id="user-123",
        action="tool:invoke",
        resource="tool:execute_query",
        context={"role": "developer"}
    )

    assert decision is True

@pytest.mark.asyncio
async def test_sensitivity_enforcement():
    """Test sensitivity level enforcement."""
    opa_client = OPAClient()

    # Viewer trying to invoke critical tool
    decision = await opa_client.authorize(
        user_id="user-456",
        action="tool:invoke",
        resource="tool:process_payment",
        context={
            "role": "viewer",
            "tool_sensitivity": "critical"
        }
    )

    assert decision is False
```

### Performance Testing

```python
import time
import asyncio

async def benchmark_policy_evaluation():
    """Benchmark policy evaluation performance."""
    opa_client = OPAClient()

    # Warm up cache
    for _ in range(10):
        await opa_client.authorize(...)

    # Benchmark
    iterations = 1000
    start = time.time()

    for _ in range(iterations):
        await opa_client.authorize(...)

    duration = time.time() - start
    avg_latency = (duration / iterations) * 1000

    print(f"Avg latency: {avg_latency:.2f}ms")
    assert avg_latency < 10  # <10ms with caching
```

---

## Performance

### Latency Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| Cache hit | <5ms | 2-3ms |
| Cache miss (OPA) | <100ms | 50-80ms |
| Policy evaluation | <50ms | 30-45ms |
| Cache set | <2ms | 1-2ms |

### Throughput

- **With caching**: 10,000+ req/s
- **Without caching**: 100-200 req/s (OPA limited)
- **Target cache hit rate**: 80%+

### Optimization Tips

1. **Enable caching** (default)
2. **Monitor hit rate** - investigate if <70%
3. **Use appropriate TTL** - sensitivity-based
4. **Invalidate smartly** - on permission changes only
5. **Warm cache** - pre-populate for common requests

### Monitoring

**Key Metrics:**
- Cache hit rate (target: 80%+)
- P50/P95/P99 latency
- OPA evaluation time
- Cache size (entries)
- Error rate

**Prometheus Metrics:**
```
sark_policy_cache_hits_total
sark_policy_cache_misses_total
sark_policy_cache_hit_rate
sark_policy_evaluation_duration_ms
sark_opa_errors_total
```

---

## Common Patterns

### 1. Multi-Factor Authorization

```rego
allow if {
    input.user.role in ["admin", "developer"]
    input.action == "tool:invoke"
    tool_allowed_for_user
    team_access_granted
    within_time_window
}
```

### 2. Attribute-Based Access Control (ABAC)

```rego
allow if {
    input.user.attributes.clearance_level >= input.resource.required_clearance
    input.user.attributes.department == input.resource.department
}
```

### 3. Parameter Filtering

```rego
filtered_parameters := result if {
    input.action == "tool:invoke"
    input.tool.name == "database_query"
    result := redact_sensitive_columns(input.parameters.query)
}
```

### 4. Deny-by-Default

```rego
# Default deny
default allow := false

# Explicitly allow based on rules
allow if {
    # ... specific conditions ...
}
```

---

## Troubleshooting

### Low Cache Hit Rate

**Symptoms**: Hit rate <70%

**Causes**:
- Too diverse request patterns
- TTL too short
- Context varies too much

**Solutions**:
- Review request patterns
- Increase TTL for low sensitivity
- Normalize context data

### High Latency

**Symptoms**: P95 latency >100ms

**Causes**:
- OPA performance issues
- Complex policies
- Network latency

**Solutions**:
- Optimize policies
- Enable/verify caching
- Scale OPA horizontally

### Policy Denials

**Symptoms**: Unexpected denials

**Debug Steps**:
1. Check OPA logs
2. Evaluate policy with test input
3. Review recent policy changes
4. Verify user permissions

```bash
# Test policy with sample input
opa eval -d opa/policies/ -i test_input.json \
  'data.mcp.authorization.allow'

# Check deny reasons
opa eval -d opa/policies/ -i test_input.json \
  'data.mcp.authorization.deny_reasons'
```

---

## Best Practices

### 1. Security

- **Fail closed**: Default deny, explicitly allow
- **Least privilege**: Grant minimum required permissions
- **Audit all**: Log all authorization decisions
- **Regular reviews**: Audit policies and permissions
- **Immutable audit**: Don't delete audit logs

### 2. Performance

- **Enable caching**: Use Redis cache (default)
- **Optimize policies**: Keep rules simple
- **Monitor metrics**: Track hit rate and latency
- **Test performance**: Benchmark before deployment

### 3. Maintainability

- **Policy as code**: Version in Git
- **Comprehensive tests**: Unit and integration tests
- **Documentation**: Comment complex rules
- **Modular design**: Separate concerns into packages
- **Consistent naming**: Follow naming conventions

### 4. Operations

- **Gradual rollout**: Test policies in staging first
- **Monitoring**: Alert on policy failures
- **Backup**: Keep old policy versions
- **Incident response**: Plan for policy rollback

---

## Additional Resources

### Documentation

- [OPA Policy Guide](./OPA_POLICY_GUIDE.md) - Complete policy authoring guide
- [Policy Caching](./POLICY_CACHING.md) - Detailed caching documentation
- [Tool Sensitivity](./TOOL_SENSITIVITY_CLASSIFICATION.md) - Sensitivity classification
- [API Reference](./API_REFERENCE.md) - API endpoints
- [Security Guide](./SECURITY.md) - Security best practices

### External Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Playground](https://play.openpolicyagent.org/)
- [OPA Best Practices](https://www.openpolicyagent.org/docs/latest/policy-performance/)
- [Policy Testing](https://www.openpolicyagent.org/docs/latest/policy-testing/)

---

## Quick Reference

### Policy Evaluation API

```python
from sark.services.policy import OPAClient

# Initialize
opa_client = OPAClient()

# Evaluate policy
decision = await opa_client.authorize(
    user_id="user-123",
    action="tool:invoke",
    resource="tool:delete_user",
    context={"role": "developer"}
)

# With full input
from sark.services.policy.opa_client import AuthorizationInput

auth_input = AuthorizationInput(
    user={"id": "user-123", "role": "developer"},
    action="tool:invoke",
    tool={"name": "delete_user", "sensitivity_level": "high"},
    context={"timestamp": 1700000000}
)

decision = await opa_client.evaluate_policy(auth_input)

# Check decision
if decision.allow:
    # Proceed with action
    execute_action()
else:
    # Deny access
    raise PermissionDenied(decision.reason)
```

### Common Commands

```bash
# Test policies
opa test opa/policies/

# Evaluate policy
opa eval -d opa/policies/ -i input.json 'data.mcp.authorization.allow'

# Format policies
opa fmt -w opa/policies/

# Check policy syntax
opa check opa/policies/

# Run OPA server
opa run --server --bundle opa/policies/
```
