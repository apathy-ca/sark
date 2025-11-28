# Worker Task Updates for v1.1.0 Release

**Context:** SARK v1.0.0 is production-ready. Gateway integration must be v1.1.0 compliant.

---

## Critical Additions for ALL Workers

### **1. Backwards Compatibility Requirement**

**Rule:** Gateway integration must NOT affect existing v1.0.0 functionality.

**Implementation:**
- Gateway features disabled by default (`GATEWAY_ENABLED=false`)
- All new code must check feature flag before execution
- Zero performance impact when disabled
- Existing tests must still pass

---

### **2. Additional Tests Required**

All workers add backwards compatibility tests:

```python
def test_gateway_disabled_has_no_impact():
    """Verify Gateway disabled = v1.0.0 behavior."""
    # When GATEWAY_ENABLED=false
    # System behaves identically to v1.0.0
```

---

## Worker-Specific Updates

### **Engineer 1: Gateway Client & Infrastructure**

**Additional Tasks (2-3 hours):**

#### Task 1A: Feature Flag Guards
```python
# In src/sark/services/gateway/client.py

class GatewayClient:
    def __init__(self, ...):
        settings = get_settings()

        # CRITICAL: Check feature flag first
        if not settings.gateway_enabled:
            logger.info("Gateway integration disabled")
            self._enabled = False
            return

        self._enabled = True
        # ... rest of initialization
```

#### Task 1B: Lazy Initialization
```python
# In src/sark/api/dependencies.py

async def get_gateway_client() -> GatewayClient | None:
    """Get Gateway client (None if disabled)."""
    settings = get_settings()

    if not settings.gateway_enabled:
        return None  # Don't even create client

    # ... create client
```

#### Task 1C: Backwards Compatibility Tests
**File:** `tests/compatibility/test_gateway_client.py`

```python
def test_gateway_client_not_initialized_when_disabled():
    """Verify client doesn't initialize when disabled."""
    with patch.dict(os.environ, {"GATEWAY_ENABLED": "false"}):
        client = GatewayClient()
        assert client._enabled is False

def test_zero_overhead_when_disabled():
    """Verify no performance impact when disabled."""
    # Benchmark with GATEWAY_ENABLED=false
    # Should be identical to not having Gateway code
```

**Updated Deliverables:**
- [ ] Feature flag checks in all Gateway client methods
- [ ] Lazy initialization (only when enabled)
- [ ] Backwards compatibility tests (+3 tests)

---

### **Engineer 2: Authorization API Endpoints**

**Additional Tasks (2-3 hours):**

#### Task 2A: Version Endpoint
**File:** `src/sark/api/routers/health.py` (modify existing file)

```python
from sark import __version__

@router.get("/version")
async def get_version() -> dict:
    """Get SARK version and feature status."""
    settings = get_settings()

    return {
        "version": __version__,  # "1.1.0"
        "major": 1,
        "minor": 1,
        "patch": 0,
        "release": "stable",
        "features": {
            "gateway_integration": settings.gateway_enabled,
            "a2a_authorization": settings.a2a_enabled,
        },
        "compatibility": {
            "api_version": "v1",
            "min_client_version": "1.0.0",
        }
    }
```

#### Task 2B: Feature-Disabled Responses
```python
# In src/sark/api/routers/gateway.py

@router.post("/authorize")
async def authorize_gateway_operation(...):
    settings = get_settings()

    if not settings.gateway_enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "feature_disabled",
                "message": "Gateway integration is not enabled",
                "enable": "Set GATEWAY_ENABLED=true to enable this feature",
                "version": "1.1.0",
                "feature": "gateway_integration"
            }
        )

    # ... rest of endpoint
```

#### Task 2C: Backwards Compatibility Tests
**File:** `tests/compatibility/test_existing_endpoints.py`

```python
def test_existing_auth_endpoints_unchanged():
    """Verify v1.0.0 auth endpoints work identically."""
    # Test /api/v1/auth/login
    # Test /api/v1/auth/refresh
    # All must work exactly as v1.0.0

def test_gateway_endpoints_return_503_when_disabled():
    """Verify Gateway endpoints return 503 when disabled."""
    response = client.post("/api/v1/gateway/authorize", ...)
    assert response.status_code == 503
    assert response.json()["error"] == "feature_disabled"
```

**Updated Deliverables:**
- [ ] `/version` endpoint showing feature flags
- [ ] 503 responses when Gateway disabled
- [ ] Backwards compatibility tests (+5 tests)

---

### **Engineer 3: OPA Policies & Policy Service**

**Additional Tasks (1-2 hours):**

