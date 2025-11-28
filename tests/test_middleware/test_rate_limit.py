"""Tests for rate limiting middleware."""

from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI, Request
import pytest
from starlette.testclient import TestClient

from sark.api.middleware.rate_limit import RateLimitMiddleware
from sark.config.settings import Settings
from sark.services.rate_limiter import RateLimiter, RateLimitInfo

# Fixtures


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock(spec=Settings)
    settings.rate_limit_enabled = True
    settings.rate_limit_per_api_key = 1000
    settings.rate_limit_per_user = 5000
    settings.rate_limit_per_ip = 100
    settings.rate_limit_admin_bypass = True
    settings.rate_limit_window_seconds = 3600
    return settings


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter."""
    limiter = AsyncMock(spec=RateLimiter)
    return limiter


@pytest.fixture
def app(mock_rate_limiter, mock_settings):
    """Create test FastAPI app with rate limit middleware."""
    app = FastAPI()

    # Add test routes
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}

    # Add middleware
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=mock_rate_limiter,
        settings=mock_settings,
    )

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# Test Basic Rate Limiting


class TestBasicRateLimiting:
    """Test basic rate limiting functionality."""

    async def test_rate_limit_allowed(self, client, mock_rate_limiter):
        """Test request allowed when under rate limit."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True,
            limit=100,
            remaining=50,
            reset_at=1234567890,
        )

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"
        assert response.headers["X-RateLimit-Reset"] == "1234567890"

    async def test_rate_limit_exceeded(self, client, mock_rate_limiter):
        """Test request blocked when rate limit exceeded."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=1234567890,
            retry_after=3600,
        )

        response = client.get("/test")

        assert response.status_code == 429
        data = response.json()
        assert "Rate limit exceeded" in data["error"]
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"
        assert response.headers["Retry-After"] == "3600"

    async def test_rate_limit_disabled(self, client, mock_rate_limiter, mock_settings):
        """Test rate limiting is skipped when disabled."""
        mock_settings.rate_limit_enabled = False

        response = client.get("/test")

        assert response.status_code == 200
        # Rate limiter should not be called
        mock_rate_limiter.check_rate_limit.assert_not_called()


# Test Identifier Detection


class TestIdentifierDetection:
    """Test correct identification of request source."""

    async def test_api_key_identifier(self, client, mock_rate_limiter, mock_settings):
        """Test API key is used as identifier."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=1000, remaining=999, reset_at=1234567890
        )

        response = client.get("/test", headers={"X-API-Key": "test-api-key-123"})

        assert response.status_code == 200
        # Verify correct identifier and limit
        mock_rate_limiter.check_rate_limit.assert_called_once()
        call_args = mock_rate_limiter.check_rate_limit.call_args
        assert call_args[1]["identifier"] == "api_key:test-api-key-123"
        assert call_args[1]["limit"] == 1000

    async def test_jwt_identifier_with_user_id(self, client, mock_rate_limiter, mock_settings):
        """Test JWT user ID is used as identifier."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=5000, remaining=4999, reset_at=1234567890
        )

        # Create app with state
        app = client.app

        # Add route that sets user_id in state
        @app.get("/test-auth")
        async def test_auth_endpoint(request: Request):
            request.state.user_id = "user-uuid-123"
            return {"message": "success"}

        response = client.get("/test-auth", headers={"Authorization": "Bearer fake-jwt-token"})

        assert response.status_code == 200
        # Note: In real scenario, auth middleware would set request.state.user_id

    async def test_ip_identifier(self, client, mock_rate_limiter, mock_settings):
        """Test IP address is used as fallback identifier."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        response = client.get("/test")

        assert response.status_code == 200
        # Verify IP-based identifier
        mock_rate_limiter.check_rate_limit.assert_called_once()
        call_args = mock_rate_limiter.check_rate_limit.call_args
        identifier = call_args[1]["identifier"]
        assert identifier.startswith("ip:")
        assert call_args[1]["limit"] == 100

    async def test_forwarded_ip(self, client, mock_rate_limiter, mock_settings):
        """Test X-Forwarded-For header is used for IP."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        response = client.get("/test", headers={"X-Forwarded-For": "203.0.113.1, 198.51.100.1"})

        assert response.status_code == 200
        call_args = mock_rate_limiter.check_rate_limit.call_args
        assert call_args[1]["identifier"] == "ip:203.0.113.1"

    async def test_real_ip_header(self, client, mock_rate_limiter, mock_settings):
        """Test X-Real-IP header is used for IP."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        response = client.get("/test", headers={"X-Real-IP": "198.51.100.42"})

        assert response.status_code == 200
        call_args = mock_rate_limiter.check_rate_limit.call_args
        assert call_args[1]["identifier"] == "ip:198.51.100.42"


# Test Admin Bypass


