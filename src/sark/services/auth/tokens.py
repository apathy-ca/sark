"""Token management service for JWT access and refresh tokens.

This service handles:
- Access token generation
- Refresh token generation and validation
- Token rotation
- Token revocation via Redis
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Tuple

import redis.asyncio as aioredis
import structlog
from jose import JWTError, jwt

from sark.config import get_settings

logger = structlog.get_logger(__name__)


class TokenService:
    """Service for managing JWT and refresh tokens."""

    def __init__(self, settings=None, redis_client=None):
        """Initialize token service.

        Args:
            settings: Settings instance (defaults to get_settings())
            redis_client: Redis client instance (optional, for refresh token storage)
        """
        self.settings = settings or get_settings()
        self.redis_client = redis_client

        # Determine JWT key based on algorithm
        if self.settings.jwt_algorithm == "RS256":
            # For RS256, we need a private key for signing
            # In production, this should come from Vault or secure storage
            self.jwt_signing_key = getattr(self.settings, "jwt_private_key", None)
            if not self.jwt_signing_key:
                logger.warning(
                    "jwt_private_key_missing",
                    message="RS256 algorithm requires jwt_private_key for signing",
                )
                # Fallback to HS256 for development
                self.jwt_signing_key = self.settings.secret_key
                self.settings.jwt_algorithm = "HS256"
        else:  # HS256
            self.jwt_signing_key = (
                self.settings.jwt_secret_key or self.settings.secret_key
            )

    async def create_access_token(self, user_context: dict) -> str:
        """Create a new JWT access token.

        Args:
            user_context: Dictionary containing user information:
                - user_id (required): Unique user identifier
                - email: User email
                - name: User display name
                - roles: List of roles
                - teams: List of teams
                - permissions: List of permissions

        Returns:
            JWT access token string

        Raises:
            ValueError: If required fields are missing
        """
        if "user_id" not in user_context:
            raise ValueError("user_id is required in user_context")

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self.settings.jwt_expiration_minutes)

        # Build JWT claims
        claims = {
            # Standard JWT claims
            "sub": user_context["user_id"],
            "iat": now,
            "exp": expires_at,
            "type": "access",
            # Optional standard claims
            "email": user_context.get("email"),
            "name": user_context.get("name"),
            # Custom claims
            "roles": user_context.get("roles", []),
            "teams": user_context.get("teams", []),
            "permissions": user_context.get("permissions", []),
        }

        # Add issuer and audience if configured
        if self.settings.jwt_issuer:
            claims["iss"] = self.settings.jwt_issuer
        if self.settings.jwt_audience:
            claims["aud"] = self.settings.jwt_audience

        # Encode JWT
        token = jwt.encode(
            claims,
            self.jwt_signing_key,
            algorithm=self.settings.jwt_algorithm,
        )

        logger.debug(
            "access_token_created",
            user_id=user_context["user_id"],
            expires_at=expires_at.isoformat(),
        )

        return token

    async def create_refresh_token(self, user_id: str) -> Tuple[str, datetime]:
        """Create a new refresh token and store it in Redis.

        Args:
            user_id: Unique user identifier

        Returns:
            Tuple of (refresh_token, expiry_datetime)

        Raises:
            RuntimeError: If Redis client is not configured
        """
        if not self.redis_client:
            raise RuntimeError("Redis client required for refresh token storage")

        # Generate cryptographically secure random token
        refresh_token = secrets.token_urlsafe(32)

        # Calculate expiry
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.settings.refresh_token_expiration_days)
        ttl_seconds = int((expires_at - now).total_seconds())

        # Store in Redis with TTL
        redis_key = f"refresh_token:{refresh_token}"
        await self.redis_client.setex(
            redis_key,
            ttl_seconds,
            user_id,
        )

        logger.debug(
            "refresh_token_created",
            user_id=user_id,
            expires_at=expires_at.isoformat(),
            ttl_seconds=ttl_seconds,
        )

        return refresh_token, expires_at

    async def validate_refresh_token(self, refresh_token: str) -> str | None:
        """Validate refresh token and return associated user ID.

        Args:
            refresh_token: The refresh token to validate

        Returns:
            User ID if token is valid, None if invalid or expired

        Raises:
            RuntimeError: If Redis client is not configured
        """
        if not self.redis_client:
            raise RuntimeError("Redis client required for refresh token validation")

        redis_key = f"refresh_token:{refresh_token}"

        try:
            # Get user ID from Redis
            user_id = await self.redis_client.get(redis_key)

            if user_id:
                # Decode bytes to string if needed
                if isinstance(user_id, bytes):
                    user_id = user_id.decode("utf-8")

                logger.debug("refresh_token_valid", user_id=user_id)
                return user_id

            logger.warning("refresh_token_invalid_or_expired", token=refresh_token[:8] + "...")
            return None

        except Exception as e:
            logger.error(
                "refresh_token_validation_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token by deleting it from Redis.

        Args:
            refresh_token: The refresh token to revoke

        Returns:
            True if token was revoked, False if it didn't exist

        Raises:
            RuntimeError: If Redis client is not configured
        """
        if not self.redis_client:
            raise RuntimeError("Redis client required for refresh token revocation")

        redis_key = f"refresh_token:{refresh_token}"

        try:
            result = await self.redis_client.delete(redis_key)
            success = result > 0

            if success:
                logger.info("refresh_token_revoked", token=refresh_token[:8] + "...")
            else:
                logger.warning("refresh_token_not_found", token=refresh_token[:8] + "...")

            return success

        except Exception as e:
            logger.error(
                "refresh_token_revocation_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def rotate_refresh_token(
        self, old_refresh_token: str, user_id: str
    ) -> Tuple[str, datetime] | None:
        """Rotate a refresh token (revoke old, issue new).

        Args:
            old_refresh_token: The old refresh token to revoke
            user_id: User ID for the new token

        Returns:
            Tuple of (new_refresh_token, expiry_datetime) or None if rotation failed

        Raises:
            RuntimeError: If Redis client is not configured
        """
        if not self.redis_client:
            raise RuntimeError("Redis client required for refresh token rotation")

        # Revoke old token
        revoked = await self.revoke_refresh_token(old_refresh_token)
        if not revoked:
            logger.warning(
                "refresh_token_rotation_failed",
                reason="old_token_not_found",
                user_id=user_id,
            )
            return None

        # Create new token
        new_token, expires_at = await self.create_refresh_token(user_id)

        logger.info("refresh_token_rotated", user_id=user_id)

        return new_token, expires_at

    async def decode_access_token(self, token: str) -> dict | None:
        """Decode and validate an access token.

        Args:
            token: JWT access token string

        Returns:
            Decoded token payload or None if invalid

        Note: This is a utility method. The middleware already validates tokens.
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_signing_key,
                algorithms=[self.settings.jwt_algorithm],
                issuer=self.settings.jwt_issuer,
                audience=self.settings.jwt_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": self.settings.jwt_issuer is not None,
                    "verify_aud": self.settings.jwt_audience is not None,
                },
            )
            return payload
        except JWTError as e:
            logger.warning("access_token_decode_failed", error=str(e))
            return None
