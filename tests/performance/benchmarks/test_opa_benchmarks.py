"""
OPA Engine Performance Benchmarks.

Compares performance of Rust-based Regorus engine vs HTTP-based Python OPA client.

Acceptance Criteria:
- OPA Rust p95 latency <5ms
- Rust 4-10x faster than Python (HTTP OPA)
"""

import pytest

from sark.services.policy.opa_client import AuthorizationInput

# ==============================================================================
# Simple Policy Benchmarks (RBAC)
# ==============================================================================


@pytest.mark.benchmark(group="opa-simple")
@pytest.mark.asyncio
async def test_opa_rust_simple_policy(benchmark, rust_opa_client, simple_policy_input):
    """
    Benchmark Rust OPA with simple RBAC policy.

    Target: <5ms p95 latency
    """

    async def evaluate():
        return await rust_opa_client.evaluate_policy(
            auth_input=simple_policy_input,
            use_cache=False,  # Bypass cache to test engine directly
        )

    # Run benchmark
    result = benchmark(lambda: pytest.helpers.run_async(evaluate))

    # Verify result
    assert result is not None


@pytest.mark.benchmark(group="opa-simple")
@pytest.mark.asyncio
async def test_opa_python_simple_policy(benchmark, http_opa_client, simple_policy_input):
    """
    Benchmark HTTP OPA with simple RBAC policy.

    Baseline for comparison with Rust implementation.
    """

    async def evaluate():
        return await http_opa_client.evaluate_policy(
            auth_input=simple_policy_input,
            use_cache=False,
        )

    # Run benchmark
    result = benchmark(lambda: pytest.helpers.run_async(evaluate))

    # Verify result
    assert result is not None


# ==============================================================================
# Complex Policy Benchmarks (Multi-tenant with nesting)
# ==============================================================================


@pytest.mark.benchmark(group="opa-complex")
@pytest.mark.asyncio
async def test_opa_rust_complex_policy(benchmark, rust_opa_client, complex_policy_input):
    """
    Benchmark Rust OPA with complex multi-tenant policy.

    Tests performance with nested resources, multiple context attributes,
    and complex rule evaluation.

    Target: <5ms p95 latency even for complex policies
    """

    async def evaluate():
        return await rust_opa_client.evaluate_policy(
            auth_input=complex_policy_input,
            use_cache=False,
        )

    # Run benchmark
    result = benchmark(lambda: pytest.helpers.run_async(evaluate))

    # Verify result
    assert result is not None


@pytest.mark.benchmark(group="opa-complex")
@pytest.mark.asyncio
async def test_opa_python_complex_policy(benchmark, http_opa_client, complex_policy_input):
    """
    Benchmark HTTP OPA with complex multi-tenant policy.

    Baseline for comparison with Rust implementation.
    Expected to be 4-10x slower than Rust.
    """

    async def evaluate():
        return await http_opa_client.evaluate_policy(
            auth_input=complex_policy_input,
            use_cache=False,
        )

    # Run benchmark
    result = benchmark(lambda: pytest.helpers.run_async(evaluate))

    # Verify result
    assert result is not None


# ==============================================================================
# Varying Policy Complexity Benchmarks
# ==============================================================================


@pytest.mark.benchmark(group="opa-complexity-scaling")
@pytest.mark.asyncio
async def test_opa_rust_small_policy(benchmark, rust_opa_client):
    """Benchmark Rust OPA with minimal policy (single rule)."""
    auth_input = AuthorizationInput(
        user_id="user-test",
        action="read",
        resource="public-resource",
        context={},
    )

    async def evaluate():
        return await rust_opa_client.evaluate_policy(
            auth_input=auth_input,
            use_cache=False,
        )

    result = benchmark(lambda: pytest.helpers.run_async(evaluate))
    assert result is not None


@pytest.mark.benchmark(group="opa-complexity-scaling")
@pytest.mark.asyncio
async def test_opa_rust_medium_policy(benchmark, rust_opa_client):
    """Benchmark Rust OPA with medium policy (5-10 rules)."""
    auth_input = AuthorizationInput(
        user_id="user-test",
        action="write",
        resource="team:alpha:document:123",
        context={
            "role": "editor",
            "team_id": "alpha",
        },
    )

    async def evaluate():
        return await rust_opa_client.evaluate_policy(
            auth_input=auth_input,
            use_cache=False,
        )

    result = benchmark(lambda: pytest.helpers.run_async(evaluate))
    assert result is not None


@pytest.mark.benchmark(group="opa-complexity-scaling")
@pytest.mark.asyncio
async def test_opa_rust_large_policy(benchmark, rust_opa_client):
    """Benchmark Rust OPA with large policy (20+ rules with nesting)."""
    auth_input = AuthorizationInput(
        user_id="user-test",
        action="admin",
        resource="org:acme:dept:eng:team:backend:project:api:env:prod",
        context={
            "role": "admin",
            "org_id": "acme",
            "dept_id": "eng",
            "team_id": "backend",
            "clearance_level": 5,
            "mfa_verified": True,
            "ip_allowlist": ["192.168.1.0/24"],
        },
    )

    async def evaluate():
        return await rust_opa_client.evaluate_policy(
            auth_input=auth_input,
            use_cache=False,
        )

    result = benchmark(lambda: pytest.helpers.run_async(evaluate))
    assert result is not None


