# OPA Policy Authoring Guide

**Enterprise Policy Development for SARK MCP Governance**

---

## Table of Contents

1. [Introduction to OPA](#introduction-to-opa)
2. [Policy Architecture](#policy-architecture)
3. [Writing Effective Policies](#writing-effective-policies)
4. [Testing & Validation](#testing--validation)
5. [Policy Deployment](#policy-deployment)
6. [Best Practices](#best-practices)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Techniques](#advanced-techniques)

---

## Introduction to OPA

### What is Open Policy Agent?

Open Policy Agent (OPA) is a general-purpose policy engine that enables unified, context-aware policy enforcement across SARK. Policies are written in **Rego**, a declarative query language.

**Key Benefits:**
- **Declarative** - Describe what should be allowed, not how to enforce
- **Context-Aware** - Policies can access rich context (user, time, resource)
- **Testable** - Built-in testing framework
- **Performance** - Sub-millisecond policy evaluation
- **Versioned** - Policies stored in Git, versioned like code

### SARK Policy Architecture

```
┌────────────────────────────────────────────────────────┐
│ Policy Decision Point (PDP) - OPA                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│
│  │ MCP Policy   │  │ Admin Policy │  │ Audit Policy ││
│  │ (authorization)│  │ (management) │  │ (compliance) ││
│  └──────────────┘  └──────────────┘  └──────────────┘│
│                                                         │
│  Data Sources:                                          │
│  - PostgreSQL (users, teams, servers)                   │
│  - Redis (cached attributes)                            │
│  - External APIs (directory services)                   │
└────────────────────────────────────────────────────────┘
```

---

## Policy Architecture

### Package Structure

```
opa/policies/
├── mcp/
│   ├── authorization.rego      # Core MCP authorization
│   ├── tool_access.rego        # Tool-specific rules
│   ├── server_mgmt.rego        # Server management policies
│   └── data_classification.rego # Sensitivity-based rules
├── admin/
│   ├── user_management.rego    # User administration
│   ├── policy_management.rego  # Policy CRUD operations
│   └── audit_access.rego       # Audit log access control
├── compliance/
│   ├── soc2.rego              # SOC 2 compliance rules
│   ├── gdpr.rego              # GDPR data protection
│   └── industry.rego          # Industry-specific (HIPAA, PCI)
├── helpers/
│   ├── time_utils.rego        # Time-based functions
│   ├── team_utils.rego        # Team hierarchy functions
│   └── risk_scoring.rego      # Risk assessment utilities
└── tests/
    ├── authorization_test.rego
    ├── tool_access_test.rego
    └── compliance_test.rego
```

### Policy Namespacing

```rego
# Package declaration - defines policy namespace
package mcp.authorization

# All rules in this file belong to mcp.authorization package
# Accessed via: /v1/data/mcp/authorization
```

---

## Writing Effective Policies

### Basic Policy Structure

```rego
package mcp.authorization

import future.keywords.if
import future.keywords.in

# Default deny - fail-safe security
default allow := false

# Rule: Tool owner always has access
allow if {
    input.action == "tool:invoke"
    input.tool.owner == input.user.id
}

# Rule: Team members can access team tools
allow if {
    input.action == "tool:invoke"
    some team_id in input.user.teams
    team_id in input.tool.managers
}

# Audit trail - always generate reason
audit_reason := sprintf("Allowed: %s by %s", [input.action, input.user.email]) if allow
audit_reason := sprintf("Denied: %s by %s", [input.action, input.user.email]) if not allow
```

### Input Schema

**Expected Input Structure:**

```json
{
  "user": {
    "id": "user-123",
    "email": "alice@company.com",
    "role": "developer",
    "teams": ["team-A", "team-B"],
    "attributes": {
      "department": "engineering",
      "clearance_level": "confidential"
    }
  },
  "action": "tool:invoke",
  "tool": {
    "id": "tool-xyz",
    "name": "database_query",
    "sensitivity_level": "high",
    "owner": "user-456",
    "managers": ["team-A"]
  },
  "resource": {
    "type": "mcp_server",
    "id": "server-789"
  },
  "context": {
    "timestamp": 1700000000,
    "ip_address": "10.0.1.45",
    "request_id": "req-abc"
  }
}
```

### Conditional Logic

```rego
# AND conditions - all must be true
allow if {
    input.action == "tool:invoke"
    input.user.role == "developer"
    input.tool.sensitivity_level == "low"
}

# OR conditions - at least one must be true
allow if {
    input.user.role == "admin"
}

allow if {
    input.user.id == input.tool.owner
}

# NOT conditions
deny if {
    not is_work_hours(input.context.timestamp)
    input.tool.sensitivity_level == "critical"
}
```

### Functions and Helpers

```rego
# Helper function: Check if within work hours
is_work_hours(ts) if {
    ts > 0
    hour := time.clock([ts])[0]
    hour >= 9
    hour < 18
}

# Helper function: Check team membership
user_in_team(user_id, team_id) if {
    some team in data.teams
    team.id == team_id
    some member in team.members
    member.id == user_id
}

# Helper function: Calculate risk score
risk_score(user, action, resource) := score if {
    # Base score
    base := 0

    # Add points for high sensitivity
    sensitivity_points := 50 if resource.sensitivity_level == "high" else 0

    # Add points for after-hours access
    time_points := 30 if not is_work_hours(input.context.timestamp) else 0

    # Add points for unknown IP
    ip_points := 20 if not is_known_ip(input.context.ip_address) else 0

    score := base + sensitivity_points + time_points + ip_points
}
```

---

## Testing & Validation

### Unit Tests

```rego
package mcp.authorization_test

import future.keywords.if

# Test: Owner can access their tools
test_owner_access if {
    allow with input as {
        "action": "tool:invoke",
        "user": {"id": "user-123", "role": "developer", "teams": []},
        "tool": {"name": "test", "owner": "user-123", "sensitivity_level": "low"},
        "context": {"timestamp": 0}
    }
}

# Test: Non-owner denied
test_non_owner_denied if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {"id": "user-456", "role": "developer", "teams": []},
        "tool": {"name": "test", "owner": "user-123", "sensitivity_level": "low"},
        "context": {"timestamp": 0}
    }
}

# Test: Team member can access team tools
test_team_access if {
    allow with input as {
        "action": "tool:invoke",
        "user": {"id": "user-789", "role": "developer", "teams": ["team-A"]},
        "tool": {"name": "test", "owner": "user-123", "managers": ["team-A"]},
        "context": {"timestamp": 0}
    }
}

# Test: After-hours blocked for sensitive tools
test_after_hours_blocked if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {"id": "user-123", "role": "developer", "teams": []},
        "tool": {"name": "test", "owner": "user-123", "sensitivity_level": "critical"},
        "context": {"timestamp": 1700000000}  # 2023-11-14 22:13:20 UTC (after hours)
    }
}
```

### Running Tests

```bash
# Run all tests
opa test opa/policies/ -v

# Run specific test file
opa test opa/policies/tests/authorization_test.rego -v

# Run with coverage
opa test opa/policies/ --coverage --format=json

# Expected output:
# PASS: 15/15
# Coverage: 92.5%
```

### Test Coverage

```bash
# Generate coverage report
opa test opa/policies/ --coverage --format=json > coverage.json

# View coverage
cat coverage.json | jq '.coverage'
```

**Target Coverage:** >90% for production policies

---

## Policy Deployment

### GitOps Workflow

```
┌──────────────┐
│ Developer    │
│ writes policy│
└──────┬───────┘
       │
       ├─ 1. Create feature branch
       ├─ 2. Write policy + tests
       ├─ 3. Run local tests
       ├─ 4. Submit PR
       │
┌──────▼───────┐
│ CI/CD        │
│ Pipeline     │
└──────┬───────┘
       │
       ├─ 5. Lint policy (opa fmt)
       ├─ 6. Run tests (opa test)
       ├─ 7. Security scan (conftest)
       ├─ 8. Build bundle
       │
┌──────▼───────┐
│ Review &     │
│ Approval     │
└──────┬───────┘
       │
       ├─ 9. Security team review
       ├─ 10. Merge to main
       │
┌──────▼───────┐
│ Deployment   │
└──────┬───────┘
       │
       ├─ 11. Bundle to OPA servers
       ├─ 12. Canary deployment
       └─ 13. Monitor policy decisions
```

### Policy Bundles

```bash
# Create policy bundle
opa build opa/policies/ \
    --bundle \
    --output bundle.tar.gz

# Sign bundle (optional but recommended)
opa sign bundle.tar.gz \
    --signing-key private-key.pem \
    --output-file-path signatures.json

# Deploy to OPA
curl -X PUT http://opa:8181/v1/policies/sark \
    --data-binary @bundle.tar.gz
```

### ConfigMap Deployment (Kubernetes)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opa-policies
  namespace: sark-system
data:
  authorization.rego: |
    package mcp.authorization
    import future.keywords.if
    # ... policy content ...

  tool_access.rego: |
    package mcp.tool_access
    # ... policy content ...
```

### Dynamic Policy Updates

```python
# Python example: Update policies via API
import requests

def deploy_policy(policy_name: str, policy_content: str):
    """Deploy policy to OPA."""
    response = requests.put(
        f"http://opa:8181/v1/policies/{policy_name}",
        data=policy_content,
        headers={"Content-Type": "text/plain"}
    )

    if response.status_code == 200:
        print(f"Policy {policy_name} deployed successfully")
    else:
        print(f"Deployment failed: {response.text}")

# Deploy from file
with open("opa/policies/mcp/authorization.rego") as f:
    deploy_policy("mcp-authorization", f.read())
```

---

## Best Practices

### 1. Always Default Deny

```rego
# GOOD - Explicit default deny
package mcp.authorization

default allow := false

allow if {
    # Explicit conditions for allow
}

# BAD - Implicit allow
package mcp.authorization

allow if {
    # ...
}
# Missing default deny means undefined = allow
```

### 2. Use Descriptive Rule Names

```rego
# GOOD - Clear intent
allow_tool_owner if {
    input.tool.owner == input.user.id
}

allow_team_member if {
    some team in input.user.teams
    team in input.tool.managers
}

# BAD - Unclear
rule1 if { ... }
rule2 if { ... }
```

### 3. Comprehensive Audit Trails

```rego
# Generate detailed audit reasons
audit_reason := reason if {
    allow
    reason := sprintf(
        "Allowed: User %s (%s) invoked tool %s owned by %s",
        [input.user.id, input.user.email, input.tool.name, input.tool.owner]
    )
}

audit_reason := reason if {
    not allow
    reason := sprintf(
        "Denied: User %s lacks permission for tool %s (sensitivity: %s)",
        [input.user.id, input.tool.name, input.tool.sensitivity_level]
    )
}
```

### 4. Separate Concerns

```rego
# authorization.rego - Core authorization logic
package mcp.authorization

# data_classification.rego - Sensitivity handling
package mcp.data_classification

# time_restrictions.rego - Temporal policies
package mcp.time_restrictions
```

### 5. Use External Data Carefully

```rego
# Query external data (PostgreSQL, Redis)
allow if {
    # Get user's clearance level from external database
    clearance := data.users[input.user.id].clearance_level

    # Check against required clearance
    required_clearance := data.tools[input.tool.id].required_clearance

    clearance_hierarchy[clearance] >= clearance_hierarchy[required_clearance]
}

# Define clearance hierarchy
clearance_hierarchy := {
    "public": 0,
    "confidential": 1,
    "secret": 2,
    "top_secret": 3
}
```

### 6. Performance Optimization

```rego
# GOOD - Early termination
allow if {
    # Check cheap conditions first
    input.action == "tool:invoke"

    # Then expensive lookups
    user_has_permission(input.user.id, input.tool.id)
}

# BAD - Expensive operation first
allow if {
    # This queries database every time
    user_has_permission(input.user.id, input.tool.id)

    # Cheap check should be first
    input.action == "tool:invoke"
}
```

---

## Common Patterns

### Pattern 1: Time-Based Access Control

```rego
package mcp.time_restrictions

import future.keywords.if

# Business hours: Monday-Friday, 9 AM - 6 PM
is_business_hours(ts) if {
    ts > 0
    date := time.date([ts])
    weekday := time.weekday([ts])

    # Monday = 1, Friday = 5
    weekday >= 1
    weekday <= 5

    hour := time.clock([ts])[0]
    hour >= 9
    hour < 18
}

# Allow critical tools only during business hours
deny if {
    input.tool.sensitivity_level == "critical"
    not is_business_hours(input.context.timestamp)
}
```

### Pattern 2: Hierarchical Teams

```rego
package mcp.team_hierarchy

# Check if user is in team or parent team
user_in_team_hierarchy(user_id, team_id) if {
    # Direct membership
    user_in_team(user_id, team_id)
}

user_in_team_hierarchy(user_id, team_id) if {
    # Parent team membership
    parent_team := data.teams[team_id].parent
    parent_team != null
    user_in_team_hierarchy(user_id, parent_team)
}

# Allow access if user is in team hierarchy
allow if {
    input.action == "tool:invoke"
    user_in_team_hierarchy(input.user.id, input.tool.team_id)
}
```

### Pattern 3: Attribute-Based Access Control (ABAC)

```rego
package mcp.abac

# Define attribute-based rules
allow if {
    # User attributes
    input.user.attributes.department == "engineering"
    input.user.attributes.clearance_level == "confidential"

    # Resource attributes
    input.tool.attributes.department == "engineering"
    input.tool.attributes.data_classification == "confidential"

    # Environmental attributes
    is_corporate_network(input.context.ip_address)
}

is_corporate_network(ip) if {
    net.cidr_contains("10.0.0.0/8", ip)
}
```

### Pattern 4: Risk-Based Access Control

```rego
package mcp.risk_based

# Calculate risk score (0-100)
risk_score := score if {
    base := 0

    # User risk factors
    user_risk := user_risk_score(input.user)

    # Resource risk factors
    resource_risk := resource_risk_score(input.tool)

    # Context risk factors
    context_risk := context_risk_score(input.context)

    score := user_risk + resource_risk + context_risk
}

# Allow if risk is acceptable
allow if {
    risk_score < 50  # Low risk threshold
}

# Require MFA for medium risk
require_mfa if {
    risk_score >= 50
    risk_score < 75
}

# Deny for high risk
deny if {
    risk_score >= 75
}
```

### Pattern 5: Data Residency & Sovereignty

```rego
package mcp.data_residency

# European users can only access EU servers
allow if {
    input.user.attributes.region == "EU"
    input.resource.attributes.region == "EU"
}

# GDPR-protected data stays in EU
deny if {
    input.resource.attributes.gdpr_protected == true
    input.resource.attributes.region != "EU"
}
```

---

## Troubleshooting

### Debugging Policies

```bash
# Interactive REPL
opa run opa/policies/

# In REPL, test specific input
> input := {
    "action": "tool:invoke",
    "user": {"id": "user-123", "role": "developer"},
    "tool": {"name": "test", "owner": "user-123"}
  }

> data.mcp.authorization.allow
true

# Trace policy evaluation
> trace
> data.mcp.authorization.allow
```

### Common Errors

**Error: Undefined reference**
```rego
# Error
allow if {
    user.id == tool.owner  # 'user' not defined
}

# Fix
allow if {
    input.user.id == input.tool.owner
}
```

**Error: Recursion limit**
```rego
# Error - infinite recursion
is_admin(user) if {
    is_admin(user)  # Calls itself
}

# Fix - Add base case
is_admin(user) if {
    user.role == "admin"
}

is_admin(user) if {
    some manager in user.managers
    is_admin(manager)  # Recursive with base case
}
```

**Error: Type mismatch**
```rego
# Error
allow if {
    input.user.teams == "team-A"  # teams is array, not string
}

# Fix
allow if {
    some team in input.user.teams
    team == "team-A"
}
```

### Performance Profiling

```bash
# Profile policy execution
opa eval data.mcp.authorization.allow \
    --profile \
    --input input.json \
    --data opa/policies/

# Output shows timing for each rule
```

---

## Advanced Techniques

### Partial Evaluation

```rego
# Pre-compile policies for specific users
package mcp.authorization

# This will be partially evaluated for each user
allow if {
    input.user.id == "user-123"  # Will be compiled to true/false
    input.action == "tool:invoke"
}
```

### Policy Composition

```rego
# Combine multiple policy decisions
package mcp.combined

import data.mcp.authorization
import data.mcp.time_restrictions
import data.mcp.risk_based

# Final decision considers all policies
final_decision := {
    "allow": allow,
    "reason": reason,
    "require_mfa": require_mfa
}

allow if {
    authorization.allow
    time_restrictions.allow
    risk_based.allow
}

require_mfa if {
    risk_based.require_mfa
}
```

### External Data Sources

```rego
package mcp.external_data

# Query PostgreSQL via HTTP
user_clearance := clearance if {
    response := http.send({
        "method": "GET",
        "url": sprintf("http://postgres-api:8080/users/%s/clearance", [input.user.id]),
        "headers": {"Authorization": "Bearer token"}
    })

    response.status_code == 200
    clearance := response.body.clearance_level
}
```

---

## Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [OPA Playground](https://play.openpolicyagent.org/)
- [Policy Library](https://github.com/open-policy-agent/library)

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Next Review:** February 2026
**Owner:** Security & Platform Team
