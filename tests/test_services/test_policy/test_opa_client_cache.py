"""Tests for OPA Client with Cache Integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.policy.cache import PolicyCache
from sark.services.policy.opa_client import AuthorizationInput, OPAClient


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=0)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()
    redis_mock.scan_iter = AsyncMock(return_value=iter([]))
    return redis_mock


@pytest.fixture
def cache(mock_redis):
    """Create PolicyCache instance."""
    return PolicyCache(redis_client=mock_redis, ttl_seconds=300, enabled=True)


@pytest.fixture
def opa_client(cache):
    """Create OPA client with cache."""
    client = OPAClient(
        opa_url="http://localhost:8181",
        cache=cache,
        cache_enabled=True,
    )
    return client


@pytest.fixture
def opa_client_no_cache():
    """Create OPA client without cache."""
    cache_disabled = PolicyCache(enabled=False)
    return OPAClient(cache=cache_disabled, cache_enabled=False)


# ============================================================================
# CACHE HIT TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_evaluate_policy_cache_hit(mock_post, opa_client, mock_redis):
    """Test policy evaluation uses cached decision."""
    # Setup cached decision
    cached_decision = {
        "allow": True,
        "reason": "Cached: Admin access",
        "filtered_parameters": None,
        "audit_id": None,
    }
    import json
    mock_redis.get.return_value = json.dumps(cached_decision)

    auth_input = AuthorizationInput(
        user={"id": "user-123", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test-tool", "sensitivity_level": "medium"},
        context={"timestamp": 0},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    # Should return cached decision without calling OPA
    assert decision.allow is True
    assert decision.reason == "Cached: Admin access"
    mock_post.assert_not_called()

    # Verify cache metrics
    assert opa_client.cache.metrics.hits == 1
    assert opa_client.cache.metrics.misses == 0


# ============================================================================
# CACHE MISS TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_evaluate_policy_cache_miss(mock_post, opa_client, mock_redis):
    """Test policy evaluation queries OPA on cache miss."""
    # Setup OPA response
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {
            "allow": True,
            "audit_reason": "Admin role grants access",
        }
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    # Ensure cache miss
    mock_redis.get.return_value = None

    auth_input = AuthorizationInput(
        user={"id": "user-456", "role": "admin"},
        action="tool:invoke",
        tool={"name": "delete-user", "sensitivity_level": "high"},
        context={"timestamp": 0},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    # Should call OPA
    assert decision.allow is True
    mock_post.assert_called_once()

    # Should cache the result
    mock_redis.setex.assert_called_once()

    # Verify cache metrics
    assert opa_client.cache.metrics.misses == 1
    assert opa_client.cache.metrics.hits == 0


# ============================================================================
# TTL CONFIGURATION TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_cache_ttl_critical_sensitivity(mock_post, opa_client, mock_redis):
    """Test cache TTL is lower for critical sensitivity."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    mock_redis.get.return_value = None

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "payment-tool", "sensitivity_level": "critical"},
        context={"timestamp": 0},
    )

    await opa_client.evaluate_policy(auth_input)

    # Verify TTL for critical (30 seconds)
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 30


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_cache_ttl_low_sensitivity(mock_post, opa_client, mock_redis):
    """Test cache TTL is higher for low sensitivity."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    mock_redis.get.return_value = None

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "developer"},
        action="tool:invoke",
        tool={"name": "read-tool", "sensitivity_level": "low"},
        context={"timestamp": 0},
    )

    await opa_client.evaluate_policy(auth_input)

    # Verify TTL for low (300 seconds)
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 300


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_cache_ttl_server_sensitivity(mock_post, opa_client, mock_redis):
    """Test cache TTL uses server sensitivity."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    mock_redis.get.return_value = None

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "developer"},
        action="server:register",
        server={"name": "test-server", "sensitivity_level": "high"},
        context={"timestamp": 0},
    )

    await opa_client.evaluate_policy(auth_input)

    # Verify TTL for high (60 seconds)
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 60


