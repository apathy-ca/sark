# Tests for SARK Home Default Policy
package sark.home.default_test

import data.sark.home.default

# =============================================================================
# Test: Default allow behavior
# =============================================================================

test_default_allows_all if {
    default.allow with input as {
        "context": {"hour": 23, "day_of_week": "monday", "tokens_today": 100, "cost_today_usd": 0.50},
        "user": {"device_ip": "192.168.1.100", "device_name": "any-device", "user_group": "any-group"},
        "request": {"endpoint": "api.openai.com", "method": "POST", "path": "/v1/chat", "tokens_estimated": 500}
    }
}

test_allows_late_night if {
    default.allow with input as {
        "context": {"hour": 3},
        "user": {"device_ip": "192.168.1.100"},
        "request": {"endpoint": "api.openai.com"}
    }
}

test_allows_high_usage if {
    default.allow with input as {
        "context": {"cost_today_usd": 100.00, "tokens_today": 1000000},
        "user": {"device_ip": "192.168.1.100"},
        "request": {"endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Mode configuration
# =============================================================================

test_mode_observe_default if {
    default.mode == "observe" with input as {
        "rules": {},
        "context": {},
        "user": {},
        "request": {}
    }
}

test_mode_observe_explicit if {
    default.mode == "observe" with input as {
        "rules": {"mode": "observe"},
        "context": {},
        "user": {},
        "request": {}
    }
}

test_mode_advisory if {
    default.mode == "advisory" with input as {
        "rules": {"mode": "advisory"},
        "context": {},
        "user": {},
        "request": {}
    }
}

test_mode_enforce if {
    default.mode == "enforce" with input as {
        "rules": {"mode": "enforce"},
        "context": {},
        "user": {},
        "request": {}
    }
}

test_mode_invalid_defaults_to_observe if {
    default.mode == "observe" with input as {
        "rules": {"mode": "invalid"},
        "context": {},
        "user": {},
        "request": {}
    }
}

# =============================================================================
# Test: Policy suggestions
# =============================================================================

test_suggests_bedtime_late_night if {
    suggestions := default.suggested_policies with input as {
        "context": {"hour": 23},
        "user": {},
        "request": {"prompt_preview": "hello"}
    }
    "bedtime" in suggestions
}

test_suggests_bedtime_early_morning if {
    suggestions := default.suggested_policies with input as {
        "context": {"hour": 5},
        "user": {},
        "request": {"prompt_preview": "hello"}
    }
    "bedtime" in suggestions
}

test_suggests_cost_limit_high_tokens if {
    suggestions := default.suggested_policies with input as {
        "context": {"hour": 12, "tokens_today": 8000, "cost_today_usd": 0.50},
        "user": {},
        "request": {"prompt_preview": "hello"}
    }
    "cost_limit" in suggestions
}

test_suggests_cost_limit_high_cost if {
    suggestions := default.suggested_policies with input as {
        "context": {"hour": 12, "tokens_today": 100, "cost_today_usd": 2.00},
        "user": {},
        "request": {"prompt_preview": "hello"}
    }
    "cost_limit" in suggestions
}

test_suggests_parental_for_children if {
    suggestions := default.suggested_policies with input as {
        "context": {"hour": 12},
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "hello"}
    }
    "parental" in suggestions
}

test_suggests_privacy_with_email_char if {
    suggestions := default.suggested_policies with input as {
        "context": {"hour": 12},
        "user": {},
        "request": {"prompt_preview": "email me at test@example.com"}
    }
    "privacy" in suggestions
}

# =============================================================================
# Test: Soft limit warnings
# =============================================================================

test_warning_high_daily_usage if {
    warnings := default.soft_limit_warnings with input as {
        "context": {"cost_today_usd": 3.00, "hour": 12},
        "user": {},
        "request": {}
    }
    count(warnings) > 0
}

test_warning_late_night_usage if {
    warnings := default.soft_limit_warnings with input as {
        "context": {"cost_today_usd": 0.50, "hour": 23},
        "user": {},
        "request": {}
    }
    count(warnings) > 0
}

test_warning_early_morning_usage if {
    warnings := default.soft_limit_warnings with input as {
        "context": {"cost_today_usd": 0.50, "hour": 3},
        "user": {},
        "request": {}
    }
    count(warnings) > 0
}

test_warning_many_requests if {
    warnings := default.soft_limit_warnings with input as {
        "context": {"cost_today_usd": 0.50, "hour": 12, "device_requests_today": 150},
        "user": {},
        "request": {}
    }
    count(warnings) > 0
}

test_no_warnings_normal_usage if {
    warnings := default.soft_limit_warnings with input as {
        "context": {"cost_today_usd": 0.50, "hour": 12, "device_requests_today": 10},
        "user": {},
        "request": {}
    }
    count(warnings) == 0
}

# =============================================================================
# Test: Observation data
# =============================================================================

test_observation_captures_device_info if {
    obs := default.observation with input as {
        "context": {"timestamp": "2024-01-15T14:00:00Z", "hour": 14, "day_of_week": "monday"},
        "user": {"device_ip": "192.168.1.100", "device_name": "test-device", "user_group": "family"},
        "request": {"endpoint": "api.openai.com", "method": "POST", "path": "/v1/chat", "tokens_estimated": 500}
    }
    obs.device_ip == "192.168.1.100"
    obs.device_name == "test-device"
    obs.endpoint == "api.openai.com"
}

# =============================================================================
# Test: Usage analytics
# =============================================================================

test_peak_hour_detection if {
    default.is_peak_hour with input as {
        "context": {"hour": 18},
        "user": {},
        "request": {}
    }
}

test_not_peak_hour_morning if {
    not default.is_peak_hour with input as {
        "context": {"hour": 10},
        "user": {},
        "request": {}
    }
}

test_high_usage_device_detection if {
    default.is_high_usage_device with input as {
        "context": {"device_requests_today": 75},
        "user": {},
        "request": {}
    }
}

test_not_high_usage_device if {
    not default.is_high_usage_device with input as {
        "context": {"device_requests_today": 20},
        "user": {},
        "request": {}
    }
}

# =============================================================================
# Test: Reason messages
# =============================================================================

test_reason_observe_mode if {
    default.reason == "Allowed (observe mode) - monitoring only" with input as {
        "rules": {"mode": "observe"},
        "context": {"cost_today_usd": 0.50, "hour": 12},
        "user": {},
        "request": {}
    }
}

test_reason_advisory_mode_no_warnings if {
    default.reason == "Allowed (advisory mode) - no warnings" with input as {
        "rules": {"mode": "advisory"},
        "context": {"cost_today_usd": 0.50, "hour": 12, "device_requests_today": 10},
        "user": {},
        "request": {}
    }
}

test_reason_enforce_mode if {
    default.reason == "Allowed (enforce mode) - no policy violations" with input as {
        "rules": {"mode": "enforce"},
        "context": {"cost_today_usd": 0.50, "hour": 12},
        "user": {},
        "request": {}
    }
}

# =============================================================================
# Test: Decision output structure
# =============================================================================

test_decision_structure if {
    decision := default.decision with input as {
        "rules": {"mode": "observe"},
        "context": {"hour": 14, "tokens_today": 100, "cost_today_usd": 0.50},
        "user": {"device_ip": "192.168.1.100", "device_name": "test", "user_group": "family"},
        "request": {"endpoint": "api.openai.com", "prompt_preview": "hello"}
    }
    decision.allow == true
    decision.policy == "default"
    decision.mode == "observe"
    decision.severity == "info"
    decision.metadata.observation
    decision.metadata.suggested_policies
}

# =============================================================================
# Test: First run tips
# =============================================================================

test_include_tips_first_request if {
    default.include_tips with input as {
        "context": {"device_requests_today": 0},
        "user": {},
        "request": {}
    }
}

test_include_tips_explicit_first if {
    default.include_tips with input as {
        "context": {"device_requests_today": 10, "first_request": true},
        "user": {},
        "request": {}
    }
}

test_no_tips_after_first_request if {
    not default.include_tips with input as {
        "context": {"device_requests_today": 5},
        "user": {},
        "request": {}
    }
}
