#!/usr/bin/env bash

# ============================================================================
# SARK Health Check Test Script
# ============================================================================
# Tests all health check endpoints and service connectivity
#
# This script verifies that SARK's health check system is working correctly
# and that all services can be properly monitored.
#
# Usage:
#   ./scripts/test-health-checks.sh [profile]
#
# Arguments:
#   profile - Docker Compose profile to test (minimal, standard, full)
#             Default: standard
#
# Exit codes:
#   0 - All health checks passed
#   1 - One or more health checks failed
# ============================================================================

set -euo pipefail

# Default profile
PROFILE="${1:-standard}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Configuration
BASE_URL="http://localhost:8000"
MAX_WAIT_TIME=120  # seconds

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker compose --profile "$PROFILE" down -v 2>/dev/null || true
}

trap cleanup EXIT

# Test HTTP endpoint
test_http_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="$3"

    log_info "Testing $description: $endpoint"

    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint" || echo "000")

    if [ "$status_code" = "$expected_status" ]; then
        log_success "$description returned $status_code"
        return 0
    else
        log_error "$description returned $status_code (expected $expected_status)"
        return 1
    fi
}

# Wait for service to be ready
wait_for_service() {
    local url="$1"
    local service_name="$2"
    local waited=0

    log_info "Waiting for $service_name to be ready..."

    while [ $waited -lt $MAX_WAIT_TIME ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready (waited ${waited}s)"
            return 0
        fi
        sleep 2
        ((waited+=2))
    done

    log_error "$service_name failed to become ready after ${MAX_WAIT_TIME}s"
    return 1
}

# Main test execution
main() {
    log_section "SARK Health Check Test Suite - Profile: $PROFILE"

    # Start services
    log_info "Starting services with profile: $PROFILE"
    if ! docker compose --profile "$PROFILE" up -d 2>&1 | tee /tmp/sark-health-test.log; then
        log_error "Failed to start services"
        cat /tmp/sark-health-test.log
        exit 1
    fi

    log_success "Services started successfully"

    # Wait for app to be ready
    if wait_for_service "$BASE_URL/health" "SARK API"; then
        :
    else
        docker compose logs app
        exit 1
    fi

    # Test basic health endpoint
    log_section "Basic Health Checks"
    test_http_endpoint "$BASE_URL/health" "200" "Basic health endpoint" || true
    test_http_endpoint "$BASE_URL/health/" "200" "Basic health endpoint (with slash)" || true

    # Test readiness endpoint
    log_section "Readiness Checks"
    test_http_endpoint "$BASE_URL/ready" "200" "Readiness endpoint" || true
    test_http_endpoint "$BASE_URL/health/ready" "200" "Readiness endpoint (alt path)" || true

    # Test liveness endpoint
    log_section "Liveness Checks"
    test_http_endpoint "$BASE_URL/live" "200" "Liveness endpoint" || true
    test_http_endpoint "$BASE_URL/health/live" "200" "Liveness endpoint (alt path)" || true

    # Test startup endpoint
    log_section "Startup Checks"
    test_http_endpoint "$BASE_URL/startup" "200" "Startup endpoint" || true
    test_http_endpoint "$BASE_URL/health/startup" "200" "Startup endpoint (alt path)" || true

    # Test metrics endpoint
    log_section "Metrics Endpoint"
    test_http_endpoint "$BASE_URL/metrics" "200" "Prometheus metrics" || true

    # Test API docs
    log_section "API Documentation"
    test_http_endpoint "$BASE_URL/docs" "200" "Swagger UI" || true
    test_http_endpoint "$BASE_URL/redoc" "200" "ReDoc" || true
    test_http_endpoint "$BASE_URL/openapi.json" "200" "OpenAPI spec" || true

    # Test service-specific health checks
    if [ "$PROFILE" = "standard" ] || [ "$PROFILE" = "full" ]; then
        log_section "Service Health Checks (PostgreSQL)"

        # Check PostgreSQL container health
        if docker compose exec -T database pg_isready -U sark > /dev/null 2>&1; then
            log_success "PostgreSQL is healthy (pg_isready)"
        else
            log_error "PostgreSQL is not healthy"
        fi

        # Check PostgreSQL connectivity from app
        if docker compose exec -T app python -c "import psycopg2; conn = psycopg2.connect(host='database', user='sark', password='sark', database='sark'); conn.close()" 2>/dev/null; then
            log_success "PostgreSQL connectivity from app works"
        else
            log_error "PostgreSQL connectivity from app failed"
        fi

        log_section "Service Health Checks (Redis)"

        # Check Redis container health
        if docker compose exec -T cache redis-cli ping | grep -q "PONG"; then
            log_success "Redis is healthy (PING)"
        else
            log_error "Redis is not healthy"
        fi
    fi

    if [ "$PROFILE" = "full" ]; then
        log_section "Service Health Checks (Kong)"

        # Check Kong health
        if curl -sf http://localhost:8001/status > /dev/null 2>&1; then
            log_success "Kong Admin API is healthy"
        else
            log_error "Kong Admin API is not healthy"
        fi
    fi

    # Test negative cases
    log_section "Negative Test Cases"
    test_http_endpoint "$BASE_URL/nonexistent" "404" "Non-existent endpoint returns 404" || true

    # Performance check - response time
    log_section "Performance Check"
    local response_time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' "$BASE_URL/health")
    response_time_ms=$(echo "$response_time * 1000" | bc)

    log_info "Health endpoint response time: ${response_time_ms}ms"

    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        log_success "Response time is acceptable (<1s): ${response_time_ms}ms"
    else
        log_error "Response time is too slow (>1s): ${response_time_ms}ms"
    fi

    # Print summary
    log_section "Test Summary"
    echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo ""
        log_success "All health checks passed! ✓"
        return 0
    else
        echo ""
        log_error "Some health checks failed. Please review the output above."
        return 1
    fi
}

# Validate profile argument
case "$PROFILE" in
    minimal|standard|full|managed)
        ;;
    *)
        echo "Usage: $0 [minimal|standard|full]"
        echo "Invalid profile: $PROFILE"
        exit 1
        ;;
esac

# Run main function
main
