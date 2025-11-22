package sark.policies.ip_filtering

import rego.v1

# ============================================================================
# IP FILTERING POLICY
# ============================================================================
#
# Enforces IP-based access control using:
# - Global IP allowlist (only these IPs allowed)
# - Global IP blocklist (these IPs explicitly denied)
# - Role-specific IP restrictions
# - Sensitivity-based IP requirements
# - CIDR range support
# - Geographic restrictions
#
# Use cases:
# - Corporate network restrictions
# - VPN-only access for critical tools
# - Block known malicious IPs
# - Geo-fencing for compliance
# - Development vs production IP separation
#
# ============================================================================

# Default deny if IP checks fail
default allow := false

# Default configuration
default_require_ip_check := true

default_allow_private_ips := false

# ============================================================================
# MAIN DECISION
# ============================================================================

# Allow if IP filtering passes
allow if {
	decision.allow
}

# Main decision structure
decision := {
	"allow": allow_decision,
	"reason": reason,
	"violations": violations_list,
	"client_ip": client_ip,
	"ip_info": ip_classification,
}

# ============================================================================
# IP-BASED ALLOW LOGIC
# ============================================================================

# Allow if IP filtering is disabled (for testing)
allow_decision if {
	input.policy_config.ip_filtering_enabled == false
}

# Allow if no IP provided but not required
allow_decision if {
	not client_ip
	not requires_ip_check
}

# Allow if IP is on allowlist and not on blocklist
allow_decision if {
	client_ip
	is_ip_allowed
	not is_ip_blocked
	count(violations) == 0
}

# ============================================================================
# CLIENT IP EXTRACTION
# ============================================================================

# Extract client IP from input
client_ip := ip if {
	ip := input.context.client_ip
	ip != ""
}

client_ip := ip if {
	not input.context.client_ip
	ip := input.user.ip_address
	ip != ""
}

client_ip := ip if {
	# Support X-Forwarded-For header
	not input.context.client_ip
	not input.user.ip_address
	ip := input.context.request_headers["x-forwarded-for"]
	ip != ""
}

# ============================================================================
# IP CLASSIFICATION
# ============================================================================

ip_classification := {
	"is_private": is_private_ip,
	"is_allowed": is_ip_allowed,
	"is_blocked": is_ip_blocked,
	"matches_allowlist": allowlist_matches,
	"matches_blocklist": blocklist_matches,
	"requires_vpn": requires_vpn,
}

# Check if IP is private (RFC 1918)
is_private_ip if {
	client_ip
	# 10.0.0.0/8
	startswith(client_ip, "10.")
}

is_private_ip if {
	client_ip
	# 172.16.0.0/12
	ip_in_range(client_ip, "172.16.0.0", "172.31.255.255")
}

is_private_ip if {
	client_ip
	# 192.168.0.0/16
	startswith(client_ip, "192.168.")
}

is_private_ip if {
	client_ip
	# Localhost
	client_ip == "127.0.0.1"
}

is_private_ip if {
	client_ip
	# IPv6 localhost
	client_ip == "::1"
}

# ============================================================================
# ALLOWLIST CHECKING
# ============================================================================

# IP is allowed if on allowlist
is_ip_allowed if {
	count(get_allowlist) == 0 # No allowlist means all allowed
}

is_ip_allowed if {
	count(get_allowlist) > 0
	allowlist_entry := get_allowlist[_]
	ip_matches_entry(client_ip, allowlist_entry)
}

is_ip_allowed if {
	# Allow private IPs if configured
	is_private_ip
	allow_private_ips
}

# Get allowlist entries
allowlist_matches := [entry |
	allowlist_entry := get_allowlist[_]
	ip_matches_entry(client_ip, allowlist_entry)
	entry := allowlist_entry
]

get_allowlist := list if {
	list := input.policy_config.ip_allowlist
	list != null
}

