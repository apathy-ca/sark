# SARK Home Allowlist Policy
# Controls LLM access based on device and user allowlists/blocklists
#
# Use case: Only allow specific devices or users to access LLM services

package sark.home.allowlist

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Deny (Allowlist Mode)
# =============================================================================

# In allowlist mode, default is deny unless explicitly allowed
default allow := false
default reason := ""

# =============================================================================
# Allow Rules
# =============================================================================

# Allow if device IP is in the allowlist
allow if {
    is_allowlist_mode
    device_in_allowlist
}

# Allow if device name is in the allowlist
allow if {
    is_allowlist_mode
    device_name_in_allowlist
}

# Allow if user group is in the allowlist
allow if {
    is_allowlist_mode
    user_group_in_allowlist
}

# Allow if MAC address is in the allowlist (when available)
allow if {
    is_allowlist_mode
    mac_in_allowlist
}

# =============================================================================
# Blocklist Mode (Alternative)
# =============================================================================

# In blocklist mode, allow by default unless explicitly blocked
allow if {
    is_blocklist_mode
    not device_in_blocklist
    not device_name_in_blocklist
    not user_group_in_blocklist
    not mac_in_blocklist
}

# =============================================================================
# Admin Override
# =============================================================================

# Admins always allowed regardless of allowlist/blocklist
allow if {
    input.user.user_group == "admin"
}

# Allow if device has admin flag
allow if {
    input.user.is_admin == true
}

# =============================================================================
# Mode Detection
# =============================================================================

# Determine if we're in allowlist or blocklist mode
is_allowlist_mode if {
    input.rules.list_mode == "allowlist"
}

is_allowlist_mode if {
    # Default to allowlist mode if not specified
    not input.rules.list_mode
}

is_blocklist_mode if {
    input.rules.list_mode == "blocklist"
}

# =============================================================================
# Allowlist Checks
# =============================================================================

# Check device IP against allowlist
device_in_allowlist if {
    input.user.device_ip in data.home.device_allowlist
}

device_in_allowlist if {
    input.user.device_ip in input.rules.device_allowlist
}

# Check device name against allowlist
device_name_in_allowlist if {
    input.user.device_name in data.home.device_name_allowlist
}

device_name_in_allowlist if {
    input.user.device_name in input.rules.device_name_allowlist
}

# Check user group against allowlist
user_group_in_allowlist if {
    input.user.user_group in data.home.user_group_allowlist
}

user_group_in_allowlist if {
    input.user.user_group in input.rules.user_group_allowlist
}

# Check MAC address against allowlist
mac_in_allowlist if {
    input.user.mac_address in data.home.mac_allowlist
}

mac_in_allowlist if {
    input.user.mac_address in input.rules.mac_allowlist
}

# =============================================================================
# Blocklist Checks
# =============================================================================

# Check device IP against blocklist
device_in_blocklist if {
    input.user.device_ip in data.home.device_blocklist
}

device_in_blocklist if {
    input.user.device_ip in input.rules.device_blocklist
}

# Check device name against blocklist
device_name_in_blocklist if {
    input.user.device_name in data.home.device_name_blocklist
}

device_name_in_blocklist if {
    input.user.device_name in input.rules.device_name_blocklist
}

# Check user group against blocklist
user_group_in_blocklist if {
    input.user.user_group in data.home.user_group_blocklist
}

user_group_in_blocklist if {
    input.user.user_group in input.rules.user_group_blocklist
}

# Check MAC address against blocklist
mac_in_blocklist if {
    input.user.mac_address in data.home.mac_blocklist
}

mac_in_blocklist if {
    input.user.mac_address in input.rules.mac_blocklist
}

# =============================================================================
# CIDR Range Matching (for IP ranges)
# =============================================================================

# Check if device IP falls within an allowed CIDR range
device_in_allowed_cidr if {
    some cidr in data.home.allowed_cidrs
    net.cidr_contains(cidr, input.user.device_ip)
}

device_in_allowed_cidr if {
    some cidr in input.rules.allowed_cidrs
    net.cidr_contains(cidr, input.user.device_ip)
}

# Allow if device is in an allowed CIDR range
allow if {
    is_allowlist_mode
    device_in_allowed_cidr
}

