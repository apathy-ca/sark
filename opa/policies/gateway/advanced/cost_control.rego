# Cost Control Policy
# Enforces budget limits, resource quotas, and cost attribution for tools and operations

package mcp.gateway.costcontrol

import future.keywords.if
import future.keywords.in

# ============================================================================
# CONFIGURATION
# ============================================================================

# Budget limits per user role (USD per month)
monthly_budgets := {
    "admin": 10000,
    "team_lead": 5000,
    "developer": 1000,
    "user": 100,
}

# Cost per tool operation (USD)
tool_costs := {
    "ai_model_inference": 0.50,
    "database_query": 0.01,
    "file_storage": 0.001,
    "api_call": 0.02,
    "compute_intensive": 1.00,
}

# Approval thresholds (operations exceeding this cost require approval)
approval_thresholds := {
    "admin": 100,
    "team_lead": 50,
    "developer": 10,
    "user": 5,
}

# ============================================================================
# COST CALCULATION
# ============================================================================

# Get tool operation cost
tool_operation_cost := cost if {
    tool_category := input.tool.cost_category
    cost := tool_costs[tool_category]
}

tool_operation_cost := tool_costs.api_call if {
    not input.tool.cost_category
}

# Calculate estimated cost with multipliers
estimated_cost := total_cost if {
    base_cost := tool_operation_cost

    # Scale by data volume
    data_volume_gb := input.context.estimated_data_volume_gb
    volume_multiplier := data_volume_gb > 0 ? data_volume_gb : 1

    # Scale by compute complexity
    complexity_multiplier := input.tool.complexity_multiplier
    complexity_mult := complexity_multiplier > 0 ? complexity_multiplier : 1

    # Scale by execution time
    estimated_duration_minutes := input.tool.estimated_duration_seconds / 60
    duration_mult := estimated_duration_minutes > 1 ? estimated_duration_minutes : 1

    total_cost := base_cost * volume_multiplier * complexity_mult * duration_mult
}

# ============================================================================
# BUDGET TRACKING
# ============================================================================

# Get user's monthly budget
user_monthly_budget := budget if {
    role := input.user.role
    budget := monthly_budgets[role]
}

user_monthly_budget := monthly_budgets.user if {
    not input.user.role
}

# Get current month's spending
current_month_spending := spending if {
    spending := input.context.budget_tracking.current_month_spent
}

current_month_spending := 0 if {
    not input.context.budget_tracking
}

# Calculate remaining budget
remaining_budget := budget if {
    budget := user_monthly_budget - current_month_spending
}

# Check if within budget
within_budget if {
    remaining_budget >= estimated_cost
}

# Budget utilization percentage
budget_utilization := percentage if {
    percentage := (current_month_spending / user_monthly_budget) * 100
}

# ============================================================================
# PROJECT/TEAM BUDGET ALLOCATION
# ============================================================================

# Get project budget allocation
project_budget := budget if {
    project_id := input.context.project_id
    budget := input.context.project_budgets[project_id]
}

project_budget := 0 if {
    not input.context.project_id
}

# Get project current spending
project_spending := spending if {
    project_id := input.context.project_id
    spending := input.context.project_spending[project_id]
}

project_spending := 0 if {
    not input.context.project_id
}

# Check if within project budget
within_project_budget if {
    not input.context.project_id  # No project association
}

within_project_budget if {
    input.context.project_id
    project_budget - project_spending >= estimated_cost
}

# ============================================================================
# RESOURCE QUOTAS
# ============================================================================

# Quota limits per user
quota_limits := {
    "api_calls_per_day": 10000,
    "storage_gb": 100,
    "compute_hours_per_month": 500,
    "ai_inferences_per_day": 1000,
}

# Check API call quota
within_api_quota if {
    input.tool.cost_category != "api_call"
}

within_api_quota if {
    input.tool.cost_category == "api_call"
    current_calls := input.context.quotas.api_calls_today
    current_calls < quota_limits.api_calls_per_day
}

# Check storage quota
within_storage_quota if {
    input.tool.cost_category != "file_storage"
}

within_storage_quota if {
    input.tool.cost_category == "file_storage"
    current_storage := input.context.quotas.storage_gb_used
    estimated_new_storage := input.context.estimated_data_volume_gb
    current_storage + estimated_new_storage <= quota_limits.storage_gb
}

# Check compute quota
within_compute_quota if {
    input.tool.cost_category != "compute_intensive"
}

within_compute_quota if {
    input.tool.cost_category == "compute_intensive"
    current_hours := input.context.quotas.compute_hours_this_month
    estimated_hours := input.tool.estimated_duration_seconds / 3600
    current_hours + estimated_hours <= quota_limits.compute_hours_per_month
}

# Check AI inference quota
within_ai_quota if {
    input.tool.cost_category != "ai_model_inference"
}

within_ai_quota if {
    input.tool.cost_category == "ai_model_inference"
    current_inferences := input.context.quotas.ai_inferences_today
    current_inferences < quota_limits.ai_inferences_per_day
}

