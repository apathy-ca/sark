# Federation Deployment Guide

**Tutorial Duration:** 60-90 minutes
**Skill Level:** Advanced
**Prerequisites:** SARK v2.0 deployed, understanding of mTLS, Docker/Kubernetes knowledge

---

## Introduction

SARK v2.0 **Federation** enables multiple organizations to securely share resources while maintaining independent governance. Each organization runs its own SARK instance, and instances collaborate on authorization decisions across organizational boundaries.

### What You'll Build

By the end of this tutorial, you'll have deployed a **federated SARK environment** with:

- **Two SARK nodes** representing different organizations (Acme Corp and Globex Ltd)
- **Mutual TLS (mTLS) authentication** between nodes
- **Cross-organization resource sharing** with independent policies
- **Distributed audit trail** showing complete access paths
- **Automatic node discovery** via DNS-SD

---

## Table of Contents

1. [Federation Architecture](#federation-architecture)
2. [Prerequisites and Setup](#prerequisites-and-setup)
3. [Deploying the First Node (Acme Corp)](#deploying-the-first-node-acme-corp)
4. [Deploying the Second Node (Globex Ltd)](#deploying-the-second-node-globex-ltd)
5. [Establishing Trust (mTLS)](#establishing-trust-mtls)
6. [Configuring Cross-Org Policies](#configuring-cross-org-policies)
7. [Testing Federation](#testing-federation)
8. [Monitoring Federated Access](#monitoring-federated-access)
9. [Production Considerations](#production-considerations)

---

## Federation Architecture

### High-Level Overview

```
┌────────────────────────────────────────────────────┐
│           Organization A (Acme Corp)               │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │ SARK Node A (sark.acme.com)                 │  │
│  │                                             │  │
│  │ Resources:                                  │  │
│  │ • MCP filesystem server                     │  │
│  │ • GitHub API (Acme repos)                   │  │
│  │                                             │  │
│  │ Principals:                                 │  │
│  │ • alice@acme.com                            │  │
│  │ • bob@acme.com                              │  │
│  │                                             │  │
│  │ Policies:                                   │  │
│  │ • Acme employees can access own resources   │  │
│  │ • Allow Globex engineers (limited access)   │  │
│  └─────────────────────────────────────────────┘  │
│                     ↕ mTLS                        │
└────────────────────┼──────────────────────────────┘
                     │
         Federation Protocol (HTTPS + mTLS)
                     │
┌────────────────────┼──────────────────────────────┐
│                     ↕ mTLS                        │
│  ┌─────────────────────────────────────────────┐  │
│  │ SARK Node B (sark.globex.com)               │  │
│  │                                             │  │
│  │ Resources:                                  │  │
│  │ • gRPC analytics service                    │  │
│  │ • Slack API (Globex workspace)              │  │
│  │                                             │  │
│  │ Principals:                                 │  │
│  │ • charlie@globex.com                        │  │
│  │ • diana@globex.com                          │  │
│  │                                             │  │
│  │ Policies:                                   │  │
│  │ • Globex employees can access own resources │  │
│  │ • Allow Acme developers (read-only)         │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│           Organization B (Globex Ltd)              │
└────────────────────────────────────────────────────┘
```

### Federation Flow

When Alice (from Acme) wants to access Globex's analytics service:

1. **Alice sends request** to her local SARK node (Node A)
2. **Node A recognizes** the resource belongs to Globex (Node B)
3. **Node A queries Node B** via mTLS: "Can alice@acme.com access analytics?"
4. **Node B evaluates** its policies for cross-org access
5. **Node B responds** with Allow/Deny decision
6. **Both nodes audit** the cross-org access with correlation IDs
7. **Node A executes** the capability if allowed

---

## Prerequisites and Setup

### Infrastructure Requirements

- **2 servers or VMs** (can use Docker/Kubernetes locally)
- **2 domain names** (e.g., `sark.acme.com`, `sark.globex.com`)
  - Or use `/etc/hosts` for local testing
- **PostgreSQL databases** (one per node)
- **TLS certificates** for each node
- **Network connectivity** between nodes on port 8443

### Software Requirements

- Docker and Docker Compose 20+
- OpenSSL 1.1+ (for certificate generation)
- Python 3.11+ (for testing)
- kubectl (if deploying to Kubernetes)

### Directory Structure

```
federation-deployment/
├── node-acme/
│   ├── docker-compose.yml
│   ├── .env
│   ├── certs/
│   │   ├── acme-node.crt
│   │   ├── acme-node.key
│   │   └── acme-ca.crt
│   └── config/
│       └── federation.yaml
├── node-globex/
│   ├── docker-compose.yml
│   ├── .env
│   ├── certs/
│   │   ├── globex-node.crt
│   │   ├── globex-node.key
│   │   └── globex-ca.crt
│   └── config/
│       └── federation.yaml
└── shared/
    ├── generate-certs.sh
    └── test-federation.py
```

---

## Deploying the First Node (Acme Corp)

### Step 1: Generate Certificates

Create `shared/generate-certs.sh`:

```bash
#!/bin/bash
set -e

echo "Generating Federation Certificates"

# Create directories
mkdir -p node-acme/certs node-globex/certs

# Generate Acme Corp CA
openssl req -x509 -new -nodes \
  -keyout node-acme/certs/acme-ca.key \
  -out node-acme/certs/acme-ca.crt \
  -days 365 -subj "/CN=Acme Corp CA/O=Acme Corp"

# Generate Acme Node certificate
openssl req -new -nodes \
  -keyout node-acme/certs/acme-node.key \
  -out node-acme/certs/acme-node.csr \
  -subj "/CN=sark.acme.com/O=Acme Corp"

# Add SAN extension
cat > node-acme/certs/acme-san.ext <<EOF
subjectAltName = DNS:sark.acme.com,DNS:localhost,IP:127.0.0.1
extendedKeyUsage = serverAuth,clientAuth
EOF

# Sign node certificate
openssl x509 -req \
  -in node-acme/certs/acme-node.csr \
  -CA node-acme/certs/acme-ca.crt \
  -CAkey node-acme/certs/acme-ca.key \
  -CAcreateserial \
  -out node-acme/certs/acme-node.crt \
  -days 365 \
  -extfile node-acme/certs/acme-san.ext

# Generate Globex Corp CA
openssl req -x509 -new -nodes \
  -keyout node-globex/certs/globex-ca.key \
  -out node-globex/certs/globex-ca.crt \
  -days 365 -subj "/CN=Globex Ltd CA/O=Globex Ltd"

# Generate Globex Node certificate
openssl req -new -nodes \
  -keyout node-globex/certs/globex-node.key \
  -out node-globex/certs/globex-node.csr \
  -subj "/CN=sark.globex.com/O=Globex Ltd"

cat > node-globex/certs/globex-san.ext <<EOF
subjectAltName = DNS:sark.globex.com,DNS:localhost,IP:127.0.0.1
extendedKeyUsage = serverAuth,clientAuth
EOF

openssl x509 -req \
  -in node-globex/certs/globex-node.csr \
  -CA node-globex/certs/globex-ca.crt \
  -CAkey node-globex/certs/globex-ca.key \
  -CAcreateserial \
  -out node-globex/certs/globex-node.crt \
  -days 365 \
  -extfile node-globex/certs/globex-san.ext

# Cross-distribute CA certificates for trust
cp node-globex/certs/globex-ca.crt node-acme/certs/
cp node-acme/certs/acme-ca.crt node-globex/certs/

echo "✅ Certificates generated successfully"
echo "Acme node cert: node-acme/certs/acme-node.crt"
echo "Globex node cert: node-globex/certs/globex-node.crt"
```

Run the script:

```bash
chmod +x shared/generate-certs.sh
./shared/generate-certs.sh
```

### Step 2: Create Acme Node Configuration

Create `node-acme/.env`:

```bash
# Database
POSTGRES_HOST=postgres-acme
POSTGRES_PORT=5432
POSTGRES_DB=sark_acme
POSTGRES_USER=sark
POSTGRES_PASSWORD=supersecret

# SARK Node
SARK_NODE_NAME=acme.com
SARK_NODE_DOMAIN=sark.acme.com
SARK_PORT=8000
SARK_FEDERATION_PORT=8443

# Federation
FEDERATION_ENABLED=true
FEDERATION_CERT=/certs/acme-node.crt
FEDERATION_KEY=/certs/acme-node.key
FEDERATION_CA=/certs/acme-ca.crt

# Trust anchors (other nodes' CAs)
FEDERATION_TRUST_ANCHORS=/certs/globex-ca.crt
```

Create `node-acme/config/federation.yaml`:

```yaml
federation:
  enabled: true
  node_name: "acme.com"
  endpoint: "https://sark.acme.com:8443"

  # mTLS configuration
  tls:
    cert_file: "/certs/acme-node.crt"
    key_file: "/certs/acme-node.key"
    ca_file: "/certs/acme-ca.crt"

  # Trusted federation partners
  trust_anchors:
    - name: "globex.com"
      ca_file: "/certs/globex-ca.crt"

  # Known federation nodes
  nodes:
    - name: "globex.com"
      endpoint: "https://sark.globex.com:8443"
      trust_anchor: "globex.com"

  # Discovery
  discovery:
    enabled: true
    method: "static"  # or "dns-sd"

  # Performance
  cache_ttl: 300  # Cache authorization decisions for 5 minutes
  timeout: 10     # Federation query timeout (seconds)
```

Create `node-acme/docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres-acme:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - acme-postgres-data:/var/lib/postgresql/data
    networks:
      - acme-network

  timescaledb-acme:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: sark_audit_acme
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - acme-timescale-data:/var/lib/postgresql/data
    networks:
      - acme-network

  sark-acme:
    image: sark:v2.0
    build:
      context: ../../
      dockerfile: Dockerfile
    ports:
      - "8000:8000"      # API
      - "8443:8443"      # Federation
    environment:
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_PORT=${POSTGRES_PORT}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - SARK_NODE_NAME=${SARK_NODE_NAME}
      - FEDERATION_ENABLED=${FEDERATION_ENABLED}
    volumes:
      - ./certs:/certs:ro
      - ./config:/config:ro
    depends_on:
      - postgres-acme
      - timescaledb-acme
    networks:
      - acme-network
      - federation-network
    command: >
      uvicorn sark.main:app
      --host 0.0.0.0
      --port 8000
      --ssl-keyfile /certs/acme-node.key
      --ssl-certfile /certs/acme-node.crt

networks:
  acme-network:
    driver: bridge
  federation-network:
    driver: bridge

volumes:
  acme-postgres-data:
  acme-timescale-data:
```

### Step 3: Start Acme Node

```bash
cd node-acme
docker-compose up -d

# Check logs
docker-compose logs -f sark-acme

# Wait for "Application startup complete"
```

Verify Acme node is running:

```bash
curl -k https://localhost:8443/api/v2/federation/health
```

**Response:**
```json
{
  "status": "healthy",
  "node": "acme.com",
  "federation_enabled": true,
  "trusted_nodes": ["globex.com"]
}
```

---

## Deploying the Second Node (Globex Ltd)

### Step 1: Create Globex Node Configuration

Similar to Acme, create:
- `node-globex/.env`
- `node-globex/config/federation.yaml`
- `node-globex/docker-compose.yml`

Update with Globex-specific values:

```bash
# node-globex/.env
SARK_NODE_NAME=globex.com
SARK_NODE_DOMAIN=sark.globex.com
POSTGRES_DB=sark_globex
# ... etc
```

```yaml
# node-globex/config/federation.yaml
federation:
  enabled: true
  node_name: "globex.com"
  endpoint: "https://sark.globex.com:8443"

  tls:
    cert_file: "/certs/globex-node.crt"
    key_file: "/certs/globex-node.key"
    ca_file: "/certs/globex-ca.crt"

  trust_anchors:
    - name: "acme.com"
      ca_file: "/certs/acme-ca.crt"

  nodes:
    - name: "acme.com"
      endpoint: "https://sark.acme.com:8443"
      trust_anchor: "acme.com"
```

### Step 2: Start Globex Node

```bash
cd node-globex
docker-compose up -d
docker-compose logs -f sark-globex
```

### Step 3: Verify Federation Connectivity

From Acme node, test connection to Globex:

```bash
docker-compose exec sark-acme python -c "
from sark.federation.client import FederationClient
import asyncio

async def test():
    client = FederationClient('globex.com')
    health = await client.check_health()
    print(f'Globex node health: {health}')

asyncio.run(test())
"
```

---

## Establishing Trust (mTLS)

### Verify mTLS Handshake

Test mutual TLS authentication:

```bash
# From Acme node, connect to Globex using client cert
openssl s_client \
  -connect sark.globex.com:8443 \
  -cert node-acme/certs/acme-node.crt \
  -key node-acme/certs/acme-node.key \
  -CAfile node-acme/certs/globex-ca.crt \
  -showcerts
```

Look for:
```
Verify return code: 0 (ok)
```

### Test Federation API

Test the federation authorization endpoint:

```bash
curl -k --cert node-acme/certs/acme-node.crt \
     --key node-acme/certs/acme-node.key \
     --cacert node-acme/certs/globex-ca.crt \
     -X POST https://sark.globex.com:8443/api/v2/federation/authorize \
     -H "Content-Type: application/json" \
     -d '{
       "request_id": "test-123",
       "source_node": "acme.com",
       "principal": {
         "id": "alice@acme.com",
         "type": "user",
         "source_org": "acme.com"
       },
       "resource_id": "test-resource",
       "capability_id": "test-capability",
       "action": "execute"
     }'
```

---

## Configuring Cross-Org Policies

### Acme Corp Policies

Create policies allowing Globex engineers limited access.

`node-acme/policies/cross-org-policy.rego`:

```rego
package sark.policies.federation

import future.keywords.if

# Allow Acme employees full access to Acme resources
allow if {
    input.principal.source_org == "acme.com"
    input.resource.owner_org == "acme.com"
}

# Allow Globex engineers READ access to Acme GitHub
allow if {
    input.principal.source_org == "globex.com"
    input.principal.attributes.role == "engineer"
    input.resource.owner_org == "acme.com"
    input.resource.name == "GitHub API"
    # Only read operations
    startswith(input.capability.id, "GET-")
}

# Deny Globex access to sensitive Acme resources
deny["External org cannot access sensitive resources"] if {
    input.principal.source_org == "globex.com"
    input.resource.sensitivity_level == "high"
}

# Rate limit cross-org access
deny["Rate limit exceeded for cross-org access"] if {
    input.principal.source_org != "acme.com"
    input.resource.owner_org == "acme.com"
    cross_org_rate_limit_exceeded(input.principal.id)
}

cross_org_rate_limit_exceeded(principal_id) if {
    # Count cross-org requests in last hour
    count([r | r := data.audit_log[_]
           r.principal_id == principal_id
           r.timestamp > time.now_ns() - (3600 * 1000000000)
           r.cross_org == true]) > 100
}

# Default deny
allow = false
```

Upload to Acme node:

```bash
curl -X POST http://localhost:8000/api/v1/policies \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"acme-federation-policy\",
    \"content\": \"$(cat node-acme/policies/cross-org-policy.rego)\"
  }"
```

### Globex Ltd Policies

`node-globex/policies/cross-org-policy.rego`:

```rego
package sark.policies.federation

import future.keywords.if

# Allow Globex employees full access to Globex resources
allow if {
    input.principal.source_org == "globex.com"
    input.resource.owner_org == "globex.com"
}

# Allow Acme developers READ access to Globex analytics
allow if {
    input.principal.source_org == "acme.com"
    input.principal.attributes.role == "developer"
    input.resource.owner_org == "globex.com"
    input.resource.name == "Analytics Service"
    input.capability.name == "QueryMetrics"
}

# Audit all cross-org access
audit_required if {
    input.principal.source_org != "globex.com"
}

# Default deny
allow = false
```

---

## Testing Federation

### Register Cross-Org Resources

**On Acme node**, register GitHub API:

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "http",
    "discovery_config": {
      "base_url": "https://api.github.com"
    },
    "name": "GitHub API",
    "owner_org": "acme.com",
    "sensitivity_level": "medium"
  }'
```

**On Globex node**, register Analytics Service:

```bash
curl -X POST http://localhost:8001/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "grpc",
    "discovery_config": {
      "endpoint": "analytics.globex.com:50051"
    },
    "name": "Analytics Service",
    "owner_org": "globex.com",
    "sensitivity_level": "medium"
  }'
```

### Test Cross-Org Access

Create test script `shared/test-federation.py`:

```python
"""Test SARK federation."""

import asyncio
import httpx


async def test_cross_org_access():
    """
    Test: Alice (Acme) accessing Globex analytics service.
    """
    print("🧪 Testing Federation: Alice@Acme → Globex Analytics")

    # Alice sends request to her local Acme node
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v2/authorize",
            json={
                "capability_id": "grpc-analytics-QueryMetrics",
                "principal_id": "alice@acme.com",
                "arguments": {
                    "query": "SELECT * FROM metrics WHERE date = '2024-11-29'"
                }
            }
        )

        print(f"Status: {response.status_code}")
        result = response.json()

        if result.get("success"):
            print("✅ Cross-org access ALLOWED")
            print(f"   Result: {result.get('result')}")
            print(f"   Duration: {result.get('duration_ms')}ms")
            print(f"   Evaluated by: {result.get('metadata', {}).get('evaluated_by')}")
        else:
            print("❌ Cross-org access DENIED")
            print(f"   Reason: {result.get('error')}")

    # Check audit logs on both nodes
    print("\n📊 Checking Audit Logs...")

    # Acme node (initiator)
    async with httpx.AsyncClient() as client:
        acme_audit = await client.get(
            "http://localhost:8000/api/v1/audit-log",
            params={"principal_id": "alice@acme.com", "limit": 1}
        )
        print(f"Acme audit: {acme_audit.json()['events'][0]}")

    # Globex node (resource owner)
    async with httpx.AsyncClient() as client:
        globex_audit = await client.get(
            "http://localhost:8001/api/v1/audit-log",
            params={"cross_org": "true", "limit": 1}
        )
        print(f"Globex audit: {globex_audit.json()['events'][0]}")


if __name__ == "__main__":
    asyncio.run(test_cross_org_access())
```

Run the test:

```bash
python shared/test-federation.py
```

**Expected Output:**
```
🧪 Testing Federation: Alice@Acme → Globex Analytics
Status: 200
✅ Cross-org access ALLOWED
   Result: {'metrics': [...]}
   Duration: 1234ms
   Evaluated by: globex.com

📊 Checking Audit Logs...
Acme audit: {
  "timestamp": "2024-11-29T10:30:00Z",
  "principal": "alice@acme.com",
  "resource": "Analytics Service",
  "resource_org": "globex.com",
  "cross_org": true,
  "decision": "allow"
}
Globex audit: {
  "timestamp": "2024-11-29T10:30:00Z",
  "principal": "alice@acme.com",
  "principal_org": "acme.com",
  "resource": "Analytics Service",
  "cross_org": true,
  "decision": "allow"
}
```

Perfect! Federation is working! 🎉

---

## Monitoring Federated Access

### Centralized Monitoring Dashboard

Create a monitoring script to aggregate metrics from both nodes:

```python
"""Federation monitoring dashboard."""

import asyncio
import httpx
from datetime import datetime, timedelta


async def federation_dashboard():
    """Display federation metrics from all nodes."""

    nodes = [
        {"name": "Acme", "url": "http://localhost:8000"},
        {"name": "Globex", "url": "http://localhost:8001"}
    ]

    print("🌐 SARK Federation Dashboard")
    print("=" * 60)

    for node in nodes:
        print(f"\n📍 {node['name']} Node ({node['url']})")

        async with httpx.AsyncClient() as client:
            # Node health
            health = await client.get(f"{node['url']}/api/v2/federation/health")
            health_data = health.json()
            print(f"   Status: {health_data['status']}")
            print(f"   Trusted nodes: {', '.join(health_data['trusted_nodes'])}")

            # Cross-org statistics
            since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            stats = await client.get(
                f"{node['url']}/api/v1/audit-log/stats",
                params={"cross_org": "true", "since": since}
            )
            stats_data = stats.json()

            print(f"\n   Cross-Org Access (last 24h):")
            print(f"   • Total requests: {stats_data.get('total', 0)}")
            print(f"   • Allowed: {stats_data.get('allowed', 0)}")
            print(f"   • Denied: {stats_data.get('denied', 0)}")
            print(f"   • Average latency: {stats_data.get('avg_latency_ms', 0)}ms")

            # Top cross-org principals
            print(f"\n   Top Cross-Org Principals:")
            for principal in stats_data.get('top_principals', [])[:5]:
                print(f"   • {principal['id']}: {principal['count']} requests")


if __name__ == "__main__":
    asyncio.run(federation_dashboard())
```

---

## Production Considerations

### 1. High Availability

Deploy multiple replicas per node:

```yaml
# kubernetes/acme-node-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark-acme
spec:
  replicas: 3  # Multiple replicas
  selector:
    matchLabels:
      app: sark-acme
  template:
    spec:
      containers:
      - name: sark
        image: sark:v2.0
        ports:
        - containerPort: 8000
        - containerPort: 8443
```

### 2. Certificate Rotation

Implement automatic certificate rotation:

```bash
# Rotate certificates without downtime
# 1. Generate new certificates
# 2. Add new cert to trust store
# 3. Update node to use new cert
# 4. Remove old cert from trust store after grace period
```

### 3. Network Security

- **Firewall rules**: Only allow federation port (8443) from known nodes
- **DDoS protection**: Rate limit federation queries
- **Network segmentation**: Isolate federation traffic

### 4. Monitoring and Alerting

Set up alerts for:
- Federation connectivity failures
- Certificate expiration
- Unusual cross-org access patterns
- High cross-org request latency

### 5. Data Residency

Ensure audit logs comply with data residency requirements:

```yaml
# Store cross-org audit logs locally only
audit:
  cross_org:
    local_only: true
    retention_days: 90
```

---

## Summary

Congratulations! You've successfully deployed a federated SARK environment with:

- ✅ Two independent SARK nodes (Acme and Globex)
- ✅ Mutual TLS authentication between nodes
- ✅ Cross-organization resource sharing
- ✅ Unified policy enforcement across organizations
- ✅ Distributed audit trail
- ✅ Monitoring and observability

### Next Steps

- **[Troubleshooting](../troubleshooting/V2_TROUBLESHOOTING.md)** - Debug federation issues
- **[Advanced Federation Patterns](../v2.0/FEDERATION_SPEC.md)** - DNS-SD, multi-region
- **Production Hardening** - Security best practices

---

**Happy federating!** 🌐

SARK v2.0 - Govern across organizations
