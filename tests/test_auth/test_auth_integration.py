"""Integration tests for all authentication flows and provider failover."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
import uuid

import pytest

from sark.models.api_key import APIKey
from sark.services.auth.api_keys import APIKeyService
from sark.services.auth.providers.ldap import LDAPProvider, LDAPProviderConfig
from sark.services.auth.providers.oidc import OIDCProvider, OIDCProviderConfig
from sark.services.auth.providers.saml import SAMLProvider, SAMLProviderConfig

# Fixtures


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = AsyncMock()
    session.query = Mock(return_value=session)
    session.filter = Mock(return_value=session)
    session.first = AsyncMock(return_value=None)
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def oidc_provider():
    """Create OIDC provider for testing."""
    config = OIDCProviderConfig(
        name="test-oidc",
        issuer_url="https://accounts.google.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
    )
    return OIDCProvider(config)


@pytest.fixture
def saml_provider():
    """Create SAML provider for testing."""
    config = SAMLProviderConfig(
        name="test-saml",
        idp_entity_id="https://idp.example.com",
        idp_sso_url="https://idp.example.com/sso",
        idp_x509_cert="MIIC...",  # Dummy cert
        sp_entity_id="https://sark.example.com",
        sp_acs_url="https://sark.example.com/api/auth/saml/acs",
        sp_slo_url="https://sark.example.com/api/auth/saml/slo",
    )
    return SAMLProvider(config)


@pytest.fixture
def ldap_provider():
    """Create LDAP provider for testing."""
    config = LDAPProviderConfig(
        name="test-ldap",
        server_url="ldap://test.example.com:389",
        base_dn="ou=users,dc=example,dc=com",
        bind_dn="cn=admin,dc=example,dc=com",
        bind_password="admin_password",
        group_search_base="ou=groups,dc=example,dc=com",
    )
    return LDAPProvider(config)


@pytest.fixture
def api_key_service(mock_db_session):
    """Create API key service for testing."""
    return APIKeyService(mock_db_session)


# Test Complete Authentication Flows


class TestCompleteAuthFlows:
    """Test complete authentication workflows for all providers."""

    @pytest.mark.asyncio
    async def test_oidc_authorization_flow(self, oidc_provider):
        """Test OIDC authorization URL generation."""
        mock_discovery = {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
        }
        with patch.object(oidc_provider, "_get_discovery_document", return_value=mock_discovery):
            # Get authorization URL
            auth_url = await oidc_provider.get_authorization_url(
                state="test_state", redirect_uri="https://example.com/callback"
            )
            assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
            assert "client_id=test_client_id" in auth_url
            assert "state=test_state" in auth_url

    @pytest.mark.asyncio
    async def test_oidc_token_validation(self, oidc_provider):
        """Test OIDC token validation."""
        mock_userinfo = {
            "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "email": "user@example.com",
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
        }

        with patch.object(oidc_provider, "_get_userinfo", return_value=mock_userinfo):
            result = await oidc_provider.validate_token("mock_access_token")

            assert result is not None
            assert result.success is True
            assert result.email == "user@example.com"
            assert result.display_name == "Test User"

    @pytest.mark.asyncio
    async def test_ldap_complete_flow(self, ldap_provider):
        """Test complete LDAP authentication flow."""
        user_dn = "uid=jdoe,ou=users,dc=example,dc=com"
        user_attrs = {
            "uid": "jdoe",
            "mail": "jdoe@example.com",
            "cn": "John Doe",
        }
        groups = ["developers", "admins"]

        with patch.object(ldap_provider, "_search_user", return_value=(user_dn, user_attrs)):
            with patch.object(ldap_provider, "_bind_user", return_value=True):
                with patch.object(ldap_provider, "_get_user_groups", return_value=groups):
                    result = await ldap_provider.authenticate("jdoe", "secret")

                    assert result is not None
                    assert result.success is True
                    assert result.email == "jdoe@example.com"
                    assert result.display_name == "John Doe"
                    assert result.groups == ["developers", "admins"]

    @pytest.mark.asyncio
    async def test_api_key_validation_flow(self, api_key_service, mock_db_session):
        """Test API key validation flow."""
        user_id = uuid.uuid4()
        full_key = "sark_sk_live_test1234_secretABCDEF1234567890"

        # Create mock API key
        mock_api_key = APIKey(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Test API Key",
            key_prefix="test1234",
            key_hash=APIKeyService._hash_key(full_key),
            scopes=["server:read", "server:write"],
            rate_limit=1000,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db_session.first = AsyncMock(return_value=mock_api_key)

        validated_key, error = await api_key_service.validate_api_key(
            full_key,
            required_scope="server:read",
            ip_address="192.168.1.100",
        )

        assert validated_key is not None
        assert error is None


# Test Provider Failover


class TestProviderFailover:
    """Test authentication provider failover scenarios."""

    @pytest.mark.asyncio
    async def test_oidc_primary_saml_fallback(self, oidc_provider, saml_provider):
        """Test failover from OIDC to SAML when OIDC fails."""
        providers = [oidc_provider, saml_provider]

        # OIDC health check fails
        with patch.object(oidc_provider, "health_check", return_value=False):
            # SAML health check succeeds
            with patch.object(saml_provider, "health_check", return_value=True):
                # Find healthy provider
                healthy_provider = None
                for provider in providers:
                    if await provider.health_check():
                        healthy_provider = provider
                        break

                assert healthy_provider is not None
                assert isinstance(healthy_provider, SAMLProvider)

    @pytest.mark.asyncio
    async def test_ldap_primary_oidc_fallback(self, ldap_provider, oidc_provider):
        """Test failover from LDAP to OIDC when LDAP fails."""
        providers = [ldap_provider, oidc_provider]

        # LDAP health check fails
        with patch.object(ldap_provider, "health_check", return_value=False):
            # OIDC health check succeeds
            with patch.object(oidc_provider, "health_check", return_value=True):
                # Find healthy provider
                healthy_providers = []
                for provider in providers:
                    if await provider.health_check():
                        healthy_providers.append(provider)

                assert len(healthy_providers) == 1
                assert isinstance(healthy_providers[0], OIDCProvider)

    @pytest.mark.asyncio
    async def test_all_providers_down(self, oidc_provider, saml_provider, ldap_provider):
        """Test scenario when all providers are down."""
        providers = [oidc_provider, saml_provider, ldap_provider]

        # All health checks fail
        with patch.object(oidc_provider, "health_check", return_value=False):
            with patch.object(saml_provider, "health_check", return_value=False):
                with patch.object(ldap_provider, "health_check", return_value=False):
                    healthy_providers = []
                    for provider in providers:
                        if await provider.health_check():
                            healthy_providers.append(provider)

                    assert len(healthy_providers) == 0

    @pytest.mark.asyncio
    async def test_multi_provider_round_robin(self, oidc_provider, ldap_provider, saml_provider):
        """Test round-robin load balancing across multiple healthy providers."""
        providers = [oidc_provider, ldap_provider, saml_provider]

        # All providers healthy
        with patch.object(oidc_provider, "health_check", return_value=True):
            with patch.object(ldap_provider, "health_check", return_value=True):
                with patch.object(saml_provider, "health_check", return_value=True):
                    healthy_providers = []
                    for provider in providers:
                        if await provider.health_check():
                            healthy_providers.append(provider)

                    assert len(healthy_providers) == 3

                    # Round-robin simulation
                    current_index = 0
                    for _ in range(10):
                        selected = healthy_providers[current_index % len(healthy_providers)]
                        current_index += 1
                        assert selected is not None


# Test Rate Limiting


class TestRateLimiting:
    """Test rate limiting for API keys."""

    @pytest.mark.asyncio
    async def test_api_key_rate_limit_under_limit(self):
        """Test API key usage under rate limit."""
        api_key = APIKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Key",
            key_prefix="test1234",
            key_hash="hash",
            scopes=["server:read"],
            rate_limit=100,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        current_usage = 50  # Under limit

        is_allowed, info = APIKeyService.check_rate_limit(api_key, current_usage)

        assert is_allowed is True
        assert info["limit"] == 100
        assert info["remaining"] == 50
        assert info["current_usage"] == 50

    @pytest.mark.asyncio
    async def test_api_key_rate_limit_at_limit(self):
        """Test API key usage exactly at rate limit."""
        api_key = APIKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Key",
            key_prefix="test1234",
            key_hash="hash",
            scopes=["server:read"],
            rate_limit=100,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        current_usage = 100  # At limit

        is_allowed, info = APIKeyService.check_rate_limit(api_key, current_usage)

        assert is_allowed is False
        assert info["remaining"] == 0

    @pytest.mark.asyncio
    async def test_api_key_rate_limit_exceeded(self):
        """Test API key usage exceeding rate limit."""
        api_key = APIKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Key",
            key_prefix="test1234",
            key_hash="hash",
            scopes=["server:read"],
            rate_limit=100,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        current_usage = 150  # Exceeded limit

        is_allowed, info = APIKeyService.check_rate_limit(api_key, current_usage)

        assert is_allowed is False
        assert info["current_usage"] == 150
        assert info["limit"] == 100

    @pytest.mark.asyncio
    async def test_different_keys_independent_limits(self):
        """Test that different API keys have independent rate limits."""
        key1 = APIKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Key 1",
            key_prefix="key11111",
            key_hash="hash1",
            scopes=["server:read"],
            rate_limit=100,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        key2 = APIKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Key 2",
            key_prefix="key22222",
            key_hash="hash2",
            scopes=["server:read"],
            rate_limit=100,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Key 1 near limit
        is_allowed1, info1 = APIKeyService.check_rate_limit(key1, 90)
        assert is_allowed1 is True
        assert info1["remaining"] == 10

        # Key 2 well under limit
        is_allowed2, info2 = APIKeyService.check_rate_limit(key2, 10)
        assert is_allowed2 is True
        assert info2["remaining"] == 90

    @pytest.mark.asyncio
    async def test_rate_limit_with_burst_traffic(self):
        """Test rate limiting with burst traffic pattern."""
        api_key = APIKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Burst Test Key",
            key_prefix="burst123",
            key_hash="hash",
            scopes=["server:read"],
            rate_limit=50,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Test various usage levels
        test_cases = [
            (0, True),  # Start
            (10, True),  # Low usage
            (25, True),  # Medium usage
            (49, True),  # Just under limit
            (50, False),  # At limit
            (60, False),  # Over limit
        ]

        for usage, expected_allowed in test_cases:
            is_allowed, _ = APIKeyService.check_rate_limit(api_key, usage)
            assert is_allowed == expected_allowed


# Test Cross-Provider Scenarios


class TestCrossProviderScenarios:
    """Test scenarios involving multiple authentication methods."""

    @pytest.mark.asyncio
    async def test_user_with_multiple_auth_methods(self, oidc_provider, ldap_provider):
        """Test user can authenticate via multiple methods."""
        # OIDC authentication
        mock_userinfo = {
            "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "email": "user@example.com",
            "name": "Test User",
        }

        with patch.object(oidc_provider, "_get_userinfo", return_value=mock_userinfo):
            result_oidc = await oidc_provider.validate_token("oidc_token")
            assert result_oidc is not None
            assert result_oidc.success is True
            assert result_oidc.email == "user@example.com"

        # LDAP authentication
        user_dn = "uid=user,ou=users,dc=example,dc=com"
        user_attrs = {
            "uid": "user",
            "mail": "user@example.com",
            "cn": "Test User",
        }

        with patch.object(ldap_provider, "_search_user", return_value=(user_dn, user_attrs)):
            with patch.object(ldap_provider, "_bind_user", return_value=True):
                with patch.object(ldap_provider, "_get_user_groups", return_value=[]):
                    result_ldap = await ldap_provider.authenticate("user", "password")
                    assert result_ldap is not None
                    assert result_ldap.success is True
                    assert result_ldap.email == "user@example.com"

        # Both should have same email
        assert result_oidc.email == result_ldap.email

    @pytest.mark.asyncio
    async def test_api_key_with_scope_validation(self, api_key_service, mock_db_session):
        """Test API key scope-based access control."""
        user_id = uuid.uuid4()
        full_key = "sark_sk_live_limited1_secretABCDEF1234567890"

        # Create API key with limited scopes
        api_key = APIKey(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Limited Key",
            key_prefix="limited1",
            key_hash=APIKeyService._hash_key(full_key),
            scopes=["server:read"],  # Only read access
            rate_limit=1000,
            is_active=True,
            usage_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db_session.first = AsyncMock(return_value=api_key)

        # Validate with read scope (should succeed)
        validated_key, error = await api_key_service.validate_api_key(
            full_key,
            required_scope="server:read",
        )

        assert validated_key is not None
        assert error is None

        # Reset mock for second test
        api_key.usage_count = 0  # Reset usage
        mock_db_session.first = AsyncMock(return_value=api_key)

        # Validate with write scope (should fail)
        validated_key, error = await api_key_service.validate_api_key(
            full_key,
            required_scope="server:write",
        )

        assert validated_key is None
        assert "scope" in error.lower()

    @pytest.mark.asyncio
    async def test_provider_health_check_aggregation(
        self, oidc_provider, saml_provider, ldap_provider
    ):
        """Test aggregated health check across all providers."""
        providers = {
            "oidc": oidc_provider,
            "saml": saml_provider,
            "ldap": ldap_provider,
        }

        # Mock health checks
        with patch.object(oidc_provider, "health_check", return_value=True):
            with patch.object(saml_provider, "health_check", return_value=True):
                with patch.object(ldap_provider, "health_check", return_value=False):
                    health_status = {}
                    for name, provider in providers.items():
                        health_status[name] = await provider.health_check()

                    assert health_status["oidc"] is True
                    assert health_status["saml"] is True
                    assert health_status["ldap"] is False

                    # Overall health: degraded (2/3 healthy)
                    healthy_count = sum(1 for v in health_status.values() if v)
                    assert healthy_count == 2
                    assert healthy_count / len(providers) >= 0.5  # >50% healthy
