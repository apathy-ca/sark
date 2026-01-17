"""Tests for Gateway client service integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.models.gateway import GatewayServerInfo, GatewayToolInfo
from sark.services.gateway.client import (
    GatewayClient,
    close_gateway_client,
    get_gateway_client,
)


class TestGatewayClient:
    """Test suite for GatewayClient integration with HTTP transport."""

    @pytest.fixture
    def mock_transport(self):
        """Create mock HTTP transport."""
        transport = AsyncMock()
        transport.list_servers = AsyncMock(return_value=[])
        transport.list_all_servers = AsyncMock(return_value=[])
        transport.get_server = AsyncMock()
        transport.list_tools = AsyncMock(return_value=[])
        transport.invoke_tool = AsyncMock(return_value={"status": "success"})
        transport.health_check = AsyncMock(return_value={"healthy": True})
        transport.get_cache_metrics = MagicMock(return_value={"hit_rate": 0.85})
        transport.clear_cache = MagicMock()
        transport.close = AsyncMock()
        return transport

    @pytest.fixture
    def client(self, mock_transport):
        """Create GatewayClient with mocked transport."""
        with patch(
            "sark.services.gateway.client.GatewayHTTPClient",
            return_value=mock_transport,
        ):
            client = GatewayClient(
                base_url="http://test-gateway:8080",
                api_key="test-key",
            )
            yield client

    async def test_client_initialization(self, client, mock_transport):
        """Test client initialization creates transport."""
        assert client.base_url == "http://test-gateway:8080"
        assert client.api_key == "test-key"
        assert client._transport == mock_transport

    async def test_client_context_manager(self, mock_transport):
        """Test client as async context manager."""
        with patch(
            "sark.services.gateway.client.GatewayHTTPClient",
            return_value=mock_transport,
        ):
            async with GatewayClient(base_url="http://test:8080") as client:
                assert client is not None

            # Verify transport was closed
            mock_transport.close.assert_called_once()

    async def test_close_client(self, client, mock_transport):
        """Test closing client closes transport."""
        await client.close()
        mock_transport.close.assert_called_once()

    async def test_list_servers(self, client, mock_transport):
        """Test list_servers delegates to transport."""
        sample_servers = [
            GatewayServerInfo(
                server_id="srv-1",
                server_name="test-server",
                server_url="http://test:8080",
                sensitivity_level="high",
                authorized_teams=["team1"],
                health_status="healthy",
                tools_count=5,
            )
        ]
        mock_transport.list_servers.return_value = sample_servers

        result = await client.list_servers(page=1, page_size=50, use_cache=False)

        assert result == sample_servers
        mock_transport.list_servers.assert_called_once_with(
            page=1,
            page_size=50,
            use_cache=False,
        )

    async def test_list_all_servers(self, client, mock_transport):
        """Test list_all_servers delegates to transport."""
        sample_servers = [
            GatewayServerInfo(
                server_id=f"srv-{i}",
                server_name=f"server-{i}",
                server_url=f"http://server{i}:8080",
                sensitivity_level="high",
                authorized_teams=["team1"],
                health_status="healthy",
                tools_count=5,
            )
            for i in range(1, 101)
        ]
        mock_transport.list_all_servers.return_value = sample_servers

        result = await client.list_all_servers(page_size=100, use_cache=True)

        assert len(result) == 100
        assert result == sample_servers
        mock_transport.list_all_servers.assert_called_once_with(
            page_size=100,
            use_cache=True,
        )

    async def test_get_server(self, client, mock_transport):
        """Test get_server delegates to transport."""
        sample_server = GatewayServerInfo(
            server_id="srv-1",
            server_name="postgres-mcp",
            server_url="http://postgres:8080",
            sensitivity_level="high",
            authorized_teams=["data-eng"],
            health_status="healthy",
            tools_count=10,
        )
        mock_transport.get_server.return_value = sample_server

        result = await client.get_server("postgres-mcp", use_cache=True)

        assert result == sample_server
        mock_transport.get_server.assert_called_once_with(
            server_name="postgres-mcp",
            use_cache=True,
        )

    async def test_list_tools(self, client, mock_transport):
        """Test list_tools delegates to transport."""
        sample_tools = [
            GatewayToolInfo(
                tool_name="execute_query",
                server_name="postgres-mcp",
                description="Execute SQL query",
                sensitivity_level="high",
                parameters=[
                    {"name": "query", "type": "string", "required": True},
                ],
            )
        ]
        mock_transport.list_tools.return_value = sample_tools

        result = await client.list_tools(
            server_name="postgres-mcp",
            page=1,
            page_size=100,
            use_cache=True,
        )

        assert result == sample_tools
        mock_transport.list_tools.assert_called_once_with(
            server_name="postgres-mcp",
            page=1,
            page_size=100,
            use_cache=True,
        )

    async def test_list_tools_no_filter(self, client, mock_transport):
        """Test list_tools without server filter."""
        mock_transport.list_tools.return_value = []

        result = await client.list_tools()

        assert result == []
        mock_transport.list_tools.assert_called_once_with(
            server_name=None,
            page=1,
            page_size=100,
            use_cache=True,
        )

    async def test_invoke_tool(self, client, mock_transport):
        """Test invoke_tool delegates to transport."""
        expected_result = {
            "status": "success",
            "result": {"rows": [{"id": 1, "name": "test"}]},
        }
        mock_transport.invoke_tool.return_value = expected_result

        result = await client.invoke_tool(
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT * FROM users LIMIT 10"},
            user_token="test-jwt-token",
            check_authorization=True,
        )

        assert result == expected_result
        mock_transport.invoke_tool.assert_called_once_with(
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT * FROM users LIMIT 10"},
            user_token="test-jwt-token",
            check_authorization=True,
        )

    async def test_invoke_tool_without_auth_check(self, client, mock_transport):
        """Test invoke_tool without authorization check."""
        mock_transport.invoke_tool.return_value = {"status": "success"}

        result = await client.invoke_tool(
            server_name="test-server",
            tool_name="test-tool",
            parameters={},
            user_token="token",
            check_authorization=False,
        )

        assert result["status"] == "success"
        mock_transport.invoke_tool.assert_called_once()
        call_args = mock_transport.invoke_tool.call_args
        assert call_args.kwargs["check_authorization"] is False

    async def test_health_check(self, client, mock_transport):
        """Test health_check delegates to transport."""
        expected_health = {
            "healthy": True,
            "details": {"status": "healthy", "uptime": 12345},
        }
        mock_transport.health_check.return_value = expected_health

        result = await client.health_check()

        assert result == expected_health
        assert result["healthy"] is True
        mock_transport.health_check.assert_called_once()

    async def test_health_check_unhealthy(self, client, mock_transport):
        """Test health_check when Gateway is unhealthy."""
        mock_transport.health_check.return_value = {
            "healthy": False,
            "error": "Connection refused",
        }

        result = await client.health_check()

        assert result["healthy"] is False
        assert "error" in result

    def test_get_cache_metrics(self, client, mock_transport):
        """Test get_cache_metrics delegates to transport."""
        expected_metrics = {
            "cache_enabled": True,
            "cache_size": 42,
            "cache_maxsize": 1000,
            "cache_hits": 850,
            "cache_misses": 150,
            "hit_rate": 0.85,
        }
        mock_transport.get_cache_metrics.return_value = expected_metrics

        result = client.get_cache_metrics()

        assert result == expected_metrics
        assert result["hit_rate"] == 0.85
        mock_transport.get_cache_metrics.assert_called_once()

    def test_clear_cache(self, client, mock_transport):
        """Test clear_cache delegates to transport."""
        client.clear_cache()
        mock_transport.clear_cache.assert_called_once()


class TestGatewayClientSingleton:
    """Test suite for singleton gateway client functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        from sark.services.gateway import client as client_module

        client_module._gateway_client = None
        yield
        client_module._gateway_client = None

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.gateway_enabled = True
        settings.gateway_url = "http://test-gateway:8080"
        settings.gateway_api_key = "test-key"
        settings.gateway_timeout_seconds = 30.0
        return settings

    async def test_get_gateway_client_creates_singleton(self, mock_settings):
        """Test get_gateway_client creates singleton instance."""
        with patch("sark.config.get_settings", return_value=mock_settings):
            with patch("sark.services.gateway.client.GatewayHTTPClient"):
                client1 = await get_gateway_client()
                client2 = await get_gateway_client()

                # Should return same instance
                assert client1 is client2

    async def test_get_gateway_client_with_disabled_gateway(self, mock_settings):
        """Test get_gateway_client when Gateway is disabled."""
        mock_settings.gateway_enabled = False

        with patch("sark.config.get_settings", return_value=mock_settings):
            with patch("sark.services.gateway.client.GatewayHTTPClient"):
                client = await get_gateway_client()

                # Should still create client but log warning
                assert client is not None

    async def test_close_gateway_client_closes_singleton(self, mock_settings):
        """Test close_gateway_client closes and resets singleton."""
        mock_transport = AsyncMock()

        with patch("sark.config.get_settings", return_value=mock_settings):
            with patch(
                "sark.services.gateway.client.GatewayHTTPClient",
                return_value=mock_transport,
            ):
                client = await get_gateway_client()
                assert client is not None

                await close_gateway_client()

                # Verify transport was closed
                mock_transport.close.assert_called_once()

                # Verify singleton was reset
                from sark.services.gateway import client as client_module

                assert client_module._gateway_client is None

    async def test_close_gateway_client_when_none(self):
        """Test close_gateway_client when no client exists."""
        # Should not raise error
        await close_gateway_client()


