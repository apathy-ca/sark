"""
Redis cache utilities for SARK application.

This module provides Redis cache connection management,
supporting both managed (Docker Compose) and external enterprise deployments,
including Redis Sentinel for high availability.
"""

import logging
from typing import Any

from valkey import Redis
from valkey.sentinel import Sentinel

from sark.config import RedisConfig

logger = logging.getLogger(__name__)


class CacheManager:
    """Manager for Redis cache connections."""

    def __init__(self, config: RedisConfig):
        """
        Initialize cache manager.

        Args:
            config: Redis configuration
        """
        self.config = config
        self._client: Redis | None = None
        self._sentinel: Sentinel | None = None

        logger.info(
            f"Initialized CacheManager in {config.mode} mode: "
            f"host={config.host}, port={config.port}, sentinel={config.sentinel_enabled}"
        )

    @property
    def client(self) -> Redis:
        """
        Get or create Redis client.

        Returns:
            Redis client instance

        Raises:
            ValueError: If configuration is invalid
        """
        if self._client is None:
            if self.config.sentinel_enabled:
                self._client = self._create_sentinel_client()
            else:
                self._client = self._create_direct_client()

            logger.info(
                f"Created Redis client: {self.config.host}:{self.config.port} "
                f"(sentinel={self.config.sentinel_enabled})"
            )

        return self._client

    def _create_direct_client(self) -> Redis:
        """
        Create a direct Redis client connection.

        Returns:
            Redis client instance
        """
        return Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.database,
            password=self.config.password,
            max_connections=self.config.max_connections,
            ssl=self.config.ssl,
            decode_responses=True,  # Automatically decode responses to strings
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )

    def _create_sentinel_client(self) -> Redis:
        """
        Create a Redis client using Sentinel for high availability.

        Returns:
            Redis client instance

        Raises:
            ValueError: If sentinel configuration is invalid
        """
        if not self.config.sentinel_hosts:
            raise ValueError("VALKEY_SENTINEL_HOSTS must be set when sentinel is enabled")

        if not self.config.sentinel_service_name:
            raise ValueError("VALKEY_SENTINEL_SERVICE_NAME must be set when sentinel is enabled")

        # Parse sentinel hosts (format: "host1:port1,host2:port2,host3:port3")
        sentinel_nodes = []
        for node in self.config.sentinel_hosts.split(","):
            parts = node.strip().split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid sentinel host format: {node}")
            host = parts[0]
            port = int(parts[1])
            sentinel_nodes.append((host, port))

        logger.info(f"Connecting to Redis Sentinel: {sentinel_nodes}")

        # Create Sentinel instance
        self._sentinel = Sentinel(
            sentinel_nodes,
            socket_timeout=5,
            password=self.config.password,
            ssl=self.config.ssl,
        )

        # Get master client
        return self._sentinel.master_for(
            self.config.sentinel_service_name,
            socket_timeout=5,
            db=self.config.database,
            decode_responses=True,
        )

    def get(self, key: str) -> str | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting key '{key}' from cache: {e}")
            return None

    def set(self, key: str, value: str | bytes | int | float, expire: int | None = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.client.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Error setting key '{key}' in cache: {e}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete keys from cache.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Error deleting keys from cache: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """
        Check if keys exist in cache.

        Args:
            *keys: Keys to check

        Returns:
            Number of existing keys
        """
        try:
            return self.client.exists(*keys)
        except Exception as e:
            logger.error(f"Error checking key existence in cache: {e}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Error setting expiration for key '{key}': {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> int | None:
        """
        Increment a counter.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment, or None if error
        """
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing key '{key}': {e}")
            return None

    def flush_db(self) -> bool:
        """
        Flush the current database (use with caution!).

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.flushdb()
            logger.warning("Flushed Redis database")
            return True
        except Exception as e:
            logger.error(f"Error flushing database: {e}")
            return False

    def test_connection(self) -> dict[str, Any]:
        """
        Test Redis connection and return diagnostic information.

        Returns:
            Dictionary containing connection test results
        """
        result = {
            "mode": self.config.mode.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "sentinel_enabled": self.config.sentinel_enabled,
            "connected": False,
            "version": None,
            "error": None,
        }

        try:
            # Test connection with ping
            ping_result = self.client.ping()
            if ping_result:
                result["connected"] = True

                # Get server info
                info = self.client.info("server")
                result["version"] = info.get("redis_version")

                logger.info(f"Redis connection test successful: version={result['version']}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Redis connection test failed: {e}")

        return result

    def health_check(self) -> bool:
        """
        Check if Redis is healthy and accessible.

        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            ping_result = self.client.ping()
            logger.info("Redis health check successful")
            return ping_result
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def get_info(self) -> dict[str, Any]:
        """
        Get Redis server information.

        Returns:
            Redis server info dictionary
        """
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {}

    def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            self._client.close()
            logger.info("Closed Redis connection")
            self._client = None

    def __enter__(self) -> "CacheManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def create_cache_manager(config: RedisConfig | None = None) -> CacheManager | None:
    """
    Create a cache manager instance.

    Args:
        config: Redis configuration (if None, loads from environment)

    Returns:
        CacheManager instance if Redis is enabled, None otherwise
    """
    if config is None:
        from sark.config import get_config

        app_config = get_config()
        config = app_config.redis

    if not config.enabled:
        logger.info("Redis is not enabled")
        return None

    return CacheManager(config)


def verify_cache_connectivity(config: RedisConfig | None = None) -> bool:
    """
    Verify connectivity to Redis cache.

    Args:
        config: Redis configuration (if None, loads from environment)

    Returns:
        True if Redis is accessible, False otherwise
    """
    manager = create_cache_manager(config)
    if manager is None:
        return False

    try:
        return manager.health_check()
    finally:
        manager.close()
