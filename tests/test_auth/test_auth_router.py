"""Tests for unified authentication router."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sark.api.routers.auth import router
from sark.models.session import Session
from sark.services.auth.providers.base import UserInfo
from sark.config.settings import Settings


# Test App Setup


@pytest.fixture
def app():
    """Create FastAPI test app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock(spec=Settings)
    settings.oidc_enabled = True
    settings.oidc_provider = "google"
    settings.oidc_client_id = "test_client_id"
    settings.oidc_client_secret = "test_secret"
    settings.oidc_issuer = None
    settings.oidc_azure_tenant = None
    settings.oidc_okta_domain = None
    settings.saml_enabled = True
    settings.saml_sp_entity_id = "https://sark.example.com"
    settings.saml_sp_acs_url = "https://sark.example.com/api/auth/saml/acs"
    settings.saml_sp_sls_url = "https://sark.example.com/api/auth/saml/slo"
    settings.saml_idp_entity_id = "https://idp.example.com"
    settings.saml_idp_sso_url = "https://idp.example.com/sso"
    settings.ldap_enabled = True
    settings.ldap_server = "ldap://test.example.com"
    settings.ldap_bind_dn = "cn=admin,dc=example,dc=com"
    settings.ldap_bind_password = "password"
    settings.ldap_user_base_dn = "ou=users,dc=example,dc=com"
    settings.ldap_group_base_dn = "ou=groups,dc=example,dc=com"
    settings.session_timeout_seconds = 3600
    return settings


