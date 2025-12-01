# SARK v2.0 Quickstart Guide

**Welcome to SARK v2.0!** This guide will get you up and running with SARK's multi-protocol governance platform in under 15 minutes.

## What is SARK v2.0?

SARK (Service Access and Resource Kontrol) v2.0 is a universal governance layer for machine-to-machine protocols. Unlike v1.x which only supported MCP (Model Context Protocol), v2.0 can govern:

- **MCP Servers** - Model Context Protocol tools and resources
- **REST APIs** - HTTP/HTTPS endpoints with OpenAPI specs
- **gRPC Services** - High-performance RPC services
- **Custom Protocols** - Build your own adapters

SARK v2.0 provides:
- ✅ **Unified Authorization** - One policy engine for all protocols
- ✅ **Complete Audit Trail** - Track every API call across protocols
- ✅ **Multi-Protocol Support** - Govern MCP, HTTP, gRPC, and more
- ✅ **Federation Ready** - Connect multiple SARK instances across organizations
- ✅ **Cost Attribution** - Track and limit API costs per user/team

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Docker & Docker Compose** (for PostgreSQL and TimescaleDB)
- **Node.js 18+** (for MCP server examples)
- **Basic understanding** of REST APIs and authorization concepts

---

## Installation

### Step 1: Clone and Install SARK

```bash
# Clone the repository
git clone https://github.com/your-org/sark.git
cd sark

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install SARK v2.0
pip install -e ".[dev]"
```

### Step 2: Start the Database

SARK uses PostgreSQL with TimescaleDB for audit logging:

```bash
# Start PostgreSQL and TimescaleDB
docker-compose up -d postgres timescaledb

# Wait for databases to be ready
docker-compose ps
```

### Step 3: Run Database Migrations

```bash
# Apply v2.0 database schema
alembic upgrade head

# Verify migrations
alembic current
```

You should see the latest migration applied (e.g., `007_add_multi_protocol_support`).

### Step 4: Start SARK Server

```bash
# Start the SARK API server
uvicorn sark.main:app --reload --host 0.0.0.0 --port 8000
```

SARK is now running at `http://localhost:8000`!

Visit `http://localhost:8000/docs` to see the interactive API documentation.

---

## Your First Multi-Protocol Setup

Let's register and govern resources from three different protocols: MCP, HTTP, and gRPC.

### 1. Register an MCP Server

First, let's add an MCP filesystem server:

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "mcp",
    "discovery_config": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "name": "Filesystem Server",
    "sensitivity_level": "high"
  }'
```

**Response:**
```json
{
  "id": "mcp-filesystem-abc123",
  "name": "Filesystem Server",
  "protocol": "mcp",
  "endpoint": "npx @modelcontextprotocol/server-filesystem",
  "capabilities": [
    {
      "id": "filesystem-read_file",
      "name": "read_file",
      "description": "Read a file from the filesystem",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {"type": "string"}
        }
      }
    },
    {
      "id": "filesystem-write_file",
      "name": "write_file",
      "description": "Write content to a file"
    },
    {
      "id": "filesystem-list_directory",
      "name": "list_directory",
      "description": "List files in a directory"
    }
  ],
  "created_at": "2024-11-29T10:00:00Z"
}
```

SARK automatically discovered all the MCP server's tools and converted them to capabilities!

### 2. Register a REST API

Now let's add the GitHub API:

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "http",
    "discovery_config": {
      "base_url": "https://api.github.com",
      "openapi_spec_url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
      "auth": {
        "type": "bearer",
        "token": "ghp_your_token_here"
      }
    },
    "name": "GitHub API",
    "sensitivity_level": "medium"
  }'
```

**Response:**
```json
{
  "id": "http-github-api-def456",
  "name": "GitHub API",
  "protocol": "http",
  "endpoint": "https://api.github.com",
  "capabilities": [
    {
      "id": "GET-/user",
      "name": "get_authenticated_user",
      "description": "Get the authenticated user"
    },
    {
      "id": "GET-/user/repos",
      "name": "list_repos_for_authenticated_user",
      "description": "List repositories for the authenticated user"
    },
    {
      "id": "POST-/repos/{owner}/{repo}/issues",
      "name": "create_issue",
      "description": "Create an issue"
    }
  ]
}
```

SARK parsed the OpenAPI spec and created capabilities for each endpoint!

### 3. Register a gRPC Service

