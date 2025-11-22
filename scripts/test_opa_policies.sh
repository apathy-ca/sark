#!/bin/bash
# OPA Policy Test Runner
# Tests all SARK default OPA policies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "SARK OPA Policy Test Suite"
echo "=========================================="
echo ""

# Check if OPA is installed
if ! command -v opa &> /dev/null; then
    echo -e "${RED}ERROR: OPA is not installed${NC}"
    echo ""
    echo "To install OPA, run:"
    echo "  curl -L -o /tmp/opa https://github.com/open-policy-agent/opa/releases/download/v0.60.0/opa_linux_amd64_static"
    echo "  chmod +x /tmp/opa"
    echo "  sudo mv /tmp/opa /usr/local/bin/opa"
    echo ""
    echo "Or use the provided installation script:"
    echo "  bash /tmp/install_opa.sh"
    exit 1
fi

# Display OPA version
echo -e "${GREEN}OPA Version:${NC}"
opa version
echo ""

# Change to policy directory
POLICY_DIR="opa/policies/defaults"
if [ ! -d "$POLICY_DIR" ]; then
    echo -e "${RED}ERROR: Policy directory not found: $POLICY_DIR${NC}"
    exit 1
fi

echo "Testing policies in: $POLICY_DIR"
echo ""

# Test 1: Check policy syntax
echo -e "${YELLOW}[1/4] Checking policy syntax...${NC}"
if opa check "$POLICY_DIR"; then
    echo -e "${GREEN}✓ Syntax check passed${NC}"
else
    echo -e "${RED}✗ Syntax check failed${NC}"
    exit 1
fi
echo ""

# Test 2: Run all policy tests
echo -e "${YELLOW}[2/4] Running policy tests...${NC}"
if opa test "$POLICY_DIR" -v; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
echo ""

# Test 3: Generate test coverage report
echo -e "${YELLOW}[3/4] Generating test coverage report...${NC}"
opa test "$POLICY_DIR" --coverage --format=json > /tmp/opa_coverage.json
COVERAGE=$(cat /tmp/opa_coverage.json | grep -o '"coverage":[0-9.]*' | head -1 | cut -d':' -f2)
echo -e "${GREEN}✓ Test coverage: ${COVERAGE}%${NC}"

# Check if coverage meets minimum threshold (85%)
THRESHOLD=85
if (( $(echo "$COVERAGE >= $THRESHOLD" | bc -l) )); then
    echo -e "${GREEN}✓ Coverage meets threshold (>=${THRESHOLD}%)${NC}"
else
    echo -e "${RED}✗ Coverage below threshold (${THRESHOLD}%)${NC}"
    exit 1
fi
echo ""

# Test 4: Run policy benchmarks
echo -e "${YELLOW}[4/4] Running policy benchmarks...${NC}"
if opa test "$POLICY_DIR" --bench; then
    echo -e "${GREEN}✓ Benchmarks completed${NC}"
else
    echo -e "${YELLOW}⚠ Benchmarks not available (optional)${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}All tests passed successfully!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Syntax: ✓"
echo "  - Tests: ✓"
echo "  - Coverage: ${COVERAGE}%"
echo ""
echo "Next steps:"
echo "  1. Review test coverage report: /tmp/opa_coverage.json"
echo "  2. Integrate with CI/CD pipeline"
echo "  3. Deploy policies to OPA server"
echo ""
