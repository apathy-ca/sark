# Tests for SARK Home Allowlist Policy
package sark.home.allowlist_test

import data.sark.home.allowlist

# =============================================================================
# Test: Allowlist Mode - Device IP
# =============================================================================

test_allow_device_in_allowlist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["192.168.1.100", "192.168.1.101"]
}

test_deny_device_not_in_allowlist if {
    not allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "unknown-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["192.168.1.100", "192.168.1.101"]
}

# =============================================================================
# Test: Allowlist Mode - Device Name
# =============================================================================

test_allow_device_name_in_allowlist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "approved-tablet", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_name_allowlist as ["approved-tablet", "family-pc"]
}

test_deny_device_name_not_in_allowlist if {
    not allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "random-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_name_allowlist as ["approved-tablet", "family-pc"]
}

# =============================================================================
# Test: Allowlist Mode - User Group
# =============================================================================

test_allow_user_group_in_allowlist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "any-device", "user_group": "family"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.user_group_allowlist as ["family", "trusted"]
}

test_deny_user_group_not_in_allowlist if {
    not allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "any-device", "user_group": "guest"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.user_group_allowlist as ["family", "trusted"]
}

# =============================================================================
# Test: Blocklist Mode
# =============================================================================

test_allow_device_not_in_blocklist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.100", "device_name": "good-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "blocklist"}
    }
        with data.home.device_blocklist as ["192.168.1.50", "192.168.1.51"]
}

test_deny_device_in_blocklist if {
    not allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.50", "device_name": "blocked-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "blocklist"}
    }
        with data.home.device_blocklist as ["192.168.1.50", "192.168.1.51"]
}

test_deny_device_name_in_blocklist if {
    not allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.100", "device_name": "banned-phone", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "blocklist"}
    }
        with data.home.device_name_blocklist as ["banned-phone", "old-tablet"]
}

# =============================================================================
# Test: Admin Override
# =============================================================================

test_allow_admin_not_in_allowlist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "admin-laptop", "user_group": "admin"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["192.168.1.100"]
}

test_allow_admin_in_blocklist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.50", "device_name": "admin-laptop", "user_group": "admin"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "blocklist"}
    }
        with data.home.device_blocklist as ["192.168.1.50"]
}

test_allow_is_admin_flag if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "any-device", "user_group": "unknown", "is_admin": true},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["192.168.1.100"]
}

# =============================================================================
# Test: CIDR Range Matching
# =============================================================================

test_allow_device_in_allowed_cidr if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.150", "device_name": "lan-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.allowed_cidrs as ["192.168.1.0/24"]
}

test_deny_device_outside_allowed_cidr if {
    not allowlist.allow with input as {
        "user": {"device_ip": "10.0.0.50", "device_name": "external-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.allowed_cidrs as ["192.168.1.0/24"]
}

test_deny_device_in_blocked_cidr if {
    not allowlist.allow with input as {
        "user": {"device_ip": "10.0.0.50", "device_name": "blocked-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["10.0.0.50"]
        with data.home.blocked_cidrs as ["10.0.0.0/8"]
}

# =============================================================================
# Test: Endpoint Allowlist
# =============================================================================

test_allow_endpoint_in_allowlist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.100", "device_name": "device", "user_group": "admin"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {}
    }
        with data.home.allowed_endpoints as ["api.openai.com", "api.anthropic.com"]
}

test_deny_endpoint_not_in_allowlist if {
    not allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.100", "device_name": "device", "user_group": "admin"},
        "request": {"endpoint": "api.unknown-llm.com"},
        "rules": {}
    }
        with data.home.allowed_endpoints as ["api.openai.com", "api.anthropic.com"]
}

# =============================================================================
# Test: Rules-based allowlist (not data-based)
# =============================================================================

test_allow_device_in_rules_allowlist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.100", "device_name": "device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist", "device_allowlist": ["192.168.1.100"]}
    }
}

test_allow_device_name_in_rules_allowlist if {
    allowlist.allow with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "my-device", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist", "device_name_allowlist": ["my-device"]}
    }
}

# =============================================================================
# Test: Default mode (allowlist)
# =============================================================================

test_default_mode_is_allowlist if {
    allowlist.is_allowlist_mode with input as {
        "user": {"device_ip": "192.168.1.100"},
        "rules": {}
    }
}

# =============================================================================
# Test: Reason messages
# =============================================================================

test_reason_device_not_in_allowlist if {
    contains(allowlist.reason, "not in allowlist") with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "unknown", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["192.168.1.100"]
}

test_reason_device_in_blocklist if {
    contains(allowlist.reason, "in blocklist") with input as {
        "user": {"device_ip": "192.168.1.50", "device_name": "blocked", "user_group": "child"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "blocklist"}
    }
        with data.home.device_blocklist as ["192.168.1.50"]
}

# =============================================================================
# Test: Decision output structure
# =============================================================================

test_decision_structure_allow if {
    decision := allowlist.decision with input as {
        "user": {"device_ip": "192.168.1.100", "device_name": "approved", "user_group": "family"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["192.168.1.100"]
    decision.allow == true
    decision.policy == "allowlist"
    decision.metadata.mode == "allowlist"
}

test_decision_structure_deny if {
    decision := allowlist.decision with input as {
        "user": {"device_ip": "192.168.1.200", "device_name": "unknown", "user_group": "guest"},
        "request": {"endpoint": "api.openai.com"},
        "rules": {"list_mode": "allowlist"}
    }
        with data.home.device_allowlist as ["192.168.1.100"]
    decision.allow == false
    decision.policy == "allowlist"
    decision.severity == "warning"
}
