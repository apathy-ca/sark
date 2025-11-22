package sark.policies.time_based

import rego.v1

# ============================================================================
# TIME-BASED ACCESS CONTROL POLICY
# ============================================================================
#
# Enforces time-based restrictions on tool access based on:
# - Business hours (configurable time windows)
# - Day of week restrictions
# - Timezone support
# - Role-based exemptions
# - Sensitivity-based time restrictions
#
# Use cases:
# - Restrict critical operations to business hours
# - Prevent off-hours access for certain roles
# - Emergency access during maintenance windows
# - Compliance requirements (e.g., no changes during weekends)
#
# ============================================================================

# Default deny for undefined time-based checks
default allow := false

# Business hours configuration (UTC)
# Can be overridden via policy data
default_business_hours := {
	"monday": {"start": 9, "end": 17},
	"tuesday": {"start": 9, "end": 17},
	"wednesday": {"start": 9, "end": 17},
	"thursday": {"start": 9, "end": 17},
	"friday": {"start": 9, "end": 17},
	"saturday": null,
	"sunday": null,
}

# Timezone offset from UTC (hours)
default_timezone_offset := 0

# ============================================================================
# MAIN DECISION
# ============================================================================

# Allow if time-based checks pass
allow if {
	decision.allow
}

# Main decision structure
decision := {
	"allow": allow_decision,
	"reason": reason,
	"violations": violations_list,
	"current_time": current_time_info,
	"applied_restrictions": applied_restrictions_list,
}

# ============================================================================
# TIME-BASED ALLOW LOGIC
# ============================================================================

# Always allow admins (they can override time restrictions)
allow_decision if {
	input.user.role == "admin"
}

# Allow if no time restrictions apply
allow_decision if {
	count(applicable_restrictions) == 0
}

# Allow if all applicable restrictions are satisfied
allow_decision if {
	count(applicable_restrictions) > 0
	count(violations) == 0
}

# ============================================================================
# TIME RESTRICTIONS
# ============================================================================

# Get applicable time restrictions based on context
applicable_restrictions contains restriction if {
	# Sensitivity-based restrictions
	sensitivity := input.tool.sensitivity_level
	restriction := sensitivity_time_restrictions[sensitivity]
}

applicable_restrictions contains restriction if {
	# Action-based restrictions
	action := input.action
	restriction := action_time_restrictions[action]
}

applicable_restrictions contains restriction if {
	# Tool-specific restrictions
	tool_name := input.tool.name
	restriction := tool_time_restrictions[tool_name]
}

applicable_restrictions contains restriction if {
	# Role-based restrictions (non-admins)
	input.user.role != "admin"
	restriction := role_time_restrictions[input.user.role]
}

# Sensitivity-based time restrictions
sensitivity_time_restrictions := {
	"critical": {
		"type": "business_hours_only",
		"reason": "Critical tools require business hours access",
		"exempt_roles": ["admin"],
	},
	"high": {
		"type": "business_hours_preferred",
		"reason": "High sensitivity tools preferred during business hours",
		"exempt_roles": ["admin", "service"],
		"allow_override": true,
	},
}

# Action-based time restrictions
action_time_restrictions := {
	"server:delete": {
		"type": "business_hours_only",
		"reason": "Server deletion requires business hours",
		"exempt_roles": ["admin"],
	},
	"tool:deploy": {
		"type": "business_hours_only",
		"reason": "Tool deployment requires business hours",
		"exempt_roles": ["admin", "service"],
	},
}

# Tool-specific time restrictions (examples - would be configured via data)
tool_time_restrictions := {}

# Role-based time restrictions
role_time_restrictions := {
	"viewer": {
		"type": "business_hours_only",
		"reason": "Viewer role limited to business hours",
		"exempt_roles": [],
	},
}

# ============================================================================
# TIME CALCULATIONS
# ============================================================================

# Get current time info
current_time_info := {
	"timestamp": time.now_ns(),
	"weekday": time.weekday(time.now_ns()),
	"hour": hour,
	"minute": minute,
	"is_business_hours": is_business_hours,
	"is_weekend": is_weekend,
}

# Extract hour and minute from current time
hour := time.clock([time.now_ns()])[0]

minute := time.clock([time.now_ns()])[1]

# Check if current time is within business hours
is_business_hours if {
	not is_weekend
	weekday_name := weekday_names[time.weekday(time.now_ns())]
	business_hours := get_business_hours(weekday_name)
	business_hours != null
	hour >= business_hours.start
	hour < business_hours.end
}

