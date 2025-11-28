# Gateway Policy Architecture

## Overview

The SARK Gateway policy framework uses Open Policy Agent (OPA) to implement fine-grained, declarative authorization for MCP Gateway operations. This document describes the architecture, decision flow, and best practices for the policy system.

## Policy Hierarchy

```
mcp (root package)
├── gateway (Gateway tool invocation)
│   ├── gateway_authorization.rego
│   ├── a2a (Agent-to-Agent communication)
│   │   └── a2a_authorization.rego
│   └── advanced (Advanced policy scenarios)
│       ├── dynamic_rate_limits.rego
│       ├── contextual_auth.rego
│       ├── tool_chain_governance.rego
│       ├── data_governance.rego
│       └── cost_control.rego
└── (legacy policies)
    └── mcp_authorization.rego
```

## Policy Decision Flow

### 1. Gateway Tool Invocation

```
Request → Gateway API
          ↓
    Authorization Middleware
          ↓
    Policy Evaluation (OPA)
          ├→ gateway_authorization.rego (base rules)
          ├→ dynamic_rate_limits.rego (rate limiting)
          ├→ contextual_auth.rego (context checks)
          ├→ tool_chain_governance.rego (chaining rules)
          ├→ data_governance.rego (data policies)
          └→ cost_control.rego (budget/quotas)
          ↓
    Decision Aggregation
          ↓
    Allow / Deny + Metadata
          ↓
    Tool Execution or Rejection
```

### 2. Agent-to-Agent Communication

```
A2A Request → Gateway API
              ↓
        A2A Authorization Middleware
              ↓
        Policy Evaluation (OPA)
              └→ a2a_authorization.rego
              ↓
        Decision
              ↓
        Allow / Deny + Restrictions
              ↓
        Communication Permitted or Blocked
```

## Policy Composition

### Layered Evaluation

Policies are evaluated in layers, each adding specific authorization constraints:

1. **Base Authorization** (`gateway_authorization.rego`)
   - Role-based access control (RBAC)
   - Sensitivity-based filtering
   - Time-based enforcement
   - Team-based access

2. **Rate Limiting** (`dynamic_rate_limits.rego`)
   - Per-user quotas
   - Per-tool limits
   - Server load adaptation
   - Token bucket algorithm

3. **Contextual Authorization** (`contextual_auth.rego`)
   - Time and location checks
   - Risk scoring
   - MFA requirements
   - Device trust

4. **Tool Chain Governance** (`tool_chain_governance.rego`)
   - Chain depth limits
   - Forbidden combinations
   - Resource accumulation
   - Pattern detection

5. **Data Governance** (`data_governance.rego`)
   - Data classification
   - PII protection
   - Cross-border transfers
   - Retention policies

6. **Cost Control** (`cost_control.rego`)
   - Budget enforcement
   - Quota management
   - Approval workflows
   - Chargeback attribution

### Policy Precedence

**Rule: ALL policies must allow for overall allow**

```rego
final_decision := {
    "allow": (
        gateway_auth.allow AND
        rate_limit.allow AND
        contextual.allow AND
        tool_chain.allow AND
        data_gov.allow AND
        cost_control.allow
    ),
    ...
}
```

## Input Schema

### Standard Input Structure

```json
{
  "user": {
    "id": "string",
    "email": "string",
    "role": "admin | developer | user",
    "teams": ["team-id"],
    "data_clearance": "public | internal | confidential | restricted",
    "known_devices": ["device-id"],
    "created_at": 1234567890
  },
  "action": "gateway:tool:invoke | gateway:server:register | a2a:communicate",
  "tool": {
    "name": "string",
    "sensitivity_level": "low | medium | high | critical",
    "category": "string",
    "data_classification": "string",
    "handles_pii": false,
    "estimated_duration_seconds": 10,
    "estimated_memory_mb": 100
  },
  "server": {
    "id": "string",
    "owner_id": "string",
    "managed_by_team": "team-id",
    "visibility": "public | internal | private",
    "environment": "development | staging | production"
  },
  "context": {
    "timestamp": 1234567890,
    "server_load": "low | normal | high | critical",
    "client_location": {
      "country_code": "US",
      "is_vpn": false,
      "is_proxy": false
    },
    "authentication": {
      "mfa_verified": true,
      "mfa_timestamp": 1234567890,
      "session_start": 1234567890,
      "last_activity": 1234567890
    },
    "rate_limit_data": {
      "current_window_count": 50,
      "window_start": 1234567890,
      "token_bucket": {
        "tokens": 100,
        "last_refill": 1234567890
      }
    },
    "budget_tracking": {
      "current_month_spent": 150.50
    }
  }
}
```

## Output Schema

### Authorization Decision

```json
{
  "allow": true,
  "reason": "string - explanation of decision",
  "filtered_parameters": {
    "key": "value"
  },
  "audit_id": "string",
  "rate_limit": {
    "limit": 1000,
    "remaining": 950,
    "reset_at": 1234567890
  },
  "context": {
    "risk_score": 15,
    "risk_level": "low",
    "device_trust": "trusted"
  },
  "warnings": ["string"],
  "required_actions": ["complete_mfa", "use_trusted_device"]
}
```

## Policy Best Practices

### 1. Default Deny

Always start with default deny:

```rego
default allow := false
```

### 2. Explicit Allow Rules

Define explicit conditions for allow:

```rego
allow if {
    # All conditions must be met
    condition1
    condition2
    condition3
}
```

### 3. Audit Reasons

Always provide audit reasons:

```rego
audit_reason := "Allowed: role-based access" if {
    allow
    input.user.role == "admin"
}

audit_reason := "Denied: insufficient permissions" if {
    not allow
}
```

### 4. Helper Functions

Use helper functions for reusability:

```rego
is_work_hours(ts) if {
    hour := time.clock(ts)[0]
    hour >= 9
    hour < 18
}
```

### 5. Structured Results

Return structured results with metadata:

```rego
result := {
    "allow": allow,
    "reason": audit_reason,
    "metadata": additional_info,
}
```

## Policy Testing

### Unit Tests

Test individual rules in isolation:

```rego
package mcp.gateway

test_admin_can_invoke_tools if {
    allow with input as {
        "user": {"role": "admin"},
        "action": "gateway:tool:invoke",
        "tool": {"sensitivity_level": "high"},
        "context": {"timestamp": 0}
    }
}
```

### Integration Tests

Test policy composition and conflicts.

### Performance Tests

Measure policy evaluation latency.

## Policy Deployment

### 1. Bundle Creation

```bash
cd opa/bundle
./build.sh
```

### 2. Bundle Upload

```bash
curl -X PUT http://opa:8181/v1/policies/gateway \
  --data-binary @bundle.tar.gz
```

### 3. Verification

```bash
curl http://opa:8181/v1/data/mcp/gateway/result \
  -d @test_input.json
```

## Monitoring & Observability

### Policy Decision Metrics

- Decision latency (P50, P95, P99)
- Allow/Deny ratios
- Policy evaluation errors
- Cache hit rates

### Audit Logging

All policy decisions are logged with:
- User ID
- Action
- Decision (allow/deny)
- Reason
- Timestamp
- Input hash (for replay)

## Troubleshooting

### Common Issues

1. **Policy conflicts**: Use `./validate_policies.py --check-conflicts`
2. **Slow evaluation**: Profile with OPA explain mode
3. **Unexpected denials**: Use `./simulate_policy.py --explain`
4. **Cache issues**: Check Redis connection and TTL settings

## References

- [OPA Documentation](https://www.openpolicyagent.org/docs)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [Gateway API Reference](../../gateway-integration/API_REFERENCE.md)