#### Task 3A: Policy Namespace Isolation
```rego
# In opa/policies/gateway_authorization.rego

# IMPORTANT: Use separate namespace
package mcp.gateway  # NOT mcp (to avoid conflicts with v1.0.0)

# All Gateway policies under mcp.gateway.*
# Existing v1.0.0 policies under mcp.* remain untouched
```

#### Task 3B: Policy Bundle Versioning
**File:** `opa/bundle/.manifest`

```json
{
  "revision": "v1.1.0",
  "roots": [
    "mcp",
    "mcp.gateway",
    "mcp.gateway.a2a"
  ],
  "metadata": {
    "version": "1.1.0",
    "gateway_policies": "v1.0",
    "backwards_compatible": true
  }
}
```

#### Task 3C: Policy Compatibility Tests
**File:** `opa/policies/compatibility_test.rego`

```rego
package mcp.test

# Test that v1.0.0 policies still work
test_v1_0_0_tool_access {
    # Test existing mcp.allow policy
    # Must work identically to v1.0.0
}

# Test that Gateway policies don't interfere
test_gateway_policies_isolated {
    # Gateway policies in mcp.gateway
    # Don't affect mcp.* policies
}
```

**Updated Deliverables:**
- [ ] Policies in `mcp.gateway.*` namespace
- [ ] Policy bundle versioning
- [ ] Policy compatibility tests (+3 tests)

---

### **Engineer 4: Audit & Monitoring**

**Additional Tasks (2-3 hours):**

#### Task 4A: Conditional Audit Logging
```python
# In src/sark/services/audit/gateway_audit.py

async def log_gateway_event(event: GatewayAuditEvent) -> str | None:
    """Log Gateway event (no-op if Gateway disabled)."""
    settings = get_settings()

    if not settings.gateway_enabled:
        # No-op when disabled - zero overhead
        logger.debug("Gateway disabled, skipping audit event")
        return None

    # ... rest of logging
```

#### Task 4B: Reversible Database Migrations
**File:** `src/sark/db/migrations/XXX_add_gateway_audit.py`

```python
"""Add Gateway audit events table (v1.1.0)."""

revision = 'gateway_v1_1_0'
down_revision = 'v1_0_0_final'  # Last v1.0.0 migration


def upgrade():
    """Add Gateway tables."""
    op.create_table('gateway_audit_events', ...)
    # Mark table as optional/feature-gated
    op.execute("""
        COMMENT ON TABLE gateway_audit_events IS
        'v1.1.0 Gateway integration (GATEWAY_ENABLED=true)';
    """)


def downgrade():
    """Remove Gateway tables for rollback to v1.0.0."""
    op.drop_table('gateway_audit_events')
    # Safe to drop - if rolling back, Gateway wasn't used
```

#### Task 4C: Migration Tests
**File:** `tests/migration/test_v1_1_0_migrations.py`

```python
def test_upgrade_from_v1_0_0():
    """Test upgrading database from v1.0.0 to v1.1.0."""
    # Start with v1.0.0 schema
    # Run: alembic upgrade head
    # Verify gateway_audit_events table exists
    # Verify all v1.0.0 tables intact

def test_downgrade_to_v1_0_0():
    """Test downgrading database from v1.1.0 to v1.0.0."""
    # Start with v1.1.0 schema
    # Run: alembic downgrade -1
    # Verify gateway_audit_events table removed
    # Verify v1.0.0 tables intact
    # Verify v1.0.0 code can run
```

**Updated Deliverables:**
- [ ] Conditional audit logging (no-op when disabled)
- [ ] Reversible database migrations
- [ ] Migration tests (+2 tests)

---

### **QA Worker: Testing & Validation**

**Additional Tasks (4-5 hours):**

#### Task 5A: Backwards Compatibility Test Suite
**File:** `tests/compatibility/test_v1_0_0_compatibility.py`

```python
"""Complete v1.0.0 compatibility test suite."""

class TestBackwardsCompatibility:
    """Verify v1.1.0 maintains v1.0.0 compatibility."""

    def test_default_configuration_is_v1_0_0(self):
        """Default config = v1.0.0 behavior."""
        settings = Settings()
        assert settings.gateway_enabled is False
        assert settings.a2a_enabled is False

    def test_all_v1_0_0_endpoints_work(self):
        """All v1.0.0 endpoints work identically."""
        # Test every v1.0.0 endpoint
        # /api/v1/auth/login
        # /api/v1/auth/refresh
        # /api/v1/policy/evaluate
        # /api/v1/servers/*
        # All must work exactly as v1.0.0

    def test_no_performance_regression(self):
        """v1.1.0 has no performance regression vs v1.0.0."""
        # Benchmark auth flow with GATEWAY_ENABLED=false
        # Must be ≤ v1.0.0 latency
        # Typically within 1-2ms

    def test_gateway_disabled_returns_503(self):
        """Gateway endpoints return 503 when disabled."""
        response = client.post("/api/v1/gateway/authorize")
        assert response.status_code == 503

    def test_existing_tests_still_pass(self):
        """All v1.0.0 tests still pass."""
        # Run existing test suite
        # 100% pass rate required
```

