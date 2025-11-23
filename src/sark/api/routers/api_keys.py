"""API Key management endpoints."""

from datetime import datetime
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

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
    # TODO: Add authentication dependency to get current user
    # current_user: Annotated[User, Depends(get_current_user)],
) -> APIKeyCreateResponse:
    """Create a new API key.

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
    # TODO: Replace with actual user ID from authentication
    user_id = uuid.uuid4()  # Mock user ID for now

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
    team_id: uuid.UUID | None = None,
    include_revoked: bool = False,
    # current_user: Annotated[User, Depends(get_current_user)],
) -> list[APIKeyResponse]:
    """List API keys for the current user or team."""
    # TODO: Replace with actual user ID from authentication
    user_id = uuid.uuid4()  # Mock user ID for now

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
    # current_user: Annotated[User, Depends(get_current_user)],
) -> APIKeyResponse:
    """Get an API key by ID."""
    api_key = await service.get_api_key_by_id(key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # TODO: Check if current user owns this key or has admin access

    return APIKeyResponse.model_validate(api_key)


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    request: APIKeyUpdateRequest,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
    # current_user: Annotated[User, Depends(get_current_user)],
) -> APIKeyResponse:
    """Update an API key's metadata."""
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
    environment: str = "live",
    # current_user: Annotated[User, Depends(get_current_user)],
) -> APIKeyRotateResponse:
    """Rotate an API key (generate new credentials).

    **Important:** The new API key is returned only once. Update your applications!
    """
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
    # current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Revoke an API key.

    Revoked keys cannot be used for authentication and cannot be reactivated.
    """
    # TODO: Get actual user ID from authentication
    revoked_by = uuid.uuid4()  # Mock user ID

    success = await service.revoke_api_key(key_id, revoked_by)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
