"""
Unit tests for OPA and cache client factories.

Tests feature flag routing, fallback behavior, and implementation selection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from sark.services.policy.factory import (
    create_opa_client,
    create_policy_cache,
    create_policy_clients,
    RustOPAClient,
    RustPolicyCache,
    RUST_AVAILABLE,
)
from sark.services.policy.opa_client import OPAClient
from sark.services.policy.cache import PolicyCache


class TestCreateOPAClient:
    """Test suite for create_opa_client factory."""

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", False)
    def test_create_python_client_when_rust_not_available(
        self, mock_get_ff_manager
    ):
        """Test that Python client is created when Rust is not available."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        client = create_opa_client("user123")

        assert isinstance(client, OPAClient)
        # Feature flag should still be checked
        mock_ff_manager.should_use_rust.assert_called_once_with(
            "rust_opa", "user123"
        )

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", False)
    def test_create_python_client_when_feature_flag_disabled(
        self, mock_get_ff_manager
    ):
        """Test that Python client is created when feature flag is off."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = False
        mock_get_ff_manager.return_value = mock_ff_manager

        client = create_opa_client("user123")

        assert isinstance(client, OPAClient)
        mock_ff_manager.should_use_rust.assert_called_once_with(
            "rust_opa", "user123"
        )

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustOPAClient")
    def test_create_rust_client_when_enabled(
        self, mock_rust_client_class, mock_get_ff_manager
    ):
        """Test that Rust client is created when feature flag is on."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        mock_rust_instance = Mock()
        mock_rust_client_class.return_value = mock_rust_instance

        client = create_opa_client("user123")

        assert client == mock_rust_instance
        mock_ff_manager.should_use_rust.assert_called_once_with(
            "rust_opa", "user123"
        )
        mock_rust_client_class.assert_called_once_with(None)

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustOPAClient")
    def test_fallback_to_python_on_rust_error(
        self, mock_rust_client_class, mock_get_ff_manager
    ):
        """Test fallback to Python when Rust client fails to initialize."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        # Simulate Rust client initialization failure
        mock_rust_client_class.side_effect = RuntimeError("Rust init failed")

        client = create_opa_client("user123", fallback_on_error=True)

        # Should fallback to Python
        assert isinstance(client, OPAClient)
        mock_rust_client_class.assert_called_once()

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustOPAClient")
    def test_no_fallback_when_disabled(
        self, mock_rust_client_class, mock_get_ff_manager
    ):
        """Test that error is raised when fallback is disabled."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        # Simulate Rust client initialization failure
        mock_rust_client_class.side_effect = RuntimeError("Rust init failed")

        with pytest.raises(RuntimeError, match="Rust init failed"):
            create_opa_client("user123", fallback_on_error=False)

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustOPAClient")
    def test_opa_url_passed_to_clients(
        self, mock_rust_client_class, mock_get_ff_manager
    ):
        """Test that OPA URL is passed to clients."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        mock_rust_instance = Mock()
        mock_rust_client_class.return_value = mock_rust_instance

        client = create_opa_client("user123", opa_url="http://custom-opa:8181")

        mock_rust_client_class.assert_called_once_with("http://custom-opa:8181")


class TestCreatePolicyCache:
    """Test suite for create_policy_cache factory."""

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", False)
    def test_create_redis_cache_when_rust_not_available(
        self, mock_get_ff_manager
    ):
        """Test that Redis cache is created when Rust is not available."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        cache = create_policy_cache("user123")

        assert isinstance(cache, PolicyCache)
        mock_ff_manager.should_use_rust.assert_called_once_with(
            "rust_cache", "user123"
        )

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", False)
    def test_create_redis_cache_when_feature_flag_disabled(
        self, mock_get_ff_manager
    ):
        """Test that Redis cache is created when feature flag is off."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = False
        mock_get_ff_manager.return_value = mock_ff_manager

        cache = create_policy_cache("user123")

        assert isinstance(cache, PolicyCache)
        mock_ff_manager.should_use_rust.assert_called_once_with(
            "rust_cache", "user123"
        )

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustPolicyCache")
    def test_create_rust_cache_when_enabled(
        self, mock_rust_cache_class, mock_get_ff_manager
    ):
        """Test that Rust cache is created when feature flag is on."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        mock_rust_instance = Mock()
        mock_rust_cache_class.return_value = mock_rust_instance

        cache = create_policy_cache("user123")

        assert cache == mock_rust_instance
        mock_ff_manager.should_use_rust.assert_called_once_with(
            "rust_cache", "user123"
        )
        mock_rust_cache_class.assert_called_once_with()

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustPolicyCache")
    def test_fallback_to_redis_on_rust_error(
        self, mock_rust_cache_class, mock_get_ff_manager
    ):
        """Test fallback to Redis when Rust cache fails to initialize."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        # Simulate Rust cache initialization failure
        mock_rust_cache_class.side_effect = RuntimeError("Rust init failed")

        cache = create_policy_cache("user123", fallback_on_error=True)

        # Should fallback to Redis
        assert isinstance(cache, PolicyCache)
        mock_rust_cache_class.assert_called_once()

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustPolicyCache")
    def test_no_fallback_when_disabled(
        self, mock_rust_cache_class, mock_get_ff_manager
    ):
        """Test that error is raised when fallback is disabled."""
        mock_ff_manager = Mock()
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        # Simulate Rust cache initialization failure
        mock_rust_cache_class.side_effect = RuntimeError("Rust init failed")

        with pytest.raises(RuntimeError, match="Rust init failed"):
            create_policy_cache("user123", fallback_on_error=False)


class TestCreatePolicyClients:
    """Test suite for create_policy_clients convenience function."""

    @patch("sark.services.policy.factory.create_opa_client")
    @patch("sark.services.policy.factory.create_policy_cache")
    def test_creates_both_clients(
        self, mock_create_cache, mock_create_opa
    ):
        """Test that both clients are created."""
        mock_opa = Mock()
        mock_cache = Mock()
        mock_create_opa.return_value = mock_opa
        mock_create_cache.return_value = mock_cache

        opa_client, policy_cache = create_policy_clients("user123")

        assert opa_client == mock_opa
        assert policy_cache == mock_cache
        mock_create_opa.assert_called_once_with("user123", None)
        mock_create_cache.assert_called_once_with("user123")

    @patch("sark.services.policy.factory.create_opa_client")
    @patch("sark.services.policy.factory.create_policy_cache")
    def test_passes_opa_url(self, mock_create_cache, mock_create_opa):
        """Test that OPA URL is passed through."""
        mock_opa = Mock()
        mock_cache = Mock()
        mock_create_opa.return_value = mock_opa
        mock_create_cache.return_value = mock_cache

        opa_client, policy_cache = create_policy_clients(
            "user123", opa_url="http://custom-opa:8181"
        )

        mock_create_opa.assert_called_once_with(
            "user123", "http://custom-opa:8181"
        )


class TestRustOPAClient:
    """Test suite for RustOPAClient stub."""

    @patch("sark.services.policy.factory.RUST_AVAILABLE", False)
    def test_raises_error_when_rust_not_available(self):
        """Test that RustOPAClient raises error when Rust is not available."""
        with pytest.raises(RuntimeError, match="Rust OPA client not available"):
            RustOPAClient()

    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    def test_initialization_succeeds_when_rust_available(self):
        """Test that RustOPAClient can be initialized when Rust is available."""
        client = RustOPAClient()
        assert client._initialized is True

    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_evaluate_policy_not_implemented(self):
        """Test that evaluate_policy raises NotImplementedError (stub)."""
        client = RustOPAClient()

        from sark.services.policy.opa_client import AuthorizationInput

        auth_input = AuthorizationInput(
            user={"id": "user123"},
            action="read",
            context={},
        )

        with pytest.raises(
            NotImplementedError, match="Rust OPA client stub"
        ):
            await client.evaluate_policy(auth_input)

    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_close(self):
        """Test that close method works."""
        client = RustOPAClient()
        await client.close()  # Should not raise


class TestRustPolicyCache:
    """Test suite for RustPolicyCache stub."""

    @patch("sark.services.policy.factory.RUST_AVAILABLE", False)
    def test_raises_error_when_rust_not_available(self):
        """Test that RustPolicyCache raises error when Rust is not available."""
        with pytest.raises(
            RuntimeError, match="Rust policy cache not available"
        ):
            RustPolicyCache()

    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    def test_initialization_succeeds_when_rust_available(self):
        """Test that RustPolicyCache can be initialized when Rust is available."""
        cache = RustPolicyCache(max_size=5000)
        assert cache._initialized is True
        assert cache._max_size == 5000

    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_get_not_implemented(self):
        """Test that get raises NotImplementedError (stub)."""
        cache = RustPolicyCache()

        with pytest.raises(NotImplementedError, match="Rust cache stub"):
            await cache.get("user123", "read", "tool:slack")

    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_set_not_implemented(self):
        """Test that set raises NotImplementedError (stub)."""
        cache = RustPolicyCache()

        with pytest.raises(NotImplementedError, match="Rust cache stub"):
            await cache.set(
                "user123", "read", "tool:slack", {"allow": True}
            )

    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_delete_not_implemented(self):
        """Test that delete raises NotImplementedError (stub)."""
        cache = RustPolicyCache()

        with pytest.raises(NotImplementedError, match="Rust cache stub"):
            await cache.delete("user123", "read", "tool:slack")


class TestFeatureFlagRouting:
    """Integration tests for feature flag routing."""

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustOPAClient")
    @patch("sark.services.policy.factory.RustPolicyCache")
    def test_same_user_gets_consistent_routing(
        self,
        mock_rust_cache_class,
        mock_rust_opa_class,
        mock_get_ff_manager,
    ):
        """Test that same user always gets the same implementation."""
        mock_ff_manager = Mock()

        # User should consistently get Rust
        mock_ff_manager.should_use_rust.return_value = True
        mock_get_ff_manager.return_value = mock_ff_manager

        mock_rust_opa = Mock()
        mock_rust_cache = Mock()
        mock_rust_opa_class.return_value = mock_rust_opa
        mock_rust_cache_class.return_value = mock_rust_cache

        # Call multiple times with same user
        opa1 = create_opa_client("user123")
        opa2 = create_opa_client("user123")
        cache1 = create_policy_cache("user123")
        cache2 = create_policy_cache("user123")

        # Should call feature flag manager each time with same user
        assert mock_ff_manager.should_use_rust.call_count == 4
        calls = mock_ff_manager.should_use_rust.call_args_list
        assert all(call[0][1] == "user123" for call in calls)

    @patch("sark.services.policy.factory.get_feature_flag_manager")
    @patch("sark.services.policy.factory.RUST_AVAILABLE", True)
    @patch("sark.services.policy.factory.RustOPAClient")
    def test_different_users_can_get_different_implementations(
        self, mock_rust_opa_class, mock_get_ff_manager
    ):
        """Test that different users can get different implementations."""
        mock_ff_manager = Mock()

        # User1 gets Rust, User2 gets Python
        def should_use_rust_side_effect(feature, user_id):
            return user_id == "user1"

        mock_ff_manager.should_use_rust.side_effect = (
            should_use_rust_side_effect
        )
        mock_get_ff_manager.return_value = mock_ff_manager

        mock_rust_opa = Mock()
        mock_rust_opa_class.return_value = mock_rust_opa

        opa1 = create_opa_client("user1")
        opa2 = create_opa_client("user2")

        # User1 should get Rust
        assert opa1 == mock_rust_opa

        # User2 should get Python
        assert isinstance(opa2, OPAClient)
