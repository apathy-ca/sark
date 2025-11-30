"""API Key management endpoints."""

from datetime import datetime
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sark.api.dependencies import CurrentUser
from sark.db.session import get_db
from sark.services.auth.api_keys import APIKeyService

router = APIRouter(prefix="/api/auth/api-keys", tags=["API Keys"])


# Request/Response Models


class APIKeyCreateRequest(BaseModel):
    """Request model for creating an API key."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable key name")
    description: str | None = Field(None, description="Optional description")
    scopes: list[str] = Field(
        ..., min_items=1, description="Permission scopes (e.g., 'server:read')"
    )
    team_id: uuid.UUID | None = Field(None, description="Optional team ID")
    rate_limit: int = Field(
        1000, ge=1, le=10000, description="Maximum requests per minute (1-10000)"
    )
    expires_in_days: int | None = Field(
        None, ge=1, le=365, description="Expiration in days (None for no expiration)"
    )
    environment: str = Field("live", description="Environment (live, test, dev)")


class APIKeyUpdateRequest(BaseModel):
    """Request model for updating an API key."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    scopes: list[str] | None = Field(None, min_items=1)
    rate_limit: int | None = Field(None, ge=1, le=10000)
    is_active: bool | None = None


class APIKeyResponse(BaseModel):
    """Response model for an API key (without secret)."""

    id: uuid.UUID
    user_id: uuid.UUID
    team_id: uuid.UUID | None
    name: str
    description: str | None
    key_prefix: str
    scopes: list[str]
    rate_limit: int
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    last_used_ip: str | None
    usage_count: int
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None

    class Config:
        """Pydantic config."""

        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response model when creating an API key (includes secret once)."""

    api_key: APIKeyResponse
    key: str = Field(..., description="Full API key (shown only once!)")
    message: str = "API key created successfully. Save this key securely - it won't be shown again!"


class APIKeyRotateResponse(BaseModel):
    """Response model when rotating an API key."""

    api_key: APIKeyResponse
    key: str = Field(..., description="New API key (shown only once!)")
    message: str = "API key rotated successfully. Update your applications with the new key."


# Dependencies


async def get_api_key_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIKeyService:
    """Get API key service dependency."""
    return APIKeyService(db)


# Endpoints


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreateRequest,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    current_user: CurrentUser,
) -> APIKeyCreateResponse:
    """Create a new API key.

    **Authentication Required:** This endpoint requires a valid authentication token.

    **Important:** The API key secret is returned only once. Save it securely!

    **Scopes:**
    - `server:read` - Read server information
    - `server:write` - Register/update servers
    - `server:delete` - Delete servers
    - `policy:read` - Read policies
    - `policy:write` - Create/update policies
    - `audit:read` - Read audit logs
    - `admin` - Full admin access
    """
    # Convert user_id string to UUID (user_id comes from authenticated context)
    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    try:
        api_key, full_key = await service.create_api_key(
            user_id=user_id,
            name=request.name,
            scopes=request.scopes,
            description=request.description,
            team_id=request.team_id,
            rate_limit=request.rate_limit,
            expires_in_days=request.expires_in_days,
            environment=request.environment,
        )

        return APIKeyCreateResponse(
            api_key=APIKeyResponse.model_validate(api_key),
            key=full_key,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    current_user: CurrentUser,
    team_id: uuid.UUID | None = None,
    include_revoked: bool = False,
) -> list[APIKeyResponse]:
    """List API keys for the current user or team.

    **Authentication Required:** Returns only keys owned by the authenticated user.
    """
    # Convert user_id string to UUID
    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    api_keys = await service.list_api_keys(
        user_id=user_id,
        team_id=team_id,
        include_revoked=include_revoked,
    )

    return [APIKeyResponse.model_validate(key) for key in api_keys]


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    current_user: CurrentUser,
) -> APIKeyResponse:
    """Get an API key by ID.

    **Authentication Required:** Users can only access their own API keys.
    Admins can access all keys.
    """
    # Convert user_id string to UUID
    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    api_key = await service.get_api_key_by_id(key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Ownership check: Users can only access their own keys (unless admin)
    if api_key.user_id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own API keys",
        )

    return APIKeyResponse.model_validate(api_key)


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    request: APIKeyUpdateRequest,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    current_user: CurrentUser,
) -> APIKeyResponse:
    """Update an API key's metadata.

    **Authentication Required:** Users can only update their own API keys.
    """
    # Convert user_id string to UUID
    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Check ownership before updating
    existing_key = await service.get_api_key_by_id(key_id)
    if existing_key and existing_key.user_id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only update your own API keys",
        )

    try:
        api_key = await service.update_api_key(
            key_id=key_id,
            name=request.name,
            description=request.description,
            scopes=request.scopes,
            rate_limit=request.rate_limit,
            is_active=request.is_active,
        )

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        return APIKeyResponse.model_validate(api_key)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/{key_id}/rotate", response_model=APIKeyRotateResponse)
async def rotate_api_key(
    key_id: uuid.UUID,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    current_user: CurrentUser,
    environment: str = "live",
) -> APIKeyRotateResponse:
    """Rotate an API key (generate new credentials).

    **Authentication Required:** Users can only rotate their own API keys.

    **Important:** The new API key is returned only once. Update your applications!
    """
    # Convert user_id string to UUID
    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Check ownership before rotating
    existing_key = await service.get_api_key_by_id(key_id)
    if existing_key and existing_key.user_id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only rotate your own API keys",
        )

    result = await service.rotate_api_key(key_id, environment)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key, new_key = result

    return APIKeyRotateResponse(
        api_key=APIKeyResponse.model_validate(api_key),
        key=new_key,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    current_user: CurrentUser,
) -> None:
    """Revoke an API key.

    **Authentication Required:** Users can only revoke their own API keys.

    Revoked keys cannot be used for authentication and cannot be reactivated.
    """
    # Convert user_id string to UUID
    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Check ownership before revoking
    existing_key = await service.get_api_key_by_id(key_id)
    if existing_key and existing_key.user_id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only revoke your own API keys",
        )

    success = await service.revoke_api_key(key_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
