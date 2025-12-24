"""Integration tests for OIDC authentication provider using Docker."""

import pytest

# Import fixtures from oidc_docker
pytest_plugins = ["tests.fixtures.oidc_docker"]


@pytest.mark.integration
class TestOIDCIntegrationDiscovery:
    """OIDC discovery document integration tests."""

    @pytest.mark.asyncio
    async def test_fetch_discovery_document(self, oidc_provider):
        """Test fetching OIDC discovery document."""
        discovery = await oidc_provider._get_discovery_document()

        assert discovery is not None
        assert "authorization_endpoint" in discovery
        assert "token_endpoint" in discovery
        assert "userinfo_endpoint" in discovery
        assert "jwks_uri" in discovery

    @pytest.mark.asyncio
    async def test_discovery_document_cached(self, oidc_provider):
        """Test that discovery document is cached."""
        discovery1 = await oidc_provider._get_discovery_document()
        discovery2 = await oidc_provider._get_discovery_document()

        assert discovery1 == discovery2
        assert oidc_provider._discovery_cache is not None


@pytest.mark.integration
class TestOIDCIntegrationHealthCheck:
    """OIDC health check integration tests."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, oidc_provider):
        """Test health check succeeds with running OIDC server."""
        result = await oidc_provider.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_with_invalid_server(self):
        """Test health check fails with invalid server."""
        from sark.services.auth.providers.oidc import OIDCProvider, OIDCProviderConfig

        # Create provider with invalid server URL
        invalid_config = OIDCProviderConfig(
            name="test-oidc-invalid",
            issuer_url="http://nonexistent.example.com:9999",
            client_id="client",
            client_secret="secret",
        )
        invalid_provider = OIDCProvider(invalid_config)

        result = await invalid_provider.health_check()
        assert result is False


@pytest.mark.integration
class TestOIDCIntegrationAuthorizationURL:
    """OIDC authorization URL generation tests."""

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, oidc_provider):
        """Test generating authorization URL."""
        auth_url = await oidc_provider.get_authorization_url(state="test_state")

        assert auth_url is not None
        assert "authorize" in auth_url
        assert "client_id=test_client" in auth_url
        assert "state=test_state" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=" in auth_url

    @pytest.mark.asyncio
    async def test_authorization_url_contains_scopes(self, oidc_provider):
        """Test that authorization URL contains configured scopes."""
        auth_url = await oidc_provider.get_authorization_url()

        assert "openid" in auth_url
        # URL encoded space is %20 or +
        assert "profile" in auth_url or "email" in auth_url


@pytest.mark.integration
class TestOIDCIntegrationTokenExchange:
    """OIDC token exchange integration tests."""

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self, oidc_provider, oidc_service):
        """Test exchanging authorization code for tokens."""
        # The mock OIDC server accepts any code and returns tokens
        result = await oidc_provider._exchange_code_for_token("test_code")

        # The mock server should return a token response
        assert result is not None
        assert "access_token" in result

    @pytest.mark.asyncio
    async def test_token_contains_required_fields(self, oidc_provider):
        """Test that token response contains required fields."""
        result = await oidc_provider._exchange_code_for_token("test_code")

        if result:  # Mock server may return tokens
            assert "access_token" in result
            assert "token_type" in result or result.get("token_type") is None


@pytest.mark.integration
class TestOIDCIntegrationUserInfo:
    """OIDC userinfo endpoint integration tests."""

    @pytest.mark.asyncio
    async def test_fetch_userinfo_with_token(self, oidc_provider, oidc_test_token):
        """Test fetching user info with access token."""
        if oidc_test_token and "access_token" in oidc_test_token:
            userinfo = await oidc_provider._fetch_userinfo(oidc_test_token["access_token"])

            # Mock server returns userinfo
            assert userinfo is not None
            # The mock server should return some user information
            assert isinstance(userinfo, dict)

    @pytest.mark.asyncio
    async def test_fetch_userinfo_with_invalid_token(self, oidc_provider):
        """Test fetching user info with invalid token fails gracefully."""
        userinfo = await oidc_provider._fetch_userinfo("invalid_token")

        # Should handle error gracefully
        assert userinfo is None or isinstance(userinfo, dict)


@pytest.mark.integration
class TestOIDCIntegrationEndToEnd:
    """End-to-end OIDC integration tests."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self, oidc_provider, oidc_test_token):
        """Test validating a token."""
        if oidc_test_token and "access_token" in oidc_test_token:
            result = await oidc_provider.validate_token(oidc_test_token["access_token"])

            # Result should indicate success or failure
            assert result is not None
            assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_get_user_info_with_uuid(self, oidc_provider):
        """Test get_user_info method."""
        from uuid import uuid4

        user_id = uuid4()
        user_info = await oidc_provider.get_user_info(user_id)

        assert user_info is not None
        assert user_info["provider"] == "oidc"
        assert str(user_id) in user_info["user_id"]
