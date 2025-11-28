# Gateway Integration Plan Updates for v1.1.0 Release

**Context:** SARK v1.0.0 is production-ready. Gateway integration targets v1.1.0.

---

## Impact Analysis: 1.0.0 → 1.1.0

### What Changes

#### 1. **Backwards Compatibility is CRITICAL** ✅

**v1.0.0 Constraint:**
- Gateway integration must be **100% backwards compatible**
- Existing SARK v1.0.0 deployments upgrade seamlessly to v1.1.0
- Zero breaking changes allowed
- Gateway integration is **opt-in** via feature flag

**Implementation Requirements:**
- All new code must not affect existing functionality
- Gateway features disabled by default (`GATEWAY_ENABLED=false`)
- No changes to existing APIs without deprecation process
- Database migrations must be reversible

---

#### 2. **Production Readiness Standards** 📊

**v1.0.0 sets the bar:**
- 87% test coverage (we must maintain or exceed)
- 0 P0/P1 security vulnerabilities
- Comprehensive documentation
- Production deployment procedures
- Disaster recovery plan

**Gateway Integration Requirements:**
- Test coverage: **>90%** (higher bar for new features)
- Security: 0 P0/P1/P2 vulnerabilities (stricter)
- Performance: Must not degrade existing SARK performance
- Documentation: Production-grade from day 1

---

#### 3. **Semantic Versioning Compliance** 🔢

**v1.1.0 Release Type:** Minor version (new features, backwards compatible)

**What's Allowed:**
- ✅ New endpoints (e.g., `/api/v1/gateway/*`)
- ✅ New configuration options (opt-in)
- ✅ New database tables (additive)
- ✅ New dependencies (if isolated)
- ✅ New OPA policies (separate namespace)

**What's NOT Allowed:**
- ❌ Changes to existing endpoints
- ❌ Removal of existing features
- ❌ Breaking changes to existing APIs
- ❌ Changes to existing database schema (only additions)
- ❌ Removal of existing configuration options

---

#### 4. **Migration & Upgrade Path** 🔄

**v1.0.0 → v1.1.0 Upgrade:**

Must be **zero-downtime** and **reversible**.

**Upgrade Process:**
```bash
# 1. Backup (standard practice)
./scripts/backup-database.sh

# 2. Pull latest image
docker pull sark:1.1.0

# 3. Run database migrations (additive only)
docker run --rm sark:1.1.0 alembic upgrade head

# 4. Update configuration (optional - Gateway disabled by default)
# Only add Gateway config if enabling integration
echo "GATEWAY_ENABLED=false" >> .env  # Explicitly disabled

# 5. Restart SARK
docker compose up -d sark

# 6. Verify upgrade
curl http://localhost:8000/health
# Should show: version: "1.1.0", gateway_enabled: false
```

**Rollback Process:**
```bash
# 1. Rollback to v1.0.0 image
docker pull sark:1.0.0

# 2. Rollback database migrations
docker run --rm sark:1.1.0 alembic downgrade -1

# 3. Restart
docker compose up -d sark
```

---

#### 5. **Feature Flag Strategy** 🚩

**Gateway integration is feature-flagged at multiple levels:**

**Level 1: Configuration**
```bash
GATEWAY_ENABLED=false  # Default - v1.0.0 behavior
```

**Level 2: Runtime Detection**
```python
# In code
if not settings.gateway_enabled:
    # Skip Gateway initialization entirely
    # Zero performance impact
    return
```

**Level 3: API Endpoints**
```python
# Gateway endpoints return 503 when disabled
@router.post("/gateway/authorize")
async def authorize_gateway_operation(...):
    if not settings.gateway_enabled:
        raise HTTPException(
            status_code=503,
            detail="Gateway integration not enabled. Set GATEWAY_ENABLED=true to enable."
        )
```

**Level 4: Database Migrations**
```python
# Migrations check for feature flag
def upgrade():
    # Only create gateway tables if explicitly enabled during migration
    # OR always create but mark as optional
    op.create_table('gateway_audit_events', ...)
```

---

#### 6. **Release Process for v1.1.0** 📦

**Pre-Release Checklist:**
- [ ] All tests pass (unit, integration, performance, security)
- [ ] Test coverage ≥90%
- [ ] Security scan clean (0 P0/P1/P2 vulnerabilities)
- [ ] Documentation complete and reviewed
- [ ] Migration tested (v1.0.0 → v1.1.0 → v1.0.0)
- [ ] Performance benchmarks meet targets
- [ ] Zero-downtime upgrade verified
- [ ] Backwards compatibility verified

