# Tutorial 3: OPA Policy Development

**Duration:** 45 minutes
**Difficulty:** Intermediate
**Prerequisites:** Completion of Tutorial 1 (Basic Setup)

## What You'll Learn

In this tutorial, you'll:
1. Understand OPA (Open Policy Agent) and Rego policy language
2. Write custom authorization policies for SARK
3. Test policies locally with the OPA CLI
4. Deploy policies to SARK
5. Implement common access control patterns:
   - Role-based access control (RBAC)
   - Time-based access (business hours only)
   - SQL injection prevention
   - Parameter filtering and data masking
   - MFA requirements for critical operations

By the end, you'll be able to write production-ready policies that govern MCP tool access.

---

## Prerequisites

### Required

- Completed [Tutorial 1: Basic Setup](../01-basic-setup/README.md)
- SARK running with minimal profile
- OPA CLI installed (installation instructions below)
- Text editor (VS Code with OPA extension recommended)

### Install OPA CLI

```bash
# macOS
brew install opa

# Linux
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa
sudo mv opa /usr/local/bin/

# Windows (PowerShell)
Invoke-WebRequest -Uri https://openpolicyagent.org/downloads/latest/opa_windows_amd64.exe -OutFile opa.exe

# Verify installation
opa version
# Expected: Version 0.60.0 or later
```

### Install VS Code Extension (Optional but Recommended)

1. Open VS Code
2. Install "Open Policy Agent" extension
3. Enjoy syntax highlighting, autocomplete, and inline errors

---

## Architecture: How OPA Fits in SARK

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool Invocation Flow                      │
└─────────────────────────────────────────────────────────────┘

1. User → SARK API
   POST /api/v1/servers/{id}/tools/{tool}/invoke

2. SARK → OPA (Policy Evaluation)
   POST http://opa:8181/v1/data/mcp/allow
   {
     "input": {
       "user": {"roles": ["developer"], "teams": [...]}
       "action": "tool:invoke",
       "tool": {"sensitivity_level": "high"},
       "arguments": {"query": "SELECT * FROM users"}
     }
   }

3. OPA → Policy Engine (Rego Evaluation)
   - Evaluates all loaded policies
   - Checks allow rules
   - Checks deny rules
   - Returns decision + reason

4. OPA → SARK (Decision)
   {
     "result": {
       "allow": true,
       "deny": false,
       "audit_reason": "Allowed: Developer role with team access"
     }
   }

5. SARK → Audit Log (TimescaleDB)
   Records decision, user, tool, parameters, timestamp

6. SARK → User (Allow) OR User (Deny)
   200 OK + tool result  OR  403 Forbidden + reason
```

**Key Concepts:**
- **Default Deny:** If no policy explicitly allows, request is denied
- **Deny Overrides Allow:** If any deny rule matches, request is denied (even if allow rule matches)
- **Policy Caching:** Decisions cached for 5 minutes (configurable)
- **Complete Audit:** Every decision logged regardless of outcome

---

## Step 1: Understanding Rego Basics

Rego is OPA's declarative policy language. Let's learn by example.

### Hello World Policy

Create `hello.rego`:

```rego
package hello

# A simple allow rule
allow if {
    input.user == "alice"
}
```

Test it:

```bash
# Create input file
echo '{"user": "alice"}' > input.json

# Evaluate policy
opa eval -i input.json -d hello.rego "data.hello.allow"

# Expected output:
# {
#   "result": [
#     {
#       "expressions": [
#         {
#           "value": true
#           ...
#         }
#       ]
#     }
#   ]
# }
```

### Key Rego Concepts

**1. Packages:** Organize policies into namespaces
```rego
package mcp.authorization  # Creates namespace mcp.authorization
```

**2. Rules:** Define conditions for decisions
```rego
allow if {              # Rule named "allow"
    input.user == "bob"  # Condition
}
```

**3. Default Values:** Fail-safe defaults
```rego
default allow := false  # Deny by default (secure!)
```

**4. Logical AND:** All conditions must be true
```rego
allow if {
    input.role == "admin"     # AND
    input.clearance == "top"  # AND
    input.verified == true    # All must be true
}
```

**5. Logical OR:** Multiple rules with same name
```rego
# Either rule allows
allow if { input.role == "admin" }
allow if { input.role == "owner" }
```

**6. Arrays and Objects:**
```rego
allow if {
    # Check if value is in array
    "developer" in input.user.roles

    # Access object property
    input.tool.sensitivity_level == "low"
}
```

**7. Iteration:**
```rego
allow if {
    # Check if any team matches
    some team in input.user.teams
    team == "engineering"
}
```

**8. Helper Functions:**
```rego
# Define a function
is_weekend(timestamp) if {
    weekday := time.weekday([timestamp])
    weekday == 0  # Sunday
}

