# SARK Gateway Authorization Policy
# This policy controls which users can invoke which tools via the MCP Gateway

package mcp.gateway

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Deny
# =============================================================================

# By default, deny all Gateway requests
default allow := false

# =============================================================================
# Admin Access
# =============================================================================

# Allow administrators to invoke any tool on any server
allow if {
    input.user.roles[_] == "admin"
    input.action == "gateway:tool:invoke"
}

# Allow administrators to access any server
allow if {
    input.user.roles[_] == "admin"
    input.action == "gateway:server:access"
}

# =============================================================================
# Analyst Access
# =============================================================================

# Allow analysts to execute SELECT queries on the database
allow if {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "execute_query"

    # Only allow SELECT queries (read-only)
    query := input.parameters.query
    lower_query := lower(query)
    startswith(lower_query, "select")
}

# Allow analysts to list tables
allow if {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "list_tables"
}

# Allow analysts to describe table schemas
allow if {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "describe_table"
}

# =============================================================================
# Developer Access
# =============================================================================

# Allow developers to access GitHub repository information
allow if {
    input.user.roles[_] == "developer"
    input.action == "gateway:tool:invoke"
    input.server_name == "github-mcp"
    input.tool_name in ["get_repo", "list_repos", "search_repos"]
}

# Allow developers to read issues
allow if {
    input.user.roles[_] == "developer"
    input.action == "gateway:tool:invoke"
    input.server_name == "github-mcp"
    input.tool_name in ["get_issue", "list_issues"]
}

# Allow developers to create issues (but not close/delete)
allow if {
    input.user.roles[_] == "developer"
    input.action == "gateway:tool:invoke"
    input.server_name == "github-mcp"
    input.tool_name == "create_issue"
}

# =============================================================================
# Explicit Denies (Destructive Operations)
# =============================================================================

# Deny non-admins from executing destructive SQL operations
deny contains "Only admins can execute destructive SQL operations" if {
    input.user.roles[_] != "admin"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "execute_mutation"
}

# Deny DROP, DELETE, TRUNCATE queries for non-admins
deny contains "DROP, DELETE, TRUNCATE queries require admin role" if {
    input.user.roles[_] != "admin"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    query := input.parameters.query
    lower_query := lower(query)

    # Check for destructive keywords
    destructive_keywords := ["drop", "delete", "truncate"]
    some keyword in destructive_keywords
    contains(lower_query, keyword)
}

# Deny closing/deleting GitHub issues for non-admins
deny contains "Only admins can close or delete GitHub issues" if {
    input.user.roles[_] != "admin"
    input.action == "gateway:tool:invoke"
    input.server_name == "github-mcp"
    input.tool_name in ["close_issue", "delete_issue"]
}

# =============================================================================
# Parameter Filtering
# =============================================================================

# Filter sensitive parameters from SQL queries
filtered_parameters := filtered if {
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "execute_query"

    # Remove password fields from parameters
    filtered := object.remove(input.parameters, ["password", "secret", "api_key"])
}

# Default: no filtering (pass through parameters)
filtered_parameters := input.parameters if {
    not input.server_name == "postgres-mcp"
}

filtered_parameters := input.parameters if {
    input.server_name == "postgres-mcp"
    not input.tool_name == "execute_query"
}

# =============================================================================
# Audit Decisions
# =============================================================================

# Provide detailed reason for allow decisions
reason := msg if {
    allow
    input.user.roles[_] == "admin"
    msg := sprintf("Allowed: admin user %s can perform any action", [input.user.email])
}

reason := msg if {
    allow
    input.user.roles[_] == "analyst"
    msg := sprintf("Allowed: analyst %s can query database", [input.user.email])
}

reason := msg if {
    allow
    input.user.roles[_] == "developer"
    msg := sprintf("Allowed: developer %s can access GitHub tools", [input.user.email])
}

# Provide detailed reason for deny decisions
reason := msg if {
    not allow
    count(deny) > 0
    msg := concat("; ", deny)
}

reason := "Denied: insufficient permissions" if {
    not allow
    count(deny) == 0
}

# =============================================================================
# Cache TTL
# =============================================================================

# Cache positive decisions for 60 seconds
cache_ttl := 60 if {
    allow
}

# Do not cache negative decisions
cache_ttl := 0 if {
    not allow
}
