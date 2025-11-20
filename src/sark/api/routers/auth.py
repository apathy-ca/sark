"""Authentication API endpoints.

Provides endpoints for authentication operations including:
- LDAP/AD login
- Token refresh
- Token revocation
- Authentication health checks
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import redis.asyncio as aioredis

from sark.api.dependencies import CurrentUser, get_current_user
from sark.config import get_settings
from sark.services.auth import TokenService
from sark.services.auth.providers import LDAPProvider
from sark.services.auth.providers.ldap import (
    LDAPAuthenticationError,
    LDAPConnectionError,
)

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()


# Pydantic models for request/response
class LDAPLoginRequest(BaseModel):
    """Request model for LDAP login."""

    username: str = Field(..., description="LDAP username", min_length=1, max_length=255)
    password: str = Field(..., description="User password", min_length=1)


class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: str = Field(..., description="Refresh token for obtaining new access tokens")
    user: dict = Field(..., description="User information")


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str = Field(..., description="The refresh token to exchange for a new access token", min_length=1)


class TokenResponse(BaseModel):
    """Response model for token operations."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: str | None = Field(None, description="New refresh token (if rotation enabled)")


class TokenRevokeRequest(BaseModel):
    """Request model for token revocation."""

    refresh_token: str = Field(..., description="The refresh token to revoke", min_length=1)


class TokenRevokeResponse(BaseModel):
    """Response model for token revocation."""

    success: bool = Field(..., description="Whether the revocation was successful")
    message: str = Field(..., description="Status message")


