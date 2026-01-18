"""JWT authentication middleware for SARK API.

This middleware handles:
- JWT token extraction from Authorization header
- Token validation (signature, expiry, claims)
- Support for RS256 (asymmetric) and HS256 (symmetric) algorithms
- User context extraction and attachment to request state
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
import jwt  # PyJWT library (replaced python-jose to eliminate ecdsa dependency)
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from sark.config import get_settings

logger = structlog.get_logger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware.

    Extracts and validates JWT tokens from the Authorization header.
    Supports both RS256 and HS256 algorithms.
    """

    # Public endpoints that don't require authentication
    PUBLIC_PATHS: ClassVar[set[str]] = {
        "/health",
        "/health/live",
        "/health/ready",
        "/health/startup",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/auth/login/ldap",  # LDAP login is public
        "/api/v1/auth/oidc/login",  # OIDC login initiation is public
        "/api/v1/auth/oidc/callback",  # OIDC callback is public
        "/api/v1/auth/refresh",  # Token refresh doesn't require access token
    }

    def __init__(self, app, settings=None):
        """Initialize the authentication middleware.

        Args:
            app: FastAPI application instance
            settings: Settings instance (defaults to get_settings())
        """
        super().__init__(app)
        self.settings = settings or get_settings()

        # Determine the JWT secret/key based on algorithm
        if self.settings.jwt_algorithm == "RS256":
            self.jwt_key = self.settings.jwt_public_key
            if not self.jwt_key:
                raise ValueError("JWT_PUBLIC_KEY must be set when using RS256 algorithm")
        else:  # HS256
            self.jwt_key = self.settings.jwt_secret_key or self.settings.secret_key

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and validate JWT token.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response from the next handler or error response
        """
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        try:
            # Extract and validate token
            token = self._extract_token(request)
            if not token:
                raise AuthenticationError("Missing authorization token")

            # Decode and validate JWT
            payload = self._decode_token(token)

            # Attach user context to request state
            request.state.user = self._extract_user_context(payload)

            logger.debug(
                "authentication_success",
                user_id=request.state.user.get("user_id"),
                path=request.url.path,
            )

            response = await call_next(request)
            return response

        except AuthenticationError as e:
            logger.warning(
                "authentication_failed",
                error=e.message,
                path=request.url.path,
                status_code=e.status_code,
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.message,
                    "error_type": "authentication_error",
                },
            )
        except Exception as e:
            logger.error(
                "authentication_error_unexpected",
                error=str(e),
                error_type=type(e).__name__,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal authentication error",
                    "error_type": "internal_error",
                },
            )

    def _is_public_path(self, path: str) -> bool:
        """Check if the path is public and doesn't require authentication.

        Args:
            path: The request path

        Returns:
            True if path is public, False otherwise
        """
        # Exact match
        if path in self.PUBLIC_PATHS:
            return True

        # Prefix match for paths like /health/*
        return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)

    def _extract_token(self, request: Request) -> str | None:
        """Extract JWT token from Authorization header.

        Args:
            request: The incoming request

        Returns:
            The extracted token or None if not found

        Raises:
            AuthenticationError: If the Authorization header format is invalid
        """
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        # Expected format: "Bearer <token>"
        parts = auth_header.split()

        if len(parts) != 2:
            raise AuthenticationError(
                "Invalid authorization header format. Expected 'Bearer <token>'"
            )

        scheme, token = parts

        if scheme.lower() != "bearer":
            raise AuthenticationError(f"Invalid authorization scheme: {scheme}. Expected 'Bearer'")

        return token

    def _decode_token(self, token: str) -> dict:
        """Decode and validate JWT token.

        Args:
            token: The JWT token string

        Returns:
            The decoded token payload

        Raises:
            AuthenticationError: If token is invalid, expired, or verification fails
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                self.jwt_key,
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

            # Additional expiry validation
            exp = payload.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=UTC)
                if datetime.now(UTC) >= exp_datetime:
                    raise AuthenticationError("Token has expired")

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired") from None
        except jwt.InvalidSignatureError as e:
            raise AuthenticationError(f"Invalid token signature: {e!s}") from None
        except jwt.DecodeError as e:
            raise AuthenticationError(f"Invalid token format: {e!s}") from None
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e!s}") from None
        except Exception as e:
            logger.error(
                "token_decode_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise AuthenticationError("Token validation failed") from None

    def _extract_user_context(self, payload: dict) -> dict:
        """Extract user context from JWT payload.

        Args:
            payload: The decoded JWT payload

        Returns:
            Dictionary containing user context information

        Common JWT claims:
        - sub: Subject (user ID)
        - email: User email
        - name: User name
        - roles: User roles (list)
        - groups/teams: User teams/groups (list)
        - permissions: User permissions (list)
        """
        # Standard claims
        user_context = {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name", payload.get("preferred_username")),
            "roles": payload.get("roles", []),
            "teams": payload.get("groups", payload.get("teams", [])),
            "permissions": payload.get("permissions", []),
            # Store original payload for additional claims
            "_raw_payload": payload,
        }

        # Ensure user_id is present
        if not user_context["user_id"]:
            raise AuthenticationError("Token missing required 'sub' (subject) claim")

        return user_context
