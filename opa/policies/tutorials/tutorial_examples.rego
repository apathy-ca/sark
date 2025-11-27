# Tutorial Policy Examples
# These policies demonstrate common access control patterns used in SARK tutorials
# See ldap/README.md for sample users and their expected permissions

package mcp.tutorials

import future.keywords.if
import future.keywords.in

# ============================================================================
# Example 1: Role-Based Access Control (RBAC)
# ============================================================================
# Tutorial Use: Tutorial 1 - Basic Setup
# Demonstrates: How developers can invoke low/medium/high sensitivity tools

# Developers can invoke low and medium sensitivity tools
allow_developer_basic if {
    input.user.role == "developer"
    input.action == "tool:invoke"
    input.tool.sensitivity_level in ["low", "medium"]
}

# Team leads (like john.doe) can also invoke high sensitivity tools
allow_team_lead if {
    "team_lead" in input.user.roles
    input.action == "tool:invoke"
    input.tool.sensitivity_level in ["low", "medium", "high"]
}

# ============================================================================
# Example 2: Team-Based Access Control (Attribute-Based)
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Team ownership and shared resource access

# Users can access tools owned by their team
allow_team_ownership if {
    input.action == "tool:invoke"
    some team in input.user.teams
    team == input.tool.team
}

# Data engineering team has special database access
allow_data_engineering_db if {
    "data-engineering" in input.user.teams
    input.action == "tool:invoke"
    input.tool.name == "execute_query"
    input.arguments.database in ["analytics", "reporting"]
}

# ============================================================================
# Example 3: Time-Based Access Control
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Business hours restrictions and weekend lockout

# Check if timestamp is during business hours (9 AM - 6 PM)
is_business_hours(timestamp) if {
    # Parse timestamp to get hour
    hour := time.clock([timestamp])[0]
    hour >= 9
    hour < 18
}

# Check if timestamp is a weekday (Monday-Friday)
is_weekday(timestamp) if {
    weekday := time.weekday([timestamp])
    weekday >= 1  # Monday
    weekday <= 5  # Friday
}

# High sensitivity tools require business hours
require_business_hours if {
    input.tool.sensitivity_level == "high"
    not is_business_hours(input.context.timestamp)
}

# Critical tools require both business hours AND weekdays
require_business_hours_and_weekday if {
    input.tool.sensitivity_level == "critical"
    not is_business_hours(input.context.timestamp)
}

require_business_hours_and_weekday if {
    input.tool.sensitivity_level == "critical"
    not is_weekday(input.context.timestamp)
}

# ============================================================================
# Example 4: Parameter Filtering and Data Masking
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Sensitive data protection and PII redaction

# Analyst (carol.analyst) gets limited database access with filtering
filtered_parameters_analyst contains param if {
    input.user.role == "analyst"
    input.tool.name == "execute_query"

    # Filter out DELETE, UPDATE, INSERT keywords
    query := input.arguments.query
    not contains(upper(query), "DELETE")
    not contains(upper(query), "UPDATE")
    not contains(upper(query), "INSERT")
    not contains(upper(query), "DROP")
    not contains(upper(query), "ALTER")

    # Return allowed parameters
    param := {
        "query": query,
        "database": "analytics",  # Force analytics DB only
        "limit": min([input.arguments.limit, 1000])  # Cap at 1000 rows
    }
}

# Helper function to check if string contains substring
contains(str, substr) if {
    indexof(str, substr) != -1
}

# Helper function to convert to uppercase
upper(str) := upper_result if {
    upper_result := upper(str)
}

# Helper function to get minimum value
min(values) := result if {
    result := sort(values)[0]
}

# ============================================================================
# Example 5: MFA Requirement for Critical Operations
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Multi-factor authentication enforcement

# Critical tools require MFA verification
require_mfa if {
    input.tool.sensitivity_level == "critical"
    not input.context.mfa_verified
}

# MFA must be recent (within last 5 minutes)
mfa_expired if {
    input.tool.sensitivity_level == "critical"
    input.context.mfa_verified

    # Parse timestamps
    now := time.now_ns()
    mfa_time := time.parse_rfc3339_ns(input.context.mfa_timestamp)

    # Check if MFA is older than 5 minutes (300 seconds = 300000000000 ns)
    (now - mfa_time) > 300000000000
}

# ============================================================================
# Example 6: IP-Based Access Control
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Network-based restrictions

# Corporate network CIDR ranges (example)
corporate_networks := [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16"
]

# Check if IP is in corporate network
is_corporate_ip(ip) if {
    some network in corporate_networks
    net.cidr_contains(network, ip)
}

