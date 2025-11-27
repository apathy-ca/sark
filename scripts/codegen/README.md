# API Client Generation

This directory contains scripts for generating API clients from the SARK OpenAPI specification.

## Overview

SARK auto-generates API clients for multiple programming languages from the OpenAPI spec, ensuring type-safe and well-documented client libraries.

## Supported Languages

- **TypeScript** (Fetch API) - Recommended for web applications
- **TypeScript** (Axios) - For Node.js applications
- **Python** - For Python integrations and scripts
- **Go** - For Go microservices
- **Java** - For Java/Spring applications

## Quick Start

### Generate a TypeScript Client

```bash
./generate-client.sh typescript ./clients/typescript
```

### Generate a Python Client

```bash
./generate-client.sh python ./clients/python
```

### Using Makefile

```bash
# Generate all clients
make generate-clients

# Generate specific client
make typescript-client
make python-client
make go-client
```

## Prerequisites

### Method 1: Using npm (Recommended)

```bash
# Install Node.js (includes npm)
# Visit https://nodejs.org/

# Install the OpenAPI Generator CLI globally
npm install -g @openapitools/openapi-generator-cli
```

### Method 2: Using Docker

```bash
# Docker must be installed
# Visit https://www.docker.com/

# Set environment variable to use Docker
export USE_DOCKER=1
./generate-client.sh typescript
```

## Configuration

### Environment Variables

```bash
# OpenAPI spec URL (default: http://localhost:8000/openapi.json)
export OPENAPI_SPEC_URL="https://api.sark.example.com/openapi.json"

# Use Docker for generation (default: 0)
export USE_DOCKER=1
```

## Usage Examples

### TypeScript (Fetch)

```bash
# Generate client
./generate-client.sh typescript ./clients/typescript

# Install dependencies
cd ./clients/typescript
npm install

# Build
npm run build

# Use in your project
import { Configuration, DefaultApi } from './clients/typescript';

const config = new Configuration({
  basePath: 'http://localhost:8000',
  apiKey: 'sark_dev_your_api_key',
  headers: {
    'X-API-Key': 'sark_dev_your_api_key'
  }
});

const api = new DefaultApi(config);

// List servers
const servers = await api.listServers();
console.log(servers);

// Register server
const newServer = await api.registerServer({
  serverRegistrationRequest: {
    name: 'my-server',
    transport: 'http',
    endpoint: 'https://my-server.com/mcp',
    tools: []
  }
});
```

### Python

```bash
# Generate client
./generate-client.sh python ./clients/python

# Install client
cd ./clients/python
pip install .

# Use in your code
import sark_client
from sark_client.api import servers_api
from sark_client.models import ServerRegistrationRequest

# Configure API client
configuration = sark_client.Configuration(
    host="http://localhost:8000"
)
configuration.api_key['X-API-Key'] = 'sark_dev_your_key'

# Create API client
with sark_client.ApiClient(configuration) as api_client:
    # Create servers API instance
    servers = servers_api.ServersApi(api_client)

    # List servers
    server_list = servers.list_servers()
    print(f"Found {len(server_list.items)} servers")

    # Register new server
    new_server = ServerRegistrationRequest(
        name="analytics-server",
        transport="http",
        endpoint="https://analytics.example.com/mcp",
        tools=[]
    )
    result = servers.register_server(new_server)
    print(f"Registered server: {result.server_id}")
```

### Go

```bash
# Generate client
./generate-client.sh go ./clients/go

# Initialize Go module
cd ./clients/go
go mod init github.com/yourorg/sark-client
go mod tidy

# Use in your code
package main

import (
    "context"
    "fmt"
    sark "github.com/yourorg/sark-client"
)

func main() {
    // Configure API client
    config := sark.NewConfiguration()
    config.Servers = sark.ServerConfigurations{
        {
            URL: "http://localhost:8000",
        },
    }
    config.DefaultHeader["X-API-Key"] = "sark_dev_your_key"

    // Create client
    client := sark.NewAPIClient(config)

    // List servers
    servers, resp, err := client.ServersApi.ListServers(context.Background()).Execute()
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    fmt.Printf("Found %d servers\n", len(servers.Items))
}
```

