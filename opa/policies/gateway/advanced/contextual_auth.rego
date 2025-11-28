# Context-Aware Authorization Policy
# Authorization decisions based on temporal, geolocation, risk, and environmental context

package mcp.gateway.contextual

import future.keywords.if
import future.keywords.in

# ============================================================================
# TIME-BASED AUTHORIZATION
# ============================================================================

# Business hours (9 AM - 6 PM)
is_business_hours(timestamp) if {
    timestamp == 0  # Test mode
}

is_business_hours(timestamp) if {
    timestamp > 0
    hour := time.clock(timestamp)[0]
    hour >= 9
    hour < 18
}

# Weekend check
is_weekend(timestamp) if {
    timestamp > 0
    weekday := time.weekday(timestamp)
    weekday in [0, 6]  # Saturday (6) or Sunday (0)
}

# Holiday check (simplified - in production, use external calendar service)
is_holiday(timestamp) if {
    # Check against configured holidays
    date_str := time.format(timestamp)
    input.context.holidays[date_str]
}

# Time-based restrictions
allow_time_based if {
    # Critical tools only during business hours
    input.tool.sensitivity_level != "critical"
}

allow_time_based if {
    input.tool.sensitivity_level == "critical"
    is_business_hours(input.context.timestamp)
    not is_weekend(input.context.timestamp)
    not is_holiday(input.context.timestamp)
}

# ============================================================================
# LOCATION-BASED AUTHORIZATION
# ============================================================================

# Allowed countries for data processing
allowed_countries := {"US", "CA", "GB", "FR", "DE"}

# High-risk countries requiring additional scrutiny
high_risk_countries := {"CN", "RU", "KP", "IR"}

# Check if client IP is from allowed location
is_allowed_location if {
    client_country := input.context.client_location.country_code
    client_country in allowed_countries
}

# Block access from high-risk locations for sensitive tools
location_restrictions_met if {
    input.tool.sensitivity_level in ["low", "medium"]
}

location_restrictions_met if {
    input.tool.sensitivity_level in ["high", "critical"]
    is_allowed_location
    not (input.context.client_location.country_code in high_risk_countries)
}

# VPN detection for sensitive operations
vpn_check_passed if {
    input.tool.sensitivity_level in ["low", "medium"]
}

vpn_check_passed if {
    input.tool.sensitivity_level in ["high", "critical"]
    input.context.client_location.is_vpn == false
    input.context.client_location.is_proxy == false
    input.context.client_location.is_tor == false
}

# ============================================================================
# RISK-BASED AUTHORIZATION
# ============================================================================

# Calculate user risk score based on multiple factors
user_risk_score := score if {
    # Base score
    base := 0

    # Failed login attempts
    failed_login_penalty := input.context.user_behavior.failed_logins * 10

    # Unusual activity
    unusual_activity_penalty := count(input.context.user_behavior.unusual_patterns) * 5

    # Account age (newer accounts = higher risk)
    account_age_days := (input.context.timestamp - input.user.created_at) / 86400
    age_penalty := account_age_days < 30 ? 20 : 0

    # Geographic anomaly
    geo_anomaly_penalty := input.context.user_behavior.location_anomaly ? 15 : 0

    # Time anomaly
    time_anomaly_penalty := input.context.user_behavior.time_anomaly ? 10 : 0

    score := base + failed_login_penalty + unusual_activity_penalty + age_penalty + geo_anomaly_penalty + time_anomaly_penalty
}

# Risk level classification
risk_level := level if {
    score := user_risk_score
    level := "low" if score < 20
}

risk_level := level if {
    score := user_risk_score
    level := "medium" if {
        score >= 20
        score < 50
    }
}

risk_level := level if {
    score := user_risk_score
    level := "high" if score >= 50
}

# Risk-based authorization
risk_check_passed if {
    level := risk_level
    level == "low"
}

risk_check_passed if {
    level := risk_level
    level == "medium"
    input.tool.sensitivity_level in ["low", "medium"]
}

# High risk users blocked from high/critical sensitivity tools
# unless they complete step-up authentication

# ============================================================================
# MULTI-FACTOR AUTHENTICATION REQUIREMENTS
# ============================================================================

# MFA required for critical operations
mfa_required if {
    input.tool.sensitivity_level == "critical"
}

mfa_required if {
    input.tool.requires_mfa == true
}

mfa_required if {
    level := risk_level
    level in ["medium", "high"]
    input.tool.sensitivity_level in ["high", "critical"]
}

