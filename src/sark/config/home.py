"""Home deployment configuration for SARK.

This module provides configuration optimized for low-resource home deployments,
targeting OPNsense routers with limited resources (512MB RAM, single core).

Key differences from enterprise deployment:
- SQLite instead of PostgreSQL/TimescaleDB
- Embedded OPA instead of external OPA server
- In-memory caching instead of Redis/Valkey
- Single worker process instead of multiple
- Local audit logging instead of SIEM integration
"""

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Home deployment constants
HOME_DEFAULT_DB_PATH = "/var/db/sark/home.db"
HOME_DEFAULT_AUDIT_PATH = "/var/db/sark/audit.db"
HOME_DEFAULT_POLICIES_DIR = "/usr/local/etc/sark/policies"
HOME_DEFAULT_LOG_DIR = "/var/log/sark"
HOME_DEFAULT_CONFIG_DIR = "/usr/local/etc/sark"


@dataclass
class HomeResourceLimits:
    """Resource limits for home deployment.

    Optimized for OPNsense routers with limited resources.
    """

    max_memory_mb: int = 256
    """Maximum memory usage in MB (target: 256MB, max: 512MB)"""

    worker_processes: int = 1
    """Number of worker processes (single core operation)"""

    max_connections: int = 50
    """Maximum concurrent connections"""

    request_timeout_seconds: int = 30
    """Request timeout in seconds"""

    max_request_size_kb: int = 1024
    """Maximum request body size in KB (1MB default)"""


@dataclass
class HomeDatabaseConfig:
    """SQLite database configuration for home deployment."""

    main_database: str = HOME_DEFAULT_DB_PATH
    """Path to main SQLite database"""

    audit_database: str = HOME_DEFAULT_AUDIT_PATH
    """Path to audit SQLite database"""

    pool_size: int = 5
    """SQLite connection pool size (smaller for home)"""

    journal_mode: str = "WAL"
    """SQLite journal mode (WAL for better concurrency)"""

    synchronous: str = "NORMAL"
    """SQLite synchronous mode (NORMAL balances safety/performance)"""

    cache_size_kb: int = 2048
    """SQLite cache size in KB (2MB default)"""

    def __post_init__(self) -> None:
        """Validate database configuration."""
        # Ensure database directories exist
        for db_path in [self.main_database, self.audit_database]:
            if db_path.startswith("/"):
                db_dir = Path(db_path).parent
                if not db_dir.exists():
                    db_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class HomeOPAConfig:
    """OPA configuration for home deployment using embedded mode."""

    mode: Literal["embedded", "external"] = "embedded"
    """OPA mode: embedded (default for home) or external"""

    policies_dir: str = HOME_DEFAULT_POLICIES_DIR
    """Directory containing Rego policy files"""

    default_policy: str = "home_default.rego"
    """Default policy file to load"""

    cache_ttl_seconds: int = 300
    """Policy decision cache TTL (5 minutes)"""

    external_url: str = "http://localhost:8181"
    """OPA URL when using external mode"""

    def __post_init__(self) -> None:
        """Validate OPA configuration."""
        if self.mode == "embedded":
            policies_path = Path(self.policies_dir)
            if not policies_path.exists():
                policies_path.mkdir(parents=True, exist_ok=True)


@dataclass
class HomeAuditConfig:
    """Audit logging configuration for home deployment."""

    enabled: bool = True
    """Enable audit logging"""

    retention_days: int = 365
    """Audit log retention in days (1 year default)"""

    prompt_preview_length: int = 200
    """Characters to store from prompt preview (privacy-aware)"""

    log_responses: bool = True
    """Log response metadata"""

    detect_sensitive: bool = True
    """Detect and flag sensitive/PII content in prompts"""

    export_format: str = "csv"
    """Default export format for audit logs"""


@dataclass
class HomeProxyConfig:
    """Proxy configuration for home deployment."""

    listen_host: str = "0.0.0.0"
    """Host to listen on"""

    listen_port: int = 8443
    """Port to listen on (HTTPS)"""

    tls_enabled: bool = True
    """Enable TLS termination"""

    tls_cert_path: str = "/usr/local/etc/sark/certs/server.crt"
    """Path to TLS certificate"""

    tls_key_path: str = "/usr/local/etc/sark/certs/server.key"
    """Path to TLS private key"""

    ca_cert_path: str = "/usr/local/etc/sark/certs/ca.crt"
    """Path to CA certificate for client verification"""

    upstream_timeout_seconds: int = 60
    """Timeout for upstream LLM API requests"""

    max_retries: int = 2
    """Maximum retries for failed upstream requests"""


@dataclass
class HomeCacheConfig:
    """In-memory cache configuration for home deployment.

    Uses simple in-memory caching instead of Redis/Valkey.
    """

    enabled: bool = True
    """Enable in-memory caching"""

    max_size_mb: int = 32
    """Maximum cache size in MB"""

    default_ttl_seconds: int = 300
    """Default TTL for cached items (5 minutes)"""

    policy_cache_ttl_seconds: int = 600
    """TTL for cached policy decisions (10 minutes)"""


