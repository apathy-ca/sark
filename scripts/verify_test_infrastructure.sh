#!/usr/bin/env bash
# Script to verify test infrastructure is working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SARK Test Infrastructure Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Track results
TESTS_PASSED=0
TESTS_FAILED=0
WARNINGS=0

# Function to report success
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

# Function to report failure
fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

# Function to report warning
warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "Checking prerequisites..."
echo

# Check Docker
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        pass "Docker is installed and running"
    else
        fail "Docker is installed but not running"
    fi
else
    fail "Docker is not installed"
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ $(echo "$PYTHON_VERSION" | cut -d'.' -f1) -ge 3 ]] && [[ $(echo "$PYTHON_VERSION" | cut -d'.' -f2) -ge 11 ]]; then
        pass "Python 3.11+ is installed ($PYTHON_VERSION)"
    else
        warn "Python version is $PYTHON_VERSION (3.11+ recommended)"
    fi
else
    fail "Python 3 is not installed"
fi

# Check pytest
if python3 -c "import pytest" 2>/dev/null; then
    pass "pytest is installed"
else
    fail "pytest is not installed (run: pip install pytest)"
fi

# Check pytest-docker
if python3 -c "import pytest_docker" 2>/dev/null; then
    pass "pytest-docker is installed"
else
    warn "pytest-docker is not installed (run: pip install pytest-docker)"
fi

# Check asyncpg
if python3 -c "import asyncpg" 2>/dev/null; then
    pass "asyncpg is installed"
else
    warn "asyncpg is not installed (run: pip install asyncpg)"
fi

# Check redis
if python3 -c "import redis" 2>/dev/null; then
    pass "redis library is installed"
else
    warn "redis library is not installed (run: pip install redis)"
fi

echo

# Check Docker Compose files
echo "Checking Docker Compose files..."
echo

if [ -f "tests/fixtures/docker-compose.integration.yml" ]; then
    pass "Integration test Docker Compose file exists"
else
    fail "Integration test Docker Compose file is missing"
fi

if [ -f "tests/fixtures/docker-compose.ldap.yml" ]; then
    pass "LDAP test Docker Compose file exists"
else
    warn "LDAP test Docker Compose file is missing"
fi

if [ -f "tests/fixtures/docker-compose.oidc.yml" ]; then
    pass "OIDC test Docker Compose file exists"
else
    warn "OIDC test Docker Compose file is missing"
fi

if [ -f "tests/fixtures/docker-compose.saml.yml" ]; then
    pass "SAML test Docker Compose file exists"
else
    warn "SAML test Docker Compose file is missing"
fi

echo

# Check fixture files
echo "Checking fixture files..."
echo

if [ -f "tests/fixtures/integration_docker.py" ]; then
    pass "Integration Docker fixtures file exists"
else
    fail "Integration Docker fixtures file is missing"
fi

if [ -f "tests/fixtures/ldap_docker.py" ]; then
    pass "LDAP Docker fixtures file exists"
else
    warn "LDAP Docker fixtures file is missing"
fi

if [ -f "tests/fixtures/oidc_docker.py" ]; then
    pass "OIDC Docker fixtures file exists"
else
    warn "OIDC Docker fixtures file is missing"
fi

if [ -f "tests/fixtures/saml_docker.py" ]; then
    pass "SAML Docker fixtures file exists"
else
    warn "SAML Docker fixtures file is missing"
fi

echo

# Check test runner scripts
echo "Checking test runner scripts..."
echo

if [ -f "scripts/run_integration_tests.sh" ] && [ -x "scripts/run_integration_tests.sh" ]; then
    pass "Integration test runner script exists and is executable"
elif [ -f "scripts/run_integration_tests.sh" ]; then
    warn "Integration test runner exists but is not executable (run: chmod +x scripts/run_integration_tests.sh)"
else
    fail "Integration test runner script is missing"
fi

if [ -f "scripts/run_auth_tests.sh" ] && [ -x "scripts/run_auth_tests.sh" ]; then
    pass "Auth test runner script exists and is executable"
elif [ -f "scripts/run_auth_tests.sh" ]; then
    warn "Auth test runner exists but is not executable (run: chmod +x scripts/run_auth_tests.sh)"
else
    warn "Auth test runner script is missing"
fi

echo

# Check documentation
echo "Checking documentation..."
echo

if [ -f "tests/README_INTEGRATION_TESTS.md" ]; then
    pass "Integration tests README exists"
else
    warn "Integration tests README is missing"
fi

if [ -f "tests/README_AUTH_TESTS.md" ]; then
    pass "Auth tests README exists"
else
    warn "Auth tests README is missing"
fi

if [ -f "docs/TEST_MIGRATION_GUIDE.md" ]; then
    pass "Test migration guide exists"
else
    warn "Test migration guide is missing"
fi

echo

# Check example test file
echo "Checking example test files..."
echo

if [ -f "tests/integration/test_docker_infrastructure_example.py" ]; then
    pass "Example integration test file exists"
else
    warn "Example integration test file is missing"
fi

echo

# Try to start and verify Docker services
echo "Testing Docker services..."
echo

if [ "$1" == "--skip-docker" ]; then
    warn "Skipping Docker service tests (--skip-docker flag)"
else
    echo "Starting integration test services..."
    if docker compose -f tests/fixtures/docker-compose.integration.yml up -d 2>&1 | grep -q "Error"; then
        fail "Failed to start Docker services"
    else
        pass "Docker services started successfully"

        # Wait a bit for services to be ready
        echo "Waiting for services to be ready..."
        sleep 10

        # Check PostgreSQL
        if docker exec sark_test_postgres pg_isready -U sark_test &>/dev/null; then
            pass "PostgreSQL is ready"
        else
            fail "PostgreSQL is not responding"
        fi

        # Check Redis
        if docker exec sark_test_redis redis-cli ping 2>&1 | grep -q "PONG"; then
            pass "Redis is ready"
        else
            fail "Redis is not responding"
        fi

        # Check OPA
        if curl -s http://localhost:8181/health 2>&1 | grep -q "ok"; then
            pass "OPA is ready"
        else
            fail "OPA is not responding"
        fi

        # Cleanup
        echo
        echo "Cleaning up test services..."
        docker compose -f tests/fixtures/docker-compose.integration.yml down -v &>/dev/null
        pass "Services cleaned up successfully"
    fi
fi

echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo -e "  - Passed: $TESTS_PASSED"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "  - Warnings: $WARNINGS ${YELLOW}(non-critical)${NC}"
    fi
    echo
    echo "Your test infrastructure is ready to use!"
    echo
    echo "Next steps:"
    echo "  1. Run integration tests: ./scripts/run_integration_tests.sh run"
    echo "  2. Run auth tests: ./scripts/run_auth_tests.sh run"
    echo "  3. Check documentation: tests/README_INTEGRATION_TESTS.md"
    exit 0
else
    echo -e "${RED}✗ Verification failed!${NC}"
    echo -e "  - Passed: $TESTS_PASSED"
    echo -e "  - Failed: $TESTS_FAILED"
    echo -e "  - Warnings: $WARNINGS"
    echo
    echo "Please fix the issues above before running tests."
    echo
    echo "Common fixes:"
    echo "  - Install Docker: https://docs.docker.com/get-docker/"
    echo "  - Install Python deps: pip install -e \".[dev]\" pytest-docker"
    echo "  - Make scripts executable: chmod +x scripts/*.sh"
    exit 1
fi
