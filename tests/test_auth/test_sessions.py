"""Tests for session management service."""

from datetime import UTC, datetime, timedelta
import json
from unittest.mock import AsyncMock, patch
import uuid

import pytest

from sark.models.session import Session
from sark.services.auth.sessions import SessionService


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    redis.sadd = AsyncMock()
    redis.srem = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    redis.expire = AsyncMock()
    redis.scan = AsyncMock(return_value=(0, []))
    return redis


@pytest.fixture
def session_service(mock_redis):
    """Create session service with mock Redis."""
    return SessionService(
        redis_client=mock_redis,
        default_timeout_seconds=3600,  # 1 hour for testing
        max_concurrent_sessions=3,  # Lower limit for testing
    )


# Test Session Creation


class TestSessionCreation:
    """Test session creation functionality."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service, mock_redis):
        """Test successful session creation."""
        user_id = uuid.uuid4()
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0"

        session, session_id = await session_service.create_session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        assert session is not None
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        assert session.user_agent == user_agent
        assert session.session_id == session_id

        # Verify Redis calls
        mock_redis.setex.assert_called_once()
        mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_custom_timeout(self, session_service, mock_redis):
        """Test session creation with custom timeout."""
        user_id = uuid.uuid4()
        custom_timeout = 7200  # 2 hours

        session, _ = await session_service.create_session(
            user_id=user_id,
            ip_address="10.0.0.1",
            timeout_seconds=custom_timeout,
        )

        # Check timeout is set correctly
        duration = (session.expires_at - session.created_at).total_seconds()
        assert abs(duration - custom_timeout) < 1  # Within 1 second

    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self, session_service, mock_redis):
        """Test session creation with additional metadata."""
        user_id = uuid.uuid4()
        metadata = {"device": "mobile", "app_version": "1.0.0"}

        session, _ = await session_service.create_session(
            user_id=user_id,
            ip_address="192.168.1.100",
            metadata=metadata,
        )

        assert session.metadata == metadata


# Test Session Retrieval


class TestSessionRetrieval:
    """Test session retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_session_success(self, session_service, mock_redis):
        """Test successful session retrieval."""
        session_id = str(uuid.uuid4())
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        session_data = {
            "session_id": session_id,
            "user_id": str(user_id),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        session = await session_service.get_session(session_id)

        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == user_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_service, mock_redis):
        """Test retrieving non-existent session."""
        mock_redis.get.return_value = None

        session = await session_service.get_session("nonexistent")

        assert session is None

    @pytest.mark.asyncio
    async def test_get_session_expired(self, session_service, mock_redis):
        """Test retrieving expired session."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Session expired 1 hour ago
        session_data = {
            "session_id": session_id,
            "user_id": str(uuid.uuid4()),
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),
            "last_activity": (now - timedelta(hours=1)).isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        session = await session_service.get_session(session_id)

        # Should return None and invalidate expired session
        assert session is None
        mock_redis.delete.assert_called()


# Test Session Update


class TestSessionUpdate:
    """Test session update functionality."""

    @pytest.mark.asyncio
    async def test_update_activity_success(self, session_service, mock_redis):
        """Test successful activity update."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        session_data = {
            "session_id": session_id,
            "user_id": str(uuid.uuid4()),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        success = await session_service.update_activity(session_id)

        assert success is True
        mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_update_activity_with_ip_change(self, session_service, mock_redis):
        """Test activity update with IP address change."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        new_ip = "10.0.0.1"

        session_data = {
            "session_id": session_id,
            "user_id": str(uuid.uuid4()),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        success = await session_service.update_activity(session_id, ip_address=new_ip)

        assert success is True

    @pytest.mark.asyncio
    async def test_update_activity_nonexistent(self, session_service, mock_redis):
        """Test updating non-existent session."""
        mock_redis.get.return_value = None

        success = await session_service.update_activity("nonexistent")

        assert success is False


# Test Session Invalidation


class TestSessionInvalidation:
    """Test session invalidation functionality."""

    @pytest.mark.asyncio
    async def test_invalidate_session_success(self, session_service, mock_redis):
        """Test successful session invalidation."""
        session_id = str(uuid.uuid4())
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        session_data = {
            "session_id": session_id,
            "user_id": str(user_id),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        success = await session_service.invalidate_session(session_id)

        assert success is True
        mock_redis.delete.assert_called()
        mock_redis.srem.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_all_user_sessions(self, session_service, mock_redis):
        """Test invalidating all sessions for a user."""
        user_id = uuid.uuid4()
        session_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]

        mock_redis.smembers.return_value = {sid.encode() for sid in session_ids}

        # Mock session retrieval for each session
        now = datetime.now(UTC)
        session_data = {
            "session_id": "temp",
            "user_id": str(user_id),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        count = await session_service.invalidate_all_user_sessions(user_id)

        assert count == 3
        assert mock_redis.delete.call_count >= 3


# Test Session Listing


class TestSessionListing:
    """Test session listing functionality."""

    @pytest.mark.asyncio
    async def test_list_user_sessions(self, session_service, mock_redis):
        """Test listing user sessions."""
        user_id = uuid.uuid4()
        session_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        mock_redis.smembers.return_value = {sid.encode() for sid in session_ids}

        # Mock session data for each session
        now = datetime.now(UTC)

        async def mock_get_session_side_effect(session_id):
            return Session(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                expires_at=now + timedelta(hours=1),
                last_activity=now,
                ip_address="192.168.1.100",
                user_agent="Test Agent",
            )

        with patch.object(session_service, "get_session", side_effect=mock_get_session_side_effect):
            sessions = await session_service.list_user_sessions(user_id)

            assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_list_user_sessions_include_expired(self, session_service, mock_redis):
        """Test listing sessions including expired ones."""
        user_id = uuid.uuid4()
        mock_redis.smembers.return_value = set()

        sessions = await session_service.list_user_sessions(user_id, include_expired=True)

        assert isinstance(sessions, list)

    @pytest.mark.asyncio
    async def test_get_session_count(self, session_service, mock_redis):
        """Test getting session count statistics."""
        user_id = uuid.uuid4()
        mock_redis.smembers.return_value = set()

        with patch.object(session_service, "list_user_sessions", return_value=[]):
            stats = await session_service.get_session_count(user_id)

            assert stats["total"] == 0
            assert stats["active"] == 0
            assert stats["expired"] == 0


# Test Concurrent Session Limits


class TestConcurrentSessionLimits:
    """Test concurrent session limit enforcement."""

    @pytest.mark.asyncio
    async def test_enforce_session_limit(self, session_service, mock_redis):
        """Test that old sessions are removed when limit is reached."""
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        # Create 3 existing sessions (at the limit)
        existing_sessions = [
            Session(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=now - timedelta(hours=i),
                expires_at=now + timedelta(hours=1),
                last_activity=now - timedelta(hours=i),
                ip_address="192.168.1.100",
                user_agent="Test Agent",
            )
            for i in range(3, 0, -1)  # 3, 2, 1 hours ago
        ]

        with (
            patch.object(session_service, "list_user_sessions", return_value=existing_sessions),
            patch.object(session_service, "invalidate_session", new=AsyncMock()) as mock_invalidate,
        ):
            await session_service._enforce_session_limit(user_id)

            # Should invalidate oldest session
            assert mock_invalidate.call_count == 1

    @pytest.mark.asyncio
    async def test_no_enforcement_under_limit(self, session_service, mock_redis):
        """Test that sessions are not removed when under limit."""
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        # Only 2 sessions (under limit of 3)
        existing_sessions = [
            Session(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=now,
                expires_at=now + timedelta(hours=1),
                last_activity=now,
                ip_address="192.168.1.100",
                user_agent="Test Agent",
            )
            for _ in range(2)
        ]

        with (
            patch.object(session_service, "list_user_sessions", return_value=existing_sessions),
            patch.object(session_service, "invalidate_session", new=AsyncMock()) as mock_invalidate,
        ):
            await session_service._enforce_session_limit(user_id)

            # Should not invalidate any sessions
            assert mock_invalidate.call_count == 0


# Test Session Validation


class TestSessionValidation:
    """Test session validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_session_success(self, session_service, mock_redis):
        """Test successful session validation."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        session_data = {
            "session_id": session_id,
            "user_id": str(uuid.uuid4()),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        session = await session_service.validate_session(session_id)

        assert session is not None
        # Should also update activity
        assert mock_redis.setex.call_count >= 1

    @pytest.mark.asyncio
    async def test_validate_expired_session(self, session_service, mock_redis):
        """Test validating an expired session."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Expired session
        session_data = {
            "session_id": session_id,
            "user_id": str(uuid.uuid4()),
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),
            "last_activity": (now - timedelta(hours=1)).isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        session = await session_service.validate_session(session_id)

        assert session is None
        # Should invalidate expired session
        mock_redis.delete.assert_called()


