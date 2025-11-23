"""Comprehensive tests for API key authentication."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
import pytest

from sark.services.auth.api_key import (
    APIKey,
    APIKeyService,
    get_api_key,
    require_scope,
)


class TestAPIKeyService:
    """Test suite for APIKeyService class."""

    @pytest.fixture
    def service(self):
        """Create an APIKeyService instance."""
        return APIKeyService()

    @pytest.fixture
    def sample_owner_id(self):
        """Sample owner UUID."""
        return uuid4()

    # ===== Key Generation Tests =====

    def test_generate_key_returns_string(self, service):
        """Test generate_key returns a string."""
        key = service.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_is_unique(self, service):
        """Test generate_key produces unique keys."""
        keys = {service.generate_key() for _ in range(100)}
        assert len(keys) == 100  # All unique

    def test_generate_key_with_custom_length(self):
        """Test generate_key with custom key length."""
        service = APIKeyService(key_length=64)
        key = service.generate_key()
        # URL-safe base64 encoding increases length
        assert len(key) >= 64

    def test_generate_key_is_url_safe(self, service):
        """Test generated keys are URL-safe."""
        key = service.generate_key()
        # Should only contain URL-safe characters
        import string

        allowed = set(string.ascii_letters + string.digits + "-_")
        assert all(c in allowed for c in key)

    # ===== Key Hashing Tests =====

    def test_hash_key_returns_string(self, service):
        """Test hash_key returns a string."""
        key = "test_api_key_12345"
        key_hash = service.hash_key(key)
        assert isinstance(key_hash, str)
        assert len(key_hash) == 64  # SHA256 hex digest is 64 chars

    def test_hash_key_is_deterministic(self, service):
        """Test hash_key produces same hash for same input."""
        key = "test_api_key_12345"
        hash1 = service.hash_key(key)
        hash2 = service.hash_key(key)
        assert hash1 == hash2

    def test_hash_key_different_for_different_inputs(self, service):
        """Test hash_key produces different hashes for different inputs."""
        hash1 = service.hash_key("key_one")
        hash2 = service.hash_key("key_two")
        assert hash1 != hash2

    def test_hash_key_handles_special_characters(self, service):
        """Test hash_key handles special characters."""
        key = "special!@#$%^&*()_+-=[]{}|;:',.<>?/`~"
        key_hash = service.hash_key(key)
        assert len(key_hash) == 64

    # ===== Key Verification Tests =====

    def test_verify_key_valid(self, service):
        """Test verify_key returns True for valid key."""
        plain_key = "test_api_key_12345"
        key_hash = service.hash_key(plain_key)
        assert service.verify_key(plain_key, key_hash) is True

    def test_verify_key_invalid(self, service):
        """Test verify_key returns False for invalid key."""
        plain_key = "test_api_key_12345"
        key_hash = service.hash_key(plain_key)
        assert service.verify_key("wrong_key", key_hash) is False

    def test_verify_key_case_sensitive(self, service):
        """Test verify_key is case-sensitive."""
        plain_key = "TestApiKey"
        key_hash = service.hash_key(plain_key)
        assert service.verify_key("testapikey", key_hash) is False

    # ===== API Key Creation Tests =====

    def test_create_api_key_basic(self, service, sample_owner_id):
        """Test creating a basic API key."""
        plain_key, api_key = service.create_api_key(
            name="test-key",
            owner_id=sample_owner_id,
        )

        assert isinstance(plain_key, str)
        assert len(plain_key) > 0
        assert isinstance(api_key, APIKey)
        assert api_key.name == "test-key"
        assert api_key.owner_id == sample_owner_id
        assert api_key.is_active is True
        assert api_key.scopes == []
        assert api_key.description is None
        assert api_key.expires_at is None

    def test_create_api_key_with_scopes(self, service, sample_owner_id):
        """Test creating API key with scopes."""
        scopes = ["read:servers", "write:servers"]
        _plain_key, api_key = service.create_api_key(
            name="scoped-key",
            owner_id=sample_owner_id,
            scopes=scopes,
        )

        assert api_key.scopes == scopes

    def test_create_api_key_with_description(self, service, sample_owner_id):
        """Test creating API key with description."""
        _plain_key, api_key = service.create_api_key(
            name="described-key",
            owner_id=sample_owner_id,
            description="This is a test key",
        )

        assert api_key.description == "This is a test key"

    def test_create_api_key_with_expiration(self, service, sample_owner_id):
        """Test creating API key with expiration."""
        before_create = datetime.now(UTC)
        _plain_key, api_key = service.create_api_key(
            name="expiring-key",
            owner_id=sample_owner_id,
            expires_in_days=30,
        )
        datetime.now(UTC)

        assert api_key.expires_at is not None
        expected_expiry = before_create + timedelta(days=30)
        assert abs((api_key.expires_at - expected_expiry).total_seconds()) < 5

    def test_create_api_key_hash_matches(self, service, sample_owner_id):
        """Test created API key hash matches plain key."""
        plain_key, api_key = service.create_api_key(
            name="hash-test-key",
            owner_id=sample_owner_id,
        )

        assert service.verify_key(plain_key, api_key.key_hash) is True

    def test_create_api_key_unique_ids(self, service, sample_owner_id):
        """Test created API keys have unique IDs."""
        _, key1 = service.create_api_key("key1", sample_owner_id)
        _, key2 = service.create_api_key("key2", sample_owner_id)

        assert key1.key_id != key2.key_id

    def test_create_api_key_timestamps(self, service, sample_owner_id):
        """Test created API key has correct timestamps."""
        before_create = datetime.now(UTC)
        _plain_key, api_key = service.create_api_key(
            name="timestamp-key",
            owner_id=sample_owner_id,
        )
        after_create = datetime.now(UTC)

        assert before_create <= api_key.created_at <= after_create
        assert api_key.last_used_at is None

    # ===== API Key Validation Tests =====

    def test_validate_api_key_active(self, service, sample_owner_id):
        """Test validate_api_key passes for active key."""
        _, api_key = service.create_api_key("active-key", sample_owner_id)
        assert service.validate_api_key(api_key) is True

    def test_validate_api_key_inactive(self, service, sample_owner_id):
        """Test validate_api_key raises for inactive key."""
        _, api_key = service.create_api_key("inactive-key", sample_owner_id)
        api_key.is_active = False

        with pytest.raises(HTTPException) as exc_info:
            service.validate_api_key(api_key)

        assert exc_info.value.status_code == 401
        assert "inactive" in exc_info.value.detail.lower()

    def test_validate_api_key_expired(self, service, sample_owner_id):
        """Test validate_api_key raises for expired key."""
        _, api_key = service.create_api_key("expired-key", sample_owner_id)
        api_key.expires_at = datetime.now(UTC) - timedelta(days=1)

        with pytest.raises(HTTPException) as exc_info:
            service.validate_api_key(api_key)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_validate_api_key_not_yet_expired(self, service, sample_owner_id):
        """Test validate_api_key passes for key not yet expired."""
        _, api_key = service.create_api_key("future-key", sample_owner_id)
        api_key.expires_at = datetime.now(UTC) + timedelta(days=30)

        assert service.validate_api_key(api_key) is True

    def test_validate_api_key_no_expiration(self, service, sample_owner_id):
        """Test validate_api_key passes for key with no expiration."""
        _, api_key = service.create_api_key("permanent-key", sample_owner_id)
        assert api_key.expires_at is None
        assert service.validate_api_key(api_key) is True

    # ===== Scope Checking Tests =====

    def test_has_scope_present(self, service, sample_owner_id):
        """Test has_scope returns True when scope is present."""
        _, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers", "write:servers"],
        )

        assert service.has_scope(api_key, "read:servers") is True
        assert service.has_scope(api_key, "write:servers") is True

    def test_has_scope_absent(self, service, sample_owner_id):
        """Test has_scope returns False when scope is absent."""
        _, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers"],
        )

        assert service.has_scope(api_key, "write:servers") is False

    def test_has_scope_wildcard(self, service, sample_owner_id):
        """Test has_scope returns True for any scope with wildcard."""
        _, api_key = service.create_api_key(
            "admin-key",
            sample_owner_id,
            scopes=["*"],
        )

        assert service.has_scope(api_key, "read:servers") is True
        assert service.has_scope(api_key, "write:servers") is True
        assert service.has_scope(api_key, "delete:servers") is True
        assert service.has_scope(api_key, "anything:at:all") is True

    def test_has_scope_empty_scopes(self, service, sample_owner_id):
        """Test has_scope returns False when key has no scopes."""
        _, api_key = service.create_api_key("no-scope-key", sample_owner_id)

        assert service.has_scope(api_key, "read:servers") is False

    def test_has_any_scope_single_match(self, service, sample_owner_id):
        """Test has_any_scope returns True with single match."""
        _, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers", "write:servers"],
        )

        assert service.has_any_scope(api_key, ["read:servers", "delete:servers"]) is True

    def test_has_any_scope_multiple_matches(self, service, sample_owner_id):
        """Test has_any_scope returns True with multiple matches."""
        _, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers", "write:servers"],
        )

        assert service.has_any_scope(api_key, ["read:servers", "write:servers"]) is True

    def test_has_any_scope_no_match(self, service, sample_owner_id):
        """Test has_any_scope returns False with no matches."""
        _, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers"],
        )

        assert service.has_any_scope(api_key, ["write:servers", "delete:servers"]) is False

    def test_has_any_scope_wildcard(self, service, sample_owner_id):
        """Test has_any_scope returns True for wildcard."""
        _, api_key = service.create_api_key(
            "admin-key",
            sample_owner_id,
            scopes=["*"],
        )

        assert service.has_any_scope(api_key, ["read:servers", "write:servers"]) is True

    def test_has_any_scope_empty_check_list(self, service, sample_owner_id):
        """Test has_any_scope returns False for empty check list."""
        _, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers"],
        )

        assert service.has_any_scope(api_key, []) is False


class TestGetAPIKey:
    """Test suite for get_api_key dependency function."""

    @pytest.fixture
    def service(self):
        """Create an APIKeyService instance."""
        return APIKeyService()

    @pytest.fixture
    def sample_owner_id(self):
        """Sample owner UUID."""
        return uuid4()

    @pytest.fixture(autouse=True)
    def clear_api_key_store(self):
        """Clear API key store before each test."""
        from sark.services.auth.api_key import _api_key_store

        _api_key_store.clear()
        yield
        _api_key_store.clear()

    @pytest.mark.asyncio
    async def test_get_api_key_valid(self, service, sample_owner_id):
        """Test get_api_key with valid key."""
        from sark.services.auth.api_key import _api_key_store

        plain_key, api_key = service.create_api_key("test-key", sample_owner_id)
        _api_key_store[str(api_key.key_id)] = api_key

        result = await get_api_key(plain_key)

        assert result.key_id == api_key.key_id
        assert result.name == "test-key"

    @pytest.mark.asyncio
    async def test_get_api_key_missing(self):
        """Test get_api_key with missing key raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(None)

        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_api_key_invalid(self):
        """Test get_api_key with invalid key raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key("invalid_key_12345")

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_api_key_inactive(self, service, sample_owner_id):
        """Test get_api_key with inactive key raises HTTPException."""
        from sark.services.auth.api_key import _api_key_store

        plain_key, api_key = service.create_api_key("inactive-key", sample_owner_id)
        api_key.is_active = False
        _api_key_store[str(api_key.key_id)] = api_key

        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(plain_key)

        assert exc_info.value.status_code == 401
        assert "inactive" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_api_key_expired(self, service, sample_owner_id):
        """Test get_api_key with expired key raises HTTPException."""
        from sark.services.auth.api_key import _api_key_store

        plain_key, api_key = service.create_api_key("expired-key", sample_owner_id)
        api_key.expires_at = datetime.now(UTC) - timedelta(days=1)
        _api_key_store[str(api_key.key_id)] = api_key

        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(plain_key)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


class TestRequireScope:
    """Test suite for require_scope dependency function."""

    @pytest.fixture
    def service(self):
        """Create an APIKeyService instance."""
        return APIKeyService()

    @pytest.fixture
    def sample_owner_id(self):
        """Sample owner UUID."""
        return uuid4()

    @pytest.fixture(autouse=True)
    def clear_api_key_store(self):
        """Clear API key store before each test."""
        from sark.services.auth.api_key import _api_key_store

        _api_key_store.clear()
        yield
        _api_key_store.clear()

    @pytest.mark.asyncio
    async def test_require_scope_has_scope(self, service, sample_owner_id):
        """Test require_scope passes when key has required scope."""
        from sark.services.auth.api_key import _api_key_store

        _plain_key, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers"],
        )
        _api_key_store[str(api_key.key_id)] = api_key

        # Create the dependency
        check_scope = require_scope("read:servers")

        # Mock get_api_key to return our test key (using AsyncMock for async function)
        with patch("sark.services.auth.api_key.get_api_key", new=AsyncMock(return_value=api_key)):
            result = await check_scope(api_key=api_key)

        assert result.key_id == api_key.key_id

    @pytest.mark.asyncio
    async def test_require_scope_lacks_scope(self, service, sample_owner_id):
        """Test require_scope raises when key lacks required scope."""
        from sark.services.auth.api_key import _api_key_store

        _plain_key, api_key = service.create_api_key(
            "scoped-key",
            sample_owner_id,
            scopes=["read:servers"],
        )
        _api_key_store[str(api_key.key_id)] = api_key

        # Create the dependency
        check_scope = require_scope("write:servers")

        # Mock get_api_key to return our test key
        with patch("sark.services.auth.api_key.get_api_key", new=AsyncMock(return_value=api_key)):
            with pytest.raises(HTTPException) as exc_info:
                await check_scope(api_key=api_key)

            assert exc_info.value.status_code == 403
            assert "scope" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_require_scope_wildcard(self, service, sample_owner_id):
        """Test require_scope passes with wildcard scope."""
        from sark.services.auth.api_key import _api_key_store

        _plain_key, api_key = service.create_api_key(
            "admin-key",
            sample_owner_id,
            scopes=["*"],
        )
        _api_key_store[str(api_key.key_id)] = api_key

        # Create the dependency
        check_scope = require_scope("any:scope:here")

        # Mock get_api_key to return our test key
        with patch("sark.services.auth.api_key.get_api_key", new=AsyncMock(return_value=api_key)):
            result = await check_scope(api_key=api_key)

        assert result.key_id == api_key.key_id
