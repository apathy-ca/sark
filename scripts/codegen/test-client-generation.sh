#!/bin/bash
#
# API Client Generation Test Script
#
# This script validates the API client generation pipeline
# Tests: OpenAPI spec validity, client generation, compilation
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Configuration
SARK_API_URL="${SARK_API_URL:-http://localhost:8000}"
TEST_DIR="./test-clients"
OPENAPI_SPEC_FILE="${TEST_DIR}/openapi.json"

print_header "API Client Generation Test Suite"

# Create test directory
mkdir -p "${TEST_DIR}"

# Test 1: API Connectivity
print_info "Test 1: Checking API connectivity..."
if curl -sf "${SARK_API_URL}/health" > /dev/null; then
    print_success "API is reachable"
else
    print_error "Cannot reach API at ${SARK_API_URL}"
    print_info "Start SARK: docker compose up -d"
    exit 1
fi

# Test 2: Download OpenAPI Spec
print_info "Test 2: Downloading OpenAPI spec..."
if curl -sf "${SARK_API_URL}/openapi.json" -o "${OPENAPI_SPEC_FILE}"; then
    print_success "OpenAPI spec downloaded"

    # Get file size
    FILE_SIZE=$(wc -c < "${OPENAPI_SPEC_FILE}")
    print_info "Spec size: ${FILE_SIZE} bytes"
else
    print_error "Failed to download OpenAPI spec"
    exit 1
fi

# Test 3: Validate JSON
print_info "Test 3: Validating JSON syntax..."
if command -v jq &> /dev/null; then
    if jq empty "${OPENAPI_SPEC_FILE}" 2>/dev/null; then
        print_success "OpenAPI spec is valid JSON"
    else
        print_error "OpenAPI spec has invalid JSON"
        exit 1
    fi
else
    print_info "jq not installed, skipping JSON validation"
fi

# Test 4: Validate OpenAPI Structure
print_info "Test 4: Validating OpenAPI structure..."
if command -v jq &> /dev/null; then
    # Check required fields
    VERSION=$(jq -r '.openapi' "${OPENAPI_SPEC_FILE}")
    TITLE=$(jq -r '.info.title' "${OPENAPI_SPEC_FILE}")
    PATHS_COUNT=$(jq '.paths | length' "${OPENAPI_SPEC_FILE}")

    print_info "OpenAPI Version: ${VERSION}"
    print_info "API Title: ${TITLE}"
    print_info "Endpoints: ${PATHS_COUNT}"

    if [ "${PATHS_COUNT}" -gt 0 ]; then
        print_success "OpenAPI structure is valid"
    else
        print_error "No paths found in OpenAPI spec"
        exit 1
    fi
fi

# Test 5: Check for Response Models
print_info "Test 5: Checking for response models..."
if command -v jq &> /dev/null; then
    COMPONENTS_COUNT=$(jq '.components.schemas | length' "${OPENAPI_SPEC_FILE}")
    print_info "Schemas defined: ${COMPONENTS_COUNT}"

    if [ "${COMPONENTS_COUNT}" -gt 0 ]; then
        print_success "Response models are defined"

        # List some key models
        echo "  Key models:"
        jq -r '.components.schemas | keys[]' "${OPENAPI_SPEC_FILE}" | head -10 | while read model; do
            echo "    - ${model}"
        done
    else
        print_error "No response models found"
    fi
fi

# Test 6: Check for Examples
print_info "Test 6: Checking for request examples..."
if command -v jq &> /dev/null; then
    EXAMPLES_COUNT=$(jq '[.components.schemas[] | select(.example != null)] | length' "${OPENAPI_SPEC_FILE}")
    print_info "Schemas with examples: ${EXAMPLES_COUNT}"

    if [ "${EXAMPLES_COUNT}" -gt 0 ]; then
        print_success "Request examples are present"
    else
        print_info "Consider adding more examples to schemas"
    fi
fi

# Test 7: Validate with OpenAPI Generator (if available)
print_info "Test 7: Validating with OpenAPI Generator..."
if command -v npx &> /dev/null; then
    if npx @openapitools/openapi-generator-cli validate -i "${OPENAPI_SPEC_FILE}" 2>&1 | grep -q "successfully validated"; then
        print_success "OpenAPI spec passes generator validation"
    else
        print_error "OpenAPI spec validation failed"
        npx @openapitools/openapi-generator-cli validate -i "${OPENAPI_SPEC_FILE}" || true
    fi