is_weekend(timestamp) if {
    weekday := time.weekday([timestamp])
    weekday == 6  # Saturday
}

# Use the function
deny if {
    is_weekend(input.timestamp)
}
```

---

## Step 2: Your First SARK Policy

Let's write a policy that allows developers to query the analytics database, but denies DELETE operations.

### Create the Policy

Create `tutorials/03-policies/my_first_policy.rego`:

```rego
# My First SARK Policy
# Allows developers to run SELECT queries on analytics database
# Denies all DELETE, UPDATE, INSERT operations

package mcp.custom

import future.keywords.if
import future.keywords.in

# Default deny - fail-safe security
default allow := false

# Rule 1: Developers can invoke database query tools
allow if {
    "developer" in input.user.roles
    input.action == "tool:invoke"
    input.tool.name == "execute_query"
}

# Rule 2: Deny dangerous SQL keywords
dangerous_keywords := ["DELETE", "UPDATE", "INSERT", "DROP", "TRUNCATE"]

deny if {
    input.tool.name == "execute_query"
    query := upper(input.arguments.query)
    some keyword in dangerous_keywords
    contains(query, keyword)
}

# Helper: Check if string contains substring
contains(str, substr) if {
    indexof(str, substr) != -1
}

# Helper: Convert to uppercase
upper(str) := upper_str if {
    upper_str := upper(str)
}

# Audit reason for logging
audit_reason := "Allowed: Developer executing SELECT query" if {
    allow
    not deny
}

audit_reason := "Denied: Dangerous SQL keyword detected" if {
    deny
}

audit_reason := "Denied: Insufficient permissions" if {
    not allow
    not deny
}
```

### Test the Policy Locally

Create `input-allow.json`:
```json
{
  "user": {
    "id": "john.doe",
    "roles": ["developer", "team_lead"]
  },
  "action": "tool:invoke",
  "tool": {
    "name": "execute_query",
    "sensitivity_level": "medium"
  },
  "arguments": {
    "query": "SELECT * FROM users WHERE status = 'active'",
    "database": "analytics"
  }
}
```

Create `input-deny.json`:
```json
{
  "user": {
    "id": "john.doe",
    "roles": ["developer"]
  },
  "action": "tool:invoke",
  "tool": {
    "name": "execute_query"
  },
  "arguments": {
    "query": "DELETE FROM users WHERE id = 1"
  }
}
```

Test with OPA CLI:

```bash
# Test allow case
opa eval -i input-allow.json -d my_first_policy.rego "data.mcp.custom"

# Expected:
# "allow": true
# "deny": false
# "audit_reason": "Allowed: Developer executing SELECT query"

# Test deny case
opa eval -i input-deny.json -d my_first_policy.rego "data.mcp.custom"

# Expected:
# "allow": true  # Rule 1 allows
# "deny": true   # Rule 2 denies (deny wins!)
# "audit_reason": "Denied: Dangerous SQL keyword detected"
```

🎉 **Success!** You've written and tested your first policy.

---

## Step 3: Deploy Policy to SARK

Now let's deploy the policy and test it with real API calls.

### Copy Policy to OPA Directory

```bash
# From sark/ directory
cp tutorials/03-policies/my_first_policy.rego opa/policies/custom/

# Restart OPA to reload policies
docker compose restart opa

# Wait for OPA to be healthy
docker compose ps opa
```

### Test with SARK API

First, authenticate:

```bash
# Login as john.doe (developer)
export ACCESS_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username": "john.doe", "password": "password"}' | jq -r '.access_token')
```

Test allow case (SELECT query):

```bash
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "john.doe",
    "action": "tool:invoke",
    "tool": "execute_query",
    "arguments": {
      "query": "SELECT * FROM users WHERE status = '\''active'\''",
      "database": "analytics"
    }
  }' | jq

# Expected:
# {
#   "decision": "allow",
#   "reason": "Allowed: Developer executing SELECT query"
# }
```

Test deny case (DELETE query):

```bash
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "john.doe",
    "action": "tool:invoke",
    "tool": "execute_query",
    "arguments": {
      "query": "DELETE FROM users WHERE id = 1",
      "database": "analytics"
    }
  }' | jq

