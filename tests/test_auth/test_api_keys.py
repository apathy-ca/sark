"""Tests for API key management."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from sark.models.api_key import APIKey
from sark.services.auth.api_keys import APIKeyService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def api_key_service(mock_db_session):
    """Create an APIKeyService instance with mock DB."""
    return APIKeyService(mock_db_session)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_api_key(sample_user_id):
    """Create a sample API key for testing."""
    return APIKey(
        id=uuid.uuid4(),
        user_id=sample_user_id,
        name="Test API Key",
        description="Test description",
        key_prefix="abc12345",
        key_hash="$2b$12$hashed_key_here",
        scopes=["server:read", "server:write"],
        rate_limit=1000,
        is_active=True,
        usage_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestAPIKeyModel:
    """Test APIKey model."""

    def test_api_key_creation(self, sample_user_id):
        """Test creating an API key model."""
        api_key = APIKey(
            user_id=sample_user_id,
            name="Test Key",
            key_prefix="test1234",
            key_hash="hashed",
            scopes=["server:read"],
            rate_limit=500,
            is_active=True,
            usage_count=0,
        )

        assert api_key.user_id == sample_user_id
        assert api_key.name == "Test Key"
        assert api_key.key_prefix == "test1234"
        assert api_key.scopes == ["server:read"]
        assert api_key.rate_limit == 500
        assert api_key.is_active is True
        assert api_key.usage_count == 0

    def test_is_expired_no_expiration(self, sample_api_key):
        """Test is_expired when no expiration set."""
        sample_api_key.expires_at = None
        assert sample_api_key.is_expired is False

    def test_is_expired_future_date(self, sample_api_key):
        """Test is_expired with future expiration."""
        sample_api_key.expires_at = datetime.now(UTC) + timedelta(days=30)
        assert sample_api_key.is_expired is False

    def test_is_expired_past_date(self, sample_api_key):
        """Test is_expired with past expiration."""
        sample_api_key.expires_at = datetime.now(UTC) - timedelta(days=1)
        assert sample_api_key.is_expired is True

    def test_is_valid_active_key(self, sample_api_key):
        """Test is_valid for active, non-expired key."""
        sample_api_key.is_active = True
        sample_api_key.expires_at = None
        sample_api_key.revoked_at = None
        assert sample_api_key.is_valid is True

    def test_is_valid_inactive_key(self, sample_api_key):
        """Test is_valid for inactive key."""
        sample_api_key.is_active = False
        assert sample_api_key.is_valid is False

    def test_is_valid_revoked_key(self, sample_api_key):
        """Test is_valid for revoked key."""
        sample_api_key.revoked_at = datetime.now(UTC)
        assert sample_api_key.is_valid is False

    def test_revoke_key(self, sample_api_key, sample_user_id):
        """Test revoking an API key."""
        sample_api_key.revoke(sample_user_id)

        assert sample_api_key.is_active is False
        assert sample_api_key.revoked_at is not None
        assert sample_api_key.revoked_by == sample_user_id

    def test_record_usage(self, sample_api_key):
        """Test recording API key usage."""
        initial_count = sample_api_key.usage_count
        sample_api_key.record_usage("192.168.1.1")

        assert sample_api_key.usage_count == initial_count + 1
        assert sample_api_key.last_used_at is not None
        assert sample_api_key.last_used_ip == "192.168.1.1"


class TestKeyGeneration:
    """Test API key generation."""

    def test_generate_key_format(self):
        """Test generated key has correct format."""
        full_key, prefix, key_hash = APIKeyService.generate_key("live")

        assert full_key.startswith("sark_sk_live_")
        assert len(prefix) == 8
        assert key_hash.startswith("$2b$")  # bcrypt hash

    def test_generate_key_unique(self):
        """Test that generated keys are unique."""
        key1, prefix1, hash1 = APIKeyService.generate_key()
        key2, prefix2, hash2 = APIKeyService.generate_key()

        assert key1 != key2
        assert prefix1 != prefix2
        assert hash1 != hash2

    def test_generate_key_environments(self):
        """Test key generation for different environments."""
        live_key, _, _ = APIKeyService.generate_key("live")
        test_key, _, _ = APIKeyService.generate_key("test")
        dev_key, _, _ = APIKeyService.generate_key("dev")

        assert "_sk_live_" in live_key
        assert "_sk_test_" in test_key
        assert "_sk_dev_" in dev_key

    def test_hash_key(self):
        """Test key hashing."""
        key = "test_key_12345"
        key_hash = APIKeyService._hash_key(key)

        assert key_hash.startswith("$2b$")
        assert len(key_hash) > 50

    def test_verify_key_valid(self):
        """Test verifying a valid key."""
        key = "test_key_12345"
        key_hash = APIKeyService._hash_key(key)

        assert APIKeyService.verify_key(key, key_hash) is True

    def test_verify_key_invalid(self):
        """Test verifying an invalid key."""
        key = "test_key_12345"
        key_hash = APIKeyService._hash_key(key)

        assert APIKeyService.verify_key("wrong_key", key_hash) is False

    def test_extract_prefix_valid(self):
        """Test extracting prefix from valid key."""
        key = "sark_sk_live_abc12345_secret123456"
        prefix = APIKeyService.extract_prefix(key)

        assert prefix == "abc12345"

    def test_extract_prefix_invalid_format(self):
        """Test extracting prefix from invalid format."""
        assert APIKeyService.extract_prefix("invalid_key") is None
        assert APIKeyService.extract_prefix("sark_invalid") is None


class TestAPIKeyServiceCreate:
    """Test API key creation."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_key_service, sample_user_id):
        """Test successful API key creation."""
        api_key, full_key = await api_key_service.create_api_key(
            user_id=sample_user_id,
            name="Test Key",
            scopes=["server:read", "server:write"],
            rate_limit=500,
        )

        assert api_key.user_id == sample_user_id
        assert api_key.name == "Test Key"
        assert api_key.scopes == ["server:read", "server:write"]
        assert api_key.rate_limit == 500
        assert full_key.startswith("sark_sk_")
        assert api_key_service.db.add.called
        assert api_key_service.db.flush.called

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self, api_key_service, sample_user_id):
        """Test creating API key with expiration."""
        api_key, _ = await api_key_service.create_api_key(
            user_id=sample_user_id,
            name="Expiring Key",
            scopes=["server:read"],
            expires_in_days=30,
        )

        assert api_key.expires_at is not None
        assert api_key.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_create_api_key_invalid_scopes(self, api_key_service, sample_user_id):
        """Test creating API key with invalid scopes."""
        with pytest.raises(ValueError, match="Invalid scopes"):
            await api_key_service.create_api_key(
                user_id=sample_user_id,
                name="Bad Key",
                scopes=["invalid:scope", "another:bad"],
            )

    @pytest.mark.asyncio
    async def test_create_api_key_with_team(self, api_key_service, sample_user_id):
        """Test creating team-scoped API key."""
        team_id = uuid.uuid4()
        api_key, _ = await api_key_service.create_api_key(
            user_id=sample_user_id,
            name="Team Key",
            scopes=["server:read"],
            team_id=team_id,
        )

        assert api_key.team_id == team_id


