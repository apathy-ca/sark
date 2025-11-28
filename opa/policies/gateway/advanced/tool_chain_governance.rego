# Tool Chaining Governance Policy
# Controls and validates tool chaining behavior to prevent abuse and resource exhaustion

package mcp.gateway.toolchain

import future.keywords.if
import future.keywords.in

# ============================================================================
# CONFIGURATION
# ============================================================================

# Maximum chain depth allowed
max_chain_depth := 10

# Maximum execution time for entire chain (seconds)
max_chain_duration := 300  # 5 minutes

# Maximum resource consumption per chain
max_chain_resources := {
    "memory_mb": 1024,
    "cpu_seconds": 60,
    "disk_mb": 500,
    "network_mb": 100,
}

# Forbidden tool combinations (tools that should never be chained)
forbidden_combinations := [
    {"source": "database_delete", "target": "file_delete"},
    {"source": "export_data", "target": "external_api"},
    {"source": "credential_access", "target": "*"},  # Credential tools can't chain to anything
]

# Required audit points (tools that must log before proceeding)
audit_required_tools := {"database_modify", "file_delete", "user_modify", "permission_change"}

# ============================================================================
# CHAIN DEPTH VALIDATION
# ============================================================================

# Current chain depth
chain_depth := depth if {
    depth := input.context.chain.depth
}

chain_depth := 0 if {
    not input.context.chain
}

# Check if within depth limit
within_depth_limit if {
    chain_depth < max_chain_depth
}

# ============================================================================
# CIRCULAR DEPENDENCY DETECTION
# ============================================================================

# Check if current tool is already in the chain (circular reference)
has_circular_dependency if {
    current_tool := input.tool.name
    some tool in input.context.chain.tools
    tool == current_tool
}

# No circular dependency
no_circular_dependency if {
    not has_circular_dependency
}

# ============================================================================
# FORBIDDEN COMBINATION CHECKS
# ============================================================================

# Get previous tool in chain
previous_tool := tool if {
    chain_tools := input.context.chain.tools
    count(chain_tools) > 0
    tool := chain_tools[count(chain_tools) - 1]
}

# Check if current combination is forbidden
is_forbidden_combination if {
    prev := previous_tool
    current := input.tool.name

    some combo in forbidden_combinations
    combo.source == prev
    (combo.target == current) or (combo.target == "*")
}

# Combination is allowed
combination_allowed if {
    not is_forbidden_combination
}

combination_allowed if {
    # First tool in chain (no previous tool)
    not previous_tool
}

# ============================================================================
# RESOURCE ACCUMULATION TRACKING
# ============================================================================

# Calculate total resources consumed by chain so far
accumulated_resources := resources if {
    chain_data := input.context.chain
    resources := {
        "memory_mb": chain_data.consumed_resources.memory_mb,
        "cpu_seconds": chain_data.consumed_resources.cpu_seconds,
        "disk_mb": chain_data.consumed_resources.disk_mb,
        "network_mb": chain_data.consumed_resources.network_mb,
    }
}

accumulated_resources := {
    "memory_mb": 0,
    "cpu_seconds": 0,
    "disk_mb": 0,
    "network_mb": 0,
} if {
    not input.context.chain
}

# Estimated resources for current tool
estimated_tool_resources := resources if {
    tool := input.tool
    resources := {
        "memory_mb": tool.estimated_memory_mb,
        "cpu_seconds": tool.estimated_cpu_seconds,
        "disk_mb": tool.estimated_disk_mb,
        "network_mb": tool.estimated_network_mb,
    }
}

estimated_tool_resources := {
    "memory_mb": 10,
    "cpu_seconds": 1,
    "disk_mb": 1,
    "network_mb": 1,
} if {
    not input.tool.estimated_memory_mb
}

# Check if adding current tool would exceed resource limits
within_memory_limit if {
    accumulated_resources.memory_mb + estimated_tool_resources.memory_mb <= max_chain_resources.memory_mb
}

within_cpu_limit if {
    accumulated_resources.cpu_seconds + estimated_tool_resources.cpu_seconds <= max_chain_resources.cpu_seconds
}

within_disk_limit if {
    accumulated_resources.disk_mb + estimated_tool_resources.disk_mb <= max_chain_resources.disk_mb
}

within_network_limit if {
    accumulated_resources.network_mb + estimated_tool_resources.network_mb <= max_chain_resources.network_mb
}

within_resource_limits if {
    within_memory_limit
    within_cpu_limit
    within_disk_limit
    within_network_limit
}

# ============================================================================
# CHAIN DURATION VALIDATION
# ============================================================================

