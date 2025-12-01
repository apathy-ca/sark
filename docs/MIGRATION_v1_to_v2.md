# Migration Guide: SARK v1.x → v2.0

**Document Version**: 1.0
**SARK Version**: v2.0.0
**Last Updated**: November 30, 2025

---

## Overview

This guide helps you migrate from SARK v1.x (MCP-specific) to SARK v2.0 (protocol-agnostic). The good news: **v2.0 is 100% backward compatible** with v1.x code, so you can migrate gradually.

### Migration Strategies

1. **Immediate Upgrade** (Recommended): Upgrade to v2.0, continue using v1.x APIs
2. **Gradual Migration**: Upgrade to v2.0, incrementally adopt new features
3. **Full Migration**: Rewrite integrations to use v2.0 adapter interface

---

## Quick Start (5 Minutes)

### Step 1: Upgrade SARK
```bash
# Backup your database first!
pg_dump sark > sark_v1_backup.sql

# Upgrade SARK
pip install --upgrade sark==2.0.0
```

### Step 2: Run Database Migrations
```bash
# Navigate to your SARK installation
cd /path/to/sark

# Run migrations
alembic upgrade head
```

### Step 3: Update Configuration (Optional)
```python
# config.py or environment variables

# Enable protocol adapters (optional - v1.x works without this)
FEATURE_PROTOCOL_ADAPTERS=true
PROTOCOLS_ENABLED_PROTOCOLS=mcp,http,grpc

# All existing v1.x config continues to work
```

### Step 4: Restart SARK
```bash
# Restart your SARK service
systemctl restart sark

# Or if running directly
uvicorn sark.api.main:app --reload
```

**Done!** Your v1.x code continues to work on v2.0.

---

## Compatibility Matrix

| Feature | v1.x Code | v2.0 Status | Migration Required? |
|---------|-----------|-------------|---------------------|
| MCP Server Discovery | ✅ Works | ✅ Works | ❌ No |
| MCP Tool Invocation | ✅ Works | ✅ Works | ❌ No |
| Policy Enforcement | ✅ Works | ✅ Works | ❌ No |
| API Endpoints | ✅ Works | ✅ Works | ❌ No |
| Database Models | ✅ Works | ✅ Enhanced | ⚠️ Optional |
| Config Settings | ✅ Works | ✅ Enhanced | ⚠️ Optional |
| **NEW: HTTP/gRPC** | ❌ N/A | ✅ Available | ✅ Opt-in |
| **NEW: Federation** | ❌ N/A | ✅ Available | ✅ Opt-in |
| **NEW: Cost Tracking** | ❌ N/A | ✅ Available | ✅ Opt-in |

**Legend**:
- ✅ Fully supported
- ⚠️ Optional enhancement available
- ❌ Not applicable

---

## Migration Scenarios

### Scenario 1: "Just Upgrade" (Zero Code Changes)

**Use Case**: You want bug fixes and performance improvements, but don't need new features yet.

**Steps**:
1. Upgrade SARK: `pip install --upgrade sark==2.0.0`
2. Run migrations: `alembic upgrade head`
3. Restart service
4. Done!

**What You Get**:
- All v1.x functionality preserved
- Performance improvements
- Bug fixes
- Security enhancements
- Foundation for future adoption

**Code Changes**: **ZERO** ✅

---

### Scenario 2: "Add HTTP/REST Support" (Minimal Changes)

**Use Case**: You want to govern HTTP/REST APIs alongside MCP servers.

**Steps**:

#### 1. Enable Protocol Adapters
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing v1.x config...

    # NEW: Enable protocol adapters
    FEATURE_PROTOCOL_ADAPTERS: bool = True
    PROTOCOLS_ENABLED_PROTOCOLS: list = ["mcp", "http"]
```

#### 2. Install HTTP Dependencies (if needed)
```bash
pip install httpx>=0.25.0 pyyaml>=6.0.0
```

#### 3. Use HTTP Adapter
```python
from sark.adapters import get_registry

# Get HTTP adapter
http_adapter = get_registry().get("http")

# Discover HTTP API from OpenAPI spec
resources = await http_adapter.discover_resources({
    "base_url": "https://api.github.com",
    "openapi_spec_url": "https://api.github.com/openapi.json",
    "auth_config": {
        "type": "bearer",
        "token": "your-github-token"
    }
})

# Get capabilities (API endpoints)
capabilities = await http_adapter.get_capabilities(resources[0])
```

**Existing MCP Code**: Continues to work unchanged! ✅

---

### Scenario 3: "Migrate MCP to Adapter Interface" (Recommended)

**Use Case**: You want to use the new adapter interface for consistency across protocols.

#### Before (v1.x):
```python
from sark.models.mcp_server import MCPServer
from sark.services.discovery.discovery_service import DiscoveryService

# Old way
discovery = DiscoveryService(db)
server = await discovery.discover_mcp_server({
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem"]
})

tools = await server.list_tools()
result = await server.invoke_tool(tool_name, arguments)
```

#### After (v2.0):
```python
from sark.adapters import get_registry

