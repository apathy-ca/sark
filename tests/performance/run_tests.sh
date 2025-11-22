#!/bin/bash
# Performance Test Runner
#
# This script provides convenient shortcuts for running common performance test scenarios.
#
# Usage:
#   ./run_tests.sh smoke              # Quick smoke test
#   ./run_tests.sh load_moderate      # Moderate load test (100 users, 5 min)
#   ./run_tests.sh load_high          # High load test (500 users, 10 min)
#   ./run_tests.sh server_registration # Server registration focused test
#   ./run_tests.sh policy_evaluation  # Policy evaluation focused test
#   ./run_tests.sh stress             # Stress test (1000 users, 15 min)
#   ./run_tests.sh soak               # Soak test (50 users, 30 min)

set -e

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
REPORT_DIR="reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create reports directory
mkdir -p "$REPORT_DIR"

# Print header
print_header() {
    echo -e "${BLUE}"
    echo "========================================="
    echo "  SARK Performance Test Runner"
    echo "========================================="
    echo -e "${NC}"
}

# Print test info
print_test_info() {
    local scenario=$1
    local users=$2
    local duration=$3
    local user_class=$4

    echo -e "${GREEN}Starting Test:${NC}"
    echo "  Scenario:    $scenario"
    echo "  Users:       $users"
    echo "  Duration:    $duration"
    echo "  User Class:  $user_class"
    echo "  Base URL:    $BASE_URL"
    echo "  Report Dir:  $REPORT_DIR"
    echo ""
}

# Run Locust test
run_locust_test() {
    local scenario=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local user_class=$5

    local report_name="${scenario}_${TIMESTAMP}"
    local html_report="${REPORT_DIR}/${report_name}.html"
    local csv_report="${REPORT_DIR}/${report_name}"

    print_test_info "$scenario" "$users" "$duration" "$user_class"

    echo -e "${YELLOW}Running Locust test...${NC}"
    echo ""

    locust -f locustfile.py \
        --host="$BASE_URL" \
        --users="$users" \
        --spawn-rate="$spawn_rate" \
        --run-time="$duration" \
        --headless \
        --html="$html_report" \
        --csv="$csv_report" \
        --loglevel=INFO \
        $user_class

    echo ""
    echo -e "${GREEN}✓ Test completed successfully${NC}"
    echo ""
    echo "Reports generated:"
    echo "  HTML:  $html_report"
    echo "  CSV:   ${csv_report}_stats.csv"
    echo ""

    # Analyze results
    if [ -f "analyze_results.py" ]; then
        echo -e "${YELLOW}Analyzing results...${NC}"
        python3 analyze_results.py --csv "${csv_report}_stats.csv"
    fi
}

# Test scenarios
run_smoke_test() {
    print_header
    echo "Running smoke test to verify basic functionality..."
    echo ""
    run_locust_test "smoke" 1 1 "30s" "MixedWorkloadUser"
}

run_load_moderate() {
    print_header
    echo "Running moderate load test (100 users, 5 minutes)..."
    echo ""
    run_locust_test "load_moderate" 100 10 "5m" "MixedWorkloadUser"
}

run_load_high() {
    print_header
    echo "Running high load test (500 users, 10 minutes)..."
    echo ""
    run_locust_test "load_high" 500 50 "10m" "MixedWorkloadUser"
}

run_server_registration() {
    print_header
    echo "Running server registration focused test..."
    echo "Target: 1000 req/s, p95 < 200ms"
    echo ""
    run_locust_test "server_registration" 200 20 "5m" "ServerRegistrationUser"
}

run_policy_evaluation() {
    print_header
    echo "Running policy evaluation focused test..."
    echo "Target: p95 < 50ms"
    echo ""
    run_locust_test "policy_evaluation" 500 50 "5m" "PolicyEvaluationUser"
}

