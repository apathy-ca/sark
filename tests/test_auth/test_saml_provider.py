"""Tests for SAML authentication provider."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.auth.providers.base import UserInfo
from sark.services.auth.providers.saml import SAMLProvider, SAMLProviderConfig


@pytest.fixture
def saml_config():
    """SAML configuration for testing."""
    return {
        "sp_entity_id": "https://sark.example.com",
        "sp_acs_url": "https://sark.example.com/api/auth/saml/acs",
        "sp_sls_url": "https://sark.example.com/api/auth/saml/slo",
        "idp_entity_id": "https://idp.example.com",
        "idp_sso_url": "https://idp.example.com/sso",
        "idp_slo_url": "https://idp.example.com/slo",
        "idp_x509_cert": "MIICertificateDataHere",
    }


@pytest.fixture
def azure_saml_provider(saml_config):
    """Create an Azure AD SAML provider for testing."""
    return SAMLProvider(SAMLProviderConfig(**saml_config))


@pytest.fixture
def saml_provider_with_signing(saml_config):
    """Create a SAML provider with signing configured."""
    config = saml_config.copy()
    config["sp_x509_cert"] = "MIICertificateDataHere"
    config["sp_private_key"] = "-----BEGIN PRIVATE KEY-----\nKeyDataHere\n-----END PRIVATE KEY-----"
    return SAMLProvider(SAMLProviderConfig(**config))


@pytest.fixture
def mock_saml_response():
    """Mock SAML response data."""
    # Simplified base64-encoded SAML response
    saml_xml = """<?xml version="1.0"?>
    <samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
        <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
            <saml:Subject>
                <saml:NameID>user@example.com</saml:NameID>
            </saml:Subject>
        </saml:Assertion>
    </samlp:Response>"""
    return base64.b64encode(saml_xml.encode()).decode()


class TestSAMLProviderInitialization:
    """Test SAML provider initialization."""

    def test_basic_initialization(self, saml_config):
        """Test basic SAML provider initialization."""
        config = SAMLProviderConfig(**saml_config)
        provider = SAMLProvider(config)

        assert provider.config.sp_entity_id == saml_config["sp_entity_id"]
        assert provider.config.idp_sso_url == saml_config["idp_sso_url"]
        assert provider.config.sign_requests is True

    def test_initialization_with_signing(self, saml_config):
        """Test SAML provider initialization with signing certificates."""
        config_dict = saml_config.copy()
        config_dict["sign_requests"] = True
        config = SAMLProviderConfig(**config_dict)
        provider = SAMLProvider(config)

        assert provider.config.sign_requests is True

    def test_custom_name_id_format(self, saml_config):
        """Test SAML provider with custom NameID format."""
        config_dict = saml_config.copy()
        config_dict["name_id_format"] = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
        config = SAMLProviderConfig(**config_dict)
        provider = SAMLProvider(config)

        assert (
            provider.config.name_id_format == "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
        )


class TestAuthentication:
    """Test SAML authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_missing_response(self, azure_saml_provider):
        """Test authentication with missing SAML response."""
        result = await azure_saml_provider.authenticate({})
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_success(self, azure_saml_provider, mock_saml_response):
        """Test successful SAML authentication."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            # Setup mock auth object
            mock_auth = MagicMock()
            mock_auth.process_response = MagicMock()
            mock_auth.get_errors = MagicMock(return_value=[])
            mock_auth.is_authenticated = MagicMock(return_value=True)
            mock_auth.get_nameid = MagicMock(return_value="user@example.com")
            mock_auth.get_attributes = MagicMock(
                return_value={
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": [
                        "user@example.com"
                    ],
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": ["Test User"],
                }
            )
            mock_auth_class.return_value = mock_auth

            result = await azure_saml_provider.authenticate(
                {"saml_response": mock_saml_response, "relay_state": "/"}
            )

            assert result is not None
            assert isinstance(result, UserInfo)
            assert result.user_id == "user@example.com"
            assert result.email == "user@example.com"
            assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_authenticate_with_errors(self, azure_saml_provider, mock_saml_response):
        """Test authentication with SAML errors."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.process_response = MagicMock()
            mock_auth.get_errors = MagicMock(return_value=["Invalid signature"])
            mock_auth_class.return_value = mock_auth

            result = await azure_saml_provider.authenticate({"saml_response": mock_saml_response})

            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_not_authenticated(self, azure_saml_provider, mock_saml_response):
        """Test authentication when is_authenticated returns False."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.process_response = MagicMock()
            mock_auth.get_errors = MagicMock(return_value=[])
            mock_auth.is_authenticated = MagicMock(return_value=False)
            mock_auth_class.return_value = mock_auth

            result = await azure_saml_provider.authenticate({"saml_response": mock_saml_response})

            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_exception(self, azure_saml_provider, mock_saml_response):
        """Test authentication with exception."""
        with patch(
            "sark.services.auth.providers.saml.OneLogin_Saml2_Auth",
            side_effect=Exception("SAML processing error"),
        ):
            result = await azure_saml_provider.authenticate({"saml_response": mock_saml_response})

            assert result is None


class TestTokenValidation:
    """Test token validation (not applicable for SAML)."""

    @pytest.mark.asyncio
    async def test_validate_token_not_implemented(self, azure_saml_provider):
        """Test that validate_token raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="SAML uses session-based authentication"):
            await azure_saml_provider.validate_token("some-token")


