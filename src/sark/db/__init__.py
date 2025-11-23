"""Database connection and session management."""

from sark.db.base import Base
from sark.db.pools import (
    close_all_pools,
    close_http_client,
    close_redis_pool,
    get_http_client,
    get_redis_client,
    get_redis_pool,
    health_check_pools,
)
from sark.db.session import get_db, get_timescale_db, init_db

__all__ = [
    "Base",
    "close_all_pools",
    "close_http_client",
    "close_redis_pool",
    "get_db",
    "get_http_client",
    "get_redis_client",
    "get_redis_pool",
    "get_timescale_db",
    "health_check_pools",
    "init_db",
]