get_allowlist := [] if {
	not input.policy_config.ip_allowlist
}

allow_private_ips if {
	input.policy_config.allow_private_ips == true
}

allow_private_ips if {
	not input.policy_config.allow_private_ips
	default_allow_private_ips
}

# ============================================================================
# BLOCKLIST CHECKING
# ============================================================================

# IP is blocked if on blocklist
is_ip_blocked if {
	blocklist_entry := get_blocklist[_]
	ip_matches_entry(client_ip, blocklist_entry)
}

# Get blocklist entries
blocklist_matches := [entry |
	blocklist_entry := get_blocklist[_]
	ip_matches_entry(client_ip, blocklist_entry)
	entry := blocklist_entry
]

get_blocklist := list if {
	list := input.policy_config.ip_blocklist
	list != null
}

get_blocklist := [] if {
	not input.policy_config.ip_blocklist
}

# ============================================================================
# IP MATCHING
# ============================================================================

# Check if IP matches an allowlist/blocklist entry
ip_matches_entry(ip, entry) if {
	# Exact match
	ip == entry
}

ip_matches_entry(ip, entry) if {
	# CIDR match
	contains(entry, "/")
	net.cidr_contains(entry, ip)
}

ip_matches_entry(ip, entry) if {
	# Wildcard match (e.g., "192.168.*")
	contains(entry, "*")
	ip_matches_wildcard(ip, entry)
}

# Simple wildcard matching
ip_matches_wildcard(ip, pattern) if {
	pattern_parts := split(pattern, ".")
	ip_parts := split(ip, ".")
	count(pattern_parts) == count(ip_parts)
	parts_match(ip_parts, pattern_parts)
}

# Check if all parts match
parts_match(ip_parts, pattern_parts) if {
	every i, pattern_part in pattern_parts {
		pattern_part == "*"
	}
}

parts_match(ip_parts, pattern_parts) if {
	every i, pattern_part in pattern_parts {
		pattern_part == ip_parts[i]
	}
}

parts_match(ip_parts, pattern_parts) if {
	every i, pattern_part in pattern_parts {
		(pattern_part == "*") or (pattern_part == ip_parts[i])
	}
}

# ============================================================================
# IP RANGE CHECKING
# ============================================================================

# Check if IP is in a range (for private IP detection)
ip_in_range(ip, start, end) if {
	ip_to_int(ip) >= ip_to_int(start)
	ip_to_int(ip) <= ip_to_int(end)
}

# Convert IPv4 address to integer for comparison
ip_to_int(ip) := num if {
	parts := split(ip, ".")
	count(parts) == 4
	num := (to_number(parts[0]) * 16777216) + (to_number(parts[1]) * 65536) + (to_number(parts[2]) * 256) + to_number(parts[3])
}

# ============================================================================
# ROLE-BASED IP RESTRICTIONS
# ============================================================================

# Check if role requires specific IP restrictions
requires_ip_check if {
	input.user.role != "service"
	default_require_ip_check
}

requires_ip_check if {
	role_ip_requirements[input.user.role] != null
}

role_ip_requirements := {
	"admin": {
		"require_vpn": true,
		"allowed_ranges": ["10.0.0.0/8", "192.168.0.0/16"],
	},
	"developer": {
		"require_vpn": false,
		"allowed_ranges": null,
	},
}

# ============================================================================
# SENSITIVITY-BASED IP RESTRICTIONS
# ============================================================================

# Critical tools require VPN/corporate network
requires_vpn if {
	input.tool.sensitivity_level == "critical"
}

requires_vpn if {
	input.tool.sensitivity_level == "high"
	input.action in ["tool:invoke", "server:delete"]
}

# ============================================================================
# VIOLATION DETECTION
# ============================================================================

violations contains violation if {
	# IP required but not provided
	requires_ip_check
	not client_ip
	violation := {
		"type": "missing_ip",
		"reason": "Client IP address required but not provided",
	}
}

