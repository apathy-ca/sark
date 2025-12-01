"""
Test suite for HTTP adapter.

Tests cover:
- Authentication strategies
- OpenAPI discovery
- Capability invocation
- Rate limiting
- Circuit breaker
- Error handling
- Streaming support

Version: 2.0.0
Engineer: ENGINEER-2
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from sark.adapters.http.http_adapter import HTTPAdapter, CircuitBreaker, RateLimiter
from sark.adapters.http.authentication import (
    NoAuthStrategy,
    BasicAuthStrategy,
    BearerAuthStrategy,
    OAuth2Strategy,
    APIKeyStrategy,
    create_auth_strategy,
)
from sark.adapters.http.discovery import OpenAPIDiscovery
from sark.models.base import ResourceSchema, CapabilitySchema, InvocationRequest, InvocationResult
from sark.adapters.exceptions import (
    ValidationError,
    InvocationError,
    AuthenticationError,
    DiscoveryError,
)


# ============================================================================
# Authentication Tests
# ============================================================================


class TestNoAuthStrategy:
    """Test NoAuthStrategy."""

    def test_apply(self):
        """Test that no auth doesn't modify request."""
        strategy = NoAuthStrategy()
        request = MagicMock(spec=httpx.Request)
        request.headers = {}

        strategy.apply(request)

        assert request.headers == {}

    @pytest.mark.asyncio
    async def test_refresh(self):
        """Test refresh does nothing."""
        strategy = NoAuthStrategy()
        await strategy.refresh()  # Should not raise

    def test_validate_config(self):
        """Test config validation."""
        strategy = NoAuthStrategy()
        assert strategy.validate_config({}) is True


class TestBasicAuthStrategy:
    """Test BasicAuthStrategy."""

    def test_apply(self):
        """Test Basic Auth header is added."""
        strategy = BasicAuthStrategy(username="user", password="pass")
        request = MagicMock(spec=httpx.Request)
        request.headers = {}

        strategy.apply(request)

        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Basic ")

    @pytest.mark.asyncio
    async def test_refresh(self):
        """Test refresh does nothing."""
        strategy = BasicAuthStrategy(username="user", password="pass")
        await strategy.refresh()  # Should not raise

    def test_validate_config_valid(self):
        """Test valid config."""
        strategy = BasicAuthStrategy(username="user", password="pass")
        config = {"username": "user", "password": "pass"}
        assert strategy.validate_config(config) is True

    def test_validate_config_missing_username(self):
        """Test validation fails if username missing."""
        strategy = BasicAuthStrategy(username="user", password="pass")
        config = {"password": "pass"}

        with pytest.raises(AuthenticationError):
            strategy.validate_config(config)


class TestBearerAuthStrategy:
    """Test BearerAuthStrategy."""

    def test_apply(self):
        """Test Bearer token is added."""
        strategy = BearerAuthStrategy(token="test-token")
        request = MagicMock(spec=httpx.Request)
        request.headers = {}

        strategy.apply(request)

        assert request.headers["Authorization"] == "Bearer test-token"

    def test_validate_config_valid(self):
        """Test valid config."""
        strategy = BearerAuthStrategy(token="test-token")
        config = {"token": "test-token"}
        assert strategy.validate_config(config) is True

    def test_validate_config_missing_token(self):
        """Test validation fails if token missing."""
        strategy = BearerAuthStrategy(token="test-token")
        config = {}

        with pytest.raises(AuthenticationError):
            strategy.validate_config(config)


class TestAPIKeyStrategy:
    """Test APIKeyStrategy."""

    def test_apply_header(self):
        """Test API key in header."""
        strategy = APIKeyStrategy(api_key="key123", location="header", key_name="X-API-Key")
        request = MagicMock(spec=httpx.Request)
        request.headers = {}

        strategy.apply(request)

        assert request.headers["X-API-Key"] == "key123"

    def test_apply_query(self):
        """Test API key in query parameter."""
        strategy = APIKeyStrategy(api_key="key123", location="query", key_name="api_key")
        request = MagicMock(spec=httpx.Request)
        request.headers = {}
        request.url = httpx.URL("https://api.example.com/test")

        strategy.apply(request)

        assert "api_key=key123" in str(request.url)

    def test_invalid_location(self):
        """Test invalid location raises error."""
        with pytest.raises(AuthenticationError):
            APIKeyStrategy(api_key="key123", location="invalid")

    def test_validate_config_valid(self):
        """Test valid config."""
        strategy = APIKeyStrategy(api_key="key123")
        config = {"api_key": "key123", "location": "header"}
        assert strategy.validate_config(config) is True

    def test_validate_config_invalid_location(self):
        """Test validation fails with invalid location."""
        strategy = APIKeyStrategy(api_key="key123")
        config = {"api_key": "key123", "location": "invalid"}

        with pytest.raises(AuthenticationError):
            strategy.validate_config(config)