#### Task 5B: Migration Test Suite
**File:** `tests/migration/test_upgrades.py`

```python
"""Test upgrade and downgrade paths."""

class TestMigrations:
    """Test database migrations."""

    def test_upgrade_from_v1_0_0_to_v1_1_0(self):
        """Test clean upgrade path."""
        # 1. Create v1.0.0 database
        # 2. Add v1.0.0 test data
        # 3. Run: alembic upgrade head
        # 4. Verify v1.1.0 schema
        # 5. Verify v1.0.0 data intact
        # 6. Verify new tables exist

    def test_downgrade_from_v1_1_0_to_v1_0_0(self):
        """Test clean downgrade path."""
        # 1. Create v1.1.0 database
        # 2. Run: alembic downgrade -1
        # 3. Verify v1.0.0 schema
        # 4. Verify Gateway tables removed
        # 5. Verify v1.0.0 code can run

    def test_zero_downtime_upgrade(self):
        """Test zero-downtime upgrade."""
        # 1. Start with v1.0.0 running
        # 2. Apply v1.1.0 migrations
        # 3. Verify v1.0.0 continues working
        # 4. Switch to v1.1.0 code
        # 5. Verify v1.1.0 works
```

#### Task 5C: Feature Flag Tests
**File:** `tests/features/test_feature_flags.py`

```python
"""Test feature flag behavior."""

def test_gateway_disabled_by_default():
    """GATEWAY_ENABLED defaults to false."""
    assert Settings().gateway_enabled is False

def test_gateway_enabled_when_configured():
    """GATEWAY_ENABLED=true enables features."""
    with patch.dict(os.environ, {"GATEWAY_ENABLED": "true"}):
        assert Settings().gateway_enabled is True

def test_version_endpoint_shows_features():
    """/version endpoint shows feature status."""
    response = client.get("/api/v1/version")
    assert response.json()["version"] == "1.1.0"
    assert response.json()["features"]["gateway_integration"] is False
```

**Updated Deliverables:**
- [ ] Backwards compatibility test suite (+10 tests)
- [ ] Migration test suite (+5 tests)
- [ ] Feature flag tests (+5 tests)
- [ ] Performance regression tests (+3 tests)
- [ ] Total new tests: **~23 tests**

---

### **Documentation Engineer: Documentation & Deployment**

**Additional Tasks (3-4 hours):**

#### Task 6A: CHANGELOG.md
**File:** `CHANGELOG.md`

Add complete v1.1.0 section (see V1_1_0_RELEASE_PLAN.md for template).

#### Task 6B: Migration Guide
**File:** `docs/gateway-integration/MIGRATION_V1_0_0_TO_V1_1_0.md`

```markdown
# Migration Guide: v1.0.0 → v1.1.0

## Overview

SARK v1.1.0 adds MCP Gateway integration as an **opt-in feature**.
This guide covers upgrading from v1.0.0 to v1.1.0.

## Compatibility

✅ **100% backwards compatible**
- Zero breaking changes
- Gateway disabled by default
- v1.0.0 behavior maintained

## Prerequisites

- SARK v1.0.0 running
- Database backup completed
- 5 minutes maintenance window (optional)

## Upgrade Steps

### Step 1: Backup (Required)
```bash
./scripts/backup-database.sh
```

### Step 2: Pull v1.1.0 Image
```bash
docker pull sark:1.1.0
```

### Step 3: Run Migrations
```bash
docker run --rm \
  -e DATABASE_URL=$DATABASE_URL \
  sark:1.1.0 \
  alembic upgrade head
```

### Step 4: Update Configuration (Optional)
```bash
# Gateway DISABLED by default (v1.0.0 behavior)
# Only add if you want Gateway integration

echo "GATEWAY_ENABLED=false" >> .env  # Explicit
```

### Step 5: Restart SARK
```bash
docker compose up -d sark
```

### Step 6: Verify Upgrade
```bash
# Check version
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.1.0",
  "features": {
    "gateway_integration": false,  # Disabled by default
    "a2a_authorization": false
  }
}

# Verify v1.0.0 endpoints still work
curl -X POST http://localhost:8000/api/v1/auth/login ...
```

## Rollback (If Needed)

### Option 1: Rollback Image Only
```bash
docker pull sark:1.0.0
docker compose up -d sark
# Migrations are additive, v1.0.0 code works on v1.1.0 database
```

### Option 2: Full Rollback (Image + Database)
```bash
# Rollback migration
docker run --rm sark:1.1.0 alembic downgrade -1

