# SARK Default Policy Bundle
# Main policy that combines RBAC, team access, sensitivity, and advanced policies
#
# This policy evaluates all sub-policies and makes a final authorization decision
# based on the combined results.
#
# Policies evaluated:
# - RBAC: Role-based access control
# - Team Access: Team ownership and permissions
# - Sensitivity: Sensitivity level enforcement
# - Time-based: Business hours and time restrictions
# - IP Filtering: IP allowlist/blocklist and geo-restrictions
# - MFA Required: Multi-factor authentication requirements

package sark.defaults.main

import data.sark.defaults.rbac
import data.sark.defaults.team_access
import data.sark.defaults.sensitivity
import data.sark.policies.time_based
import data.sark.policies.ip_filtering
import data.sark.policies.mfa_required
import future.keywords.if
import future.keywords.in

# ============================================================================
# MAIN AUTHORIZATION DECISION
# ============================================================================

# Default deny - fail-safe security
default allow := false

# Allow if ALL applicable policies allow
allow if {
    # RBAC must allow
    rbac.allow

    # Team access must allow (if team-based resource)
    team_access_allows

    # Sensitivity enforcement must allow
    sensitivity.allow

    # Time-based restrictions must allow
    time_based.allow

    # IP filtering must allow
    ip_filtering.allow

    # MFA requirements must be satisfied
    mfa_required.allow

    # No explicit denies
    not rbac.deny
    not team_access.deny
    not sensitivity.deny
}

# ============================================================================
# POLICY COMBINATION LOGIC
# ============================================================================

# Team access is required for team-owned resources
team_access_allows if {
    has_teams
    team_access.allow
}

# Team access not required for non-team resources
team_access_allows if {
    not has_teams
}

has_teams if {
    count(object.get(input, "resource", {}).teams) > 0
}

has_teams if {
    count(object.get(input, "server", {}).teams) > 0
}

has_teams if {
    count(object.get(input, "tool", {}).teams) > 0
}

# ============================================================================
# EXPLICIT DENY AGGREGATION
# ============================================================================

# Collect all deny reasons from sub-policies
deny if {
    rbac.deny
}

deny if {
    team_access.deny
}

deny if {
    sensitivity.deny
}

# ============================================================================
# AUDIT TRAIL GENERATION
# ============================================================================

decision := {
    "allow": allow,
    "deny": deny,
    "policies_evaluated": policies_evaluated,
    "policy_results": policy_results,
    "reason": reason,
    "timestamp": time.now_ns(),
}

policies_evaluated := [
    "rbac",
    "team_access",
    "sensitivity",
    "time_based",
    "ip_filtering",
    "mfa_required",
]

policy_results := {
    "rbac": {
        "allow": rbac.allow,
        "deny": object.get(rbac, "deny", false),
        "reason": rbac.reason,
    },
    "team_access": {
        "allow": team_access.allow,
        "deny": object.get(team_access, "deny", false),
        "reason": team_access.reason,
    },
    "sensitivity": {
        "allow": sensitivity.allow,
        "deny": object.get(sensitivity, "deny", false),
        "reason": sensitivity.reason,
    },
    "time_based": {
        "allow": time_based.decision.allow,
        "reason": time_based.decision.reason,
        "violations": time_based.decision.violations,
        "current_time": time_based.decision.current_time,
    },
    "ip_filtering": {
        "allow": ip_filtering.decision.allow,
        "reason": ip_filtering.decision.reason,
        "violations": ip_filtering.decision.violations,
        "client_ip": ip_filtering.decision.client_ip,
    },
    "mfa_required": {
        "allow": mfa_required.decision.allow,
        "reason": mfa_required.decision.reason,
        "violations": mfa_required.decision.violations,
        "mfa_status": mfa_required.decision.mfa_status,
    },
}

# Generate human-readable reason
reason := "Access granted by all policies" if {
    allow
}

reason := sprintf("Access denied by RBAC: %s", [rbac.reason]) if {
    not allow
    not rbac.allow
}

reason := sprintf("Access denied by team access: %s", [team_access.reason]) if {
    not allow
    rbac.allow
    not team_access_allows
}

