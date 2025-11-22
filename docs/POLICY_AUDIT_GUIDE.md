# SARK Policy Audit Guide

**Version:** 1.0
**Last Updated:** 2025-11-22
**Audience:** Security Teams, Compliance Officers, Auditors

---

## Table of Contents

1. [Overview](#overview)
2. [Policy Decision Logging](#policy-decision-logging)
3. [Policy Change Tracking](#policy-change-tracking)
4. [Audit Event Schema](#audit-event-schema)
5. [Querying Audit Logs](#querying-audit-logs)
6. [Compliance Reporting](#compliance-reporting)
7. [Analytics & Insights](#analytics--insights)
8. [Audit Data Retention](#audit-data-retention)
9. [Security & Access Control](#security--access-control)
10. [Troubleshooting](#troubleshooting)

---

## Overview

SARK provides comprehensive audit trails for all policy decisions and changes, enabling:
- **Compliance**: SOC 2, ISO 27001, HIPAA, PCI-DSS requirements
- **Security**: Detect unauthorized access attempts
- **Forensics**: Investigate security incidents
- **Analytics**: Understand access patterns and policy effectiveness

### Audit Capabilities

| Feature | Description | Storage |
|---------|-------------|---------|
| **Policy Decisions** | Every authorization decision logged | PostgreSQL + SIEM |
| **Policy Changes** | All policy modifications tracked | PostgreSQL |
| **User Actions** | Authentication, API calls, admin actions | PostgreSQL + SIEM |
| **Configuration Changes** | System config modifications | PostgreSQL |
| **Access Denials** | Failed authorization attempts | PostgreSQL + SIEM |

---

## Policy Decision Logging

Every policy evaluation is logged with full context for audit purposes.

### Decision Log Schema

```json
{
  "decision_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-22T10:30:45.123Z",
  "user_id": "user-123",
  "user_email": "john.doe@example.com",
  "action": "tool:invoke",
  "resource": {
    "type": "tool",
    "id": "delete_user_account",
    "sensitivity": "HIGH"
  },
  "decision": "deny",
  "reason": "User lacks required role 'admin' for high-sensitivity tool",
  "policy_id": "rbac-v1.2.3",
  "policy_version": "1.2.3",
  "evaluation_time_ms": 45.2,
  "cache_hit": false,
  "context": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "mfa_verified": false,
    "time_of_day": "10:30",
    "request_id": "req-abc123"
  },
  "metadata": {
    "server_id": "server-456",
    "environment": "production",
    "api_version": "v1"
  }
}
```

### Decision Types

**Allow Decisions:**
- Logged at INFO level
- Includes which policy allowed access
- Records any parameter filtering applied
- Cache hit/miss status

**Deny Decisions:**
- Logged at WARNING level
- Includes detailed reason for denial
- Multiple policy violations if applicable
- Forwarded to SIEM for security monitoring

**Error Decisions:**
- Logged at ERROR level
- Policy evaluation failures
- OPA communication errors
- Fallback to deny-by-default

### Querying Policy Decisions

**PostgreSQL:**
```sql
-- Denied access attempts in last 24 hours
SELECT
  timestamp,
  user_email,
  action,
  resource->>'id' as resource_id,
  reason
FROM audit_events
WHERE event_type = 'policy_decision'
  AND decision = 'deny'
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- High-sensitivity tool access
SELECT
  user_email,
  COUNT(*) as access_count,
  COUNT(*) FILTER (WHERE decision = 'allow') as allowed,
  COUNT(*) FILTER (WHERE decision = 'deny') as denied
FROM audit_events
WHERE resource->>'sensitivity' = 'HIGH'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY user_email
ORDER BY access_count DESC;

-- Failed MFA attempts
SELECT
  timestamp,
  user_email,
  action,
  reason
FROM audit_events
WHERE decision = 'deny'
  AND reason ILIKE '%mfa%'
  AND timestamp > NOW() - INTERVAL '1 day'
ORDER BY timestamp DESC;
```

**Splunk:**
```spl
# Access denials by user
index=sark_audit decision=deny
| stats count by user_email, action
| sort -count

# High-sensitivity access pattern
index=sark_audit resource.sensitivity=HIGH
| timechart span=1h count by decision

# MFA requirement violations
index=sark_audit reason="*MFA*"
| stats count by user_email, resource.id
| where count > 3
```

**Datadog:**
```
# Access denials dashboard query
service:sark @decision:deny
| group by @user_email, @action
```

---

## Policy Change Tracking

All policy modifications are tracked with full audit trail.

### Policy Change Schema

```json
{
  "change_id": "change-789",
  "timestamp": "2025-11-22T11:00:00Z",
  "change_type": "policy_update",
  "changed_by": {
    "user_id": "admin-456",
    "user_email": "admin@example.com",
    "role": "admin"
  },
  "policy": {
    "id": "rbac-policy",
    "version_before": "1.2.2",
    "version_after": "1.2.3",
    "environment": "production"
  },
  "changes": [
    {
      "field": "rules.admin_privileges",
      "old_value": "['server:write', 'server:read']",
      "new_value": "['server:write', 'server:read', 'server:delete']",
      "change_reason": "Added delete permission for admin role"
    }
  ],
  "approval": {
    "required": true,
    "approved_by": "security-lead@example.com",
    "approval_timestamp": "2025-11-22T10:55:00Z"
  },
  "rollback_available": true,
  "rollback_version": "1.2.2"
}
```

### Change Types

| Type | Description | Requires Approval |
|------|-------------|-------------------|
| **policy_create** | New policy created | Yes |
| **policy_update** | Existing policy modified | Yes |
| **policy_delete** | Policy removed | Yes (2-person) |
| **policy_activate** | Policy enabled | Yes |
| **policy_deactivate** | Policy disabled | Yes |
| **policy_rollback** | Reverted to previous version | Yes |

### Policy Versioning

SARK maintains full version history:
- **Git-like versioning**: v1.0.0, v1.0.1, v1.1.0, v2.0.0
- **Semantic versioning**: Major.Minor.Patch
- **Rollback support**: Revert to any previous version
- **Diff tracking**: Changes between versions

**Query Policy History:**
```sql
-- Policy change history
SELECT
  timestamp,
  changed_by,
  version_before,
  version_after,
  change_reason
FROM policy_changes
WHERE policy_id = 'rbac-policy'
ORDER BY timestamp DESC;

-- Recent policy rollbacks
SELECT
  timestamp,
  policy_id,
  version_before as current_version,
  version_after as rolled_back_to,
  changed_by
FROM policy_changes
WHERE change_type = 'policy_rollback'
  AND timestamp > NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;
```

---

## Audit Event Schema

### Core Fields

All audit events include:

```python
class AuditEvent:
    id: UUID                    # Unique event ID
    timestamp: datetime         # Event timestamp (UTC)
    event_type: str            # Event category
    severity: str              # INFO, WARNING, ERROR, CRITICAL
    user_id: UUID              # Acting user
    user_email: str            # User email
    ip_address: str            # Source IP
    user_agent: str            # Client user agent
    request_id: str            # Request correlation ID
    details: dict              # Event-specific data
    siem_forwarded: datetime   # SIEM forward timestamp
```

### Event Types

| Event Type | Description | Severity | SIEM |
|------------|-------------|----------|------|
| `policy_decision` | Authorization decision | INFO/WARN | Yes |
| `policy_change` | Policy modification | INFO | Yes |
| `authentication_success` | Successful login | INFO | Yes |
| `authentication_failure` | Failed login | WARNING | Yes |
| `server_registered` | New server added | INFO | Yes |
| `server_deleted` | Server removed | WARNING | Yes |
| `api_key_created` | API key generated | INFO | Yes |
| `api_key_revoked` | API key deleted | WARNING | Yes |
| `config_change` | System configuration modified | WARNING | Yes |
| `data_export` | Audit data exported | WARNING | Yes |

### Severity Levels

**INFO**: Normal operations
- Successful authentication
- Allowed policy decisions
- Standard CRUD operations

**WARNING**: Security-relevant events
- Denied access attempts
- Policy changes
- Account modifications

**ERROR**: System errors
- Policy evaluation failures
- SIEM forwarding errors
- Database errors

**CRITICAL**: Security incidents
- Multiple failed authentication attempts
- Policy bypass attempts
- Unauthorized access attempts

---

## Querying Audit Logs

### Database Queries

**Failed Authentication Attempts:**
```sql
-- Brute force detection
SELECT
  user_email,
  COUNT(*) as failed_attempts,
  MIN(timestamp) as first_attempt,
  MAX(timestamp) as last_attempt,
  array_agg(DISTINCT ip_address) as source_ips
FROM audit_events
WHERE event_type = 'authentication_failure'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY user_email
HAVING COUNT(*) >= 5
ORDER BY failed_attempts DESC;
```

**Policy Changes by User:**
```sql
-- Admin activity audit
SELECT
  timestamp,
  user_email,
  event_type,
  details->>'policy_id' as policy_modified,
  details->>'change_reason' as reason
FROM audit_events
WHERE user_id = 'admin-user-id'
  AND event_type LIKE 'policy_%'
  AND timestamp > NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;
```

**Access Pattern Analysis:**
```sql
-- Peak usage times
SELECT
  date_trunc('hour', timestamp) as hour,
  COUNT(*) as decision_count,
  COUNT(*) FILTER (WHERE decision = 'allow') as allowed,
  COUNT(*) FILTER (WHERE decision = 'deny') as denied
FROM audit_events
WHERE event_type = 'policy_decision'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

### SIEM Queries

**Splunk Saved Searches:**
```spl
# Suspicious access patterns
index=sark_audit decision=deny
| stats count by user_email, action, resource.id
| where count > 10
| table user_email, action, resource.id, count

# Policy changes
index=sark_audit event_type=policy_*
| table timestamp, user_email, event_type, details.policy_id, details.change_reason
| sort -timestamp
```

**Datadog Monitors:**
```
# Failed authentication spike
sum(last_5m):sum:sark.auth.failures{*} by {user_email}.as_count() > 10

# Unauthorized access attempts
sum(last_15m):sum:sark.policy.denials{sensitivity:CRITICAL} > 5
```

---

## Compliance Reporting

### SOC 2 Requirements

**Type II Controls:**

**Access Control (CC6.1, CC6.2):**
```sql
-- Who accessed what resources
CREATE VIEW soc2_access_log AS
SELECT
  timestamp,
  user_email,
  action,
  resource,
  decision,
  reason,
  ip_address
FROM audit_events
WHERE event_type = 'policy_decision'
ORDER BY timestamp DESC;

-- Privileged access monitoring
CREATE VIEW soc2_privileged_access AS
SELECT
  timestamp,
  user_email,
  action,
  resource,
  decision
FROM audit_events
WHERE event_type = 'policy_decision'
  AND (resource->>'sensitivity' IN ('HIGH', 'CRITICAL')
       OR action LIKE '%:delete%'
       OR action LIKE '%:admin%')
ORDER BY timestamp DESC;
```

**Change Management (CC8.1):**
```sql
-- All policy and configuration changes
CREATE VIEW soc2_change_log AS
SELECT
  timestamp,
  event_type,
  user_email,
  details->>'policy_id' as policy,
  details->>'version_before' as old_version,
  details->>'version_after' as new_version,
  details->>'change_reason' as reason,
  details->>'approved_by' as approver
FROM audit_events
WHERE event_type IN ('policy_change', 'config_change')
ORDER BY timestamp DESC;
```

### PCI-DSS Requirements

**Requirement 10: Track and monitor all access to network resources and cardholder data**

```sql
-- Audit trail report (Requirement 10.2)
SELECT
  timestamp,
  user_email,
  event_type,
  action,
  resource,
  decision,
  ip_address,
  details
FROM audit_events
WHERE timestamp >= date_trunc('day', NOW())
ORDER BY timestamp;

-- Failed access attempts (Requirement 10.2.4)
SELECT
  timestamp,
  user_email,
  action,
  resource,
  reason,
  ip_address
FROM audit_events
WHERE decision = 'deny'
  AND timestamp >= date_trunc('day', NOW())
ORDER BY timestamp;
```

### HIPAA Compliance

**164.308(a)(1)(ii)(D): Information System Activity Review**

```sql
-- Access to PHI (Protected Health Information)
SELECT
  timestamp,
  user_email,
  action,
  resource->>'id' as resource_id,
  decision,
  details->>'phi_accessed' as phi_status
FROM audit_events
WHERE details->>'data_classification' = 'PHI'
  AND timestamp > NOW() - INTERVAL '90 days'
ORDER BY timestamp DESC;
```

### Report Generation

**Monthly Compliance Report:**
```sql
-- Generate monthly summary
SELECT
  to_char(timestamp, 'YYYY-MM') as month,
  event_type,
  COUNT(*) as event_count,
  COUNT(DISTINCT user_email) as unique_users,
  COUNT(*) FILTER (WHERE severity = 'WARNING') as warnings,
  COUNT(*) FILTER (WHERE severity = 'ERROR') as errors
FROM audit_events
WHERE timestamp > NOW() - INTERVAL '12 months'
GROUP BY month, event_type
ORDER BY month DESC, event_count DESC;
```

---

## Analytics & Insights

### Policy Effectiveness

**Denial Rate Analysis:**
```sql
-- Policies causing most denials
SELECT
  details->>'policy_id' as policy,
  COUNT(*) as denial_count,
  COUNT(DISTINCT user_email) as affected_users,
  array_agg(DISTINCT reason) as denial_reasons
FROM audit_events
WHERE event_type = 'policy_decision'
  AND decision = 'deny'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY policy
ORDER BY denial_count DESC
LIMIT 10;
```

**Cache Performance:**
```sql
-- Policy cache effectiveness
SELECT
  date_trunc('hour', timestamp) as hour,
  COUNT(*) as total_decisions,
  COUNT(*) FILTER (WHERE details->>'cache_hit' = 'true') as cache_hits,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE details->>'cache_hit' = 'true') / COUNT(*),
    2
  ) as hit_rate_pct,
  AVG((details->>'evaluation_time_ms')::float) as avg_latency_ms
FROM audit_events
WHERE event_type = 'policy_decision'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;
```

### User Behavior Analytics

**Anomaly Detection:**
```sql
-- Users with unusual access patterns
WITH user_baseline AS (
  SELECT
    user_email,
    AVG(daily_requests) as avg_daily_requests,
    STDDEV(daily_requests) as stddev_requests
  FROM (
    SELECT
      user_email,
      date_trunc('day', timestamp) as day,
      COUNT(*) as daily_requests
    FROM audit_events
    WHERE timestamp > NOW() - INTERVAL '30 days'
    GROUP BY user_email, day
  ) daily_stats
  GROUP BY user_email
),
today_activity AS (
  SELECT
    user_email,
    COUNT(*) as today_requests
  FROM audit_events
  WHERE timestamp >= date_trunc('day', NOW())
  GROUP BY user_email
)
SELECT
  t.user_email,
  t.today_requests,
  b.avg_daily_requests,
  ROUND((t.today_requests - b.avg_daily_requests) / NULLIF(b.stddev_requests, 0), 2) as z_score
FROM today_activity t
JOIN user_baseline b ON t.user_email = b.user_email
WHERE t.today_requests > b.avg_daily_requests + (2 * b.stddev_requests)
ORDER BY z_score DESC;
```

**Time-of-Day Analysis:**
```sql
-- Access patterns by hour
SELECT
  EXTRACT(HOUR FROM timestamp) as hour_of_day,
  COUNT(*) as request_count,
  COUNT(DISTINCT user_email) as unique_users,
  COUNT(*) FILTER (WHERE decision = 'deny') as denials
FROM audit_events
WHERE event_type = 'policy_decision'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY hour_of_day
ORDER BY hour_of_day;
```

---

## Audit Data Retention

### Retention Policies

| Data Type | Retention Period | Archive | Deletion |
|-----------|------------------|---------|----------|
| **Policy Decisions** | 90 days (hot) | 1 year (warm) | 7 years (cold) |
| **Authentication Events** | 90 days | 1 year | 7 years |
| **Policy Changes** | Indefinite | N/A | Never |
| **Admin Actions** | 2 years | 5 years | 7 years |
| **Error Logs** | 30 days | 90 days | 1 year |

### Archival Strategy

**Hot Storage (PostgreSQL):**
- Recent 90 days
- Fast queries
- Frequent access

**Warm Storage (S3/GCS):**
- 90 days to 1 year
- Compressed parquet files
- Occasional queries

**Cold Storage (Glacier/Coldline):**
- 1-7 years
- Compliance requirements
- Rare access

**Archival Script:**
```sql
-- Archive old audit events to S3/GCS
CREATE OR REPLACE FUNCTION archive_old_audit_events()
RETURNS void AS $$
BEGIN
  -- Export to parquet
  COPY (
    SELECT * FROM audit_events
    WHERE timestamp < NOW() - INTERVAL '90 days'
      AND timestamp >= NOW() - INTERVAL '1 year'
  ) TO PROGRAM 'parquet-tools write s3://sark-audit-archive/$(date +%Y-%m).parquet';

  -- Delete archived events
  DELETE FROM audit_events
  WHERE timestamp < NOW() - INTERVAL '90 days';

  -- Vacuum to reclaim space
  VACUUM FULL audit_events;
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly archival
SELECT cron.schedule('archive-audit-events', '0 2 1 * *', 'SELECT archive_old_audit_events()');
```

---

## Security & Access Control

### Audit Log Protection

**Immutability:**
- Audit events are insert-only (no updates/deletes)
- Database triggers prevent modifications
- Cryptographic signatures for tamper detection

**Access Control:**
```sql
-- Grant read-only access to auditors
CREATE ROLE auditor;
GRANT SELECT ON audit_events TO auditor;
GRANT SELECT ON policy_changes TO auditor;
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM auditor;
```

**Audit Trail for Audit Logs:**
```sql
-- Track who accessed audit logs
CREATE TABLE audit_log_access (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  accessed_by VARCHAR(255) NOT NULL,
  query TEXT NOT NULL,
  row_count INTEGER,
  ip_address INET
);

-- Trigger to log audit access
CREATE OR REPLACE FUNCTION log_audit_access()
RETURNS event_trigger AS $$
BEGIN
  -- Log SELECT queries on audit_events
  -- Implementation depends on audit extension
END;
$$ LANGUAGE plpgsql;
```

---

## Troubleshooting

### Missing Audit Events

**Problem:** Expected events not appearing in audit log

**Diagnosis:**
```sql
-- Check recent audit events
SELECT COUNT(*), MAX(timestamp) as last_event
FROM audit_events;

-- Check SIEM forwarding status
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE siem_forwarded IS NOT NULL) as forwarded,
  COUNT(*) FILTER (WHERE siem_forwarded IS NULL) as pending
FROM audit_events
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

**Solutions:**
1. Verify application logging level: `LOG_LEVEL=INFO`
2. Check database connectivity
3. Verify SIEM forwarding enabled: `SIEM_ENABLED=true`

### High Audit Volume

**Problem:** Audit table growing too fast

**Diagnosis:**
```sql
-- Table size
SELECT pg_size_pretty(pg_total_relation_size('audit_events'));

-- Event rate
SELECT
  date_trunc('hour', timestamp) as hour,
  COUNT(*) as events_per_hour
FROM audit_events
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY events_per_hour DESC;
```

**Solutions:**
1. Implement partitioning by date
2. Archive old events more frequently
3. Increase retention policy
4. Filter noisy events (if appropriate)

---

## Related Documentation

- [AUTHORIZATION.md](./AUTHORIZATION.md) - Policy configuration
- [SIEM_INTEGRATION.md](./siem/SIEM_INTEGRATION.md) - SIEM setup
- [OPERATIONAL_RUNBOOK.md](./OPERATIONAL_RUNBOOK.md) - Operational procedures

---

**Audit Best Practices:**
1. Review audit logs daily for anomalies
2. Set up automated alerts for security events
3. Archive old data regularly
4. Protect audit logs from tampering
5. Document all policy changes with reasons
6. Maintain 7-year retention for compliance
7. Regular compliance reporting (monthly/quarterly)
8. Test audit log restoration procedures
