# Agent-to-Agent (A2A) Authorization Policy
# This policy implements authorization rules for agent-to-agent communication
# within the MCP Gateway ecosystem with trust levels and capability controls.

package mcp.gateway.a2a

import future.keywords.if
import future.keywords.in

# Default deny - fail-safe security
default allow := false

# ============================================================================
# TRUST LEVEL RULES
# ============================================================================

# Trusted agents can communicate with each other
allow if {
    input.action == "a2a:communicate"
    input.source_agent.trust_level == "trusted"
    input.target_agent.trust_level == "trusted"
    same_environment(input.source_agent, input.target_agent)
}

# Service agents can communicate with worker agents (same environment)
allow if {
    input.action == "a2a:communicate"
    input.source_agent.type == "service"
    input.target_agent.type == "worker"
    input.source_agent.trust_level in ["trusted", "verified"]
    same_environment(input.source_agent, input.target_agent)
}

# Verified agents can communicate within same organization AND environment
allow if {
    input.action == "a2a:communicate"
    input.source_agent.trust_level == "verified"
    input.target_agent.trust_level == "verified"
    same_organization(input.source_agent, input.target_agent)
    same_environment(input.source_agent, input.target_agent)
}

# ============================================================================
# CAPABILITY ENFORCEMENT
# ============================================================================

# Execute capability - allows agent to execute tasks
allow if {
    input.action == "a2a:execute"
    "execute" in input.source_agent.capabilities
    input.target_agent.accepts_execution == true
    can_execute_on_target(input.source_agent, input.target_agent)
}

# Query capability - allows agent to query information
allow if {
    input.action == "a2a:query"
    "query" in input.source_agent.capabilities
    input.target_agent.accepts_queries == true
}

# Delegate capability - allows agent to delegate tasks
allow if {
    input.action == "a2a:delegate"
    "delegate" in input.source_agent.capabilities
    input.target_agent.accepts_delegation == true
    input.source_agent.trust_level in ["trusted", "verified"]
}

# ============================================================================
# CROSS-ENVIRONMENT RESTRICTIONS
# ============================================================================

# Block cross-environment communication unless explicitly allowed
deny if {
    input.action in ["a2a:communicate", "a2a:execute", "a2a:delegate"]
    not same_environment(input.source_agent, input.target_agent)
    not is_cross_env_allowed(input.source_agent, input.target_agent)
}

# Block communication from untrusted agents
deny if {
    input.source_agent.trust_level == "untrusted"
}

# Block communication to production from non-production agents
deny if {
    input.target_agent.environment == "production"
    input.source_agent.environment != "production"
    input.source_agent.trust_level != "trusted"
}

# ============================================================================
# AGENT TYPE RULES
# ============================================================================

# Service agents can invoke worker agents
allow if {
    input.action == "a2a:invoke"
    input.source_agent.type == "service"
    input.target_agent.type == "worker"
    rate_limit_ok(input.source_agent, input.context)
}

# Orchestrator agents have elevated privileges
allow if {
    input.action in ["a2a:communicate", "a2a:execute", "a2a:query"]
    input.source_agent.type == "orchestrator"
    input.source_agent.trust_level == "trusted"
    rate_limit_ok(input.source_agent, input.context)
}

# Monitor agents can query but not execute
allow if {
    input.action == "a2a:query"
    input.source_agent.type == "monitor"
    input.source_agent.trust_level in ["trusted", "verified"]
}

# ============================================================================
# RATE LIMITING CHECKS
# ============================================================================

# Check if agent is within rate limits
rate_limit_ok(agent, context) if {
    # If no rate limit data in context, assume OK
    not context.rate_limit
}

