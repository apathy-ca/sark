# OIDC/OAuth 2.0 Setup Guide

Complete guide to configuring OpenID Connect and OAuth 2.0 authentication in SARK.

## Table of Contents

- [Overview](#overview)
- [Supported Providers](#supported-providers)
- [Google Workspace](#google-workspace)
- [Microsoft Azure AD](#microsoft-azure-ad)
- [Okta](#okta)
- [Custom OIDC Provider](#custom-oidc-provider)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

SARK supports OAuth 2.0 and OpenID Connect (OIDC) for modern, standards-based authentication. OIDC provides:

- **Single Sign-On (SSO)**: Users authenticate via external identity provider
- **Federated Identity**: No password storage in SARK
- **Standard Protocol**: Works with any OIDC-compliant provider
- **Automatic User Provisioning**: User accounts created on first login

### OIDC Flow

```
1. User → SARK → Redirect to IdP
2. User authenticates with IdP (Google, Azure, etc.)
3. IdP redirects back to SARK with authorization code
4. SARK exchanges code for access token
5. SARK validates token and creates session
6. User granted access
```

## Supported Providers

SARK includes built-in support for:

- **Google Workspace** - Google OAuth 2.0
- **Microsoft Azure AD** - Azure Active Directory / Entra ID
- **Okta** - Okta Identity Cloud
- **Custom** - Any OIDC-compliant provider

## Google Workspace

### Prerequisites

- Google Cloud Project
- Google Workspace or Gmail account
- Admin access to Google Cloud Console

### Setup Steps

#### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a Project" → "New Project"
3. Enter project name: "SARK Authentication"
4. Click "Create"

#### 2. Enable APIs

1. Navigate to "APIs & Services" → "Library"
2. Search for "Google+ API" and enable it
3. Search for "People API" and enable it

#### 3. Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose user type:
   - **Internal**: For Google Workspace organizations only
   - **External**: For any Google account
3. Fill in required fields:
   - App name: "SARK"
   - User support email: your-email@example.com
   - Developer contact: your-email@example.com
4. Add scopes:
   - `openid`
   - `profile`
   - `email`
5. Click "Save and Continue"

#### 4. Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Web application"
4. Name: "SARK Web Client"
5. Add authorized redirect URIs:
   ```
   http://localhost:8000/api/auth/oidc/callback
   https://sark.example.com/api/auth/oidc/callback
   ```
6. Click "Create"
7. **Save the Client ID and Client Secret**

#### 5. Configure SARK

Create `.env` file or set environment variables:

```bash
# Enable OIDC
OIDC_ENABLED=true

# Google provider
OIDC_PROVIDER=google

# Credentials from Google Cloud Console
OIDC_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
OIDC_CLIENT_SECRET=GOCSPX-your-secret-here

# Scopes (optional, defaults shown)
OIDC_SCOPES=openid,profile,email
```

#### 6. Test

```bash
# Start SARK
python -m sark

# Open browser
http://localhost:8000/api/auth/oidc/authorize?redirect_uri=http://localhost:8000/callback
```

### Domain Restriction (Workspace Only)

Restrict access to specific Google Workspace domain:

1. In Google Cloud Console, go to OAuth consent screen
2. Add "Authorized domains": `example.com`
3. In SARK, verify `hd` claim in token:

```python
# src/sark/services/auth/providers/oidc.py
def validate_token(self, token):
    user_info = self.decode_token(token)

    # Verify hosted domain
    if user_info.get('hd') != 'example.com':
        raise ValueError("Invalid domain")

    return user_info
```

## Microsoft Azure AD

### Prerequisites

- Azure subscription
- Azure AD tenant
- Application registration permissions

### Setup Steps

#### 1. Register Application

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to "Azure Active Directory" → "App registrations"
3. Click "New registration"
4. Fill in details:
   - Name: "SARK"
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: Web → `https://sark.example.com/api/auth/oidc/callback`
5. Click "Register"

#### 2. Create Client Secret

1. In your app registration, go to "Certificates & secrets"
2. Click "New client secret"
3. Description: "SARK OAuth Secret"
4. Expires: Choose duration (12 months recommended)
5. Click "Add"
6. **Copy the secret value immediately** (shown only once)

#### 3. Configure API Permissions

1. Go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Delegated permissions"
5. Add permissions:
   - `openid`
   - `profile`
   - `email`
   - `User.Read`
6. Click "Grant admin consent" (if you have admin rights)

#### 4. Get Tenant ID

1. In Azure AD, go to "Overview"
2. Copy the "Tenant ID" (e.g., `12345678-1234-1234-1234-123456789012`)

#### 5. Configure SARK

```bash
# Enable OIDC
OIDC_ENABLED=true

# Azure provider
OIDC_PROVIDER=azure

# Application (client) ID from app registration
OIDC_CLIENT_ID=12345678-1234-1234-1234-123456789012

# Client secret created in step 2
OIDC_CLIENT_SECRET=your-secret-value-here

# Tenant ID from Azure AD
OIDC_AZURE_TENANT=your-tenant-id-here

# Scopes
OIDC_SCOPES=openid,profile,email,User.Read
```

#### 6. Test

```bash
python -m sark

# Open browser to
http://localhost:8000/api/auth/oidc/authorize?redirect_uri=http://localhost:8000/callback
```

### Multi-Tenant Support

To support users from any Azure AD tenant:

1. In app registration, change "Supported account types" to "Accounts in any organizational directory"
2. In SARK config, set:
   ```bash
   OIDC_AZURE_TENANT=common
   ```

### B2C Support

For Azure AD B2C:

```bash
OIDC_PROVIDER=azure
OIDC_ISSUER=https://your-tenant.b2clogin.com/your-tenant.onmicrosoft.com/v2.0/
OIDC_AZURE_TENANT=your-tenant
```

## Okta

### Prerequisites

- Okta account (free developer account available)
- Admin access to Okta dashboard

### Setup Steps

#### 1. Create Application

1. Log in to [Okta Admin Console](https://your-domain.okta.com/admin)
2. Go to "Applications" → "Applications"
3. Click "Create App Integration"
4. Sign-in method: "OIDC - OpenID Connect"
5. Application type: "Web Application"
6. Click "Next"

#### 2. Configure Application

1. App integration name: "SARK"
2. Grant type: "Authorization Code"
3. Sign-in redirect URIs:
   ```
   http://localhost:8000/api/auth/oidc/callback
   https://sark.example.com/api/auth/oidc/callback
   ```
4. Sign-out redirect URIs: (optional)
   ```
   https://sark.example.com/
   ```
5. Controlled access: Choose appropriate option
6. Click "Save"

#### 3. Get Credentials

1. In your application, note:
   - Client ID (shown on General tab)
   - Client secret (click "Copy to clipboard")
2. In Okta domain overview, note:
   - Okta domain (e.g., `dev-12345.okta.com`)

#### 4. Assign Users

1. Go to "Assignments" tab
2. Click "Assign" → "Assign to People"
3. Add users who should have access

#### 5. Configure SARK

```bash
# Enable OIDC
OIDC_ENABLED=true

# Okta provider
OIDC_PROVIDER=okta

# Client credentials from Okta app
OIDC_CLIENT_ID=0oa12345abcdefgh
OIDC_CLIENT_SECRET=your-secret-here

# Okta domain (without https://)
OIDC_OKTA_DOMAIN=dev-12345.okta.com

# Scopes
OIDC_SCOPES=openid,profile,email
```

#### 6. Test

```bash
python -m sark

# Navigate to
http://localhost:8000/api/auth/oidc/authorize?redirect_uri=http://localhost:8000/callback
```

### Group Claims

To include Okta groups in token:

1. In Okta app, go to "Sign On" tab
2. Click "Edit" in OpenID Connect ID Token section
3. Add claims:
   - Name: `groups`
   - Include in: ID Token, Always
   - Value type: Groups
   - Filter: Matches regex `.*`
4. Save

Access groups in SARK:

```python
user_info = await oidc_provider.validate_token(token)
groups = user_info.get('groups', [])
```

## Custom OIDC Provider

### Requirements

Your OIDC provider must support:
- OpenID Connect Discovery (`.well-known/openid-configuration`)
- Authorization Code Flow
- JWT token validation

### Configuration

```bash
# Enable OIDC
OIDC_ENABLED=true

# Custom provider
OIDC_PROVIDER=custom

# Client credentials
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret

# Issuer (base URL of your OIDC provider)
OIDC_ISSUER=https://auth.example.com

# Discovery endpoint (optional, auto-detected from issuer)
OIDC_DISCOVERY_URL=https://auth.example.com/.well-known/openid-configuration

# Manual endpoint configuration (if discovery not supported)
OIDC_AUTHORIZATION_ENDPOINT=https://auth.example.com/authorize
OIDC_TOKEN_ENDPOINT=https://auth.example.com/token
OIDC_USERINFO_ENDPOINT=https://auth.example.com/userinfo
OIDC_JWKS_URI=https://auth.example.com/.well-known/jwks.json

# Scopes
OIDC_SCOPES=openid,profile,email
```

### Testing Discovery

```bash
# Test OIDC discovery endpoint
curl https://auth.example.com/.well-known/openid-configuration | jq
```

Should return:
```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "userinfo_endpoint": "https://auth.example.com/userinfo",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "response_types_supported": ["code"],
  "subject_types_supported": ["public"],
  "id_token_signing_alg_values_supported": ["RS256"]
}
```

## Configuration

### Complete Configuration Options

```bash
# Enable/disable OIDC
OIDC_ENABLED=true

# Provider type
OIDC_PROVIDER=google  # google, azure, okta, custom

# Client credentials (REQUIRED)
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret

# Provider-specific settings
OIDC_AZURE_TENANT=your-tenant-id      # Azure only
OIDC_OKTA_DOMAIN=dev-12345.okta.com   # Okta only
OIDC_ISSUER=https://auth.example.com  # Custom provider

# OAuth scopes (comma-separated)
OIDC_SCOPES=openid,profile,email

# Manual endpoint configuration (optional)
OIDC_AUTHORIZATION_ENDPOINT=https://provider.com/authorize
OIDC_TOKEN_ENDPOINT=https://provider.com/token
OIDC_USERINFO_ENDPOINT=https://provider.com/userinfo
OIDC_JWKS_URI=https://provider.com/.well-known/jwks.json

# Discovery URL (auto-detected from issuer if not set)
OIDC_DISCOVERY_URL=https://provider.com/.well-known/openid-configuration
```

### Python Configuration

```python
from sark.config.settings import Settings

settings = Settings(
    oidc_enabled=True,
    oidc_provider="google",
    oidc_client_id="your-client-id",
    oidc_client_secret="your-client-secret",
    oidc_scopes=["openid", "profile", "email"],
)
```

## Testing

### Test Authentication Flow

```bash
# 1. Start SARK
python -m sark

# 2. Get authorization URL
curl http://localhost:8000/api/auth/oidc/authorize?redirect_uri=http://localhost:3000/callback

# 3. Open URL in browser, authenticate

# 4. After callback, check session
curl -H "Cookie: session_id=YOUR_SESSION_ID" \
  http://localhost:8000/api/auth/status
```

### Test Token Validation

```python
import asyncio
from sark.services.auth.providers import OIDCProvider

async def test_oidc():
    provider = OIDCProvider(
        client_id="your-client-id",
        client_secret="your-secret",
        provider="google"
    )

    # Test token validation
    user_info = await provider.validate_token("access-token")
    print(f"User: {user_info.email}")

    # Test health check
    healthy = await provider.health_check()
    print(f"Provider healthy: {healthy}")

asyncio.run(test_oidc())
```

### Verify Provider Health

```bash
# Check all auth providers
curl http://localhost:8000/api/auth/health | jq

# Response
{
  "status": "healthy",
  "providers": [
    {"name": "oidc", "healthy": true}
  ],
  "healthy": 1,
  "total": 1
}
```

## Troubleshooting

### Common Issues

#### "Invalid redirect URI" Error

**Cause**: Redirect URI mismatch between SARK and provider config

**Solution**:
1. Check SARK's callback URL matches provider exactly
2. Include protocol (`http://` or `https://`)
3. Check for trailing slashes
4. Add all environments (localhost, staging, production)

#### "Invalid client" Error

**Cause**: Wrong client ID or secret

**Solution**:
1. Verify `OIDC_CLIENT_ID` matches provider
2. Ensure `OIDC_CLIENT_SECRET` is correct
3. Check for extra spaces or quotes in `.env` file

#### Token Validation Fails

**Cause**: JWT signature verification fails

**Solution**:
1. Verify issuer matches: check `OIDC_ISSUER`
2. Ensure provider's JWKS is accessible
3. Check system time is synchronized (for `exp` claim)

```bash
# Test JWKS endpoint
curl https://oauth2.googleapis.com/certs | jq
```

#### "Insufficient scopes" Error

**Cause**: Required scopes not requested

**Solution**:
```bash
# Add missing scopes
OIDC_SCOPES=openid,profile,email,additional_scope
```

#### Discovery Fails (Custom Provider)

**Cause**: Provider doesn't support OIDC discovery

**Solution**: Configure endpoints manually
```bash
OIDC_AUTHORIZATION_ENDPOINT=https://provider.com/authorize
OIDC_TOKEN_ENDPOINT=https://provider.com/token
OIDC_USERINFO_ENDPOINT=https://provider.com/userinfo
OIDC_JWKS_URI=https://provider.com/.well-known/jwks.json
```

### Debug Mode

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG
```

Check logs for:
- Authorization URL generation
- Token exchange requests
- Token validation details
- Provider API responses

### Testing Endpoints

```bash
# Test authorization endpoint
curl "http://localhost:8000/api/auth/oidc/authorize?redirect_uri=http://localhost:3000/callback&state=test123"

# Should return 307 redirect to provider

# Test callback (after getting code from provider)
curl "http://localhost:8000/api/auth/oidc/callback?code=AUTH_CODE&state=test123"

# Should return session details
```

## Security Best Practices

1. **Use HTTPS in Production**
   - Never use `http://` for callback URLs in production
   - Use proper SSL certificates

2. **Protect Client Secrets**
   - Never commit secrets to git
   - Use environment variables or secure vaults
   - Rotate secrets periodically

3. **Validate State Parameter**
   - Prevents CSRF attacks
   - SARK handles this automatically

4. **Restrict Redirect URIs**
   - Whitelist specific URIs in provider config
   - Never use wildcards

5. **Use Short-Lived Tokens**
   ```bash
   SESSION_TIMEOUT_SECONDS=3600  # 1 hour
   ```

6. **Monitor Failed Authentications**
   - Enable audit logging
   - Alert on repeated failures

## Next Steps

- [Session Management](./AUTHENTICATION.md#session-management)
- [Rate Limiting](./AUTHENTICATION.md#rate-limiting)
- [API Keys Guide](./API_KEYS.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

## Support

- GitHub Issues: https://github.com/apathy-ca/sark/issues
- Documentation: https://sark.readthedocs.io
