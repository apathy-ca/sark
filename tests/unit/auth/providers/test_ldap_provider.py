"""Comprehensive tests for LDAP authentication provider."""

from unittest.mock import patch
from uuid import UUID

import pytest

from sark.services.auth.providers.ldap import LDAPProvider, LDAPProviderConfig


class TestLDAPProviderConfig:
    """Test suite for LDAPProviderConfig."""

    def test_config_initialization(self):
        """Test LDAP config initialization with required fields."""
        config = LDAPProviderConfig(
            name="test-ldap",
            server_url="ldap://ldap.example.com",
            base_dn="dc=example,dc=com",
        )

        assert config.name == "test-ldap"
        assert config.server_url == "ldap://ldap.example.com"
        assert config.base_dn == "dc=example,dc=com"
        assert config.enabled is True
        assert config.use_ssl is True

    def test_config_with_bind_credentials(self):
        """Test LDAP config with bind credentials."""
        config = LDAPProviderConfig(
            name="test-ldap",
            server_url="ldap://ldap.example.com",
            base_dn="dc=example,dc=com",
            bind_dn="cn=admin,dc=example,dc=com",
            bind_password="admin_password",
        )

        assert config.bind_dn == "cn=admin,dc=example,dc=com"
        assert config.bind_password == "admin_password"

    def test_config_with_custom_search_filter(self):
        """Test LDAP config with custom user search filter."""
        config = LDAPProviderConfig(
            name="test-ldap",
            server_url="ldap://ldap.example.com",
            base_dn="dc=example,dc=com",
            user_search_filter="(sAMAccountName={username})",
        )

        assert config.user_search_filter == "(sAMAccountName={username})"

    def test_config_with_group_search(self):
        """Test LDAP config with group search configuration."""
        config = LDAPProviderConfig(
            name="test-ldap",
            server_url="ldap://ldap.example.com",
            base_dn="dc=example,dc=com",
            group_search_base="ou=groups,dc=example,dc=com",
            group_search_filter="(uniqueMember={user_dn})",
        )

        assert config.group_search_base == "ou=groups,dc=example,dc=com"
        assert config.group_search_filter == "(uniqueMember={user_dn})"