rate_limit_ok(agent, context) if {
    context.rate_limit
    context.rate_limit.current_count < agent.rate_limit_per_minute
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Check if agents are in the same environment
same_environment(source, target) if {
    source.environment == target.environment
}

# Check if agents are in the same organization
same_organization(source, target) if {
    source.organization_id == target.organization_id
}

# Check if cross-environment communication is explicitly allowed
is_cross_env_allowed(source, target) if {
    # Allow staging -> production for trusted service agents
    source.environment == "staging"
    target.environment == "production"
    source.type == "service"
    source.trust_level == "trusted"
}

is_cross_env_allowed(source, target) if {
    # Allow development -> staging for verified agents
    source.environment == "development"
    target.environment == "staging"
    source.trust_level in ["trusted", "verified"]
}

# Check if source agent can execute on target
can_execute_on_target(source, target) if {
    # Service agents can execute on workers
    source.type == "service"
    target.type == "worker"
}

can_execute_on_target(source, target) if {
    # Orchestrators can execute on most agents
    source.type == "orchestrator"
    target.type in ["worker", "service"]
}

can_execute_on_target(source, target) if {
    # Trusted agents can execute on same-type agents
    source.trust_level == "trusted"
    source.type == target.type
}

# ============================================================================
# AUDIT REASON GENERATION
# ============================================================================

# Default audit reason for allowed requests
default audit_reason := "Authorization evaluation completed"

# Denied reasons (checked first)
audit_reason := sprintf("Denied: %s from agent %s to %s (untrusted source)", [
    input.action,
    input.source_agent.id,
    input.target_agent.id
]) if {
    not allow
    input.source_agent.trust_level == "untrusted"
} else := sprintf("Denied: %s from agent %s to %s (cross-environment blocked)", [
    input.action,
    input.source_agent.id,
    input.target_agent.id
]) if {
    not allow
    not same_environment(input.source_agent, input.target_agent)
} else := sprintf("Denied: %s from agent %s to %s (insufficient permissions)", [
    input.action,
    input.source_agent.id,
    input.target_agent.id
]) if {
    not allow
} else := sprintf("Allowed: %s from agent %s (orchestrator) to %s", [
    input.action,
    input.source_agent.id,
    input.target_agent.id
]) if {
    allow
    input.source_agent.type == "orchestrator"
} else := sprintf("Allowed: %s from agent %s (%s) to %s (%s) (service->worker)", [
    input.action,
    input.source_agent.id,
    input.source_agent.type,
    input.target_agent.id,
    input.target_agent.type
]) if {
    allow
    input.source_agent.type == "service"
    input.target_agent.type == "worker"
} else := sprintf("Allowed: %s from agent %s to %s (trusted agents, same environment)", [
    input.action,
    input.source_agent.id,
    input.target_agent.id
]) if {
    allow
    input.source_agent.trust_level == "trusted"
    input.target_agent.trust_level == "trusted"
    same_environment(input.source_agent, input.target_agent)
} else := sprintf("Allowed: %s from agent %s to %s (capability granted)", [
    input.action,
    input.source_agent.id,
    input.target_agent.id
]) if {
    allow
}

# ============================================================================
# POLICY RESULT WITH METADATA
# ============================================================================

result := {
    "allow": allow,
    "deny": deny,
    "audit_reason": audit_reason,
    "restrictions": get_restrictions(input.source_agent, input.target_agent),
}

# Get any restrictions that should be applied to the communication
get_restrictions(source, target) := restrictions if {
    allow
    restrictions := {
        "rate_limited": is_rate_limited(source),
        "monitoring_required": requires_monitoring(source, target),
        "encryption_required": true,
    }
}

get_restrictions(source, target) := {} if {
    not allow
}

# Check if agent should be rate limited
is_rate_limited(agent) if {
    agent.trust_level == "verified"
}

is_rate_limited(agent) if {
    agent.type in ["worker", "monitor"]
}

# Check if communication requires monitoring
requires_monitoring(source, target) if {
    source.environment != target.environment
}

requires_monitoring(source, target) if {
    source.trust_level == "verified"
    target.trust_level == "verified"
}

requires_monitoring(source, target) if {
    target.environment == "production"
}