# Critical tools require corporate network
require_corporate_network if {
    input.tool.sensitivity_level == "critical"
    not is_corporate_ip(input.context.ip_address)
}

# ============================================================================
# Example 7: Approval Workflow for Break-Glass Access
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Time-limited approval for exceptional access

# Check if approval is valid and not expired
has_valid_approval if {
    input.approval.approved_by
    not is_approval_expired(input.approval.expires_at)
}

# Check if approval has expired
is_approval_expired(expiry_time) if {
    now := time.now_ns()
    expiry := time.parse_rfc3339_ns(expiry_time)
    now > expiry
}

# Junior developers (jane.smith) need approval for high-sensitivity tools
require_approval_junior_dev if {
    input.user.role == "developer"
    "team_lead" not in input.user.roles
    input.tool.sensitivity_level == "high"
    not has_valid_approval
}

# ============================================================================
# Example 8: Database Query Validation
# ============================================================================
# Tutorial Use: Tutorial 1 - Basic Setup
# Demonstrates: SQL injection prevention and query safety

# Detect dangerous SQL keywords
dangerous_keywords := [
    "DELETE",
    "UPDATE",
    "INSERT",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "CREATE",
    "EXEC",
    "EXECUTE"
]

# Check if query contains dangerous keywords
query_is_dangerous if {
    input.tool.name == "execute_query"
    query := upper(input.arguments.query)
    some keyword in dangerous_keywords
    contains(query, keyword)
}

# Deny dangerous queries
deny_dangerous_query if {
    query_is_dangerous
}

# ============================================================================
# Example 9: Rate Limiting by Role
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Usage quotas and rate limits

# Define rate limits by role
rate_limits := {
    "admin": 10000,
    "developer": 1000,
    "analyst": 100,
    "junior_developer": 50
}

# Get rate limit for user role
user_rate_limit := limit if {
    limit := rate_limits[input.user.role]
} else := 100  # Default limit

# Check if user exceeded rate limit (requires external data)
exceeded_rate_limit if {
    # This would check against audit logs or cache
    # Simplified example:
    input.context.requests_last_hour > user_rate_limit
}

# ============================================================================
# Example 10: Environment-Based Access
# ============================================================================
# Tutorial Use: Tutorial 3 - Policies
# Demonstrates: Production safeguards

# Production database requires elevated permissions
deny_production_access if {
    input.arguments.database == "production"
    input.user.role not in ["admin", "dba"]
}

# Staging environment allows more permissive access
allow_staging if {
    input.arguments.database == "staging"
    input.user.role in ["developer", "data_engineer", "analyst"]
}

# ============================================================================
# Tutorial Policy Decision Logic
# ============================================================================

# Main allow decision combining all rules
allow if {
    allow_developer_basic
    not require_business_hours
    not require_mfa
    not require_corporate_network
    not deny_dangerous_query
    not exceeded_rate_limit
    not deny_production_access
}

allow if {
    allow_team_lead
    not require_business_hours
    not require_mfa
    not deny_dangerous_query
}

allow if {
    allow_team_ownership
    not require_business_hours
}

allow if {
    allow_data_engineering_db
}

allow if {
    allow_staging
}

# Deny takes precedence
deny if require_mfa
deny if mfa_expired
deny if require_corporate_network
deny if deny_dangerous_query
deny if exceeded_rate_limit
deny if deny_production_access

# Generate audit reason
audit_reason := "Allowed: Developer with low/medium sensitivity" if {
    allow_developer_basic
}

audit_reason := "Allowed: Team lead with elevated permissions" if {
    allow_team_lead
}

audit_reason := "Allowed: Team-based access" if {
    allow_team_ownership
}

audit_reason := "Allowed: Data engineering database access" if {
    allow_data_engineering_db
}

audit_reason := "Denied: Requires MFA verification" if {
    require_mfa
}

audit_reason := "Denied: MFA verification expired" if {
    mfa_expired
}

audit_reason := "Denied: Requires corporate network" if {
    require_corporate_network
}

audit_reason := "Denied: Dangerous SQL query detected" if {
    deny_dangerous_query
}

audit_reason := "Denied: Rate limit exceeded" if {
    exceeded_rate_limit
}

audit_reason := "Denied: Production database access restricted" if {
    deny_production_access
}

audit_reason := "Denied: Insufficient permissions" if {
    not allow
    not deny
}

# Policy result
result := {
    "allow": allow,
    "deny": deny,
    "audit_reason": audit_reason,
    "filtered_parameters": filtered_parameters_analyst
}
