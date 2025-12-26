"""
OPA Integration Tests with Real Docker OPA Server.

This module tests policy evaluation using a real OPA Docker instance,
replacing mocked tests with actual integration tests against OPA.

Tests include:
- Policy uploading and management
- Authorization decisions
- Gateway tool invocation authorization
- Server registration policies
- Fail-closed behavior
- Policy caching and performance
- Context enrichment
- Multi-policy evaluation
"""

import asyncio
import time
from uuid import uuid4

import httpx
import pytest

# Enable Docker fixtures
pytest_plugins = ["tests.fixtures.integration_docker"]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def sample_policies():
    """Sample OPA policies for testing."""
    return {
        "gateway_allow_all": """
            package sark.gateway

            default allow = false

            allow {
                input.action == "gateway:tool:invoke"
            }
        """,
        "gateway_role_based": """
            package sark.gateway

            default allow = false

            allow {
                input.action == "gateway:tool:invoke"
                input.user.role == "admin"
            }

            allow {
                input.action == "gateway:tool:read"
            }
        """,
        "server_sensitivity": """
            package sark.server

            default allow = false

            allow {
                input.action == "register"
                input.resource.sensitivity == "low"
            }

            allow {
                input.action == "register"
                input.resource.sensitivity == "medium"
                input.user.role == "developer"
            }

            allow {
                input.action == "register"
                input.resource.sensitivity == "high"
                input.user.role == "admin"
            }
        """,
        "tool_parameters_filter": """
            package sark.gateway

            import future.keywords.if

            default allow = false
            default filtered_parameters = null

            allow if {
                input.action == "gateway:tool:invoke"
            }

            filtered_parameters := filtered if {
                input.action == "gateway:tool:invoke"
                input.tool.name == "search_database"
                # Remove sensitive fields from parameters
                filtered := object.remove(input.parameters, ["password", "secret", "token"])
            }
        """,
        "fail_closed_test": """
            package sark.gateway

            default allow = false
            default reason = "Default deny - no matching rule"

            allow {
                input.action == "gateway:tool:invoke"
                input.server.name == "allowed-server"
            }

            reason := "Server not in allowlist" {
                input.action == "gateway:tool:invoke"
                not input.server.name == "allowed-server"
            }
        """,
    }


@pytest.fixture
async def load_policy(opa_client):
    """Helper fixture to load policies into OPA."""

    async def _load_policy(policy_name: str, policy_content: str):
        """Load a policy into OPA.

        Args:
            policy_name: Policy identifier
            policy_content: Rego policy content
        """
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{opa_client.opa_url}/v1/policies/{policy_name}",
                data=policy_content,
                headers={"Content-Type": "text/plain"},
            )
            response.raise_for_status()
            return response.json()

    return _load_policy


