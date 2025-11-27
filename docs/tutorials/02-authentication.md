# Tutorial 02: Authentication with SARK

**Level:** Beginner
**Duration:** 30-45 minutes
**Prerequisites:** Tutorial 01 completed, Docker Compose running

## Overview

In this tutorial, you'll learn how to authenticate with SARK using multiple methods:
- API Keys (for automation)
- LDAP (for enterprise users)
- OIDC/OAuth2 (for SSO)
- JWT tokens (for API access)

## Learning Objectives

By the end of this tutorial, you will be able to:
- ✅ Create and manage API keys
- ✅ Authenticate using LDAP
- ✅ Set up OIDC authentication
- ✅ Work with JWT access and refresh tokens
- ✅ Understand SARK's session management

---

## Part 1: API Key Authentication

API keys are the simplest authentication method, perfect for:
- Automation scripts
- CI/CD pipelines
- Service-to-service communication

### Step 1.1: Create Your First API Key

First, we need to bootstrap with a temporary admin token (in development only):

```bash
# Set up development environment
export SARK_API_URL="http://localhost:8000"

# Bootstrap admin token (dev only - from .env file)
export ADMIN_TOKEN="dev-admin-token-change-in-production"

# Create an API key
curl -X POST $SARK_API_URL/api/auth/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First API Key",
    "description": "Tutorial API key for learning",
    "scopes": ["server:read", "server:write"],
    "expires_in_days": 30,
    "environment": "development"
  }' | jq .
```

**Expected Response:**
```json
{
  "api_key": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My First API Key",
    "key_prefix": "sark_dev_abc",
    "scopes": ["server:read", "server:write"],
    "expires_at": "2025-12-27T00:00:00Z",
    "is_active": true
  },
  "key": "sark_dev_abc123def456ghi789jkl012mno345pqr",
  "message": "API key created successfully. Save this key securely - it won't be shown again!"
}
```

⚠️ **Important:** Save the `key` value! It will only be shown once.

```bash
# Save your API key
export SARK_API_KEY="sark_dev_abc123def456ghi789jkl012mno345pqr"
```

### Step 1.2: Use Your API Key

Now test your API key by listing servers:

```bash
curl -X GET $SARK_API_URL/api/v1/servers \
  -H "X-API-Key: $SARK_API_KEY" | jq .
```

**Expected Response:**
```json
{
  "items": [],
  "next_cursor": null,
  "has_more": false,
  "total": 0
}
```

### Step 1.3: Test API Key Scopes

Try to access an endpoint outside your scopes:

```bash
# This should work (server:read scope)
curl -X GET $SARK_API_URL/api/v1/servers \
  -H "X-API-Key: $SARK_API_KEY"

# This should work (server:write scope)
curl -X POST $SARK_API_URL/api/v1/servers \
  -H "X-API-Key: $SARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d @examples/minimal-server.json

# This should fail (policy:write not in scopes)
curl -X POST $SARK_API_URL/api/v1/policy/upload \
  -H "X-API-Key: $SARK_API_KEY" \
  -d '{"policy": "..."}' \
  --fail || echo "❌ Access denied (expected)"
```

### Step 1.4: List Your API Keys

```bash
curl -X GET $SARK_API_URL/api/auth/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
```

### Step 1.5: Revoke an API Key

```bash
# Get the API key ID from the list above
API_KEY_ID="550e8400-e29b-41d4-a716-446655440000"

# Revoke it
curl -X DELETE $SARK_API_URL/api/auth/api-keys/$API_KEY_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Try using the revoked key (should fail)
curl -X GET $SARK_API_URL/api/v1/servers \
  -H "X-API-Key: $SARK_API_KEY" \
  --fail || echo "❌ Key revoked (expected)"
```

---

## Part 2: LDAP Authentication

LDAP authentication is used for enterprise environments with Active Directory or OpenLDAP.

### Step 2.1: Configure LDAP (If Using Docker Compose)

Your `docker-compose.yml` should include an LDAP server for testing:

```yaml
services:
  openldap:
    image: osixia/openldap:latest
    environment:
      LDAP_ORGANISATION: "Example Corp"
      LDAP_DOMAIN: "example.com"
      LDAP_ADMIN_PASSWORD: "admin"
```

### Step 2.2: Authenticate with LDAP

