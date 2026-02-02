"""
Emergency override service for home LLM governance.

Provides emergency bypass functionality to disable all policies
temporarily. Useful for urgent situations like homework deadlines.
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.governance import EmergencyOverride
from sark.services.governance.exceptions import EmergencyOverrideError

logger = structlog.get_logger()


class EmergencyService:
    """
    Service for emergency override management.

    When an emergency override is active, all policies are bypassed.
    This is designed for exceptional situations where immediate access is needed.
    """

    # Maximum duration for emergency override (24 hours)
    MAX_DURATION_MINUTES = 1440

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db
        self._cached_override: EmergencyOverride | None = None
        self._cache_updated: datetime | None = None
        self._cache_ttl = 10  # Short TTL for emergency checks

    async def activate(
        self,
        duration_minutes: int,
        reason: str,
        *,
        activated_by: str | None = None,
    ) -> EmergencyOverride:
        """
        Activate emergency override.

        Args:
            duration_minutes: Duration in minutes (1-1440)
            reason: Reason for emergency override
            activated_by: Who activated the override

        Returns:
            Created emergency override

        Raises:
            EmergencyOverrideError: If validation fails or override already active
        """
        # Validate duration
        if duration_minutes < 1:
            raise EmergencyOverrideError("Duration must be at least 1 minute")
        if duration_minutes > self.MAX_DURATION_MINUTES:
            raise EmergencyOverrideError(
                f"Duration cannot exceed {self.MAX_DURATION_MINUTES} minutes (24 hours)"
            )

        # Validate reason
        if not reason or not reason.strip():
            raise EmergencyOverrideError("Reason is required for emergency override")

        # Check if already active
        current = await self._get_current_override()
        if current:
            raise EmergencyOverrideError(
                "Emergency override is already active",
                details={
                    "override_id": current.id,
                    "expires_at": current.expires_at.isoformat(),
                    "reason": current.reason,
                },
            )

        # Calculate expiration
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=duration_minutes)

        # Create override
        override = EmergencyOverride(
            active=True,
            reason=reason.strip(),
            activated_by=activated_by,
            activated_at=now,
            expires_at=expires_at,
        )
        self.db.add(override)
        await self.db.commit()
        await self.db.refresh(override)

        self._invalidate_cache()
        logger.warning(
            "emergency_override_activated",
            override_id=override.id,
            duration_minutes=duration_minutes,
            reason=reason,
            activated_by=activated_by,
            expires_at=expires_at.isoformat(),
        )
        return override

    async def deactivate(
        self,
        *,
        deactivated_by: str | None = None,
    ) -> bool:
        """
        Manually deactivate emergency override.

        Args:
            deactivated_by: Who deactivated the override

        Returns:
            True if override was deactivated, False if no active override
        """
        current = await self._get_current_override()
        if not current:
            return False

        now = datetime.now(UTC)
        current.active = False
        current.deactivated_at = now
        current.deactivated_by = deactivated_by
        await self.db.commit()

        self._invalidate_cache()
        logger.warning(
            "emergency_override_deactivated",
            override_id=current.id,
            deactivated_by=deactivated_by,
        )
        return True

    async def is_active(self) -> bool:
        """
        Check if emergency override is currently active.

        This is the hot-path method - optimized for fast lookups.

        Returns:
            True if emergency override is active, False otherwise
        """
        # Check cache first
        if self._is_cache_valid() and self._cached_override is not None:
            if self._cached_override.expires_at > datetime.now(UTC):
                return True
            # Cached override has expired, invalidate
            self._invalidate_cache()

        override = await self._get_current_override()
        if override:
            # Update cache
            self._cached_override = override
            self._cache_updated = datetime.now(UTC)
            return True

        return False

    async def get_current(self) -> EmergencyOverride | None:
        """
        Get current active emergency override.

        Returns:
            Current override or None if not active
        """
        return await self._get_current_override()

    async def extend(
        self,
        additional_minutes: int,
        *,
        extended_by: str | None = None,
    ) -> EmergencyOverride | None:
        """
        Extend current emergency override.

        Args:
            additional_minutes: Minutes to add to current expiration
            extended_by: Who extended the override

        Returns:
            Updated override or None if no active override

        Raises:
            EmergencyOverrideError: If extension would exceed max duration
        """
        current = await self._get_current_override()
        if not current:
            return None

        # Calculate new expiration
        new_expires_at = current.expires_at + timedelta(minutes=additional_minutes)

        # Check total duration doesn't exceed max
        total_duration = (new_expires_at - current.activated_at).total_seconds() / 60
        if total_duration > self.MAX_DURATION_MINUTES:
            raise EmergencyOverrideError(
                f"Total duration cannot exceed {self.MAX_DURATION_MINUTES} minutes",
                details={
                    "current_duration_minutes": int(total_duration - additional_minutes),
                    "requested_additional_minutes": additional_minutes,
                },
            )

        current.expires_at = new_expires_at
        await self.db.commit()
        await self.db.refresh(current)

        self._invalidate_cache()
        logger.warning(
            "emergency_override_extended",
            override_id=current.id,
            additional_minutes=additional_minutes,
            new_expires_at=new_expires_at.isoformat(),
            extended_by=extended_by,
        )
        return current

    async def get_history(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmergencyOverride]:
        """
        Get history of emergency overrides.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of emergency overrides (newest first)
        """
        result = await self.db.execute(
            select(EmergencyOverride)
            .order_by(EmergencyOverride.activated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_statistics(self) -> dict:
        """
        Get emergency override statistics.

        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func

        # Total overrides
        total_result = await self.db.execute(
            select(func.count(EmergencyOverride.id))
        )
        total = total_result.scalar() or 0

        # Active override
        current = await self._get_current_override()

        # Last 30 days
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        recent_result = await self.db.execute(
            select(func.count(EmergencyOverride.id)).where(
                EmergencyOverride.activated_at >= thirty_days_ago
            )
        )
        recent = recent_result.scalar() or 0

        return {
            "total_overrides": total,
            "overrides_last_30_days": recent,
            "currently_active": current is not None,
            "current_expires_at": current.expires_at.isoformat() if current else None,
            "current_reason": current.reason if current else None,
        }

    async def cleanup_expired(self) -> int:
        """
        Mark expired overrides as inactive.

        Returns:
            Number of overrides marked inactive
        """
        from sqlalchemy import update

        now = datetime.now(UTC)
        result = await self.db.execute(
            update(EmergencyOverride)
            .where(
                EmergencyOverride.active == True,  # noqa: E712
                EmergencyOverride.expires_at < now,
            )
            .values(active=False, deactivated_at=now)
        )
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            self._invalidate_cache()
            logger.info("emergency_overrides_expired", count=count)
        return count

    # =========================================================================
    # Private helpers
    # =========================================================================

    async def _get_current_override(self) -> EmergencyOverride | None:
        """Get current active emergency override."""
        now = datetime.now(UTC)

        # First, clean up any expired overrides
        from sqlalchemy import update

        await self.db.execute(
            update(EmergencyOverride)
            .where(
                EmergencyOverride.active == True,  # noqa: E712
                EmergencyOverride.expires_at < now,
            )
            .values(active=False, deactivated_at=now)
        )

        # Get active override
        result = await self.db.execute(
            select(EmergencyOverride).where(
                EmergencyOverride.active == True,  # noqa: E712
                EmergencyOverride.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    def _invalidate_cache(self) -> None:
        """Invalidate the cache."""
        self._cached_override = None
        self._cache_updated = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_updated is None:
            return False
        age = (datetime.now(UTC) - self._cache_updated).total_seconds()
        return age < self._cache_ttl


# =============================================================================
# Factory function
# =============================================================================


def get_emergency_service(db: AsyncSession) -> EmergencyService:
    """Get emergency service instance."""
    return EmergencyService(db)