mfa_satisfied if {
    not mfa_required
}

mfa_satisfied if {
    mfa_required
    input.context.authentication.mfa_verified == true
    # MFA session must be recent (within last 15 minutes)
    mfa_age := input.context.timestamp - input.context.authentication.mfa_timestamp
    mfa_age < 900  # 15 minutes
}

# ============================================================================
# STEP-UP AUTHENTICATION
# ============================================================================

# Require step-up authentication for sensitive operations
stepup_required if {
    input.tool.sensitivity_level == "critical"
    input.action in ["delete", "modify", "export"]
}

stepup_required if {
    level := risk_level
    level == "high"
}

stepup_satisfied if {
    not stepup_required
}

stepup_satisfied if {
    stepup_required
    input.context.authentication.stepup_verified == true
    # Step-up session must be very recent (within last 5 minutes)
    stepup_age := input.context.timestamp - input.context.authentication.stepup_timestamp
    stepup_age < 300  # 5 minutes
}

# ============================================================================
# DEVICE TRUST
# ============================================================================

# Known device check
is_known_device if {
    device_id := input.context.device.device_id
    device_id in input.user.known_devices
}

# Device trust level
device_trust_level := "trusted" if {
    is_known_device
    input.context.device.is_managed == true
    input.context.device.is_compliant == true
}

device_trust_level := "recognized" if {
    is_known_device
    not (device_trust_level == "trusted")
}

device_trust_level := "unknown" if {
    not is_known_device
}

# Device trust requirements
device_check_passed if {
    input.tool.sensitivity_level in ["low", "medium"]
}

device_check_passed if {
    input.tool.sensitivity_level == "high"
    device_trust_level in ["trusted", "recognized"]
}

device_check_passed if {
    input.tool.sensitivity_level == "critical"
    device_trust_level == "trusted"
}

# ============================================================================
# SESSION VALIDATION
# ============================================================================

# Session must be active and not expired
session_valid if {
    session_age := input.context.timestamp - input.context.authentication.session_start
    session_max_age := 28800  # 8 hours
    session_age < session_max_age
}

session_valid if {
    # Allow if session is recent and user is active
    last_activity := input.context.authentication.last_activity
    idle_time := input.context.timestamp - last_activity
    max_idle := 3600  # 1 hour
    idle_time < max_idle
}

# ============================================================================
# FINAL AUTHORIZATION DECISION
# ============================================================================

# All contextual checks must pass
allow if {
    allow_time_based
    location_restrictions_met
    vpn_check_passed
    risk_check_passed
    mfa_satisfied
    stepup_satisfied
    device_check_passed
    session_valid
}

default allow := false

# ============================================================================
# DECISION METADATA
# ============================================================================

# Identify which checks failed
failed_checks := checks if {
    checks := {check |
        not allow_time_based
        check := "time_based"
    } | {check |
        not location_restrictions_met
        check := "location_restrictions"
    } | {check |
        not vpn_check_passed
        check := "vpn_check"
    } | {check |
        not risk_check_passed
        check := "risk_check"
    } | {check |
        not mfa_satisfied
        check := "mfa_required"
    } | {check |
        not stepup_satisfied
        check := "stepup_required"
    } | {check |
        not device_check_passed
        check := "device_trust"
    } | {check |
        not session_valid
        check := "session_validity"
    }
}

# Reason for decision
reason := "Allowed: All contextual checks passed" if {
    allow
}

reason := sprintf("Denied: Failed contextual checks: %s", [concat(", ", failed_checks)]) if {
    not allow
    count(failed_checks) > 0
}

# Required actions for user to gain access
required_actions := actions if {
    not allow
    actions := {action |
        not mfa_satisfied
        mfa_required
        action := "complete_mfa"
    } | {action |
        not stepup_satisfied
        stepup_required
        action := "complete_stepup_auth"
    } | {action |
        not device_check_passed
        action := "use_trusted_device"
    } | {action |
        not location_restrictions_met
        action := "access_from_allowed_location"
    }
}

# ============================================================================
# RESULT
# ============================================================================

result := {
    "allow": allow,
    "reason": reason,
    "context": {
        "risk_score": user_risk_score,
        "risk_level": risk_level,
        "device_trust": device_trust_level,
        "mfa_required": mfa_required,
        "stepup_required": stepup_required,
    },
    "required_actions": required_actions,
    "failed_checks": failed_checks,
}