reason := sprintf("Access denied by sensitivity enforcement: %s", [sensitivity.reason]) if {
    not allow
    rbac.allow
    team_access_allows
    not sensitivity.allow
}

reason := sprintf("Access denied by time restrictions: %s", [time_based.decision.reason]) if {
    not allow
    rbac.allow
    team_access_allows
    sensitivity.allow
    not time_based.allow
}

reason := sprintf("Access denied by IP filtering: %s", [ip_filtering.decision.reason]) if {
    not allow
    rbac.allow
    team_access_allows
    sensitivity.allow
    time_based.allow
    not ip_filtering.allow
}

reason := sprintf("Access denied by MFA requirements: %s", [mfa_required.decision.reason]) if {
    not allow
    rbac.allow
    team_access_allows
    sensitivity.allow
    time_based.allow
    ip_filtering.allow
    not mfa_required.allow
}

reason := sprintf("Access explicitly denied: RBAC=%v, Team=%v, Sensitivity=%v", [
    object.get(rbac, "deny", false),
    object.get(team_access, "deny", false),
    object.get(sensitivity, "deny", false),
]) if {
    deny
}

# ============================================================================
# COMPLIANCE AND AUDIT METADATA
# ============================================================================

compliance_metadata := {
    "user_id": input.user.id,
    "user_role": input.user.role,
    "action": input.action,
    "resource_type": resource_type,
    "sensitivity_level": sensitivity_level,
    "teams_involved": teams_involved,
    "time_of_request": input.context.timestamp,
    "work_hours_compliant": work_hours_compliant,
    "audit_enabled": object.get(input.context, "audit_enabled", false),
}

resource_type := "server" if {
    input.action in ["server:register", "server:read", "server:update", "server:delete"]
}

resource_type := "tool" if {
    input.action == "tool:invoke"
}

resource_type := "policy" if {
    input.action in ["policy:create", "policy:read", "policy:update", "policy:delete"]
}

resource_type := "unknown" if {
    not resource_type
}

sensitivity_level := object.get(input.resource, "sensitivity_level",
                     object.get(input.server, "sensitivity_level",
                     object.get(input.tool, "sensitivity_level", "unknown")))

teams_involved := array.concat(
    object.get(input.user, "teams", []),
    object.get(input.resource, "teams",
    object.get(input.server, "teams",
    object.get(input.tool, "teams", [])))
)

work_hours_compliant := sensitivity.is_work_hours if {
    sensitivity_level in ["high", "critical"]
}

work_hours_compliant := true if {
    sensitivity_level in ["low", "medium"]
}

# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

# Policy evaluation performance tracking
performance := {
    "cache_key": cache_key,
    "cacheable": cacheable,
    "cache_ttl_seconds": cache_ttl,
}

# Generate cache key for this decision
cache_key := sprintf("policy:%s:%s:%s:%s", [
    input.user.id,
    input.action,
    resource_identifier,
    context_hash,
])

resource_identifier := object.get(input.resource, "id",
                       object.get(input.server, "id",
                       object.get(input.tool, "id", "unknown")))

# Simple hash of context (in production, use crypto.sha256)
context_hash := sprintf("%v", [input.context])

# Decisions are cacheable if they don't depend on time
cacheable := true if {
    sensitivity_level in ["low", "medium"]
    input.action in ["server:read", "tool:invoke"]
}

cacheable := false if {
    sensitivity_level in ["high", "critical"]
}

cacheable := false if {
    input.action in ["server:register", "server:update", "server:delete"]
}

# Cache TTL based on sensitivity (in seconds)
cache_ttl := 300 if {  # 5 minutes
    sensitivity_level == "low"
}

cache_ttl := 180 if {  # 3 minutes
    sensitivity_level == "medium"
}

cache_ttl := 60 if {   # 1 minute
    sensitivity_level == "high"
}

cache_ttl := 30 if {   # 30 seconds
    sensitivity_level == "critical"
}

cache_ttl := 120 if {  # Default 2 minutes
    not cache_ttl
}