**Release Process:**
```bash
# 1. Create release branch
git checkout -b release/v1.1.0

# 2. Update version in code
# Update pyproject.toml: version = "1.1.0"
# Update __init__.py: __version__ = "1.1.0"

# 3. Update CHANGELOG.md
# Add v1.1.0 section with all changes

# 4. Tag release
git tag -a v1.1.0 -m "Release v1.1.0: MCP Gateway Integration"

# 5. Build and test Docker image
docker build -t sark:1.1.0 .
docker run --rm sark:1.1.0 pytest

# 6. Push release
git push origin release/v1.1.0
git push origin v1.1.0

# 7. Create GitHub release
gh release create v1.1.0 \
  --title "SARK v1.1.0 - MCP Gateway Integration" \
  --notes-file docs/gateway-integration/RELEASE_NOTES.md
```

---

#### 7. **Deployment Strategy for v1.1.0** 🚀

**Production Rollout Plan:**

**Phase 1: Staging Validation (Day 1)**
- Deploy v1.1.0 to staging
- Run full test suite
- Verify upgrade from v1.0.0
- Test Gateway integration (if enabled)

**Phase 2: Canary Deployment (Days 2-3)**
- Deploy to 10% of production instances
- Monitor for 48 hours
- Key metrics:
  - Error rate (must be ≤ v1.0.0)
  - Latency (must be ≤ v1.0.0)
  - Resource usage (must be ≤ v1.0.0 +5%)
  - Zero Gateway-related errors (if disabled)

**Phase 3: Gradual Rollout (Days 4-5)**
- 10% → 50% → 100%
- 24-hour soak period between steps
- Continuous monitoring

**Phase 4: Gateway Enablement (Days 6+, Optional)**
- For users wanting Gateway integration
- Enable on single instance first
- Monitor Gateway-specific metrics
- Gradual rollout of Gateway feature

---

## Updated Implementation Plan Changes

### **Critical Additions for v1.1.0:**

#### 1. **Backwards Compatibility Tests**

**New Test File:** `tests/compatibility/test_v1_0_0_compatibility.py`

```python
"""Verify v1.1.0 maintains v1.0.0 compatibility."""

import pytest


def test_gateway_disabled_by_default():
    """Verify Gateway is disabled by default (v1.0.0 behavior)."""
    from sark.config import Settings

    settings = Settings()
    assert settings.gateway_enabled is False


def test_existing_endpoints_unchanged():
    """Verify all v1.0.0 endpoints work identically."""
    # Test auth endpoints
    # Test policy endpoints
    # Test server endpoints
    # All must work exactly as v1.0.0


def test_no_gateway_overhead_when_disabled():
    """Verify zero performance impact when Gateway disabled."""
    # Benchmark auth flow
    # Should be identical to v1.0.0


def test_database_schema_compatible():
    """Verify v1.1.0 database works with v1.0.0 code."""
    # Migrations are additive only
    # v1.0.0 code can run on v1.1.0 database
```

**Assign to:** QA Worker (add to existing tasks)

---

#### 2. **Migration Tests**

**New Test File:** `tests/migration/test_v1_0_0_to_v1_1_0.py`

```python
"""Test upgrade/downgrade between v1.0.0 and v1.1.0."""

import pytest


@pytest.mark.migration
def test_upgrade_from_v1_0_0():
    """Test upgrading from v1.0.0 to v1.1.0."""
    # 1. Start with v1.0.0 database
    # 2. Run alembic upgrade head
    # 3. Verify all tables exist
    # 4. Verify v1.0.0 data intact
    # 5. Verify v1.1.0 features work


@pytest.mark.migration
def test_downgrade_to_v1_0_0():
    """Test downgrading from v1.1.0 back to v1.0.0."""
    # 1. Start with v1.1.0 database
    # 2. Run alembic downgrade -1
    # 3. Verify Gateway tables removed
    # 4. Verify v1.0.0 code works
```

**Assign to:** QA Worker

---

#### 3. **Version Information Endpoint**

**Update:** `src/sark/api/routers/health.py`

```python
@router.get("/version")
async def get_version() -> dict:
    """Get SARK version and feature status."""
    from sark import __version__
    from sark.config import get_settings

    settings = get_settings()

    return {
        "version": __version__,  # "1.1.0"
        "major": 1,
        "minor": 1,
        "patch": 0,
        "features": {
            "gateway_integration": settings.gateway_enabled,
            "a2a_authorization": settings.a2a_enabled,
        },
        "compatibility": {
            "min_version": "1.0.0",
            "max_version": "1.x.x",
        }
    }
```

**Assign to:** Engineer 2 (add to API tasks)

---

#### 4. **CHANGELOG.md Update**