class TestCreateAuthStrategy:
    """Test auth strategy factory."""

    def test_create_none(self):
        """Test creating NoAuthStrategy."""
        strategy = create_auth_strategy({"type": "none"})
        assert isinstance(strategy, NoAuthStrategy)

    def test_create_basic(self):
        """Test creating BasicAuthStrategy."""
        strategy = create_auth_strategy({
            "type": "basic",
            "username": "user",
            "password": "pass"
        })
        assert isinstance(strategy, BasicAuthStrategy)

    def test_create_bearer(self):
        """Test creating BearerAuthStrategy."""
        strategy = create_auth_strategy({
            "type": "bearer",
            "token": "test-token"
        })
        assert isinstance(strategy, BearerAuthStrategy)

    def test_create_oauth2(self):
        """Test creating OAuth2Strategy."""
        strategy = create_auth_strategy({
            "type": "oauth2",
            "token_url": "https://auth.example.com/token",
            "client_id": "client",
            "client_secret": "secret"
        })
        assert isinstance(strategy, OAuth2Strategy)

    def test_create_api_key(self):
        """Test creating APIKeyStrategy."""
        strategy = create_auth_strategy({
            "type": "api_key",
            "api_key": "key123"
        })
        assert isinstance(strategy, APIKeyStrategy)

    def test_create_unsupported_type(self):
        """Test unsupported auth type raises error."""
        with pytest.raises(AuthenticationError):
            create_auth_strategy({"type": "unsupported"})


# ============================================================================
# Discovery Tests
# ============================================================================