@dataclass
class HomeEndpointConfig:
    """LLM endpoint configuration."""

    domain: str
    """Domain to intercept (e.g., api.openai.com)"""

    enabled: bool = True
    """Whether interception is enabled for this endpoint"""

    name: str = ""
    """Human-readable name for this endpoint"""

    def __post_init__(self) -> None:
        """Set default name if not provided."""
        if not self.name:
            self.name = self.domain.split(".")[0].upper()


# Default LLM endpoints for home deployment
DEFAULT_HOME_ENDPOINTS = [
    HomeEndpointConfig(domain="api.openai.com", name="OpenAI"),
    HomeEndpointConfig(domain="api.anthropic.com", name="Anthropic"),
    HomeEndpointConfig(domain="generativelanguage.googleapis.com", name="Google AI"),
    HomeEndpointConfig(domain="api.mistral.ai", name="Mistral"),
    HomeEndpointConfig(domain="api.cohere.ai", name="Cohere"),
]


class HomeSettings(BaseSettings):
    """Home deployment settings loaded from environment.

    Pydantic settings class that reads from environment variables
    with SARK_HOME_ prefix and .env.home file.
    """

    model_config = SettingsConfigDict(
        env_prefix="SARK_HOME_",
        env_file=".env.home",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SARK Home"
    app_version: str = "2.0.0"
    environment: Literal["development", "production"] = "production"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_file: str = f"{HOME_DEFAULT_LOG_DIR}/sark-home.log"

    # Deployment mode
    mode: Literal["observe", "advisory", "enforce"] = "observe"
    """
    Operation mode:
    - observe: Log all LLM traffic, no blocking
    - advisory: Log and alert on policy violations, no blocking
    - enforce: Log, alert, and optionally block based on policies
    """

    # Server
    host: str = "0.0.0.0"
    port: int = 8443
    workers: int = 1

    # Database paths
    db_path: str = HOME_DEFAULT_DB_PATH
    audit_db_path: str = HOME_DEFAULT_AUDIT_PATH

    # Policy
    policies_dir: str = HOME_DEFAULT_POLICIES_DIR
    opa_mode: Literal["embedded", "external"] = "embedded"
    opa_url: str = "http://localhost:8181"

    # TLS
    tls_enabled: bool = True
    tls_cert_path: str = "/usr/local/etc/sark/certs/server.crt"
    tls_key_path: str = "/usr/local/etc/sark/certs/server.key"

    # Resource limits
    max_memory_mb: int = 256
    max_connections: int = 50

    # Audit
    audit_enabled: bool = True
    audit_retention_days: int = 365
    audit_prompt_preview: bool = True
    audit_prompt_preview_length: int = 200

    # Cache
    cache_enabled: bool = True
    cache_size_mb: int = 32
    cache_ttl_seconds: int = 300

    # Alerts (advisory/enforce modes)
    alerts_enabled: bool = False
    alerts_email: str | None = None
    alerts_pushover_token: str | None = None
    alerts_pushover_user: str | None = None

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        """Validate and normalize log level."""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("db_path", "audit_db_path", mode="after")
    @classmethod
    def validate_db_path(cls, v: str) -> str:
        """Validate database path is SQLite."""
        if not v.endswith(".db") and not v.startswith("sqlite:"):
            logger.warning(
                f"Database path {v} does not appear to be SQLite. "
                "Home deployment requires SQLite."
            )
        return v

    @field_validator("max_memory_mb", mode="after")
    @classmethod
    def validate_memory(cls, v: int) -> int:
        """Validate memory limit is within home deployment range."""
        if v > 512:
            logger.warning(
                f"Memory limit {v}MB exceeds recommended 512MB for home deployment. "
                "This may cause issues on resource-constrained routers."
            )
        return v


@dataclass
class HomeDeploymentConfig:
    """Complete configuration for home deployment profile.

    This dataclass aggregates all configuration components for
    home deployment, optimized for low-resource environments
    like OPNsense routers.

    Usage:
        config = HomeDeploymentConfig.from_settings()
        # or with custom settings
        settings = HomeSettings()
        config = HomeDeploymentConfig.from_settings(settings)
    """

    # Settings from environment
    settings: HomeSettings = field(default_factory=HomeSettings)

    # Component configurations
    resources: HomeResourceLimits = field(default_factory=HomeResourceLimits)
    database: HomeDatabaseConfig = field(default_factory=HomeDatabaseConfig)
    opa: HomeOPAConfig = field(default_factory=HomeOPAConfig)
    audit: HomeAuditConfig = field(default_factory=HomeAuditConfig)
    proxy: HomeProxyConfig = field(default_factory=HomeProxyConfig)
    cache: HomeCacheConfig = field(default_factory=HomeCacheConfig)

    # LLM endpoints to intercept
    endpoints: list[HomeEndpointConfig] = field(default_factory=lambda: DEFAULT_HOME_ENDPOINTS.copy())

    def __post_init__(self) -> None:
        """Initialize configuration from settings."""
        self._sync_from_settings()
        self._validate()

    def _sync_from_settings(self) -> None:
        """Synchronize component configs from settings."""
        s = self.settings

        # Resources
        self.resources.max_memory_mb = s.max_memory_mb
        self.resources.worker_processes = s.workers
        self.resources.max_connections = s.max_connections

        # Database
        self.database.main_database = s.db_path
        self.database.audit_database = s.audit_db_path

        # OPA
        self.opa.mode = s.opa_mode
        self.opa.policies_dir = s.policies_dir
        self.opa.external_url = s.opa_url

        # Audit
        self.audit.enabled = s.audit_enabled
        self.audit.retention_days = s.audit_retention_days
        self.audit.prompt_preview_length = s.audit_prompt_preview_length if s.audit_prompt_preview else 0

        # Proxy
        self.proxy.listen_host = s.host
        self.proxy.listen_port = s.port
        self.proxy.tls_enabled = s.tls_enabled
        self.proxy.tls_cert_path = s.tls_cert_path
        self.proxy.tls_key_path = s.tls_key_path

        # Cache
        self.cache.enabled = s.cache_enabled
        self.cache.max_size_mb = s.cache_size_mb
        self.cache.default_ttl_seconds = s.cache_ttl_seconds

    def _validate(self) -> None:
        """Validate overall configuration."""
        # Validate SQLite database paths
        for db_path in [self.database.main_database, self.database.audit_database]:
            if "postgresql" in db_path.lower() or "postgres" in db_path.lower():
                raise ValueError(
                    f"Home deployment requires SQLite, got PostgreSQL path: {db_path}"
                )

        # Validate resource limits for home deployment
        if self.resources.max_memory_mb > 512:
            logger.warning(
                f"Memory limit {self.resources.max_memory_mb}MB exceeds "
                "recommended 512MB for home deployment."
            )

        if self.resources.worker_processes > 2:
            logger.warning(
                f"Worker count {self.resources.worker_processes} exceeds "
                "recommended 1-2 workers for single-core home deployment."
            )

    @property
    def mode(self) -> str:
        """Get the current operation mode."""
        return self.settings.mode

    @property
    def is_observe_mode(self) -> bool:
        """Check if running in observe-only mode."""
        return self.settings.mode == "observe"

    @property
    def is_advisory_mode(self) -> bool:
        """Check if running in advisory mode."""
        return self.settings.mode == "advisory"

    @property
    def is_enforce_mode(self) -> bool:
        """Check if running in enforce mode."""
        return self.settings.mode == "enforce"

    @property
    def can_block(self) -> bool:
        """Check if blocking is enabled (enforce mode only)."""
        return self.settings.mode == "enforce"

    @property
    def sqlite_main_dsn(self) -> str:
        """Get SQLite DSN for main database."""
        path = self.database.main_database
        if path.startswith("sqlite:"):
            return path
        return f"sqlite:///{path}"

    @property
    def sqlite_audit_dsn(self) -> str:
        """Get SQLite DSN for audit database."""
        path = self.database.audit_database
        if path.startswith("sqlite:"):
            return path
        return f"sqlite:///{path}"

    @classmethod
    def from_settings(cls, settings: HomeSettings | None = None) -> "HomeDeploymentConfig":
        """Create configuration from settings.

        Args:
            settings: Optional HomeSettings instance. If not provided,
                      loads from environment.

        Returns:
            HomeDeploymentConfig instance.
        """
        if settings is None:
            settings = HomeSettings()
        return cls(settings=settings)

    @classmethod
    def from_env(cls) -> "HomeDeploymentConfig":
        """Create configuration from environment variables.

        Convenience method that loads settings from environment.

        Returns:
            HomeDeploymentConfig instance.
        """
        return cls.from_settings(HomeSettings())

    def to_dict(self) -> dict[str, Any]:
        """Export configuration as dictionary.

        Useful for serialization and debugging.
        """
        return {
            "mode": self.mode,
            "environment": self.settings.environment,
            "debug": self.settings.debug,
            "resources": {
                "max_memory_mb": self.resources.max_memory_mb,
                "worker_processes": self.resources.worker_processes,
                "max_connections": self.resources.max_connections,
            },
            "database": {
                "main": self.database.main_database,
                "audit": self.database.audit_database,
                "pool_size": self.database.pool_size,
            },
            "opa": {
                "mode": self.opa.mode,
                "policies_dir": self.opa.policies_dir,
            },
            "proxy": {
                "host": self.proxy.listen_host,
                "port": self.proxy.listen_port,
                "tls_enabled": self.proxy.tls_enabled,
            },
            "audit": {
                "enabled": self.audit.enabled,
                "retention_days": self.audit.retention_days,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "max_size_mb": self.cache.max_size_mb,
            },
            "endpoints": [
                {"domain": e.domain, "name": e.name, "enabled": e.enabled}
                for e in self.endpoints
            ],
        }


@lru_cache
def get_home_settings() -> HomeSettings:
    """Get cached home settings instance."""
    return HomeSettings()


@lru_cache
def get_home_config() -> HomeDeploymentConfig:
    """Get cached home deployment configuration instance."""
    return HomeDeploymentConfig.from_settings(get_home_settings())
