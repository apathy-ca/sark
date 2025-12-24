# Tool Discovery Policy
# Controls which tools are visible to users based on permissions

package sark.tools

import future.keywords.if
import future.keywords.in

# Default allow tool discovery (but filter results)
default allow = true
default visible_tools = []

# =============================================================================
# Tool Visibility Rules
# =============================================================================

# Admins can see all tools
visible_tools := input.tools if {
    input.user.role == "admin"
}

# Developers can see non-admin tools
visible_tools := [tool |
    some tool in input.tools
    not tool.requires_admin
] if {
    input.user.role == "developer"
}

# Regular users can only see read-only tools
visible_tools := [tool |
    some tool in input.tools
    tool.read_only == true
] if {
    input.user.role == "user"
}

# Data analysts can see data-related tools
visible_tools := [tool |
    some tool in input.tools
    startswith(tool.category, "data")
] if {
    input.user.role == "data_analyst"
}

# =============================================================================
# Tool Categorization
# =============================================================================

# Categorize tools based on risk level
tool_risk_level(tool) := "high" if {
    tool.can_modify_data == true
    tool.affects_production == true
}

tool_risk_level(tool) := "medium" if {
    tool.can_modify_data == true
    not tool.affects_production
}

tool_risk_level(tool) := "low" if {
    tool.read_only == true
}

# =============================================================================
# Server-Based Filtering
# =============================================================================

# Filter tools based on server access permissions
has_server_access(server_name) if {
    input.user.role == "admin"
}

has_server_access(server_name) if {
    server_name in input.user.accessible_servers
}

has_server_access(server_name) if {
    server_name in input.user.team_servers
}

# Only show tools from accessible servers
visible_tools := [tool |
    some tool in input.tools
    has_server_access(tool.server_name)
] if {
    not input.user.role == "admin"
}