run_stress_test() {
    print_header
    echo "Running stress test to find breaking point..."
    echo "Warning: This may push the system beyond its limits!"
    echo ""
    run_locust_test "stress" 1000 100 "15m" "MixedWorkloadUser"
}

run_soak_test() {
    print_header
    echo "Running soak test (30 minutes)..."
    echo "This will take a while. Monitor for memory leaks and performance degradation."
    echo ""
    run_locust_test "soak" 50 10 "30m" "MixedWorkloadUser"
}

run_rate_limit_test() {
    print_header
    echo "Running rate limit test..."
    echo ""
    run_locust_test "rate_limit" 100 100 "2m" "RateLimitTestUser"
}

run_database_stress() {
    print_header
    echo "Running database stress test..."
    echo "Target: DB queries < 20ms"
    echo ""
    run_locust_test "database_stress" 200 20 "10m" "DatabaseStressUser"
}

run_concurrent_operations() {
    print_header
    echo "Running concurrent operations test..."
    echo ""
    run_locust_test "concurrent_ops" 300 50 "5m" "ConcurrentOperationsUser"
}

run_all_tests() {
    print_header
    echo "Running ALL test scenarios (this will take a long time)..."
    echo ""
    read -p "Are you sure you want to run all tests? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi

    run_smoke_test
    echo ""; echo "Waiting 30 seconds before next test..."; sleep 30

    run_load_moderate
    echo ""; echo "Waiting 30 seconds before next test..."; sleep 30

    run_server_registration
    echo ""; echo "Waiting 30 seconds before next test..."; sleep 30

    run_policy_evaluation
    echo ""; echo "Waiting 30 seconds before next test..."; sleep 30

    echo ""
    echo -e "${GREEN}✓ All tests completed!${NC}"
    echo "Reports saved to: $REPORT_DIR"
}

# Main
SCENARIO="${1:-help}"

case "$SCENARIO" in
    smoke)
        run_smoke_test
        ;;
    load_moderate|load-moderate|moderate)
        run_load_moderate
        ;;
    load_high|load-high|high)
        run_load_high
        ;;
    server_registration|server-registration|registration)
        run_server_registration
        ;;
    policy_evaluation|policy-evaluation|policy)
        run_policy_evaluation
        ;;
    stress)
        run_stress_test
        ;;
    soak)
        run_soak_test
        ;;
    rate_limit|rate-limit|ratelimit)
        run_rate_limit_test
        ;;
    database_stress|database-stress|db-stress)
        run_database_stress
        ;;
    concurrent|concurrent_operations|concurrent-operations)
        run_concurrent_operations
        ;;
    all)
        run_all_tests
        ;;
    help|--help|-h|*)
        print_header
        echo "Usage: $0 <scenario>"
        echo ""
        echo "Available scenarios:"
        echo "  smoke                 - Quick smoke test (1 user, 30s)"
        echo "  load_moderate         - Moderate load (100 users, 5m)"
        echo "  load_high             - High load (500 users, 10m)"
        echo "  server_registration   - Server registration test (200 users, 5m)"
        echo "  policy_evaluation     - Policy evaluation test (500 users, 5m)"
        echo "  stress                - Stress test (1000 users, 15m)"
        echo "  soak                  - Soak test (50 users, 30m)"
        echo "  rate_limit            - Rate limit test (100 users, 2m)"
        echo "  database_stress       - Database stress test (200 users, 10m)"
        echo "  concurrent            - Concurrent operations test (300 users, 5m)"
        echo "  all                   - Run all scenarios (sequential)"
        echo ""
        echo "Environment variables:"
        echo "  BASE_URL              - API base URL (default: http://localhost:8000)"
        echo "  TEST_API_KEY          - API key for authentication"
        echo ""
        echo "Examples:"
        echo "  $0 smoke"
        echo "  BASE_URL=http://staging.example.com:8000 $0 load_moderate"
        echo ""
        exit 0
        ;;
esac

exit 0
