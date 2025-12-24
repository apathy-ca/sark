#!/usr/bin/env bash
# Script to run integration tests with proper Docker infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SARK Integration Test Runner${NC}"
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
    docker-compose -f tests/fixtures/docker-compose.integration.yml down -v 2>/dev/null || true
    echo -e "${GREEN}✓ Cleanup complete${NC}"
    echo
}

# Function to start Docker services
start_services() {
    echo -e "${YELLOW}Starting integration test services...${NC}"
    echo "  - PostgreSQL (port 5433)"
    echo "  - TimescaleDB (port 5434)"
    echo "  - Redis (port 6380)"
    echo "  - OPA (port 8181)"
    echo "  - gRPC Mock (port 50051)"
    echo

    docker-compose -f tests/fixtures/docker-compose.integration.yml up -d

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to start services${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Services started${NC}"
    echo
}

# Function to wait for services
wait_for_services() {
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"

    # Wait for PostgreSQL
    echo -n "Waiting for PostgreSQL... "
    timeout=30
    while ! docker exec sark_test_postgres pg_isready -U sark_test > /dev/null 2>&1; do
        sleep 1
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            echo -e "${RED}TIMEOUT${NC}"
            docker logs sark_test_postgres | tail -20
            exit 1
        fi
    done
    echo -e "${GREEN}OK${NC}"

    # Wait for TimescaleDB
    echo -n "Waiting for TimescaleDB... "
    timeout=30
    while ! docker exec sark_test_timescale pg_isready -U sark_test > /dev/null 2>&1; do
        sleep 1
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            echo -e "${RED}TIMEOUT${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}OK${NC}"

    # Wait for Redis
    echo -n "Waiting for Redis... "
    timeout=30
    while ! docker exec sark_test_redis redis-cli ping > /dev/null 2>&1; do
        sleep 1
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            echo -e "${RED}TIMEOUT${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}OK${NC}"

    # Wait for OPA
    echo -n "Waiting for OPA... "
    timeout=30
    while ! curl -s http://localhost:8181/health > /dev/null; do
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

# Function to show service status
show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    docker-compose -f tests/fixtures/docker-compose.integration.yml ps
    echo
}

# Function to show service logs
show_logs() {
    local service="${1:-}"

    if [ -z "$service" ]; then
        echo -e "${BLUE}All Service Logs:${NC}"
        docker-compose -f tests/fixtures/docker-compose.integration.yml logs --tail=50
    else
        echo -e "${BLUE}Logs for ${service}:${NC}"
        docker-compose -f tests/fixtures/docker-compose.integration.yml logs --tail=100 "$service"
    fi
}

# Function to run tests
run_tests() {
    local test_type="${1:-all}"

    echo -e "${YELLOW}Running integration tests...${NC}"
    echo

    case "$test_type" in
        api)
            pytest tests/integration/test_api_integration.py -v
            ;;
        auth)
            pytest tests/integration/test_auth_integration.py tests/integration/auth/ -v
            ;;
        policy)
            pytest tests/integration/test_policy_integration.py tests/integration/gateway/test_policy_integration.py -v
            ;;
        gateway)
            pytest tests/integration/gateway/ -v
            ;;
        siem)
            pytest tests/integration/test_siem*.py tests/integration/test_splunk*.py tests/integration/test_datadog*.py -v -m "not integration"
            ;;
        database)
            pytest tests/integration/test_large_scale_operations.py -v
            ;;
        v2)
            pytest tests/integration/v2/ -v
            ;;
        fast)
            # Run only fast tests (exclude slow ones)
            pytest tests/integration/ -v -m "not slow"
            ;;
        coverage)
            pytest tests/integration/ \
                --cov=src/sark \
                --cov-report=html \
                --cov-report=term-missing \
                -v
            ;;
        all|*)
            pytest tests/integration/ -v
            ;;
    esac

    test_result=$?
    echo

    if [ $test_result -eq 0 ]; then
        echo -e "${GREEN}✓ Tests passed${NC}"
    else
        echo -e "${RED}✗ Tests failed (exit code: $test_result)${NC}"
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
            show_status
            echo -e "${GREEN}Services are ready for testing${NC}"
            echo
            echo "Run tests with: $0 test [type]"
            echo "Stop services with: $0 stop"
            ;;
        stop)
            cleanup
            ;;
        restart)
            cleanup
            check_docker
            start_services
            wait_for_services
            show_status
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${test_type}"
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
        shell)
            # Open shell in service container
            service="${test_type:-postgres}"
            echo "Opening shell in ${service}..."
            case "$service" in
                postgres)
                    docker exec -it sark_test_postgres psql -U sark_test -d sark_test
                    ;;
                timescale)
                    docker exec -it sark_test_timescale psql -U sark_test -d sark_audit_test
                    ;;
                redis)
                    docker exec -it sark_test_redis redis-cli
                    ;;
                *)
                    docker exec -it "sark_test_${service}" sh
                    ;;
            esac
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|run|test|status|logs|shell} [options]"
            echo
            echo "Commands:"
            echo "  start       - Start Docker test services"
            echo "  stop        - Stop and remove Docker test services"
            echo "  restart     - Restart all services"
            echo "  run         - Full test run (start services, run tests, cleanup)"
            echo "  test        - Run tests only (services must be started separately)"
            echo "  status      - Show service status"
            echo "  logs        - Show service logs (logs [service])"
            echo "  shell       - Open shell in service (shell [postgres|redis|timescale])"
            echo
            echo "Test types (for 'run' and 'test'):"
            echo "  all         - Run all integration tests (default)"
            echo "  api         - API integration tests"
            echo "  auth        - Authentication integration tests"
            echo "  policy      - Policy engine integration tests"
            echo "  gateway     - Gateway integration tests"
            echo "  siem        - SIEM integration tests (mocked)"
            echo "  database    - Database integration tests"
            echo "  v2          - Version 2 adapter tests"
            echo "  fast        - Fast tests only (exclude slow)"
            echo "  coverage    - Run all tests with coverage report"
            echo
            echo "Examples:"
            echo "  $0 run               # Full test run"
            echo "  $0 run fast          # Fast tests only"
            echo "  $0 run coverage      # With coverage report"
            echo "  $0 start             # Start services for manual testing"
            echo "  $0 test api          # Run API tests (services running)"
            echo "  $0 logs postgres     # Show PostgreSQL logs"
            echo "  $0 shell postgres    # Open PostgreSQL shell"
            echo "  $0 stop              # Stop all services"
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"
