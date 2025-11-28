# Gateway Integration Examples

This directory contains comprehensive examples for SARK v1.1.0 Gateway Integration:

1. **Python Code Examples** - How to use the Gateway client and models
2. **Docker Compose Setup** - Complete deployment example with all services

---

## 🐍 Python Code Examples

### Purpose
Educational examples showing best practices for Gateway model usage and client operations.

**Author:** Engineer 1 (Gateway Models Architect)

### Available Examples

#### 1. `basic_client.py` - Gateway Client Basics

**What it demonstrates:**
- Initializing the Gateway client with proper configuration
- Listing available MCP servers
- Filtering servers by sensitivity level
- Getting detailed server information
- Discovering tools on servers
- Health checking the Gateway

**Best for:**
- First-time Gateway users
- Understanding basic client operations
- Learning about server discovery

**Run it:**
```bash
python examples/gateway-integration/basic_client.py
```

#### 2. `error_handling.py` - Error Handling Patterns

**What it demonstrates:**
- Connection errors and retries
- Timeout handling
- Authentication failures
- Circuit breaker patterns
- Graceful degradation

**Best for:**
- Production-ready error handling
- Resilience patterns
- Retry strategies

**Run it:**
```bash
python examples/gateway-integration/error_handling.py
```

#### 3. `server_registration.py` - Server Registration

**What it demonstrates:**
- Registering MCP servers with the Gateway
- Configuring sensitivity levels
- Setting up access restrictions
- Team-based authorization
- Health status monitoring

**Best for:**
- Gateway administrators
- Server operators
- Understanding access control

**Run it:**
```bash
python examples/gateway-integration/server_registration.py
```

#### 4. `tool_invocation.py` - Tool Invocation

**What it demonstrates:**
- Invoking tools through the Gateway
- Parameter validation
- Authorization checks
- Audit logging
- Response handling

**Best for:**
- Understanding tool invocation flow
- Authorization patterns
- Audit requirements

**Run it:**
```bash
python examples/gateway-integration/tool_invocation.py
```

---

## 🐳 Docker Compose Setup

### Purpose
Complete Docker Compose environment for testing SARK v1.1.0 with Gateway integration.

**Author:** Engineer 3 (Policies & Integration)

### What's Included

- **SARK v1.1.0** - Authorization service with Gateway integration enabled
- **MCP Gateway** - Gateway registry for routing MCP requests
- **PostgreSQL** - Database for SARK
- **Redis** - Cache for SARK
- **OPA** - Policy engine for authorization
- **Example MCP Servers** - PostgreSQL and GitHub MCP servers
- **Prometheus** (Optional) - Metrics collection
- **Grafana** (Optional) - Metrics visualization

### Quick Start

#### 1. Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

#### 2. Setup

```bash
# Copy environment file
cp .env.example .env

# Edit .env and update:
# - GATEWAY_API_KEY (generate with: openssl rand -hex 32)
# - POSTGRES_PASSWORD
# - Other secrets as needed

# Start all services
docker compose -f docker-compose.gateway.yml up -d

# Check status
docker compose -f docker-compose.gateway.yml ps

# View logs
docker compose -f docker-compose.gateway.yml logs -f sark
```

#### 3. Verify Installation

```bash
# Check SARK health
curl http://localhost:8000/health

# Check Gateway health
curl http://localhost:8080/health

# Check OPA health
curl http://localhost:8181/health
```

#### 4. Create SARK API Key

```bash
# Get shell in SARK container
docker compose -f docker-compose.gateway.yml exec sark bash

# Create API key
sark-cli create-api-key --user admin --team platform

# Save the API key to .env as SARK_API_KEY
```

#### 5. Test Gateway Integration

```bash
# List servers
curl -H "Authorization: Bearer $SARK_API_KEY" \
  http://localhost:8000/api/gateway/servers

# List tools
curl -H "Authorization: Bearer $SARK_API_KEY" \
  http://localhost:8000/api/gateway/tools

# Test authorization
curl -X POST -H "Authorization: Bearer $SARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"action": "gateway:tool:invoke", "server_name": "postgres-mcp", "tool_name": "query"}' \
  http://localhost:8000/api/gateway/authorize
```

### Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────┐
│    SARK     │────▶│   OPA    │ (Policies)
└──────┬──────┘     └──────────┘
       │
       ▼
┌─────────────┐     ┌──────────┐
│  Gateway    │────▶│PostgreSQL│ (Registry)
└──────┬──────┘     └──────────┘
       │
       ▼
┌─────────────────────────────┐
│   MCP Servers               │
│  ┌──────────┬──────────┐    │
│  │Postgres  │ GitHub   │    │
│  │   MCP    │   MCP    │    │
│  └──────────┴──────────┘    │
└─────────────────────────────┘
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| SARK | 8000 | Authorization API |
| Gateway | 8080 | MCP Gateway Registry |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| OPA | 8181 | Policy Engine |
| Prometheus | 9090 | Metrics (optional) |
| Grafana | 3000 | Dashboards (optional) |

### Policies

OPA policies are located in `policies/` directory:
- `gateway.rego` - Gateway authorization policies
- `a2a.rego` - Agent-to-agent policies

Edit these policies to customize authorization rules.

### Monitoring

Enable monitoring stack:
```bash
docker compose -f docker-compose.gateway.yml --profile monitoring up -d
```

Access Grafana at http://localhost:3000 (admin/admin)

### Troubleshooting

**Services won't start:**
- Check Docker resources (4GB RAM minimum)
- Check port conflicts (8000, 8080, 5432, 6379, 8181)
- Review logs: `docker compose logs`

**Authorization failing:**
- Verify SARK_API_KEY in .env
- Check OPA is running: `curl http://localhost:8181/health`
- Review policy logs: `docker compose logs opa`

**Gateway not finding servers:**
- Check Gateway is running: `curl http://localhost:8080/health`
- Verify MCP servers are registered
- Check Gateway logs: `docker compose logs gateway`

---

## 📁 Directory Structure

```
examples/gateway-integration/
├── README.md                          # This file
├── basic_client.py                    # Python: Basic client usage
├── error_handling.py                  # Python: Error handling patterns
├── server_registration.py             # Python: Server registration
├── tool_invocation.py                 # Python: Tool invocation
├── docker-compose.gateway.yml         # Docker: Complete environment
├── .env.example                       # Docker: Environment template
└── policies/                          # Docker: OPA policies
    ├── gateway.rego                   # Gateway authorization
    └── a2a.rego                       # Agent-to-agent auth
```

---

## 🎓 Learning Path

1. **Understand the Basics** - Read `basic_client.py`
2. **Handle Errors** - Study `error_handling.py`
3. **Deploy Locally** - Run Docker Compose setup
4. **Test Authorization** - Use the API examples
5. **Customize Policies** - Edit OPA policies
6. **Monitor** - Enable Prometheus + Grafana

---

## 📚 Additional Resources

- [Gateway Integration Documentation](../../docs/gateway-integration/)
- [API Reference](../../docs/gateway-integration/API_REFERENCE.md)
- [Deployment Guide](../../docs/gateway-integration/deployment/)
- [Troubleshooting](../../docs/troubleshooting/gateway/)

---

## 🤝 Contributing

Found an issue or have a suggestion? Please contribute examples that help others learn!

---

**Version:** 1.1.0
**Last Updated:** 2025-01-28
**Authors:** Engineer 1, Engineer 3