# =============================================================================
# OPA Connection and Health Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_opa_health_check(opa_client):
    """Test OPA server is healthy and responsive."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{opa_client.opa_url}/health")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_opa_server_info(opa_service):
    """Test OPA server connection details."""
    assert opa_service["host"] == "localhost"
    assert opa_service["port"] == 8181
    assert "url" in opa_service


# =============================================================================
# Policy Upload and Management Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_simple_policy(opa_client, load_policy, sample_policies):
    """Test uploading a simple policy to OPA."""
    policy_name = "test_simple_allow"
    policy_content = sample_policies["gateway_allow_all"]

    result = await load_policy(policy_name, policy_content)

    # Verify policy was uploaded
    assert result is not None

    # Test policy decision
    decision = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "test-user"},
        }
    )

    assert decision.allow is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_role_based_policy(opa_client, load_policy, sample_policies):
    """Test uploading and evaluating role-based access policy."""
    policy_name = "test_role_based"
    policy_content = sample_policies["gateway_role_based"]

    await load_policy(policy_name, policy_content)

    # Admin should be allowed to invoke
    decision_admin = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "admin-user", "role": "admin"},
        }
    )
    assert decision_admin.allow is True

    # Regular user should be denied for invoke
    decision_user = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "regular-user", "role": "user"},
        }
    )
    assert decision_user.allow is False

    # But allowed for read
    decision_read = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:read",
            "user": {"id": "regular-user", "role": "user"},
        }
    )
    assert decision_read.allow is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_policies(opa_client, load_policy, sample_policies):
    """Test listing policies from OPA."""
    # Upload multiple policies
    await load_policy("policy_1", sample_policies["gateway_allow_all"])
    await load_policy("policy_2", sample_policies["gateway_role_based"])

    # List policies
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{opa_client.opa_url}/v1/policies")
        assert response.status_code == 200

        policies = response.json()
        assert "result" in policies
        assert len(policies["result"]) >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_policy(opa_client, load_policy, sample_policies):
    """Test deleting a policy from OPA."""
    policy_name = "test_delete_me"

    # Upload policy
    await load_policy(policy_name, sample_policies["gateway_allow_all"])

    # Delete policy
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{opa_client.opa_url}/v1/policies/{policy_name}")
        assert response.status_code == 200


# =============================================================================
# Gateway Authorization Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_tool_invocation_authorization(opa_client, load_policy, sample_policies):
    """Test authorization for gateway tool invocation."""
    await load_policy("gateway_auth", sample_policies["gateway_allow_all"])

    # Test allowed tool invocation
    decision = await opa_client.evaluate_gateway_policy(
        user_context={"id": str(uuid4()), "role": "developer"},
        action="gateway:tool:invoke",
        server={"name": "test-server", "sensitivity": "medium"},
        tool={"name": "query_database", "parameters": {"query": "SELECT 1"}},
        context={"timestamp": int(time.time())},
    )

    assert decision.allow is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_authorization_with_reason(opa_client, load_policy, sample_policies):
    """Test that denied requests include a reason."""
    await load_policy("fail_closed", sample_policies["fail_closed_test"])

    # Test denied invocation (server not in allowlist)
    decision = await opa_client.evaluate_gateway_policy(
        user_context={"id": str(uuid4()), "role": "user"},
        action="gateway:tool:invoke",
        server={"name": "blocked-server"},
        tool={"name": "dangerous_tool"},
        context={},
    )

    assert decision.allow is False
    assert decision.reason is not None
    assert len(decision.reason) > 0


# =============================================================================
# Server Registration Policy Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_server_sensitivity_level_policy(opa_client, load_policy, sample_policies):
    """Test server registration based on sensitivity level."""
    await load_policy("server_policy", sample_policies["server_sensitivity"])

    # Low sensitivity - everyone can register
    decision_low = await opa_client.evaluate_policy(
        {
            "action": "register",
            "user": {"id": "user123", "role": "user"},
            "resource": {"type": "server", "sensitivity": "low"},
        }
    )
    assert decision_low.allow is True

    # Medium sensitivity - developers and admins only
    decision_med_dev = await opa_client.evaluate_policy(
        {
            "action": "register",
            "user": {"id": "dev123", "role": "developer"},
            "resource": {"type": "server", "sensitivity": "medium"},
        }
    )
    assert decision_med_dev.allow is True

    # Medium sensitivity - regular user denied
    decision_med_user = await opa_client.evaluate_policy(
        {
            "action": "register",
            "user": {"id": "user123", "role": "user"},
            "resource": {"type": "server", "sensitivity": "medium"},
        }
    )
    assert decision_med_user.allow is False

    # High sensitivity - admins only
    decision_high_admin = await opa_client.evaluate_policy(
        {
            "action": "register",
            "user": {"id": "admin123", "role": "admin"},
            "resource": {"type": "server", "sensitivity": "high"},
        }
    )
    assert decision_high_admin.allow is True

    # High sensitivity - developer denied
    decision_high_dev = await opa_client.evaluate_policy(
        {
            "action": "register",
            "user": {"id": "dev123", "role": "developer"},
            "resource": {"type": "server", "sensitivity": "high"},
        }
    )
    assert decision_high_dev.allow is False


# =============================================================================
# Parameter Filtering Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parameter_filtering_policy(opa_client, load_policy, sample_policies):
    """Test policy that filters sensitive parameters."""
    await load_policy("param_filter", sample_policies["tool_parameters_filter"])

    # Invoke with sensitive parameters
    input_data = {
        "action": "gateway:tool:invoke",
        "user": {"id": "user123"},
        "tool": {"name": "search_database"},
        "parameters": {
            "query": "SELECT *",
            "password": "secret123",  # Should be filtered
            "secret": "api_key",  # Should be filtered
            "limit": 10,  # Should remain
        },
    }

    # Make direct OPA query to check filtered_parameters
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{opa_client.opa_url}/v1/data/sark/gateway",
            json={"input": input_data},
        )
        result = response.json()["result"]

        assert result["allow"] is True

        # Check that sensitive fields were filtered
        if "filtered_parameters" in result:
            filtered = result["filtered_parameters"]
            assert "password" not in filtered
            assert "secret" not in filtered
            assert "query" in filtered
            assert "limit" in filtered


# =============================================================================
# Performance and Caching Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_policy_evaluation_performance(opa_client, load_policy, sample_policies):
    """Test policy evaluation performance."""
    await load_policy("perf_test", sample_policies["gateway_allow_all"])

    # Warm up
    await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "test-user"},
        }
    )

    # Measure multiple evaluations
    start_time = time.perf_counter()
    iterations = 100

    for i in range(iterations):
        decision = await opa_client.evaluate_policy(
            {
                "action": "gateway:tool:invoke",
                "user": {"id": f"user-{i}"},
            }
        )
        assert decision.allow is True

    elapsed = (time.perf_counter() - start_time) * 1000  # ms
    avg_latency = elapsed / iterations

    print("\nOPA evaluation performance:")
    print(f"  Total: {elapsed:.2f}ms for {iterations} evaluations")
    print(f"  Average: {avg_latency:.2f}ms per evaluation")
    print(f"  Throughput: {iterations / (elapsed / 1000):.2f} req/s")

    # Should be fast (< 10ms average)
    assert avg_latency < 10, f"Average latency {avg_latency}ms is too slow"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_policy_evaluations(opa_client, load_policy, sample_policies):
    """Test concurrent policy evaluations."""
    import asyncio

    await load_policy("concurrent_test", sample_policies["gateway_role_based"])

    # Create many concurrent evaluation tasks
    async def evaluate(user_id: str, role: str):
        return await opa_client.evaluate_policy(
            {
                "action": "gateway:tool:invoke",
                "user": {"id": user_id, "role": role},
            }
        )

    tasks = [evaluate(f"user-{i}", "admin" if i % 2 == 0 else "user") for i in range(50)]

    start_time = time.perf_counter()
    results = await asyncio.gather(*tasks)
    elapsed = (time.perf_counter() - start_time) * 1000

    # Check results
    assert len(results) == 50
    # Admin users (even IDs) should be allowed
    for i, decision in enumerate(results):
        if i % 2 == 0:  # Admin
            assert decision.allow is True
        else:  # Regular user
            assert decision.allow is False

    print(f"\nConcurrent evaluations: {len(tasks)} completed in {elapsed:.2f}ms")
    print(f"Throughput: {len(tasks) / (elapsed / 1000):.2f} req/s")


# =============================================================================
# Fail-Closed Behavior Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fail_closed_on_invalid_policy(opa_client):
    """Test fail-closed behavior when policy doesn't exist."""
    # Query non-existent policy package
    decision = await opa_client.evaluate_policy(
        {"action": "test"}, policy_path="sark/nonexistent_package"
    )

    # Should fail closed (deny)
    assert decision.allow is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fail_closed_on_network_error(opa_client):
    """Test fail-closed behavior when OPA is unreachable."""
    # Create OPA client with wrong URL
    from sark.services.policy.opa_client import OPAClient

    bad_client = OPAClient(opa_url="http://localhost:9999")  # Wrong port

    decision = await bad_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "test"},
        }
    )

    # Should fail closed (deny)
    assert decision.allow is False


