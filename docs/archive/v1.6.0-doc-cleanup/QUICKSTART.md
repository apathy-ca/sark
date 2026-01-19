# SARK Quick Start Guide

Get up and running with SARK in under 10 minutes.

## Prerequisites

- Docker and Docker Compose v2
- Python 3.11+ (for local development)
- 8GB+ RAM available for Docker

## Step 1: Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/sark.git
cd sark

# Create environment file
cp .env.example .env

# The default values in .env are suitable for development
```

## Step 2: Start Services

```bash
# Start all services
docker compose up -d

# Wait for services to be ready (30-60 seconds)
docker compose ps
```

You should see all services in "Up" state:
- sark-api
- sark-postgres
- sark-timescaledb
- sark-redis
- sark-consul
- sark-opa
- sark-vault
- sark-prometheus
- sark-grafana

## Step 3: Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"0.1.0","environment":"development"}

# View API documentation
open http://localhost:8000/docs
```

## Step 4: Register Your First MCP Server

```bash
# Register a sample MCP server
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sample-database-server",
    "transport": "http",
    "endpoint": "http://localhost:9000",
    "version": "2025-06-18",
    "capabilities": ["tools"],
    "tools": [
      {
        "name": "query_database",
        "description": "Query the database",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string"}
          }
        },
        "sensitivity_level": "medium"
      }
    ],
    "sensitivity_level": "medium"
  }'

# Expected response:
# {
#   "server_id": "uuid-here",
#   "status": "registered",
#   "consul_id": "mcp-sample-database-server-uuid"
# }
```

## Step 5: Test Authorization

```bash
# Evaluate policy for tool access
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000000",
    "action": "tool:invoke",
    "tool": "query_database",
    "parameters": {}
  }'

# Expected response:
# {
#   "decision": "allow" or "deny",
#   "reason": "...",
#   "filtered_parameters": null,
#   "audit_id": null
# }
```

## Step 6: Explore Services

### Consul UI (Service Discovery)
```bash
open http://localhost:8500
```

Browse registered MCP servers in the Consul service registry.

### Grafana (Monitoring)
```bash
open http://localhost:3000
# Login: admin / admin
```

View metrics dashboards for SARK services.

### OPA Playground (Policy Testing)
```bash
# Test OPA policies directly
curl -X POST http://localhost:8181/v1/data/mcp/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "user-123", "role": "developer", "teams": []},
      "action": "tool:invoke",
      "tool": {"name": "test", "sensitivity_level": "low"},
      "context": {"timestamp": 0}
    }
  }'
```

## Step 7: View Audit Logs

```bash
# Connect to TimescaleDB
docker compose exec timescaledb psql -U sark sark_audit

# Query recent audit events
sark_audit=# SELECT event_type, severity, user_email, tool_name, timestamp
             FROM audit_events
             ORDER BY timestamp DESC
             LIMIT 10;
```

## Next Steps

### Development

1. **Install Python dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

2. **Run tests:**
```bash
pytest
```

3. **Start API in development mode:**
```bash
# Stop the Docker API container first
docker compose stop api

# Run locally with hot reload
uvicorn sark.api.main:app --reload
```

### Production Deployment

See [Deployment Runbook](docs/runbooks/DEPLOYMENT.md) for:
- Kubernetes deployment
- Production configuration
- Scaling guidelines
- Monitoring setup

### Learn More

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs)
- [OPA Policy Guide](opa/policies/README.md)
- [Incident Response](docs/runbooks/INCIDENT_RESPONSE.md)

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose logs

# Common issues:
# 1. Port conflicts - ensure ports 8000, 5432, 6379, 8500, 8181, 8200 are available
# 2. Insufficient memory - ensure Docker has at least 8GB RAM
# 3. Network issues - check Docker network configuration
```

### Database connection errors

```bash
# Restart databases
docker compose restart postgres timescaledb

# Recreate volumes if corrupted (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

### OPA policy errors

```bash
# Validate policies
docker compose exec opa opa test /policies -v

# Check OPA logs
docker compose logs opa
```

## Clean Up

To stop and remove all services:

```bash
# Stop services (preserves data)
docker compose down

# Stop and remove all data
docker compose down -v
```

---

**Welcome to SARK!** You're now ready to govern MCP deployments at scale.

For questions or issues, please open a GitHub issue or contact the team.
