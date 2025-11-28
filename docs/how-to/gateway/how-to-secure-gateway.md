# How to Secure SARK Gateway

This comprehensive guide shows you how to implement production-grade security for the SARK Gateway, from authentication to secret management.

## Before You Begin

**Prerequisites:**
- SARK Gateway deployed (development or production)
- Admin access to gateway configuration
- Understanding of authentication mechanisms (JWT, API keys, mTLS)
- Access to secret management system (optional but recommended)
- SSL/TLS certificates for production deployment

**What You'll Learn:**
- Implement authentication using JWT, API keys, and mTLS
- Set up API key management and rotation
- Configure rate limiting to prevent abuse
- Review and analyze audit logs
- Integrate with HashiCorp Vault or Kubernetes Secrets
- Follow production security checklist

**Security Principles:**
- **Defense in Depth**: Multiple layers of security
- **Least Privilege**: Minimum necessary access
- **Zero Trust**: Verify everything, trust nothing
- **Audit Everything**: Comprehensive logging
- **Fail Secure**: Default deny, explicit allow

## Authentication Best Practices

### Option 1: JWT Authentication (Recommended for User Access)

**Why JWT:**
- Stateless authentication
- Contains user claims (roles, permissions)
- Standard format (RFC 7519)
- Short-lived with refresh tokens

#### Step 1: Configure JWT Validation

Create `config/auth-jwt.yaml`:

```yaml
authentication:
  type: jwt

  jwt:
    # Public key for verification
    verification_keys:
      - type: jwks_url
        url: https://auth.example.com/.well-known/jwks.json
        cache_duration: 1h

      - type: pem
        value: |
          -----BEGIN PUBLIC KEY-----
          MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
          -----END PUBLIC KEY-----

    # Validation rules
    validation:
      issuer: https://auth.example.com
      audience: sark-gateway
      require_expiration: true
      clock_skew: 30s

    # Required claims
    required_claims:
      - sub  # Subject (user ID)
      - exp  # Expiration
      - iat  # Issued at
      - role # User role

    # Extract user information from claims
    claims_mapping:
      user_id: sub
      username: preferred_username
      email: email
      role: role
      groups: groups

    # Token location
    token_sources:
      - header: Authorization
        scheme: Bearer
      - query: access_token  # Fallback for WebSocket
      - cookie: auth_token   # Fallback for browsers
```

Apply configuration:

```bash
kubectl create configmap gateway-auth-config \
  --from-file=auth-jwt.yaml \
  -n sark-system

kubectl set env deployment/sark-gateway \
  AUTH_CONFIG=/etc/gateway/auth-jwt.yaml \
  -n sark-system
```

#### Step 2: Test JWT Authentication

Generate test JWT:

```bash
# Using jwt.io or a library
cat > generate_token.py <<'EOF'
import jwt
from datetime import datetime, timedelta

# Generate JWT
payload = {
    'sub': 'user-123',
    'preferred_username': 'alice',
    'email': 'alice@example.com',
    'role': 'developer',
    'groups': ['engineering', 'platform'],
    'exp': datetime.utcnow() + timedelta(hours=1),
    'iat': datetime.utcnow(),
    'iss': 'https://auth.example.com',
    'aud': 'sark-gateway'
}

# Sign with private key (in production, use auth server)
private_key = open('private_key.pem').read()
token = jwt.encode(payload, private_key, algorithm='RS256')
print(token)
EOF

python generate_token.py
```

**Expected Output:**
```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsInByZWZlcnJlZF91c2VybmFtZSI6ImFsaWNlIiwiZW1haWwiOiJhbGljZUBleGFtcGxlLmNvbSIsInJvbGUiOiJkZXZlbG9wZXIiLCJncm91cHMiOlsiZW5naW5lZXJpbmciLCJwbGF0Zm9ybSJdLCJleHAiOjE3MDUzMjg0MDAsImlhdCI6MTcwNTMyNDgwMCwiaXNzIjoiaHR0cHM6Ly9hdXRoLmV4YW1wbGUuY29tIiwiYXVkIjoic2Fyay1nYXRld2F5In0...
```

