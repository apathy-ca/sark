# SARK v2.0 Federation Setup Guide

## Overview

SARK v2.0 Federation enables secure cross-organization governance by allowing multiple SARK instances to discover and communicate with each other. This guide covers the complete setup process for establishing a SARK federation.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Certificate Setup (mTLS)](#certificate-setup-mtls)
4. [Node Discovery Configuration](#node-discovery-configuration)
5. [Trust Establishment](#trust-establishment)
6. [Federation Testing](#federation-testing)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

SARK Federation consists of three core components:

### 1. Discovery Service
Automatically discovers SARK nodes using:
- **DNS-SD** (DNS Service Discovery - RFC 6763)
- **mDNS** (Multicast DNS - RFC 6762) for local networks
- **Consul** for containerized/orchestrated environments
- **Manual** configuration for static deployments

### 2. Trust Service
Establishes and manages trust relationships using:
- **mTLS** (Mutual TLS) with X.509 certificates
- Certificate validation and verification
- Trust anchor management
- Challenge-response authentication
- Certificate revocation support

### 3. Routing Service
Routes requests across federation nodes with:
- Resource lookup and resolution
- Circuit breaking for fault tolerance
- Load balancing across nodes
- Audit correlation for cross-node operations
- Automatic failover

---

## Prerequisites

### Software Requirements
- SARK v2.0 or later
- PostgreSQL 13+ (with TimescaleDB for cost tracking)
- Redis 5+ (for caching)
- Python 3.11+

### Network Requirements
- mTLS certificates (CA, node certificates, private keys)
- Network connectivity between federation nodes
- DNS or mDNS support (for automatic discovery)
- Firewall rules allowing HTTPS traffic between nodes

### Security Requirements
- Secure certificate storage
- Certificate rotation capability
- Audit logging enabled
- Rate limiting configured

---

## Certificate Setup (mTLS)

Federation requires mutual TLS authentication. Each SARK node needs:
1. A CA certificate (shared trust anchor)
2. A node certificate signed by the CA
3. A private key for the node certificate

### Step 1: Create Certificate Authority (CA)

```bash
# Generate CA private key
openssl genrsa -out ca-key.pem 4096

# Generate CA certificate (valid for 10 years)
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/C=US/ST=CA/L=San Francisco/O=SARK Federation/CN=SARK CA"
```

### Step 2: Generate Node Certificates

For each SARK node in the federation:

```bash
# Generate node private key
openssl genrsa -out node1-key.pem 2048

# Create certificate signing request
openssl req -new -key node1-key.pem -out node1-csr.pem \
  -subj "/C=US/ST=CA/L=San Francisco/O=SARK Federation/CN=node1.sark.example.com"

# Create certificate extensions file
cat > node1-ext.cnf <<EOF
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=DNS:node1.sark.example.com,DNS:*.node1.sark.example.com
EOF

# Sign certificate with CA
openssl x509 -req -in node1-csr.pem -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out node1-cert.pem -days 365 -extfile node1-ext.cnf
```

### Step 3: Verify Certificates

```bash
# Verify certificate is signed by CA
openssl verify -CAfile ca-cert.pem node1-cert.pem

# Check certificate details
openssl x509 -in node1-cert.pem -text -noout
```

### Step 4: Distribute Certificates

On each SARK node, create certificate directory:

```bash
mkdir -p /etc/sark/certs
chmod 700 /etc/sark/certs

# Copy certificates
cp ca-cert.pem /etc/sark/certs/
cp node1-cert.pem /etc/sark/certs/
cp node1-key.pem /etc/sark/certs/
chmod 600 /etc/sark/certs/node1-key.pem
```

---

## Node Discovery Configuration

### Method 1: DNS-SD (Recommended for Production)

Configure DNS SRV records for your SARK nodes:

```dns
; SRV record format: _service._proto.domain TTL class SRV priority weight port target
_sark._tcp.example.com. 3600 IN SRV 10 60 8000 node1.example.com.
_sark._tcp.example.com. 3600 IN SRV 10 40 8000 node2.example.com.

; TXT records for additional metadata
_sark._tcp.example.com. 3600 IN TXT "version=2.0" "region=us-east"
```

Configure SARK to use DNS-SD:

```python
# config.py
FEDERATION_DISCOVERY_METHOD = "dns-sd"
FEDERATION_DNS_NAMESERVER = "8.8.8.8"  # Optional
FEDERATION_SERVICE_TYPE = "_sark._tcp.example.com."
```

### Method 2: mDNS (For Local Networks)

mDNS works without DNS infrastructure. Enable on each node:

```python
# config.py
FEDERATION_DISCOVERY_METHOD = "mdns"
FEDERATION_SERVICE_TYPE = "_sark._tcp.local."
FEDERATION_MDNS_ADVERTISE = True  # Advertise this node via mDNS
```

### Method 3: Consul (For Kubernetes/Docker)

Register SARK nodes with Consul:

```bash
# Register service
curl -X PUT http://consul:8500/v1/agent/service/register \
  -d '{
    "ID": "sark-node1",
    "Name": "sark",
    "Tags": ["v2.0", "production"],
    "Address": "node1.example.com",
    "Port": 8000,
    "Meta": {
      "version": "2.0.0",
      "region": "us-east-1"
    },
    "Check": {
      "HTTP": "https://node1.example.com:8000/api/v2/health",
      "Interval": "10s",
      "Timeout": "1s"
    }
  }'
```

Configure SARK:

```python
# config.py
FEDERATION_DISCOVERY_METHOD = "consul"
FEDERATION_CONSUL_URL = "http://consul:8500"
FEDERATION_SERVICE_NAME = "sark"
```

### Method 4: Manual Configuration

For static deployments, manually configure federation nodes:

```python
# config.py
FEDERATION_DISCOVERY_METHOD = "manual"
FEDERATION_NODES = [
    {
        "node_id": "node2",
        "name": "SARK Node 2",
        "endpoint": "https://node2.example.com:8000",
    },
    {
        "node_id": "node3",
        "name": "SARK Node 3",
        "endpoint": "https://node3.example.com:8000",
    }
]
```

---

## Trust Establishment

### Step 1: Configure Trust Service

On each node, configure the trust service:

```python
# config.py
FEDERATION_CA_CERT_PATH = "/etc/sark/certs/ca-cert.pem"
FEDERATION_NODE_CERT_PATH = "/etc/sark/certs/node1-cert.pem"
FEDERATION_NODE_KEY_PATH = "/etc/sark/certs/node1-key.pem"
FEDERATION_NODE_ID = "node1"  # Unique identifier for this node
```

### Step 2: Establish Trust via API

Use the SARK API to establish trust with other nodes:

```bash
# Get node certificate
NODE_CERT=$(cat /etc/sark/certs/node2-cert.pem)

# Establish trust
curl -X POST https://node1.example.com:8000/api/v2/federation/trust \
  -H "Content-Type: application/json" \
  -d "{
    \"node_id\": \"node2\",
    \"client_cert\": \"$NODE_CERT\"
  }"
```

Response:
```json
{
  "success": true,
  "node_id": "node2",
  "trust_level": "trusted",
  "certificate_info": {
    "subject": "CN=node2.sark.example.com",
    "issuer": "CN=SARK CA",
    "serial_number": "01",
    "not_before": "2024-01-01T00:00:00Z",
    "not_after": "2025-01-01T00:00:00Z",
    "fingerprint_sha256": "abc123..."
  },
  "expires_at": "2025-01-01T00:00:00Z"
}
```

### Step 3: Verify Trust

```bash
# Verify trust with a node
curl -X POST https://node1.example.com:8000/api/v2/federation/verify \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node2",
    "certificate_fingerprint": "abc123..."
  }'
```

### Step 4: List Trusted Nodes

```bash
# Get all federation nodes
curl https://node1.example.com:8000/api/v2/federation/nodes
```

---

## Federation Testing

### Test 1: Discovery

```python
from sark.services.federation import DiscoveryService
from sark.models.federation import DiscoveryQuery, DiscoveryMethod

# Create discovery service
discovery = DiscoveryService()

# Test mDNS discovery
query = DiscoveryQuery(
    method=DiscoveryMethod.MDNS,
    service_type="_sark._tcp.local.",
    timeout_seconds=5
)

response = await discovery.discover(query)
print(f"Found {response.total_found} nodes")
for record in response.records:
    print(f"  - {record.instance_name} at {record.hostname}:{record.port}")
```

### Test 2: Trust Establishment

```python
from sark.services.federation import TrustService
from sark.models.federation import TrustEstablishmentRequest

# Create trust service
trust = TrustService(
    ca_cert_path="/etc/sark/certs/ca-cert.pem",
    cert_path="/etc/sark/certs/node1-cert.pem",
    key_path="/etc/sark/certs/node1-key.pem"
)

# Load node2 certificate
with open("/etc/sark/certs/node2-cert.pem") as f:
    node2_cert = f.read()

# Establish trust
request = TrustEstablishmentRequest(
    node_id="node2",
    client_cert=node2_cert
)

response = await trust.establish_trust(request, db)
assert response.success
print(f"Trust level: {response.trust_level}")
```

### Test 3: Federated Resource Access

```python
from sark.services.federation import RoutingService
from sark.models.federation import FederatedResourceRequest

# Create routing service
routing = RoutingService(local_node_id="node1")

# Invoke resource on node2
request = FederatedResourceRequest(
    target_node_id="node2",
    resource_id="mcp-server-filesystem",
    capability_id="read_file",
    principal_id="user@example.com",
    arguments={"path": "/etc/hosts"}
)

response = await routing.invoke_federated(request, db)
if response.success:
    print(f"Result: {response.result}")
else:
    print(f"Error: {response.error}")
```

### Test 4: Health Checks

```bash
# Check federation health
curl https://node1.example.com:8000/api/v2/federation/health
```

Response:
```json
{
  "total_nodes": 3,
  "online_nodes": 3,
  "offline_nodes": 0,
  "degraded_nodes": 0,
  "node_health": [
    {
      "node_id": "node1",
      "status": "online",
      "last_check": "2024-01-01T12:00:00Z",
      "response_time_ms": 1.2
    },
    {
      "node_id": "node2",
      "status": "online",
      "last_check": "2024-01-01T12:00:00Z",
      "response_time_ms": 15.3
    }
  ]
}
```

---

## Production Deployment

### High Availability Setup

For production, deploy at least 3 SARK nodes:

```yaml
# docker-compose.federation.yml
version: '3.8'

services:
  sark-node1:
    image: sark:2.0
    environment:
      FEDERATION_NODE_ID: node1
      FEDERATION_DISCOVERY_METHOD: consul
      FEDERATION_CONSUL_URL: http://consul:8500
    volumes:
      - /etc/sark/certs:/certs:ro
    networks:
      - federation

  sark-node2:
    image: sark:2.0
    environment:
      FEDERATION_NODE_ID: node2
      FEDERATION_DISCOVERY_METHOD: consul
      FEDERATION_CONSUL_URL: http://consul:8500
    volumes:
      - /etc/sark/certs:/certs:ro
    networks:
      - federation

  sark-node3:
    image: sark:2.0
    environment:
      FEDERATION_NODE_ID: node3
      FEDERATION_DISCOVERY_METHOD: consul
      FEDERATION_CONSUL_URL: http://consul:8500
    volumes:
      - /etc/sark/certs:/certs:ro
    networks:
      - federation

  consul:
    image: consul:latest
    networks:
      - federation

networks:
  federation:
    driver: bridge
```

### Rate Limiting

Configure rate limits for federated requests:

```python
# config.py
FEDERATION_RATE_LIMIT_PER_HOUR = 10000  # Default for all nodes
FEDERATION_RATE_LIMIT_BURST = 100  # Burst allowance
```

### Monitoring

Monitor federation health:

```python
# Prometheus metrics
federation_requests_total{node="node2", status="success"}
federation_requests_total{node="node2", status="error"}
federation_request_duration_seconds{node="node2"}
federation_circuit_breaker_state{node="node2"} # 0=closed, 1=open, 2=half-open
```

### Certificate Rotation

Set up automatic certificate rotation:

```bash
# cert-rotate.sh
#!/bin/bash

# Generate new certificate
openssl genrsa -out node1-key-new.pem 2048
openssl req -new -key node1-key-new.pem -out node1-csr-new.pem
openssl x509 -req -in node1-csr-new.pem -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out node1-cert-new.pem -days 365

# Update SARK configuration
mv /etc/sark/certs/node1-cert.pem /etc/sark/certs/node1-cert.pem.old
mv /etc/sark/certs/node1-key.pem /etc/sark/certs/node1-key.pem.old
cp node1-cert-new.pem /etc/sark/certs/node1-cert.pem
cp node1-key-new.pem /etc/sark/certs/node1-key.pem

# Restart SARK
systemctl restart sark
```

Schedule with cron:
```cron
# Rotate certificates monthly
0 0 1 * * /usr/local/bin/cert-rotate.sh
```

---

## Troubleshooting

### Issue: Discovery not finding nodes

**Symptoms**: `discover()` returns empty list

**Solutions**:
1. Check network connectivity: `ping node2.example.com`
2. Verify DNS records: `dig SRV _sark._tcp.example.com`
3. For mDNS, ensure multicast is enabled on network
4. Check firewall rules: port 5353 (mDNS), port 8600 (Consul DNS)

### Issue: Trust establishment fails

**Symptoms**: `establish_trust()` returns `success: false`

**Solutions**:
1. Verify certificate validity: `openssl x509 -in node-cert.pem -text -noout`
2. Check certificate is signed by CA: `openssl verify -CAfile ca-cert.pem node-cert.pem`
3. Ensure certificate has clientAuth and serverAuth extended key usage
4. Check certificate not expired: `openssl x509 -in node-cert.pem -noout -dates`

### Issue: Federated invocation fails

**Symptoms**: `invoke_federated()` returns error

**Solutions**:
1. Check circuit breaker state: `GET /api/v2/federation/nodes/{node_id}/circuit`
2. Verify node is trusted: `GET /api/v2/federation/nodes`
3. Test connectivity: `curl https://node2.example.com:8000/api/v2/health`
4. Check audit logs for detailed error: `GET /api/v2/audit/events?correlation_id={id}`

### Issue: Circuit breaker stuck open

**Symptoms**: Node always unavailable

**Solutions**:
1. Check node health: `GET /api/v2/federation/health`
2. Manually reset circuit breaker: `POST /api/v2/federation/nodes/{node_id}/reset-circuit`
3. Verify network connectivity restored
4. Check node logs for underlying issues

### Issue: Certificate fingerprint mismatch

**Symptoms**: `verify_trust()` fails with fingerprint mismatch

**Solutions**:
1. Recalculate fingerprint: `openssl x509 -in node-cert.pem -noout -fingerprint -sha256`
2. Update federation node record with new fingerprint
3. Re-establish trust: `POST /api/v2/federation/trust`

---

## Security Best Practices

1. **Certificate Security**
   - Store private keys securely (encrypted filesystem, HSM)
   - Rotate certificates regularly (recommended: every 90 days)
   - Use strong key sizes (minimum 2048-bit RSA or 256-bit ECDSA)
   - Monitor certificate expiration

2. **Network Security**
   - Use TLS 1.2+ only (disable TLS 1.0/1.1)
   - Enable perfect forward secrecy (PFS)
   - Use strong cipher suites
   - Implement network segmentation

3. **Access Control**
   - Implement strict RBAC for federation operations
   - Audit all federation requests
   - Rate limit federated requests
   - Monitor for anomalous access patterns

4. **Monitoring**
   - Track certificate expiration dates
   - Monitor circuit breaker states
   - Alert on federation failures
   - Track request latencies and error rates

---

## Additional Resources

- [SARK v2.0 API Reference](../api/v2/API_REFERENCE.md)
- [GRID Protocol Specification](../../GRID_PROTOCOL_SPECIFICATION_v0.1.md)
- [Security Best Practices](../SECURITY_BEST_PRACTICES.md)
- [Production Deployment Guide](../PRODUCTION_DEPLOYMENT.md)

---

## Support

For issues or questions about SARK Federation:
- GitHub Issues: https://github.com/sark/sark/issues
- Documentation: https://docs.sark.ai
- Community Slack: https://sark.slack.com

---

*Last updated: 2024-12-01*
*SARK Version: 2.0.0*
