# MCP Authorization Policy Tests

package mcp

import future.keywords.if

# Test: Owner can access their own tools
test_owner_access if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-123",
            "role": "developer",
            "teams": [],
        },
        "tool": {
            "name": "database_query",
            "owner": "user-123",
            "sensitivity_level": "high",
            "managers": [],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Team member can access team tools
test_team_access if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-456",
            "role": "developer",
            "teams": ["team-A"],
        },
        "tool": {
            "name": "database_query",
            "owner": "user-123",
            "sensitivity_level": "medium",
            "managers": ["team-A"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Non-team member denied
test_non_team_denied if {
    not allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "user-789",
            "role": "developer",
            "teams": ["team-B"],
        },
        "tool": {
            "name": "database_query",
            "owner": "user-123",
            "sensitivity_level": "medium",
            "managers": ["team-A"],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Admin can access non-critical tools
test_admin_access if {
    allow with input as {
        "action": "tool:invoke",
        "user": {
            "id": "admin-1",
            "role": "admin",
            "teams": [],
        },
        "tool": {
            "name": "system_tool",
            "owner": "user-123",
            "sensitivity_level": "high",
            "managers": [],
        },
        "context": {"timestamp": 0},
    }
}

# Test: Server registration allowed for developers
test_server_registration if {
    allow with input as {
        "action": "server:register",
        "user": {
            "id": "user-123",
            "role": "developer",
        },
        "server": {
            "name": "test-server",
            "sensitivity_level": "medium",
        },
        "context": {"timestamp": 0},
    }
}
