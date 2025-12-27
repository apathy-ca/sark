#!/usr/bin/env bash

# ============================================================================
# SARK Production Configuration Validation Script
# ============================================================================
# Validates configuration for production deployments
#
# This script checks that all production requirements are met before
# deploying SARK to a production environment.
#
# Usage:
#   ./scripts/validate-production-config.sh [env-file]
#
# Arguments:
#   env-file - Path to .env file to validate (default: .env)
#
# Exit codes:
#   0 - Configuration is production-ready
#   1 - Configuration has issues
# ============================================================================

set -euo pipefail

ENV_FILE="${1:-.env}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((CHECKS_PASSED++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((CHECKS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((CHECKS_WARNING++))
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Load environment file
load_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi

    log_info "Loading environment from: $ENV_FILE"

    # Export all variables from .env file
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a

    log_success "Environment file loaded successfully"
}

# Check environment variable
check_env_var() {
    local var_name="$1"
    local var_value="${!var_name:-}"
    local required="${2:-true}"
    local description="$3"

    if [ -z "$var_value" ]; then
        if [ "$required" = "true" ]; then
            log_error "$description ($var_name) is not set"
            return 1
        else
            log_warning "$description ($var_name) is not set (optional)"
            return 0
        fi
    else
        log_success "$description ($var_name) is set"
        return 0
    fi
}

# Check if value is not default
check_not_default() {
    local var_name="$1"
    local default_value="$2"
    local var_value="${!var_name:-}"
    local description="$3"

    if [ "$var_value" = "$default_value" ]; then
        log_error "$description ($var_name) is still using default value: $default_value"
        return 1
    else
        log_success "$description ($var_name) is not using default value"
        return 0
    fi
}

