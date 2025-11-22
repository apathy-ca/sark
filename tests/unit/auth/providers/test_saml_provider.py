"""Comprehensive tests for SAML authentication provider."""

import base64
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid5

import pytest

from sark.services.auth.providers.saml import SAMLProvider, SAMLProviderConfig


class TestSAMLProviderConfig:
    """Test suite for SAMLProviderConfig."""

    def test_config_initialization(self):
        """Test SAML config initialization with required fields."""
        config = SAMLProviderConfig(
            name="test-saml",
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_x509_cert="test_cert",
            sp_entity_id="https://sp.example.com",
            sp_acs_url="https://sp.example.com/acs",
        )

        assert config.name == "test-saml"
        assert config.idp_entity_id == "https://idp.example.com"
        assert config.idp_sso_url == "https://idp.example.com/sso"
        assert config.sp_entity_id == "https://sp.example.com"
        assert config.sp_acs_url == "https://sp.example.com/acs"
        assert config.enabled is True

    def test_config_with_slo(self):
        """Test SAML config with Single Logout URLs."""
        config = SAMLProviderConfig(
            name="test-saml",
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_slo_url="https://idp.example.com/slo",
            idp_x509_cert="test_cert",
            sp_entity_id="https://sp.example.com",
            sp_acs_url="https://sp.example.com/acs",
            sp_slo_url="https://sp.example.com/slo",
        )

        assert config.idp_slo_url == "https://idp.example.com/slo"
        assert config.sp_slo_url == "https://sp.example.com/slo"

    def test_config_with_custom_name_id_format(self):
        """Test SAML config with custom NameID format."""
        config = SAMLProviderConfig(
            name="test-saml",
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_x509_cert="test_cert",
            sp_entity_id="https://sp.example.com",
            sp_acs_url="https://sp.example.com/acs",
            name_id_format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
        )

        assert config.name_id_format == "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"