# New way
mcp_adapter = get_registry().get("mcp")

# Discovery
resources = await mcp_adapter.discover_resources({
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem"]
})

# Get capabilities
capabilities = await mcp_adapter.get_capabilities(resources[0])

# Invocation
from sark.models.base import InvocationRequest

request = InvocationRequest(
    capability_id=capabilities[0].id,
    principal_id="user-123",
    arguments={"path": "/etc/hosts"}
)

result = await mcp_adapter.invoke(request)
```

**Benefits**:
- Consistent interface across all protocols
- Better type safety
- Easier testing with adapter mocks
- Future-proof for new protocols

---

### Scenario 4: "Enable Cost Tracking" (New Feature)

**Use Case**: You want to track and control AI costs.

#### 1. Enable Cost Attribution
```python
# config.py
FEATURE_COST_ATTRIBUTION: bool = True
```

#### 2. Set Budgets
```python
from sark.models.cost_attribution import CostAttributionService

cost_service = CostAttributionService(db)

# Set budget for a user
await cost_service.set_budget(
    principal_id="user-123",
    daily_budget=Decimal("10.00"),
    monthly_budget=Decimal("100.00")
)
```

#### 3. Track Costs
```python
from sark.services.cost.providers.openai import OpenAICostEstimator

estimator = OpenAICostEstimator()

# Estimate before invocation
estimate = await estimator.estimate_cost(
    request,
    metadata={"model": "gpt-4-turbo"}
)

# Check budget
allowed, reason = await cost_service.check_budget(
    principal_id="user-123",
    estimated_cost=estimate.total_cost
)

if not allowed:
    raise BudgetExceededError(reason)

# After invocation, record actual cost
await cost_service.record_cost(
    principal_id="user-123",
    resource_id=resource.id,
    capability_id=capability.id,
    cost=actual_cost,
    usage_data={"tokens": 1500}
)
```

---

### Scenario 5: "Enable Federation" (Advanced)

**Use Case**: Multi-tenant platform or cross-org resource sharing.

#### 1. Set Up Trust Relationship
```python
from sark.services.federation.trust import TrustManager

trust_mgr = TrustManager(db)

# Establish trust with partner org
await trust_mgr.establish_trust(
    partner_org_id="partner-corp",
    trust_level="full",
    mtle_cert_path="/path/to/partner-cert.pem",
    allowed_protocols=["mcp", "http", "grpc"]
)
```

#### 2. Discover Federated Resources
```python
from sark.services.federation import FederationService

federation = FederationService(db)

# Discover resources from partner
resources = await federation.discover_federated_resources(
    partner_org_id="partner-corp"
)
```

#### 3. Invoke Federated Capabilities
```python
result = await federation.invoke_federated_capability(
    capability_id="partner-resource-tool",
    organization_id="partner-corp",
    principal_id="user@myorg.com",
    arguments={"key": "value"}
)
```

---

## Database Migration Details

### Schema Changes

**New Tables** (all optional, backward compatible):
- `adapter_registrations` - Protocol adapter registry
- `federated_resources` - Cross-org resource cache
- `federation_trusts` - Org trust relationships
- `cost_tracking` - Cost attribution records (hypertable)
- `principal_budgets` - Budget limits

**Modified Tables**:
- `resources` - Added `protocol` field (defaults to "mcp" for v1.x)
- `capabilities` - Added `sensitivity_level` enum
- `invocations` - Added `cost` tracking fields

### Migration Commands

```bash
# Check current version
alembic current

# Show pending migrations
alembic heads

# Upgrade to v2.0
alembic upgrade head

# If issues, rollback
alembic downgrade -1
```

### Rollback Plan

If you need to rollback to v1.x:

```bash
# Rollback database
alembic downgrade <v1.x-revision>

# Downgrade package
pip install sark==1.1.0

# Restore backup if needed
psql sark < sark_v1_backup.sql
```

---

## API Changes

### Deprecated APIs (Still Work in v2.0)

None! All v1.x APIs continue to work.

### New APIs

#### Protocol Adapters
```python
from sark.adapters import get_registry

# Get any adapter
adapter = get_registry().get("mcp")  # or "http", "grpc"
```

#### Cost Tracking
```python
from sark.models.cost_attribution import CostAttributionService
cost_service = CostAttributionService(db)
```

#### Federation
```python
from sark.services.federation import FederationService
federation = FederationService(db)
```

#### Policy Plugins
```python
from sark.services.policy.plugins import PolicyPluginManager
plugin_mgr = PolicyPluginManager()
```

---

## Configuration Changes

### v1.x Config (Still Valid)
```python
# All v1.x environment variables work
DATABASE_URL=postgresql://...
POLICY_OPA_URL=http://localhost:8181
MCP_SERVER_DISCOVERY_ENABLED=true
```

### v2.0 New Config (Optional)
```python
# Feature flags
FEATURE_PROTOCOL_ADAPTERS=true
FEATURE_COST_ATTRIBUTION=true
FEATURE_FEDERATION=true