# Expected:
# {
#   "decision": "deny",
#   "reason": "Denied: Dangerous SQL keyword detected"
# }
```

🎉 **Success!** Your policy is live and protecting the database.

---

## Step 4: Time-Based Access Control

Let's implement a policy that only allows high-sensitivity tool access during business hours (9 AM - 6 PM, Monday-Friday).

### Create the Policy

Create `business_hours.rego`:

```rego
package mcp.business_hours

import future.keywords.if

default allow := false

# Allow high-sensitivity tools during business hours only
allow if {
    input.tool.sensitivity_level == "high"
    "team_lead" in input.user.roles
    is_business_hours(input.context.timestamp)
    is_weekday(input.context.timestamp)
}

# Check if timestamp is 9 AM - 6 PM
is_business_hours(timestamp) if {
    hour := time.clock([timestamp])[0]  # Get hour
    hour >= 9
    hour < 18
}

# Check if timestamp is Monday-Friday
is_weekday(timestamp) if {
    day := time.weekday([timestamp])
    day >= 1  # Monday
    day <= 5  # Friday
}

# Audit reasons
audit_reason := "Allowed: Business hours access" if {
    allow
}

audit_reason := "Denied: Outside business hours (9 AM - 6 PM)" if {
    not is_business_hours(input.context.timestamp)
    input.tool.sensitivity_level == "high"
}

audit_reason := "Denied: Weekend access not allowed" if {
    not is_weekday(input.context.timestamp)
    input.tool.sensitivity_level == "high"
}
```

### Test Locally

Create `input-business-hours-weekday.json`:
```json
{
  "user": {"roles": ["team_lead"]},
  "tool": {"sensitivity_level": "high"},
  "context": {
    "timestamp": 1732708800
  }
}
```

**Note:** `1732708800` is a Unix timestamp. Use this to generate timestamps:

```bash
# Get current timestamp
date +%s

# Get timestamp for specific time (2 PM on a weekday)
date -j -f "%Y-%m-%d %H:%M:%S" "2025-11-28 14:00:00" +%s

# For Linux:
date -d "2025-11-28 14:00:00" +%s
```

Test:

```bash
# During business hours (should allow)
opa eval -i input-business-hours-weekday.json -d business_hours.rego \
  "data.mcp.business_hours"

# Outside business hours (should deny)
# Change timestamp to 11 PM:
# "timestamp": 1732752000

# Weekend (should deny)
# Change timestamp to Saturday:
# "timestamp": 1732881600
```

### Deploy and Test

```bash
# Copy to OPA directory
cp business_hours.rego opa/policies/custom/
docker compose restart opa

# Test with SARK API (during business hours)
NOW=$(date +%s)  # Current time
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"user_id\": \"john.doe\",
    \"tool\": {\"sensitivity_level\": \"high\"},
    \"context\": {\"timestamp\": $NOW}
  }" | jq
```

---

## Step 5: Policy Testing with OPA Test Framework

OPA includes a built-in test framework. Let's write tests for our policies.

### Create Test File

Create `my_first_policy_test.rego`:

```rego
package mcp.custom

import future.keywords.if

# Test: Developer can execute SELECT query
test_developer_can_select if {
    allow with input as {
        "user": {"roles": ["developer"]},
        "action": "tool:invoke",
        "tool": {"name": "execute_query"},
        "arguments": {"query": "SELECT * FROM users"}
    }
}

# Test: DELETE query is denied
test_delete_query_denied if {
    deny with input as {
        "user": {"roles": ["developer"]},
        "action": "tool:invoke",
        "tool": {"name": "execute_query"},
        "arguments": {"query": "DELETE FROM users"}
    }
}

# Test: Non-developer cannot execute query
test_non_developer_denied if {
    not allow with input as {
        "user": {"roles": ["analyst"]},
        "action": "tool:invoke",
        "tool": {"name": "execute_query"},
        "arguments": {"query": "SELECT * FROM users"}
    }
}

# Test: UPDATE query is denied
test_update_query_denied if {
    deny with input as {
        "user": {"roles": ["developer"]},
        "tool": {"name": "execute_query"},
        "arguments": {"query": "UPDATE users SET status = 'inactive'"}
    }
}

# Test: Audit reason is correct for allow
test_audit_reason_allow if {
    audit_reason == "Allowed: Developer executing SELECT query" with input as {
        "user": {"roles": ["developer"]},
        "action": "tool:invoke",
        "tool": {"name": "execute_query"},
        "arguments": {"query": "SELECT * FROM users"}
    }
}