class TestSAMLProvider:
    """Test suite for SAMLProvider."""

    @pytest.fixture
    def config(self):
        """Create test SAML config."""
        return SAMLProviderConfig(
            name="test-saml",
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_x509_cert="test_cert",
            sp_entity_id="https://sp.example.com",
            sp_acs_url="https://sp.example.com/acs",
        )

    @pytest.fixture
    def provider(self, config):
        """Create SAML provider instance."""
        return SAMLProvider(config)

    @pytest.fixture
    def valid_saml_response(self):
        """Create a valid SAML response XML."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                ID="_test_response_id"
                Version="2.0">
    <saml:Assertion ID="_test_assertion_id" Version="2.0">
        <saml:Subject>
            <saml:NameID>test@example.com</saml:NameID>
        </saml:Subject>
        <saml:AuthnStatement SessionIndex="test_session_123"/>
        <saml:AttributeStatement>
            <saml:Attribute Name="email">
                <saml:AttributeValue>test@example.com</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="displayName">
                <saml:AttributeValue>Test User</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="groups">
                <saml:AttributeValue>admin</saml:AttributeValue>
                <saml:AttributeValue>developers</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>"""

    # ===== SAML Response Parsing Tests =====

    @pytest.mark.asyncio
    async def test_parse_saml_response_valid(self, provider, valid_saml_response):
        """Test parsing valid SAML response."""
        result = await provider._parse_saml_response(valid_saml_response)

        assert result is not None
        assert "assertion" in result
        assert "namespaces" in result

    @pytest.mark.asyncio
    async def test_parse_saml_response_invalid_xml(self, provider):
        """Test parsing invalid XML returns None."""
        invalid_xml = "This is not valid XML"

        result = await provider._parse_saml_response(invalid_xml)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_saml_response_no_assertion(self, provider):
        """Test parsing SAML response without assertion returns None."""
        no_assertion = """<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                ID="_test_id" Version="2.0">
</samlp:Response>"""

        result = await provider._parse_saml_response(no_assertion)

        assert result is None

    # ===== User Info Extraction Tests =====

    @pytest.mark.asyncio
    async def test_extract_user_info(self, provider, valid_saml_response):
        """Test extracting user info from SAML assertion."""
        assertion_data = await provider._parse_saml_response(valid_saml_response)

        user_info = provider._extract_user_info(assertion_data)

        assert user_info["name_id"] == "test@example.com"
        assert user_info["session_index"] == "test_session_123"
        assert user_info["email"] == "test@example.com"
        assert user_info["displayName"] == "Test User"
        assert user_info["groups"] == ["admin", "developers"]

    @pytest.mark.asyncio
    async def test_extract_user_info_single_value_attribute(self, provider):
        """Test extracting single-value attributes."""
        saml_response = """<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
    <saml:Assertion>
        <saml:Subject>
            <saml:NameID>user@example.com</saml:NameID>
        </saml:Subject>
        <saml:AttributeStatement>
            <saml:Attribute Name="department">
                <saml:AttributeValue>Engineering</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>"""

        assertion_data = await provider._parse_saml_response(saml_response)
        user_info = provider._extract_user_info(assertion_data)

        assert user_info["department"] == "Engineering"

    # ===== Authentication Tests =====

    @pytest.mark.asyncio
    async def test_authenticate_success(self, provider, valid_saml_response):
        """Test successful SAML authentication."""
        encoded_response = base64.b64encode(valid_saml_response.encode("utf-8")).decode("utf-8")

        result = await provider.authenticate("", encoded_response)

        assert result.success is True
        assert isinstance(result.user_id, UUID)
        assert result.email == "test@example.com"
        assert result.display_name == "Test User"
        assert result.groups == ["admin", "developers"]
        assert result.metadata["provider"] == "saml"
        assert result.metadata["name_id"] == "test@example.com"
        assert result.metadata["session_index"] == "test_session_123"

    @pytest.mark.asyncio
    async def test_authenticate_uuid_generation(self, provider, valid_saml_response):
        """Test that user UUID is stable for same NameID."""
        encoded_response = base64.b64encode(valid_saml_response.encode("utf-8")).decode("utf-8")

        result1 = await provider.authenticate("", encoded_response)
        result2 = await provider.authenticate("", encoded_response)

        assert result1.user_id == result2.user_id

    @pytest.mark.asyncio
    async def test_authenticate_invalid_assertion(self, provider):
        """Test authentication fails with invalid assertion."""
        invalid_response = base64.b64encode(b"Invalid SAML").decode("utf-8")

        result = await provider.authenticate("", invalid_response)

        assert result.success is False
        assert "Invalid or missing SAML assertion" in result.error_message

    @pytest.mark.asyncio
    async def test_authenticate_exception_handling(self, provider):
        """Test authentication handles exceptions gracefully."""
        # Not base64 encoded
        invalid_credential = "not-base64-encoded"

        result = await provider.authenticate("", invalid_credential)

        assert result.success is False
        assert result.error_message is not None

    # ===== Token Validation Tests =====

    @pytest.mark.asyncio
    async def test_validate_token(self, provider, valid_saml_response):
        """Test validate_token delegates to authenticate."""
        encoded_response = base64.b64encode(valid_saml_response.encode("utf-8")).decode("utf-8")

        result = await provider.validate_token(encoded_response)

        assert result.success is True
        assert result.email == "test@example.com"

    # ===== Get User Info Tests =====

    @pytest.mark.asyncio
    async def test_get_user_info(self, provider):
        """Test get_user_info returns basic info."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await provider.get_user_info(user_id)

        assert result["user_id"] == str(user_id)
        assert result["provider"] == "saml"

    # ===== AuthnRequest Generation Tests =====

    def test_generate_authn_request(self, provider):
        """Test generating SAML AuthnRequest."""
        authn_request = provider.generate_authn_request()

        # Should be base64 encoded
        assert isinstance(authn_request, str)
        assert len(authn_request) > 0

        # Decode and verify structure
        decoded = base64.b64decode(authn_request).decode("utf-8")
        assert "AuthnRequest" in decoded
        assert provider.config.sp_entity_id in decoded
        assert provider.config.idp_sso_url in decoded
        assert provider.config.sp_acs_url in decoded

    def test_generate_authn_request_with_relay_state(self, provider):
        """Test generating AuthnRequest with relay state."""
        authn_request = provider.generate_authn_request(relay_state="/dashboard")

        # Relay state is typically passed separately, not in the request itself
        assert isinstance(authn_request, str)

    def test_generate_authn_request_unique_ids(self, provider):
        """Test each AuthnRequest has unique ID."""
        request1 = provider.generate_authn_request()
        request2 = provider.generate_authn_request()

        decoded1 = base64.b64decode(request1).decode("utf-8")
        decoded2 = base64.b64decode(request2).decode("utf-8")

        # Extract IDs (they should be different)
        assert decoded1 != decoded2

    # ===== Health Check Tests =====

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test health check succeeds with valid configuration."""
        result = await provider.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_disabled(self, provider):
        """Test health check fails when disabled."""
        provider.config.enabled = False

        result = await provider.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_missing_config(self, provider):
        """Test health check fails with missing required config."""
        provider.config.idp_entity_id = ""

        result = await provider.health_check()

        assert result is False
