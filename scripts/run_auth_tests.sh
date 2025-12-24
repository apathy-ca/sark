#!/usr/bin/env bash
# Script to run auth provider tests with proper Docker infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SARK Auth Provider Test Runner${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Function to check if Docker is running
check_docker() {
    echo -e "${YELLOW}Checking Docker...${NC}"
    if ! docker ps > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running${NC}"
        echo "Please start Docker and try again"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is running${NC}"
    echo
}

# Function to cleanup containers
cleanup() {
    echo -e "${YELLOW}Cleaning up test containers...${NC}"
    docker stop test_ldap test_oidc test_saml_idp 2>/dev/null || true
    docker rm test_ldap test_oidc test_saml_idp 2>/dev/null || true
    echo -e "${GREEN}✓ Cleanup complete${NC}"
    echo
}

# Function to start Docker services
start_services() {
    echo -e "${YELLOW}Starting test services...${NC}"

    # Start LDAP
    echo "Starting LDAP..."
    docker compose -f tests/fixtures/docker-compose.ldap.yml up -d

    # Start OIDC
    echo "Starting OIDC..."
    docker compose -f tests/fixtures/docker-compose.oidc.yml up -d

    # Start SAML
    echo "Starting SAML..."
    docker compose -f tests/fixtures/docker-compose.saml.yml up -d

    echo -e "${GREEN}✓ Services started${NC}"
    echo
}

# Function to wait for services
wait_for_services() {
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"

    # Wait for LDAP
    echo -n "Waiting for LDAP... "
    timeout=30
    while ! docker exec test_ldap ldapsearch -x -H ldap://localhost:389 -b dc=example,dc=com -D "cn=admin,dc=example,dc=com" -w admin > /dev/null 2>&1; do
        sleep 1
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            echo -e "${RED}TIMEOUT${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}OK${NC}"

    # Wait for OIDC
    echo -n "Waiting for OIDC... "
    timeout=30
    while ! curl -s http://localhost:8080/default/.well-known/openid-configuration > /dev/null; do
        sleep 1
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            echo -e "${RED}TIMEOUT${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}OK${NC}"

    # Wait for SAML
    echo -n "Waiting for SAML... "
    timeout=30
    while ! curl -s http://localhost:8082/simplesaml/ > /dev/null; do
        sleep 1
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            echo -e "${RED}TIMEOUT${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}OK${NC}"

    echo -e "${GREEN}✓ All services ready${NC}"
    echo
}

# Function to run tests
run_tests() {
    local test_type="${1:-all}"

    echo -e "${YELLOW}Running tests...${NC}"
    echo

    case "$test_type" in
        ldap)
            pytest tests/unit/auth/providers/test_ldap_provider.py tests/integration/auth/test_ldap_integration.py -v
            ;;
        oidc)
            pytest tests/unit/auth/providers/test_oidc_provider.py tests/integration/auth/test_oidc_integration.py -v
            ;;
        saml)
            pytest tests/unit/auth/providers/test_saml_provider.py tests/integration/auth/test_saml_integration.py -v
            ;;
        unit)
            pytest tests/unit/auth/providers/ -v -m "not integration"
            ;;
        integration)
            pytest tests/integration/auth/ -v -m integration
            ;;
        coverage)
            pytest tests/unit/auth/providers/ tests/integration/auth/ \
                --cov=src/sark/services/auth/providers \
                --cov-report=html \
                --cov-report=term-missing \
                -v
            ;;
        all|*)
            pytest tests/unit/auth/providers/ tests/integration/auth/ -v
            ;;
    esac

    test_result=$?
    echo

    if [ $test_result -eq 0 ]; then
        echo -e "${GREEN}✓ Tests passed${NC}"
    else
        echo -e "${RED}✗ Tests failed${NC}"
    fi

    return $test_result
}

# Main execution
main() {
    local command="${1:-run}"
    local test_type="${2:-all}"

    case "$command" in
        start)
            check_docker
            cleanup
            start_services
            wait_for_services
            echo -e "${GREEN}Services are ready for testing${NC}"
            ;;
        stop)
            cleanup
            ;;
        run)
            check_docker
            cleanup
            start_services
            wait_for_services
            run_tests "$test_type"
            test_result=$?
            cleanup
            exit $test_result
            ;;
        test)
            # Run tests without managing containers (assumes they're already running)
            run_tests "$test_type"
            ;;
        *)
            echo "Usage: $0 {start|stop|run|test} [test_type]"
            echo
            echo "Commands:"
            echo "  start       - Start Docker test services"
            echo "  stop        - Stop and remove Docker test services"
            echo "  run         - Full test run (start services, run tests, cleanup)"
            echo "  test        - Run tests only (services must be started separately)"
            echo
            echo "Test types (for 'run' and 'test'):"
            echo "  all         - Run all auth provider tests (default)"
            echo "  unit        - Run only unit tests"
            echo "  integration - Run only integration tests"
            echo "  ldap        - Run only LDAP tests"
            echo "  oidc        - Run only OIDC tests"
            echo "  saml        - Run only SAML tests"
            echo "  coverage    - Run all tests with coverage report"
            echo
            echo "Examples:"
            echo "  $0 run               # Full test run"
            echo "  $0 run ldap          # Test only LDAP provider"
            echo "  $0 run coverage      # Run with coverage report"
            echo "  $0 start             # Start services for manual testing"
            echo "  $0 stop              # Stop all test services"
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"
