"""Comprehensive tests for Gateway HTTP transport client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from pytest_httpx import HTTPXMock

from sark.gateway.transports.http_client import (
    CacheEntry,
    GatewayHTTPClient,
    PaginationParams,
)
from sark.models.gateway import GatewayServerInfo, GatewayToolInfo
from sark.services.policy.opa_client import (
    AuthorizationDecision,
    AuthorizationInput,
    OPAClient,
)


class TestPaginationParams:
    """Test suite for PaginationParams class."""

    def test_pagination_params_defaults(self):
        """Test pagination params with default values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 100
        assert params.offset == 0

    def test_pagination_params_custom_page(self):
        """Test pagination params with custom page."""
        params = PaginationParams(page=5, page_size=50)
        assert params.page == 5
        assert params.page_size == 50
        assert params.offset == 200  # (5-1) * 50

    def test_pagination_params_max_page_size(self):
        """Test pagination params enforces max page size."""
        params = PaginationParams(page_size=5000)
        assert params.page_size == 1000  # Capped at 1000

    def test_pagination_params_negative_page(self):
        """Test pagination params handles negative page."""
        params = PaginationParams(page=-5)
        assert params.page == 1  # Minimum is 1

    def test_pagination_params_direct_offset(self):
        """Test pagination params with direct offset."""
        params = PaginationParams(page=5, offset=100)
        assert params.offset == 100  # Direct offset overrides page

    def test_pagination_params_to_query(self):
        """Test converting pagination params to query dict."""
        params = PaginationParams(page=2, page_size=50)
        query = params.to_query_params()
        assert query["offset"] == 50
        assert query["limit"] == 50


class TestCacheEntry:
    """Test suite for CacheEntry class."""

    def test_cache_entry_creation(self):
        """Test creating cache entry."""
        data = {"key": "value"}
        entry = CacheEntry(data, ttl=300)
        assert entry.data == data
        assert entry.ttl == 300
        assert entry.is_valid()

    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        entry = CacheEntry({"key": "value"}, ttl=0)
        assert not entry.is_valid()

    def test_cache_entry_validity(self):
        """Test cache entry validity check."""
        entry = CacheEntry({"key": "value"}, ttl=60)
        assert entry.is_valid()
        # Simulate time passing
        entry.created_at -= 70
        assert not entry.is_valid()


