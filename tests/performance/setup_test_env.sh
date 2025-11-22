#!/bin/bash
# Performance Test Environment Setup Script
#
# This script sets up the environment for running performance tests,
# including creating test API keys and verifying service availability.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
API_KEY_FILE=".test_api_key"

echo "========================================="
echo "SARK Performance Test Environment Setup"
echo "========================================="
echo ""

# Function to check if service is running
check_service() {
    local service_name=$1
    local service_url=$2

    echo -n "Checking ${service_name}... "

    if curl -s --fail "${service_url}" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local service_url=$2
    local max_attempts=30
    local attempt=1

    echo "Waiting for ${service_name} to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s --fail "${service_url}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ${service_name} is ready${NC}"
            return 0
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}✗ ${service_name} failed to start${NC}"
    return 1
}

# Check all required services
echo "1. Checking required services..."
echo "--------------------------------"

all_services_running=true

if ! check_service "SARK API" "${BASE_URL}/health/"; then
    all_services_running=false
fi

if ! check_service "PostgreSQL" "${BASE_URL}/health/ready"; then
    all_services_running=false
fi

if ! check_service "Redis" "${BASE_URL}/health/ready"; then
    all_services_running=false
fi

echo ""

if [ "$all_services_running" = false ]; then
    echo -e "${RED}✗ Some services are not running${NC}"
    echo ""
    echo "Please start all required services:"
    echo "  1. Start SARK API: uvicorn sark.api.main:app --host 0.0.0.0 --port 8000"
    echo "  2. Ensure PostgreSQL is running"
    echo "  3. Ensure Redis is running"
    echo ""
    exit 1
fi

# Create test API key (if admin token provided)
echo "2. Setting up test API key..."
echo "--------------------------------"

if [ -n "$ADMIN_TOKEN" ]; then
    echo "Creating test API key..."

    # Create API key via API
    response=$(curl -s -X POST "${BASE_URL}/api/auth/api-keys" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "performance-test-key",
            "description": "API key for performance testing",
            "scopes": [
                "server:read",
                "server:write",
                "server:delete",
                "tool:invoke",
                "policy:evaluate"
            ],
            "rate_limit": 10000,
            "expires_in_days": 7,
            "environment": "test"
        }')

    # Extract API key from response
    api_key=$(echo $response | python3 -c "import sys, json; print(json.load(sys.stdin)['key'])" 2>/dev/null || echo "")

    if [ -n "$api_key" ]; then
        echo "$api_key" > "$API_KEY_FILE"
        echo -e "${GREEN}✓ API key created and saved to ${API_KEY_FILE}${NC}"
        echo ""
        echo "Export the API key for use in tests:"
        echo "  export TEST_API_KEY='${api_key}'"
    else
        echo -e "${YELLOW}⚠ Could not create API key. Using default test key.${NC}"
        echo "sk_test_1234567890abcdefghijklmnop" > "$API_KEY_FILE"
    fi
else
    echo -e "${YELLOW}⚠ No admin token provided. Using default test API key.${NC}"
    echo ""
    echo "To create a real API key, provide ADMIN_TOKEN:"
    echo "  export ADMIN_TOKEN='your_jwt_token'"
    echo "  ./setup_test_env.sh"
    echo ""
    echo "Using default test key for now..."
    echo "sk_test_1234567890abcdefghijklmnop" > "$API_KEY_FILE"
fi

echo ""

# Create reports directory
echo "3. Creating reports directory..."
echo "--------------------------------"
mkdir -p reports
echo -e "${GREEN}✓ Reports directory created${NC}"
echo ""

# Verify Locust installation
echo "4. Verifying Locust installation..."
echo "--------------------------------"
if command -v locust &> /dev/null; then
    locust_version=$(locust --version 2>&1 | head -n 1)
    echo -e "${GREEN}✓ Locust installed: ${locust_version}${NC}"
else
    echo -e "${RED}✗ Locust not installed${NC}"
    echo "Install with: pip install locust"
    all_services_running=false
fi
echo ""

# Verify k6 installation (optional)
echo "5. Verifying k6 installation (optional)..."
echo "--------------------------------"
if command -v k6 &> /dev/null; then
    k6_version=$(k6 version 2>&1 | head -n 1)
    echo -e "${GREEN}✓ k6 installed: ${k6_version}${NC}"
else
    echo -e "${YELLOW}⚠ k6 not installed (optional)${NC}"
    echo "Install k6 for additional testing capabilities:"
    echo "  macOS: brew install k6"
    echo "  Linux: See https://k6.io/docs/getting-started/installation/"
fi
echo ""

# Performance test checklist
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Export API key:"
if [ -f "$API_KEY_FILE" ]; then
    api_key=$(cat "$API_KEY_FILE")
    echo "   export TEST_API_KEY='${api_key}'"
else
    echo "   export TEST_API_KEY='sk_test_1234567890abcdefghijklmnop'"
fi
echo ""
echo "2. Run smoke test:"
echo "   cd tests/performance"
echo "   locust -f locustfile.py --host=${BASE_URL} --users 1 --spawn-rate 1 --run-time 30s --headless"
echo ""
echo "3. Run full load test:"
echo "   locust -f locustfile.py --host=${BASE_URL} --users 100 --spawn-rate 10 --run-time 5m --headless --html=reports/load_test.html"
echo ""
echo "4. Or use web UI:"
echo "   locust -f locustfile.py --host=${BASE_URL}"
echo "   Open http://localhost:8089"
echo ""
echo "========================================="

exit 0
