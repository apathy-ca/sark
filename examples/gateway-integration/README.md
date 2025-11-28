# SARK Gateway Integration - Docker Compose Example

This directory contains a complete Docker Compose setup for SARK v1.1.0 with MCP Gateway integration.

## What's Included

- **SARK v1.1.0** - Authorization service with Gateway integration enabled
- **MCP Gateway** - Gateway registry for routing MCP requests
- **PostgreSQL** - Database for SARK
- **Redis** - Cache for SARK
- **OPA** - Policy engine for authorization
- **Example MCP Servers** - PostgreSQL and GitHub MCP servers
- **Prometheus** (Optional) - Metrics collection
- **Grafana** (Optional) - Metrics visualization

## Quick Start

### 1. Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### 2. Setup

```bash
# Copy environment file
cp .env.example .env

# Edit .env and update:
# - GATEWAY_API_KEY (generate with: openssl rand -hex 32)
# - SARK_API_KEY (will generate after starting SARK)
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)
nano .env
```

### 3. Start Services

```bash
# Start all services
docker compose -f docker-compose.gateway.yml up -d

# Watch logs
docker compose -f docker-compose.gateway.yml logs -f sark
```

### 4. Generate SARK API Key

```bash
# Generate API key for Gateway to call SARK
docker exec -it sark-app python -m sark.cli.generate_api_key \
  --name "MCP Gateway" \
  --type gateway \
  --permissions "gateway:*"

# Copy the generated API key
# Update .env: SARK_API_KEY=sark_gw_...

# Restart Gateway to pick up new API key
docker compose -f docker-compose.gateway.yml restart mcp-gateway
```

### 5. Verify Integration

```bash
# Check SARK version
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.1.0",
  "features": {
    "gateway_integration": true,
    "a2a_authorization": false
  }
}

# Login to get a token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin"
  }' | jq -r '.access_token')

# Test Gateway authorization endpoint
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {
      "id": "user_123",
      "email": "admin@example.com",
      "roles": ["admin"]
    }
  }'

# Expected: {"allow": true, ...}
```

### 6. Access Monitoring (Optional)

- **Prometheus:** http://localhost:9091
- **Grafana:** http://localhost:3000 (admin / admin)

## Architecture

```
┌─────────────────┐
│   User/Client   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  MCP Gateway    │ ←──────┐
│   (port 8080)   │        │ Authorization
└────────┬────────┘        │ Requests
         │                 │
         │ Route to        │
         │ MCP Server      │
         v                 │
┌─────────────────┐        │
│  MCP Servers    │        │
│  - postgres-mcp │        │
│  - github-mcp   │        │
└─────────────────┘        │
                           │
┌──────────────────────────┴──────┐
│          SARK v1.1.0            │
│       (port 8000)               │
│  ┌────────────────────────┐    │
│  │  Gateway API           │    │
│  │  /api/v1/gateway/*     │    │
│  └───────┬────────────────┘    │
│          │                      │
│          v                      │
│  ┌────────────────────────┐    │
│  │  OPA Policy Engine     │    │
│  │  (port 8181)           │    │
│  └────────────────────────┘    │
│                                 │
│  ┌────────────────────────┐    │
│  │  PostgreSQL Database   │    │
│  │  (port 5432)           │    │
│  └────────────────────────┘    │
│                                 │
│  ┌────────────────────────┐    │
│  │  Redis Cache           │    │
│  │  (port 6379)           │    │
│  └────────────────────────┘    │
└─────────────────────────────────┘
```

## Directory Structure

```
examples/gateway-integration/
├── docker-compose.gateway.yml  # Main compose file
├── .env.example                # Environment template
├── README.md                   # This file
├── opa/
│   ├── bundle/                 # OPA policy bundles
│   └── policies/               # Gateway policies
│       └── gateway.rego
├── gateway/
│   └── config/
│       └── mcp-servers.json    # MCP server registry
├── prometheus/
│   └── prometheus.yml          # Prometheus config
└── grafana/
    ├── dashboards/             # Grafana dashboards
    └── datasources/            # Grafana datasources
```

## Configuration

