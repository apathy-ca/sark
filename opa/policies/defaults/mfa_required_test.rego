package sark.policies.mfa_required

import rego.v1

# ============================================================================
# MFA REQUIREMENT POLICY TESTS
# ============================================================================

# Test: MFA not required for low sensitivity
test_mfa_not_required_low_sensitivity if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "read_tool", "sensitivity_level": "low"},
		"context": {},
	}
	result.allow
	not result.mfa_status.required
}

# Test: MFA required for critical tools
test_mfa_required_critical_tools if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
	not result.allow
	result.mfa_status.required
	some violation in result.violations
	violation.type == "mfa_not_verified"
}

# Test: MFA verified allows access
test_mfa_verified_allows_access if {
	current_time := 1699444800000000000
	mfa_time := 1699444200000000000 # 10 minutes ago
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_verified": true,
			"mfa_timestamp": mfa_time,
			"mfa_methods": ["totp"],
		},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
		with time.now_ns as current_time
	result.allow
	result.mfa_status.verified
}

# Test: MFA session expired
test_mfa_session_expired if {
	current_time := 1699444800000000000
	mfa_time := 1699441200000000000 # 1 hour ago (default timeout)
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_verified": true,
			"mfa_timestamp": mfa_time,
			"mfa_methods": ["totp"],
		},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
		with time.now_ns as current_time
	not result.allow
	result.mfa_status.session_expired
	some violation in result.violations
	violation.type == "mfa_session_expired"
}

# Test: Service account with API key bypasses MFA
test_service_account_bypass_mfa if {
	result := decision with input as {
		"user": {"id": "service1", "role": "service"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {"api_key": "valid_key_123"},
	}
	result.allow
}

# Test: Destructive action requires MFA
test_destructive_action_requires_mfa if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "server:delete",
		"tool": {"name": "server_tool", "sensitivity_level": "medium"},
		"context": {},
	}
	not result.allow
	result.mfa_status.required
}

# Test: Admin actions require MFA
test_admin_actions_require_mfa if {
	result := decision with input as {
		"user": {"id": "admin1", "role": "admin", "mfa_verified": false},
		"action": "user:delete",
		"tool": {"name": "admin_tool", "sensitivity_level": "medium"},
		"context": {},
	}
	not result.allow
	result.mfa_status.required
}

# Test: High sensitivity off-hours requires MFA
test_high_sensitivity_off_hours_mfa if {
	# 8 PM (off-hours)
	wednesday_8pm := 1699477200000000000
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "tool:invoke",
		"tool": {"name": "high_tool", "sensitivity_level": "high"},
		"context": {},
	}
		with time.now_ns as wednesday_8pm
	not result.allow
	result.mfa_status.required
}

# Test: Non-corporate network requires MFA
test_non_corporate_network_mfa if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "tool:invoke",
		"tool": {"name": "high_tool", "sensitivity_level": "high"},
		"context": {"client_ip": "1.2.3.4"}, # Public IP
	}
	not result.allow
	result.mfa_status.required
}

# Test: Corporate network reduces MFA requirement
test_corporate_network_reduces_mfa if {
	current_time := 1699444800000000000
	mfa_time := 1699444200000000000
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_verified": true,
			"mfa_timestamp": mfa_time,
			"mfa_methods": ["totp"],
		},
		"action": "tool:invoke",
		"tool": {"name": "medium_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "10.0.0.100"}, # Private/corporate IP
	}
		with time.now_ns as current_time
	result.allow
}

# Test: MFA token validation
test_mfa_token_validation if {
	current_time := 1699444800000000000
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_methods": ["totp"],
		},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {"mfa_token": "123456"},
	}
		with time.now_ns as current_time
	result.allow
	result.mfa_status.verified
}

# Test: Custom MFA timeout
test_custom_mfa_timeout if {
	current_time := 1699444800000000000
	mfa_time := 1699443900000000000 # 15 minutes ago
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_verified": true,
			"mfa_timestamp": mfa_time,
			"mfa_methods": ["totp"],
		},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
		"policy_config": {"mfa_timeout_seconds": 600}, # 10 minutes
	}
		with time.now_ns as current_time
	not result.allow # Should fail because 15 min > 10 min timeout
	result.mfa_status.session_expired
}