```bash
curl -X POST $SARK_API_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ldap",
    "username": "john.doe",
    "password": "secret123"
  }' | jq .
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "session": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "rt_abc123..."
  },
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Step 2.3: Save Your Tokens

```bash
# Extract tokens using jq
export ACCESS_TOKEN=$(curl -s -X POST $SARK_API_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ldap",
    "username": "john.doe",
    "password": "secret123"
  }' | jq -r '.session.access_token')

export REFRESH_TOKEN=$(curl -s -X POST $SARK_API_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ldap",
    "username": "john.doe",
    "password": "secret123"
  }' | jq -r '.session.refresh_token')

echo "Access Token: $ACCESS_TOKEN"
```

### Step 2.4: Use JWT Access Token

```bash
# Use the access token to call protected endpoints
curl -X GET $SARK_API_URL/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

**Expected Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "role": "developer",
  "teams": ["engineering", "platform"],
  "permissions": ["server:read", "server:write"]
}
```

### Step 2.5: Refresh Your Access Token

Access tokens expire after 60 minutes (by default). Use your refresh token to get a new one:

```bash
curl -X POST $SARK_API_URL/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }" | jq .
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "rt_xyz789..."
}
```

**Note:** If `REFRESH_TOKEN_ROTATION_ENABLED=true`, you'll get a new refresh token. Save it!

---

## Part 3: OIDC/OAuth2 Authentication

OIDC (OpenID Connect) is used for SSO with providers like Okta, Auth0, or Google.

### Step 3.1: Configure OIDC Provider

In your `.env` file:

```bash
# OIDC Configuration
OIDC_ENABLED=true
OIDC_PROVIDER_URL=https://accounts.google.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=http://localhost:8000/api/v1/auth/oidc/callback
```

### Step 3.2: Initiate OIDC Login

OIDC requires a web browser flow:

```bash
# Get the authorization URL
curl -X GET $SARK_API_URL/api/v1/auth/oidc/login

# This will redirect you to the OIDC provider
# After login, you'll be redirected back with a code
```

**In a browser:**
1. Navigate to `http://localhost:8000/api/v1/auth/oidc/login`
2. You'll be redirected to your OIDC provider (e.g., Google)
3. Log in with your credentials
4. After successful login, you'll be redirected back with tokens

### Step 3.3: Handle OIDC Callback

The callback will return tokens similar to LDAP:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "rt_oidc_abc123...",
  "user": {
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "email": "user@example.com",
    "name": "Jane Smith",
    "roles": ["developer"]
  }
}
```

---

## Part 4: Session Management

SARK uses a dual-token system for security:
- **Access Token** (JWT) - Short-lived (60 min), used for API requests
- **Refresh Token** - Long-lived (7 days), used to get new access tokens

### Step 4.1: Check Your Session

```bash
curl -X GET $SARK_API_URL/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

### Step 4.2: Logout (Revoke Session)

```bash
curl -X POST $SARK_API_URL/api/v1/auth/revoke \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }" | jq .
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Refresh token revoked successfully"
}
```

### Step 4.3: Try Using Revoked Token

```bash
# This should fail
curl -X POST $SARK_API_URL/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }" \
  --fail || echo "❌ Token revoked (expected)"
```

---

## Part 5: Best Practices

### 5.1: Token Storage

**For Web Applications:**
```javascript
// ❌ DON'T: Store in localStorage (vulnerable to XSS)
localStorage.setItem('access_token', token);

// ✅ DO: Store in memory + httpOnly cookie for refresh token
let accessToken = '...';  // In memory
// Refresh token in httpOnly cookie (set by backend)
```

**For CLI/Scripts:**
```bash
# ✅ DO: Use API keys instead of tokens
export SARK_API_KEY="sark_live_..."

# ❌ DON'T: Hard-code tokens in scripts
```

**For Mobile/Desktop Apps:**
```python
# ✅ DO: Use secure storage (Keychain/Keystore)
from keyring import set_password, get_password

set_password("sark", "access_token", token)
token = get_password("sark", "access_token")
```

### 5.2: Token Refresh Strategy