# Check if device IP falls within a blocked CIDR range
device_in_blocked_cidr if {
    some cidr in data.home.blocked_cidrs
    net.cidr_contains(cidr, input.user.device_ip)
}

device_in_blocked_cidr if {
    some cidr in input.rules.blocked_cidrs
    net.cidr_contains(cidr, input.user.device_ip)
}

# Deny if device is in a blocked CIDR range (even in allowlist mode)
allow := false if {
    device_in_blocked_cidr
}

# =============================================================================
# Endpoint Allowlist
# =============================================================================

# Check if the target endpoint is allowed
endpoint_allowed if {
    not data.home.allowed_endpoints
    not input.rules.allowed_endpoints
}

endpoint_allowed if {
    input.request.endpoint in data.home.allowed_endpoints
}

endpoint_allowed if {
    input.request.endpoint in input.rules.allowed_endpoints
}

# Deny if endpoint is not in the allowed list
allow := false if {
    data.home.allowed_endpoints
    not endpoint_allowed
}

allow := false if {
    input.rules.allowed_endpoints
    not endpoint_allowed
}

# =============================================================================
# Reason Messages
# =============================================================================

reason := sprintf("Device '%s' (%s) not in allowlist", [
    input.user.device_name,
    input.user.device_ip
]) if {
    is_allowlist_mode
    not device_in_allowlist
    not device_name_in_allowlist
    not device_in_allowed_cidr
    not user_group_in_allowlist
}

reason := sprintf("Device '%s' (%s) is in blocklist", [
    input.user.device_name,
    input.user.device_ip
]) if {
    is_blocklist_mode
    device_in_blocklist
}

reason := sprintf("Device '%s' (%s) is in blocklist", [
    input.user.device_name,
    input.user.device_ip
]) if {
    is_blocklist_mode
    device_name_in_blocklist
}

reason := sprintf("User group '%s' not in allowlist", [input.user.user_group]) if {
    is_allowlist_mode
    not user_group_in_allowlist
    not device_in_allowlist
    not device_name_in_allowlist
}

reason := sprintf("User group '%s' is in blocklist", [input.user.user_group]) if {
    is_blocklist_mode
    user_group_in_blocklist
}

reason := sprintf("Device IP in blocked CIDR range") if {
    device_in_blocked_cidr
}

reason := sprintf("Endpoint '%s' not in allowed endpoints list", [input.request.endpoint]) if {
    not endpoint_allowed
}

# =============================================================================
# Policy Decision Output
# =============================================================================

decision := {
    "allow": allow,
    "reason": reason,
    "policy": "allowlist",
    "severity": severity,
    "metadata": {
        "mode": list_mode,
        "device_ip": input.user.device_ip,
        "device_name": input.user.device_name,
        "user_group": input.user.user_group,
        "in_allowlist": in_any_allowlist,
        "in_blocklist": in_any_blocklist
    }
}

# Determine effective list mode
list_mode := "allowlist" if {
    is_allowlist_mode
}

list_mode := "blocklist" if {
    is_blocklist_mode
}

# Track if device is in any allowlist
in_any_allowlist := true if { device_in_allowlist }
in_any_allowlist := true if { device_name_in_allowlist }
in_any_allowlist := true if { user_group_in_allowlist }
in_any_allowlist := true if { mac_in_allowlist }
in_any_allowlist := true if { device_in_allowed_cidr }
in_any_allowlist := false if {
    not device_in_allowlist
    not device_name_in_allowlist
    not user_group_in_allowlist
    not mac_in_allowlist
    not device_in_allowed_cidr
}

# Track if device is in any blocklist
in_any_blocklist := true if { device_in_blocklist }
in_any_blocklist := true if { device_name_in_blocklist }
in_any_blocklist := true if { user_group_in_blocklist }
in_any_blocklist := true if { mac_in_blocklist }
in_any_blocklist := true if { device_in_blocked_cidr }
in_any_blocklist := false if {
    not device_in_blocklist
    not device_name_in_blocklist
    not user_group_in_blocklist
    not mac_in_blocklist
    not device_in_blocked_cidr
}

severity := "info" if {
    allow
}

severity := "warning" if {
    not allow
    is_allowlist_mode
}

severity := "high" if {
    not allow
    is_blocklist_mode
}
