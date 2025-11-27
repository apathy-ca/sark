#!/bin/bash
#
# SARK Authentication Tutorial - Bash Script
#
# This script demonstrates authentication methods with SARK using bash/curl.
#
# Usage:
#   ./auth_tutorial.sh api-key
#   ./auth_tutorial.sh ldap
#   ./auth_tutorial.sh all
#

set -e  # Exit on error

# Configuration
SARK_API_URL="${SARK_API_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-dev-admin-token-change-in-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}\n"
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

# Check dependencies
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed (required for JSON parsing)"
        exit 1
    fi

    print_success "Dependencies check passed"
}

# Test API connectivity
test_connectivity() {
    print_header "Testing API Connectivity"

    if curl -s -f "${SARK_API_URL}/health" > /dev/null; then
        print_success "SARK API is reachable at ${SARK_API_URL}"

        # Get version info
        VERSION=$(curl -s "${SARK_API_URL}/health" | jq -r '.version')
        ENVIRONMENT=$(curl -s "${SARK_API_URL}/health" | jq -r '.environment')
        print_info "Version: ${VERSION}, Environment: ${ENVIRONMENT}"
    else
        print_error "Cannot reach SARK API at ${SARK_API_URL}"
        print_info "Make sure SARK is running: docker-compose up -d"
        exit 1
    fi
}

# API Key Authentication Tutorial
tutorial_api_key() {
    print_header "Part 1: API Key Authentication"

    # Step 1: Create API Key
    print_info "Step 1: Creating API key..."

    API_KEY_RESPONSE=$(curl -s -X POST "${SARK_API_URL}/api/auth/api-keys" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Tutorial API Key",
            "description": "Created by auth_tutorial.sh",
            "scopes": ["server:read", "server:write"],
            "expires_in_days": 30,
            "environment": "development"
        }')

    if [ $? -eq 0 ]; then
        API_KEY=$(echo "$API_KEY_RESPONSE" | jq -r '.key')
        API_KEY_ID=$(echo "$API_KEY_RESPONSE" | jq -r '.api_key.id')
        KEY_PREFIX=$(echo "$API_KEY_RESPONSE" | jq -r '.api_key.key_prefix')

        print_success "API key created successfully"
        echo "   Name: Tutorial API Key"
        echo "   Prefix: ${KEY_PREFIX}"
        echo "   ID: ${API_KEY_ID}"
        echo ""
        echo -e "${YELLOW}⚠️  SAVE THIS KEY (shown only once):${NC}"
        echo "   ${API_KEY}"
        echo ""
    else
        print_error "Failed to create API key"
        echo "$API_KEY_RESPONSE" | jq .
        return 1
    fi

    # Step 2: Use API Key
    print_info "Step 2: Testing API key by listing servers..."

    SERVER_LIST=$(curl -s -X GET "${SARK_API_URL}/api/v1/servers" \
        -H "X-API-Key: ${API_KEY}")

    if [ $? -eq 0 ]; then
        SERVER_COUNT=$(echo "$SERVER_LIST" | jq '.items | length')
        print_success "API key works! Found ${SERVER_COUNT} servers"
    else
        print_error "API key test failed"
        return 1
    fi

    # Step 3: Test Scopes
    print_info "Step 3: Testing API key scopes..."

    # This should work (server:read)
    curl -s -X GET "${SARK_API_URL}/api/v1/servers" \
        -H "X-API-Key: ${API_KEY}" > /dev/null

    if [ $? -eq 0 ]; then
        print_success "Scope check passed: server:read ✓"
    else
        print_error "Scope check failed: server:read"
    fi

    # Step 4: List API Keys
    print_info "Step 4: Listing all API keys..."

    ALL_KEYS=$(curl -s -X GET "${SARK_API_URL}/api/auth/api-keys" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}")

    KEY_COUNT=$(echo "$ALL_KEYS" | jq '. | length')
    print_success "Found ${KEY_COUNT} API keys"

    # Step 5: Revoke API Key
    print_info "Step 5: Revoking API key..."

    curl -s -X DELETE "${SARK_API_URL}/api/auth/api-keys/${API_KEY_ID}" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" > /dev/null

    if [ $? -eq 0 ]; then
        print_success "API key revoked successfully"

        # Try using revoked key (should fail)
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -X GET "${SARK_API_URL}/api/v1/servers" \
            -H "X-API-Key: ${API_KEY}")

        if [ "$HTTP_CODE" = "401" ]; then
            print_success "Revoked key rejected (expected) ✓"
        else
            print_error "Revoked key still works (unexpected)"
        fi
    else
        print_error "Failed to revoke API key"
    fi
}

