# SARK v2.0: Federation Protocol Specification

**Version:** 1.0 (Draft)
**Status:** Specification for v2.0 implementation
**Created:** November 28, 2025

---

## Overview

Federation enables multiple SARK instances (nodes) to collaborate on governance across organizational boundaries. Each organization runs their own SARK node, and nodes can query each other for authorization decisions.

---

## Core Concept

```
┌─────────────────────────────────────────────────────────────┐
│                    Organization A                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SARK Node A                                          │   │
│  │ • Policies for Org A resources                       │   │
│  │ • Audit logs for Org A                               │   │
│  │ • Trust anchors (Org B, Org C certificates)         │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↕ mTLS                             │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           │ Federation Protocol
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                          ↕ mTLS                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SARK Node B                                          │   │
│  │ • Policies for Org B resources                       │   │
│  │ • Audit logs for Org B                               │   │
│  │ • Trust anchors (Org A, Org C certificates)         │   │
│  └──────────────────────────────────────────────────────┘   │
│                    Organization B                           │
└─────────────────────────────────────────────────────────────┘
```

**Use Case:** Principal from Org A wants to access resource in Org B
1. Org A's SARK queries Org B's SARK: "Can alice@orgA access resource-X?"
2. Org B evaluates policy and responds: Allow/Deny
3. Both orgs audit the cross-org access
4. Audit trail shows complete path: Org A principal → Org B resource

---

## Federation Components

### 1. Node Discovery

Nodes discover each other via DNS SRV records or static configuration.

**DNS-based discovery:**
```
_sark._tcp.orgb.com. 86400 IN SRV 0 5 8443 sark.orgb.com.
```

**Static configuration:**
```yaml
federation:
  enabled: true
  nodes:
    - name: "orgb"
      endpoint: "https://sark.orgb.com:8443"
      trust_anchor: "/etc/sark/federation/orgb-ca.crt"
```

### 2. Trust Establishment

Nodes establish trust via mutual TLS (mTLS):

```
┌─────────────┐                           ┌─────────────┐
│  Node A     │                           │  Node B     │
│             │──── TLS Handshake ───────→│             │
│             │←─── Server Cert (B) ──────│             │
│             │──── Client Cert (A) ─────→│             │
│             │←─── Verify Cert (A) ──────│             │
│             │──── Verify Cert (B) ─────→│             │
│             │←──── Trust Established ───│             │
└─────────────┘                           └─────────────┘
```

**Certificate requirements:**
- Each node has a certificate signed by their org's CA
- Each node trusts specific org CAs (configured trust anchors)
- Certificates include node identity in Subject Alternative Name (SAN)

### 3. Cross-Org Authorization

**Authorization Request Format:**
```json
{
  "request_id": "uuid",
  "timestamp": "2025-11-28T06:30:00Z",
  "source_node": "orga.com",
  "principal": {
    "id": "alice@orga.com",
    "type": "user",
    "attributes": {
      "role": "developer",
      "department": "engineering"
    },
    "source_org": "orga.com"
  },
  "resource": {
    "id": "resource-123",
    "type": "mcp_server",
    "name": "database-server",
    "owner_org": "orgb.com"
  },
  "action": "execute",
  "capability": {
    "id": "query_database",
    "name": "query_database"
  },
  "context": {
    "ip_address": "10.1.2.3",
    "user_agent": "SARK-Client/2.0"
  }
}
```

**Authorization Response Format:**
```json
{
  "request_id": "uuid",
  "timestamp": "2025-11-28T06:30:01Z",
  "decision": "allow",  // or "deny"
  "reason": "Cross-org developer access permitted",
  "policy_id": "cross-org-dev-access",
  "ttl_seconds": 300,  // Cache duration
  "conditions": [
    "rate_limit: 100 requests/hour",
    "audit_required: true"
  ],
  "metadata": {
    "evaluated_by": "orgb.com",
    "policy_version": "1.2.3"
  }
}
```

### 4. Audit Correlation

Both nodes log the cross-org access with correlation IDs:

**Node A (source) audit log:**
```json
{
  "event_id": "evt-a-123",
  "correlation_id": "corr-456",
  "timestamp": "2025-11-28T06:30:00Z",
  "event_type": "cross_org_request",
  "principal": "alice@orga.com",
  "resource": "resource-123@orgb.com",
  "action": "execute",
  "decision": "allow",
  "source_node": "orga.com",
  "target_node": "orgb.com"
}
```

**Node B (target) audit log:**
```json
{
  "event_id": "evt-b-789",
  "correlation_id": "corr-456",
  "timestamp": "2025-11-28T06:30:01Z",
  "event_type": "cross_org_authorization",
  "principal": "alice@orga.com",
  "principal_org": "orga.com",
  "resource": "resource-123",
  "action": "execute",
  "decision": "allow",
  "reason": "Cross-org developer access permitted",
  "requesting_node": "orga.com"
}
```

---

## Federation API Endpoints

### Node Information

```
GET /api/v2/federation/info
```

Response:
```json
{
  "node_id": "orgb.com",
  "version": "2.0.0",
  "capabilities": ["authorization", "audit_query"],
  "public_key": "-----BEGIN PUBLIC KEY-----..."
}
```

### Cross-Org Authorization

```
POST /api/v2/federation/authorize
```

Request body: Authorization request (see format above)
Response: Authorization response (see format above)

### Audit Query (Optional)

```
POST /api/v2/federation/audit/query
```

Allows federated nodes to query each other's audit logs for correlation.

---

## Federation Policy Examples

### Allow Cross-Org Developer Access

