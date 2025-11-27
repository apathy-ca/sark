# Get Started with SARK in 5 Minutes

**Quick setup guide to get SARK running locally**

---

## Prerequisites

Before you begin, ensure you have:
- **Docker** with Docker Compose v2 installed
- **Git** installed
- **5 minutes** of your time

That's it! Docker Compose will handle all dependencies.

---

## Quick Start

### Step 1: Clone the Repository (30 seconds)

```bash
git clone https://github.com/your-org/sark.git
cd sark
```

### Step 2: Start SARK (2 minutes)

```bash
# Start all services with Docker Compose
docker compose --profile full up -d
```

This starts:
- **PostgreSQL** - Database for policies and metadata
- **Redis** - Caching layer
- **Open Policy Agent (OPA)** - Policy engine
- **SARK API** - Main application

**Wait for services to be ready** (check status):
```bash
docker compose ps
```

All services should show `healthy` status.

### Step 3: Verify Installation (30 seconds)

Check that SARK is running:

```bash
# Health check
curl http://localhost:8000/health

# Expected output:
# {"status": "healthy", "version": "0.2.0"}
```

### Step 4: Access the API (1 minute)

Try the API endpoints:

**Get server list (empty initially):**
```bash
curl http://localhost:8000/api/v1/servers
```

**Register your first MCP server:**
```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-server",
    "url": "http://localhost:9000",
    "description": "My first MCP server",
    "team": "engineering",
    "sensitivity": "low",
    "tags": ["test", "demo"]
  }'
```

**Verify registration:**
```bash
curl http://localhost:8000/api/v1/servers
```

### Step 5: Explore the Documentation (1 minute)

**API Documentation:**
```bash
# Open in browser
open http://localhost:8000/docs
```

Interactive Swagger UI with all API endpoints.

**Available Guides:**
- **[MCP Introduction](MCP_INTRODUCTION.md)** - Understanding Model Context Protocol
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Quick Start](QUICK_START.md)** - Detailed getting started guide
- **[Architecture](ARCHITECTURE.md)** - System design and components

---

## What You Just Did

In 5 minutes, you:

✅ Installed SARK with all dependencies
✅ Started PostgreSQL, Redis, OPA, and SARK API
✅ Verified the installation
✅ Registered your first MCP server
✅ Accessed the interactive API documentation

---

## Next Steps

### For Developers: Build an MCP Server

Create a simple MCP server and register it with SARK:

```python
# my_mcp_server.py
from mcp import Server

server = Server(name="my-server", version="1.0.0")

@server.tool(name="hello", description="Say hello")
async def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    server.run(port=9000)
```

Register with SARK (see Step 4 above).

### For Organizations: Configure Authentication

Set up enterprise authentication:

1. **OIDC/OAuth 2.0**: [OIDC Setup Guide](OIDC_SETUP.md)
2. **LDAP/AD**: [LDAP Setup Guide](LDAP_SETUP.md)
3. **SAML 2.0**: [SAML Setup Guide](SAML_SETUP.md)

### For Security Teams: Configure Policies

Customize authorization policies:

1. **OPA Policies**: [OPA Policy Guide](OPA_POLICY_GUIDE.md)
2. **Tool Sensitivity**: [Tool Sensitivity Classification](TOOL_SENSITIVITY_CLASSIFICATION.md)
3. **Audit Configuration**: [Audit Guide](POLICY_AUDIT_GUIDE.md)

---

## Common Issues

### Port Already in Use

If port 8000 is already in use:

```bash
# Stop existing services
docker compose down

# Change port in docker-compose.yml
# Edit the 'ports' section for SARK API:
# ports:
#   - "8001:8000"  # Use 8001 instead

# Restart
docker compose --profile full up -d
```

### Services Not Healthy

Check logs for specific service:

```bash
# Check SARK API logs
docker compose logs sark-api

# Check PostgreSQL logs
docker compose logs postgres

# Check all logs
docker compose logs
```

### Database Connection Issues

Reset the database:

```bash
docker compose down -v  # Remove volumes
docker compose --profile full up -d  # Restart
```

---

## Clean Up

To stop and remove all services:

```bash
# Stop services
docker compose down

# Remove all data (including volumes)
docker compose down -v
```

---

## Getting Help

- **[FAQ](FAQ.md)** - Frequently asked questions
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[GitHub Issues](https://github.com/your-org/sark/issues)** - Report bugs or request features

---

## Full Documentation

This 5-minute guide gets you started quickly. For complete documentation:

**Comprehensive Guides:**
- **[Complete Quick Start](QUICK_START.md)** - 15-minute detailed guide
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment
- **[Development Guide](DEVELOPMENT.md)** - Development setup and workflow

**Learning Resources:**
- **[MCP Introduction](MCP_INTRODUCTION.md)** - What is MCP and why SARK
- **[Learning Path](LEARNING_PATH.md)** - Structured learning journey (Coming Soon)
- **[Onboarding Checklist](ONBOARDING_CHECKLIST.md)** - Complete setup checklist (Coming Soon)

---

**Success!** You now have SARK running locally. Ready to govern your MCP deployments! 🎉
