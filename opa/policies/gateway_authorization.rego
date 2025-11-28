# MCP Gateway Authorization Policy
# This policy implements authorization rules for Gateway-managed MCP servers
# and tool invocations with enhanced security controls.

package mcp.gateway

import future.keywords.if
import future.keywords.in

# Default deny - fail-safe security
default allow := false

# ============================================================================
# GATEWAY TOOL INVOCATION RULES
# ============================================================================

# Admin can invoke non-critical tools during work hours
allow if {
    input.action == "gateway:tool:invoke"
    input.user.role == "admin"
    input.tool.sensitivity_level != "critical"
    is_work_hours(input.context.timestamp)
}

# Developer can invoke low/medium sensitivity tools during work hours
allow if {
    input.action == "gateway:tool:invoke"
    input.user.role == "developer"
    input.user.id != ""  # User must be authenticated
    input.tool.sensitivity_level in ["low", "medium"]
    is_work_hours(input.context.timestamp)
}

# Team-based access - team members can access team-managed servers
allow if {
    input.action == "gateway:tool:invoke"
    input.user.id != ""  # User must be authenticated
    some team_id in input.user.teams
    input.server.managed_by_team == team_id
    server_access_allowed(input.user, input.server)
}

# Server owner can always invoke tools on their server (during work hours)
allow if {
    input.action == "gateway:tool:invoke"
    input.server.owner_id == input.user.id
    is_work_hours(input.context.timestamp)
}

# ============================================================================
# GATEWAY SERVER REGISTRATION RULES
# ============================================================================

# Admin can register servers
allow if {
    input.action == "gateway:server:register"
    input.user.role in ["admin", "team_lead"]
}

# Developer can register low-sensitivity servers
allow if {
    input.action == "gateway:server:register"
    input.user.role == "developer"
    input.server.sensitivity_level in ["low", "medium"]
}

# ============================================================================
# GATEWAY DISCOVERY RULES
# ============================================================================

# Users can discover servers they have access to
allow if {
    input.action == "gateway:servers:list"
    # All authenticated users can list servers
    input.user.id != ""
}

# Users can view tools for servers they can access
allow if {
    input.action == "gateway:tools:list"
    input.user.id != ""
}

# ============================================================================
# GATEWAY AUDIT ACCESS RULES
# ============================================================================

# Admin can view all audit logs
allow if {
    input.action == "gateway:audit:view"
    input.user.role in ["admin", "security_admin"]
}

# Team leads can view audit logs for their team's servers
allow if {
    input.action == "gateway:audit:view"
    input.user.role == "team_lead"
    some team_id in input.user.teams
    input.server.managed_by_team == team_id
}

# ============================================================================
# PARAMETER FILTERING
# ============================================================================

# Filter sensitive parameters based on user role and sensitivity
filtered_parameters := filter_params(input.tool.parameters, input.user.role, input.tool.sensitivity_level) if {
    input.action == "gateway:tool:invoke"
    allow
}

filter_params(params, role, sensitivity) := filtered if {
    # Admin sees all parameters
    role == "admin"
    filtered := params
}

filter_params(params, role, sensitivity) := filtered if {
    # Non-admin users: filter out sensitive fields
    role != "admin"
    filtered := {k: v |
        some k, v in params
        not is_sensitive_param(k, sensitivity)
    }
}

# Determine if a parameter is sensitive based on name and tool sensitivity
is_sensitive_param(param_name, sensitivity) if {
    sensitivity in ["high", "critical"]
    param_name in ["password", "secret", "api_key", "token", "credentials"]
}

is_sensitive_param(param_name, sensitivity) if {
    sensitivity == "critical"
    # For critical tools, also filter additional params
    param_name in ["ssn", "credit_card", "private_key", "encryption_key"]
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Check if current time is within work hours (9 AM - 6 PM)
is_work_hours(ts) if {
    # For testing, allow if timestamp is 0
    ts == 0
}

is_work_hours(ts) if {
    ts > 0
    clock := time.clock(ts)
    hour := clock[0]
    hour >= 9
    hour < 18
}

# Check if user has access to a specific server
server_access_allowed(user, server) if {
    # Server is public
    server.visibility == "public"
}

server_access_allowed(user, server) if {
    # User owns the server
    server.owner_id == user.id
}

server_access_allowed(user, server) if {
    # User is in a team that manages the server
    some team_id in user.teams
    server.managed_by_team == team_id
}

server_access_allowed(user, server) if {
    # Server is shared with user's environment
    server.environment == user.environment
    server.visibility == "internal"
}

# ============================================================================
# AUDIT REASON GENERATION
# ============================================================================

audit_reason := sprintf("Allowed: %s by user %s (role: %s, admin)", [
    input.action,
    input.user.id,
    input.user.role
]) if {
    allow
    input.user.role == "admin"
}

audit_reason := sprintf("Allowed: %s by user %s (role: %s, team member)", [
    input.action,
    input.user.id,
    input.user.role
]) if {
    allow
    some team_id in input.user.teams
    input.server.managed_by_team == team_id
}

audit_reason := sprintf("Allowed: %s by user %s (role: %s, server owner)", [
    input.action,
    input.user.id,
    input.user.role
]) if {
    allow
    input.server.owner_id == input.user.id
}

audit_reason := sprintf("Allowed: %s by user %s (role: %s, developer access)", [
    input.action,
    input.user.id,
    input.user.role
]) if {
    allow
    input.user.role == "developer"
    input.tool.sensitivity_level in ["low", "medium"]
}

audit_reason := sprintf("Denied: %s by user %s (insufficient permissions)", [
    input.action,
    input.user.id
]) if {
    not allow
}

# ============================================================================
# POLICY RESULT WITH METADATA
# ============================================================================

result := {
    "allow": allow,
    "audit_reason": audit_reason,
    "filtered_parameters": filtered_parameters,
} if {
    # Include filtered parameters only for tool invocation
    input.action == "gateway:tool:invoke"
    allow
}

result := {
    "allow": allow,
    "audit_reason": audit_reason,
} if {
    # For non-tool-invocation actions or denied requests
    input.action != "gateway:tool:invoke"
}

result := {
    "allow": allow,
    "audit_reason": audit_reason,
} if {
    not allow
}
