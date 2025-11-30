# SARK v2.0 Troubleshooting Guide

**Last Updated:** November 2024
**Version:** 2.0.0
**Audience:** Developers, DevOps, System Administrators

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation and Setup Issues](#installation-and-setup-issues)
3. [Adapter Problems](#adapter-problems)
4. [Policy and Authorization Issues](#policy-and-authorization-issues)
5. [Federation Problems](#federation-problems)
6. [Performance Issues](#performance-issues)
7. [Database and Migration Issues](#database-and-migration-issues)
8. [Logging and Debugging](#logging-and-debugging)
9. [Common Error Messages](#common-error-messages)
10. [FAQ](#faq)

---

## Quick Diagnostics

Before diving into specific issues, run these quick diagnostics:

### Health Check

```bash
# Check SARK API health
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "version": "2.0.0",
  "adapters": {
    "mcp": "ready",
    "http": "ready",
    "grpc": "ready"
  },
  "database": "connected",
  "federation": "enabled"
}
```

### Check Logs

```bash
# View recent logs
docker-compose logs --tail=100 sark

# Follow logs in real-time
docker-compose logs -f sark

# Filter for errors only
docker-compose logs sark | grep ERROR
```

### Verify Database Connection

```bash
# Check PostgreSQL
psql -h localhost -U sark -d sark_db -c "SELECT version();"

# Check TimescaleDB (audit log)
psql -h localhost -U sark -d sark_audit -c "SELECT count(*) FROM audit_events;"
```

### Test Adapter Registration

```bash
# List registered adapters
curl http://localhost:8000/api/v2/adapters

# Expected response
{
  "adapters": [
    {"protocol": "mcp", "version": "2024-11-05", "status": "ready"},
    {"protocol": "http", "version": "1.1", "status": "ready"},
    {"protocol": "grpc", "version": "1.0", "status": "ready"}
  ]
}
```

---

## Installation and Setup Issues

### Issue: `pip install` fails with dependency conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
ERROR: Cannot install sark because these package versions have conflicting dependencies
```

**Solutions:**

1. **Use a clean virtual environment:**
```bash
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

2. **Install with `--no-deps` and resolve manually:**
```bash
pip install --no-deps -e .
pip install -r requirements.txt
```

3. **Check Python version:**
```bash
python --version  # Should be 3.11 or higher
```

---

### Issue: Docker containers won't start

**Symptoms:**
```
ERROR: Cannot start service sark: driver failed programming external connectivity
```

**Solutions:**

1. **Check port conflicts:**
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill the process or change SARK_PORT in .env
```

2. **Verify Docker and Docker Compose versions:**
```bash
docker --version      # Should be 20.10+
docker-compose --version  # Should be 1.29+ or 2.0+
```

3. **Check Docker daemon status:**
```bash
systemctl status docker

# Restart if needed
sudo systemctl restart docker
```

4. **Clear Docker cache:**
```bash
docker-compose down -v
docker system prune -a
docker-compose up -d --build
```

---

### Issue: Database migrations fail

**Symptoms:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

**Solutions:**

1. **Reset migrations (WARNING: Destroys data):**
```bash
# Drop and recreate database
docker-compose down -v
docker-compose up -d postgres timescaledb
sleep 5
alembic upgrade head
```

2. **Check current migration state:**
```bash
alembic current
alembic history
```

3. **Manually fix migration chain:**
```bash
# Stamp database at specific revision
alembic stamp head

# Or downgrade and re-upgrade
alembic downgrade -1
alembic upgrade head
```

4. **Verify database exists:**
```bash
psql -h localhost -U sark -c "\l" | grep sark
```

---

## Adapter Problems

### Issue: MCP adapter fails to discover resources

**Symptoms:**
```json
{
  "error": "DiscoveryError: Failed to start MCP server",
  "details": "Command 'npx' not found"
}
```

**Solutions:**

1. **Verify Node.js and npm are installed:**
```bash
node --version   # Should be 18+
npx --version
```

2. **Test MCP server manually:**
```bash
npx -y @modelcontextprotocol/server-filesystem /tmp
# Should start without errors
```

3. **Check MCP server logs:**
```bash
# Enable debug logging for MCP adapter
export SARK_LOG_LEVEL=DEBUG
docker-compose restart sark
docker-compose logs -f sark | grep mcp
```

4. **Verify discovery config:**
```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "mcp",
    "discovery_config": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {}  # Add any required environment variables
    }
  }'
```

---

### Issue: HTTP adapter can't parse OpenAPI spec

**Symptoms:**
```json
{
  "error": "DiscoveryError: Failed to parse OpenAPI spec",
  "details": "Invalid OpenAPI version: 2.0"
}
```

**Solutions:**

1. **Verify OpenAPI spec is valid:**
```bash
# Download and validate the spec
curl https://api.example.com/openapi.json > spec.json
npx @apidevtools/swagger-cli validate spec.json
```

2. **Check OpenAPI version compatibility:**
```python
# SARK supports OpenAPI 3.0+
# Convert OpenAPI 2.0 (Swagger) to 3.0:
npx swagger2openapi spec-v2.json > spec-v3.json
```

3. **Use direct endpoint discovery (without OpenAPI):**
```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "http",
    "discovery_config": {
      "base_url": "https://api.example.com",
      "manual_capabilities": [
        {
          "name": "GET /users",
          "method": "GET",
          "path": "/users"
        }
      ]
    }
  }'
```

---

### Issue: gRPC adapter reflection fails

**Symptoms:**
```json
{
  "error": "DiscoveryError: gRPC reflection not supported by server"
}
```

**Solutions:**

1. **Verify gRPC server has reflection enabled:**
```bash
# Test with grpcurl
grpcurl -plaintext localhost:50051 list

# If reflection is disabled, use .proto files instead
```

2. **Use proto file discovery:**
```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "grpc",
    "discovery_config": {
      "endpoint": "localhost:50051",
      "reflection": false,
      "proto_files": ["/path/to/service.proto"]
    }
  }'
```

3. **Check TLS/SSL configuration:**
```bash
# For secure gRPC connections
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "grpc",
    "discovery_config": {
      "endpoint": "grpc.example.com:443",
      "tls": true,
      "server_name": "grpc.example.com"
    }
  }'
```

---

### Issue: Custom adapter not loading

**Symptoms:**
```
AdapterNotFoundError: Protocol 'myprotocol' not supported
```

**Solutions:**

1. **Verify adapter is registered:**
```python
# In src/sark/adapters/__init__.py
from sark.adapters.my_adapter import MyAdapter

__all__ = ["MyAdapter", ...]
```

```python
# In src/sark/adapters/registry.py
from sark.adapters.my_adapter import MyAdapter

def initialize_default_adapters():
    registry = AdapterRegistry()
    registry.register(MyAdapter())  # Add this line
    return registry
```

2. **Check adapter implementation:**
```bash
# Test adapter directly
python -c "
from sark.adapters.my_adapter import MyAdapter
adapter = MyAdapter()
print(f'Protocol: {adapter.protocol_name}')
print(f'Version: {adapter.protocol_version}')
"
```

3. **Verify adapter passes contract tests:**
```bash
pytest tests/adapters/test_my_adapter.py -v
```

---

## Policy and Authorization Issues

### Issue: All requests are denied

**Symptoms:**
```json
{
  "success": false,
  "error": "Authorization denied: No matching policy"
}
```

**Solutions:**

1. **Check if policies are loaded:**
```bash
curl http://localhost:8000/api/v1/policies

# Should return list of policies
```

2. **Test policy evaluation manually:**
```bash
curl -X POST http://localhost:8000/api/v1/policies/test \
  -H "Content-Type: application/json" \
  -d '{
    "policy_name": "my-policy",
    "input": {
      "principal": {"id": "user-1", "name": "Alice"},
      "resource": {"id": "res-1", "protocol": "mcp"},
      "capability": {"id": "cap-1", "name": "read_file"},
      "action": "execute"
    }
  }'
```

3. **Check OPA syntax errors:**
```bash
# Validate Rego policy
opa check policy.rego

# Test policy with sample input
opa eval -d policy.rego -i input.json 'data.sark.policies.allow'
```

4. **Enable policy debugging:**
```bash
# Add to your policy
package sark.policies

import future.keywords.if

# Debug: Print input
debug_input := input

allow if {
    # Your policy rules
    trace(sprintf("Evaluating: principal=%s, resource=%s",
                  [input.principal.id, input.resource.id]))
    # ... rest of policy
}
```

---

### Issue: Policy changes not taking effect

**Symptoms:**
Policy updated via API, but authorization decisions unchanged.

**Solutions:**

1. **Check policy cache TTL:**
```bash
# Policies are cached for performance
# Force reload by restarting SARK
docker-compose restart sark
```

2. **Verify policy was actually updated:**
```bash
# Get current policy
curl http://localhost:8000/api/v1/policies/my-policy

# Check version/timestamp
```

3. **Clear policy cache:**
```bash
curl -X POST http://localhost:8000/api/v1/policies/reload
```

---

## Federation Problems

### Issue: Federation nodes can't connect

**Symptoms:**
```
FederationError: Connection refused to sark.partner.com:8443
```

**Solutions:**

1. **Verify network connectivity:**
```bash
# Can you reach the remote node?
ping sark.partner.com

# Is the federation port open?
telnet sark.partner.com 8443

# Test with curl
curl -k https://sark.partner.com:8443/api/v2/federation/health
```

2. **Check firewall rules:**
```bash
# Ensure port 8443 is open
sudo ufw status
sudo ufw allow 8443/tcp

# Or for specific IP
sudo ufw allow from 10.1.2.3 to any port 8443
```

3. **Verify DNS resolution:**
```bash
# Can you resolve the remote node's domain?
dig sark.partner.com

# Check /etc/hosts for local testing
cat /etc/hosts | grep sark
```

---

### Issue: mTLS handshake fails

**Symptoms:**
```
SSLError: certificate verify failed: self signed certificate in certificate chain
```

**Solutions:**

1. **Verify certificates are valid:**
```bash
# Check certificate expiration
openssl x509 -in node.crt -noout -dates

# Verify certificate chain
openssl verify -CAfile ca.crt node.crt
```

2. **Check certificate SAN (Subject Alternative Name):**
```bash
openssl x509 -in node.crt -noout -text | grep -A1 "Subject Alternative Name"

# Should include the node's domain
# DNS:sark.example.com
```

3. **Verify trust anchors are configured:**
```yaml
# federation.yaml
federation:
  trust_anchors:
    - name: "partner.com"
      ca_file: "/certs/partner-ca.crt"  # Must exist and be readable
```

4. **Test mTLS manually:**
```bash
openssl s_client \
  -connect sark.partner.com:8443 \
  -cert my-node.crt \
  -key my-node.key \
  -CAfile partner-ca.crt \
  -showcerts
```

---

### Issue: Cross-org requests always denied

**Symptoms:**
```json
{
  "decision": "deny",
  "reason": "Cross-org access not permitted"
}
```

**Solutions:**

1. **Check cross-org policy:**
```rego
# Policy MUST explicitly allow cross-org access
package sark.policies.federation

allow if {
    input.principal.source_org != input.resource.owner_org
    # Add your cross-org rules here
    input.principal.attributes.trusted == true
}
```

2. **Verify principal attributes include org:**
```bash
curl http://localhost:8000/api/v1/principals/user-1

# Should have source_org attribute
{
  "id": "user-1",
  "source_org": "acme.com",
  "attributes": {...}
}
```

3. **Check audit logs for denial reason:**
```bash
curl "http://localhost:8000/api/v1/audit-log?decision=deny&limit=10"
```

---

## Performance Issues

### Issue: Slow adapter invocations

**Symptoms:**
Invocations taking >5 seconds, timeouts occurring.

**Solutions:**

1. **Check adapter-specific timeouts:**
```python
# In your adapter
class MyAdapter(ProtocolAdapter):
    DEFAULT_TIMEOUT = 30.0  # Increase if needed

    async def invoke(self, request):
        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT):
            # ...
```

2. **Enable connection pooling:**
```python
# For HTTP adapters
class HTTPAdapter(ProtocolAdapter):
    def __init__(self):
        self._http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )
```

3. **Monitor database performance:**
```bash
# Check slow queries
psql -h localhost -U sark -d sark_db -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"
```

4. **Add database indexes:**
```sql
-- Common indexes for performance
CREATE INDEX idx_resources_protocol ON resources(protocol);
CREATE INDEX idx_capabilities_resource_id ON capabilities(resource_id);
CREATE INDEX idx_audit_principal_timestamp ON audit_events(principal_id, timestamp);
```

---

### Issue: High memory usage

**Symptoms:**
```
MemoryError: Cannot allocate memory
```

**Solutions:**

1. **Check for memory leaks in adapters:**
```python
# Ensure proper cleanup
async def on_resource_unregistered(self, resource):
    # Clean up cached data
    if resource.id in self._cache:
        del self._cache[resource.id]

    # Close connections
    if resource.id in self._connections:
        await self._connections[resource.id].close()
        del self._connections[resource.id]
```

2. **Limit cache sizes:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)  # Limit cache size
def get_capability(capability_id: str):
    # ...
```

3. **Monitor memory usage:**
```bash
# Check container memory
docker stats sark

# Limit memory if needed
# In docker-compose.yml:
services:
  sark:
    mem_limit: 2g
    memswap_limit: 2g
```

---

## Database and Migration Issues

### Issue: Migration `007_multi_protocol_support` fails

**Symptoms:**
```
alembic.runtime.migration.MigrationError: Can't ALTER TABLE
```

**Solutions:**

1. **Check database permissions:**
```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE sark_db TO sark;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sark;
```

2. **Run migration with verbose output:**
```bash
alembic upgrade head --sql  # Show SQL only, don't execute
alembic upgrade head -x verbose=true
```

3. **Manual migration (last resort):**
```bash
# Export schema changes
alembic upgrade head --sql > migration.sql

# Edit migration.sql to fix issues

# Apply manually
psql -h localhost -U sark -d sark_db -f migration.sql
```

---

### Issue: Audit log queries are slow

**Symptoms:**
Queries to `/api/v1/audit-log` taking >30 seconds.

**Solutions:**

1. **Ensure TimescaleDB hypertables are created:**
```sql
-- Check if hypertable exists
SELECT * FROM timescaledb_information.hypertables;

-- Create if missing
SELECT create_hypertable('audit_events', 'timestamp');
```

2. **Add time-based indexes:**
```sql
CREATE INDEX idx_audit_timestamp_desc ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_principal_time ON audit_events(principal_id, timestamp DESC);
```

3. **Enable data retention policy:**
```sql
-- Automatically drop data older than 90 days
SELECT add_retention_policy('audit_events', INTERVAL '90 days');
```

4. **Use time-range queries:**
```bash
# Always specify time range for better performance
curl "http://localhost:8000/api/v1/audit-log?since=2024-11-01&until=2024-11-30"
```

---

## Logging and Debugging

### Enable Debug Logging

```bash
# Environment variable
export SARK_LOG_LEVEL=DEBUG

# Or in .env file
SARK_LOG_LEVEL=DEBUG

# Restart SARK
docker-compose restart sark
```

### Structured Logging with Filters

```bash
# Filter logs by adapter
docker-compose logs sark | grep "adapter=mcp"

# Filter by principal
docker-compose logs sark | grep "principal_id=user-1"

# Filter by error level
docker-compose logs sark | grep "level=error"
```

### Enable Request Tracing

```python
# Add to main.py
import logging
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        client=request.client.host
    )
    response = await call_next(request)
    logger.info(
        "request_completed",
        status_code=response.status_code
    )
    return response
```

---

## Common Error Messages

### `AdapterConfigurationError: Missing required field`

**Cause:** Discovery config is incomplete.

**Fix:** Check adapter documentation for required fields:
```bash
# MCP requires: transport, command, args
# HTTP requires: base_url
# gRPC requires: endpoint
```

---

### `PolicyEvaluationError: Undefined reference`

**Cause:** Rego policy references undefined data.

**Fix:**
```rego
# Always check if data exists
allow if {
    # Bad: data.principals[input.principal.id].role == "admin"

    # Good:
    principal_data := data.principals[input.principal.id]
    principal_data  # Ensure it exists
    principal_data.role == "admin"
}
```

---

### `ResourceNotFoundError: Resource 'xyz' not found`

**Cause:** Resource was deleted or never registered.

**Fix:**
```bash
# List all resources
curl http://localhost:8000/api/v2/resources

# Re-register if needed
curl -X POST http://localhost:8000/api/v2/resources -d '{...}'
```

---

## FAQ

### Q: Can I use SARK v2.0 with v1.x policies?

**A:** Mostly yes, but you may need to update policies to account for new fields like `protocol` and `source_org`.

```rego
# v1.x policy
allow if {
    input.principal.name == "Alice"
}

# v2.0 policy (add protocol awareness)
allow if {
    input.principal.name == "Alice"
    input.resource.protocol == "mcp"  # New field
}
```

---

### Q: How do I migrate from v1.x to v2.0?

**A:** Run the migration script:

```bash
# Backup v1.x database first!
pg_dump sark_db > backup-v1.sql

# Run migration
python scripts/migrate_v1_to_v2.py

# Verify migration
python scripts/verify_migration.py
```

---

### Q: Can I disable certain adapters?

**A:** Yes, configure which adapters to load:

```yaml
# config.yaml
adapters:
  enabled:
    - mcp
    - http
    # Omit 'grpc' to disable it
```

---

### Q: How do I debug policy evaluation?

**A:** Use the policy test endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/policies/test \
  -H "Content-Type: application/json" \
  -d '{
    "policy_name": "my-policy",
    "input": {...},
    "debug": true  # Enable debug output
  }'