# Calculate total chain execution time
chain_duration := duration if {
    start_time := input.context.chain.start_time
    current_time := input.context.timestamp
    duration := current_time - start_time
}

chain_duration := 0 if {
    not input.context.chain
}

# Check if within duration limit
within_duration_limit if {
    chain_duration + input.tool.estimated_duration_seconds <= max_chain_duration
}

# ============================================================================
# AUDIT TRAIL VALIDATION
# ============================================================================

# Check if previous tool that required audit was properly audited
previous_audit_satisfied if {
    not previous_tool
}

previous_audit_satisfied if {
    prev := previous_tool
    not (prev in audit_required_tools)
}

previous_audit_satisfied if {
    prev := previous_tool
    prev in audit_required_tools
    input.context.chain.last_audit_timestamp > 0
}

# Check if current tool requires audit
current_tool_needs_audit if {
    input.tool.name in audit_required_tools
}

# ============================================================================
# TOOL CHAINING PATTERNS
# ============================================================================

# Detect potentially dangerous patterns

# Data exfiltration pattern (read → export → external)
is_data_exfiltration_pattern if {
    chain_tools := input.context.chain.tools
    some i
    chain_tools[i] == "database_read"
    chain_tools[i + 1] == "export_data"
    input.tool.name == "external_api"
}

# Privilege escalation pattern
is_privilege_escalation_pattern if {
    chain_tools := input.context.chain.tools
    some i
    chain_tools[i] in {"user_create", "permission_change"}
    input.tool.name in {"credential_access", "admin_shell"}
}

# Destructive cascade pattern
is_destructive_cascade if {
    delete_count := count([tool | tool := input.context.chain.tools[_]; contains(tool, "delete")])
    delete_count >= 2
    contains(input.tool.name, "delete")
}

# No dangerous patterns detected
no_dangerous_patterns if {
    not is_data_exfiltration_pattern
    not is_privilege_escalation_pattern
    not is_destructive_cascade
}

# ============================================================================
# ROLE-BASED CHAIN RESTRICTIONS
# ============================================================================

# Developers can only create simple chains
developer_chain_allowed if {
    input.user.role != "developer"
}

developer_chain_allowed if {
    input.user.role == "developer"
    chain_depth < 5  # Developers limited to 5 tools
    no_dangerous_patterns
}

# ============================================================================
# FINAL AUTHORIZATION DECISION
# ============================================================================

# Allow if all checks pass
allow if {
    within_depth_limit
    no_circular_dependency
    combination_allowed
    within_resource_limits
    within_duration_limit
    previous_audit_satisfied
    no_dangerous_patterns
    developer_chain_allowed
}

default allow := false

# ============================================================================
# DECISION METADATA
# ============================================================================

# Identify which checks failed
failed_checks := checks if {
    checks := {check |
        not within_depth_limit
        check := "chain_depth_exceeded"
    } | {check |
        has_circular_dependency
        check := "circular_dependency"
    } | {check |
        is_forbidden_combination
        check := "forbidden_combination"
    } | {check |
        not within_resource_limits
        check := "resource_limit_exceeded"
    } | {check |
        not within_duration_limit
        check := "duration_limit_exceeded"
    } | {check |
        not previous_audit_satisfied
        check := "missing_audit_trail"
    } | {check |
        is_data_exfiltration_pattern
        check := "data_exfiltration_pattern"
    } | {check |
        is_privilege_escalation_pattern
        check := "privilege_escalation_pattern"
    } | {check |
        is_destructive_cascade
        check := "destructive_cascade"
    }
}

# Reason for decision
reason := "Allowed: Tool chain governance checks passed" if {
    allow
}

reason := sprintf("Denied: Tool chain governance violations: %s", [concat(", ", failed_checks)]) if {
    not allow
    count(failed_checks) > 0
}

# Warnings (allow but flag for review)
warnings := warning_list if {
    warning_list := {warn |
        chain_depth > 7
        warn := "approaching_max_depth"
    } | {warn |
        accumulated_resources.memory_mb > 800
        warn := "high_memory_usage"
    } | {warn |
        chain_duration > 240  # 4 minutes
        warn := "long_running_chain"
    }
}

# ============================================================================
# RESULT
# ============================================================================

result := {
    "allow": allow,
    "reason": reason,
    "chain_info": {
        "depth": chain_depth,
        "max_depth": max_chain_depth,
        "duration_seconds": chain_duration,
        "max_duration": max_chain_duration,
        "resources": accumulated_resources,
        "resource_limits": max_chain_resources,
    },
    "warnings": warnings,
    "failed_checks": failed_checks,
    "audit_required": current_tool_needs_audit,
}
