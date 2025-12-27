#!/usr/bin/env python3
"""
SARK Configuration Validation Script

This script validates environment configuration for production deployments.
It checks for:
- Required variables are set
- Security best practices (strong passwords, SSL enabled, etc.)
- Valid formats and values
- Common misconfigurations

Usage:
    python scripts/validate_config.py --env-file .env.production
    python scripts/validate_config.py --env-file .env.production --strict
    python scripts/validate_config.py --env-file .env.production --format json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class Severity(str, Enum):
    """Issue severity levels."""

    ERROR = "ERROR"  # Must fix before deployment
    WARNING = "WARNING"  # Should fix for production
    INFO = "INFO"  # Informational only


@dataclass
class ValidationIssue:
    """Configuration validation issue."""

    severity: Severity
    category: str
    variable: str
    message: str
    recommendation: str | None = None


@dataclass
class ValidationResult:
    """Configuration validation result."""

    valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    warnings: int = 0
    errors: int = 0
    info: int = 0

    def add_issue(
        self,
        severity: Severity,
        category: str,
        variable: str,
        message: str,
        recommendation: str | None = None,
    ) -> None:
        """Add a validation issue."""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            variable=variable,
            message=message,
            recommendation=recommendation,
        )
        self.issues.append(issue)

        if severity == Severity.ERROR:
            self.errors += 1
            self.valid = False
        elif severity == Severity.WARNING:
            self.warnings += 1
        elif severity == Severity.INFO:
            self.info += 1


class ConfigValidator:
    """Configuration validator for SARK environment variables."""

    # Default/weak passwords that must not be used in production
    WEAK_PASSWORDS = {
        "sark",
        "password",
        "123456",
        "admin",
        "root",
        "postgres",
        "redis",
        "dev-secret-key-change-in-production-min-32-chars",
    }

    def __init__(self, env_file: Path, strict: bool = False):
        """Initialize validator.

        Args:
            env_file: Path to .env file to validate
            strict: If True, treat warnings as errors
        """
        self.env_file = env_file
        self.strict = strict
        self.config: dict[str, str] = {}
        self.result = ValidationResult()

    def load_env_file(self) -> None:
        """Load environment variables from .env file."""
        if not self.env_file.exists():
            self.result.add_issue(
                Severity.ERROR,
                "file",
                "env_file",
                f"Environment file not found: {self.env_file}",
                "Create the file or check the path",
            )
            return

        try:
            with open(self.env_file) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse KEY=VALUE
                    if "=" not in line:
                        self.result.add_issue(
                            Severity.WARNING,
                            "file",
                            f"line_{line_num}",
                            f"Invalid line format: {line}",
                            "Use KEY=VALUE format",
                        )
                        continue

                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    self.config[key] = value

        except Exception as e:
            self.result.add_issue(
                Severity.ERROR,
                "file",
                "env_file",
                f"Failed to read environment file: {e}",
            )

    def validate_all(self) -> ValidationResult:
        """Run all validation checks.

        Returns:
            ValidationResult with all issues found
        """
        self.load_env_file()

        if not self.result.valid:
            # File loading failed, can't continue
            return self.result

        # Run all validators
        self.validate_application()
        self.validate_api_server()
        self.validate_security()
        self.validate_postgres()
        self.validate_timescale()
        self.validate_redis()
        self.validate_splunk()
        self.validate_datadog()
        self.validate_audit()
        self.validate_observability()

        # In strict mode, warnings become errors
        if self.strict and self.result.warnings > 0:
            self.result.errors += self.result.warnings
            self.result.valid = False

        return self.result

    def get_var(self, key: str, default: str | None = None) -> str | None:
        """Get environment variable value."""
        return self.config.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = self.get_var(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Get integer environment variable."""
        value = self.get_var(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def validate_required(
        self,
        category: str,
        variable: str,
        description: str,
        condition: bool = True,
    ) -> bool:
        """Validate that a required variable is set.

        Args:
            category: Configuration category
            variable: Variable name
            description: Human-readable description
            condition: Only required if condition is True

        Returns:
            True if variable is set, False otherwise
        """
        if not condition:
            return True

        value = self.get_var(variable)
        if not value:
            self.result.add_issue(
                Severity.ERROR,
                category,
                variable,
                f"Required variable not set: {description}",
                f"Set {variable} in your environment configuration",
            )
            return False
        return True

    def validate_enum(
        self,
        category: str,
        variable: str,
        valid_values: list[str],
        required: bool = True,
    ) -> None:
        """Validate that variable is one of allowed values."""
        value = self.get_var(variable)

        if not value:
            if required:
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    variable,
                    f"Required variable not set",
                    f"Set {variable} to one of: {', '.join(valid_values)}",
                )
            return

        if value not in valid_values:
            self.result.add_issue(
                Severity.ERROR,
                category,
                variable,
                f"Invalid value '{value}'",
                f"Must be one of: {', '.join(valid_values)}",
            )

    def validate_url(
        self,
        category: str,
        variable: str,
        required: bool = True,
        https_required: bool = False,
    ) -> None:
        """Validate URL format."""
        value = self.get_var(variable)

        if not value:
            if required:
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    variable,
                    "Required URL not set",
                )
            return

        try:
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    variable,
                    f"Invalid URL format: {value}",
                    "Use format: https://hostname:port/path",
                )
            elif https_required and parsed.scheme != "https":
                self.result.add_issue(
                    Severity.WARNING,
                    category,
                    variable,
                    f"URL should use HTTPS: {value}",
                    "Use https:// for production security",
                )
        except Exception:
            self.result.add_issue(
                Severity.ERROR,
                category,
                variable,
                f"Invalid URL: {value}",
            )

    def validate_password_strength(
        self,
        category: str,
        variable: str,
        min_length: int = 20,
    ) -> None:
        """Validate password strength."""
        value = self.get_var(variable)

        if not value:
            return  # Handled by validate_required

        # Check for weak/default passwords
        if value.lower() in self.WEAK_PASSWORDS:
            self.result.add_issue(
                Severity.ERROR,
                category,
                variable,
                f"Weak/default password detected",
                f"Generate a strong password: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"",
            )
            return

        # Check password length
        if len(value) < min_length:
            severity = Severity.ERROR if len(value) < 12 else Severity.WARNING
            self.result.add_issue(
                severity,
                category,
                variable,
                f"Password too short ({len(value)} chars, minimum {min_length})",
                f"Use a password with at least {min_length} characters",
            )

    def validate_application(self) -> None:
        """Validate application settings."""
        category = "application"

        # ENVIRONMENT
        self.validate_enum(category, "ENVIRONMENT", ["development", "staging", "production"])

        environment = self.get_var("ENVIRONMENT", "development")

        # DEBUG must be false in production
        if environment == "production":
            debug = self.get_bool("DEBUG", False)
            if debug:
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    "DEBUG",
                    "Debug mode enabled in production",
                    "Set DEBUG=false in production (security risk)",
                )

        # LOG_LEVEL
        self.validate_enum(
            category,
            "LOG_LEVEL",
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            required=False,
        )

        # Warn if DEBUG logging in production
        if environment == "production":
            log_level = self.get_var("LOG_LEVEL", "INFO")
            if log_level == "DEBUG":
                self.result.add_issue(
                    Severity.WARNING,
                    category,
                    "LOG_LEVEL",
                    "DEBUG logging in production may impact performance",
                    "Consider INFO or WARNING level for production",
                )

    def validate_api_server(self) -> None:
        """Validate API server configuration."""
        category = "api_server"

        # API_WORKERS
        workers = self.get_int("API_WORKERS", 4)
        if workers and workers > 50:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "API_WORKERS",
                f"Very high worker count ({workers})",
                "Typically use (2 × CPU cores) + 1",
            )

        # API_RELOAD must be false in production
        environment = self.get_var("ENVIRONMENT", "development")
        if environment == "production":
            reload = self.get_bool("API_RELOAD", False)
            if reload:
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    "API_RELOAD",
                    "Auto-reload enabled in production",
                    "Set API_RELOAD=false in production",
                )

    def validate_security(self) -> None:
        """Validate security configuration."""
        category = "security"

        environment = self.get_var("ENVIRONMENT", "development")

        # SECRET_KEY
        if self.validate_required(category, "SECRET_KEY", "JWT secret key"):
            secret_key = self.get_var("SECRET_KEY")

            # Check minimum length
            if len(secret_key) < 32:
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    "SECRET_KEY",
                    f"Secret key too short ({len(secret_key)} chars, minimum 32)",
                    "Generate: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\"",
                )

            # Check for default value
            if "dev-secret-key" in secret_key or "change-in-production" in secret_key:
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    "SECRET_KEY",
                    "Default secret key must be changed in production",
                    "Generate a new secure key",
                )

        # ACCESS_TOKEN_EXPIRE_MINUTES
        expire = self.get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
        if expire and expire > 120:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "ACCESS_TOKEN_EXPIRE_MINUTES",
                f"Token expiration very long ({expire} minutes)",
                "Consider shorter expiration (15-60 minutes) for better security",
            )

        # CORS_ORIGINS
        if self.validate_required(category, "CORS_ORIGINS", "CORS allowed origins"):
            cors = self.get_var("CORS_ORIGINS")
            if cors == "*":
                self.result.add_issue(
                    Severity.ERROR,
                    category,
                    "CORS_ORIGINS",
                    "Wildcard CORS origins not allowed in production",
                    "Specify exact frontend domains",
                )
            elif environment == "production" and "localhost" in cors:
                self.result.add_issue(
                    Severity.WARNING,
                    category,
                    "CORS_ORIGINS",
                    "localhost in CORS origins for production",
                    "Remove localhost from production CORS configuration",
                )

    def validate_postgres(self) -> None:
        """Validate PostgreSQL configuration."""
        category = "postgres"

        environment = self.get_var("ENVIRONMENT", "development")

        # Required variables
        self.validate_required(category, "POSTGRES_HOST", "PostgreSQL host")
        self.validate_required(category, "POSTGRES_USER", "PostgreSQL user")
        self.validate_required(category, "POSTGRES_DB", "PostgreSQL database")

        # Password
        if self.validate_required(category, "POSTGRES_PASSWORD", "PostgreSQL password"):
            if environment != "development":
                self.validate_password_strength(category, "POSTGRES_PASSWORD", min_length=20)

        # Pool size
        pool_size = self.get_int("POSTGRES_POOL_SIZE", 20)
        max_overflow = self.get_int("POSTGRES_MAX_OVERFLOW", 10)

        if pool_size and max_overflow:
            total = pool_size + max_overflow
            if total > 100:
                self.result.add_issue(
                    Severity.WARNING,
                    category,
                    "POSTGRES_POOL_SIZE",
                    f"Very large connection pool ({total} total connections)",
                    "Ensure PostgreSQL max_connections setting can handle this",
                )

    def validate_timescale(self) -> None:
        """Validate TimescaleDB configuration."""
        category = "timescale"

        environment = self.get_var("ENVIRONMENT", "development")

        # Required variables
        self.validate_required(category, "TIMESCALE_HOST", "TimescaleDB host")
        self.validate_required(category, "TIMESCALE_USER", "TimescaleDB user")
        self.validate_required(category, "TIMESCALE_DB", "TimescaleDB database")

        # Password
        if self.validate_required(category, "TIMESCALE_PASSWORD", "TimescaleDB password"):
            if environment != "development":
                self.validate_password_strength(category, "TIMESCALE_PASSWORD", min_length=20)

    def validate_redis(self) -> None:
        """Validate Redis configuration."""
        category = "redis"

        environment = self.get_var("ENVIRONMENT", "development")

        # Valkey password required in production
        if environment == "production":
            password = self.get_var("VALKEY_PASSWORD")
            if not password:
                self.result.add_issue(
                    Severity.WARNING,
                    category,
                    "VALKEY_PASSWORD",
                    "Valkey password not set in production",
                    "Set a strong Valkey password for production security",
                )

        # Pool size
        pool_size = self.get_int("VALKEY_POOL_SIZE", 50)
        if pool_size and pool_size > 500:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "VALKEY_POOL_SIZE",
                f"Very large Redis connection pool ({pool_size})",
                "Typical range: 50-200 connections",
            )

    def validate_splunk(self) -> None:
        """Validate Splunk SIEM configuration."""
        category = "splunk"

        enabled = self.get_bool("SPLUNK_ENABLED", False)
        if not enabled:
            return

        # Required variables when enabled
        self.validate_required(
            category, "SPLUNK_HEC_URL", "Splunk HEC URL", condition=enabled
        )
        self.validate_required(
            category, "SPLUNK_HEC_TOKEN", "Splunk HEC token", condition=enabled
        )

        # Validate HEC URL
        self.validate_url(category, "SPLUNK_HEC_URL", required=enabled, https_required=True)

        # Validate HEC token format (should be UUID)
        hec_token = self.get_var("SPLUNK_HEC_TOKEN")
        if hec_token and not re.match(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            hec_token,
        ):
            self.result.add_issue(
                Severity.WARNING,
                category,
                "SPLUNK_HEC_TOKEN",
                "HEC token does not match UUID format",
                "Verify token is correct (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)",
            )

        # SSL verification
        verify_ssl = self.get_bool("SPLUNK_VERIFY_SSL", True)
        environment = self.get_var("ENVIRONMENT", "development")
        if environment == "production" and not verify_ssl:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "SPLUNK_VERIFY_SSL",
                "SSL verification disabled in production",
                "Enable SPLUNK_VERIFY_SSL=true for production security",
            )

        # Batch size
        batch_size = self.get_int("SPLUNK_BATCH_SIZE", 100)
        if batch_size and batch_size > 10000:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "SPLUNK_BATCH_SIZE",
                f"Very large batch size ({batch_size})",
                "Consider smaller batches (100-1000) for better latency",
            )

    def validate_datadog(self) -> None:
        """Validate Datadog SIEM configuration."""
        category = "datadog"

        enabled = self.get_bool("DATADOG_ENABLED", False)
        if not enabled:
            return

        # Required variables when enabled
        self.validate_required(
            category, "DATADOG_API_KEY", "Datadog API key", condition=enabled
        )

        # Validate site
        site = self.get_var("DATADOG_SITE", "datadoghq.com")
        valid_sites = [
            "datadoghq.com",
            "datadoghq.eu",
            "us3.datadoghq.com",
            "us5.datadoghq.com",
            "ap1.datadoghq.com",
            "ddog-gov.com",
        ]
        if site and site not in valid_sites:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "DATADOG_SITE",
                f"Uncommon Datadog site: {site}",
                f"Common sites: {', '.join(valid_sites)}",
            )

        # SSL verification
        verify_ssl = self.get_bool("DATADOG_VERIFY_SSL", True)
        environment = self.get_var("ENVIRONMENT", "development")
        if environment == "production" and not verify_ssl:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "DATADOG_VERIFY_SSL",
                "SSL verification disabled in production",
                "Enable DATADOG_VERIFY_SSL=true for production security",
            )

        # Batch size (Datadog limit: 1000)
        batch_size = self.get_int("DATADOG_BATCH_SIZE", 100)
        if batch_size and batch_size > 1000:
            self.result.add_issue(
                Severity.ERROR,
                category,
                "DATADOG_BATCH_SIZE",
                f"Batch size exceeds Datadog limit ({batch_size} > 1000)",
                "Set DATADOG_BATCH_SIZE to 1000 or less",
            )

    def validate_audit(self) -> None:
        """Validate audit configuration."""
        category = "audit"

        # Audit retention
        retention = self.get_int("AUDIT_RETENTION_DAYS", 90)
        if retention and retention < 30:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "AUDIT_RETENTION_DAYS",
                f"Short audit retention ({retention} days)",
                "Consider longer retention for compliance (90-365 days)",
            )

        # Batch configuration
        batch_size = self.get_int("AUDIT_BATCH_SIZE", 100)
        flush_interval = self.get_int("AUDIT_FLUSH_INTERVAL_SECONDS", 5)

        if batch_size and batch_size > 10000:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "AUDIT_BATCH_SIZE",
                f"Very large batch size ({batch_size})",
                "Large batches may increase latency",
            )

        if flush_interval and flush_interval > 60:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "AUDIT_FLUSH_INTERVAL_SECONDS",
                f"Long flush interval ({flush_interval} seconds)",
                "Long intervals may delay audit event visibility",
            )

    def validate_observability(self) -> None:
        """Validate observability configuration."""
        category = "observability"

        # Metrics enabled recommended for production
        environment = self.get_var("ENVIRONMENT", "development")
        metrics_enabled = self.get_bool("METRICS_ENABLED", True)

        if environment == "production" and not metrics_enabled:
            self.result.add_issue(
                Severity.WARNING,
                category,
                "METRICS_ENABLED",
                "Metrics disabled in production",
                "Enable metrics for production monitoring",
            )


