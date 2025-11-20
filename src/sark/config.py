"""
Configuration management for SARK application.

This module provides a flexible configuration system that supports both:
- Managed services (deployed via Docker Compose)
- External services (existing enterprise deployments)

Environment variables control which mode is used for each service.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ServiceMode(str, Enum):
    """Service deployment mode."""

    MANAGED = "managed"  # Service deployed via Docker Compose
    EXTERNAL = "external"  # Service hosted externally


@dataclass
class PostgreSQLConfig:
    """PostgreSQL database configuration."""

    enabled: bool
    mode: ServiceMode
    host: str
    port: int
    database: str
    user: str
    password: str
    pool_size: int
    max_overflow: int
    ssl_mode: str

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        ssl_param = f"?sslmode={self.ssl_mode}" if self.ssl_mode != "disable" else ""
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}{ssl_param}"
        )

    @classmethod
    def from_env(cls) -> "PostgreSQLConfig":
        """Load PostgreSQL configuration from environment variables."""
        mode = ServiceMode(os.getenv("POSTGRES_MODE", "managed"))

        # Default values depend on mode
        if mode == ServiceMode.MANAGED:
            default_host = "database"  # Docker Compose service name
            default_port = 5432
        else:
            default_host = os.getenv("POSTGRES_HOST", "localhost")
            default_port = int(os.getenv("POSTGRES_PORT", "5432"))

        return cls(
            enabled=os.getenv("POSTGRES_ENABLED", "false").lower() == "true",
            mode=mode,
            host=os.getenv("POSTGRES_HOST", default_host),
            port=int(os.getenv("POSTGRES_PORT", str(default_port))),
            database=os.getenv("POSTGRES_DB", "sark"),
            user=os.getenv("POSTGRES_USER", "sark"),
            password=os.getenv("POSTGRES_PASSWORD", "sark"),
            pool_size=int(os.getenv("POSTGRES_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("POSTGRES_MAX_OVERFLOW", "10")),
            ssl_mode=os.getenv("POSTGRES_SSL_MODE", "disable"),
        )


@dataclass
class RedisConfig:
    """Redis cache configuration."""

    enabled: bool
    mode: ServiceMode
    host: str
    port: int
    database: int
    password: Optional[str]
    max_connections: int
    ssl: bool
    sentinel_enabled: bool
    sentinel_service_name: Optional[str]
    sentinel_hosts: Optional[str]

    @property
    def connection_url(self) -> str:
        """Generate Redis connection URL."""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Load Redis configuration from environment variables."""
        mode = ServiceMode(os.getenv("REDIS_MODE", "managed"))

        # Default values depend on mode
        if mode == ServiceMode.MANAGED:
            default_host = "cache"  # Docker Compose service name
            default_port = 6379
        else:
            default_host = os.getenv("REDIS_HOST", "localhost")
            default_port = int(os.getenv("REDIS_PORT", "6379"))

        return cls(
            enabled=os.getenv("REDIS_ENABLED", "false").lower() == "true",
            mode=mode,
            host=os.getenv("REDIS_HOST", default_host),
            port=int(os.getenv("REDIS_PORT", str(default_port))),
            database=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
            sentinel_enabled=os.getenv("REDIS_SENTINEL_ENABLED", "false").lower() == "true",
            sentinel_service_name=os.getenv("REDIS_SENTINEL_SERVICE_NAME"),
            sentinel_hosts=os.getenv("REDIS_SENTINEL_HOSTS"),
        )


@dataclass
class KongConfig:
    """Kong API Gateway configuration."""

    enabled: bool
    mode: ServiceMode
    admin_url: str
    proxy_url: str
    admin_api_key: Optional[str]
    workspace: str
    verify_ssl: bool
    timeout: int
    retries: int

    @classmethod
    def from_env(cls) -> "KongConfig":
        """Load Kong configuration from environment variables."""
        mode = ServiceMode(os.getenv("KONG_MODE", "managed"))

        # Default values depend on mode
        if mode == ServiceMode.MANAGED:
            default_admin_url = "http://kong:8001"
            default_proxy_url = "http://kong:8000"
        else:
            default_admin_url = os.getenv("KONG_ADMIN_URL", "http://localhost:8001")
            default_proxy_url = os.getenv("KONG_PROXY_URL", "http://localhost:8000")

        return cls(
            enabled=os.getenv("KONG_ENABLED", "false").lower() == "true",
            mode=mode,
            admin_url=os.getenv("KONG_ADMIN_URL", default_admin_url),
            proxy_url=os.getenv("KONG_PROXY_URL", default_proxy_url),
            admin_api_key=os.getenv("KONG_ADMIN_API_KEY"),
            workspace=os.getenv("KONG_WORKSPACE", "default"),
            verify_ssl=os.getenv("KONG_VERIFY_SSL", "true").lower() == "true",
            timeout=int(os.getenv("KONG_TIMEOUT", "30")),
            retries=int(os.getenv("KONG_RETRIES", "3")),
        )


@dataclass
class AppConfig:
    """Main application configuration."""

    environment: str
    debug: bool
    log_level: str
    postgres: PostgreSQLConfig
    redis: RedisConfig
    kong: KongConfig

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load complete application configuration from environment variables."""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            postgres=PostgreSQLConfig.from_env(),
            redis=RedisConfig.from_env(),
            kong=KongConfig.from_env(),
        )

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate PostgreSQL configuration
        if self.postgres.enabled and self.postgres.mode == ServiceMode.EXTERNAL:
            if not self.postgres.host or self.postgres.host == "database":
                errors.append(
                    "POSTGRES_HOST must be set when using external PostgreSQL deployment"
                )
            if self.postgres.password == "sark" and self.environment == "production":
                errors.append("POSTGRES_PASSWORD must be changed in production")

        # Validate Redis configuration
        if self.redis.enabled and self.redis.mode == ServiceMode.EXTERNAL:
            if not self.redis.host or self.redis.host == "cache":
                errors.append("REDIS_HOST must be set when using external Redis deployment")
            if self.redis.sentinel_enabled and not self.redis.sentinel_hosts:
                errors.append(
                    "REDIS_SENTINEL_HOSTS must be set when Redis Sentinel is enabled"
                )

        # Validate Kong configuration
        if self.kong.enabled and self.kong.mode == ServiceMode.EXTERNAL:
            if not self.kong.admin_url or "kong:" in self.kong.admin_url:
                errors.append("KONG_ADMIN_URL must be set when using external Kong deployment")
            if not self.kong.proxy_url or "kong:" in self.kong.proxy_url:
                errors.append("KONG_PROXY_URL must be set when using external Kong deployment")
            if not self.kong.admin_api_key and self.environment == "production":
                errors.append(
                    "KONG_ADMIN_API_KEY should be set for secure external Kong deployment"
                )

        return errors


# Global configuration instance (lazy-loaded)
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get the global configuration instance.

    Returns:
        AppConfig: The application configuration

    Raises:
        ValueError: If configuration validation fails
    """
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        errors = _config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(errors))
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None
