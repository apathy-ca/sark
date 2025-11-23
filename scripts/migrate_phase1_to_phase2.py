#!/usr/bin/env python3
"""
SARK Phase 1 to Phase 2 Migration Script

This script migrates SARK configuration from Phase 1 to Phase 2, adding:
- SIEM integration (Splunk, Datadog)
- Enhanced security middleware
- Circuit breaker configuration
- Compression settings
- Security hardening

Usage:
    python scripts/migrate_phase1_to_phase2.py --input .env --output .env.phase2 [--apply]

    --input PATH     : Path to Phase 1 .env file (default: .env)
    --output PATH    : Path to output Phase 2 .env file (default: .env.phase2)
    --apply          : Apply changes directly to input file (creates backup)
    --force          : Skip confirmation prompts
    --validate-only  : Only validate configuration, don't migrate

Examples:
    # Preview migration (safe, no changes)
    python scripts/migrate_phase1_to_phase2.py

    # Generate new .env file
    python scripts/migrate_phase1_to_phase2.py --output .env.production

    # Apply changes to existing .env (creates .env.backup)
    python scripts/migrate_phase1_to_phase2.py --apply
"""

import argparse
import os
import re
import secrets
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@dataclass
class MigrationIssue:
    """Represents a migration issue or warning."""
    severity: str  # "error", "warning", "info"
    component: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class MigrationResult:
    """Results of a migration operation."""
    success: bool
    config: Dict[str, str] = field(default_factory=dict)
    issues: List[MigrationIssue] = field(default_factory=list)
    changes_made: List[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        """Check if result has any errors."""
        return any(issue.severity == "error" for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if result has any warnings."""
        return any(issue.severity == "warning" for issue in self.issues)


class ConfigMigrator:
    """Handles migration from Phase 1 to Phase 2 configuration."""

    # Phase 2 new variables with default values
    PHASE2_DEFAULTS = {
        # SIEM Integration - Splunk
        "SPLUNK_ENABLED": "false",
        "SPLUNK_HEC_URL": "",
        "SPLUNK_HEC_TOKEN": "",
        "SPLUNK_INDEX": "sark_audit",
        "SPLUNK_SOURCE": "sark",
        "SPLUNK_SOURCETYPE": "_json",
        "SPLUNK_BATCH_SIZE": "100",
        "SPLUNK_FLUSH_INTERVAL": "10.0",
        "SPLUNK_VERIFY_SSL": "true",
        "SPLUNK_TIMEOUT": "30.0",

        # SIEM Integration - Datadog
        "DATADOG_ENABLED": "false",
        "DATADOG_API_KEY": "",
        "DATADOG_SITE": "datadoghq.com",
        "DATADOG_SERVICE": "sark",
        "DATADOG_ENV": "production",
        "DATADOG_SOURCE": "sark",
        "DATADOG_BATCH_SIZE": "100",
        "DATADOG_FLUSH_INTERVAL": "10.0",
        "DATADOG_VERIFY_SSL": "true",
        "DATADOG_TIMEOUT": "30.0",

        # Circuit Breaker
        "CIRCUIT_BREAKER_ENABLED": "true",
        "CIRCUIT_BREAKER_FAILURE_THRESHOLD": "5",
        "CIRCUIT_BREAKER_RECOVERY_TIMEOUT": "60.0",
        "CIRCUIT_BREAKER_EXPECTED_EXCEPTION": "Exception",

        # Compression
        "COMPRESSION_ENABLED": "true",
        "COMPRESSION_LEVEL": "6",
        "COMPRESSION_MIN_SIZE": "1024",

        # Security Headers
        "SECURITY_HEADERS_ENABLED": "true",
        "HSTS_ENABLED": "true",
        "HSTS_MAX_AGE": "31536000",
        "HSTS_INCLUDE_SUBDOMAINS": "true",
        "HSTS_PRELOAD": "false",
        "CSP_POLICY": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';",
        "X_FRAME_OPTIONS": "DENY",
        "REFERRER_POLICY": "strict-origin-when-cross-origin",

        # CSRF Protection
        "CSRF_ENABLED": "true",
        "CSRF_SECRET_KEY": "",  # Will be generated
        "CSRF_HEADER_NAME": "X-CSRF-Token",
        "CSRF_COOKIE_NAME": "csrf_token",
        "CSRF_COOKIE_HTTPONLY": "true",
        "CSRF_COOKIE_SECURE": "true",
        "CSRF_COOKIE_SAMESITE": "strict",
    }

    # Variables that require secure random values
    SECURE_VARIABLES = {"SECRET_KEY", "CSRF_SECRET_KEY"}

    # Variables that should be non-empty in production
    REQUIRED_PRODUCTION_VARS = {
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
    }

    # Minimum length for secret keys
    MIN_SECRET_KEY_LENGTH = 32

    def __init__(self, input_path: Path, output_path: Path):
        """Initialize migrator with input and output paths."""
        self.input_path = input_path
        self.output_path = output_path
        self.phase1_config: Dict[str, str] = {}
        self.phase2_config: Dict[str, str] = {}

    def load_env_file(self, path: Path) -> Dict[str, str]:
        """Load environment variables from .env file."""
        config = {}

        if not path.exists():
            return config

        with open(path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE
                match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$', line)
                if match:
                    key, value = match.groups()
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    config[key] = value
                else:
                    print(f"{Colors.WARNING}Warning: Skipping invalid line {line_num}: {line}{Colors.ENDC}")

        return config

    def generate_secret_key(self, length: int = 64) -> str:
        """Generate a secure random secret key."""
        return secrets.token_urlsafe(length)

    def validate_secret_key(self, key: str) -> Tuple[bool, Optional[str]]:
        """Validate a secret key for security."""
        if not key:
            return False, "Secret key is empty"

        if len(key) < self.MIN_SECRET_KEY_LENGTH:
            return False, f"Secret key is too short (minimum {self.MIN_SECRET_KEY_LENGTH} characters)"

        # Check for weak/common keys
        weak_keys = {
            "dev-secret-key-change-in-production-min-32-chars",
            "CHANGEME-generate-secure-random-key-minimum-32-characters",
            "your-secret-key-here",
            "change-me",
        }

        if key in weak_keys:
            return False, "Secret key is a known weak/default value"

        # Check for sufficient entropy (at least some variety in characters)
        if len(set(key)) < 10:
            return False, "Secret key has insufficient entropy"

        return True, None

    def migrate(self) -> MigrationResult:
        """Perform the migration from Phase 1 to Phase 2."""
        result = MigrationResult(success=True)

        # Load Phase 1 configuration
        if not self.input_path.exists():
            result.success = False
            result.issues.append(MigrationIssue(
                severity="error",
                component="input",
                message=f"Input file not found: {self.input_path}",
                suggestion="Create a .env file or specify a different input path"
            ))
            return result

        self.phase1_config = self.load_env_file(self.input_path)

        if not self.phase1_config:
            result.issues.append(MigrationIssue(
                severity="warning",
                component="input",
                message="Input configuration is empty",
                suggestion="Verify the .env file contains valid KEY=VALUE pairs"
            ))

        # Start with Phase 1 configuration
        self.phase2_config = self.phase1_config.copy()

        # Add Phase 2 variables
        for key, default_value in self.PHASE2_DEFAULTS.items():
            if key not in self.phase2_config:
                self.phase2_config[key] = default_value
                result.changes_made.append(f"Added {key}={default_value}")

        # Validate and potentially regenerate secret keys
        for var_name in self.SECURE_VARIABLES:
            current_value = self.phase2_config.get(var_name, "")

            if var_name == "CSRF_SECRET_KEY" and not current_value:
                # Generate new CSRF secret key
                new_key = self.generate_secret_key()
                self.phase2_config[var_name] = new_key
                result.changes_made.append(f"Generated secure {var_name}")
                result.issues.append(MigrationIssue(
                    severity="info",
                    component="security",
                    message=f"Generated new {var_name}",
                    suggestion=f"Store this securely: {new_key[:20]}..."
                ))

            # Validate existing keys
            is_valid, error_msg = self.validate_secret_key(current_value)
            if not is_valid and current_value:
                result.issues.append(MigrationIssue(
                    severity="error",
                    component="security",
                    message=f"{var_name}: {error_msg}",
                    suggestion=f"Generate a new secure key using: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
                ))

        # Check for required production variables
        for var_name in self.REQUIRED_PRODUCTION_VARS:
            value = self.phase2_config.get(var_name, "")
            if not value or value == "":
                result.issues.append(MigrationIssue(
                    severity="warning",
                    component="configuration",
                    message=f"{var_name} is not set",
                    suggestion=f"Set {var_name} before deploying to production"
                ))

        # Validate SIEM configuration if enabled
        if self.phase2_config.get("SPLUNK_ENABLED", "false").lower() == "true":
            if not self.phase2_config.get("SPLUNK_HEC_URL"):
                result.issues.append(MigrationIssue(
                    severity="error",
                    component="siem",
                    message="SPLUNK_ENABLED is true but SPLUNK_HEC_URL is not set",
                    suggestion="Set SPLUNK_HEC_URL or disable Splunk integration"
                ))
            if not self.phase2_config.get("SPLUNK_HEC_TOKEN"):
                result.issues.append(MigrationIssue(
                    severity="error",
                    component="siem",
                    message="SPLUNK_ENABLED is true but SPLUNK_HEC_TOKEN is not set",
                    suggestion="Set SPLUNK_HEC_TOKEN or disable Splunk integration"
                ))

        if self.phase2_config.get("DATADOG_ENABLED", "false").lower() == "true":
            if not self.phase2_config.get("DATADOG_API_KEY"):
                result.issues.append(MigrationIssue(
                    severity="error",
                    component="siem",
                    message="DATADOG_ENABLED is true but DATADOG_API_KEY is not set",
                    suggestion="Set DATADOG_API_KEY or disable Datadog integration"
                ))

        # Check for deprecated or changed variables
        self._check_deprecated_vars(result)

        # Store final config
        result.config = self.phase2_config

        return result

    def _check_deprecated_vars(self, result: MigrationResult):
        """Check for deprecated or changed variables."""
        # Currently no deprecated variables in Phase 1 -> Phase 2
        # This is a placeholder for future migrations
        pass

    def write_config(self, config: Dict[str, str], output_path: Path):
        """Write configuration to output file."""
        # Group variables by category for better organization
        categories = {
            "Application": ["APP_NAME", "APP_VERSION", "ENV", "DEBUG", "LOG_LEVEL"],
            "API Server": ["API_HOST", "API_PORT", "API_WORKERS", "API_RELOAD"],
            "Security": ["SECRET_KEY", "ACCESS_TOKEN_EXPIRE_MINUTES", "CORS_ORIGINS",
                        "SECURITY_HEADERS_ENABLED", "HSTS_ENABLED", "HSTS_MAX_AGE",
                        "HSTS_INCLUDE_SUBDOMAINS", "HSTS_PRELOAD", "CSP_POLICY",
                        "X_FRAME_OPTIONS", "REFERRER_POLICY"],
            "CSRF Protection": ["CSRF_ENABLED", "CSRF_SECRET_KEY", "CSRF_HEADER_NAME",
                               "CSRF_COOKIE_NAME", "CSRF_COOKIE_HTTPONLY",
                               "CSRF_COOKIE_SECURE", "CSRF_COOKIE_SAMESITE"],
            "PostgreSQL": ["DATABASE_URL", "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_ECHO"],
            "TimescaleDB": ["TIMESCALE_ENABLED"],
            "Redis": ["REDIS_URL", "REDIS_MAX_CONNECTIONS", "REDIS_SOCKET_KEEPALIVE"],
            "Splunk SIEM": ["SPLUNK_ENABLED", "SPLUNK_HEC_URL", "SPLUNK_HEC_TOKEN",
                           "SPLUNK_INDEX", "SPLUNK_SOURCE", "SPLUNK_SOURCETYPE",
                           "SPLUNK_BATCH_SIZE", "SPLUNK_FLUSH_INTERVAL",
                           "SPLUNK_VERIFY_SSL", "SPLUNK_TIMEOUT"],
            "Datadog SIEM": ["DATADOG_ENABLED", "DATADOG_API_KEY", "DATADOG_SITE",
                            "DATADOG_SERVICE", "DATADOG_ENV", "DATADOG_SOURCE",
                            "DATADOG_BATCH_SIZE", "DATADOG_FLUSH_INTERVAL",
                            "DATADOG_VERIFY_SSL", "DATADOG_TIMEOUT"],
            "Circuit Breaker": ["CIRCUIT_BREAKER_ENABLED", "CIRCUIT_BREAKER_FAILURE_THRESHOLD",
                               "CIRCUIT_BREAKER_RECOVERY_TIMEOUT",
                               "CIRCUIT_BREAKER_EXPECTED_EXCEPTION"],
            "Compression": ["COMPRESSION_ENABLED", "COMPRESSION_LEVEL", "COMPRESSION_MIN_SIZE"],
        }

        with open(output_path, 'w') as f:
            # Write header
            f.write("# SARK Phase 2 Configuration\n")
            f.write(f"# Generated by migration script on {datetime.now().isoformat()}\n")
            f.write(f"# Migrated from: {self.input_path}\n\n")

            # Write categorized variables
            written_vars: Set[str] = set()

            for category, var_names in categories.items():
                # Check if any variables in this category exist
                category_vars = [(name, config.get(name, "")) for name in var_names if name in config]

                if category_vars:
                    f.write(f"# {category}\n")
                    for var_name, value in category_vars:
                        f.write(f"{var_name}={value}\n")
                        written_vars.add(var_name)
                    f.write("\n")

            # Write any remaining variables not in categories
            remaining_vars = [(k, v) for k, v in sorted(config.items()) if k not in written_vars]
            if remaining_vars:
                f.write("# Other Configuration\n")
                for var_name, value in remaining_vars:
                    f.write(f"{var_name}={value}\n")

    def print_diff(self, result: MigrationResult):
        """Print a diff of changes between Phase 1 and Phase 2."""
        print(f"\n{Colors.BOLD}{Colors.HEADER}=== Configuration Changes ==={Colors.ENDC}\n")

        # Show added variables
        added_vars = [k for k in result.config.keys() if k not in self.phase1_config]
        if added_vars:
            print(f"{Colors.OKGREEN}Added variables ({len(added_vars)}):{Colors.ENDC}")
            for var in sorted(added_vars):
                value = result.config[var]
                # Mask sensitive values
                if any(secret in var for secret in ["KEY", "TOKEN", "PASSWORD", "SECRET"]):
                    if value:
                        display_value = value[:10] + "..." if len(value) > 10 else "***"
                    else:
                        display_value = "(empty)"
                else:
                    display_value = value
                print(f"  + {var}={display_value}")
            print()

        # Show modified variables
        modified_vars = [k for k in result.config.keys()
                        if k in self.phase1_config and result.config[k] != self.phase1_config[k]]
        if modified_vars:
            print(f"{Colors.WARNING}Modified variables ({len(modified_vars)}):{Colors.ENDC}")
            for var in sorted(modified_vars):
                old_value = self.phase1_config[var]
                new_value = result.config[var]
                # Mask sensitive values
                if any(secret in var for secret in ["KEY", "TOKEN", "PASSWORD", "SECRET"]):
                    old_display = old_value[:10] + "..." if len(old_value) > 10 else "***"
                    new_display = new_value[:10] + "..." if len(new_value) > 10 else "***"
                else:
                    old_display = old_value
                    new_display = new_value
                print(f"  ~ {var}: {old_display} -> {new_display}")
            print()

        # Show unchanged variables count
        unchanged_count = len([k for k in self.phase1_config.keys()
                             if k in result.config and result.config[k] == self.phase1_config[k]])
        print(f"{Colors.OKBLUE}Unchanged variables: {unchanged_count}{Colors.ENDC}\n")

    def print_issues(self, result: MigrationResult):
        """Print migration issues."""
        if not result.issues:
            print(f"{Colors.OKGREEN}✓ No issues found{Colors.ENDC}\n")
            return

        print(f"\n{Colors.BOLD}{Colors.HEADER}=== Migration Issues ==={Colors.ENDC}\n")

        # Group by severity
        errors = [i for i in result.issues if i.severity == "error"]
        warnings = [i for i in result.issues if i.severity == "warning"]
        info = [i for i in result.issues if i.severity == "info"]

        if errors:
            print(f"{Colors.FAIL}{Colors.BOLD}Errors ({len(errors)}):{Colors.ENDC}")
            for issue in errors:
                print(f"  ✗ [{issue.component}] {issue.message}")
                if issue.suggestion:
                    print(f"    → {issue.suggestion}")
            print()

        if warnings:
            print(f"{Colors.WARNING}{Colors.BOLD}Warnings ({len(warnings)}):{Colors.ENDC}")
            for issue in warnings:
                print(f"  ⚠ [{issue.component}] {issue.message}")
                if issue.suggestion:
                    print(f"    → {issue.suggestion}")
            print()

        if info:
            print(f"{Colors.OKCYAN}{Colors.BOLD}Info ({len(info)}):{Colors.ENDC}")
            for issue in info:
                print(f"  ℹ [{issue.component}] {issue.message}")
                if issue.suggestion:
                    print(f"    → {issue.suggestion}")
            print()


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate SARK configuration from Phase 1 to Phase 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(".env"),
        help="Path to Phase 1 .env file (default: .env)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".env.phase2"),
        help="Path to output Phase 2 .env file (default: .env.phase2)"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes directly to input file (creates backup)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration, don't migrate"
    )

    args = parser.parse_args()

    # Print header
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}  SARK Phase 1 → Phase 2 Migration{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    print(f"Input:  {args.input}")
    if args.apply:
        print(f"Output: {args.input} (backup: {args.input}.backup)")
    else:
        print(f"Output: {args.output}")
    print()

    # Create migrator
    migrator = ConfigMigrator(args.input, args.output)

    # Perform migration
    print(f"{Colors.BOLD}Running migration...{Colors.ENDC}\n")
    result = migrator.migrate()

    if not result.success:
        print(f"{Colors.FAIL}{Colors.BOLD}Migration failed!{Colors.ENDC}\n")
        migrator.print_issues(result)
        sys.exit(1)

    # Print results
    migrator.print_diff(result)
    migrator.print_issues(result)

    # Check for errors
    if result.has_errors():
        print(f"{Colors.FAIL}{Colors.BOLD}Migration completed with errors!{Colors.ENDC}")
        print(f"{Colors.FAIL}Please fix the errors above before proceeding.{Colors.ENDC}\n")
        sys.exit(1)

    if args.validate_only:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ Validation completed successfully{Colors.ENDC}\n")
        sys.exit(0)

    # Ask for confirmation unless --force
    if not args.force:
        print(f"{Colors.BOLD}Proceed with migration? [y/N]{Colors.ENDC} ", end="")
        response = input().strip().lower()
        if response not in ['y', 'yes']:
            print(f"{Colors.WARNING}Migration cancelled{Colors.ENDC}\n")
            sys.exit(0)

    # Write output
    if args.apply:
        # Create backup
        backup_path = Path(str(args.input) + ".backup")
        print(f"\n{Colors.OKCYAN}Creating backup: {backup_path}{Colors.ENDC}")
        shutil.copy2(args.input, backup_path)

        # Write to original file
        print(f"{Colors.OKCYAN}Writing to: {args.input}{Colors.ENDC}")
        migrator.write_config(result.config, args.input)

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Migration completed successfully!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Backup saved to: {backup_path}{Colors.ENDC}\n")
    else:
        # Write to new file
        print(f"\n{Colors.OKCYAN}Writing to: {args.output}{Colors.ENDC}")
        migrator.write_config(result.config, args.output)

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Migration completed successfully!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Configuration written to: {args.output}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Review the file and copy to .env when ready{Colors.ENDC}\n")

    # Print next steps
    print(f"{Colors.BOLD}Next steps:{Colors.ENDC}")
    print(f"  1. Review the generated configuration file")
    print(f"  2. Fill in any missing values (SPLUNK_*, DATADOG_*, etc.)")
    print(f"  3. Run: python scripts/validate_config.py --env {args.output if not args.apply else args.input}")
    print(f"  4. Follow the deployment checklist in docs/DEPLOYMENT_CHECKLIST.md")
    print()

    if result.has_warnings():
        print(f"{Colors.WARNING}⚠ Please address the warnings above before deploying to production{Colors.ENDC}\n")


if __name__ == "__main__":
    main()
