# SARK Incident Response Runbook

## Incident Types and Response Procedures

### 1. Policy Evaluation Failure

**Symptoms:**
- Authorization decisions failing
- 500 errors from OPA
- High latency on policy endpoints

**Immediate Actions:**

```bash
# Check OPA cluster health
kubectl get pods -n sark-system -l app=opa

# Review OPA logs
kubectl logs -n sark-system -l app=opa --tail=100

# Verify policy bundle loaded
kubectl exec -n sark-system deployment/opa -- \
  curl http://localhost:8181/v1/policies
```

**Recovery Steps:**

1. If OPA pods are down:
```bash
kubectl scale deploy/opa -n sark-system --replicas=5
```

2. If policy is corrupt:
```bash
# Rollback to previous ConfigMap version
kubectl rollout undo deployment/opa -n sark-system
```

3. If persistent issues:
```bash
# Enable fail-open mode (EMERGENCY ONLY)
# This should be done via feature flag in code
# DO NOT use in production without approval
```

**Post-Incident:**
- Review policy changes in last 24 hours
- Update alerting thresholds
- Document lessons learned

---

### 2. Database Connection Failure

**Symptoms:**
- API returning 500 errors
- "connection refused" in logs
- Database queries timing out

**Immediate Actions:**

```bash
# Check database pods
kubectl get pods -n sark-system | grep postgres

# Check database logs
kubectl logs -n sark-system postgres-0

# Verify network connectivity
kubectl exec -it deployment/sark-api -n sark-system -- \
  nc -zv postgres 5432
```

**Recovery Steps:**

1. Restart database pod if needed:
```bash
kubectl delete pod postgres-0 -n sark-system
```

2. Scale API to reduce connection load:
```bash
kubectl scale deployment/sark-api --replicas=2 -n sark-system
```

3. Check connection pool settings:
```bash
kubectl describe deployment/sark-api -n sark-system | grep POOL
```

---

### 3. High API Latency

**Symptoms:**
- p95 latency >200ms
- Slow response times
- Client timeouts

**Immediate Actions:**

```bash
# Check resource utilization
kubectl top pods -n sark-system

# Review slow queries
kubectl logs deployment/sark-api -n sark-system | grep "slow_query"

# Check external dependencies
kubectl exec deployment/sark-api -n sark-system -- \
  curl -w "@curl-format.txt" http://opa:8181/health
```

**Recovery Steps:**

1. Scale horizontally:
```bash
kubectl scale deployment/sark-api --replicas=10 -n sark-system
```

2. Check Redis cache hit rate:
```bash
kubectl exec deployment/redis -n sark-system -- \
  redis-cli INFO stats | grep keyspace
```

3. Review database query plans

---

### 4. Audit Events Not Recording

**Symptoms:**
- Missing audit events in TimescaleDB
- Gaps in audit trail
- Compliance dashboard showing no data

**Immediate Actions:**

```bash
# Check TimescaleDB status
kubectl get pods -n sark-system | grep timescale

# Verify API can connect
kubectl logs deployment/sark-api -n sark-system | grep timescale

# Check disk space
kubectl exec timescaledb-0 -n sark-system -- df -h
```

**Recovery Steps:**

1. Check batch processing:
```bash
# Review audit service logs
kubectl logs deployment/sark-api -n sark-system | grep audit_batch
```

2. If disk full:
```bash
# Extend PVC or enable compression
kubectl edit pvc timescaledb-data -n sark-system
```

3. Verify data integrity:
```sql
SELECT COUNT(*), DATE_TRUNC('hour', timestamp) as hour
FROM audit_events
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;
```

---

### 5. Security Incident

**Symptoms:**
- Unusual authorization patterns
- Failed login attempts
- Suspicious tool invocations

**Immediate Actions:**

1. **Identify scope:**
```bash
# Check recent audit events
kubectl exec timescaledb-0 -n sark-system -- \
  psql -U sark sark_audit -c \
  "SELECT * FROM audit_events WHERE severity='CRITICAL' AND timestamp > NOW() - INTERVAL '1 hour';"
```

2. **Isolate affected resources:**
```bash
# Disable compromised server
curl -X PATCH http://sark-api:8000/api/v1/servers/{server_id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "inactive"}'
```

3. **Rotate credentials:**
```bash
# Update secrets
kubectl delete secret sark-secrets -n sark-system
kubectl create secret generic sark-secrets \
  --from-literal=secret-key=<new-key> \
  -n sark-system

# Rolling restart
kubectl rollout restart deployment/sark-api -n sark-system
```

---

## Escalation Procedures

### Level 1 - On-Call Engineer
- Initial triage
- Follow runbooks
- Attempt recovery

### Level 2 - Senior SRE
- Complex incidents
- Multi-service failures
- Architecture changes needed

**Escalate if:**
- Incident not resolved in 30 minutes
- Data loss suspected
- Security breach confirmed

### Level 3 - Management + Security
- Major security incidents
- Compliance violations
- Customer impact

**Escalate if:**
- Sensitive data exposed
- Regulatory requirements affected
- Media/PR involvement

---

## Communication Templates

### Internal Status Update

```
Subject: [SARK] Incident Update - <Brief Description>

Status: Investigating / Identified / Resolved
Severity: P0 (Critical) / P1 (High) / P2 (Medium) / P3 (Low)
Start Time: YYYY-MM-DD HH:MM UTC
Impact: <Description of user impact>

Current Situation:
<What we know>

Actions Taken:
<What we've done>

Next Steps:
<What we're doing next>

ETA to Resolution: <Best estimate>
```

### Customer Communication

```
Subject: Service Disruption Notice - SARK MCP Governance

We are currently experiencing issues with SARK authorization services.

Impact:
- MCP server registrations may be delayed
- Tool invocations may experience increased latency

Status: We are actively working on resolution
ETA: Approximately <X> hours

We will provide updates every 30 minutes.

For urgent issues, please contact: support@your-company.com
```

---

## Post-Incident Review Template

### Incident Summary

- **Date:** YYYY-MM-DD
- **Duration:** X hours
- **Severity:** P0/P1/P2/P3
- **Services Affected:** List of services

### Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM      | Incident detected |
| HH:MM      | Team notified |
| HH:MM      | Root cause identified |
| HH:MM      | Fix deployed |
| HH:MM      | Services restored |

### Root Cause

Detailed explanation of what happened and why.

### Impact

- Number of affected users
- Duration of impact
- Data integrity status

### Resolution

What was done to resolve the incident.

### Lessons Learned

What went well:
- ...

What could be improved:
- ...

### Action Items

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| ...    | ...   | ...      | ...      |

---

**Emergency Contacts:**

- On-Call Engineer: [PagerDuty/Slack]
- Platform Lead: [Contact Info]
- Security Team: [Contact Info]
- CTO: [Contact Info]
