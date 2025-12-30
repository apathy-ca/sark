"""
Unit tests for feature flag manager.

Tests stable user assignment, rollout percentages, Redis integration,
and rollback functionality.
"""

from unittest.mock import Mock

import pytest

from sark.services.feature_flags import FeatureFlagManager, get_feature_flag_manager


class TestFeatureFlagManager:
    """Test suite for FeatureFlagManager."""

    def test_init_without_redis(self):
        """Test initialization without Redis client."""
        manager = FeatureFlagManager()
        assert manager.redis is None
        assert manager.rollout_pct == {"rust_opa": 0, "rust_cache": 0}

    def test_init_with_redis(self):
        """Test initialization with Redis client."""
        mock_redis = Mock()
        manager = FeatureFlagManager(redis_client=mock_redis)
        assert manager.redis == mock_redis
        assert manager.rollout_pct == {"rust_opa": 0, "rust_cache": 0}

    def test_stable_user_assignment(self):
        """Test that same user always gets same assignment."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 50)

        # Same user should get consistent assignment
        user_id = "user123"
        result1 = manager.should_use_rust("rust_opa", user_id)
        result2 = manager.should_use_rust("rust_opa", user_id)
        result3 = manager.should_use_rust("rust_opa", user_id)

        assert result1 == result2 == result3

    def test_different_users_different_assignment(self):
        """Test that different users can get different assignments."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 50)

        # With 50% rollout, we should see some variation across many users
        results = []
        for i in range(100):
            result = manager.should_use_rust("rust_opa", f"user{i}")
            results.append(result)

        # Should have both True and False (not all same)
        assert True in results
        assert False in results

    def test_rollout_percentage_accuracy(self):
        """Test that rollout percentage is accurate (±5%)."""
        manager = FeatureFlagManager()
        percentages = [0, 25, 50, 75, 100]

        for target_pct in percentages:
            manager.set_rollout_pct("rust_opa", target_pct)

            # Test with 1000 users
            rust_count = sum(
                1 for i in range(1000) if manager.should_use_rust("rust_opa", f"user{i}")
            )
            actual_pct = (rust_count / 1000) * 100

            # Should be within ±5% of target
            assert abs(actual_pct - target_pct) <= 5, f"Expected ~{target_pct}%, got {actual_pct}%"

    def test_set_rollout_pct_in_memory(self):
        """Test setting rollout percentage in memory."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 75)

        assert manager.get_rollout_pct("rust_opa") == 75

    def test_set_rollout_pct_with_redis(self):
        """Test setting rollout percentage with Redis."""
        mock_redis = Mock()
        manager = FeatureFlagManager(redis_client=mock_redis)

        manager.set_rollout_pct("rust_opa", 75)

        # Should update in-memory
        assert manager.rollout_pct["rust_opa"] == 75

        # Should persist to Redis
        mock_redis.set.assert_called_once_with("feature_flag:rust_opa", 75)

    def test_get_rollout_pct_from_redis(self):
        """Test getting rollout percentage from Redis."""
        mock_redis = Mock()
        mock_redis.get.return_value = "42"
        manager = FeatureFlagManager(redis_client=mock_redis)

        pct = manager.get_rollout_pct("rust_opa")

        assert pct == 42
        mock_redis.get.assert_called_once_with("feature_flag:rust_opa")

    def test_get_rollout_pct_fallback_to_memory(self):
        """Test fallback to memory when Redis fails."""
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis error")
        manager = FeatureFlagManager(redis_client=mock_redis)
        manager.rollout_pct["rust_opa"] = 30

        pct = manager.get_rollout_pct("rust_opa")

        # Should fallback to in-memory value
        assert pct == 30

    def test_get_rollout_pct_redis_returns_none(self):
        """Test getting rollout when Redis returns None."""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        manager = FeatureFlagManager(redis_client=mock_redis)
        manager.rollout_pct["rust_opa"] = 25

        pct = manager.get_rollout_pct("rust_opa")

        # Should fallback to in-memory value
        assert pct == 25

    def test_set_rollout_pct_invalid_percentage_low(self):
        """Test that setting invalid percentage (too low) raises error."""
        manager = FeatureFlagManager()

        with pytest.raises(ValueError, match="Percentage must be 0-100"):
            manager.set_rollout_pct("rust_opa", -1)

    def test_set_rollout_pct_invalid_percentage_high(self):
        """Test that setting invalid percentage (too high) raises error."""
        manager = FeatureFlagManager()

        with pytest.raises(ValueError, match="Percentage must be 0-100"):
            manager.set_rollout_pct("rust_opa", 101)

    def test_set_rollout_pct_redis_persistence_failure(self):
        """Test that Redis persistence failure is handled gracefully."""
        mock_redis = Mock()
        mock_redis.set.side_effect = Exception("Redis error")
        manager = FeatureFlagManager(redis_client=mock_redis)

        # Should not raise, just log error
        manager.set_rollout_pct("rust_opa", 50)

        # In-memory should still be updated
        assert manager.rollout_pct["rust_opa"] == 50

    def test_get_all_rollouts(self):
        """Test getting all rollout percentages."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 25)
        manager.set_rollout_pct("rust_cache", 50)

        rollouts = manager.get_all_rollouts()

        assert rollouts == {"rust_opa": 25, "rust_cache": 50}

    def test_get_all_rollouts_with_redis(self):
        """Test getting all rollouts from Redis."""
        mock_redis = Mock()
        mock_redis.get.side_effect = lambda key: {
            "feature_flag:rust_opa": "30",
            "feature_flag:rust_cache": "60",
        }.get(key)

        manager = FeatureFlagManager(redis_client=mock_redis)

        rollouts = manager.get_all_rollouts()

        assert rollouts == {"rust_opa": 30, "rust_cache": 60}

    def test_rollback_single_feature(self):
        """Test rolling back a single feature."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 100)

        manager.rollback("rust_opa")

        assert manager.get_rollout_pct("rust_opa") == 0

    def test_rollback_all_features(self):
        """Test rolling back all features."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 100)
        manager.set_rollout_pct("rust_cache", 75)

        manager.rollback_all()

        assert manager.get_rollout_pct("rust_opa") == 0
        assert manager.get_rollout_pct("rust_cache") == 0

    def test_different_features_different_assignment(self):
        """Test that same user can have different assignments for different features."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 10)
        manager.set_rollout_pct("rust_cache", 90)

        # Some users will have different assignments for different features
        # due to different hash inputs
        differences = 0
        for i in range(100):
            user_id = f"user{i}"
            opa_result = manager.should_use_rust("rust_opa", user_id)
            cache_result = manager.should_use_rust("rust_cache", user_id)
            if opa_result != cache_result:
                differences += 1

        # Should have some differences (not all same)
        assert differences > 0

    def test_edge_case_0_percent_rollout(self):
        """Test 0% rollout - nobody gets Rust."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 0)

        for i in range(100):
            assert manager.should_use_rust("rust_opa", f"user{i}") is False

    def test_edge_case_100_percent_rollout(self):
        """Test 100% rollout - everyone gets Rust."""
        manager = FeatureFlagManager()
        manager.set_rollout_pct("rust_opa", 100)

        for i in range(100):
            assert manager.should_use_rust("rust_opa", f"user{i}") is True

    def test_unknown_feature_defaults_to_zero(self):
        """Test that unknown features default to 0% rollout."""
        manager = FeatureFlagManager()

        # Unknown feature should default to 0%
        assert manager.get_rollout_pct("unknown_feature") == 0
        assert manager.should_use_rust("unknown_feature", "user123") is False


class TestGetFeatureFlagManager:
    """Test suite for global feature flag manager singleton."""

    def test_get_feature_flag_manager_creates_instance(self):
        """Test that get_feature_flag_manager creates instance."""
        # Reset global
        import sark.services.feature_flags as ff_module

        ff_module._feature_flag_manager = None

        manager = get_feature_flag_manager()
        assert manager is not None
        assert isinstance(manager, FeatureFlagManager)

    def test_get_feature_flag_manager_returns_same_instance(self):
        """Test that get_feature_flag_manager returns same instance."""
        # Reset global
        import sark.services.feature_flags as ff_module

        ff_module._feature_flag_manager = None

        manager1 = get_feature_flag_manager()
        manager2 = get_feature_flag_manager()

        assert manager1 is manager2

    def test_get_feature_flag_manager_with_redis(self):
        """Test creating manager with Redis client."""
        # Reset global
        import sark.services.feature_flags as ff_module

        ff_module._feature_flag_manager = None

        mock_redis = Mock()
        manager = get_feature_flag_manager(redis_client=mock_redis)

        assert manager.redis == mock_redis
