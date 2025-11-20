# SARK Security Guide

**Enterprise-Grade Security Best Practices for MCP Governance**

---

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Secrets Management](#secrets-management)
4. [Network Security](#network-security)
5. [Data Protection](#data-protection)
6. [Audit & Compliance](#audit--compliance)
7. [Threat Detection](#threat-detection)
8. [Vulnerability Management](#vulnerability-management)
9. [Security Hardening](#security-hardening)
10. [Incident Response](#incident-response)

---

## Security Architecture

### Defense in Depth

SARK implements multiple security layers:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Network Perimeter                              │
│ - WAF (Web Application Firewall)                        │
│ - DDoS Protection                                        │
│ - TLS 1.3 Termination                                   │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│ Layer 2: API Gateway (Kong)                             │
│ - Rate Limiting                                          │
│ - Request Validation                                     │
│ - MCP Protocol Enforcement                               │
│ - OAuth 2.0 / OIDC                                       │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Application Security                           │
│ - Input Validation (Pydantic)                           │
│ - OPA Authorization                                      │
│ - CSRF Protection                                        │
│ - SQL Injection Prevention (SQLAlchemy)                 │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Service Mesh (mTLS)                            │
│ - Mutual TLS Between Services                           │
│ - Service Identity Verification                         │
│ - Encrypted Service-to-Service Communication            │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│ Layer 5: Data Layer                                     │
│ - Encryption at Rest (AES-256)                          │
│ - Column-Level Encryption for Sensitive Data            │
│ - Database Access Control                               │
│ - Audit Logging                                          │
└─────────────────────────────────────────────────────────┘
```

### Zero-Trust Principles

**Never Trust, Always Verify:**

1. **Explicit Verification** - Every request authenticated and authorized
2. **Least Privilege Access** - Minimum permissions required
3. **Assume Breach** - Limit blast radius of compromises
4. **Continuous Validation** - Real-time policy evaluation

---

## Authentication & Authorization

### OAuth 2.0 / OpenID Connect Integration

**Recommended Identity Providers:**
- Okta
- Auth0
- Azure AD
- Google Workspace
- AWS Cognito

**Configuration:**

```python
# src/sark/config/settings.py
OAUTH_PROVIDER = "okta"
OAUTH_CLIENT_ID = "your-client-id"
OAUTH_CLIENT_SECRET = vault("oauth/client-secret")
OAUTH_DISCOVERY_URL = "https://your-tenant.okta.com/.well-known/openid-configuration"
OAUTH_REDIRECT_URI = "https://sark.company.com/auth/callback"
OAUTH_SCOPES = ["openid", "profile", "email", "groups"]
```

### JWT Token Validation

**Required Claims:**
```json
{
  "iss": "https://your-tenant.okta.com",
  "sub": "user-id-12345",
  "aud": "sark-api",
  "exp": 1699999999,
  "iat": 1699996399,
  "email": "user@company.com",
  "groups": ["engineering", "mcp-users"],
  "role": "developer"
}
```

**Token Security:**
- **Algorithm**: RS256 (not HS256)
- **Expiration**: 15 minutes maximum
- **Refresh**: Automatic with refresh tokens
- **Revocation**: Real-time via token introspection

### Role-Based Access Control (RBAC)

**Standard Roles:**

```yaml
roles:
  viewer:
    permissions:
      - server:read
      - tool:read
      - policy:read

  developer:
    inherits: viewer
    permissions:
      - server:register
      - server:update
      - tool:invoke:low
      - tool:invoke:medium

  admin:
    inherits: developer
    permissions:
      - server:delete
      - policy:create
      - policy:update
      - policy:delete
      - tool:invoke:*
      - user:manage

  security_analyst:
    inherits: viewer
    permissions:
      - audit:read
      - audit:export
      - incident:investigate
```

### API Key Management

**Best Practices:**

1. **Generation:**
```bash
# Generate cryptographically secure API key
openssl rand -base64 32
```

2. **Storage:**
```python
# Hash API keys before storage (never store plaintext)
from passlib.hash import argon2

hashed_key = argon2.hash(api_key)
```

3. **Rotation:**
```bash
# Automated rotation every 90 days
make rotate-api-keys
```

4. **Scoping:**
```json
{
  "api_key_id": "key_abc123",
  "scopes": ["server:read", "server:write"],
  "rate_limit": 1000,
  "expires_at": "2024-12-31T23:59:59Z"
}
```

---

## Secrets Management

### HashiCorp Vault Integration

**Architecture:**

```
┌──────────────────┐
│   SARK Services  │
│                  │
│  Dynamic Secrets │◄──────┐
│  Short-lived     │       │
│  Auto-rotation   │       │
└──────────────────┘       │
                           │
                    ┌──────▼─────────┐
                    │  Vault Cluster │
                    │  (HA Mode)     │
                    │                │
                    │  - KV v2       │
                    │  - DB Secrets  │
                    │  - PKI         │
                    └────────────────┘
```

**Dynamic Database Credentials:**

```python
# Vault configuration for PostgreSQL
vault write database/config/sark-postgres \
    plugin_name=postgresql-database-plugin \
    allowed_roles="sark-app" \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/sark" \
    username="vault-admin" \
    password="admin-password"

# Create role with TTL
vault write database/roles/sark-app \
    db_name=sark-postgres \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"

# Application retrieves credentials
vault read database/creds/sark-app
```

**Secret Rotation:**

```python
# Automatic rotation configuration
from sark.services.vault import VaultClient

vault = VaultClient()

# Rotate every 24 hours
vault.enable_auto_rotation(
    path="database/creds/sark-app",
    interval_hours=24
)
```

### Encryption Keys Management

**Key Hierarchy:**

```
Root Key (Vault Transit)
    │
    ├── Data Encryption Keys (DEK)
    │   ├── User Data Encryption
    │   ├── Audit Log Encryption
    │   └── Configuration Encryption
    │
    └── Key Encryption Keys (KEK)
        ├── Database Column Encryption
        └── Backup Encryption
```

**Implementation:**

```python
from sark.crypto import EncryptionService

encryptor = EncryptionService()

# Encrypt sensitive data
encrypted_data = encryptor.encrypt(
    plaintext="sensitive-tool-parameter",
    key_id="data-encryption-key-v1"
)

# Automatic key rotation
encryptor.rotate_keys(
    old_key="data-encryption-key-v1",
    new_key="data-encryption-key-v2"
)
```

---

## Network Security

### TLS/SSL Configuration

**Minimum TLS 1.3:**

```yaml
# Kong Gateway TLS configuration
ssl_cipher_suite: modern
ssl_protocols: TLSv1.3
ssl_prefer_server_ciphers: true
ssl_session_cache: shared:SSL:10m
ssl_session_timeout: 10m

# Certificate pinning
ssl_certificate: /etc/kong/certs/sark.crt
ssl_certificate_key: /etc/kong/certs/sark.key
ssl_trusted_certificate: /etc/kong/certs/ca-chain.crt
```

**Certificate Management:**

```bash
# Automated cert renewal with cert-manager (Kubernetes)
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: sark-tls
  namespace: sark-system
spec:
  secretName: sark-tls-secret
  issuer:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - sark.company.com
  - api.sark.company.com
EOF
```

### Network Segmentation

**Kubernetes Network Policies:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sark-api-network-policy
  namespace: sark-system
spec:
  podSelector:
    matchLabels:
      app: sark-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: sark-system
    - podSelector:
        matchLabels:
          app: kong-gateway
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: opa
    ports:
    - protocol: TCP
      port: 8181
```

### Service Mesh Security (Kong Mesh / Istio)

**mTLS Configuration:**

```yaml
apiVersion: kuma.io/v1alpha1
kind: Mesh
metadata:
  name: sark-mesh
spec:
  mtls:
    enabledBackend: ca-1
    backends:
    - name: ca-1
      type: builtin
      dpCert:
        rotation:
          expiration: 24h
      conf:
        caCert:
          RSAbits: 4096
          expiration: 87600h  # 10 years
```

---

## Data Protection

### Encryption at Rest

**Database Encryption:**

```sql
-- PostgreSQL Transparent Data Encryption (TDE)
ALTER SYSTEM SET data_encryption = on;

-- Column-level encryption for sensitive fields
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255),
    hashed_password TEXT,
    -- Encrypted columns
    ssn_encrypted BYTEA,  -- Encrypted with pgcrypto
    api_key_encrypted BYTEA
);

-- Encrypt sensitive data
INSERT INTO users (id, email, ssn_encrypted)
VALUES (
    gen_random_uuid(),
    'user@example.com',
    pgp_sym_encrypt('123-45-6789', 'encryption-key-from-vault')
);
```

**File Storage Encryption:**

```python
# S3 Server-Side Encryption
import boto3

s3 = boto3.client('s3')

# Upload with encryption
s3.put_object(
    Bucket='sark-backups',
    Key='audit-logs-2024-11.tar.gz.enc',
    Body=encrypted_data,
    ServerSideEncryption='aws:kms',
    SSEKMSKeyId='arn:aws:kms:us-east-1:123456789:key/abc-123'
)
```

### Data Masking & Redaction

**Automatic PII Redaction:**

```python
from sark.security.data_masking import PIIRedactor

redactor = PIIRedactor()

# Redact before logging
audit_event = {
    "user_email": "user@company.com",
    "action": "tool:invoke",
    "parameters": {
        "query": "SELECT * FROM users WHERE ssn='123-45-6789'"
    }
}

redacted = redactor.redact(audit_event)
# Result: {"user_email": "u***@company.com", "parameters": {"query": "SELECT * FROM users WHERE ssn='***-**-****'"}}
```

### Data Loss Prevention (DLP)

**Integration with DLP Solutions:**

```python
from sark.security.dlp import DLPScanner

scanner = DLPScanner(
    provider="microsoft_purview",  # or "google_dlp", "symantec_dlp"
    api_key=vault("dlp/api-key")
)

# Scan tool outputs before returning
def scan_tool_output(output: str) -> tuple[bool, list[str]]:
    """Scan for sensitive data patterns."""
    violations = scanner.scan(output)

    if violations:
        return False, violations
    return True, []

# Block if sensitive data detected
safe, violations = scan_tool_output(tool_response)
if not safe:
    raise SecurityViolation(f"DLP violations detected: {violations}")
```

---

## Audit & Compliance

### Comprehensive Audit Logging

**What to Log:**

1. **Authentication Events**
   - Login attempts (success/failure)
   - Logout events
   - Token refresh
   - Password changes
   - MFA enrollment/challenges

2. **Authorization Decisions**
   - Policy evaluations (allow/deny)
   - Permission changes
   - Role assignments

3. **Data Access**
   - MCP server registrations
   - Tool invocations
   - Configuration changes
   - Sensitive data access

4. **Administrative Actions**
   - User management
   - Policy updates
   - System configuration changes

**Log Format (Structured JSON):**

```json
{
  "timestamp": "2024-11-20T10:30:45.123Z",
  "event_id": "evt_abc123",
  "event_type": "authorization.denied",
  "severity": "warning",
  "actor": {
    "user_id": "user_123",
    "email": "user@company.com",
    "ip_address": "10.0.1.45",
    "user_agent": "SARK-Client/1.0"
  },
  "resource": {
    "type": "mcp_tool",
    "id": "tool_xyz789",
    "name": "database_query",
    "sensitivity": "high"
  },
  "action": "tool:invoke",
  "decision": "deny",
  "reason": "User not in authorized team",
  "policy_id": "policy_456",
  "context": {
    "request_id": "req_789",
    "session_id": "sess_321",
    "time_of_day": "after_hours"
  }
}
```

### Compliance Frameworks

**SOC 2 Type II:**

```yaml
controls:
  CC6.1:  # Logical and Physical Access Controls
    - Implement MFA for all users
    - Review access quarterly
    - Automated access certification

  CC6.6:  # Logging and Monitoring
    - Centralized audit logging (TimescaleDB)
    - 90-day retention minimum
    - Daily backup verification

  CC7.2:  # System Monitoring
    - Real-time alerting (PagerDuty)
    - Anomaly detection (ML-based)
    - Monthly security reviews
```

**ISO 27001:**

| Control | Requirement | SARK Implementation |
|---------|-------------|---------------------|
| A.9.2.1 | User registration | OAuth 2.0 / OIDC integration |
| A.9.4.1 | Information access restriction | OPA policy enforcement |
| A.12.4.1 | Event logging | TimescaleDB audit trail |
| A.18.1.1 | Compliance with legal requirements | GDPR data subject rights |

**GDPR Compliance:**

```python
# Right to Access (Article 15)
@router.get("/api/v1/gdpr/data-export/{user_id}")
async def export_user_data(user_id: UUID) -> dict:
    """Export all data for GDPR compliance."""
    return {
        "personal_data": get_user_data(user_id),
        "audit_logs": get_user_audit_logs(user_id),
        "consents": get_user_consents(user_id)
    }

# Right to Erasure (Article 17)
@router.delete("/api/v1/gdpr/right-to-erasure/{user_id}")
async def erase_user_data(user_id: UUID):
    """Anonymize user data per GDPR."""
    anonymize_user(user_id)
    anonymize_audit_logs(user_id)
```

---

## Threat Detection

### Anomaly Detection

**Machine Learning Models:**

```python
from sark.security.ml_detection import AnomalyDetector

detector = AnomalyDetector()

# Train on normal behavior
detector.train(
    data=historical_audit_logs,
    features=[
        "requests_per_hour",
        "unique_tools_invoked",
        "failure_rate",
        "time_of_day",
        "day_of_week"
    ]
)

# Real-time detection
def check_for_anomalies(user_id: UUID, current_activity: dict):
    score = detector.predict_anomaly(current_activity)

    if score > 0.95:  # High anomaly score
        alert = SecurityAlert(
            type="unusual_activity",
            user_id=user_id,
            score=score,
            details=current_activity
        )
        send_alert_to_siem(alert)

        # Automatic response
        if score > 0.99:
            temporarily_suspend_user(user_id, duration="1h")
```

### Threat Intelligence Integration

**Indicators of Compromise (IOC):**

```python
from sark.security.threat_intel import ThreatIntelFeed

threat_intel = ThreatIntelFeed(
    sources=["alienvault_otx", "abuse_ch", "custom_feeds"]
)

# Check IP reputation
def validate_request_ip(ip_address: str) -> bool:
    reputation = threat_intel.check_ip(ip_address)

    if reputation.is_malicious:
        block_ip(ip_address, reason=reputation.reason)
        return False

    return True
```

### Security Information and Event Management (SIEM)

**Splunk Integration:**

```python
import splunklib.client as splunk_client

class SIEMForwarder:
    def __init__(self):
        self.client = splunk_client.connect(
            host="splunk.company.com",
            port=8089,
            username=vault("splunk/username"),
            password=vault("splunk/password")
        )

    def forward_high_severity_events(self, event: AuditEvent):
        """Forward critical events to SIEM."""
        if event.severity in ["HIGH", "CRITICAL"]:
            self.client.indexes["sark_security"].submit(
                event.to_json(),
                sourcetype="sark:audit"
            )
```

---

## Vulnerability Management

### Dependency Scanning

**Automated Tools:**

```yaml
# .github/workflows/security-scan.yml
name: Security Scanning

on:
  push:
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Python dependencies
      - name: Safety check
        run: |
          pip install safety
          safety check --json --output safety-report.json

      # Container scanning
      - name: Trivy scan
        run: |
          trivy image sark/api:latest \
            --severity HIGH,CRITICAL \
            --exit-code 1

      # Infrastructure as Code
      - name: Checkov scan
        run: |
          pip install checkov
          checkov -d k8s/ --framework kubernetes
```

### Penetration Testing

**Quarterly Pen Test Scope:**

1. **External Attack Surface**
   - API endpoints
   - Authentication mechanisms
   - Rate limiting effectiveness

2. **Internal Security**
   - Privilege escalation
   - Lateral movement
   - Data exfiltration paths

3. **Application Security**
   - Injection attacks (SQL, NoSQL, Command)
   - XSS, CSRF vulnerabilities
   - Business logic flaws

**Recommended Tools:**

- **OWASP ZAP** - Automated vulnerability scanning
- **Burp Suite Professional** - Manual penetration testing
- **Nuclei** - Template-based scanning
- **SQLMap** - SQL injection testing

### Bug Bounty Program

**Example Program Structure:**

```markdown
# SARK Security Bug Bounty

## Scope
- sark.company.com
- api.sark.company.com
- All SARK production infrastructure

## Rewards
- Critical: $5,000 - $10,000
- High: $2,000 - $5,000
- Medium: $500 - $2,000
- Low: $100 - $500

## Out of Scope
- DoS/DDoS attacks
- Social engineering
- Physical attacks

## Responsible Disclosure
- Report to security@company.com
- 90-day disclosure timeline
- No public disclosure before fix
```

---

## Security Hardening

### Container Security

**Dockerfile Best Practices:**

```dockerfile
# Use minimal base image
FROM python:3.11-slim-bookworm AS base

# Run as non-root user
RUN useradd -m -u 1000 sark && \
    chown -R sark:sark /app

USER sark

# Read-only filesystem
VOLUME ["/tmp"]
RUN chmod 1777 /tmp

# Drop capabilities
SECURITY_OPT="no-new-privileges:true"

# Scan for vulnerabilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

**Kubernetes Pod Security:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sark-api
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: api
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

### Database Security

**PostgreSQL Hardening:**

```sql
-- Disable unnecessary extensions
DROP EXTENSION IF NOT EXISTS plpythonu;

-- Row-level security
ALTER TABLE mcp_servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY team_isolation ON mcp_servers
    USING (team_id IN (
        SELECT team_id FROM user_teams WHERE user_id = current_user_id()
    ));

-- Audit trail
CREATE EXTENSION IF NOT EXISTS pgaudit;
ALTER SYSTEM SET pgaudit.log = 'all';

-- Connection limits
ALTER ROLE sark_app CONNECTION LIMIT 100;
```

### Redis Security

```bash
# redis.conf hardening
requirepass "strong-redis-password-from-vault"
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
maxmemory-policy allkeys-lru
bind 127.0.0.1 ::1
protected-mode yes
```

---

## Incident Response

### Security Incident Playbook

**Phase 1: Detection & Analysis**

```python
# Automated detection
class SecurityIncidentDetector:
    def detect_brute_force(self, user_id: UUID):
        failed_attempts = count_failed_logins(user_id, window="5m")
        if failed_attempts > 5:
            trigger_incident(
                type="brute_force_attack",
                severity="high",
                user_id=user_id
            )

    def detect_data_exfiltration(self, user_id: UUID):
        data_transferred = sum_data_transfer(user_id, window="1h")
        if data_transferred > threshold_bytes:
            trigger_incident(
                type="data_exfiltration",
                severity="critical",
                user_id=user_id
            )
```

**Phase 2: Containment**

```bash
# Immediate actions
# 1. Isolate compromised user/service
make isolate-user USER_ID=user_123

# 2. Block malicious IPs
kubectl exec -it deployment/kong -- \
    curl -X POST http://localhost:8001/plugins \
    -d "name=ip-restriction" \
    -d "config.deny=192.168.1.100"

# 3. Rotate credentials
make rotate-all-credentials
```

**Phase 3: Eradication & Recovery**

1. Patch vulnerabilities
2. Update security policies
3. Restore from clean backups
4. Verify system integrity

**Phase 4: Post-Incident**

- Conduct root cause analysis
- Update detection rules
- Improve response procedures
- Brief stakeholders

---

## Security Checklist

### Production Deployment

- [ ] TLS 1.3 enabled on all endpoints
- [ ] mTLS configured between services
- [ ] OAuth 2.0 / OIDC integration complete
- [ ] API keys rotated and secured
- [ ] Secrets stored in Vault (not env vars)
- [ ] Database encryption at rest enabled
- [ ] Audit logging to SIEM configured
- [ ] Network policies enforced (Kubernetes)
- [ ] Container images scanned (Trivy)
- [ ] Dependency vulnerabilities patched
- [ ] WAF rules configured
- [ ] DDoS protection enabled
- [ ] Rate limiting enforced
- [ ] Backup encryption verified
- [ ] Incident response team trained
- [ ] Security monitoring dashboards created
- [ ] Compliance controls documented
- [ ] Penetration test completed
- [ ] Security review signed off

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Cloud Security Alliance](https://cloudsecurityalliance.org/)

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Next Review:** February 2026
**Owner:** Security Team