class TestTokenRefresh:
    """Test token refresh (not applicable for SAML)."""

    @pytest.mark.asyncio
    async def test_refresh_token_returns_none(self, azure_saml_provider):
        """Test that refresh_token returns None for SAML."""
        result = await azure_saml_provider.refresh_token("refresh-token")
        assert result is None


class TestAuthorizationFlow:
    """Test SAML authorization flow."""

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, azure_saml_provider):
        """Test generation of SAML SSO URL."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.login = MagicMock(
                return_value="https://idp.example.com/sso?SAMLRequest=encodedRequest"
            )
            mock_auth_class.return_value = mock_auth

            url = await azure_saml_provider.get_authorization_url(
                state="/dashboard",
                redirect_uri="",  # Not used in SAML
            )

            assert url.startswith("https://idp.example.com/sso")
            assert "SAMLRequest" in url
            mock_auth.login.assert_called_once_with(return_to="/dashboard")

    @pytest.mark.asyncio
    async def test_get_authorization_url_error(self, azure_saml_provider):
        """Test authorization URL generation error fallback."""
        with patch(
            "sark.services.auth.providers.saml.OneLogin_Saml2_Auth",
            side_effect=Exception("SSO error"),
        ):
            url = await azure_saml_provider.get_authorization_url(state="/", redirect_uri="")

            # Should fall back to IdP SSO URL
            assert url == azure_saml_provider.idp_sso_url

    @pytest.mark.asyncio
    async def test_handle_callback_success(self, azure_saml_provider, mock_saml_response):
        """Test successful SAML callback handling."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.process_response = MagicMock()
            mock_auth.get_errors = MagicMock(return_value=[])
            mock_auth.is_authenticated = MagicMock(return_value=True)
            mock_auth.get_nameid = MagicMock(return_value="user@example.com")
            mock_auth.get_attributes = MagicMock(
                return_value={"email": ["user@example.com"], "name": ["Test User"]}
            )
            mock_auth_class.return_value = mock_auth

            result = await azure_saml_provider.handle_callback(
                code=mock_saml_response,
                state="/dashboard",
                redirect_uri="",
            )

            assert result is not None
            assert result["user_id"] == "user@example.com"
            assert result["email"] == "user@example.com"
            assert result["authenticated"] == "true"

    @pytest.mark.asyncio
    async def test_handle_callback_failure(self, azure_saml_provider, mock_saml_response):
        """Test SAML callback handling failure."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.process_response = MagicMock()
            mock_auth.get_errors = MagicMock(return_value=["Invalid assertion"])
            mock_auth_class.return_value = mock_auth

            result = await azure_saml_provider.handle_callback(
                code=mock_saml_response,
                state="/",
                redirect_uri="",
            )

            assert result is None


class TestHealthCheck:
    """Test SAML provider health check."""

    @pytest.mark.asyncio
    async def test_health_check_with_metadata_url(self, saml_config):
        """Test health check with IdP metadata URL."""
        provider = SAMLProvider(**saml_config, idp_metadata_url="https://idp.example.com/metadata")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_metadata_url_failure(self, saml_config):
        """Test health check when metadata URL is unreachable."""
        provider = SAMLProvider(**saml_config, idp_metadata_url="https://idp.example.com/metadata")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            result = await provider.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_without_metadata_url(self, azure_saml_provider):
        """Test health check without metadata URL (validates SSO URL)."""
        result = await azure_saml_provider.health_check()
        assert result is True  # Valid HTTPS URL

    @pytest.mark.asyncio
    async def test_health_check_invalid_sso_url(self, saml_config):
        """Test health check with invalid SSO URL."""
        config = saml_config.copy()
        config["idp_sso_url"] = "invalid-url"
        provider = SAMLProvider(**config)

        result = await provider.health_check()
        assert result is False


class TestMetadata:
    """Test SAML metadata generation."""

    def test_get_metadata(self, azure_saml_provider):
        """Test SP metadata generation."""
        with patch(
            "sark.services.auth.providers.saml.OneLogin_Saml2_Settings"
        ) as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.get_sp_metadata = MagicMock(
                return_value='<?xml version="1.0"?><EntityDescriptor>...</EntityDescriptor>'
            )
            mock_settings.validate_metadata = MagicMock(return_value=[])
            mock_settings_class.return_value = mock_settings

            metadata = azure_saml_provider.get_metadata()

            assert metadata is not None
            assert "EntityDescriptor" in metadata
            mock_settings.get_sp_metadata.assert_called_once()

    def test_get_metadata_with_errors(self, azure_saml_provider):
        """Test metadata generation with validation errors."""
        with patch(
            "sark.services.auth.providers.saml.OneLogin_Saml2_Settings"
        ) as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.get_sp_metadata = MagicMock(return_value="<EntityDescriptor>...")
            mock_settings.validate_metadata = MagicMock(return_value=["Invalid metadata"])
            mock_settings_class.return_value = mock_settings

            with pytest.raises(ValueError, match="Invalid SP metadata"):
                azure_saml_provider.get_metadata()


class TestUserInfoExtraction:
    """Test user info extraction from SAML assertions."""

    def test_extract_user_info_basic(self, azure_saml_provider):
        """Test basic user info extraction."""
        mock_auth = MagicMock()
        mock_auth.get_nameid = MagicMock(return_value="user@example.com")
        mock_auth.get_attributes = MagicMock(
            return_value={
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": [
                    "user@example.com"
                ],
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": ["Test User"],
            }
        )

        user_info = azure_saml_provider._extract_user_info_from_auth(mock_auth)

        assert user_info.user_id == "user@example.com"
        assert user_info.email == "user@example.com"
        assert user_info.name == "Test User"

    def test_extract_user_info_with_groups(self, azure_saml_provider):
        """Test user info extraction with groups."""
        mock_auth = MagicMock()
        mock_auth.get_nameid = MagicMock(return_value="user@example.com")
        mock_auth.get_attributes = MagicMock(
            return_value={
                "email": ["user@example.com"],
                "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": [
                    "Admins",
                    "Developers",
                ],
            }
        )

        user_info = azure_saml_provider._extract_user_info_from_auth(mock_auth)

        assert user_info.groups == ["Admins", "Developers"]

    def test_extract_user_info_minimal(self, azure_saml_provider):
        """Test user info extraction with minimal attributes."""
        mock_auth = MagicMock()
        mock_auth.get_nameid = MagicMock(return_value="user@example.com")
        mock_auth.get_attributes = MagicMock(return_value={})

        user_info = azure_saml_provider._extract_user_info_from_auth(mock_auth)

        assert user_info.user_id == "user@example.com"
        assert user_info.email == "user@example.com"
        assert user_info.name is None
        assert user_info.groups is None


class TestAttributeMapping:
    """Test SAML attribute mapping."""

    def test_map_attributes_azure_format(self, azure_saml_provider):
        """Test attribute mapping for Azure AD format."""
        raw_attributes = {
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": [
                "user@example.com"
            ],
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": ["Test User"],
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": ["Test"],
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": ["User"],
        }

        mapped = azure_saml_provider._map_attributes(raw_attributes)

        assert mapped["email"] == "user@example.com"
        assert mapped["name"] == "Test User"
        assert mapped["given_name"] == "Test"
        assert mapped["family_name"] == "User"

    def test_map_attributes_okta_format(self, azure_saml_provider):
        """Test attribute mapping for Okta format."""
        raw_attributes = {
            "email": ["user@example.com"],
            "firstName": ["Test"],
            "lastName": ["User"],
            "groups": ["Admin", "User"],
        }

        mapped = azure_saml_provider._map_attributes(raw_attributes)

        assert mapped["email"] == "user@example.com"
        assert mapped["given_name"] == "Test"
        assert mapped["family_name"] == "User"
        assert mapped["groups"] == ["Admin", "User"]

    def test_map_attributes_custom_mapping(self, saml_config):
        """Test custom attribute mapping."""
        custom_mapping = {
            "customEmail": "email",
            "displayName": "name",
        }

        provider = SAMLProvider(**saml_config, attribute_mapping=custom_mapping)

        raw_attributes = {
            "customEmail": ["custom@example.com"],
            "displayName": ["Custom User"],
        }

        mapped = provider._map_attributes(raw_attributes)

        assert mapped["email"] == "custom@example.com"
        assert mapped["name"] == "Custom User"


class TestLogout:
    """Test SAML logout functionality."""

    @pytest.mark.asyncio
    async def test_initiate_logout(self, azure_saml_provider):
        """Test SP-initiated logout."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.logout = MagicMock(
                return_value="https://idp.example.com/slo?SAMLRequest=logoutRequest"
            )
            mock_auth_class.return_value = mock_auth

            logout_url = await azure_saml_provider.initiate_logout(
                name_id="user@example.com",
                session_index="session123",
            )

            assert logout_url.startswith("https://idp.example.com/slo")
            assert "SAMLRequest" in logout_url
            mock_auth.logout.assert_called_once_with(
                name_id="user@example.com",
                session_index="session123",
            )

    @pytest.mark.asyncio
    async def test_initiate_logout_error(self, azure_saml_provider):
        """Test logout initiation error."""
        with patch(
            "sark.services.auth.providers.saml.OneLogin_Saml2_Auth",
            side_effect=Exception("Logout error"),
        ):
            logout_url = await azure_saml_provider.initiate_logout(name_id="user@example.com")

            # Should fall back to IdP SLO URL
            assert logout_url == azure_saml_provider.idp_slo_url

    @pytest.mark.asyncio
    async def test_process_logout_request(self, azure_saml_provider):
        """Test processing IdP-initiated logout request."""
        with patch("sark.services.auth.providers.saml.OneLogin_Saml2_Auth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.process_slo = MagicMock(return_value="https://app.example.com/")
            mock_auth_class.return_value = mock_auth

            await azure_saml_provider.process_logout_request("base64EncodedLogoutRequest")

            # In real implementation, this would return the logout response
            # For now, we're just testing the flow
            mock_auth.process_slo.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_logout_request_error(self, azure_saml_provider):
        """Test logout request processing error."""
        with patch(
            "sark.services.auth.providers.saml.OneLogin_Saml2_Auth",
            side_effect=Exception("Processing error"),
        ):
            logout_response = await azure_saml_provider.process_logout_request("logoutRequest")

            assert logout_response == ""


class TestRequestPreparation:
    """Test SAML request preparation."""

    def test_prepare_request_basic(self, azure_saml_provider):
        """Test basic request preparation."""
        credentials = {
            "saml_response": "base64EncodedResponse",
            "relay_state": "/dashboard",
        }

        req = azure_saml_provider._prepare_request(credentials)

        assert req["https"] == "on"
        assert req["http_host"] == "sark.example.com"
        assert req["post_data"]["SAMLResponse"] == "base64EncodedResponse"
        assert req["post_data"]["RelayState"] == "/dashboard"

    def test_prepare_request_http(self, saml_config):
        """Test request preparation with HTTP URL."""
        config = saml_config.copy()
        config["sp_acs_url"] = "http://sark.example.com:8000/api/auth/saml/acs"
        provider = SAMLProvider(**config)

        req = provider._prepare_request({"saml_response": "response"})

        assert req["https"] == "off"
        assert req["server_port"] == 8000

    def test_prepare_request_minimal(self, azure_saml_provider):
        """Test request preparation with minimal data."""
        req = azure_saml_provider._prepare_request({})

        assert "https" in req
        assert "http_host" in req
        assert "post_data" in req
        assert req["post_data"] == {}
