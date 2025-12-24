# SARK Rollback Procedures

**Applies to:** v1.x releases
**Date:** 2025-11-23
**Purpose:** Emergency rollback procedures for Phase 2 deployment
**Recovery Time Objective (RTO):** < 15 minutes
**Recovery Point Objective (RPO):** 0 (no data loss)

---

## Table of Contents

1. [Rollback Overview](#rollback-overview)
2. [When to Rollback](#when-to-rollback)
3. [Rollback Decision Tree](#rollback-decision-tree)
4. [Quick Rollback (Traffic Only)](#quick-rollback-traffic-only)
5. [Full Rollback (All Components)](#full-rollback-all-components)
6. [Component-Specific Rollbacks](#component-specific-rollbacks)
7. [Database Rollback](#database-rollback)
8. [Verification After Rollback](#verification-after-rollback)
9. [Post-Rollback Actions](#post-rollback-actions)
10. [Rollback Testing](#rollback-testing)

---

## Rollback Overview

### Rollback Types

| Type | Scope | Downtime | Complexity | When to Use |
|------|-------|----------|------------|-------------|
| **Traffic Shift** | Load balancer only | 0 seconds | Low | Issues detected early, Phase 1 still running |
| **Service Restart** | Application only | < 10 seconds | Low | Configuration issues, no code issues |
| **Code Rollback** | Code + config | < 5 minutes | Medium | Code bugs, breaking changes |
| **Database Rollback** | Schema changes | < 10 minutes | High | Schema migration failures |
| **Full Rollback** | All components | < 15 minutes | High | Critical system failure |

### Rollback Safety

**Phase 2 Design Principles:**
- ✅ **Backward compatible** - No breaking schema changes
- ✅ **Dual-stack support** - Phase 1 and 2 can run simultaneously
- ✅ **Zero data loss** - All data preserved during rollback
- ✅ **Fast recovery** - < 15 minute RTO

### Rollback Authority

| Severity | Who Can Authorize | Notification Required |
|----------|-------------------|----------------------|
| **Critical** (service down) | On-call engineer | Notify after action |
| **High** (>5% error rate) | Team lead | Notify stakeholders |
| **Medium** (degraded performance) | Engineering manager | Discuss in post-mortem |

---

## When to Rollback

### Critical Triggers (Immediate Rollback)

**Execute rollback immediately if:**

1. **Service Unavailable**
   - Health check endpoint returns 5xx
   - Service not responding
   - Load balancer marks all instances unhealthy

2. **High Error Rate**
   - Error rate > 5% for >5 minutes
   - Critical endpoints failing
   - Database connection failures

3. **Data Integrity Issues**
   - Audit events not being recorded
   - Data corruption detected
   - Schema migration failures

4. **Security Vulnerabilities**
   - New vulnerability discovered in Phase 2
   - Security headers causing authentication bypass
   - CSRF protection malfunctioning

### Warning Triggers (Consider Rollback)

**Evaluate rollback if:**

1. **Performance Degradation**
   - Response time p95 > 2x baseline
   - Memory usage > 80%
   - CPU usage > 90%

2. **SIEM Integration Issues**
   - SIEM events not delivering (if not critical business function)
   - Circuit breaker frequently opening
   - High SIEM latency

3. **Minor Bugs**
   - Non-critical features broken
   - Cosmetic issues
   - Documentation errors

**Decision:** Fix forward vs rollback based on:
- Impact severity
- Time to fix
- Risk of further issues

---

## Rollback Decision Tree

```
┌─────────────────────────────────┐
│   Issue Detected                │
└────────────┬────────────────────┘
             │
             ▼
      ┌──────────────┐
      │  Critical?   │
      └──┬────────┬──┘
         │ No     │ Yes
         │        └──────────────┐
         ▼                       ▼
   ┌─────────────┐      ┌───────────────┐
   │Can fix in   │      │Execute Quick  │
   │< 30 min?    │      │Rollback Now   │
   └──┬────────┬─┘      └───────────────┘
      │ No     │ Yes
      │        └────────┐
      ▼                 ▼
┌──────────────┐  ┌────────────┐
│Execute Full  │  │Fix Forward │
│Rollback      │  │& Monitor   │
└──────────────┘  └────────────┘
```

---

## Quick Rollback (Traffic Only)

**When to use:** Phase 1 still running, minor issues detected

**Downtime:** 0 seconds

**RTO:** < 1 minute

### Procedure

#### Step 1: Shift Traffic to Phase 1 (< 30 seconds)

```bash
# Option 1: HAProxy
cat > /tmp/haproxy_rollback.cfg <<'EOF'
backend sark_backend
    server sark-old 10.0.1.10:8000 weight 100
    server sark-new 10.0.1.11:8001 weight 0
EOF

# Apply configuration
sudo cp /tmp/haproxy_rollback.cfg /etc/haproxy/haproxy.cfg
sudo systemctl reload haproxy

# Verify
curl -s http://load-balancer/health | jq '.version'
# Expected: "1.x.x" (Phase 1)
```

```bash
# Option 2: Nginx
cat > /etc/nginx/conf.d/sark_upstream.conf <<'EOF'
upstream sark_backend {
    server 10.0.1.10:8000 weight=100;
    server 10.0.1.11:8001 weight=0;
}
EOF

sudo nginx -t
sudo systemctl reload nginx
```

```bash
# Option 3: AWS ALB
aws elbv2 modify-target-group \
    --target-group-arn arn:aws:elasticloadbalancing:... \
    --health-check-interval-seconds 5

# Manually mark Phase 2 targets unhealthy or remove from target group
```

#### Step 2: Verify Rollback (< 30 seconds)

```bash
# Check version
for i in {1..10}; do
    curl -s http://load-balancer/health | jq -r '.version'
    sleep 1
done
# Expected: All requests return "1.x.x"

# Check error rate
curl -s http://old-server:8000/metrics | grep http_requests_total

# Check health
curl -s http://load-balancer/health | jq '.status'
# Expected: "healthy"
```

#### Step 3: Monitor (5 minutes)

```bash
# Monitor error rates
watch -n 5 'curl -s http://load-balancer/metrics | grep -E "http_requests_total|error_rate"'

# Check logs
tail -f /var/log/sark/sark.log | grep ERROR

# Verify business operations normal
```

#### Step 4: Document Issue

```bash
# Create incident report
cat > incidents/phase2_rollback_$(date +%Y%m%d_%H%M%S).md <<EOF
# Phase 2 Rollback Incident

**Date:** $(date)
**Severity:** High
**Action:** Rolled back to Phase 1

## Issue
[Describe issue that triggered rollback]

## Metrics at Rollback
- Error rate: [%]
- Response time p95: [ms]
- Affected users: [number]

## Root Cause
[To be determined]

## Next Steps
1. Investigate root cause
2. Fix issue in Phase 2
3. Test in staging
4. Re-attempt migration
EOF
```

---

## Full Rollback (All Components)

**When to use:** Critical failure, Phase 1 may be stopped

**Downtime:** < 15 minutes

**RTO:** < 15 minutes

### Procedure

#### Step 1: Emergency Traffic Shift (< 1 minute)

```bash
#!/bin/bash
# emergency_rollback.sh

set -e

echo "=== EMERGENCY ROLLBACK TO PHASE 1 ==="
echo "Timestamp: $(date)"
echo ""

# 1. Route all traffic to Phase 1
echo "1. Routing traffic to Phase 1..."
if systemctl is-active haproxy &>/dev/null; then
    # HAProxy
    cat > /etc/haproxy/haproxy.cfg <<'EOF'
backend sark_backend
    server sark-old 10.0.1.10:8000 weight 100
EOF
    systemctl reload haproxy
elif systemctl is-active nginx &>/dev/null; then
    # Nginx
    cat > /etc/nginx/conf.d/sark_upstream.conf <<'EOF'
upstream sark_backend {
    server 10.0.1.10:8000;
}
EOF
    systemctl reload nginx
fi

echo "   ✅ Traffic routed to Phase 1"
```

#### Step 2: Verify/Restart Phase 1 (< 2 minutes)

```bash
# 2. Check if Phase 1 is running
echo "2. Checking Phase 1 status..."
if systemctl is-active sark-phase1 &>/dev/null; then
    echo "   ✅ Phase 1 running"
else
    echo "   ⚠️  Phase 1 not running, starting..."
    systemctl start sark-phase1
    sleep 5

    if systemctl is-active sark-phase1 &>/dev/null; then
        echo "   ✅ Phase 1 started"
    else
        echo "   ❌ Phase 1 failed to start!"
        echo "   Checking logs..."
        journalctl -u sark-phase1 -n 50 --no-pager
        exit 1
    fi
fi

# 3. Verify Phase 1 health
echo "3. Verifying Phase 1 health..."
HEALTH_ATTEMPTS=0
MAX_ATTEMPTS=12

while [ $HEALTH_ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if curl -f -s http://localhost:8000/health | jq -e '.status == "healthy"' &>/dev/null; then
        echo "   ✅ Phase 1 healthy"
        break
    fi

    HEALTH_ATTEMPTS=$((HEALTH_ATTEMPTS + 1))
    echo "   Attempt $HEALTH_ATTEMPTS/$MAX_ATTEMPTS..."
    sleep 5
done

if [ $HEALTH_ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    echo "   ❌ Phase 1 health check failed!"
    exit 1
fi
```

#### Step 3: Stop Phase 2 (< 1 minute)

```bash
# 4. Stop Phase 2
echo "4. Stopping Phase 2..."
systemctl stop sark-phase2
echo "   ✅ Phase 2 stopped"
```

#### Step 4: Rollback Configuration (< 1 minute)

```bash
# 5. Restore Phase 1 configuration
echo "5. Restoring Phase 1 configuration..."
cp backups/.env.phase1_latest /opt/sark-phase1/.env
chown sark:sark /opt/sark-phase1/.env
chmod 600 /opt/sark-phase1/.env
echo "   ✅ Configuration restored"
```

#### Step 5: Database Rollback (if needed)

```bash
# 6. Rollback database (only if schema changed)
echo "6. Checking database rollback need..."
NEEDS_DB_ROLLBACK=false  # Set to true if Phase 2 modified schema

if [ "$NEEDS_DB_ROLLBACK" = true ]; then
    echo "   Executing database rollback..."

    # Stop all services
    systemctl stop sark-phase1

    # Restore database from backup
    psql -h <postgres-host> -U postgres \
        -c "DROP DATABASE sark;"
    psql -h <postgres-host> -U postgres \
        -c "CREATE DATABASE sark OWNER sark;"
    psql -h <postgres-host> -U sark -d sark \
        < backups/sark_phase1_latest.sql

    # Restore TimescaleDB
    psql -h <timescale-host> -U postgres \
        -c "DROP DATABASE sark_audit;"
    psql -h <timescale-host> -U postgres \
        -c "CREATE DATABASE sark_audit OWNER sark;"
    psql -h <timescale-host> -U sark -d sark_audit \
        < backups/sark_audit_phase1_latest.sql

    # Restart Phase 1
    systemctl start sark-phase1

    echo "   ✅ Database restored"
else
    echo "   ℹ️  No database rollback needed (schema compatible)"
fi
```

#### Step 6: Verification (< 5 minutes)

```bash
# 7. Comprehensive verification
echo "7. Running verification..."

# Health check
echo "   Checking health..."
curl -f http://localhost:8000/health || {
    echo "   ❌ Health check failed"
    exit 1
}

# Version check
echo "   Checking version..."
VERSION=$(curl -s http://localhost:8000/health | jq -r '.version')
if [[ "$VERSION" == 1.* ]]; then
    echo "   ✅ Version: $VERSION (Phase 1)"
else
    echo "   ❌ Wrong version: $VERSION"
    exit 1
fi

# API endpoint check
echo "   Checking API endpoints..."
curl -f http://localhost:8000/api/v1/servers &>/dev/null || {
    echo "   ❌ API endpoints failed"
    exit 1
}

# Database connectivity
echo "   Checking database..."
psql -h <postgres-host> -U sark -d sark \
    -c "SELECT COUNT(*) FROM servers;" &>/dev/null || {
    echo "   ❌ Database connectivity failed"
    exit 1
}

echo "   ✅ All checks passed"

# 8. Final status
echo ""
echo "=== ROLLBACK COMPLETE ==="
echo "Timestamp: $(date)"
echo "Version: $VERSION"
echo "Status: Healthy"
echo ""
echo "Next steps:"
echo "1. Investigate root cause"
echo "2. Document in incident report"
echo "3. Fix Phase 2 issues"
echo "4. Test in staging"
echo "5. Retry migration"
```

---

## Component-Specific Rollbacks

### Application Code Rollback

**When:** Code bugs in Phase 2

**RTO:** < 5 minutes

```bash
# Stop Phase 2
systemctl stop sark-phase2

# Checkout Phase 1 code
cd /opt/sark
git fetch --all
git checkout v1.x.x  # Last Phase 1 version

# Reinstall dependencies (if needed)
source venv/bin/activate
pip install -r requirements.txt

# Restart with Phase 1 code
systemctl start sark
```

### Configuration Rollback

**When:** Configuration errors

**RTO:** < 2 minutes

```bash
# Restore Phase 1 configuration
cp backups/.env.phase1_$(date +%Y%m%d) .env

# Validate
python scripts/validate_config.py

# Restart service
systemctl restart sark
```

### Dependency Rollback

**When:** Upgraded dependencies causing issues

**RTO:** < 3 minutes

```bash
# Downgrade security packages
pip install 'cryptography==41.0.7'
pip install 'setuptools==68.1.2'
pip install 'urllib3==2.3.0'

# Verify versions
pip list | grep -E "(cryptography|setuptools|urllib3)"

# Restart service
systemctl restart sark
```

### SIEM Integration Rollback

**When:** SIEM causing performance issues

**RTO:** < 1 minute

```bash
# Disable SIEM without full rollback
cat >> .env <<EOF
SPLUNK_ENABLED=false
DATADOG_ENABLED=false
EOF

# Restart service
systemctl restart sark

# Verify SIEM disabled
curl http://localhost:8000/metrics | grep siem_enabled
# Expected: siem_enabled 0
```

### Security Middleware Rollback

**When:** Security headers breaking clients

**RTO:** < 1 minute

**Note:** Cannot disable security middleware without code change

**Options:**
1. Adjust CSP policy in configuration
2. Add domains to CORS whitelist
3. Full rollback to Phase 1

```bash
# Option 1: Adjust CSP (less restrictive)
cat >> .env <<EOF
CSP_POLICY=default-src 'self' 'unsafe-inline' 'unsafe-eval'; script-src 'self' 'unsafe-inline' 'unsafe-eval'
EOF

# Restart
systemctl restart sark
```

---

## Database Rollback

### Scenario 1: No Schema Changes (Phase 2)

**Phase 2 is designed to NOT modify existing schema.**

**Rollback:** ✅ Not needed - schema is backward compatible

```bash
# Verify no schema changes
psql -h <timescale-host> -U sark -d sark_audit \
    -c "\d audit_events" | grep siem_forwarded

# If column added but not required, can keep it
# Phase 1 will ignore the column
```

### Scenario 2: Optional Column Added

**If `siem_forwarded` column was added:**

**Rollback:** ⚠️ Optional - column is nullable and backward compatible

```bash
# Option 1: Keep column (recommended)
# Phase 1 ignores it, no issues

# Option 2: Remove column (if desired)
psql -h <timescale-host> -U sark -d sark_audit <<EOF
ALTER TABLE audit_events DROP COLUMN IF EXISTS siem_forwarded;
DROP INDEX IF EXISTS idx_audit_events_siem_forwarded;
EOF
```

### Scenario 3: Schema Migration Failure

**If schema migration failed partially:**

**Rollback:** ✅ Required - restore from backup

```bash
# Stop all services
systemctl stop sark sark-phase2

# Restore PostgreSQL
psql -h <postgres-host> -U postgres <<EOF
DROP DATABASE sark;
CREATE DATABASE sark OWNER sark;
EOF

psql -h <postgres-host> -U sark -d sark \
    < backups/sark_phase1_latest.sql

# Restore TimescaleDB
psql -h <timescale-host> -U postgres <<EOF
DROP DATABASE sark_audit;
CREATE DATABASE sark_audit OWNER sark;
EOF

psql -h <timescale-host> -U sark -d sark_audit \
    < backups/sark_audit_phase1_latest.sql

# Recreate TimescaleDB extension
psql -h <timescale-host> -U postgres -d sark_audit <<EOF
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EOF

# Verify restore
psql -h <timescale-host> -U sark -d sark_audit \
    -c "SELECT COUNT(*) FROM audit_events;"

# Restart Phase 1
systemctl start sark
```

### Data Preservation

**Important:** No data loss during rollback

- ✅ All audit events preserved
- ✅ All server configurations preserved
- ✅ All policy data preserved

**Phase 2 → Phase 1 Data Flow:**
- Phase 2 audit events remain in TimescaleDB
- Phase 1 can read all events (backward compatible)
- SIEM forwarding stops (but data preserved)

---

## Verification After Rollback

### Complete Verification Checklist

```bash
#!/bin/bash
# verify_rollback.sh

echo "=== Phase 1 Rollback Verification ==="

# 1. Version check
echo "1. Checking version..."
VERSION=$(curl -s http://localhost:8000/health | jq -r '.version')
if [[ "$VERSION" == 1.* ]]; then
    echo "   ✅ Version: $VERSION (Phase 1)"
else
    echo "   ❌ Version mismatch: $VERSION"
    exit 1
fi

# 2. Health check
echo "2. Checking health..."
HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$HEALTH" = "healthy" ]; then
    echo "   ✅ Service healthy"
else
    echo "   ❌ Service unhealthy: $HEALTH"
    exit 1
fi

# 3. API endpoints
echo "3. Checking API endpoints..."
curl -f -s http://localhost:8000/api/v1/servers &>/dev/null && echo "   ✅ Servers API" || echo "   ❌ Servers API"
curl -f -s http://localhost:8000/api/v1/policy &>/dev/null && echo "   ✅ Policy API" || echo "   ❌ Policy API"
curl -f -s http://localhost:8000/metrics &>/dev/null && echo "   ✅ Metrics" || echo "   ❌ Metrics"

# 4. Database connectivity
echo "4. Checking database..."
psql -h <postgres-host> -U sark -d sark \
    -c "SELECT 1" &>/dev/null && echo "   ✅ PostgreSQL" || echo "   ❌ PostgreSQL"

psql -h <timescale-host> -U sark -d sark_audit \
    -c "SELECT 1" &>/dev/null && echo "   ✅ TimescaleDB" || echo "   ❌ TimescaleDB"

# 5. Error rate
echo "5. Checking error rate..."
ERRORS=$(curl -s http://localhost:8000/metrics | grep 'http_requests_total.*status="5' | awk '{sum+=$2} END {print sum+0}')
TOTAL=$(curl -s http://localhost:8000/metrics | grep 'http_requests_total' | awk '{sum+=$2} END {print sum+0}')
if [ "$TOTAL" -gt 0 ]; then
    ERROR_RATE=$(echo "scale=2; ($ERRORS / $TOTAL) * 100" | bc)
    echo "   Error rate: $ERROR_RATE%"
    if (( $(echo "$ERROR_RATE < 1" | bc -l) )); then
        echo "   ✅ Error rate acceptable"
    else
        echo "   ⚠️  Error rate high"
    fi
else
    echo "   ℹ️  No requests yet"
fi

# 6. Response time
echo "6. Checking response time..."
for i in {1..10}; do
    curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
done | awk '{sum+=$1; n++} END {printf "   Average: %.0fms\n", sum/n*1000}'

echo ""
echo "=== Verification Complete ==="
```

### Monitoring Dashboard

**Check key metrics:**

```bash
# Open Grafana dashboard
# URL: https://grafana.example.com/d/sark-overview

# Key panels to check:
# - Request rate (should be normal)
# - Error rate (should be < 1%)
# - Response time (should match baseline)
# - Database connections (should be stable)
```

### Business Function Verification

```bash
# Test critical business functions

# 1. Server registration
curl -X POST http://localhost:8000/api/v1/servers \
    -H "Content-Type: application/json" \
    -d '{"hostname":"test-server","ip":"10.0.0.1"}'

# 2. Policy evaluation
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
    -H "Content-Type: application/json" \
    -d '{"user":"test@example.com","resource":"test"}'

# 3. Audit event creation
# (happens automatically)

# 4. Metrics collection
curl http://localhost:8000/metrics | grep -c "^# HELP"
# Expected: Many metrics present
```

---

## Post-Rollback Actions

### Immediate Actions (Within 1 Hour)

1. **Document Incident**
   ```bash
   # Create detailed incident report
   cat > incidents/phase2_rollback_$(date +%Y%m%d_%H%M%S).md <<EOF
   # Phase 2 Rollback Incident Report

   **Date:** $(date)
   **Initiated By:** [Name]
   **Severity:** [Critical/High/Medium]
   **RTO:** [Actual time to recovery]

   ## Timeline
   - Issue detected: [Time]
   - Rollback initiated: [Time]
   - Traffic shifted: [Time]
   - Verification complete: [Time]
   - Incident resolved: [Time]

   ## Issue Description
   [Detailed description]

   ## Root Cause
   [Analysis]

   ## Impact
   - Affected users: [Number or %]
   - Duration: [Minutes]
   - Data loss: None

   ## Rollback Procedure Used
   - [Quick Rollback / Full Rollback]
   - [Components rolled back]

   ## Verification Steps
   - [Checklist of verification performed]

   ## Lessons Learned
   1. [Lesson 1]
   2. [Lesson 2]

   ## Action Items
   - [ ] Fix root cause
   - [ ] Add monitoring for issue
   - [ ] Update rollback procedures
   - [ ] Re-test migration in staging
   EOF
   ```

2. **Notify Stakeholders**
   ```bash
   # Send notification
   # Subject: SARK Phase 2 Rollback - Service Restored
   #
   # Team,
   #
   # We've rolled back the Phase 2 deployment to Phase 1 due to [issue].
   # Service is now stable and operating normally.
   #
   # Impact:
   # - Duration: [X] minutes
   # - Affected features: [None / List]
   # - Data loss: None
   #
   # Next steps:
   # - Root cause analysis: [Timeline]
   # - Fix and re-deploy: [Timeline]
   #
   # Incident report: [Link]
   ```

3. **Update Status Page**
   ```bash
   # Update status page (if applicable)
   # Status: Resolved
   # Message: Service has been restored. Phase 2 deployment postponed.
   ```

### Short-Term Actions (Within 24 Hours)

4. **Root Cause Analysis**
   - Analyze logs from Phase 2
   - Review metrics and traces
   - Identify exact failure point
   - Document findings

5. **Fix Issues**
   - Implement fixes for root cause
   - Add tests to prevent regression
   - Update documentation

6. **Test Fixes**
   - Deploy to development
   - Deploy to staging
   - Run full test suite
   - Verify fix effective

### Medium-Term Actions (Within 1 Week)

7. **Post-Mortem Meeting**
   - Schedule within 48 hours
   - Include all stakeholders
   - Review timeline
   - Identify improvements
   - Assign action items

8. **Update Procedures**
   - Update migration guide
   - Update rollback procedures
   - Add new monitoring
   - Improve automation

9. **Re-Attempt Migration**
   - Schedule new migration window
   - Communicate plan
   - Execute with fixes
   - Monitor closely

---

## Rollback Testing

### Pre-Production Rollback Testing

**Test rollback procedures before production migration:**

```bash
# In staging environment

# 1. Deploy Phase 2
[Follow migration guide]

# 2. Simulate failure
systemctl stop sark-phase2

# 3. Execute rollback
bash scripts/emergency_rollback.sh

# 4. Verify rollback successful
bash scripts/verify_rollback.sh

# 5. Document timing
echo "Rollback RTO: [Measured time]"
```

### Rollback Drill

**Schedule regular rollback drills:**

- **Frequency:** Quarterly
- **Participants:** DevOps team, on-call engineers
- **Scenario:** Random failure injection
- **Goal:** < 15 minute RTO achieved

**Drill Procedure:**

1. Announce drill (or surprise drill)
2. Inject failure (traffic shift, config error, etc.)
3. Team executes rollback
4. Measure RTO
5. Review and improve

---

## Emergency Contacts

### Rollback Support

| Role | Name | Phone | Slack |
|------|------|-------|-------|
| **DevOps Lead** | [Name] | [Phone] | @devops-lead |
| **Database Admin** | [Name] | [Phone] | @dba |
| **Platform Engineer** | [Name] | [Phone] | @platform-eng |
| **Engineering Manager** | [Name] | [Phone] | @eng-manager |

### Escalation

1. **Level 1:** On-call engineer executes rollback
2. **Level 2:** DevOps lead if rollback fails
3. **Level 3:** Engineering manager if service still down

### External Support

- **Cloud Provider:** [Support number]
- **Database Provider:** [Support number]
- **SIEM Provider:** [Support number]

---

## Rollback Metrics

### Track Rollback Performance

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **RTO (Recovery Time)** | < 15 min | [Measured] | ✅/❌ |
| **RPO (Data Loss)** | 0 | 0 | ✅ |
| **Error Rate During** | < 5% | [Measured] | ✅/❌ |
| **Verification Time** | < 5 min | [Measured] | ✅/❌ |

### Rollback History

**Track all rollbacks:**

```bash
# Log rollback
echo "$(date)|Phase2|[Issue]|[RTO]|[Impact]" >> rollback_history.log
```

---

## Appendix: Quick Reference

### Quick Commands

```bash
# Quick rollback (traffic only)
sudo systemctl reload haproxy  # After updating weights

# Stop Phase 2
sudo systemctl stop sark-phase2

# Start Phase 1
sudo systemctl start sark-phase1

# Check version
curl -s http://localhost:8000/health | jq -r '.version'

# Check health
curl -s http://localhost:8000/health | jq -r '.status'

# View logs
tail -f /var/log/sark/sark.log

# Check error rate
curl -s http://localhost:8000/metrics | grep error_rate
```

### Emergency Rollback One-Liner

```bash
# Nuclear option: immediate rollback
sudo systemctl reload haproxy && \
sudo systemctl stop sark-phase2 && \
sudo systemctl start sark-phase1 && \
curl http://localhost:8000/health
```

---

**Rollback Procedures Version:** 2.0
**Last Updated:** 2025-11-23
**Maintained By:** Engineer 3 (SIEM Lead)
**Next Review:** After each rollback incident
**Last Tested:** [Date of last rollback drill]
