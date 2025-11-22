"""Tests for OIDC authentication provider."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from authlib.jose import JsonWebToken

from sark.services.auth.providers.base import UserInfo
from sark.services.auth.providers.oidc import OIDCProvider


@pytest.fixture
def google_provider():
    """Create a Google OIDC provider for testing."""
    return OIDCProvider(
        client_id="test-client-id",
        client_secret="test-client-secret",
        provider="google",
    )


@pytest.fixture
def azure_provider():
    """Create an Azure AD OIDC provider for testing."""
    return OIDCProvider(
        client_id="test-client-id",
        client_secret="test-client-secret",
        provider="azure",
        tenant="test-tenant-id",
    )


@pytest.fixture
def okta_provider():
    """Create an Okta OIDC provider for testing."""
    return OIDCProvider(
        client_id="test-client-id",
        client_secret="test-client-secret",
        provider="okta",
        domain="test.okta.com",
    )


@pytest.fixture
def custom_provider():
    """Create a custom OIDC provider for testing."""
    return OIDCProvider(
        client_id="test-client-id",
        client_secret="test-client-secret",
        provider="custom",
        issuer="https://custom.example.com",
        authorization_endpoint="https://custom.example.com/oauth/authorize",
        token_endpoint="https://custom.example.com/oauth/token",
        userinfo_endpoint="https://custom.example.com/oauth/userinfo",
        jwks_uri="https://custom.example.com/oauth/jwks",
    )


@pytest.fixture
def mock_jwt_claims():
    """Mock JWT claims for testing."""
    return {
        "sub": "user-123",
        "email": "user@example.com",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/photo.jpg",
        "iss": "https://accounts.google.com",
        "aud": "test-client-id",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }


class TestOIDCProviderInitialization:
    """Test OIDC provider initialization."""

    def test_google_provider_initialization(self, google_provider):
        """Test Google provider is initialized correctly."""
        assert google_provider.provider == "google"
        assert google_provider.issuer == "https://accounts.google.com"
        assert "google.com" in google_provider.authorization_endpoint
        assert google_provider.scopes == ["openid", "profile", "email"]

    def test_azure_provider_initialization(self, azure_provider):
        """Test Azure AD provider is initialized correctly."""
        assert azure_provider.provider == "azure"
        assert "test-tenant-id" in azure_provider.issuer
        assert "test-tenant-id" in azure_provider.authorization_endpoint
        assert "test-tenant-id" in azure_provider.token_endpoint

    def test_azure_provider_missing_tenant(self):
        """Test Azure AD provider raises error without tenant."""
        with pytest.raises(ValueError, match="Azure AD requires 'tenant' parameter"):
            OIDCProvider(
                client_id="test",
                client_secret="test",
                provider="azure",
            )

    def test_okta_provider_initialization(self, okta_provider):
        """Test Okta provider is initialized correctly."""
        assert okta_provider.provider == "okta"
        assert "test.okta.com" in okta_provider.issuer
        assert "test.okta.com" in okta_provider.authorization_endpoint

    def test_okta_provider_missing_domain(self):
        """Test Okta provider raises error without domain."""
        with pytest.raises(ValueError, match="Okta requires 'domain' parameter"):
            OIDCProvider(
                client_id="test",
                client_secret="test",
                provider="okta",
            )

    def test_custom_provider_initialization(self, custom_provider):
        """Test custom provider is initialized correctly."""
        assert custom_provider.provider == "custom"
        assert custom_provider.issuer == "https://custom.example.com"
        assert custom_provider.authorization_endpoint == "https://custom.example.com/oauth/authorize"

    def test_custom_provider_missing_endpoints(self):
        """Test custom provider raises error without all endpoints."""
        with pytest.raises(ValueError, match="Custom OIDC provider requires all endpoints"):
            OIDCProvider(
                client_id="test",
                client_secret="test",
                provider="custom",
                issuer="https://custom.example.com",
            )

    def test_custom_scopes(self):
        """Test provider with custom scopes."""
        provider = OIDCProvider(
            client_id="test",
            client_secret="test",
            provider="google",
            scopes=["openid", "email"],
        )
        assert provider.scopes == ["openid", "email"]


class TestAuthentication:
    """Test authentication methods."""

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_token(self, google_provider, mock_jwt_claims):
        """Test authentication with valid access token."""
        with patch.object(google_provider, "validate_token", new_callable=AsyncMock) as mock_validate:
            expected_user = UserInfo(
                user_id="user-123",
                email="user@example.com",
                name="Test User",
            )
            mock_validate.return_value = expected_user

            result = await google_provider.authenticate({"access_token": "test-token"})

            assert result == expected_user
            mock_validate.assert_called_once_with("test-token")

    @pytest.mark.asyncio
    async def test_authenticate_with_id_token(self, google_provider):
        """Test authentication with ID token."""
        with patch.object(google_provider, "validate_token", new_callable=AsyncMock) as mock_validate:
            expected_user = UserInfo(user_id="user-123", email="user@example.com")
            mock_validate.return_value = expected_user

            result = await google_provider.authenticate({"id_token": "test-id-token"})

            assert result == expected_user
            mock_validate.assert_called_once_with("test-id-token")

    @pytest.mark.asyncio
    async def test_authenticate_without_token(self, google_provider):
        """Test authentication without token returns None."""
        result = await google_provider.authenticate({})
        assert result is None


class TestTokenValidation:
    """Test token validation."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self, google_provider, mock_jwt_claims):
        """Test successful token validation."""
        with patch.object(google_provider, "_get_jwks", new_callable=AsyncMock) as mock_jwks, \
             patch.object(google_provider.jwt, "decode") as mock_decode:

            mock_jwks.return_value = {"keys": []}

            # Create a mock JWTClaims-like object
            mock_claims = MagicMock()
            mock_claims.__iter__ = lambda self: iter(mock_jwt_claims.items())
            mock_claims.get = lambda key, default=None: mock_jwt_claims.get(key, default)
            mock_claims.validate = MagicMock()
            mock_decode.return_value = mock_claims

            result = await google_provider.validate_token("test-token")

            assert result is not None
            assert result.user_id == "user-123"
            assert result.email == "user@example.com"
            assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, google_provider):
        """Test token validation with invalid token."""
        with patch.object(google_provider, "_get_jwks", new_callable=AsyncMock) as mock_jwks, \
             patch.object(google_provider.jwt, "decode", side_effect=Exception("Invalid token")):

            mock_jwks.return_value = {"keys": []}
            result = await google_provider.validate_token("invalid-token")
            assert result is None


