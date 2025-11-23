"""Session management service with Redis backend."""

from datetime import datetime, timedelta
import json
import logging
from typing import Any
import uuid

from redis.asyncio import Redis

from sark.models.session import Session

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing authentication sessions with Redis backend.

    Sessions are stored in Redis with automatic expiration (TTL).
    Each user can have multiple concurrent sessions up to a configurable limit.

    Redis Keys:
        - session:{session_id} -> Session data (TTL = timeout)
        - user_sessions:{user_id} -> Set of session IDs
    """

    def __init__(
        self,
        redis_client: Redis,
        default_timeout_seconds: int = 86400,  # 24 hours
        max_concurrent_sessions: int = 5,
    ):
        """Initialize session service.

        Args:
            redis_client: Redis client instance
            default_timeout_seconds: Default session timeout in seconds (default: 24h)
            max_concurrent_sessions: Maximum concurrent sessions per user (default: 5)
        """
        self.redis = redis_client
        self.default_timeout = default_timeout_seconds
        self.max_concurrent = max_concurrent_sessions

    async def create_session(
        self,
        user_id: uuid.UUID,
        ip_address: str,
        user_agent: str | None = None,
        timeout_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[Session, str]:
        """Create a new session for a user.

        Enforces concurrent session limits by removing oldest sessions if needed.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent string
            timeout_seconds: Custom timeout (uses default if None)
            metadata: Additional session metadata

        Returns:
            Tuple of (Session object, session_id)
        """
        timeout = timeout_seconds or self.default_timeout
        now = datetime.utcnow()
        session_id = str(uuid.uuid4())

        # Create session object
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(seconds=timeout),
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )

        # Check concurrent session limit
        await self._enforce_session_limit(user_id)

        # Store session in Redis
        session_key = f"session:{session_id}"
        user_sessions_key = f"user_sessions:{user_id}"

        # Store session data with TTL
        await self.redis.setex(
            session_key,
            timeout,
            json.dumps(session.to_dict()),
        )

        # Add to user's session set
        await self.redis.sadd(user_sessions_key, session_id)
        await self.redis.expire(user_sessions_key, timeout + 3600)  # Extra hour buffer

        logger.info(f"Created session {session_id} for user {user_id}")
        return session, session_id

    async def get_session(self, session_id: str) -> Session | None:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session object if found and valid, None otherwise
        """
        session_key = f"session:{session_id}"
        data = await self.redis.get(session_key)

        if not data:
            return None

        try:
            session_dict = json.loads(data)
            session = Session.from_dict(session_dict)

            # Check if expired
            if session.is_expired():
                await self.invalidate_session(session_id)
                return None

            return session
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing session {session_id}: {e}")
            return None

    async def update_activity(
        self, session_id: str, ip_address: str | None = None
    ) -> bool:
        """Update session's last activity timestamp.

        Also extends the session TTL.

        Args:
            session_id: Session ID
            ip_address: Optional IP address update

        Returns:
            True if updated successfully, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        # Update last activity
        session.last_activity = datetime.utcnow()
        if ip_address:
            session.ip_address = ip_address

        # Update in Redis with refreshed TTL
        session_key = f"session:{session_id}"
        ttl = int((session.expires_at - datetime.utcnow()).total_seconds())

        if ttl > 0:
            await self.redis.setex(
                session_key,
                ttl,
                json.dumps(session.to_dict()),
            )
            return True

        return False

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a specific session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if invalidated successfully, False if session not found
        """
        # Get session data directly from Redis to avoid recursion
        session_key = f"session:{session_id}"
        data = await self.redis.get(session_key)

        user_id = None
        if data:
            try:
                session_dict = json.loads(data)
                user_id = uuid.UUID(session_dict["user_id"])
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        # Remove from Redis
        await self.redis.delete(session_key)

        # Remove from user sessions set if we have user_id
        if user_id:
            user_sessions_key = f"user_sessions:{user_id}"
            await self.redis.srem(user_sessions_key, session_id)
            logger.info(f"Invalidated session {session_id} for user {user_id}")
        else:
            logger.info(f"Invalidated session {session_id}")

        return True

    async def invalidate_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """Invalidate all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Number of sessions invalidated
        """
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self.redis.smembers(user_sessions_key)

        count = 0
        # Convert to list to avoid "RuntimeError: Set changed size during iteration"
        # since invalidate_session() modifies the same set via srem()
        for session_id_bytes in list(session_ids):
            session_id = session_id_bytes.decode("utf-8")
            if await self.invalidate_session(session_id):
                count += 1

        # Clean up user sessions set
        await self.redis.delete(user_sessions_key)

        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count

    async def list_user_sessions(
        self, user_id: uuid.UUID, include_expired: bool = False
    ) -> list[Session]:
        """List all sessions for a user.

        Args:
            user_id: User ID
            include_expired: Include expired sessions (default: False)

        Returns:
            List of Session objects
        """
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self.redis.smembers(user_sessions_key)

        sessions = []
        for session_id_bytes in session_ids:
            session_id = session_id_bytes.decode("utf-8")
            session = await self.get_session(session_id)

            if session:
                if include_expired or not session.is_expired():
                    sessions.append(session)
            else:
                # Clean up stale session ID from set
                await self.redis.srem(user_sessions_key, session_id)

        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.last_activity, reverse=True)
        return sessions

    async def get_session_count(self, user_id: uuid.UUID) -> dict[str, int]:
        """Get session count statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with total, active, and expired counts
        """
        sessions = await self.list_user_sessions(user_id, include_expired=True)

        total = len(sessions)
        active = sum(1 for s in sessions if not s.is_expired())
        expired = total - active

        return {
            "total": total,
            "active": active,
            "expired": expired,
        }

    async def _enforce_session_limit(self, user_id: uuid.UUID) -> None:
        """Enforce concurrent session limit for a user.

        Removes oldest sessions if limit is exceeded.

        Args:
            user_id: User ID
        """
        sessions = await self.list_user_sessions(user_id)

        # Only count active sessions
        active_sessions = [s for s in sessions if not s.is_expired()]

        if len(active_sessions) >= self.max_concurrent:
            # Sort by last activity (oldest first)
            active_sessions.sort(key=lambda s: s.last_activity)

            # Remove oldest sessions to make room
            to_remove = len(active_sessions) - self.max_concurrent + 1
            for session in active_sessions[:to_remove]:
                await self.invalidate_session(session.session_id)
                logger.info(
                    f"Removed old session {session.session_id} for user {user_id} "
                    f"(concurrent limit: {self.max_concurrent})"
                )

    async def cleanup_expired_sessions(self, user_id: uuid.UUID) -> int:
        """Clean up expired sessions for a user.

        Redis TTL handles automatic deletion, but this helps clean up
        the user_sessions set for better accuracy.

        Args:
            user_id: User ID

        Returns:
            Number of expired sessions removed
        """
        sessions = await self.list_user_sessions(user_id, include_expired=True)
        count = 0

        for session in sessions:
            if session.is_expired():
                await self.invalidate_session(session.session_id)
                count += 1

        return count

    async def validate_session(self, session_id: str) -> Session | None:
        """Validate a session and update its activity.

        This is a convenience method for authentication middleware.

        Args:
            session_id: Session ID

        Returns:
            Session object if valid, None if invalid/expired
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        if session.is_expired():
            await self.invalidate_session(session_id)
            return None

        # Update activity timestamp
        await self.update_activity(session_id)
        return session

    async def extend_session(
        self, session_id: str, additional_seconds: int
    ) -> Session | None:
        """Extend a session's expiration time.

        Args:
            session_id: Session ID
            additional_seconds: Seconds to add to expiration

        Returns:
            Updated Session object if successful, None otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Extend expiration
        session.expires_at = session.expires_at + timedelta(seconds=additional_seconds)

        # Update in Redis
        session_key = f"session:{session_id}"
        ttl = int((session.expires_at - datetime.utcnow()).total_seconds())

        if ttl > 0:
            await self.redis.setex(
                session_key,
                ttl,
                json.dumps(session.to_dict()),
            )
            logger.info(f"Extended session {session_id} by {additional_seconds}s")
            return session

        return None

    async def get_active_session_count(self) -> int:
        """Get total count of active sessions across all users.

        Returns:
            Total number of active sessions
        """
        # This is an approximation using Redis key pattern
        # In production, consider maintaining a global counter
        session_keys = []
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor, match="session:*", count=100
            )
            session_keys.extend(keys)
            if cursor == 0:
                break

        return len(session_keys)
