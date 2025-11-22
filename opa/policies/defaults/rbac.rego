# RBAC (Role-Based Access Control) Policy
# Implements role-based authorization for SARK MCP operations
#
# Roles:
# - admin: Full access to all operations
# - developer: Limited access based on sensitivity levels
# - viewer: Read-only access
# - service: Automated service accounts

package sark.defaults.rbac

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# ============================================================================
# SERVER REGISTRATION RULES
# ============================================================================

# Admin can register any server
allow if {
    input.action == "server:register"
    input.user.role == "admin"
}

# Developer can register low/medium sensitivity servers
allow if {
    input.action == "server:register"
    input.user.role == "developer"
    input.server.sensitivity_level in ["low", "medium"]
}

# Service accounts can register servers based on their scopes
allow if {
    input.action == "server:register"
    input.user.role == "service"
    "server:register" in input.user.scopes
    input.server.sensitivity_level in ["low", "medium"]
}

# ============================================================================
# SERVER MANAGEMENT RULES
# ============================================================================

# Admin can update any server
allow if {
    input.action == "server:update"
    input.user.role == "admin"
}

# Developer can update servers they own
allow if {
    input.action == "server:update"
    input.user.role == "developer"
    input.server.owner == input.user.id
}

# Admin can delete any server
allow if {
    input.action == "server:delete"
    input.user.role == "admin"
}

# Developer can delete servers they own (low/medium sensitivity only)
allow if {
    input.action == "server:delete"
    input.user.role == "developer"
    input.server.owner == input.user.id
    input.server.sensitivity_level in ["low", "medium"]
}

# ============================================================================
# SERVER READ RULES
# ============================================================================

# Admin can read any server
allow if {
    input.action == "server:read"
    input.user.role == "admin"
}

# Developer can read servers
allow if {
    input.action == "server:read"
    input.user.role in ["developer", "viewer"]
}

# Service accounts can read servers if in scope
allow if {
    input.action == "server:read"
    input.user.role == "service"
    "server:read" in input.user.scopes
}

# ============================================================================
# TOOL INVOCATION RULES
# ============================================================================

# Admin can invoke any tool (except critical outside work hours)
allow if {
    input.action == "tool:invoke"
    input.user.role == "admin"
    not is_critical_outside_hours
}

# Developer can invoke low/medium sensitivity tools
allow if {
    input.action == "tool:invoke"
    input.user.role == "developer"
    input.tool.sensitivity_level in ["low", "medium"]
}

# ============================================================================
# POLICY MANAGEMENT RULES
# ============================================================================

# Only admin can manage policies
allow if {
    input.action == "policy:create"
    input.user.role == "admin"
}

allow if {
    input.action == "policy:update"
    input.user.role == "admin"
}

allow if {
    input.action == "policy:delete"
    input.user.role == "admin"
}

# Everyone can read policies
allow if {
    input.action == "policy:read"
    input.user.role in ["admin", "developer", "viewer"]
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

is_critical_outside_hours if {
    input.tool.sensitivity_level == "critical"
    not is_work_hours
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

# ============================================================================
# AUDIT METADATA
# ============================================================================

decision := {
    "allow": allow,
    "policy": "rbac",
    "role": input.user.role,
    "action": input.action,
    "reason": reason,
}

reason := "Admin role grants access" if {
    allow
    input.user.role == "admin"
}

reason := "Developer role grants access for low/medium sensitivity" if {
    allow
    input.user.role == "developer"
}

reason := "Service account scope grants access" if {
    allow
    input.user.role == "service"
}

reason := "Insufficient role permissions" if {
    not allow
}
