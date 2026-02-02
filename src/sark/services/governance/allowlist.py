"""
Allowlist service for home LLM governance.

Manages device/user allowlist entries that bypass all policy evaluation.
Supports IP addresses, MAC addresses, and user IDs.
"""

from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.governance import (
    AllowlistEntry,
    AllowlistEntryCreate,
    AllowlistEntryResponse,
    AllowlistEntryType,
)
from sark.services.governance.exceptions import AllowlistError

logger = structlog.get_logger()


class AllowlistService:
    """
    Service for managing device/user allowlist.

    Devices or users in the allowlist bypass all policy evaluation,
    making them exempt from time rules, content filtering, etc.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db
        self._cache: dict[str, bool] = {}  # Simple in-memory cache
        self._cache_ttl = 60  # Cache TTL in seconds
        self._cache_updated: datetime | None = None

    async def add_entry(
        self,
        identifier: str,
        entry_type: AllowlistEntryType = AllowlistEntryType.DEVICE,
        *,
        name: str | None = None,
        reason: str | None = None,
        created_by: str | None = None,
        expires_at: datetime | None = None,
    ) -> AllowlistEntry:
        """
        Add entry to allowlist.

        Args:
            identifier: IP address, MAC address, or user ID
            entry_type: Type of entry (device, user, mac)
            name: Human-readable name for the entry
            reason: Reason for allowlisting
            created_by: Who added this entry
            expires_at: Optional expiration time

        Returns:
            Created allowlist entry

        Raises:
            AllowlistError: If entry already exists or validation fails
        """
        # Validate identifier based on type
        identifier = self._validate_identifier(identifier, entry_type)

        # Check if entry already exists
        existing = await self._get_entry_by_identifier(identifier)
        if existing:
            if existing.active:
                raise AllowlistError(
                    f"Entry already exists for {identifier}",
                    details={"identifier": identifier, "entry_id": existing.id},
                )
            # Reactivate existing entry
            existing.active = True
            existing.name = name or existing.name
            existing.reason = reason or existing.reason
            existing.expires_at = expires_at
            existing.updated_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(existing)
            self._invalidate_cache()
            logger.info(
                "allowlist_entry_reactivated",
                identifier=identifier,
                entry_type=entry_type.value,
            )
            return existing

        # Create new entry
        entry = AllowlistEntry(
            entry_type=entry_type.value,
            identifier=identifier,
            name=name,
            reason=reason,
            created_by=created_by,
            expires_at=expires_at,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        self._invalidate_cache()
        logger.info(
            "allowlist_entry_added",
            identifier=identifier,
            entry_type=entry_type.value,
            name=name,
        )
        return entry

    async def add_device(
        self,
        ip_address: str,
        *,
        name: str | None = None,
        reason: str | None = None,
        created_by: str | None = None,
    ) -> AllowlistEntry:
        """
        Add device to allowlist by IP address.

        Convenience method for adding device entries.

        Args:
            ip_address: Device IP address
            name: Human-readable name (e.g., "dad-laptop")
            reason: Reason for allowlisting (e.g., "Admin device")
            created_by: Who added this entry

        Returns:
            Created allowlist entry
        """
        return await self.add_entry(
            ip_address,
            AllowlistEntryType.DEVICE,
            name=name,
            reason=reason,
            created_by=created_by,
        )

    async def remove_entry(self, identifier: str) -> bool:
        """
        Remove entry from allowlist (soft delete).

        Args:
            identifier: IP address, MAC address, or user ID

        Returns:
            True if entry was removed, False if not found
        """
        entry = await self._get_entry_by_identifier(identifier)
        if not entry:
            return False

        entry.active = False
        entry.updated_at = datetime.now(UTC)
        await self.db.commit()

        self._invalidate_cache()
        logger.info("allowlist_entry_removed", identifier=identifier)
        return True

    async def is_allowed(self, identifier: str) -> bool:
        """
        Check if identifier is in active allowlist.

        This is the hot-path method - optimized for fast lookups.

        Args:
            identifier: IP address, MAC address, or user ID

        Returns:
            True if identifier is allowlisted, False otherwise
        """
        # Check cache first
        cache_key = identifier.lower()
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]

        # Query database
        result = await self.db.execute(
            select(AllowlistEntry).where(
                AllowlistEntry.identifier == identifier,
                AllowlistEntry.active == True,  # noqa: E712
            )
        )
        entry = result.scalar_one_or_none()

        # Check expiration
        if entry and entry.expires_at and entry.expires_at < datetime.now(UTC):
            # Entry expired, deactivate it
            entry.active = False
            await self.db.commit()
            self._invalidate_cache()
            return False

        is_allowed = entry is not None
        self._cache[cache_key] = is_allowed
        return is_allowed

    async def list_entries(
        self,
        *,
        entry_type: AllowlistEntryType | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AllowlistEntry]:
        """
        List allowlist entries.

        Args:
            entry_type: Filter by entry type
            active_only: Only return active entries
            limit: Maximum number of entries to return
            offset: Number of entries to skip

        Returns:
            List of allowlist entries
        """
        query = select(AllowlistEntry)

        if entry_type:
            query = query.where(AllowlistEntry.entry_type == entry_type.value)
        if active_only:
            query = query.where(AllowlistEntry.active == True)  # noqa: E712

        query = query.order_by(AllowlistEntry.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_entry(self, entry_id: int) -> AllowlistEntry | None:
        """Get allowlist entry by ID."""
        result = await self.db.execute(
            select(AllowlistEntry).where(AllowlistEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def update_entry(
        self,
        entry_id: int,
        *,
        name: str | None = None,
        reason: str | None = None,
        expires_at: datetime | None = None,
        active: bool | None = None,
    ) -> AllowlistEntry | None:
        """
        Update allowlist entry.

        Args:
            entry_id: Entry ID to update
            name: New name (None to keep existing)
            reason: New reason (None to keep existing)
            expires_at: New expiration (None to keep existing)
            active: New active status (None to keep existing)

        Returns:
            Updated entry or None if not found
        """
        entry = await self.get_entry(entry_id)
        if not entry:
            return None

        if name is not None:
            entry.name = name
        if reason is not None:
            entry.reason = reason
        if expires_at is not None:
            entry.expires_at = expires_at
        if active is not None:
            entry.active = active

        entry.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(entry)

        self._invalidate_cache()
        logger.info("allowlist_entry_updated", entry_id=entry_id)
        return entry

    async def count_entries(self, *, active_only: bool = True) -> int:
        """Count total allowlist entries."""
        from sqlalchemy import func

        query = select(func.count(AllowlistEntry.id))
        if active_only:
            query = query.where(AllowlistEntry.active == True)  # noqa: E712

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def cleanup_expired(self) -> int:
        """
        Deactivate expired allowlist entries.

        Returns:
            Number of entries deactivated
        """
        from sqlalchemy import update

        now = datetime.now(UTC)
        result = await self.db.execute(
            update(AllowlistEntry)
            .where(
                AllowlistEntry.active == True,  # noqa: E712
                AllowlistEntry.expires_at < now,
            )
            .values(active=False, updated_at=now)
        )
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            self._invalidate_cache()
            logger.info("allowlist_expired_entries_cleaned", count=count)
        return count

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _validate_identifier(self, identifier: str, entry_type: AllowlistEntryType) -> str:
        """Validate and normalize identifier."""
        identifier = identifier.strip()
        if not identifier:
            raise AllowlistError("Identifier cannot be empty")

        if entry_type == AllowlistEntryType.DEVICE:
            # Validate IP address
            try:
                ip = ip_address(identifier)
                return str(ip)  # Normalize IP format
            except ValueError as e:
                raise AllowlistError(f"Invalid IP address: {identifier}") from e

        elif entry_type == AllowlistEntryType.MAC:
            # Validate MAC address (basic validation)
            mac = identifier.upper().replace("-", ":").replace(".", ":")
            parts = mac.split(":")
            if len(parts) != 6:
                raise AllowlistError(f"Invalid MAC address: {identifier}")
            for part in parts:
                if len(part) != 2 or not all(c in "0123456789ABCDEF" for c in part):
                    raise AllowlistError(f"Invalid MAC address: {identifier}")
            return mac

        elif entry_type == AllowlistEntryType.USER:
            # User IDs - minimal validation
            if len(identifier) > 100:
                raise AllowlistError("User ID too long (max 100 characters)")
            return identifier

        return identifier

    async def _get_entry_by_identifier(self, identifier: str) -> AllowlistEntry | None:
        """Get entry by identifier."""
        result = await self.db.execute(
            select(AllowlistEntry).where(AllowlistEntry.identifier == identifier)
        )
        return result.scalar_one_or_none()

    def _invalidate_cache(self) -> None:
        """Invalidate the in-memory cache."""
        self._cache.clear()
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


def get_allowlist_service(db: AsyncSession) -> AllowlistService:
    """Get allowlist service instance."""
    return AllowlistService(db)