# ============================================================================
# CACHE BYPASS TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_evaluate_policy_bypass_cache(mock_post, opa_client, mock_redis):
    """Test policy evaluation can bypass cache."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    # Setup cached decision
    import json
    cached = {"allow": False, "reason": "Cached deny"}
    mock_redis.get.return_value = json.dumps(cached)

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test", "sensitivity_level": "medium"},
        context={"timestamp": 0},
    )

    # Bypass cache
    decision = await opa_client.evaluate_policy(auth_input, use_cache=False)

    # Should call OPA even though cache has value
    assert decision.allow is True
    mock_post.assert_called_once()


# ============================================================================
# CACHE INVALIDATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_invalidate_cache_all(opa_client, mock_redis):
    """Test invalidating all cache entries."""
    async def async_iter(keys):
        for key in keys:
            yield key

    keys = ["policy:decision:key1", "policy:decision:key2"]
    mock_redis.scan_iter.return_value = async_iter(keys)
    mock_redis.delete.return_value = len(keys)

    deleted = await opa_client.invalidate_cache()

    assert deleted == 2


@pytest.mark.asyncio
async def test_invalidate_cache_by_user(opa_client, mock_redis):
    """Test invalidating cache for specific user."""
    async def async_iter(keys):
        for key in keys:
            yield key

    mock_redis.scan_iter.return_value = async_iter(
        ["policy:decision:user-123:tool:invoke:res:hash"]
    )
    mock_redis.delete.return_value = 1

    deleted = await opa_client.invalidate_cache(user_id="user-123")

    assert deleted == 1


# ============================================================================
# METRICS TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_get_cache_metrics(mock_post, opa_client, mock_redis):
    """Test getting cache metrics."""
    import json

    # Simulate cache hit
    cached = {"allow": True, "reason": "Cached"}
    mock_redis.get.return_value = json.dumps(cached)

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test", "sensitivity_level": "low"},
        context={"timestamp": 0},
    )

    await opa_client.evaluate_policy(auth_input)

    metrics = opa_client.get_cache_metrics()

    assert metrics["hits"] == 1
    assert metrics["hit_rate"] == 100.0
    assert "avg_cache_latency_ms" in metrics


@pytest.mark.asyncio
async def test_get_cache_size(opa_client, mock_redis):
    """Test getting cache size."""
    async def async_iter(keys):
        for key in keys:
            yield key

    keys = [f"policy:decision:key{i}" for i in range(5)]
    mock_redis.scan_iter.return_value = async_iter(keys)

    size = await opa_client.get_cache_size()

    assert size == 5


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_health_check_both_healthy(mock_get, opa_client, mock_redis):
    """Test health check when both OPA and cache are healthy."""
    # Mock OPA health
    opa_response = MagicMock()
    opa_response.status_code = 200
    mock_get.return_value = opa_response

    # Mock cache health
    mock_redis.ping.return_value = True

    health = await opa_client.health_check()

    assert health["opa"] is True
    assert health["cache"] is True
    assert health["overall"] is True


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_health_check_opa_down(mock_get, opa_client, mock_redis):
    """Test health check when OPA is down."""
    mock_get.side_effect = Exception("Connection refused")
    mock_redis.ping.return_value = True

    health = await opa_client.health_check()

    assert health["opa"] is False
    assert health["cache"] is True
    assert health["overall"] is False


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_health_check_cache_down(mock_get, opa_client, mock_redis):
    """Test health check when cache is down."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    mock_get.return_value = opa_response

    mock_redis.ping.side_effect = Exception("Redis down")

    health = await opa_client.health_check()

    assert health["opa"] is True
    assert health["cache"] is False
    assert health["overall"] is False


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_opa_error_still_cached(mock_post, opa_client, mock_redis):
    """Test that OPA errors result in deny decisions (not cached)."""
    mock_post.side_effect = Exception("OPA server error")
    mock_redis.get.return_value = None

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test", "sensitivity_level": "low"},
        context={"timestamp": 0},
    )

    decision = await opa_client.evaluate_policy(auth_input)

    # Should deny on error (fail closed)
    assert decision.allow is False
    assert "failed" in decision.reason.lower() or "error" in decision.reason.lower()

    # Should NOT cache error responses
    mock_redis.setex.assert_not_called()


# ============================================================================
# DISABLED CACHE TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_disabled_cache_always_queries_opa(mock_post, opa_client_no_cache):
    """Test that disabled cache always queries OPA."""
    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Test"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test", "sensitivity_level": "low"},
        context={"timestamp": 0},
    )

    # First call
    await opa_client_no_cache.evaluate_policy(auth_input)
    assert mock_post.call_count == 1

    # Second call - should still call OPA (no cache)
    await opa_client_no_cache.evaluate_policy(auth_input)
    assert mock_post.call_count == 2


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_cache_workflow_complete(mock_post, opa_client, mock_redis):
    """Test complete cache workflow with hits and misses."""
    import json

    opa_response = MagicMock()
    opa_response.status_code = 200
    opa_response.json.return_value = {
        "result": {"allow": True, "audit_reason": "Admin access"}
    }
    opa_response.raise_for_status = MagicMock()
    mock_post.return_value = opa_response

    auth_input = AuthorizationInput(
        user={"id": "user-1", "role": "admin"},
        action="tool:invoke",
        tool={"name": "test", "sensitivity_level": "medium"},
        context={"timestamp": 0},
    )

    # First call - cache miss
    mock_redis.get.return_value = None
    decision1 = await opa_client.evaluate_policy(auth_input)

    assert decision1.allow is True
    assert opa_client.cache.metrics.misses == 1
    mock_post.assert_called_once()

    # Simulate caching
    cached_decision = decision1.model_dump()
    mock_redis.get.return_value = json.dumps(cached_decision)

    # Second call - cache hit
    decision2 = await opa_client.evaluate_policy(auth_input)

    assert decision2.allow is True
    assert opa_client.cache.metrics.hits == 1
    assert mock_post.call_count == 1  # Should not call OPA again

    # Metrics
    metrics = opa_client.get_cache_metrics()
    assert metrics["hit_rate"] == 50.0  # 1 hit, 1 miss


@pytest.mark.asyncio
async def test_close_connections(opa_client, mock_redis):
    """Test closing all connections."""
    with patch.object(opa_client.client, 'aclose', new=AsyncMock()) as mock_client_close:
        await opa_client.close()

        mock_client_close.assert_called_once()
        mock_redis.aclose.assert_called_once()
