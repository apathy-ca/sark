"""Centralized connection pool management for Redis and HTTP clients.

This module provides singleton connection pool managers to ensure efficient
connection reuse across the application, reducing connection overhead and
improving performance.
"""

import logging
from typing import Any

import httpx
import valkey.asyncio as aioredis
from valkey.asyncio import ConnectionPool

from sark.config import get_settings

logger = logging.getLogger(__name__)

# Global connection pool instances (lazy-loaded singletons)
_redis_pool: ConnectionPool | None = None
_http_client: httpx.AsyncClient | None = None


def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool.

    Returns:
        Redis ConnectionPool instance configured with settings
    """
    global _redis_pool

    if _redis_pool is None:
        settings = get_settings()

        logger.info(
            "Creating Redis connection pool",
            extra={
                "host": settings.redis_host,
                "port": settings.redis_port,
                "max_connections": settings.redis_pool_size,
            },
        )

        _redis_pool = ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            # Connection pool settings
            max_connections=settings.redis_pool_size,
            # Socket settings
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_keepalive=settings.redis_socket_keepalive,
            # Retry settings
            retry_on_timeout=settings.redis_retry_on_timeout,
            # Health check
            health_check_interval=settings.redis_health_check_interval,
            # Decode responses to strings
            decode_responses=True,
        )

    return _redis_pool


async def get_redis_client() -> aioredis.Redis:
    """Get Redis client from connection pool.

    Returns:
        Redis client instance using the shared connection pool
    """
    pool = get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


def get_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client with connection pooling.

    This creates a single AsyncClient instance shared across the application,
    which internally manages a connection pool for better performance.

    Returns:
        httpx.AsyncClient instance with configured connection pooling
    """
    global _http_client

    if _http_client is None:
        settings = get_settings()

        logger.info(
            "Creating HTTP client connection pool",
            extra={
                "max_connections": settings.http_pool_connections,
                "max_keepalive": settings.http_pool_keepalive,
            },
        )

        # Create limits for connection pooling
        limits = httpx.Limits(
            # Maximum number of concurrent connections in the pool
            max_connections=settings.http_pool_connections,
            # Maximum number of connections to keep alive
            max_keepalive_connections=settings.http_pool_keepalive,
            # Seconds to keep idle connections alive
            keepalive_expiry=settings.http_keepalive_expiry,
        )

        # Create the async client with connection pooling
        _http_client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(5.0),  # Default timeout
            follow_redirects=True,
            http2=True,  # Enable HTTP/2 for better performance
        )

    return _http_client


async def close_redis_pool() -> None:
    """Close Redis connection pool.

    Should be called during application shutdown.
    """
    global _redis_pool

    if _redis_pool is not None:
        logger.info("Closing Redis connection pool")
        await _redis_pool.disconnect()
        _redis_pool = None


async def close_http_client() -> None:
    """Close HTTP client connection pool.

    Should be called during application shutdown.
    """
    global _http_client

    if _http_client is not None:
        logger.info("Closing HTTP client connection pool")
        await _http_client.aclose()
        _http_client = None


async def close_all_pools() -> None:
    """Close all connection pools.

    Should be called during application shutdown.
    """
    logger.info("Closing all connection pools")
    await close_redis_pool()
    await close_http_client()


async def health_check_pools() -> dict[str, Any]:
    """Health check for all connection pools.

    Returns:
        Dictionary with health status of all pools
    """
    health = {
        "redis": {"healthy": False, "error": None},
        "http": {"healthy": False, "error": None},
    }

    # Check Redis
    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        health["redis"]["healthy"] = True
    except Exception as e:
        health["redis"]["error"] = str(e)
        logger.error(f"Redis health check failed: {e}")

    # Check HTTP client
    try:
        http_client = get_http_client()
        # HTTP client is healthy if it exists (no easy way to test without making a request)
        health["http"]["healthy"] = http_client is not None
    except Exception as e:
        health["http"]["error"] = str(e)
        logger.error(f"HTTP client health check failed: {e}")

    return health