Test authentication:

```bash
TOKEN="eyJhbGci..."

curl http://gateway.example.com/api/v1/tools \
  -H "Authorization: Bearer ${TOKEN}"
```

**Expected Response (valid):**
```json
{
  "tools": [...],
  "user": {
    "id": "user-123",
    "username": "alice",
    "role": "developer"
  }
}
```

**Expected Response (invalid):**
```json
{
  "error": "authentication_failed",
  "message": "Invalid JWT token",
  "details": {
    "reason": "token_expired"
  }
}
```

#### Step 3: Implement Token Refresh Flow

Create refresh token endpoint:

```yaml
# config/auth-jwt.yaml (continued)
authentication:
  jwt:
    refresh_tokens:
      enabled: true
      endpoint: /api/v1/auth/refresh
      cookie_name: refresh_token
      cookie_secure: true
      cookie_httponly: true
      cookie_samesite: strict
      max_age: 7d  # Refresh tokens valid for 7 days
```

Client refresh flow:

```bash
# Store refresh token securely
REFRESH_TOKEN="abc123..."

# Access token expired, refresh it
NEW_TOKEN=$(curl -X POST http://gateway.example.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"${REFRESH_TOKEN}\"}" \
  | jq -r '.access_token')

# Use new token
curl http://gateway.example.com/api/v1/tools \
  -H "Authorization: Bearer ${NEW_TOKEN}"
```

### Option 2: API Key Authentication (Recommended for Service Accounts)

**Why API Keys:**
- Simple for machine-to-machine auth
- Long-lived credentials
- Easy to rotate
- Per-key rate limiting

#### Step 1: Configure API Key Authentication

Create `config/auth-apikey.yaml`:

```yaml
authentication:
  type: api_key

  api_key:
    # Key location
    header_name: X-API-Key

    # Storage backend
    storage:
      type: database
      connection_string: postgresql://user:pass@db:5432/gateway

    # Or use Redis
    # storage:
    #   type: redis
    #   address: redis:6379
    #   database: 0

    # Key properties
    key_length: 32
    key_prefix: sk_
    hash_algorithm: sha256

    # Validation
    require_key_name: true
    allow_query_param: false  # More secure

    # Rate limiting per key
    rate_limits:
      default:
        requests_per_minute: 100
        burst: 20
```

#### Step 2: Generate API Keys

Create API key management script:

```bash
#!/bin/bash
# generate_api_key.sh

set -e

API_KEY_NAME=$1
USER_ID=$2
ROLE=${3:-"developer"}

if [ -z "$API_KEY_NAME" ] || [ -z "$USER_ID" ]; then
  echo "Usage: $0 <key_name> <user_id> [role]"
  exit 1
fi

# Generate API key
curl -X POST http://gateway.example.com/api/v1/auth/keys \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"${API_KEY_NAME}\",
    \"user_id\": \"${USER_ID}\",
    \"role\": \"${ROLE}\",
    \"metadata\": {
      \"created_by\": \"admin\",
      \"purpose\": \"automation\"
    },
    \"expires_at\": \"$(date -u -d '+90 days' +%Y-%m-%dT%H:%M:%SZ)\"
  }" | jq
```

Run script:

```bash
chmod +x generate_api_key.sh
./generate_api_key.sh "ci-pipeline" "service-ci" "automation"
```

**Expected Response:**
```json
{
  "key_id": "key_abc123",
  "api_key": "sk_1234567890abcdef1234567890abcdef",
  "name": "ci-pipeline",
  "user_id": "service-ci",
  "role": "automation",
  "created_at": "2024-01-15T10:00:00Z",
  "expires_at": "2024-04-15T10:00:00Z",
  "rate_limit": {
    "requests_per_minute": 100,
    "burst": 20
  }
}
```

**⚠️ SECURITY WARNING:**
The API key is only shown once. Store it securely immediately.

#### Step 3: Use API Key

```bash
API_KEY="sk_1234567890abcdef1234567890abcdef"

curl http://gateway.example.com/api/v1/tools/invoke \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "data-server",
    "tool_name": "analyze_data",
    "arguments": {}
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "result": {...},
  "auth": {
    "key_id": "key_abc123",
    "user_id": "service-ci",
    "role": "automation"
  }
}
```

