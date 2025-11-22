package sark.policies.mfa_required

import rego.v1

# ============================================================================
# MFA REQUIREMENT POLICY
# ============================================================================
#
# Enforces Multi-Factor Authentication requirements based on:
# - Sensitivity level (critical/high tools require MFA)
# - Action type (destructive actions require MFA)
# - Role requirements (certain roles always need MFA)
# - Time-based MFA (re-verification after timeout)
# - Step-up authentication (additional MFA for sensitive ops)
#
# Use cases:
# - Protect critical infrastructure operations
# - Compliance requirements (SOC2, ISO 27001)
# - Prevent unauthorized access with compromised credentials
# - Step-up auth for sensitive operations
# - Time-based re-verification
#
# ============================================================================

# Default deny if MFA checks fail
default allow := false

# MFA session timeout (seconds)
default_mfa_timeout := 3600

# 1 hour

# ============================================================================
# MAIN DECISION
# ============================================================================

# Allow if MFA requirements are satisfied
allow if {
	decision.allow
}

# Main decision structure
decision := {
	"allow": allow_decision,
	"reason": reason,
	"violations": violations_list,
	"mfa_status": mfa_status_info,
	"required_factors": required_factors_list,
}

# ============================================================================
# MFA-BASED ALLOW LOGIC
# ============================================================================

# Allow if MFA not required for this operation
allow_decision if {
	not mfa_required
}

# Allow if MFA is verified and session is valid
allow_decision if {
	mfa_required
	mfa_verified
	mfa_session_valid
	count(violations) == 0
}

# Allow service accounts without MFA (they use API keys)
allow_decision if {
	input.user.role == "service"
	has_valid_api_key
}

# ============================================================================
# MFA REQUIREMENT DETECTION
# ============================================================================

# MFA required if any condition triggers it
mfa_required if {
	sensitivity_requires_mfa
}

mfa_required if {
	action_requires_mfa
}

mfa_required if {
	role_requires_mfa
}

mfa_required if {
	tool_requires_mfa
}

mfa_required if {
	context_requires_mfa
}

# Sensitivity-based MFA requirements
sensitivity_requires_mfa if {
	input.tool.sensitivity_level == "critical"
}

sensitivity_requires_mfa if {
	input.tool.sensitivity_level == "high"
	input.action in high_sensitivity_actions
}

high_sensitivity_actions := {
	"tool:invoke",
	"tool:delete",
	"tool:deploy",
	"server:delete",
	"server:modify",
	"config:update",
	"secrets:read",
	"secrets:write",
}

# Action-based MFA requirements
action_requires_mfa if {
	input.action in destructive_actions
}

destructive_actions := {
	"server:delete",
	"tool:delete",
	"user:delete",
	"team:delete",
	"config:delete",
	"secrets:delete",
}

# Role-based MFA requirements
role_requires_mfa if {
	input.user.role == "admin"
	input.action in admin_mfa_actions
}

admin_mfa_actions := {
	"user:create",
	"user:delete",
	"role:assign",
	"policy:update",
	"secrets:write",
}

# Tool-specific MFA requirements (configurable)
tool_requires_mfa if {
	tool_name := input.tool.name
	tool_name in get_mfa_required_tools
}

get_mfa_required_tools := tools if {
	tools := input.policy_config.mfa_required_tools
	tools != null
}

get_mfa_required_tools := [] if {
	not input.policy_config.mfa_required_tools
}

# Context-based MFA requirements
context_requires_mfa if {
	# Require MFA for off-hours access to critical systems
	input.tool.sensitivity_level in ["critical", "high"]
	not is_business_hours
}

context_requires_mfa if {
	# Require MFA when accessing from non-corporate network
	not is_corporate_network
	input.tool.sensitivity_level in ["critical", "high"]
}

# ============================================================================
# MFA VERIFICATION
# ============================================================================

# Check if MFA is verified
mfa_verified if {
	input.user.mfa_verified == true
}

mfa_verified if {
	input.context.mfa_token != ""
	valid_mfa_token
}

# Validate MFA token (in production, this would call an MFA service)
valid_mfa_token if {
	# Check if token is present and recent
	token := input.context.mfa_token
	token != ""
	# In production, validate token with MFA service (TOTP, WebAuthn, etc.)
	true
}

# Check if MFA session is still valid
mfa_session_valid if {
	not mfa_required # If MFA not required, session validity doesn't matter
}

mfa_session_valid if {
	mfa_required
	mfa_timestamp := get_mfa_timestamp
	current_time := time.now_ns()
	# Convert to seconds for comparison
	mfa_age_seconds := (current_time - mfa_timestamp) / 1000000000
	mfa_age_seconds <= get_mfa_timeout
}

# Get MFA timestamp
get_mfa_timestamp := timestamp if {
	timestamp := input.user.mfa_timestamp
	timestamp != null
}

get_mfa_timestamp := timestamp if {
	not input.user.mfa_timestamp
	timestamp := input.context.mfa_timestamp
	timestamp != null
}

get_mfa_timestamp := 0 if {
	not input.user.mfa_timestamp
	not input.context.mfa_timestamp
}

# Get MFA timeout from config or default
get_mfa_timeout := timeout if {
	timeout := input.policy_config.mfa_timeout_seconds
	timeout != null
}

get_mfa_timeout := default_mfa_timeout if {
	not input.policy_config.mfa_timeout_seconds
}

# ============================================================================
# MFA STATUS INFO
# ============================================================================

mfa_status_info := {
	"required": mfa_required,
	"verified": mfa_verified,
	"session_valid": mfa_session_valid,
	"timestamp": get_mfa_timestamp,
	"age_seconds": mfa_age_seconds,
	"timeout_seconds": get_mfa_timeout,
	"session_expired": mfa_session_expired,
}