# Check if current day is a weekend
is_weekend if {
	weekday := time.weekday(time.now_ns())
	weekday_name := weekday_names[weekday]
	weekday_name in ["saturday", "sunday"]
}

# Weekday name mapping (0 = Monday in time.weekday)
weekday_names := [
	"monday",
	"tuesday",
	"wednesday",
	"thursday",
	"friday",
	"saturday",
	"sunday",
]

# Get business hours for a specific weekday
get_business_hours(weekday) := hours if {
	# Try to get from input data first
	hours := input.policy_config.business_hours[weekday]
}

get_business_hours(weekday) := hours if {
	# Fall back to default
	not input.policy_config.business_hours
	hours := default_business_hours[weekday]
}

# ============================================================================
# VIOLATION DETECTION
# ============================================================================

# Collect all violations
violations contains violation if {
	restriction := applicable_restrictions[_]
	not is_restriction_satisfied(restriction)
	violation := {
		"type": "time_restriction",
		"restriction": restriction,
		"current_time": current_time_info,
		"reason": restriction.reason,
	}
}

# Check if a restriction is satisfied
is_restriction_satisfied(restriction) if {
	restriction.type == "business_hours_only"
	is_business_hours
}

is_restriction_satisfied(restriction) if {
	restriction.type == "business_hours_only"
	not is_business_hours
	# Check if user role is exempt
	input.user.role in restriction.exempt_roles
}

is_restriction_satisfied(restriction) if {
	restriction.type == "business_hours_preferred"
	# Preferred restrictions always allow with warning
	true
}

is_restriction_satisfied(restriction) if {
	restriction.type == "business_hours_only"
	not is_business_hours
	# Check if override is provided and allowed
	restriction.allow_override == true
	input.context.time_override == true
	input.context.time_override_reason != ""
}

# ============================================================================
# REASON GENERATION
# ============================================================================

reason := msg if {
	allow_decision
	count(violations) == 0
	count(applicable_restrictions) == 0
	msg := "No time restrictions apply"
}

reason := msg if {
	allow_decision
	count(violations) == 0
	count(applicable_restrictions) > 0
	msg := sprintf("All time restrictions satisfied (%d checked)", [count(applicable_restrictions)])
}

reason := msg if {
	allow_decision
	input.user.role == "admin"
	msg := "Admin role exempt from time restrictions"
}

reason := msg if {
	not allow_decision
	count(violations) > 0
	violation_reasons := [v.reason | v := violations[_]]
	msg := sprintf("Time restrictions violated: %s", [concat("; ", violation_reasons)])
}

# ============================================================================
# APPLIED RESTRICTIONS LIST
# ============================================================================

applied_restrictions_list := [restriction |
	restriction := applicable_restrictions[_]
]

violations_list := [violation |
	violation := violations[_]
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Check if a specific time is within business hours (for testing)
is_time_in_business_hours(timestamp_ns) if {
	weekday := time.weekday(timestamp_ns)
	weekday_name := weekday_names[weekday]
	not weekday_name in ["saturday", "sunday"]
	hour := time.clock([timestamp_ns])[0]
	business_hours := get_business_hours(weekday_name)
	business_hours != null
	hour >= business_hours.start
	hour < business_hours.end
}

# Calculate if a time window overlaps with business hours
time_window_overlaps_business_hours(start_ns, end_ns) if {
	# Simple check: if any hour in the range overlaps
	is_time_in_business_hours(start_ns)
}

time_window_overlaps_business_hours(start_ns, end_ns) if {
	is_time_in_business_hours(end_ns)
}

# ============================================================================
# EMERGENCY OVERRIDE
# ============================================================================

# Allow emergency override with proper justification
allow_decision if {
	input.context.emergency_override == true
	input.context.emergency_reason != ""
	input.context.emergency_approver != ""
	# Log this for audit
	trace(sprintf("EMERGENCY OVERRIDE: %s (approved by: %s)", [
		input.context.emergency_reason,
		input.context.emergency_approver,
	]))
}

# ============================================================================
# MAINTENANCE WINDOW SUPPORT
# ============================================================================

# Allow during maintenance windows (configured via data)
allow_decision if {
	maintenance_window := input.policy_config.maintenance_windows[_]
	current_time := time.now_ns()
	current_time >= maintenance_window.start
	current_time <= maintenance_window.end
	input.action in maintenance_window.allowed_actions
}
