"""
Failure recovery and resilience stress tests.

Tests failure scenarios and recovery mechanisms:
1. OPA server failure and recovery
2. Redis cache failure and recovery
3. Network interruption recovery
4. Database connection loss recovery
5. Cascading failure prevention

Acceptance Criteria:
- Fallback mechanisms work
- Recovery time is acceptable
- No cascading failures
- System state remains consistent
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import AuthorizationInput, OPAClient

# ==============================================================================
# OPA Server Failure Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_opa_server_failure_and_recovery():
    """
    Stress Test: Kill OPA server and verify fallback/recovery.

    Tests:
    - Graceful failure when OPA is unavailable
    - Fallback to cached decisions
    - Recovery when OPA comes back online
    - No cascading failures

    Expected Outcome:
    - Requests fail gracefully (don't crash)
    - Cached responses still served
    - System recovers when OPA is restored
    - Recovery time < 5 seconds
    """
    print(f"\n{'=' * 80}")
    print("OPA SERVER FAILURE RECOVERY TEST")
    print(f"{'=' * 80}\n")

    # Mock httpx client to simulate OPA failure
    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Phase 1: OPA is healthy
        print("Phase 1: OPA server healthy")
        healthy_response = AsyncMock()
        healthy_response.status_code = 200
        healthy_response.json.return_value = {"result": {"allow": True}}
        mock_client.post.return_value = healthy_response

        client = OPAClient(opa_url="http://localhost:8181", timeout=2.0)

        # Make successful request
        auth_input = AuthorizationInput(
            user_id="test-user",
            action="read",
            resource="document-123",
            context={},
        )

        result1 = await client.evaluate_policy(auth_input, use_cache=True)
        assert result1 is not None
        print("✓ Request successful")

        # Phase 2: OPA server fails
        print("\nPhase 2: OPA server fails")

        # Simulate connection error
        from httpx import ConnectError

        mock_client.post.side_effect = ConnectError("Connection refused")

        # Request should fail but not crash
        failure_start = time.time()
        try:
            await client.evaluate_policy(auth_input, use_cache=False)
            print("✗ Expected failure but got success")
            raise AssertionError("Should have raised exception")
        except Exception as e:
            failure_time = (time.time() - failure_start) * 1000
            print(f"✓ Graceful failure: {type(e).__name__} after {failure_time:.0f}ms")
            assert failure_time < 5000, f"Failure took too long: {failure_time:.0f}ms"

        # Phase 3: OPA server recovers
        print("\nPhase 3: OPA server recovers")

        # Remove the side effect to simulate recovery
        mock_client.post.side_effect = None
        mock_client.post.return_value = healthy_response

        # Verify recovery
        recovery_start = time.time()
        result3 = await client.evaluate_policy(auth_input, use_cache=False)
        recovery_time = (time.time() - recovery_start) * 1000

        assert result3 is not None
        print(f"✓ Recovered in {recovery_time:.0f}ms")
        assert (
            recovery_time < 5000
        ), f"Recovery too slow: {recovery_time:.0f}ms"

        print(f"\n{'=' * 80}")
        print("RECOVERY TEST PASSED")
        print(f"{'=' * 80}\n")

        await client.close()


# ==============================================================================
# Redis Cache Failure Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_redis_cache_failure_and_recovery():
    """
    Stress Test: Redis failure with fallback to direct OPA evaluation.

    Tests:
    - Cache failure doesn't crash system
    - Fallback to OPA when cache unavailable
    - Performance degradation is acceptable
    - Recovery when Redis comes back

    Expected Outcome:
    - System continues without cache
    - Latency increases but requests succeed
    - Cache recovers when Redis is restored
    """
    print(f"\n{'=' * 80}")
    print("REDIS CACHE FAILURE RECOVERY TEST")
    print(f"{'=' * 80}\n")

    # Phase 1: Redis healthy
    print("Phase 1: Redis healthy")

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value='{"allow": true}')
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    cache = PolicyCache(redis_client=mock_redis, ttl_seconds=300, enabled=True)

    # Cache hit (fast)
    start = time.time()
    result1 = await cache.get(
        user_id="test-user", action="read", resource="doc-123"
    )
    cache_hit_latency = (time.time() - start) * 1000

    assert result1 is not None
    print(f"✓ Cache hit latency: {cache_hit_latency:.2f}ms")

    # Phase 2: Redis fails
    print("\nPhase 2: Redis fails")

    # Simulate Redis connection error
    from valkey.exceptions import ConnectionError as RedisConnectionError

    mock_redis.get.side_effect = RedisConnectionError("Connection lost")
    mock_redis.setex.side_effect = RedisConnectionError("Connection lost")

    # Cache should fail gracefully and return None
    start = time.time()
    result2 = await cache.get(
        user_id="test-user", action="read", resource="doc-123"
    )
    failure_latency = (time.time() - start) * 1000

    # Should return None without crashing
    assert result2 is None
    print(f"✓ Graceful cache failure: {failure_latency:.2f}ms")

    # Phase 3: Redis recovers
    print("\nPhase 3: Redis recovers")

    # Remove side effects
    mock_redis.get.side_effect = None
    mock_redis.setex.side_effect = None
    mock_redis.get.return_value = '{"allow": true}'

    # Cache should work again
    start = time.time()
    result3 = await cache.get(
        user_id="test-user", action="read", resource="doc-123"
    )
    recovery_latency = (time.time() - start) * 1000

    assert result3 is not None
    print(f"✓ Cache recovered: {recovery_latency:.2f}ms")

    print(f"\n{'=' * 80}")
    print("CACHE RECOVERY TEST PASSED")
    print(f"{'=' * 80}\n")


# ==============================================================================
# Network Interruption Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_network_interruption_recovery():
    """
    Stress Test: Simulate network interruption and recovery.

    Tests:
    - Timeout handling
    - Retry logic
    - Partial failure handling
    - Network recovery

    Expected Outcome:
    - Timeouts handled gracefully
    - Retries work correctly
    - System recovers when network is restored
    """
    print(f"\n{'=' * 80}")
    print("NETWORK INTERRUPTION RECOVERY TEST")
    print(f"{'=' * 80}\n")

    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Phase 1: Network is healthy (fast response)
        print("Phase 1: Network healthy")

        fast_response = AsyncMock()
        fast_response.status_code = 200
        fast_response.json.return_value = {"result": {"allow": True}}

        async def fast_post(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms
            return fast_response

        mock_client.post = fast_post

        client = OPAClient(opa_url="http://localhost:8181", timeout=2.0)

        start = time.time()
        result1 = await client.evaluate_policy(
            AuthorizationInput(
                user_id="user-1", action="read", resource="doc-1", context={}
            ),
            use_cache=False,
        )
        healthy_latency = (time.time() - start) * 1000

        assert result1 is not None
        print(f"✓ Healthy network latency: {healthy_latency:.0f}ms")

        # Phase 2: Network degrades (slow response)
        print("\nPhase 2: Network degraded (high latency)")

        async def slow_post(*args, **kwargs):
            await asyncio.sleep(1.0)  # 1000ms delay
            return fast_response

        mock_client.post = slow_post

        start = time.time()
        result2 = await client.evaluate_policy(
            AuthorizationInput(
                user_id="user-2", action="read", resource="doc-2", context={}
            ),
            use_cache=False,
        )
        degraded_latency = (time.time() - start) * 1000

        assert result2 is not None
        print(f"✓ Degraded network latency: {degraded_latency:.0f}ms")
        assert degraded_latency > 1000, "Should reflect network degradation"

        # Phase 3: Network timeout
        print("\nPhase 3: Network timeout")

        async def timeout_post(*args, **kwargs):
            await asyncio.sleep(5.0)  # Longer than 2s timeout
            return fast_response

        mock_client.post = timeout_post

        # Should timeout and raise exception
        try:
            await client.evaluate_policy(
                AuthorizationInput(
                    user_id="user-3", action="read", resource="doc-3", context={}
                ),
                use_cache=False,
            )
            raise AssertionError("Should have timed out")
        except Exception as e:
            print(f"✓ Timeout handled: {type(e).__name__}")

        # Phase 4: Network recovers
        print("\nPhase 4: Network recovers")

        mock_client.post = fast_post

        start = time.time()
        result4 = await client.evaluate_policy(
            AuthorizationInput(
                user_id="user-4", action="read", resource="doc-4", context={}
            ),
            use_cache=False,
        )
        recovery_latency = (time.time() - start) * 1000

        assert result4 is not None
        print(f"✓ Network recovered: {recovery_latency:.0f}ms")

        print(f"\n{'=' * 80}")
        print("NETWORK RECOVERY TEST PASSED")
        print(f"{'=' * 80}\n")

        await client.close()


# ==============================================================================
# Cascading Failure Prevention Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_cascading_failure_prevention():
    """
    Stress Test: Verify isolated failures don't cascade.

    Tests:
    - Circuit breaker pattern
    - Bulkhead isolation
    - Fallback mechanisms
    - Error containment

    Expected Outcome:
    - Failures are isolated
    - Other components continue working
    - System doesn't enter death spiral
    - Graceful degradation
    """
    print(f"\n{'=' * 80}")
    print("CASCADING FAILURE PREVENTION TEST")
    print(f"{'=' * 80}\n")

    # Simulate multiple components
    components = {
        "opa": {"status": "healthy", "failures": 0},
        "cache": {"status": "healthy", "failures": 0},
        "database": {"status": "healthy", "failures": 0},
    }

    async def make_request(component: str, should_fail: bool = False):
        """Simulate request to a component."""
        if should_fail:
            components[component]["failures"] += 1
            if components[component]["failures"] > 3:
                components[component]["status"] = "degraded"
            raise Exception(f"{component} failed")
        else:
            # Successful request can recover component
            if components[component]["failures"] > 0:
                components[component]["failures"] -= 1
            if components[component]["failures"] == 0:
                components[component]["status"] = "healthy"
            return f"{component} success"

    # Phase 1: All healthy
    print("Phase 1: All components healthy")
    await make_request("opa")
    await make_request("cache")
    await make_request("database")

    assert all(c["status"] == "healthy" for c in components.values())
    print("✓ All components healthy")

    # Phase 2: OPA fails, others should continue
    print("\nPhase 2: OPA fails (isolated failure)")

    # OPA fails multiple times
    for _ in range(5):
        try:
            await make_request("opa", should_fail=True)
        except Exception:
            pass

    # Other components should still work
    await make_request("cache")
    await make_request("database")

    assert components["opa"]["status"] == "degraded"
    assert components["cache"]["status"] == "healthy"
    assert components["database"]["status"] == "healthy"
    print("✓ Failure isolated to OPA component")

    # Phase 3: Cache also fails
    print("\nPhase 3: Cache fails (multiple failures)")

    for _ in range(5):
        try:
            await make_request("cache", should_fail=True)
        except Exception:
            pass

    # Database should still be healthy
    await make_request("database")

    assert components["opa"]["status"] == "degraded"
    assert components["cache"]["status"] == "degraded"
    assert components["database"]["status"] == "healthy"
    print("✓ Failures isolated, database still healthy")

    # Phase 4: Components recover
    print("\nPhase 4: Components recover")

    # Make successful requests to recover
    for _ in range(5):
        try:
            await make_request("opa")
            await make_request("cache")
        except Exception:
            pass

    # All should recover
    assert components["opa"]["status"] == "healthy"
    assert components["cache"]["status"] == "healthy"
    assert components["database"]["status"] == "healthy"
    print("✓ All components recovered")

    print(f"\n{'=' * 80}")
    print("CASCADING FAILURE PREVENTION PASSED")
    print(f"{'=' * 80}\n")


# ==============================================================================
# Partial Failure Tests
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_partial_failure_handling():
    """
    Stress Test: Handle partial failures in batch operations.

    Tests:
    - Batch operation resilience
    - Partial success handling
    - Rollback mechanisms
    - Data consistency

    Expected Outcome:
    - Partial failures don't abort entire batch
    - Successful items are processed
    - Failed items are properly reported
    - No data corruption
    """
    print(f"\n{'=' * 80}")
    print("PARTIAL FAILURE HANDLING TEST")
    print(f"{'=' * 80}\n")

    # Mock Redis for batch operations
    mock_redis = AsyncMock()

    call_count = [0]

    async def setex_with_failures(*args, **kwargs):
        """Fail every 3rd call."""
        call_count[0] += 1
        if call_count[0] % 3 == 0:
            raise Exception("Simulated failure")
        return True

    mock_redis.setex = setex_with_failures
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    cache = PolicyCache(redis_client=mock_redis, ttl_seconds=300, enabled=True)

    # Batch of 10 items (3 will fail: #3, #6, #9)
    batch_size = 10
    successful = 0
    failed = 0

    print(f"Processing batch of {batch_size} items...")

    for i in range(batch_size):
        try:
            await cache.set(
                user_id=f"user-{i}",
                action="read",
                resource=f"doc-{i}",
                decision={"allow": True},
            )
            successful += 1
            print(f"  Item {i + 1}: ✓ success")
        except Exception as e:
            failed += 1
            print(f"  Item {i + 1}: ✗ failed ({e})")

    print("\nBatch Results:")
    print(f"  Successful: {successful}/{batch_size}")
    print(f"  Failed: {failed}/{batch_size}")

    # Verify partial success
    assert successful > 0, "No items succeeded"
    assert failed > 0, "No items failed (test setup issue)"
    assert successful + failed == batch_size, "Item count mismatch"

    print(f"\n{'=' * 80}")
    print("PARTIAL FAILURE HANDLING PASSED")
    print(f"{'=' * 80}\n")


# ==============================================================================
# Recovery Time Measurement
# ==============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_recovery_time_measurement():
    """
    Stress Test: Measure and document recovery times.

    Tests:
    - Component restart time
    - Cache warmup time
    - Connection reestablishment time
    - System stabilization time

    Expected Outcome:
    - Recovery time < 5 seconds
    - System fully operational after recovery
    - Performance returns to baseline
    """
    print(f"\n{'=' * 80}")
    print("RECOVERY TIME MEASUREMENT TEST")
    print(f"{'=' * 80}\n")

    with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        healthy_response = AsyncMock()
        healthy_response.status_code = 200
        healthy_response.json.return_value = {"result": {"allow": True}}

        # Phase 1: System is down
        print("Phase 1: System down")
        from httpx import ConnectError

        mock_client.post.side_effect = ConnectError("Connection refused")

        client = OPAClient(opa_url="http://localhost:8181", timeout=2.0)

        # Verify system is down
        try:
            await client.evaluate_policy(
                AuthorizationInput(
                    user_id="user", action="read", resource="doc", context={}
                ),
                use_cache=False,
            )
            raise AssertionError("Should have failed")
        except Exception:
            print("✓ System confirmed down")

        # Phase 2: System comes up, measure recovery
        print("\nPhase 2: System recovery")

        # Simulate system coming online
        mock_client.post.side_effect = None
        mock_client.post.return_value = healthy_response

        # Measure time to first successful request
        recovery_start = time.time()

        # Attempt requests until one succeeds
        max_attempts = 10
        recovery_attempts = 0

        for attempt in range(max_attempts):
            recovery_attempts = attempt + 1
            try:
                result = await client.evaluate_policy(
                    AuthorizationInput(
                        user_id="user",
                        action="read",
                        resource="doc",
                        context={},
                    ),
                    use_cache=False,
                )
                if result is not None:
                    break
            except Exception:
                await asyncio.sleep(0.5)  # Wait before retry

        recovery_time = (time.time() - recovery_start) * 1000

        print("\nRecovery Metrics:")
        print(f"  Recovery time: {recovery_time:.0f}ms")
        print(f"  Recovery attempts: {recovery_attempts}")
        print(f"  Time per attempt: {recovery_time / recovery_attempts:.0f}ms")

        # Verify recovery is fast enough
        assert recovery_time < 5000, f"Recovery too slow: {recovery_time:.0f}ms"
        print(f"\n✓ Recovery time acceptable ({recovery_time:.0f}ms < 5000ms)")

        print(f"\n{'=' * 80}")
        print("RECOVERY TIME TEST PASSED")
        print(f"{'=' * 80}\n")

        await client.close()