# ==============================================================================
# Batch Evaluation Benchmarks
# ==============================================================================


@pytest.mark.benchmark(group="opa-batch")
@pytest.mark.asyncio
async def test_opa_rust_batch_evaluation(benchmark, rust_opa_client):
    """
    Benchmark Rust OPA batch evaluation (10 requests).

    Tests throughput when evaluating multiple policies in parallel.
    """
    auth_inputs = [
        AuthorizationInput(
            user_id=f"user-{i}",
            action="read",
            resource=f"document-{i}",
            context={"role": "viewer"},
        )
        for i in range(10)
    ]

    async def evaluate_batch():
        results = []
        for auth_input in auth_inputs:
            result = await rust_opa_client.evaluate_policy(
                auth_input=auth_input,
                use_cache=False,
            )
            results.append(result)
        return results

    results = benchmark(lambda: pytest.helpers.run_async(evaluate_batch))
    assert len(results) == 10


@pytest.mark.benchmark(group="opa-batch")
@pytest.mark.asyncio
async def test_opa_python_batch_evaluation(benchmark, http_opa_client):
    """
    Benchmark Python OPA batch evaluation (10 requests).

    Baseline for comparison with Rust implementation.
    """
    auth_inputs = [
        AuthorizationInput(
            user_id=f"user-{i}",
            action="read",
            resource=f"document-{i}",
            context={"role": "viewer"},
        )
        for i in range(10)
    ]

    async def evaluate_batch():
        results = []
        for auth_input in auth_inputs:
            result = await http_opa_client.evaluate_policy(
                auth_input=auth_input,
                use_cache=False,
            )
            results.append(result)
        return results

    results = benchmark(lambda: pytest.helpers.run_async(evaluate_batch))
    assert len(results) == 10


# ==============================================================================
# Concurrent Evaluation Benchmarks
# ==============================================================================


@pytest.mark.benchmark(group="opa-concurrent")
@pytest.mark.asyncio
async def test_opa_rust_concurrent_10(benchmark, rust_opa_client):
    """
    Benchmark Rust OPA with 10 concurrent evaluations.

    Tests how well the engine handles concurrent load.
    """
    import asyncio

    auth_inputs = [
        AuthorizationInput(
            user_id=f"user-{i}",
            action="read",
            resource=f"document-{i}",
            context={"role": "viewer"},
        )
        for i in range(10)
    ]

    async def evaluate_concurrent():
        tasks = [
            rust_opa_client.evaluate_policy(auth_input=auth_input, use_cache=False)
            for auth_input in auth_inputs
        ]
        return await asyncio.gather(*tasks)

    results = benchmark(lambda: pytest.helpers.run_async(evaluate_concurrent))
    assert len(results) == 10


@pytest.mark.benchmark(group="opa-concurrent")
@pytest.mark.asyncio
async def test_opa_rust_concurrent_100(benchmark, rust_opa_client):
    """
    Benchmark Rust OPA with 100 concurrent evaluations.

    Tests scalability under heavy concurrent load.
    """
    import asyncio

    auth_inputs = [
        AuthorizationInput(
            user_id=f"user-{i}",
            action="read",
            resource=f"document-{i}",
            context={"role": "viewer"},
        )
        for i in range(100)
    ]

    async def evaluate_concurrent():
        tasks = [
            rust_opa_client.evaluate_policy(auth_input=auth_input, use_cache=False)
            for auth_input in auth_inputs
        ]
        return await asyncio.gather(*tasks)

    results = benchmark(lambda: pytest.helpers.run_async(evaluate_concurrent))
    assert len(results) == 100


@pytest.mark.benchmark(group="opa-concurrent")
@pytest.mark.asyncio
async def test_opa_rust_concurrent_1000(benchmark, rust_opa_client):
    """
    Benchmark Rust OPA with 1000 concurrent evaluations.

    Stress test to find performance limits.
    """
    import asyncio

    auth_inputs = [
        AuthorizationInput(
            user_id=f"user-{i}",
            action="read",
            resource=f"document-{i}",
            context={"role": "viewer"},
        )
        for i in range(1000)
    ]

    async def evaluate_concurrent():
        tasks = [
            rust_opa_client.evaluate_policy(auth_input=auth_input, use_cache=False)
            for auth_input in auth_inputs
        ]
        return await asyncio.gather(*tasks)

    results = benchmark(lambda: pytest.helpers.run_async(evaluate_concurrent))
    assert len(results) == 1000


# ==============================================================================
# Helpers
# ==============================================================================


@pytest.helpers.register
def run_async(coro):
    """Helper to run async functions in benchmarks."""
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro())