```python
import requests
from datetime import datetime, timedelta

class SARKClient:
    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = datetime.now() + timedelta(minutes=60)

    def _ensure_fresh_token(self):
        # Refresh if token expires in < 5 minutes
        if datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            self._refresh_token()

    def _refresh_token(self):
        response = requests.post(
            "http://localhost:8000/api/v1/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"])

    def list_servers(self):
        self._ensure_fresh_token()
        response = requests.get(
            "http://localhost:8000/api/v1/servers",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        return response.json()
```

### 5.3: Error Handling

```bash
# Always check for 401 Unauthorized
response=$(curl -s -w "\n%{http_code}" -X GET $SARK_API_URL/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "401" ]; then
    echo "Token expired or invalid, refreshing..."
    # Refresh token logic here
fi
```

### 5.4: Scope Principle of Least Privilege

```bash
# ❌ DON'T: Request all scopes
{
  "scopes": ["*"]  # Too broad!
}

# ✅ DO: Request only what you need
{
  "scopes": ["server:read"]  # Read-only access
}

# ✅ DO: Use different keys for different purposes
# Key for CI/CD (write access)
{
  "name": "CI/CD Pipeline",
  "scopes": ["server:write"]
}

# Key for monitoring (read-only)
{
  "name": "Monitoring Dashboard",
  "scopes": ["server:read", "metrics:read"]
}
```

---

## Part 6: Troubleshooting

### Issue: "Invalid credentials"

**Symptoms:**
```json
{
  "error": "invalid_credentials",
  "message": "Username or password is incorrect"
}
```

**Solutions:**
1. Check LDAP server is running: `docker-compose ps openldap`
2. Verify credentials in LDAP
3. Check SARK logs: `docker-compose logs sark-api | grep auth`

### Issue: "Token expired"

**Symptoms:**
```json
{
  "error": "token_expired",
  "message": "Access token has expired"
}
```

**Solutions:**
1. Use refresh token to get new access token
2. Re-authenticate if refresh token also expired

### Issue: "Insufficient scopes"

**Symptoms:**
```json
{
  "error": "insufficient_scopes",
  "message": "API key does not have required scopes"
}
```

**Solutions:**
1. Check API key scopes: `GET /api/auth/api-keys`
2. Create new key with required scopes
3. Update existing key scopes (if allowed by policy)

---

## Part 7: Quick Reference

### Authentication Methods

| Method | Use Case | Lifespan | Best For |
|--------|----------|----------|----------|
| **API Key** | Automation, scripts | 30-90 days | CI/CD, cron jobs |
| **JWT Access Token** | API requests | 60 minutes | User sessions |
| **JWT Refresh Token** | Token renewal | 7 days | Mobile/web apps |
| **LDAP** | Enterprise users | Session-based | Corporate environments |
| **OIDC** | SSO | Session-based | SaaS, multi-org |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/api-keys` | POST | Create API key |
| `/api/auth/api-keys` | GET | List API keys |
| `/api/auth/api-keys/{id}` | DELETE | Revoke API key |
| `/api/v1/auth/login` | POST | Login (LDAP) |
| `/api/v1/auth/oidc/login` | GET | Initiate OIDC flow |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/revoke` | POST | Logout |
| `/api/v1/auth/me` | GET | Get current user |

### Common Headers

```bash
# API Key
-H "X-API-Key: sark_live_abc123..."

# JWT Bearer Token
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

---

## Summary

In this tutorial, you learned:

✅ How to create and manage API keys
✅ How to authenticate with LDAP
✅ How OIDC/OAuth2 authentication works
✅ How to work with JWT tokens
✅ How to refresh tokens before expiration
✅ Session management best practices
✅ Token storage security
✅ Error handling and troubleshooting

## Next Steps

- **Tutorial 03:** Working with Policies
- **Tutorial 04:** Advanced Server Management
- **Tutorial 05:** Audit Logs and Compliance

## Additional Resources

- [Authentication Guide](../AUTHENTICATION.md)
- [API Reference - Auth Endpoints](../API_REFERENCE.md#authentication-endpoints)
- [Security Best Practices](../SECURITY.md)
- [LDAP Setup Guide](../LDAP_SETUP.md)
- [OIDC Setup Guide](../OIDC_SETUP.md)

---

**Need Help?**
- Check the [FAQ](../FAQ.md)
- Review [Troubleshooting Guide](../TROUBLESHOOTING.md)
- Ask in community forum
- Contact support@company.com