### Option 3: Mutual TLS (mTLS) Authentication (Highest Security)

**Why mTLS:**
- Strongest authentication method
- Client and server both verified
- No credentials in requests
- Certificate-based identity

#### Step 1: Generate Client Certificates

Create certificate authority:

```bash
# Generate CA private key
openssl genrsa -out ca-key.pem 4096

# Generate CA certificate
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/C=US/ST=CA/L=San Francisco/O=Example/CN=SARK CA"

# Generate client private key
openssl genrsa -out client-key.pem 2048

# Generate client certificate signing request
openssl req -new -key client-key.pem -out client-csr.pem \
  -subj "/C=US/ST=CA/L=San Francisco/O=Example/CN=mcp-server-01"

# Sign client certificate
openssl x509 -req -days 365 -in client-csr.pem \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -out client-cert.pem
```

**Expected Output:**
```
Signature ok
subject=C = US, ST = CA, L = San Francisco, O = Example, CN = mcp-server-01
Getting CA Private Key
```

#### Step 2: Configure Gateway for mTLS

Create `config/auth-mtls.yaml`:

```yaml
authentication:
  type: mtls

  mtls:
    # CA certificate for client verification
    ca_cert_path: /etc/gateway/certs/ca-cert.pem

    # Server certificate and key
    server_cert_path: /etc/gateway/certs/server-cert.pem
    server_key_path: /etc/gateway/certs/server-key.pem

    # Client verification
    client_cert_required: true
    verify_client_cert: true

    # Extract identity from certificate
    identity_field: CN  # Common Name

    # Map certificate CN to user
    user_mapping:
      "mcp-server-01":
        user_id: "service-mcp-01"
        role: "server"
      "ci-pipeline":
        user_id: "service-ci"
        role: "automation"

    # Certificate validation
    check_revocation: true
    crl_url: https://crl.example.com/revoked.crl

    # TLS settings
    min_tls_version: "1.2"
    cipher_suites:
      - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
      - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
```

Mount certificates:

```bash
kubectl create secret tls gateway-tls \
  --cert=server-cert.pem \
  --key=server-key.pem \
  -n sark-system

kubectl create secret generic gateway-ca \
  --from-file=ca-cert.pem \
  -n sark-system

kubectl create configmap gateway-mtls-config \
  --from-file=auth-mtls.yaml \
  -n sark-system
```

#### Step 3: Test mTLS Connection

```bash
curl https://gateway.example.com/api/v1/tools \
  --cert client-cert.pem \
  --key client-key.pem \
  --cacert ca-cert.pem
```

**Expected Response (valid certificate):**
```json
{
  "tools": [...],
  "auth": {
    "type": "mtls",
    "user_id": "service-mcp-01",
    "role": "server",
    "certificate_subject": "CN=mcp-server-01,O=Example,L=San Francisco,ST=CA,C=US"
  }
}
```

**Expected Response (invalid certificate):**
```
curl: (35) error:14094412:SSL routines:ssl3_read_bytes:sslv3 alert bad certificate
```

## API Key Management and Rotation

### Step 1: List Active Keys

```bash
curl http://gateway.example.com/api/v1/auth/keys \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  | jq '.keys[] | {id, name, user_id, expires_at, last_used}'
```

**Expected Response:**
```json
{
  "id": "key_abc123",
  "name": "ci-pipeline",
  "user_id": "service-ci",
  "expires_at": "2024-04-15T10:00:00Z",
  "last_used": "2024-01-15T14:25:00Z"
}
{
  "id": "key_def456",
  "name": "monitoring",
  "user_id": "service-monitor",
  "expires_at": "2024-06-01T10:00:00Z",
  "last_used": "2024-01-15T14:30:00Z"
}
```

### Step 2: Rotate API Key

Create rotation script:

```bash
#!/bin/bash
# rotate_api_key.sh

set -e

KEY_ID=$1
GRACE_PERIOD=${2:-3600}  # 1 hour default

# Generate new key
NEW_KEY=$(curl -X POST http://gateway.example.com/api/v1/auth/keys/${KEY_ID}/rotate \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"grace_period_seconds\": ${GRACE_PERIOD}
  }" | jq -r '.new_key')

echo "New API Key: ${NEW_KEY}"
echo "Old key will be valid for ${GRACE_PERIOD} seconds"
echo ""
echo "Action items:"
echo "1. Update application with new key"
echo "2. Verify application works with new key"
echo "3. Old key automatically revoked after grace period"
```

Run rotation:

```bash
./rotate_api_key.sh key_abc123 7200  # 2 hour grace period
```

**Expected Output:**
```
New API Key: sk_9876543210fedcba9876543210fedcba
Old key will be valid for 7200 seconds

Action items:
1. Update application with new key
2. Verify application works with new key
3. Old key automatically revoked after grace period
```

### Step 3: Revoke Compromised Key

```bash
# Immediate revocation
curl -X DELETE http://gateway.example.com/api/v1/auth/keys/key_abc123 \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "key_compromised",
    "revoked_by": "security-team"
  }'
```

**Expected Response:**
```json
{
  "status": "revoked",
  "key_id": "key_abc123",
  "revoked_at": "2024-01-15T14:30:00Z",
  "revoked_by": "security-team",
  "reason": "key_compromised"
}
```

### Step 4: Automate Key Rotation

Create cron job for regular rotation:

```yaml
# kubernetes/cronjob-key-rotation.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: rotate-api-keys
  namespace: sark-system
spec:
  schedule: "0 0 1 * *"  # Monthly on 1st at midnight
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: rotate-keys
            image: curlimages/curl:latest
            command:
            - /bin/sh
            - -c
            - |
              # Get all keys expiring in next 30 days
              EXPIRING_KEYS=$(curl -s http://gateway/api/v1/auth/keys?expiring_within=30d \
                -H "Authorization: Bearer ${ADMIN_TOKEN}" \
                | jq -r '.keys[].id')

              # Rotate each key
              for KEY_ID in $EXPIRING_KEYS; do
                echo "Rotating key: $KEY_ID"
                curl -X POST http://gateway/api/v1/auth/keys/${KEY_ID}/rotate \
                  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
                  -d '{"grace_period_seconds": 86400}'
              done
            env:
            - name: ADMIN_TOKEN
              valueFrom:
                secretKeyRef:
                  name: gateway-admin-token
                  key: token
          restartPolicy: OnFailure
```

## Rate Limiting Configuration

### Step 1: Configure Global Rate Limits

Create `config/rate-limits.yaml`:

```yaml
rate_limiting:
  enabled: true

  # Global limits (per gateway instance)
  global:
    requests_per_second: 1000
    burst: 2000

  # Per-user limits
  per_user:
    default:
      requests_per_minute: 100
      burst: 20

    # Override for specific roles
    by_role:
      admin:
        requests_per_minute: 1000
        burst: 200
      developer:
        requests_per_minute: 500
        burst: 100
      viewer:
        requests_per_minute: 100
        burst: 20

  # Per-API-key limits
  per_api_key:
    default:
      requests_per_minute: 200
      burst: 40

  # Per-endpoint limits
  per_endpoint:
    "/api/v1/tools/invoke":
      requests_per_minute: 60
      burst: 10
    "/api/v1/servers/register":
      requests_per_minute: 10
      burst: 2

  # Rate limit by IP address (for unauthenticated endpoints)
  per_ip:
    enabled: true
    requests_per_minute: 10
    burst: 5
    whitelist:
      - 10.0.0.0/8      # Internal network
      - 192.168.0.0/16  # Private network

  # Storage backend for distributed rate limiting
  storage:
    type: redis
    address: redis:6379
    database: 1
    key_prefix: "ratelimit:"

  # Response headers
  include_headers: true
  headers:
    limit: "X-RateLimit-Limit"
    remaining: "X-RateLimit-Remaining"
    reset: "X-RateLimit-Reset"
```

Apply configuration:

```bash
kubectl create configmap gateway-ratelimit-config \
  --from-file=rate-limits.yaml \
  -n sark-system

kubectl rollout restart deployment/sark-gateway -n sark-system
```

