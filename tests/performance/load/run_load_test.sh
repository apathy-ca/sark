#!/usr/bin/env bash
#
# SARK Authorization Load Test Runner
#
# Runs load tests with predefined scenarios:
# - baseline: 100 req/s (current production)
# - target: 2,000 req/s (v1.4.0 goal)
# - stress: 5,000 req/s (find breaking point)
#
# Usage:
#   ./run_load_test.sh baseline
#   ./run_load_test.sh target
#   ./run_load_test.sh stress
#   ./run_load_test.sh all
#

set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Output directory
REPORTS_DIR="${SCRIPT_DIR}/reports"
mkdir -p "$REPORTS_DIR"

# Server URL
SARK_URL="${SARK_URL:-http://localhost:8000}"

# ==============================================================================
# Color output
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# ==============================================================================
# Scenario Configurations
# ==============================================================================

run_baseline() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_prefix="${REPORTS_DIR}/baseline_${timestamp}"

    log_info "Running BASELINE load test (100 req/s)"
    log_info "  Users: 50"
    log_info "  Spawn rate: 5/s"
    log_info "  Duration: 30 minutes"
    log_info "  Report: ${report_prefix}.html"

    locust \
        -f locustfile.py \
        --host="$SARK_URL" \
        --users 50 \
        --spawn-rate 5 \
        --run-time 30m \
        --html="${report_prefix}.html" \
        --csv="${report_prefix}" \
        --headless \
        --print-stats \
        --only-summary

    log_success "Baseline test complete"
}

run_target() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_prefix="${REPORTS_DIR}/target_${timestamp}"

    log_info "Running TARGET load test (2,000 req/s)"
    log_info "  Users: 1000"
    log_info "  Spawn rate: 100/s"
    log_info "  Duration: 30 minutes"
    log_info "  Report: ${report_prefix}.html"

    locust \
        -f locustfile.py \
        --host="$SARK_URL" \
        --users 1000 \
        --spawn-rate 100 \
        --run-time 30m \
        --html="${report_prefix}.html" \
        --csv="${report_prefix}" \
        --headless \
        --print-stats \
        --only-summary

    log_success "Target test complete"
}

run_stress() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_prefix="${REPORTS_DIR}/stress_${timestamp}"

    log_info "Running STRESS load test (5,000 req/s)"
    log_info "  Users: 2500"
    log_info "  Spawn rate: 250/s"
    log_info "  Duration: 10 minutes"
    log_info "  Report: ${report_prefix}.html"

    locust \
        -f locustfile.py \
        --host="$SARK_URL" \
        --users 2500 \
        --spawn-rate 250 \
        --run-time 10m \
        --html="${report_prefix}.html" \
        --csv="${report_prefix}" \
        --headless \
        --print-stats \
        --only-summary

    log_success "Stress test complete"
}

run_cache_hit() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_prefix="${REPORTS_DIR}/cache_hit_${timestamp}"

    log_info "Running CACHE HIT load test"
    log_info "  User class: ReadHeavyUser"
    log_info "  Users: 500"
    log_info "  Spawn rate: 50/s"
    log_info "  Duration: 10 minutes"
    log_info "  Report: ${report_prefix}.html"

    locust \
        -f locustfile.py \
        --host="$SARK_URL" \
        --users 500 \
        --spawn-rate 50 \
        --run-time 10m \
        --html="${report_prefix}.html" \
        --csv="${report_prefix}" \
        ReadHeavyUser \
        --headless \
        --print-stats \
        --only-summary

    log_success "Cache hit test complete"
}

run_cache_miss() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_prefix="${REPORTS_DIR}/cache_miss_${timestamp}"

    log_info "Running CACHE MISS load test"
    log_info "  User class: CacheMissUser"
    log_info "  Users: 200"
    log_info "  Spawn rate: 20/s"
    log_info "  Duration: 10 minutes"
    log_info "  Report: ${report_prefix}.html"

    locust \
        -f locustfile.py \
        --host="$SARK_URL" \
        --users 200 \
        --spawn-rate 20 \
        --run-time 10m \
        --html="${report_prefix}.html" \
        --csv="${report_prefix}" \
        CacheMissUser \
        --headless \
        --print-stats \
        --only-summary

    log_success "Cache miss test complete"
}

run_complex_policy() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_prefix="${REPORTS_DIR}/complex_${timestamp}"

    log_info "Running COMPLEX POLICY load test"
    log_info "  User class: ComplexPolicyUser"
    log_info "  Users: 300"
    log_info "  Spawn rate: 30/s"
    log_info "  Duration: 10 minutes"
    log_info "  Report: ${report_prefix}.html"

    locust \
        -f locustfile.py \
        --host="$SARK_URL" \
        --users 300 \
        --spawn-rate 30 \
        --run-time 10m \
        --html="${report_prefix}.html" \
        --csv="${report_prefix}" \
        ComplexPolicyUser \
        --headless \
        --print-stats \
        --only-summary

    log_success "Complex policy test complete"
}

# ==============================================================================
# Health Check
# ==============================================================================

check_server() {
    log_info "Checking server at $SARK_URL..."

    if curl -s -f "${SARK_URL}/health" > /dev/null 2>&1; then
        log_success "Server is responsive"
        return 0
    else
        log_error "Server is not responsive at $SARK_URL"
        log_error "Start the server or set SARK_URL environment variable"
        return 1
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    local scenario="${1:-help}"

    echo ""
    echo "=========================================="
    echo "SARK Authorization Load Test Runner"
    echo "=========================================="
    echo ""

    # Check if locust is installed
    if ! command -v locust &> /dev/null; then
        log_error "Locust is not installed"
        log_info "Install with: pip install locust"
        exit 1
    fi

    # Check server health
    if [ "$scenario" != "help" ]; then
        if ! check_server; then
            exit 1
        fi
    fi

    case "$scenario" in
        baseline)
            run_baseline
            ;;
        target)
            run_target
            ;;
        stress)
            run_stress
            ;;
        cache-hit)
            run_cache_hit
            ;;
        cache-miss)
            run_cache_miss
            ;;
        complex)
            run_complex_policy
            ;;
        all)
            log_info "Running all scenarios..."
            run_baseline
            sleep 60  # Cool-down period
            run_target
            sleep 60
            run_stress
            sleep 60
            run_cache_hit
            sleep 60
            run_cache_miss
            sleep 60
            run_complex_policy
            log_success "All scenarios complete"
            ;;
        help|*)
            echo "Usage: $0 <scenario>"
            echo ""
            echo "Scenarios:"
            echo "  baseline     - 100 req/s (current production)"
            echo "  target       - 2,000 req/s (v1.4.0 goal)"
            echo "  stress       - 5,000 req/s (find breaking point)"
            echo "  cache-hit    - High cache hit rate scenario"
            echo "  cache-miss   - Cold cache scenario"
            echo "  complex      - Complex multi-tenant policies"
            echo "  all          - Run all scenarios"
            echo ""
            echo "Environment Variables:"
            echo "  SARK_URL     - Server URL (default: http://localhost:8000)"
            echo ""
            echo "Examples:"
            echo "  $0 baseline"
            echo "  $0 target"
            echo "  SARK_URL=http://staging.example.com $0 stress"
            echo ""
            exit 0
            ;;
    esac

    echo ""
    echo "=========================================="
    echo "Reports saved to: $REPORTS_DIR"
    echo "=========================================="
    echo ""
}

main "$@"
