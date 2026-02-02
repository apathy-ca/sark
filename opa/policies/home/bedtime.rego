# SARK Home Bedtime Policy
# Controls LLM access based on time-of-day rules for household devices
#
# Use case: Restrict children's access to AI assistants during bedtime hours

package sark.home.bedtime

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Deny
# =============================================================================

default allow := false
default reason := ""

# =============================================================================
# Allow Rules
# =============================================================================

# Allow if not during bedtime hours
allow if {
    not is_bedtime_active
}

# Allow if device is exempt from bedtime rules
allow if {
    is_device_exempt
}

# Allow if user group is exempt (e.g., parents/admins)
allow if {
    is_user_exempt
}

# =============================================================================
# Bedtime Detection
# =============================================================================

# Check if current time falls within bedtime window
# Handles both same-day (e.g., 13:00-17:00) and overnight (e.g., 21:00-07:00) windows
is_bedtime_active if {
    hour := input.context.hour
    start := input.rules.bedtime_start_hour
    end := input.rules.bedtime_end_hour

    # Overnight window (e.g., 21:00 to 07:00)
    start > end
    hour >= start
}

is_bedtime_active if {
    hour := input.context.hour
    start := input.rules.bedtime_start_hour
    end := input.rules.bedtime_end_hour

    # Overnight window (e.g., 21:00 to 07:00)
    start > end
    hour < end
}

is_bedtime_active if {
    hour := input.context.hour
    start := input.rules.bedtime_start_hour
    end := input.rules.bedtime_end_hour

    # Same-day window (e.g., 13:00 to 17:00)
    start <= end
    hour >= start
    hour < end
}

# =============================================================================
# Exemptions
# =============================================================================

# Device exemption - some devices (parent's phone, etc.) skip bedtime rules
is_device_exempt if {
    input.user.device_ip in data.home.bedtime_exempt_devices
}

is_device_exempt if {
    input.user.device_name in data.home.bedtime_exempt_devices
}

# User group exemption - parents and admins skip bedtime rules
is_user_exempt if {
    input.user.user_group in ["admin", "parent", "adult"]
}

# =============================================================================
# Day-of-Week Rules (Optional)
# =============================================================================

# Check if today is a bedtime-enforced day
is_enforced_day if {
    # If no specific days configured, enforce every day
    not input.rules.bedtime_days
}

is_enforced_day if {
    # If days are configured, check if today is in the list
    input.context.day_of_week in input.rules.bedtime_days
}

# Override: Don't enforce bedtime if today is not an enforced day
allow if {
    not is_enforced_day
}

# =============================================================================
# Reason Messages
# =============================================================================

reason := sprintf("Bedtime active (%02d:00 - %02d:00). LLM access restricted.", [
    input.rules.bedtime_start_hour,
    input.rules.bedtime_end_hour
]) if {
    is_bedtime_active
    is_enforced_day
    not is_device_exempt
    not is_user_exempt
}

# =============================================================================
# Policy Decision Output
# =============================================================================

decision := {
    "allow": allow,
    "reason": reason,
    "policy": "bedtime",
    "severity": severity,
    "metadata": {
        "current_hour": input.context.hour,
        "bedtime_start": input.rules.bedtime_start_hour,
        "bedtime_end": input.rules.bedtime_end_hour,
        "is_bedtime": is_bedtime_active,
        "is_exempt": is_exempt
    }
}

# Severity level for logging/alerting
severity := "info" if {
    allow
}

severity := "warning" if {
    not allow
}

# Combined exemption check for metadata
is_exempt := true if {
    is_device_exempt
}

is_exempt := true if {
    is_user_exempt
}

is_exempt := false if {
    not is_device_exempt
    not is_user_exempt
}