class TestGatewayClientParameters:
    """Test suite for GatewayClient parameter passing."""

    async def test_client_passes_all_parameters_to_transport(self):
        """Test client passes all initialization parameters to transport."""
        mock_opa = MagicMock()

        with patch("sark.services.gateway.client.GatewayHTTPClient") as MockTransport:
            mock_transport = AsyncMock()
            MockTransport.return_value = mock_transport

            client = GatewayClient(
                base_url="http://gateway:8080",
                api_key="my-api-key",
                timeout=60.0,
                max_connections=100,
                opa_client=mock_opa,
                cache_enabled=False,
                cache_ttl_seconds=600,
                max_retries=5,
            )

            # Verify transport was created with all parameters
            MockTransport.assert_called_once_with(
                base_url="http://gateway:8080",
                api_key="my-api-key",
                timeout=60.0,
                max_connections=100,
                opa_client=mock_opa,
                cache_enabled=False,
                cache_ttl_seconds=600,
                max_retries=5,
            )

            assert client._transport == mock_transport

    async def test_client_default_parameters(self):
        """Test client default parameters are passed correctly."""
        with patch("sark.services.gateway.client.GatewayHTTPClient") as MockTransport:
            mock_transport = AsyncMock()
            MockTransport.return_value = mock_transport

            client = GatewayClient(base_url="http://gateway:8080")

            # Verify defaults
            call_kwargs = MockTransport.call_args.kwargs
            assert call_kwargs["timeout"] == 30.0
            assert call_kwargs["max_connections"] == 50
            assert call_kwargs["opa_client"] is None
            assert call_kwargs["cache_enabled"] is True
            assert call_kwargs["cache_ttl_seconds"] == 300
            assert call_kwargs["max_retries"] == 3