mfa_age_seconds := age if {
	mfa_timestamp := get_mfa_timestamp
	mfa_timestamp > 0
	current_time := time.now_ns()
	age := (current_time - mfa_timestamp) / 1000000000
}

mfa_age_seconds := 0 if {
	get_mfa_timestamp == 0
}

mfa_session_expired if {
	mfa_required
	mfa_age_seconds > get_mfa_timeout
}

# ============================================================================
# REQUIRED FACTORS
# ============================================================================

# List of authentication factors required
required_factors_list := factors if {
	mfa_required
	factors := ["password", "mfa"]
}

required_factors_list := factors if {
	not mfa_required
	factors := ["password"]
}

# Check for step-up authentication requirements
step_up_required if {
	input.tool.sensitivity_level == "critical"
	input.action in ["tool:invoke", "server:delete"]
	# Require additional verification even if MFA already done
	mfa_age_seconds > 300 # 5 minutes
}

required_factors_list := factors if {
	step_up_required
	factors := ["password", "mfa", "step_up"]
}

# ============================================================================
# VIOLATION DETECTION
# ============================================================================

violations contains violation if {
	mfa_required
	not mfa_verified
	violation := {
		"type": "mfa_not_verified",
		"reason": "Multi-factor authentication required but not verified",
		"required_factors": required_factors_list,
	}
}

violations contains violation if {
	mfa_required
	mfa_verified
	not mfa_session_valid
	violation := {
		"type": "mfa_session_expired",
		"reason": sprintf("MFA session expired (age: %d seconds, timeout: %d seconds)", [
			mfa_age_seconds,
			get_mfa_timeout,
		]),
		"mfa_age": mfa_age_seconds,
		"mfa_timeout": get_mfa_timeout,
	}
}

violations contains violation if {
	step_up_required
	not input.context.step_up_verified
	violation := {
		"type": "step_up_required",
		"reason": "Additional authentication verification required for this sensitive operation",
		"last_mfa_age": mfa_age_seconds,
	}
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Check if within business hours (simplified - would use time_based.rego)
is_business_hours if {
	hour := time.clock([time.now_ns()])[0]
	hour >= 9
	hour < 17
	weekday := time.weekday(time.now_ns())
	weekday < 5 # Monday-Friday
}

# Check if accessing from corporate network
is_corporate_network if {
	client_ip := input.context.client_ip
	client_ip != ""
	# Check if IP is in corporate range
	is_corporate_ip(client_ip)
}

is_corporate_ip(ip) if {
	# Private IP ranges (RFC 1918)
	startswith(ip, "10.")
}

is_corporate_ip(ip) if {
	startswith(ip, "192.168.")
}

is_corporate_ip(ip) if {
	# Corporate IP ranges from config
	corporate_range := input.policy_config.corporate_ip_ranges[_]
	net.cidr_contains(corporate_range, ip)
}

# Check for valid API key (service accounts)
has_valid_api_key if {
	api_key := input.context.api_key
	api_key != ""
	api_key_valid(api_key)
}

api_key_valid(key) if {
	# In production, validate API key with key management service
	key != ""
	# Check key format, expiry, etc.
	true
}

# ============================================================================
# REASON GENERATION
# ============================================================================

reason := msg if {
	allow_decision
	not mfa_required
	msg := "MFA not required for this operation"
}

reason := msg if {
	allow_decision
	mfa_required
	count(violations) == 0
	msg := sprintf("MFA verified and session valid (age: %d seconds)", [mfa_age_seconds])
}

reason := msg if {
	allow_decision
	input.user.role == "service"
	msg := "Service account with valid API key"
}

reason := msg if {
	not allow_decision
	count(violations) > 0
	violation_reasons := [v.reason | v := violations[_]]
	msg := sprintf("MFA requirements not met: %s", [concat("; ", violation_reasons)])
}

violations_list := [violation |
	violation := violations[_]
]

# ============================================================================
# MFA CONFIGURATION
# ============================================================================

# Supported MFA methods
supported_mfa_methods := {
	"totp": "Time-based One-Time Password",
	"webauthn": "WebAuthn/FIDO2",
	"sms": "SMS code (not recommended)",
	"push": "Push notification",
	"backup_codes": "Backup codes",
}

# Get configured MFA methods
configured_mfa_methods := methods if {
	methods := input.policy_config.mfa_methods
	methods != null
}

configured_mfa_methods := ["totp", "webauthn"] if {
	not input.policy_config.mfa_methods
}

# Validate that user has configured MFA
user_mfa_configured if {
	input.user.mfa_methods != null
	count(input.user.mfa_methods) > 0
}

violations contains violation if {
	mfa_required
	not user_mfa_configured
	violation := {
		"type": "mfa_not_configured",
		"reason": "User account requires MFA setup before accessing sensitive resources",
		"supported_methods": configured_mfa_methods,
	}
}

# ============================================================================
# AUDIT LOGGING
# ============================================================================

audit_log := {
	"mfa_required": mfa_required,
	"mfa_verified": mfa_verified,
	"mfa_session_valid": mfa_session_valid,
	"mfa_age_seconds": mfa_age_seconds,
	"violations": count(violations),
	"step_up_required": step_up_required,
	"user_mfa_configured": user_mfa_configured,
}

# ============================================================================
# EMERGENCY OVERRIDE
# ============================================================================

# Allow emergency override with proper documentation
allow_decision if {
	input.context.emergency_override == true
	input.context.emergency_reason != ""
	input.context.emergency_approver != ""
	input.user.role == "admin"
	trace(sprintf("EMERGENCY MFA OVERRIDE: %s (approved by: %s)", [
		input.context.emergency_reason,
		input.context.emergency_approver,
	]))
}
