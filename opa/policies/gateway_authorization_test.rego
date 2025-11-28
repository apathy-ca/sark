# Gateway Authorization Policy Tests
# Comprehensive test suite for gateway_authorization.rego

package mcp.gateway

import future.keywords.if

# ============================================================================
# ADMIN AUTHORIZATION TESTS
# ============================================================================

test_admin_can_invoke_high_sensitivity_tools if {
    allow with input as {
        "user": {"id": "admin1", "role": "admin", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "db-query", "sensitivity_level": "high"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_admin_cannot_invoke_critical_tools if {
    not allow with input as {
        "user": {"id": "admin1", "role": "admin", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "db-admin", "sensitivity_level": "critical"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_admin_blocked_outside_work_hours if {
    not allow with input as {
        "user": {"id": "admin1", "role": "admin", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "api-call", "sensitivity_level": "high"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 1640000000}  # Outside work hours (6 PM+)
    }
}

test_admin_can_register_servers if {
    allow with input as {
        "user": {"id": "admin1", "role": "admin", "teams": []},
        "action": "gateway:server:register",
        "server": {"name": "new-server", "sensitivity_level": "high"},
        "context": {"timestamp": 0}
    }
}

# ============================================================================
# DEVELOPER AUTHORIZATION TESTS
# ============================================================================

test_developer_can_invoke_low_sensitivity_tools if {
    allow with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "read-file", "sensitivity_level": "low"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_developer_can_invoke_medium_sensitivity_tools if {
    allow with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "api-call", "sensitivity_level": "medium"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_developer_blocked_on_high_sensitivity if {
    not allow with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "db-query", "sensitivity_level": "high"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_developer_blocked_on_critical_sensitivity if {
    not allow with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "db-admin", "sensitivity_level": "critical"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_developer_can_register_low_sensitivity_servers if {
    allow with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:server:register",
        "server": {"name": "dev-server", "sensitivity_level": "low"},
        "context": {"timestamp": 0}
    }
}

test_developer_cannot_register_high_sensitivity_servers if {
    not allow with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:server:register",
        "server": {"name": "prod-server", "sensitivity_level": "high"},
        "context": {"timestamp": 0}
    }
}

# ============================================================================
# TEAM-BASED ACCESS TESTS
# ============================================================================

test_team_member_can_access_team_server if {
    allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": ["team-alpha"]},
        "action": "gateway:tool:invoke",
        "tool": {"name": "team-tool", "sensitivity_level": "medium"},
        "server": {
            "id": "server1",
            "owner_id": "user2",
            "managed_by_team": "team-alpha",
            "visibility": "internal"
        },
        "context": {"timestamp": 0}
    }
}

test_non_team_member_blocked_from_team_server if {
    not allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": ["team-beta"]},
        "action": "gateway:tool:invoke",
        "tool": {"name": "team-tool", "sensitivity_level": "high"},  # High sensitivity, not low/medium
        "server": {
            "id": "server1",
            "owner_id": "user2",
            "managed_by_team": "team-alpha",
            "visibility": "private"
        },
        "context": {"timestamp": 0}
    }
}

# ============================================================================
# SERVER OWNER TESTS
# ============================================================================

test_server_owner_can_invoke_tools if {
    allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "owner-tool", "sensitivity_level": "high"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_server_owner_blocked_outside_work_hours if {
    not allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "owner-tool", "sensitivity_level": "high"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 1640025600}  # 8 PM
    }
}

# ============================================================================
# DISCOVERY TESTS
# ============================================================================

test_authenticated_user_can_list_servers if {
    allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": []},
        "action": "gateway:servers:list",
        "context": {"timestamp": 0}
    }
}

test_authenticated_user_can_list_tools if {
    allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": []},
        "action": "gateway:tools:list",
        "context": {"timestamp": 0}
    }
}

test_anonymous_user_cannot_list_servers if {
    not allow with input as {
        "user": {"id": "", "role": "", "teams": []},
        "action": "gateway:servers:list",
        "context": {"timestamp": 0}
    }
}

# ============================================================================
# AUDIT ACCESS TESTS
# ============================================================================

test_admin_can_view_audit_logs if {
    allow with input as {
        "user": {"id": "admin1", "role": "admin", "teams": []},
        "action": "gateway:audit:view",
        "context": {"timestamp": 0}
    }
}

test_security_admin_can_view_audit_logs if {
    allow with input as {
        "user": {"id": "sec1", "role": "security_admin", "teams": []},
        "action": "gateway:audit:view",
        "context": {"timestamp": 0}
    }
}

test_team_lead_can_view_team_audit_logs if {
    allow with input as {
        "user": {"id": "lead1", "role": "team_lead", "teams": ["team-alpha"]},
        "action": "gateway:audit:view",
        "server": {"id": "server1", "managed_by_team": "team-alpha"},
        "context": {"timestamp": 0}
    }
}

test_developer_cannot_view_audit_logs if {
    not allow with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:audit:view",
        "context": {"timestamp": 0}
    }
}

# ============================================================================
# PARAMETER FILTERING TESTS
# ============================================================================

test_admin_sees_all_parameters if {
    filtered_parameters == {"password": "secret123", "api_key": "key123", "data": "value"} with input as {
        "user": {"id": "admin1", "role": "admin", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {
            "name": "db-query",
            "sensitivity_level": "high",
            "parameters": {"password": "secret123", "api_key": "key123", "data": "value"}
        },
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_developer_parameters_filtered_for_high_sensitivity if {
    filtered_parameters == {"data": "value"} with input as {
        "user": {"id": "admin1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {
            "name": "db-query",
            "sensitivity_level": "high",
            "parameters": {"password": "secret123", "api_key": "key123", "data": "value"}
        },
        "server": {"id": "server1", "owner_id": "admin1"},
        "context": {"timestamp": 0}
    }
}

test_developer_parameters_filtered_for_critical_sensitivity if {
    # For critical sensitivity, even more params are filtered
    filtered_parameters == {"data": "value"} with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {
            "name": "critical-tool",
            "sensitivity_level": "critical",
            "parameters": {
                "password": "secret123",
                "api_key": "key123",
                "ssn": "123-45-6789",
                "data": "value"
            }
        },
        "server": {"id": "server1", "owner_id": "dev1"},
        "context": {"timestamp": 0}
    }
}

# ============================================================================
# WORK HOURS TESTS
# ============================================================================

test_work_hours_function_allows_9am if {
    is_work_hours(1640001600) with time.clock as [9, 0, 0]
}

test_work_hours_function_allows_5pm if {
    is_work_hours(1640030400) with time.clock as [17, 0, 0]
}

test_work_hours_function_blocks_6pm if {
    not is_work_hours(1640034000) with time.clock as [18, 0, 0]
}

test_work_hours_function_blocks_8am if {
    not is_work_hours(1639997200) with time.clock as [8, 0, 0]
}

test_work_hours_allows_timestamp_zero if {
    is_work_hours(0)
}

# ============================================================================
# SERVER ACCESS HELPER TESTS
# ============================================================================

test_server_access_public_server if {
    server_access_allowed(
        {"id": "user1", "teams": []},
        {"id": "server1", "visibility": "public"}
    )
}

test_server_access_owner if {
    server_access_allowed(
        {"id": "user1", "teams": []},
        {"id": "server1", "owner_id": "user1", "visibility": "private"}
    )
}

test_server_access_team_member if {
    server_access_allowed(
        {"id": "user1", "teams": ["team-alpha"]},
        {"id": "server1", "managed_by_team": "team-alpha", "visibility": "internal"}
    )
}

test_server_access_same_environment if {
    server_access_allowed(
        {"id": "user1", "environment": "production", "teams": []},
        {"id": "server1", "environment": "production", "visibility": "internal"}
    )
}

test_server_access_denied_different_environment if {
    not server_access_allowed(
        {"id": "user1", "environment": "development", "teams": []},
        {"id": "server1", "environment": "production", "visibility": "internal"}
    )
}

# ============================================================================
# AUDIT REASON TESTS
# ============================================================================

test_audit_reason_admin if {
    audit_reason == "Allowed: gateway:tool:invoke by user admin1 (role: admin, admin)" with input as {
        "user": {"id": "admin1", "role": "admin", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "tool1", "sensitivity_level": "high"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_audit_reason_denied if {
    audit_reason == "Denied: gateway:tool:invoke by user dev1 (insufficient permissions)" with input as {
        "user": {"id": "dev1", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "tool1", "sensitivity_level": "critical"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

# ============================================================================
# EDGE CASES AND SECURITY TESTS
# ============================================================================

test_empty_user_id_denied if {
    not allow with input as {
        "user": {"id": "", "role": "developer", "teams": []},
        "action": "gateway:tool:invoke",
        "tool": {"name": "tool1", "sensitivity_level": "low"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_missing_action_denied if {
    not allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": []},
        "tool": {"name": "tool1", "sensitivity_level": "low"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_unknown_action_denied if {
    not allow with input as {
        "user": {"id": "user1", "role": "developer", "teams": []},
        "action": "gateway:unknown:action",
        "tool": {"name": "tool1", "sensitivity_level": "low"},
        "server": {"id": "server1", "owner_id": "user1"},
        "context": {"timestamp": 0}
    }
}

test_team_lead_can_register_servers if {
    allow with input as {
        "user": {"id": "lead1", "role": "team_lead", "teams": ["team-alpha"]},
        "action": "gateway:server:register",
        "server": {"name": "team-server", "sensitivity_level": "medium"},
        "context": {"timestamp": 0}
    }
}
