"""API Key management service.

Handles creation, validation, rotation, and rate limiting of API keys.
"""

from datetime import UTC, datetime, timedelta
import secrets
from typing import Any, ClassVar
import uuid

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.api_key import APIKey


class APIKeyService:
    """Service for managing API keys."""

    # API key format: sark_<prefix>_<secret>
    # Example: sark_sk_live_AbCdEfGhIjKlMnOpQrStUvWxYz123456
    KEY_PREFIX = "sark"
    KEY_SEPARATOR = "_"
    PREFIX_LENGTH = 8  # Random prefix for key identification
    SECRET_LENGTH = 32  # Secret portion length

    # Scope definitions
    VALID_SCOPES: ClassVar[set[str]] = {
        "server:read",  # Read server information
        "server:write",  # Register/update servers
        "server:delete",  # Delete servers
        "policy:read",  # Read policies
        "policy:write",  # Create/update policies
        "audit:read",  # Read audit logs
        "admin",  # Full admin access
    }

    def __init__(self, db_session: AsyncSession):
        """Initialize API key service.

        Args:
            db_session: Database session
        """
        self.db = db_session

    @classmethod
    def generate_key(
        cls,
        environment: str = "live",
    ) -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            Tuple of (full_key, prefix, key_hash)
            - full_key: The complete API key to return to user (only shown once)
            - prefix: The key prefix for identification
            - key_hash: bcrypt hash of the full key for storage
        """
        # Generate cryptographically secure random values
        prefix = secrets.token_urlsafe(cls.PREFIX_LENGTH)[:cls.PREFIX_LENGTH]
        secret = secrets.token_urlsafe(cls.SECRET_LENGTH)[:cls.SECRET_LENGTH]

        # Construct full key: sark_sk_<env>_<prefix>_<secret>
        full_key = f"{cls.KEY_PREFIX}_sk_{environment}_{prefix}_{secret}"

        # Hash the full key for storage
        key_hash = cls._hash_key(full_key)

        return full_key, prefix, key_hash

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash an API key using bcrypt.

        Args:
            key: The API key to hash

        Returns:
            bcrypt hash of the key
        """
        # Use bcrypt with cost factor 12 (good balance of security and performance)
        salt = bcrypt.gensalt(rounds=12)
        key_hash = bcrypt.hashpw(key.encode("utf-8"), salt)
        return key_hash.decode("utf-8")

    @staticmethod
    def verify_key(key: str, key_hash: str) -> bool:
        """Verify an API key against its hash.

        Args:
            key: The API key to verify
            key_hash: The stored bcrypt hash

        Returns:
            True if key matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(key.encode("utf-8"), key_hash.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def extract_prefix(key: str) -> str | None:
        """Extract the prefix from an API key.

        Args:
            key: The full API key

        Returns:
            The prefix portion, or None if invalid format
        """
        # Expected format: sark_sk_<env>_<prefix>_<secret>
        parts = key.split("_")
        if len(parts) >= 4 and parts[0] == "sark" and parts[1] == "sk":
            # Prefix is the 4th part (index 3)
            return parts[3] if len(parts) > 3 else None
        return None

    async def create_api_key(
        self,
        user_id: uuid.UUID,
        name: str,
        scopes: list[str],
        description: str | None = None,
        team_id: uuid.UUID | None = None,
        rate_limit: int = 1000,
        expires_in_days: int | None = None,
        environment: str = "live",
    ) -> tuple[APIKey, str]:
        """Create a new API key.

        Args:
            user_id: ID of the user creating the key
            name: Human-readable name for the key
            scopes: List of permission scopes
            description: Optional description
            team_id: Optional team ID for team-scoped keys
            rate_limit: Maximum requests per minute (default: 1000)
            expires_in_days: Expiration in days (None for no expiration)
            environment: Environment (live, test, dev)

        Returns:
            Tuple of (APIKey model, full_key_string)
            NOTE: The full_key_string should be returned to the user only once

        Raises:
            ValueError: If invalid scopes provided
        """
        # Validate scopes
        invalid_scopes = set(scopes) - self.VALID_SCOPES
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")

        # Generate key
        full_key, prefix, key_hash = self.generate_key(environment)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        # Create database record
        api_key = APIKey(
            user_id=user_id,
            team_id=team_id,
            name=name,
            description=description,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            rate_limit=rate_limit,
            expires_at=expires_at,
            is_active=True,
        )

        self.db.add(api_key)
        await self.db.flush()

        return api_key, full_key

    async def get_api_key_by_id(self, key_id: uuid.UUID) -> APIKey | None:
        """Get an API key by its ID.

        Args:
            key_id: The API key ID

        Returns:
            APIKey model or None if not found
        """
        result = await self.db.execute(select(APIKey).where(APIKey.id == key_id))
        return result.scalar_one_or_none()

    async def get_api_key_by_prefix(self, prefix: str) -> APIKey | None:
        """Get an API key by its prefix.

        Args:
            prefix: The key prefix

        Returns:
            APIKey model or None if not found
        """
        result = await self.db.execute(select(APIKey).where(APIKey.key_prefix == prefix))
        return result.scalar_one_or_none()

    async def list_api_keys(
        self,
        user_id: uuid.UUID | None = None,
        team_id: uuid.UUID | None = None,
        include_revoked: bool = False,
    ) -> list[APIKey]:
        """List API keys.

        Args:
            user_id: Filter by user ID
            team_id: Filter by team ID
            include_revoked: Include revoked keys

        Returns:
            List of APIKey models
        """
        query = select(APIKey)

        if user_id:
            query = query.where(APIKey.user_id == user_id)

        if team_id:
            query = query.where(APIKey.team_id == team_id)

        if not include_revoked:
            query = query.where(APIKey.revoked_at.is_(None))

        query = query.order_by(APIKey.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def validate_api_key(
        self,
        key: str,
        required_scope: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[APIKey | None, str | None]:
        """Validate an API key.

        Args:
            key: The full API key to validate
            required_scope: Optional required scope
            ip_address: Optional IP address for usage tracking

        Returns:
            Tuple of (APIKey model or None, error_message or None)
            - If valid: (APIKey, None)
            - If invalid: (None, "error message")
        """
        # Extract prefix
        prefix = self.extract_prefix(key)
        if not prefix:
            return None, "Invalid API key format"

        # Lookup by prefix
        api_key = await self.get_api_key_by_prefix(prefix)
        if not api_key:
            return None, "API key not found"

        # Verify hash
        if not self.verify_key(key, api_key.key_hash):
            return None, "Invalid API key"

        # Check if active
        if not api_key.is_active:
            return None, "API key is inactive"

        # Check if revoked
        if api_key.revoked_at:
            return None, "API key has been revoked"

        # Check expiration
        if api_key.is_expired:
            return None, "API key has expired"

        # Check scope if required
        if required_scope and required_scope not in api_key.scopes:
            # Check for admin scope (has all permissions)
            if "admin" not in api_key.scopes:
                return None, f"API key does not have required scope: {required_scope}"

        # Record usage
        api_key.record_usage(ip_address)
        await self.db.flush()

        return api_key, None

    async def rotate_api_key(
        self,
        key_id: uuid.UUID,
        environment: str = "live",
    ) -> tuple[APIKey, str] | None:
        """Rotate an API key (generate new credentials).

        Args:
            key_id: ID of the key to rotate
            environment: Environment for new key

        Returns:
            Tuple of (updated APIKey, new_full_key) or None if not found
        """
        # Get existing key
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return None

        # Generate new key
        full_key, prefix, key_hash = self.generate_key(environment)

        # Update the key
        api_key.key_prefix = prefix
        api_key.key_hash = key_hash
        api_key.updated_at = datetime.now(UTC)

        await self.db.flush()

        return api_key, full_key

    async def revoke_api_key(
        self,
        key_id: uuid.UUID,
        revoked_by: uuid.UUID | None = None,
    ) -> bool:
        """Revoke an API key.

        Args:
            key_id: ID of the key to revoke
            revoked_by: UUID of user revoking the key

        Returns:
            True if revoked, False if not found
        """
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return False

        api_key.revoke(revoked_by)
        await self.db.flush()

        return True

    async def update_api_key(
        self,
        key_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        scopes: list[str] | None = None,
        rate_limit: int | None = None,
        is_active: bool | None = None,
    ) -> APIKey | None:
        """Update an API key's metadata.

        Args:
            key_id: ID of the key to update
            name: New name
            description: New description
            scopes: New scopes
            rate_limit: New rate limit
            is_active: New active status

        Returns:
            Updated APIKey or None if not found

        Raises:
            ValueError: If invalid scopes provided
        """
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return None

        # Validate scopes if provided
        if scopes:
            invalid_scopes = set(scopes) - self.VALID_SCOPES
            if invalid_scopes:
                raise ValueError(f"Invalid scopes: {invalid_scopes}")
            api_key.scopes = scopes

        if name is not None:
            api_key.name = name

        if description is not None:
            api_key.description = description

        if rate_limit is not None:
            api_key.rate_limit = rate_limit

        if is_active is not None:
            api_key.is_active = is_active

        api_key.updated_at = datetime.now(UTC)
        await self.db.flush()

        return api_key

    @staticmethod
    def check_rate_limit(
        api_key: APIKey,
        current_usage: int,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if an API key has exceeded its rate limit.

        Args:
            api_key: The API key to check
            current_usage: Current usage count in the time window

        Returns:
            Tuple of (is_allowed, rate_limit_info)
            - is_allowed: True if under limit, False if exceeded
            - rate_limit_info: Dict with rate limit details
        """
        is_allowed = current_usage < api_key.rate_limit

        rate_limit_info = {
            "limit": api_key.rate_limit,
            "remaining": max(0, api_key.rate_limit - current_usage),
            "reset_in_seconds": 60,  # Per-minute window
        }

        return is_allowed, rate_limit_info
