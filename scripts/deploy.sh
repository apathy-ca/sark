#!/usr/bin/env bash

# ============================================================================
# SARK Deployment Automation Script
# ============================================================================
# Automated deployment script for SARK across different environments
#
# This script handles deployment, validation, and testing for SARK.
#
# Usage:
#   ./scripts/deploy.sh [environment] [profile]
#
# Arguments:
#   environment - Target environment (development, staging, production)
#   profile     - Docker Compose profile (minimal, standard, full)
#
# Examples:
#   ./scripts/deploy.sh development standard
#   ./scripts/deploy.sh staging full
#   ./scripts/deploy.sh production minimal
#
# Exit codes:
#   0 - Deployment successful
#   1 - Deployment failed
# ============================================================================

set -euo pipefail

# Default values
ENVIRONMENT="${1:-development}"
PROFILE="${2:-standard}"
RUN_TESTS="${RUN_TESTS:-true}"
RUN_VALIDATION="${RUN_VALIDATION:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}"
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Deployment failed with exit code $exit_code"
        log_info "Run with DEBUG=1 for more verbose output"
    fi
}

trap cleanup EXIT

# Validate prerequisites
validate_prerequisites() {
    log_section "Validating Prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_success "Docker is installed: $(docker --version | cut -d' ' -f3)"

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    log_success "Docker Compose is installed: $(docker compose version --short)"

    # Check Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    log_success "Docker daemon is running"

    # Check environment file
    if [ ! -f "$PROJECT_ROOT/.env" ] && [ "$ENVIRONMENT" != "development" ]; then
        log_error ".env file not found. Copy .env.example to .env and configure it."
        exit 1
    fi

    if [ "$ENVIRONMENT" = "production" ] && [ "$RUN_VALIDATION" = "true" ]; then
        log_info "Running production configuration validation..."
        if [ -x "$SCRIPT_DIR/validate-production-config.sh" ]; then
            if ! "$SCRIPT_DIR/validate-production-config.sh"; then
                log_error "Production configuration validation failed"
                exit 1
            fi
        else
            log_warning "Production validation script not found or not executable"
        fi
    fi
}

# Build Docker images
build_images() {
    log_section "Building Docker Images"

    log_info "Building images for profile: $PROFILE"

    if docker compose --profile "$PROFILE" build; then
        log_success "Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        exit 1
    fi
}

# Start services
start_services() {
    log_section "Starting Services"

    log_info "Starting services with profile: $PROFILE"

    if docker compose --profile "$PROFILE" up -d; then
        log_success "Services started successfully"
    else
        log_error "Failed to start services"
        docker compose logs
        exit 1
    fi
}

# Wait for services to be healthy
wait_for_health() {
    log_section "Waiting for Services to be Healthy"

    local max_wait=120
    local waited=0
    local all_healthy=false

    log_info "Waiting for services to become healthy (timeout: ${max_wait}s)..."

    while [ $waited -lt $max_wait ] && [ "$all_healthy" = "false" ]; do
        # Get unhealthy services
        local unhealthy
        unhealthy=$(docker compose --profile "$PROFILE" ps --format json | \
                   jq -r 'select(.Health != "" and .Health != "healthy") | .Name' 2>/dev/null || echo "")

        if [ -z "$unhealthy" ]; then
            all_healthy=true
            log_success "All services are healthy (waited ${waited}s)"
            break
        else
            log_info "Waiting for services: $(echo "$unhealthy" | tr '\n' ' ')"
        fi

        sleep 5
        ((waited+=5))
    done

    if [ "$all_healthy" = "false" ]; then
        log_error "Services failed to become healthy after ${max_wait}s"
        docker compose ps
        docker compose logs --tail=50
        exit 1
    fi
}

# Run health check tests
run_health_tests() {
    if [ "$RUN_TESTS" != "true" ]; then
        log_info "Skipping health check tests (RUN_TESTS=false)"
        return 0
    fi

    log_section "Running Health Check Tests"

    if [ -x "$SCRIPT_DIR/test-health-checks.sh" ]; then
        if "$SCRIPT_DIR/test-health-checks.sh" "$PROFILE"; then
            log_success "Health check tests passed"
        else
            log_error "Health check tests failed"
            exit 1
        fi
    else
        log_warning "Health check test script not found or not executable"
    fi
}

# Display deployment info
display_deployment_info() {
    log_section "Deployment Information"

    echo ""
    echo -e "${BOLD}Environment:${NC} $ENVIRONMENT"
    echo -e "${BOLD}Profile:${NC} $PROFILE"
    echo ""

    echo -e "${BOLD}Running Services:${NC}"
    docker compose --profile "$PROFILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    echo -e "${BOLD}Access Points:${NC}"
    echo "  API Documentation: http://localhost:8000/docs"
    echo "  API Health:        http://localhost:8000/health"
    echo "  API Metrics:       http://localhost:8000/metrics"

    if [ "$PROFILE" = "full" ]; then
        echo "  Kong Admin:        http://localhost:8001"
        echo "  Kong Proxy:        http://localhost:8000"
    fi

    echo ""
    echo -e "${BOLD}Useful Commands:${NC}"
    echo "  View logs:         docker compose logs -f"
    echo "  Stop services:     docker compose --profile $PROFILE down"
    echo "  Restart:           docker compose --profile $PROFILE restart"
    echo "  Shell access:      docker compose exec app bash"

    echo ""
}

# Main deployment flow
main() {
    log_section "SARK Deployment - $ENVIRONMENT ($PROFILE)"

    cd "$PROJECT_ROOT"

    log_info "Starting deployment process..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Profile: $PROFILE"
    log_info "Run tests: $RUN_TESTS"
    log_info "Run validation: $RUN_VALIDATION"

    echo ""

    # Validate prerequisites
    validate_prerequisites

    # Build images
    build_images

    # Start services
    start_services

    # Wait for services to be healthy
    wait_for_health

    # Run health tests
    run_health_tests

    # Display deployment info
    display_deployment_info

    log_section "Deployment Complete"
    log_success "SARK is now running!"

    echo ""
    log_info "View logs with: docker compose logs -f"
    log_info "Stop with: docker compose --profile $PROFILE down"

    return 0
}

# Validate arguments
case "$ENVIRONMENT" in
    development|staging|production)
        ;;
    *)
        echo "Usage: $0 [development|staging|production] [minimal|standard|full]"
        echo "Invalid environment: $ENVIRONMENT"
        exit 1
        ;;
esac

case "$PROFILE" in
    minimal|standard|full|managed)
        ;;
    *)
        echo "Usage: $0 [development|staging|production] [minimal|standard|full]"
        echo "Invalid profile: $PROFILE"
        exit 1
        ;;
esac

# Run main function
main