## Generated Files

After generation, the output directory will contain:

```
./clients/<language>/
├── README.md              # Generated client documentation
├── src/                   # Source code
│   ├── apis/             # API endpoint implementations
│   ├── models/           # Data models
│   └── index.ts          # Main entry point
├── package.json          # Dependencies (TypeScript/JavaScript)
├── setup.py              # Installation script (Python)
├── go.mod                # Go module file (Go)
└── .openapi-generator/   # Generator metadata
```

## Customization

### Custom Generator Options

Edit `generate-client.sh` and modify the `--additional-properties` flag:

```bash
npx @openapitools/openapi-generator-cli generate \
    -i "${OPENAPI_SPEC_FILE}" \
    -g "${GENERATOR}" \
    -o "${OUTPUT_DIR}" \
    --additional-properties=\
npmName=sark-client,\
npmVersion=1.0.0,\
supportsES6=true,\
withInterfaces=true
```

### TypeScript Options

```bash
--additional-properties=\
npmName=sark-client,\
npmVersion=1.0.0,\
supportsES6=true,\
withInterfaces=true,\
useSingleRequestParameter=true
```

### Python Options

```bash
--additional-properties=\
packageName=sark_client,\
packageVersion=1.0.0,\
projectName=sark-client
```

### Go Options

```bash
--additional-properties=\
packageName=sark,\
packageVersion=1.0.0,\
isGoSubmodule=true
```

## Continuous Integration

### GitHub Actions

```yaml
name: Generate API Clients

on:
  push:
    paths:
      - 'src/sark/api/**'

jobs:
  generate-clients:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Start SARK API
        run: docker-compose up -d

      - name: Wait for API
        run: sleep 10

      - name: Generate TypeScript Client
        run: ./scripts/codegen/generate-client.sh typescript ./generated/typescript

      - name: Generate Python Client
        run: ./scripts/codegen/generate-client.sh python ./generated/python

      - name: Commit Generated Clients
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add generated/
          git commit -m "chore: regenerate API clients" || true
          git push
```

## Troubleshooting

### Issue: "Cannot download OpenAPI spec"

**Solution:**
```bash
# Make sure SARK API is running
docker-compose up -d

# Check health endpoint
curl http://localhost:8000/health

# Test OpenAPI endpoint
curl http://localhost:8000/openapi.json | jq .
```

### Issue: "npm: command not found"

**Solution:**
```bash
# Install Node.js from https://nodejs.org/
# Or use Docker method:
export USE_DOCKER=1
./generate-client.sh typescript
```

### Issue: "Generated client has errors"

**Solution:**
```bash
# Validate OpenAPI spec
npx @openapitools/openapi-generator-cli validate -i ./openapi.json

# Check for common issues:
# 1. Missing response models
# 2. Invalid schema definitions
# 3. Circular references
```

### Issue: "Client generation is slow"

**Solution:**
```bash
# Use local OpenAPI spec instead of downloading
export OPENAPI_SPEC_FILE="./path/to/openapi.json"
./generate-client.sh typescript
```

## Best Practices

### 1. Version Your Clients

```bash
# Tag generated clients with API version
./generate-client.sh typescript ./clients/typescript-v1.0.0
```

### 2. Commit Generated Code

Commit generated clients to version control for consistency across team.

### 3. Automate Regeneration

Set up CI/CD to regenerate clients when OpenAPI spec changes.

### 4. Test Generated Clients

```bash
# TypeScript
cd clients/typescript
npm test

# Python
cd clients/python
pytest tests/
```

### 5. Document Client Usage

Provide examples and guides for each generated client.

## Resources

- [OpenAPI Generator](https://openapi-generator.tech/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [SARK API Documentation](../../docs/API_REFERENCE.md)

## Support

- Documentation: `docs/`
- Issues: File an issue on GitHub
- Discussions: GitHub Discussions