def format_text_output(result: ValidationResult) -> str:
    """Format validation result as text."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("SARK Configuration Validation Report")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    status = "✅ PASS" if result.valid else "❌ FAIL"
    lines.append(f"Status: {status}")
    lines.append(f"Errors: {result.errors}")
    lines.append(f"Warnings: {result.warnings}")
    lines.append(f"Info: {result.info}")
    lines.append("")

    if not result.issues:
        lines.append("✅ No issues found!")
        return "\n".join(lines)

    # Group issues by category
    issues_by_category: dict[str, list[ValidationIssue]] = {}
    for issue in result.issues:
        if issue.category not in issues_by_category:
            issues_by_category[issue.category] = []
        issues_by_category[issue.category].append(issue)

    # Output issues by category
    for category in sorted(issues_by_category.keys()):
        lines.append(f"\n{category.upper()}")
        lines.append("-" * 80)

        for issue in issues_by_category[category]:
            severity_icon = {
                Severity.ERROR: "❌",
                Severity.WARNING: "⚠️",
                Severity.INFO: "ℹ️",
            }[issue.severity]

            lines.append(f"\n{severity_icon} [{issue.severity.value}] {issue.variable}")
            lines.append(f"   {issue.message}")
            if issue.recommendation:
                lines.append(f"   💡 {issue.recommendation}")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)


def format_json_output(result: ValidationResult) -> str:
    """Format validation result as JSON."""
    return json.dumps(
        {
            "valid": result.valid,
            "summary": {
                "errors": result.errors,
                "warnings": result.warnings,
                "info": result.info,
            },
            "issues": [
                {
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "variable": issue.variable,
                    "message": issue.message,
                    "recommendation": issue.recommendation,
                }
                for issue in result.issues
            ],
        },
        indent=2,
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate SARK configuration for production deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate production configuration
  python scripts/validate_config.py --env-file .env.production

  # Strict mode (warnings as errors)
  python scripts/validate_config.py --env-file .env.production --strict

  # JSON output for CI/CD
  python scripts/validate_config.py --env-file .env.production --format json

  # Validate specific category
  python scripts/validate_config.py --env-file .env.production --category security
        """,
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to environment file (default: .env)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--category",
        help="Validate specific category only",
    )

    args = parser.parse_args()

    # Run validation
    validator = ConfigValidator(args.env_file, strict=args.strict)
    result = validator.validate_all()

    # Filter by category if specified
    if args.category:
        result.issues = [i for i in result.issues if i.category == args.category]
        result.errors = sum(1 for i in result.issues if i.severity == Severity.ERROR)
        result.warnings = sum(1 for i in result.issues if i.severity == Severity.WARNING)
        result.info = sum(1 for i in result.issues if i.severity == Severity.INFO)
        result.valid = result.errors == 0

    # Output result
    if args.format == "json":
        print(format_json_output(result))
    else:
        print(format_text_output(result))

    # Exit code
    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