# =============================================================================
# Complex Policy Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_enriched_policy(opa_client, load_policy):
    """Test policy with enriched context (time, location, etc.)."""
    policy_content = """
        package sark.gateway

        import future.keywords.if

        default allow = false

        allow if {
            input.action == "gateway:tool:invoke"
            input.context.time_of_day == "business_hours"
            input.context.location == "office"
        }

        allow if {
            input.action == "gateway:tool:invoke"
            input.user.role == "admin"
        }
    """

    await load_policy("context_policy", policy_content)

    # Test with proper context - should allow
    decision_allowed = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "user123", "role": "user"},
            "context": {
                "time_of_day": "business_hours",
                "location": "office",
            },
        }
    )
    assert decision_allowed.allow is True

    # Test with wrong context - should deny
    decision_denied = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "user123", "role": "user"},
            "context": {
                "time_of_day": "night",
                "location": "remote",
            },
        }
    )
    assert decision_denied.allow is False

    # Admin should always be allowed regardless of context
    decision_admin = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "admin123", "role": "admin"},
            "context": {
                "time_of_day": "night",
                "location": "remote",
            },
        }
    )
    assert decision_admin.allow is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_resource_policy(opa_client, load_policy):
    """Test policy evaluating multiple resources."""
    policy_content = """
        package sark.gateway

        import future.keywords.if

        default allow = false

        allow if {
            input.action == "gateway:tool:invoke"
            input.server.name in ["approved-server-1", "approved-server-2", "approved-server-3"]
        }
    """

    await load_policy("multi_resource", policy_content)

    # Test approved servers
    for server_name in ["approved-server-1", "approved-server-2", "approved-server-3"]:
        decision = await opa_client.evaluate_policy(
            {
                "action": "gateway:tool:invoke",
                "server": {"name": server_name},
            }
        )
        assert decision.allow is True, f"Server {server_name} should be allowed"

    # Test unapproved server
    decision_denied = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "server": {"name": "unknown-server"},
        }
    )
    assert decision_denied.allow is False


