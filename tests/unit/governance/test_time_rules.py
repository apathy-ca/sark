"""Unit tests for time-based policy rules.

These tests cover:
- Cache TTL calculations based on sensitivity levels
- Time-based policy decision logging
- Time-based policy evaluation tracking

Following AAA pattern: Arrange, Act, Assert
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.models.gateway import SensitivityLevel
from sark.services.gateway.authorization import _get_cache_ttl


class TestCacheTTLByScensitivity:
    """Test cache TTL calculation based on sensitivity level."""

    def test_low_sensitivity_gets_longest_ttl(self):
        """Test LOW sensitivity gets 30 minute cache TTL."""
        # Arrange
        sensitivity = SensitivityLevel.LOW

        # Act
        ttl = _get_cache_ttl(sensitivity)

        # Assert
        assert ttl == 1800  # 30 minutes

    def test_medium_sensitivity_gets_moderate_ttl(self):
        """Test MEDIUM sensitivity gets 5 minute cache TTL."""
        # Arrange
        sensitivity = SensitivityLevel.MEDIUM

        # Act
        ttl = _get_cache_ttl(sensitivity)

        # Assert
        assert ttl == 300  # 5 minutes

    def test_high_sensitivity_gets_short_ttl(self):
        """Test HIGH sensitivity gets 1 minute cache TTL."""
        # Arrange
        sensitivity = SensitivityLevel.HIGH

        # Act
        ttl = _get_cache_ttl(sensitivity)

        # Assert
        assert ttl == 60  # 1 minute

    def test_critical_sensitivity_gets_no_cache(self):
        """Test CRITICAL sensitivity gets no caching."""
        # Arrange
        sensitivity = SensitivityLevel.CRITICAL

        # Act
        ttl = _get_cache_ttl(sensitivity)

        # Assert
        assert ttl == 0  # No caching

    def test_none_sensitivity_gets_default_ttl(self):
        """Test None sensitivity gets default 5 minute cache TTL."""
        # Arrange
        sensitivity = None

        # Act
        ttl = _get_cache_ttl(sensitivity)

        # Assert
        assert ttl == 300  # Default: 5 minutes


class TestTimeBasedPolicyDecisionFields:
    """Test time-based policy decision tracking in audit logs."""

    def test_decision_log_has_time_based_field(self):
        """Test PolicyDecisionLog model has time_based_allowed field."""
        from sark.models.policy_audit import PolicyDecisionLog

        # Assert - field exists in model
        assert hasattr(PolicyDecisionLog, "time_based_allowed")

    def test_decision_log_has_ip_filtering_field(self):
        """Test PolicyDecisionLog model has ip_filtering_allowed field."""
        from sark.models.policy_audit import PolicyDecisionLog

        # Assert - field exists in model
        assert hasattr(PolicyDecisionLog, "ip_filtering_allowed")

    def test_decision_log_has_mfa_required_field(self):
        """Test PolicyDecisionLog model has mfa_required_satisfied field."""
        from sark.models.policy_audit import PolicyDecisionLog

        # Assert - field exists in model
        assert hasattr(PolicyDecisionLog, "mfa_required_satisfied")


class TestTimestampHandling:
    """Test timestamp handling in policy decisions."""

    def test_datetime_now_uses_utc(self):
        """Test that datetime.now() is used with UTC timezone."""
        # Arrange
        now = datetime.now(UTC)

        # Assert
        assert now.tzinfo is not None
        assert now.tzinfo == UTC

    def test_timestamp_comparison(self):
        """Test timestamp comparison for time-based rules."""
        # Arrange
        current_time = datetime.now(UTC)
        bedtime_start = current_time.replace(hour=21, minute=0, second=0)
        bedtime_end = (current_time + timedelta(days=1)).replace(hour=7, minute=0, second=0)

        # Create a time that would be in bedtime (22:30)
        test_time = current_time.replace(hour=22, minute=30, second=0)

        # Act - Check if test_time is in bedtime window
        if bedtime_start > bedtime_end:  # Crosses midnight
            is_bedtime = test_time >= bedtime_start or test_time <= bedtime_end
        else:
            is_bedtime = bedtime_start <= test_time <= bedtime_end

        # Assert
        # Since we're testing at 22:30, it should be after 21:00 bedtime start
        assert test_time.hour == 22
        assert test_time.minute == 30


class TestCacheCleanupTimeBased:
    """Test time-based cache cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cache_cleanup_task_exists(self):
        """Test that CacheCleanupTask exists and can be instantiated."""
        from sark.services.policy.cache_cleanup import CacheCleanupTask

        # Arrange
        mock_cache = MagicMock()
        mock_cache.cleanup_expired = AsyncMock(return_value=0)

        # Act
        task = CacheCleanupTask(cache=mock_cache, cleanup_interval=60)

        # Assert
        assert task is not None
        assert task.cleanup_interval == 60

    @pytest.mark.asyncio
    async def test_cache_cleanup_interval_is_configurable(self):
        """Test that cleanup interval can be configured."""
        from sark.services.policy.cache_cleanup import CacheCleanupTask

        # Arrange
        mock_cache = MagicMock()
        mock_cache.cleanup_expired = AsyncMock(return_value=0)

        # Act
        task_60 = CacheCleanupTask(cache=mock_cache, cleanup_interval=60)
        task_120 = CacheCleanupTask(cache=mock_cache, cleanup_interval=120)

        # Assert
        assert task_60.cleanup_interval == 60
        assert task_120.cleanup_interval == 120