Finally, let's add a gRPC greeter service:

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "grpc",
    "discovery_config": {
      "endpoint": "localhost:50051",
      "reflection": true,
      "tls": false
    },
    "name": "Greeter Service",
    "sensitivity_level": "low"
  }'
```

**Response:**
```json
{
  "id": "grpc-greeter-ghi789",
  "name": "Greeter Service",
  "protocol": "grpc",
  "endpoint": "localhost:50051",
  "capabilities": [
    {
      "id": "Greeter.SayHello",
      "name": "SayHello",
      "description": "Sends a greeting",
      "input_schema": {
        "name": "string"
      },
      "output_schema": {
        "message": "string"
      }
    }
  ]
}
```

---

## Authorizing and Invoking Capabilities

Now that we have resources from three different protocols, let's create policies and invoke them.

### Step 1: Create a User Principal

```bash
curl -X POST http://localhost:8000/api/v1/principals \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice",
    "type": "user",
    "attributes": {
      "email": "alice@example.com",
      "department": "engineering"
    }
  }'
```

**Response:**
```json
{
  "id": "principal-alice-123",
  "name": "Alice",
  "type": "user",
  "created_at": "2024-11-29T10:05:00Z"
}
```

### Step 2: Create Authorization Policies

Let's create policies that allow Alice to:
- Read files (MCP)
- View GitHub repos (HTTP)
- Call the greeter service (gRPC)

Create a file `alice-policy.rego`:

```rego
package sark.policies

import future.keywords.if

# Allow Alice to read files from filesystem
allow if {
    input.principal.name == "Alice"
    input.resource.protocol == "mcp"
    input.capability.name == "read_file"
}

# Allow Alice to list GitHub repos
allow if {
    input.principal.name == "Alice"
    input.resource.protocol == "http"
    contains(input.capability.id, "/user/repos")
}

# Allow Alice to call greeter service
allow if {
    input.principal.name == "Alice"
    input.resource.protocol == "grpc"
    input.resource.name == "Greeter Service"
}

# Deny everything else by default
allow = false
```

Upload the policy:

```bash
curl -X POST http://localhost:8000/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "alice-multi-protocol-policy",
    "content": "'$(cat alice-policy.rego)'"
  }'
```

### Step 3: Invoke Capabilities (Multi-Protocol!)

Now Alice can invoke capabilities across all three protocols through SARK's unified authorization layer:

#### Invoke MCP Capability (Read File)

```bash
curl -X POST http://localhost:8000/api/v2/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "capability_id": "filesystem-read_file",
    "principal_id": "principal-alice-123",
    "arguments": {
      "path": "/tmp/test.txt"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "result": {
    "content": "Hello from the filesystem!"
  },
  "duration_ms": 125.4,
  "protocol": "mcp"
}
```

#### Invoke HTTP Capability (List GitHub Repos)

```bash
curl -X POST http://localhost:8000/api/v2/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "capability_id": "GET-/user/repos",
    "principal_id": "principal-alice-123",
    "arguments": {}
  }'
```

**Response:**
```json
{
  "success": true,
  "result": [
    {
      "name": "my-repo",
      "full_name": "alice/my-repo",
      "private": false
    }
  ],
  "duration_ms": 342.1,
  "protocol": "http"
}
```

#### Invoke gRPC Capability (Say Hello)

```bash
curl -X POST http://localhost:8000/api/v2/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "capability_id": "Greeter.SayHello",
    "principal_id": "principal-alice-123",
    "arguments": {
      "name": "Alice"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "result": {
    "message": "Hello, Alice!"
  },
  "duration_ms": 12.3,
  "protocol": "grpc"
}
```

---

## Viewing the Audit Trail

Every invocation is automatically logged. View the audit trail:

```bash
curl http://localhost:8000/api/v1/audit-log?principal_id=principal-alice-123
```

**Response:**
```json
{
  "events": [
    {
      "timestamp": "2024-11-29T10:10:00Z",
      "principal": "Alice",
      "resource": "Filesystem Server",
      "capability": "read_file",
      "protocol": "mcp",
      "action": "execute",
      "decision": "allow",
      "duration_ms": 125.4
    },
    {
      "timestamp": "2024-11-29T10:11:00Z",
      "principal": "Alice",
      "resource": "GitHub API",
      "capability": "GET-/user/repos",
      "protocol": "http",
      "action": "execute",
      "decision": "allow",
      "duration_ms": 342.1
    },
    {
      "timestamp": "2024-11-29T10:12:00Z",
      "principal": "Alice",
      "resource": "Greeter Service",
      "capability": "SayHello",
      "protocol": "grpc",
      "action": "execute",
      "decision": "allow",
      "duration_ms": 12.3
    }
  ]
}
```

You now have a complete audit trail of all API calls across MCP, HTTP, and gRPC!

---

## Understanding the Architecture

SARK v2.0 uses a **protocol adapter pattern** to provide unified governance:

```
┌─────────────────────────────────────────────────┐
│           SARK Core (Protocol-Agnostic)         │
│  ┌────────────┐  ┌──────────┐  ┌─────────────┐ │
│  │  Policy    │  │  Audit   │  │    Auth     │ │
│  │  Engine    │  │  Logger  │  │   Service   │ │
│  │   (OPA)    │  │(Timescale)│ │             │ │
│  └────────────┘  └──────────┘  └─────────────┘ │
└─────────────────────────────────────────────────┘
                      ↓
           Universal GRID Interface
           (Resource, Capability, Action)
                      ↓