class TestTokenRefresh:
    """Test token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, google_provider):
        """Test successful token refresh."""
        with patch.object(google_provider.client, "refresh_token", new_callable=AsyncMock) as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "id_token": "new-id-token",
            }

            result = await google_provider.refresh_token("old-refresh-token")

            assert result is not None
            assert result["access_token"] == "new-access-token"
            assert result["refresh_token"] == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, google_provider):
        """Test token refresh failure."""
        with patch.object(
            google_provider.client,
            "refresh_token",
            new_callable=AsyncMock,
            side_effect=Exception("Refresh failed"),
        ):
            result = await google_provider.refresh_token("invalid-token")
            assert result is None


class TestAuthorizationFlow:
    """Test OAuth authorization flow."""

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, google_provider):
        """Test generation of authorization URL."""
        url = await google_provider.get_authorization_url(
            state="test-state",
            redirect_uri="https://example.com/callback",
        )

        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=test-client-id" in url
        assert "state=test-state" in url
        assert "redirect_uri=" in url
        assert "scope=" in url

    @pytest.mark.asyncio
    async def test_handle_callback_success(self, google_provider):
        """Test successful OAuth callback handling."""
        with patch.object(google_provider.client, "fetch_token", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
                "id_token": "id-token",
                "token_type": "Bearer",
            }

            result = await google_provider.handle_callback(
                code="auth-code",
                state="test-state",
                redirect_uri="https://example.com/callback",
            )

            assert result is not None
            assert result["access_token"] == "access-token"
            assert result["token_type"] == "Bearer"
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_failure(self, google_provider):
        """Test OAuth callback handling failure."""
        with patch.object(
            google_provider.client,
            "fetch_token",
            new_callable=AsyncMock,
            side_effect=Exception("Token exchange failed"),
        ):
            result = await google_provider.handle_callback(
                code="invalid-code",
                state="test-state",
                redirect_uri="https://example.com/callback",
            )
            assert result is None


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, google_provider):
        """Test successful health check."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await google_provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, google_provider):
        """Test health check failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            result = await google_provider.health_check()
            assert result is False


class TestUserInfo:
    """Test user info extraction."""

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, google_provider):
        """Test successful user info retrieval."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "sub": "user-123",
                "email": "user@example.com",
                "name": "Test User",
                "picture": "https://example.com/photo.jpg",
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await google_provider.get_user_info("access-token")

            assert result is not None
            assert result.user_id == "user-123"
            assert result.email == "user@example.com"
            assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self, google_provider):
        """Test user info retrieval failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("API call failed")
            )

            result = await google_provider.get_user_info("invalid-token")
            assert result is None

    def test_extract_user_info_with_groups(self, google_provider):
        """Test user info extraction with groups."""
        claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "name": "Test User",
            "groups": ["admin", "developers"],
        }

        user_info = google_provider._extract_user_info(claims)

        assert user_info.user_id == "user-123"
        assert user_info.groups == ["admin", "developers"]

    def test_extract_user_info_with_roles(self, google_provider):
        """Test user info extraction with roles (Azure AD)."""
        claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "roles": ["Administrator", "User"],
        }

        user_info = google_provider._extract_user_info(claims)

        assert user_info.groups == ["Administrator", "User"]

    def test_extract_user_info_minimal(self, google_provider):
        """Test user info extraction with minimal claims."""
        claims = {
            "sub": "user-123",
            "email": "user@example.com",
        }

        user_info = google_provider._extract_user_info(claims)

        assert user_info.user_id == "user-123"
        assert user_info.email == "user@example.com"
        assert user_info.name is None
        assert user_info.groups is None


class TestJWKSCaching:
    """Test JWKS caching functionality."""

    @pytest.mark.asyncio
    async def test_jwks_caching(self, google_provider):
        """Test JWKS are cached properly."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"keys": [{"kid": "key1"}]}
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # First call - should fetch
            jwks1 = await google_provider._get_jwks()
            assert jwks1 == {"keys": [{"kid": "key1"}]}

            # Second call - should use cache
            jwks2 = await google_provider._get_jwks()
            assert jwks2 == jwks1

            # Should only call the API once
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 1

    @pytest.mark.asyncio
    async def test_jwks_cache_expiration(self, google_provider):
        """Test JWKS cache expiration."""
        google_provider._jwks_cache_ttl = 1  # 1 second TTL

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"keys": [{"kid": "key1"}]}
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # First call
            await google_provider._get_jwks()

            # Wait for cache to expire
            time.sleep(1.1)

            # Second call - should fetch again
            await google_provider._get_jwks()

            # Should call the API twice
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 2
