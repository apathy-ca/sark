#!/bin/bash
#
# API Client Generation Script
#
# This script generates API clients from the OpenAPI specification
# Supports multiple languages: TypeScript, Python, Go, Java
#
# Usage:
#   ./generate-client.sh <language> [output-dir]
#
# Examples:
#   ./generate-client.sh typescript ./generated/typescript-client
#   ./generate-client.sh python ./generated/python-client
#   ./generate-client.sh go ./generated/go-client
#

set -e

# Configuration
OPENAPI_SPEC_URL="${OPENAPI_SPEC_URL:-http://localhost:8000/openapi.json}"
OPENAPI_SPEC_FILE="./openapi.json"

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

# Check if language is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <language> [output-dir]"
    echo ""
    echo "Supported languages:"
    echo "  typescript       - TypeScript Fetch client"
    echo "  typescript-axios - TypeScript Axios client"
    echo "  python           - Python client"
    echo "  go               - Go client"
    echo "  java             - Java client"
    echo ""
    exit 1
fi

LANGUAGE=$1
OUTPUT_DIR=${2:-"./generated/${LANGUAGE}-client"}

print_header "SARK API Client Generation"

# Check dependencies
check_npm() {
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed (required for client generation)"
        print_info "Install Node.js from https://nodejs.org/"
        exit 1
    fi
    print_success "npm is installed"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "docker is not installed (alternative method)"
        print_info "Install Docker from https://www.docker.com/"
        return 1
    fi
    print_success "docker is installed"
}

# Download OpenAPI spec
download_spec() {
    print_info "Downloading OpenAPI spec from ${OPENAPI_SPEC_URL}..."

    if curl -sf "${OPENAPI_SPEC_URL}" -o "${OPENAPI_SPEC_FILE}"; then
        print_success "OpenAPI spec downloaded successfully"

        # Validate JSON
        if command -v jq &> /dev/null; then
            if jq empty "${OPENAPI_SPEC_FILE}" 2>/dev/null; then
                print_success "OpenAPI spec is valid JSON"
            else
                print_error "OpenAPI spec is not valid JSON"
                exit 1
            fi
        fi
    else
        print_error "Failed to download OpenAPI spec"
        print_info "Make sure SARK API is running: docker-compose up -d"
        exit 1
    fi
}

# Generate client using npm (openapi-generator-cli)
generate_with_npm() {
    print_info "Generating ${LANGUAGE} client using npm..."

    # Install openapi-generator-cli if not present
    if ! npm list -g @openapitools/openapi-generator-cli &> /dev/null; then
        print_info "Installing @openapitools/openapi-generator-cli..."
        npm install -g @openapitools/openapi-generator-cli
    fi

    # Map language to generator
    case ${LANGUAGE} in
        typescript)
            GENERATOR="typescript-fetch"
            ;;
        typescript-axios)
            GENERATOR="typescript-axios"
            ;;
        python)
            GENERATOR="python"
            ;;
        go)
            GENERATOR="go"
            ;;
        java)
            GENERATOR="java"
            ;;
        *)
            print_error "Unsupported language: ${LANGUAGE}"
            exit 1
            ;;
    esac

    # Generate client
    npx @openapitools/openapi-generator-cli generate \
        -i "${OPENAPI_SPEC_FILE}" \
        -g "${GENERATOR}" \
        -o "${OUTPUT_DIR}" \
        --additional-properties=npmName=sark-client,npmVersion=1.0.0

    if [ $? -eq 0 ]; then
        print_success "Client generated successfully at ${OUTPUT_DIR}"
    else
        print_error "Client generation failed"
        exit 1
    fi
}

# Generate client using Docker
generate_with_docker() {
    print_info "Generating ${LANGUAGE} client using Docker..."

    # Map language to generator
    case ${LANGUAGE} in
        typescript)
            GENERATOR="typescript-fetch"
            ;;
        typescript-axios)
            GENERATOR="typescript-axios"
            ;;
        python)
            GENERATOR="python"
            ;;
        go)
            GENERATOR="go"
            ;;
        java)
            GENERATOR="java"
            ;;
        *)
            print_error "Unsupported language: ${LANGUAGE}"
            exit 1
            ;;
    esac

    # Create output directory
    mkdir -p "${OUTPUT_DIR}"

    # Generate using Docker
    docker run --rm \
        -v "${PWD}/${OPENAPI_SPEC_FILE}:/spec/openapi.json" \
        -v "${PWD}/${OUTPUT_DIR}:/out" \
        openapitools/openapi-generator-cli generate \
        -i /spec/openapi.json \
        -g "${GENERATOR}" \
        -o /out \
        --additional-properties=npmName=sark-client,npmVersion=1.0.0

    if [ $? -eq 0 ]; then
        print_success "Client generated successfully at ${OUTPUT_DIR}"
    else
        print_error "Client generation failed"
        exit 1
    fi
}

# Main execution
main() {
    # Check dependencies
    check_npm
    HAS_DOCKER=0
    check_docker && HAS_DOCKER=1 || true

    # Download spec
    download_spec

    # Generate client
    if [ "${HAS_DOCKER}" -eq 1 ] && [ "${USE_DOCKER:-0}" -eq 1 ]; then
        generate_with_docker
    else
        generate_with_npm
    fi

    # Post-generation instructions
    print_header "Next Steps"

    case ${LANGUAGE} in
        typescript|typescript-axios)
            echo "1. Install dependencies:"
            echo "   cd ${OUTPUT_DIR}"
            echo "   npm install"
            echo ""
            echo "2. Build the client:"
            echo "   npm run build"
            echo ""
            echo "3. Use in your project:"
            echo "   import { Configuration, DefaultApi } from './generated/typescript-client';"
            echo ""
            echo "   const config = new Configuration({"
            echo "     basePath: 'http://localhost:8000',"
            echo "     apiKey: 'sark_dev_your_api_key'"
            echo "   });"
            echo ""
            echo "   const api = new DefaultApi(config);"
            echo "   const servers = await api.listServers();"
            ;;
        python)
            echo "1. Install the generated client:"
            echo "   cd ${OUTPUT_DIR}"
            echo "   pip install ."
            echo ""
            echo "2. Use in your code:"
            echo "   import sark_client"
            echo "   from sark_client.api import servers_api"
            echo ""
            echo "   configuration = sark_client.Configuration("
            echo "       host = 'http://localhost:8000'"
            echo "   )"
            echo "   configuration.api_key['X-API-Key'] = 'sark_dev_your_key'"
            echo ""
            echo "   with sark_client.ApiClient(configuration) as api_client:"
            echo "       api_instance = servers_api.ServersApi(api_client)"
            echo "       servers = api_instance.list_servers()"
            ;;
        go)
            echo "1. Install dependencies:"
            echo "   cd ${OUTPUT_DIR}"
            echo "   go mod init sark-client"
            echo "   go mod tidy"
            echo ""
            echo "2. Use in your code:"
            echo "   import sark \"./generated/go-client\""
            echo ""
            echo "   config := sark.NewConfiguration()"
            echo "   config.Servers = []sark.ServerConfiguration{"
            echo "       {URL: \"http://localhost:8000\"}"
            echo "   }"
            echo "   client := sark.NewAPIClient(config)"
            echo "   servers, _, err := client.ServersApi.ListServers(context.Background()).Execute()"
            ;;
    esac

    print_success "Client generation complete!"
}

# Run main
main
