"""Unit tests for JWT authentication middleware."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import jwt
import pytest

from sark.api.middleware.auth import AuthenticationError, AuthMiddleware
from sark.config import Settings


@pytest.fixture
def settings_hs256():
    """Settings fixture for HS256 algorithm."""
    return Settings(
        secret_key="test-secret-key-that-is-at-least-32-characters-long",
        jwt_algorithm="HS256",
        jwt_expiration_minutes=60,
        postgres_password="test",
        timescale_password="test",
    )


@pytest.fixture
def settings_rs256():
    """Settings fixture for RS256 algorithm."""
    # RSA key pair for testing (DO NOT USE IN PRODUCTION)

    public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyGvM8RQ8LoqsZVGcOVJP
zT1+6MdGStYpM6n+VcfkBx6HzLOpkT9fQY+X72rGCHkX+kc2qGVj9wqNyBz3bAGa
H9MrT8FBzqOD9w4YL8wjZAGGGGJ8AqL1OGH0yA6Wl9N8XH8YzQc9lF+4fJy8dU7r
GBJJ8wGZ9bGJT8vZfqOZfqOZfqOZvZyGZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZ
fqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZ
fqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZ
fqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfqOZfQIDAQAB
-----END PUBLIC KEY-----"""

    return Settings(
        secret_key="test-secret-key-that-is-at-least-32-characters-long",
        jwt_algorithm="RS256",
        jwt_public_key=public_key,
        jwt_expiration_minutes=60,
        postgres_password="test",
        timescale_password="test",
    )


def create_test_token(settings: Settings, **claims):
    """Helper to create test JWT tokens."""
    # Default claims
    now = datetime.now(UTC)
    default_claims = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"],
        "teams": ["engineering"],
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiration_minutes),
    }

    # Merge with provided claims
    token_claims = {**default_claims, **claims}

    # Encode token
    if settings.jwt_algorithm == "RS256":
        # For testing, we'll use HS256 since we don't have a real private key
        # In production, this would use the private key
        key = settings.secret_key
        algorithm = "HS256"
    else:
        key = settings.jwt_secret_key or settings.secret_key
        algorithm = settings.jwt_algorithm

    return jwt.encode(token_claims, key, algorithm=algorithm)


