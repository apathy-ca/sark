"""Security tests for CSRF token validation middleware."""

import secrets
from unittest.mock import MagicMock

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from sark.api.middleware.security_headers import CSRFProtectionMiddleware


class TestCSRFValidation:
    """Test suite for CSRF token validation."""

    @pytest.fixture
    def middleware(self):
        """Create CSRF middleware instance."""
        app = Starlette()
        return CSRFProtectionMiddleware(app)

    @pytest.fixture
    def app(self):
        """Create test app with CSRF middleware."""

        async def homepage(request: Request):
            return PlainTextResponse("OK")

        async def protected_endpoint(request: Request):
            return PlainTextResponse("Protected")

        app = Starlette(
            routes=[],
            middleware=[
                Middleware(CSRFProtectionMiddleware),
            ],
        )

        # Add routes
        app.add_route("/", homepage, methods=["GET"])
        app.add_route("/api/protected", protected_endpoint, methods=["POST", "PUT"])
        app.add_route("/health", homepage, methods=["GET", "POST"])

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_csrf_token_generation(self, middleware):
        """Test CSRF token generation produces cryptographically secure tokens."""
        token1 = middleware.generate_csrf_token()
        token2 = middleware.generate_csrf_token()

        # Tokens should be strings
        assert isinstance(token1, str)
        assert isinstance(token2, str)

        # Tokens should be unique
        assert token1 != token2

        # Tokens should be long enough (32 bytes = ~43 chars in base64)
        assert len(token1) >= 40
        assert len(token2) >= 40

    def test_csrf_token_validation_success(self, middleware):
        """Test successful CSRF token validation with matching tokens."""
        token = middleware.generate_csrf_token()

        # Mock request with session
        request = MagicMock(spec=Request)
        request.headers.get.return_value = token
        request.session = {"csrf_token": token}

        assert middleware._validate_csrf_token(request) is True

    def test_csrf_token_missing_header(self, middleware):
        """Test CSRF validation fails when header is missing."""
        # Mock request with session but no header
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        request.session = {"csrf_token": "valid-token"}

        assert middleware._validate_csrf_token(request) is False

    def test_csrf_token_missing_session(self, middleware):
        """Test CSRF validation fails when session token is missing."""
        # Mock request with header but no session token
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "token-from-header"
        request.session = {}

        assert middleware._validate_csrf_token(request) is False

    def test_csrf_token_mismatch(self, middleware):
        """Test CSRF validation fails when tokens don't match."""
        # Mock request with different tokens
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "token1"
        request.session = {"csrf_token": "token2"}

        assert middleware._validate_csrf_token(request) is False

    def test_csrf_token_timing_attack_resistance(self, middleware):
        """Test that token comparison uses constant-time algorithm."""
        import inspect

        source = inspect.getsource(middleware._validate_csrf_token)

        # Verify secrets.compare_digest is used (not ==)
        assert "secrets.compare_digest" in source

    def test_csrf_no_session_fallback(self, middleware):
        """Test CSRF validation when session is not available."""
        # Mock request without session attribute
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "some-token"
        delattr(request, "session")  # Remove session attribute

        # Should fall back to checking header presence only
        result = middleware._validate_csrf_token(request)
        assert result is True

    def test_csrf_no_session_no_header(self, middleware):
        """Test CSRF validation fails when no session and no header."""
        # Mock request without session attribute and no header
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        delattr(request, "session")  # Remove session attribute

        result = middleware._validate_csrf_token(request)
        assert result is False

    def test_csrf_exempt_paths(self, middleware):
        """Test that exempt paths bypass CSRF validation."""
        # Check default exempt paths
        assert "/health" in middleware.exempt_paths
        assert "/metrics" in middleware.exempt_paths
        assert "/docs" in middleware.exempt_paths

    def test_csrf_protected_methods(self, middleware):
        """Test that POST, PUT, PATCH, DELETE are protected."""
        assert "POST" in middleware.protected_methods
        assert "PUT" in middleware.protected_methods
        assert "PATCH" in middleware.protected_methods
        assert "DELETE" in middleware.protected_methods

    def test_csrf_safe_methods_allowed(self, middleware):
        """Test that GET, HEAD, OPTIONS are not protected."""
        assert "GET" not in middleware.protected_methods
        assert "HEAD" not in middleware.protected_methods
        assert "OPTIONS" not in middleware.protected_methods

    def test_get_request_bypasses_csrf(self, client):
        """Test that GET requests bypass CSRF validation."""
        response = client.get("/")
        assert response.status_code == 200

    def test_post_without_token_fails(self, client):
        """Test that POST without CSRF token returns 403."""
        response = client.post("/api/protected")
        assert response.status_code == 403
        assert "CSRF token invalid" in response.json()["error"]

    def test_post_to_exempt_path_allowed(self, client):
        """Test that POST to exempt paths bypasses CSRF."""
        response = client.post("/health")
        assert response.status_code == 200

    def test_constant_time_comparison_prevents_timing_attacks(self, middleware):
        """Test that different length tokens still use constant-time comparison."""
        short_token = "short"
        long_token = "a" * 100

        request = MagicMock(spec=Request)
        request.headers.get.return_value = short_token
        request.session = {"csrf_token": long_token}

        # Should return False, but importantly, should not crash
        # and should use constant-time comparison
        assert middleware._validate_csrf_token(request) is False

    def test_csrf_token_entropy(self, middleware):
        """Test that generated tokens have sufficient entropy."""
        # Generate multiple tokens and check for patterns
        tokens = [middleware.generate_csrf_token() for _ in range(100)]

        # All tokens should be unique
        assert len(set(tokens)) == 100

        # Tokens should contain varied characters (URL-safe base64)
        all_chars = "".join(tokens)
        unique_chars = set(all_chars)

        # URL-safe base64 uses A-Z, a-z, 0-9, -, _
        # Should have good variety
        assert len(unique_chars) >= 20

    def test_csrf_header_name_customizable(self):
        """Test that CSRF header name can be customized."""
        app = Starlette()
        custom_middleware = CSRFProtectionMiddleware(
            app, csrf_header_name="X-Custom-CSRF-Token"
        )

        assert custom_middleware.csrf_header_name == "X-Custom-CSRF-Token"

    def test_csrf_custom_exempt_paths(self):
        """Test that custom exempt paths can be configured."""
        app = Starlette()
        custom_middleware = CSRFProtectionMiddleware(
            app, exempt_paths=["/custom/path", "/another/path"]
        )

        assert "/custom/path" in custom_middleware.exempt_paths
        assert "/another/path" in custom_middleware.exempt_paths

    def test_empty_token_fails_validation(self, middleware):
        """Test that empty tokens fail validation."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = ""
        request.session = {"csrf_token": "valid-token"}

        assert middleware._validate_csrf_token(request) is False

    def test_whitespace_token_fails_validation(self, middleware):
        """Test that whitespace-only tokens fail validation."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "   "
        request.session = {"csrf_token": "valid-token"}

        assert middleware._validate_csrf_token(request) is False
