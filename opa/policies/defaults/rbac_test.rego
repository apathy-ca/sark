# RBAC Policy Tests
# Comprehensive test suite for role-based access control

package sark.defaults.rbac

import future.keywords.if

# ============================================================================
# SERVER REGISTRATION TESTS
# ============================================================================

# Test: Admin can register any server
test_admin_register_any_server if {
    allow with input as {
        "action": "server:register",
        "user": {"id": "admin-1", "role": "admin"},
        "server": {"name": "critical-server", "sensitivity_level": "critical"},
        "context": {"timestamp": 0},
    }
}

# Test: Developer can register low sensitivity server
test_developer_register_low_server if {
    allow with input as {
        "action": "server:register",
        "user": {"id": "dev-1", "role": "developer"},
        "server": {"name": "test-server", "sensitivity_level": "low"},
        "context": {"timestamp": 0},
    }
}

# Test: Developer can register medium sensitivity server
test_developer_register_medium_server if {
    allow with input as {
        "action": "server:register",
        "user": {"id": "dev-1", "role": "developer"},
        "server": {"name": "test-server", "sensitivity_level": "medium"},
        "context": {"timestamp": 0},
    }
}

# Test: Developer CANNOT register high sensitivity server
test_developer_cannot_register_high_server if {
    not allow with input as {
        "action": "server:register",
        "user": {"id": "dev-1", "role": "developer"},
        "server": {"name": "high-server", "sensitivity_level": "high"},
        "context": {"timestamp": 0},
    }
}

# Test: Service account can register server with scope
test_service_register_with_scope if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "svc-1",
            "role": "service",
            "scopes": ["server:register"],
        },
        "server": {"name": "svc-server", "sensitivity_level": "low"},
        "context": {"timestamp": 0},
    }
}

