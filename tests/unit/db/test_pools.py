"""Unit tests for database connection pools."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import valkey.asyncio as aioredis

from sark.db import pools


@pytest.fixture(autouse=True)
def reset_pools():
    """Reset global pool instances before each test."""
    pools._redis_pool = None
    pools._http_client = None
    yield
    # Cleanup after test
    pools._redis_pool = None
    pools._http_client = None


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock()
    settings.redis_host = "localhost"
    settings.redis_port = 6379
    settings.redis_db = 0
    settings.redis_password = None
    settings.redis_pool_size = 10
    settings.redis_socket_timeout = 5
    settings.redis_socket_connect_timeout = 5
    settings.redis_socket_keepalive = True
    settings.redis_retry_on_timeout = True
    settings.redis_health_check_interval = 30
    settings.http_pool_connections = 100
    settings.http_pool_keepalive = 20
    settings.http_keepalive_expiry = 30
    return settings


class TestRedisPoolManagement:
    """Test Redis connection pool management."""

    def test_get_redis_pool_creates_pool(self, mock_settings):
        """Test that get_redis_pool creates a new pool if none exists."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            pool = pools.get_redis_pool()

            assert pool is not None
            assert isinstance(pool, aioredis.ConnectionPool)

    def test_get_redis_pool_returns_singleton(self, mock_settings):
        """Test that get_redis_pool returns the same instance on multiple calls."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            pool1 = pools.get_redis_pool()
            pool2 = pools.get_redis_pool()

            assert pool1 is pool2

    def test_get_redis_pool_configuration(self, mock_settings):
        """Test that Redis pool is configured with correct settings."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            with patch("sark.db.pools.ConnectionPool") as mock_pool_class:
                pools.get_redis_pool()

                mock_pool_class.assert_called_once()
                call_kwargs = mock_pool_class.call_args[1]

                assert call_kwargs["host"] == "localhost"
                assert call_kwargs["port"] == 6379
                assert call_kwargs["db"] == 0
                assert call_kwargs["max_connections"] == 10
                assert call_kwargs["socket_timeout"] == 5
                assert call_kwargs["decode_responses"] is True

    @pytest.mark.asyncio
    async def test_get_redis_client_uses_pool(self, mock_settings):
        """Test that get_redis_client creates client from pool."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            client = await pools.get_redis_client()

            assert isinstance(client, aioredis.Redis)
            # Verify it uses the pool
            assert client.connection_pool == pools.get_redis_pool()

    @pytest.mark.asyncio
    async def test_close_redis_pool_closes_connection(self, mock_settings):
        """Test that close_redis_pool properly closes the pool."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            # Create a pool first
            pool = pools.get_redis_pool()
            pool.disconnect = AsyncMock()

            # Close the pool
            await pools.close_redis_pool()

            pool.disconnect.assert_called_once()
            assert pools._redis_pool is None

    @pytest.mark.asyncio
    async def test_close_redis_pool_when_no_pool(self):
        """Test that close_redis_pool handles no pool gracefully."""
        # Should not raise error
        await pools.close_redis_pool()
        assert pools._redis_pool is None


class TestHTTPClientManagement:
    """Test HTTP client pool management."""

    def test_get_http_client_creates_client(self, mock_settings):
        """Test that get_http_client creates a new client if none exists."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            client = pools.get_http_client()

            assert client is not None
            assert isinstance(client, httpx.AsyncClient)

    def test_get_http_client_returns_singleton(self, mock_settings):
        """Test that get_http_client returns the same instance on multiple calls."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            client1 = pools.get_http_client()
            client2 = pools.get_http_client()

            assert client1 is client2

    def test_get_http_client_configuration(self, mock_settings):
        """Test that HTTP client is configured with correct connection pooling."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            client = pools.get_http_client()

            # Verify client configuration
            assert client.limits.max_connections == 100
            assert client.limits.max_keepalive_connections == 20
            assert client.limits.keepalive_expiry == 30
            assert client.follow_redirects is True

    @pytest.mark.asyncio
    async def test_close_http_client_closes_connection(self, mock_settings):
        """Test that close_http_client properly closes the client."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            # Create a client first
            client = pools.get_http_client()
            client.aclose = AsyncMock()

            # Close the client
            await pools.close_http_client()

            client.aclose.assert_called_once()
            assert pools._http_client is None

    @pytest.mark.asyncio
    async def test_close_http_client_when_no_client(self):
        """Test that close_http_client handles no client gracefully."""
        # Should not raise error
        await pools.close_http_client()
        assert pools._http_client is None


