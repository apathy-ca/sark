"""JWT token handling and validation."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import structlog

from sark.config import get_settings
from sark.services.auth.user_context import UserContext

logger = structlog.get_logger()
settings = get_settings()

# Security scheme for JWT tokens
security = HTTPBearer()


class JWTHandler:
    """Handles JWT token creation and validation."""

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """
        Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens (defaults to settings)
            algorithm: JWT algorithm (HS256 or RS256)
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_days: Refresh token expiration in days
        """
        self.secret_key = secret_key or settings.secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: str,
        teams: list[str] | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new JWT access token.

        Args:
            user_id: User ID
            email: User email
            role: User role
            teams: List of team names
            extra_claims: Additional claims to include

        Returns:
            Encoded JWT token
        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        claims = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "teams": teams or [],
            "iat": now,
            "exp": expire,
            "type": "access",
        }

        if extra_claims:
            claims.update(extra_claims)

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

        logger.info(
            "access_token_created",
            user_id=str(user_id),
            email=email,
            role=role,
            expires_at=expire.isoformat(),
        )

        return token

    def create_refresh_token(
        self,
        user_id: UUID,
        email: str,
    ) -> str:
        """
        Create a new JWT refresh token.

        Args:
            user_id: User ID
            email: User email

        Returns:
            Encoded JWT refresh token
        """
        now = datetime.now(UTC)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        claims = {
            "sub": str(user_id),
            "email": email,
            "iat": now,
            "exp": expire,
            "type": "refresh",
        }

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

        logger.info(
            "refresh_token_created",
            user_id=str(user_id),
            email=email,
            expires_at=expire.isoformat(),
        )

        return token

    def decode_token(self, token: str) -> dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token claims

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Verify token type is access token
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except JWTError as e:
            logger.warning("token_validation_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        """
        Decode and validate a refresh token.

        Args:
            token: JWT refresh token string

        Returns:
            Decoded token claims

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Verify token type is refresh token
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except JWTError as e:
            logger.warning("refresh_token_validation_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def verify_token(self, token: str, token_type: str) -> UUID:
        """
        Verify a JWT token and return the user ID.

        This is a backward compatibility method for tests and legacy code.
        New code should use decode_token() or decode_refresh_token() instead.

        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')

        Returns:
            User ID from token

        Raises:
            HTTPException: If token is invalid, expired, or wrong type
        """
        if token_type == "access":
            payload = self.decode_token(token)
        elif token_type == "refresh":
            payload = self.decode_refresh_token(token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid token type: {token_type}",
            )

        return UUID(payload["sub"])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserContext:
    """
    Extract and validate current user from JWT token.

    This dependency can be used in FastAPI routes to require authentication.

    Args:
        credentials: HTTP Authorization header with Bearer token

    Returns:
        UserContext with user information

    Raises:
        HTTPException: If token is invalid or missing

    Example:
        ```python
        @router.get("/protected")
        async def protected_route(user: UserContext = Depends(get_current_user)):
            return {"user_id": user.user_id}
        ```
    """
    handler = JWTHandler()
    payload = handler.decode_token(credentials.credentials)

    # Extract user information from token
    try:
        user_id = UUID(payload["sub"])
        email = payload["email"]
        role = payload["role"]
        teams = payload.get("teams", [])

        user_context = UserContext(
            user_id=user_id,
            email=email,
            role=role,
            teams=teams,
            is_authenticated=True,
        )

        logger.debug(
            "user_authenticated",
            user_id=str(user_id),
            email=email,
            role=role,
        )

        return user_context

    except (KeyError, ValueError) as e:
        logger.warning("invalid_token_claims", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
