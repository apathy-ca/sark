# SARK Migration Guide: Phase 1 to Phase 2

**Applies to:** v1.x releases
**Date:** 2025-11-23
**Migration Type:** Phase 1 (Basic Setup) → Phase 2 (SIEM Integration)
**Downtime Required:** Zero (with proper execution)

---

## Table of Contents

1. [Migration Overview](#migration-overview)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Phase Comparison](#phase-comparison)
4. [Zero-Downtime Deployment Strategy](#zero-downtime-deployment-strategy)
5. [Migration Procedure](#migration-procedure)
6. [Database Migrations](#database-migrations)
7. [Configuration Changes](#configuration-changes)
8. [Component Upgrade Steps](#component-upgrade-steps)
9. [Verification Procedures](#verification-procedures)
10. [Rollback Plan](#rollback-plan)
11. [Troubleshooting](#troubleshooting)

---

## Migration Overview

### What's Changing

**Phase 1 → Phase 2 Migration adds:**
- ✅ SIEM integration (Splunk/Datadog)
- ✅ Audit event streaming to SIEM
- ✅ Security hardening (headers, CSRF)
- ✅ Production configuration validation
- ✅ Enhanced error handling and circuit breakers
- ✅ Event batching and compression
- ✅ Comprehensive monitoring and metrics

### What's NOT Changing

**Maintains compatibility with:**
- ✅ Existing API endpoints
- ✅ Database schema (TimescaleDB audit events)
- ✅ Configuration file format (.env)
- ✅ Service architecture
- ✅ Client integrations

### Migration Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| **Preparation** | 1-2 days | Configuration, testing, backups |
| **Deployment** | 2-4 hours | Zero-downtime rolling deployment |
| **Verification** | 1-2 hours | Health checks, SIEM validation |
| **Monitoring** | 24-48 hours | Stability monitoring |
| **Total** | 3-5 days | Full migration cycle |

---

## Pre-Migration Checklist

### 1. Environment Preparation

#### Required Information

- [ ] **Current Phase Version**
  ```bash
  curl http://localhost:8000/health | jq '.version'
  # Expected: "1.x.x" (Phase 1)
  ```

- [ ] **Target Phase Version**
  ```
  Version: 2.0.0 (Phase 2 with SIEM)
  ```

- [ ] **Deployment Environment**
  - [ ] Production
  - [ ] Staging (test here first!)
  - [ ] Development

#### Infrastructure Requirements

- [ ] **Server Resources**
  - CPU: Current + 10% overhead for SIEM processing
  - Memory: Current + 500 MB for event batching
  - Disk: Current + 10 GB for fallback logging
  - Network: Outbound HTTPS to SIEM endpoints

- [ ] **SIEM Endpoint Access**
  - [ ] Splunk HEC endpoint reachable (port 8088)
  - [ ] Datadog Logs API reachable (port 443)
  - [ ] Firewall rules configured
  - [ ] DNS resolution working

- [ ] **Credentials Obtained**
  - [ ] Splunk HEC token (if using Splunk)
  - [ ] Datadog API key (if using Datadog)
  - [ ] Secret keys generated (minimum 48 chars)

### 2. Backup Procedures

#### Database Backup

```bash
# Backup PostgreSQL database
pg_dump -h <postgres-host> -U sark -d sark \
  -f backups/sark_phase1_$(date +%Y%m%d_%H%M%S).sql

# Backup TimescaleDB audit database
pg_dump -h <timescale-host> -U sark -d sark_audit \
  -f backups/sark_audit_phase1_$(date +%Y%m%d_%H%M%S).sql

# Verify backups
ls -lh backups/
```

#### Configuration Backup

```bash
# Backup current configuration
cp .env backups/.env.phase1_$(date +%Y%m%d_%H%M%S)
cp -r config/ backups/config_phase1_$(date +%Y%m%d_%H%M%S)/

# Backup systemd service file
sudo cp /etc/systemd/system/sark.service backups/
```

#### Application Code Backup

```bash
# Tag current version
git tag -a v1.x.x -m "Phase 1 final version before SIEM migration"
git push origin v1.x.x

# Create backup branch
git checkout -b phase1-stable
git push origin phase1-stable
```

### 3. Testing Environment

#### Staging Environment Setup

- [ ] **Staging environment identical to production**
  - Same OS version
  - Same database version
  - Same configuration structure
  - Sample production data

- [ ] **Test migration in staging first**
  - Run full migration procedure
  - Verify SIEM integration
  - Test rollback procedure
  - Document any issues

#### Test Plan

- [ ] Health check endpoints respond
- [ ] API endpoints functional
- [ ] SIEM events delivered
- [ ] Metrics collected
- [ ] Logs generated correctly

### 4. Communication Plan

#### Stakeholder Notification

- [ ] **Notify stakeholders 48 hours before:**
  - Engineering team
  - Operations team
  - Security team
  - Management

- [ ] **Maintenance window (optional):**
  - Zero-downtime deployment (no window needed)
  - Or schedule 2-hour window for safety

- [ ] **Emergency contacts ready:**
  - On-call engineer
  - Database administrator
  - Network operations
  - SIEM administrator

---

## Phase Comparison

### Architecture Differences

| Component | Phase 1 | Phase 2 |
|-----------|---------|---------|
| **Audit Events** | Local database only | Database + SIEM streaming |
| **Event Processing** | Direct write | Batching + circuit breaker |
| **Error Handling** | Basic logging | Fallback logging + retry |
| **Security Headers** | None | Comprehensive (HSTS, CSP, etc.) |
| **CSRF Protection** | None | Token-based validation |
| **Compression** | None | gzip (73% reduction) |
| **Metrics** | Basic | Enhanced + SIEM delivery |
| **Configuration** | Basic validation | Comprehensive validation |

### Dependency Changes

| Dependency | Phase 1 | Phase 2 |
|------------|---------|---------|
| cryptography | 41.0.7 | 46.0.3 ⬆️ |
| setuptools | 68.1.2 | 80.9.0 ⬆️ |
| urllib3 | 2.3.0 | 2.5.0 ⬆️ |
| httpx | 0.28.1 | 0.28.1 ✅ |
| structlog | Latest | Latest ✅ |

**New Dependencies:**
- `pytest-httpx` (testing only)

### Configuration File Changes

**New variables in Phase 2:**

```bash
# SIEM Integration (new)
SPLUNK_ENABLED=true
SPLUNK_HEC_URL=https://splunk.example.com:8088/services/collector
SPLUNK_HEC_TOKEN=your-hec-token
SPLUNK_INDEX=sark_audit
SPLUNK_BATCH_SIZE=100
SPLUNK_BATCH_TIMEOUT_SECONDS=5

# Or Datadog
DATADOG_ENABLED=true
DATADOG_API_KEY=your-api-key
DATADOG_SITE=datadoghq.com

# Security (enhanced)
SECRET_KEY=<48-char-minimum>  # Now enforced
CORS_ORIGINS=https://app.example.com  # Now validated
```

---

## Zero-Downtime Deployment Strategy

### Strategy Overview

**Approach:** Blue-Green Deployment with Rolling Update

**Key Principles:**
1. Run old and new versions simultaneously
2. Gradually shift traffic to new version
3. Monitor health at each step
4. Rollback immediately if issues detected

### Deployment Architecture

```
┌─────────────────┐
│  Load Balancer  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│ Old  │  │ New  │  ← Both running
│ v1.x │  │ v2.0 │
└──────┘  └──────┘
    │         │
    └────┬────┘
         │
    ┌────▼────┐
    │Database │
    └─────────┘
```

### Traffic Shift Plan

| Step | Old Version | New Version | Traffic | Duration |
|------|-------------|-------------|---------|----------|
| 1 | 100% | 0% | All to old | Baseline |
| 2 | 90% | 10% | Test new | 15 min |
| 3 | 50% | 50% | Split | 30 min |
| 4 | 10% | 90% | Most to new | 30 min |
| 5 | 0% | 100% | All to new | Final |

### Health Check Gates

**Proceed to next step only if:**
- ✅ HTTP 200 on `/health` endpoint
- ✅ Error rate < 1%
- ✅ Response time < 500ms (p95)
- ✅ SIEM events delivering successfully
- ✅ No critical logs in past 5 minutes

**If health check fails:**
- ⏸️ Pause traffic shift
- 🔍 Investigate issue
- ⏮️ Rollback to previous step if unresolvable

---

## Migration Procedure

### Step 1: Pre-Deployment Validation

**Time:** 30 minutes

#### 1.1 Run Configuration Validator

```bash
# Copy new configuration template
cp .env.production.example .env.phase2

# Edit with Phase 2 settings
nano .env.phase2

# Validate configuration
python scripts/validate_config.py --env-file .env.phase2 --strict

# Expected output: ✅ All checks passed
```

#### 1.2 Test SIEM Connectivity

```bash
# Test Splunk HEC connectivity
curl -k https://<splunk-host>:8088/services/collector/health \
  -H "Authorization: Splunk <hec-token>"

# Expected: {"text":"HEC is healthy","code":17}

# Or test Datadog connectivity
curl -X POST "https://http-intake.logs.datadoghq.com/api/v2/logs" \
  -H "DD-API-KEY: <api-key>" \
  -H "Content-Type: application/json" \
  -d '[{"message":"test","service":"sark"}]'

# Expected: HTTP 202 Accepted
```

#### 1.3 Verify Database Migrations

```bash
# Check current schema version
psql -h <timescale-host> -U sark -d sark_audit \
  -c "SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1;"

# Expected: Phase 1 schema version
```

### Step 2: Deploy New Version (Instance 2)

**Time:** 15 minutes

#### 2.1 Deploy Code

```bash
# On second server/container
cd /opt/sark-phase2
git fetch origin
git checkout v2.0.0

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies (with upgraded versions)
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

#### 2.2 Apply Configuration

```bash
# Copy Phase 2 configuration
cp /path/to/.env.phase2 .env

# Set file permissions
chmod 600 .env
chown sark:sark .env

# Validate
python scripts/validate_config.py --strict
```

#### 2.3 Run Database Migrations

```bash
# Phase 2 migrations (if any)
alembic upgrade head

# Verify migration
alembic current
# Expected: Latest migration ID
```

#### 2.4 Start New Service

```bash
# Start Phase 2 service on different port (8001)
API_PORT=8001 uvicorn sark.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --workers 4 &

# Wait for startup
sleep 10

# Verify health
curl http://localhost:8001/health

# Expected: {"status":"healthy","version":"2.0.0"}
```

### Step 3: Traffic Shift (10% Canary)

**Time:** 15 minutes

#### 3.1 Configure Load Balancer

```bash
# Add new backend to load balancer
# Example: HAProxy configuration
cat >> /etc/haproxy/haproxy.cfg <<EOF
backend sark_backend
    server sark-old 10.0.1.10:8000 weight 90
    server sark-new 10.0.1.11:8001 weight 10
EOF

# Reload HAProxy
sudo systemctl reload haproxy
```

#### 3.2 Monitor Canary Traffic

```bash
# Watch error rates
watch -n 5 'curl -s http://localhost:8001/metrics | grep http_requests_total'

# Check SIEM delivery
curl http://localhost:8001/metrics | grep siem_events_sent_total

# Monitor logs
tail -f /var/log/sark/sark-phase2.log
```

#### 3.3 Verify SIEM Integration

```bash
# Check SIEM events arriving
# Splunk:
# index=sark_audit earliest=-5m | stats count

# Datadog:
# Check Logs Explorer for service:sark in last 5 minutes
```

**Decision Point:**
- ✅ **If healthy:** Proceed to Step 4
- ❌ **If issues:** Execute rollback (see Rollback Plan)

### Step 4: Gradual Traffic Shift (50% → 100%)

**Time:** 60 minutes

#### 4.1 Shift to 50% Traffic

```bash
# Update load balancer weights
# HAProxy example:
#   server sark-old weight 50
#   server sark-new weight 50
sudo systemctl reload haproxy

# Monitor for 30 minutes
```

#### 4.2 Monitor Phase 2 Performance

```bash
# Response times
curl http://localhost:8001/metrics | grep http_request_duration_seconds

# Error rates
curl http://localhost:8001/metrics | grep http_requests_total | grep status=\"5

# SIEM delivery metrics
curl http://localhost:8001/metrics | grep siem

# Database connections
curl http://localhost:8001/metrics | grep db_pool
```

**Health Checks:**
- Response time p95 < 500ms ✅
- Error rate < 1% ✅
- SIEM delivery success > 99% ✅
- No database connection issues ✅

#### 4.3 Shift to 90% Traffic

```bash
# Update load balancer weights
#   server sark-old weight 10
#   server sark-new weight 90
sudo systemctl reload haproxy

# Monitor for 30 minutes
```

#### 4.4 Full Traffic Shift (100%)

```bash
# Route all traffic to Phase 2
#   server sark-old weight 0  (or remove)
#   server sark-new weight 100
sudo systemctl reload haproxy

# Keep Phase 1 running for 24 hours (safety)
```

### Step 5: Post-Deployment Verification

**Time:** 30 minutes

#### 5.1 Functional Testing

```bash
# Test all API endpoints
curl http://load-balancer/health
curl http://load-balancer/api/v1/servers
curl http://load-balancer/api/v1/policy
curl http://load-balancer/metrics

# Verify security headers
curl -I http://load-balancer/health | grep -E "(X-Frame|Strict-Transport|Content-Security)"

# Expected: All security headers present
```

#### 5.2 SIEM Verification

**Splunk:**
```spl
index=sark_audit earliest=-1h
| stats count by event_type, severity
| where count > 0
```

**Datadog:**
```
service:sark
```

**Expected:** Events from last hour visible

#### 5.3 Metrics Verification

```bash
# Check Phase 2 metrics
curl http://load-balancer/metrics | grep -E "(http_requests_total|siem_events_sent_total|circuit_breaker_state)"

# Verify:
# - http_requests_total increasing
# - siem_events_sent_total increasing
# - circuit_breaker_state = closed
```

### Step 6: Cleanup (24 hours later)

**Time:** 15 minutes

#### 6.1 Decommission Phase 1

```bash
# Stop Phase 1 service
sudo systemctl stop sark-phase1

# Remove from load balancer
# (already done in Step 4.4)

# Archive Phase 1 code
tar -czf backups/sark-phase1-$(date +%Y%m%d).tar.gz /opt/sark-phase1/
```

#### 6.2 Update Service Configuration

```bash
# Update main service to use Phase 2
sudo cp /etc/systemd/system/sark-phase2.service /etc/systemd/system/sark.service
sudo systemctl daemon-reload
sudo systemctl enable sark.service
```

---

## Database Migrations

### Schema Changes

**Phase 2 does NOT modify existing schema:**
- ✅ No changes to `audit_events` table
- ✅ No changes to `servers` table
- ✅ No changes to `policies` table

**Phase 2 adds new fields (backward compatible):**
```sql
-- Optional: Add SIEM forwarding tracking (if needed)
ALTER TABLE audit_events
  ADD COLUMN IF NOT EXISTS siem_forwarded TIMESTAMP WITH TIME ZONE;

-- Create index for SIEM forwarding queries
CREATE INDEX IF NOT EXISTS idx_audit_events_siem_forwarded
  ON audit_events(siem_forwarded)
  WHERE siem_forwarded IS NULL;
```

### Migration Script

**No manual migration needed** - schema is backward compatible.

**If adding SIEM tracking column:**

```bash
# Run migration
psql -h <timescale-host> -U sark -d sark_audit -f migrations/add_siem_tracking.sql

# Verify
psql -h <timescale-host> -U sark -d sark_audit \
  -c "\d audit_events" | grep siem_forwarded
```

---

## Configuration Changes

### Environment Variables

**Required new variables:**

```bash
# Choose ONE SIEM platform

# Option 1: Splunk
SPLUNK_ENABLED=true
SPLUNK_HEC_URL=https://splunk.example.com:8088/services/collector
SPLUNK_HEC_TOKEN=12345678-1234-1234-1234-123456789012
SPLUNK_INDEX=sark_audit
SPLUNK_SOURCETYPE=sark:audit:event
SPLUNK_SOURCE=sark-production
SPLUNK_VERIFY_SSL=true
SPLUNK_BATCH_SIZE=100
SPLUNK_BATCH_TIMEOUT_SECONDS=5
SPLUNK_RETRY_ATTEMPTS=3

# Option 2: Datadog
DATADOG_ENABLED=true
DATADOG_API_KEY=your-datadog-api-key-here
DATADOG_APP_KEY=  # Optional
DATADOG_SITE=datadoghq.com
DATADOG_SERVICE=sark
DATADOG_ENVIRONMENT=production
DATADOG_VERIFY_SSL=true
DATADOG_BATCH_SIZE=100
DATADOG_BATCH_TIMEOUT_SECONDS=5
DATADOG_RETRY_ATTEMPTS=3
```

**Enhanced security variables:**

```bash
# SECRET_KEY now enforced (minimum 48 chars)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

# CORS now validated
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

### Configuration Migration Tool

```bash
# Use migration script to update configuration
python scripts/migrate_phase1_to_phase2.py \
  --phase1-config .env \
  --phase2-config .env.phase2 \
  --validate

# Review changes
diff .env .env.phase2

# Apply changes
cp .env.phase2 .env
```

---

## Component Upgrade Steps

### 1. Python Dependencies

**Upgrade strategy:** Use `pip install --upgrade` with version pinning

```bash
# Upgrade critical security packages
pip install --upgrade --ignore-installed 'cryptography>=46.0.0'
pip install --upgrade 'setuptools>=80.9.0'
pip install --upgrade 'urllib3>=2.5.0'

# Verify versions
pip list | grep -E "(cryptography|setuptools|urllib3)"

# Expected:
# cryptography  46.0.3
# setuptools    80.9.0
# urllib3       2.5.0
```

### 2. Security Middleware

**New components in Phase 2:**

```python
# Automatically added - no manual changes needed
from sark.api.middleware.security_headers import add_security_middleware

add_security_middleware(
    app,
    enable_hsts=(settings.environment == "production"),
    enable_csrf=True,
    csp_policy="default-src 'self'; script-src 'self' 'unsafe-inline'",
    csrf_exempt_paths=["/health", "/metrics", "/docs"],
)
```

**Client impact:** Clients must include `X-CSRF-Token` header for POST/PUT/PATCH/DELETE requests.

### 3. SIEM Integration

**Initialization:** Automatic on application startup

```python
# SIEM initialized based on configuration
if settings.splunk_enabled:
    splunk_siem = SplunkSIEM(SplunkConfig.from_settings(settings))
    await splunk_siem.health_check()

if settings.datadog_enabled:
    datadog_siem = DatadogSIEM(DatadogConfig.from_settings(settings))
    await datadog_siem.health_check()
```

**Verification:**

```bash
# Check SIEM initialization in logs
grep "siem_initialized" /var/log/sark/sark.log

# Expected:
# [info] splunk_siem_initialized hec_url=https://... index=sark_audit
# or
# [info] datadog_siem_initialized site=datadoghq.com service=sark
```

### 4. Circuit Breaker

**Automatic setup** - no manual configuration needed

**Monitoring:**

```bash
# Check circuit breaker state
curl http://localhost:8000/metrics | grep circuit_breaker_state

# Expected: circuit_breaker_state{circuit="splunk"} 0  (0 = closed, 1 = open)
```

---

## Verification Procedures

### Health Check Verification

```bash
#!/bin/bash
# verify_phase2.sh

echo "=== Phase 2 Health Verification ==="

# 1. Application health
echo "1. Application health..."
HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$HEALTH" = "healthy" ]; then
    echo "   ✅ Application healthy"
else
    echo "   ❌ Application unhealthy: $HEALTH"
    exit 1
fi

# 2. Version check
echo "2. Version check..."
VERSION=$(curl -s http://localhost:8000/health | jq -r '.version')
if [[ "$VERSION" == 2.* ]]; then
    echo "   ✅ Version: $VERSION"
else
    echo "   ❌ Wrong version: $VERSION"
    exit 1
fi

# 3. Security headers
echo "3. Security headers..."
HEADERS=$(curl -sI http://localhost:8000/health | grep -E "(X-Frame-Options|Strict-Transport-Security)")
if [ -n "$HEADERS" ]; then
    echo "   ✅ Security headers present"
else
    echo "   ❌ Security headers missing"
    exit 1
fi

# 4. SIEM connectivity
echo "4. SIEM connectivity..."
SIEM_EVENTS=$(curl -s http://localhost:8000/metrics | grep 'siem_events_sent_total' | awk '{print $2}')
if [ "$SIEM_EVENTS" -gt 0 ]; then
    echo "   ✅ SIEM events sent: $SIEM_EVENTS"
else
    echo "   ⚠️  No SIEM events sent yet (may be normal if just started)"
fi

# 5. Circuit breaker state
echo "5. Circuit breaker state..."
CB_STATE=$(curl -s http://localhost:8000/metrics | grep 'circuit_breaker_state' | grep 'closed' || echo "")
if [ -n "$CB_STATE" ]; then
    echo "   ✅ Circuit breaker closed (healthy)"
else
    echo "   ⚠️  Circuit breaker not closed (check if SIEM is reachable)"
fi

echo ""
echo "=== Verification Complete ==="
```

### SIEM Data Verification

**Splunk Verification:**

```spl
index=sark_audit earliest=-15m
| stats count by event_type, severity, source
| where count > 0
```

**Expected results:**
- Multiple event types (tool_invoked, server_registered, etc.)
- Various severity levels
- Source = "sark" or configured source name

**Datadog Verification:**

```
service:sark @timestamp:>now-15m
| stats count by event_type, severity
```

**Expected results:**
- Events from last 15 minutes
- Proper service tagging
- All custom attributes present

---

## Rollback Plan

**See [ROLLBACK_PROCEDURES.md](./ROLLBACK_PROCEDURES.md) for detailed procedures.**

### Quick Rollback Steps

**If issues detected during migration:**

1. **Immediate Traffic Shift**
   ```bash
   # Route all traffic back to Phase 1
   # Update load balancer to 100% old version
   sudo systemctl reload haproxy
   ```

2. **Stop Phase 2**
   ```bash
   # Stop new service
   sudo systemctl stop sark-phase2
   ```

3. **Verify Phase 1**
   ```bash
   # Check Phase 1 still healthy
   curl http://old-server:8000/health
   ```

4. **Investigate**
   - Check logs: `/var/log/sark/sark-phase2.log`
   - Check metrics: `curl http://localhost:8001/metrics`
   - Check SIEM connectivity

---

## Troubleshooting

### Common Issues

#### Issue 1: SIEM Events Not Delivering

**Symptoms:**
- `siem_events_failed_total` metric increasing
- Circuit breaker opening
- Logs show connection errors

**Diagnosis:**
```bash
# Check SIEM connectivity
curl -k https://<splunk-host>:8088/services/collector/health

# Check circuit breaker state
curl http://localhost:8000/metrics | grep circuit_breaker

# Check logs
grep "siem_connection_error" /var/log/sark/sark.log
```

**Solutions:**
1. Verify SIEM endpoint URL
2. Check firewall rules
3. Verify HEC token/API key
4. Check SIEM service health

#### Issue 2: High Memory Usage

**Symptoms:**
- Memory usage increased by >500 MB
- OOM errors in logs

**Diagnosis:**
```bash
# Check memory usage
free -h
ps aux | grep uvicorn | awk '{print $6}'

# Check event queue size
curl http://localhost:8000/metrics | grep event_queue_size
```

**Solutions:**
1. Reduce `SPLUNK_BATCH_SIZE` or `DATADOG_BATCH_SIZE`
2. Reduce `API_WORKERS`
3. Increase `BATCH_TIMEOUT_SECONDS` (flush more frequently)

#### Issue 3: Security Headers Breaking Clients

**Symptoms:**
- Browser errors (CSP violations)
- CORS errors
- Frame embedding issues

**Diagnosis:**
```bash
# Check security headers
curl -I http://localhost:8000/health

# Check browser console for CSP violations
```

**Solutions:**
1. Adjust CSP policy in configuration
2. Add client domains to CORS_ORIGINS
3. Update X-Frame-Options if embedding needed

#### Issue 4: CSRF Token Errors

**Symptoms:**
- 403 Forbidden on POST/PUT/PATCH/DELETE
- "CSRF token missing" errors

**Diagnosis:**
```bash
# Test with CSRF token
curl -X POST http://localhost:8000/api/v1/test \
  -H "X-CSRF-Token: test-token" \
  -H "Content-Type: application/json"
```

**Solutions:**
1. Update clients to include `X-CSRF-Token` header
2. Add endpoints to `csrf_exempt_paths` if needed
3. Implement proper CSRF token generation

---

## Migration Checklist

### Pre-Migration

- [ ] Backup databases (PostgreSQL + TimescaleDB)
- [ ] Backup configuration files
- [ ] Tag current version in git
- [ ] Test migration in staging
- [ ] Obtain SIEM credentials
- [ ] Generate new SECRET_KEY
- [ ] Validate Phase 2 configuration
- [ ] Test SIEM connectivity
- [ ] Notify stakeholders

### Migration

- [ ] Deploy Phase 2 code
- [ ] Apply configuration
- [ ] Run database migrations
- [ ] Start Phase 2 service
- [ ] Verify health checks
- [ ] Shift 10% traffic
- [ ] Monitor for 15 minutes
- [ ] Verify SIEM delivery
- [ ] Shift to 50% traffic
- [ ] Monitor for 30 minutes
- [ ] Shift to 90% traffic
- [ ] Monitor for 30 minutes
- [ ] Shift to 100% traffic
- [ ] Keep Phase 1 running 24h

### Post-Migration

- [ ] Verify all API endpoints
- [ ] Verify security headers
- [ ] Verify SIEM events in Splunk/Datadog
- [ ] Verify metrics collection
- [ ] Monitor for 24-48 hours
- [ ] Decommission Phase 1
- [ ] Update documentation
- [ ] Post-mortem meeting

---

## Support

### Migration Support

**During migration (live support):**
- Slack channel: #sark-migration
- Video call: [Zoom link]
- Emergency hotline: [Phone]

**Post-migration (monitoring):**
- SIEM dashboard: [URL]
- Metrics dashboard: [Grafana URL]
- Logs: [Log aggregation URL]

### Escalation Path

1. **Level 1:** DevOps engineer attempts resolution
2. **Level 2:** Escalate to team lead after 30 minutes
3. **Level 3:** Escalate to architect if service down >1 hour

---

**Migration Guide Version:** 2.0
**Last Updated:** 2025-11-23
**Maintained By:** Engineer 3 (SIEM Lead)
**Next Review:** After first production migration
