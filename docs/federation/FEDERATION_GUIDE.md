# SARK v2.0: Federation Setup and Configuration Guide

**Version:** 2.0.0
**Last Updated:** December 2025
**Difficulty:** Advanced
**Estimated Setup Time:** 3-6 hours

---

## Table of Contents

- [Overview](#overview)
- [Use Cases](#use-cases)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Certificate Setup](#certificate-setup)
- [Configuration](#configuration)
- [Node Registration](#node-registration)
- [Testing Federation](#testing-federation)
- [Writing Federation Policies](#writing-federation-policies)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)
- [Production Deployment](#production-deployment)

---

## Overview

Federation enables multiple SARK instances (nodes) to collaborate on governance across organizational boundaries. Each organization runs their own SARK node with full control over policies, while enabling selective cross-organization resource access.

### Key Features

- **Distributed Governance**: Each org controls their own policies
- **mTLS Security**: Mutual TLS for authentication and encryption
- **Audit Correlation**: Complete audit trail across organizations
- **Trust Management**: Explicit trust relationships
- **Rate Limiting**: Prevent abuse from federated partners

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Organization A                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SARK Node A                                          │   │
│  │ • alice@orga.com wants access                        │   │
│  │ • Queries Node B for permission                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓ mTLS                             │
└──────────────────────────┼──────────────────────────────────┘
                           │ Cross-Org Request
┌──────────────────────────┼──────────────────────────────────┐
│                          ↓ mTLS                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SARK Node B                                          │   │
│  │ • Evaluates policy for alice@orga.com                │   │
│  │ • Returns Allow/Deny decision                        │   │
│  │ • Both orgs audit the access                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                    Organization B                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Use Cases

### 1. Partner Collaboration

**Scenario**: Company A and Company B are business partners who need to share certain resources.

**Setup**:
- Company A exposes database API to Company B developers
- Company B exposes analytics API to Company A data team
- Each company controls who can access what

### 2. Multi-Tenant SaaS

**Scenario**: A SaaS platform wants customers to govern their own resources while enabling cross-tenant collaboration.

**Setup**:
- Each tenant runs their own SARK node
- Tenants can share resources selectively
- Platform maintains audit trail across tenants

### 3. Supply Chain Governance

**Scenario**: Manufacturer, supplier, and logistics company need to coordinate but maintain independence.

**Setup**:
- Each company runs SARK node
- Selective resource sharing (inventory APIs, shipping APIs)
- Complete audit trail for compliance

### 4. Development/Staging/Production Isolation

**Scenario**: Separate SARK instances for each environment with controlled cross-environment access.

**Setup**:
- Dev SARK can query Staging SARK (for testing)
- Staging SARK isolated from Production
- Emergency access procedures via federation

---

## Architecture

### Components

1. **Federation Node**: A trusted SARK instance in another organization
2. **mTLS**: Mutual TLS for secure authentication
3. **Trust Anchors**: CA certificates for validating federated nodes
4. **Cross-Org Authorization API**: Endpoint for authorization requests
5. **Audit Correlation**: Linking audit logs across organizations

### Trust Model

```
Organization A Trust Anchors:
  ├─ Org B CA Certificate (trusted)
  └─ Org C CA Certificate (trusted)

Organization B Trust Anchors:
  ├─ Org A CA Certificate (trusted)
  └─ Org C CA Certificate (trusted)

Each org validates incoming mTLS connections against their trust anchors.
```

### Data Flow

```
1. Principal makes request
   alice@orgA → Node A: "Execute capability@orgB"

2. Node A queries Node B
   Node A → Node B: "Can alice@orgA execute capability@orgB?"

3. Node B evaluates policy
   Node B Policy: Check if alice@orgA is in trusted_principals

4. Node B responds
   Node B → Node A: Allow/Deny + conditions

5. Both nodes audit
   Node A audit: cross_org_request
   Node B audit: cross_org_authorization

6. Correlation
   Both logs share correlation_id for tracing
```

---

## Prerequisites

### Infrastructure

- [ ] Separate SARK instance for each organization
- [ ] Network connectivity between nodes (HTTPS on custom port, e.g., 8443)
- [ ] TLS certificates for each node
- [ ] Certificate Authority (CA) for each organization

### Software

- [ ] SARK v2.0 or later
- [ ] PostgreSQL 14+
- [ ] OpenSSL for certificate generation
- [ ] Access to DNS (for optional DNS-based discovery)

### Knowledge

- [ ] Basic understanding of TLS/mTLS
- [ ] PKI (Public Key Infrastructure) basics
- [ ] OPA policy writing
- [ ] Network security

---

## Certificate Setup

Federation requires mTLS certificates for each node.

### Option 1: Self-Signed Certificates (Development/Testing)

**Generate CA for Organization A:**

```bash
# Create CA key and certificate
openssl genrsa -out orga-ca.key 4096
openssl req -new -x509 -days 3650 -key orga-ca.key -out orga-ca.crt \
  -subj "/C=US/ST=CA/O=Organization A/CN=Organization A CA"
```

**Generate Server Certificate for Node A:**

```bash
# Create server key
openssl genrsa -out node-a.key 4096

# Create certificate signing request
openssl req -new -key node-a.key -out node-a.csr \
  -subj "/C=US/ST=CA/O=Organization A/CN=sark.orga.com"

# Sign with CA
openssl x509 -req -in node-a.csr -CA orga-ca.crt -CAkey orga-ca.key \
  -CAcreateserial -out node-a.crt -days 825 \
  -extfile <(printf "subjectAltName=DNS:sark.orga.com,DNS:*.orga.com")
```

**Repeat for Organization B:**

```bash
# Organization B CA
openssl genrsa -out orgb-ca.key 4096
openssl req -new -x509 -days 3650 -key orgb-ca.key -out orgb-ca.crt \
  -subj "/C=US/ST=CA/O=Organization B/CN=Organization B CA"

# Organization B Node Certificate
openssl genrsa -out node-b.key 4096
openssl req -new -key node-b.key -out node-b.csr \
  -subj "/C=US/ST=CA/O=Organization B/CN=sark.orgb.com"
openssl x509 -req -in node-b.csr -CA orgb-ca.crt -CAkey orgb-ca.key \
  -CAcreateserial -out node-b.crt -days 825 \
  -extfile <(printf "subjectAltName=DNS:sark.orgb.com,DNS:*.orgb.com")
```

### Option 2: Production Certificates (Let's Encrypt or Enterprise CA)

For production, use proper certificates from:
- Let's Encrypt (free, automated)
- Your organization's PKI/CA
- Commercial CA (DigiCert, GlobalSign, etc.)

**Requirements:**
- Valid domain names
- Certificates with Subject Alternative Names (SAN)
- Separate client/server certificates or combined

---

## Configuration

### Federation Config File

Create `/etc/sark/federation.yaml`:

```yaml
federation:
  # Enable federation
  enabled: true

  # This node's identity
  node_id: "orga.com"
  node_name: "Organization A"

  # Federation endpoint (separate from main API)
  listen_address: "0.0.0.0:8443"

  # TLS configuration for this node
  tls:
    # Server certificate (presented to federated nodes)
    cert: "/etc/sark/certs/node-a.crt"
    key: "/etc/sark/certs/node-a.key"

    # CA bundle for validating client certificates
    client_ca: "/etc/sark/certs/client-ca-bundle.crt"

  # Trusted federated nodes
  nodes:
    - name: "orgb"
      node_id: "orgb.com"
      endpoint: "https://sark.orgb.com:8443"

      # Trust anchor (Organization B's CA certificate)
      trust_anchor: "/etc/sark/federation/orgb-ca.crt"

      # Enable/disable this node
      enabled: true

      # Rate limiting
      rate_limit_per_hour: 10000

      # Optional: specific policies for this node
      policy_overrides:
        - "cross-org-dev-access"

    - name: "orgc"
      node_id: "orgc.com"
      endpoint: "https://sark.orgc.com:8443"
      trust_anchor: "/etc/sark/federation/orgc-ca.crt"
      enabled: true
      rate_limit_per_hour: 5000

  # Global rate limits
  rate_limits:
    # Max requests per org per hour
    per_org: 10000

    # Max requests per principal per hour
    per_principal: 100

    # Burst allowance
    burst: 50

  # Audit correlation settings
  audit:
    correlation_enabled: true

    # How often to reconcile audit logs with federated nodes (seconds)
    reconciliation_interval: 3600

    # Alert on correlation mismatches
    alert_on_mismatch: true

  # Optional: DNS-based discovery (v2.1+)
  discovery:
    enabled: false
    dns_domain: "_sark._tcp.orga.com"
```

### Environment Variables

```bash
# Federation
FEDERATION_ENABLED=true
FEDERATION_NODE_ID=orga.com
FEDERATION_LISTEN_ADDRESS=0.0.0.0:8443

# TLS
FEDERATION_TLS_CERT=/etc/sark/certs/node-a.crt
FEDERATION_TLS_KEY=/etc/sark/certs/node-a.key
FEDERATION_TLS_CLIENT_CA=/etc/sark/certs/client-ca-bundle.crt

# Audit
FEDERATION_AUDIT_CORRELATION=true
```

### Docker Compose

```yaml
version: '3.8'

services:
  sark:
    image: sark:2.0.0
    ports:
      - "8000:8000"    # Main API
      - "8443:8443"    # Federation API
    volumes:
      - ./federation.yaml:/etc/sark/federation.yaml
      - ./certs:/etc/sark/certs
      - ./federation-trust:/etc/sark/federation
    environment:
      - FEDERATION_ENABLED=true
      - FEDERATION_NODE_ID=orga.com
      - DATABASE_URL=postgresql://sark:password@postgres:5432/sark_db
      - OPA_URL=http://opa:8181
    networks:
      - sark_network
      - federation_network  # Network for cross-org communication

  postgres:
    image: timescale/timescaledb:latest-pg14
    # ... (same as before)

  opa:
    image: openpolicyagent/opa:latest
    # ... (same as before)

networks:
  sark_network:
    driver: bridge
  federation_network:
    driver: bridge
```

---

## Node Registration

After configuration, register federated nodes via API or database.

### Via API

```bash
# Register Organization B as a federated node
curl -X POST http://localhost:8000/api/v2/federation/nodes \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "orgb.com",
    "name": "Organization B",
    "endpoint": "https://sark.orgb.com:8443",
    "trust_anchor_cert": "-----BEGIN CERTIFICATE-----\nMII...\n-----END CERTIFICATE-----",
    "rate_limit_per_hour": 10000,
    "enabled": true
  }'
```

### Via Database

```sql
INSERT INTO federation_nodes (
  node_id,
  name,
  endpoint,
  trust_anchor_cert,
  enabled,
  rate_limit_per_hour,
  trusted_since
) VALUES (
  'orgb.com',
  'Organization B',
  'https://sark.orgb.com:8443',
  '-----BEGIN CERTIFICATE-----...-----END CERTIFICATE-----',
  true,
  10000,
  NOW()
);
```

### Verify Registration

```bash
# List registered nodes
curl http://localhost:8000/api/v2/federation/nodes \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "nodes": [
    {
      "node_id": "orgb.com",
      "name": "Organization B",
      "endpoint": "https://sark.orgb.com:8443",
      "enabled": true,
      "trusted_since": "2025-12-01T00:00:00Z",
      "rate_limit_per_hour": 10000
    }
  ]
}
```

---

## Testing Federation

### 1. Test mTLS Connection

```bash
# Test connection to federated node
curl --cert /etc/sark/certs/node-a.crt \
     --key /etc/sark/certs/node-a.key \
     --cacert /etc/sark/federation/orgb-ca.crt \
     https://sark.orgb.com:8443/api/v2/federation/info
```

**Expected Response:**
```json
{
  "node_id": "orgb.com",
  "version": "2.0.0",
  "capabilities": ["authorization", "audit_query"],
  "public_key": "-----BEGIN PUBLIC KEY-----...",
  "trusted_nodes": ["orga.com", "orgc.com"]
}
```

### 2. Test Cross-Org Authorization

**Scenario**: Alice from Org A wants to access a resource in Org B.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v2/authorize \
  -H "X-API-Key: $ALICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_id": "database-query@orgb.com",
    "principal_id": "alice@orga.com",
    "arguments": {
      "query": "SELECT * FROM users LIMIT 10"
    }
  }'
```

**Flow:**
1. Node A receives request from alice@orga.com
2. Node A sees capability belongs to Node B
3. Node A queries Node B: "Can alice@orga.com execute database-query?"
4. Node B evaluates policy
5. Node B responds: Allow/Deny
6. Both nodes create audit logs with correlation_id
7. Node A returns result to Alice

### 3. Verify Audit Correlation

**Check audit logs on Node A:**
```bash
curl http://localhost:8000/api/v2/audit/logs?event_type=cross_org_request \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "items": [
    {
      "event_id": "evt-a-123",
      "correlation_id": "corr-456",
      "event_type": "cross_org_request",
      "principal": "alice@orga.com",
      "resource": "database-query@orgb.com",
      "decision": "allow",
      "source_node": "orga.com",
      "target_node": "orgb.com",
      "timestamp": "2025-12-01T10:00:00Z"
    }
  ]
}
```

**Check audit logs on Node B (same correlation_id):**
```bash
curl https://sark.orgb.com:8000/api/v2/audit/logs?correlation_id=corr-456 \
  --cert /etc/sark/certs/node-a.crt \
  --key /etc/sark/certs/node-a.key \
  --cacert /etc/sark/federation/orgb-ca.crt
```

---

## Writing Federation Policies

### Allow Trusted Organizations

```rego
package grid.federation

# List of trusted organization domains
trusted_orgs := ["orga.com", "orgb.com", "orgc.com"]

# Allow access from trusted orgs
allow if {
    input.principal.source_org in trusted_orgs
    input.resource.owner_org == "orgb.com"
    input.action == "execute"
}
```

### Role-Based Cross-Org Access

```rego
package grid.federation

# Allow developers from trusted orgs to access medium sensitivity resources
allow if {
    input.principal.source_org in data.trusted_orgs
    input.principal.attributes.role == "developer"
    input.resource.sensitivity_level in ["low", "medium"]
    input.action == "execute"
}
```

### Require Explicit Approval for High Sensitivity

```rego
package grid.federation

# High sensitivity resources require explicit approval
allow if {
    input.resource.sensitivity_level == "high"
    input.principal.id in data.approved_cross_org_principals[input.resource.id]
}

# Approved principals per resource (managed via API)
approved_cross_org_principals := {
    "database-prod@orgb.com": [
        "alice@orga.com",
        "bob@orgc.com"
    ]
}
```

### Rate Limit Cross-Org Requests

```rego
package grid.federation

# Limit cross-org requests to 100/hour per principal
deny if {
    input.principal.source_org != input.resource.owner_org
    count_recent_cross_org_requests(input.principal.id) >= 100
}

# Helper function (implemented in OPA)
count_recent_cross_org_requests(principal_id) := count {
    recent_requests := [r |
        r := data.audit.events[_]
        r.principal == principal_id
        r.event_type == "cross_org_request"
        r.timestamp > time.now_ns() - (3600 * 1000000000)  # Last hour
    ]
    count := count(recent_requests)
}
```

### Time-Based Restrictions

```rego
package grid.federation

# Only allow cross-org access during business hours
allow if {
    input.principal.source_org != input.resource.owner_org
    is_business_hours
}

is_business_hours if {
    current_hour := time.clock([time.now_ns()])[0]
    current_hour >= 9
    current_hour < 17
}
```

---

## Monitoring

### Key Metrics

Monitor these metrics for federation health:

**Request Metrics:**
- `federation_requests_total{source_org, target_org, decision}`
- `federation_request_duration_seconds`
- `federation_errors_total{error_type}`

**mTLS Metrics:**
- `federation_tls_handshakes_total{result}`
- `federation_cert_expiry_days{node_id}`

**Rate Limiting:**
- `federation_rate_limit_hits_total{node_id}`
- `federation_requests_per_hour{source_org}`

### Grafana Dashboard

Sample Prometheus queries:

```promql
# Cross-org request rate
rate(federation_requests_total[5m])

# Cross-org error rate
rate(federation_errors_total[5m])

# Average request duration by org
avg(federation_request_duration_seconds) by (source_org, target_org)

# Certificate expiry warning
federation_cert_expiry_days < 30
```

### Alerts

```yaml
# alertmanager.yml
groups:
  - name: federation
    rules:
      - alert: FederationCertificateExpiringSoon
        expr: federation_cert_expiry_days < 30
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Federation certificate expiring soon for {{ $labels.node_id }}"

      - alert: FederationHighErrorRate
        expr: rate(federation_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High federation error rate from {{ $labels.source_org }}"

      - alert: FederationRateLimitExceeded
        expr: rate(federation_rate_limit_hits_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Rate limit frequently exceeded for {{ $labels.node_id }}"
```

---

## Troubleshooting

### Common Issues

#### 1. mTLS Handshake Failure

**Symptom:** `ssl handshake failed` in logs

**Solutions:**
```bash
# Verify certificate validity
openssl x509 -in node-a.crt -text -noout | grep -A2 "Validity"

# Check certificate chain
openssl verify -CAfile orga-ca.crt node-a.crt

# Test mTLS connection manually
openssl s_client -connect sark.orgb.com:8443 \
  -cert node-a.crt -key node-a.key -CAfile orgb-ca.crt
```

#### 2. Cross-Org Authorization Denied

**Symptom:** Requests denied even with correct policies

**Debug:**
```bash
# Check policy evaluation on target node
curl -X POST https://sark.orgb.com:8000/api/v2/policies/test \
  --cert node-a.crt --key node-a.key --cacert orgb-ca.crt \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "principal": {
        "id": "alice@orga.com",
        "source_org": "orga.com",
        "role": "developer"
      },
      "resource": {
        "id": "database-query",
        "owner_org": "orgb.com"
      },
      "action": "execute"
    }
  }'
```

#### 3. Audit Correlation Mismatch

**Symptom:** Audit logs missing correlation_id

**Solutions:**
```bash
# Check correlation settings
grep "correlation_enabled" /etc/sark/federation.yaml

# Verify both nodes have correlation enabled
# Check reconciliation logs
docker logs sark | grep "audit_reconciliation"
```

#### 4. Rate Limit Issues

**Symptom:** `429 Too Many Requests`

**Solutions:**
```bash
# Check current rate limit
curl http://localhost:8000/api/v2/federation/nodes/orgb.com \
  -H "X-API-Key: $API_KEY"

# Update rate limit
curl -X PATCH http://localhost:8000/api/v2/federation/nodes/orgb.com \
  -H "X-API-Key: $API_KEY" \
  -d '{"rate_limit_per_hour": 20000}'
```

---

## Security Best Practices

### 1. Certificate Management

- **Rotate certificates regularly** (every 12 months)
- **Use strong key sizes** (4096-bit RSA or 256-bit ECDSA)
- **Set appropriate expiry dates** (12-24 months)
- **Monitor certificate expiry** (alert 30 days before)
- **Revoke compromised certificates immediately**

### 2. Trust Management

- **Minimize trust relationships** (only trust necessary orgs)
- **Review trust anchors quarterly**
- **Document trust establishment procedures**
- **Have revocation procedures ready**

### 3. Network Security

- **Use dedicated network for federation** (separate from main API)
- **Firewall rules** (only allow trusted IPs)
- **DDoS protection** (rate limiting, connection limits)
- **Network segmentation** (isolate federation traffic)

### 4. Audit & Monitoring

- **Enable correlation** (always)
- **Regular audit reviews** (weekly for cross-org access)
- **Alert on anomalies** (unusual access patterns)
- **Reconcile audit logs** (daily)

### 5. Policy Management

- **Principle of least privilege** (deny by default)
- **Explicit approvals for sensitive resources**
- **Time-based restrictions** (business hours only)
- **Regular policy reviews** (quarterly)

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Production certificates obtained
- [ ] Federation config reviewed and tested
- [ ] Policies tested in staging
- [ ] Monitoring and alerts configured
- [ ] Audit correlation tested
- [ ] Disaster recovery plan documented
- [ ] Security review completed
- [ ] Stakeholders notified

### Deployment Steps

1. **Setup Node A:**
   ```bash
   # Deploy SARK with federation enabled
   docker-compose -f docker-compose.prod.yml up -d

   # Verify federation endpoint
   curl https://sark.orga.com:8443/api/v2/federation/info
   ```

2. **Setup Node B:**
   ```bash
   # Same process for Node B
   docker-compose -f docker-compose.prod.yml up -d
   curl https://sark.orgb.com:8443/api/v2/federation/info
   ```

3. **Register Trust:**
   ```bash
   # On Node A, register Node B
   curl -X POST https://sark.orga.com/api/v2/federation/nodes \
     -d '{ "node_id": "orgb.com", ... }'

   # On Node B, register Node A
   curl -X POST https://sark.orgb.com/api/v2/federation/nodes \
     -d '{ "node_id": "orga.com", ... }'
   ```

4. **Deploy Policies:**
   ```bash
   # Deploy cross-org policies to both nodes
   curl -X POST https://sark.orga.com/api/v2/policies \
     -d @federation-policies.json
   ```

5. **Test End-to-End:**
   ```bash
   # Test cross-org access
   ./test-federation.sh
   ```

6. **Enable Monitoring:**
   ```bash
   # Verify metrics are flowing
   curl https://sark.orga.com/metrics | grep federation
   ```

### Post-Deployment

- [ ] Monitor for errors (first 24 hours)
- [ ] Review audit logs
- [ ] Collect feedback from users
- [ ] Document any issues
- [ ] Plan optimizations

---

## Next Steps

After successful federation setup:

1. **Expand to more orgs** (if needed)
2. **Optimize policies** based on usage patterns
3. **Implement advanced features** (delegation chains, dynamic trust)
4. **Regular security audits**
5. **Consider DNS-based discovery** (v2.1+)

---

## Support

- **Federation Documentation**: https://docs.sark.dev/federation
- **Security Issues**: security@sark.dev (PGP key available)
- **GitHub**: https://github.com/yourusername/sark/issues
- **Discord**: https://discord.gg/sark (channel: #federation)

---

**Document Version:** 1.0
**Last Updated:** December 2025
**Maintainer:** SARK Core Team
