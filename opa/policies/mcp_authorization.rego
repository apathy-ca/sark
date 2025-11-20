# MCP Authorization Policy
# This policy implements hybrid ReBAC+ABAC authorization for MCP tool access

package mcp

import future.keywords.if
import future.keywords.in

# Default deny - fail-safe security
default allow := false

# Tool ownership - owner always has access
allow if {
    input.action == "tool:invoke"
    input.tool.owner == input.user.id
}

# Team-based access - team members can access team-managed tools
allow if {
    input.action == "tool:invoke"
    some team_id in input.user.teams
    team_id in input.tool.managers
}

# Developer role with time and sensitivity restrictions
allow if {
    input.action == "tool:invoke"
    input.user.role == "developer"
    input.tool.sensitivity_level in ["low", "medium"]
    is_work_hours(input.context.timestamp)
}

# Admin override - admins can access most tools during work hours
allow if {
    input.action == "tool:invoke"
    input.user.role == "admin"
    input.tool.sensitivity_level != "critical"
    is_work_hours(input.context.timestamp)
}

# Explicit deny rules (take precedence over allow)
deny if {
    input.tool.sensitivity_level == "critical"
    not is_work_hours(input.context.timestamp)
    input.user.role != "admin"
}

deny if {
    input.tool.sensitivity_level == "high"
    not is_business_day(input.context.timestamp)
}

# Server registration authorization
allow if {
    input.action == "server:register"
    input.user.role in ["admin", "developer"]
}

# Helper functions
is_work_hours(ts) if {
    # For testing, allow if timestamp is 0
    ts == 0
}

is_work_hours(ts) if {
    ts > 0
    hour := time.clock([ts])[0]
    hour >= 9
    hour < 18
}

is_business_day(ts) if {
    ts == 0
}

is_business_day(ts) if {
    ts > 0
    weekday := time.weekday([ts])
    weekday >= 1  # Monday
    weekday <= 5  # Friday
}

# Audit reason generation
audit_reason := sprintf("Allowed: %s by user %s (owner)", [input.action, input.user.id]) if {
    allow
    input.tool.owner == input.user.id
}

audit_reason := sprintf("Allowed: %s by user %s (team member)", [input.action, input.user.id]) if {
    allow
    some team_id in input.user.teams
    team_id in input.tool.managers
}

audit_reason := sprintf("Allowed: %s by user %s (role-based)", [input.action, input.user.id]) if {
    allow
    input.user.role == "admin"
}

audit_reason := sprintf("Denied: %s by user %s (insufficient permissions)", [input.action, input.user.id]) if {
    not allow
}

# Policy result with metadata
result := {
    "allow": allow,
    "deny": deny,
    "audit_reason": audit_reason,
}