# Test: Service account CANNOT register without scope
test_service_cannot_register_without_scope if {
    not allow with input as {
        "action": "server:register",
        "user": {
            "id": "svc-1",
            "role": "service",
            "scopes": ["server:read"],
        },
        "server": {"name": "svc-server", "sensitivity_level": "low"},
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# SERVER UPDATE TESTS
# ============================================================================

# Test: Admin can update any server
test_admin_update_any_server if {
    allow with input as {
        "action": "server:update",
        "user": {"id": "admin-1", "role": "admin"},
        "server": {
            "id": "srv-123",
            "owner": "other-user",
            "sensitivity_level": "high",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Developer can update owned server
test_developer_update_owned_server if {
    allow with input as {
        "action": "server:update",
        "user": {"id": "dev-1", "role": "developer"},
        "server": {
            "id": "srv-123",
            "owner": "dev-1",
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Developer CANNOT update non-owned server
test_developer_cannot_update_non_owned_server if {
    not allow with input as {
        "action": "server:update",
        "user": {"id": "dev-1", "role": "developer"},
        "server": {
            "id": "srv-123",
            "owner": "other-user",
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# SERVER DELETE TESTS
# ============================================================================

# Test: Admin can delete any server
test_admin_delete_any_server if {
    allow with input as {
        "action": "server:delete",
        "user": {"id": "admin-1", "role": "admin"},
        "server": {
            "id": "srv-123",
            "owner": "other-user",
            "sensitivity_level": "high",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Developer can delete owned low sensitivity server
test_developer_delete_owned_low_server if {
    allow with input as {
        "action": "server:delete",
        "user": {"id": "dev-1", "role": "developer"},
        "server": {
            "id": "srv-123",
            "owner": "dev-1",
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Developer CANNOT delete owned high sensitivity server
test_developer_cannot_delete_owned_high_server if {
    not allow with input as {
        "action": "server:delete",
        "user": {"id": "dev-1", "role": "developer"},
        "server": {
            "id": "srv-123",
            "owner": "dev-1",
            "sensitivity_level": "high",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# SERVER READ TESTS
# ============================================================================

# Test: Admin can read any server
test_admin_read_server if {
    allow with input as {
        "action": "server:read",
        "user": {"id": "admin-1", "role": "admin"},
        "context": {"timestamp": 0},
    }
}

# Test: Developer can read servers
test_developer_read_server if {
    allow with input as {
        "action": "server:read",
        "user": {"id": "dev-1", "role": "developer"},
        "context": {"timestamp": 0},
    }
}

# Test: Viewer can read servers
test_viewer_read_server if {
    allow with input as {
        "action": "server:read",
        "user": {"id": "viewer-1", "role": "viewer"},
        "context": {"timestamp": 0},
    }
}

# Test: Service account can read with scope
test_service_read_with_scope if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "svc-1",
            "role": "service",
            "scopes": ["server:read"],
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# TOOL INVOCATION TESTS
# ============================================================================

# Test: Admin can invoke non-critical tools
test_admin_invoke_non_critical if {
    allow with input as {
        "action": "tool:invoke",
        "user": {"id": "admin-1", "role": "admin"},
        "tool": {"name": "test-tool", "sensitivity_level": "high"},
        "context": {"timestamp": 0},
    }
}

# Test: Admin CANNOT invoke critical tools outside work hours
test_admin_cannot_invoke_critical_outside_hours if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {"id": "admin-1", "role": "admin"},
        "tool": {"name": "critical-tool", "sensitivity_level": "critical"},
        "context": {"timestamp": 1700000000000000000},  # Outside work hours
    }
}

# Test: Developer can invoke low sensitivity tools
test_developer_invoke_low if {
    allow with input as {
        "action": "tool:invoke",
        "user": {"id": "dev-1", "role": "developer"},
        "tool": {"name": "test-tool", "sensitivity_level": "low"},
        "context": {"timestamp": 0},
    }
}

# Test: Developer can invoke medium sensitivity tools
test_developer_invoke_medium if {
    allow with input as {
        "action": "tool:invoke",
        "user": {"id": "dev-1", "role": "developer"},
        "tool": {"name": "test-tool", "sensitivity_level": "medium"},
        "context": {"timestamp": 0},
    }
}

# Test: Developer CANNOT invoke high sensitivity tools
test_developer_cannot_invoke_high if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {"id": "dev-1", "role": "developer"},
        "tool": {"name": "test-tool", "sensitivity_level": "high"},
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# POLICY MANAGEMENT TESTS
# ============================================================================

# Test: Admin can create policies
test_admin_create_policy if {
    allow with input as {
        "action": "policy:create",
        "user": {"id": "admin-1", "role": "admin"},
        "context": {"timestamp": 0},
    }
}

# Test: Developer CANNOT create policies
test_developer_cannot_create_policy if {
    not allow with input as {
        "action": "policy:create",
        "user": {"id": "dev-1", "role": "developer"},
        "context": {"timestamp": 0},
    }
}

# Test: Admin can update policies
test_admin_update_policy if {
    allow with input as {
        "action": "policy:update",
        "user": {"id": "admin-1", "role": "admin"},
        "context": {"timestamp": 0},
    }
}

# Test: Everyone can read policies
test_developer_read_policy if {
    allow with input as {
        "action": "policy:read",
        "user": {"id": "dev-1", "role": "developer"},
        "context": {"timestamp": 0},
    }
}

test_viewer_read_policy if {
    allow with input as {
        "action": "policy:read",
        "user": {"id": "viewer-1", "role": "viewer"},
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# WORK HOURS HELPER TESTS
# ============================================================================

# Test: Work hours detection (9 AM - 6 PM)
test_work_hours_morning if {
    is_work_hours with input.context.timestamp as 1700049600000000000  # 9 AM
}

test_work_hours_afternoon if {
    is_work_hours with input.context.timestamp as 1700071200000000000  # 5 PM
}

test_not_work_hours_evening if {
    not is_work_hours with input.context.timestamp as 1700078400000000000  # 7 PM
}

test_not_work_hours_night if {
    not is_work_hours with input.context.timestamp as 1700020800000000000  # 1 AM
}
