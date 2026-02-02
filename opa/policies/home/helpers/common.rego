# SARK Home Policy Library - Common Functions
# Shared utility functions for home policies
#
# Import this library in your policies:
#   import data.sark.home.helpers.common

package sark.home.helpers.common

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Time Utilities
# =============================================================================

# Check if current hour is within a time range (handles overnight ranges)
# Usage: is_time_in_range(14, 9, 17) => true (2pm is between 9am-5pm)
# Usage: is_time_in_range(23, 21, 7) => true (11pm is between 9pm-7am overnight)
is_time_in_range(hour, start, end) if {
    start <= end
    hour >= start
    hour < end
}

is_time_in_range(hour, start, end) if {
    start > end  # overnight range
    hour >= start
}

is_time_in_range(hour, start, end) if {
    start > end  # overnight range
    hour < end
}

# Check if current day is a weekday
is_weekday(day) if {
    day in ["monday", "tuesday", "wednesday", "thursday", "friday"]
}

# Check if current day is a weekend
is_weekend(day) if {
    day in ["saturday", "sunday"]
}

# =============================================================================
# User Group Utilities
# =============================================================================

# Check if user is in an admin group
is_admin_user(user_group) if {
    user_group in ["admin", "administrator", "root"]
}

# Check if user is a minor (child)
is_minor_user(user_group) if {
    user_group in ["child", "children", "minor", "teen", "teenager", "kid"]
}

# Check if user is an adult
is_adult_user(user_group) if {
    user_group in ["admin", "parent", "adult", "guardian"]
}

# =============================================================================
# Cost Calculation Utilities
# =============================================================================

# Estimate cost based on tokens (rough OpenAI-like pricing)
# Input tokens: ~$0.01 per 1K, Output tokens: ~$0.03 per 1K
estimate_cost_usd(input_tokens, output_tokens) := cost if {
    input_cost := (input_tokens / 1000) * 0.01
    output_cost := (output_tokens / 1000) * 0.03
    cost := input_cost + output_cost
}

# Calculate remaining budget
remaining_daily_budget(spent, limit) := remaining if {
    remaining := limit - spent
    remaining >= 0
}

remaining_daily_budget(spent, limit) := 0 if {
    limit - spent < 0
}

# Calculate usage percentage
usage_percentage(current, limit) := pct if {
    limit > 0
    pct := (current / limit) * 100
}

usage_percentage(current, limit) := 0 if {
    limit <= 0
}

# =============================================================================
# PII Detection Utilities
# =============================================================================

# Common PII regex patterns
email_pattern := `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
phone_pattern := `(\+1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}`
ssn_pattern := `\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b`
credit_card_pattern := `\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b`

# Check for any PII in text
contains_any_pii(text) if {
    regex.match(email_pattern, text)
}

contains_any_pii(text) if {
    regex.match(phone_pattern, text)
}

contains_any_pii(text) if {
    regex.match(ssn_pattern, text)
}

contains_any_pii(text) if {
    regex.match(credit_card_pattern, text)
}

# Check for sensitive PII only (SSN, credit card)
contains_sensitive_pii(text) if {
    regex.match(ssn_pattern, text)
}

contains_sensitive_pii(text) if {
    regex.match(credit_card_pattern, text)
}

# =============================================================================
# Network Utilities
# =============================================================================

# Check if IP is in a private range
is_private_ip(ip) if {
    # 10.0.0.0/8
    startswith(ip, "10.")
}

is_private_ip(ip) if {
    # 172.16.0.0/12
    startswith(ip, "172.16.")
}

is_private_ip(ip) if {
    startswith(ip, "172.17.")
}

is_private_ip(ip) if {
    startswith(ip, "172.18.")
}

is_private_ip(ip) if {
    startswith(ip, "172.19.")
}

is_private_ip(ip) if {
    startswith(ip, "172.2")
}

is_private_ip(ip) if {
    startswith(ip, "172.30.")
}

is_private_ip(ip) if {
    startswith(ip, "172.31.")
}

is_private_ip(ip) if {
    # 192.168.0.0/16
    startswith(ip, "192.168.")
}

is_private_ip(ip) if {
    # Localhost
    ip == "127.0.0.1"
}

# =============================================================================
# Mode Utilities
# =============================================================================

# Standard mode values
valid_modes := ["observe", "advisory", "enforce"]

# Determine effective mode with fallback
effective_mode(requested_mode) := requested_mode if {
    requested_mode in valid_modes
}

effective_mode(requested_mode) := "observe" if {
    not requested_mode in valid_modes
}

# Mode descriptions for UI
mode_description("observe") := "Logging only - no requests blocked"
mode_description("advisory") := "Warnings shown but requests allowed"
mode_description("enforce") := "Policy violations are blocked"

# =============================================================================
# Severity Utilities
# =============================================================================

# Standard severity levels
severity_levels := ["info", "warning", "high", "critical"]

# Map allow/deny to base severity
base_severity(true) := "info"
base_severity(false) := "warning"

# =============================================================================
# List Utilities
# =============================================================================

# Check if any element from list1 is in list2
any_in(list1, list2) if {
    some item in list1
    item in list2
}

# Check if all elements from list1 are in list2
all_in(list1, list2) if {
    every item in list1 {
        item in list2
    }
}

# =============================================================================
# Decision Builder
# =============================================================================

# Build a standard policy decision object
build_decision(allow_val, reason_val, policy_name, severity_val, metadata_obj) := {
    "allow": allow_val,
    "reason": reason_val,
    "policy": policy_name,
    "severity": severity_val,
    "metadata": metadata_obj
}

# Build decision with automatic severity
build_decision_auto(allow_val, reason_val, policy_name, metadata_obj) := decision if {
    severity_val := base_severity(allow_val)
    decision := build_decision(allow_val, reason_val, policy_name, severity_val, metadata_obj)
}
