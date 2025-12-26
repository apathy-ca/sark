"""Complex Tool Chain Integration Tests.

Tests for tools that call other tools (nested invocations),
circular dependency detection, timeout handling, and failure recovery.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_nested_tool_invocations(app_client, mock_user_token):
    """Test tools that call other tools (nested invocations)."""

    # Tool A calls Tool B which calls Tool C
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "tool-a",
            "parameters": {
                "call_chain": ["tool-b", "tool-c"],
                "depth": 3,
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["allow"] is True
    assert "execution_chain" in data
    assert len(data["execution_chain"]) == 3
    assert data["execution_chain"] == ["tool-a", "tool-b", "tool-c"]


async def test_circular_dependency_detection(app_client, mock_user_token):
    """Test circular dependency detection in tool chains."""

    # Tool A -> Tool B -> Tool C -> Tool A (circular)
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "circular-tool-a",
            "parameters": {
                "next_tool": "circular-tool-b",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should detect circular dependency and deny
    assert response.status_code == 200
    data = response.json()

    assert data["allow"] is False
    assert "circular dependency" in data.get("reason", "").lower()


async def test_tool_chain_depth_limit(app_client, mock_user_token):
    """Test maximum depth limit for tool chains."""

    # Attempt very deep chain (> max depth)
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "deep-tool",
            "parameters": {
                "depth": 20,  # Exceeds max depth
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should be denied or truncated
    if data["allow"]:
        assert data.get("depth_limited") is True
        assert len(data.get("execution_chain", [])) <= 10  # Max depth
    else:
        assert "depth limit" in data.get("reason", "").lower()


async def test_tool_chain_timeout_handling(app_client, mock_user_token):
    """Test timeout handling in tool chains."""

    # Invoke chain with slow tool
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "slow-tool-chain",
            "parameters": {
                "chain": ["fast-tool", "very-slow-tool", "fast-tool"],
                "timeout": 5,  # 5 second timeout
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should timeout and return partial results
    assert response.status_code == 200
    data = response.json()

    assert "timeout" in data.get("status", "").lower() or data.get("timed_out") is True
    assert "execution_chain" in data
    # Partial execution should be recorded
    assert len(data["execution_chain"]) < 3


async def test_partial_chain_failure_recovery(app_client, mock_user_token):
    """Test recovery when part of tool chain fails."""

    # Chain: Tool A -> Tool B (fails) -> Tool C
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "resilient-chain",
            "parameters": {
                "chain": ["tool-a", "failing-tool-b", "tool-c"],
                "recovery_strategy": "continue_on_error",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should indicate partial failure
    assert "failed_steps" in data
    assert "failing-tool-b" in data["failed_steps"]
    # But chain should continue
    assert "tool-c" in data.get("execution_chain", [])


async def test_tool_chain_with_conditional_branches(app_client, mock_user_token):
    """Test tool chains with conditional branching."""

    # Tool A -> (if condition) Tool B else Tool C
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "conditional-tool",
            "parameters": {
                "condition": "high_priority",
                "if_true": "urgent-tool",
                "if_false": "standard-tool",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["allow"] is True
    assert "execution_path" in data
    # Should have taken one branch
    executed_tools = data.get("execution_chain", [])
    assert "urgent-tool" in executed_tools or "standard-tool" in executed_tools
    # But not both
    assert not ("urgent-tool" in executed_tools and "standard-tool" in executed_tools)


async def test_parallel_tool_execution(app_client, mock_user_token):
    """Test parallel execution of independent tools."""

    # Fan-out: Tool A -> [Tool B, Tool C, Tool D] (parallel) -> Tool E (fan-in)
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "parallel-orchestrator",
            "parameters": {
                "parallel_tools": ["tool-b", "tool-c", "tool-d"],
                "aggregator": "tool-e",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["allow"] is True
    # All parallel tools should execute
    parallel_results = data.get("parallel_results", [])
    assert len(parallel_results) == 3
    # Final aggregator should run
    assert data.get("final_step") == "tool-e"


async def test_tool_chain_resource_limits(app_client, mock_user_token):
    """Test resource limit enforcement in tool chains."""

    # Chain that would exceed resource limits
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "resource-intensive-chain",
            "parameters": {
                "chain": [f"heavy-tool-{i}" for i in range(50)],
                "max_memory_mb": 100,
                "max_cpu_seconds": 10,
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    # Should be limited or denied
    assert response.status_code == 200
    data = response.json()

    if not data["allow"]:
        assert "resource limit" in data.get("reason", "").lower()
    else:
        # Execution should be throttled
        assert data.get("resource_limited") is True


async def test_tool_chain_state_management(app_client, mock_user_token):
    """Test state management across tool chain execution."""

    # Chain that maintains state across tools
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "stateful-chain",
            "parameters": {
                "initial_state": {"counter": 0, "items": []},
                "chain": ["increment-tool", "add-item-tool", "increment-tool"],
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # State should be preserved and modified
    final_state = data.get("final_state", {})
    assert final_state.get("counter") == 2  # Incremented twice
    assert len(final_state.get("items", [])) == 1  # One item added


async def test_tool_chain_transaction_rollback(app_client, mock_user_token):
    """Test transaction rollback on chain failure."""

    # Chain with transactional semantics
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "transactional-chain",
            "parameters": {
                "chain": ["create-resource", "modify-resource", "failing-step"],
                "transaction": True,
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should indicate rollback occurred
    assert data.get("rolled_back") is True
    assert data.get("committed_changes") is False


async def test_tool_chain_retry_logic(app_client, mock_user_token):
    """Test retry logic for transient failures in chains."""

    # Chain with flaky tool that might fail
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "retry-chain",
            "parameters": {
                "chain": ["reliable-tool", "flaky-tool", "reliable-tool"],
                "retry_strategy": {
                    "max_attempts": 3,
                    "backoff": "exponential",
                },
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check retry metadata
    if "retry_metadata" in data:
        assert data["retry_metadata"].get("flaky-tool", {}).get("attempts") <= 3


async def test_tool_chain_dynamic_routing(app_client, mock_user_token):
    """Test dynamic routing based on intermediate results."""

    # Chain that routes based on data from previous tool
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "router-tool",
            "parameters": {
                "routing_logic": {
                    "evaluate": "classification-tool",
                    "routes": {
                        "type_a": ["handler-a-1", "handler-a-2"],
                        "type_b": ["handler-b-1", "handler-b-2"],
                    },
                },
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "route_taken" in data
    assert "execution_chain" in data
    # Chain should follow one of the defined routes
    route = data["route_taken"]
    assert route in ["type_a", "type_b"]


async def test_tool_chain_caching(app_client, mock_user_token):
    """Test caching of tool results in chains."""

    # First execution - cache miss
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "cached-chain",
            "parameters": {
                "chain": ["expensive-tool-1", "expensive-tool-2"],
                "enable_cache": True,
                "cache_key": "test-chain-123",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response1.status_code == 200
    first_duration = response1.json().get("duration_ms", 0)

    # Second execution with same key - cache hit
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "cached-chain",
            "parameters": {
                "chain": ["expensive-tool-1", "expensive-tool-2"],
                "enable_cache": True,
                "cache_key": "test-chain-123",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response2.status_code == 200
    data = response2.json()

    # Should indicate cache hit
    assert data.get("cache_hit") is True
    # Should be faster
    second_duration = data.get("duration_ms", 0)
    if first_duration > 0 and second_duration > 0:
        assert second_duration < first_duration


async def test_tool_chain_error_propagation(app_client, mock_user_token):
    """Test error propagation through tool chains."""

    # Chain where error occurs in middle
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "chain-server",
            "tool_name": "error-chain",
            "parameters": {
                "chain": ["tool-1", "error-tool", "tool-3"],
                "error_handling": "propagate",
            },
        },
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Error should be captured
    assert "error" in data
    assert data["error"]["tool"] == "error-tool"
    # Subsequent tools should not execute
    assert len(data.get("execution_chain", [])) == 2  # Only tool-1 and error-tool