# Test: Audit reason is correct for deny
test_audit_reason_deny if {
    audit_reason == "Denied: Dangerous SQL keyword detected" with input as {
        "user": {"roles": ["developer"]},
        "tool": {"name": "execute_query"},
        "arguments": {"query": "DELETE FROM users"}
    }
}
```

### Run Tests

```bash
# Run all tests
opa test my_first_policy.rego my_first_policy_test.rego -v

# Expected output:
# my_first_policy_test.rego:
#   data.mcp.custom.test_developer_can_select: PASS (0.5ms)
#   data.mcp.custom.test_delete_query_denied: PASS (0.3ms)
#   data.mcp.custom.test_non_developer_denied: PASS (0.4ms)
#   data.mcp.custom.test_update_query_denied: PASS (0.3ms)
#   data.mcp.custom.test_audit_reason_allow: PASS (0.6ms)
#   data.mcp.custom.test_audit_reason_deny: PASS (0.5ms)
# --------------------------------------------------------------------------------
# PASS: 6/6
```

### Run Tests in Docker

```bash
# Copy test file to OPA policies
cp my_first_policy_test.rego opa/policies/custom/

# Run tests inside Docker container
docker compose exec opa opa test /policies -v

# All policies and tests will run
```

---

## Step 6: Advanced Policy - Parameter Filtering

Let's write a policy that automatically filters parameters for junior users. Analysts (like carol.analyst) should only query analytics database with row limits capped at 1000.

### Create the Policy

Create `parameter_filtering.rego`:

```rego
package mcp.filtering

import future.keywords.if
import future.keywords.in

default allow := false

# Analysts can query with automatic parameter filtering
allow if {
    "analyst" in input.user.roles
    input.tool.name == "execute_query"
    not query_is_dangerous(input.arguments.query)
}

# Filter and modify parameters for analysts
filtered_parameters := params if {
    "analyst" in input.user.roles
    params := {
        "query": input.arguments.query,
        "database": "analytics",  # Force analytics only
        "limit": min_limit(input.arguments.limit)  # Cap at 1000
    }
}

# Cap limit at 1000 for analysts
min_limit(requested) := limit if {
    requested > 1000
    limit := 1000
} else := requested

# Check for dangerous keywords
dangerous_keywords := ["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE"]

query_is_dangerous(query) if {
    q := upper(query)
    some keyword in dangerous_keywords
    contains(q, keyword)
}

contains(str, substr) if {
    indexof(str, substr) != -1
}

upper(str) := upper(str)

audit_reason := "Allowed: Analyst with filtered parameters" if {
    allow
}

audit_reason := "Denied: Dangerous query" if {
    query_is_dangerous(input.arguments.query)
}
```

### Test Parameter Filtering

Create `input-analyst.json`:
```json
{
  "user": {"roles": ["analyst"]},
  "tool": {"name": "execute_query"},
  "arguments": {
    "query": "SELECT * FROM users",
    "database": "production",
    "limit": 50000
  }
}
```

Test:

```bash
opa eval -i input-analyst.json -d parameter_filtering.rego \
  "data.mcp.filtering.filtered_parameters"

# Expected:
# "filtered_parameters": {
#   "query": "SELECT * FROM users",
#   "database": "analytics",  # Changed from "production"
#   "limit": 1000  # Capped from 50000
# }
```

---

## Step 7: Policy Composition and Organization

As your policies grow, organize them into modules.

### Recommended Structure

```
opa/policies/
├── defaults/              # SARK default policies
│   ├── main.rego
│   ├── rbac.rego
│   ├── sensitivity.rego
│   └── time_based.rego
├── custom/                # Your custom policies
│   ├── database_access.rego
│   ├── mfa_required.rego
│   └── team_permissions.rego
└── tutorials/             # Tutorial examples
    └── tutorial_examples.rego
```

### Main Policy Entry Point

Create `main.rego` that aggregates all policies:

```rego
package mcp

import future.keywords.if

# Import sub-policies
import data.mcp.custom
import data.mcp.business_hours
import data.mcp.filtering

# Combine allow decisions
allow if { custom.allow }
allow if { business_hours.allow }
allow if { filtering.allow }

# Combine deny decisions
deny if { custom.deny }
deny if { business_hours.deny }
deny if { filtering.deny }

# Combine filtered parameters
filtered_parameters := params if {
    params := filtering.filtered_parameters
}

# Aggregate audit reasons
audit_reason := reason if {
    reason := custom.audit_reason
}

audit_reason := reason if {
    reason := business_hours.audit_reason
}

