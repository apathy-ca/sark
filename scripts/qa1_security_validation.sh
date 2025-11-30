#!/bin/bash
#
# QA-1 Security Validation Script
# Purpose: Validate all security fixes for SARK v2.0.0 release
# Priority: P0 - Blocking release
#
# Usage: ./scripts/qa1_security_validation.sh
#

set -e  # Exit on error

echo "=================================================="
echo "QA-1 SECURITY VALIDATION FOR SARK v2.0.0"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Function to run test and check result
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo ""
    echo "=========================================="
    echo "Running: $test_name"
    echo "=========================================="

    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED${NC}: $test_name"
    else
        echo -e "${RED}❌ FAILED${NC}: $test_name"
        FAILED=$((FAILED + 1))
    fi
}

echo "Step 1: API Keys Security Tests"
echo "================================="
run_test "API Keys Authentication Tests" \
    "python -m pytest tests/security/test_api_keys_security.py::TestAPIKeysAuthentication -v"

run_test "API Keys Authorization Tests" \
    "python -m pytest tests/security/test_api_keys_security.py::TestAPIKeysAuthorization -v"

run_test "API Keys Vulnerability Tests" \
    "python -m pytest tests/security/test_api_keys_security.py::TestAPIKeysSecurityVulnerabilities -v"

echo ""
echo "Step 2: OIDC Security Tests"
echo "============================"
run_test "OIDC State Security Tests" \
    "python -m pytest tests/security/test_oidc_security.py::TestOIDCStateSecurity -v"

run_test "OIDC Callback Security Tests" \
    "python -m pytest tests/security/test_oidc_security.py::TestOIDCCallbackSecurity -v"

run_test "OIDC Session Security Tests" \
    "python -m pytest tests/security/test_oidc_security.py::TestOIDCSessionSecurity -v"

echo ""
echo "Step 3: Full Security Test Suite"
echo "================================="
run_test "All Security Tests" \
    "python -m pytest tests/security/test_api_keys_security.py tests/security/test_oidc_security.py -v"

echo ""
echo "Step 4: Existing V2 Security Tests"
echo "==================================="
run_test "V2 mTLS Security Tests" \
    "python -m pytest tests/security/v2/test_mtls_security.py -v --tb=line"

run_test "V2 Penetration Scenarios" \
    "python -m pytest tests/security/v2/test_penetration_scenarios.py -v --tb=line"

echo ""
echo "Step 5: Integration Tests (Regression Check)"
echo "=============================================="
run_test "Full Integration Test Suite" \
    "python -m pytest tests/integration/v2/ -v --tb=line"

echo ""
echo "=================================================="
echo "SECURITY VALIDATION SUMMARY"
echo "=================================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL SECURITY TESTS PASSED${NC}"
    echo ""
    echo "Security Status: READY FOR RELEASE"
    echo "Critical Issues: RESOLVED"
    echo "Regressions: ZERO"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $FAILED TEST SUITE(S) FAILED${NC}"
    echo ""
    echo "Security Status: NOT READY FOR RELEASE"
    echo "Action Required: Fix failing tests before v2.0.0 tag"
    echo ""
    exit 1
fi
