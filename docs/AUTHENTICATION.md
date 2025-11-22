# SARK Authentication Guide

Comprehensive guide to authentication, authorization, and access control in SARK.

## Table of Contents

- [Overview](#overview)
- [Authentication Architecture](#authentication-architecture)
- [Supported Providers](#supported-providers)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Session Management](#session-management)
- [Rate Limiting](#rate-limiting)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

SARK provides a flexible, multi-provider authentication system supporting:

- **OIDC/OAuth 2.0**: Google, Azure AD, Okta, custom providers
- **SAML 2.0**: Enterprise SSO integration
- **LDAP/Active Directory**: Corporate directory authentication
- **API Keys**: Programmatic access with granular permissions

### Key Features

✅ **Multi-Provider Support**: Use multiple authentication methods simultaneously
✅ **Session Management**: Redis-backed sessions with concurrent device limits
✅ **Rate Limiting**: Protect against abuse with configurable limits
✅ **Provider Failover**: Automatic fallback between providers
✅ **Audit Logging**: Complete audit trail of authentication events
✅ **Role-Based Access**: Fine-grained permissions and role management

## Authentication Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Application                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├─ OIDC/OAuth 2.0 ──────────────┐
                  ├─ SAML 2.0 ────────────────────┤
                  ├─ LDAP/AD ─────────────────────┤
                  ├─ API Keys ────────────────────┤
                  │                                │
                  ▼                                ▼
         ┌────────────────┐            ┌─────────────────┐
         │ Rate Limiting  │            │ Auth Providers  │
         │  Middleware    │            │   (OIDC, SAML,  │
         └───────┬────────┘            │   LDAP, etc.)   │
                 │                      └────────┬────────┘
                 │                               │
                 ▼                               ▼
         ┌────────────────┐            ┌─────────────────┐
         │ Unified Auth   │◄───────────│ Session Service │
         │    Router      │            │   (Redis)       │
         └───────┬────────┘            └─────────────────┘
                 │
                 ├─ Session Created
                 ├─ User Context Established
                 └─ Access Granted
                 │
                 ▼
         ┌────────────────┐
         │ Protected API  │
         │   Endpoints    │
         └────────────────┘
```

### Authentication Flow

1. **Client Request**: User initiates authentication
2. **Provider Selection**: System determines auth method (API key > JWT > IP)
3. **Authentication**: Provider validates credentials
4. **Session Creation**: Redis session created with metadata
5. **Rate Limit Check**: Request counted against limit
6. **Access Granted**: User context established, request proceeds

## Supported Providers

### OIDC/OAuth 2.0

Enterprise-grade OAuth 2.0 and OpenID Connect support.

**Supported Providers**:
- Google Workspace
- Microsoft Azure AD / Entra ID
- Okta
- Custom OIDC providers

📖 **[OIDC Setup Guide](./OIDC_SETUP.md)**

### SAML 2.0

Enterprise SSO integration via SAML 2.0.

**Features**:
- SP-initiated and IdP-initiated flows
- Encrypted assertions
- Single Logout (SLO)

📖 **[SAML Setup Guide](./SAML_SETUP.md)**

### LDAP/Active Directory

Corporate directory authentication.

**Features**:
- Connection pooling
- Group membership resolution
- Active Directory support
- SSL/TLS encryption

📖 **[LDAP Setup Guide](./LDAP_SETUP.md)**

### API Keys

Programmatic access for service accounts and integrations.

**Features**:
- Scoped permissions
- Usage tracking
- Per-key rate limits
- Rotation support

📖 **[API Keys Guide](./API_KEYS.md)**

## Quick Start

### 1. Choose Authentication Method

```bash
# Enable OIDC (Google)
export OIDC_ENABLED=true
export OIDC_PROVIDER=google
export OIDC_CLIENT_ID=your-client-id
export OIDC_CLIENT_SECRET=your-client-secret

# Or enable LDAP
export LDAP_ENABLED=true
export LDAP_SERVER=ldap://ldap.example.com:389
export LDAP_BIND_DN=cn=admin,dc=example,dc=com
export LDAP_BIND_PASSWORD=your-password
export LDAP_USER_BASE_DN=ou=users,dc=example,dc=com
```

### 2. Configure Redis (Required)

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=your-redis-password  # Optional
```

### 3. Start SARK

```bash
python -m sark
```

### 4. Test Authentication

```bash
# List available providers
curl http://localhost:8000/api/auth/providers

# LDAP Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ldap",
    "username": "jdoe",
    "password": "secret"
  }'

# OIDC Authorization (redirect to provider)
curl http://localhost:8000/api/auth/oidc/authorize?redirect_uri=http://localhost:3000/callback
```

## Configuration

### Environment Variables

All authentication settings can be configured via environment variables or `.env` file.

#### General Settings

```bash
# Secret key for signing tokens (REQUIRED)
SECRET_KEY=your-secret-key-min-32-characters

# Session configuration
SESSION_TIMEOUT_SECONDS=86400        # 24 hours
SESSION_MAX_CONCURRENT=5             # Max sessions per user
SESSION_EXTEND_ON_ACTIVITY=true      # Extend on activity
```

#### OIDC Configuration

```bash
OIDC_ENABLED=true
OIDC_PROVIDER=google                  # google, azure, okta, custom
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_SCOPES=openid,profile,email     # Comma-separated
```

#### SAML Configuration

```bash
SAML_ENABLED=true
SAML_SP_ENTITY_ID=https://sark.example.com
SAML_SP_ACS_URL=https://sark.example.com/api/auth/saml/acs
SAML_IDP_ENTITY_ID=https://idp.example.com
SAML_IDP_SSO_URL=https://idp.example.com/sso
SAML_IDP_METADATA_URL=https://idp.example.com/metadata
```

#### LDAP Configuration

```bash
LDAP_ENABLED=true
LDAP_SERVER=ldap://ldap.example.com:389
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=your-password
LDAP_USER_BASE_DN=ou=users,dc=example,dc=com
LDAP_GROUP_BASE_DN=ou=groups,dc=example,dc=com
LDAP_USE_SSL=false                   # Use ldaps://
```

#### Rate Limiting

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_API_KEY=1000         # Per hour
RATE_LIMIT_PER_USER=5000            # Per hour
RATE_LIMIT_PER_IP=100               # Per hour
RATE_LIMIT_ADMIN_BYPASS=true        # Admins bypass limits
```

### Python Configuration

```python
from sark.config.settings import Settings

settings = Settings(
    oidc_enabled=True,
    oidc_provider="google",
    oidc_client_id="your-client-id",
    oidc_client_secret="your-client-secret",
    session_timeout_seconds=86400,
    rate_limit_per_user=5000,
)
```

## API Endpoints

### Authentication Endpoints

#### List Providers

```http
GET /api/auth/providers
```

Returns list of enabled authentication providers.

**Response**:
```json
{
  "providers": [
    {
      "id": "oidc",
      "name": "OIDC (Google)",
      "type": "oidc",
      "enabled": true,
      "authorization_url": "/api/auth/oidc/authorize"
    },
    {
      "id": "ldap",
      "name": "LDAP / Active Directory",
      "type": "ldap",
      "enabled": true
    }
  ],
  "total": 2
}
```

#### LDAP Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "provider": "ldap",
  "username": "jdoe",
  "password": "secret",
  "remember_me": false
}
```

**Response**:
```json
{
  "success": true,
  "message": "Login successful",
  "session": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    "created_at": "2025-11-22T20:00:00Z",
    "expires_at": "2025-11-23T20:00:00Z"
  },
  "user_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
}
```

#### OIDC Authorization

```http
GET /api/auth/oidc/authorize?redirect_uri=http://localhost:3000/callback&state=random-state
```

Redirects to OIDC provider for authentication.

#### OIDC Callback

```http
GET /api/auth/oidc/callback?code=auth-code&state=random-state
```

Handles OAuth callback and creates session.

#### Authentication Status

```http
GET /api/auth/status
Cookie: session_id=550e8400-e29b-41d4-a716-446655440000
```

**Response**:
```json
{
  "authenticated": true,
  "user_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider": "ldap",
  "expires_at": "2025-11-23T20:00:00Z"
}
```

#### Logout

```http
POST /api/auth/logout
Cookie: session_id=550e8400-e29b-41d4-a716-446655440000
```

Invalidates current session.

#### Logout All Devices

```http
POST /api/auth/logout/all
Cookie: session_id=550e8400-e29b-41d4-a716-446655440000
```

Invalidates all user sessions.

### Session Management Endpoints

#### List Sessions

```http
GET /api/auth/sessions
Cookie: session_id=550e8400-e29b-41d4-a716-446655440000
```

Returns all active sessions for the user.

#### Invalidate Session

```http
DELETE /api/auth/sessions/{session_id}
Cookie: session_id=550e8400-e29b-41d4-a716-446655440000
```

Revokes a specific session.

## Session Management

SARK uses Redis for scalable, distributed session storage.

### Features

- **Redis-Backed**: Fast, distributed storage
- **TTL-Based Expiration**: Automatic cleanup
- **Concurrent Limits**: Max 5 sessions per user (configurable)
- **Activity Extension**: Sessions extend on use
- **Multi-Device Support**: Manage sessions across devices

### Session Lifecycle

```python
# 1. Session Created
session = await session_service.create_session(
    user_id=user_uuid,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    metadata={"provider": "ldap", "email": "user@example.com"}
)

# 2. Session Retrieved
session = await session_service.get_session(session_id)

# 3. Session Updated
await session_service.update_last_activity(session_id)

# 4. Session Invalidated
await session_service.invalidate_session(session_id)
```

### Concurrent Session Limits

When a user exceeds the maximum concurrent sessions (default: 5), the oldest session is automatically invalidated.

```python
# Configure limit
SESSION_MAX_CONCURRENT=3  # Only allow 3 devices
```

## Rate Limiting

SARK implements sliding window rate limiting to protect against abuse.

### Rate Limits

| Identifier | Default Limit | Window  |
|-----------|---------------|---------|
| API Key   | 1,000/hour    | 1 hour  |
| JWT User  | 5,000/hour    | 1 hour  |
| IP Address| 100/hour      | 1 hour  |

### Rate Limit Headers

All API responses include rate limit headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4523
X-RateLimit-Reset: 1732310400
```

When rate limited:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1732310400
Retry-After: 1234

{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Limit: 100 per hour",
  "retry_after": 1234
}
```

### Admin Bypass

Users with `admin` or `administrator` role bypass rate limits (configurable).

```bash
RATE_LIMIT_ADMIN_BYPASS=true
```

### Configuration

```python
# Environment variables
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_API_KEY=1000
RATE_LIMIT_PER_USER=5000
RATE_LIMIT_PER_IP=100
RATE_LIMIT_WINDOW_SECONDS=3600
```

## Security Best Practices

### General Security

1. **Use Strong Secret Keys**
   ```bash
   # Generate secure secret key
   openssl rand -hex 32
   ```

2. **Enable HTTPS**
   - All authentication must use HTTPS in production
   - Use secure cookies with `Secure` and `HttpOnly` flags

3. **Implement CORS Properly**
   ```bash
   CORS_ORIGINS=https://app.example.com,https://admin.example.com
   ```

4. **Monitor Authentication Events**
   - Enable audit logging
   - Alert on failed authentication attempts
   - Track session anomalies

### Provider-Specific Security

#### OIDC
- Use `state` parameter for CSRF protection
- Validate `redirect_uri` whitelist
- Store client secrets securely (environment variables, vault)

#### SAML
- Validate SAML assertions
- Use encrypted assertions when possible
- Verify signature on responses

#### LDAP
- Use SSL/TLS (`ldaps://`)
- Limit service account permissions
- Implement connection pooling

#### API Keys
- Rotate keys regularly
- Use scoped permissions
- Never log or expose keys

### Session Security

```python
# Short session timeout for sensitive operations
SESSION_TIMEOUT_SECONDS=900  # 15 minutes

# Limit concurrent sessions
SESSION_MAX_CONCURRENT=3

# Extend session on activity
SESSION_EXTEND_ON_ACTIVITY=true
```

## Troubleshooting

### Common Issues

#### Authentication Fails

**Symptom**: Login returns 401 Unauthorized

**Solutions**:
1. Check provider configuration
2. Verify credentials
3. Check provider health: `GET /api/auth/health`
4. Review logs for detailed errors

#### Session Expires Too Quickly

**Symptom**: Users logged out unexpectedly

**Solutions**:
```bash
# Increase session timeout
SESSION_TIMEOUT_SECONDS=86400  # 24 hours

# Enable activity extension
SESSION_EXTEND_ON_ACTIVITY=true
```

#### Rate Limit Issues

**Symptom**: 429 Too Many Requests

**Solutions**:
```bash
# Increase limits
RATE_LIMIT_PER_USER=10000

# Enable admin bypass
RATE_LIMIT_ADMIN_BYPASS=true

# Check rate limit status
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/auth/status
```

#### Redis Connection Errors

**Symptom**: Sessions not persisting

**Solutions**:
1. Verify Redis is running: `redis-cli ping`
2. Check connection settings:
   ```bash
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=your-password
   ```
3. Test connection: `redis-cli -h localhost -p 6379 ping`

### Debug Mode

Enable debug logging for troubleshooting:

```bash
LOG_LEVEL=DEBUG
DEBUG=true
```

### Health Checks

Monitor authentication system health:

```http
GET /api/auth/health
```

**Response**:
```json
{
  "status": "healthy",
  "providers": [
    {"name": "oidc", "healthy": true},
    {"name": "ldap", "healthy": true},
    {"name": "saml", "healthy": false, "error": "Connection timeout"}
  ],
  "healthy": 2,
  "total": 3
}
```

## Further Reading

- [OIDC Setup Guide](./OIDC_SETUP.md) - Detailed OIDC/OAuth configuration
- [LDAP Setup Guide](./LDAP_SETUP.md) - Active Directory integration
- [SAML Setup Guide](./SAML_SETUP.md) - Enterprise SSO setup
- [API Keys Guide](./API_KEYS.md) - Programmatic access
- [Troubleshooting Guide](./TROUBLESHOOTING.md) - Common issues and solutions

## Support

For issues and questions:
- GitHub Issues: https://github.com/apathy-ca/sark/issues
- Documentation: https://sark.readthedocs.io
- Security Issues: security@example.com