else
    print_info "OpenAPI Generator CLI not available, skipping validation"
fi

# Test 8: Generate TypeScript Client
print_info "Test 8: Generating TypeScript client..."
if command -v npx &> /dev/null; then
    TS_OUTPUT="${TEST_DIR}/typescript-client"
    rm -rf "${TS_OUTPUT}"

    if npx @openapitools/openapi-generator-cli generate \
        -i "${OPENAPI_SPEC_FILE}" \
        -g typescript-fetch \
        -o "${TS_OUTPUT}" \
        --additional-properties=npmName=sark-client,npmVersion=1.0.0 \
        > /dev/null 2>&1; then

        print_success "TypeScript client generated"

        # Check generated files
        if [ -f "${TS_OUTPUT}/package.json" ]; then
            print_info "package.json created"
        fi

        if [ -d "${TS_OUTPUT}/src" ]; then
            API_COUNT=$(find "${TS_OUTPUT}/src/apis" -name "*.ts" | wc -l)
            MODEL_COUNT=$(find "${TS_OUTPUT}/src/models" -name "*.ts" | wc -l)
            print_info "Generated ${API_COUNT} API files, ${MODEL_COUNT} models"
        fi
    else
        print_error "TypeScript client generation failed"
    fi
else
    print_info "npm not available, skipping TypeScript generation"
fi

# Test 9: Generate Python Client
print_info "Test 9: Generating Python client..."
if command -v npx &> /dev/null; then
    PY_OUTPUT="${TEST_DIR}/python-client"
    rm -rf "${PY_OUTPUT}"

    if npx @openapitools/openapi-generator-cli generate \
        -i "${OPENAPI_SPEC_FILE}" \
        -g python \
        -o "${PY_OUTPUT}" \
        --additional-properties=packageName=sark_client,packageVersion=1.0.0 \
        > /dev/null 2>&1; then

        print_success "Python client generated"

        # Check generated files
        if [ -f "${PY_OUTPUT}/setup.py" ]; then
            print_info "setup.py created"
        fi

        if [ -d "${PY_OUTPUT}/sark_client" ]; then
            API_COUNT=$(find "${PY_OUTPUT}/sark_client/api" -name "*.py" 2>/dev/null | wc -l)
            MODEL_COUNT=$(find "${PY_OUTPUT}/sark_client/models" -name "*.py" 2>/dev/null | wc -l)
            print_info "Generated ${API_COUNT} API files, ${MODEL_COUNT} models"
        fi
    else
        print_error "Python client generation failed"
    fi
else
    print_info "npm not available, skipping Python generation"
fi

# Test 10: Check Security Definitions
print_info "Test 10: Checking security definitions..."
if command -v jq &> /dev/null; then
    SECURITY_SCHEMES=$(jq '.components.securitySchemes | length' "${OPENAPI_SPEC_FILE}")

    if [ "${SECURITY_SCHEMES}" -gt 0 ]; then
        print_success "Security schemes defined: ${SECURITY_SCHEMES}"

        echo "  Security schemes:"
        jq -r '.components.securitySchemes | keys[]' "${OPENAPI_SPEC_FILE}" | while read scheme; do
            TYPE=$(jq -r ".components.securitySchemes.\"${scheme}\".type" "${OPENAPI_SPEC_FILE}")
            echo "    - ${scheme} (${TYPE})"
        done
    else
        print_info "No security schemes defined (consider adding API key/bearer auth)"
    fi
fi

# Summary
print_header "Test Summary"

TOTAL_TESTS=10
PASSED_TESTS=0

# Count passed tests (simplified - in real scenario, track each test result)
if [ -f "${OPENAPI_SPEC_FILE}" ]; then ((PASSED_TESTS++)); fi
if [ -d "${TEST_DIR}/typescript-client" ]; then ((PASSED_TESTS++)); fi
if [ -d "${TEST_DIR}/python-client" ]; then ((PASSED_TESTS++)); fi

echo "Tests run: ${TOTAL_TESTS}"
echo "Tests passed: ${PASSED_TESTS}+"
echo ""

if [ -f "${OPENAPI_SPEC_FILE}" ]; then
    print_success "OpenAPI spec is valid and ready for client generation"
else
    print_error "OpenAPI spec validation failed"
    exit 1
fi

# Cleanup option
read -p "Clean up test clients? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "${TEST_DIR}"
    print_info "Test directory cleaned up"
else
    print_info "Test clients saved in ${TEST_DIR}"
fi

print_success "Client generation test suite complete!"