# Protocol config
PROTOCOLS_ENABLED_PROTOCOLS=mcp,http,grpc

# Adapter-specific
HTTP_ADAPTER_RATE_LIMIT=10.0
GRPC_ADAPTER_POOL_SIZE=10
```

---

## Testing Your Migration

### Step 1: Integration Tests
```bash
# Run existing v1.x tests (should all pass)
pytest tests/ -m "not v2"

# Run v2.0 tests
pytest tests/ -m "v2"

# Run all tests
pytest tests/ -v
```

### Step 2: Smoke Tests

#### Test MCP (v1.x compatibility)
```bash
# Should work exactly as before
curl http://localhost:8000/api/servers
curl http://localhost:8000/api/tools
```

#### Test New Adapters
```bash
# Test adapter registry
curl http://localhost:8000/api/v2/adapters

# Should show: mcp, http, grpc (if enabled)
```

### Step 3: Performance Tests

```bash
# Benchmark v2.0 performance
pytest tests/performance/ -v

# Should meet or exceed v1.x performance
```

---

## Common Issues & Solutions

### Issue: "Adapter not found"

**Problem**: `get_registry().get("http")` returns `None`

**Solution**:
```python
# Enable protocol adapters in config
FEATURE_PROTOCOL_ADAPTERS=true
PROTOCOLS_ENABLED_PROTOCOLS=mcp,http,grpc
```

### Issue: "Migration fails on cost_tracking table"

**Problem**: TimescaleDB extension not installed

**Solution**:
```bash
# Install TimescaleDB extension
sudo apt install timescaledb-postgresql-14

# Enable in PostgreSQL
psql sark -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Retry migration
alembic upgrade head
```

### Issue: "Tests failing after upgrade"

**Problem**: Mock objects don't match new adapter interface

**Solution**:
```python
# Update tests to use adapter interface
from sark.adapters import get_registry

# Old
mock_server = Mock(spec=MCPServer)

# New
mock_adapter = Mock(spec=ProtocolAdapter)
```

### Issue: "Performance degradation"

**Problem**: Adapter overhead slowing requests

**Solution**:
1. Enable capability caching:
   ```python
   ADAPTER_CACHE_ENABLED=true
   ADAPTER_CACHE_TTL=300  # 5 minutes
   ```

2. Use connection pooling:
   ```python
   HTTP_ADAPTER_POOL_SIZE=100
   GRPC_ADAPTER_POOL_SIZE=10
   ```

---

## Gradual Migration Timeline

### Phase 1: Upgrade (Week 1)
- [x] Backup database
- [x] Upgrade to v2.0
- [x] Run migrations
- [x] Verify v1.x functionality
- [x] Monitor for issues

### Phase 2: New Protocols (Week 2-3)
- [ ] Enable protocol adapters
- [ ] Add HTTP adapter for REST APIs
- [ ] Add gRPC adapter if needed
- [ ] Test new integrations

### Phase 3: Advanced Features (Week 4-6)
- [ ] Enable cost attribution
- [ ] Set budgets for principals
- [ ] Create custom policy plugins
- [ ] Enable federation if needed

### Phase 4: Code Migration (Week 7+)
- [ ] Migrate MCP code to adapter interface
- [ ] Refactor for consistency
- [ ] Update tests
- [ ] Documentation updates

---

## Best Practices

### DO ✅
- Backup database before upgrading
- Test in staging environment first
- Enable features incrementally
- Monitor performance after upgrade
- Keep v1.x and v2.0 code in sync during transition
- Use adapter interface for new code

### DON'T ❌
- Skip database backup
- Enable all features at once in production
- Mix v1.x and v2.0 patterns in same module
- Ignore performance monitoring
- Forget to update documentation

---

## Getting Help

### Resources
- **Release Notes**: `RELEASE_NOTES_v2.0.0.md`
- **API Docs**: `docs/api/v2/API_REFERENCE.md`
- **Tutorials**: `docs/tutorials/`
- **Examples**: `examples/`

### Support Channels
- **GitHub Issues**: Report bugs
- **GitHub Discussions**: Ask questions
- **Documentation**: https://sark.dev/docs/v2.0

---

## Success Checklist

Before declaring migration complete:

- [ ] Database migrated successfully
- [ ] All v1.x functionality works
- [ ] New features tested (if enabled)
- [ ] Integration tests passing
- [ ] Performance metrics acceptable
- [ ] Documentation updated
- [ ] Team trained on new features
- [ ] Rollback plan tested
- [ ] Production deployment successful
- [ ] Monitoring in place

---

## Conclusion

SARK v2.0 migration is designed to be **safe, gradual, and backward compatible**. You can upgrade immediately and adopt new features at your own pace.

**Questions?** Open a GitHub discussion or issue.

**Happy Migrating!** 🚀

---

**Version**: 1.0
**SARK Version**: v2.0.0
**Last Updated**: November 30, 2025

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
