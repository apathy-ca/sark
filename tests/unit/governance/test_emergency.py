"""
Unit tests for EmergencyService.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sark.services.governance.emergency import EmergencyService
from sark.services.governance.exceptions import EmergencyOverrideError


class TestEmergencyService:
    """Tests for EmergencyService."""

    @pytest.mark.asyncio
    async def test_activate(self, emergency_service: EmergencyService):
        """Test activating emergency override."""
        override = await emergency_service.activate(
            duration_minutes=60,
            reason="Homework deadline",
            activated_by="parent",
        )

        assert override.active is True
        assert override.reason == "Homework deadline"
        assert override.activated_by == "parent"
        assert override.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_activate_invalid_duration(self, emergency_service: EmergencyService):
        """Test activation with invalid duration raises error."""
        with pytest.raises(EmergencyOverrideError):
            await emergency_service.activate(duration_minutes=0, reason="test")

        with pytest.raises(EmergencyOverrideError):
            await emergency_service.activate(duration_minutes=2000, reason="test")

    @pytest.mark.asyncio
    async def test_activate_empty_reason(self, emergency_service: EmergencyService):
        """Test activation with empty reason raises error."""
        with pytest.raises(EmergencyOverrideError) as exc_info:
            await emergency_service.activate(duration_minutes=60, reason="")

        assert "Reason is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_activate_already_active(self, emergency_service: EmergencyService):
        """Test activating when already active raises error."""
        await emergency_service.activate(duration_minutes=60, reason="First")

        with pytest.raises(EmergencyOverrideError) as exc_info:
            await emergency_service.activate(duration_minutes=60, reason="Second")

        assert "already active" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_is_active_true(self, emergency_service: EmergencyService):
        """Test is_active returns True when override is active."""
        await emergency_service.activate(duration_minutes=60, reason="test")

        assert await emergency_service.is_active() is True

    @pytest.mark.asyncio
    async def test_is_active_false(self, emergency_service: EmergencyService):
        """Test is_active returns False when no override."""
        assert await emergency_service.is_active() is False

    @pytest.mark.asyncio
    async def test_deactivate(self, emergency_service: EmergencyService):
        """Test deactivating emergency override."""
        await emergency_service.activate(duration_minutes=60, reason="test")

        result = await emergency_service.deactivate(deactivated_by="admin")
        assert result is True
        assert await emergency_service.is_active() is False

    @pytest.mark.asyncio
    async def test_deactivate_not_active(self, emergency_service: EmergencyService):
        """Test deactivating when not active returns False."""
        result = await emergency_service.deactivate()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_current(self, emergency_service: EmergencyService):
        """Test getting current override."""
        await emergency_service.activate(duration_minutes=60, reason="test")

        current = await emergency_service.get_current()
        assert current is not None
        assert current.reason == "test"

    @pytest.mark.asyncio
    async def test_get_current_none(self, emergency_service: EmergencyService):
        """Test getting current when no override returns None."""
        current = await emergency_service.get_current()
        assert current is None

    @pytest.mark.asyncio
    async def test_extend(self, emergency_service: EmergencyService):
        """Test extending emergency override."""
        override = await emergency_service.activate(duration_minutes=60, reason="test")
        original_expires = override.expires_at

        extended = await emergency_service.extend(30, extended_by="admin")
        assert extended.expires_at > original_expires

    @pytest.mark.asyncio
    async def test_extend_exceeds_max(self, emergency_service: EmergencyService):
        """Test extending beyond max duration raises error."""
        await emergency_service.activate(duration_minutes=1400, reason="test")

        with pytest.raises(EmergencyOverrideError) as exc_info:
            await emergency_service.extend(100)

        assert "cannot exceed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extend_not_active(self, emergency_service: EmergencyService):
        """Test extending when not active returns None."""
        result = await emergency_service.extend(30)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_history(self, emergency_service: EmergencyService):
        """Test getting override history."""
        # Create and deactivate multiple overrides
        await emergency_service.activate(duration_minutes=60, reason="first")
        await emergency_service.deactivate()
        await emergency_service.activate(duration_minutes=60, reason="second")
        await emergency_service.deactivate()

        history = await emergency_service.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_statistics(self, emergency_service: EmergencyService):
        """Test getting override statistics."""
        await emergency_service.activate(duration_minutes=60, reason="test")

        stats = await emergency_service.get_statistics()
        assert stats["total_overrides"] >= 1
        assert stats["currently_active"] is True

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, emergency_service: EmergencyService):
        """Test cleanup of expired overrides."""
        # Create an override that will expire immediately
        override = await emergency_service.activate(duration_minutes=1, reason="test")

        # Manually expire it by setting expires_at to past
        override.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await emergency_service.db.commit()

        count = await emergency_service.cleanup_expired()
        assert count == 1