# Test: Step-up authentication required
test_step_up_authentication_required if {
	current_time := 1699444800000000000
	mfa_time := 1699444500000000000 # 5 minutes ago (>300s = 5min)
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_verified": true,
			"mfa_timestamp": mfa_time,
			"mfa_methods": ["totp"],
		},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {}, # No step_up_verified
	}
		with time.now_ns as current_time
	not result.allow
	some violation in result.violations
	violation.type == "step_up_required"
}

# Test: Step-up authentication satisfied
test_step_up_authentication_satisfied if {
	current_time := 1699444800000000000
	mfa_time := 1699444500000000000
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_verified": true,
			"mfa_timestamp": mfa_time,
			"mfa_methods": ["totp"],
		},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {"step_up_verified": true},
	}
		with time.now_ns as current_time
	result.allow
}

# Test: MFA not configured violation
test_mfa_not_configured if {
	current_time := 1699444800000000000
	result := decision with input as {
		"user": {
			"id": "dev1",
			"role": "developer",
			"mfa_methods": null, # No MFA configured
		},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
		with time.now_ns as current_time
	not result.allow
	some violation in result.violations
	violation.type == "mfa_not_configured"
}

# Test: MFA configured check passes
test_mfa_configured_passes if {
	user_mfa_configured with input as {"user": {"mfa_methods": ["totp", "webauthn"]}}
	not user_mfa_configured with input as {"user": {"mfa_methods": null}}
	not user_mfa_configured with input as {"user": {"mfa_methods": []}}
}

# Test: Emergency override works
test_emergency_override if {
	result := decision with input as {
		"user": {"id": "admin1", "role": "admin", "mfa_verified": false},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {
			"emergency_override": true,
			"emergency_reason": "Critical production outage",
			"emergency_approver": "cto@company.com",
		},
	}
	result.allow
}

# Test: Emergency override requires admin role
test_emergency_override_requires_admin if {
	result := allow with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {
			"emergency_override": true,
			"emergency_reason": "Production issue",
			"emergency_approver": "manager@company.com",
		},
	}
	not result # Developer cannot use emergency override
}

# Test: Business hours check
test_is_business_hours if {
	# Monday 10 AM
	monday_10am := 1699272000000000000
	is_business_hours with time.now_ns as monday_10am
}

test_is_not_business_hours if {
	# Monday 8 PM
	monday_8pm := 1699308000000000000
	not is_business_hours with time.now_ns as monday_8pm
}

# Test: Corporate network detection
test_is_corporate_network if {
	is_corporate_network with input as {"context": {"client_ip": "10.0.0.1"}}
	is_corporate_network with input as {"context": {"client_ip": "192.168.1.1"}}
}

test_is_not_corporate_network if {
	not is_corporate_network with input as {"context": {"client_ip": "1.2.3.4"}}
}

# Test: Tool-specific MFA requirements
test_tool_specific_mfa if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "tool:invoke",
		"tool": {"name": "payment_processor", "sensitivity_level": "medium"},
		"context": {},
		"policy_config": {"mfa_required_tools": ["payment_processor", "user_admin"]},
	}
	not result.allow
	result.mfa_status.required
}

# Test: MFA age calculation
test_mfa_age_calculation if {
	current_time := 1699444800000000000
	mfa_time := 1699444200000000000 # 600 seconds ago
	mfa_age_seconds == 600 with input as {
		"user": {"mfa_timestamp": mfa_time},
		"context": {},
	}
		with time.now_ns as current_time
}

# Test: Required factors list
test_required_factors_list if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {},
	}
	count(result.required_factors) == 2
	"password" in result.required_factors
	"mfa" in result.required_factors
}

# Test: High sensitivity actions on high sensitivity tools
test_high_sensitivity_action_on_high_tool if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer", "mfa_verified": false},
		"action": "tool:delete",
		"tool": {"name": "high_tool", "sensitivity_level": "high"},
		"context": {},
	}
	not result.allow
	result.mfa_status.required
}
