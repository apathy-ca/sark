# Tests for SARK Home Bedtime Policy
package sark.home.bedtime_test

import data.sark.home.bedtime

# =============================================================================
# Test: Allow during daytime hours
# =============================================================================

test_allow_during_daytime if {
    bedtime.allow with input as {
        "context": {"hour": 14},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

test_allow_morning_after_bedtime_ends if {
    bedtime.allow with input as {
        "context": {"hour": 8},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

test_allow_just_after_bedtime_ends if {
    bedtime.allow with input as {
        "context": {"hour": 7},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

# =============================================================================
# Test: Deny during bedtime hours (overnight window)
# =============================================================================

test_deny_during_late_night if {
    not bedtime.allow with input as {
        "context": {"hour": 23},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

test_deny_during_early_morning if {
    not bedtime.allow with input as {
        "context": {"hour": 5},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

test_deny_at_bedtime_start if {
    not bedtime.allow with input as {
        "context": {"hour": 21},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

# =============================================================================
# Test: Same-day bedtime window (e.g., afternoon quiet time)
# =============================================================================

test_deny_during_same_day_window if {
    not bedtime.allow with input as {
        "context": {"hour": 14},
        "rules": {"bedtime_start_hour": 13, "bedtime_end_hour": 15},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

test_allow_before_same_day_window if {
    bedtime.allow with input as {
        "context": {"hour": 12},
        "rules": {"bedtime_start_hour": 13, "bedtime_end_hour": 15},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

test_allow_after_same_day_window if {
    bedtime.allow with input as {
        "context": {"hour": 16},
        "rules": {"bedtime_start_hour": 13, "bedtime_end_hour": 15},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

# =============================================================================
# Test: User group exemptions
# =============================================================================

test_allow_admin_during_bedtime if {
    bedtime.allow with input as {
        "context": {"hour": 23},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "admin-pc", "user_group": "admin"}
    }
}

test_allow_parent_during_bedtime if {
    bedtime.allow with input as {
        "context": {"hour": 23},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "parent-phone", "user_group": "parent"}
    }
}

test_allow_adult_during_bedtime if {
    bedtime.allow with input as {
        "context": {"hour": 2},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "adult-laptop", "user_group": "adult"}
    }
}

# =============================================================================
# Test: Device exemptions
# =============================================================================

test_allow_exempt_device_during_bedtime if {
    bedtime.allow with input as {
        "context": {"hour": 23},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.50", "device_name": "exempt-device", "user_group": "child"}
    }
        with data.home.bedtime_exempt_devices as ["192.168.1.50"]
}

test_allow_exempt_device_by_name if {
    bedtime.allow with input as {
        "context": {"hour": 23},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "parents-phone", "user_group": "child"}
    }
        with data.home.bedtime_exempt_devices as ["parents-phone"]
}

# =============================================================================
# Test: Reason messages
# =============================================================================

test_reason_message_during_bedtime if {
    bedtime.reason == "Bedtime active (21:00 - 07:00). LLM access restricted." with input as {
        "context": {"hour": 23, "day_of_week": "monday"},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
}

# =============================================================================
# Test: Decision output structure
# =============================================================================

test_decision_structure_allow if {
    decision := bedtime.decision with input as {
        "context": {"hour": 14},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
    decision.allow == true
    decision.policy == "bedtime"
    decision.severity == "info"
}

test_decision_structure_deny if {
    decision := bedtime.decision with input as {
        "context": {"hour": 23},
        "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7},
        "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"}
    }
    decision.allow == false
    decision.policy == "bedtime"
    decision.severity == "warning"
}