class TestGatewayHTTPClient:
    """Test suite for GatewayHTTPClient class."""

    @pytest.fixture
    def client(self):
        """Create HTTP client instance."""
        return GatewayHTTPClient(
            base_url="http://test-gateway:8080",
            api_key="test-api-key",
            timeout=5.0,
            cache_enabled=True,
        )

    @pytest.fixture
    def client_with_opa(self):
        """Create HTTP client with OPA client."""
        opa_client = MagicMock(spec=OPAClient)
        return GatewayHTTPClient(
            base_url="http://test-gateway:8080",
            opa_client=opa_client,
        )

    @pytest.fixture
    def sample_server_data(self):
        """Sample server data for tests."""
        return {
            "server_id": "srv-123",
            "server_name": "postgres-mcp",
            "server_url": "http://postgres-mcp:8080",
            "sensitivity_level": "high",
            "authorized_teams": ["data-eng"],
            "health_status": "healthy",
            "tools_count": 10,
        }

    @pytest.fixture
    def sample_tool_data(self):
        """Sample tool data for tests."""
        return {
            "tool_name": "execute_query",
            "server_name": "postgres-mcp",
            "description": "Execute SQL query",
            "sensitivity_level": "high",
            "parameters": [
                {"name": "query", "type": "string", "required": True},
            ],
        }

    async def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "http://test-gateway:8080"
        assert client.api_key == "test-api-key"
        assert client.timeout == 5.0
        assert client.cache_enabled is True
        await client.close()

    async def test_client_context_manager(self):
        """Test client as async context manager."""
        async with GatewayHTTPClient(base_url="http://test:8080") as client:
            assert client is not None
        # Client should be closed after context

    async def test_get_headers_with_api_key(self, client):
        """Test building headers with API key."""
        headers = client._get_headers()
        assert headers["X-API-Key"] == "test-api-key"
        assert headers["Content-Type"] == "application/json"
        await client.close()

    async def test_get_headers_with_user_token(self, client):
        """Test building headers with user token."""
        headers = client._get_headers(user_token="jwt-token-123")
        assert headers["Authorization"] == "Bearer jwt-token-123"
        await client.close()

    async def test_cache_key_generation(self, client):
        """Test cache key generation."""
        key1 = client._get_cache_key("/api/v1/servers")
        assert key1 == "/api/v1/servers"

        key2 = client._get_cache_key("/api/v1/servers", {"page": "1", "limit": "100"})
        assert "limit=100" in key2
        assert "page=1" in key2
        await client.close()

    async def test_list_servers_success(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test listing servers successfully."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            json={"servers": [sample_server_data]},
        )

        servers = await client.list_servers()
        assert len(servers) == 1
        assert servers[0].server_name == "postgres-mcp"
        assert servers[0].sensitivity_level.value == "high"
        await client.close()

    async def test_list_servers_pagination(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test listing servers with pagination."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=100&limit=50",
            json={"servers": [sample_server_data]},
        )

        servers = await client.list_servers(page=3, page_size=50)
        assert len(servers) == 1
        await client.close()

    async def test_list_servers_caching(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test servers list caching."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            json={"servers": [sample_server_data]},
        )

        # First request - cache miss
        servers1 = await client.list_servers()
        assert len(servers1) == 1

        # Second request - cache hit (no additional HTTP request)
        servers2 = await client.list_servers()
        assert len(servers2) == 1

        # Only one HTTP request should have been made
        assert len(httpx_mock.get_requests()) == 1

        metrics = client.get_cache_metrics()
        assert metrics["cache_hits"] == 1
        assert metrics["cache_misses"] == 1
        await client.close()

    async def test_list_all_servers_pagination(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test listing all servers with automatic pagination."""
        # Page 1: Full page
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            json={"servers": [sample_server_data] * 100},
        )

        # Page 2: Partial page (end of results)
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=100&limit=100",
            json={"servers": [sample_server_data] * 50},
        )

        all_servers = await client.list_all_servers(page_size=100)
        assert len(all_servers) == 150
        await client.close()

    async def test_get_server_success(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test getting specific server."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers/postgres-mcp",
            json=sample_server_data,
        )

        server = await client.get_server("postgres-mcp")
        assert server.server_name == "postgres-mcp"
        assert server.tools_count == 10
        await client.close()

    async def test_get_server_not_found(self, client, httpx_mock: HTTPXMock):
        """Test getting non-existent server."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers/nonexistent",
            status_code=404,
            json={"error": "Server not found"},
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.get_server("nonexistent")
        await client.close()

    async def test_list_tools_success(self, client, sample_tool_data, httpx_mock: HTTPXMock):
        """Test listing tools."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/tools?offset=0&limit=100",
            json={"tools": [sample_tool_data]},
        )

        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0].tool_name == "execute_query"
        await client.close()

    async def test_list_tools_filtered_by_server(self, client, sample_tool_data, httpx_mock: HTTPXMock):
        """Test listing tools filtered by server."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/tools?offset=0&limit=100&server=postgres-mcp",
            json={"tools": [sample_tool_data]},
        )

        tools = await client.list_tools(server_name="postgres-mcp")
        assert len(tools) == 1
        assert tools[0].server_name == "postgres-mcp"
        await client.close()

    async def test_invoke_tool_success(self, client, httpx_mock: HTTPXMock):
        """Test invoking tool successfully."""
        httpx_mock.add_response(
            method="POST",
            url="http://test-gateway:8080/api/v1/invoke",
            json={"status": "success", "result": {"rows": []}},
        )

        result = await client.invoke_tool(
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT 1"},
            user_token="jwt-token",
            check_authorization=False,  # Skip OPA check for this test
        )

        assert result["status"] == "success"
        await client.close()

    async def test_invoke_tool_with_opa_authorization(self, client_with_opa, httpx_mock: HTTPXMock):
        """Test invoking tool with OPA authorization check."""
        # Mock OPA authorization decision
        client_with_opa.opa_client.evaluate_gateway_policy = AsyncMock(
            return_value=AuthorizationDecision(
                allow=True,
                reason="User authorized",
            )
        )

        httpx_mock.add_response(
            method="POST",
            url="http://test-gateway:8080/api/v1/invoke",
            json={"status": "success"},
        )

        result = await client_with_opa.invoke_tool(
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT 1"},
            user_token="jwt-token",
            check_authorization=True,
        )

        assert result["status"] == "success"
        client_with_opa.opa_client.evaluate_gateway_policy.assert_called_once()
        await client_with_opa.close()

    async def test_invoke_tool_opa_denied(self, client_with_opa, httpx_mock: HTTPXMock):
        """Test invoking tool when OPA denies authorization."""
        # Mock OPA denial
        client_with_opa.opa_client.evaluate_gateway_policy = AsyncMock(
            return_value=AuthorizationDecision(
                allow=False,
                reason="Insufficient permissions",
            )
        )

        with pytest.raises(PermissionError, match="Insufficient permissions"):
            await client_with_opa.invoke_tool(
                server_name="postgres-mcp",
                tool_name="execute_query",
                parameters={"query": "SELECT 1"},
                user_token="jwt-token",
                check_authorization=True,
            )

        await client_with_opa.close()

    async def test_invoke_tool_with_filtered_parameters(self, client_with_opa, httpx_mock: HTTPXMock):
        """Test invoking tool with OPA-filtered parameters."""
        # Mock OPA authorization with filtered parameters
        client_with_opa.opa_client.evaluate_gateway_policy = AsyncMock(
            return_value=AuthorizationDecision(
                allow=True,
                reason="User authorized",
                filtered_parameters={"query": "SELECT id FROM users LIMIT 10"},
            )
        )

        httpx_mock.add_response(
            method="POST",
            url="http://test-gateway:8080/api/v1/invoke",
            json={"status": "success"},
        )

        result = await client_with_opa.invoke_tool(
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT * FROM users"},
            user_token="jwt-token",
            check_authorization=True,
        )

        assert result["status"] == "success"
        await client_with_opa.close()

    async def test_health_check_success(self, client, httpx_mock: HTTPXMock):
        """Test health check success."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/health",
            json={"status": "healthy"},
        )

        health = await client.health_check()
        assert health["healthy"] is True
        await client.close()

    async def test_health_check_failure(self, client, httpx_mock: HTTPXMock):
        """Test health check failure."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/health",
            status_code=503,
            json={"status": "unhealthy"},
        )

        health = await client.health_check()
        assert health["healthy"] is False
        await client.close()

    async def test_retry_logic_on_server_error(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test retry logic on server errors (5xx)."""
        # First two requests fail, third succeeds
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            status_code=503,
        )
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            status_code=503,
        )
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            json={"servers": [sample_server_data]},
        )

        servers = await client.list_servers(use_cache=False)
        assert len(servers) == 1

        # Should have made 3 requests
        assert len(httpx_mock.get_requests()) == 3
        await client.close()

    async def test_no_retry_on_client_error(self, client, httpx_mock: HTTPXMock):
        """Test no retry on client errors (4xx)."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            status_code=400,
            json={"error": "Bad request"},
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.list_servers(use_cache=False)

        # Should have made only 1 request (no retries on 4xx)
        assert len(httpx_mock.get_requests()) == 1
        await client.close()

    async def test_cache_metrics(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test cache metrics tracking."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            json={"servers": [sample_server_data]},
        )

        # Make requests to generate metrics
        await client.list_servers()  # Cache miss
        await client.list_servers()  # Cache hit

        metrics = client.get_cache_metrics()
        assert metrics["cache_enabled"] is True
        assert metrics["cache_hits"] == 1
        assert metrics["cache_misses"] == 1
        assert metrics["total_requests"] == 2
        assert metrics["hit_rate"] > 0.0
        await client.close()

    async def test_clear_cache(self, client, sample_server_data, httpx_mock: HTTPXMock):
        """Test clearing cache."""
        httpx_mock.add_response(
            method="GET",
            url="http://test-gateway:8080/api/v1/servers?offset=0&limit=100",
            json={"servers": [sample_server_data]},
        )

        await client.list_servers()
        client.clear_cache()

        metrics = client.get_cache_metrics()
        assert metrics["cache_size"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0
        await client.close()

    async def test_cache_disabled(self):
        """Test client with caching disabled."""
        async with GatewayHTTPClient(
            base_url="http://test:8080",
            cache_enabled=False,
        ) as client:
            assert client.cache_enabled is False
            metrics = client.get_cache_metrics()
            assert metrics["cache_enabled"] is False

    async def test_connection_pooling_limits(self):
        """Test connection pooling configuration."""
        async with GatewayHTTPClient(
            base_url="http://test:8080",
            max_connections=100,
        ) as client:
            assert client.client.limits.max_connections == 100
            assert client.client.limits.max_keepalive_connections == 20

    async def test_timeout_configuration(self):
        """Test timeout configuration."""
        async with GatewayHTTPClient(
            base_url="http://test:8080",
            timeout=10.0,
        ) as client:
            assert client.timeout == 10.0

    async def test_base_url_trailing_slash_removal(self):
        """Test that trailing slash is removed from base URL."""
        async with GatewayHTTPClient(
            base_url="http://test:8080/",
        ) as client:
            assert client.base_url == "http://test:8080"

    async def test_invoke_tool_not_cached(self, client, httpx_mock: HTTPXMock):
        """Test that tool invocations are never cached."""
        httpx_mock.add_response(
            method="POST",
            url="http://test-gateway:8080/api/v1/invoke",
            json={"status": "success", "result": {"value": 1}},
        )

        # Make same invocation twice
        await client.invoke_tool(
            server_name="test-server",
            tool_name="test-tool",
            parameters={},
            user_token="token",
            check_authorization=False,
        )
        await client.invoke_tool(
            server_name="test-server",
            tool_name="test-tool",
            parameters={},
            user_token="token",
            check_authorization=False,
        )

        # Both should hit the server (2 requests)
        assert len(httpx_mock.get_requests()) == 2
        await client.close()