class TestAPIKeyServiceValidation:
    """Test API key validation."""

    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, api_key_service, sample_api_key):
        """Test successful API key validation."""
        # Generate a real key and hash
        full_key = "sark_sk_live_abc12345_secret123456"
        key_hash = APIKeyService._hash_key(full_key)
        sample_api_key.key_prefix = "abc12345"
        sample_api_key.key_hash = key_hash
        sample_api_key.is_active = True
        sample_api_key.revoked_at = None
        sample_api_key.expires_at = None

        # Mock the database lookup
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key(full_key)

        assert validated_key is not None
        assert error is None
        assert validated_key.id == sample_api_key.id

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid_format(self, api_key_service):
        """Test validation with invalid key format."""
        validated_key, error = await api_key_service.validate_api_key("invalid_key")

        assert validated_key is None
        assert error == "Invalid API key format"

    @pytest.mark.asyncio
    async def test_validate_api_key_not_found(self, api_key_service):
        """Test validation when key not found."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key(
            "sark_sk_live_notfound_secret"
        )

        assert validated_key is None
        assert error == "API key not found"

    @pytest.mark.asyncio
    async def test_validate_api_key_wrong_hash(self, api_key_service, sample_api_key):
        """Test validation with wrong key hash."""
        sample_api_key.key_hash = APIKeyService._hash_key("different_key")

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key("sark_sk_live_abc12345_wrong")

        assert validated_key is None
        assert error == "Invalid API key"

    @pytest.mark.asyncio
    async def test_validate_api_key_inactive(self, api_key_service, sample_api_key):
        """Test validation of inactive key."""
        full_key = "sark_sk_live_abc12345_secret"
        sample_api_key.key_hash = APIKeyService._hash_key(full_key)
        sample_api_key.is_active = False

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key(full_key)

        assert validated_key is None
        assert error == "API key is inactive"

    @pytest.mark.asyncio
    async def test_validate_api_key_revoked(self, api_key_service, sample_api_key):
        """Test validation of revoked key."""
        full_key = "sark_sk_live_abc12345_secret"
        sample_api_key.key_hash = APIKeyService._hash_key(full_key)
        sample_api_key.revoked_at = datetime.now(UTC)

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key(full_key)

        assert validated_key is None
        assert error == "API key has been revoked"

    @pytest.mark.asyncio
    async def test_validate_api_key_expired(self, api_key_service, sample_api_key):
        """Test validation of expired key."""
        full_key = "sark_sk_live_abc12345_secret"
        sample_api_key.key_hash = APIKeyService._hash_key(full_key)
        sample_api_key.expires_at = datetime.now(UTC) - timedelta(days=1)

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key(full_key)

        assert validated_key is None
        assert error == "API key has expired"

    @pytest.mark.asyncio
    async def test_validate_api_key_missing_scope(self, api_key_service, sample_api_key):
        """Test validation with required scope not present."""
        full_key = "sark_sk_live_abc12345_secret"
        sample_api_key.key_hash = APIKeyService._hash_key(full_key)
        sample_api_key.scopes = ["server:read"]
        sample_api_key.is_active = True
        sample_api_key.revoked_at = None
        sample_api_key.expires_at = None

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key(
            full_key, required_scope="server:delete"
        )

        assert validated_key is None
        assert "does not have required scope" in error

    @pytest.mark.asyncio
    async def test_validate_api_key_admin_scope(self, api_key_service, sample_api_key):
        """Test validation with admin scope (has all permissions)."""
        full_key = "sark_sk_live_abc12345_secret"
        sample_api_key.key_hash = APIKeyService._hash_key(full_key)
        sample_api_key.scopes = ["admin"]
        sample_api_key.is_active = True
        sample_api_key.revoked_at = None
        sample_api_key.expires_at = None

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        validated_key, error = await api_key_service.validate_api_key(
            full_key, required_scope="server:delete"
        )

        assert validated_key is not None
        assert error is None


class TestAPIKeyServiceRotation:
    """Test API key rotation."""

    @pytest.mark.asyncio
    async def test_rotate_api_key_success(self, api_key_service, sample_api_key):
        """Test successful key rotation."""
        old_prefix = sample_api_key.key_prefix
        old_hash = sample_api_key.key_hash

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        rotated_key, new_key = await api_key_service.rotate_api_key(sample_api_key.id)

        assert rotated_key is not None
        assert new_key.startswith("sark_sk_")
        assert sample_api_key.key_prefix != old_prefix
        assert sample_api_key.key_hash != old_hash

    @pytest.mark.asyncio
    async def test_rotate_api_key_not_found(self, api_key_service):
        """Test rotating non-existent key."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        api_key_service.db.execute.return_value = result

        rotated_key = await api_key_service.rotate_api_key(uuid.uuid4())

        assert rotated_key is None


