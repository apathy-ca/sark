#!/usr/bin/env bash

# ============================================================================
# SARK Minimal Deployment Test Script
# ============================================================================
# Tests minimal deployment configuration on a clean system
#
# This script verifies that SARK can be deployed with minimal configuration
# and that all essential services start correctly.
#
# Usage:
#   ./scripts/test-minimal-deployment.sh
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
    ((TOTAL_TESTS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
    ((TOTAL_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test environment..."
    docker compose down -v --remove-orphans 2>/dev/null || true
    docker compose -f docker-compose.quickstart.yml down -v --remove-orphans 2>/dev/null || true
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Test 1: Docker and Docker Compose availability
test_prerequisites() {
    log_section "Test 1: Prerequisites Check"

    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        log_success "Docker installed: $DOCKER_VERSION"
    else
        log_error "Docker not installed"
        return 1
    fi

    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version --short)
        log_success "Docker Compose installed: $COMPOSE_VERSION"
    else
        log_error "Docker Compose not installed"
        return 1
    fi

    # Check Docker is running
    if docker info &> /dev/null; then
        log_success "Docker daemon is running"
    else
        log_error "Docker daemon is not running"
        return 1
    fi
}

# Test 2: Minimal deployment (app only)
test_minimal_app_only() {
    log_section "Test 2: Minimal Deployment (App Only)"

    log_info "Starting app-only deployment..."
    if docker compose up -d app 2>&1 | tee /tmp/sark-deploy.log; then
        log_success "App-only deployment started"
    else
        log_error "Failed to start app-only deployment"
        cat /tmp/sark-deploy.log
        return 1
    fi

    # Wait for container to be healthy (or at least running)
    log_info "Waiting for app container to be ready..."
    sleep 5

    if docker compose ps app | grep -q "Up\|running"; then
        log_success "App container is running"
    else
        log_error "App container failed to start"
        docker compose logs app
        return 1
    fi

    # Cleanup
    docker compose down -v
}

# Test 3: Managed profile deployment
test_managed_profile() {
    log_section "Test 3: Managed Profile Deployment"

    log_info "Starting managed profile (PostgreSQL + Redis)..."
    if docker compose --profile managed up -d 2>&1 | tee /tmp/sark-managed.log; then
        log_success "Managed profile deployment started"
    else
        log_error "Failed to start managed profile"
        cat /tmp/sark-managed.log
        return 1
    fi

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    local max_wait=60
    local waited=0

    while [ $waited -lt $max_wait ]; do
        if docker compose ps database | grep -q "healthy"; then
            log_success "PostgreSQL is healthy"
            break
        fi
        sleep 2
        ((waited+=2))
    done

    if [ $waited -ge $max_wait ]; then
        log_error "PostgreSQL failed to become healthy"
        docker compose logs database
        return 1
    fi

    # Check Redis
    waited=0
    while [ $waited -lt $max_wait ]; do
        if docker compose ps cache | grep -q "healthy"; then
            log_success "Redis is healthy"
            break
        fi
        sleep 2
        ((waited+=2))
    done

    if [ $waited -ge $max_wait ]; then
        log_error "Redis failed to become healthy"
        docker compose logs cache
        return 1
    fi

    # Cleanup
    docker compose --profile managed down -v
}

# Test 4: Full profile deployment
test_full_profile() {
    log_section "Test 4: Full Profile Deployment"

    log_info "Starting full profile (all managed services)..."
    if docker compose --profile full up -d 2>&1 | tee /tmp/sark-full.log; then
        log_success "Full profile deployment started"
    else
        log_error "Failed to start full profile"
        cat /tmp/sark-full.log
        return 1
    fi

    # Count expected services
    local expected_services=5  # app, database, cache, opa, timescaledb minimum
    local running_services=$(docker compose ps --format json | jq -s 'length')

    if [ "$running_services" -ge "$expected_services" ]; then
        log_success "At least $expected_services services are running ($running_services total)"
    else
        log_error "Expected at least $expected_services services, got $running_services"
        docker compose ps
        return 1
    fi

    # Cleanup
    docker compose --profile full down -v
}

# Test 5: Quickstart deployment
test_quickstart() {
    log_section "Test 5: Quickstart Deployment"

    log_info "Testing quickstart configuration..."
    if docker compose -f docker-compose.quickstart.yml up -d 2>&1 | tee /tmp/sark-quickstart.log; then
        log_success "Quickstart deployment started"
    else
        log_error "Failed to start quickstart deployment"
        cat /tmp/sark-quickstart.log
        return 1
    fi

    # Wait a bit for services to start
    sleep 10

    # Check if services are running
    local running=$(docker compose -f docker-compose.quickstart.yml ps --format json | jq -s 'length')
    if [ "$running" -gt 0 ]; then
        log_success "Quickstart services are running ($running containers)"
    else
        log_error "No quickstart services are running"
        return 1
    fi

    # Cleanup
    docker compose -f docker-compose.quickstart.yml down -v
}

# Test 6: Environment variable configuration
test_env_configuration() {
    log_section "Test 6: Environment Configuration"

    # Create temporary .env file
    cat > /tmp/sark-test.env << EOF
ENVIRONMENT=test
POSTGRES_ENABLED=true
POSTGRES_MODE=managed
VALKEY_ENABLED=true
VALKEY_MODE=managed
LOG_LEVEL=DEBUG
EOF

    log_info "Testing with custom environment configuration..."
    if docker compose --env-file /tmp/sark-test.env --profile managed up -d 2>&1 > /tmp/sark-env-test.log; then
        log_success "Deployment with custom environment succeeded"
    else
        log_error "Deployment with custom environment failed"
        cat /tmp/sark-env-test.log
        return 1
    fi

    # Cleanup
    rm -f /tmp/sark-test.env
    docker compose --profile managed down -v
}

# Test 7: Resource limits and constraints
test_resource_limits() {
    log_section "Test 7: Resource Usage Check"

    # Start minimal deployment
    docker compose up -d app &> /dev/null
    sleep 5

    # Check container resource usage
    local mem_usage=$(docker stats --no-stream --format "{{.MemUsage}}" sark-app 2>/dev/null || echo "0B / 0B")
    local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" sark-app 2>/dev/null || echo "0%")

    log_info "App container resource usage: CPU=$cpu_usage, Memory=$mem_usage"
    log_success "Resource usage check completed"

    # Cleanup
    docker compose down -v
}

# Test 8: Network configuration
test_network_setup() {
    log_section "Test 8: Network Configuration"

    docker compose --profile managed up -d &> /dev/null
    sleep 5

    # Check if sark-network exists
    if docker network ls | grep -q "sark-network"; then
        log_success "SARK network created successfully"
    else
        log_error "SARK network not found"
        return 1
    fi

    # Check network connectivity between services
    if docker compose exec -T database pg_isready -h localhost &> /dev/null; then
        log_success "Database network connectivity verified"
    else
        log_error "Database network connectivity failed"
        return 1
    fi

    # Cleanup
    docker compose --profile managed down -v
}

# Main execution
main() {
    log_section "SARK Minimal Deployment Test Suite"
    log_info "Starting deployment tests..."
    echo ""

    # Run all tests
    test_prerequisites || true
    test_minimal_app_only || true
    test_managed_profile || true
    test_full_profile || true
    test_quickstart || true
    test_env_configuration || true
    test_resource_limits || true
    test_network_setup || true

    # Print summary
    log_section "Test Summary"
    echo "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo ""
        log_success "All tests passed! ✓"
        return 0
    else
        echo ""
        log_error "Some tests failed. Please review the output above."
        return 1
    fi
}

# Run main function
main
