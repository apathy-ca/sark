# SARK v1.x to v2.0 Migration Guide

**Version:** 2.0.0
**Last Updated:** December 2025
**Migration Difficulty:** Medium
**Estimated Time:** 2-4 hours

---

## Table of Contents

- [Overview](#overview)
- [Breaking Changes](#breaking-changes)
- [Database Migration](#database-migration)
- [API Changes](#api-changes)
- [Configuration Changes](#configuration-changes)
- [Policy Migration](#policy-migration)
- [Code Migration](#code-migration)
- [Testing Your Migration](#testing-your-migration)
- [Rollback Plan](#rollback-plan)
- [FAQ](#faq)

---

## Overview

SARK v2.0 represents a major evolution from an MCP-specific governance system to a universal protocol governance platform implementing GRID Protocol v1.0. While there are breaking changes, the migration path is straightforward and mostly automated.

### What's Changing

**Major Changes:**
- MCP servers → Generic resources
- MCP tools → Generic capabilities
- Protocol-specific code → Protocol adapters
- New federation support
- New cost attribution system

**What's NOT Changing:**
- Policy evaluation (still OPA)
- Audit logging (still TimescaleDB)
- Authentication & authorization flow
- Core security model

### Migration Strategy

For users with NO production deployments (most cases):
- ✅ **Fresh installation** of v2.0 recommended
- ✅ Re-register resources using new API
- ✅ Minimal migration effort

For users with existing data (testing/development):
- ✅ **Automated migration script** provided
- ✅ Database schema migration via Alembic
- ✅ Data transformation for existing resources

---

## Breaking Changes

### API Endpoints

| v1.x Endpoint | v2.0 Endpoint | Notes |
|---------------|---------------|-------|
| `POST /api/v1/servers` | `POST /api/v2/resources` | Different request format |
| `GET /api/v1/servers` | `GET /api/v2/resources?protocol=mcp` | Filter by protocol |
| `GET /api/v1/servers/{id}` | `GET /api/v2/resources/{id}` | Same response structure |
| `DELETE /api/v1/servers/{id}` | `DELETE /api/v2/resources/{id}` | No change |

**Backward Compatibility:**
v1.x endpoints are still supported but deprecated. They will be removed in v3.0 (Q1 2027).

### Request/Response Formats

**v1.x: Register MCP Server**
```json
{
  "name": "filesystem-server",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem"],
  "env": {
    "ALLOWED_DIRECTORIES": "/home/user/docs"
  }
}
```

**v2.0: Register Resource (MCP)**
```json
{
  "protocol": "mcp",
  "discovery_config": {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    "env": {
      "ALLOWED_DIRECTORIES": "/home/user/docs"
    }
  },
  "sensitivity_level": "high"
}
```

### Database Schema

**New Tables:**
- `resources` (replaces `mcp_servers`)
- `capabilities` (replaces `mcp_tools`)
- `federation_nodes` (new)
- `cost_tracking` (new)
- `principal_budgets` (new)

**Deprecated Tables:**
- `mcp_servers` (data migrated to `resources`)
- `mcp_tools` (data migrated to `capabilities`)

These tables remain for backward compatibility but will be removed in v3.0.

### Configuration File

**v1.x: config.yaml**
```yaml
database:
  url: postgresql://...

opa:
  url: http://opa:8181

mcp:
  default_sensitivity: medium
```

**v2.0: config.yaml**
```yaml
database:
  url: postgresql://...

opa:
  url: http://opa:8181

adapters:
  mcp:
    default_sensitivity: medium
  http:
    default_timeout: 30
  grpc:
    max_connections: 100

# New: Federation config
federation:
  enabled: false
  node_id: "myorg.com"

# New: Cost tracking config
cost_tracking:
  enabled: false
```

---

## Database Migration

### Prerequisites

1. **Backup your database:**
   ```bash
   pg_dump -h localhost -U sark sark_db > sark_v1_backup.sql
   ```

2. **Stop SARK v1.x:**
   ```bash
   docker-compose down
   ```

3. **Update to v2.0:**
   ```bash
   git checkout v2.0.0
   docker-compose pull
   ```

### Automated Migration

SARK v2.0 includes an automated migration script:

```bash
# Run migration script
python scripts/migrate_v1_to_v2.py

# This script will:
# 1. Create new v2.0 tables
# 2. Migrate data from mcp_servers → resources
# 3. Migrate data from mcp_tools → capabilities
# 4. Set protocol='mcp' for all migrated resources
# 5. Verify data integrity
```

**Migration Script Output:**
```
🔍 Checking database connection...
✅ Connected to database: sark_db

🔍 Checking current schema version...
✅ Current version: v1.5.0

📦 Creating new v2.0 tables...
✅ Created: resources
✅ Created: capabilities
✅ Created: federation_nodes
✅ Created: cost_tracking
✅ Created: principal_budgets

🔄 Migrating data from mcp_servers to resources...
✅ Migrated 15 servers

🔄 Migrating data from mcp_tools to capabilities...
✅ Migrated 67 tools

🔍 Verifying data integrity...
✅ All resources verified
✅ All capabilities verified

🎉 Migration complete!
   - Resources: 15
   - Capabilities: 67
   - Duration: 2.3s

⚠️  Note: Old tables (mcp_servers, mcp_tools) are preserved for rollback.
   To remove them: ALTER TABLE mcp_servers RENAME TO _deprecated_mcp_servers;
```

### Manual Migration (Alternative)

If you prefer to run migrations manually:

```bash
# Run Alembic migrations
alembic upgrade head

# This runs:
# - 006_add_protocol_adapter_support.py
# - 007_add_federation_support.py
# - 008_add_cost_tracking.py
```

### Verify Migration

```bash
# Connect to database
psql -h localhost -U sark sark_db

# Check resources table
SELECT id, name, protocol FROM resources LIMIT 5;

# Check capabilities table
SELECT id, name, resource_id FROM capabilities LIMIT 5;

# Exit
\q
```

---

## API Changes

### Client Code Migration

**v1.x Python Client:**
```python
import requests

# Register server
response = requests.post(
    "http://sark:8000/api/v1/servers",
    json={
        "name": "filesystem-server",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    },
    headers={"X-API-Key": api_key}
)
server = response.json()
```

**v2.0 Python Client:**
```python
import requests

# Register resource
response = requests.post(
    "http://sark:8000/api/v2/resources",
    json={
        "protocol": "mcp",
        "discovery_config": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"]
        },
        "sensitivity_level": "high"
    },
    headers={"X-API-Key": api_key}
)
resources = response.json()  # Returns list of resources
```

### Using v2.0 SDK (Recommended)

```python
from sark_sdk import SARKClient

client = SARKClient(
    base_url="http://sark:8000",
    api_key=api_key
)

# Register MCP resource
resource = client.resources.register(
    protocol="mcp",
    discovery_config={
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
)

# Register HTTP resource (new in v2.0!)
api_resource = client.resources.register(
    protocol="http",
    discovery_config={
        "base_url": "https://api.example.com",
        "openapi_spec_url": "https://api.example.com/openapi.json"
    }
)
```

---

## Configuration Changes

### Environment Variables

**New in v2.0:**
```bash
# Federation
FEDERATION_ENABLED=true
FEDERATION_NODE_ID=myorg.com
FEDERATION_LISTEN_ADDRESS=0.0.0.0:8443

# Cost Tracking
COST_TRACKING_ENABLED=true
COST_TRACKING_CURRENCY=USD

# Adapter-specific
MCP_DEFAULT_SENSITIVITY=high
HTTP_DEFAULT_TIMEOUT=30
GRPC_MAX_CONNECTIONS=100
```

**Deprecated:**
```bash
# These still work but are deprecated
MCP_SERVERS_PATH=/etc/sark/servers  # Now: RESOURCES_PATH
MCP_DEFAULT_TRANSPORT=stdio          # Now in discovery_config
```

### Docker Compose

**v1.x docker-compose.yml:**
```yaml
version: '3.8'
services:
  sark:
    image: sark:1.5.0
    environment:
      - DATABASE_URL=postgresql://...
      - OPA_URL=http://opa:8181
```

**v2.0 docker-compose.yml:**
```yaml
version: '3.8'
services:
  sark:
    image: sark:2.0.0
    environment:
      - DATABASE_URL=postgresql://...
      - OPA_URL=http://opa:8181
      # New: Federation (optional)
      - FEDERATION_ENABLED=false
      # New: Cost tracking (optional)
      - COST_TRACKING_ENABLED=false
```

---

## Policy Migration

Most OPA policies work without changes, but there are some updates for new features.

### v1.x Policy

```rego
package grid.base

# Allow developers to access MCP servers
allow if {
    input.principal.role == "developer"
    input.resource.type == "mcp_server"
    input.capability.sensitivity_level in ["low", "medium"]
}
```

### v2.0 Policy (Updated)

```rego
package grid.base

# Allow developers to access any protocol
allow if {
    input.principal.role == "developer"
    # Resource type is now just 'resource', protocol is separate
    input.resource.protocol in ["mcp", "http", "grpc"]
    input.capability.sensitivity_level in ["low", "medium"]
}
```

### New Policy Features in v2.0

**Protocol-based policies:**
```rego
# Allow HTTP requests to public APIs
allow if {
    input.resource.protocol == "http"
    input.resource.metadata.public == true
}
```

**Cost-based policies:**
```rego
# Deny if estimated cost exceeds budget
deny if {
    estimated_cost := cost.estimate(input.capability, input.arguments)
    principal_budget := data.budgets[input.principal.id]
    principal_spent := data.costs.monthly_total(input.principal.id)

    principal_spent + estimated_cost > principal_budget
}
```

**Federation policies:**
```rego
# Allow cross-org access for trusted orgs
allow if {
    input.principal.source_org in data.trusted_orgs
    input.principal.attributes.role == "developer"
}
```

---

## Code Migration

### Custom Integrations

If you have custom code integrating with SARK:

**v1.x: Direct Database Access**
```python
from sark.models.mcp_server import MCPServer

# Query servers
servers = session.query(MCPServer).filter_by(
    sensitivity_level="high"
).all()
```

**v2.0: Use Resources**
```python
from sark.models.base import Resource

# Query resources (any protocol)
resources = session.query(Resource).filter_by(
    sensitivity_level="high",
    protocol="mcp"  # Optional: filter by protocol
).all()
```

### Custom MCP Server Wrappers

**v1.x:**
```python
from sark.services.mcp import MCPService

mcp_service = MCPService()
result = await mcp_service.invoke_tool(
    server_id="filesystem-server",
    tool_name="read_file",
    arguments={"path": "/file.txt"}
)
```

**v2.0:**
```python
from sark.adapters import get_registry
from sark.models.base import InvocationRequest

registry = get_registry()
mcp_adapter = registry.get("mcp")

request = InvocationRequest(
    capability_id="filesystem-server-read_file",
    principal_id="user-123",
    arguments={"path": "/file.txt"}
)

result = await mcp_adapter.invoke(request)
```

---

## Testing Your Migration

### 1. Verify Database

```bash
# Check resource count
psql sark_db -c "SELECT COUNT(*) FROM resources;"

# Check capability count
psql sark_db -c "SELECT COUNT(*) FROM capabilities;"

# Check protocol distribution
psql sark_db -c "SELECT protocol, COUNT(*) FROM resources GROUP BY protocol;"
```

### 2. Test API Endpoints

```bash
# List resources (should return migrated MCP servers)
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v2/resources

# Get specific resource
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v2/resources/filesystem-server

# Test v1 backward compat
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/servers
```

### 3. Test Authorization Flow

```bash
# Authorize and execute capability
curl -X POST http://localhost:8000/api/v2/authorize \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_id": "filesystem-server-read_file",
    "principal_id": "user-123",
    "arguments": {"path": "/test.txt"}
  }'
```

### 4. Verify Policies

```bash
# Test policy evaluation
curl -X POST http://localhost:8000/api/v2/policies/test \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "rego_code": "package grid.test\nallow if { input.principal.role == \"developer\" }",
    "input": {
      "principal": {"role": "developer"},
      "resource": {"protocol": "mcp"},
      "capability": {"name": "read_file"}
    }
  }'
```

### 5. Check Audit Logs

```bash
# Verify audit logs still work
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/v2/audit/logs?page=1&page_size=10"
```

---

## Rollback Plan

If you encounter issues, you can rollback:

### Quick Rollback (Docker)

```bash
# Stop v2.0
docker-compose down

# Restore database
dropdb sark_db
createdb sark_db
psql sark_db < sark_v1_backup.sql

# Return to v1.x
git checkout v1.5.0
docker-compose up -d
```

### Partial Rollback (Keep Data)

If you want to rollback but preserve some v2.0 data:

```bash
# The migration script preserves old tables
# You can still query them:
SELECT * FROM mcp_servers;  # Original v1.x data
SELECT * FROM resources;     # Migrated v2.0 data
```

---

## FAQ

### Q: Do I need to migrate if I'm a new user?

**A:** No! Just install v2.0 directly. The migration guide is only for users with existing v1.x deployments.

### Q: Will my existing policies work?

**A:** Most policies work as-is. You may need to update policies that specifically reference `mcp_server` type to use `resource.protocol == "mcp"` instead.

### Q: Can I run v1.x and v2.0 in parallel?

**A:** Not recommended. They share the same database schema. Use separate databases if you need both versions.

### Q: What happens to my audit logs?

**A:** Audit logs are preserved and unchanged. They continue to work in v2.0.

### Q: Do I need to re-register all my MCP servers?

**A:** No. The migration script automatically converts them to resources with `protocol="mcp"`.

### Q: Can I use new features (HTTP, gRPC) immediately after migration?

**A:** Yes! Once migrated to v2.0, you can register HTTP and gRPC resources alongside your existing MCP resources.

### Q: What about custom code that uses `MCPServer` model?

**A:** You'll need to update it to use `Resource` model with `protocol="mcp"` filter. The migration script provides a helper for this.

### Q: How long does migration take?

**A:** Typically 1-5 minutes for the database migration, plus time to update client code and test. Total: 2-4 hours for a typical deployment.

### Q: Is there a migration checklist?

**A:** Yes! See below.

---

## Migration Checklist

### Pre-Migration

- [ ] Read this guide completely
- [ ] Backup database: `pg_dump sark_db > backup.sql`
- [ ] Backup configuration files
- [ ] Document current API integrations
- [ ] Test migration in staging environment

### Migration

- [ ] Stop SARK v1.x: `docker-compose down`
- [ ] Update to v2.0: `git checkout v2.0.0`
- [ ] Run migration script: `python scripts/migrate_v1_to_v2.py`
- [ ] Verify database schema: Check resources and capabilities tables
- [ ] Update configuration: Add new v2.0 config options
- [ ] Update docker-compose.yml
- [ ] Start SARK v2.0: `docker-compose up -d`

### Post-Migration

- [ ] Verify API endpoints work
- [ ] Test authorization flow
- [ ] Check audit logs
- [ ] Update client code
- [ ] Update policies (if needed)
- [ ] Test all integrations
- [ ] Monitor logs for errors
- [ ] Update documentation

### Optional: Enable New Features

- [ ] Configure federation (if needed)
- [ ] Enable cost tracking (if needed)
- [ ] Register HTTP/gRPC resources (if needed)

---

## Getting Help

If you encounter issues during migration:

1. **Check logs:** `docker-compose logs sark`
2. **Consult documentation:** https://docs.sark.dev/migration
3. **GitHub Issues:** https://github.com/yourusername/sark/issues
4. **Discord:** https://discord.gg/sark (channel: #migration-help)
5. **Email:** support@sark.dev

---

## Next Steps

After successful migration:

1. **Explore new features:**
   - Register HTTP APIs using OpenAPI specs
   - Set up gRPC service governance
   - Enable cost tracking for budget management

2. **Review policies:**
   - Update policies to use new v2.0 features
   - Add protocol-specific policies
   - Implement cost-based policies

3. **Consider federation:**
   - If working with partners, set up cross-org federation
   - Configure trusted nodes and mTLS

4. **Update monitoring:**
   - New metrics available in v2.0
   - Enhanced dashboards for multi-protocol monitoring

---

**Document Version:** 1.0
**Last Updated:** December 2025
**Maintainer:** SARK Core Team