class TestAPIKeyServiceRevocation:
    """Test API key revocation."""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, api_key_service, sample_api_key):
        """Test successful key revocation."""
        revoked_by = uuid.uuid4()

        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        success = await api_key_service.revoke_api_key(sample_api_key.id, revoked_by)

        assert success is True
        assert sample_api_key.is_active is False
        assert sample_api_key.revoked_at is not None
        assert sample_api_key.revoked_by == revoked_by

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, api_key_service):
        """Test revoking non-existent key."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        api_key_service.db.execute.return_value = result

        success = await api_key_service.revoke_api_key(uuid.uuid4())

        assert success is False


class TestAPIKeyServiceUpdate:
    """Test API key updates."""

    @pytest.mark.asyncio
    async def test_update_api_key_name(self, api_key_service, sample_api_key):
        """Test updating API key name."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        updated_key = await api_key_service.update_api_key(sample_api_key.id, name="New Name")

        assert updated_key is not None
        assert updated_key.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_api_key_scopes(self, api_key_service, sample_api_key):
        """Test updating API key scopes."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        new_scopes = ["server:read", "policy:read"]
        updated_key = await api_key_service.update_api_key(sample_api_key.id, scopes=new_scopes)

        assert updated_key.scopes == new_scopes

    @pytest.mark.asyncio
    async def test_update_api_key_invalid_scopes(self, api_key_service, sample_api_key):
        """Test updating with invalid scopes."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_api_key
        api_key_service.db.execute.return_value = result

        with pytest.raises(ValueError, match="Invalid scopes"):
            await api_key_service.update_api_key(sample_api_key.id, scopes=["invalid:scope"])


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_check_rate_limit_allowed(self, sample_api_key):
        """Test rate limit check when under limit."""
        sample_api_key.rate_limit = 1000
        current_usage = 500

        is_allowed, info = APIKeyService.check_rate_limit(sample_api_key, current_usage)

        assert is_allowed is True
        assert info["limit"] == 1000
        assert info["remaining"] == 500
        assert info["reset_in_seconds"] == 60

    def test_check_rate_limit_exceeded(self, sample_api_key):
        """Test rate limit check when limit exceeded."""
        sample_api_key.rate_limit = 1000
        current_usage = 1000

        is_allowed, info = APIKeyService.check_rate_limit(sample_api_key, current_usage)

        assert is_allowed is False
        assert info["limit"] == 1000
        assert info["remaining"] == 0

    def test_check_rate_limit_at_limit(self, sample_api_key):
        """Test rate limit check exactly at limit."""
        sample_api_key.rate_limit = 1000
        current_usage = 999

        is_allowed, info = APIKeyService.check_rate_limit(sample_api_key, current_usage)

        assert is_allowed is True
        assert info["remaining"] == 1


class TestAPIKeyServiceList:
    """Test listing API keys."""

    @pytest.mark.asyncio
    async def test_list_api_keys_by_user(self, api_key_service, sample_user_id):
        """Test listing API keys by user."""
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        api_key_service.db.execute.return_value = result

        keys = await api_key_service.list_api_keys(user_id=sample_user_id)

        assert isinstance(keys, list)
        assert api_key_service.db.execute.called

    @pytest.mark.asyncio
    async def test_list_api_keys_by_team(self, api_key_service):
        """Test listing API keys by team."""
        team_id = uuid.uuid4()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        api_key_service.db.execute.return_value = result

        keys = await api_key_service.list_api_keys(team_id=team_id)

        assert isinstance(keys, list)

    @pytest.mark.asyncio
    async def test_list_api_keys_include_revoked(self, api_key_service, sample_user_id):
        """Test listing API keys including revoked."""
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        api_key_service.db.execute.return_value = result

        keys = await api_key_service.list_api_keys(user_id=sample_user_id, include_revoked=True)

        assert isinstance(keys, list)
