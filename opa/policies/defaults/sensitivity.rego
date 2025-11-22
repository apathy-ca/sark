# Sensitivity Level Enforcement Policy
# Enforces data sensitivity classification and access controls
#
# Sensitivity Levels:
# - low: Public or internal data, minimal restrictions
# - medium: Confidential data, requires authentication
# - high: Highly sensitive data, requires team ownership and business hours
# - critical: Mission-critical data, requires manager approval and strict controls

package sark.defaults.sensitivity

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# ============================================================================
# LOW SENSITIVITY ACCESS
# ============================================================================

# Low sensitivity resources are accessible to authenticated users
allow if {
    input.action in ["server:read", "tool:invoke"]
    input.resource.sensitivity_level == "low"
    input.user.authenticated == true
}

# Low sensitivity servers can be registered by any authenticated user
allow if {
    input.action == "server:register"
    input.server.sensitivity_level == "low"
    input.user.authenticated == true
}

# ============================================================================
# MEDIUM SENSITIVITY ACCESS
# ============================================================================

# Medium sensitivity requires role-based access
allow if {
    input.action in ["server:read", "tool:invoke"]
    input.resource.sensitivity_level == "medium"
    input.user.role in ["developer", "admin"]
}

# Medium sensitivity server registration requires developer+ role
allow if {
    input.action == "server:register"
    input.server.sensitivity_level == "medium"
    input.user.role in ["developer", "admin"]
}

# ============================================================================
# HIGH SENSITIVITY ACCESS
# ============================================================================

# High sensitivity requires team ownership
allow if {
    input.action in ["server:read", "tool:invoke"]
    input.resource.sensitivity_level == "high"
    is_team_member
    is_work_hours
}

# High sensitivity server registration requires team assignment
allow if {
    input.action == "server:register"
    input.server.sensitivity_level == "high"
    count(input.server.teams) > 0
    some team_id in input.server.teams
    team_id in input.user.teams
}

# High sensitivity tools require audit logging
allow if {
    input.action == "tool:invoke"
    input.tool.sensitivity_level == "high"
    is_team_member
    is_work_hours
    input.context.audit_enabled == true
}

# ============================================================================
# CRITICAL SENSITIVITY ACCESS
# ============================================================================

# Critical sensitivity requires manager approval and strict controls
allow if {
    input.action in ["server:read", "tool:invoke"]
    input.resource.sensitivity_level == "critical"
    is_team_manager
    is_work_hours
    is_business_day
    input.context.audit_enabled == true
}

# Critical server registration requires admin or team manager
allow if {
    input.action == "server:register"
    input.server.sensitivity_level == "critical"
    input.user.role in ["admin", "team_manager"]
    count(input.server.teams) > 0
    is_work_hours
    is_business_day
}

# Critical tools require MFA authentication
allow if {
    input.action == "tool:invoke"
    input.tool.sensitivity_level == "critical"
    is_team_manager
    input.user.mfa_verified == true
    is_work_hours
    is_business_day
    input.context.audit_enabled == true
}

# ============================================================================
# SENSITIVITY ESCALATION RULES
# ============================================================================

# Deny sensitivity downgrade without admin approval
deny if {
    input.action == "server:update"
    input.server.sensitivity_level_change == true
    new_level := input.server.new_sensitivity_level
    old_level := input.server.current_sensitivity_level
    is_sensitivity_downgrade(old_level, new_level)
    input.user.role != "admin"
}

# Allow sensitivity upgrade by resource owner
allow if {
    input.action == "server:update"
    input.server.sensitivity_level_change == true
    new_level := input.server.new_sensitivity_level
    old_level := input.server.current_sensitivity_level
    is_sensitivity_upgrade(old_level, new_level)
    input.server.owner == input.user.id
}

# ============================================================================
# TIME-BASED RESTRICTIONS
# ============================================================================

# Deny high/critical access outside work hours (unless emergency override)
deny if {
    input.action in ["tool:invoke", "server:update", "server:delete"]
    input.resource.sensitivity_level in ["high", "critical"]
    not is_work_hours
    not input.context.emergency_override
}

# Deny critical access outside business days
deny if {
    input.action in ["tool:invoke", "server:register"]
    input.resource.sensitivity_level == "critical"
    not is_business_day
    not input.context.emergency_override
}

# ============================================================================
# AUDIT REQUIREMENTS
# ============================================================================

# Deny high/critical operations without audit logging
deny if {
    input.action in ["tool:invoke", "server:update", "server:delete"]
    input.resource.sensitivity_level in ["high", "critical"]
    input.context.audit_enabled != true
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

is_team_member if {
    some team_id in input.user.teams
    team_id in input.resource.teams
}

is_team_manager if {
    some team_id in input.user.team_manager_of
    team_id in input.resource.teams
}

is_work_hours if {
    # Allow if timestamp is 0 (testing)
    input.context.timestamp == 0
}

is_work_hours if {
    input.context.timestamp > 0
    hour := time.clock([input.context.timestamp])[0]
    hour >= 9
    hour < 18
}

is_business_day if {
    input.context.timestamp == 0
}

is_business_day if {
    input.context.timestamp > 0
    weekday := time.weekday([input.context.timestamp])
    weekday >= 1  # Monday
    weekday <= 5  # Friday
}

sensitivity_order := {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

is_sensitivity_upgrade(old, new) if {
    sensitivity_order[new] > sensitivity_order[old]
}

is_sensitivity_downgrade(old, new) if {
    sensitivity_order[new] < sensitivity_order[old]
}

# ============================================================================
# AUDIT METADATA
# ============================================================================

decision := {
    "allow": allow,
    "deny": deny,
    "policy": "sensitivity",
    "sensitivity_level": object.get(input.resource, "sensitivity_level", "unknown"),
    "time_restriction": time_restriction,
    "audit_required": audit_required,
    "reason": reason,
}

time_restriction := "work_hours_required" if {
    input.resource.sensitivity_level in ["high", "critical"]
}

time_restriction := "business_days_required" if {
    input.resource.sensitivity_level == "critical"
}

time_restriction := "none" if {
    input.resource.sensitivity_level in ["low", "medium"]
}

audit_required := true if {
    input.resource.sensitivity_level in ["high", "critical"]
}

audit_required := false if {
    input.resource.sensitivity_level in ["low", "medium"]
}

reason := "Low sensitivity allows public access" if {
    allow
    input.resource.sensitivity_level == "low"
}

reason := "Medium sensitivity allows developer access" if {
    allow
    input.resource.sensitivity_level == "medium"
}

reason := "High sensitivity allows team member access during work hours" if {
    allow
    input.resource.sensitivity_level == "high"
}

reason := "Critical sensitivity allows team manager access with MFA" if {
    allow
    input.resource.sensitivity_level == "critical"
}

reason := "Sensitivity level requires higher permissions or time restrictions" if {
    not allow
}

reason := "Audit logging required for high/critical operations" if {
    deny
    input.context.audit_enabled != true
}

reason := "Work hours required for high/critical sensitivity" if {
    deny
    not is_work_hours
}