┌──────────────┬──────────────┬──────────────┐
│ MCP Adapter  │ HTTP Adapter │ gRPC Adapter │
│              │              │              │
│ • stdio      │ • OpenAPI    │ • Reflection │
│ • SSE        │ • REST auth  │ • Streaming  │
│ • HTTP       │ • OAuth 2.0  │ • mTLS       │
└──────────────┴──────────────┴──────────────┘
       ↓               ↓               ↓
   MCP Servers    REST APIs      gRPC Services
```

**Key Concepts:**

1. **Protocol Adapter**: Translates protocol-specific concepts to GRID abstractions
2. **Resource**: Any governed entity (MCP server, REST API, gRPC service)
3. **Capability**: An action that can be performed (MCP tool, REST endpoint, gRPC method)
4. **Principal**: An entity making requests (user, service account, AI agent)
5. **Policy**: Rules governing who can do what (written in Rego)

---

## What's Different from v1.x?

SARK v2.0 brings major improvements:

| Feature | v1.x (MCP-only) | v2.0 (Multi-Protocol) |
|---------|-----------------|----------------------|
| **Protocols Supported** | MCP only | MCP, HTTP, gRPC, Custom |
| **Architecture** | MCP-specific logic | Protocol adapter pattern |
| **Authorization** | Per MCP server | Unified across all protocols |
| **Audit** | MCP calls only | All protocol invocations |
| **Federation** | Not supported | Cross-org resource sharing |
| **Cost Tracking** | Manual | Automatic per-protocol |
| **Extensibility** | Hard to add protocols | Easy adapter plugin system |

---

## Next Steps

Congratulations! You've successfully:
- ✅ Installed SARK v2.0
- ✅ Registered resources from three different protocols
- ✅ Created authorization policies
- ✅ Invoked capabilities across MCP, HTTP, and gRPC
- ✅ Viewed the unified audit trail

### Continue Learning:

1. **[Building Custom Adapters](BUILDING_ADAPTERS.md)** - Create your own protocol adapter
2. **[Multi-Protocol Orchestration](MULTI_PROTOCOL_ORCHESTRATION.md)** - Build workflows spanning multiple protocols
3. **[Federation Deployment](FEDERATION_DEPLOYMENT.md)** - Connect multiple SARK instances
4. **[Troubleshooting Guide](../troubleshooting/V2_TROUBLESHOOTING.md)** - Common issues and solutions

### Explore Examples:

- `examples/v2/multi-protocol-example/` - Complete multi-protocol workflow
- `examples/v2/custom-adapter-example/` - Build a custom adapter
- `examples/http-adapter-example/` - Advanced HTTP/REST scenarios
- `examples/grpc-adapter-example/` - gRPC streaming and auth

---

## Getting Help

- **Documentation**: [https://sark.example.com/docs](https://sark.example.com/docs)
- **GitHub Issues**: [https://github.com/your-org/sark/issues](https://github.com/your-org/sark/issues)
- **Slack Community**: [#sark-support](https://your-workspace.slack.com/archives/sark-support)
- **Email**: support@sark.example.com

---

**Happy governing!** 🚀

SARK v2.0 - Universal Governance for Machine-to-Machine Protocols
