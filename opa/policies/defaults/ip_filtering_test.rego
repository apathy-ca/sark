package sark.policies.ip_filtering

import rego.v1

# ============================================================================
# IP FILTERING POLICY TESTS
# ============================================================================

# Test: IP filtering disabled allows all
test_ip_filtering_disabled if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "1.2.3.4"},
		"policy_config": {"ip_filtering_enabled": false},
	}
	result.allow
}

# Test: IP on allowlist is allowed
test_ip_on_allowlist_allowed if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "192.168.1.100"},
		"policy_config": {
			"ip_allowlist": ["192.168.1.100", "10.0.0.0/8"],
			"ip_blocklist": [],
		},
	}
	result.allow
	result.reason != ""
}

# Test: IP not on allowlist is blocked
test_ip_not_on_allowlist_blocked if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "1.2.3.4"},
		"policy_config": {
			"ip_allowlist": ["192.168.1.0/24"],
			"ip_blocklist": [],
		},
	}
	not result.allow
	some violation in result.violations
	violation.type == "ip_not_allowed"
}

# Test: IP on blocklist is blocked even if on allowlist
test_ip_on_blocklist_blocked if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "192.168.1.100"},
		"policy_config": {
			"ip_allowlist": ["192.168.1.0/24"],
			"ip_blocklist": ["192.168.1.100"],
		},
	}
	not result.allow
	some violation in result.violations
	violation.type == "ip_blocked"
}

# Test: CIDR range matching
test_cidr_range_matching if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "10.0.5.123"},
		"policy_config": {
			"ip_allowlist": ["10.0.0.0/8"],
			"ip_blocklist": [],
		},
	}
	result.allow
	count(result.ip_info.matches_allowlist) > 0
}

# Test: Wildcard matching
test_wildcard_matching if {
	ip_matches_wildcard("192.168.1.100", "192.168.1.*")
	ip_matches_wildcard("192.168.2.50", "192.168.*")
	not ip_matches_wildcard("10.0.0.1", "192.168.*")
}

# Test: Private IP detection
test_private_ip_detection if {
	is_private_ip with input as {"context": {"client_ip": "10.0.0.1"}}
	is_private_ip with input as {"context": {"client_ip": "192.168.1.1"}}
	is_private_ip with input as {"context": {"client_ip": "172.16.0.1"}}
	is_private_ip with input as {"context": {"client_ip": "127.0.0.1"}}
}

test_not_private_ip if {
	not is_private_ip with input as {"context": {"client_ip": "8.8.8.8"}}
	not is_private_ip with input as {"context": {"client_ip": "1.2.3.4"}}
}

# Test: Private IPs allowed when configured
test_private_ips_allowed_when_configured if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "192.168.1.100"},
		"policy_config": {
			"allow_private_ips": true,
			"ip_allowlist": [],
			"ip_blocklist": [],
		},
	}
	result.allow
}

# Test: VPN requirement for critical tools
test_vpn_required_for_critical if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {"client_ip": "1.2.3.4"}, # Public IP
		"policy_config": {
			"allow_private_ips": true,
			"ip_allowlist": ["0.0.0.0/0"], # Allow all
			"ip_blocklist": [],
		},
	}
	not result.allow
	some violation in result.violations
	violation.type == "vpn_required"
}

# Test: VPN requirement satisfied with private IP
test_vpn_requirement_satisfied_private_ip if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {"client_ip": "10.0.5.100"},
		"policy_config": {
			"allow_private_ips": true,
			"ip_allowlist": [],
			"ip_blocklist": [],
		},
	}
	result.allow
}

# Test: Role-specific IP restrictions
test_role_ip_restrictions if {
	result := decision with input as {
		"user": {"id": "admin1", "role": "admin"},
		"action": "user:create",
		"tool": {"name": "admin_tool", "sensitivity_level": "high"},
		"context": {"client_ip": "1.2.3.4"}, # Public IP
		"policy_config": {
			"ip_allowlist": ["0.0.0.0/0"],
			"ip_blocklist": [],
		},
	}
	not result.allow
	some violation in result.violations
	violation.type == "role_ip_restriction"
}

# Test: No IP required for service accounts
test_service_account_no_ip_required if {
	result := decision with input as {
		"user": {"id": "service1", "role": "service"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {},
		"policy_config": {"ip_filtering_enabled": false},
	}
	result.allow
}

# Test: Geographic restrictions
test_geo_restrictions if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {
			"client_ip": "1.2.3.4",
			"geo_country": "CN",
		},
		"policy_config": {
			"geo_restrictions_enabled": true,
			"allowed_countries": ["US", "CA", "GB"],
			"allow_private_ips": true,
			"ip_allowlist": ["0.0.0.0/0"],
			"ip_blocklist": [],
		},
	}
	not result.allow
	some violation in result.violations
	violation.type == "geo_restriction"
}

# Test: Geographic restrictions allowed country
test_geo_restrictions_allowed_country if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "critical_tool", "sensitivity_level": "critical"},
		"context": {
			"client_ip": "10.0.0.1",
			"geo_country": "US",
		},
		"policy_config": {
			"geo_restrictions_enabled": true,
			"allowed_countries": ["US", "CA", "GB"],
			"allow_private_ips": true,
			"ip_allowlist": [],
			"ip_blocklist": [],
		},
	}
	result.allow
}

# Test: IP to integer conversion
test_ip_to_int if {
	ip_to_int("192.168.1.1") == 3232235777
	ip_to_int("10.0.0.1") == 167772161
	ip_to_int("172.16.0.1") == 2886729729
}

# Test: IP range checking
test_ip_in_range if {
	ip_in_range("172.16.0.1", "172.16.0.0", "172.31.255.255")
	ip_in_range("172.20.50.100", "172.16.0.0", "172.31.255.255")
	not ip_in_range("172.32.0.1", "172.16.0.0", "172.31.255.255")
}

# Test: Multiple allowlist entries
test_multiple_allowlist_entries if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "203.0.113.50"},
		"policy_config": {
			"ip_allowlist": ["192.168.0.0/16", "10.0.0.0/8", "203.0.113.0/24"],
			"ip_blocklist": [],
		},
	}
	result.allow
}

# Test: Empty allowlist allows all
test_empty_allowlist_allows_all if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "low"},
		"context": {"client_ip": "1.2.3.4"},
		"policy_config": {
			"ip_allowlist": [],
			"ip_blocklist": [],
		},
	}
	result.allow
}

# Test: Blocklist takes precedence
test_blocklist_precedence if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "tool:invoke",
		"tool": {"name": "test_tool", "sensitivity_level": "medium"},
		"context": {"client_ip": "10.0.0.100"},
		"policy_config": {
			"ip_allowlist": ["10.0.0.0/8"],
			"ip_blocklist": ["10.0.0.100"],
		},
	}
	not result.allow
	result.ip_info.is_blocked
}

# Test: X-Forwarded-For header support
test_x_forwarded_for_header if {
	client_ip == "203.0.113.50" with input as {"context": {"request_headers": {"x-forwarded-for": "203.0.113.50"}}}
}

# Test: High sensitivity action requires VPN
test_high_sensitivity_action_vpn if {
	result := decision with input as {
		"user": {"id": "dev1", "role": "developer"},
		"action": "server:delete",
		"tool": {"name": "server_tool", "sensitivity_level": "high"},
		"context": {"client_ip": "1.2.3.4"},
		"policy_config": {
			"ip_allowlist": ["0.0.0.0/0"],
			"ip_blocklist": [],
		},
	}
	not result.allow
	some violation in result.violations
	violation.type == "vpn_required"
}