# Check password strength
check_password_strength() {
    local var_name="$1"
    local var_value="${!var_name:-}"
    local description="$2"
    local min_length=16

    if [ -z "$var_value" ]; then
        log_error "$description ($var_name) is not set"
        return 1
    fi

    local length=${#var_value}

    if [ "$length" -lt "$min_length" ]; then
        log_error "$description ($var_name) is too short ($length chars, minimum $min_length)"
        return 1
    else
        log_success "$description ($var_name) has sufficient length ($length chars)"
        return 0
    fi
}

# Main validation
main() {
    log_section "SARK Production Configuration Validation"

    load_env_file

    # Environment checks
    log_section "Environment Configuration"
    check_env_var "ENVIRONMENT" true "Environment" || true

    if [ "${ENVIRONMENT:-}" != "production" ]; then
        log_warning "ENVIRONMENT is not set to 'production' (current: ${ENVIRONMENT:-undefined})"
    else
        log_success "ENVIRONMENT is set to 'production'"
    fi

    check_env_var "LOG_LEVEL" true "Log level" || true

    # PostgreSQL checks
    log_section "PostgreSQL Configuration"
    check_env_var "POSTGRES_ENABLED" true "PostgreSQL enabled" || true
    check_env_var "POSTGRES_MODE" true "PostgreSQL mode" || true

    if [ "${POSTGRES_MODE:-}" = "managed" ]; then
        log_error "PostgreSQL mode is 'managed' - production should use external managed database"
    elif [ "${POSTGRES_MODE:-}" = "external" ]; then
        log_success "PostgreSQL mode is 'external' (recommended for production)"
        check_env_var "POSTGRES_HOST" true "PostgreSQL host" || true
        check_env_var "POSTGRES_PORT" true "PostgreSQL port" || true
        check_env_var "POSTGRES_DB" true "PostgreSQL database" || true
        check_env_var "POSTGRES_USER" true "PostgreSQL user" || true
        check_env_var "POSTGRES_PASSWORD" true "PostgreSQL password" || true
        check_not_default "POSTGRES_PASSWORD" "sark" "PostgreSQL password" || true
        check_password_strength "POSTGRES_PASSWORD" "PostgreSQL password" || true
    fi

    # Redis checks
    log_section "Redis Configuration"
    check_env_var "VALKEY_ENABLED" true "Valkey enabled" || true
    check_env_var "VALKEY_MODE" true "Valkey mode" || true

    if [ "${VALKEY_MODE:-}" = "managed" ]; then
        log_error "Valkey mode is 'managed' - production should use external managed cache"
    elif [ "${VALKEY_MODE:-}" = "external" ]; then
        log_success "Valkey mode is 'external' (recommended for production)"
        check_env_var "VALKEY_HOST" true "Valkey host" || true
        check_env_var "VALKEY_PORT" true "Valkey port" || true
        check_env_var "VALKEY_PASSWORD" false "Valkey password" || true

        if [ -n "${VALKEY_PASSWORD:-}" ]; then
            check_password_strength "VALKEY_PASSWORD" "Valkey password" || true
        else
            log_warning "Valkey password is not set (recommended for production)"
        fi
    fi

    # Kong checks (if enabled)
    log_section "Kong API Gateway Configuration"
    check_env_var "KONG_ENABLED" true "Kong enabled" || true

    if [ "${KONG_ENABLED:-false}" = "true" ]; then
        check_env_var "KONG_MODE" true "Kong mode" || true

        if [ "${KONG_MODE:-}" = "managed" ]; then
            log_error "Kong mode is 'managed' - production should use external Kong"
        elif [ "${KONG_MODE:-}" = "external" ]; then
            log_success "Kong mode is 'external' (recommended for production)"
            check_env_var "KONG_ADMIN_URL" true "Kong Admin URL" || true
            check_env_var "KONG_PROXY_URL" true "Kong Proxy URL" || true
        fi
    fi

    # Security checks
    log_section "Security Configuration"

    # Check for SECRET_KEY
    if check_env_var "SECRET_KEY" true "Secret key"; then
        check_not_default "SECRET_KEY" "change-me-in-production" "Secret key" || true
        check_password_strength "SECRET_KEY" "Secret key" || true
    fi

    # Check CORS settings
    check_env_var "ALLOWED_HOSTS" false "Allowed hosts" || true

    # SSL/TLS checks
    log_section "SSL/TLS Configuration"
    check_env_var "SSL_ENABLED" false "SSL enabled" || true

    if [ "${SSL_ENABLED:-false}" = "true" ]; then
        check_env_var "SSL_CERT_PATH" true "SSL certificate path" || true
        check_env_var "SSL_KEY_PATH" true "SSL key path" || true
    else
        log_warning "SSL is not enabled (recommended for production)"
    fi

    # Monitoring checks
    log_section "Monitoring Configuration"
    check_env_var "PROMETHEUS_ENABLED" false "Prometheus enabled" || true
    check_env_var "GRAFANA_ENABLED" false "Grafana enabled" || true

    # SIEM integration
    log_section "SIEM Integration"
    check_env_var "SIEM_ENABLED" false "SIEM enabled" || true

    if [ "${SIEM_ENABLED:-false}" = "true" ]; then
        check_env_var "SIEM_TYPE" true "SIEM type" || true
    else
        log_warning "SIEM integration not enabled (recommended for production)"
    fi

    # Backup configuration
    log_section "Backup Configuration"
    check_env_var "BACKUP_ENABLED" false "Backup enabled" || true

    if [ "${BACKUP_ENABLED:-false}" = "false" ]; then
        log_warning "Automated backups not configured (required for production)"
    fi

    # Authentication
    log_section "Authentication Configuration"
    check_env_var "OIDC_ENABLED" false "OIDC enabled" || true
    check_env_var "LDAP_ENABLED" false "LDAP enabled" || true
    check_env_var "SAML_ENABLED" false "SAML enabled" || true

    local auth_enabled=false

    if [ "${OIDC_ENABLED:-false}" = "true" ] || [ "${LDAP_ENABLED:-false}" = "true" ] || [ "${SAML_ENABLED:-false}" = "true" ]; then
        auth_enabled=true
        log_success "At least one authentication method is enabled"
    else
        log_error "No authentication methods enabled (required for production)"
    fi

    # Resource limits (Kubernetes)
    log_section "Resource Configuration"
    check_env_var "MEMORY_LIMIT" false "Memory limit" || true
    check_env_var "CPU_LIMIT" false "CPU limit" || true

    # Print summary
    log_section "Validation Summary"
    echo "Total Checks: $((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNING))"
    echo -e "${GREEN}Passed: $CHECKS_PASSED${NC}"
    echo -e "${YELLOW}Warnings: $CHECKS_WARNING${NC}"
    echo -e "${RED}Failed: $CHECKS_FAILED${NC}"

    echo ""

    if [ $CHECKS_FAILED -eq 0 ] && [ $CHECKS_WARNING -eq 0 ]; then
        log_success "Configuration is production-ready! ✓"
        return 0
    elif [ $CHECKS_FAILED -eq 0 ]; then
        log_warning "Configuration is acceptable with warnings. Please review above."
        return 0
    else
        log_error "Configuration has critical issues. NOT production-ready."
        return 1
    fi
}

# Run main function
main
