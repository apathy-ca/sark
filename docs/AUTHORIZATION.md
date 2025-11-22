# SARK Authorization System Guide

**Complete Guide to OPA Policies, Testing, and Best Practices**

## Table of Contents

1. [Overview](#overview)
2. [Policy Architecture](#policy-architecture)
3. [Default Policies](#default-policies)
4. [Policy Authoring Tutorial](#policy-authoring-tutorial)
5. [Policy Testing Guide](#policy-testing-guide)
6. [Performance Tuning](#performance-tuning)
7. [Best Practices](#best-practices)
8. [Real-World Examples](#real-world-examples)
9. [Troubleshooting](#troubleshooting)

## Overview

SARK uses [Open Policy Agent (OPA)](https://www.openpolicyagent.org/) for flexible, fine-grained authorization. All authorization decisions are made through policy evaluation, ensuring consistent security enforcement across the platform.

### Key Features

- **🔒 Multi-Layer Security**: 6 policy layers (RBAC, Team Access, Sensitivity, Time-based, IP Filtering, MFA)
- **⚡ High Performance**: <50ms p95 latency with Redis caching
- **📊 Complete Audit Trail**: Every decision logged for compliance
- **🔧 Flexible Policies**: Easy to customize and extend
- **✅ Comprehensive Testing**: 90+ OPA tests, 105+ integration tests

### How It Works

```
User Request → Policy Evaluation → Decision (Allow/Deny)
                      ↓
        ┌─────────────┴─────────────┐
        │   6-Layer Policy Stack    │
        ├───────────────────────────┤
        │ 1. RBAC (Role-Based)      │
        │ 2. Team Access            │
        │ 3. Sensitivity Level      │
        │ 4. Time-Based Restrictions│
        │ 5. IP Filtering           │
        │ 6. MFA Requirements       │
        └───────────────────────────┘
                      ↓
            Cache + Audit Log
```

## Policy Architecture

### Policy Evaluation Flow

```rego
# main.rego - Policy orchestrator
package sark.defaults.main

import data.sark.defaults.rbac
import data.sark.defaults.team_access
import data.sark.defaults.sensitivity
import data.sark.policies.time_based
import data.sark.policies.ip_filtering
import data.sark.policies.mfa_required

# All policies must pass
allow if {
    rbac.allow
    team_access_allows
    sensitivity.allow
    time_based.allow
    ip_filtering.allow
    mfa_required.allow
}
```

### Input Structure

All policies receive a standardized input:

```json
{
  "user": {
    "id": "user-123",
    "role": "developer",
    "teams": ["team-1", "team-2"],
    "mfa_verified": true,
    "mfa_timestamp": 1699444800000000000,
    "mfa_methods": ["totp"]
  },
  "action": "tool:invoke",
  "tool": {
    "id": "tool-456",
    "name": "deploy_script",
    "sensitivity_level": "high",
    "teams": ["team-1"]
  },
  "context": {
    "client_ip": "10.0.0.100",
    "timestamp": 1699444800,
    "request_id": "req-789"
  },
  "policy_config": {
    "business_hours": { /* ... */ },
    "ip_allowlist": ["10.0.0.0/8"],
    "mfa_timeout_seconds": 3600
  }
}
```

### Output Structure

```json
{
  "allow": true,
  "reason": "Access granted by all policies",
  "policies_evaluated": ["rbac", "team_access", "sensitivity", "time_based", "ip_filtering", "mfa_required"],
  "policy_results": {
    "rbac": {
      "allow": true,
      "reason": "Developer role authorized"
    },
    "time_based": {
      "allow": true,
      "reason": "Within business hours"
    }
  },
  "timestamp": 1699444800000000000
}
```

## Default Policies

SARK includes 6 production-ready default policies covering common authorization scenarios.

### 1. RBAC (Role-Based Access Control)

**File**: `opa/policies/defaults/rbac.rego`

**Purpose**: Enforce role-based permissions for actions.

**Roles**:
- `admin`: Full access to all operations
- `developer`: Tool invocation, server management (no deletion)
- `viewer`: Read-only access
- `service`: Automated service operations

**Example Rules**:

```rego
# Admins can do everything
allow if {
    input.user.role == "admin"
}

# Developers can invoke tools
allow if {
    input.user.role == "developer"
    input.action == "tool:invoke"
}

# Viewers can only read
allow if {
    input.user.role == "viewer"
    input.action in ["server:read", "tool:read"]
}

# Service accounts can register servers
allow if {
    input.user.role == "service"
    input.action == "server:register"
}
```

**Denials**:

```rego
# Viewers cannot write
deny if {
    input.user.role == "viewer"
    startswith(input.action, "tool:invoke")
}

# Only admins can delete
deny if {
    input.user.role != "admin"
    endswith(input.action, ":delete")
}
```

### 2. Team Access Control

**File**: `opa/policies/defaults/team_access.rego`

**Purpose**: Enforce team-based ownership and permissions.

**Key Concepts**:
- Resources have owners (teams)
- Users belong to teams
- Cross-team access is restricted

**Example Rules**:

```rego
# User must be in resource's team
allow if {
    resource_teams := input.tool.teams
    user_teams := input.user.teams
    intersection := resource_teams & user_teams
    count(intersection) > 0
}

# Admins bypass team restrictions
allow if {
    input.user.role == "admin"
}
```

**Use Cases**:
- Multi-tenant isolation
- Department-based access
- Project-based permissions

### 3. Sensitivity Enforcement

**File**: `opa/policies/defaults/sensitivity.rego`

**Purpose**: Enforce access controls based on resource sensitivity.

**Sensitivity Levels**:
- `low`: Minimal restrictions
- `medium`: Standard controls
- `high`: Enhanced security (MFA recommended)
- `critical`: Maximum security (MFA + business hours + VPN)

**Example Rules**:

```rego
# Critical tools require admin or explicit approval
allow if {
    input.tool.sensitivity_level == "critical"
    input.user.role == "admin"
}

allow if {
    input.tool.sensitivity_level == "critical"
    input.user.role == "developer"
    input.context.approved_by_admin == true
}

# High sensitivity requires specific roles
allow if {
    input.tool.sensitivity_level == "high"
    input.user.role in ["admin", "developer"]
}

# Low/medium available to all authenticated users
allow if {
    input.tool.sensitivity_level in ["low", "medium"]
    input.user.role != "viewer"
}
```

### 4. Time-Based Access Control

**File**: `opa/policies/defaults/time_based.rego`

**Purpose**: Restrict operations to specific time windows.

**Features**:
- Business hours enforcement (9 AM - 5 PM, M-F)
- Weekend blocking for critical operations
- Custom time windows per resource
- Emergency override mechanism

**Example Rules**:

```rego
# Critical tools only during business hours
allow if {
    input.tool.sensitivity_level == "critical"
    is_business_hours
}

# Check if current time is in business hours
is_business_hours if {
    hour := time.clock([time.now_ns()])[0]
    weekday := time.weekday(time.now_ns())
    weekday < 5  # Monday-Friday
    hour >= 9
    hour < 17
}

# Admins bypass time restrictions
allow if {
    input.user.role == "admin"
}

# Emergency override
allow if {
    input.context.emergency_override == true
    input.context.emergency_reason != ""
    input.context.emergency_approver != ""
}
```

**Configuration**:

```json
{
  "policy_config": {
    "business_hours": {
      "monday": {"start": 9, "end": 17},
      "tuesday": {"start": 9, "end": 17},
      "wednesday": {"start": 9, "end": 17},
      "thursday": {"start": 9, "end": 17},
      "friday": {"start": 9, "end": 17},
      "saturday": null,
      "sunday": null
    }
  }
}
```

### 5. IP Filtering

**File**: `opa/policies/defaults/ip_filtering.rego`

**Purpose**: Enforce IP-based access controls.

**Features**:
- IP allowlist/blocklist
- CIDR range support
- VPN requirement for critical tools
- Geographic restrictions
- Private IP detection

**Example Rules**:

```rego
# Critical tools require VPN (private IP)
requires_vpn if {
    input.tool.sensitivity_level == "critical"
}

is_private_ip if {
    client_ip := input.context.client_ip
    startswith(client_ip, "10.")
}

is_private_ip if {
    client_ip := input.context.client_ip
    startswith(client_ip, "192.168.")
}

# Allow if on allowlist
is_ip_allowed if {
    client_ip := input.context.client_ip
    allowlist_entry := input.policy_config.ip_allowlist[_]
    ip_matches_entry(client_ip, allowlist_entry)
}

# Deny if on blocklist
is_ip_blocked if {
    client_ip := input.context.client_ip
    blocklist_entry := input.policy_config.ip_blocklist[_]
    ip_matches_entry(client_ip, blocklist_entry)
}
```

**Configuration**:

```json
{
  "policy_config": {
    "ip_allowlist": ["10.0.0.0/8", "192.168.0.0/16"],
    "ip_blocklist": ["1.2.3.4"],
    "geo_restrictions_enabled": true,
    "allowed_countries": ["US", "CA", "GB"]
  }
}
```

### 6. MFA Requirements

**File**: `opa/policies/defaults/mfa_required.rego`

**Purpose**: Enforce multi-factor authentication for sensitive operations.

**Features**:
- Sensitivity-based MFA (critical/high)
- Action-based MFA (destructive operations)
- MFA session timeout (default: 1 hour)
- Step-up authentication (re-verify after 5 min)
- Service account exemption

**Example Rules**:

```rego
# Critical tools require MFA
mfa_required if {
    input.tool.sensitivity_level == "critical"
}

# Destructive actions require MFA
mfa_required if {
    input.action in ["server:delete", "tool:delete", "user:delete"]
}

# MFA verified and session valid
mfa_verified if {
    input.user.mfa_verified == true
}

mfa_session_valid if {
    mfa_timestamp := input.user.mfa_timestamp
    current_time := time.now_ns()
    mfa_age_seconds := (current_time - mfa_timestamp) / 1000000000
    mfa_age_seconds <= 3600  # 1 hour
}

# Allow if MFA requirements met
allow if {
    mfa_required
    mfa_verified
    mfa_session_valid
}

# Service accounts use API keys instead
allow if {
    input.user.role == "service"
    input.context.api_key != ""
}
```

## Policy Authoring Tutorial

### Getting Started

#### 1. Create a New Policy File

```bash
# Create policy file
touch opa/policies/custom/my_policy.rego

# Create test file
touch opa/policies/custom/my_policy_test.rego
```

#### 2. Basic Policy Structure

```rego
package sark.custom.my_policy

import rego.v1

# Default deny (fail-safe)
default allow := false

# Main decision
allow if {
    # Your conditions here
    input.user.role == "developer"
    input.action == "custom:action"
}

# Human-readable reason
reason := "Access granted: developer role" if {
    allow
}

reason := "Access denied: insufficient permissions" if {
    not allow
}
```

#### 3. Policy Testing

```rego
package sark.custom.my_policy

import rego.v1

# Test allow case
test_allow_developer if {
    result := allow with input as {
        "user": {"role": "developer"},
        "action": "custom:action"
    }
    result == true
}

# Test deny case
test_deny_viewer if {
    result := allow with input as {
        "user": {"role": "viewer"},
        "action": "custom:action"
    }
    result == false
}
```

#### 4. Run Tests

```bash
# Test single policy
opa test opa/policies/custom/my_policy_test.rego -v

# Test all policies
opa test opa/policies/ -v
```

### Advanced Policy Patterns

#### Pattern 1: Attribute-Based Access Control (ABAC)

```rego
# Allow based on user attributes
allow if {
    input.user.department == "engineering"
    input.user.clearance_level >= 3
    input.tool.required_clearance <= input.user.clearance_level
}
```

#### Pattern 2: Relationship-Based Access Control (ReBAC)

```rego
# Allow based on relationships
allow if {
    # User is owner
    input.user.id == input.resource.owner_id
}

allow if {
    # User is in owner's team
    input.resource.owner_id in input.user.team_members
}
```

#### Pattern 3: Context-Aware Policies

```rego
# Different rules based on context
allow if {
    # Relaxed rules during maintenance window
    input.context.maintenance_mode == true
    input.user.role in ["admin", "sre"]
}

allow if {
    # Stricter rules in production
    input.context.environment == "production"
    input.user.role == "admin"
    input.user.mfa_verified == true
}
```

#### Pattern 4: Data Filtering

```rego
# Filter sensitive fields from response
filtered_response := response if {
    base_response := input.original_response

    # Remove sensitive fields
    response := object.remove(base_response, ["ssn", "credit_card"])
}

# Different filtering based on role
filtered_response := response if {
    input.user.role == "admin"
    response := input.original_response  # No filtering
}
```

#### Pattern 5: Rate Limiting

```rego
# Check if user exceeded rate limit
rate_limit_exceeded if {
    user_requests := input.context.user_request_count
    time_window := input.context.time_window_minutes

    user_requests > 100  # 100 requests
    time_window <= 60     # per hour
}

allow if {
    not rate_limit_exceeded
    # ... other conditions
}
```

### Policy Composition

Combine multiple policy modules:

```rego
package sark.custom.combined

import data.sark.defaults.rbac
import data.sark.custom.department_policy
import data.sark.custom.project_policy

# All policies must agree
allow if {
    rbac.allow
    department_policy.allow
    project_policy.allow
}

# Collect reasons from all policies
reason := sprintf("RBAC: %s, Dept: %s, Project: %s", [
    rbac.reason,
    department_policy.reason,
    project_policy.reason
])
```

## Policy Testing Guide

### Unit Testing with OPA

#### Basic Test Structure

```rego
package sark.policies.example

import rego.v1

# Test naming: test_<scenario>_<expected_result>
test_allow_admin_all_actions if {
    result := allow with input as {
        "user": {"role": "admin"},
        "action": "any:action"
    }
    result == true
}

test_deny_viewer_write_actions if {
    result := allow with input as {
        "user": {"role": "viewer"},
        "action": "tool:invoke"
    }
    result == false
}
```

#### Testing with Mock Data

```rego
# Define test data
test_user_admin := {
    "id": "admin-1",
    "role": "admin",
    "teams": ["team-1"]
}

test_user_developer := {
    "id": "dev-1",
    "role": "developer",
    "teams": ["team-2"]
}

# Use in tests
test_admin_can_delete if {
    result := allow with input as {
        "user": test_user_admin,
        "action": "server:delete"
    }
    result == true
}
```

#### Testing Edge Cases

```rego
# Test with minimal data
test_minimal_input if {
    result := allow with input as {
        "user": {"id": "user-1"},
        "action": "test"
    }
    # Should handle gracefully
    result == false
}

# Test with missing fields
test_missing_role if {
    result := allow with input as {
        "user": {"id": "user-1"},  # No role field
        "action": "tool:invoke"
    }
    result == false
}

# Test with null values
test_null_teams if {
    result := allow with input as {
        "user": {"id": "user-1", "role": "developer", "teams": null},
        "action": "tool:invoke"
    }
    # Should handle null gracefully
}
```

### Integration Testing with Python

```python
import pytest
from sark.services.policy.opa_client import OPAClient, AuthorizationInput

@pytest.mark.asyncio
async def test_rbac_policy_integration(opa_client):
    """Test RBAC policy through OPA client."""
    auth_input = AuthorizationInput(
        user={"id": "user-123", "role": "developer"},
        action="tool:invoke",
        tool={"name": "test_tool", "sensitivity_level": "low"},
        context={},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    assert decision.allow is True
    assert "developer" in decision.reason.lower()

@pytest.mark.asyncio
async def test_combined_policies(opa_client):
    """Test that all policies are evaluated."""
    auth_input = AuthorizationInput(
        user={
            "id": "user-123",
            "role": "developer",
            "teams": ["team-1"],
            "mfa_verified": True,
        },
        action="tool:invoke",
        tool={
            "name": "critical_tool",
            "sensitivity_level": "critical",
            "teams": ["team-1"],
        },
        context={"client_ip": "10.0.0.100"},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    # Check that all policies were evaluated
    assert "rbac" in decision.policies_evaluated
    assert "team_access" in decision.policies_evaluated
    assert "sensitivity" in decision.policies_evaluated
    assert "mfa_required" in decision.policies_evaluated
```

### Test Coverage

Ensure comprehensive test coverage:

```bash
# Run OPA tests with coverage
opa test --coverage opa/policies/

# Example output:
# opa/policies/defaults/rbac.rego: 95.2%
# opa/policies/defaults/team_access.rego: 92.8%
# opa/policies/defaults/sensitivity.rego: 94.1%
```

### Performance Testing

```rego
# Benchmark policy evaluation
test_performance_simple_policy if {
    start := time.now_ns()

    # Run policy 1000 times
    count([result |
        i := numbers.range(0, 999)[_]
        result := allow with input as test_input
    ]) == 1000

    end := time.now_ns()
    duration_ms := (end - start) / 1000000

    # Should complete in <10ms
    duration_ms < 10
}
```

## Performance Tuning

### 1. Policy Optimization

#### Use Built-in Functions

```rego
# ❌ Slow: Manual iteration
slow_check if {
    item := input.items[_]
    item.value == "target"
}

# ✅ Fast: Built-in set operations
fast_check if {
    "target" in {item.value | item := input.items[_]}
}
```

#### Minimize Iterations

```rego
# ❌ Slow: Multiple iterations
slow_policy if {
    user_team := input.user.teams[_]
    resource_team := input.resource.teams[_]
    user_team == resource_team
}

# ✅ Fast: Set intersection
fast_policy if {
    user_teams := {t | t := input.user.teams[_]}
    resource_teams := {t | t := input.resource.teams[_]}
    count(user_teams & resource_teams) > 0
}
```

#### Short-Circuit Evaluation

```rego
# ❌ Slow: Always evaluates expensive checks
slow_allow if {
    expensive_check_1
    expensive_check_2
    cheap_check
}

# ✅ Fast: Cheap checks first
fast_allow if {
    cheap_check
    expensive_check_1
    expensive_check_2
}
```

### 2. Caching Strategy

```python
# Configure cache TTL based on sensitivity
cache_ttl_map = {
    "critical": 30,   # 30 seconds
    "high": 60,       # 1 minute
    "medium": 180,    # 3 minutes
    "low": 300,       # 5 minutes
}

# Disable cache for real-time checks
no_cache_actions = [
    "server:delete",
    "user:delete",
    "policy:update"
]
```

### 3. Index Optimization

```rego
# Add indexes for frequently accessed fields
# (configured in OPA)
{
    "decision_logs": {
        "partitions": {
            "partition_name": "user_id"
        }
    }
}
```

### 4. Policy Bundling

```bash
# Build optimized policy bundle
opa build -b opa/policies/ -o bundle.tar.gz

# Deploy bundle to OPA
curl -X PUT http://localhost:8181/v1/policies/sark \
  --data-binary @bundle.tar.gz
```

### Performance Targets

| Metric | Target | Optimization |
|--------|--------|-------------|
| P95 Latency (Cache Hit) | <5ms | Redis optimization |
| P95 Latency (Cache Miss) | <50ms | OPA optimization, policy simplification |
| Throughput | >500 req/s | Connection pooling, async operations |
| Cache Hit Rate | >80% | TTL tuning, cache key optimization |

## Best Practices

### 1. Policy Design

#### ✅ DO: Use Default Deny

```rego
# Start with deny
default allow := false

# Explicitly define allow conditions
allow if {
    # Specific conditions
}
```

#### ✅ DO: Provide Clear Reasons

```rego
reason := "Access granted: admin role" if {
    allow
    input.user.role == "admin"
}

reason := sprintf("Access denied: role '%s' cannot perform '%s'", [
    input.user.role,
    input.action
]) if {
    not allow
}
```

#### ✅ DO: Validate Input

```rego
# Check required fields
allow if {
    input.user.id  # Required
    input.action   # Required
    # ... rest of policy
}
```

#### ❌ DON'T: Use Implicit Allow

```rego
# ❌ Bad: No default, unclear what happens
allow if {
    input.user.role == "admin"
}
# What if role is not admin? Unclear!

# ✅ Good: Explicit default
default allow := false

allow if {
    input.user.role == "admin"
}
```

### 2. Security Best Practices

#### Fail Closed

```rego
# Always deny on error
default allow := false

allow if {
    # If this fails, deny by default
    risky_operation
}
```

#### Audit Everything

```rego
# Log all decisions
audit_log := {
    "user": input.user.id,
    "action": input.action,
    "allowed": allow,
    "reason": reason,
    "timestamp": time.now_ns()
}
```

#### Principle of Least Privilege

```rego
# Grant minimum necessary permissions
allow if {
    input.user.role == "developer"
    input.action == "tool:invoke"
    # NOT: allow all actions for developers
}
```

### 3. Maintainability

#### Use Descriptive Names

```rego
# ❌ Bad
allow if { x }

# ✅ Good
allow if { user_has_required_role }
```

#### Document Complex Logic

```rego
# Check if user can access resource based on team membership.
# Users must be in at least one common team with the resource.
# Admins bypass this check.
allow if {
    not input.user.role == "admin"
    user_teams & resource_teams != set()
}
```

#### Break Down Complex Policies

```rego
# ❌ Bad: Monolithic policy
allow if {
    (input.user.role == "admin" || (input.user.role == "developer" && input.user.teams[_] == input.resource.teams[_])) &&
    (input.tool.sensitivity != "critical" || input.user.mfa_verified) &&
    # ... more complex logic
}

# ✅ Good: Modular helpers
user_has_access if {
    user_is_admin
}

user_has_access if {
    user_is_developer
    user_in_resource_team
}

allow if {
    user_has_access
    mfa_requirements_met
}
```

### 4. Testing Best Practices

#### Test All Paths

```rego
# Test allow path
test_allow_case if { ... }

# Test deny path
test_deny_case if { ... }

# Test edge cases
test_edge_case_missing_data if { ... }
test_edge_case_null_values if { ... }
```

#### Use Meaningful Test Names

```rego
# ❌ Bad
test_1 if { ... }

# ✅ Good
test_admin_can_delete_servers if { ... }
test_developer_cannot_delete_servers if { ... }
```

## Real-World Examples

### Example 1: Development/Staging/Production Environments

```rego
package sark.examples.environment

import rego.v1

default allow := false

# Development: Allow all developers
allow if {
    input.context.environment == "development"
    input.user.role in ["developer", "admin"]
}

# Staging: Require approval
allow if {
    input.context.environment == "staging"
    input.user.role in ["developer", "admin"]
    input.context.approved_by != ""
}

# Production: Admin only + MFA
allow if {
    input.context.environment == "production"
    input.user.role == "admin"
    input.user.mfa_verified == true
}
```

### Example 2: Temporary Access Grants

```rego
package sark.examples.temporary_access

import rego.v1

default allow := false

# Check if user has active temporary grant
has_temporary_grant if {
    grant := input.user.temporary_grants[_]
    grant.resource_id == input.resource.id
    grant.action == input.action

    # Grant not expired
    current_time := time.now_ns()
    current_time >= grant.start_time
    current_time <= grant.end_time
}

allow if {
    has_temporary_grant
}

# Log temporary access usage
audit_log := {
    "type": "temporary_access",
    "grant_id": grant.id,
    "expires_at": grant.end_time
} if {
    grant := input.user.temporary_grants[_]
    grant.resource_id == input.resource.id
}
```

### Example 3: Approval Workflows

```rego
package sark.examples.approval_workflow

import rego.v1

default allow := false

# High-risk operations require approval
high_risk_action if {
    input.action in ["server:delete", "database:drop", "user:delete"]
}

# Check if action has approval
has_approval if {
    input.context.approval_id != ""
    approval := data.approvals[input.context.approval_id]
    approval.action == input.action
    approval.resource_id == input.resource.id
    approval.status == "approved"
    approval.approver_role == "admin"
}

allow if {
    high_risk_action
    has_approval
}

allow if {
    not high_risk_action
    # Regular authorization
    input.user.role in ["admin", "developer"]
}
```

### Example 4: Data Classification

```rego
package sark.examples.data_classification

import rego.v1

default allow := false

# Data classification levels
data_classification := {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "secret": 3
}

# User clearance levels
user_clearance := {
    "intern": 0,
    "employee": 1,
    "senior": 2,
    "executive": 3
}

# Allow if user clearance >= data classification
allow if {
    user_level := user_clearance[input.user.clearance]
    data_level := data_classification[input.data.classification]
    user_level >= data_level
}

# Require additional checks for secret data
allow if {
    input.data.classification == "secret"
    input.user.clearance == "executive"
    input.user.mfa_verified == true
    input.user.background_check_date >= input.policy_config.required_background_check_date
}
```

### Example 5: Rate Limiting by Role

```rego
package sark.examples.rate_limiting

import rego.v1

default allow := false

# Rate limits by role (requests per hour)
rate_limits := {
    "admin": 10000,
    "developer": 1000,
    "viewer": 100,
    "free_tier": 10
}

# Check rate limit
within_rate_limit if {
    user_requests := input.context.requests_last_hour
    max_requests := rate_limits[input.user.role]
    user_requests < max_requests
}

allow if {
    within_rate_limit
    # Other authorization checks
}

# Provide helpful error message
reason := sprintf("Rate limit exceeded: %d/%d requests in last hour", [
    input.context.requests_last_hour,
    rate_limits[input.user.role]
]) if {
    not within_rate_limit
}
```

### Example 6: Resource Ownership with Delegation

```rego
package sark.examples.delegation

import rego.v1

default allow := false

# User is owner
is_owner if {
    input.resource.owner_id == input.user.id
}

# User is delegated access
has_delegation if {
    delegation := input.resource.delegations[_]
    delegation.user_id == input.user.id
    delegation.actions[_] == input.action

    # Delegation not expired
    current_time := time.now_ns()
    current_time <= delegation.expires_at
}

allow if {
    is_owner
}

allow if {
    has_delegation
}
```

### Example 7: PCI-DSS Compliance

```rego
package sark.examples.pci_dss

import rego.v1

default allow := false

# Cardholder data access requires:
# 1. VPN connection
# 2. MFA
# 3. Business hours
# 4. Specific roles
# 5. Annual training completion

accessing_cardholder_data if {
    input.resource.contains_cardholder_data == true
}

pci_requirements_met if {
    # VPN required
    input.context.client_ip
    startswith(input.context.client_ip, "10.")

    # MFA required
    input.user.mfa_verified == true

    # Business hours only
    hour := time.clock([time.now_ns()])[0]
    hour >= 9
    hour < 17

    # Authorized roles
    input.user.role in ["pci_admin", "payment_processor"]

    # Training completion
    training_date := input.user.pci_training_date
    current_time := time.now_ns()
    # Training less than 1 year old
    (current_time - training_date) < (365 * 24 * 60 * 60 * 1000000000)
}

allow if {
    accessing_cardholder_data
    pci_requirements_met
}

# Non-cardholder data has standard rules
allow if {
    not accessing_cardholder_data
    input.user.role != "guest"
}
```

### Example 8: Break-Glass Access

```rego
package sark.examples.break_glass

import rego.v1

default allow := false

# Normal access path
allow if {
    normal_authorization
}

# Emergency "break-glass" access
allow if {
    input.context.break_glass == true

    # Must provide incident ticket
    input.context.incident_ticket != ""

    # Must be on-call engineer
    input.user.id in data.on_call_engineers

    # Log for audit
    trace(sprintf("BREAK-GLASS ACCESS: User %s, Incident %s", [
        input.user.id,
        input.context.incident_ticket
    ]))
}

# Require break-glass review
audit_flag := "break_glass_review_required" if {
    input.context.break_glass == true
}
```

### Example 9: Cost-Based Authorization

```rego
package sark.examples.cost_based

import rego.v1

default allow := false

# Estimate operation cost
operation_cost := cost if {
    # Base cost by action
    base_costs := {
        "compute:start": 10,
        "compute:stop": 0,
        "storage:create": 50,
        "database:query": 1
    }

    cost := base_costs[input.action] * input.resource.quantity
}

# Check user budget
within_budget if {
    user_spent := input.user.spending_this_month
    user_limit := input.user.monthly_budget
    user_spent + operation_cost <= user_limit
}

# Require approval for expensive operations
requires_approval if {
    operation_cost > 1000
}

allow if {
    within_budget
    not requires_approval
}

allow if {
    within_budget
    requires_approval
    input.context.manager_approval == true
}

reason := sprintf("Estimated cost $%d exceeds remaining budget $%d", [
    operation_cost,
    input.user.monthly_budget - input.user.spending_this_month
]) if {
    not within_budget
}
```

### Example 10: Compliance Tagging

```rego
package sark.examples.compliance

import rego.v1

default allow := false

# Required compliance tags for production resources
required_tags := {
    "cost_center",
    "data_classification",
    "owner",
    "compliance_framework"
}

# Check if resource has required tags
has_required_tags if {
    resource_tags := {tag | tag := input.resource.tags[_].key}
    missing := required_tags - resource_tags
    count(missing) == 0
}

# Enforce tagging for production
allow if {
    input.context.environment == "production"
    input.action == "resource:create"
    has_required_tags
}

# Development doesn't require tags
allow if {
    input.context.environment != "production"
    input.action == "resource:create"
}

# Provide helpful error
reason := sprintf("Missing required tags: %v", [
    required_tags - {tag | tag := input.resource.tags[_].key}
]) if {
    input.context.environment == "production"
    not has_required_tags
}
```

## Troubleshooting

### Common Issues

#### 1. Policy Not Taking Effect

**Symptoms**: Policy changes not reflected in decisions

**Solutions**:
```bash
# Verify policy is loaded
curl http://localhost:8181/v1/policies

# Check OPA logs
docker logs opa

# Force policy reload
curl -X PUT http://localhost:8181/v1/policies/sark \
  --data-binary @bundle.tar.gz
```

#### 2. Slow Policy Evaluation

**Symptoms**: P95 latency >100ms

**Solutions**:
```rego
# Profile policy
# Add to policy:
trace(sprintf("Checkpoint 1: %v", [time.now_ns()]))

# Optimize iterations
# Use set operations instead of loops

# Enable caching
# Configure appropriate cache TTL
```

#### 3. Unexpected Denials

**Symptoms**: User denied when should be allowed

**Debug Steps**:
```bash
# Get decision details
curl http://localhost:8000/api/v1/policy/audit/decisions/{decision_id}

# Check policy results
{
  "policy_results": {
    "rbac": {"allow": true},
    "team_access": {"allow": false},  # ← Problem here
    "sensitivity": {"allow": true}
  }
}

# Review specific policy logic
```

#### 4. Cache Staleness

**Symptoms**: Policy changes not reflected immediately

**Solutions**:
```python
# Invalidate cache for specific user/action
await cache.invalidate_pattern(f"policy:{user_id}:{action}:*")

# Reduce cache TTL for critical operations
cache_ttl = 30  # 30 seconds for critical

# Disable cache for real-time requirements
cache_enabled = False
```

### Debugging Tools

#### OPA REPL

```bash
# Start REPL with policies loaded
opa run opa/policies/

# Test policy interactively
> data.sark.defaults.rbac.allow with input as {"user": {"role": "admin"}, "action": "tool:invoke"}
true
```

#### Policy Decision Logs

```bash
# Query recent denials
curl "http://localhost:8000/api/v1/policy/audit/decisions?result=deny&limit=10"

# Get top denial reasons
curl "http://localhost:8000/api/v1/policy/audit/analytics/denial-reasons"
```

#### Performance Profiling

```bash
# Enable profiling in OPA
opa run --server --log-level=debug

# Check evaluation metrics
curl http://localhost:8000/metrics | grep policy_evaluation
```

## Additional Resources

### Documentation
- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Rego Language Guide](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [OPA Best Practices](https://www.openpolicyagent.org/docs/latest/policy-testing/)

### SARK Specific
- [Policy Performance Report](POLICY_PERFORMANCE_REPORT.md)
- [Advanced OPA Policies](ADVANCED_OPA_POLICIES.md)
- [Policy Audit Trail](POLICY_AUDIT_TRAIL.md)
- [Load Testing Guide](../tests/load/README.md)

### Tools
- [OPA Playground](https://play.openpolicyagent.org/)
- [VS Code OPA Extension](https://marketplace.visualstudio.com/items?itemName=tsandall.opa)
- [Rego Unit Test Generator](https://github.com/open-policy-agent/vscode-opa)

---

**Version**: 1.0
**Last Updated**: 2024-11-22
**Maintainer**: SARK Team
