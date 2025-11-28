"""SARK configuration settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
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

    # JWT Configuration
    jwt_secret_key: str | None = None  # For HS256, defaults to secret_key if not set
    jwt_public_key: str | None = None  # For RS256 (PEM format)
    jwt_algorithm: str = Field(default="HS256", pattern="^(HS256|RS256)$")
    jwt_expiration_minutes: int = 60
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    # Refresh Token Configuration
    refresh_token_expiration_days: int = 7
    refresh_token_rotation_enabled: bool = True

    # LDAP/Active Directory Configuration
    ldap_enabled: bool = False
    ldap_server: str | None = None  # e.g., "ldaps://ldap.example.com:636"
    ldap_bind_dn: str | None = None  # e.g., "cn=sark,ou=service,dc=example,dc=com"
    ldap_bind_password: str | None = None
    ldap_user_base_dn: str | None = None  # e.g., "ou=users,dc=example,dc=com"
    ldap_group_base_dn: str | None = None  # e.g., "ou=groups,dc=example,dc=com"
    ldap_user_filter: str = "(uid={username})"  # Filter for user search
    ldap_group_filter: str = "(member={user_dn})"  # Filter for group search
    ldap_timeout: int = 5  # Connection timeout in seconds
    ldap_use_ssl: bool = True  # Use LDAPS
    ldap_role_mapping: dict[str, str] = {}  # Map LDAP groups to SARK roles

    # OIDC (OpenID Connect) Configuration
    oidc_enabled: bool = False
    oidc_provider: str = "google"  # google, azure, okta, custom
    oidc_discovery_url: str | None = (
        None  # e.g., "https://idp.example.com/.well-known/openid-configuration"
    )
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str | None = (
        None  # e.g., "https://sark.example.com/api/v1/auth/oidc/callback"
    )
    oidc_issuer: str | None = None  # Required for custom provider
    oidc_authorization_endpoint: str | None = None
    oidc_token_endpoint: str | None = None
    oidc_userinfo_endpoint: str | None = None
    oidc_jwks_uri: str | None = None
    oidc_scopes: list[str] = ["openid", "profile", "email"]
    oidc_use_pkce: bool = True  # Use PKCE for enhanced security
    oidc_azure_tenant: str | None = None  # Required for Azure AD
    oidc_okta_domain: str | None = None  # Required for Okta

    # SAML Configuration
    saml_enabled: bool = False
    saml_sp_entity_id: str = "https://sark.example.com"
    saml_sp_acs_url: str = "https://sark.example.com/api/auth/saml/acs"
    saml_sp_sls_url: str = "https://sark.example.com/api/auth/saml/slo"
    saml_idp_entity_id: str = ""
    saml_idp_sso_url: str = ""
    saml_idp_slo_url: str | None = None
    saml_idp_x509_cert: str | None = None  # IdP certificate (PEM without headers)
    saml_idp_metadata_url: str | None = None  # Alternative to manual config
    saml_sp_x509_cert: str | None = None  # SP certificate for signing
    saml_sp_private_key: str | None = None  # SP private key for signing
    saml_name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    saml_want_assertions_signed: bool = True
    saml_want_messages_signed: bool = False

    # LDAP/Active Directory Configuration
    ldap_enabled: bool = False
    ldap_server: str = "ldap://localhost:389"
    ldap_bind_dn: str = "cn=admin,dc=example,dc=com"
    ldap_bind_password: str = ""
    ldap_user_base_dn: str = "ou=users,dc=example,dc=com"
    ldap_group_base_dn: str | None = "ou=groups,dc=example,dc=com"
    ldap_user_search_filter: str = "(uid={username})"
    ldap_group_search_filter: str = "(member={user_dn})"
    ldap_email_attribute: str = "mail"
    ldap_name_attribute: str = "cn"
    ldap_given_name_attribute: str = "givenName"
    ldap_family_name_attribute: str = "sn"
    ldap_use_ssl: bool = False
    ldap_pool_size: int = 10

    # Session Management
    session_timeout_seconds: int = 86400  # 24 hours
    session_max_concurrent: int = 5  # Maximum concurrent sessions per user
    session_extend_on_activity: bool = True  # Extend session on activity
    session_cleanup_interval_seconds: int = 3600  # Clean up expired sessions every hour

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_api_key: int = 1000  # Requests per hour for API keys
    rate_limit_per_user: int = 5000  # Requests per hour for authenticated users (JWT)
    rate_limit_per_ip: int = 100  # Requests per hour for unauthenticated IPs
    rate_limit_admin_bypass: bool = True  # Allow admins to bypass rate limits
    rate_limit_window_seconds: int = 3600  # Rate limit window (1 hour)

    # PostgreSQL Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "sark"
    postgres_password: str = "sark"
    postgres_db: str = "sark"

    # Database Connection Pool Configuration
    # pool_size: Number of connections to keep in the pool
    postgres_pool_size: int = 20
    # max_overflow: Additional connections beyond pool_size under high load
    postgres_max_overflow: int = 10
    # pool_timeout: Seconds to wait for connection from pool before error
    postgres_pool_timeout: int = 30
    # pool_recycle: Recycle connections after N seconds (-1 = disabled)
    # Prevents "MySQL server has gone away" and similar timeout issues
    postgres_pool_recycle: int = 3600
    # pool_pre_ping: Test connections before using them from pool
    # Ensures connection is alive before query execution
    postgres_pool_pre_ping: bool = True
    # echo_pool: Log connection pool checkouts/returns (debugging)
    postgres_echo_pool: bool = False

    # TimescaleDB (Audit Database) - can be same as PostgreSQL or separate
    timescale_host: str = "localhost"
    timescale_port: int = 5432
    timescale_user: str = "sark"
    timescale_password: str = "sark"
    timescale_db: str = "sark_audit"

    # Redis Connection Pool Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: int = 0
    # max_connections: Maximum connections in pool (for ConnectionPool)
    redis_pool_size: int = 50
    # min_idle_connections: Minimum idle connections to keep
    redis_min_idle: int = 10
    # socket_timeout: Socket timeout in seconds
    redis_socket_timeout: int = 5
    # socket_connect_timeout: Connection timeout in seconds
    redis_socket_connect_timeout: int = 5
    # socket_keepalive: Enable TCP keepalive
    redis_socket_keepalive: bool = True
    # retry_on_timeout: Retry commands on timeout
    redis_retry_on_timeout: bool = True
    # health_check_interval: Seconds between connection health checks
    redis_health_check_interval: int = 30

    # Consul
    consul_host: str = "localhost"
    consul_port: int = 8500
    consul_scheme: str = "http"
    consul_token: str | None = None

    # Open Policy Agent (OPA)
    opa_url: str = "http://localhost:8181"
    opa_policy_path: str = "/v1/data/mcp/allow"
    opa_timeout_seconds: float = 1.0

    # HTTP Client Connection Pool Configuration
    # max_connections: Maximum connections in pool
    http_pool_connections: int = 100
    # max_keepalive_connections: Maximum connections to keep alive
    http_pool_keepalive: int = 20
    # keepalive_expiry: Seconds to keep idle connections alive
    http_keepalive_expiry: float = 5.0

    # Response Caching Configuration
    # enable_response_cache: Enable caching for read-heavy endpoints
    enable_response_cache: bool = True
    # cache_ttl_seconds: Default TTL for cached responses
    cache_ttl_seconds: int = 60
    # cache_server_list_ttl: TTL for server list endpoint
    cache_server_list_ttl: int = 30
    # cache_server_detail_ttl: TTL for server detail endpoint
    cache_server_detail_ttl: int = 300

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

    # Gateway Integration
    gateway_enabled: bool = False
    gateway_url: str = "http://localhost:8080"
    gateway_api_key: str | None = None
    gateway_timeout_seconds: float = 5.0
    gateway_retry_attempts: int = 3
    gateway_circuit_breaker_threshold: int = 5

    # Discovery Service
    discovery_interval_seconds: int = 300  # 5 minutes
    discovery_network_scan_enabled: bool = False
    discovery_k8s_enabled: bool = False
    discovery_cloud_enabled: bool = False

    # Audit Configuration
    audit_batch_size: int = 100
    audit_flush_interval_seconds: int = 5
    audit_retention_days: int = 90

    # Splunk SIEM Configuration
    splunk_enabled: bool = False
    splunk_hec_url: str = "https://localhost:8088/services/collector"
    splunk_hec_token: str = ""
    splunk_index: str = "sark_audit"
    splunk_sourcetype: str = "sark:audit:event"
    splunk_source: str = "sark"
    splunk_host: str | None = None
    splunk_verify_ssl: bool = True
    splunk_batch_size: int = 100
    splunk_batch_timeout_seconds: int = 5
    splunk_retry_attempts: int = 3

    # Datadog SIEM Configuration
    datadog_enabled: bool = False
    datadog_api_key: str = ""
    datadog_app_key: str = ""
    datadog_site: str = "datadoghq.com"
    datadog_service: str = "sark"
    datadog_environment: str = "production"
    datadog_hostname: str | None = None
    datadog_verify_ssl: bool = True
    datadog_batch_size: int = 100
    datadog_batch_timeout_seconds: int = 5
    datadog_retry_attempts: int = 3

    # Observability
    metrics_enabled: bool = True
    metrics_port: int = 9090
    tracing_enabled: bool = False
    tracing_endpoint: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("oidc_scopes", mode="before")
    @classmethod
    def parse_oidc_scopes(cls, v: Any) -> list[str]:
        """Parse OIDC scopes from comma-separated string or list."""
        if isinstance(v, str):
            return [scope.strip() for scope in v.split(",")]
        return v

    @field_validator("kafka_bootstrap_servers", mode="before")
    @classmethod
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
