"""Unit tests for RustOPAClient."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from sark.services.policy.rust_opa_client import (
    RustOPAClient,
    AuthorizationInput,
    AuthorizationDecision,
    RUST_AVAILABLE,
)


# Mark all tests to skip if Rust extension is not available
pytestmark = pytest.mark.skipif(
    not RUST_AVAILABLE,
    reason="Rust extensions not available"
)


@pytest.fixture
def mock_cache():
    """Create a mock cache."""
    cache = Mock()
    cache.enabled = True
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.invalidate = AsyncMock(return_value=0)
    cache.get_cache_size = AsyncMock(return_value=0)
    cache.close = AsyncMock()
    cache.health_check = AsyncMock(return_value=True)
    cache.record_opa_latency = Mock()
    cache.get_metrics = Mock(return_value={})
    return cache


@pytest.fixture
def rust_client(mock_cache, tmp_path):
    """Create a RustOPAClient instance for testing."""
    # Create a temporary policy directory
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()

    # Create a simple test policy
    policy_file = policy_dir / "test_policy.rego"
    policy_file.write_text("""
        package test
        default allow = false
        allow {
            input.user.role == "admin"
        }
    """)

    client = RustOPAClient(
        policy_dir=policy_dir,
        cache=mock_cache,
        cache_enabled=True
    )

    yield client


class TestRustOPAClientInit:
    """Test RustOPAClient initialization."""

    def test_init_without_rust_extension(self, mock_cache):
        """Test initialization fails gracefully without Rust extension."""
        with patch("sark.services.policy.rust_opa_client.RUST_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Rust extensions not available"):
                RustOPAClient(cache=mock_cache)

    def test_init_with_rust_extension(self, mock_cache, tmp_path):
        """Test successful initialization with Rust extension."""
        client = RustOPAClient(
            policy_dir=tmp_path,
            cache=mock_cache,
            cache_enabled=True
        )

        assert client.engine is not None
        assert client.policy_dir == tmp_path
        assert client.cache == mock_cache
        assert client._loaded_policies == set()

    def test_init_default_policy_dir(self, mock_cache):
        """Test initialization uses default policy directory."""
        client = RustOPAClient(cache=mock_cache)

        assert client.policy_dir == Path("opa/policies")


class TestPolicyLoading:
    """Test policy loading functionality."""

    @pytest.mark.asyncio
    async def test_load_policy_success(self, rust_client):
        """Test loading a valid policy."""
        policy = """
            package example
            allow {
                input.user == "admin"
            }
        """

        await rust_client.load_policy("example", policy)

        assert "example" in rust_client._loaded_policies
        assert "example" in rust_client.get_loaded_policies()

    @pytest.mark.asyncio
    async def test_load_policy_invalid(self, rust_client):
        """Test loading an invalid policy raises an error."""
        invalid_policy = "this is not valid rego"

        with pytest.raises(Exception):
            await rust_client.load_policy("invalid", invalid_policy)

    @pytest.mark.asyncio
    async def test_load_policy_from_file(self, rust_client):
        """Test loading a policy from a file."""
        policy_file = rust_client.policy_dir / "test_policy.rego"

        await rust_client.load_policy_from_file(policy_file)

        assert "test_policy" in rust_client._loaded_policies

    @pytest.mark.asyncio
    async def test_load_policy_from_missing_file(self, rust_client):
        """Test loading from a non-existent file raises FileNotFoundError."""
        missing_file = rust_client.policy_dir / "missing.rego"

        with pytest.raises(FileNotFoundError):
            await rust_client.load_policy_from_file(missing_file)

    @pytest.mark.asyncio
    async def test_ensure_policy_loaded_already_loaded(self, rust_client):
        """Test ensure_policy_loaded skips already loaded policies."""
        policy = "package test\nallow = true"
        await rust_client.load_policy("test_policy", policy)

        initial_count = len(rust_client._loaded_policies)

        await rust_client.ensure_policy_loaded("test_policy")

        # Should not reload
        assert len(rust_client._loaded_policies) == initial_count

    @pytest.mark.asyncio
    async def test_ensure_policy_loaded_from_file(self, rust_client):
        """Test ensure_policy_loaded loads from file if not loaded."""
        await rust_client.ensure_policy_loaded("test_policy")

        assert "test_policy" in rust_client._loaded_policies


class TestPolicyEvaluation:
    """Test policy evaluation functionality."""

    @pytest.mark.asyncio
    async def test_evaluate_policy_cache_hit(self, rust_client, mock_cache):
        """Test evaluation returns cached decision when available."""
        auth_input = AuthorizationInput(
            user={"id": "user1", "role": "admin"},
            action="gateway:tool:invoke",
            tool={"name": "test-tool", "sensitivity_level": "low"},
            context={}
        )

        cached_decision = {
            "allow": True,
            "reason": "Cached decision",
            "filtered_parameters": None,
            "audit_id": None,
        }

        mock_cache.get = AsyncMock(return_value=cached_decision)

        decision = await rust_client.evaluate_policy(auth_input)

        assert decision.allow is True
        assert decision.reason == "Cached decision"
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_policy_cache_miss(self, rust_client, mock_cache):
        """Test evaluation queries Rust engine on cache miss."""
        # Load a simple policy
        policy = """
            package sark.gateway
            default allow = false
            allow {
                input.user.role == "admin"
            }
        """
        await rust_client.load_policy("gateway_authorization", policy)

        auth_input = AuthorizationInput(
            user={"id": "user1", "role": "admin"},
            action="gateway:tool:invoke",
            tool={"name": "test-tool", "sensitivity_level": "low"},
            context={}
        )

        mock_cache.get = AsyncMock(return_value=None)

        decision = await rust_client.evaluate_policy(auth_input)

        # Should evaluate and cache the result
        assert isinstance(decision, AuthorizationDecision)
        mock_cache.set.assert_called_once()
        mock_cache.record_opa_latency.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_policy_boolean_result(self, rust_client, mock_cache):
        """Test evaluation handles boolean results correctly."""
        policy = """
            package sark.gateway
            allow = true
        """
        await rust_client.load_policy("gateway_authorization", policy)

        auth_input = AuthorizationInput(
            user={"id": "user1", "role": "user"},
            action="gateway:tool:invoke",
            tool={"name": "test-tool"},
            context={}
        )

        mock_cache.get = AsyncMock(return_value=None)

        decision = await rust_client.evaluate_policy(auth_input)

        assert decision.allow is True

    @pytest.mark.asyncio
    async def test_evaluate_policy_error_fails_closed(self, rust_client, mock_cache):
        """Test evaluation fails closed (deny) on error."""
        auth_input = AuthorizationInput(
            user={"id": "user1", "role": "user"},
            action="gateway:tool:invoke",
            tool={"name": "test-tool"},
            context={}
        )

        mock_cache.get = AsyncMock(return_value=None)

        # Trigger an error by not loading any policy
        # This should fail when trying to evaluate
        decision = await rust_client.evaluate_policy(auth_input)

        # Should fail closed
        assert decision.allow is False
        assert "failed" in decision.reason.lower()


class TestCacheOperations:
    """Test cache-related operations."""

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, rust_client, mock_cache):
        """Test cache invalidation."""
        mock_cache.invalidate = AsyncMock(return_value=5)

        count = await rust_client.invalidate_cache(
            user_id="user1",
            action="gateway:tool:invoke",
            resource="tool:test"
        )

        assert count == 5
        mock_cache.invalidate.assert_called_once_with(
            user_id="user1",
            action="gateway:tool:invoke",
            resource="tool:test"
        )

    @pytest.mark.asyncio
    async def test_get_cache_size(self, rust_client, mock_cache):
        """Test getting cache size."""
        mock_cache.get_cache_size = AsyncMock(return_value=42)

        size = await rust_client.get_cache_size()

        assert size == 42

    def test_get_cache_metrics(self, rust_client, mock_cache):
        """Test getting cache metrics."""
        expected_metrics = {"hit_rate": 0.75, "total_requests": 100}
        mock_cache.get_metrics = Mock(return_value=expected_metrics)

        metrics = rust_client.get_cache_metrics()

        assert metrics == expected_metrics


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, rust_client, mock_cache):
        """Test health check when all components are healthy."""
        mock_cache.health_check = AsyncMock(return_value=True)

        health = await rust_client.health_check()

        assert health["rust_engine"] is True
        assert health["cache"] is True
        assert health["overall"] is True

    @pytest.mark.asyncio
    async def test_health_check_cache_unhealthy(self, rust_client, mock_cache):
        """Test health check when cache is unhealthy."""
        mock_cache.health_check = AsyncMock(return_value=False)

        health = await rust_client.health_check()

        assert health["rust_engine"] is True
        assert health["cache"] is False
        assert health["overall"] is False


class TestHelperMethods:
    """Test helper methods."""

    def test_get_policy_query_gateway(self, rust_client):
        """Test policy query determination for gateway actions."""
        query = rust_client._get_policy_query("gateway:tool:invoke")

        assert query == "data.sark.gateway.allow"

    def test_get_policy_query_a2a(self, rust_client):
        """Test policy query determination for A2A actions."""
        query = rust_client._get_policy_query("a2a:communicate")

        assert query == "data.mcp.gateway.a2a.result.allow"

    def test_get_cache_ttl_by_sensitivity(self, rust_client):
        """Test cache TTL determination based on sensitivity."""
        auth_input_critical = AuthorizationInput(
            user={"id": "user1"},
            action="test",
            tool={"name": "test", "sensitivity_level": "critical"},
            context={}
        )

        auth_input_public = AuthorizationInput(
            user={"id": "user1"},
            action="test",
            tool={"name": "test", "sensitivity_level": "public"},
            context={}
        )

        ttl_critical = rust_client._get_cache_ttl(auth_input_critical)
        ttl_public = rust_client._get_cache_ttl(auth_input_public)

        # Critical should have shorter TTL
        assert ttl_critical < ttl_public

    def test_get_sensitivity_from_tool(self, rust_client):
        """Test sensitivity extraction from tool."""
        auth_input = AuthorizationInput(
            user={"id": "user1"},
            action="test",
            tool={"name": "test", "sensitivity_level": "high"},
            context={}
        )

        sensitivity = rust_client._get_sensitivity(auth_input)

        assert sensitivity == "high"

    def test_get_sensitivity_from_server(self, rust_client):
        """Test sensitivity extraction from server."""
        auth_input = AuthorizationInput(
            user={"id": "user1"},
            action="test",
            server={"name": "test", "sensitivity_level": "low"},
            context={}
        )

        sensitivity = rust_client._get_sensitivity(auth_input)

        assert sensitivity == "low"

    def test_get_sensitivity_default(self, rust_client):
        """Test default sensitivity when neither tool nor server is provided."""
        auth_input = AuthorizationInput(
            user={"id": "user1"},
            action="test",
            context={}
        )

        sensitivity = rust_client._get_sensitivity(auth_input)

        assert sensitivity == "default"


class TestLifecycle:
    """Test client lifecycle methods."""

    @pytest.mark.asyncio
    async def test_close(self, rust_client, mock_cache):
        """Test client close method."""
        await rust_client.close()

        mock_cache.close.assert_called_once()

    def test_get_loaded_policies(self, rust_client):
        """Test getting loaded policies list."""
        policies = rust_client.get_loaded_policies()

        assert isinstance(policies, list)