# Dependency to get Redis client
async def get_redis_client() -> aioredis.Redis:
    """Get Redis client for token storage.

    Returns:
        Redis client instance

    Raises:
        HTTPException: If Redis connection fails
    """
    try:
        redis_client = aioredis.from_url(
            settings.redis_dsn,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await redis_client.ping()
        return redis_client
    except Exception as e:
        logger.error(
            "redis_connection_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from e


# Dependency to get token service
async def get_token_service(
    redis_client: aioredis.Redis = Depends(get_redis_client),
) -> TokenService:
    """Get token service instance.

    Args:
        redis_client: Redis client dependency

    Returns:
        Configured TokenService instance
    """
    return TokenService(settings=settings, redis_client=redis_client)


@router.post(
    "/login/ldap",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="LDAP/AD login",
    description="Authenticate user against LDAP/Active Directory and issue JWT tokens",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        503: {"description": "LDAP service unavailable"},
    },
)
async def ldap_login(
    request: LDAPLoginRequest,
    token_service: TokenService = Depends(get_token_service),
) -> LoginResponse:
    """Authenticate user via LDAP/Active Directory.

    This endpoint authenticates the user against an LDAP directory
    (including Microsoft Active Directory) and returns JWT tokens
    along with user information.

    Args:
        request: Login request containing username and password
        token_service: Token service dependency

    Returns:
        Access token, refresh token, and user information

    Raises:
        HTTPException: If authentication fails or LDAP is unavailable
    """
    if not settings.ldap_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LDAP authentication is not enabled",
        )

    logger.info("ldap_login_attempt", username=request.username)

    try:
        # Initialize LDAP provider
        ldap_provider = LDAPProvider(settings=settings)

        # Authenticate user and get user info
        user_info = ldap_provider.authenticate(request.username, request.password)

        # Create access token
        access_token = await token_service.create_access_token(user_info)

        # Create refresh token
        refresh_token, _ = await token_service.create_refresh_token(user_info["user_id"])

        # Calculate expiry in seconds
        expires_in = settings.jwt_expiration_minutes * 60

        # Prepare user info for response (remove sensitive data)
        user_response = {
            "user_id": user_info["user_id"],
            "username": user_info.get("username"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "roles": user_info.get("roles", []),
            "teams": user_info.get("teams", []),
        }

        logger.info(
            "ldap_login_success",
            username=request.username,
            user_id=user_info["user_id"],
            roles=user_info.get("roles", []),
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token,
            user=user_response,
        )

    except LDAPAuthenticationError as e:
        logger.warning(
            "ldap_login_failed",
            username=request.username,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from e

    except LDAPConnectionError as e:
        logger.error(
            "ldap_connection_error",
            username=request.username,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from e

    except Exception as e:
        logger.error(
            "ldap_login_error_unexpected",
            username=request.username,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to internal error",
        ) from e


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token. "
    "If token rotation is enabled, a new refresh token is also issued.",
    responses={
        200: {"description": "Tokens refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
        503: {"description": "Authentication service unavailable"},
    },
)
async def refresh_token(
    request: TokenRefreshRequest,
    token_service: TokenService = Depends(get_token_service),
) -> TokenResponse:
    """Refresh access token using a refresh token.

    This endpoint allows clients to obtain a new access token without
    requiring the user to re-authenticate.

    If `refresh_token_rotation_enabled` is True, the old refresh token
    is revoked and a new one is issued for enhanced security.

    Args:
        request: Token refresh request containing the refresh token
        token_service: Token service dependency

    Returns:
        New access token and optionally a new refresh token

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    logger.info("token_refresh_requested")

    # Validate refresh token and get user ID
    user_id = await token_service.validate_refresh_token(request.refresh_token)

    if not user_id:
        logger.warning("token_refresh_failed", reason="invalid_refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    try:
        # TODO: Fetch full user context from database/cache
        # For now, use minimal context with just user_id
        # This will be enhanced in TASK-202 (User Context Service)
        user_context = {
            "user_id": user_id,
            "roles": [],
            "teams": [],
            "permissions": [],
        }

        # Create new access token
        access_token = await token_service.create_access_token(user_context)

        # Calculate expiry in seconds
        expires_in = settings.jwt_expiration_minutes * 60

        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

        # Rotate refresh token if enabled
        if settings.refresh_token_rotation_enabled:
            rotation_result = await token_service.rotate_refresh_token(
                request.refresh_token, user_id
            )

            if rotation_result:
                new_refresh_token, _ = rotation_result
                response_data["refresh_token"] = new_refresh_token
                logger.info("token_refresh_success_with_rotation", user_id=user_id)
            else:
                logger.warning(
                    "token_rotation_failed",
                    user_id=user_id,
                    message="Failed to rotate refresh token",
                )
                # Continue with access token issuance even if rotation failed
        else:
            logger.info("token_refresh_success", user_id=user_id)

        return TokenResponse(**response_data)

    except Exception as e:
        logger.error(
            "token_refresh_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token",
        ) from e


@router.post(
    "/revoke",
    response_model=TokenRevokeResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke refresh token",
    description="Revoke a refresh token to prevent it from being used again. "
    "This is useful for logout functionality.",
    responses={
        200: {"description": "Token revoked successfully"},
        401: {"description": "Authentication required"},
        503: {"description": "Authentication service unavailable"},
    },
)
async def revoke_token(
    request: TokenRevokeRequest,
    user: CurrentUser,  # Require authentication to revoke tokens
    token_service: TokenService = Depends(get_token_service),
) -> TokenRevokeResponse:
    """Revoke a refresh token.

    This endpoint allows users to revoke their own refresh tokens,
    effectively logging them out from that session.

    Args:
        request: Token revocation request containing the refresh token
        user: Current authenticated user (from access token)
        token_service: Token service dependency

    Returns:
        Revocation status

    Raises:
        HTTPException: If revocation fails
    """
    logger.info("token_revoke_requested", user_id=user.user_id)

    try:
        # Revoke the refresh token
        success = await token_service.revoke_refresh_token(request.refresh_token)

        if success:
            return TokenRevokeResponse(
                success=True,
                message="Refresh token revoked successfully",
            )
        else:
            # Token was not found, but this isn't necessarily an error
            # (could already be revoked or expired)
            return TokenRevokeResponse(
                success=True,
                message="Refresh token not found (may already be revoked or expired)",
            )

    except Exception as e:
        logger.error(
            "token_revoke_error",
            user_id=user.user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke token",
        ) from e


@router.get(
    "/me",
    summary="Get current user",
    description="Get information about the currently authenticated user",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Authentication required"},
    },
)
async def get_current_user_info(user: CurrentUser) -> dict:
    """Get current authenticated user information.

    This endpoint returns information about the user from their JWT token.
    Useful for verifying authentication and retrieving user details.

    Args:
        user: Current authenticated user

    Returns:
        User information dictionary
    """
    logger.debug("user_info_requested", user_id=user.user_id)

    return user.to_dict()
