# Gateway Authorization Policy
# Defines authorization rules for MCP Gateway operations

package sark.gateway

import future.keywords.if
import future.keywords.in

# Default deny all requests
default allow = false
default reason = "No matching authorization rule"
default filtered_parameters = null

# =============================================================================
# Tool Invocation Rules
# =============================================================================

# Allow tool invocation for admins
allow if {
    input.action == "gateway:tool:invoke"
    input.user.role == "admin"
}

# Allow tool invocation for developers on non-production servers
allow if {
    input.action == "gateway:tool:invoke"
    input.user.role == "developer"
    not startswith(input.server.name, "prod-")
}

# Allow read-only tools for all authenticated users
allow if {
    input.action == "gateway:tool:invoke"
    input.tool.read_only == true
}

# Allow specific tools for specific roles
allow if {
    input.action == "gateway:tool:invoke"
    input.user.role == "data_analyst"
    input.tool.name in ["query_database", "export_report", "search_records"]
}

# Deny dangerous tools unless admin
reason := "Dangerous tool requires admin role" if {
    input.action == "gateway:tool:invoke"
    input.tool.dangerous == true
    not input.user.role == "admin"
}

# =============================================================================
# Parameter Filtering
# =============================================================================

# Filter sensitive parameters from database queries
filtered_parameters := filter_sensitive(input.parameters) if {
    input.action == "gateway:tool:invoke"
    input.tool.name == "query_database"
}

# Helper function to remove sensitive fields
filter_sensitive(params) := filtered if {
    sensitive_fields := ["password", "secret", "api_key", "token", "credit_card"]
    filtered := {k: v |
        some k, v in params
        not k in sensitive_fields
    }
}

# =============================================================================
# Context-Based Rules
# =============================================================================

# Allow access during business hours from office
allow if {
    input.action == "gateway:tool:invoke"
    input.context.time_of_day == "business_hours"
    input.context.location == "office"
    input.context.device_trust_level == "high"
}

# Allow emergency access for on-call engineers
allow if {
    input.action == "gateway:tool:invoke"
    input.user.on_call == true
    input.context.severity == "critical"
}

# =============================================================================
# Rate Limiting (informational - actual limiting done by API)
# =============================================================================

# Flag requests that exceed rate limits
rate_limit_exceeded := true if {
    input.context.request_count > 100
    input.context.time_window_seconds < 60
}

reason := "Rate limit exceeded" if {
    rate_limit_exceeded
}