# All quotas met
within_quotas if {
    within_api_quota
    within_storage_quota
    within_compute_quota
    within_ai_quota
}

# ============================================================================
# APPROVAL WORKFLOW
# ============================================================================

# Check if operation requires approval
requires_approval if {
    role := input.user.role
    threshold := approval_thresholds[role]
    estimated_cost >= threshold
}

# Check if approval has been granted
approval_granted if {
    not requires_approval
}

approval_granted if {
    requires_approval
    input.context.approval_status == "approved"
    # Approval must be recent (within last hour)
    approval_age := input.context.timestamp - input.context.approval_timestamp
    approval_age < 3600
}

# ============================================================================
# COST ATTRIBUTION & CHARGEBACKS
# ============================================================================

# Determine cost attribution
cost_attribution := attribution if {
    attribution := {
        "user_id": input.user.id,
        "project_id": input.context.project_id,
        "department": input.user.department,
        "cost_center": input.context.cost_center,
        "estimated_cost": estimated_cost,
    }
}

# Check if cost attribution is properly configured
cost_attribution_valid if {
    input.context.cost_center != ""
}

cost_attribution_valid if {
    input.user.role == "admin"  # Admins exempt from attribution
}

# ============================================================================
# EXPENSIVE OPERATION CONTROLS
# ============================================================================

# Expensive operations (>$10) have special requirements
is_expensive_operation if {
    estimated_cost >= 10
}

expensive_operation_requirements_met if {
    not is_expensive_operation
}

expensive_operation_requirements_met if {
    is_expensive_operation
    # Require business justification
    input.context.business_justification != ""
    # Require notification to team lead
    input.context.team_lead_notified == true
    # Require estimated vs actual cost tracking
    input.context.cost_tracking_enabled == true
}

# ============================================================================
# BUDGET ALERTS & THROTTLING
# ============================================================================

# Alert levels based on budget utilization
budget_alert_level := level if {
    utilization := budget_utilization
    level := "green" if utilization < 70
}

budget_alert_level := level if {
    utilization := budget_utilization
    level := "yellow" if {
        utilization >= 70
        utilization < 90
    }
}

budget_alert_level := level if {
    utilization := budget_utilization
    level := "red" if utilization >= 90
}

# Throttle expensive operations when budget is critical
should_throttle if {
    budget_alert_level == "red"
    estimated_cost > 1.0  # Throttle operations >$1 when budget critical
}

not_throttled if {
    not should_throttle
}

not_throttled if {
    should_throttle
    # Allow if explicitly approved by admin
    input.context.admin_override == true
}

# ============================================================================
# FINAL AUTHORIZATION DECISION
# ============================================================================

allow if {
    within_budget
    within_project_budget
    within_quotas
    approval_granted
    cost_attribution_valid
    expensive_operation_requirements_met
    not_throttled
}

default allow := false

# ============================================================================
# DECISION METADATA
# ============================================================================

failed_checks := checks if {
    checks := {check |
        not within_budget
        check := "budget_exceeded"
    } | {check |
        not within_project_budget
        check := "project_budget_exceeded"
    } | {check |
        not within_api_quota
        check := "api_quota_exceeded"
    } | {check |
        not within_storage_quota
        check := "storage_quota_exceeded"
    } | {check |
        not within_compute_quota
        check := "compute_quota_exceeded"
    } | {check |
        not within_ai_quota
        check := "ai_quota_exceeded"
    } | {check |
        not approval_granted
        requires_approval
        check := "approval_required"
    } | {check |
        not cost_attribution_valid
        check := "cost_attribution_missing"
    } | {check |
        not expensive_operation_requirements_met
        check := "expensive_operation_requirements_not_met"
    } | {check |
        should_throttle
        not input.context.admin_override
        check := "budget_throttling_active"
    }
}

reason := "Allowed: Cost control policies satisfied" if {
    allow
}

reason := sprintf("Denied: Cost control violations: %s", [concat(", ", failed_checks)]) if {
    not allow
}

# Warnings
warnings := warning_list if {
    warning_list := {warn |
        budget_utilization >= 70
        budget_utilization < 90
        warn := "budget_70_percent_warning"
    } | {warn |
        budget_utilization >= 90
        warn := "budget_90_percent_critical"
    } | {warn |
        estimated_cost >= 5
        warn := "high_cost_operation"
    }
}

result := {
    "allow": allow,
    "reason": reason,
    "cost_info": {
        "estimated_cost_usd": estimated_cost,
        "monthly_budget_usd": user_monthly_budget,
        "remaining_budget_usd": remaining_budget,
        "budget_utilization_percent": budget_utilization,
        "budget_alert_level": budget_alert_level,
    },
    "attribution": cost_attribution,
    "requires_approval": requires_approval,
    "failed_checks": failed_checks,
    "warnings": warnings,
}
