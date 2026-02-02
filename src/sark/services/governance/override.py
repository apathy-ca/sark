"""
Per-request override service for home LLM governance.

Provides PIN-based override functionality for bypassing policy
on a specific request, with proper authentication and audit trail.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.governance import OverrideRequest, OverrideStatus
from sark.services.governance.exceptions import OverrideError

logger = structlog.get_logger()


class OverrideService:
    """
    Service for per-request override with PIN authentication.

    Allows bypassing policy for a specific request when authenticated
    with a valid PIN. Each override is single-use and expires.
    """

    # PIN configuration
    MIN_PIN_LENGTH = 4
    MAX_PIN_LENGTH = 20
    DEFAULT_EXPIRATION_MINUTES = 5
    MAX_EXPIRATION_MINUTES = 60

    def __init__(self, db: AsyncSession, *, master_pin_hash: str | None = None) -> None:
        """
        Initialize with database session.

        Args:
            db: Async database session
            master_pin_hash: Optional pre-configured master PIN hash
        """
        self.db = db
        self._master_pin_hash = master_pin_hash

    async def create_override(
        self,
        request_id: str,
        pin: str,
        *,
        reason: str | None = None,
        requested_by: str | None = None,
        expires_in_minutes: int = DEFAULT_EXPIRATION_MINUTES,
    ) -> OverrideRequest:
        """
        Create a per-request override.

        Args:
            request_id: Original request ID to override
            pin: PIN for authentication
            reason: Reason for override
            requested_by: Who requested the override
            expires_in_minutes: Minutes until override expires

        Returns:
            Created override request

        Raises:
            OverrideError: If validation fails
        """
        # Validate request_id
        if not request_id or not request_id.strip():
            raise OverrideError("Request ID is required")

        # Validate PIN
        if len(pin) < self.MIN_PIN_LENGTH:
            raise OverrideError(f"PIN must be at least {self.MIN_PIN_LENGTH} characters")
        if len(pin) > self.MAX_PIN_LENGTH:
            raise OverrideError(f"PIN cannot exceed {self.MAX_PIN_LENGTH} characters")

        # Validate expiration
        if expires_in_minutes < 1:
            raise OverrideError("Expiration must be at least 1 minute")
        if expires_in_minutes > self.MAX_EXPIRATION_MINUTES:
            raise OverrideError(f"Expiration cannot exceed {self.MAX_EXPIRATION_MINUTES} minutes")

        # Check for existing pending override for this request
        existing = await self._get_pending_by_request_id(request_id)
        if existing:
            raise OverrideError(
                f"Override already exists for request {request_id}",
                details={"override_id": existing.id},
            )

        # Hash the PIN
        pin_hash = self._hash_pin(pin)

        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)

        # Create override request
        override = OverrideRequest(
            request_id=request_id.strip(),
            pin_hash=pin_hash,
            status=OverrideStatus.PENDING.value,
            reason=reason,
            requested_by=requested_by,
            expires_at=expires_at,
        )
        self.db.add(override)
        await self.db.commit()
        await self.db.refresh(override)

        logger.info(
            "override_request_created",
            override_id=override.id,
            request_id=request_id,
            expires_at=expires_at.isoformat(),
        )
        return override

    async def validate_override(
        self,
        request_id: str,
        pin: str,
    ) -> bool:
        """
        Validate and use an override.

        This is the hot-path method for policy evaluation.

        Args:
            request_id: Request ID to check
            pin: PIN to validate

        Returns:
            True if override is valid and now used, False otherwise
        """
        # First check for master PIN
        if self._master_pin_hash and self._verify_pin(pin, self._master_pin_hash):
            logger.warning(
                "override_master_pin_used",
                request_id=request_id,
            )
            return True

        # Get pending override for this request
        override = await self._get_pending_by_request_id(request_id)
        if not override:
            return False

        # Check expiration
        if override.expires_at < datetime.now(UTC):
            override.status = OverrideStatus.EXPIRED.value
            await self.db.commit()
            return False

        # Verify PIN
        if not self._verify_pin(pin, override.pin_hash):
            logger.warning(
                "override_invalid_pin",
                override_id=override.id,
                request_id=request_id,
            )
            return False

        # Mark as used
        override.status = OverrideStatus.USED.value
        override.used_at = datetime.now(UTC)
        await self.db.commit()

        logger.info(
            "override_used",
            override_id=override.id,
            request_id=request_id,
        )
        return True

    async def check_override_exists(self, request_id: str) -> bool:
        """
        Check if a valid override exists for a request (without using it).

        Args:
            request_id: Request ID to check

        Returns:
            True if valid override exists, False otherwise
        """
        override = await self._get_pending_by_request_id(request_id)
        if not override:
            return False

        # Check expiration
        if override.expires_at < datetime.now(UTC):
            override.status = OverrideStatus.EXPIRED.value
            await self.db.commit()
            return False

        return True

    async def cancel_override(
        self,
        request_id: str,
        *,
        cancelled_by: str | None = None,
    ) -> bool:
        """
        Cancel a pending override.

        Args:
            request_id: Request ID of override to cancel
            cancelled_by: Who cancelled the override

        Returns:
            True if cancelled, False if not found
        """
        override = await self._get_pending_by_request_id(request_id)
        if not override:
            return False

        override.status = OverrideStatus.DENIED.value
        await self.db.commit()

        logger.info(
            "override_cancelled",
            override_id=override.id,
            request_id=request_id,
            cancelled_by=cancelled_by,
        )
        return True

    async def get_override(self, override_id: int) -> OverrideRequest | None:
        """Get override request by ID."""
        result = await self.db.execute(
            select(OverrideRequest).where(OverrideRequest.id == override_id)
        )
        return result.scalar_one_or_none()

    async def list_overrides(
        self,
        *,
        status: OverrideStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OverrideRequest]:
        """
        List override requests.

        Args:
            status: Filter by status
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of override requests
        """
        query = select(OverrideRequest)

        if status:
            query = query.where(OverrideRequest.status == status.value)

        query = query.order_by(OverrideRequest.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_statistics(self) -> dict:
        """
        Get override statistics.

        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func

        stats = {}

        # Total by status
        for status in OverrideStatus:
            result = await self.db.execute(
                select(func.count(OverrideRequest.id)).where(
                    OverrideRequest.status == status.value
                )
            )
            stats[f"total_{status.value}"] = result.scalar() or 0

        # Currently pending
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(func.count(OverrideRequest.id)).where(
                OverrideRequest.status == OverrideStatus.PENDING.value,
                OverrideRequest.expires_at > now,
            )
        )
        stats["currently_pending"] = result.scalar() or 0

        # Last 24 hours usage
        day_ago = now - timedelta(days=1)
        result = await self.db.execute(
            select(func.count(OverrideRequest.id)).where(
                OverrideRequest.status == OverrideStatus.USED.value,
                OverrideRequest.used_at >= day_ago,
            )
        )
        stats["used_last_24h"] = result.scalar() or 0

        return stats

    async def cleanup_expired(self) -> int:
        """
        Mark expired overrides.

        Returns:
            Number of overrides marked expired
        """
        from sqlalchemy import update

        now = datetime.now(UTC)
        result = await self.db.execute(
            update(OverrideRequest)
            .where(
                OverrideRequest.status == OverrideStatus.PENDING.value,
                OverrideRequest.expires_at < now,
            )
            .values(status=OverrideStatus.EXPIRED.value)
        )
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            logger.info("override_requests_expired", count=count)
        return count

    def set_master_pin(self, pin: str) -> None:
        """
        Set the master override PIN.

        The master PIN can be used to override any request.

        Args:
            pin: Master PIN to set
        """
        if len(pin) < self.MIN_PIN_LENGTH:
            raise OverrideError(f"Master PIN must be at least {self.MIN_PIN_LENGTH} characters")
        self._master_pin_hash = self._hash_pin(pin)
        logger.warning("override_master_pin_set")

    def clear_master_pin(self) -> None:
        """Clear the master override PIN."""
        self._master_pin_hash = None
        logger.warning("override_master_pin_cleared")

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _hash_pin(self, pin: str) -> str:
        """Hash a PIN using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
        return f"{salt}:{hashed}"

    def _verify_pin(self, pin: str, stored_hash: str) -> bool:
        """Verify a PIN against stored hash."""
        try:
            salt, expected_hash = stored_hash.split(":")
            actual_hash = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
            return secrets.compare_digest(actual_hash, expected_hash)
        except (ValueError, AttributeError):
            return False

    async def _get_pending_by_request_id(self, request_id: str) -> OverrideRequest | None:
        """Get pending override by request ID."""
        result = await self.db.execute(
            select(OverrideRequest).where(
                OverrideRequest.request_id == request_id,
                OverrideRequest.status == OverrideStatus.PENDING.value,
            )
        )
        return result.scalar_one_or_none()


# =============================================================================
# Factory function
# =============================================================================


def get_override_service(
    db: AsyncSession,
    *,
    master_pin_hash: str | None = None,
) -> OverrideService:
    """Get override service instance."""
    return OverrideService(db, master_pin_hash=master_pin_hash)
