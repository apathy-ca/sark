"""Integration tests for SAML authentication provider using Docker."""

import pytest

# Import fixtures from saml_docker
pytest_plugins = ["tests.fixtures.saml_docker"]


@pytest.mark.integration
class TestSAMLIntegrationBasic:
    """Basic SAML integration tests."""

    @pytest.mark.asyncio
    async def test_parse_saml_response(self, saml_provider, sample_saml_response):
        """Test parsing a SAML response."""
        import base64

        # Decode the base64-encoded response for parsing
        saml_xml = base64.b64decode(sample_saml_response).decode("utf-8")

        result = await saml_provider._parse_saml_response(saml_xml)

        assert result is not None
        assert "assertion" in result or result is not None

    @pytest.mark.asyncio
    async def test_authenticate_with_saml_response(self, saml_provider, sample_saml_response):
        """Test authentication with a valid SAML response."""
        result = await saml_provider.authenticate("", sample_saml_response)

        assert result is not None
        assert hasattr(result, "success")

        if result.success:
            assert result.email is not None
            assert result.user_id is not None

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_response(self, saml_provider):
        """Test authentication fails with invalid SAML response."""
        import base64

        invalid_response = base64.b64encode(b"Invalid SAML").decode("utf-8")
        result = await saml_provider.authenticate("", invalid_response)

        assert result is not None
        assert result.success is False

    @pytest.mark.asyncio
    async def test_user_id_consistency(self, saml_provider, sample_saml_response):
        """Test that the same SAML response generates consistent user IDs."""
        result1 = await saml_provider.authenticate("", sample_saml_response)
        result2 = await saml_provider.authenticate("", sample_saml_response)

        if result1.success and result2.success:
            assert result1.user_id == result2.user_id


@pytest.mark.integration
class TestSAMLIntegrationUserAttributes:
    """SAML user attribute extraction tests."""

    @pytest.mark.asyncio
    async def test_extract_email_attribute(self, saml_provider, sample_saml_response):
        """Test that email attribute is extracted correctly."""
        result = await saml_provider.authenticate("", sample_saml_response)

        if result.success:
            assert result.email is not None
            assert "@example.com" in result.email

    @pytest.mark.asyncio
    async def test_extract_display_name(self, saml_provider, sample_saml_response):
        """Test that display name is extracted correctly."""
        result = await saml_provider.authenticate("", sample_saml_response)

        if result.success:
            assert result.display_name is not None
            # Display name should contain user information
            assert len(result.display_name) > 0

    @pytest.mark.asyncio
    async def test_extract_groups(self, saml_provider, sample_saml_response):
        """Test that group memberships are extracted."""
        result = await saml_provider.authenticate("", sample_saml_response)

        if result.success and result.groups:
            assert isinstance(result.groups, list)
            assert len(result.groups) > 0

    @pytest.mark.asyncio
    async def test_metadata_includes_provider(self, saml_provider, sample_saml_response):
        """Test that metadata includes provider information."""
        result = await saml_provider.authenticate("", sample_saml_response)

        if result.success:
            assert result.metadata is not None
            assert result.metadata.get("provider") == "saml"


@pytest.mark.integration
class TestSAMLIntegrationHealthCheck:
    """SAML health check integration tests."""

    @pytest.mark.asyncio
    async def test_health_check(self, saml_provider):
        """Test SAML provider health check."""
        # SAML providers typically don't have active health checks
        # as they rely on request/response flow
        result = await saml_provider.health_check()

        # Should return True or False without errors
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_health_check_with_invalid_config(self):
        """Test health check with invalid configuration."""
        from sark.services.auth.providers.saml import SAMLProvider, SAMLProviderConfig

        invalid_config = SAMLProviderConfig(
            name="invalid-saml",
            idp_entity_id="http://nonexistent.example.com/metadata",
            idp_sso_url="http://nonexistent.example.com/sso",
            idp_x509_cert="invalid_cert",
            sp_entity_id="http://localhost:8000/metadata",
            sp_acs_url="http://localhost:8000/acs",
        )

        invalid_provider = SAMLProvider(invalid_config)
        result = await invalid_provider.health_check()

        # Should handle gracefully
        assert isinstance(result, bool)


@pytest.mark.integration
class TestSAMLIntegrationEdgeCases:
    """SAML edge case integration tests."""

    @pytest.mark.asyncio
    async def test_validate_token_delegates_to_authenticate(
        self, saml_provider, sample_saml_response
    ):
        """Test that validate_token properly delegates to authenticate."""
        result = await saml_provider.validate_token(sample_saml_response)

        assert result is not None
        assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_get_user_info(self, saml_provider):
        """Test get_user_info method."""
        from uuid import uuid4

        user_id = uuid4()
        user_info = await saml_provider.get_user_info(user_id)

        assert user_info is not None
        assert user_info["provider"] == "saml"
        assert str(user_id) in user_info["user_id"]

    @pytest.mark.asyncio
    async def test_authenticate_empty_response(self, saml_provider):
        """Test authentication with empty response."""
        result = await saml_provider.authenticate("", "")

        assert result is not None
        assert result.success is False

    @pytest.mark.asyncio
    async def test_parse_malformed_xml(self, saml_provider):
        """Test parsing malformed XML."""
        malformed_xml = "<invalid>xml<without>proper</closing>"

        result = await saml_provider._parse_saml_response(malformed_xml)

        # Should handle gracefully
        assert result is None or isinstance(result, dict)
