"""Security tests for settings configuration - default credentials validation."""

import logging
import os
from unittest.mock import patch

import pytest

from sark.config.settings import Settings


class TestDefaultCredentialsValidation:
    """Test suite for default credentials validation in production."""

    def test_production_requires_postgres_password(self, monkeypatch, caplog):
        """Test that production environment requires POSTGRES_PASSWORD."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

        # Should exit with code 1 in production with default password
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.CRITICAL):
                Settings()

        assert exc_info.value.code == 1
        assert "POSTGRES_PASSWORD not set in production environment!" in caplog.text

    def test_production_requires_timescale_password(self, monkeypatch, caplog):
        """Test that production environment requires TIMESCALE_PASSWORD."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secure-postgres-password")
        monkeypatch.delenv("TIMESCALE_PASSWORD", raising=False)

        # Should exit with code 1 in production with default password
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.CRITICAL):
                Settings()

        assert exc_info.value.code == 1
        assert "TIMESCALE_PASSWORD not set in production environment!" in caplog.text

    def test_production_requires_redis_password(self, monkeypatch, caplog):
        """Test that production environment requires REDIS_PASSWORD."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secure-postgres-password")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "secure-timescale-password")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        # Should exit with code 1 in production without Redis password
        with pytest.raises(SystemExit) as exc_info:
            with caplog.at_level(logging.CRITICAL):
                Settings()

        assert exc_info.value.code == 1
        assert "REDIS_PASSWORD not set in production environment!" in caplog.text

    def test_production_accepts_custom_passwords(self, monkeypatch):
        """Test that production accepts custom passwords."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("POSTGRES_PASSWORD", "my-secure-postgres-pw-123")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "my-secure-timescale-pw-456")
        monkeypatch.setenv("REDIS_PASSWORD", "my-secure-redis-pw-789")

        # Should not raise SystemExit
        settings = Settings()

        assert settings.postgres_password == "my-secure-postgres-pw-123"
        assert settings.timescale_password == "my-secure-timescale-pw-456"
        assert settings.redis_password == "my-secure-redis-pw-789"

    def test_development_allows_default_postgres_with_warning(self, monkeypatch, caplog):
        """Test that development allows default postgres password with warning."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        monkeypatch.setenv("TIMESCALE_PASSWORD", "custom-timescale")
        monkeypatch.setenv("REDIS_PASSWORD", "custom-redis")

        with caplog.at_level(logging.WARNING):
            settings = Settings()

        assert "DO NOT USE IN PRODUCTION" in caplog.text
        assert "POSTGRES_PASSWORD using default value" in caplog.text
        assert settings.postgres_password == "sark"

    def test_development_allows_default_timescale_with_warning(self, monkeypatch, caplog):
        """Test that development allows default timescale password with warning."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("POSTGRES_PASSWORD", "custom-postgres")
        monkeypatch.delenv("TIMESCALE_PASSWORD", raising=False)
        monkeypatch.setenv("REDIS_PASSWORD", "custom-redis")

        with caplog.at_level(logging.WARNING):
            settings = Settings()

        assert "DO NOT USE IN PRODUCTION" in caplog.text
        assert "TIMESCALE_PASSWORD using default value" in caplog.text
        assert settings.timescale_password == "sark"

    def test_development_allows_no_redis_password_with_warning(self, monkeypatch, caplog):
        """Test that development allows missing redis password with warning."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("POSTGRES_PASSWORD", "custom-postgres")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "custom-timescale")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        with caplog.at_level(logging.WARNING):
            settings = Settings()

        assert "DO NOT USE IN PRODUCTION" in caplog.text
        assert "REDIS_PASSWORD not set" in caplog.text
        assert settings.redis_password is None

    def test_staging_environment_allows_defaults_with_warning(self, monkeypatch, caplog):
        """Test that staging environment (non-production) allows defaults with warning."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        monkeypatch.setenv("TIMESCALE_PASSWORD", "custom-timescale")
        monkeypatch.setenv("REDIS_PASSWORD", "custom-redis")

        with caplog.at_level(logging.WARNING):
            settings = Settings()

        assert "DO NOT USE IN PRODUCTION" in caplog.text
        assert settings.postgres_password == "sark"

    def test_default_environment_is_development(self, monkeypatch, caplog):
        """Test that default environment is development when not specified."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        monkeypatch.setenv("TIMESCALE_PASSWORD", "custom-timescale")
        monkeypatch.setenv("REDIS_PASSWORD", "custom-redis")

        # Should not exit (defaults to development)
        with caplog.at_level(logging.WARNING):
            settings = Settings()

        assert settings.environment == "development"
        assert settings.postgres_password == "sark"
        assert "DO NOT USE IN PRODUCTION" in caplog.text

    def test_all_defaults_in_development_show_multiple_warnings(self, monkeypatch, caplog):
        """Test that using all defaults in development shows all warnings."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        monkeypatch.delenv("TIMESCALE_PASSWORD", raising=False)
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        with caplog.at_level(logging.WARNING):
            settings = Settings()

        # All three warnings should appear
        assert caplog.text.count("DO NOT USE IN PRODUCTION") >= 3
        assert "POSTGRES_PASSWORD" in caplog.text
        assert "TIMESCALE_PASSWORD" in caplog.text
        assert "REDIS_PASSWORD" in caplog.text

    def test_production_with_all_passwords_set_no_warnings(self, monkeypatch, caplog):
        """Test that production with all passwords set shows no warnings."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secure-pg-123")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "secure-ts-456")
        monkeypatch.setenv("REDIS_PASSWORD", "secure-redis-789")

        with caplog.at_level(logging.WARNING):
            settings = Settings()

        # No warnings should be logged
        assert "DO NOT USE IN PRODUCTION" not in caplog.text
        assert settings.postgres_password == "secure-pg-123"
        assert settings.timescale_password == "secure-ts-456"
        assert settings.redis_password == "secure-redis-789"

    def test_secret_key_default_warning_in_production(self, monkeypatch):
        """Test that default secret_key should also be changed in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secure-pg")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "secure-ts")
        monkeypatch.setenv("REDIS_PASSWORD", "secure-redis")
        monkeypatch.delenv("SECRET_KEY", raising=False)

        settings = Settings()

        # The default secret_key contains "dev" and "change-in-production"
        # This is a reminder that it should be changed
        assert "dev" in settings.secret_key.lower()
        assert "production" in settings.secret_key.lower()

    def test_postgres_dsn_uses_validated_password(self, monkeypatch):
        """Test that postgres_dsn uses the validated password."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("POSTGRES_PASSWORD", "my-test-password")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "custom-ts")
        monkeypatch.setenv("REDIS_PASSWORD", "custom-redis")

        settings = Settings()

        assert "my-test-password" in settings.postgres_dsn
        assert settings.postgres_dsn.startswith("postgresql+asyncpg://")

    def test_timescale_dsn_uses_validated_password(self, monkeypatch):
        """Test that timescale_dsn uses the validated password."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("POSTGRES_PASSWORD", "custom-pg")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "my-timescale-password")
        monkeypatch.setenv("REDIS_PASSWORD", "custom-redis")

        settings = Settings()

        assert "my-timescale-password" in settings.timescale_dsn
        assert settings.timescale_dsn.startswith("postgresql+asyncpg://")

    def test_redis_dsn_uses_validated_password(self, monkeypatch):
        """Test that redis_dsn uses the validated password."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("POSTGRES_PASSWORD", "custom-pg")
        monkeypatch.setenv("TIMESCALE_PASSWORD", "custom-ts")
        monkeypatch.setenv("REDIS_PASSWORD", "my-redis-password")

        settings = Settings()

        assert "my-redis-password" in settings.redis_dsn
        assert settings.redis_dsn.startswith("redis://")