class TestLDAPProvider:
    """Test suite for LDAPProvider."""

    @pytest.fixture
    def config(self):
        """Create test LDAP config."""
        return LDAPProviderConfig(
            name="test-ldap",
            server_url="ldap://ldap.example.com",
            base_dn="dc=example,dc=com",
            bind_dn="cn=admin,dc=example,dc=com",
            bind_password="admin_password",
        )

    @pytest.fixture
    def provider(self, config):
        """Create LDAP provider instance."""
        return LDAPProvider(config)

    # ===== Authentication Tests =====

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, provider):
        """Test authentication fails when user not found."""
        with patch.object(provider, "_search_user", return_value=(None, {})):
            result = await provider.authenticate("nonexistent", "password")

            assert result.success is False
            assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self, provider):
        """Test authentication fails with invalid credentials."""
        user_dn = "uid=testuser,ou=users,dc=example,dc=com"
        user_attrs = {"uid": "testuser", "mail": "test@example.com", "cn": "Test User"}

        with patch.object(provider, "_search_user", return_value=(user_dn, user_attrs)):
            with patch.object(provider, "_bind_user", return_value=False):
                result = await provider.authenticate("testuser", "wrong_password")

                assert result.success is False
                assert "Invalid credentials" in result.error_message

    @pytest.mark.asyncio
    async def test_authenticate_success(self, provider):
        """Test successful authentication."""
        user_dn = "uid=testuser,ou=users,dc=example,dc=com"
        user_attrs = {
            "uid": "testuser",
            "mail": "test@example.com",
            "cn": "Test User",
        }
        groups = ["developers", "admins"]

        with patch.object(provider, "_search_user", return_value=(user_dn, user_attrs)):
            with patch.object(provider, "_bind_user", return_value=True):
                with patch.object(provider, "_get_user_groups", return_value=groups):
                    result = await provider.authenticate("testuser", "correct_password")

                    assert result.success is True
                    assert isinstance(result.user_id, UUID)
                    assert result.email == "test@example.com"
                    assert result.display_name == "Test User"
                    assert result.groups == groups
                    assert result.metadata["provider"] == "ldap"
                    assert result.metadata["dn"] == user_dn

    @pytest.mark.asyncio
    async def test_authenticate_uuid_generation(self, provider):
        """Test that user UUID is stable for same DN."""
        user_dn = "uid=testuser,ou=users,dc=example,dc=com"
        user_attrs = {"uid": "testuser", "mail": "test@example.com", "cn": "Test User"}

        with patch.object(provider, "_search_user", return_value=(user_dn, user_attrs)):
            with patch.object(provider, "_bind_user", return_value=True):
                with patch.object(provider, "_get_user_groups", return_value=[]):
                    result1 = await provider.authenticate("testuser", "password")
                    result2 = await provider.authenticate("testuser", "password")

                    assert result1.user_id == result2.user_id

    @pytest.mark.asyncio
    async def test_authenticate_exception_handling(self, provider):
        """Test authentication handles exceptions gracefully."""
        with patch.object(provider, "_search_user", side_effect=Exception("LDAP connection failed")):
            result = await provider.authenticate("testuser", "password")

            assert result.success is False
            assert "LDAP connection failed" in result.error_message

    # ===== Token Validation Tests =====

    @pytest.mark.asyncio
    async def test_validate_token_not_supported(self, provider):
        """Test that token validation is not supported for LDAP."""
        result = await provider.validate_token("any_token")

        assert result.success is False
        assert "not supported" in result.error_message.lower()

    # ===== User Search Tests =====

    @pytest.mark.asyncio
    async def test_search_user(self, provider):
        """Test user search returns expected format."""
        user_dn, user_attrs = await provider._search_user("testuser")

        # Mock implementation returns None
        assert user_dn is None
        assert user_attrs == {}

    # ===== Bind Tests =====

    @pytest.mark.asyncio
    async def test_bind_user(self, provider):
        """Test user bind attempt."""
        result = await provider._bind_user("uid=test,dc=example,dc=com", "password")

        # Mock implementation returns False
        assert result is False

    # ===== Group Search Tests =====

    @pytest.mark.asyncio
    async def test_get_user_groups_no_group_base(self, provider):
        """Test get_user_groups returns empty list when no group base configured."""
        provider.config.group_search_base = None

        groups = await provider._get_user_groups("uid=test,dc=example,dc=com")

        assert groups == []

    @pytest.mark.asyncio
    async def test_get_user_groups_with_group_base(self, provider):
        """Test get_user_groups when group base is configured."""
        provider.config.group_search_base = "ou=groups,dc=example,dc=com"

        groups = await provider._get_user_groups("uid=test,dc=example,dc=com")

        # Mock implementation returns empty list
        assert groups == []

    # ===== Get User Info Tests =====

    @pytest.mark.asyncio
    async def test_get_user_info(self, provider):
        """Test get_user_info returns basic info."""
        user_id = "uid=test,dc=example,dc=com"

        result = await provider.get_user_info(user_id)

        assert result["user_id"] == user_id
        assert result["provider"] == "ldap"

    # ===== Health Check Tests =====

    @pytest.mark.asyncio
    async def test_health_check_enabled(self, provider):
        """Test health check succeeds when enabled and configured."""
        result = await provider.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_disabled(self, provider):
        """Test health check fails when disabled."""
        provider.config.enabled = False

        result = await provider.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_no_server_url(self, provider):
        """Test health check fails when server URL is missing."""
        provider.config.server_url = ""

        result = await provider.health_check()

        assert result is False
