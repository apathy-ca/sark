# Server Registration Policy
# Controls which users can register MCP servers based on sensitivity levels

package sark.server

import future.keywords.if
import future.keywords.in

# Default deny all registrations
default allow = false
default reason = "No matching registration rule"

# =============================================================================
# Sensitivity-Based Registration Rules
# =============================================================================

# Anyone can register low sensitivity servers
allow if {
    input.action == "register"
    input.resource.sensitivity == "low"
}

# Developers and above can register medium sensitivity servers
allow if {
    input.action == "register"
    input.resource.sensitivity == "medium"
    input.user.role in ["developer", "admin", "security_admin"]
}

# Only admins can register high sensitivity servers
allow if {
    input.action == "register"
    input.resource.sensitivity == "high"
    input.user.role in ["admin", "security_admin"]
}

# =============================================================================
# Team-Based Access Control
# =============================================================================

# Users can register servers for their own team
allow if {
    input.action == "register"
    input.user.team_id == input.resource.team_id
    input.resource.sensitivity != "high"
}

# Team leads can register any server for their team
allow if {
    input.action == "register"
    input.user.role == "team_lead"
    input.user.team_id == input.resource.team_id
}

# =============================================================================
# Production Environment Protection
# =============================================================================

# Production servers require additional approval
allow if {
    input.action == "register"
    contains(input.resource.name, "prod")
    input.resource.approved_by != null
    input.user.role in ["admin", "security_admin"]
}

reason := "Production servers require admin approval" if {
    input.action == "register"
    contains(input.resource.name, "prod")
    input.resource.approved_by == null
}

# =============================================================================
# Quota and Limits
# =============================================================================

# Enforce per-user server registration limits
exceeds_quota := true if {
    input.user.server_count >= 10
    not input.user.role in ["admin", "team_lead"]
}

reason := sprintf("User has exceeded server quota (%d/10)", [input.user.server_count]) if {
    exceeds_quota
}

# =============================================================================
# Compliance and Auditing
# =============================================================================

# Servers handling PII require compliance acknowledgment
allow if {
    input.action == "register"
    input.resource.handles_pii == true
    input.resource.compliance_acknowledged == true
    input.user.compliance_trained == true
}

reason := "PII-handling servers require compliance training and acknowledgment" if {
    input.action == "register"
    input.resource.handles_pii == true
    not input.resource.compliance_acknowledged
}
