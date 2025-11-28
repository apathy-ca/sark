"""Comprehensive tests for OIDC authentication provider."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from sark.services.auth.providers.oidc import OIDCProvider, OIDCProviderConfig


class TestOIDCProviderConfig:
    """Test suite for OIDCProviderConfig."""

    def test_config_initialization(self):
        """Test OIDC config initialization with required fields."""
        config = OIDCProviderConfig(
            name="test-oidc",
            issuer_url="https://issuer.example.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        assert config.name == "test-oidc"
        assert config.issuer_url == "https://issuer.example.com"
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.enabled is True
        assert config.scopes == ["openid", "profile", "email"]

    def test_config_with_custom_scopes(self):
        """Test OIDC config with custom scopes."""
        config = OIDCProviderConfig(
            name="test-oidc",
            issuer_url="https://issuer.example.com",
            client_id="client_id",
            client_secret="client_secret",
            scopes=["openid", "custom_scope"],
        )

        assert config.scopes == ["openid", "custom_scope"]

    def test_config_with_redirect_uri(self):
        """Test OIDC config with redirect URI."""
        config = OIDCProviderConfig(
            name="test-oidc",
            issuer_url="https://issuer.example.com",
            client_id="client_id",
            client_secret="client_secret",
            redirect_uri="https://app.example.com/callback",
        )

        assert config.redirect_uri == "https://app.example.com/callback"


class TestOIDCProvider:
    """Test suite for OIDCProvider."""

    @pytest.fixture
    def config(self):
        """Create test OIDC config."""
        return OIDCProviderConfig(
            name="test-oidc",
            issuer_url="https://issuer.example.com",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="https://app.example.com/callback",
        )

    @pytest.fixture
    def provider(self, config):
        """Create OIDC provider instance."""
        return OIDCProvider(config)

    @pytest.fixture
    def mock_discovery_doc(self):
        """Mock OIDC discovery document."""
        return {
            "issuer": "https://issuer.example.com",
            "authorization_endpoint": "https://issuer.example.com/authorize",
            "token_endpoint": "https://issuer.example.com/token",
            "userinfo_endpoint": "https://issuer.example.com/userinfo",
            "jwks_uri": "https://issuer.example.com/jwks",
        }

    # ===== Discovery Document Tests =====

    @pytest.mark.asyncio
    async def test_get_discovery_document(self, provider, mock_discovery_doc):
        """Test fetching OIDC discovery document."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_discovery_doc
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            result = await provider._get_discovery_document()

            assert result == mock_discovery_doc
            assert provider._discovery_cache == mock_discovery_doc

    @pytest.mark.asyncio
    async def test_discovery_document_cached(self, provider, mock_discovery_doc):
        """Test discovery document is cached after first fetch."""
        provider._discovery_cache = mock_discovery_doc

        result = await provider._get_discovery_document()

        assert result == mock_discovery_doc
        # No HTTP call should be made

    # ===== Authentication Tests =====

    @pytest.mark.asyncio
    async def test_authenticate_success(self, provider, mock_discovery_doc):
        """Test successful OIDC authentication."""
        user_sub = str(uuid4())
        mock_token_response = {
            "access_token": "test_access_token",
            "id_token": "test_id_token",
            "token_type": "Bearer",
        }
        mock_userinfo = {
            "sub": user_sub,
            "email": "user@example.com",
            "name": "Test User",
            "groups": ["group1", "group2"],
        }

        with patch.object(provider, "_get_discovery_document", return_value=mock_discovery_doc):
            with patch("httpx.AsyncClient") as mock_client:
                # Mock token endpoint response
                mock_token_resp = MagicMock()
                mock_token_resp.status_code = 200
                mock_token_resp.json.return_value = mock_token_response

                # Mock userinfo endpoint response
                mock_userinfo_resp = MagicMock()
                mock_userinfo_resp.json.return_value = mock_userinfo
                mock_userinfo_resp.raise_for_status = MagicMock()

                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None
                mock_client_instance.post = AsyncMock(return_value=mock_token_resp)
                mock_client_instance.get = AsyncMock(return_value=mock_userinfo_resp)
                mock_client.return_value = mock_client_instance

                result = await provider.authenticate("user", "auth_code")

                assert result.success is True
                assert result.user_id == UUID(user_sub)
                assert result.email == "user@example.com"
                assert result.display_name == "Test User"
                assert result.groups == ["group1", "group2"]

    @pytest.mark.asyncio
    async def test_authenticate_token_exchange_failed(self, provider, mock_discovery_doc):
        """Test authentication fails when token exchange fails."""
        with patch.object(provider, "_get_discovery_document", return_value=mock_discovery_doc):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.text = "Invalid authorization code"

                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_client_instance

                result = await provider.authenticate("user", "bad_code")

                assert result.success is False
                assert "Token exchange failed" in result.error_message

    @pytest.mark.asyncio
    async def test_authenticate_no_id_token(self, provider, mock_discovery_doc):
        """Test authentication fails when no ID token returned."""
        mock_token_response = {
            "access_token": "test_access_token",
            # Missing id_token
        }

        with patch.object(provider, "_get_discovery_document", return_value=mock_discovery_doc):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_response

                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_client_instance

                result = await provider.authenticate("user", "auth_code")

                assert result.success is False
                assert "No ID token" in result.error_message

    # ===== Token Validation Tests =====

    @pytest.mark.asyncio
    async def test_validate_token_success(self, provider):
        """Test successful token validation."""
        user_sub = str(uuid4())
        mock_userinfo = {
            "sub": user_sub,
            "email": "user@example.com",
            "name": "Test User",
        }

        with patch.object(provider, "_get_userinfo", return_value=mock_userinfo):
            result = await provider.validate_token("valid_token")

            assert result.success is True
            assert result.user_id == UUID(user_sub)
            assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_validate_token_failed(self, provider):
        """Test token validation failure."""
        with patch.object(
            provider,
            "_get_userinfo",
            side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=MagicMock()
            ),
        ):
            result = await provider.validate_token("invalid_token")

            assert result.success is False
            assert result.error_message is not None

    # ===== Userinfo Tests =====

    @pytest.mark.asyncio
    async def test_get_userinfo(self, provider, mock_discovery_doc):
        """Test fetching user info from userinfo endpoint."""
        mock_userinfo = {
            "sub": str(uuid4()),
            "email": "user@example.com",
            "name": "Test User",
        }

        provider._discovery_cache = mock_discovery_doc

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_userinfo
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            result = await provider._get_userinfo("access_token")

            assert result == mock_userinfo

    # ===== Get User Info Tests =====

    @pytest.mark.asyncio
    async def test_get_user_info(self, provider):
        """Test get_user_info returns basic info."""
        user_id = uuid4()

        result = await provider.get_user_info(user_id)

        assert result["user_id"] == str(user_id)

    # ===== Health Check Tests =====

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider, mock_discovery_doc):
        """Test health check succeeds when discovery document is fetchable."""
        with patch.object(provider, "_get_discovery_document", return_value=mock_discovery_doc):
            result = await provider.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failed(self, provider):
        """Test health check fails when discovery document fetch fails."""
        with patch.object(
            provider, "_get_discovery_document", side_effect=httpx.HTTPError("Connection failed")
        ):
            result = await provider.health_check()

            assert result is False
