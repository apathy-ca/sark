"""API Key authentication for service-to-service communication."""

from datetime import UTC, datetime, timedelta
import secrets
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()

# Security scheme for API keys
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKey(BaseModel):
    """API Key model."""

    key_id: UUID
    key_hash: str
    name: str
    description: str | None = None
    owner_id: UUID
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    is_active: bool = True


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, key_length: int = 32):
        """
        Initialize API key service.

        Args:
            key_length: Length of generated API keys in bytes
        """
        self.key_length = key_length

    def generate_key(self) -> str:
        """
        Generate a new API key.

        Returns:
            Secure random API key
        """
        return secrets.token_urlsafe(self.key_length)

    def hash_key(self, api_key: str) -> str:
        """
        Hash an API key for storage.

        Args:
            api_key: Plain text API key

        Returns:
            Hashed API key
        """
        import hashlib

        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_key(self, plain_key: str, key_hash: str) -> bool:
        """
        Verify an API key against its hash.

        Args:
            plain_key: Plain text API key
            key_hash: Stored key hash

        Returns:
            True if key matches hash
        """
        return self.hash_key(plain_key) == key_hash

    def create_api_key(
        self,
        name: str,
        owner_id: UUID,
        scopes: list[str] | None = None,
        description: str | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.

        Args:
            name: Human-readable name for the key
            owner_id: User/service that owns this key
            scopes: List of permission scopes
            description: Optional description
            expires_in_days: Days until expiration (None = no expiration)

        Returns:
            Tuple of (plain_key, api_key_object)
        """
        from uuid import uuid4

        plain_key = self.generate_key()
        key_hash = self.hash_key(plain_key)

        now = datetime.now(UTC)
        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)

        api_key = APIKey(
            key_id=uuid4(),
            key_hash=key_hash,
            name=name,
            description=description,
            owner_id=owner_id,
            scopes=scopes or [],
            created_at=now,
            expires_at=expires_at,
            is_active=True,
        )

        logger.info(
            "api_key_created",
            key_id=str(api_key.key_id),
            name=name,
            owner_id=str(owner_id),
            scopes=scopes,
        )

        return plain_key, api_key

    def validate_api_key(self, api_key: APIKey) -> bool:
        """
        Validate an API key's status and expiration.

        Args:
            api_key: API key to validate

        Returns:
            True if key is valid

        Raises:
            HTTPException: If key is invalid, expired, or inactive
        """
        if not api_key.is_active:
            logger.warning("api_key_inactive", key_id=str(api_key.key_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is inactive",
            )

        if api_key.expires_at and datetime.now(UTC) > api_key.expires_at:
            logger.warning("api_key_expired", key_id=str(api_key.key_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )

        return True

    def has_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """
        Check if API key has a required scope.

        Args:
            api_key: API key to check
            required_scope: Required permission scope

        Returns:
            True if key has the scope
        """
        return required_scope in api_key.scopes or "*" in api_key.scopes

    def has_any_scope(self, api_key: APIKey, required_scopes: list[str]) -> bool:
        """
        Check if API key has any of the required scopes.

        Args:
            api_key: API key to check
            required_scopes: List of required permission scopes

        Returns:
            True if key has any of the scopes
        """
        if "*" in api_key.scopes:
            return True
        return any(scope in api_key.scopes for scope in required_scopes)


# In-memory storage for demonstration (replace with database in production)
_api_key_store: dict[str, APIKey] = {}


async def get_api_key(
    api_key_value: str | None = Security(api_key_header),
) -> APIKey:
    """
    Validate and retrieve API key from header.

    This dependency can be used in FastAPI routes to require API key authentication.

    Args:
        api_key_value: API key from X-API-Key header

    Returns:
        APIKey object

    Raises:
        HTTPException: If API key is missing or invalid

    Example:
        ```python
        @router.get("/protected")
        async def protected_route(api_key: APIKey = Depends(get_api_key)):
            return {"owner": api_key.owner_id}
        ```
    """
    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )

    service = APIKeyService()

    # Search for matching key in store
    for stored_key in _api_key_store.values():
        if service.verify_key(api_key_value, stored_key.key_hash):
            # Validate key status and expiration
            service.validate_api_key(stored_key)

            logger.info("api_key_authenticated", key_id=str(stored_key.key_id))
            return stored_key

    logger.warning("api_key_invalid", key_value_prefix=api_key_value[:8])
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def require_scope(required_scope: str):
    """
    Dependency to require a specific API key scope.

    Args:
        required_scope: Required permission scope

    Returns:
        Dependency function

    Example:
        ```python
        @router.delete("/servers/{server_id}")
        async def delete_server(
            server_id: UUID,
            api_key: APIKey = Depends(require_scope("servers:delete")),
        ):
            pass
        ```
    """

    async def _check_scope(api_key: APIKey = Depends(get_api_key)) -> APIKey:
        service = APIKeyService()
        if not service.has_scope(api_key, required_scope):
            logger.warning(
                "api_key_insufficient_scope",
                key_id=str(api_key.key_id),
                required=required_scope,
                available=api_key.scopes,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key lacks required scope: {required_scope}",
            )
        return api_key

    return _check_scope