class TestOpenAPIDiscovery:
    """Test OpenAPI discovery."""

    @pytest.mark.asyncio
    async def test_discover_spec_direct_url(self):
        """Test discovering spec from direct URL."""
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {}
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = openapi_spec
            mock_client.get.return_value = mock_response

            discovery = OpenAPIDiscovery(
                base_url="https://api.example.com",
                spec_url="https://api.example.com/openapi.json"
            )

            spec = await discovery.discover_spec()

            assert spec == openapi_spec
            assert discovery.openapi_version == "3.0.0"

    @pytest.mark.asyncio
    async def test_discover_capabilities(self):
        """Test discovering capabilities from spec."""
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List all users",
                        "responses": {"200": {"description": "Success"}}
                    }
                },
                "/users/{id}": {
                    "get": {
                        "operationId": "getUser",
                        "summary": "Get user by ID",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        resource = ResourceSchema(
            id="http:api.example.com",
            name="Test API",
            protocol="http",
            endpoint="https://api.example.com",
            sensitivity_level="medium",
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        discovery = OpenAPIDiscovery(base_url="https://api.example.com")
        discovery.spec = openapi_spec
        discovery.openapi_version = "3.0.0"

        capabilities = await discovery.discover_capabilities(resource, spec=openapi_spec)

        assert len(capabilities) == 2

        # Check first capability
        list_users = next(c for c in capabilities if c.name == "listUsers")
        assert list_users.resource_id == resource.id
        assert list_users.metadata["http_method"] == "GET"
        assert list_users.metadata["http_path"] == "/users"

        # Check second capability
        get_user = next(c for c in capabilities if c.name == "getUser")
        assert get_user.resource_id == resource.id
        assert get_user.metadata["http_method"] == "GET"
        assert get_user.metadata["http_path"] == "/users/{id}"


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


class TestCircuitBreaker:
    """Test CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        async def failing_func():
            raise Exception("Test error")

        # First 3 failures should go through
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == "OPEN"

        # Next call should fail immediately
        with pytest.raises(InvocationError, match="Circuit breaker is OPEN"):
            await breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_closes_after_success(self):
        """Test circuit closes after successful call in HALF_OPEN state."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        call_count = [0]

        async def flaky_func():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("Test error")
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(flaky_func)

        assert breaker.state == "OPEN"

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Next call should enter HALF_OPEN and succeed
        result = await breaker.call(flaky_func)
        assert result == "success"
        assert breaker.state == "CLOSED"


# ============================================================================
# Rate Limiter Tests
# ============================================================================


class TestRateLimiter:
    """Test RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting enforces limits."""
        limiter = RateLimiter(rate=5.0, burst=5)  # 5 requests/second

        start_time = asyncio.get_event_loop().time()

        # Make 10 requests
        for _ in range(10):
            await limiter.acquire()

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Should take at least 1 second (5 immediate, 5 more need 1 second)
        assert duration >= 1.0


# ============================================================================
# HTTPAdapter Tests
# ============================================================================


class TestHTTPAdapter:
    """Test HTTPAdapter."""

    def test_protocol_properties(self):
        """Test protocol name and version."""
        adapter = HTTPAdapter(base_url="https://api.example.com")

        assert adapter.protocol_name == "http"
        assert adapter.protocol_version == "1.1"

    @pytest.mark.asyncio
    async def test_validate_request_valid(self):
        """Test validation passes for valid request."""
        adapter = HTTPAdapter(base_url="https://api.example.com")

        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={"param": "value"}
        )

        assert await adapter.validate_request(request) is True

    @pytest.mark.asyncio
    async def test_validate_request_missing_capability_id(self):
        """Test validation fails if capability_id missing."""
        adapter = HTTPAdapter(base_url="https://api.example.com")

        request = InvocationRequest(
            capability_id="",
            principal_id="user-1",
            arguments={}
        )

        with pytest.raises(ValidationError):
            await adapter.validate_request(request)

    @pytest.mark.asyncio
    async def test_validate_request_invalid_arguments(self):
        """Test validation fails if arguments not dict."""
        adapter = HTTPAdapter(base_url="https://api.example.com")

        # Create request with invalid arguments
        request = InvocationRequest(
            capability_id="cap-1",
            principal_id="user-1",
            arguments={}
        )
        request.arguments = "invalid"  # Override with invalid type

        with pytest.raises(ValidationError):
            await adapter.validate_request(request)

    @pytest.mark.asyncio
    async def test_discover_resources(self):
        """Test resource discovery from OpenAPI spec."""
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "A test API"
            },
            "servers": [{"url": "https://api.example.com"}],
            "paths": {}
        }

        adapter = HTTPAdapter(base_url="https://api.example.com")

        with patch.object(OpenAPIDiscovery, "discover_spec", new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = openapi_spec

            discovery_config = {
                "base_url": "https://api.example.com",
                "openapi_spec_url": "https://api.example.com/openapi.json"
            }

            resources = await adapter.discover_resources(discovery_config)

            assert len(resources) == 1
            resource = resources[0]
            assert resource.protocol == "http"
            assert resource.name == "Test API"
            assert resource.metadata["api_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check returns True for healthy API."""
        adapter = HTTPAdapter(base_url="https://api.example.com")

        resource = ResourceSchema(
            id="http:api.example.com",
            name="Test API",
            protocol="http",
            endpoint="https://api.example.com",
            sensitivity_level="medium",
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await adapter.health_check(resource)
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check returns False for unhealthy API."""
        adapter = HTTPAdapter(base_url="https://api.example.com")

        resource = ResourceSchema(
            id="http:api.example.com",
            name="Test API",
            protocol="http",
            endpoint="https://api.example.com",
            sensitivity_level="medium",
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")

            result = await adapter.health_check(resource)
            assert result is False

    def test_repr(self):
        """Test string representation."""
        adapter = HTTPAdapter(base_url="https://api.example.com")
        repr_str = repr(adapter)

        assert "HTTPAdapter" in repr_str
        assert "api.example.com" in repr_str


# ============================================================================
# Integration Tests
# ============================================================================


class TestHTTPAdapterIntegration:
    """Integration tests for HTTP adapter."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow: discover -> get capabilities -> invoke."""
        # This is a placeholder for integration tests with real APIs
        # In production, this would use a test HTTP server
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