audit_reason := reason if {
    reason := filtering.audit_reason
}
```

---

## Step 8: Debugging Policies

### Use `trace` for Debugging

Add `trace()` calls to see evaluation steps:

```rego
allow if {
    trace("Checking developer role")
    "developer" in input.user.roles

    trace("Checking tool name")
    input.tool.name == "execute_query"

    trace("Allow decision made")
}
```

Run with tracing:

```bash
opa eval --explain=notes -i input.json -d policy.rego "data.mcp.allow"

# Output shows evaluation steps
```

### Use OPA Playground

1. Go to https://play.openpolicyagent.org/
2. Paste your policy
3. Paste input JSON
4. Click "Evaluate"
5. View results and query explanations

---

## Step 9: Production Best Practices

### 1. Default Deny

Always start with:
```rego
default allow := false
```

### 2. Explicit Deny Rules

Use deny rules for critical restrictions:
```rego
deny if {
    input.tool.sensitivity_level == "critical"
    not "admin" in input.user.roles
}
```

### 3. Comprehensive Tests

Test every policy rule:
```rego
# Test both positive and negative cases
test_allow_case if { ... }
test_deny_case if { ... }
```

### 4. Audit Reasons

Always provide clear audit reasons:
```rego
audit_reason := "Specific reason for allow/deny"
```

### 5. Performance

- Avoid expensive operations in hot paths
- Use `some` for early termination
- Cache results with intermediate rules
- Limit recursion depth

### 6. Version Control

- Store policies in Git
- Use semantic versioning
- Tag policy releases
- Document breaking changes

---

## Hands-On Exercises

### Exercise 1: MFA Requirement

**Task:** Write a policy that requires MFA for critical tools.

**Requirements:**
- Critical tools require `input.context.mfa_verified == true`
- MFA must be recent (within last 5 minutes)
- MFA timestamp in `input.context.mfa_timestamp`

**Hints:**
```rego
# Check MFA age
now := time.now_ns()
mfa_time := time.parse_rfc3339_ns(input.context.mfa_timestamp)
age := now - mfa_time

# 5 minutes in nanoseconds
five_minutes := 300000000000
```

**Solution:** See `opa/policies/tutorials/tutorial_examples.rego` (Example 5)

### Exercise 2: IP-Based Access Control

**Task:** Write a policy that restricts production database access to corporate network (10.0.0.0/8).

**Hints:**
```rego
# Check if IP is in CIDR range
net.cidr_contains("10.0.0.0/8", input.context.ip_address)
```

**Solution:** See `opa/policies/tutorials/tutorial_examples.rego` (Example 6)

### Exercise 3: Approval Workflow

**Task:** Junior developers need manager approval for high-sensitivity tools.

**Requirements:**
- Check if `"team_lead" in input.user.roles`
- If not, require `input.approval.approved_by != ""`
- Check approval not expired: `input.approval.expires_at > now`

**Solution:** See `opa/policies/tutorials/tutorial_examples.rego` (Example 7)

---

## Summary

You've learned:

✅ Rego language basics (rules, conditions, functions)
✅ SARK policy structure and evaluation flow
✅ Writing custom authorization policies
✅ Testing policies locally with OPA CLI
✅ Deploying policies to SARK
✅ Advanced patterns:
  - Time-based access control
  - SQL injection prevention
  - Parameter filtering
  - MFA requirements
  - IP-based restrictions
✅ Policy testing and debugging
✅ Production best practices

### Next Steps

- **[Tutorial 4: Production Deployment](../04-production/README.md)** - Deploy SARK to Kubernetes
- **[OPA Policy Examples](../../opa/policies/tutorials/README.md)** - 10 ready-to-use patterns
- **[OPA Documentation](https://www.openpolicyagent.org/docs/)** - Official OPA docs
- **[Rego Playground](https://play.openpolicyagent.org/)** - Interactive testing

---

## Troubleshooting

### Policy Not Loading

```bash
# Check OPA logs
docker compose logs opa

# Look for syntax errors
docker compose exec opa opa check /policies

# Reload policies
docker compose restart opa
```

### Policy Always Denies

```bash
# Test policy directly with OPA
opa eval -i input.json -d policy.rego "data.mcp"

# Check default deny
# Make sure you have: default allow := false

# Check allow rules match
# Use trace() to debug
```

### Tests Failing

```bash
# Run tests with verbose output
opa test policy.rego policy_test.rego -v

# Check test input matches policy expectations
# Verify test assertions are correct
```

---

**Congratulations!** 🎉 You're now a SARK policy developer. You can write, test, and deploy production-ready access control policies for MCP governance.