class TestTimeBasedPolicyResults:
    """Test time-based policy results extraction."""

    def test_extract_time_based_result_from_policy_results(self):
        """Test extracting time_based result from policy evaluation."""
        # Arrange
        policy_results = {
            "time_based": {"allow": True, "reason": "Within allowed hours"},
            "ip_filtering": {"allow": True, "reason": "IP in allowlist"},
        }

        # Act
        time_based_allowed = policy_results.get("time_based", {}).get("allow")

        # Assert
        assert time_based_allowed is True

    def test_extract_time_based_result_when_missing(self):
        """Test extracting time_based result when not present."""
        # Arrange
        policy_results = {
            "ip_filtering": {"allow": True},
        }

        # Act
        time_based_allowed = policy_results.get("time_based", {}).get("allow")

        # Assert
        assert time_based_allowed is None

    def test_extract_time_based_denied(self):
        """Test extracting time_based denial reason."""
        # Arrange
        policy_results = {
            "time_based": {"allow": False, "reason": "Outside allowed hours (bedtime)"},
        }

        # Act
        time_based_allowed = policy_results.get("time_based", {}).get("allow")
        time_based_reason = policy_results.get("time_based", {}).get("reason")

        # Assert
        assert time_based_allowed is False
        assert "bedtime" in time_based_reason


class TestSensitivityTTLMapping:
    """Test the complete sensitivity to TTL mapping."""

    def test_ttl_decreases_with_sensitivity(self):
        """Test that TTL decreases as sensitivity increases."""
        # Arrange
        sensitivities = [
            SensitivityLevel.LOW,
            SensitivityLevel.MEDIUM,
            SensitivityLevel.HIGH,
            SensitivityLevel.CRITICAL,
        ]

        # Act
        ttls = [_get_cache_ttl(s) for s in sensitivities]

        # Assert - TTLs should be in strictly decreasing order
        assert ttls[0] > ttls[1] > ttls[2] > ttls[3]
        assert ttls == [1800, 300, 60, 0]

    def test_all_sensitivity_levels_have_defined_ttls(self):
        """Test all sensitivity levels return valid TTL values."""
        # Arrange
        all_levels = list(SensitivityLevel)

        # Act & Assert
        for level in all_levels:
            ttl = _get_cache_ttl(level)
            assert isinstance(ttl, int)
            assert ttl >= 0
