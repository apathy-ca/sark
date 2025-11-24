"""Tests for LDAP authentication provider."""

from unittest.mock import Mock, patch

from ldap3 import Connection
from ldap3.core.exceptions import LDAPBindError, LDAPException
import pytest

from sark.services.auth.providers.ldap import LDAPProvider, LDAPProviderConfig


@pytest.fixture
def ldap_config():
    """LDAP configuration for testing."""
    return {
        "name": "test-ldap-provider",
        "server_url": "ldap://test.example.com:389",
        "bind_dn": "cn=admin,dc=example,dc=com",
        "bind_password": "admin_password",
        "base_dn": "dc=example,dc=com",
        "group_search_base": "ou=groups,dc=example,dc=com",
    }


@pytest.fixture
def ldap_provider(ldap_config):
    """Create LDAP provider for testing."""
    return LDAPProvider(LDAPProviderConfig(**ldap_config))


# Test Initialization


class TestLDAPProviderInitialization:
    """Test LDAP provider initialization."""

    def test_basic_initialization(self, ldap_config):
        """Test basic LDAP provider initialization."""
        config = LDAPProviderConfig(**ldap_config)
        provider = LDAPProvider(config)

        assert provider.config.server_url == ldap_config["server_url"]
        assert provider.config.bind_dn == ldap_config["bind_dn"]
        assert provider.config.bind_password == ldap_config["bind_password"]
        assert provider.config.base_dn == ldap_config["base_dn"]

    def test_custom_search_filters(self, ldap_config):
        """Test LDAP provider with custom search filters."""
        config_dict = ldap_config.copy()
        config_dict["user_search_filter"] = "(sAMAccountName={username})"
        config_dict["group_search_filter"] = "(memberOf={user_dn})"
        config = LDAPProviderConfig(**config_dict)
        provider = LDAPProvider(config)

        assert provider.config.user_search_filter == "(sAMAccountName={username})"
        assert provider.config.group_search_filter == "(memberOf={user_dn})"

    def test_ssl_configuration(self, ldap_config):
        """Test LDAP provider with SSL enabled."""
        config_dict = ldap_config.copy()
        config_dict["server_url"] = "ldaps://test.example.com:636"
        config_dict["use_ssl"] = True
        config = LDAPProviderConfig(**config_dict)
        provider = LDAPProvider(config)

        assert provider.config.use_ssl is True
        assert provider.config.server_url.startswith("ldaps://")


# Test Authentication


