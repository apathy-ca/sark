"""Session management for user authentication."""

from datetime import UTC, datetime, timedelta
import secrets
from typing import Any
from uuid import UUID

from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class Session(BaseModel):
    """User session model."""

    session_id: str
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    last_accessed_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None
    metadata: dict[str, Any] = {}
    is_active: bool = True


class SessionService:
    """Service for managing user sessions."""

    def __init__(
        self,
        session_lifetime_hours: int = 24,
        max_sessions_per_user: int = 5,
    ):
        """
        Initialize session service.

        Args:
            session_lifetime_hours: Session lifetime in hours
            max_sessions_per_user: Maximum concurrent sessions per user
        """
        self.session_lifetime_hours = session_lifetime_hours
        self.max_sessions_per_user = max_sessions_per_user

    def generate_session_id(self) -> str:
        """
        Generate a secure session ID.

        Returns:
            Secure random session ID
        """
        return secrets.token_urlsafe(32)

    def create_session(
        self,
        user_id: UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """
        Create a new user session.

        Args:
            user_id: User ID
            user_agent: User agent string from request
            ip_address: Client IP address
            metadata: Additional session metadata

        Returns:
            Created session
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=self.session_lifetime_hours)

        session = Session(
            session_id=self.generate_session_id(),
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
            last_accessed_at=now,
            user_agent=user_agent,
            ip_address=ip_address,
            metadata=metadata or {},
            is_active=True,
        )

        logger.info(
            "session_created",
            session_id=session.session_id,
            user_id=str(user_id),
            expires_at=expires_at.isoformat(),
        )

        return session

    def validate_session(self, session: Session) -> bool:
        """
        Validate a session's status and expiration.

        Args:
            session: Session to validate

        Returns:
            True if session is valid

        Raises:
            ValueError: If session is invalid or expired
        """
        if not session.is_active:
            logger.warning("session_inactive", session_id=session.session_id)
            raise ValueError("Session is inactive")

        if datetime.now(UTC) > session.expires_at:
            logger.warning("session_expired", session_id=session.session_id)
            raise ValueError("Session has expired")

        return True

    def refresh_session(self, session: Session) -> Session:
        """
        Refresh a session's expiration time and last accessed timestamp.

        Args:
            session: Session to refresh

        Returns:
            Updated session

        Raises:
            ValueError: If session cannot be refreshed
        """
        self.validate_session(session)

        now = datetime.now(UTC)
        session.last_accessed_at = now
        session.expires_at = now + timedelta(hours=self.session_lifetime_hours)

        logger.debug(
            "session_refreshed",
            session_id=session.session_id,
            new_expiry=session.expires_at.isoformat(),
        )

        return session

    def invalidate_session(self, session: Session) -> Session:
        """
        Invalidate a session.

        Args:
            session: Session to invalidate

        Returns:
            Invalidated session
        """
        session.is_active = False

        logger.info("session_invalidated", session_id=session.session_id)

        return session

    def get_remaining_time(self, session: Session) -> timedelta:
        """
        Get remaining time until session expires.

        Args:
            session: Session to check

        Returns:
            Time remaining until expiration
        """
        return session.expires_at - datetime.now(UTC)

    def is_expired(self, session: Session) -> bool:
        """
        Check if a session is expired.

        Args:
            session: Session to check

        Returns:
            True if session is expired
        """
        return datetime.now(UTC) > session.expires_at

    def update_metadata(
        self,
        session: Session,
        metadata: dict[str, Any],
        merge: bool = True,
    ) -> Session:
        """
        Update session metadata.

        Args:
            session: Session to update
            metadata: New metadata to add
            merge: If True, merge with existing metadata; if False, replace

        Returns:
            Updated session
        """
        if merge:
            session.metadata.update(metadata)
        else:
            session.metadata = metadata

        logger.debug(
            "session_metadata_updated",
            session_id=session.session_id,
            metadata_keys=list(metadata.keys()),
        )

        return session


class SessionStore:
    """In-memory session store (replace with Redis/database in production)."""

    def __init__(self):
        """Initialize session store."""
        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[UUID, set[str]] = {}

    def save(self, session: Session) -> None:
        """
        Save a session to the store.

        Args:
            session: Session to save
        """
        self._sessions[session.session_id] = session

        # Track user's sessions
        if session.user_id not in self._user_sessions:
            self._user_sessions[session.user_id] = set()
        self._user_sessions[session.user_id].add(session.session_id)

    def get(self, session_id: str) -> Session | None:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session if found, None otherwise
        """
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """
        Delete a session from the store.

        Args:
            session_id: Session ID

        Returns:
            True if session was deleted
        """
        session = self._sessions.pop(session_id, None)
        if session:
            # Remove from user sessions tracking
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id].discard(session_id)
            return True
        return False

    def get_user_sessions(self, user_id: UUID) -> list[Session]:
        """
        Get all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of user's sessions
        """
        session_ids = self._user_sessions.get(user_id, set())
        return [
            self._sessions[sid] for sid in session_ids if sid in self._sessions
        ]

    def delete_user_sessions(self, user_id: UUID) -> int:
        """
        Delete all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Number of sessions deleted
        """
        session_ids = self._user_sessions.get(user_id, set()).copy()
        count = 0
        for session_id in session_ids:
            if self.delete(session_id):
                count += 1

        self._user_sessions.pop(user_id, None)
        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired sessions from the store.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(UTC)
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now > session.expires_at
        ]

        for session_id in expired:
            self.delete(session_id)

        logger.info("expired_sessions_cleaned", count=len(expired))
        return len(expired)


# Global session store instance
_session_store = SessionStore()


def get_session_store() -> SessionStore:
    """
    Get the global session store instance.

    Returns:
        SessionStore instance
    """
    return _session_store
