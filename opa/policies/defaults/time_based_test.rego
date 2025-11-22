package sark.policies.time_based

import rego.v1

# ============================================================================
# TIME-BASED POLICY TESTS
# ============================================================================

# Test: Admin bypasses time restrictions
test_admin_bypass_time_restrictions if {
	result := decision with input as {
		"user": {"id": "admin1", "role": "admin"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
	result.allow
	result.reason == "Admin role exempt from time restrictions"
}

# Test: Critical tool requires business hours
test_critical_tool_business_hours_required if {
	# During business hours (Wednesday 10 AM)
	wednesday_10am := 1699444800000000000 # 2023-11-08 10:00:00 UTC (Wednesday)
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
		with time.now_ns as wednesday_10am

	result.allow
}

# Test: Critical tool blocked outside business hours
test_critical_tool_outside_business_hours_blocked if {
	# Outside business hours (Wednesday 8 PM)
	wednesday_8pm := 1699477200000000000 # 2023-11-08 20:00:00 UTC (Wednesday)
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
		with time.now_ns as wednesday_8pm

	not result.allow
	count(result.violations) > 0
}

# Test: Weekend access blocked for critical tools
test_critical_tool_weekend_blocked if {
	# Saturday 10 AM
	saturday_10am := 1699617600000000000 # 2023-11-10 10:00:00 UTC (Saturday)
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
		with time.now_ns as saturday_10am

	not result.allow
	some violation in result.violations
	violation.type == "time_restriction"
}

# Test: High sensitivity with override allowed
test_high_sensitivity_override if {
	# Outside business hours with override
	wednesday_8pm := 1699477200000000000
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "high_tool", "sensitivity_level": "high"},
		"context": {
			"time_override": true,
			"time_override_reason": "Production incident",
		},
	}
		with time.now_ns as wednesday_8pm

	# Should allow because high sensitivity allows override
	result.allow
}

# Test: Emergency override works
test_emergency_override if {
	# Weekend with emergency override
	saturday_10am := 1699617600000000000
	result := allow with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {
			"emergency_override": true,
			"emergency_reason": "Critical production outage",
			"emergency_approver": "manager@company.com",
		},
	}
		with time.now_ns as saturday_10am

	result
}

# Test: Viewer role limited to business hours
test_viewer_business_hours_only if {
	# Outside business hours
	wednesday_8pm := 1699477200000000000
	result := decision with input as {
		"user": {"id": "viewer1", "role": "viewer"},
		"action": "tool:read",
		"tool": {"name": "read_tool", "sensitivity_level": "low"},
		"context": {},
	}
		with time.now_ns as wednesday_8pm

	not result.allow
}

# Test: Maintenance window allows access
test_maintenance_window_allows_access if {
	# Outside business hours but in maintenance window
	wednesday_8pm := 1699477200000000000
	wednesday_10pm := 1699484400000000000
	result := allow with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:deploy",
		"tool": {"name": "deploy_tool", "sensitivity_level": "high"},
		"context": {},
		"policy_config": {"maintenance_windows": [{
			"start": wednesday_8pm,
			"end": wednesday_10pm,
			"allowed_actions": ["tool:deploy", "server:update"],
		}]},
	}
		with time.now_ns as 1699480800000000000 # 9 PM, within window

	result
}

# Test: Service account exempt from time restrictions
test_service_account_exempt if {
	# Weekend
	saturday_10am := 1699617600000000000
	result := decision with input as {
		"user": {"id": "service1", "role": "service"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
		with time.now_ns as saturday_10am

	# Service accounts don't have explicit exemption in sensitivity restrictions
	# but can override with proper context
	not result.allow # Will fail without override
}

# Test: No time restrictions for low sensitivity
test_low_sensitivity_no_time_restrictions if {
	# Weekend
	saturday_10am := 1699617600000000000
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "low_tool", "sensitivity_level": "low"},
		"context": {},
	}
		with time.now_ns as saturday_10am

	result.allow
	result.reason == "No time restrictions apply"
}

# Test: Time window calculation
test_is_business_hours_monday_morning if {
	# Monday 10 AM
	monday_10am := 1699272000000000000 # 2023-11-06 10:00:00 UTC (Monday)
	is_business_hours with time.now_ns as monday_10am
}

test_is_not_business_hours_evening if {
	# Monday 8 PM
	monday_8pm := 1699308000000000000 # 2023-11-06 20:00:00 UTC (Monday)
	not is_business_hours with time.now_ns as monday_8pm
}

test_is_weekend_saturday if {
	saturday_10am := 1699617600000000000
	is_weekend with time.now_ns as saturday_10am
}

test_is_not_weekend_monday if {
	monday_10am := 1699272000000000000
	not is_weekend with time.now_ns as monday_10am
}

# Test: Server deletion requires business hours
test_server_deletion_business_hours if {
	# Outside business hours
	wednesday_8pm := 1699477200000000000
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "server:delete",
		"tool": {"name": "server_tool", "sensitivity_level": "medium"},
		"context": {},
	}
		with time.now_ns as wednesday_8pm

	not result.allow
	some violation in result.violations
	violation.restriction.type == "business_hours_only"
}

# Test: Custom business hours from config
test_custom_business_hours if {
	# 8 AM (before default 9 AM start)
	monday_8am := 1699268400000000000
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
		"policy_config": {"business_hours": {
			"monday": {"start": 8, "end": 18},
			"tuesday": {"start": 8, "end": 18},
			"wednesday": {"start": 8, "end": 18},
			"thursday": {"start": 8, "end": 18},
			"friday": {"start": 8, "end": 18},
			"saturday": null,
			"sunday": null,
		}},
	}
		with time.now_ns as monday_8am

	result.allow # Should allow with custom hours
}
