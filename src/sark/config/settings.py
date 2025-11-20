"""SARK configuration settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SARK application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SARK"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = False
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = False

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars",
        min_length=32,
    )
    access_token_expire_minutes: int = 15
    cors_origins: list[str] = ["http://localhost:3000"]

    # PostgreSQL Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "sark"
    postgres_password: str = "sark"
    postgres_db: str = "sark"
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 10

    # TimescaleDB (Audit Database) - can be same as PostgreSQL or separate
    timescale_host: str = "localhost"
    timescale_port: int = 5432
    timescale_user: str = "sark"
    timescale_password: str = "sark"
    timescale_db: str = "sark_audit"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: int = 0
    redis_pool_size: int = 50

    # Consul
    consul_host: str = "localhost"
    consul_port: int = 8500
    consul_scheme: str = "http"
    consul_token: str | None = None

    # Open Policy Agent (OPA)
    opa_url: str = "http://localhost:8181"
    opa_policy_path: str = "/v1/data/mcp/allow"
    opa_timeout_seconds: float = 1.0

    # HashiCorp Vault
    vault_url: str = "http://localhost:8200"
    vault_token: str | None = None
    vault_namespace: str | None = None
    vault_mount_point: str = "secret"

    # Kafka (optional - for audit pipeline at scale)
    kafka_enabled: bool = False
    kafka_bootstrap_servers: list[str] = ["localhost:9092"]
    kafka_audit_topic: str = "sark-audit-events"
    kafka_consumer_group: str = "sark-audit-consumers"

    # Discovery Service
    discovery_interval_seconds: int = 300  # 5 minutes
    discovery_network_scan_enabled: bool = False
    discovery_k8s_enabled: bool = False
    discovery_cloud_enabled: bool = False

    # Audit Configuration
    audit_batch_size: int = 100
    audit_flush_interval_seconds: int = 5
    audit_retention_days: int = 90

    # Observability
    metrics_enabled: bool = True
    metrics_port: int = 9090
    tracing_enabled: bool = False
    tracing_endpoint: str | None = None

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("kafka_bootstrap_servers", pre=True)
    def parse_kafka_servers(cls, v: Any) -> list[str]:
        """Parse Kafka bootstrap servers from comma-separated string or list."""
        if isinstance(v, str):
            return [server.strip() for server in v.split(",")]
        return v

    @property
    def postgres_dsn(self) -> str:
        """Construct PostgreSQL connection string."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def timescale_dsn(self) -> str:
        """Construct TimescaleDB connection string."""
        return (
            f"postgresql+asyncpg://{self.timescale_user}:{self.timescale_password}"
            f"@{self.timescale_host}:{self.timescale_port}/{self.timescale_db}"
        )

    @property
    def redis_dsn(self) -> str:
        """Construct Redis connection string."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
