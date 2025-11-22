"""Session management API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sark.models.session import SessionListResponse, SessionResponse
from sark.services.auth.sessions import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/sessions", tags=["sessions"])


# Dependency to get session service
# In production, this would be injected from application state
async def get_session_service() -> SessionService:
    """Get session service instance.

    This is a placeholder for dependency injection.
    In production, retrieve from app state or dependency injection container.
    """
    # TODO: Get from app state
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Session service dependency not configured",
    )


# Dependency to get current user
# In production, this would extract user from JWT/session
async def get_current_user() -> UUID:
    """Get current user ID from authentication context.

    This is a placeholder for authentication middleware.
    In production, extract from JWT token or session.
    """
    # TODO: Get from authentication context
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


class SessionDeleteResponse(BaseModel):
    """Response for session deletion."""

    success: bool
    message: str
    sessions_deleted: int = 0


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    include_expired: bool = False,
    current_user: UUID = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """List all sessions for the current user.

    Args:
        include_expired: Include expired sessions in the list
        current_user: Current user ID (from auth dependency)
        session_service: Session service instance

    Returns:
        List of user sessions with statistics
    """
    try:
        sessions = await session_service.list_user_sessions(
            current_user, include_expired=include_expired
        )

        # Convert to response models
        session_responses = []
        for session in sessions:
            session_responses.append(
                SessionResponse(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    created_at=session.created_at,
                    expires_at=session.expires_at,
                    last_activity=session.last_activity,
                    ip_address=session.ip_address,
                    user_agent=session.user_agent,
                    is_expired=session.is_expired(),
                )
            )

        # Get statistics
        stats = await session_service.get_session_count(current_user)

        return SessionListResponse(
            sessions=session_responses,
            total=stats["total"],
            active=stats["active"],
            expired=stats["expired"],
        )

    except Exception as e:
        logger.error(f"Error listing sessions for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions",
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: UUID = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """Get details of a specific session.

    Args:
        session_id: Session ID to retrieve
        current_user: Current user ID (from auth dependency)
        session_service: Session service instance

    Returns:
        Session details

    Raises:
        404: Session not found
        403: Session belongs to different user
    """
    try:
        session = await session_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify session belongs to current user
        if session.user_id != current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session",
            )

        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_activity=session.last_activity,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_expired=session.is_expired(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session",
        )


@router.delete("/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(
    session_id: str,
    current_user: UUID = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """Invalidate a specific session.

    Args:
        session_id: Session ID to invalidate
        current_user: Current user ID (from auth dependency)
        session_service: Session service instance

    Returns:
        Deletion confirmation

    Raises:
        404: Session not found
        403: Session belongs to different user
    """
    try:
        # Verify session exists and belongs to user
        session = await session_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        if session.user_id != current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session",
            )

        # Invalidate session
        success = await session_service.invalidate_session(session_id)

        if success:
            return SessionDeleteResponse(
                success=True,
                message=f"Session {session_id} invalidated successfully",
                sessions_deleted=1,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to invalidate session",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate session",
        )


@router.delete("/all", response_model=SessionDeleteResponse)
async def delete_all_sessions(
    current_user: UUID = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """Invalidate all sessions for the current user.

    This will log the user out from all devices.

    Args:
        current_user: Current user ID (from auth dependency)
        session_service: Session service instance

    Returns:
        Deletion confirmation with count
    """
    try:
        count = await session_service.invalidate_all_user_sessions(current_user)

        return SessionDeleteResponse(
            success=True,
            message=f"All sessions invalidated successfully",
            sessions_deleted=count,
        )

    except Exception as e:
        logger.error(f"Error invalidating all sessions for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate sessions",
        )


@router.post("/{session_id}/extend", response_model=SessionResponse)
async def extend_session(
    session_id: str,
    additional_seconds: int,
    current_user: UUID = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """Extend a session's expiration time.

    Args:
        session_id: Session ID to extend
        additional_seconds: Seconds to add to expiration
        current_user: Current user ID (from auth dependency)
        session_service: Session service instance

    Returns:
        Updated session details

    Raises:
        404: Session not found
        403: Session belongs to different user
        400: Invalid extension time
    """
    if additional_seconds <= 0 or additional_seconds > 86400:  # Max 24 hours
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extension must be between 1 and 86400 seconds",
        )

    try:
        # Verify session exists and belongs to user
        session = await session_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        if session.user_id != current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session",
            )

        # Extend session
        extended_session = await session_service.extend_session(
            session_id, additional_seconds
        )

        if not extended_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to extend session",
            )

        return SessionResponse(
            session_id=extended_session.session_id,
            user_id=extended_session.user_id,
            created_at=extended_session.created_at,
            expires_at=extended_session.expires_at,
            last_activity=extended_session.last_activity,
            ip_address=extended_session.ip_address,
            user_agent=extended_session.user_agent,
            is_expired=extended_session.is_expired(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extending session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend session",
        )