violations contains violation if {
	# IP on blocklist
	client_ip
	is_ip_blocked
	violation := {
		"type": "ip_blocked",
		"reason": sprintf("IP address %s is on blocklist", [client_ip]),
		"blocked_by": blocklist_matches,
	}
}

violations contains violation if {
	# IP not on allowlist
	client_ip
	not is_ip_allowed
	violation := {
		"type": "ip_not_allowed",
		"reason": sprintf("IP address %s is not on allowlist", [client_ip]),
		"allowlist_size": count(get_allowlist),
	}
}

violations contains violation if {
	# VPN required but not connected
	requires_vpn
	client_ip
	not is_private_ip
	not is_vpn_ip
	violation := {
		"type": "vpn_required",
		"reason": "VPN connection required for this operation",
		"client_ip": client_ip,
	}
}

violations contains violation if {
	# Role-specific IP restriction violated
	role_requirement := role_ip_requirements[input.user.role]
	role_requirement != null
	role_requirement.allowed_ranges != null
	client_ip
	not ip_in_role_range
	violation := {
		"type": "role_ip_restriction",
		"reason": sprintf("IP %s not in allowed ranges for role %s", [client_ip, input.user.role]),
		"allowed_ranges": role_requirement.allowed_ranges,
	}
}

# Check if IP is in role-specific allowed ranges
ip_in_role_range if {
	role_requirement := role_ip_requirements[input.user.role]
	role_requirement.allowed_ranges != null
	range := role_requirement.allowed_ranges[_]
	ip_matches_entry(client_ip, range)
}

# Check if IP is a VPN IP (corporate network)
is_vpn_ip if {
	is_private_ip
}

is_vpn_ip if {
	vpn_range := input.policy_config.vpn_ip_ranges[_]
	ip_matches_entry(client_ip, vpn_range)
}

# ============================================================================
# REASON GENERATION
# ============================================================================

reason := msg if {
	allow_decision
	not requires_ip_check
	msg := "IP filtering not required"
}

reason := msg if {
	allow_decision
	count(violations) == 0
	client_ip
	msg := sprintf("IP %s allowed (allowlist: %d entries, blocklist: %d entries)", [
		client_ip,
		count(get_allowlist),
		count(get_blocklist),
	])
}

reason := msg if {
	not allow_decision
	count(violations) > 0
	violation_reasons := [v.reason | v := violations[_]]
	msg := sprintf("IP filtering violations: %s", [concat("; ", violation_reasons)])
}

reason := msg if {
	not allow_decision
	is_ip_blocked
	msg := sprintf("IP address %s is blocked", [client_ip])
}

violations_list := [violation |
	violation := violations[_]
]

# ============================================================================
# GEOGRAPHIC RESTRICTIONS (OPTIONAL)
# ============================================================================

# Check if geographic restrictions apply
geo_restriction_applies if {
	input.policy_config.geo_restrictions_enabled == true
	input.tool.sensitivity_level == "critical"
}

violations contains violation if {
	geo_restriction_applies
	country := input.context.geo_country
	country != ""
	not country in get_allowed_countries
	violation := {
		"type": "geo_restriction",
		"reason": sprintf("Access from country %s not allowed", [country]),
		"country": country,
		"allowed_countries": get_allowed_countries,
	}
}

get_allowed_countries := countries if {
	countries := input.policy_config.allowed_countries
	countries != null
}

get_allowed_countries := [] if {
	not input.policy_config.allowed_countries
}

# ============================================================================
# AUDIT LOGGING
# ============================================================================

# Log suspicious IP access attempts
audit_log := {
	"ip_blocked": is_ip_blocked,
	"ip_allowed": is_ip_allowed,
	"client_ip": client_ip,
	"blocklist_matches": count(blocklist_matches),
	"is_private": is_private_ip,
	"requires_vpn": requires_vpn,
	"violations": count(violations),
}
