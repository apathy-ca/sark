# Sensitivity Level Enforcement Policy Tests
# Comprehensive test suite for sensitivity-based access control

package sark.defaults.sensitivity

import future.keywords.if

# ============================================================================
# LOW SENSITIVITY TESTS
# ============================================================================

# Test: Authenticated user can access low sensitivity resource
test_low_sensitivity_authenticated_access if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "role": "developer",
            "authenticated": true,
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Authenticated user can register low sensitivity server
test_low_sensitivity_register if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-1",
            "authenticated": true,
        },
        "server": {
            "name": "low-srv",
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Low sensitivity tool invocation allowed
test_low_sensitivity_tool_invoke if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "authenticated": true,
        },
        "resource": {
            "id": "tool-1",
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# MEDIUM SENSITIVITY TESTS
# ============================================================================

# Test: Developer can access medium sensitivity resource
test_medium_sensitivity_developer_access if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "role": "developer",
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Admin can access medium sensitivity resource
test_medium_sensitivity_admin_access if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "admin-1",
            "role": "admin",
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Developer can register medium sensitivity server
test_medium_sensitivity_register if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-1",
            "role": "developer",
        },
        "server": {
            "name": "med-srv",
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Viewer CANNOT register medium sensitivity server
test_medium_sensitivity_viewer_denied if {
    not allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-1",
            "role": "viewer",
        },
        "server": {
            "name": "med-srv",
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# HIGH SENSITIVITY TESTS
# ============================================================================

# Test: Team member can access high sensitivity during work hours
test_high_sensitivity_team_member_work_hours if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: High sensitivity requires team membership
test_high_sensitivity_requires_team if {
    not allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-beta"],
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: High sensitivity server registration requires team
test_high_sensitivity_register_requires_team if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "server": {
            "name": "high-srv",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: High sensitivity DENIED without team
test_high_sensitivity_register_denied_without_team if {
    not allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "server": {
            "name": "high-srv",
            "sensitivity_level": "high",
            "teams": [],
        },
        "context": {"timestamp": 0},
    }
}

# Test: High sensitivity tool requires audit logging
test_high_sensitivity_tool_requires_audit if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "tool": {
            "id": "tool-1",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": true,
        },
    }
}

# Test: High sensitivity tool DENIED without audit
test_high_sensitivity_tool_denied_without_audit if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "tool": {
            "id": "tool-1",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": false,
        },
    }
}

# ============================================================================
# CRITICAL SENSITIVITY TESTS
# ============================================================================

# Test: Team manager can access critical during work hours with MFA
test_critical_team_manager_access if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "mgr-1",
            "role": "admin",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
            "mfa_verified": true,
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": true,
        },
    }
}

# Test: Critical requires team manager
test_critical_requires_team_manager if {
    not allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": true,
        },
    }
}

# Test: Critical server registration requires admin/manager
test_critical_register_requires_admin if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "admin-1",
            "role": "admin",
            "teams": ["team-alpha"],
        },
        "server": {
            "name": "critical-srv",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Critical server registration requires team
test_critical_register_requires_team if {
    not allow with input as {
        "action": "server:register",
        "user": {
            "id": "admin-1",
            "role": "admin",
        },
        "server": {
            "name": "critical-srv",
            "sensitivity_level": "critical",
            "teams": [],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Critical tool invocation requires MFA
test_critical_tool_requires_mfa if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "mgr-1",
            "role": "admin",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
            "mfa_verified": true,
        },
        "tool": {
            "id": "tool-1",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": true,
        },
    }
}

# Test: Critical tool DENIED without MFA
test_critical_tool_denied_without_mfa if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "mgr-1",
            "role": "admin",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
            "mfa_verified": false,
        },
        "tool": {
            "id": "tool-1",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": true,
        },
    }
}

# ============================================================================
# SENSITIVITY ESCALATION TESTS
# ============================================================================

# Test: Admin can downgrade sensitivity
test_admin_can_downgrade_sensitivity if {
    allow with input as {
        "action": "server:update",
        "user": {
            "id": "admin-1",
            "role": "admin",
        },
        "server": {
            "id": "srv-1",
            "sensitivity_level_change": true,
            "current_sensitivity_level": "high",
            "new_sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Non-admin CANNOT downgrade sensitivity
test_non_admin_cannot_downgrade if {
    deny with input as {
        "action": "server:update",
        "user": {
            "id": "user-1",
            "role": "developer",
        },
        "server": {
            "id": "srv-1",
            "sensitivity_level_change": true,
            "current_sensitivity_level": "high",
            "new_sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Owner can upgrade sensitivity
test_owner_can_upgrade_sensitivity if {
    allow with input as {
        "action": "server:update",
        "user": {
            "id": "user-1",
            "role": "developer",
        },
        "server": {
            "id": "srv-1",
            "owner": "user-1",
            "sensitivity_level_change": true,
            "current_sensitivity_level": "medium",
            "new_sensitivity_level": "high",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# TIME-BASED RESTRICTION TESTS
# ============================================================================

# Test: High sensitivity DENIED outside work hours
test_high_denied_outside_work_hours if {
    deny with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "resource": {
            "id": "tool-1",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 1700078400000000000,  # 7 PM
            "emergency_override": false,
            "audit_enabled": true,
        },
    }
}

# Test: Critical DENIED outside business days
test_critical_denied_outside_business_days if {
    deny with input as {
        "action": "tool:invoke",
        "user": {
            "id": "mgr-1",
            "role": "admin",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
            "mfa_verified": true,
        },
        "resource": {
            "id": "tool-1",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 1700352000000000000,  # Saturday
            "emergency_override": false,
            "audit_enabled": true,
        },
    }
}

# Test: Emergency override bypasses time restrictions
test_emergency_override_bypasses_time if {
    not deny with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "resource": {
            "id": "tool-1",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 1700078400000000000,  # 7 PM
            "emergency_override": true,
            "audit_enabled": true,
        },
    }
}

# ============================================================================
# AUDIT REQUIREMENT TESTS
# ============================================================================

# Test: High sensitivity DENIED without audit
test_high_denied_without_audit if {
    deny with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
        },
        "resource": {
            "id": "tool-1",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": false,
        },
    }
}

# Test: Critical update DENIED without audit
test_critical_update_denied_without_audit if {
    deny with input as {
        "action": "server:update",
        "user": {
            "id": "admin-1",
            "role": "admin",
        },
        "resource": {
            "id": "srv-1",
            "sensitivity_level": "critical",
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": false,
        },
    }
}

# Test: Low/medium don't require audit
test_low_no_audit_required if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "authenticated": true,
        },
        "resource": {
            "id": "res-1",
            "sensitivity_level": "low",
        },
        "context": {
            "timestamp": 0,
            "audit_enabled": false,
        },
    }
}

# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

# Test: Sensitivity upgrade detection
test_sensitivity_upgrade if {
    is_sensitivity_upgrade("low", "medium")
    is_sensitivity_upgrade("medium", "high")
    is_sensitivity_upgrade("high", "critical")
}

# Test: Sensitivity downgrade detection
test_sensitivity_downgrade if {
    is_sensitivity_downgrade("critical", "high")
    is_sensitivity_downgrade("high", "medium")
    is_sensitivity_downgrade("medium", "low")
}

# Test: Work hours helper
test_work_hours_helper if {
    is_work_hours with input.context.timestamp as 0
    is_work_hours with input.context.timestamp as 1700049600000000000  # 9 AM
}

# Test: Business day helper
test_business_day_helper if {
    is_business_day with input.context.timestamp as 0
    is_business_day with input.context.timestamp as 1700049600000000000  # Monday
}
