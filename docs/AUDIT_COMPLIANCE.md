# Audit & Compliance Guide

**Version:** 1.6.0
**Last Updated:** January 2026

SARK provides comprehensive audit logging and compliance features to meet regulatory requirements for enterprise AI deployments.

---

## Table of Contents

1. [Overview](#overview)
2. [Audit Trail](#audit-trail)
3. [Compliance Frameworks](#compliance-frameworks)
4. [SIEM Integration](#siem-integration)
5. [Data Retention](#data-retention)
6. [Compliance Reports](#compliance-reports)
7. [Security Controls](#security-controls)
8. [Best Practices](#best-practices)

---

## Overview

### What SARK Audits

SARK maintains an immutable audit trail of:

- **Authentication Events** - All login attempts (success/failure)
- **Authorization Decisions** - All policy evaluations (allow/deny with reason)
- **Data Access** - All resource interactions (read/write/delete)
- **Configuration Changes** - All policy updates, server registrations, settings
- **Security Events** - Injection attempts, anomalies, MFA challenges
- **Administrative Actions** - User management, role changes, system config

### Immutability Guarantee

- **Append-only** - Events can only be added, never modified or deleted
- **TimescaleDB** - Time-series database optimized for audit logs
- **Tamper Detection** - Cryptographic checksums for integrity verification
- **Long-term Retention** - 90%+ compression with hypertables

---

## Audit Trail

### Event Schema

Every audit event contains:

```json
{
  "timestamp": "2026-01-18T15:30:45.123Z",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "authorization",
  "user": {
    "id": "user_abc123",
    "email": "alice@company.com",
    "role": "developer",
    "team": "backend"
  },
  "action": "query_database",
  "resource": {
    "type": "mcp_server",
    "id": "postgres-production",
    "name": "Production Database",
    "sensitivity": "high"
  },
  "result": "allowed",
  "reason": "team_match AND role_sufficient",
  "policy_version": "v1.2.3",
  "context": {
    "ip_address": "10.0.1.50",
    "user_agent": "Claude/1.0",
    "session_id": "sess_xyz789"
  },
  "parameters": {
    "query": "SELECT COUNT(*) FROM users WHERE active=true"
  },
  "response_summary": {
    "status": "success",
    "duration_ms": 42,
    "records_affected": 1
  }
}
```

### Event Types

| Event Type | Description | Retention |
|------------|-------------|-----------|
| `authentication` | Login/logout attempts | 1 year |
| `authorization` | Policy evaluation results | 1 year |
| `data_access` | Resource read/write operations | 2 years |
| `configuration` | System/policy changes | Permanent |
| `security_incident` | Injection, anomaly, breach | Permanent |
| `admin_action` | User/role management | Permanent |

### Query Examples

**All failed authentication attempts:**
```sql
SELECT
    timestamp,
    user_email,
    event_type,
    result,
    reason,
    context->>'ip_address' as ip
FROM audit_events
WHERE event_type = 'authentication'
  AND result = 'denied'
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

**High-sensitivity data access:**
```sql
SELECT
    timestamp,
    user_email,
    action,
    resource_name,
    result
FROM audit_events
WHERE resource_sensitivity = 'high'
  AND event_type = 'data_access'
  AND timestamp BETWEEN '2026-01-01' AND '2026-01-31'
ORDER BY timestamp DESC;
```

**Policy violations (denied requests):**
```sql
SELECT
    timestamp,
    user_email,
    action,
    resource_name,
    reason
FROM audit_events
WHERE result = 'denied'
  AND event_type = 'authorization'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY user_email, reason
ORDER BY COUNT(*) DESC;
```

---

## Compliance Frameworks

### SOC 2 Type II

**Trust Service Criteria:** Security, Availability, Confidentiality

**SARK Controls:**

1. **CC6.1 - Logical Access Controls**
   - ✅ Multi-factor authentication available
   - ✅ Role-based access control enforced
   - ✅ Principle of least privilege
   - ✅ Session timeout and concurrent session limits

2. **CC6.2 - System Access**
   - ✅ Unique user identification (OIDC/LDAP/SAML)
   - ✅ Authentication before access
   - ✅ Authorization policy evaluation
   - ✅ Failed login attempt monitoring

3. **CC6.3 - Access Revocation**
   - ✅ Immediate access revocation on user disable
   - ✅ Automatic session termination
   - ✅ API key deactivation
   - ✅ Audit trail of access changes

4. **CC7.2 - System Monitoring**
   - ✅ Comprehensive audit logging
   - ✅ SIEM integration for real-time alerting
   - ✅ Anomaly detection
   - ✅ Security incident tracking

5. **CC7.3 - Incident Response**
   - ✅ Automated alerts for security events
   - ✅ Incident response playbooks
   - ✅ Complete forensic audit trail
   - ✅ Breach notification logging

**Evidence Collection:**
```bash
# Generate SOC 2 compliance report for Q1 2026
python scripts/compliance/soc2_report.py \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --output reports/soc2_q1_2026.pdf
```

### PCI-DSS (Payment Card Industry)

**Requirements Met:**

**Requirement 7 - Restrict access to cardholder data**
- ✅ Role-based access control
- ✅ Data sensitivity classification (credit card = critical)
- ✅ Deny by default
- ✅ Need-to-know principle

**Requirement 8 - Identify and authenticate access**
- ✅ Unique user IDs
- ✅ Strong authentication (OIDC/LDAP/SAML + MFA)
- ✅ Multi-factor for administrative access
- ✅ Session management and timeout

**Requirement 10 - Log and monitor all access**
- ✅ Audit trail of all data access
- ✅ User identification in logs
- ✅ Timestamp on all events
- ✅ Immutable log storage
- ✅ Log retention 1+ year (cardholder data)
- ✅ Daily log review capability

**Requirement 12.10 - Incident response plan**
- ✅ Documented incident response procedures
- ✅ Automated alerting for anomalies
- ✅ Security team notification
- ✅ Forensic investigation support

**Secret Scanning:**
SARK automatically detects and redacts credit card numbers:
```
Input:  "Payment for order #123: 4532-1234-5678-9010"
Output: "Payment for order #123: [REDACTED:CREDIT_CARD]"
```

**Compliance Query:**
```sql
-- Audit all access to payment systems
SELECT
    timestamp,
    user_email,
    action,
    resource_name,
    result,
    parameters
FROM audit_events
WHERE resource_name LIKE '%payment%'
  OR resource_name LIKE '%billing%'
  OR parameters::text LIKE '%credit_card%'
ORDER BY timestamp DESC;
```

### HIPAA (Health Insurance Portability and Accountability Act)

**Security Rule Requirements:**

**§164.308(a)(3) - Workforce Security**
- ✅ Authorization and supervision
- ✅ Workforce clearance procedures
- ✅ Termination procedures (immediate access revocation)

**§164.308(a)(4) - Information Access Management**
- ✅ Access authorization (OPA policies)
- ✅ Access establishment and modification
- ✅ Isolating PHI clearinghouse functions

**§164.312(a)(1) - Access Control**
- ✅ Unique user identification
- ✅ Emergency access procedures
- ✅ Automatic log-off (session timeout)
- ✅ Encryption and decryption

**§164.312(b) - Audit Controls**
- ✅ Hardware, software, and procedural mechanisms
- ✅ Record and examine activity in systems containing PHI
- ✅ Immutable audit trail
- ✅ Comprehensive logging

**§164.312(d) - Person or Entity Authentication**
- ✅ Verify identity before accessing PHI
- ✅ Multi-factor authentication support
- ✅ Integration with healthcare IdPs

**PHI Detection:**
SARK can be configured to detect and redact PHI:
```yaml
# config/secrets_patterns.yaml
phi_patterns:
  - name: ssn
    pattern: '\b\d{3}-\d{2}-\d{4}\b'
    redaction: '[REDACTED:SSN]'
  - name: mrn
    pattern: '\bMRN[:\s]*\d{6,10}\b'
    redaction: '[REDACTED:MRN]'
```

**BAA Process:**
SARK deployments can support Business Associate Agreements:
- Documented security controls
- Breach notification procedures
- Audit trail for compliance verification
- Encryption at rest and in transit

---

## SIEM Integration

### Supported Platforms

**Splunk**
- HTTP Event Collector (HEC)
- Custom indexes per event type
- Source type tagging
- Real-time forwarding

**Datadog**
- Logs API integration
- Custom tags and attributes
- Correlation with APM metrics
- Alerting and dashboards

**Kafka**
- High-throughput event streaming
- Schema registry integration
- Partition by event type
- Exactly-once semantics

### Configuration

```yaml
# config/siem.yaml
siem:
  enabled: true
  provider: splunk

  splunk:
    hec_url: https://splunk.company.com:8088/services/collector
    token: ${SPLUNK_HEC_TOKEN}
    index: sark_audit
    source_type: sark:audit:json

  circuit_breaker:
    enabled: true
    failure_threshold: 5
    timeout_seconds: 30
    half_open_requests: 3

  dead_letter_queue:
    enabled: true
    max_retries: 3
    retry_delay_seconds: 60
```

### Event Forwarding

**Real-time Forwarding:**
- Events sent to SIEM within 1 second
- Asynchronous processing (non-blocking)
- Automatic retry on failure
- Dead letter queue for persistent failures

**Throughput:**
- 10,000+ events/min sustained
- Circuit breaker prevents overload
- Graceful degradation on SIEM failure

### Alerting

Example Splunk alerts:

```spl
# Alert on failed authentication attempts (brute force)
index=sark_audit event_type=authentication result=denied
| stats count by user_email, ip_address
| where count > 5
```

```spl
# Alert on high-sensitivity data access
index=sark_audit event_type=data_access resource_sensitivity=critical
| table timestamp, user_email, action, resource_name, result
```

```spl
# Alert on policy violations
index=sark_audit event_type=authorization result=denied
| stats count by user_email, reason
| where count > 10
```

---

## Data Retention

### Retention Periods

| Data Type | Minimum Retention | Default | Justification |
|-----------|-------------------|---------|---------------|
| Authentication logs | 90 days | 1 year | SOC 2, HIPAA |
| Authorization logs | 90 days | 1 year | SOC 2, PCI-DSS |
| Data access (general) | 90 days | 1 year | SOC 2 |
| Data access (PHI/PCI) | 1 year | 2 years | HIPAA, PCI-DSS |
| Configuration changes | Permanent | Permanent | Audit trail |
| Security incidents | Permanent | Permanent | Forensics |

### Storage Optimization

**TimescaleDB Compression:**
- Automatic compression after 7 days
- 90%+ compression ratio
- Zero query latency impact
- Continuous aggregates for dashboards

**Example:**
```sql
-- Configure compression policy
SELECT add_compression_policy('audit_events', INTERVAL '7 days');

-- Create continuous aggregate for daily summaries
CREATE MATERIALIZED VIEW audit_daily_summary
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 day', timestamp) AS day,
  event_type,
  result,
  COUNT(*) as event_count
FROM audit_events
GROUP BY day, event_type, result;
```

### Archival

**Long-term Archive (S3/Azure Blob/GCS):**
```bash
# Archive audit logs older than 2 years to S3
pg_dump -t audit_events \
  --where "timestamp < NOW() - INTERVAL '2 years'" \
  | gzip \
  | aws s3 cp - s3://company-audit-archive/sark/audit_2024.sql.gz
```

---

## Compliance Reports

### Pre-built Reports

SARK includes compliance report generators:

**Access Control Report:**
```bash
python scripts/compliance/access_control_report.py \
  --start-date 2026-01-01 \
  --end-date 2026-01-31 \
  --output reports/access_control_jan_2026.pdf
```

**Output includes:**
- Total users and roles
- Authentication success/failure rates
- Authorization allow/deny breakdown
- High-risk access patterns
- MFA adoption rate

**Data Access Report:**
```bash
python scripts/compliance/data_access_report.py \
  --sensitivity high,critical \
  --start-date 2026-01-01 \
  --end-date 2026-01-31 \
  --output reports/sensitive_data_access_jan_2026.pdf
```

**Output includes:**
- Users accessing sensitive data
- Resources accessed by sensitivity level
- Access patterns over time
- Anomalous access detection
- Failed access attempts

**Security Incident Report:**
```bash
python scripts/compliance/security_incident_report.py \
  --start-date 2026-01-01 \
  --end-date 2026-01-31 \
  --output reports/security_incidents_jan_2026.pdf
```

**Output includes:**
- Injection attempts detected/blocked
- Anomalies flagged
- Failed authentication patterns
- Policy violations
- Incident response actions

### Custom Queries

Use SQL to generate custom compliance reports:

```sql
-- User activity summary for compliance audit
SELECT
    user_email,
    COUNT(*) FILTER (WHERE event_type = 'authentication') as logins,
    COUNT(*) FILTER (WHERE event_type = 'authorization' AND result = 'allowed') as authorized_actions,
    COUNT(*) FILTER (WHERE event_type = 'authorization' AND result = 'denied') as policy_violations,
    COUNT(*) FILTER (WHERE resource_sensitivity IN ('high', 'critical')) as sensitive_access,
    MAX(timestamp) as last_activity
FROM audit_events
WHERE timestamp BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY user_email
ORDER BY sensitive_access DESC;
```

---

## Security Controls

### Control Mapping

| Control | Implementation | Evidence |
|---------|----------------|----------|
| Access Control | OPA policy engine, RBAC | Authorization audit logs |
| Authentication | OIDC/LDAP/SAML + MFA | Authentication audit logs |
| Encryption | TLS 1.3, AES-256 | Configuration audit |
| Audit Logging | TimescaleDB immutable | Audit event records |
| Incident Response | Automated alerts, playbooks | Security incident logs |
| Data Protection | Secret scanning, redaction | Redaction audit logs |
| Network Security | NetworkPolicies, firewalls | Configuration changes |
| Vulnerability Management | Automated scanning, patching | Security scan results |

### Verification Procedures

**Monthly:**
- [ ] Review audit log completeness
- [ ] Verify SIEM integration operational
- [ ] Test backup and restore procedures
- [ ] Review access control policies

**Quarterly:**
- [ ] Conduct access review (all users)
- [ ] Test incident response procedures
- [ ] Review and update security policies
- [ ] Compliance report generation
- [ ] Penetration testing

**Annually:**
- [ ] SOC 2 audit (if applicable)
- [ ] HIPAA Security Risk Assessment (if applicable)
- [ ] PCI-DSS validation (if applicable)
- [ ] Third-party security assessment

---

## Best Practices

### 1. Enable Comprehensive Logging

```yaml
# config/audit.yaml
audit:
  enabled: true
  log_all_events: true  # Don't filter - compliance requires complete trail
  include_parameters: true  # Log request parameters (redacted)
  include_responses: true  # Log response summaries
  retention_days: 730  # 2 years minimum for PCI/HIPAA
```

### 2. Implement Real-time Monitoring

- Configure SIEM integration for all environments
- Set up alerts for security events
- Monitor anomaly detection dashboards
- Review failed authentication attempts daily

### 3. Enforce MFA for Sensitive Access

```rego
# policies/mfa_requirement.rego
package sark.mfa

import future.keywords

deny[msg] {
    input.resource.sensitivity == "critical"
    not input.user.mfa_verified
    msg := "MFA required for critical resource access"
}
```

### 4. Regular Compliance Audits

- Generate monthly compliance reports
- Review access patterns quarterly
- Conduct annual third-party audits
- Document all findings and remediation

### 5. Data Minimization

- Only log necessary information
- Redact PII/PHI in logs
- Use data retention policies
- Archive old data to cold storage

### 6. Incident Response Readiness

- Document incident response procedures
- Test response playbooks quarterly
- Maintain on-call rotation
- Integrate with security team workflows

### 7. Access Reviews

```sql
-- Quarterly access review query
SELECT
    user_email,
    role,
    team,
    COUNT(DISTINCT resource_id) as resources_accessed,
    MAX(timestamp) as last_access,
    CASE
        WHEN MAX(timestamp) < NOW() - INTERVAL '90 days' THEN 'INACTIVE'
        ELSE 'ACTIVE'
    END as status
FROM audit_events
WHERE event_type = 'data_access'
  AND timestamp > NOW() - INTERVAL '90 days'
GROUP BY user_email, role, team
ORDER BY last_access DESC;
```

---

## Related Documentation

- **[Security Policy](../SECURITY.md)** - Vulnerability reporting, security features
- **[Security Best Practices](SECURITY_BEST_PRACTICES.md)** - Development guidelines
- **[Security Audit (v1.6.0)](v1.6.0/SECURITY_AUDIT.md)** - Latest security assessment
- **[Incident Response](INCIDENT_RESPONSE.md)** - Incident handling procedures
- **[OPA Policy Guide](OPA_POLICY_GUIDE.md)** - Policy authoring guide
- **[Monitoring Guide](MONITORING.md)** - Observability and alerting

---

## Support

For compliance questions:
- **GitHub Issues**: https://github.com/apathy-ca/sark/issues
- **Documentation**: https://github.com/apathy-ca/sark
- **Security**: Report via [GitHub Security Advisories](https://github.com/apathy-ca/sark/security/advisories/new)

---

**Last Updated:** January 2026 (v1.6.0)
**Compliance Frameworks:** SOC 2, PCI-DSS, HIPAA
**Review Cycle:** Quarterly