### Gateway Integration

Enable/disable Gateway integration:

```bash
# Enable (v1.1.0 feature)
GATEWAY_ENABLED=true

# Disable (v1.0.0 behavior)
GATEWAY_ENABLED=false
```

### Agent-to-Agent Authorization

Enable A2A authorization (requires `GATEWAY_ENABLED=true`):

```bash
A2A_ENABLED=true
```

### OPA Policies

Edit Gateway policies in `opa/policies/gateway.rego`:

```rego
package mcp.gateway

# Default deny
default allow = false

# Allow admins to invoke any tool
allow {
    input.user.roles[_] == "admin"
    input.action == "gateway:tool:invoke"
}

# Allow analysts to query databases
allow {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.server_name == "postgres-mcp"
    input.tool_name == "execute_query"
}
```

Reload policies:

```bash
# Bundle policies
cd opa/policies
tar -czf ../bundle/bundle.tar.gz .

# Restart OPA
docker compose -f docker-compose.gateway.yml restart opa
```

## Troubleshooting

### Issue: Gateway integration not enabled

```bash
# Check environment variable
docker exec -it sark-app env | grep GATEWAY_ENABLED

# Should output: GATEWAY_ENABLED=true
```

### Issue: "Gateway connection failed"

```bash
# Test Gateway connectivity from SARK
docker exec -it sark-app curl http://mcp-gateway:8080/health

# Should return: {"status": "healthy"}
```

### Issue: "Invalid SARK API key"

```bash
# Regenerate SARK API key
docker exec -it sark-app python -m sark.cli.generate_api_key \
  --name "MCP Gateway" \
  --type gateway \
  --permissions "gateway:*"

# Update .env with new SARK_API_KEY
# Restart Gateway
docker compose -f docker-compose.gateway.yml restart mcp-gateway
```

### View Logs

```bash
# All services
docker compose -f docker-compose.gateway.yml logs -f

# Specific service
docker compose -f docker-compose.gateway.yml logs -f sark
docker compose -f docker-compose.gateway.yml logs -f mcp-gateway
docker compose -f docker-compose.gateway.yml logs -f opa
```

## Stopping Services

```bash
# Stop all services
docker compose -f docker-compose.gateway.yml down

# Stop and remove volumes (WARNING: deletes data)
docker compose -f docker-compose.gateway.yml down -v
```

## Production Considerations

This is a **development/testing** example. For production:

1. **Security:**
   - Change all default passwords
   - Use secrets management (HashiCorp Vault, AWS Secrets Manager)
   - Enable TLS/HTTPS
   - Use stronger JWT secrets

2. **Scalability:**
   - Deploy to Kubernetes (see `../kubernetes/`)
   - Use managed databases (RDS, Cloud SQL)
   - Use managed Redis (ElastiCache, Cloud Memorystore)
   - Scale SARK horizontally (multiple replicas)

3. **Monitoring:**
   - Set up Prometheus alerts
   - Configure Grafana dashboards
   - Enable logging to centralized system (ELK, Datadog)

4. **High Availability:**
   - Deploy across multiple availability zones
   - Use load balancers
   - Set up database replication
   - Configure auto-scaling

See [../../docs/gateway-integration/deployment/PRODUCTION_DEPLOYMENT.md](../../docs/gateway-integration/deployment/PRODUCTION_DEPLOYMENT.md) for production deployment guide.

## Next Steps

- **Configure Policies:** See [OPA policy examples](../policies/)
- **Kubernetes Deployment:** See [../kubernetes/](../kubernetes/)
- **Production Deployment:** See [../../docs/gateway-integration/deployment/PRODUCTION_DEPLOYMENT.md](../../docs/gateway-integration/deployment/PRODUCTION_DEPLOYMENT.md)
- **Troubleshooting:** See [../../docs/gateway-integration/runbooks/TROUBLESHOOTING.md](../../docs/gateway-integration/runbooks/TROUBLESHOOTING.md)

## Support

For issues or questions:
- Documentation: https://docs.sark.io/gateway-integration
- GitHub Issues: https://github.com/your-org/sark/issues
