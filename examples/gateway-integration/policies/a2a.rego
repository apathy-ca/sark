# SARK Agent-to-Agent (A2A) Authorization Policy
# This policy controls which agents can communicate with each other

package mcp.gateway.a2a

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Deny
# =============================================================================

default allow := false

# =============================================================================
# Trust Level Definitions
# =============================================================================

# Trust level hierarchy: critical > high > medium > low
trust_level_value := 4 if { input.source_agent.trust_level == "critical" }
trust_level_value := 3 if { input.source_agent.trust_level == "high" }
trust_level_value := 2 if { input.source_agent.trust_level == "medium" }
trust_level_value := 1 if { input.source_agent.trust_level == "low" }
trust_level_value := 0  # Default to lowest if not specified

target_trust_level_value := 4 if { input.target_agent.trust_level == "critical" }
target_trust_level_value := 3 if { input.target_agent.trust_level == "high" }
target_trust_level_value := 2 if { input.target_agent.trust_level == "medium" }
target_trust_level_value := 1 if { input.target_agent.trust_level == "low" }
target_trust_level_value := 0

# =============================================================================
# Trust Level Based Authorization
# =============================================================================

# Critical trust agents can invoke any other agent
allow if {
    input.action == "a2a:invoke"
    input.source_agent.trust_level == "critical"
}

# High trust agents can invoke high, medium, and low trust agents
allow if {
    input.action == "a2a:invoke"
    input.source_agent.trust_level == "high"
    input.target_agent.trust_level in ["high", "medium", "low"]
}

# Medium trust agents can invoke medium and low trust agents
allow if {
    input.action == "a2a:invoke"
    input.source_agent.trust_level == "medium"
    input.target_agent.trust_level in ["medium", "low"]
}

# Low trust agents can only invoke other low trust agents
allow if {
    input.action == "a2a:invoke"
    input.source_agent.trust_level == "low"
    input.target_agent.trust_level == "low"
}

# =============================================================================
# Capability-Based Authorization
# =============================================================================

# Allow research agents to query database agents
allow if {
    input.action == "a2a:invoke"
    "research" in input.source_agent.capabilities
    "query" in input.target_agent.capabilities
    input.tool_name in ["query_database", "search_database"]
}

# Allow orchestrator agents to invoke any agent
allow if {
    input.action == "a2a:invoke"
    "orchestrator" in input.source_agent.capabilities
}

# Allow data processing agents to call analytics agents
allow if {
    input.action == "a2a:invoke"
    "data_processing" in input.source_agent.capabilities
    "analytics" in input.target_agent.capabilities
}

# =============================================================================
# Workflow Context Authorization
# =============================================================================

# Allow agents within the same workflow to communicate
allow if {
    input.action == "a2a:invoke"
    input.context.workflow_id != ""
    input.source_agent.workflow_id == input.context.workflow_id
    input.target_agent.workflow_id == input.context.workflow_id
}

# Allow agents owned by the same user to communicate
allow if {
    input.action == "a2a:invoke"
    input.context.user_id != ""
    input.source_agent.owner_id == input.context.user_id
    input.target_agent.owner_id == input.context.user_id
}

# =============================================================================
# Delegation Authorization
# =============================================================================

# Allow delegation if source agent has higher trust level
allow if {
    input.action == "a2a:delegate"
    trust_level_value > target_trust_level_value
}

# Allow delegation within the same trust level if explicitly permitted
allow if {
    input.action == "a2a:delegate"
    trust_level_value == target_trust_level_value
    "delegate" in input.source_agent.capabilities
}

# =============================================================================
# Explicit Denies
# =============================================================================

# Deny low trust agents from calling high/critical trust agents
deny contains "Low trust agents cannot invoke high/critical trust agents" if {
    input.source_agent.trust_level == "low"
    input.target_agent.trust_level in ["high", "critical"]
}

# Deny delegation if it would exceed max depth
deny contains "Max delegation depth exceeded" if {
    input.action == "a2a:delegate"
    input.context.delegation_depth >= max_delegation_depth
}

# Maximum delegation depth
max_delegation_depth := 3

# Deny agents without required capabilities
deny contains "Source agent lacks required capability for this action" if {
    input.action == "a2a:invoke"
    required_capability := tool_capability_map[input.tool_name]
    not required_capability in input.source_agent.capabilities
}

# Map tools to required capabilities
tool_capability_map := {
    "query_database": "database_access",
    "execute_code": "code_execution",
    "send_email": "email_sending",
    "make_http_request": "http_client"
}

# =============================================================================
# Time-Based Restrictions
# =============================================================================

# Deny A2A communication outside business hours for low trust agents
deny contains "Low trust agents restricted to business hours (9am-5pm UTC)" if {
    input.source_agent.trust_level == "low"
    current_hour := time.clock(time.now_ns())[0]
    not current_hour >= 9
    not current_hour < 17
}

# =============================================================================
# Rate Limiting
# =============================================================================

# Deny if agent has exceeded rate limit
deny contains "Agent has exceeded A2A rate limit" if {
    input.source_agent.request_count_last_hour > rate_limit_per_hour
}

# Rate limit per hour based on trust level
rate_limit_per_hour := 1000 if { input.source_agent.trust_level == "critical" }
rate_limit_per_hour := 500 if { input.source_agent.trust_level == "high" }
rate_limit_per_hour := 100 if { input.source_agent.trust_level == "medium" }
rate_limit_per_hour := 50 if { input.source_agent.trust_level == "low" }
rate_limit_per_hour := 10  # Default

# =============================================================================
# Audit Decisions
# =============================================================================

reason := msg if {
    allow
    input.source_agent.trust_level == "critical"
    msg := sprintf("Allowed: critical trust agent %s can invoke any agent", [input.source_agent.name])
}

reason := msg if {
    allow
    trust_level_value >= target_trust_level_value
    msg := sprintf("Allowed: %s trust agent %s can invoke %s trust agent %s",
        [input.source_agent.trust_level, input.source_agent.name,
         input.target_agent.trust_level, input.target_agent.name])
}

reason := msg if {
    not allow
    count(deny) > 0
    msg := concat("; ", deny)
}

reason := "Denied: insufficient trust level or missing capabilities" if {
    not allow
    count(deny) == 0
}

# =============================================================================
# Cache TTL
# =============================================================================

# Cache positive decisions for 5 minutes (A2A relationships are stable)
cache_ttl := 300 if {
    allow
}

# Do not cache negative decisions
cache_ttl := 0 if {
    not allow
}

# =============================================================================
# Delegation Depth
# =============================================================================

# Maximum delegation depth for this authorization
max_delegation_depth_result := 3 if {
    allow
    input.source_agent.trust_level in ["critical", "high"]
}

max_delegation_depth_result := 2 if {
    allow
    input.source_agent.trust_level == "medium"
}

max_delegation_depth_result := 1 if {
    allow
    input.source_agent.trust_level == "low"
}

max_delegation_depth_result := 0 if {
    not allow
}