**File:** `CHANGELOG.md`

```markdown
# Changelog

All notable changes to SARK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-XX-XX

### Added

#### MCP Gateway Integration (Opt-in Feature)
- Gateway client for connecting to MCP Gateway Registry
- Gateway authorization endpoints (`/api/v1/gateway/*`)
- Agent-to-Agent (A2A) authorization support
- OPA policies for Gateway and A2A authorization
- Gateway audit logging and SIEM integration
- Prometheus metrics for Gateway operations
- Grafana dashboard for Gateway monitoring

**Configuration:**
- `GATEWAY_ENABLED` - Enable Gateway integration (default: `false`)
- `GATEWAY_URL` - Gateway API endpoint
- `GATEWAY_API_KEY` - Gateway authentication
- `A2A_ENABLED` - Enable A2A authorization (default: `false`)

**New Endpoints:**
- `POST /api/v1/gateway/authorize` - Authorize Gateway requests
- `POST /api/v1/gateway/authorize-a2a` - Authorize A2A communication
- `GET /api/v1/gateway/servers` - List authorized servers
- `GET /api/v1/gateway/tools` - List authorized tools
- `POST /api/v1/gateway/audit` - Log Gateway events
- `GET /api/v1/version` - Get version and feature status

**Database:**
- New table: `gateway_audit_events` (additive, optional)

**Documentation:**
- Complete Gateway integration guide
- API reference for Gateway endpoints
- Deployment guide (Docker, Kubernetes)
- Migration guide (v1.0.0 → v1.1.0)

### Changed
- None (fully backwards compatible)

### Deprecated
- None

### Removed
- None

### Fixed
- None

### Security
- Gateway integration includes parameter filtering to prevent injection attacks
- A2A authorization enforces trust levels and capabilities
- All Gateway operations audited

### Performance
- Zero performance impact when Gateway integration disabled
- Gateway authorization: P95 <50ms (when enabled)
- Throughput: 5000+ req/s (when enabled)

### Migration
- Upgrade: `docker pull sark:1.1.0 && alembic upgrade head`
- Downgrade: `alembic downgrade -1 && docker pull sark:1.0.0`
- Zero-downtime upgrade supported
- Rollback supported

---

## [1.0.0] - 2025-XX-XX

### Summary
First production-ready release of SARK with comprehensive authentication,
authorization, and operational excellence features.

[Full v1.0.0 changelog...]
```

**Assign to:** Documentation Engineer

---

#### 5. **Feature Flag Documentation**

**New File:** `docs/gateway-integration/FEATURE_FLAGS.md`

```markdown
# Gateway Integration Feature Flags

## Overview

Gateway integration in SARK v1.1.0 is **opt-in** and controlled by feature flags.
This ensures zero impact on existing v1.0.0 deployments.

## Feature Flags

### `GATEWAY_ENABLED`

**Default:** `false`

**Description:** Master toggle for Gateway integration.

**When disabled (default):**
- Zero performance impact
- Gateway endpoints return 503
- No Gateway client initialization
- No Gateway audit logging
- Behaves identically to v1.0.0

**When enabled:**
- Gateway client initialized
- Gateway endpoints active
- Authorization flow enabled
- Audit logging active

**Example:**
```bash
# Disable (default - v1.0.0 behavior)
GATEWAY_ENABLED=false

# Enable Gateway integration
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
GATEWAY_API_KEY=your_api_key
```

### `A2A_ENABLED`

**Default:** `false`

**Description:** Enable Agent-to-Agent authorization.

**Requires:** `GATEWAY_ENABLED=true`

**Example:**
```bash
GATEWAY_ENABLED=true
A2A_ENABLED=true
```

## Gradual Rollout Strategy

### Step 1: Upgrade to v1.1.0 (Gateway Disabled)
```bash
# Upgrade with Gateway disabled
docker pull sark:1.1.0
docker compose up -d

# Verify v1.0.0 behavior maintained
curl http://localhost:8000/version
# Should show: gateway_integration: false
```

### Step 2: Enable Gateway on Single Instance
```bash
# Enable on one instance
echo "GATEWAY_ENABLED=true" >> .env
echo "GATEWAY_URL=http://gateway:8080" >> .env
echo "GATEWAY_API_KEY=..." >> .env

docker compose restart sark

# Monitor metrics
curl http://localhost:9090/metrics | grep gateway
```

### Step 3: Gradual Rollout
- Monitor for 48 hours
- If stable, enable on more instances
- If issues, disable with `GATEWAY_ENABLED=false`

## Runtime Checks

Gateway integration performs runtime checks:

```python
if not settings.gateway_enabled:
    # Skip all Gateway logic
    # Zero overhead
    return
```

## Monitoring

**Key Metrics:**
- `sark_gateway_enabled` - Gauge showing if Gateway is enabled
- `sark_gateway_authorization_requests_total` - Only increments when enabled

**Dashboard:**
- Gateway metrics panel shows "Feature Disabled" when `GATEWAY_ENABLED=false`
```

**Assign to:** Documentation Engineer

---

## Updated Worker Task Additions

### **Engineer 1 - Additional Tasks:**

- [ ] Add `gateway_enabled` feature flag checks in Gateway client
- [ ] Ensure Gateway client initialization is lazy (only when enabled)
- [ ] Add backwards compatibility tests

**Code Addition:**
```python
# In Gateway client __init__
if not settings.gateway_enabled:
    logger.info("Gateway integration disabled, skipping initialization")
    return
```

---

### **Engineer 2 - Additional Tasks:**

- [ ] Add `/version` endpoint with feature flags
- [ ] Ensure Gateway endpoints return 503 when disabled
- [ ] Add backwards compatibility tests for existing endpoints

---

### **Engineer 3 - Additional Tasks:**

- [ ] Ensure OPA policies in separate namespace (`mcp.gateway.*`)
- [ ] No changes to existing `mcp.*` policies
- [ ] Add policy bundle versioning

---

### **Engineer 4 - Additional Tasks:**

- [ ] Ensure database migrations are additive only
- [ ] Add migration rollback tests
- [ ] Ensure audit logging is no-op when Gateway disabled

---

### **QA Worker - Additional Tasks:**

- [ ] Add v1.0.0 compatibility test suite
- [ ] Add migration tests (upgrade/downgrade)
- [ ] Add feature flag tests
- [ ] Verify zero performance impact when disabled

---

### **Documentation Engineer - Additional Tasks:**

- [ ] Update CHANGELOG.md for v1.1.0
- [ ] Create MIGRATION_GUIDE.md (v1.0.0 → v1.1.0)
- [ ] Create FEATURE_FLAGS.md
- [ ] Update README.md with v1.1.0 features
- [ ] Create RELEASE_NOTES.md for v1.1.0

---

## Release Checklist for v1.1.0

### **Pre-Release (Before Day 8)**
- [ ] All backwards compatibility tests pass
- [ ] Migration tests pass (both directions)
- [ ] Feature flag tests pass
- [ ] Zero performance regression when Gateway disabled
- [ ] Test coverage ≥90%
- [ ] Security scan: 0 P0/P1/P2 vulnerabilities

### **Release Preparation (Day 10)**
- [ ] Update version in `pyproject.toml`
- [ ] Update version in `src/sark/__init__.py`
- [ ] Update CHANGELOG.md
- [ ] Create RELEASE_NOTES.md
- [ ] Tag release: `v1.1.0`
- [ ] Build Docker image: `sark:1.1.0`

### **Post-Release**
- [ ] Deploy to staging
- [ ] Verify upgrade from v1.0.0
- [ ] Verify rollback to v1.0.0
- [ ] Canary deployment (10%)
- [ ] Gradual rollout (50%, 100%)
- [ ] Publish release notes
- [ ] Update documentation site

---

## Summary of Changes for v1.1.0

### **What's Different:**

1. **Backwards Compatibility:** Non-negotiable requirement
2. **Feature Flags:** Gateway disabled by default
3. **Migration Testing:** Upgrade/downgrade must be tested
4. **Version Endpoint:** New `/version` endpoint shows features
5. **Semantic Versioning:** Strict compliance (minor version bump)
6. **Release Process:** Formal release with changelog, tags, rollout plan
7. **Documentation:** Production-grade migration guides

### **What Stays the Same:**

- All technical implementation details
- All worker assignments
- All code examples
- 10-day timeline
- Parallelization strategy
- Omnibus PR process

### **Key Additions:**

- Backwards compatibility test suite (~200 lines)
- Migration test suite (~150 lines)
- Feature flag documentation
- CHANGELOG.md updates
- Migration guide
- Release notes
- Version endpoint

**Total Additional Work:** ~2-3 hours per worker (mostly testing and documentation)

---

## Deployment Timeline for v1.1.0

```
Day 1-10:  Development (as planned)
Day 11:    Staging deployment + migration testing
Day 12:    Pre-release checklist completion
Day 13:    Create release (tag, build, publish)
Day 14:    Canary deployment (10% production)
Day 15-16: Gradual rollout (50%, 100%)
Day 17+:   Monitor, enable Gateway feature gradually (optional)
```

---

**Updated plan ready for v1.1.0 release! 🚀**