# Test Session Extension


class TestSessionExtension:
    """Test session extension functionality."""

    @pytest.mark.asyncio
    async def test_extend_session_success(self, session_service, mock_redis):
        """Test successful session extension."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        session_data = {
            "session_id": session_id,
            "user_id": str(uuid.uuid4()),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent",
            "metadata": {},
        }

        mock_redis.get.return_value = json.dumps(session_data).encode()

        extended_session = await session_service.extend_session(session_id, 3600)

        assert extended_session is not None
        # Should update expiration in Redis
        mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_extend_nonexistent_session(self, session_service, mock_redis):
        """Test extending non-existent session."""
        mock_redis.get.return_value = None

        extended_session = await session_service.extend_session("nonexistent", 3600)

        assert extended_session is None


# Test Cleanup


class TestSessionCleanup:
    """Test session cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_service, mock_redis):
        """Test cleaning up expired sessions."""
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        # Mix of active and expired sessions
        sessions = [
            Session(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=now - timedelta(hours=2),
                expires_at=now - timedelta(hours=1),  # Expired
                last_activity=now - timedelta(hours=1),
                ip_address="192.168.1.100",
                user_agent="Test Agent",
            ),
            Session(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=now,
                expires_at=now + timedelta(hours=1),  # Active
                last_activity=now,
                ip_address="192.168.1.100",
                user_agent="Test Agent",
            ),
        ]

        with (
            patch.object(session_service, "list_user_sessions", return_value=sessions),
            patch.object(session_service, "invalidate_session", new=AsyncMock()) as mock_invalidate,
        ):
            count = await session_service.cleanup_expired_sessions(user_id)

            assert count == 1
            assert mock_invalidate.call_count == 1

    @pytest.mark.asyncio
    async def test_get_active_session_count(self, session_service, mock_redis):
        """Test getting total active session count."""
        mock_redis.scan.return_value = (0, [b"session:1", b"session:2"])

        count = await session_service.get_active_session_count()

        assert count >= 0
