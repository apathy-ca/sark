# Engineer 3: OPA Policies & Policy Service

**Branch:** `feat/gateway-policies`
**Duration:** 6-8 days
**Focus:** OPA policy development and testing
**Dependencies:** Shared models (Day 1)

---

## Setup

```bash
git checkout -b feat/gateway-policies
git pull origin feat/gateway-client  # Get shared models
mkdir -p opa/policies
mkdir -p opa/tests
```

---

## Tasks Overview

### Day 1-3: Gateway Authorization Policy
### Day 4-5: A2A Authorization Policy
### Day 6: Policy Testing & Optimization

---

## Detailed Tasks

### Task 1: Gateway Authorization Policy

**File:** `opa/policies/gateway_authorization.rego`

See full policy spec in main integration plan. Key rules:
- Admin can invoke non-critical tools
- Developer can invoke low/medium sensitivity tools
- Team-based access for team-managed servers
- Parameter filtering logic
- Work hours enforcement

**Checklist:**
- [ ] Package `mcp.gateway` defined
- [ ] Default deny rule
- [ ] All authorization rules implemented
- [ ] Parameter filtering function
- [ ] Helper functions (is_work_hours, server_access_allowed)
- [ ] Audit reason generation

---

### Task 2: A2A Authorization Policy

**File:** `opa/policies/a2a_authorization.rego`

Key rules:
- Trusted agents can communicate
- Capability enforcement (execute, query, delegate)
- Cross-environment blocking
- Agent type rules (service→worker)
- Rate limit checks

**Checklist:**
- [ ] Package `mcp.gateway.a2a` defined
- [ ] Trust level rules
- [ ] Capability rules
- [ ] Restriction rules
- [ ] Audit reason generation

---

### Task 3: OPA Policy Tests

**File:** `opa/policies/gateway_authorization_test.rego`

```rego
package mcp.gateway

test_admin_can_invoke_tools {
    allow with input as {
        "user": {"role": "admin", "id": "admin1"},
        "action": "gateway:tool:invoke",
        "tool": {"sensitivity_level": "high"},
        "context": {"timestamp": 0}
    }
}

test_developer_blocked_on_critical {
    not allow with input as {
        "user": {"role": "developer", "id": "dev1"},
        "action": "gateway:tool:invoke",
        "tool": {"sensitivity_level": "critical"},
        "context": {"timestamp": 0}
    }
}

# Add 15+ test cases covering all rules
```

**Checklist:**
- [ ] Test admin authorization
- [ ] Test developer restrictions
- [ ] Test team-based access
- [ ] Test parameter filtering
- [ ] Test work hours enforcement
- [ ] Test sensitivity levels
- [ ] Coverage >90%

---

### Task 4: Policy Service Extensions

**File:** `src/sark/services/policy/opa_client.py` (additions)

Add methods:

```python
async def evaluate_gateway_policy(
    self,
    user_context: dict,
    action: str,
    server: dict | None = None,
    tool: dict | None = None,
    context: dict | None = None,
) -> AuthorizationDecision:
    """Evaluate Gateway-specific policy."""
    auth_input = AuthorizationInput(
        user=user_context,
        action=action,
        server=server,
        tool=tool,
        context=context or {},
    )
    return await self.evaluate_policy(auth_input)


async def batch_evaluate_gateway(
    self,
    requests: list[tuple[dict, str, dict | None, dict | None]],
) -> list[AuthorizationDecision]:
    """Batch evaluate Gateway authorizations."""
    auth_inputs = [
        AuthorizationInput(user=u, action=a, server=s, tool=t, context={})
        for u, a, s, t in requests
    ]
    return await self.evaluate_policy_batch(auth_inputs)
```

---

### Task 5: Policy Bundle

**File:** `opa/bundle/.manifest`

```json
{
  "revision": "v1.0.0",
  "roots": ["mcp", "mcp/gateway", "mcp/gateway/a2a"]
}
```

**Build script:** `opa/bundle/build.sh`

```bash
#!/bin/bash
opa build -b opa/policies -o opa/bundle/bundle.tar.gz
```

---

## Testing

```bash
# Run OPA tests
opa test opa/policies/*.rego -v

# Expected output: All tests pass
```

---

## Delivery Checklist

- [ ] Gateway authorization policy complete
- [ ] A2A authorization policy complete
- [ ] All policy tests pass
- [ ] Policy service methods added
- [ ] Policy bundle builds
- [ ] Documentation updated
- [ ] PR created

---

## PR Description

```markdown
## OPA Policies for Gateway Integration

### Summary
Implements Open Policy Agent policies for Gateway and A2A authorization.

### Policies
- Gateway tool invocation authorization
- A2A communication authorization
- Parameter filtering
- Sensitivity-based access control

### Testing
```bash
opa test opa/policies/ -v
pytest tests/unit/services/policy/ -v
```

### Policy Examples
See docs/gateway-integration/POLICY_GUIDE.md
```

Ready! 🚀