class TestAuthMiddleware:
    """Test suite for AuthMiddleware."""

    def test_middleware_initialization_hs256(self, settings_hs256):
        """Test middleware initializes correctly with HS256."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        assert middleware.settings.jwt_algorithm == "HS256"
        assert middleware.jwt_key == settings_hs256.secret_key

    def test_middleware_initialization_rs256_without_public_key(self):
        """Test middleware raises error when RS256 used without public key."""
        settings = Settings(
            secret_key="test-secret-key-that-is-at-least-32-characters-long",
            jwt_algorithm="RS256",
            jwt_public_key=None,
            postgres_password="test",
            timescale_password="test",
        )

        app = FastAPI()
        with pytest.raises(ValueError, match="JWT_PUBLIC_KEY must be set"):
            AuthMiddleware(app, settings=settings)

    def test_is_public_path(self, settings_hs256):
        """Test public path detection."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Exact matches
        assert middleware._is_public_path("/health")
        assert middleware._is_public_path("/metrics")
        assert middleware._is_public_path("/docs")

        # Prefix matches
        assert middleware._is_public_path("/health/live")
        assert middleware._is_public_path("/health/ready")

        # Not public
        assert not middleware._is_public_path("/api/v1/servers")
        assert not middleware._is_public_path("/api/v1/policy")

    def test_extract_token_success(self, settings_hs256):
        """Test successful token extraction."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Mock request with valid Authorization header
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "Bearer test-token-123"

        token = middleware._extract_token(request)
        assert token == "test-token-123"

    def test_extract_token_missing_header(self, settings_hs256):
        """Test token extraction with missing Authorization header."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Mock request without Authorization header
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None

        token = middleware._extract_token(request)
        assert token is None

    def test_extract_token_invalid_format(self, settings_hs256):
        """Test token extraction with invalid header format."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Mock request with invalid format
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "InvalidFormat"

        with pytest.raises(AuthenticationError, match="Invalid authorization header format"):
            middleware._extract_token(request)

    def test_extract_token_wrong_scheme(self, settings_hs256):
        """Test token extraction with wrong authorization scheme."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Mock request with wrong scheme
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "Basic dGVzdDp0ZXN0"

        with pytest.raises(AuthenticationError, match="Invalid authorization scheme"):
            middleware._extract_token(request)

    def test_decode_token_valid(self, settings_hs256):
        """Test decoding valid JWT token."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Create valid token
        token = create_test_token(settings_hs256)

        # Decode token
        payload = middleware._decode_token(token)

        assert payload["sub"] == "test-user-123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_decode_token_expired(self, settings_hs256):
        """Test decoding expired token."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Create expired token
        now = datetime.now(UTC)
        expired_token = create_test_token(
            settings_hs256,
            exp=now - timedelta(minutes=10),  # Expired 10 minutes ago
        )

        with pytest.raises(AuthenticationError, match="Token has expired"):
            middleware._decode_token(expired_token)

    def test_decode_token_invalid_signature(self, settings_hs256):
        """Test decoding token with invalid signature."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        # Create token with wrong key
        wrong_settings = Settings(
            secret_key="wrong-key-that-is-at-least-32-characters-longgg",
            jwt_algorithm="HS256",
            postgres_password="test",
            timescale_password="test",
        )
        invalid_token = create_test_token(wrong_settings)

        with pytest.raises(AuthenticationError, match="Invalid token"):
            middleware._decode_token(invalid_token)

    def test_extract_user_context(self, settings_hs256):
        """Test user context extraction from JWT payload."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        payload = {
            "sub": "user-456",
            "email": "alice@example.com",
            "name": "Alice Smith",
            "roles": ["admin", "user"],
            "groups": ["security", "engineering"],
            "permissions": ["servers:read", "servers:write"],
        }

        context = middleware._extract_user_context(payload)

        assert context["user_id"] == "user-456"
        assert context["email"] == "alice@example.com"
        assert context["name"] == "Alice Smith"
        assert context["roles"] == ["admin", "user"]
        assert context["teams"] == ["security", "engineering"]
        assert context["permissions"] == ["servers:read", "servers:write"]

    def test_extract_user_context_missing_sub(self, settings_hs256):
        """Test user context extraction fails without 'sub' claim."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        payload = {
            "email": "alice@example.com",
            "name": "Alice Smith",
        }

        with pytest.raises(AuthenticationError, match="missing required 'sub'"):
            middleware._extract_user_context(payload)

    def test_extract_user_context_optional_fields(self, settings_hs256):
        """Test user context extraction with minimal claims."""
        app = FastAPI()
        middleware = AuthMiddleware(app, settings=settings_hs256)

        payload = {
            "sub": "user-789",
        }

        context = middleware._extract_user_context(payload)

        assert context["user_id"] == "user-789"
        assert context["email"] is None
        assert context["name"] is None
        assert context["roles"] == []
        assert context["teams"] == []
        assert context["permissions"] == []


class TestAuthMiddlewareIntegration:
    """Integration tests with FastAPI application."""

    def test_public_endpoint_no_auth_required(self, settings_hs256):
        """Test that public endpoints don't require authentication."""
        app = FastAPI()
        app.add_middleware(AuthMiddleware, settings=settings_hs256)

        @app.get("/health")
        def health():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_protected_endpoint_requires_auth(self, settings_hs256):
        """Test that protected endpoints require authentication."""
        app = FastAPI()
        app.add_middleware(AuthMiddleware, settings=settings_hs256)

        @app.get("/api/v1/protected")
        def protected(request: Request):
            return {"user": request.state.user}

        client = TestClient(app)

        # Request without token
        response = client.get("/api/v1/protected")
        assert response.status_code == 401
        assert "Missing authorization token" in response.json()["detail"]

    def test_protected_endpoint_with_valid_token(self, settings_hs256):
        """Test protected endpoint with valid JWT token."""
        app = FastAPI()
        app.add_middleware(AuthMiddleware, settings=settings_hs256)

        @app.get("/api/v1/protected")
        def protected(request: Request):
            return {"user_id": request.state.user["user_id"]}

        client = TestClient(app)

        # Create valid token
        token = create_test_token(settings_hs256, sub="user-999")

        # Request with valid token
        response = client.get(
            "/api/v1/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["user_id"] == "user-999"

    def test_protected_endpoint_with_expired_token(self, settings_hs256):
        """Test protected endpoint with expired token."""
        app = FastAPI()
        app.add_middleware(AuthMiddleware, settings=settings_hs256)

        @app.get("/api/v1/protected")
        def protected(request: Request):
            return {"user": request.state.user}

        client = TestClient(app)

        # Create expired token
        now = datetime.now(UTC)
        expired_token = create_test_token(
            settings_hs256,
            exp=now - timedelta(minutes=10),
        )

        # Request with expired token
        response = client.get(
            "/api/v1/protected",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