@pytest.fixture
def mock_session_service():
    """Create mock session service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_session():
    """Create mock session."""
    return Session(
        session_id=str(uuid.uuid4()),
        user_id=uuid.uuid4(),
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        last_activity=datetime.utcnow(),
        ip_address="192.168.1.100",
        user_agent="Test Agent",
        metadata={"provider": "test"},
    )


# Test Provider Listing


class TestListProviders:
    """Test provider listing endpoint."""

    def test_list_providers_all_enabled(self, client, app, mock_settings):
        """Test listing providers when all are enabled."""
        from sark.api.routers.auth import get_settings

        app.dependency_overrides[get_settings] = lambda: mock_settings

        response = client.get("/api/auth/providers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4  # OIDC, SAML, LDAP, API Key
        assert len(data["providers"]) == 4

        # Check provider types
        provider_types = {p["type"] for p in data["providers"]}
        assert provider_types == {"oidc", "saml", "ldap", "api_key"}

        # Check OIDC provider details
        oidc_provider = next(p for p in data["providers"] if p["type"] == "oidc")
        assert oidc_provider["id"] == "oidc"
        assert oidc_provider["enabled"] is True
        assert oidc_provider["authorization_url"] == "/api/auth/oidc/authorize"

    def test_list_providers_partial_enabled(self, client, app, mock_settings):
        """Test listing providers when only some are enabled."""
        mock_settings.oidc_enabled = False
        mock_settings.saml_enabled = False

        from sark.api.routers.auth import get_settings

        app.dependency_overrides[get_settings] = lambda: mock_settings

        response = client.get("/api/auth/providers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # LDAP, API Key
        provider_types = {p["type"] for p in data["providers"]}
        assert provider_types == {"ldap", "api_key"}


# Test Login


class TestLogin:
    """Test login endpoint."""

    def test_login_ldap_success(
        self, client, app, mock_settings, mock_session_service, mock_session
    ):
        """Test successful LDAP login."""
        from sark.api.routers.auth import get_settings, get_session_service

        mock_user_info = UserInfo(
            user_id="uid=jdoe,ou=users,dc=example,dc=com",
            email="jdoe@example.com",
            name="John Doe",
        )

        mock_session_service.create_session.return_value = (mock_session, mock_session.session_id)

        app.dependency_overrides[get_settings] = lambda: mock_settings
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        with patch("sark.api.routers.auth.LDAPProvider") as mock_ldap_class:
            mock_ldap_instance = AsyncMock()
            mock_ldap_instance.authenticate.return_value = mock_user_info
            mock_ldap_class.return_value = mock_ldap_instance

            response = client.post(
                "/api/auth/login",
                json={
                    "provider": "ldap",
                    "username": "jdoe",
                    "password": "secret",
                    "remember_me": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["session"] is not None
            assert data["user_id"] is not None

    def test_login_ldap_invalid_credentials(
        self, client, app, mock_settings, mock_session_service
    ):
        """Test LDAP login with invalid credentials."""
        from sark.api.routers.auth import get_settings, get_session_service

        app.dependency_overrides[get_settings] = lambda: mock_settings
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        with patch("sark.api.routers.auth.LDAPProvider") as mock_ldap_class:
            mock_ldap_instance = AsyncMock()
            mock_ldap_instance.authenticate.return_value = None
            mock_ldap_class.return_value = mock_ldap_instance

            response = client.post(
                "/api/auth/login",
                json={
                    "provider": "ldap",
                    "username": "jdoe",
                    "password": "wrong",
                },
            )

            assert response.status_code == 401

    def test_login_ldap_disabled(self, client, app, mock_settings, mock_session_service):
        """Test login when LDAP is disabled."""
        from sark.api.routers.auth import get_settings, get_session_service

        mock_settings.ldap_enabled = False

        app.dependency_overrides[get_settings] = lambda: mock_settings
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        response = client.post(
            "/api/auth/login",
            json={
                "provider": "ldap",
                "username": "jdoe",
                "password": "secret",
            },
        )

        assert response.status_code == 400

    def test_login_unsupported_provider(
        self, client, app, mock_settings, mock_session_service
    ):
        """Test login with unsupported provider."""
        from sark.api.routers.auth import get_settings, get_session_service

        app.dependency_overrides[get_settings] = lambda: mock_settings
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        response = client.post(
            "/api/auth/login",
            json={
                "provider": "unknown",
                "username": "test",
                "password": "test",
            },
        )

        assert response.status_code == 400


# Test OIDC Authorization


class TestOIDCAuthorize:
    """Test OIDC authorization endpoint."""

    def test_oidc_authorize_success(self, client, app, mock_settings):
        """Test OIDC authorization URL generation."""
        from sark.api.routers.auth import get_settings

        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch("sark.api.routers.auth.OIDCProvider") as mock_oidc_class:
            mock_oidc_instance = AsyncMock()
            mock_oidc_instance.get_authorization_url.return_value = "https://accounts.google.com/auth"
            mock_oidc_class.return_value = mock_oidc_instance

            response = client.get(
                "/api/auth/oidc/authorize",
                params={
                    "redirect_uri": "https://app.example.com/callback",
                    "state": "test_state",
                },
                follow_redirects=False,
            )

            assert response.status_code == 307
            assert "Location" in response.headers

    def test_oidc_authorize_disabled(self, client, app, mock_settings):
        """Test OIDC authorization when disabled."""
        from sark.api.routers.auth import get_settings

        mock_settings.oidc_enabled = False

        app.dependency_overrides[get_settings] = lambda: mock_settings

        response = client.get(
            "/api/auth/oidc/authorize",
            params={"redirect_uri": "https://app.example.com/callback"},
        )

        assert response.status_code == 400


# Test OIDC Callback


class TestOIDCCallback:
    """Test OIDC callback endpoint."""

    def test_oidc_callback_success(
        self, client, app, mock_settings, mock_session_service, mock_session
    ):
        """Test successful OIDC callback."""
        from sark.api.routers.auth import get_settings, get_session_service

        mock_user_info = UserInfo(
            user_id="google_user123",
            email="user@example.com",
            name="Test User",
        )

        mock_session_service.create_session.return_value = (mock_session, mock_session.session_id)

        app.dependency_overrides[get_settings] = lambda: mock_settings
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        with patch("sark.api.routers.auth.OIDCProvider") as mock_oidc_class:
            mock_oidc_instance = AsyncMock()
            mock_oidc_instance.handle_callback.return_value = {"access_token": "test_token"}
            mock_oidc_instance.validate_token.return_value = mock_user_info
            mock_oidc_class.return_value = mock_oidc_instance

            response = client.get(
                "/api/auth/oidc/callback",
                params={"code": "auth_code", "state": "test_state"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["session"] is not None

    def test_oidc_callback_auth_failure(
        self, client, app, mock_settings, mock_session_service
    ):
        """Test OIDC callback when authentication fails."""
        from sark.api.routers.auth import get_settings, get_session_service

        app.dependency_overrides[get_settings] = lambda: mock_settings
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        with patch("sark.api.routers.auth.OIDCProvider") as mock_oidc_class:
            mock_oidc_instance = AsyncMock()
            mock_oidc_instance.handle_callback.return_value = None
            mock_oidc_class.return_value = mock_oidc_instance

            response = client.get(
                "/api/auth/oidc/callback",
                params={"code": "bad_code", "state": "test_state"},
            )

            assert response.status_code == 401


# Test Auth Status


class TestAuthStatus:
    """Test authentication status endpoint."""

    def test_auth_status_authenticated(self, client, app, mock_session):
        """Test auth status when authenticated."""
        from sark.api.routers.auth import get_current_session

        app.dependency_overrides[get_current_session] = lambda: mock_session

        response = client.get("/api/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] is not None
        assert data["session_id"] == mock_session.session_id

    def test_auth_status_not_authenticated(self, client, app):
        """Test auth status when not authenticated."""
        from sark.api.routers.auth import get_current_session

        app.dependency_overrides[get_current_session] = lambda: None

        response = client.get("/api/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user_id"] is None
        assert data["session_id"] is None


# Test Logout


class TestLogout:
    """Test logout endpoints."""

    def test_logout_success(self, client, app, mock_session, mock_session_service):
        """Test successful logout."""
        from sark.api.routers.auth import get_current_session, get_session_service, require_auth

        app.dependency_overrides[get_current_session] = lambda: mock_session
        app.dependency_overrides[require_auth] = lambda: mock_session
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sessions_invalidated"] == 1

        mock_session_service.invalidate_session.assert_called_once_with(
            mock_session.session_id
        )

    def test_logout_not_authenticated(self, client, app):
        """Test logout when not authenticated."""
        from sark.api.routers.auth import get_current_session

        app.dependency_overrides[get_current_session] = lambda: None

        response = client.post("/api/auth/logout")

        assert response.status_code == 401

    def test_logout_all_success(self, client, app, mock_session, mock_session_service):
        """Test logout from all devices."""
        from sark.api.routers.auth import get_current_session, get_session_service, require_auth

        mock_session_service.invalidate_all_user_sessions.return_value = 3

        app.dependency_overrides[get_current_session] = lambda: mock_session
        app.dependency_overrides[require_auth] = lambda: mock_session
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        response = client.post("/api/auth/logout/all")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sessions_invalidated"] == 3

        mock_session_service.invalidate_all_user_sessions.assert_called_once_with(
            mock_session.user_id
        )


# Test Health Check


class TestAuthHealth:
    """Test authentication health check."""

    def test_health_check_all_healthy(self, client, app, mock_settings):
        """Test health check when all providers are healthy."""
        from sark.api.routers.auth import get_settings

        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch("sark.api.routers.auth.OIDCProvider") as mock_oidc_class:
            with patch("sark.api.routers.auth.SAMLProvider") as mock_saml_class:
                with patch("sark.api.routers.auth.LDAPProvider") as mock_ldap_class:
                    mock_oidc = AsyncMock()
                    mock_oidc.health_check.return_value = True
                    mock_oidc_class.return_value = mock_oidc

                    mock_saml = AsyncMock()
                    mock_saml.health_check.return_value = True
                    mock_saml_class.return_value = mock_saml

                    mock_ldap = AsyncMock()
                    mock_ldap.health_check.return_value = True
                    mock_ldap_class.return_value = mock_ldap

                    response = client.get("/api/auth/health")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert data["healthy"] == 3
                    assert data["total"] == 3

    def test_health_check_degraded(self, client, app, mock_settings):
        """Test health check when some providers are unhealthy."""
        from sark.api.routers.auth import get_settings

        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch("sark.api.routers.auth.OIDCProvider") as mock_oidc_class:
            with patch("sark.api.routers.auth.SAMLProvider") as mock_saml_class:
                with patch("sark.api.routers.auth.LDAPProvider") as mock_ldap_class:
                    mock_oidc = AsyncMock()
                    mock_oidc.health_check.return_value = True
                    mock_oidc_class.return_value = mock_oidc

                    mock_saml = AsyncMock()
                    mock_saml.health_check.return_value = False
                    mock_saml_class.return_value = mock_saml

                    mock_ldap = AsyncMock()
                    mock_ldap.health_check.return_value = True
                    mock_ldap_class.return_value = mock_ldap

                    response = client.get("/api/auth/health")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "degraded"
                    assert data["healthy"] == 2
                    assert data["total"] == 3
