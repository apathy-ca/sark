"""
Unit tests for OverrideService.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sark.models.governance import OverrideStatus
from sark.services.governance.exceptions import OverrideError
from sark.services.governance.override import OverrideService


class TestOverrideService:
    """Tests for OverrideService."""

    @pytest.mark.asyncio
    async def test_create_override(self, override_service: OverrideService):
        """Test creating a per-request override."""
        override = await override_service.create_override(
            request_id="req-123",
            pin="1234",
            reason="Homework help",
            requested_by="parent",
        )

        assert override.request_id == "req-123"
        assert override.status == OverrideStatus.PENDING.value
        assert override.reason == "Homework help"

    @pytest.mark.asyncio
    async def test_create_override_short_pin(self, override_service: OverrideService):
        """Test creating override with short PIN raises error."""
        with pytest.raises(OverrideError) as exc_info:
            await override_service.create_override(
                request_id="req-123",
                pin="123",  # Too short
            )

        assert "at least" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_override_duplicate(self, override_service: OverrideService):
        """Test creating duplicate override raises error."""
        await override_service.create_override(
            request_id="req-123",
            pin="1234",
        )

        with pytest.raises(OverrideError) as exc_info:
            await override_service.create_override(
                request_id="req-123",
                pin="5678",
            )

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_override_valid(self, override_service: OverrideService):
        """Test validating override with correct PIN."""
        await override_service.create_override(
            request_id="req-123",
            pin="1234",
        )

        valid = await override_service.validate_override("req-123", "1234")
        assert valid is True

    @pytest.mark.asyncio
    async def test_validate_override_invalid_pin(self, override_service: OverrideService):
        """Test validating override with wrong PIN."""
        await override_service.create_override(
            request_id="req-123",
            pin="1234",
        )

        valid = await override_service.validate_override("req-123", "5678")
        assert valid is False

    @pytest.mark.asyncio
    async def test_validate_override_nonexistent(self, override_service: OverrideService):
        """Test validating non-existent override."""
        valid = await override_service.validate_override("req-nonexistent", "1234")
        assert valid is False

    @pytest.mark.asyncio
    async def test_validate_override_marks_as_used(self, override_service: OverrideService):
        """Test successful validation marks override as used."""
        await override_service.create_override(
            request_id="req-123",
            pin="1234",
        )

        await override_service.validate_override("req-123", "1234")

        # Second validation should fail (already used)
        valid = await override_service.validate_override("req-123", "1234")
        assert valid is False

    @pytest.mark.asyncio
    async def test_validate_override_expired(self, override_service: OverrideService):
        """Test validating expired override."""
        override = await override_service.create_override(
            request_id="req-123",
            pin="1234",
            expires_in_minutes=1,
        )

        # Manually expire
        override.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await override_service.db.commit()

        valid = await override_service.validate_override("req-123", "1234")
        assert valid is False

    @pytest.mark.asyncio
    async def test_check_override_exists(self, override_service: OverrideService):
        """Test checking if override exists."""
        await override_service.create_override(
            request_id="req-123",
            pin="1234",
        )

        assert await override_service.check_override_exists("req-123") is True
        assert await override_service.check_override_exists("req-999") is False

    @pytest.mark.asyncio
    async def test_cancel_override(self, override_service: OverrideService):
        """Test cancelling an override."""
        await override_service.create_override(
            request_id="req-123",
            pin="1234",
        )

        result = await override_service.cancel_override("req-123", cancelled_by="admin")
        assert result is True

        # Should no longer be valid
        assert await override_service.check_override_exists("req-123") is False

    @pytest.mark.asyncio
    async def test_cancel_override_nonexistent(self, override_service: OverrideService):
        """Test cancelling non-existent override returns False."""
        result = await override_service.cancel_override("req-nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_overrides(self, override_service: OverrideService):
        """Test listing override requests."""
        await override_service.create_override(request_id="req-1", pin="1234")
        await override_service.create_override(request_id="req-2", pin="5678")

        overrides = await override_service.list_overrides()
        assert len(overrides) == 2

    @pytest.mark.asyncio
    async def test_list_overrides_by_status(self, override_service: OverrideService):
        """Test filtering overrides by status."""
        await override_service.create_override(request_id="req-1", pin="1234")
        await override_service.create_override(request_id="req-2", pin="5678")
        await override_service.validate_override("req-1", "1234")  # Mark as used

        pending = await override_service.list_overrides(status=OverrideStatus.PENDING)
        assert len(pending) == 1

        used = await override_service.list_overrides(status=OverrideStatus.USED)
        assert len(used) == 1

    @pytest.mark.asyncio
    async def test_get_statistics(self, override_service: OverrideService):
        """Test getting override statistics."""
        await override_service.create_override(request_id="req-1", pin="1234")
        await override_service.create_override(request_id="req-2", pin="5678")

        stats = await override_service.get_statistics()
        assert stats["currently_pending"] == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, override_service: OverrideService):
        """Test cleanup of expired overrides."""
        override = await override_service.create_override(
            request_id="req-123",
            pin="1234",
            expires_in_minutes=1,
        )

        # Manually expire
        override.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await override_service.db.commit()

        count = await override_service.cleanup_expired()
        assert count == 1

    @pytest.mark.asyncio
    async def test_master_pin(self, override_service: OverrideService):
        """Test master PIN functionality."""
        override_service.set_master_pin("master1234")

        # Master PIN should validate any request
        valid = await override_service.validate_override("any-request", "master1234")
        assert valid is True

    @pytest.mark.asyncio
    async def test_clear_master_pin(self, override_service: OverrideService):
        """Test clearing master PIN."""
        override_service.set_master_pin("master1234")
        override_service.clear_master_pin()

        # Master PIN should no longer work
        valid = await override_service.validate_override("any-request", "master1234")
        assert valid is False

    @pytest.mark.asyncio
    async def test_set_master_pin_short(self, override_service: OverrideService):
        """Test setting short master PIN raises error."""
        with pytest.raises(OverrideError):
            override_service.set_master_pin("123")