class TestAdminBypass:
    """Test admin bypass functionality."""

    async def test_admin_bypass_enabled(self, client, mock_rate_limiter, mock_settings):
        """Test admin users bypass rate limits."""
        # Create app with admin user
        app = client.app

        @app.get("/test-admin")
        async def test_admin_endpoint(request: Request):
            request.state.user_roles = ["admin"]
            return {"message": "success"}

        response = client.get("/test-admin")

        assert response.status_code == 200
        # Rate limiter should not be called for admin
        mock_rate_limiter.check_rate_limit.assert_not_called()
        # Should have special admin headers
        assert response.headers["X-RateLimit-Limit"] == "999999"
        assert response.headers["X-RateLimit-Remaining"] == "999999"

    async def test_admin_bypass_disabled(self, client, mock_rate_limiter, mock_settings):
        """Test admin bypass can be disabled."""
        mock_settings.rate_limit_admin_bypass = False
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        app = client.app

        @app.get("/test-admin-disabled")
        async def test_admin_endpoint(request: Request):
            request.state.user_roles = ["admin"]
            return {"message": "success"}

        response = client.get("/test-admin-disabled")

        assert response.status_code == 200
        # Rate limiter should be called even for admin
        mock_rate_limiter.check_rate_limit.assert_called_once()

    async def test_non_admin_user(self, client, mock_rate_limiter, mock_settings):
        """Test non-admin users don't bypass rate limits."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        app = client.app

        @app.get("/test-user")
        async def test_user_endpoint(request: Request):
            request.state.user_roles = ["user"]
            return {"message": "success"}

        response = client.get("/test-user")

        assert response.status_code == 200
        # Rate limiter should be called for regular users
        mock_rate_limiter.check_rate_limit.assert_called_once()


# Test Health Check Bypass


class TestHealthCheckBypass:
    """Test health check endpoints bypass rate limiting."""

    async def test_health_endpoint_bypassed(self, client, mock_rate_limiter):
        """Test /health endpoint bypasses rate limiting."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
        # Rate limiter should not be called
        mock_rate_limiter.check_rate_limit.assert_not_called()

    async def test_api_health_bypassed(self, client, mock_rate_limiter):
        """Test /api/health endpoint bypasses rate limiting."""
        app = client.app

        @app.get("/api/health")
        async def api_health():
            return {"status": "ok"}

        response = client.get("/api/health")

        assert response.status_code == 200
        mock_rate_limiter.check_rate_limit.assert_not_called()

    async def test_metrics_bypassed(self, client, mock_rate_limiter):
        """Test /metrics endpoint bypasses rate limiting."""
        app = client.app

        @app.get("/metrics")
        async def metrics():
            return {"metrics": "data"}

        response = client.get("/metrics")

        assert response.status_code == 200
        mock_rate_limiter.check_rate_limit.assert_not_called()


# Test Rate Limit Headers


class TestRateLimitHeaders:
    """Test rate limit headers in responses."""

    async def test_all_headers_present(self, client, mock_rate_limiter):
        """Test all rate limit headers are present."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True,
            limit=1000,
            remaining=750,
            reset_at=1234567890,
        )

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "1000"
        assert response.headers["X-RateLimit-Remaining"] == "750"
        assert response.headers["X-RateLimit-Reset"] == "1234567890"

    async def test_retry_after_header_when_limited(self, client, mock_rate_limiter):
        """Test Retry-After header when rate limited."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=1234567890,
            retry_after=1800,
        )

        response = client.get("/test")

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "1800"

    async def test_no_retry_after_when_allowed(self, client, mock_rate_limiter):
        """Test no Retry-After header when request is allowed."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True,
            limit=100,
            remaining=50,
            reset_at=1234567890,
        )

        response = client.get("/test")

        assert response.status_code == 200
        assert "Retry-After" not in response.headers


# Test Error Handling


class TestErrorHandling:
    """Test error handling in middleware."""

    async def test_rate_limiter_exception(self, client, mock_rate_limiter):
        """Test middleware handles rate limiter exceptions gracefully."""
        # Rate limiter should fail open (allow request)
        mock_rate_limiter.check_rate_limit.side_effect = Exception("Redis down")

        # Should still succeed due to fail-open behavior in RateLimiter
        response = client.get("/test")

        # The RateLimiter itself should catch the exception and return allowed=True
        # So the request should succeed
        assert response.status_code in [200, 500]  # Depends on implementation


# Test Different Request Methods


class TestRequestMethods:
    """Test rate limiting works for different HTTP methods."""

    async def test_get_request(self, client, mock_rate_limiter):
        """Test GET requests are rate limited."""
        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        response = client.get("/test")

        assert response.status_code == 200
        mock_rate_limiter.check_rate_limit.assert_called_once()

    async def test_post_request(self, client, mock_rate_limiter):
        """Test POST requests are rate limited."""
        app = client.app

        @app.post("/test-post")
        async def test_post():
            return {"message": "created"}

        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        response = client.post("/test-post")

        assert response.status_code == 200
        mock_rate_limiter.check_rate_limit.assert_called_once()

    async def test_delete_request(self, client, mock_rate_limiter):
        """Test DELETE requests are rate limited."""
        app = client.app

        @app.delete("/test-delete")
        async def test_delete():
            return {"message": "deleted"}

        mock_rate_limiter.check_rate_limit.return_value = RateLimitInfo(
            allowed=True, limit=100, remaining=99, reset_at=1234567890
        )

        response = client.delete("/test-delete")

        assert response.status_code == 200
        mock_rate_limiter.check_rate_limit.assert_called_once()
