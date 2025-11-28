# Agent-to-Agent (A2A) Authorization Policy Tests
# Comprehensive test suite for a2a_authorization.rego

package mcp.gateway.a2a

import future.keywords.if

# ============================================================================
# TRUST LEVEL TESTS
# ============================================================================

test_trusted_agents_can_communicate_same_env if {
    allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "trusted",
            "environment": "production",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_untrusted_agent_blocked if {
    not allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "untrusted",
            "environment": "production",
            "type": "worker"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_verified_agents_same_org if {
    allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "verified",
            "environment": "production",
            "organization_id": "org1",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "verified",
            "environment": "production",
            "organization_id": "org1",
            "type": "worker"
        },
        "context": {}
    }
}

test_verified_agents_different_org_blocked if {
    not allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "verified",
            "environment": "production",
            "organization_id": "org1",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "verified",
            "environment": "production",
            "organization_id": "org2",
            "type": "worker"
        },
        "context": {}
    }
}

# ============================================================================
# SERVICE TO WORKER TESTS
# ============================================================================

test_service_can_communicate_with_worker if {
    allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "service1",
            "type": "service",
            "trust_level": "verified",
            "environment": "production"
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

test_service_can_invoke_worker if {
    allow with input as {
        "action": "a2a:invoke",
        "source_agent": {
            "id": "service1",
            "type": "service",
            "trust_level": "trusted",
            "environment": "production",
            "rate_limit_per_minute": 1000
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {
            "rate_limit": {
                "current_count": 50
            }
        }
    }
}

# ============================================================================
# CAPABILITY TESTS
# ============================================================================

test_execute_capability_allowed if {
    allow with input as {
        "action": "a2a:execute",
        "source_agent": {
            "id": "agent1",
            "type": "service",
            "capabilities": ["execute", "query"],
            "trust_level": "trusted",
            "environment": "production"
        },
        "target_agent": {
            "id": "agent2",
            "type": "worker",
            "accepts_execution": true,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

test_execute_capability_denied_without_capability if {
    not allow with input as {
        "action": "a2a:execute",
        "source_agent": {
            "id": "agent1",
            "type": "service",
            "capabilities": ["query"],
            "trust_level": "trusted",
            "environment": "production"
        },
        "target_agent": {
            "id": "agent2",
            "type": "worker",
            "accepts_execution": true,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

test_query_capability_allowed if {
    allow with input as {
        "action": "a2a:query",
        "source_agent": {
            "id": "agent1",
            "type": "service",
            "capabilities": ["query"],
            "trust_level": "verified",
            "environment": "production"
        },
        "target_agent": {
            "id": "agent2",
            "type": "worker",
            "accepts_queries": true,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

test_delegate_capability_requires_trust if {
    allow with input as {
        "action": "a2a:delegate",
        "source_agent": {
            "id": "agent1",
            "type": "service",
            "capabilities": ["delegate"],
            "trust_level": "trusted",
            "environment": "production"
        },
        "target_agent": {
            "id": "agent2",
            "type": "worker",
            "accepts_delegation": true,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

test_delegate_denied_for_untrusted if {
    not allow with input as {
        "action": "a2a:delegate",
        "source_agent": {
            "id": "agent1",
            "type": "service",
            "capabilities": ["delegate"],
            "trust_level": "untrusted",
            "environment": "production"
        },
        "target_agent": {
            "id": "agent2",
            "type": "worker",
            "accepts_delegation": true,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

# ============================================================================
# CROSS-ENVIRONMENT TESTS
# ============================================================================

test_cross_env_blocked_by_default if {
    not allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "verified",
            "environment": "development",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "verified",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_production_protected_from_nonprod if {
    deny with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "verified",
            "environment": "development",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_staging_to_production_allowed_for_trusted_service if {
    allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "trusted",
            "type": "service",
            "environment": "staging"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "type": "worker",
            "environment": "production"
        },
        "context": {}
    }
}

test_dev_to_staging_allowed_for_verified if {
    allow with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "verified",
            "type": "service",
            "environment": "development"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "type": "worker",
            "environment": "staging"
        },
        "context": {}
    }
}

# ============================================================================
# AGENT TYPE TESTS
# ============================================================================

test_orchestrator_can_execute if {
    allow with input as {
        "action": "a2a:execute",
        "source_agent": {
            "id": "orchestrator1",
            "type": "orchestrator",
            "trust_level": "trusted",
            "environment": "production",
            "rate_limit_per_minute": 10000
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {
            "rate_limit": {
                "current_count": 100
            }
        }
    }
}

test_orchestrator_can_query if {
    allow with input as {
        "action": "a2a:query",
        "source_agent": {
            "id": "orchestrator1",
            "type": "orchestrator",
            "trust_level": "trusted",
            "environment": "production",
            "rate_limit_per_minute": 10000
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {
            "rate_limit": {
                "current_count": 100
            }
        }
    }
}

test_monitor_can_query_but_not_execute if {
    allow with input as {
        "action": "a2a:query",
        "source_agent": {
            "id": "monitor1",
            "type": "monitor",
            "trust_level": "trusted",
            "environment": "production"
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

test_monitor_cannot_execute if {
    not allow with input as {
        "action": "a2a:execute",
        "source_agent": {
            "id": "monitor1",
            "type": "monitor",
            "trust_level": "trusted",
            "environment": "production",
            "capabilities": ["execute"]
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "accepts_execution": true,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

test_rate_limit_ok_when_under_limit if {
    rate_limit_ok(
        {"id": "agent1", "rate_limit_per_minute": 1000},
        {"rate_limit": {"current_count": 500}}
    )
}

test_rate_limit_exceeded if {
    not rate_limit_ok(
        {"id": "agent1", "rate_limit_per_minute": 1000},
        {"rate_limit": {"current_count": 1001}}
    )
}

test_rate_limit_ok_when_no_context if {
    rate_limit_ok(
        {"id": "agent1", "rate_limit_per_minute": 1000},
        {}
    )
}

# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

test_same_environment_true if {
    same_environment(
        {"environment": "production"},
        {"environment": "production"}
    )
}

test_same_environment_false if {
    not same_environment(
        {"environment": "development"},
        {"environment": "production"}
    )
}

test_same_organization_true if {
    same_organization(
        {"organization_id": "org1"},
        {"organization_id": "org1"}
    )
}

test_same_organization_false if {
    not same_organization(
        {"organization_id": "org1"},
        {"organization_id": "org2"}
    )
}

test_can_execute_service_to_worker if {
    can_execute_on_target(
        {"type": "service"},
        {"type": "worker"}
    )
}

test_can_execute_orchestrator_to_service if {
    can_execute_on_target(
        {"type": "orchestrator"},
        {"type": "service"}
    )
}

test_can_execute_trusted_same_type if {
    can_execute_on_target(
        {"type": "service", "trust_level": "trusted"},
        {"type": "service"}
    )
}

# ============================================================================
# RESTRICTIONS TESTS
# ============================================================================

test_restrictions_include_rate_limiting_for_verified if {
    result.restrictions.rate_limited == true with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "verified",
            "environment": "production",
            "organization_id": "org1",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "verified",
            "environment": "production",
            "organization_id": "org1",
            "type": "worker"
        },
        "context": {}
    }
}

test_restrictions_require_monitoring_for_cross_env if {
    result.restrictions.monitoring_required == true with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "trusted",
            "environment": "staging",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_restrictions_require_monitoring_for_production if {
    result.restrictions.monitoring_required == true with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "trusted",
            "environment": "production",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_encryption_always_required if {
    result.restrictions.encryption_required == true with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "trusted",
            "environment": "production",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

# ============================================================================
# AUDIT REASON TESTS
# ============================================================================

test_audit_reason_trusted_agents if {
    startswith(audit_reason, "Allowed: a2a:communicate from agent agent1 to agent2 (trusted agents") with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "trusted",
            "environment": "production",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_audit_reason_service_worker if {
    contains(audit_reason, "service->worker") with input as {
        "action": "a2a:invoke",
        "source_agent": {
            "id": "service1",
            "type": "service",
            "trust_level": "trusted",
            "environment": "production",
            "rate_limit_per_minute": 1000
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {
            "rate_limit": {"current_count": 50}
        }
    }
}

test_audit_reason_orchestrator if {
    contains(audit_reason, "orchestrator") with input as {
        "action": "a2a:query",
        "source_agent": {
            "id": "orch1",
            "type": "orchestrator",
            "trust_level": "trusted",
            "environment": "production",
            "rate_limit_per_minute": 10000
        },
        "target_agent": {
            "id": "worker1",
            "type": "worker",
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {
            "rate_limit": {"current_count": 100}
        }
    }
}

test_audit_reason_denied_untrusted if {
    contains(audit_reason, "untrusted source") with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "untrusted",
            "environment": "production",
            "type": "worker"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "trusted",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

test_audit_reason_denied_cross_env if {
    contains(audit_reason, "cross-environment blocked") with input as {
        "action": "a2a:communicate",
        "source_agent": {
            "id": "agent1",
            "trust_level": "verified",
            "environment": "development",
            "type": "service"
        },
        "target_agent": {
            "id": "agent2",
            "trust_level": "verified",
            "environment": "production",
            "type": "worker"
        },
        "context": {}
    }
}

# ============================================================================
# EDGE CASES
# ============================================================================

test_empty_capabilities_blocks_execute if {
    not allow with input as {
        "action": "a2a:execute",
        "source_agent": {
            "id": "agent1",
            "type": "service",
            "capabilities": [],
            "trust_level": "trusted",
            "environment": "production"
        },
        "target_agent": {
            "id": "agent2",
            "type": "worker",
            "accepts_execution": true,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}

test_target_not_accepting_execution_blocks if {
    not allow with input as {
        "action": "a2a:execute",
        "source_agent": {
            "id": "agent1",
            "type": "service",
            "capabilities": ["execute"],
            "trust_level": "trusted",
            "environment": "production"
        },
        "target_agent": {
            "id": "agent2",
            "type": "worker",
            "accepts_execution": false,
            "trust_level": "trusted",
            "environment": "production"
        },
        "context": {}
    }
}
