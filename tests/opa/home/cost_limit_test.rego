# Tests for SARK Home Cost Limit Policy
package sark.home.cost_limit_test

import data.sark.home.cost_limit

# =============================================================================
# Test: Allow when under daily cost limit
# =============================================================================

test_allow_under_daily_cost_limit if {
    cost_limit.allow with input as {
        "context": {"cost_today_usd": 2.50},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_allow_at_zero_cost if {
    cost_limit.allow with input as {
        "context": {"cost_today_usd": 0.00},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_allow_just_under_limit if {
    cost_limit.allow with input as {
        "context": {"cost_today_usd": 4.99},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

# =============================================================================
# Test: Deny when over daily cost limit
# =============================================================================

test_deny_over_daily_cost_limit if {
    not cost_limit.allow with input as {
        "context": {"cost_today_usd": 5.50},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_deny_at_exact_limit if {
    not cost_limit.allow with input as {
        "context": {"cost_today_usd": 5.00},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

# =============================================================================
# Test: Monthly cost limits
# =============================================================================

test_allow_under_monthly_limit if {
    cost_limit.allow with input as {
        "context": {"cost_today_usd": 2.00, "cost_month_usd": 50.00},
        "rules": {"daily_cost_limit_usd": 5.00, "monthly_cost_limit_usd": 100.00},
        "request": {}
    }
}

test_deny_over_monthly_limit if {
    not cost_limit.allow with input as {
        "context": {"cost_today_usd": 2.00, "cost_month_usd": 105.00},
        "rules": {"daily_cost_limit_usd": 5.00, "monthly_cost_limit_usd": 100.00},
        "request": {}
    }
}

# =============================================================================
# Test: Request exceeds remaining budget
# =============================================================================

test_deny_request_exceeds_budget if {
    not cost_limit.allow with input as {
        "context": {"cost_today_usd": 4.50},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {"estimated_cost_usd": 1.00}
    }
}

test_allow_request_within_budget if {
    cost_limit.allow with input as {
        "context": {"cost_today_usd": 4.00},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {"estimated_cost_usd": 0.50}
    }
}

# =============================================================================
# Test: Token limits
# =============================================================================

test_allow_under_daily_token_limit if {
    cost_limit.allow with input as {
        "context": {"tokens_today": 5000, "cost_today_usd": 1.00},
        "rules": {"daily_token_limit": 10000, "daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_deny_over_daily_token_limit if {
    not cost_limit.allow with input as {
        "context": {"tokens_today": 12000, "cost_today_usd": 1.00},
        "rules": {"daily_token_limit": 10000, "daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_deny_over_monthly_token_limit if {
    not cost_limit.allow with input as {
        "context": {"tokens_today": 1000, "tokens_month": 350000, "cost_today_usd": 1.00},
        "rules": {"daily_token_limit": 10000, "monthly_token_limit": 300000, "daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

# =============================================================================
# Test: Warning levels
# =============================================================================

test_warning_level_low if {
    cost_limit.warning_level == "low" with input as {
        "context": {"cost_today_usd": 1.00},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_warning_level_medium if {
    cost_limit.warning_level == "medium" with input as {
        "context": {"cost_today_usd": 2.50},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_warning_level_high if {
    cost_limit.warning_level == "high" with input as {
        "context": {"cost_today_usd": 3.80},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_warning_level_critical if {
    cost_limit.warning_level == "critical" with input as {
        "context": {"cost_today_usd": 4.60},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

# =============================================================================
# Test: Usage percentages
# =============================================================================

test_daily_cost_percentage_50 if {
    cost_limit.daily_cost_percentage == 50 with input as {
        "context": {"cost_today_usd": 2.50},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_daily_cost_percentage_100 if {
    cost_limit.daily_cost_percentage == 100 with input as {
        "context": {"cost_today_usd": 5.00},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

# =============================================================================
# Test: Reason messages
# =============================================================================

test_reason_daily_cost_exceeded if {
    contains(cost_limit.reason, "Daily cost limit exceeded") with input as {
        "context": {"cost_today_usd": 6.00},
        "rules": {"daily_cost_limit_usd": 5.00},
        "request": {}
    }
}

test_reason_monthly_cost_exceeded if {
    contains(cost_limit.reason, "Monthly cost limit exceeded") with input as {
        "context": {"cost_today_usd": 2.00, "cost_month_usd": 110.00},
        "rules": {"daily_cost_limit_usd": 5.00, "monthly_cost_limit_usd": 100.00},
        "request": {}
    }
}

test_reason_token_limit_exceeded if {
    contains(cost_limit.reason, "Daily token limit exceeded") with input as {
        "context": {"tokens_today": 15000, "cost_today_usd": 1.00},
        "rules": {"daily_token_limit": 10000, "daily_cost_limit_usd": 10.00},
        "request": {}
    }
}

# =============================================================================
# Test: Decision output structure
# =============================================================================

test_decision_structure_allow if {
    decision := cost_limit.decision with input as {
        "context": {"cost_today_usd": 2.00, "cost_month_usd": 20.00, "tokens_today": 1000},
        "rules": {"daily_cost_limit_usd": 5.00, "monthly_cost_limit_usd": 100.00},
        "request": {}
    }
    decision.allow == true
    decision.policy == "cost_limit"
    decision.metadata.warning_level
}

test_decision_structure_deny if {
    decision := cost_limit.decision with input as {
        "context": {"cost_today_usd": 6.00, "cost_month_usd": 60.00, "tokens_today": 1000},
        "rules": {"daily_cost_limit_usd": 5.00, "monthly_cost_limit_usd": 100.00},
        "request": {}
    }
    decision.allow == false
    decision.policy == "cost_limit"
    decision.severity == "high"
}

# =============================================================================
# Test: No limits configured
# =============================================================================

test_allow_when_no_limits if {
    cost_limit.allow with input as {
        "context": {"cost_today_usd": 100.00},
        "rules": {},
        "request": {}
    }
}
