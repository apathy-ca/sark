"""
Feature flag management system for gradual rollout and A/B testing.

This module provides percentage-based feature flags with stable user assignment,
Redis persistence, and real-time rollout control.
"""

import hashlib
import logging
from typing import Dict

from valkey import Redis

logger = logging.getLogger(__name__)


class FeatureFlagManager:
    """Manages feature flag rollouts with percentage-based targeting."""

    def __init__(self, redis_client: Redis | None = None):
        """
        Initialize feature flag manager.

        Args:
            redis_client: Optional Redis client for persistent storage.
                         If None, uses in-memory storage only.
        """
        self.redis = redis_client
        self.rollout_pct: Dict[str, int] = {
            "rust_opa": 0,  # Start at 0%
            "rust_cache": 0,
        }
        logger.info(
            f"Initialized FeatureFlagManager with Redis: {redis_client is not None}"
        )

    def should_use_rust(self, feature: str, user_id: str) -> bool:
        """
        Determine if user should get Rust implementation.

        Uses stable hash-based assignment so the same user always gets
        the same implementation for a given rollout percentage.

        Args:
            feature: Feature name (e.g., "rust_opa", "rust_cache")
            user_id: User identifier for stable assignment

        Returns:
            True if user should use Rust implementation, False otherwise
        """
        # Stable hash-based assignment (0-99)
        hash_val = (
            int(hashlib.md5(f"{feature}:{user_id}".encode()).hexdigest(), 16) % 100
        )
        rollout = self.get_rollout_pct(feature)

        # User is in rollout if their hash is below the percentage
        use_rust = hash_val < rollout

        logger.debug(
            f"Feature flag decision: feature={feature}, user={user_id}, "
            f"hash={hash_val}, rollout={rollout}%, use_rust={use_rust}"
        )

        return use_rust

    def get_rollout_pct(self, feature: str) -> int:
        """
        Get current rollout percentage from Redis or memory.

        Args:
            feature: Feature name

        Returns:
            Current rollout percentage (0-100)
        """
        if self.redis:
            try:
                val = self.redis.get(f"feature_flag:{feature}")
                if val is not None:
                    pct = int(val)
                    logger.debug(
                        f"Retrieved rollout from Redis: {feature}={pct}%"
                    )
                    return pct
            except Exception as e:
                logger.warning(
                    f"Failed to get rollout from Redis for {feature}: {e}, "
                    f"falling back to in-memory"
                )

        # Fallback to in-memory
        pct = self.rollout_pct.get(feature, 0)
        logger.debug(f"Retrieved rollout from memory: {feature}={pct}%")
        return pct

    def set_rollout_pct(self, feature: str, percentage: int) -> None:
        """
        Set rollout percentage (0-100).

        Args:
            feature: Feature name
            percentage: Rollout percentage (0-100)

        Raises:
            ValueError: If percentage is not between 0 and 100
        """
        if not 0 <= percentage <= 100:
            raise ValueError(f"Percentage must be 0-100, got {percentage}")

        # Update in-memory first
        self.rollout_pct[feature] = percentage

        # Persist to Redis if available
        if self.redis:
            try:
                self.redis.set(f"feature_flag:{feature}", percentage)
                logger.info(
                    f"Set rollout percentage in Redis: {feature}={percentage}%"
                )
            except Exception as e:
                logger.error(
                    f"Failed to persist rollout to Redis for {feature}: {e}"
                )
        else:
            logger.info(
                f"Set rollout percentage in memory: {feature}={percentage}%"
            )

    def get_all_rollouts(self) -> Dict[str, int]:
        """
        Get all feature rollout percentages.

        Returns:
            Dictionary mapping feature names to rollout percentages
        """
        rollouts = {}
        for feature in self.rollout_pct.keys():
            rollouts[feature] = self.get_rollout_pct(feature)
        return rollouts

    def rollback(self, feature: str) -> None:
        """
        Emergency rollback: set feature to 0% immediately.

        Args:
            feature: Feature name to rollback
        """
        logger.warning(f"ROLLBACK: Setting {feature} to 0%")
        self.set_rollout_pct(feature, 0)

    def rollback_all(self) -> None:
        """Emergency rollback: set all features to 0% immediately."""
        logger.warning("ROLLBACK ALL: Setting all features to 0%")
        for feature in self.rollout_pct.keys():
            self.set_rollout_pct(feature, 0)


# Global instance (will be initialized with Redis from dependencies)
_feature_flag_manager: FeatureFlagManager | None = None


def get_feature_flag_manager(
    redis_client: Redis | None = None,
) -> FeatureFlagManager:
    """
    Get or create global feature flag manager instance.

    Args:
        redis_client: Optional Redis client. Only used on first call.

    Returns:
        FeatureFlagManager instance
    """
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager(redis_client)
    return _feature_flag_manager
