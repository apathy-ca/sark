# Team Access Policy Tests
# Comprehensive test suite for team-based access control

package sark.defaults.team_access

import future.keywords.if

# ============================================================================
# TEAM OWNERSHIP TESTS
# ============================================================================

# Test: Team member can read team-owned server
test_team_member_read_server if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "srv-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Team member can invoke team tool
test_team_member_invoke_tool if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "tool-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Non-team member CANNOT read team server
test_non_team_member_denied if {
    not allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "teams": ["team-beta"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "srv-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# TEAM MANAGER TESTS
# ============================================================================

# Test: Team manager can update team server
test_team_manager_update_server if {
    allow with input as {
        "action": "server:update",
        "user": {
            "id": "mgr-1",
            "role": "developer",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
        },
        "resource": {
            "id": "srv-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Team manager can delete team server (low/medium)
test_team_manager_delete_low_server if {
    allow with input as {
        "action": "server:delete",
        "user": {
            "id": "mgr-1",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
        },
        "resource": {
            "id": "srv-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Team member CANNOT update team server (not manager)
test_team_member_cannot_update if {
    not allow with input as {
        "action": "server:update",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "srv-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Team manager can invoke high sensitivity team tools
test_team_manager_invoke_high_tool if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "mgr-1",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
        },
        "tool": {
            "id": "tool-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "high",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# HIGH/CRITICAL SENSITIVITY REQUIREMENTS
# ============================================================================

# Test: High sensitivity server requires team assignment
test_high_sensitivity_requires_team if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "server": {
            "name": "high-srv",
            "sensitivity_level": "high",
            "teams": ["team-alpha"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: High sensitivity DENIED without team assignment
test_high_sensitivity_denied_without_team if {
    deny with input as {
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

# Test: Critical sensitivity requires team manager
test_critical_requires_team_manager if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "mgr-1",
            "role": "developer",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
        },
        "server": {
            "name": "critical-srv",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Critical sensitivity DENIED for non-manager
test_critical_denied_for_non_manager if {
    not allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-1",
            "role": "developer",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "server": {
            "name": "critical-srv",
            "sensitivity_level": "critical",
            "teams": ["team-alpha"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Critical sensitivity DENIED without team
test_critical_denied_without_team if {
    deny with input as {
        "action": "server:register",
        "user": {
            "id": "mgr-1",
            "role": "developer",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
        },
        "server": {
            "name": "critical-srv",
            "sensitivity_level": "critical",
            "teams": [],
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# TOOL ACCESS TESTS
# ============================================================================

# Test: Team member can invoke low sensitivity team tool
test_team_member_invoke_low_tool if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "tool": {
            "id": "tool-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Team member can invoke medium sensitivity team tool
test_team_member_invoke_medium_tool if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "tool": {
            "id": "tool-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Team member CANNOT invoke high sensitivity team tool
test_team_member_cannot_invoke_high_tool if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "tool": {
            "id": "tool-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "high",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Critical tool invocation denied for non-manager
test_critical_tool_denied_for_non_manager if {
    deny with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "tool": {
            "id": "tool-1",
            "teams": ["team-alpha"],
            "sensitivity_level": "critical",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# RESOURCE SHARING TESTS
# ============================================================================

# Test: Team member can share owned resource within team
test_team_member_share_within_team if {
    allow with input as {
        "action": "resource:share",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "res-1",
            "owner": "user-1",
        },
        "target_team": "team-alpha",
        "context": {"timestamp": 0},
    }
}

# Test: Team manager can share team resources
test_team_manager_share_team_resource if {
    allow with input as {
        "action": "resource:share",
        "user": {
            "id": "mgr-1",
            "teams": ["team-alpha"],
            "team_manager_of": ["team-alpha"],
        },
        "resource": {
            "id": "res-1",
            "teams": ["team-alpha"],
        },
        "target_team": "team-beta",
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# CROSS-TEAM ACCESS TESTS
# ============================================================================

# Test: Public low sensitivity resources accessible across teams
test_public_resource_cross_team if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "teams": ["team-beta"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "res-1",
            "teams": ["team-alpha"],
            "visibility": "public",
            "sensitivity_level": "low",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Explicit allowed_teams grants access
test_allowed_teams_grants_access if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "teams": ["team-beta"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "res-1",
            "teams": ["team-alpha"],
            "allowed_teams": ["team-beta"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Public high sensitivity resources still restricted
test_public_high_sensitivity_restricted if {
    not allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "teams": ["team-beta"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "res-1",
            "teams": ["team-alpha"],
            "visibility": "public",
            "sensitivity_level": "high",
        },
        "context": {"timestamp": 0},
    }
}

# ============================================================================
# MULTIPLE TEAMS TESTS
# ============================================================================

# Test: User in multiple teams can access any team resource
test_multiple_teams_access if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "teams": ["team-alpha", "team-beta", "team-gamma"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "res-1",
            "teams": ["team-beta"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}

# Test: Resource with multiple teams accessible to any team member
test_resource_multiple_teams if {
    allow with input as {
        "action": "server:read",
        "user": {
            "id": "user-1",
            "teams": ["team-gamma"],
            "team_manager_of": [],
        },
        "resource": {
            "id": "res-1",
            "teams": ["team-alpha", "team-beta", "team-gamma"],
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}