class TestAuthentication:
    """Test LDAP authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, ldap_provider):
        """Test successful LDAP authentication."""
        # Mock LDAP entry
        mock_entry = Mock()
        mock_entry.entry_dn = "uid=jdoe,ou=users,dc=example,dc=com"
        mock_entry.mail = Mock(value="jdoe@example.com")
        mock_entry.cn = Mock(value="John Doe")
        mock_entry.givenName = Mock(value="John")
        mock_entry.sn = Mock(value="Doe")

        # Mock service account connection
        mock_service_conn = Mock(spec=Connection)
        mock_service_conn.entries = [mock_entry]

        # Mock user connection (for password verification)
        mock_user_conn = Mock(spec=Connection)

        with patch.object(ldap_provider, "_get_connection") as mock_get_conn:
            # First call returns service account connection
            # Second call returns user connection (password verify)
            mock_get_conn.side_effect = [mock_service_conn, mock_user_conn]

            user_info = await ldap_provider.authenticate(
                {"username": "jdoe", "password": "secret"}
            )

            assert user_info is not None
            assert user_info.user_id == "uid=jdoe,ou=users,dc=example,dc=com"
            assert user_info.email == "jdoe@example.com"
            assert user_info.name == "John Doe"
            assert user_info.given_name == "John"
            assert user_info.family_name == "Doe"
            mock_service_conn.unbind.assert_called_once()
            mock_user_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, ldap_provider):
        """Test authentication when user is not found."""
        mock_conn = Mock(spec=Connection)
        mock_conn.entries = []  # No user found

        with patch.object(ldap_provider, "_get_connection", return_value=mock_conn):
            user_info = await ldap_provider.authenticate(
                {"username": "nonexistent", "password": "secret"}
            )

            assert user_info is None
            mock_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, ldap_provider):
        """Test authentication with wrong password."""
        mock_entry = Mock()
        mock_entry.entry_dn = "uid=jdoe,ou=users,dc=example,dc=com"
        mock_entry.mail = Mock(value="jdoe@example.com")
        mock_entry.cn = Mock(value="John Doe")

        mock_service_conn = Mock(spec=Connection)
        mock_service_conn.entries = [mock_entry]

        with patch.object(ldap_provider, "_get_connection") as mock_get_conn:
            # Service connection succeeds, user bind fails
            mock_get_conn.side_effect = [mock_service_conn, LDAPBindError()]

            user_info = await ldap_provider.authenticate(
                {"username": "jdoe", "password": "wrong_password"}
            )

            assert user_info is None
            mock_service_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_missing_username(self, ldap_provider):
        """Test authentication with missing username."""
        user_info = await ldap_provider.authenticate({"password": "secret"})

        assert user_info is None

    @pytest.mark.asyncio
    async def test_authenticate_missing_password(self, ldap_provider):
        """Test authentication with missing password."""
        user_info = await ldap_provider.authenticate({"username": "jdoe"})

        assert user_info is None

    @pytest.mark.asyncio
    async def test_authenticate_ldap_exception(self, ldap_provider):
        """Test authentication when LDAP exception occurs."""
        with patch.object(
            ldap_provider, "_get_connection", side_effect=LDAPException("Connection error")
        ):
            user_info = await ldap_provider.authenticate(
                {"username": "jdoe", "password": "secret"}
            )

            assert user_info is None

    @pytest.mark.asyncio
    async def test_authenticate_with_groups(self, ldap_provider):
        """Test authentication with group lookup."""
        mock_entry = Mock()
        mock_entry.entry_dn = "uid=jdoe,ou=users,dc=example,dc=com"
        mock_entry.mail = Mock(value="jdoe@example.com")
        mock_entry.cn = Mock(value="John Doe")

        mock_service_conn = Mock(spec=Connection)
        mock_service_conn.entries = [mock_entry]

        mock_user_conn = Mock(spec=Connection)

        with patch.object(ldap_provider, "_get_connection") as mock_get_conn, patch.object(
            ldap_provider, "_get_user_groups", return_value=["developers", "admins"]
        ):
            mock_get_conn.side_effect = [mock_service_conn, mock_user_conn]

            user_info = await ldap_provider.authenticate(
                {"username": "jdoe", "password": "secret"}
            )

            assert user_info is not None
            assert user_info.groups == ["developers", "admins"]


# Test Group Lookup


class TestGroupLookup:
    """Test LDAP group lookup functionality."""

    @pytest.mark.asyncio
    async def test_get_user_groups_success(self, ldap_provider):
        """Test successful group lookup."""
        mock_entry1 = Mock()
        mock_entry1.cn = Mock(value="developers")

        mock_entry2 = Mock()
        mock_entry2.cn = Mock(value="admins")

        mock_conn = Mock(spec=Connection)
        mock_conn.entries = [mock_entry1, mock_entry2]

        with patch.object(ldap_provider, "_get_connection", return_value=mock_conn):
            groups = await ldap_provider._get_user_groups(
                "uid=jdoe,ou=users,dc=example,dc=com"
            )

            assert groups == ["developers", "admins"]
            mock_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_groups_no_groups(self, ldap_provider):
        """Test group lookup when user has no groups."""
        mock_conn = Mock(spec=Connection)
        mock_conn.entries = []

        with patch.object(ldap_provider, "_get_connection", return_value=mock_conn):
            groups = await ldap_provider._get_user_groups(
                "uid=jdoe,ou=users,dc=example,dc=com"
            )

            assert groups == []
            mock_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_groups_no_base_dn(self, ldap_config):
        """Test group lookup when group_search_base is not configured."""
        config_dict = ldap_config.copy()
        config_dict["group_search_base"] = None
        config = LDAPProviderConfig(**config_dict)
        provider = LDAPProvider(config)

        groups = await provider._get_user_groups("uid=jdoe,ou=users,dc=example,dc=com")

        assert groups == []

    @pytest.mark.asyncio
    async def test_get_user_groups_ldap_exception(self, ldap_provider):
        """Test group lookup when LDAP exception occurs."""
        with patch.object(
            ldap_provider, "_get_connection", side_effect=LDAPException("Connection error")
        ):
            groups = await ldap_provider._get_user_groups(
                "uid=jdoe,ou=users,dc=example,dc=com"
            )

            assert groups == []


# Test User Lookup


class TestUserLookup:
    """Test LDAP user lookup functionality."""

    @pytest.mark.asyncio
    async def test_lookup_user_success(self, ldap_provider):
        """Test successful user lookup."""
        mock_entry = Mock()
        mock_entry.entry_dn = "uid=jdoe,ou=users,dc=example,dc=com"
        mock_entry.mail = Mock(value="jdoe@example.com")
        mock_entry.cn = Mock(value="John Doe")
        mock_entry.givenName = Mock(value="John")
        mock_entry.sn = Mock(value="Doe")

        mock_conn = Mock(spec=Connection)
        mock_conn.entries = [mock_entry]

        with patch.object(ldap_provider, "_get_connection", return_value=mock_conn):
            with patch.object(
                ldap_provider, "_get_user_groups", return_value=["developers"]
            ):
                user_info = await ldap_provider.lookup_user("jdoe")

                assert user_info is not None
                assert user_info.email == "jdoe@example.com"
                assert user_info.name == "John Doe"
                assert user_info.groups == ["developers"]
                mock_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_user_not_found(self, ldap_provider):
        """Test user lookup when user not found."""
        mock_conn = Mock(spec=Connection)
        mock_conn.entries = []

        with patch.object(ldap_provider, "_get_connection", return_value=mock_conn):
            user_info = await ldap_provider.lookup_user("nonexistent")

            assert user_info is None
            mock_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_user_ldap_exception(self, ldap_provider):
        """Test user lookup when LDAP exception occurs."""
        with patch.object(
            ldap_provider, "_get_connection", side_effect=LDAPException("Connection error")
        ):
            user_info = await ldap_provider.lookup_user("jdoe")

            assert user_info is None


# Test Health Check


class TestHealthCheck:
    """Test LDAP health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, ldap_provider):
        """Test successful health check."""
        mock_conn = Mock(spec=Connection)

        with patch.object(ldap_provider, "_get_connection", return_value=mock_conn):
            is_healthy = await ldap_provider.health_check()

            assert is_healthy is True
            mock_conn.search.assert_called_once()
            mock_conn.unbind.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ldap_provider):
        """Test health check when LDAP server is unavailable."""
        with patch.object(
            ldap_provider, "_get_connection", side_effect=LDAPException("Connection error")
        ):
            is_healthy = await ldap_provider.health_check()

            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_unexpected_error(self, ldap_provider):
        """Test health check with unexpected error."""
        with patch.object(
            ldap_provider, "_get_connection", side_effect=Exception("Unexpected error")
        ):
            is_healthy = await ldap_provider.health_check()

            assert is_healthy is False


