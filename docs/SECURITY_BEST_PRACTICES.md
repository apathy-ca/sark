# SARK Security Best Practices

**Comprehensive Security Hardening and Best Practices Guide**

**Version:** 1.0
**Last Updated:** 2025-11-22
**Classification:** Internal Use Only
**Audience:** Security Engineers, DevOps, SRE Teams

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication Security](#authentication-security)
3. [Authorization Security](#authorization-security)
4. [Network Security](#network-security)
5. [Data Encryption](#data-encryption)
6. [Secrets Management](#secrets-management)
7. [API Security](#api-security)
8. [Database Security](#database-security)
9. [Redis Security](#redis-security)
10. [Container Security](#container-security)
11. [Kubernetes Security](#kubernetes-security)
12. [Logging & Audit Security](#logging--audit-security)
13. [Dependency Security](#dependency-security)
14. [Compliance](#compliance)
15. [Security Testing](#security-testing)
16. [Incident Response](#incident-response)
17. [Security Checklist](#security-checklist)

---

## Security Overview

### Security Principles

SARK follows these core security principles:

1. **Defense in Depth:** Multiple layers of security controls
2. **Least Privilege:** Minimum permissions required for operations
3. **Zero Trust:** Never trust, always verify
4. **Secure by Default:** Secure configurations out-of-the-box
5. **Fail Securely:** Failures default to deny
6. **Separation of Duties:** No single person has complete access
7. **Audit Everything:** Comprehensive logging of security events

### Threat Model

**Assets:**
- User authentication credentials (LDAP, OIDC, SAML)
- JWT tokens and API keys
- Server registration data
- Policy decisions and audit logs
- Database credentials and connection strings
- SIEM integration credentials

**Threats:**
- **Authentication bypass:** Weak password policies, stolen credentials
- **Authorization bypass:** Misconfigured OPA policies, privilege escalation
- **Data breach:** Unencrypted data at rest or in transit
- **Denial of Service:** Resource exhaustion, rate limiting bypass
- **Injection attacks:** SQL injection, command injection, XSS
- **Man-in-the-Middle:** Unencrypted communications
- **Supply chain attacks:** Compromised dependencies
- **Insider threats:** Malicious or negligent insiders

### Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Internet                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                ┌────────▼─────────┐
                │   Firewall/WAF   │  ← DDoS protection, rate limiting
                └────────┬─────────┘
                         │
                ┌────────▼─────────┐
                │  TLS Termination │  ← HTTPS/TLS 1.3
                └────────┬─────────┘
                         │
                ┌────────▼─────────┐
                │  API Gateway     │  ← Authentication, authorization
                └────────┬─────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐   ┌─────▼──────┐  ┌────▼────┐
    │ SARK API│   │  Redis     │  │PostgreSQL│
    │(Network │   │(Encrypted  │  │(Encrypted│
    │ Policy) │   │ at rest)   │  │ at rest) │
    └─────────┘   └────────────┘  └──────────┘
         │
    ┌────▼────┐
    │   OPA   │  ← Policy enforcement
    │(Policies│
    │ in Git) │
    └─────────┘
```

---

## Authentication Security

### Password Security

#### Password Policy

**Requirements:**
```yaml
# Minimum requirements for user passwords
password_policy:
  min_length: 12
  require_uppercase: true
  require_lowercase: true
  require_numbers: true
  require_special_chars: true
  password_history: 5  # Prevent reusing last 5 passwords
  max_age_days: 90  # Force password rotation every 90 days
  lockout_threshold: 5  # Lock account after 5 failed attempts
  lockout_duration_minutes: 30
```

#### Password Hashing

**NEVER store plain text passwords!**

**For LDAP/Local Auth:**
```python
# Use Argon2id (recommended) or bcrypt
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,  # Number of iterations
    memory_cost=65536,  # Memory usage (64 MB)
    parallelism=4,  # Number of parallel threads
    hash_len=32,  # Length of hash
    salt_len=16  # Length of salt
)

# Hash password
password_hash = ph.hash(password)

# Verify password
try:
    ph.verify(password_hash, password)
    # Password is correct
except:
    # Password is incorrect
    pass
```

**Alternative (bcrypt):**
```python
import bcrypt

# Hash password
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

# Verify password
if bcrypt.checkpw(password.encode('utf-8'), password_hash):
    # Password is correct
    pass
```

---

### JWT Token Security

#### Token Configuration

```python
# JWT Settings (Environment Variables)
JWT_SECRET_KEY=<256-bit-secret>  # MUST be random and kept secret
JWT_ALGORITHM=HS256  # Or RS256 for asymmetric
JWT_EXPIRATION_MINUTES=60  # Short-lived access tokens
JWT_ISSUER=sark-api
JWT_AUDIENCE=sark-users

# Use RS256 for better security (asymmetric keys)
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=/secrets/jwt-private-key.pem
JWT_PUBLIC_KEY_PATH=/secrets/jwt-public-key.pem
```

#### Generating Secure JWT Secret

```bash
# Generate random 256-bit secret
openssl rand -base64 32

# Generate RSA key pair (for RS256)
openssl genrsa -out jwt-private-key.pem 4096
openssl rsa -in jwt-private-key.pem -pubout -out jwt-public-key.pem

# Store in Kubernetes secret
kubectl create secret generic jwt-keys \
  --from-file=private-key=jwt-private-key.pem \
  --from-file=public-key=jwt-public-key.pem \
  -n production

# Delete local files after storing in secret manager
shred -u jwt-private-key.pem
```

#### Token Claims

**Include minimum necessary claims:**
```json
{
  "sub": "user-id",  // Subject (user ID)
  "iss": "sark-api",  // Issuer
  "aud": "sark-users",  // Audience
  "exp": 1638360000,  // Expiration (Unix timestamp)
  "iat": 1638356400,  // Issued at
  "jti": "unique-token-id",  // JWT ID (prevents replay)
  "roles": ["developer"],  // User roles
  "teams": ["engineering"]  // User teams
}
```

**Security Notes:**
- ✅ DO include: user ID, roles, expiration
- ❌ DON'T include: passwords, sensitive PII, secrets
- ✅ DO validate: signature, expiration, issuer, audience
- ❌ DON'T store in localStorage (XSS vulnerable) → Use httpOnly cookies

#### Token Refresh Security

```python
# Refresh token best practices
REFRESH_TOKEN_EXPIRATION_DAYS=7  # Longer lived but still limited
REFRESH_TOKEN_ROTATION_ENABLED=true  # Rotate on each use
MAX_SESSIONS_PER_USER=5  # Limit concurrent sessions
REFRESH_TOKEN_FAMILY_TRACKING=true  # Detect token reuse

# Store in Redis with metadata
refresh_token_data = {
    "user_id": user_id,
    "token_family_id": uuid.uuid4(),  # Detect stolen tokens
    "created_at": datetime.now(),
    "last_used_at": datetime.now(),
    "ip_address": request.remote_addr,
    "user_agent": request.headers.get('User-Agent'),
    "device_id": request.headers.get('X-Device-ID')
}
```

---

### Multi-Factor Authentication (MFA)

#### MFA Implementation

**Supported MFA Methods:**
1. **TOTP (Time-based One-Time Password):** Google Authenticator, Authy
2. **SMS:** Text message codes (less secure, use as fallback)
3. **Hardware Tokens:** YubiKey, FIDO2
4. **Push Notifications:** Duo, Okta Verify

**TOTP Implementation:**
```python
import pyotp

# Generate secret for user
secret = pyotp.random_base32()
# Store secret in database (encrypted!)

# Generate QR code for user to scan
totp = pyotp.TOTP(secret)
qr_uri = totp.provisioning_uri(
    name=user_email,
    issuer_name="SARK"
)
# Display QR code to user

# Verify TOTP code
totp = pyotp.TOTP(secret)
if totp.verify(user_code, valid_window=1):  # Allow 30s window
    # MFA successful
    pass
```

#### MFA Enforcement

```python
# Require MFA for critical operations
@require_mfa
def delete_server(server_id: str):
    # Verify MFA was completed within last 5 minutes
    if not mfa_verified_recently(user_id, max_age_seconds=300):
        raise MFARequiredException("Re-authenticate with MFA")

    # Proceed with deletion
    pass
```

**OPA Policy for MFA:**
```rego
# Require MFA for critical operations
deny[msg] {
    input.action == "server:delete"
    not input.context.mfa_verified
    msg := "Multi-factor authentication required for server deletion"
}

deny[msg] {
    input.action == "server:delete"
    input.context.mfa_verified
    time.now_ns() - input.context.mfa_timestamp_ns > 300000000000  # 5 minutes
    msg := "MFA verification expired, please re-authenticate"
}
```

---

### Session Security

#### Secure Session Configuration

```python
# Session Settings
SESSION_COOKIE_SECURE=true  # Only send over HTTPS
SESSION_COOKIE_HTTPONLY=true  # Prevent JavaScript access (XSS protection)
SESSION_COOKIE_SAMESITE=Strict  # CSRF protection
SESSION_COOKIE_MAX_AGE=3600  # 1 hour
SESSION_IDLE_TIMEOUT=1800  # 30 minutes inactivity

# Cookie configuration
from fastapi import Response

response.set_cookie(
    key="session_id",
    value=session_token,
    max_age=3600,
    secure=True,  # HTTPS only
    httponly=True,  # No JavaScript access
    samesite="strict",  # CSRF protection
    domain=".sark.example.com",
    path="/"
)
```

#### Session Fixation Prevention

```python
# Regenerate session ID after authentication
def login(username, password):
    # Authenticate user
    user = authenticate(username, password)

    # Invalidate old session
    if 'session_id' in request.cookies:
        delete_session(request.cookies['session_id'])

    # Generate NEW session ID
    new_session_id = secrets.token_urlsafe(32)

    # Create session
    create_session(new_session_id, user.id)

    # Set cookie with new session ID
    response.set_cookie(key="session_id", value=new_session_id)
```

---

## Authorization Security

### OPA Policy Security

#### Secure Policy Development

**Policy Security Checklist:**
- ✅ Default deny (fail closed)
- ✅ Explicit allow rules only
- ✅ Input validation
- ✅ No hardcoded credentials
- ✅ Versioned in Git
- ✅ Code review required
- ✅ Automated testing

**Example Secure Policy:**
```rego
package mcp

import future.keywords.if

# Default deny (fail closed)
default allow := false

# Validate input structure
allow if {
    # Ensure required fields exist
    input.user.id
    input.user.roles
    input.action
    input.tool

    # Check authorization
    user_can_access_tool
}

# Helper rule
user_can_access_tool if {
    # Get user's roles
    user_roles := input.user.roles

    # Get tool's required roles
    tool_required_roles := data.tools[input.tool.name].required_roles

    # Check if user has at least one required role
    some role in user_roles
    role in tool_required_roles
}

# Prevent privilege escalation
deny[msg] if {
    input.action == "role:assign"
    input.target_role == "admin"
    not "admin" in input.user.roles
    msg := "Only admins can assign admin role"
}

# Audit all denials
deny[msg] if {
    not allow
    # Log to audit system
    trace(sprintf("Access denied: %v", [input]))
    msg := "Access denied by policy"
}
```

#### Policy Testing

```rego
# Test policies thoroughly
package mcp_test

import data.mcp

test_developer_can_access_low_sensitivity if {
    input := {
        "user": {"id": "user-1", "roles": ["developer"]},
        "action": "tool:invoke",
        "tool": {"name": "test_tool", "sensitivity_level": "low"}
    }
    mcp.allow with data.tools as {
        "test_tool": {"required_roles": ["developer"], "sensitivity": "low"}
    }
}

test_developer_cannot_access_critical if {
    input := {
        "user": {"id": "user-1", "roles": ["developer"]},
        "action": "tool:invoke",
        "tool": {"name": "admin_tool", "sensitivity_level": "critical"}
    }
    not mcp.allow with data.tools as {
        "admin_tool": {"required_roles": ["admin"], "sensitivity": "critical"}
    }
}
```

#### Policy Versioning

```bash
# Version control for policies
git/
└── opa/
    └── policies/
        ├── main.rego
        ├── rbac.rego
        ├── sensitivity.rego
        └── tests/
            ├── main_test.rego
            └── rbac_test.rego

# Deploy policies via GitOps
# 1. Commit policy changes
git add opa/policies/
git commit -m "Add IP-based access control policy"
git push

# 2. CI/CD pipeline tests policies
opa test opa/policies/

# 3. Deploy to OPA bundle server
opa build -b opa/policies/ -o bundle.tar.gz
curl -X PUT --data-binary @bundle.tar.gz \
  https://bundle-server.example.com/bundles/sark/v1.2.3
```

---

### Role-Based Access Control (RBAC)

#### Role Hierarchy

```yaml
roles:
  # Base role - read-only
  viewer:
    permissions:
      - server:read
      - policy:read

  # Developer role
  developer:
    inherits: [viewer]
    permissions:
      - server:write
      - tool:invoke:low
      - tool:invoke:medium

  # Admin role
  admin:
    inherits: [developer]
    permissions:
      - server:delete
      - tool:invoke:high
      - tool:invoke:critical
      - user:manage
      - policy:write

  # Security admin (separate from admin)
  security_admin:
    inherits: [viewer]
    permissions:
      - audit:read
      - audit:export
      - policy:write
      - security:configure
```

#### Permission Assignment

```python
# Assign roles to users
def assign_role(user_id: str, role: str, assigned_by: str):
    # Validate assigner has permission
    if not has_permission(assigned_by, "user:manage"):
        raise PermissionDenied("Only admins can assign roles")

    # Prevent privilege escalation
    if role == "admin" and not has_role(assigned_by, "admin"):
        raise PermissionDenied("Only admins can assign admin role")

    # Audit the assignment
    log_audit_event(
        event_type="role_assignment",
        user_id=user_id,
        role=role,
        assigned_by=assigned_by,
        timestamp=datetime.now()
    )

    # Assign role
    db.execute(
        "INSERT INTO user_roles (user_id, role, assigned_by, assigned_at) VALUES (?, ?, ?, ?)",
        (user_id, role, assigned_by, datetime.now())
    )
```

---

## Network Security

### TLS/HTTPS Configuration

#### TLS 1.3 Configuration

**NGINX Configuration:**
```nginx
# /etc/nginx/conf.d/sark.conf
server {
    listen 443 ssl http2;
    server_name sark.example.com;

    # TLS 1.3 only (disable TLS 1.0, 1.1, 1.2)
    ssl_protocols TLSv1.3;

    # Strong cipher suites (TLS 1.3)
    ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256';
    ssl_prefer_server_ciphers off;

    # Certificates
    ssl_certificate /etc/letsencrypt/live/sark.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sark.example.com/privkey.pem;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/sark.example.com/chain.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'" always;

    # Proxy to SARK
    location / {
        proxy_pass http://sark-backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name sark.example.com;
    return 301 https://$server_name$request_uri;
}
```

#### Certificate Management

```bash
# Use Let's Encrypt for free TLS certificates
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d sark.example.com -d api.sark.example.com

# Auto-renewal (add to cron)
0 0 1 * * certbot renew --quiet

# Kubernetes cert-manager (automatic renewal)
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: sark-tls
spec:
  secretName: sark-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - sark.example.com
  - api.sark.example.com
```

---

### Firewall Rules

#### Network Policies (Kubernetes)

```yaml
# Only allow ingress from ingress controller
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sark-api-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: sark
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
  # Allow PostgreSQL
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  # Allow Redis
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  # Allow OPA
  - to:
    - podSelector:
        matchLabels:
          app: opa
    ports:
    - protocol: TCP
      port: 8181
  # Allow HTTPS egress (for SIEM, OIDC, etc.)
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

#### IP Whitelisting

```nginx
# NGINX - IP whitelist for admin endpoints
location /api/admin {
    # Allow corporate network
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;

    # Allow VPN
    allow 192.168.100.0/24;

    # Deny all others
    deny all;

    proxy_pass http://sark-backend;
}
```

---

### Rate Limiting (DDoS Protection)

#### NGINX Rate Limiting

```nginx
# Define rate limit zones
http {
    # Limit by IP address
    limit_req_zone $binary_remote_addr zone=by_ip:10m rate=10r/s;

    # Limit by API key
    limit_req_zone $http_x_api_key zone=by_api_key:10m rate=100r/s;

    server {
        # Apply rate limit
        location /api {
            limit_req zone=by_ip burst=20 nodelay;
            proxy_pass http://sark-backend;
        }

        # Stricter limit for auth endpoints
        location /api/auth {
            limit_req zone=by_ip burst=5 nodelay;
            proxy_pass http://sark-backend;
        }
    }
}
```

---

## Data Encryption

### Encryption at Rest

#### Database Encryption

**PostgreSQL TDE (Transparent Data Encryption):**
```bash
# Enable pgcrypto extension
psql -U sark -d sark -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# Encrypt sensitive columns
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255),
    password_hash BYTEA,  # Already hashed
    mfa_secret BYTEA NOT NULL,  # Encrypted!
    created_at TIMESTAMP
);

# Insert encrypted data
INSERT INTO users (id, email, mfa_secret)
VALUES (
    gen_random_uuid(),
    'user@example.com',
    pgp_sym_encrypt('mfa-secret-value', 'encryption-key')
);

# Query encrypted data
SELECT
    id,
    email,
    pgp_sym_decrypt(mfa_secret, 'encryption-key') AS mfa_secret
FROM users
WHERE id = 'user-id';
```

**Full Disk Encryption (Production):**
```bash
# Linux (LUKS)
cryptsetup luksFormat /dev/sdb
cryptsetup luksOpen /dev/sdb encrypted_disk
mkfs.ext4 /dev/mapper/encrypted_disk
mount /dev/mapper/encrypted_disk /mnt/encrypted

# AWS EBS Encryption
aws ec2 create-volume \
  --size 100 \
  --encrypted \
  --kms-key-id arn:aws:kms:region:account:key/key-id

# GCP Persistent Disk Encryption
gcloud compute disks create encrypted-disk \
  --size 100GB \
  --kms-key projects/PROJECT/locations/LOCATION/keyRings/RING/cryptoKeys/KEY
```

---

### Encryption in Transit

#### Internal Service Communication

**PostgreSQL SSL:**
```bash
# Generate SSL certificates
openssl req -new -x509 -days 365 -nodes -text \
  -out server.crt \
  -keyout server.key \
  -subj "/CN=postgres.sark.local"

# Configure PostgreSQL
# postgresql.conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_ca_file = 'root.crt'

# pg_hba.conf - require SSL
hostssl all all 0.0.0.0/0 md5

# Connection string
DATABASE_URL=postgresql://user:pass@postgres:5432/sark?sslmode=require
```

**Redis TLS:**
```bash
# Generate certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout redis.key -out redis.crt

# Configure Redis
# redis.conf
port 0  # Disable non-TLS port
tls-port 6379
tls-cert-file /etc/redis/redis.crt
tls-key-file /etc/redis/redis.key
tls-ca-cert-file /etc/redis/ca.crt
tls-auth-clients yes  # Require client certificates

# Connection string
VALKEY_DSN=rediss://:password@redis:6379/0?ssl_cert_reqs=required
```

---

## Secrets Management

### HashiCorp Vault

#### Vault Setup

```bash
# Install Vault
wget https://releases.hashicorp.com/vault/1.14.0/vault_1.14.0_linux_amd64.zip
unzip vault_1.14.0_linux_amd64.zip
sudo mv vault /usr/local/bin/

# Initialize Vault
vault operator init

# Unseal Vault (requires 3 of 5 keys)
vault operator unseal <key-1>
vault operator unseal <key-2>
vault operator unseal <key-3>

# Enable secrets engine
vault secrets enable -path=sark kv-v2

# Store secrets
vault kv put sark/database \
  username=sark \
  password=super-secret-password

vault kv put sark/jwt \
  secret_key=256-bit-random-key

vault kv put sark/redis \
  password=redis-password
```

#### Vault Integration

```python
# Read secrets from Vault
import hvac

client = hvac.Client(url='https://vault.example.com:8200')
client.auth.approle.login(
    role_id='role-id',
    secret_id='secret-id'
)

# Read database credentials
db_secret = client.secrets.kv.v2.read_secret_version(path='sark/database')
DB_USERNAME = db_secret['data']['data']['username']
DB_PASSWORD = db_secret['data']['data']['password']

# Read JWT secret
jwt_secret = client.secrets.kv.v2.read_secret_version(path='sark/jwt')
JWT_SECRET_KEY = jwt_secret['data']['data']['secret_key']
```

#### Kubernetes Vault Integration

```yaml
# Using Vault Agent Sidecar
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "sark"
        vault.hashicorp.com/agent-inject-secret-database: "sark/database"
        vault.hashicorp.com/agent-inject-template-database: |
          {{- with secret "sark/database" -}}
          export DB_USERNAME="{{ .Data.data.username }}"
          export DB_PASSWORD="{{ .Data.data.password }}"
          {{- end }}
    spec:
      containers:
      - name: sark
        image: sark:latest
        command: ["/bin/sh", "-c"]
        args:
          - source /vault/secrets/database && /app/start.sh
```

---

### Kubernetes Secrets

#### Creating Secrets

```bash
# Create secret from literal
kubectl create secret generic sark-secrets \
  --from-literal=database-password='super-secret' \
  --from-literal=redis-password='redis-secret' \
  --from-literal=jwt-secret='jwt-secret-key' \
  -n production

# Create secret from file
kubectl create secret generic tls-cert \
  --from-file=tls.crt=./server.crt \
  --from-file=tls.key=./server.key \
  -n production

# Create TLS secret
kubectl create secret tls sark-tls \
  --cert=./server.crt \
  --key=./server.key \
  -n production
```

#### Using Secrets

```yaml
# Mount secrets as environment variables
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark
spec:
  template:
    spec:
      containers:
      - name: sark
        image: sark:latest
        env:
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: database-password
        - name: VALKEY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: redis-password

# Mount secrets as files
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark
spec:
  template:
    spec:
      containers:
      - name: sark
        image: sark:latest
        volumeMounts:
        - name: jwt-keys
          mountPath: /secrets
          readOnly: true
      volumes:
      - name: jwt-keys
        secret:
          secretName: jwt-keys
          items:
          - key: private-key
            path: jwt-private-key.pem
            mode: 0400  # Read-only for owner
          - key: public-key
            path: jwt-public-key.pem
            mode: 0444
```

#### Encrypt Secrets at Rest (Kubernetes)

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <BASE64_ENCODED_32_BYTE_KEY>
    - identity: {}  # Fallback to unencrypted

# Enable in API server
kube-apiserver \
  --encryption-provider-config=/etc/kubernetes/encryption-config.yaml
```

---

## API Security

### Input Validation

**Prevent Injection Attacks:**

```python
from pydantic import BaseModel, validator, Field
from typing import Optional
import re

class ServerRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    transport: str
    endpoint: str
    sensitivity_level: str

    @validator('name')
    def validate_name(cls, v):
        # Alphanumeric, hyphens, underscores only
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Name must be alphanumeric with hyphens/underscores only')
        return v

    @validator('transport')
    def validate_transport(cls, v):
        # Enum validation
        if v not in ['http', 'stdio', 'sse']:
            raise ValueError('Invalid transport type')
        return v

    @validator('endpoint')
    def validate_endpoint(cls, v):
        # URL validation
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Endpoint must be HTTP/HTTPS URL')
        # Prevent SSRF
        if any(blocked in v.lower() for blocked in ['localhost', '127.0.0.1', '169.254.169.254']):
            raise ValueError('Invalid endpoint (blocked domain)')
        return v

    @validator('sensitivity_level')
    def validate_sensitivity(cls, v):
        if v not in ['low', 'medium', 'high', 'critical']:
            raise ValueError('Invalid sensitivity level')
        return v
```

### SQL Injection Prevention

**ALWAYS use parameterized queries:**

```python
# ✅ GOOD - Parameterized query
user_id = request.get('user_id')
query = "SELECT * FROM users WHERE id = ?"
result = db.execute(query, (user_id,))

# ✅ GOOD - ORM (SQLAlchemy)
user = db.session.query(User).filter(User.id == user_id).first()

# ❌ BAD - String concatenation (SQL injection vulnerable!)
query = f"SELECT * FROM users WHERE id = '{user_id}'"
result = db.execute(query)  # NEVER DO THIS!
```

### Command Injection Prevention

```python
# ❌ BAD - Shell injection vulnerable
import subprocess
server_name = request.get('server_name')
subprocess.call(f"ping -c 1 {server_name}", shell=True)  # NEVER DO THIS!

# ✅ GOOD - Use parameterized subprocess
subprocess.call(['ping', '-c', '1', server_name], shell=False)

# ✅ BETTER - Validate input first
if not re.match(r'^[a-zA-Z0-9.-]+$', server_name):
    raise ValueError('Invalid server name')
subprocess.call(['ping', '-c', '1', server_name], shell=False)
```

### Cross-Site Scripting (XSS) Prevention

```python
# For HTML responses, escape user input
from markupsafe import escape

user_input = request.get('comment')
safe_output = escape(user_input)

# For JSON APIs, set proper Content-Type
@app.get("/api/data")
def get_data():
    return JSONResponse(
        content={"data": user_data},
        headers={"Content-Type": "application/json"}  # Not text/html!
    )
```

### CSRF Protection

```python
# Use CSRF tokens for state-changing operations
from fastapi_csrf_protect import CsrfProtect

@app.post("/api/servers")
async def create_server(csrf_protect: CsrfProtect = Depends()):
    # Validate CSRF token
    await csrf_protect.validate_csrf(request)

    # Proceed with server creation
    pass
```

---

## Database Security

### Least Privilege Access

```sql
-- Create read-only user for reporting
CREATE USER sark_readonly WITH PASSWORD 'readonly-password';
GRANT CONNECT ON DATABASE sark TO sark_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sark_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO sark_readonly;

-- Create application user (limited permissions)
CREATE USER sark_app WITH PASSWORD 'app-password';
GRANT CONNECT ON DATABASE sark TO sark_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sark_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO sark_app;

-- Revoke dangerous permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON pg_user FROM PUBLIC;
```

### Database Auditing

```sql
-- Enable audit logging
ALTER DATABASE sark SET log_statement = 'all';
ALTER DATABASE sark SET log_duration = on;
ALTER DATABASE sark SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Track connection attempts
CREATE TABLE connection_log (
    timestamp TIMESTAMP DEFAULT NOW(),
    username VARCHAR(255),
    database VARCHAR(255),
    remote_host INET,
    success BOOLEAN
);
```

---

## Redis Security

### Redis Configuration

```conf
# redis.conf

# Bind to specific IP (not 0.0.0.0!)
bind 127.0.0.1 ::1

# Require password
requirepass super-secret-redis-password

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_abc123"  # Rename, don't disable (for monitoring)
rename-command SHUTDOWN ""
rename-command DEBUG ""

# Enable protected mode
protected-mode yes

# Limit memory
maxmemory 4gb
maxmemory-policy allkeys-lru

# Enable persistence (if needed)
appendonly yes
appendfsync everysec

# Disable remote access (if only local)
port 0  # Disable TCP port
unixsocket /var/run/redis/redis.sock
unixsocketperm 700
```

---

## Container Security

### Docker Security

**Dockerfile Security:**
```dockerfile
# Use specific version (not latest)
FROM python:3.11.5-slim-bullseye

# Create non-root user
RUN groupadd -r sark && useradd -r -g sark sark

# Install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY --chown=sark:sark requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=sark:sark src/ /app/src/

# Switch to non-root user
USER sark

# Run application
CMD ["uvicorn", "sark.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Image Scanning:**
```bash
# Scan with Trivy
trivy image sark:latest

# Scan with Snyk
snyk container test sark:latest

# Scan with Anchore
anchore-cli image add sark:latest
anchore-cli image wait sark:latest
anchore-cli image vuln sark:latest all
```

---

## Kubernetes Security

### Pod Security

```yaml
# Pod Security Standards
apiVersion: v1
kind: Pod
metadata:
  name: sark
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault

  containers:
  - name: sark
    image: sark:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
      runAsNonRoot: true
      runAsUser: 1000

    # Resource limits (prevent DoS)
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "2000m"

    # Read-only root filesystem
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /app/.cache

  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
```

### RBAC

```yaml
# Service Account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sark
  namespace: production

---
# Role (namespace-scoped)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: sark-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["sark-secrets"]  # Specific secret only
  verbs: ["get"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]

---
# RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: sark-rolebinding
  namespace: production
subjects:
- kind: ServiceAccount
  name: sark
  namespace: production
roleRef:
  kind: Role
  name: sark-role
  apiGroup: rbac.authorization.k8s.io
```

---

## Logging & Audit Security

### Secure Logging

**What to Log:**
- ✅ Authentication attempts (success and failure)
- ✅ Authorization decisions
- ✅ Admin actions
- ✅ Data access (sensitive data)
- ✅ Configuration changes
- ✅ Security events (failed logins, MFA failures)
- ❌ Passwords, API keys, tokens
- ❌ Full credit card numbers, SSNs

**Log Sanitization:**
```python
import re

def sanitize_log(message: str) -> str:
    # Redact credit card numbers
    message = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[REDACTED CC]', message)

    # Redact SSNs
    message = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', message)

    # Redact API keys
    message = re.sub(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^\s"\']+)', r'\1[REDACTED]', message, flags=re.IGNORECASE)

    # Redact JWTs
    message = re.sub(r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[REDACTED JWT]', message)

    return message

# Use in logging
import logging
logger = logging.getLogger(__name__)

message = f"User logged in with API key: {api_key}"
logger.info(sanitize_log(message))
# Output: "User logged in with API key: [REDACTED]"
```

### Audit Log Retention

```yaml
# Retention policy
audit_retention:
  # Hot storage (fast access)
  hot:
    duration: 90_days
    storage: postgresql
    compression: none

  # Warm storage (archival)
  warm:
    duration: 1_year
    storage: s3
    compression: gzip

  # Cold storage (compliance)
  cold:
    duration: 7_years
    storage: glacier
    compression: gzip
    encryption: aws_kms
```

---

## Dependency Security

### Dependency Scanning

```bash
# Python - Safety
pip install safety
safety check

# Python - Bandit (security linter)
pip install bandit
bandit -r src/

# Python - pip-audit
pip install pip-audit
pip-audit

# Container - Trivy
trivy image sark:latest

# SBOM (Software Bill of Materials)
syft sark:latest -o json > sbom.json
grype sbom:sbom.json
```

### Dependency Updates

```yaml
# Dependabot configuration
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "security"

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## Compliance

### SOC 2 Type II

**Required Controls:**
- ✅ Access controls (authentication, authorization)
- ✅ Encryption (at rest, in transit)
- ✅ Audit logging
- ✅ Vulnerability management
- ✅ Incident response plan
- ✅ Business continuity
- ✅ Change management

### PCI-DSS

**Key Requirements:**
- ✅ No storage of full credit card numbers
- ✅ Encrypt transmission of cardholder data
- ✅ Maintain vulnerability management program
- ✅ Implement strong access control
- ✅ Regularly monitor and test networks
- ✅ Maintain information security policy

### HIPAA

**PHI Protection:**
- ✅ Access controls
- ✅ Audit controls
- ✅ Integrity controls
- ✅ Transmission security

**HIPAA Logging:**
```python
# Log all PHI access
def access_phi(user_id: str, patient_id: str, purpose: str):
    log_audit_event(
        event_type="phi_access",
        user_id=user_id,
        patient_id=patient_id,  # Hash or pseudonym
        purpose=purpose,
        timestamp=datetime.now(),
        ip_address=request.remote_addr
    )

    # Proceed with access
    pass
```

---

## Security Testing

### OWASP ZAP

```bash
# Install ZAP
docker pull owasp/zap2docker-stable

# Baseline scan
docker run -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable \
  zap-baseline.py -t https://sark.example.com -r zap-report.html

# Full scan
docker run -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable \
  zap-full-scan.py -t https://sark.example.com -r zap-full-report.html
```

### Penetration Testing

**Annual Penetration Test Scope:**
1. External network penetration test
2. Web application penetration test
3. API security assessment
4. Social engineering test
5. Physical security assessment

---

## Incident Response

See [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md) for complete incident response procedures.

---

## Security Checklist

### Pre-Production Security Checklist

**Authentication:**
- [ ] Strong password policy enforced (12+ chars, complexity)
- [ ] MFA enabled for all users
- [ ] JWT secret is random 256-bit key
- [ ] JWT tokens expire (60 min for access, 7 days for refresh)
- [ ] Session timeout configured (30 min idle timeout)
- [ ] Account lockout after failed attempts (5 attempts, 30 min lockout)

**Authorization:**
- [ ] OPA policies reviewed and tested
- [ ] Default deny policy in place
- [ ] Least privilege access enforced
- [ ] Admin actions require MFA

**Network:**
- [ ] TLS 1.3 enforced
- [ ] HSTS header enabled
- [ ] Strong cipher suites only
- [ ] Certificate auto-renewal configured
- [ ] Network policies configured (Kubernetes)
- [ ] Firewall rules configured
- [ ] Rate limiting enabled (DDoS protection)

**Data:**
- [ ] Database encrypted at rest
- [ ] Redis encrypted at rest (if persistence enabled)
- [ ] Sensitive columns encrypted in database
- [ ] Full disk encryption enabled
- [ ] Backups encrypted

**Secrets:**
- [ ] Secrets stored in Vault or K8s secrets
- [ ] No secrets in code or environment variables
- [ ] Secrets rotated regularly (90 days)
- [ ] Access to secrets audited

**API:**
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (escape output)
- [ ] CSRF protection enabled
- [ ] CORS configured properly

**Database:**
- [ ] Least privilege database users
- [ ] SSL/TLS connections enforced
- [ ] Audit logging enabled
- [ ] Regular backups configured (automated)

**Containers:**
- [ ] Images scanned for vulnerabilities
- [ ] Non-root user in containers
- [ ] Read-only root filesystem
- [ ] Resource limits configured
- [ ] Security contexts configured (Kubernetes)

**Logging:**
- [ ] Audit logging enabled for all security events
- [ ] Logs sent to SIEM
- [ ] Log retention policy configured (7 years)
- [ ] Sensitive data redacted from logs

**Dependencies:**
- [ ] All dependencies up to date
- [ ] Vulnerability scanning automated (Dependabot)
- [ ] SBOM generated and reviewed

**Compliance:**
- [ ] SOC 2 controls implemented
- [ ] PCI-DSS requirements met (if applicable)
- [ ] HIPAA controls implemented (if applicable)

**Testing:**
- [ ] Security scanning automated (OWASP ZAP)
- [ ] Annual penetration test scheduled
- [ ] Vulnerability management process in place

**Incident Response:**
- [ ] Incident response plan documented
- [ ] On-call rotation configured
- [ ] Runbooks created for common incidents
- [ ] Post-mortem process defined

---

**This document is reviewed quarterly and updated as needed. Last review: 2025-11-22**

**For security incidents, contact the Security Team immediately.**

**Security hotline:** security@example.com | PagerDuty: security-team