# LDAP Authentication Tutorial
tutorial_ldap() {
    print_header "Part 2: LDAP Authentication"

    # Step 1: Login
    print_info "Step 1: Authenticating with LDAP..."

    LOGIN_RESPONSE=$(curl -s -X POST "${SARK_API_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "provider": "ldap",
            "username": "john.doe",
            "password": "secret123"
        }')

    if echo "$LOGIN_RESPONSE" | jq -e '.success' > /dev/null; then
        ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.session.access_token')
        REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.session.refresh_token')
        EXPIRES_IN=$(echo "$LOGIN_RESPONSE" | jq -r '.session.expires_in')
        USER_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user_id')

        print_success "LDAP login successful"
        echo "   User ID: ${USER_ID}"
        echo "   Token expires in: ${EXPIRES_IN} seconds"
    else
        print_error "LDAP login failed"
        echo "$LOGIN_RESPONSE" | jq .
        return 1
    fi

    # Step 2: Get Current User
    print_info "Step 2: Getting current user info..."

    USER_INFO=$(curl -s -X GET "${SARK_API_URL}/api/v1/auth/me" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}")

    if [ $? -eq 0 ]; then
        USERNAME=$(echo "$USER_INFO" | jq -r '.username')
        EMAIL=$(echo "$USER_INFO" | jq -r '.email')
        ROLE=$(echo "$USER_INFO" | jq -r '.role')

        print_success "Current user retrieved"
        echo "   Username: ${USERNAME}"
        echo "   Email: ${EMAIL}"
        echo "   Role: ${ROLE}"
    else
        print_error "Failed to get user info"
    fi

    # Step 3: Refresh Token
    print_info "Step 3: Refreshing access token..."

    REFRESH_RESPONSE=$(curl -s -X POST "${SARK_API_URL}/api/v1/auth/refresh" \
        -H "Content-Type: application/json" \
        -d "{
            \"refresh_token\": \"${REFRESH_TOKEN}\"
        }")

    if [ $? -eq 0 ]; then
        NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.access_token')
        NEW_EXPIRES_IN=$(echo "$REFRESH_RESPONSE" | jq -r '.expires_in')

        print_success "Token refreshed successfully"
        echo "   New token expires in: ${NEW_EXPIRES_IN} seconds"

        # Update tokens
        ACCESS_TOKEN="$NEW_ACCESS_TOKEN"

        # Check if refresh token was rotated
        if echo "$REFRESH_RESPONSE" | jq -e '.refresh_token' > /dev/null; then
            REFRESH_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.refresh_token')
            print_info "Refresh token rotated (new token received)"
        fi
    else
        print_error "Token refresh failed"
    fi

    # Step 4: Use Access Token
    print_info "Step 4: Using access token to list servers..."

    SERVER_LIST=$(curl -s -X GET "${SARK_API_URL}/api/v1/servers" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}")

    if [ $? -eq 0 ]; then
        SERVER_COUNT=$(echo "$SERVER_LIST" | jq '.items | length')
        print_success "Access token works! Found ${SERVER_COUNT} servers"
    else
        print_error "Access token test failed"
    fi

    # Step 5: Logout
    print_info "Step 5: Logging out (revoking refresh token)..."

    LOGOUT_RESPONSE=$(curl -s -X POST "${SARK_API_URL}/api/v1/auth/revoke" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"refresh_token\": \"${REFRESH_TOKEN}\"
        }")

    if echo "$LOGOUT_RESPONSE" | jq -e '.success' > /dev/null; then
        print_success "Logout successful"

        # Try using revoked refresh token (should fail)
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST "${SARK_API_URL}/api/v1/auth/refresh" \
            -H "Content-Type: application/json" \
            -d "{\"refresh_token\": \"${REFRESH_TOKEN}\"}")

        if [ "$HTTP_CODE" = "401" ]; then
            print_success "Revoked refresh token rejected (expected) ✓"
        else
            print_error "Revoked token still works (unexpected)"
        fi
    else
        print_error "Logout failed"
    fi
}

# OIDC Authentication Tutorial (Info only)
tutorial_oidc() {
    print_header "Part 3: OIDC Authentication"

    print_info "OIDC requires a web browser flow. Here's how to set it up:"
    echo ""
    echo "1. Configure OIDC in your .env file:"
    echo "   OIDC_ENABLED=true"
    echo "   OIDC_PROVIDER_URL=https://accounts.google.com"
    echo "   OIDC_CLIENT_ID=your-client-id"
    echo "   OIDC_CLIENT_SECRET=your-client-secret"
    echo ""
    echo "2. Open in browser:"
    echo "   ${SARK_API_URL}/api/v1/auth/oidc/login"
    echo ""
    echo "3. After login, you'll be redirected with tokens"
    echo ""
    print_info "See Tutorial 02 documentation for complete OIDC setup"
}

# Main script
main() {
    print_header "SARK Authentication Tutorial"

    # Check dependencies
    check_dependencies

    # Test connectivity
    test_connectivity

    # Run tutorial based on argument
    case "${1:-all}" in
        api-key)
            tutorial_api_key
            ;;
        ldap)
            tutorial_ldap
            ;;
        oidc)
            tutorial_oidc
            ;;
        all)
            tutorial_api_key
            tutorial_ldap
            tutorial_oidc
            ;;
        *)
            echo "Usage: $0 {api-key|ldap|oidc|all}"
            echo ""
            echo "Examples:"
            echo "  $0 api-key    # API Key authentication only"
            echo "  $0 ldap       # LDAP authentication only"
            echo "  $0 oidc       # OIDC info only"
            echo "  $0 all        # Run all tutorials (default)"
            exit 1
            ;;
    esac

    print_header "Tutorial Complete!"
    print_success "All authentication methods demonstrated"
    echo ""
    print_info "Next steps:"
    echo "  - Read docs/tutorials/02-authentication.md"
    echo "  - Try tutorial 03: Working with Policies"
    echo "  - Explore the API: ${SARK_API_URL}/docs"
}

# Run main function
main "$@"
