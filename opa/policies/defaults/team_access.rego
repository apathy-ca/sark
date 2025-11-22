# Team-Based Access Control Policy
# Implements team ownership and team-based permissions for MCP resources
#
# Team Access Rules:
# - Team members can access team-owned resources
# - Team managers have elevated permissions
# - High/critical sensitivity requires team ownership

package sark.defaults.team_access

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# ============================================================================
# TEAM OWNERSHIP RULES
# ============================================================================

# Team members can access team-owned servers
allow if {
    input.action in ["server:read", "tool:invoke"]
    some team_id in input.user.teams
    team_id in input.resource.teams
}

# Team managers can manage team-owned servers
allow if {
    input.action in ["server:update", "server:delete"]
    some team_id in input.user.team_manager_of
    team_id in input.resource.teams
    input.resource.sensitivity_level in ["low", "medium"]
}

# ============================================================================
# HIGH/CRITICAL SENSITIVITY REQUIREMENTS
# ============================================================================

# High sensitivity servers REQUIRE team ownership
allow if {
    input.action == "server:register"
    input.server.sensitivity_level == "high"
    count(input.server.teams) > 0
    some team_id in input.server.teams
    team_id in input.user.teams
}

# Critical sensitivity servers REQUIRE team ownership AND manager approval
allow if {
    input.action == "server:register"
    input.server.sensitivity_level == "critical"
    count(input.server.teams) > 0
    some team_id in input.server.teams
    team_id in input.user.team_manager_of
}

# ============================================================================
# TEAM TOOL ACCESS
# ============================================================================

# Team members can invoke team tools based on sensitivity
allow if {
    input.action == "tool:invoke"
    input.tool.sensitivity_level in ["low", "medium"]
    some team_id in input.user.teams
    team_id in input.tool.teams
}

# Team managers can invoke high sensitivity team tools
allow if {
    input.action == "tool:invoke"
    input.tool.sensitivity_level == "high"
    some team_id in input.user.team_manager_of
    team_id in input.tool.teams
}

# ============================================================================
# TEAM RESOURCE SHARING
# ============================================================================

# Team members can share resources within their team
allow if {
    input.action == "resource:share"
    input.target_team in input.user.teams
    input.resource.owner == input.user.id
}

# Team managers can share team resources with other teams
allow if {
    input.action == "resource:share"
    some team_id in input.user.team_manager_of
    team_id in input.resource.teams
}

# ============================================================================
# CROSS-TEAM ACCESS
# ============================================================================

# Allow cross-team access for public resources
allow if {
    input.action in ["server:read", "tool:invoke"]
    input.resource.visibility == "public"
    input.resource.sensitivity_level == "low"
}

# Allow cross-team access with explicit permissions
allow if {
    input.action in ["server:read", "tool:invoke"]
    some team_id in input.user.teams
    team_id in input.resource.allowed_teams
}

# ============================================================================
# EXPLICIT DENY RULES
# ============================================================================

# Deny high/critical server registration without team assignment
deny if {
    input.action == "server:register"
    input.server.sensitivity_level in ["high", "critical"]
    count(input.server.teams) == 0
}

# Deny tool invocation on critical tools without team manager status
deny if {
    input.action == "tool:invoke"
    input.tool.sensitivity_level == "critical"
    not is_team_manager_for_tool
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

is_team_manager_for_tool if {
    some team_id in input.user.team_manager_of
    team_id in input.tool.teams
}

is_team_member_for_resource if {
    some team_id in input.user.teams
    team_id in input.resource.teams
}

# ============================================================================
# AUDIT METADATA
# ============================================================================

decision := {
    "allow": allow,
    "deny": deny,
    "policy": "team_access",
    "user_teams": input.user.teams,
    "resource_teams": object.get(input, "resource", {}).teams,
    "reason": reason,
}

reason := "Team member access granted" if {
    allow
    is_team_member_for_resource
}

reason := "Team manager access granted" if {
    allow
    is_team_manager_for_tool
}

reason := "Public resource access granted" if {
    allow
    input.resource.visibility == "public"
}

reason := "Cross-team access granted via allowed_teams" if {
    allow
    some team_id in input.user.teams
    team_id in input.resource.allowed_teams
}

reason := "Team ownership required for high/critical sensitivity" if {
    deny
    input.server.sensitivity_level in ["high", "critical"]
    count(input.server.teams) == 0
}

reason := "No team membership or insufficient permissions" if {
    not allow
    not deny
}