# Rollback image
docker pull sark:1.0.0
docker compose up -d sark

# Restore backup if needed
./scripts/restore-database.sh
```

## Enabling Gateway Integration (Optional)

After successful upgrade, optionally enable Gateway:

```bash
# Edit .env
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
GATEWAY_API_KEY=your_api_key

# Restart
docker compose restart sark

# Verify
curl http://localhost:8000/api/v1/version
# Should show: gateway_integration: true
```

## Troubleshooting

See [Troubleshooting Guide](TROUBLESHOOTING.md)
```

#### Task 6C: Feature Flags Documentation
**File:** `docs/gateway-integration/FEATURE_FLAGS.md`

(See V1_1_0_RELEASE_PLAN.md for complete content)

#### Task 6D: Release Notes
**File:** `docs/gateway-integration/RELEASE_NOTES_V1_1_0.md`

```markdown
# SARK v1.1.0 Release Notes

**Release Date:** TBD
**Type:** Minor Release (New Features, Backwards Compatible)

## 🎉 What's New

### MCP Gateway Integration (Opt-in Feature)

SARK v1.1.0 introduces enterprise-grade integration with MCP Gateway Registry,
providing centralized policy enforcement for gateway-managed MCP servers.

**Key Features:**
- Gateway authorization API
- Agent-to-Agent (A2A) authorization
- Gateway audit logging and SIEM integration
- Prometheus metrics and Grafana dashboards

**Important:** Gateway integration is **disabled by default** and must be
explicitly enabled via `GATEWAY_ENABLED=true`.

## ✅ Backwards Compatibility

100% backwards compatible with v1.0.0:
- No breaking changes
- Gateway disabled by default
- All v1.0.0 endpoints work identically
- Zero performance impact when disabled

## 📦 Upgrade Instructions

```bash
# 1. Backup
./scripts/backup-database.sh

# 2. Upgrade
docker pull sark:1.1.0
alembic upgrade head
docker compose up -d sark

# 3. Verify
curl http://localhost:8000/api/v1/version
```

See [Migration Guide](MIGRATION_V1_0_0_TO_V1_1_0.md) for details.

## 🔄 Rollback

Full rollback supported:
```bash
alembic downgrade -1
docker pull sark:1.0.0
docker compose up -d sark
```

## 📊 Performance

- Zero impact when Gateway disabled
- P95 authorization latency: <50ms (when enabled)
- Throughput: 5000+ req/s (when enabled)

## 🔒 Security

- 0 P0/P1/P2 vulnerabilities
- Parameter filtering for injection protection
- A2A trust level enforcement
- Comprehensive audit logging

## 📚 Documentation

- [Gateway Integration Guide](deployment/QUICKSTART.md)
- [API Reference](API_REFERENCE.md)
- [Migration Guide](MIGRATION_V1_0_0_TO_V1_1_0.md)
- [Feature Flags](FEATURE_FLAGS.md)

## 🙏 Contributors

Thanks to all workers who contributed to this release!
```

**Updated Deliverables:**
- [ ] CHANGELOG.md updated
- [ ] Migration guide (v1.0.0 → v1.1.0)
- [ ] Feature flags documentation
- [ ] Release notes for v1.1.0
- [ ] Updated README.md with v1.1.0 features

---

## Summary of Additional Work

| Worker | Additional Time | New Deliverables |
|--------|----------------|------------------|
| Engineer 1 | 2-3 hours | Feature flags, lazy init, compat tests |
| Engineer 2 | 2-3 hours | /version endpoint, 503 responses, tests |
| Engineer 3 | 1-2 hours | Namespace isolation, bundle versioning, tests |
| Engineer 4 | 2-3 hours | Conditional logging, reversible migrations, tests |
| QA Worker | 4-5 hours | 23 new tests (compat, migration, features) |
| Doc Engineer | 3-4 hours | Changelog, migration guide, release notes |

**Total Additional Time:** ~15-20 hours (distributed across 6 workers = ~3 hours/worker)

**Impact on Timeline:** +1 day (Day 11 for final v1.1.0 compliance)

---

## Updated Timeline

```
Day 1-10:  Core development (as planned)
Day 11:    v1.1.0 compliance work (feature flags, compat tests, docs)
Day 12:    Staging deployment + migration testing
Day 13:    Pre-release checklist
Day 14:    Create release (tag v1.1.0, build, publish)
Day 15:    Canary deployment (10%)
Day 16-17: Gradual rollout (50%, 100%)
```

**Total Timeline:** 17 days (was 10 days + 7 days for v1.1.0 compliance and rollout)

---

**All workers: Review your updated tasks and adjust timelines accordingly! 🚀**