class TestCloseAllPools:
    """Test closing all pools at once."""

    @pytest.mark.asyncio
    async def test_close_all_pools_closes_redis_and_http(self, mock_settings):
        """Test that close_all_pools closes both Redis and HTTP pools."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            # Create both pools
            redis_pool = pools.get_redis_pool()
            http_client = pools.get_http_client()

            redis_pool.disconnect = AsyncMock()
            http_client.aclose = AsyncMock()

            # Close all
            await pools.close_all_pools()

            redis_pool.disconnect.assert_called_once()
            http_client.aclose.assert_called_once()
            assert pools._redis_pool is None
            assert pools._http_client is None

    @pytest.mark.asyncio
    async def test_close_all_pools_when_no_pools(self):
        """Test that close_all_pools handles no pools gracefully."""
        # Should not raise error
        await pools.close_all_pools()
        assert pools._redis_pool is None
        assert pools._http_client is None


class TestHealthCheckPools:
    """Test health check functionality for pools."""

    @pytest.mark.asyncio
    async def test_health_check_redis_healthy(self, mock_settings):
        """Test health check when Redis is healthy."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            with patch("sark.db.pools.get_redis_client") as mock_get_client:
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(return_value=True)
                mock_get_client.return_value = mock_client

                health = await pools.health_check_pools()

                assert health["redis"]["healthy"] is True
                assert health["redis"]["error"] is None

    @pytest.mark.asyncio
    async def test_health_check_redis_unhealthy(self, mock_settings):
        """Test health check when Redis is unhealthy."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            with patch("sark.db.pools.get_redis_client") as mock_get_client:
                mock_get_client.side_effect = Exception("Connection refused")

                health = await pools.health_check_pools()

                assert health["redis"]["healthy"] is False
                assert "Connection refused" in health["redis"]["error"]

    @pytest.mark.asyncio
    async def test_health_check_http_healthy(self, mock_settings):
        """Test health check when HTTP client is healthy."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            with patch("sark.db.pools.get_redis_client") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.ping = AsyncMock(return_value=True)
                mock_redis.return_value = mock_redis_client

                health = await pools.health_check_pools()

                assert health["http"]["healthy"] is True
                assert health["http"]["error"] is None

    @pytest.mark.asyncio
    async def test_health_check_http_unhealthy(self, mock_settings):
        """Test health check when HTTP client is unhealthy."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            with patch("sark.db.pools.get_redis_client") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.ping = AsyncMock(return_value=True)
                mock_redis.return_value = mock_redis_client

                with patch("sark.db.pools.get_http_client") as mock_http:
                    mock_http.side_effect = Exception("Client creation failed")

                    health = await pools.health_check_pools()

                    assert health["http"]["healthy"] is False
                    assert "Client creation failed" in health["http"]["error"]

    @pytest.mark.asyncio
    async def test_health_check_all_services(self, mock_settings):
        """Test health check returns status for all services."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            with patch("sark.db.pools.get_redis_client") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.ping = AsyncMock(return_value=True)
                mock_redis.return_value = mock_redis_client

                health = await pools.health_check_pools()

                assert "redis" in health
                assert "http" in health
                assert isinstance(health["redis"], dict)
                assert isinstance(health["http"], dict)
                assert "healthy" in health["redis"]
                assert "error" in health["redis"]
                assert "healthy" in health["http"]
                assert "error" in health["http"]


class TestPoolLifecycle:
    """Test pool lifecycle management."""

    @pytest.mark.asyncio
    async def test_pool_creation_and_cleanup_lifecycle(self, mock_settings):
        """Test complete lifecycle of pool creation and cleanup."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            # Pools don't exist initially
            assert pools._redis_pool is None
            assert pools._http_client is None

            # Create pools
            redis_pool = pools.get_redis_pool()
            http_client = pools.get_http_client()

            assert redis_pool is not None
            assert http_client is not None
            assert pools._redis_pool is redis_pool
            assert pools._http_client is http_client

            # Mock cleanup methods
            redis_pool.disconnect = AsyncMock()
            http_client.aclose = AsyncMock()

            # Cleanup
            await pools.close_all_pools()

            assert pools._redis_pool is None
            assert pools._http_client is None

    def test_pool_singleton_behavior(self, mock_settings):
        """Test that multiple get calls don't create multiple pools."""
        with patch("sark.db.pools.get_settings", return_value=mock_settings):
            # Get pools multiple times
            redis1 = pools.get_redis_pool()
            redis2 = pools.get_redis_pool()
            redis3 = pools.get_redis_pool()

            http1 = pools.get_http_client()
            http2 = pools.get_http_client()
            http3 = pools.get_http_client()

            # All should be the same instance
            assert redis1 is redis2 is redis3
            assert http1 is http2 is http3


class TestPoolSettings:
    """Test pool configuration with different settings."""

    def test_redis_pool_with_password(self):
        """Test Redis pool creation with password."""
        settings = Mock()
        settings.redis_host = "secure-redis.example.com"
        settings.redis_port = 6380
        settings.redis_db = 1
        settings.redis_password = "secret_password"
        settings.redis_pool_size = 20
        settings.redis_socket_timeout = 10
        settings.redis_socket_connect_timeout = 10
        settings.redis_socket_keepalive = True
        settings.redis_retry_on_timeout = True
        settings.redis_health_check_interval = 60

        with patch("sark.db.pools.get_settings", return_value=settings):
            with patch("sark.db.pools.ConnectionPool") as mock_pool_class:
                pools.get_redis_pool()

                call_kwargs = mock_pool_class.call_args[1]
                assert call_kwargs["password"] == "secret_password"
                assert call_kwargs["host"] == "secure-redis.example.com"
                assert call_kwargs["port"] == 6380
                assert call_kwargs["db"] == 1

    def test_http_client_with_custom_limits(self):
        """Test HTTP client creation with custom connection limits."""
        settings = Mock()
        settings.redis_host = "localhost"
        settings.redis_port = 6379
        settings.redis_db = 0
        settings.redis_password = None
        settings.redis_pool_size = 10
        settings.redis_socket_timeout = 5
        settings.redis_socket_connect_timeout = 5
        settings.redis_socket_keepalive = True
        settings.redis_retry_on_timeout = True
        settings.redis_health_check_interval = 30
        settings.http_pool_connections = 500
        settings.http_pool_keepalive = 100
        settings.http_keepalive_expiry = 60

        with patch("sark.db.pools.get_settings", return_value=settings):
            client = pools.get_http_client()

            assert client.limits.max_connections == 500
            assert client.limits.max_keepalive_connections == 100
            assert client.limits.keepalive_expiry == 60
