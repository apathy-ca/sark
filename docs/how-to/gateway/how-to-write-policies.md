# How to Write OPA Policies for SARK Gateway

This guide teaches you how to write, test, and deploy Open Policy Agent (OPA) policies to control access to MCP tools through the SARK Gateway.

## Before You Begin

**Prerequisites:**
- Basic understanding of authorization concepts (RBAC, ABAC)
- OPA installed locally for testing (`brew install opa` or download from [openpolicyagent.org](https://www.openpolicyagent.org/))
- SARK Gateway with OPA integration enabled
- Text editor with Rego syntax support (VS Code with OPA extension recommended)
- Access to gateway policy management API

**What You'll Learn:**
- Write your first OPA policy from scratch
- Test policies in isolation before deployment
- Debug policy decisions step-by-step
- Deploy and version policies
- Implement common access control patterns
- Rollback policies when needed

## Understanding Policy Structure

OPA policies are written in **Rego**, a declarative policy language. A basic policy has:

```rego
package sark.gateway.authz

# Default deny - explicit allow required
default allow = false

# Allow rule - must evaluate to true for access
allow {
    # Conditions go here
    input.user.role == "admin"
}
```

## Writing Your First Policy from Scratch

### Step 1: Define Policy Requirements

Before writing code, document what you want to control:

```markdown
# Policy Requirements: Basic Tool Access

## Goal
Control which users can invoke specific MCP tools.

## Rules
1. Admins can invoke all tools
2. Developers can invoke development tools only
3. Viewers can only invoke read-only tools
4. All users must be authenticated
5. Block access outside business hours (9 AM - 5 PM)

## Test Cases
- Admin invoking any tool → ALLOW
- Developer invoking write tool → DENY
- Viewer invoking read tool during business hours → ALLOW
- Any user invoking tool at 2 AM → DENY
```

### Step 2: Create Basic Policy File

Create `basic_authz.rego`:

```rego
package sark.gateway.authz

# Import helper functions
import future.keywords.contains
import future.keywords.if
import future.keywords.in

# Default deny - fail closed for security
default allow = false

# Allow admins to do anything
allow if {
    input.user.role == "admin"
}

# Allow developers to invoke development tools
allow if {
    input.user.role == "developer"
    input.tool.category == "development"
}

# Allow viewers to invoke read-only tools
allow if {
    input.user.role == "viewer"
    input.tool.read_only == true
}

# Deny all access outside business hours
allow = false if {
    not is_business_hours
}

# Helper function: check if current time is within business hours
is_business_hours if {
    # Get current hour (0-23)
    hour := time.clock([time.now_ns(), "America/New_York"])[0]

    # Business hours: 9 AM to 5 PM
    hour >= 9
    hour < 17
}

# Helper function: check if day is a weekday
is_weekday if {
    # Get day of week (0 = Monday, 6 = Sunday)
    day := time.weekday([time.now_ns(), "America/New_York"])
    day < 5  # Monday to Friday
}
```

**Expected Result:** A basic policy file with clear structure.

### Step 3: Understand Input Structure

The gateway sends this JSON structure to OPA:

```json
{
  "user": {
    "id": "user-123",
    "username": "alice@example.com",
    "role": "developer",
    "groups": ["engineering", "platform"],
    "attributes": {
      "department": "engineering",
      "clearance_level": 2
    }
  },
  "tool": {
    "name": "deploy_service",
    "server_id": "deployment-server",
    "category": "deployment",
    "read_only": false,
    "tags": ["production", "critical"],
    "metadata": {
      "risk_level": "high"
    }
  },
  "request": {
    "method": "POST",
    "path": "/api/v1/tools/invoke",
    "timestamp": "2024-01-15T14:30:00Z",
    "ip_address": "192.168.1.100",
    "user_agent": "SARK-Client/1.0"
  },
  "context": {
    "environment": "production",
    "region": "us-east-1"
  }
}
```

### Step 4: Create Test Input Files

Create `test_inputs/admin_invoke.json`:

```json
{
  "user": {
    "id": "user-admin",
    "username": "admin@example.com",
    "role": "admin",
    "groups": ["admins"]
  },
  "tool": {
    "name": "deploy_service",
    "server_id": "deployment-server",
    "category": "deployment",
    "read_only": false
  },
  "request": {
    "timestamp": "2024-01-15T14:30:00Z"
  }
}
```

Create `test_inputs/developer_invoke.json`:

```json
{
  "user": {
    "id": "user-dev",
    "username": "dev@example.com",
    "role": "developer",
    "groups": ["engineering"]
  },
  "tool": {
    "name": "run_tests",
    "server_id": "test-server",
    "category": "development",
    "read_only": false
  },
  "request": {
    "timestamp": "2024-01-15T14:30:00Z"
  }
}
```

Create `test_inputs/viewer_read.json`:

```json
{
  "user": {
    "id": "user-viewer",
    "username": "viewer@example.com",
    "role": "viewer",
    "groups": ["support"]
  },
  "tool": {
    "name": "get_status",
    "server_id": "monitoring-server",
    "category": "monitoring",
    "read_only": true
  },
  "request": {
    "timestamp": "2024-01-15T14:30:00Z"
  }
}
```

## Testing Policies in Isolation

### Step 1: Test with OPA CLI

Test each scenario:

```bash
# Test admin access (should allow)
opa eval -i test_inputs/admin_invoke.json \
  -d basic_authz.rego \
  "data.sark.gateway.authz.allow"
```

**Expected Output:**
```json
{
  "result": [
    {
      "expressions": [
        {
          "value": true,
          "text": "data.sark.gateway.authz.allow",
          "location": {
            "row": 1,
            "col": 1
          }
        }
      ]
    }
  ]
}
```

**What This Means:** Policy evaluated to `true` - access allowed.

```bash
# Test developer accessing development tool (should allow)
opa eval -i test_inputs/developer_invoke.json \
  -d basic_authz.rego \
  "data.sark.gateway.authz.allow"
```

**Expected Output:**
```json
{
  "result": [
    {
      "expressions": [
        {
          "value": true
        }
      ]
    }
  ]
}
```

```bash
# Test viewer accessing read-only tool (should allow)
opa eval -i test_inputs/viewer_read.json \
  -d basic_authz.rego \
  "data.sark.gateway.authz.allow"
```

**Expected Output:**
```json
{
  "result": [
    {
      "expressions": [
        {
          "value": true
        }
      ]
    }
  ]
}
```

### Step 2: Create Automated Test Suite

Create `policy_test.rego`:

```rego
package sark.gateway.authz

import future.keywords.if

# Test: Admin can access any tool
test_admin_full_access if {
    allow with input as {
        "user": {"role": "admin"},
        "tool": {"name": "any_tool"}
    }
}

# Test: Developer can access development tools
test_developer_dev_tools if {
    allow with input as {
        "user": {"role": "developer"},
        "tool": {"category": "development"}
    }
}

# Test: Developer cannot access non-development tools
test_developer_blocked_non_dev if {
    not allow with input as {
        "user": {"role": "developer"},
        "tool": {"category": "deployment"}
    }
}

# Test: Viewer can access read-only tools
test_viewer_read_only if {
    allow with input as {
        "user": {"role": "viewer"},
        "tool": {"read_only": true}
    }
}

# Test: Viewer cannot access write tools
test_viewer_blocked_write if {
    not allow with input as {
        "user": {"role": "viewer"},
        "tool": {"read_only": false}
    }
}

# Test: Unknown role is denied
test_unknown_role_denied if {
    not allow with input as {
        "user": {"role": "unknown"},
        "tool": {"name": "any_tool"}
    }
}

# Test: Missing user is denied
test_missing_user_denied if {
    not allow with input as {
        "tool": {"name": "any_tool"}
    }
}
```

**Run All Tests:**

```bash
opa test . -v
```

**Expected Output:**
```
policy_test.rego:
  data.sark.gateway.authz.test_admin_full_access: PASS (0.5ms)
  data.sark.gateway.authz.test_developer_dev_tools: PASS (0.3ms)
  data.sark.gateway.authz.test_developer_blocked_non_dev: PASS (0.4ms)
  data.sark.gateway.authz.test_viewer_read_only: PASS (0.3ms)
  data.sark.gateway.authz.test_viewer_blocked_write: PASS (0.4ms)
  data.sark.gateway.authz.test_unknown_role_denied: PASS (0.3ms)
  data.sark.gateway.authz.test_missing_user_denied: PASS (0.2ms)
--------------------------------------------------------------------------------
PASS: 7/7
```

### Step 3: Test with Real Gateway Data

Capture real request data from gateway logs:

```bash
# Extract sample request from gateway logs
kubectl logs deployment/sark-gateway -n sark-system \
  | grep "policy_input" \
  | jq '.policy_input' \
  > real_request.json
```

Test policy against real data:

```bash
opa eval -i real_request.json \
  -d basic_authz.rego \
  --explain=full \
  "data.sark.gateway.authz.allow"
```

## Debugging Policy Decisions Step-by-Step

### Step 1: Enable Debug Mode

Add debug rules to policy:

```rego
package sark.gateway.authz

# ... existing rules ...

# Debug: Show why decision was made
reasons contains "admin_override" if {
    input.user.role == "admin"
}

reasons contains "developer_dev_tool" if {
    input.user.role == "developer"
    input.tool.category == "development"
}

reasons contains "viewer_read_only" if {
    input.user.role == "viewer"
    input.tool.read_only == true
}

reasons contains "outside_business_hours" if {
    not is_business_hours
}

# Include reasons in response
response = {"allow": allow, "reasons": reasons}
```

### Step 2: Use OPA Explain Feature

```bash
opa eval -i test_inputs/developer_invoke.json \
  -d basic_authz.rego \
  --explain=full \
  "data.sark.gateway.authz.allow"
```

**Expected Output:**
```
Enter data.sark.gateway.authz.allow = _

| Eval data.sark.gateway.authz.allow = _
| Index data.sark.gateway.authz.allow (matched 3 rules)
| Enter data.sark.gateway.authz.allow
| | Eval input.user.role == "admin"
| | Fail input.user.role == "admin"
| | Redo input.user.role == "admin"
| Enter data.sark.gateway.authz.allow
| | Eval input.user.role == "developer"
| | Eval input.tool.category == "development"
| | Exit data.sark.gateway.authz.allow
| Exit data.sark.gateway.authz.allow = _

true
```

**What This Shows:** Policy matched the second rule (developer with development tool).

### Step 3: Add Logging to Policies

```rego
package sark.gateway.authz

import data.sark.audit.log_decision

# Allow rule with logging
allow if {
    input.user.role == "admin"

    # Log this decision
    log_decision({
        "decision": "allow",
        "reason": "admin_role",
        "user": input.user.id,
        "tool": input.tool.name
    })
}
```

### Step 4: Use OPA REPL for Interactive Testing

```bash
opa run basic_authz.rego
```

In the REPL:

```rego
# Set test input
input := {"user": {"role": "developer"}, "tool": {"category": "development"}}

# Check allow decision
data.sark.gateway.authz.allow

# Check reasons
data.sark.gateway.authz.reasons

# Test different scenarios interactively
input := {"user": {"role": "viewer"}, "tool": {"read_only": false}}
data.sark.gateway.authz.allow
```

## Policy Deployment Workflow

### Step 1: Validate Policy Syntax

```bash
# Check for syntax errors
opa check basic_authz.rego
```

**Expected Output:**
```
basic_authz.rego:
  No syntax errors found
```

### Step 2: Run Full Test Suite

```bash
# Run all tests with coverage
opa test . -v --coverage
```

**Expected Output:**
```
--------------------------------------------------------------------------------
PASS: 7/7

Coverage: 95.2%
  basic_authz.rego: 100%
  policy_test.rego: N/A (test file)
```

### Step 3: Bundle Policy for Deployment

Create bundle manifest `bundle_manifest.yaml`:

```yaml
revision: "1.0.0"
roots:
  - sark/gateway/authz

metadata:
  name: "SARK Gateway Authorization Policies"
  version: "1.0.0"
  description: "Basic RBAC policies for tool access control"
  authors:
    - "Security Team <security@example.com>"
  created_at: "2024-01-15T10:00:00Z"
  tags:
    - rbac
    - gateway
    - production
```

Build bundle:

```bash
opa build -b basic_authz.rego bundle_manifest.yaml
```

**Expected Output:**
```
Created bundle: bundle.tar.gz
  Policies: 1
  Data: 0
  Size: 2.3 KB
```

### Step 4: Deploy to Gateway

**Option 1: Deploy via API**

```bash
curl -X PUT https://gateway.example.com/api/v1/policies/authz \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @bundle.tar.gz
```

**Expected Response:**
```json
{
  "status": "deployed",
  "policy_id": "authz-v1.0.0",
  "deployed_at": "2024-01-15T10:30:00Z",
  "bundle_revision": "1.0.0",
  "validation": {
    "syntax_valid": true,
    "tests_passed": 7,
    "coverage": 95.2
  }
}
```

**Option 2: Deploy via CLI**

```bash
sark-cli policy deploy \
  --bundle bundle.tar.gz \
  --name authz \
  --version 1.0.0
```

**Expected Output:**
```
Deploying policy bundle...
✓ Bundle uploaded
✓ Syntax validation passed
✓ Tests passed (7/7)
✓ Policy activated

Policy ID: authz-v1.0.0
Status: active
Endpoints updated: 3
```

**Option 3: Deploy via GitOps**

Create `policies/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

configMapGenerator:
  - name: opa-policies
    files:
      - basic_authz.rego
      - advanced_authz.rego
    options:
      labels:
        app: sark-gateway
        component: policies
        version: "1.0.0"
```

Deploy with Kustomize:

```bash
kubectl apply -k policies/
```

### Step 5: Verify Deployment

```bash
# Check policy is active
sark-cli policy list
```

**Expected Output:**
```
┌──────────────┬──────────┬────────────────────┬────────┐
│ Policy Name  │ Version  │ Deployed           │ Status │
├──────────────┼──────────┼────────────────────┼────────┤
│ authz        │ 1.0.0    │ 2024-01-15 10:30   │ active │
└──────────────┴──────────┴────────────────────┴────────┘
```

Test policy in production:

```bash
# Make test request
curl -X POST https://gateway.example.com/api/v1/tools/invoke \
  -H "Authorization: Bearer ${USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "test-server",
    "tool_name": "run_tests",
    "arguments": {}
  }'
```

**Expected Response (if allowed):**
```json
{
  "success": true,
  "result": {...},
  "policy_decision": {
    "allowed": true,
    "reasons": ["developer_dev_tool"],
    "policy_version": "1.0.0"
  }
}
```

**Expected Response (if denied):**
```json
{
  "error": "access_denied",
  "message": "Policy evaluation denied access",
  "policy_decision": {
    "allowed": false,
    "reasons": [],
    "policy_version": "1.0.0"
  }
}
```

## Policy Versioning and Rollback

### Implement Versioning Strategy

Create `versions/v1.0.0/authz.rego`:

```rego
package sark.gateway.authz.v1

# Version 1.0.0 implementation
# Basic RBAC only
```

Create `versions/v2.0.0/authz.rego`:

```rego
package sark.gateway.authz.v2

# Version 2.0.0 implementation
# RBAC + time-based access control
```

Create version router `authz.rego`:

```rego
package sark.gateway.authz

import data.sark.gateway.authz.v1
import data.sark.gateway.authz.v2

# Use versioned policy based on configuration
allow = decision if {
    # Get active version from config
    active_version := data.config.policy_version

    # Route to appropriate version
    active_version == "1.0.0"
    decision := v1.allow
}

allow = decision if {
    active_version := data.config.policy_version
    active_version == "2.0.0"
    decision := v2.allow
}

# Default to latest version
allow = v2.allow if {
    not data.config.policy_version
}
```

### Deploy New Version

```bash
# Deploy v2.0.0
sark-cli policy deploy \
  --bundle bundle-v2.tar.gz \
  --version 2.0.0 \
  --strategy canary \
  --canary-percentage 10
```

**Expected Output:**
```
Deploying policy v2.0.0 with canary strategy...
✓ Version 2.0.0 deployed
✓ Canary routing configured: 10% traffic

Current distribution:
  v1.0.0: 90% traffic
  v2.0.0: 10% traffic (canary)

Monitor canary metrics before full rollout.
```

### Monitor Canary Deployment

```bash
# Watch policy metrics
sark-cli policy metrics watch --version 2.0.0
```

**Expected Output:**
```
Policy Metrics (v2.0.0 canary - 10% traffic)

Requests:        1,234
Allowed:         1,100 (89.1%)
Denied:          134 (10.9%)
Errors:          0 (0.0%)
Avg Latency:     2.3ms
p99 Latency:     8.1ms

Compared to v1.0.0:
  Allowed rate:  +0.2%  (within threshold)
  Error rate:    0.0%   (no change)
  Latency:       +0.1ms (acceptable)

Status: ✓ Canary healthy - safe to promote
```

### Promote Canary to Production

```bash
# Gradually increase traffic
sark-cli policy promote \
  --version 2.0.0 \
  --percentage 50
```

**Expected Output:**
```
Promoting v2.0.0 to 50% traffic...
✓ Traffic distribution updated

Current distribution:
  v1.0.0: 50% traffic
  v2.0.0: 50% traffic
```

After validation:

```bash
# Full rollout
sark-cli policy promote \
  --version 2.0.0 \
  --percentage 100
```

### Rollback Policy

If issues detected:

```bash
# Immediate rollback
sark-cli policy rollback --version 1.0.0
```

**Expected Output:**
```
⚠ Rolling back to v1.0.0...
✓ Policy reverted to v1.0.0
✓ All traffic routed to v1.0.0

Rollback complete. v2.0.0 deactivated.
```

## Common Policy Patterns

### Pattern 1: Role-Based Access Control (RBAC)

```rego
package sark.gateway.authz.patterns.rbac

import future.keywords.if
import future.keywords.in

# Define role permissions
role_permissions := {
    "admin": {"actions": ["*"], "resources": ["*"]},
    "developer": {
        "actions": ["invoke", "read"],
        "resources": ["development/*", "testing/*"]
    },
    "operator": {
        "actions": ["invoke", "read"],
        "resources": ["monitoring/*", "deployment/*"]
    },
    "viewer": {
        "actions": ["read"],
        "resources": ["*"]
    }
}

# Check if user's role allows the action
allow if {
    # Get user's role
    user_role := input.user.role

    # Get permissions for role
    permissions := role_permissions[user_role]

    # Check action is allowed
    action_allowed(permissions.actions, input.request.action)

    # Check resource is allowed
    resource_allowed(permissions.resources, input.tool.name)
}

# Helper: Check if action is in allowed list
action_allowed(allowed_actions, requested_action) if {
    "*" in allowed_actions
}

action_allowed(allowed_actions, requested_action) if {
    requested_action in allowed_actions
}

# Helper: Check if resource matches allowed patterns
resource_allowed(allowed_resources, requested_resource) if {
    "*" in allowed_resources
}

resource_allowed(allowed_resources, requested_resource) if {
    some pattern in allowed_resources
    glob.match(pattern, [], requested_resource)
}
```

### Pattern 2: Attribute-Based Access Control (ABAC)

```rego
package sark.gateway.authz.patterns.abac

import future.keywords.if

# Allow based on multiple attributes
allow if {
    # User must be in correct department
    input.user.attributes.department == input.tool.metadata.owner_department

    # User must have sufficient clearance
    input.user.attributes.clearance_level >= input.tool.metadata.required_clearance

    # Tool must not be deprecated
    not input.tool.metadata.deprecated

    # Request must come from allowed network
    ip_in_allowed_range(input.request.ip_address)
}

# Check if IP is in allowed CIDR range
ip_in_allowed_range(ip) if {
    # Define allowed CIDR blocks
    allowed_cidrs := ["10.0.0.0/8", "192.168.0.0/16"]

    # Check if IP matches any CIDR
    some cidr in allowed_cidrs
    net.cidr_contains(cidr, ip)
}

# Allow high-clearance users to override
allow if {
    input.user.attributes.clearance_level >= 5
    input.user.attributes.override_approved == true
}
```

### Pattern 3: Time-Based Access Control

```rego
package sark.gateway.authz.patterns.time_based

import future.keywords.if

# Business hours restriction
allow if {
    # Base authorization check
    basic_authz_passes

    # Time-based restrictions
    is_business_hours
    is_weekday
}

# Emergency access outside business hours
allow if {
    # Must be on-call engineer
    input.user.attributes.on_call == true

    # Must be responding to incident
    input.request.metadata.incident_id != ""

    # Require MFA for emergency access
    input.request.mfa_verified == true
}

# Helper: Check business hours
is_business_hours if {
    hour := time.clock([time.now_ns(), "America/New_York"])[0]
    hour >= 9
    hour < 17
}

# Helper: Check weekday
is_weekday if {
    day := time.weekday([time.now_ns(), "America/New_York"])
    day < 5
}

# Scheduled maintenance windows
allow if {
    # Check if in approved maintenance window
    some window in data.maintenance_windows
    in_time_window(window.start_time, window.end_time)

    # Must be maintenance engineer
    "maintenance" in input.user.groups

    # Tool must be maintenance-related
    input.tool.category == "maintenance"
}

# Helper: Check if current time is in window
in_time_window(start_time, end_time) if {
    now := time.now_ns()
    start_ns := time.parse_rfc3339_ns(start_time)
    end_ns := time.parse_rfc3339_ns(end_time)

    now >= start_ns
    now <= end_ns
}
```

### Pattern 4: Rate Limiting Policy

```rego
package sark.gateway.authz.patterns.rate_limit

import future.keywords.if

# Track request counts (requires external data)
allow if {
    # Base authorization
    user_authorized

    # Check rate limits
    not rate_limit_exceeded
}

# Check if user has exceeded rate limit
rate_limit_exceeded if {
    # Get user's request count in current window
    count := data.rate_limits[input.user.id].count

    # Get user's rate limit
    limit := user_rate_limit

    # Check if exceeded
    count >= limit
}

# Determine rate limit based on user tier
user_rate_limit := limit if {
    input.user.attributes.tier == "premium"
    limit := 1000
}

user_rate_limit := limit if {
    input.user.attributes.tier == "standard"
    limit := 100
}

user_rate_limit := 10 if {
    # Default for free tier
    not input.user.attributes.tier
}

# Provide detailed denial reason
denial_reason := reason if {
    rate_limit_exceeded
    reason := {
        "code": "rate_limit_exceeded",
        "message": sprintf("Rate limit of %d requests exceeded", [user_rate_limit]),
        "retry_after": time_until_reset
    }
}
```

### Pattern 5: Data Classification Policy

```rego
package sark.gateway.authz.patterns.data_classification

import future.keywords.if
import future.keywords.in

# Allow based on data sensitivity
allow if {
    # Get data classification
    classification := input.tool.metadata.data_classification

    # Check user clearance
    user_can_access_classification(classification)

    # Additional controls for sensitive data
    sensitive_data_controls(classification)
}

# Check if user can access data at this classification
user_can_access_classification("public") if {
    # Anyone can access public data
    input.user.authenticated
}

user_can_access_classification("internal") if {
    # Must be employee
    input.user.attributes.employee == true
}

user_can_access_classification("confidential") if {
    # Must have confidential clearance
    input.user.attributes.clearance_level >= 3

    # Must be in authorized group
    some group in input.user.groups
    group in data.confidential_access_groups
}

user_can_access_classification("secret") if {
    # Highest clearance required
    input.user.attributes.clearance_level >= 5

    # Must have NDA on file
    input.user.attributes.nda_signed == true

    # Require MFA
    input.request.mfa_verified == true
}

# Additional controls for sensitive data
sensitive_data_controls(classification) if {
    classification in ["confidential", "secret"]

    # Must be from corporate network
    ip_in_corporate_network(input.request.ip_address)

    # Must log access
    log_sensitive_access
}

sensitive_data_controls(classification) if {
    classification in ["public", "internal"]
    # No additional controls needed
}
```

## Common Pitfalls

### Pitfall 1: Default Allow

**Problem:** Policy allows by default, creating security risk.

**Bad:**
```rego
default allow = true  # DANGEROUS!
```

**Good:**
```rego
default allow = false  # Fail closed
```

### Pitfall 2: Not Testing Denial Cases

**Problem:** Only testing allowed scenarios.

**Solution:** Test both allow and deny:
```rego
test_unauthorized_access_denied if {
    not allow with input as {
        "user": {"role": "viewer"},
        "tool": {"read_only": false}
    }
}
```

### Pitfall 3: Hardcoding Values

**Problem:** Hardcoded values in policy logic.

**Bad:**
```rego
allow if {
    input.user.id == "admin-123"  # Hardcoded!
}
```

**Good:**
```rego
allow if {
    input.user.id in data.admin_user_ids
}
```

### Pitfall 4: Incomplete Error Handling

**Problem:** Policy fails without clear error messages.

**Solution:** Provide denial reasons:
```rego
denial_reason := reason if {
    not allow
    input.user.role == "viewer"
    not input.tool.read_only
    reason := {
        "code": "insufficient_permissions",
        "message": "Viewers can only access read-only tools"
    }
}
```

### Pitfall 5: Not Versioning Policies

**Problem:** Can't rollback broken policies.

**Solution:** Always version and tag:
```bash
git tag -a policy-v1.0.0 -m "Initial RBAC policy"
git push origin policy-v1.0.0
```

## Related Resources

- [OPA Policy Reference](https://www.openpolicyagent.org/docs/latest/policy-reference/)
- [Rego Language Guide](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [Gateway Policy Integration](../reference/policy-integration.md)
- [Security Best Practices](./how-to-secure-gateway.md)
- [Policy Testing Guide](../tutorials/testing-policies.md)
- [RBAC vs ABAC Explained](../explanation/access-control-models.md)

## Next Steps

After writing policies:

1. **Monitor policy decisions** in production
   - See: [How to Monitor Gateway](./how-to-monitor-gateway.md)

2. **Debug policy issues** as they arise
   - See: [How to Troubleshoot Tools](./how-to-troubleshoot-tools.md)

3. **Secure your deployment** with additional controls
   - See: [How to Secure Gateway](./how-to-secure-gateway.md)

4. **Set up audit logging** for compliance
   - See: [Audit Logging Guide](../tutorials/audit-logging.md)