```rego
package grid.federation

# Allow developers from trusted orgs to access medium sensitivity resources
allow if {
    input.principal.source_org in data.trusted_orgs
    input.principal.attributes.role == "developer"
    input.resource.sensitivity_level in ["low", "medium"]
    input.action == "execute"
}

# Trusted organizations
trusted_orgs := ["orga.com", "orgc.com"]
```

### Require Approval for High Sensitivity

```rego
package grid.federation

# High sensitivity resources require explicit approval
allow if {
    input.resource.sensitivity_level == "high"
    input.principal.id in data.approved_principals[input.resource.id]
}

# Approved principals per resource (managed separately)
approved_principals := {
    "resource-123": ["alice@orga.com", "bob@orgc.com"]
}
```

### Rate Limiting Cross-Org Access

```rego
package grid.federation

# Limit cross-org requests to 100/hour per principal
allow if {
    input.principal.source_org != input.resource.owner_org
    count_recent_requests(input.principal.id) < 100
}

# Helper function (implemented in policy service)
count_recent_requests(principal_id) := count {
    # Query audit log for requests in last hour
    count := data.audit.count_requests(principal_id, 3600)
}
```

---

## Security Considerations

### 1. Trust Boundaries

- Each org controls their own policies
- No org can override another org's policies
- Trust is explicit (configured trust anchors)
- Revocation is immediate (remove trust anchor)

### 2. Certificate Management

```yaml
# Trust anchor configuration
federation:
  trust_anchors:
    - org: "orgb.com"
      ca_cert: "/etc/sark/federation/orgb-ca.crt"
      valid_until: "2026-12-31"
      auto_renew: true
    - org: "orgc.com"
      ca_cert: "/etc/sark/federation/orgc-ca.crt"
      valid_until: "2026-12-31"
      auto_renew: true
```

### 3. Audit Trail Integrity

- All cross-org requests are logged by both nodes
- Correlation IDs link audit entries across orgs
- Audit logs are immutable (INSERT-ONLY)
- Periodic audit reconciliation (compare correlation IDs)

### 4. Rate Limiting

```yaml
federation:
  rate_limits:
    per_org: 10000  # requests/hour from any single org
    per_principal: 100  # requests/hour from any single principal
    burst: 50  # burst allowance
```

---

## Implementation Phases

### Phase 1: Basic Federation (v2.0)

- ✅ Node discovery (static config)
- ✅ mTLS trust establishment
- ✅ Cross-org authorization API
- ✅ Audit correlation
- ✅ Basic federation policies

### Phase 2: Advanced Federation (v2.1+)

- ⏳ DNS-based discovery
- ⏳ Dynamic trust establishment
- ⏳ Federated audit queries
- ⏳ Cross-org delegation chains
- ⏳ Federation health monitoring

---

## Configuration Example

```yaml
# /etc/sark/config.yaml
federation:
  enabled: true
  
  # This node's identity
  node_id: "orga.com"
  listen_address: "0.0.0.0:8443"
  
  # TLS configuration
  tls:
    cert: "/etc/sark/certs/node.crt"
    key: "/etc/sark/certs/node.key"
    ca: "/etc/sark/certs/ca.crt"
  
  # Trusted nodes
  nodes:
    - name: "orgb"
      node_id: "orgb.com"
      endpoint: "https://sark.orgb.com:8443"
      trust_anchor: "/etc/sark/federation/orgb-ca.crt"
      enabled: true
    
    - name: "orgc"
      node_id: "orgc.com"
      endpoint: "https://sark.orgc.com:8443"
      trust_anchor: "/etc/sark/federation/orgc-ca.crt"
      enabled: true
  
  # Rate limits
  rate_limits:
    per_org: 10000
    per_principal: 100
    burst: 50
  
  # Audit correlation
  audit:
    correlation_enabled: true
    reconciliation_interval: 3600  # seconds
```

---

## Testing Federation

### 1. Local Testing (Docker Compose)

```yaml
version: '3.8'
services:
  sark-orga:
    image: sark:2.0
    environment:
      - FEDERATION_ENABLED=true
      - NODE_ID=orga.local
    volumes:
      - ./certs/orga:/etc/sark/certs
  
  sark-orgb:
    image: sark:2.0
    environment:
      - FEDERATION_ENABLED=true
      - NODE_ID=orgb.local
    volumes:
      - ./certs/orgb:/etc/sark/certs
```

### 2. Integration Tests

```python
async def test_cross_org_authorization():
    # Setup: Create principal in Org A
    principal_a = await orga_client.create_principal("alice@orga.com")
    
    # Setup: Create resource in Org B
    resource_b = await orgb_client.create_resource("database-server")
    
    # Test: Alice from Org A requests access to Org B resource
    response = await orga_client.authorize(
        principal=principal_a,
        resource=resource_b,
        action="execute"
    )
    
    assert response.decision == "allow"
    
    # Verify: Both orgs logged the access
    audit_a = await orga_client.get_audit_logs(correlation_id=response.correlation_id)
    audit_b = await orgb_client.get_audit_logs(correlation_id=response.correlation_id)
    
    assert len(audit_a) == 1
    assert len(audit_b) == 1
    assert audit_a[0].correlation_id == audit_b[0].correlation_id
```

---

## Success Criteria

Federation is complete when:
- ✅ Two SARK nodes can establish mTLS connection
- ✅ Cross-org authorization requests work
- ✅ Both nodes log cross-org access with correlation IDs
- ✅ Policies can allow/deny based on source org
- ✅ Rate limiting prevents abuse
- ✅ Certificate revocation works
- ✅ Integration tests pass

---

**Document Version:** 1.0
**Status:** Draft for v2.0 implementation
**Next Steps:** Implement federation service, mTLS setup, cross-org policies