# =============================================================================
# Policy Update and Versioning Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_policy_hot_reload(opa_client, load_policy, sample_policies):
    """Test policy hot reload (update without restart)."""
    policy_name = "hot_reload_test"

    # Load initial policy (allow all)
    await load_policy(policy_name, sample_policies["gateway_allow_all"])

    # Test that it allows
    decision1 = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "test", "role": "user"},
        }
    )
    assert decision1.allow is True

    # Update policy (deny all)
    new_policy = """
        package sark.gateway

        default allow = false
    """
    await load_policy(policy_name, new_policy)

    # Give OPA a moment to reload
    await asyncio.sleep(0.1)

    # Test that it now denies
    decision2 = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "user": {"id": "test", "role": "user"},
        }
    )
    assert decision2.allow is False


# =============================================================================
# Data API Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_opa_data_api(opa_client):
    """Test OPA Data API for storing and retrieving data."""
    # Store data
    async with httpx.AsyncClient() as client:
        # Put data
        await client.put(
            f"{opa_client.opa_url}/v1/data/sark/servers/allowed_list",
            json=["server1", "server2", "server3"],
        )

        # Retrieve data
        response = await client.get(f"{opa_client.opa_url}/v1/data/sark/servers/allowed_list")
        assert response.status_code == 200

        result = response.json()
        assert result["result"] == ["server1", "server2", "server3"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_policy_with_external_data(opa_client, load_policy):
    """Test policy that uses external data from OPA's data API."""
    # Load data
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{opa_client.opa_url}/v1/data/sark/allowlist",
            json={"servers": ["approved-1", "approved-2"]},
        )

    # Load policy that references data
    policy_content = """
        package sark.gateway

        import data.sark.allowlist
        import future.keywords.if

        default allow = false

        allow if {
            input.action == "gateway:tool:invoke"
            input.server.name in allowlist.servers
        }
    """

    await load_policy("data_driven", policy_content)

    # Test with allowed server
    decision_allowed = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "server": {"name": "approved-1"},
        }
    )
    assert decision_allowed.allow is True

    # Test with blocked server
    decision_denied = await opa_client.evaluate_policy(
        {
            "action": "gateway:tool:invoke",
            "server": {"name": "unapproved-server"},
        }
    )
    assert decision_denied.allow is False
