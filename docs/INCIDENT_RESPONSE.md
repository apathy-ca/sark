# SARK Incident Response Runbook

**Comprehensive Incident Response Procedures and Playbooks**

**Version:** 1.0
**Last Updated:** 2025-11-22
**Classification:** Internal Use Only
**Audience:** SRE, DevOps, Security Teams, On-Call Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Incident Classification](#incident-classification)
3. [Incident Response Process](#incident-response-process)
4. [Escalation & Communication](#escalation--communication)
5. [Common Incident Playbooks](#common-incident-playbooks)
6. [Post-Incident Activities](#post-incident-activities)
7. [On-Call Procedures](#on-call-procedures)
8. [Tools & Resources](#tools--resources)

---

## Overview

### Purpose

This runbook provides standardized procedures for responding to incidents affecting SARK. Following these procedures ensures quick resolution, minimal impact, and continuous improvement.

### Incident Definition

**An incident is:**
- Any event that disrupts or degrades SARK services
- Security breach or suspected breach
- Data loss or corruption
- Performance degradation beyond acceptable thresholds
- Compliance violation

### Incident Response Goals

1. **Restore service** as quickly as possible
2. **Minimize impact** to users and data
3. **Communicate** clearly with stakeholders
4. **Document** everything for post-mortem analysis
5. **Learn** and prevent future incidents

---

## Incident Classification

### Severity Levels

#### P0 - Critical (SEV-1)

**Definition:** Complete service outage or security breach

**Examples:**
- SARK API completely down
- Database corruption or data loss
- Security breach with data exfiltration
- Authentication completely broken
- Production credentials compromised

**Response Time:**
- **Detection to Acknowledgment:** 5 minutes
- **Acknowledgment to Mitigation:** 30 minutes
- **Mitigation to Resolution:** 4 hours

**Communication:**
- Immediate notification to all stakeholders
- Status updates every 30 minutes
- Executive notification required

**Team:**
- Incident Commander (IC)
- Tech Lead
- SRE On-Call
- Security Team (if security-related)
- Communications Lead

---

#### P1 - High (SEV-2)

**Definition:** Major service degradation affecting multiple users

**Examples:**
- API response time degraded (>5x normal)
- Authentication delays affecting >50% of users
- SIEM integration down (no audit logs)
- Policy evaluation failures affecting critical operations
- Partial database outage

**Response Time:**
- **Detection to Acknowledgment:** 15 minutes
- **Acknowledgment to Mitigation:** 2 hours
- **Mitigation to Resolution:** 8 hours

**Communication:**
- Notification to stakeholders within 15 minutes
- Status updates every hour
- Manager notification required

**Team:**
- Incident Commander (IC)
- SRE On-Call
- Tech Lead (if needed)

---

#### P2 - Medium (SEV-3)

**Definition:** Minor service degradation affecting some users

**Examples:**
- Non-critical endpoint errors (<5% error rate)
- Performance degradation (2x normal latency)
- Single server registration failures
- Rate limiting too aggressive
- Monitoring gaps

**Response Time:**
- **Detection to Acknowledgment:** 1 hour
- **Acknowledgment to Mitigation:** 8 hours
- **Mitigation to Resolution:** 24 hours

**Communication:**
- Notification to team
- Status updates at shift changes
- Manager notification if not resolved in 24h

**Team:**
- SRE On-Call
- Developer (if code change needed)

---

#### P3 - Low (SEV-4)

**Definition:** Minor issue with workaround available

**Examples:**
- Documentation errors
- Cosmetic UI issues
- Non-critical logging issues
- Performance tuning needed but not urgent

**Response Time:**
- **Detection to Acknowledgment:** 4 hours
- **Acknowledgment to Mitigation:** 48 hours
- **Mitigation to Resolution:** 1 week

**Communication:**
- Ticket created in tracking system
- No immediate notification required

**Team:**
- Developer
- Documentation team (if applicable)

---

## Incident Response Process

### Phase 1: Detection & Alert

#### Alerting Channels

1. **Prometheus/Alertmanager**
   - Automated alerts to PagerDuty
   - Slack #incidents channel
   - Email to on-call

2. **SIEM (Splunk/Datadog)**
   - Security alerts
   - Unusual activity patterns
   - Failed authentication spikes

3. **User Reports**
   - Support tickets
   - Direct reports from stakeholders

#### Initial Assessment

```
When alert is received:
1. Acknowledge alert within SLA timeframe
2. Verify the issue is real (not false positive)
3. Determine severity (P0-P3)
4. Create incident ticket
5. Start incident log (shared document)
```

---

### Phase 2: Triage & Mobilization

#### Create Incident War Room

```bash
# Slack
Create incident channel: #incident-YYYY-MM-DD-description
Pin incident doc to channel

# Zoom/Google Meet
Start video call for P0/P1 incidents
Post link in incident channel

# Shared Document
Create incident log (Google Doc):
- Incident ID
- Severity
- Start time
- Impact
- Timeline
- Action items
- Current status
```

#### Assign Roles

**For P0/P1 Incidents:**

1. **Incident Commander (IC)**
   - Coordinates response
   - Makes final decisions
   - Manages communication
   - Not directly fixing the issue

2. **Tech Lead**
   - Investigates root cause
   - Implements fixes
   - Coordinates technical team

3. **Communications Lead**
   - Updates stakeholders
   - Prepares status updates
   - Manages external communication

4. **Scribe**
   - Documents timeline
   - Records decisions
   - Takes notes

**For P2/P3 Incidents:**
- Single responder (on-call engineer)
- Optional: one additional engineer

---

### Phase 3: Investigation & Diagnosis

#### Diagnostic Steps

**1. Check Overall Health**
```bash
# API health
curl https://sark.example.com/health/detailed | jq

# Check pods (Kubernetes)
kubectl get pods -n production
kubectl describe pod <pod-name> -n production

# Check logs
kubectl logs -f deployment/sark -n production --tail=100

# Check metrics
open https://grafana.example.com/d/sark-overview
```

**2. Check Dependencies**
```bash
# PostgreSQL
kubectl exec -it postgres-pod -- psql -U sark -c "SELECT 1"
kubectl exec -it postgres-pod -- psql -U sark -c "SELECT count(*) FROM pg_stat_activity"

# Redis
kubectl exec -it redis-pod -- redis-cli -a password ping
kubectl exec -it redis-pod -- redis-cli -a password INFO stats

# OPA
curl http://opa:8181/health
```

**3. Review Recent Changes**
```bash
# Check recent deployments
kubectl rollout history deployment/sark -n production

# Check recent git commits
git log --oneline --since="2 hours ago"

# Check recent configuration changes
kubectl get configmap sark-config -n production -o yaml
```

**4. Check Metrics & Logs**
```promql
# Prometheus queries

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Pod restarts
kube_pod_container_status_restarts_total{namespace="production"}

# Database connections
postgresql_connections{state="active"}

# Memory usage
container_memory_usage_bytes{pod=~"sark-.*"}
```

---

### Phase 4: Mitigation & Resolution

#### Quick Mitigations

**Rollback Deployment:**
```bash
# Kubernetes
kubectl rollout undo deployment/sark -n production

# Helm
helm rollback sark -n production

# Verify rollback
kubectl rollout status deployment/sark -n production
```

**Scale Up Resources:**
```bash
# Increase replicas
kubectl scale deployment sark --replicas=10 -n production

# Increase HPA max
kubectl patch hpa sark-hpa -n production -p '{"spec":{"maxReplicas":20}}'
```

**Restart Services:**
```bash
# Restart API
kubectl rollout restart deployment/sark -n production

# Restart PostgreSQL (CAUTION!)
kubectl delete pod postgres-0 -n production  # StatefulSet will recreate

# Restart Redis
kubectl delete pod redis-0 -n production
```

**Circuit Breaker Reset:**
```bash
# Reset SIEM circuit breaker
kubectl exec -it redis-pod -- redis-cli -a password DEL circuit:splunk:state
kubectl exec -it redis-pod -- redis-cli -a password DEL circuit:datadog:state
```

**Clear Cache:**
```bash
# Clear policy cache (if corrupted)
kubectl exec -it redis-pod -- redis-cli -a password EVAL "return redis.call('del', unpack(redis.call('keys', 'policy:decision:*')))" 0

# Clear all cache (LAST RESORT)
kubectl exec -it redis-pod -- redis-cli -a password FLUSHDB
```

---

### Phase 5: Communication

#### Status Page Update

```markdown
# Example Status Page Update

**Investigating** (Initial)
We are investigating reports of slow API response times. Users may experience degraded performance.
Posted: 2025-11-22 10:05 UTC

**Identified** (Cause found)
We have identified a database connection pool exhaustion issue causing API slowness. We are working on a fix.
Posted: 2025-11-22 10:25 UTC

**Monitoring** (Fix deployed)
We have increased the database connection pool size and are monitoring for improvement.
Posted: 2025-11-22 10:45 UTC

**Resolved** (Issue resolved)
The issue has been resolved. API response times have returned to normal.
Posted: 2025-11-22 11:15 UTC
```

#### Stakeholder Notification

**Email Template:**
```
Subject: [P0] SARK Production Incident - API Outage

Dear Stakeholders,

We are experiencing a P0 incident affecting SARK production services.

**Impact:**
- API requests failing with 503 errors
- ~100% of users affected
- Estimated duration: 2 hours

**Status:**
- Incident detected: 10:05 UTC
- Team mobilized: 10:10 UTC
- Root cause identified: 10:25 UTC (database connection exhaustion)
- Fix in progress: 10:35 UTC

**Next Update:** 11:05 UTC (or sooner if status changes)

**Incident Commander:** John Doe (john.doe@example.com)

For real-time updates, see: https://status.sark.example.com
```

---

### Phase 6: Recovery Verification

#### Verification Checklist

```bash
# 1. Health checks pass
curl https://sark.example.com/health/detailed | jq '.overall_healthy'
# Expected: true

# 2. Error rate normalized
# Check Prometheus
rate(http_requests_total{status=~"5.."}[5m]) < 0.001

# 3. Latency normal
# Check p95 < 200ms
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) < 0.2

# 4. All pods running
kubectl get pods -n production | grep sark | grep -c Running
# Expected: All replicas

# 5. Database healthy
kubectl exec -it postgres-pod -- psql -U sark -c "SELECT 1"

# 6. Redis healthy
kubectl exec -it redis-pod -- redis-cli -a password ping

# 7. SIEM forwarding
# Check metrics for successful events
siem_events_forwarded_total{siem="splunk"}

# 8. User validation
# Ask a few users to test key workflows
```

---

## Escalation & Communication

### Escalation Matrix

| Severity | First Contact | Escalate After | Escalate To |
|----------|---------------|----------------|-------------|
| **P0** | On-Call SRE | Immediate | Engineering Manager, VP Eng |
| **P1** | On-Call SRE | 2 hours | Engineering Manager |
| **P2** | On-Call SRE | 8 hours | Engineering Manager |
| **P3** | Developer | 48 hours | Team Lead |

### Communication Channels

**Internal:**
- Slack #incidents (all incidents)
- PagerDuty (P0/P1 only)
- Email (stakeholder updates)
- Zoom/Meet (war room for P0/P1)

**External:**
- Status page (https://status.sark.example.com)
- Customer email (major incidents only)
- Social media (if public-facing)

### Communication Cadence

| Severity | Update Frequency |
|----------|------------------|
| **P0** | Every 30 minutes |
| **P1** | Every hour |
| **P2** | Every 4 hours |
| **P3** | At shift change |

---

## Common Incident Playbooks

### Playbook 1: API Completely Down (P0)

**Symptoms:**
- All API requests return 503 errors
- Health check endpoint unreachable
- Pods crash-looping or not ready

**Initial Response:**
```bash
# 1. Check pod status
kubectl get pods -n production -l app=sark

# 2. Check recent deployments
kubectl rollout history deployment/sark -n production

# 3. Check logs for crash reason
kubectl logs deployment/sark -n production --tail=50
```

**Common Causes & Fixes:**

**Cause 1: Bad Deployment**
```bash
# Rollback to previous version
kubectl rollout undo deployment/sark -n production

# Verify rollback
kubectl rollout status deployment/sark -n production
```

**Cause 2: Database Unreachable**
```bash
# Check database pod
kubectl get pod postgres-0 -n production
kubectl logs postgres-0 -n production

# Check database connectivity
kubectl exec -it sark-pod -- curl postgres:5432

# Fix: Restart database if needed
kubectl delete pod postgres-0 -n production
```

**Cause 3: Out of Memory (OOMKilled)**
```bash
# Check pod events
kubectl describe pod sark-pod -n production | grep OOM

# Temporary fix: Increase memory limits
kubectl set resources deployment sark --limits=memory=4Gi -n production

# Permanent fix: Investigate memory leak
```

**Cause 4: Configuration Error**
```bash
# Check ConfigMap/Secrets
kubectl get configmap sark-config -n production -o yaml
kubectl get secret sark-secrets -n production -o yaml

# Rollback configuration
kubectl apply -f k8s/configmap.yaml.backup
kubectl rollout restart deployment/sark -n production
```

---

### Playbook 2: High Latency (P1)

**Symptoms:**
- API response time >1 second (5x normal)
- Timeout errors
- Users reporting slowness

**Initial Response:**
```bash
# 1. Check current latency
curl -w "@curl-format.txt" https://sark.example.com/api/v1/servers

# 2. Check Prometheus
# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 3. Check resource usage
kubectl top pods -n production
```

**Common Causes & Fixes:**

**Cause 1: Database Slow Queries**
```sql
-- Connect to database
kubectl exec -it postgres-pod -- psql -U sark

-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Fix: Run VACUUM
VACUUM ANALYZE;

-- Fix: Add missing index
CREATE INDEX CONCURRENTLY idx_servers_status ON servers(status);
```

**Cause 2: Cache Miss Rate High**
```bash
# Check cache hit rate
kubectl exec -it redis-pod -- redis-cli -a password INFO stats | grep keyspace_hits
kubectl exec -it redis-pod -- redis-cli -a password INFO stats | grep keyspace_misses

# Calculate hit rate:
# hit_rate = hits / (hits + misses)

# If <70%, increase cache TTL
# Edit ConfigMap
kubectl edit configmap sark-config -n production
# POLICY_CACHE_TTL_HIGH=300  (increase from 60)

kubectl rollout restart deployment/sark -n production
```

**Cause 3: OPA Slow**
```bash
# Check OPA latency
curl http://opa:8181/health | jq

# Check OPA metrics
curl http://opa:8181/metrics | grep rego_query

# Fix: Optimize policies (remove nested loops)
# Fix: Scale OPA horizontally
kubectl scale deployment opa --replicas=5 -n production
```

**Cause 4: Insufficient Resources**
```bash
# Check CPU/memory usage
kubectl top pods -n production

# If >80%, scale up
kubectl scale deployment sark --replicas=10 -n production

# Or increase HPA targets
kubectl patch hpa sark-hpa -p '{"spec":{"targetCPUUtilizationPercentage":60}}'
```

---

### Playbook 3: Authentication Failures (P0/P1)

**Symptoms:**
- Users unable to login
- 401 errors on all requests
- "Invalid credentials" for valid users

**Initial Response:**
```bash
# 1. Check authentication service
kubectl logs deployment/sark -n production | grep -i auth

# 2. Test login directly
curl -X POST https://sark.example.com/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password"}'

# 3. Check dependencies
kubectl get pods -n production | grep -E "(ldap|oidc|redis)"
```

**Common Causes & Fixes:**

**Cause 1: LDAP Server Down**
```bash
# Check LDAP connectivity
kubectl exec -it sark-pod -- curl ldap://openldap:389

# Check LDAP pod
kubectl get pod openldap-0 -n production
kubectl logs openldap-0 -n production

# Fix: Restart LDAP
kubectl delete pod openldap-0 -n production
```

**Cause 2: Redis Down (Session Store)**
```bash
# Check Redis
kubectl exec -it redis-pod -- redis-cli -a password ping

# If down, restart
kubectl delete pod redis-0 -n production

# WARNING: This will log out all users!
```

**Cause 3: JWT Secret Changed**
```bash
# Check if JWT secret was rotated
kubectl get secret jwt-keys -n production -o yaml

# If secret changed recently, old tokens are invalid
# Solution: Users must re-login

# Communication:
# "We recently rotated security credentials. Please log in again."
```

**Cause 4: Token Validation Failing**
```bash
# Check logs for JWT validation errors
kubectl logs deployment/sark -n production | grep -i "jwt"

# Common issues:
# - Clock skew (check NTP)
# - Expired tokens (increase TTL temporarily)
# - Wrong algorithm (check JWT_ALGORITHM env var)

# Fix clock skew
kubectl exec -it sark-pod -- ntpdate -s time.nist.gov
```

---

### Playbook 4: Database Outage (P0)

**Symptoms:**
- Database connection errors
- "Connection refused" or "Connection timeout"
- All database-dependent operations failing

**Initial Response:**
```bash
# 1. Check database pod
kubectl get pod postgres-0 -n production
kubectl describe pod postgres-0 -n production

# 2. Check database logs
kubectl logs postgres-0 -n production --tail=50

# 3. Check database health
kubectl exec -it postgres-0 -- pg_isready -U sark
```

**Common Causes & Fixes:**

**Cause 1: Pod Crashed**
```bash
# Check pod events
kubectl describe pod postgres-0 -n production

# If OOMKilled
kubectl set resources statefulset postgres \
  --limits=memory=8Gi \
  -n production

# If CrashLoopBackOff, check logs
kubectl logs postgres-0 -n production --previous
```

**Cause 2: Disk Full**
```bash
# Check disk usage
kubectl exec -it postgres-0 -- df -h

# If >90%, emergency cleanup
kubectl exec -it postgres-0 -- psql -U sark -c "VACUUM FULL"

# Expand volume (if cloud provider supports)
kubectl edit pvc postgres-data-postgres-0 -n production
# Increase size, then restart pod
```

**Cause 3: Too Many Connections**
```bash
# Check connection count
kubectl exec -it postgres-0 -- psql -U sark -c "SELECT count(*) FROM pg_stat_activity"

# Check max connections
kubectl exec -it postgres-0 -- psql -U sark -c "SHOW max_connections"

# If at limit, kill idle connections
kubectl exec -it postgres-0 -- psql -U sark -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state = 'idle'
  AND state_change < NOW() - INTERVAL '5 minutes'
"

# Increase max_connections (restart required)
kubectl exec -it postgres-0 -- psql -U sark -c "ALTER SYSTEM SET max_connections = 200"
kubectl delete pod postgres-0 -n production
```

**Cause 4: Corrupted Data**
```bash
# Check for corruption
kubectl exec -it postgres-0 -- psql -U sark -c "
  SELECT pg_database.datname, pg_database_size(pg_database.datname)
  FROM pg_database
"

# If corruption detected, restore from backup
# LAST RESORT - DATA LOSS POSSIBLE

# 1. Stop application
kubectl scale deployment sark --replicas=0 -n production

# 2. Restore from latest backup
kubectl exec -it postgres-0 -- /restore-backup.sh

# 3. Verify restoration
kubectl exec -it postgres-0 -- psql -U sark -c "SELECT count(*) FROM servers"

# 4. Restart application
kubectl scale deployment sark --replicas=5 -n production
```

---

### Playbook 5: SIEM Integration Down (P1)

**Symptoms:**
- Audit events not appearing in Splunk/Datadog
- Circuit breaker open
- SIEM forwarding metrics show failures

**Initial Response:**
```bash
# 1. Check SIEM metrics
curl http://localhost:9090/api/v1/query?query=siem_events_forwarded_total
curl http://localhost:9090/api/v1/query?query=siem_events_failed_total

# 2. Check circuit breaker state
kubectl exec -it redis-pod -- redis-cli -a password GET circuit:splunk:state
kubectl exec -it redis-pod -- redis-cli -a password GET circuit:datadog:state
```

**Common Causes & Fixes:**

**Cause 1: Splunk HEC Token Invalid**
```bash
# Test HEC token manually
curl -k https://splunk.example.com:8088/services/collector/event \
  -H "Authorization: Splunk $SPLUNK_HEC_TOKEN" \
  -d '{"event":"test"}'

# If 401/403, token is invalid
# Fix: Update token in secret
kubectl create secret generic sark-siem-secrets \
  --from-literal=splunk_hec_token='new-valid-token' \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/sark -n production
```

**Cause 2: Network Connectivity**
```bash
# Test connectivity from pod
kubectl exec -it sark-pod -- curl -I https://splunk.example.com:8088

# If connection refused, check firewall rules
# If timeout, check network policies

# Fix: Update network policy to allow SIEM egress
```

**Cause 3: Circuit Breaker Open (Too Many Failures)**
```bash
# Check failure count
kubectl exec -it redis-pod -- redis-cli -a password GET circuit:splunk:failure

# Reset circuit breaker
kubectl exec -it redis-pod -- redis-cli -a password DEL circuit:splunk:state
kubectl exec -it redis-pod -- redis-cli -a password DEL circuit:splunk:failure

# Monitor for recovery
watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=siem_events_forwarded_total | jq'
```

**Cause 4: Rate Limited by SIEM**
```bash
# Check SIEM rate limits

# Datadog: 429 errors indicate rate limiting
# Fix: Increase batch size, decrease frequency
kubectl edit configmap sark-config -n production
# SIEM_BATCH_SIZE=200  (increase from 100)
# SIEM_BATCH_TIMEOUT_SECONDS=10  (increase from 5)

kubectl rollout restart deployment/sark -n production
```

---

### Playbook 6: Security Incident (P0)

**Symptoms:**
- Unauthorized access detected
- Suspicious audit log entries
- Failed login attempts spike
- Data exfiltration suspected

**Initial Response (DO NOT DELAY):**

```bash
# 1. IMMEDIATELY engage Security Team
# PagerDuty: @security-team
# Slack: #security-incidents
# Email: security@example.com

# 2. Preserve evidence (DO NOT modify logs/systems yet)
# Take snapshots of:
kubectl exec -it postgres-pod -- pg_dump sark > evidence-db-$(date +%s).sql
kubectl exec -it redis-pod -- redis-cli -a password SAVE
kubectl logs deployment/sark -n production --since=24h > evidence-logs-$(date +%s).log

# 3. Isolate affected systems (if compromise confirmed)
# Block network access
kubectl apply -f network-policy-lockdown.yaml

# 4. Rotate all credentials (CRITICAL)
kubectl delete secret sark-secrets -n production
# Generate new secrets
# Update applications with new secrets
```

**Security Incident Workflow:**

1. **Detection** (0 minutes)
   - Alert received
   - Security team paged
   - Incident commander assigned

2. **Containment** (5-15 minutes)
   - Isolate affected systems
   - Block malicious IP addresses
   - Revoke compromised credentials

3. **Investigation** (30 minutes - 4 hours)
   - Analyze logs
   - Identify attack vector
   - Determine scope of compromise

4. **Eradication** (2-8 hours)
   - Remove malware/backdoors
   - Patch vulnerabilities
   - Close attack vector

5. **Recovery** (4-24 hours)
   - Restore from clean backups if needed
   - Verify systems clean
   - Re-enable services gradually

6. **Post-Incident** (1-2 weeks)
   - Forensic analysis
   - Security improvements
   - Compliance notifications (if required)

---

## Post-Incident Activities

### Incident Timeline

**Document complete timeline:**
```
2025-11-22 10:05 UTC - Alert received (Prometheus: high error rate)
2025-11-22 10:07 UTC - On-call acknowledged alert
2025-11-22 10:10 UTC - Severity determined: P0
2025-11-22 10:12 UTC - War room created (#incident-2025-11-22-api-down)
2025-11-22 10:15 UTC - Team mobilized (IC: John Doe, Tech Lead: Jane Smith)
2025-11-22 10:20 UTC - Initial investigation started
2025-11-22 10:25 UTC - Root cause identified: database connection exhaustion
2025-11-22 10:30 UTC - Fix implemented: increased connection pool
2025-11-22 10:35 UTC - Deployment rolled out
2025-11-22 10:40 UTC - Monitoring for recovery
2025-11-22 10:50 UTC - Metrics normalized
2025-11-22 11:00 UTC - Incident resolved
2025-11-22 11:15 UTC - Post-incident activities started
```

### Post-Mortem

**Schedule within 48 hours of incident resolution**

**Participants:**
- Incident Commander
- Tech Lead
- On-call engineer(s)
- Engineering Manager
- Product Manager (if customer-impacting)

**Agenda:**
1. Timeline review (5 min)
2. What went well (10 min)
3. What could be improved (15 min)
4. Root cause analysis (15 min)
5. Action items (15 min)

**Post-Mortem Template:**
```markdown
# Post-Mortem: API Outage - 2025-11-22

## Summary
On 2025-11-22 at 10:05 UTC, SARK API experienced a complete outage lasting 55 minutes. All API requests returned 503 errors, affecting 100% of users.

## Impact
- **Duration:** 55 minutes (10:05 - 11:00 UTC)
- **Users Affected:** ~1,000 active users
- **Requests Failed:** ~25,000 requests
- **Revenue Impact:** Estimated $5,000 (downtime SLA credits)
- **Severity:** P0

## Root Cause
Database connection pool exhaustion caused by:
1. Connection pool size too small (20 connections)
2. Increased traffic (2x normal load)
3. Long-running queries not timing out
4. Connections not being released properly

## Timeline
[Insert detailed timeline from above]

## What Went Well
1. Alert fired within 1 minute of issue
2. On-call responded quickly (2 minutes)
3. Team mobilized efficiently
4. Root cause identified quickly (20 minutes)
5. Fix deployed rapidly (25 minutes)
6. Clear communication to stakeholders

## What Could Be Improved
1. Connection pool monitoring not alerting before exhaustion
2. No automated scaling for connection pool
3. Insufficient load testing in staging
4. Missing circuit breaker for database connections
5. Documentation for this scenario was unclear

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| Increase connection pool to 50 | Jane Smith | 2025-11-23 | ✅ Done |
| Add connection pool monitoring | John Doe | 2025-11-25 | In Progress |
| Implement DB circuit breaker | DevOps Team | 2025-11-30 | TODO |
| Run load test in staging | QA Team | 2025-12-01 | TODO |
| Update incident runbook | SRE Team | 2025-11-24 | ✅ Done |
| Add connection timeout (30s) | Jane Smith | 2025-11-23 | ✅ Done |

## Lessons Learned
1. **Monitoring Gaps:** We need better leading indicators (connection pool usage) not just lagging indicators (error rate)
2. **Capacity Planning:** Connection pool size should be validated during load tests
3. **Defense in Depth:** Circuit breakers needed for all critical dependencies
4. **Documentation:** Incident runbooks need to be tested and kept up-to-date

## Follow-up
- Review all connection pool sizes across services
- Implement automated scaling for critical resources
- Schedule quarterly disaster recovery exercises
```

---

## On-Call Procedures

### On-Call Schedule

**Rotation:** Weekly rotation
**Handoff:** Monday 9 AM local time
**Requirements:**
- Laptop with VPN access
- PagerDuty app installed
- Slack on phone
- Access to all production systems

### On-Call Handoff Checklist

**From previous on-call:**
- [ ] Review any ongoing incidents
- [ ] Review any monitoring anomalies
- [ ] Share any relevant context
- [ ] Confirm next on-call has access

**New on-call:**
- [ ] Verify PagerDuty notifications working
- [ ] Test VPN access
- [ ] Review recent deployments
- [ ] Review current system status
- [ ] Check Runbook for any updates

### On-Call Expectations

**Response Times:**
- **P0:** 5 minutes (acknowledge alert)
- **P1:** 15 minutes
- **P2:** 1 hour
- **P3:** 4 hours

**During On-Call Week:**
- Available to respond 24/7
- Laptop and phone accessible
- Stable internet connection
- If unavailable, arrange backup

### Escalation Contacts

```
On-Call SRE → Engineering Manager → VP Engineering → CTO
     ↓              ↓                      ↓           ↓
Security Team   Product Team          Executive     CEO
(for security)  (for product)          Team
```

**Contact Information:**
```yaml
on_call_sre:
  pagerduty: sre-on-call
  slack: @sre-on-call
  phone: (555) 123-4567

engineering_manager:
  name: Jane Smith
  email: jane.smith@example.com
  phone: (555) 234-5678

vp_engineering:
  name: John Doe
  email: john.doe@example.com
  phone: (555) 345-6789

security_team:
  pagerduty: security-team
  email: security@example.com
  phone: (555) 456-7890
```

---

## Tools & Resources

### Essential Tools

**Monitoring & Alerting:**
- Prometheus: https://prometheus.example.com
- Grafana: https://grafana.example.com
- PagerDuty: https://example.pagerduty.com
- Alertmanager: https://alertmanager.example.com

**Logging:**
- Splunk: https://splunk.example.com
- Datadog: https://app.datadoghq.com
- Kubernetes logs: `kubectl logs`

**Infrastructure:**
- Kubernetes Dashboard: https://k8s-dashboard.example.com
- AWS Console: https://console.aws.amazon.com
- GCP Console: https://console.cloud.google.com

**Communication:**
- Slack: https://example.slack.com
- Status Page: https://status.sark.example.com
- Incident Doc Template: https://docs.google.com/...

**Documentation:**
- Runbooks: https://wiki.example.com/runbooks
- Architecture Docs: https://wiki.example.com/architecture
- API Docs: https://docs.sark.example.com

### Quick Commands Reference

```bash
# Health checks
curl https://sark.example.com/health/detailed | jq

# Check pods
kubectl get pods -n production -l app=sark

# Check logs
kubectl logs -f deployment/sark -n production --tail=100

# Rollback deployment
kubectl rollout undo deployment/sark -n production

# Scale up
kubectl scale deployment sark --replicas=10 -n production

# Check database
kubectl exec -it postgres-0 -- psql -U sark -c "SELECT 1"

# Check Redis
kubectl exec -it redis-0 -- redis-cli -a password ping

# Check metrics
curl http://prometheus:9090/api/v1/query?query=up

# Check circuit breaker
kubectl exec -it redis-0 -- redis-cli -a password GET circuit:splunk:state
```

---

## Appendix

### Incident Severity Matrix

| Impact → <br> Duration ↓ | No Impact | Single User | Multiple Users | All Users |
|--------------------------|-----------|-------------|----------------|-----------|
| **< 5 minutes** | P3 | P3 | P2 | P1 |
| **5-30 minutes** | P3 | P2 | P1 | P0 |
| **30 min - 2 hours** | P2 | P1 | P0 | P0 |
| **> 2 hours** | P1 | P0 | P0 | P0 |

### Incident Report Template

```markdown
# Incident Report: [Brief Description]

**Incident ID:** INC-2025-11-22-001
**Date:** 2025-11-22
**Duration:** 55 minutes
**Severity:** P0
**Status:** Resolved

## Executive Summary
[1-2 sentence summary of incident and impact]

## Technical Details
**Root Cause:** [Detailed root cause]
**Affected Systems:** [List of systems]
**Error Messages:** [Key error messages]

## Impact
- **Users Affected:** [Number/percentage]
- **Services Down:** [List]
- **Data Loss:** [Yes/No - if yes, details]
- **Revenue Impact:** [Estimate]

## Response
**Detection Time:** [Timestamp]
**Response Time:** [Duration]
**Resolution Time:** [Duration]
**Mitigation:** [Actions taken]

## Follow-up Actions
[Bulleted list of action items with owners and due dates]

## Attachments
- Post-mortem document: [Link]
- Incident log: [Link]
- Metrics/graphs: [Link]
```

---

**This runbook is a living document. Update after each incident with lessons learned.**

**For urgent incidents, contact:** PagerDuty @sre-on-call | Slack #incidents | Phone: (555) 123-4567

**Last Updated:** 2025-11-22 | **Next Review:** 2026-02-22