# Test OAuth/Token Methods (Not Supported)


class TestUnsupportedMethods:
    """Test methods that are not supported by LDAP provider."""

    @pytest.mark.asyncio
    async def test_validate_token_not_supported(self, ldap_provider):
        """Test that token validation is not supported."""
        result = await ldap_provider.validate_token("fake_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_token_not_supported(self, ldap_provider):
        """Test that token refresh is not supported."""
        result = await ldap_provider.refresh_token("fake_refresh_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_authorization_url_not_supported(self, ldap_provider):
        """Test that authorization URL is not supported."""
        result = await ldap_provider.get_authorization_url("state", "redirect_uri")

        assert result == ""

    @pytest.mark.asyncio
    async def test_handle_callback_not_supported(self, ldap_provider):
        """Test that OAuth callback is not supported."""
        result = await ldap_provider.handle_callback("code", "state", "redirect_uri")

        assert result is None


# Test User Info Extraction


class TestUserInfoExtraction:
    """Test user information extraction from LDAP entries."""

    def test_extract_user_info_complete(self, ldap_provider):
        """Test extraction with all attributes present."""
        mock_entry = Mock()
        mock_entry.mail = Mock(value="jdoe@example.com")
        mock_entry.cn = Mock(value="John Doe")
        mock_entry.givenName = Mock(value="John")
        mock_entry.sn = Mock(value="Doe")

        user_info = ldap_provider._extract_user_info(
            mock_entry, "uid=jdoe,ou=users,dc=example,dc=com"
        )

        assert user_info.user_id == "uid=jdoe,ou=users,dc=example,dc=com"
        assert user_info.email == "jdoe@example.com"
        assert user_info.name == "John Doe"
        assert user_info.given_name == "John"
        assert user_info.family_name == "Doe"
        assert user_info.attributes == {"dn": "uid=jdoe,ou=users,dc=example,dc=com"}

    def test_extract_user_info_minimal(self, ldap_provider):
        """Test extraction with minimal attributes."""
        mock_entry = Mock()
        mock_entry.mail = Mock(value="jdoe@example.com")
        # Other attributes don't exist
        delattr(mock_entry, "cn") if hasattr(mock_entry, "cn") else None
        delattr(mock_entry, "givenName") if hasattr(mock_entry, "givenName") else None
        delattr(mock_entry, "sn") if hasattr(mock_entry, "sn") else None

        user_info = ldap_provider._extract_user_info(
            mock_entry, "uid=jdoe,ou=users,dc=example,dc=com"
        )

        assert user_info.email == "jdoe@example.com"
        assert user_info.name is None
        assert user_info.given_name is None
        assert user_info.family_name is None

    def test_extract_user_info_missing_email(self, ldap_provider):
        """Test extraction when email is missing."""
        mock_entry = Mock()
        delattr(mock_entry, "mail") if hasattr(mock_entry, "mail") else None

        user_info = ldap_provider._extract_user_info(
            mock_entry, "uid=jdoe,ou=users,dc=example,dc=com"
        )

        assert user_info.email == ""
        assert user_info.user_id == "uid=jdoe,ou=users,dc=example,dc=com"


# Test Active Directory Specific


class TestActiveDirectoryIntegration:
    """Test Active Directory specific configurations."""

    def test_active_directory_search_filter(self, ldap_config):
        """Test provider with Active Directory sAMAccountName filter."""
        config_dict = ldap_config.copy()
        config_dict["user_search_filter"] = "(sAMAccountName={username})"
        config = LDAPProviderConfig(**config_dict)
        provider = LDAPProvider(config)

        assert provider.config.user_search_filter == "(sAMAccountName={username})"

    def test_active_directory_group_filter(self, ldap_config):
        """Test provider with Active Directory memberOf filter."""
        config_dict = ldap_config.copy()
        config_dict["group_search_filter"] = "(memberOf={user_dn})"
        config = LDAPProviderConfig(**config_dict)
        provider = LDAPProvider(config)

        assert provider.config.group_search_filter == "(memberOf={user_dn})"