### Step 2: Test Rate Limiting

```bash
# Test rate limit
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code} " \
    http://gateway.example.com/api/v1/tools \
    -H "Authorization: Bearer ${TOKEN}"
  sleep 0.1
done
```

**Expected Output:**
```
200 200 200 ... 200 429 429 429
```

**After 100 requests:** Status 429 (Too Many Requests)

View rate limit headers:

```bash
curl -I http://gateway.example.com/api/v1/tools \
  -H "Authorization: Bearer ${TOKEN}"
```

**Expected Response:**
```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705324920
Content-Type: application/json
```

### Step 3: Handle Rate Limit Errors

Client implementation:

```python
import time
import requests

def call_gateway_with_retry(url, headers, max_retries=3):
    """Call gateway with rate limit retry logic."""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            # Rate limited
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = max(reset_time - time.time(), 1)

            print(f"Rate limited. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue

        return response

    raise Exception("Max retries exceeded")

# Usage
response = call_gateway_with_retry(
    "http://gateway.example.com/api/v1/tools",
    headers={"Authorization": f"Bearer {token}"}
)
```

## Audit Log Review Procedures

### Step 1: Enable Comprehensive Audit Logging

Create `config/audit-logging.yaml`:

```yaml
audit_logging:
  enabled: true

  # What to log
  events:
    - authentication_success
    - authentication_failure
    - authorization_success
    - authorization_failure
    - tool_invocation
    - server_registration
    - server_deregistration
    - policy_decision
    - api_key_created
    - api_key_rotated
    - api_key_revoked
    - rate_limit_exceeded
    -
_error

  # Log format
  format: json

  # Log fields
  fields:
    - timestamp
    - event_type
    - user_id
    - username
    - ip_address
    - user_agent
    - request_id
    - tool_name
    - server_id
    - policy_decision
    - status_code
    - error_message
    - duration_ms

  # Output
  outputs:
    # File output
    - type: file
      path: /var/log/sark-gateway/audit.log
      rotation:
        max_size: 100MB
        max_age: 90d
        max_backups: 10
        compress: true

    # Syslog output
    - type: syslog
      address: syslog.example.com:514
      protocol: tcp
      tag: sark-gateway

    # HTTP webhook
    - type: webhook
      url: https://siem.example.com/ingest
      method: POST
      headers:
        Authorization: "Bearer ${SIEM_TOKEN}"
      batch_size: 100
      batch_timeout: 5s

  # Filtering
  exclude_paths:
    - /health
    - /ready
    - /metrics

  # Sampling (for high-volume endpoints)
  sampling:
    enabled: true
    rate: 0.1  # Log 10% of requests
    always_log_on_error: true
```

### Step 2: Query Audit Logs

Search for authentication failures:

```bash
# Using jq
cat /var/log/sark-gateway/audit.log \
  | jq 'select(.event_type == "authentication_failure")' \
  | jq '{timestamp, user_id, ip_address, error: .error_message}'
```

**Expected Output:**
```json
{
  "timestamp": "2024-01-15T14:25:00Z",
  "user_id": "unknown",
  "ip_address": "203.0.113.42",
  "error": "Invalid JWT token"
}
{
  "timestamp": "2024-01-15T14:25:05Z",
  "user_id": "unknown",
  "ip_address": "203.0.113.42",
  "error": "Token expired"
}
```

Search for policy denials:

```bash
cat /var/log/sark-gateway/audit.log \
  | jq 'select(.event_type == "authorization_failure")' \
  | jq '{timestamp, user_id, tool_name, reason: .policy_decision.reasons}'
```

**Expected Output:**
```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "user_id": "user-123",
  "tool_name": "deploy_service",
  "reason": ["role_not_allowed"]
}
```

### Step 3: Create Audit Dashboards

Splunk query:

```spl
index=sark_gateway event_type=authentication_failure
| stats count by ip_address, error_message
| sort -count
| head 20
```

Elasticsearch query:

```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"event_type": "authorization_failure"}},
        {"range": {"timestamp": {"gte": "now-24h"}}}
      ]
    }
  },
  "aggs": {
    "by_user": {
      "terms": {"field": "user_id"}
    },
    "by_reason": {
      "terms": {"field": "policy_decision.reasons"}
    }
  }
}
```

### Step 4: Set Up Audit Alerts

Create alert for suspicious activity:

```yaml
# alertmanager/audit-alerts.yml
groups:
  - name: security_audit
    interval: 1m
    rules:
      # Multiple failed auth attempts
      - alert: BruteForceAttempt
        expr: |
          sum(rate(gateway_audit_events_total{
            event_type="authentication_failure"
          }[5m])) by (ip_address) > 10
        for: 5m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "Possible brute force attack from {{ $labels.ip_address }}"
          description: "{{ $value }} failed auth attempts in 5 minutes"

      # Privilege escalation attempt
      - alert: PrivilegeEscalationAttempt
        expr: |
          sum(rate(gateway_audit_events_total{
            event_type="authorization_failure",
            reason=~".*insufficient_permissions.*"
          }[15m])) by (user_id) > 5
        labels:
          severity: warning
          category: security
        annotations:
          summary: "User {{ $labels.user_id }} repeatedly accessing unauthorized resources"
```

## Secret Management

### Option 1: HashiCorp Vault Integration

#### Step 1: Install and Configure Vault

```bash
# Install Vault
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault -n vault --create-namespace

# Initialize Vault
kubectl exec -it vault-0 -n vault -- vault operator init
```

**Expected Output:**
```
Unseal Key 1: abc123...
Unseal Key 2: def456...
Unseal Key 3: ghi789...
Unseal Key 4: jkl012...
Unseal Key 5: mno345...

Initial Root Token: s.xyz789...
```

**⚠️ SECURITY WARNING:** Store unseal keys and root token securely!

#### Step 2: Configure Vault for Gateway

```bash
# Enable KV secrets engine
kubectl exec -it vault-0 -n vault -- vault secrets enable -path=sark kv-v2

# Store gateway secrets
kubectl exec -it vault-0 -n vault -- vault kv put sark/gateway/config \
  jwt_signing_key="$(cat private_key.pem)" \
  database_password="supersecret" \
  admin_api_key="sk_admin_key"

# Create policy for gateway
cat > gateway-policy.hcl <<EOF
path "sark/data/gateway/*" {
  capabilities = ["read"]
}
EOF

kubectl exec -it vault-0 -n vault -- vault policy write gateway-policy gateway-policy.hcl

# Enable Kubernetes auth
kubectl exec -it vault-0 -n vault -- vault auth enable kubernetes

# Configure Kubernetes auth
kubectl exec -it vault-0 -n vault -- vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc:443"

# Create role for gateway
kubectl exec -it vault-0 -n vault -- vault write auth/kubernetes/role/gateway \
  bound_service_account_names=sark-gateway \
  bound_service_account_namespaces=sark-system \
  policies=gateway-policy \
  ttl=24h
```

#### Step 3: Configure Gateway to Use Vault

Create `config/vault-integration.yaml`:

```yaml
secrets:
  provider: vault

  vault:
    address: http://vault.vault.svc.cluster.local:8200

    # Kubernetes auth
    auth:
      type: kubernetes
      role: gateway
      service_account_token_path: /var/run/secrets/kubernetes.io/serviceaccount/token

    # Secret paths
    secrets:
      jwt_signing_key:
        path: sark/data/gateway/config
        key: jwt_signing_key
      database_password:
        path: sark/data/gateway/config
        key: database_password
      admin_api_key:
        path: sark/data/gateway/config
        key: admin_api_key

    # Renewal
    renew_token: true
    renew_increment: 3600

    # TLS
    tls:
      ca_cert_path: /etc/vault/ca.crt
      skip_verify: false
```

### Option 2: Kubernetes Secrets

Create secrets:

