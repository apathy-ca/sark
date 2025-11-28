# Dynamic Rate Limiting Policy
# Implements adaptive rate limiting based on server load, user behavior, and tool sensitivity

package mcp.gateway.ratelimit

import future.keywords.if
import future.keywords.in

# ============================================================================
# CONFIGURATION & DEFAULTS
# ============================================================================

# Default rate limits (requests per minute)
default_limits := {
    "user": {
        "admin": 1000,
        "developer": 500,
        "user": 100,
    },
    "tool": {
        "critical": 10,
        "high": 50,
        "medium": 200,
        "low": 500,
    },
    "server_load": {
        "critical": 0.5,  # Reduce to 50% of normal when load is critical
        "high": 0.75,     # Reduce to 75% when load is high
        "normal": 1.0,    # No reduction
        "low": 1.5,       # Allow 150% when load is low
    },
}

# Burst allowance (multiplier for short bursts)
burst_multiplier := 2.0

# Time windows for rate limiting (seconds)
time_windows := {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "month": 2592000,
}

# ============================================================================
# TOKEN BUCKET ALGORITHM
# ============================================================================

# Calculate available tokens in bucket
available_tokens(bucket_state, current_time, refill_rate, max_tokens) := tokens if {
    elapsed_seconds := current_time - bucket_state.last_refill
    tokens_added := elapsed_seconds * refill_rate
    tokens_before_refill := bucket_state.tokens

    # Cap at max_tokens
    tokens := min(max_tokens, tokens_before_refill + tokens_added)
}

# Check if request can be allowed based on token bucket
token_bucket_allow(bucket_state, current_time, refill_rate, max_tokens, cost) if {
    tokens := available_tokens(bucket_state, current_time, refill_rate, max_tokens)
    tokens >= cost
}

# Calculate new bucket state after consuming tokens
consume_tokens(bucket_state, current_time, refill_rate, max_tokens, cost) := new_state if {
    tokens := available_tokens(bucket_state, current_time, refill_rate, max_tokens)
    new_state := {
        "tokens": tokens - cost,
        "last_refill": current_time,
    }
}

# ============================================================================
# RATE LIMIT CALCULATIONS
# ============================================================================

# Calculate effective rate limit based on server load
effective_rate_limit(base_limit, server_load_level) := adjusted_limit if {
    multiplier := default_limits.server_load[server_load_level]
    adjusted_limit := base_limit * multiplier
}

# Get user's base rate limit
user_rate_limit(user) := limit if {
    role := user.role
    limit := default_limits.user[role]
}

user_rate_limit(user) := default_limits.user.user if {
    not user.role
}

# Get tool's base rate limit
tool_rate_limit(tool) := limit if {
    sensitivity := tool.sensitivity_level
    limit := default_limits.tool[sensitivity]
}

tool_rate_limit(tool) := default_limits.tool.low if {
    not tool.sensitivity_level
}

# Calculate final rate limit (minimum of user and tool limits, adjusted for load)
final_rate_limit(user, tool, context) := limit if {
    user_limit := user_rate_limit(user)
    tool_limit := tool_rate_limit(tool)
    base_limit := min(user_limit, tool_limit)

    server_load := context.server_load
    limit := effective_rate_limit(base_limit, server_load)
}

# ============================================================================
# RATE LIMIT CHECKS
# ============================================================================

# Check if user is within rate limit for current window
within_rate_limit if {
    input.context.rate_limit_data.current_window_count < final_rate_limit(
        input.user,
        input.tool,
        input.context
    )
}

# Check burst allowance (allow temporary spikes)
within_burst_allowance if {
    limit := final_rate_limit(input.user, input.tool, input.context)
    burst_limit := limit * burst_multiplier
    input.context.rate_limit_data.current_window_count < burst_limit
}

# Check token bucket (more sophisticated rate limiting)
within_token_bucket if {
    bucket_state := input.context.rate_limit_data.token_bucket
    current_time := input.context.timestamp

    limit := final_rate_limit(input.user, input.tool, input.context)
    refill_rate := limit / 60  # Tokens per second
    max_tokens := limit
    cost := 1  # Each request costs 1 token

    token_bucket_allow(bucket_state, current_time, refill_rate, max_tokens, cost)
}

# ============================================================================
# MULTI-WINDOW RATE LIMITING
# ============================================================================

# Check all time windows
check_all_windows if {
    within_minute_limit
    within_hour_limit
    within_day_limit
}

within_minute_limit if {
    input.context.rate_limit_data.minute_count < final_rate_limit(
        input.user,
        input.tool,
        input.context
    )
}

within_hour_limit if {
    hourly_limit := final_rate_limit(input.user, input.tool, input.context) * 60
    input.context.rate_limit_data.hour_count < hourly_limit
}

within_day_limit if {
    daily_limit := final_rate_limit(input.user, input.tool, input.context) * 1440
    input.context.rate_limit_data.day_count < daily_limit
}

# ============================================================================
# EXEMPTIONS
# ============================================================================

# Emergency override (system administrators)
is_exempt if {
    input.user.role == "system_admin"
    input.context.emergency_override == true
}

# Health check and monitoring tools are exempt
is_exempt if {
    input.tool.category == "monitoring"
    input.tool.is_health_check == true
}

# Rate limit bypass for critical operations
is_exempt if {
    input.action in ["health_check", "emergency_shutdown", "disaster_recovery"]
}

# ============================================================================
# FINAL DECISION
# ============================================================================

# Allow if exempt or within limits
allow if {
    is_exempt
}

allow if {
    not is_exempt
    within_token_bucket
    check_all_windows
}

# Default deny
default allow := false

# ============================================================================
# DECISION METADATA
# ============================================================================

# Calculate remaining quota
remaining_quota := quota if {
    limit := final_rate_limit(input.user, input.tool, input.context)
    current := input.context.rate_limit_data.current_window_count
    quota := max(0, limit - current)
}

# Calculate reset time
reset_time := time if {
    current_window_start := input.context.rate_limit_data.window_start
    window_duration := time_windows.minute
    time := current_window_start + window_duration
}

# Reason for decision
reason := "Allowed: Within rate limits" if {
    allow
    not is_exempt
}

reason := "Allowed: Exempt from rate limiting" if {
    allow
    is_exempt
}

reason := sprintf("Denied: Rate limit exceeded (%d/%d requests in current window)", [
    input.context.rate_limit_data.current_window_count,
    final_rate_limit(input.user, input.tool, input.context)
]) if {
    not allow
    not is_exempt
}

# ============================================================================
# RESULT
# ============================================================================

result := {
    "allow": allow,
    "reason": reason,
    "rate_limit": {
        "limit": final_rate_limit(input.user, input.tool, input.context),
        "remaining": remaining_quota,
        "reset_at": reset_time,
        "retry_after": max(0, reset_time - input.context.timestamp),
    },
    "exemption": is_exempt,
}
