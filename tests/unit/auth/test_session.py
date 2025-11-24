"""Comprehensive tests for session management."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from sark.services.auth.session import (
    Session,
    SessionService,
    SessionStore,
    get_session_store,
)


class TestSessionService:
    """Test suite for SessionService class."""

    @pytest.fixture
    def service(self):
        """Create a SessionService instance."""
        return SessionService()

    @pytest.fixture
    def sample_user_id(self):
        """Sample user UUID."""
        return uuid4()

    # ===== Session ID Generation Tests =====

    def test_generate_session_id_returns_string(self, service):
        """Test generate_session_id returns a string."""
        session_id = service.generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_generate_session_id_is_unique(self, service):
        """Test generate_session_id produces unique IDs."""
        ids = {service.generate_session_id() for _ in range(100)}
        assert len(ids) == 100  # All unique

    def test_generate_session_id_is_url_safe(self, service):
        """Test generated session IDs are URL-safe."""
        session_id = service.generate_session_id()
        import string

        allowed = set(string.ascii_letters + string.digits + "-_")
        assert all(c in allowed for c in session_id)

    # ===== Session Creation Tests =====

    def test_create_session_basic(self, service, sample_user_id):
        """Test creating a basic session."""
        session = service.create_session(user_id=sample_user_id)

        assert isinstance(session, Session)
        assert session.user_id == sample_user_id
        assert session.is_active is True
        assert session.metadata == {}
        assert session.user_agent is None
        assert session.ip_address is None

    def test_create_session_with_user_agent(self, service, sample_user_id):
        """Test creating session with user agent."""
        user_agent = "Mozilla/5.0 (Test)"
        session = service.create_session(
            user_id=sample_user_id,
            user_agent=user_agent,
        )

        assert session.user_agent == user_agent

    def test_create_session_with_ip_address(self, service, sample_user_id):
        """Test creating session with IP address."""
        ip_address = "192.168.1.1"
        session = service.create_session(
            user_id=sample_user_id,
            ip_address=ip_address,
        )

        assert session.ip_address == ip_address

    def test_create_session_with_metadata(self, service, sample_user_id):
        """Test creating session with metadata."""
        metadata = {"login_method": "password", "mfa_enabled": True}
        session = service.create_session(
            user_id=sample_user_id,
            metadata=metadata,
        )

        assert session.metadata == metadata

    def test_create_session_timestamps(self, service, sample_user_id):
        """Test created session has correct timestamps."""
        before_create = datetime.now(UTC)
        session = service.create_session(user_id=sample_user_id)
        after_create = datetime.now(UTC)

        assert before_create <= session.created_at <= after_create
        assert session.created_at == session.last_accessed_at
        assert session.expires_at > session.created_at

    def test_create_session_expiration(self, service, sample_user_id):
        """Test session expires at correct time."""
        session = service.create_session(user_id=sample_user_id)

        expected_expiry = session.created_at + timedelta(hours=service.session_lifetime_hours)
        assert abs((session.expires_at - expected_expiry).total_seconds()) < 1

    def test_create_session_custom_lifetime(self, sample_user_id):
        """Test creating session with custom lifetime."""
        service = SessionService(session_lifetime_hours=48)
        session = service.create_session(user_id=sample_user_id)

        expected_expiry = session.created_at + timedelta(hours=48)
        assert abs((session.expires_at - expected_expiry).total_seconds()) < 1

    def test_create_session_unique_ids(self, service, sample_user_id):
        """Test created sessions have unique IDs."""
        session1 = service.create_session(user_id=sample_user_id)
        session2 = service.create_session(user_id=sample_user_id)

        assert session1.session_id != session2.session_id

    # ===== Session Validation Tests =====

    def test_validate_session_active(self, service, sample_user_id):
        """Test validate_session passes for active session."""
        session = service.create_session(user_id=sample_user_id)
        assert service.validate_session(session) is True

    def test_validate_session_inactive(self, service, sample_user_id):
        """Test validate_session raises for inactive session."""
        session = service.create_session(user_id=sample_user_id)
        session.is_active = False

        with pytest.raises(ValueError) as exc_info:
            service.validate_session(session)

        assert "inactive" in str(exc_info.value).lower()

    def test_validate_session_expired(self, service, sample_user_id):
        """Test validate_session raises for expired session."""
        session = service.create_session(user_id=sample_user_id)
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)

        with pytest.raises(ValueError) as exc_info:
            service.validate_session(session)

        assert "expired" in str(exc_info.value).lower()

    def test_validate_session_not_expired(self, service, sample_user_id):
        """Test validate_session passes for session not yet expired."""
        session = service.create_session(user_id=sample_user_id)
        session.expires_at = datetime.now(UTC) + timedelta(hours=1)

        assert service.validate_session(session) is True

    # ===== Session Refresh Tests =====

    def test_refresh_session_updates_timestamps(self, service, sample_user_id):
        """Test refresh_session updates last accessed and expiration."""
        session = service.create_session(user_id=sample_user_id)
        original_last_accessed = session.last_accessed_at
        original_expires = session.expires_at

        # Wait a small amount
        import time

        time.sleep(0.01)

        refreshed = service.refresh_session(session)

        assert refreshed.last_accessed_at > original_last_accessed
        assert refreshed.expires_at > original_expires

    def test_refresh_session_extends_lifetime(self, service, sample_user_id):
        """Test refresh_session extends session lifetime."""
        session = service.create_session(user_id=sample_user_id)

        import time

        time.sleep(0.01)

        refreshed = service.refresh_session(session)

        expected_expiry = refreshed.last_accessed_at + timedelta(
            hours=service.session_lifetime_hours
        )
        assert abs((refreshed.expires_at - expected_expiry).total_seconds()) < 1

    def test_refresh_session_inactive_fails(self, service, sample_user_id):
        """Test refreshing inactive session raises error."""
        session = service.create_session(user_id=sample_user_id)
        session.is_active = False

        with pytest.raises(ValueError):
            service.refresh_session(session)

    def test_refresh_session_expired_fails(self, service, sample_user_id):
        """Test refreshing expired session raises error."""
        session = service.create_session(user_id=sample_user_id)
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)

        with pytest.raises(ValueError):
            service.refresh_session(session)

    # ===== Session Invalidation Tests =====

    def test_invalidate_session(self, service, sample_user_id):
        """Test invalidate_session marks session as inactive."""
        session = service.create_session(user_id=sample_user_id)
        assert session.is_active is True

        invalidated = service.invalidate_session(session)

        assert invalidated.is_active is False

    def test_invalidate_session_returns_same_session(self, service, sample_user_id):
        """Test invalidate_session returns the same session object."""
        session = service.create_session(user_id=sample_user_id)
        invalidated = service.invalidate_session(session)

        assert invalidated.session_id == session.session_id

    # ===== Session Time Checks Tests =====

    def test_get_remaining_time(self, service, sample_user_id):
        """Test get_remaining_time returns correct duration."""
        session = service.create_session(user_id=sample_user_id)

        remaining = service.get_remaining_time(session)

        assert isinstance(remaining, timedelta)
        # Should be close to session_lifetime_hours
        expected_hours = service.session_lifetime_hours
        assert abs(remaining.total_seconds() - expected_hours * 3600) < 10

    def test_get_remaining_time_negative_when_expired(self, service, sample_user_id):
        """Test get_remaining_time returns negative for expired session."""
        session = service.create_session(user_id=sample_user_id)
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)

        remaining = service.get_remaining_time(session)

        assert remaining.total_seconds() < 0

    def test_is_expired_false_for_active(self, service, sample_user_id):
        """Test is_expired returns False for active session."""
        session = service.create_session(user_id=sample_user_id)

        assert service.is_expired(session) is False

    def test_is_expired_true_for_expired(self, service, sample_user_id):
        """Test is_expired returns True for expired session."""
        session = service.create_session(user_id=sample_user_id)
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)

        assert service.is_expired(session) is True

    # ===== Metadata Update Tests =====

    def test_update_metadata_merge(self, service, sample_user_id):
        """Test update_metadata merges with existing metadata."""
        session = service.create_session(
            user_id=sample_user_id,
            metadata={"key1": "value1"},
        )

        updated = service.update_metadata(
            session,
            {"key2": "value2"},
            merge=True,
        )

        assert updated.metadata == {"key1": "value1", "key2": "value2"}

    def test_update_metadata_replace(self, service, sample_user_id):
        """Test update_metadata replaces existing metadata."""
        session = service.create_session(
            user_id=sample_user_id,
            metadata={"key1": "value1"},
        )

        updated = service.update_metadata(
            session,
            {"key2": "value2"},
            merge=False,
        )

        assert updated.metadata == {"key2": "value2"}

    def test_update_metadata_overwrite_key(self, service, sample_user_id):
        """Test update_metadata overwrites existing keys."""
        session = service.create_session(
            user_id=sample_user_id,
            metadata={"key1": "value1"},
        )

        updated = service.update_metadata(
            session,
            {"key1": "new_value"},
            merge=True,
        )

        assert updated.metadata == {"key1": "new_value"}


class TestSessionStore:
    """Test suite for SessionStore class."""

    @pytest.fixture
    def store(self):
        """Create a fresh SessionStore instance."""
        return SessionStore()

    @pytest.fixture
    def service(self):
        """Create a SessionService instance."""
        return SessionService()

    @pytest.fixture
    def sample_user_id(self):
        """Sample user UUID."""
        return uuid4()

    # ===== Save and Get Tests =====

    def test_save_and_get_session(self, store, service, sample_user_id):
        """Test saving and retrieving a session."""
        session = service.create_session(user_id=sample_user_id)
        store.save(session)

        retrieved = store.get(session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.user_id == sample_user_id

    def test_get_nonexistent_session(self, store):
        """Test getting nonexistent session returns None."""
        result = store.get("nonexistent_session_id")
        assert result is None

    def test_save_overwrites_existing(self, store, service, sample_user_id):
        """Test saving session with same ID overwrites existing."""
        session = service.create_session(user_id=sample_user_id)
        store.save(session)

        # Modify and save again
        session.metadata = {"updated": True}
        store.save(session)

        retrieved = store.get(session.session_id)
        assert retrieved.metadata == {"updated": True}

    # ===== Delete Tests =====

    def test_delete_existing_session(self, store, service, sample_user_id):
        """Test deleting an existing session."""
        session = service.create_session(user_id=sample_user_id)
        store.save(session)

        result = store.delete(session.session_id)

        assert result is True
        assert store.get(session.session_id) is None

    def test_delete_nonexistent_session(self, store):
        """Test deleting nonexistent session returns False."""
        result = store.delete("nonexistent_session_id")
        assert result is False

    # ===== User Sessions Tests =====

    def test_get_user_sessions(self, store, service, sample_user_id):
        """Test getting all sessions for a user."""
        session1 = service.create_session(user_id=sample_user_id)
        session2 = service.create_session(user_id=sample_user_id)
        session3 = service.create_session(user_id=sample_user_id)

        store.save(session1)
        store.save(session2)
        store.save(session3)

        user_sessions = store.get_user_sessions(sample_user_id)

        assert len(user_sessions) == 3
        session_ids = {s.session_id for s in user_sessions}
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id in session_ids

    def test_get_user_sessions_empty(self, store):
        """Test getting sessions for user with no sessions."""
        user_sessions = store.get_user_sessions(uuid4())
        assert user_sessions == []

    def test_get_user_sessions_different_users(self, store, service):
        """Test sessions are tracked per user."""
        user1_id = uuid4()
        user2_id = uuid4()

        session1 = service.create_session(user_id=user1_id)
        session2 = service.create_session(user_id=user2_id)

        store.save(session1)
        store.save(session2)

        user1_sessions = store.get_user_sessions(user1_id)
        user2_sessions = store.get_user_sessions(user2_id)

        assert len(user1_sessions) == 1
        assert len(user2_sessions) == 1
        assert user1_sessions[0].session_id == session1.session_id
        assert user2_sessions[0].session_id == session2.session_id

    # ===== Delete User Sessions Tests =====

    def test_delete_user_sessions(self, store, service, sample_user_id):
        """Test deleting all sessions for a user."""
        session1 = service.create_session(user_id=sample_user_id)
        session2 = service.create_session(user_id=sample_user_id)

        store.save(session1)
        store.save(session2)

        count = store.delete_user_sessions(sample_user_id)

        assert count == 2
        assert store.get_user_sessions(sample_user_id) == []
        assert store.get(session1.session_id) is None
        assert store.get(session2.session_id) is None

    def test_delete_user_sessions_preserves_other_users(self, store, service):
        """Test deleting user sessions doesn't affect other users."""
        user1_id = uuid4()
        user2_id = uuid4()

        session1 = service.create_session(user_id=user1_id)
        session2 = service.create_session(user_id=user2_id)

        store.save(session1)
        store.save(session2)

        store.delete_user_sessions(user1_id)

        assert store.get_user_sessions(user1_id) == []
        assert len(store.get_user_sessions(user2_id)) == 1

    def test_delete_user_sessions_nonexistent_user(self, store):
        """Test deleting sessions for nonexistent user returns 0."""
        count = store.delete_user_sessions(uuid4())
        assert count == 0

    # ===== Cleanup Expired Sessions Tests =====

    def test_cleanup_expired_removes_expired(self, store, service, sample_user_id):
        """Test cleanup_expired removes expired sessions."""
        session = service.create_session(user_id=sample_user_id)
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        store.save(session)

        count = store.cleanup_expired()

        assert count == 1
        assert store.get(session.session_id) is None

    def test_cleanup_expired_preserves_active(self, store, service, sample_user_id):
        """Test cleanup_expired preserves non-expired sessions."""
        session = service.create_session(user_id=sample_user_id)
        store.save(session)

        count = store.cleanup_expired()

        assert count == 0
        assert store.get(session.session_id) is not None

    def test_cleanup_expired_mixed(self, store, service, sample_user_id):
        """Test cleanup_expired with mix of expired and active sessions."""
        active_session = service.create_session(user_id=sample_user_id)
        expired_session1 = service.create_session(user_id=sample_user_id)
        expired_session2 = service.create_session(user_id=sample_user_id)

        expired_session1.expires_at = datetime.now(UTC) - timedelta(hours=1)
        expired_session2.expires_at = datetime.now(UTC) - timedelta(hours=2)

        store.save(active_session)
        store.save(expired_session1)
        store.save(expired_session2)

        count = store.cleanup_expired()

        assert count == 2
        assert store.get(active_session.session_id) is not None
        assert store.get(expired_session1.session_id) is None
        assert store.get(expired_session2.session_id) is None

    def test_cleanup_expired_empty_store(self, store):
        """Test cleanup_expired on empty store returns 0."""
        count = store.cleanup_expired()
        assert count == 0


class TestGetSessionStore:
    """Test suite for get_session_store function."""

    def test_get_session_store_returns_instance(self):
        """Test get_session_store returns SessionStore instance."""
        store = get_session_store()
        assert isinstance(store, SessionStore)

    def test_get_session_store_returns_singleton(self):
        """Test get_session_store returns same instance."""
        store1 = get_session_store()
        store2 = get_session_store()
        assert store1 is store2