```bash
# Create secret from files
kubectl create secret generic gateway-secrets \
  --from-file=jwt-signing-key=private_key.pem \
  --from-literal=database-password=supersecret \
  --from-literal=admin-api-key=sk_admin_key \
  -n sark-system

# Mount in deployment
kubectl patch deployment sark-gateway -n sark-system --patch '
spec:
  template:
    spec:
      volumes:
      - name: secrets
        secret:
          secretName: gateway-secrets
      containers:
      - name: gateway
        volumeMounts:
        - name: secrets
          mountPath: /etc/gateway/secrets
          readOnly: true
        env:
        - name: JWT_SIGNING_KEY_PATH
          value: /etc/gateway/secrets/jwt-signing-key
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: gateway-secrets
              key: database-password
'
```

### Encrypt Secrets at Rest

Enable encryption in Kubernetes:

```yaml
# /etc/kubernetes/enc/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

## Security Checklist for Production

### Pre-Deployment Checklist

```markdown
## Authentication & Authorization
- [ ] JWT validation configured with proper issuer/audience
- [ ] API keys using secure random generation
- [ ] mTLS certificates from trusted CA
- [ ] Strong password policies enforced
- [ ] MFA required for admin access
- [ ] Service accounts use dedicated credentials
- [ ] Credentials never in code/configs (use secrets)

## Network Security
- [ ] TLS 1.2+ enforced (TLS 1.3 preferred)
- [ ] Strong cipher suites configured
- [ ] HTTPS only (HTTP redirects to HTTPS)
- [ ] CORS properly configured
- [ ] Network policies restrict pod communication
- [ ] Firewall rules allow only necessary ports
- [ ] DDoS protection enabled

## Secrets Management
- [ ] Secrets stored in Vault or K8s Secrets
- [ ] Secrets encrypted at rest
- [ ] Regular secret rotation (90 days max)
- [ ] No secrets in logs or error messages
- [ ] Separate secrets per environment
- [ ] Audit trail for secret access

## Rate Limiting & DoS Prevention
- [ ] Global rate limits configured
- [ ] Per-user rate limits configured
- [ ] Per-endpoint rate limits for sensitive operations
- [ ] IP-based rate limiting for unauthenticated endpoints
- [ ] Circuit breakers for upstream services
- [ ] Request size limits enforced

## Audit & Monitoring
- [ ] Comprehensive audit logging enabled
- [ ] Logs sent to centralized SIEM
- [ ] Alerts for security events
- [ ] Failed auth attempts monitored
- [ ] Privilege escalation attempts detected
- [ ] Anomaly detection configured
- [ ] Log retention policy (90 days minimum)

## Policies & Access Control
- [ ] Default deny policy implemented
- [ ] Least privilege access enforced
- [ ] Regular policy reviews scheduled
- [ ] Policy testing in staging environment
- [ ] Policy rollback procedure documented
- [ ] Emergency access procedure defined

## Container & Infrastructure
- [ ] Base images scanned for vulnerabilities
- [ ] Containers run as non-root user
- [ ] Read-only root filesystem where possible
- [ ] Resource limits set on containers
- [ ] Pod security policies/admission controllers
- [ ] Regular security patching

## Data Protection
- [ ] Data encrypted in transit (TLS)
- [ ] Data encrypted at rest
- [ ] PII/sensitive data handling documented
- [ ] Data retention policies defined
- [ ] Backup encryption enabled
- [ ] GDPR/compliance requirements met

## Incident Response
- [ ] Security incident response plan
- [ ] On-call rotation for security incidents
- [ ] Runbooks for common security scenarios
- [ ] Contact list for security team
- [ ] Disaster recovery plan tested
- [ ] Communication plan for breaches
```

## Related Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [How to Write Policies](./how-to-write-policies.md)
- [How to Monitor Gateway](./how-to-monitor-gateway.md)

## Next Steps

1. **Implement audit log analysis** for security monitoring
   - See: [Audit Log Analysis Guide](../tutorials/audit-log-analysis.md)

2. **Set up security scanning** in CI/CD pipeline
   - See: [Security Scanning Guide](../tutorials/security-scanning.md)

3. **Create incident response runbooks**
   - See: [Security Incident Runbook](../runbooks/security-incident.md)

4. **Regular security assessments**
   - See: [Security Assessment Checklist](../reference/security-assessment.md)
