# Policy Development: [Policy Name]

**Policy Type:** [RBAC | ABAC | Team-Based | Custom]
**Difficulty:** [Intermediate | Advanced]
**Estimated Time:** [30-90] minutes
**OPA Version:** [vX.X+]

---

## Overview

Learn how to develop and deploy a [policy type] policy for [use case description].

### Policy Goal

This policy will:
- [ ] [Requirement 1]
- [ ] [Requirement 2]
- [ ] [Requirement 3]
- [ ] [Requirement 4]

### Policy Logic

**Allow access when:**
- [Condition 1]
- [Condition 2]

**Deny access when:**
- [Condition 1]
- [Condition 2]

---

## Prerequisites

### Knowledge Requirements

- [ ] Basic understanding of [Rego language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [ ] Familiarity with SARK authorization model
- [ ] Understanding of [related concept]

### Environment Setup

```bash
# Install OPA CLI for local testing
brew install opa  # macOS
# or
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa

# Verify installation
opa version

# Set up policy directory
mkdir -p ~/sark-policies/[policy-name]
cd ~/sark-policies/[policy-name]
```

---

## Policy Requirements

### Business Rules

Document the business requirements this policy enforces:

1. **Rule 1:** [Description]
   - **Example:** Users with role "admin" can access all resources
   - **Rationale:** [Why this rule exists]

2. **Rule 2:** [Description]
   - **Example:** Users can only access resources in their team
   - **Rationale:** [Why this rule exists]

3. **Rule 3:** [Description]
   - **Example:** Critical resources require additional approval
   - **Rationale:** [Why this rule exists]

### Test Cases

Define test scenarios before writing policy:

| Scenario | User | Resource | Expected | Reason |
|----------|------|----------|----------|--------|
| [Scenario 1] | {role: "admin"} | {type: "server"} | ✅ Allow | Admins have full access |
| [Scenario 2] | {role: "user", team: "A"} | {type: "tool", team: "A"} | ✅ Allow | Same team access |
| [Scenario 3] | {role: "user", team: "A"} | {type: "tool", team: "B"} | ❌ Deny | Cross-team denied |
| [Scenario 4] | {role: "user"} | {type: "tool", sensitivity: "critical"} | ❌ Deny | Insufficient clearance |

---

## Step 1: Create Policy Skeleton

**Goal:** Set up the basic policy structure

Create `[policy-name].rego`:

```rego
package authz.[policy_name]

# Import common utilities (if available)
import data.utils.user_helpers
import data.utils.resource_helpers

# Default deny - security best practice
default allow = false

# Policy metadata
policy_info := {
    "name": "[Policy Name]",
    "version": "1.0.0",
    "description": "[Policy description]",
    "author": "[Your name]",
    "created": "[Date]"
}

# Main allow rule - placeholder
allow {
    # TODO: Implement policy logic
    false
}
```

**Test the skeleton:**

```bash
# Verify syntax
opa check [policy-name].rego

# Expected output: no errors
```

---

## Step 2: Implement Core Logic

**Goal:** Write the main policy rules

```rego
package authz.[policy_name]

default allow = false

# Rule 1: [Description]
allow {
    input.user.role == "admin"
}

# Rule 2: [Description]
allow {
    # User and resource are in the same team
    input.user.team_id == input.resource.team_id

    # User has required clearance level
    clearance_sufficient(input.user.clearance, input.resource.sensitivity)
}

# Rule 3: [Description]
allow {
    input.action == "read"
    input.resource.visibility == "public"
}

# Helper function: Check if user clearance is sufficient
clearance_sufficient(user_level, resource_level) {
    levels := ["low", "medium", "high", "critical"]
    user_index := indexof(levels, user_level)
    resource_index := indexof(levels, resource_level)
    user_index >= resource_index
}

# Helper function: Find index of element in array
indexof(arr, elem) = i {
    arr[i] == elem
}
```

**Explanation:**

- **Rule 1:** [Explanation of rule 1 logic]
- **Rule 2:** [Explanation of rule 2 logic]
- **Rule 3:** [Explanation of rule 3 logic]
- **Helper functions:** [Explanation of helpers]

---

## Step 3: Create Test Data

**Goal:** Set up test inputs for validation

Create `test-data.json`:

```json
{
  "test_cases": [
    {
      "name": "Admin access to any resource",
      "input": {
        "user": {
          "id": "user-001",
          "role": "admin",
          "team_id": "team-a",
          "clearance": "high"
        },
        "action": "update",
        "resource": {
          "type": "server",
          "id": "srv-001",
          "team_id": "team-b",
          "sensitivity": "critical"
        }
      },
      "expected": {
        "allow": true
      }
    },
    {
      "name": "Same team access",
      "input": {
        "user": {
          "id": "user-002",
          "role": "user",
          "team_id": "team-a",
          "clearance": "medium"
        },
        "action": "invoke",
        "resource": {
          "type": "tool",
          "id": "tool-001",
          "team_id": "team-a",
          "sensitivity": "medium"
        }
      },
      "expected": {
        "allow": true
      }
    },
    {
      "name": "Cross-team access denied",
      "input": {
        "user": {
          "id": "user-003",
          "role": "user",
          "team_id": "team-a",
          "clearance": "medium"
        },
        "action": "invoke",
        "resource": {
          "type": "tool",
          "id": "tool-002",
          "team_id": "team-b",
          "sensitivity": "medium"
        }
      },
      "expected": {
        "allow": false
      }
    }
  ]
}
```

---

## Step 4: Write Unit Tests

**Goal:** Create automated tests for the policy

Create `[policy-name]_test.rego`:

```rego
package authz.[policy_name]

# Test: Admin has full access
test_admin_full_access {
    allow with input as {
        "user": {"role": "admin", "team_id": "team-a"},
        "action": "update",
        "resource": {"type": "server", "team_id": "team-b"}
    }
}

# Test: Same team access allowed
test_same_team_access_allowed {
    allow with input as {
        "user": {
            "role": "user",
            "team_id": "team-a",
            "clearance": "medium"
        },
        "action": "invoke",
        "resource": {
            "type": "tool",
            "team_id": "team-a",
            "sensitivity": "medium"
        }
    }
}

# Test: Cross-team access denied
test_cross_team_access_denied {
    not allow with input as {
        "user": {"role": "user", "team_id": "team-a"},
        "action": "invoke",
        "resource": {"type": "tool", "team_id": "team-b"}
    }
}

# Test: Insufficient clearance denied
test_insufficient_clearance {
    not allow with input as {
        "user": {
            "role": "user",
            "team_id": "team-a",
            "clearance": "low"
        },
        "action": "invoke",
        "resource": {
            "type": "tool",
            "team_id": "team-a",
            "sensitivity": "critical"
        }
    }
}

# Test: Public read access
test_public_read_access {
    allow with input as {
        "user": {"role": "user"},
        "action": "read",
        "resource": {"type": "tool", "visibility": "public"}
    }
}

# Test clearance helper function
test_clearance_sufficient {
    clearance_sufficient("high", "medium")
    clearance_sufficient("critical", "critical")
    not clearance_sufficient("low", "high")
}
```

---

## Step 5: Test the Policy

### 5.1: Run Unit Tests

```bash
# Run all tests
opa test . -v

# Expected output:
# PASS: 6/6
```

### 5.2: Interactive Testing with REPL

```bash
# Start OPA REPL with policy loaded
opa run [policy-name].rego

# Test interactively
> data.authz.[policy_name].allow with input as {
    "user": {"role": "admin"},
    "action": "read",
    "resource": {"type": "server"}
  }
true

> data.authz.[policy_name].allow with input as {
    "user": {"role": "user", "team_id": "team-a"},
    "action": "invoke",
    "resource": {"type": "tool", "team_id": "team-b"}
  }
false
```

### 5.3: Test with Sample Data

```bash
# Test against JSON test cases
opa eval -d [policy-name].rego -d test-data.json \
  'data.authz.[policy_name].allow' \
  --input test-data.json
```

---

## Step 6: Deploy to SARK

### 6.1: Bundle the Policy

```bash
# Create policy bundle
opa build -b [policy-name].rego -o [policy-name].tar.gz

# Verify bundle
tar -tzf [policy-name].tar.gz
```

### 6.2: Upload to SARK

```bash
# Upload policy via API
curl -X POST "${SARK_API_URL}/api/v1/policies" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -F "file=@[policy-name].tar.gz" \
  -F "name=[policy-name]" \
  -F "description=[Policy description]" \
  -F "enabled=false"  # Start disabled for testing
```

### 6.3: Test in Staging

```bash
# Enable policy in staging environment
curl -X PATCH "${SARK_API_URL}/api/v1/policies/[policy-id]" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -d '{"enabled": true, "environment": "staging"}'

# Test authorization decisions
curl -X POST "${SARK_API_URL}/api/v1/policies/[policy-id]/test" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @test-data.json
```

---

## Step 7: Monitor and Iterate

### 7.1: Enable Policy Metrics

```bash
# Configure policy telemetry
curl -X PATCH "${SARK_API_URL}/api/v1/policies/[policy-id]" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -d '{
    "telemetry": {
      "enabled": true,
      "log_decisions": true,
      "log_level": "debug"
    }
  }'
```

### 7.2: View Policy Decisions

```bash
# Fetch policy decision logs
curl -X GET "${SARK_API_URL}/api/v1/policies/[policy-id]/logs" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  | jq '.[] | select(.result == false) | {input, reason}'
```

### 7.3: Analyze Policy Performance

```bash
# Get policy performance metrics
curl -X GET "${SARK_API_URL}/api/v1/policies/[policy-id]/metrics" \
  -H "Authorization: Bearer ${SARK_API_KEY}"
```

**Key metrics to monitor:**
- Evaluation latency (p50, p95, p99)
- Decision distribution (allow vs deny)
- Cache hit rate
- Error rate

---

## Best Practices

### 1. Security

- ✅ **Default deny:** Always start with `default allow = false`
- ✅ **Explicit rules:** Make all allow conditions explicit
- ✅ **Principle of least privilege:** Grant minimum necessary access
- ✅ **Defense in depth:** Layer multiple checks

### 2. Performance

- ✅ **Early returns:** Put most restrictive rules first
- ✅ **Indexing:** Use indexed lookups when possible
- ✅ **Caching:** Enable policy result caching
- ✅ **Avoid loops:** Use built-in functions instead of iteration

### 3. Maintainability

- ✅ **Comments:** Document complex logic
- ✅ **Helper functions:** Extract reusable logic
- ✅ **Consistent naming:** Use clear, consistent names
- ✅ **Versioning:** Track policy versions

### 4. Testing

- ✅ **Comprehensive tests:** Cover all code paths
- ✅ **Edge cases:** Test boundary conditions
- ✅ **Negative tests:** Verify denial cases
- ✅ **CI/CD:** Automate policy testing

---

## Troubleshooting

### Policy Not Working

```bash
# Check policy syntax
opa check [policy-name].rego

# View detailed evaluation trace
opa eval -d [policy-name].rego \
  --explain full \
  --format pretty \
  'data.authz.[policy_name].allow' \
  --input <(echo '{"user": {...}, "resource": {...}}')
```

### Performance Issues

```bash
# Profile policy execution
opa eval -d [policy-name].rego \
  --profile \
  --format pretty \
  'data.authz.[policy_name].allow' \
  --input test-input.json
```

### Debugging Tips

1. **Use `trace()` function:**
   ```rego
   allow {
       trace(sprintf("Checking user %v", [input.user.id]))
       # ... rest of logic
   }
   ```

2. **Test individual rules:**
   ```bash
   opa eval -d policy.rego 'data.authz.policy.rule_name'
   ```

3. **Visualize policy:**
   ```bash
   opa deps -d policy.rego data.authz.policy.allow | dot -Tpng > graph.png
   ```

---

## Next Steps

- **Advanced Policies:** [Link to advanced policy guide]
- **Policy Composition:** [Link to policy composition guide]
- **Custom Functions:** [Link to custom function development]
- **Production Deployment:** [Link to production best practices]

---

## References

- [OPA Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [OPA Built-in Functions](https://www.openpolicyagent.org/docs/latest/policy-reference/)
- [SARK Policy Guide](../../OPA_POLICY_GUIDE.md)
- [Authorization Model](../../AUTHORIZATION.md)

---

**Tutorial Info:**
- **Last Updated:** [Date]
- **OPA Version:** [Version]
- **Policy Version:** [Version]
- **Author:** [Name]
