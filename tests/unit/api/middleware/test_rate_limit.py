"""Unit tests for Rate Limit Middleware."""

from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import pytest

from sark.api.middleware.rate_limit import RateLimitMiddleware
from sark.services.rate_limiter import RateLimitInfo


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock()
    settings.rate_limit_enabled = True
    settings.rate_limit_admin_bypass = True
    settings.rate_limit_per_api_key = 100
    settings.rate_limit_per_user = 50
    settings.rate_limit_per_ip = 10
    return settings


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter."""
    return AsyncMock()


@pytest.fixture
def app():
    """Create FastAPI app."""
    return FastAPI()


@pytest.fixture
def middleware(app, mock_rate_limiter, mock_settings):
    """Create rate limit middleware instance."""
    return RateLimitMiddleware(
        app=app,
        rate_limiter=mock_rate_limiter,
        settings=mock_settings,
    )


@pytest.fixture
def mock_request():
    """Create mock request."""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/api/test"
    request.headers = {}
    request.client = Mock()
    request.client.host = "127.0.0.1"
    # Use a proper object for state to support attribute access
    request.state = type("obj", (object,), {"user_id": None, "user_roles": []})()
    return request


class TestRateLimitMiddlewareInitialization:
    """Test middleware initialization."""

    def test_initialization(self, app, mock_rate_limiter, mock_settings):
        """Test that middleware initializes correctly."""
        middleware = RateLimitMiddleware(
            app=app,
            rate_limiter=mock_rate_limiter,
            settings=mock_settings,
        )

        assert middleware.rate_limiter == mock_rate_limiter
        assert middleware.settings == mock_settings


class TestRateLimitBypass:
    """Test rate limit bypass scenarios."""

    @pytest.mark.asyncio
    async def test_bypass_when_disabled(self, middleware, mock_request):
        """Test that rate limiting is bypassed when disabled."""
        middleware.settings.rate_limit_enabled = False

        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        # Should call next without checking rate limit
        call_next.assert_called_once()
        middleware.rate_limiter.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_bypass_health_endpoint(self, middleware, mock_request):
        """Test that health check endpoints bypass rate limiting."""
        mock_request.url.path = "/health"

        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        # Should not check rate limit for health endpoints
        middleware.rate_limiter.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_bypass_api_health_endpoint(self, middleware, mock_request):
        """Test that API health endpoint bypasses rate limiting."""
        mock_request.url.path = "/api/health"

        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        middleware.rate_limiter.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_bypass_metrics_endpoint(self, middleware, mock_request):
        """Test that metrics endpoint bypasses rate limiting."""
        mock_request.url.path = "/metrics"

        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        middleware.rate_limiter.check_rate_limit.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_bypass(self, middleware, mock_request):
        """Test that admins can bypass rate limits."""
        mock_request.state.user_roles = ["admin"]
        middleware.settings.rate_limit_admin_bypass = True

        call_next = AsyncMock(return_value=Response())

        response = await middleware.dispatch(mock_request, call_next)

        # Should call next without enforcing rate limit
        call_next.assert_called_once()
        # Headers should still be added with high values
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "999999"


class TestIdentifierDetection:
    """Test identifier and limit detection."""

    @pytest.mark.asyncio
    async def test_api_key_identifier(self, middleware, mock_request):
        """Test rate limiting by API key."""
        mock_request.headers = {"X-API-Key": "test_api_key_123"}

        identifier, limit = await middleware._get_identifier_and_limit(mock_request)

        assert identifier == "api_key:test_api_key_123"
        assert limit == middleware.settings.rate_limit_per_api_key

    @pytest.mark.asyncio
    async def test_user_jwt_identifier(self, middleware, mock_request):
        """Test rate limiting by JWT user."""
        mock_request.headers = {"Authorization": "Bearer fake_jwt_token"}
        mock_request.state.user_id = "user_123"

        identifier, limit = await middleware._get_identifier_and_limit(mock_request)

        assert identifier == "user:user_123"
        assert limit == middleware.settings.rate_limit_per_user

    @pytest.mark.asyncio
    async def test_jwt_without_user_id(self, middleware, mock_request):
        """Test rate limiting by JWT token hash when user_id not available."""
        mock_request.headers = {"Authorization": "Bearer fake_jwt_token"}
        # No user_id in state

        identifier, limit = await middleware._get_identifier_and_limit(mock_request)

        assert identifier.startswith("token:")
        assert limit == middleware.settings.rate_limit_per_user

    @pytest.mark.asyncio
    async def test_ip_address_identifier(self, middleware, mock_request):
        """Test rate limiting by IP address."""
        mock_request.client.host = "192.168.1.100"

        identifier, limit = await middleware._get_identifier_and_limit(mock_request)

        assert identifier == "ip:192.168.1.100"
        assert limit == middleware.settings.rate_limit_per_ip

    @pytest.mark.asyncio
    async def test_x_forwarded_for_header(self, middleware, mock_request):
        """Test IP detection from X-Forwarded-For header."""
        mock_request.headers = {"X-Forwarded-For": "203.0.113.45, 198.51.100.1"}

        identifier, _limit = await middleware._get_identifier_and_limit(mock_request)

        # Should use first IP in X-Forwarded-For
        assert identifier == "ip:203.0.113.45"

    @pytest.mark.asyncio
    async def test_x_real_ip_header(self, middleware, mock_request):
        """Test IP detection from X-Real-IP header."""
        mock_request.headers = {"X-Real-IP": "198.51.100.99"}

        identifier, _limit = await middleware._get_identifier_and_limit(mock_request)

        assert identifier == "ip:198.51.100.99"


class TestRateLimitEnforcement:
    """Test rate limit enforcement."""

    @pytest.mark.asyncio
    async def test_request_allowed_within_limit(self, middleware, mock_request):
        """Test that request is allowed when within rate limit."""
        rate_info = RateLimitInfo(
            allowed=True,
            limit=100,
            remaining=50,
            reset_at=1234567890,
        )
        middleware.rate_limiter.check_rate_limit = AsyncMock(return_value=rate_info)

        call_next = AsyncMock(return_value=Response())

        response = await middleware.dispatch(mock_request, call_next)

        # Should proceed with request
        call_next.assert_called_once()
        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"

    @pytest.mark.asyncio
    async def test_request_blocked_over_limit(self, middleware, mock_request):
        """Test that request is blocked when over rate limit."""
        rate_info = RateLimitInfo(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=1234567890,
            retry_after=60,
        )
        middleware.rate_limiter.check_rate_limit = AsyncMock(return_value=rate_info)

        call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, call_next)

        # Should not proceed with request
        call_next.assert_not_called()

        # Should return 429 status
        assert isinstance(response, JSONResponse)
        assert response.status_code == 429

        # Should have retry-after header
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_rate_limit_response_body(self, middleware, mock_request):
        """Test rate limit exceeded response body."""
        rate_info = RateLimitInfo(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=1234567890,
            retry_after=60,
        )
        middleware.rate_limiter.check_rate_limit = AsyncMock(return_value=rate_info)

        call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, call_next)

        # Check response body
        assert response.status_code == 429
        # The response body should contain error information
        # Note: In production, you'd decode the JSON body to verify content


class TestAdminBypass:
    """Test admin bypass functionality."""

    @pytest.mark.asyncio
    async def test_is_admin_with_admin_role(self, middleware, mock_request):
        """Test admin detection with admin role."""
        mock_request.state.user_roles = ["admin", "user"]

        is_admin = await middleware._is_admin(mock_request)

        assert is_admin is True

    @pytest.mark.asyncio
    async def test_is_admin_with_administrator_role(self, middleware, mock_request):
        """Test admin detection with administrator role."""
        mock_request.state.user_roles = ["administrator"]

        is_admin = await middleware._is_admin(mock_request)

        assert is_admin is True

    @pytest.mark.asyncio
    async def test_is_admin_without_admin_role(self, middleware, mock_request):
        """Test admin detection without admin role."""
        mock_request.state.user_roles = ["user", "viewer"]

        is_admin = await middleware._is_admin(mock_request)

        assert is_admin is False

    @pytest.mark.asyncio
    async def test_is_admin_no_roles(self, middleware, mock_request):
        """Test admin detection with no roles."""
        mock_request.state.user_roles = []

        is_admin = await middleware._is_admin(mock_request)

        assert is_admin is False


class TestRateLimitHeaders:
    """Test rate limit header addition."""

    def test_add_rate_limit_headers_success(self, middleware):
        """Test adding rate limit headers to successful response."""
        response = Response()

        middleware._add_rate_limit_headers(
            response=response,
            limit=100,
            remaining=50,
            reset_at=1234567890,
        )

        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"
        assert response.headers["X-RateLimit-Reset"] == "1234567890"
        assert "Retry-After" not in response.headers

    def test_add_rate_limit_headers_with_retry(self, middleware):
        """Test adding rate limit headers with retry-after."""
        response = Response()

        middleware._add_rate_limit_headers(
            response=response,
            limit=100,
            remaining=0,
            reset_at=1234567890,
            retry_after=60,
        )

        assert response.headers["Retry-After"] == "60"

    def test_add_rate_limit_headers_all_fields(self, middleware):
        """Test that all rate limit headers are added correctly."""
        response = Response()

        middleware._add_rate_limit_headers(
            response=response,
            limit=1000,
            remaining=500,
            reset_at=9876543210,
            retry_after=120,
        )

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers


class TestRateLimitIntegration:
    """Test end-to-end rate limiting scenarios."""

    @pytest.mark.asyncio
    async def test_api_key_rate_limiting(self, middleware, mock_request):
        """Test complete flow for API key rate limiting."""
        mock_request.headers = {"X-API-Key": "test_key"}

        rate_info = RateLimitInfo(
            allowed=True,
            limit=100,
            remaining=99,
            reset_at=1234567890,
        )
        middleware.rate_limiter.check_rate_limit = AsyncMock(return_value=rate_info)

        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        # Verify rate limiter was called with API key identifier
        middleware.rate_limiter.check_rate_limit.assert_called_once()
        call_args = middleware.rate_limiter.check_rate_limit.call_args
        assert call_args[1]["identifier"].startswith("api_key:")
        assert call_args[1]["limit"] == 100

    @pytest.mark.asyncio
    async def test_progressive_rate_limiting(self, middleware, mock_request):
        """Test that remaining count decreases with each request."""
        mock_request.headers = {"X-API-Key": "test_key"}

        # Simulate 3 requests
        for remaining in [99, 98, 97]:
            rate_info = RateLimitInfo(
                allowed=True,
                limit=100,
                remaining=remaining,
                reset_at=1234567890,
            )
            middleware.rate_limiter.check_rate_limit = AsyncMock(return_value=rate_info)

            call_next = AsyncMock(return_value=Response())

            response = await middleware.dispatch(mock_request, call_next)

            assert response.headers["X-RateLimit-Remaining"] == str(remaining)

    @pytest.mark.asyncio
    async def test_identifier_priority(self, middleware, mock_request):
        """Test that API key takes priority over JWT."""
        # Provide both API key and JWT
        mock_request.headers = {
            "X-API-Key": "test_key",
            "Authorization": "Bearer jwt_token",
        }
        mock_request.state.user_id = "user_123"

        identifier, limit = await middleware._get_identifier_and_limit(mock_request)

        # Should use API key (higher priority)
        assert identifier.startswith("api_key:")
        assert limit == middleware.settings.rate_limit_per_api_key
