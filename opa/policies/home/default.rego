# SARK Home Default Policy
# Default allow-all policy with observation mode for new YORI installations
#
# Use case: Out-of-the-box policy that logs all requests without blocking
# Perfect for initial setup and understanding household LLM usage patterns

package sark.home.default

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Allow (Observation Mode)
# =============================================================================

# Default policy allows all requests - designed for observation mode
default allow := true
default reason := ""

# =============================================================================
# Mode Configuration
# =============================================================================

# Supported modes:
# - observe: Log all requests, never block (default for new installations)
# - advisory: Log and alert on policy violations, but don't block
# - enforce: Actually block requests that violate policies

mode := input.rules.mode if {
    input.rules.mode in ["observe", "advisory", "enforce"]
}

mode := "observe" if {
    not input.rules.mode
}

# =============================================================================
# Observation Logging
# =============================================================================

# Always generate observation data regardless of mode
observation := {
    "timestamp": input.context.timestamp,
    "device_ip": input.user.device_ip,
    "device_name": input.user.device_name,
    "user_group": input.user.user_group,
    "endpoint": input.request.endpoint,
    "method": input.request.method,
    "path": input.request.path,
    "tokens_estimated": input.request.tokens_estimated,
    "hour": input.context.hour,
    "day_of_week": input.context.day_of_week
}

# =============================================================================
# Policy Suggestions (for observation mode)
# =============================================================================

# Suggest bedtime policy if request is late night
suggested_policies contains "bedtime" if {
    hour := input.context.hour
    hour >= 21
}

suggested_policies contains "bedtime" if {
    hour := input.context.hour
    hour < 7
}

# Suggest cost_limit if high token usage
suggested_policies contains "cost_limit" if {
    input.context.tokens_today > 5000
}

suggested_policies contains "cost_limit" if {
    input.context.cost_today_usd > 1.00
}

# Suggest parental if device appears to be for a minor
suggested_policies contains "parental" if {
    input.user.user_group in ["child", "children", "minor", "teen"]
}

# Suggest privacy if common PII patterns detected
suggested_policies contains "privacy" if {
    # Basic email check
    regex.match(`@`, input.request.prompt_preview)
}

# =============================================================================
# Usage Analytics
# =============================================================================

# Track usage patterns for recommendations
usage_analytics := {
    "peak_hours": is_peak_hour,
    "high_usage_device": is_high_usage_device,
    "frequent_endpoint": input.request.endpoint
}

is_peak_hour if {
    hour := input.context.hour
    hour >= 16
    hour <= 22
}

is_peak_hour := false if {
    hour := input.context.hour
    hour < 16
}

is_peak_hour := false if {
    hour := input.context.hour
    hour > 22
}

is_high_usage_device if {
    input.context.device_requests_today > 50
}

is_high_usage_device := false if {
    not input.context.device_requests_today > 50
}

# =============================================================================
# Soft Limits (Advisory Only)
# =============================================================================

# These limits don't block in default mode, but generate warnings
soft_limit_warnings contains "High daily usage - consider setting a cost limit" if {
    input.context.cost_today_usd > 2.00
}

soft_limit_warnings contains "Late night usage detected - consider bedtime policy" if {
    input.context.hour >= 23
}

soft_limit_warnings contains "Late night usage detected - consider bedtime policy" if {
    input.context.hour < 5
}

soft_limit_warnings contains "Many requests from this device - consider per-device limits" if {
    input.context.device_requests_today > 100
}

# =============================================================================
# Reason Messages
# =============================================================================

# In observe mode, we always allow but may note observations
reason := "Allowed (observe mode) - monitoring only" if {
    mode == "observe"
}

reason := sprintf("Allowed (advisory mode) - warnings: %s", [concat(", ", soft_limit_warnings)]) if {
    mode == "advisory"
    count(soft_limit_warnings) > 0
}

reason := "Allowed (advisory mode) - no warnings" if {
    mode == "advisory"
    count(soft_limit_warnings) == 0
}

reason := "Allowed (enforce mode) - no policy violations" if {
    mode == "enforce"
}

# =============================================================================
# Policy Decision Output
# =============================================================================

decision := {
    "allow": allow,
    "reason": reason,
    "policy": "default",
    "mode": mode,
    "severity": "info",
    "metadata": {
        "observation": observation,
        "suggested_policies": suggested_policies,
        "soft_limit_warnings": soft_limit_warnings,
        "usage_analytics": usage_analytics
    }
}

# =============================================================================
# First-Run Helper
# =============================================================================

# Provide helpful messages for new installations
first_run_tips := [
    "Welcome to YORI! This default policy allows all requests while logging usage.",
    "After a few days, check your logs to understand your household's LLM usage patterns.",
    "Use 'suggested_policies' in the decision output to see which policies might benefit your household.",
    "Ready to enforce? Change mode from 'observe' to 'advisory' (warnings) or 'enforce' (blocking)."
]

# Include tips in first request of the day
include_tips if {
    input.context.device_requests_today == 0
}

include_tips if {
    input.context.first_request == true
}

include_tips := false if {
    input.context.device_requests_today > 0
    not input.context.first_request == true
}

# =============================================================================
# Compatibility
# =============================================================================

# Ensure compatibility with policy aggregation
cache_ttl := 60

# Export standard fields expected by SARK
severity := "info"
