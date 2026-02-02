# SARK Home Cost Limit Policy
# Controls LLM API usage based on daily/monthly cost and token limits
#
# Use case: Prevent unexpected API bills by limiting household usage

package sark.home.cost_limit

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Allow
# =============================================================================

default allow := true
default reason := ""

# =============================================================================
# Deny Rules - Cost Limits
# =============================================================================

# Deny if daily cost limit exceeded
allow := false if {
    daily_cost_exceeded
}

# Deny if monthly cost limit exceeded
allow := false if {
    monthly_cost_exceeded
}

# Deny if single request would exceed remaining budget
allow := false if {
    request_exceeds_budget
}

# =============================================================================
# Deny Rules - Token Limits
# =============================================================================

# Deny if daily token limit exceeded
allow := false if {
    daily_tokens_exceeded
}

# Deny if monthly token limit exceeded
allow := false if {
    monthly_tokens_exceeded
}

# =============================================================================
# Cost Limit Checks
# =============================================================================

# Check if daily cost limit is exceeded
daily_cost_exceeded if {
    input.rules.daily_cost_limit_usd
    input.context.cost_today_usd >= input.rules.daily_cost_limit_usd
}

# Check if monthly cost limit is exceeded
monthly_cost_exceeded if {
    input.rules.monthly_cost_limit_usd
    input.context.cost_month_usd >= input.rules.monthly_cost_limit_usd
}

# Check if this request would exceed remaining daily budget
request_exceeds_budget if {
    input.rules.daily_cost_limit_usd
    input.request.estimated_cost_usd
    remaining := input.rules.daily_cost_limit_usd - input.context.cost_today_usd
    input.request.estimated_cost_usd > remaining
}

# =============================================================================
# Token Limit Checks
# =============================================================================

# Check if daily token limit is exceeded
daily_tokens_exceeded if {
    input.rules.daily_token_limit
    input.context.tokens_today >= input.rules.daily_token_limit
}

# Check if monthly token limit is exceeded
monthly_tokens_exceeded if {
    input.rules.monthly_token_limit
    input.context.tokens_month >= input.rules.monthly_token_limit
}

# =============================================================================
# Per-User Limits (Optional)
# =============================================================================

# Check user-specific daily limit
user_daily_limit_exceeded if {
    user_limit := data.home.user_daily_limits[input.user.device_name]
    input.context.user_cost_today_usd >= user_limit
}

allow := false if {
    user_daily_limit_exceeded
}

# =============================================================================
# Warning Thresholds
# =============================================================================

# Calculate usage percentages for warnings
daily_cost_percentage := pct if {
    input.rules.daily_cost_limit_usd > 0
    pct := (input.context.cost_today_usd / input.rules.daily_cost_limit_usd) * 100
}

daily_cost_percentage := 0 if {
    not input.rules.daily_cost_limit_usd > 0
}

monthly_cost_percentage := pct if {
    input.rules.monthly_cost_limit_usd > 0
    pct := (input.context.cost_month_usd / input.rules.monthly_cost_limit_usd) * 100
}

monthly_cost_percentage := 0 if {
    not input.rules.monthly_cost_limit_usd > 0
}

# Warning level based on usage
warning_level := "critical" if {
    daily_cost_percentage >= 90
}

warning_level := "high" if {
    daily_cost_percentage >= 75
    daily_cost_percentage < 90
}

warning_level := "medium" if {
    daily_cost_percentage >= 50
    daily_cost_percentage < 75
}

warning_level := "low" if {
    daily_cost_percentage < 50
}

# =============================================================================
# Reason Messages
# =============================================================================

reason := sprintf("Daily cost limit exceeded: $%.2f / $%.2f", [
    input.context.cost_today_usd,
    input.rules.daily_cost_limit_usd
]) if {
    daily_cost_exceeded
}

reason := sprintf("Monthly cost limit exceeded: $%.2f / $%.2f", [
    input.context.cost_month_usd,
    input.rules.monthly_cost_limit_usd
]) if {
    monthly_cost_exceeded
    not daily_cost_exceeded
}

reason := sprintf("Request would exceed remaining daily budget ($%.2f remaining)", [
    input.rules.daily_cost_limit_usd - input.context.cost_today_usd
]) if {
    request_exceeds_budget
    not daily_cost_exceeded
    not monthly_cost_exceeded
}

reason := sprintf("Daily token limit exceeded: %d / %d tokens", [
    input.context.tokens_today,
    input.rules.daily_token_limit
]) if {
    daily_tokens_exceeded
    not daily_cost_exceeded
    not monthly_cost_exceeded
    not request_exceeds_budget
}

reason := sprintf("Monthly token limit exceeded: %d / %d tokens", [
    input.context.tokens_month,
    input.rules.monthly_token_limit
]) if {
    monthly_tokens_exceeded
    not daily_tokens_exceeded
    not daily_cost_exceeded
    not monthly_cost_exceeded
    not request_exceeds_budget
}

reason := sprintf("User '%s' daily limit exceeded", [input.user.device_name]) if {
    user_daily_limit_exceeded
    not daily_cost_exceeded
    not monthly_cost_exceeded
    not daily_tokens_exceeded
    not monthly_tokens_exceeded
}

# =============================================================================
# Policy Decision Output
# =============================================================================

decision := {
    "allow": allow,
    "reason": reason,
    "policy": "cost_limit",
    "severity": severity,
    "metadata": {
        "cost_today_usd": input.context.cost_today_usd,
        "cost_month_usd": input.context.cost_month_usd,
        "tokens_today": input.context.tokens_today,
        "daily_cost_percentage": daily_cost_percentage,
        "monthly_cost_percentage": monthly_cost_percentage,
        "warning_level": warning_level
    }
}

severity := "info" if {
    allow
    warning_level == "low"
}

severity := "warning" if {
    allow
    warning_level in ["medium", "high"]
}

severity := "high" if {
    not allow
}

severity := "critical" if {
    warning_level == "critical"
}

# =============================================================================
# Budget Recommendations
# =============================================================================

# Suggest budget-friendly alternatives when nearing limits
budget_recommendation := "Consider using a smaller model to reduce costs" if {
    warning_level in ["high", "critical"]
    input.request.model in ["gpt-4", "gpt-4-turbo", "claude-3-opus"]
}

budget_recommendation := "Usage is within normal limits" if {
    warning_level == "low"
}

budget_recommendation := "Monitor usage - approaching daily limit" if {
    warning_level == "medium"
}
