# Security Hardening Guide

**Document Version**: 1.0
**Last Updated**: November 22, 2025
**Audience**: Security Engineers, DevOps Engineers, System Administrators

---

## Table of Contents

1. [Overview](#overview)
2. [Security Headers](#security-headers)
3. [Application Hardening](#application-hardening)
4. [Network Security](#network-security)
5. [Container Security](#container-security)
6. [Kubernetes Security](#kubernetes-security)
7. [Secrets Management](#secrets-management)
8. [Database Security](#database-security)
9. [Redis Security](#redis-security)
10. [Logging and Audit Security](#logging-and-audit-security)
11. [Production Hardening Checklist](#production-hardening-checklist)
12. [Security Testing](#security-testing)

---

## Overview

This guide provides comprehensive security hardening procedures for deploying SARK in production. It covers security headers, infrastructure hardening, and a complete pre-production checklist.

### Security Objectives

1. **Confidentiality**: Protect sensitive data from unauthorized access
2. **Integrity**: Ensure data cannot be tampered with
3. **Availability**: Maintain service availability under attack
4. **Accountability**: Track all actions for audit and forensics
5. **Compliance**: Meet regulatory requirements (SOC 2, PCI-DSS, HIPAA)

---

## Security Headers

HTTP security headers protect against common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).

### Required Security Headers

| Header | Purpose | Value | Protection Against |
|--------|---------|-------|---------------------|
| **Strict-Transport-Security** | Force HTTPS | `max-age=31536000; includeSubDomains; preload` | MITM, Protocol Downgrade |
| **X-Content-Type-Options** | Prevent MIME sniffing | `nosniff` | MIME Confusion |
| **X-Frame-Options** | Prevent clickjacking | `DENY` or `SAMEORIGIN` | Clickjacking |
| **Content-Security-Policy** | Control resource loading | `default-src 'self'` | XSS, Data Injection |
| **X-XSS-Protection** | Enable XSS filter | `1; mode=block` | Reflected XSS |
| **Referrer-Policy** | Control referrer info | `strict-origin-when-cross-origin` | Information Leakage |
| **Permissions-Policy** | Control browser features | `geolocation=(), microphone=()` | Unwanted Feature Access |

### Implementation

#### FastAPI Middleware (Python)

**File**: `src/sark/middleware/security.py`

```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # HSTS: Force HTTPS for 1 year
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # XSS Protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Remove server header (hide implementation details)
        response.headers.pop("Server", None)

        # Add custom security headers
        response.headers["X-API-Version"] = "1.0"
        response.headers["X-Request-ID"] = request.state.request_id if hasattr(request.state, "request_id") else ""

        return response


# Register middleware
app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)
```

#### Nginx Configuration

**File**: `/etc/nginx/conf.d/security-headers.conf`

```nginx
# Security Headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()" always;

# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

# Remove server version
server_tokens off;

# Hide nginx version in errors
more_clear_headers 'Server';
```

#### Kubernetes Ingress Annotations

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sark-ingress
  annotations:
    # Security headers via nginx ingress controller
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains; preload";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
      more_set_headers "Content-Security-Policy: default-src 'self'";
      more_set_headers "Permissions-Policy: geolocation=(), microphone=(), camera=()";

    # TLS configuration
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: sark-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: sark
                port:
                  number: 8000
```

### Testing Security Headers

```bash
# Test with curl
curl -I https://api.example.com/health

# Expected headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Content-Security-Policy: default-src 'self'; ...

# Test with security headers checker
curl https://securityheaders.com/?q=https://api.example.com

# Test with Mozilla Observatory
curl https://observatory.mozilla.org/analyze/api.example.com
```

---

## Application Hardening

### Environment Variables

**Never commit secrets to version control**. Use environment variables or secret management.

```bash
# ✗ BAD: Hardcoded secrets
JWT_SECRET_KEY="super-secret-key-12345"

# ✓ GOOD: Environment variables
JWT_SECRET_KEY="${JWT_SECRET_KEY}"
DATABASE_PASSWORD="${DATABASE_PASSWORD}"
VALKEY_PASSWORD="${VALKEY_PASSWORD}"
```

**.env.example** (commit this):
```bash
# Application
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# JWT Configuration
JWT_SECRET_KEY=<CHANGE_ME_32_CHARS_MIN>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=15

# Database
DATABASE_URL=postgresql://sark:PASSWORD@postgres:5432/sark
DATABASE_POOL_SIZE=20

# Redis
VALKEY_URL=redis://redis:6379/0
VALKEY_PASSWORD=<CHANGE_ME>

# Security
ALLOWED_HOSTS=api.example.com
CORS_ORIGINS=https://app.example.com
RATE_LIMIT_ENABLED=true
```

**.env** (never commit):
```bash
# Actual secrets (generated)
JWT_SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
DATABASE_URL=postgresql://sark:Y9mPx3K7sL2Q@postgres:5432/sark
VALKEY_PASSWORD=R8tGv5Nx2Wp9Ld4K
```

### Generate Strong Secrets

```bash
# Generate random 32-character secret
openssl rand -base64 32

# Generate random 256-bit hex key
openssl rand -hex 32

# Generate UUID
python3 -c "import uuid; print(uuid.uuid4())"
```

### Input Validation

**Use Pydantic for strict validation**:

```python
from pydantic import BaseModel, validator, Field, EmailStr, constr
import re

class UserRegistrationRequest(BaseModel):
    """User registration with strict validation."""

    # Email validation
    email: EmailStr = Field(..., description="User email address")

    # Username: alphanumeric, 3-50 chars
    username: constr(min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_-]+$')

    # Password: min 12 chars, complexity enforced
    password: constr(min_length=12, max_length=128)

    @validator('password')
    def validate_password_complexity(cls, v):
        """Enforce password complexity."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain special character')
        return v

class ServerRegistrationRequest(BaseModel):
    """Server registration with SSRF protection."""

    name: constr(min_length=1, max_length=255, regex=r'^[a-zA-Z0-9_-]+$')
    endpoint: str = Field(..., regex=r'^https?://')

    @validator('endpoint')
    def prevent_ssrf(cls, v):
        """Prevent Server-Side Request Forgery (SSRF)."""
        # Block internal IPs and metadata endpoints
        blocked = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '169.254.169.254',  # AWS metadata
            '::1',               # IPv6 localhost
            'metadata.google.internal',  # GCP metadata
        ]

        v_lower = v.lower()
        if any(blocked_host in v_lower for blocked_host in blocked):
            raise ValueError(f'Blocked endpoint (internal host)')

        return v
```

### SQL Injection Prevention

**Always use parameterized queries**:

```python
from sqlalchemy import text

# ✓ GOOD: Parameterized query
def get_user_by_username(username: str):
    stmt = text("SELECT * FROM users WHERE username = :username")
    result = session.execute(stmt, {"username": username})
    return result.fetchone()

# ✗ BAD: String concatenation (SQL injection vulnerability!)
def get_user_by_username_bad(username: str):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    # Attacker input: "' OR '1'='1" → returns all users!
    result = session.execute(query)
    return result.fetchall()
```

### API Rate Limiting

```python
from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"]
)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply rate limiting per endpoint
@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(request: Request, credentials: LoginRequest):
    # Login logic
    pass

@app.get("/api/v1/servers")
@limiter.limit("100/minute")  # Max 100 requests per minute
async def list_servers(request: Request):
    # List servers logic
    pass
```

---

## Network Security

### TLS/SSL Configuration

#### Nginx TLS Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    # TLS Certificate
    ssl_certificate /etc/nginx/ssl/api.example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/api.example.com.key;

    # TLS Protocol (TLS 1.3 only for maximum security)
    ssl_protocols TLSv1.3;

    # TLS 1.2 + 1.3 (if older clients needed)
    # ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites (TLS 1.3)
    ssl_ciphers 'TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256';
    ssl_prefer_server_ciphers off;

    # Session settings
    ssl_session_cache shared:SSL:50m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Diffie-Hellman parameters
    ssl_dhparam /etc/nginx/ssl/dhparam.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

**Generate DH parameters**:
```bash
openssl dhparam -out /etc/nginx/ssl/dhparam.pem 4096
```

**Test TLS configuration**:
```bash
# Test TLS version and ciphers
nmap --script ssl-enum-ciphers -p 443 api.example.com

# Test with SSL Labs
curl https://www.ssllabs.com/ssltest/analyze.html?d=api.example.com

# Test with testssl.sh
./testssl.sh https://api.example.com
```

### Firewall Rules

#### UFW (Ubuntu Firewall)

```bash
# Enable UFW
sudo ufw enable

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (be careful!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow specific IPs only (more secure)
sudo ufw allow from 203.0.113.0/24 to any port 22 proto tcp

# Check status
sudo ufw status verbose
```

#### iptables Rules

```bash
# Flush existing rules
sudo iptables -F

# Default policies
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow SSH (from specific IP)
sudo iptables -A INPUT -p tcp -s 203.0.113.0/24 --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Rate limiting (prevent DDoS)
sudo iptables -A INPUT -p tcp --dport 443 -m conntrack --ctstate NEW -m limit --limit 100/minute --limit-burst 200 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -m conntrack --ctstate NEW -j DROP

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

---

## Container Security

### Docker Security

#### Dockerfile Best Practices

```dockerfile
# Use specific version (not latest)
FROM python:3.11.6-slim

# Run as non-root user
RUN groupadd -r sark && useradd -r -g sark sark

# Set working directory
WORKDIR /app

# Copy only requirements first (layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=sark:sark . .

# Remove unnecessary files
RUN rm -rf tests/ docs/ .git/

# Use non-root user
USER sark

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "sark.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose Security

```yaml
# Docker Compose file (no version needed for Compose v2+)

services:
  api:
    image: sark:latest
    user: "1000:1000"  # Non-root user
    read_only: true    # Read-only filesystem
    tmpfs:
      - /tmp           # Writable tmp
    cap_drop:
      - ALL            # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE  # Only needed capabilities
    security_opt:
      - no-new-privileges:true
      - apparmor=docker-default
    networks:
      - internal       # Internal network only
    secrets:
      - jwt_secret
      - db_password
    environment:
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret
      DATABASE_PASSWORD_FILE: /run/secrets/db_password

  postgres:
    image: postgres:14-alpine
    user: postgres
    read_only: true
    tmpfs:
      - /var/run/postgresql
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
    security_opt:
      - no-new-privileges:true
    networks:
      - internal

networks:
  internal:
    driver: bridge
    internal: true  # No external access

secrets:
  jwt_secret:
    external: true
  db_password:
    external: true
```

#### Docker Security Scanning

```bash
# Scan image for vulnerabilities
docker scan sark:latest

# Scan with Trivy
trivy image sark:latest

# Scan with Grype
grype sark:latest

# Benchmark with Docker Bench Security
docker run --rm --net host --pid host --cap-add audit_control \
  -v /var/lib:/var/lib \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /etc:/etc:ro \
  docker/docker-bench-security
```

---

## Kubernetes Security

### Pod Security

**Pod Security Standards** (PSS):

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Secure Pod Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark
  namespace: production
spec:
  replicas: 4
  selector:
    matchLabels:
      app: sark
  template:
    metadata:
      labels:
        app: sark
    spec:
      # Service account
      serviceAccountName: sark

      # Security context (pod level)
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
        imagePullPolicy: Always

        # Security context (container level)
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
              - ALL
            add:
              - NET_BIND_SERVICE

        # Resource limits
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

        # Read-only root filesystem
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache

        # Environment from secrets
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: jwt-secret
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: database-password

      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
```

### Network Policies

**Restrict network access between pods**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sark-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: sark
  policyTypes:
  - Ingress
  - Egress

  # Ingress: Allow from ingress controller only
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000

  # Egress: Allow to specific services only
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

  # Allow HTTPS for external APIs
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

### RBAC Configuration

**Least privilege service account**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sark
  namespace: production

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: sark-role
  namespace: production
rules:
# Allow reading ConfigMaps
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]

# Allow reading Secrets
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]

# No other permissions needed

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: sark-rolebinding
  namespace: production
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: sark-role
subjects:
- kind: ServiceAccount
  name: sark
  namespace: production
```

---

## Secrets Management

### HashiCorp Vault

**Setup Vault**:

```bash
# Start Vault server (dev mode for testing)
vault server -dev

# Initialize Vault (production)
vault operator init

# Unseal Vault
vault operator unseal <KEY1>
vault operator unseal <KEY2>
vault operator unseal <KEY3>

# Login
vault login <TOKEN>
```

**Store Secrets**:

```bash
# Enable KV v2 secrets engine
vault secrets enable -version=2 kv

# Store secrets
vault kv put secret/sark/production \
  jwt_secret="$(openssl rand -base64 32)" \
  database_password="$(openssl rand -base64 32)" \
  redis_password="$(openssl rand -base64 32)"

# Read secrets
vault kv get secret/sark/production
vault kv get -field=jwt_secret secret/sark/production
```

**Vault Agent (Kubernetes)**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vault-agent-config
data:
  vault-agent-config.hcl: |
    vault {
      address = "https://vault.example.com:8200"
    }

    auto_auth {
      method {
        type = "kubernetes"
        config = {
          role = "sark"
        }
      }

      sink {
        type = "file"
        config = {
          path = "/vault/secrets/token"
        }
      }
    }

    template {
      source      = "/vault/configs/app-config.tmpl"
      destination = "/vault/secrets/app-config"
    }

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark
spec:
  template:
    spec:
      serviceAccountName: sark
      initContainers:
      - name: vault-agent
        image: vault:latest
        args:
          - agent
          - -config=/vault/config/vault-agent-config.hcl
        volumeMounts:
        - name: vault-config
          mountPath: /vault/config
        - name: vault-secrets
          mountPath: /vault/secrets

      containers:
      - name: sark
        image: sark:latest
        volumeMounts:
        - name: vault-secrets
          mountPath: /vault/secrets
        env:
        - name: JWT_SECRET_KEY
          value: "file:///vault/secrets/jwt_secret"

      volumes:
      - name: vault-config
        configMap:
          name: vault-agent-config
      - name: vault-secrets
        emptyDir:
          medium: Memory
```

### Kubernetes Secrets

```bash
# Create secret from literals
kubectl create secret generic sark-secrets \
  --from-literal=jwt-secret="$(openssl rand -base64 32)" \
  --from-literal=database-password="$(openssl rand -base64 32)" \
  --from-literal=redis-password="$(openssl rand -base64 32)" \
  --namespace production

# Create secret from file
kubectl create secret generic sark-tls \
  --from-file=tls.crt=api.example.com.crt \
  --from-file=tls.key=api.example.com.key \
  --namespace production

# Encrypt secrets at rest (enable in Kubernetes)
# In /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <BASE64_ENCODED_SECRET>
      - identity: {}
```

---

## Database Security

### PostgreSQL Security

```bash
# postgresql.conf
ssl = on
ssl_cert_file = '/var/lib/postgresql/server.crt'
ssl_key_file = '/var/lib/postgresql/server.key'
ssl_ca_file = '/var/lib/postgresql/root.crt'
ssl_ciphers = 'HIGH:!aNULL:!MD5'
ssl_prefer_server_ciphers = on

# Enforce SSL connections
hostssl all all 0.0.0.0/0 md5

# pg_hba.conf (authentication)
# Reject non-SSL connections
hostnossl all all 0.0.0.0/0 reject

# Require SSL + password
hostssl all all 0.0.0.0/0 scram-sha-256

# Local connections
local all postgres peer
```

**Create Users with Least Privilege**:

```sql
-- Create read-only user
CREATE ROLE sark_readonly WITH LOGIN PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE sark TO sark_readonly;
GRANT USAGE ON SCHEMA public TO sark_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sark_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sark_readonly;

-- Create application user (read/write)
CREATE ROLE sark WITH LOGIN PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE sark TO sark;
GRANT USAGE, CREATE ON SCHEMA public TO sark;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sark;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sark;

-- Revoke unnecessary privileges
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE postgres FROM PUBLIC;
```

---

## Redis Security

```conf
# redis.conf

# Require password
requirepass your-strong-password-here

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command KEYS ""
rename-command CONFIG "CONFIG-a1b2c3d4"
rename-command SHUTDOWN ""

# Bind to specific interface (not 0.0.0.0)
bind 127.0.0.1

# Protected mode
protected-mode yes

# Max clients
maxclients 10000

# Timeout idle clients (seconds)
timeout 300
```

---

## Logging and Audit Security

### Centralized Logging

**Forward logs to SIEM**:

```python
import logging
from pythonjsonlogger import jsonlogger

# JSON formatter for structured logs
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logHandler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Log security events
logger.info("User authentication successful", extra={
    "user_id": user.id,
    "ip_address": request.client.host,
    "event_type": "authentication",
    "status": "success"
})

logger.warning("Failed login attempt", extra={
    "username": username,
    "ip_address": request.client.host,
    "event_type": "authentication",
    "status": "failure"
})
```

### Audit Logging

**Track all critical actions**:

```python
async def audit_log(
    event_type: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    status: str,
    details: dict = None
):
    """Log audit event."""
    audit_event = {
        "time": datetime.utcnow(),
        "event_type": event_type,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status": status,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "details": details or {}
    }

    # Store in TimescaleDB
    await db.execute(
        """
        INSERT INTO audit_events (time, event_type, user_id, action, resource_type, resource_id, status, ip_address, details)
        VALUES (:time, :event_type, :user_id, :action, :resource_type, :resource_id, :status, :ip_address, :details)
        """,
        audit_event
    )

    # Forward to SIEM
    await forward_to_siem(audit_event)

# Example usage
await audit_log(
    event_type="server_registration",
    user_id=current_user.id,
    action="create",
    resource_type="server",
    resource_id=server.id,
    status="success",
    details={"server_name": server.name}
)
```

---

## Production Hardening Checklist

### Pre-Deployment Checklist

#### Application Security
- [ ] All secrets rotated and stored in Vault/Kubernetes Secrets
- [ ] JWT secret is 32+ characters, randomly generated
- [ ] Database passwords are strong (16+ characters)
- [ ] API keys are randomly generated UUIDs
- [ ] Debug mode disabled (`DEBUG=false`)
- [ ] Error messages don't expose internal details
- [ ] Input validation enabled on all endpoints
- [ ] SQL injection prevention verified (parameterized queries)
- [ ] XSS prevention verified (no raw HTML rendering)
- [ ] CSRF protection enabled
- [ ] Rate limiting configured for all endpoints
- [ ] Password complexity enforced (12+ chars, uppercase, lowercase, digit, special)
- [ ] MFA enabled for admin accounts
- [ ] Session timeout configured (15 min access, 7 day refresh)
- [ ] Concurrent session limits enforced

#### Network Security
- [ ] TLS 1.3 enforced on all endpoints
- [ ] Valid TLS certificate installed (Let's Encrypt or commercial)
- [ ] HSTS header enabled (max-age=31536000)
- [ ] All HTTP redirected to HTTPS
- [ ] Firewall rules configured (UFW/iptables)
- [ ] Only necessary ports exposed (443, maybe 22)
- [ ] Internal services not exposed to internet (database, Redis)
- [ ] Network policies configured (Kubernetes)
- [ ] VPC/private network configured (cloud)

#### Security Headers
- [ ] Strict-Transport-Security enabled
- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: DENY
- [ ] Content-Security-Policy configured
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Referrer-Policy: strict-origin-when-cross-origin
- [ ] Permissions-Policy configured
- [ ] Server header removed/obscured

#### Container Security
- [ ] Running as non-root user
- [ ] Read-only root filesystem
- [ ] Minimal base image (alpine/distroless)
- [ ] No unnecessary packages installed
- [ ] Security scanning passed (no critical vulnerabilities)
- [ ] Capabilities dropped (cap_drop: ALL)
- [ ] AppArmor/SELinux enabled
- [ ] Resource limits configured

#### Kubernetes Security
- [ ] Pod Security Standards enforced (restricted)
- [ ] Network Policies configured
- [ ] RBAC configured (least privilege)
- [ ] Service accounts per application
- [ ] Secrets encrypted at rest
- [ ] Image pull policy: Always
- [ ] Security context configured
- [ ] Resource quotas and limits

#### Database Security
- [ ] PostgreSQL authentication: scram-sha-256
- [ ] SSL/TLS enforced for connections
- [ ] Least privilege users created
- [ ] Admin user password rotated
- [ ] Dangerous SQL commands disabled
- [ ] Connection limits configured
- [ ] Query timeout configured (30s)
- [ ] Automated backups enabled
- [ ] Point-in-time recovery configured

#### Redis Security
- [ ] Password authentication enabled
- [ ] Dangerous commands disabled (FLUSHDB, KEYS, CONFIG)
- [ ] Bind to localhost or internal network only
- [ ] Protected mode enabled
- [ ] Maxmemory and eviction policy configured
- [ ] Connection timeout configured
- [ ] Redis Sentinel configured (HA)

#### Logging & Monitoring
- [ ] Audit logging enabled for all security events
- [ ] Centralized logging configured (SIEM)
- [ ] Log retention policy configured (90 days)
- [ ] Sensitive data not logged (passwords, tokens)
- [ ] Prometheus metrics enabled
- [ ] Grafana dashboards configured
- [ ] Alerts configured (high CPU, memory, errors)
- [ ] On-call rotation configured
- [ ] Incident response playbooks documented

#### Compliance
- [ ] SOC 2 controls implemented (if applicable)
- [ ] PCI-DSS requirements met (if handling payment data)
- [ ] HIPAA requirements met (if handling health data)
- [ ] GDPR requirements met (if EU users)
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Data retention policy documented
- [ ] Data deletion procedures documented

#### Testing
- [ ] Security scanning passed (OWASP ZAP)
- [ ] Dependency scanning passed (Safety, Trivy)
- [ ] Penetration testing completed
- [ ] Load testing completed
- [ ] Disaster recovery tested
- [ ] Backup restore tested
- [ ] Failover tested (database, Redis)

---

## Security Testing

### OWASP ZAP Scan

```bash
# Baseline scan (passive)
docker run -t zaproxy/zap-stable zap-baseline.py \
  -t https://api.example.com \
  -r zap-baseline-report.html

# Full scan (active)
docker run -t zaproxy/zap-stable zap-full-scan.py \
  -t https://api.example.com \
  -r zap-full-report.html
```

### Dependency Scanning

```bash
# Python dependencies
safety check --json
pip-audit

# Container image
trivy image sark:latest --severity HIGH,CRITICAL
grype sark:latest

# Static code analysis
bandit -r src/ -f json -o bandit-report.json
```

### Penetration Testing

**Recommended tools**:
- Burp Suite Professional
- OWASP ZAP
- Metasploit
- Nmap
- Nikto

**Testing areas**:
1. Authentication bypass
2. Authorization bypass
3. SQL injection
4. XSS (reflected, stored, DOM)
5. CSRF
6. SSRF
7. XXE
8. Command injection
9. Directory traversal
10. Session management

---

## Summary

This guide provides comprehensive security hardening for SARK:

- **Security Headers**: All required HTTP security headers configured
- **Application Hardening**: Input validation, secret management, SQL injection prevention
- **Network Security**: TLS 1.3, firewall rules, VPC configuration
- **Container Security**: Non-root users, minimal images, security scanning
- **Kubernetes Security**: Pod security, network policies, RBAC
- **Secrets Management**: HashiCorp Vault, Kubernetes secrets
- **Production Checklist**: Complete pre-deployment security checklist

Following this guide ensures SARK meets industry security standards and compliance requirements.