```

---

### Q: Can SARK run without Docker?

**A:** Yes, but you need to manually set up dependencies:

```bash
# Install PostgreSQL and TimescaleDB locally
sudo apt-get install postgresql-15 timescaledb

# Configure connection in .env
POSTGRES_HOST=localhost

# Run SARK
uvicorn sark.main:app --host 0.0.0.0 --port 8000
```

---

### Q: How do I rotate federation certificates?

**A:** Follow these steps:

1. Generate new certificates
2. Add new CA to trust anchors (both nodes)
3. Update node certificate (one at a time)
4. Remove old CA after grace period (e.g., 30 days)

---

## Getting More Help

### Logs to Collect

When reporting issues, include:

1. **SARK version:** `curl http://localhost:8000/health | jq .version`
2. **Error logs:** `docker-compose logs sark --tail=500`
3. **Configuration:** `.env` (remove secrets!)
4. **Recent audit events:** `curl http://localhost:8000/api/v1/audit-log?limit=10`

### Support Channels

- **GitHub Issues:** https://github.com/your-org/sark/issues
- **Slack:** #sark-support
- **Email:** support@sark.example.com
- **Docs:** https://sark.example.com/docs

### Debug Mode

Run SARK in debug mode for maximum logging:

```bash
export SARK_LOG_LEVEL=DEBUG
export SARK_DEBUG=true
docker-compose up
```

---

**Still stuck?** File an issue with:
- Problem description
- Steps to reproduce
- Expected vs. actual behavior
- Logs and configuration
- SARK version

We're here to help! 🛟
