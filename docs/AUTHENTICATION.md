# SARK Authentication Guide

This guide covers all authentication methods supported by SARK, including configuration, usage, and troubleshooting.

---

## Table of Contents

1. [Overview](#overview)
2. [JWT Authentication](#jwt-authentication)
3. [LDAP/Active Directory](#ldap-active-directory)
4. [OIDC (OpenID Connect)](#oidc-openid-connect)
5. [SAML 2.0](#saml-20)
6. [API Key Management](#api-key-management)
7. [Token Management](#token-management)
8. [Troubleshooting](#troubleshooting)

---

## Overview

SARK provides a flexible, multi-method authentication architecture supporting:

- **JWT (JSON Web Tokens)** - Stateless authentication with HS256/RS256 algorithms
- **LDAP/Active Directory** - Enterprise directory integration with user/group lookup
- **OIDC (OpenID Connect)** - Modern OAuth2/OIDC flow with major cloud providers
- **SAML 2.0** - Enterprise SSO for legacy systems
- **API Keys** - Service-to-service authentication with scoped permissions

### Authentication Flow

```
┌──────────┐                  ┌──────────────┐
│  Client  │                  │     SARK     │
└────┬─────┘                  └──────┬───────┘
     │                               │
     │  1. Login (credentials)       │
     │──────────────────────────────>│
     │                               │
     │                        ┌──────┴────────┐
     │                        │ Authenticate  │
     │                        │ via provider  │
     │                        └──────┬────────┘
     │                               │
     │  2. JWT + Refresh Token       │
     │<──────────────────────────────│
     │                               │
     │  3. API Request + JWT         │
     │──────────────────────────────>│
     │                               │
     │  4. Response                  │
     │<──────────────────────────────│
```

---

## JWT Authentication

### Algorithms Supported

SARK supports two JWT algorithms:

1. **HS256 (HMAC with SHA-256)** - Symmetric key signing
2. **RS256 (RSA with SHA-256)** - Asymmetric key signing

### HS256 Configuration

Best for single-server deployments. Uses a shared secret key.

```bash
# .env
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long
JWT_EXPIRATION_MINUTES=60
```

**Advantages:**
- Simple configuration
- Fast signing/verification
- No key management complexity

**Disadvantages:**
- Same key for signing and verification
- Harder to rotate keys
- Not ideal for distributed systems

### RS256 Configuration

Best for distributed systems and microservices.

```bash
# .env
JWT_ALGORITHM=RS256
JWT_PUBLIC_KEY=/path/to/public_key.pem
JWT_PRIVATE_KEY=/path/to/private_key.pem
JWT_EXPIRATION_MINUTES=60
```

**Generate RSA Key Pair:**
```bash
# Generate private key
openssl genrsa -out private_key.pem 2048

# Extract public key
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

**Advantages:**
- Public key for verification (can be distributed)
- Private key stays secure on auth server
- Better for microservices

**Disadvantages:**
- More complex setup
- Slower than HS256
- Requires key management

### JWT Token Structure

**Access Token Claims:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john.doe@example.com",
  "name": "John Doe",
  "role": "developer",
  "roles": ["developer", "team_lead"],
  "teams": ["engineering", "platform"],
  "permissions": ["server:read", "server:write"],
  "iat": 1645534800,
  "exp": 1645538400,
  "type": "access"
}
```

### Token Verification

JWT tokens are verified by the authentication middleware:

```python
from fastapi import Depends
from sark.services.auth import get_current_user, UserContext

@router.get("/protected")
async def protected_route(user: UserContext = Depends(get_current_user)):
    return {"user_id": user.user_id, "email": user.email}
```

### Token Expiration

**Default Configuration:**
- Access Token: 60 minutes
- Refresh Token: 7 days

**Environment Variables:**
```bash
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=7
```

---

## LDAP/Active Directory

### Configuration

```bash
# .env
LDAP_ENABLED=true
LDAP_SERVER=ldaps://ldap.example.com:636
LDAP_BIND_DN=cn=sark,ou=service,dc=example,dc=com
LDAP_BIND_PASSWORD=service_account_password
LDAP_USER_BASE_DN=ou=users,dc=example,dc=com
LDAP_GROUP_BASE_DN=ou=groups,dc=example,dc=com
LDAP_USER_FILTER=(uid={username})
LDAP_GROUP_FILTER=(member={user_dn})
LDAP_USE_SSL=true
LDAP_TIMEOUT=5
```

### Search Filters

**User Search Filter:**
```bash
# OpenLDAP
LDAP_USER_FILTER=(uid={username})

# Active Directory
LDAP_USER_FILTER=(sAMAccountName={username})
LDAP_USER_FILTER=(userPrincipalName={username}@example.com)
```

**Group Search Filter:**
```bash
# OpenLDAP
LDAP_GROUP_FILTER=(member={user_dn})

# Active Directory
LDAP_GROUP_FILTER=(member:1.2.840.113556.1.4.1941:={user_dn})
```

### Role Mapping

Map LDAP groups to SARK roles:

```bash
# .env
LDAP_ROLE_MAPPING={"cn=admins,ou=groups,dc=example,dc=com":"admin","cn=developers,ou=groups,dc=example,dc=com":"developer"}
```

Or in Python config:
```python
LDAP_ROLE_MAPPING = {
    "cn=admins,ou=groups,dc=example,dc=com": "admin",
    "cn=developers,ou=groups,dc=example,dc=com": "developer",
    "cn=readonly,ou=groups,dc=example,dc=com": "viewer"
}
```

### SSL/TLS Configuration

**LDAPS (Recommended):**
```bash
LDAP_SERVER=ldaps://ldap.example.com:636
LDAP_USE_SSL=true
```

**StartTLS:**
```bash
LDAP_SERVER=ldap://ldap.example.com:389
LDAP_USE_SSL=false  # Will use StartTLS automatically
```

**Certificate Validation:**
```bash
# For self-signed certificates (dev only)
export LDAPTLS_REQCERT=never
```

### Authentication Flow

1. **User submits credentials** (`/api/v1/auth/login/ldap`)
2. **Service account searches for user** in `LDAP_USER_BASE_DN`
3. **Bind as user** to verify password
4. **Look up groups** (if configured)
5. **Map groups to roles** via `LDAP_ROLE_MAPPING`
6. **Issue JWT tokens**

### Testing LDAP Connection

```bash
# Test LDAP connection with ldapsearch
ldapsearch -x -H ldaps://ldap.example.com:636 \
  -D "cn=sark,ou=service,dc=example,dc=com" \
  -w "service_password" \
  -b "ou=users,dc=example,dc=com" \
  "(uid=john.doe)"
```

### Active Directory Example

```bash
# .env for AD
LDAP_ENABLED=true
LDAP_SERVER=ldaps://ad.corp.example.com:636
LDAP_BIND_DN=CN=SARK Service,OU=Service Accounts,DC=corp,DC=example,DC=com
LDAP_BIND_PASSWORD=service_password
LDAP_USER_BASE_DN=OU=Users,DC=corp,DC=example,DC=com
LDAP_GROUP_BASE_DN=OU=Groups,DC=corp,DC=example,DC=com
LDAP_USER_FILTER=(sAMAccountName={username})
LDAP_GROUP_FILTER=(member={user_dn})
LDAP_USE_SSL=true
```

---

## OIDC (OpenID Connect)

### Supported Providers

- **Google** - Google Workspace / Gmail accounts
- **Azure AD** - Microsoft Azure Active Directory
- **Okta** - Okta identity platform
- **Auth0** - Auth0 identity platform
- **Custom** - Any OIDC-compliant provider

### Google Configuration

```bash
# .env
OIDC_ENABLED=true
OIDC_PROVIDER=google
OIDC_DISCOVERY_URL=https://accounts.google.com/.well-known/openid-configuration
OIDC_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
OIDC_CLIENT_SECRET=your-google-client-secret
OIDC_REDIRECT_URI=https://sark.example.com/api/v1/auth/oidc/callback
OIDC_SCOPES=openid,profile,email
OIDC_USE_PKCE=true
```

**Google Cloud Console Setup:**
1. Go to https://console.cloud.google.com/
2. Create a new OAuth 2.0 Client ID
3. Set authorized redirect URI: `https://sark.example.com/api/v1/auth/oidc/callback`
4. Copy Client ID and Client Secret

### Azure AD Configuration

```bash
# .env
OIDC_ENABLED=true
OIDC_PROVIDER=azure
OIDC_AZURE_TENANT=your-tenant-id
OIDC_DISCOVERY_URL=https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration
OIDC_CLIENT_ID=your-azure-client-id
OIDC_CLIENT_SECRET=your-azure-client-secret
OIDC_REDIRECT_URI=https://sark.example.com/api/v1/auth/oidc/callback
OIDC_SCOPES=openid,profile,email
OIDC_USE_PKCE=true
```

**Azure Portal Setup:**
1. Go to https://portal.azure.com/
2. Azure Active Directory → App registrations → New registration
3. Add redirect URI: `https://sark.example.com/api/v1/auth/oidc/callback`
4. Create client secret under Certificates & secrets
5. Copy Application (client) ID and Directory (tenant) ID

### Okta Configuration

```bash
# .env
OIDC_ENABLED=true
OIDC_PROVIDER=okta
OIDC_OKTA_DOMAIN=dev-12345.okta.com
OIDC_DISCOVERY_URL=https://dev-12345.okta.com/.well-known/openid-configuration
OIDC_CLIENT_ID=your-okta-client-id
OIDC_CLIENT_SECRET=your-okta-client-secret
OIDC_REDIRECT_URI=https://sark.example.com/api/v1/auth/oidc/callback
OIDC_SCOPES=openid,profile,email,groups
OIDC_USE_PKCE=true
```

**Okta Admin Console Setup:**
1. Go to https://dev-12345-admin.okta.com/
2. Applications → Create App Integration → OIDC
3. Select Web Application
4. Add Sign-in redirect URI
5. Copy Client ID and Client Secret

### Custom OIDC Provider

```bash
# .env
OIDC_ENABLED=true
OIDC_PROVIDER=custom
OIDC_DISCOVERY_URL=https://idp.example.com/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://sark.example.com/api/v1/auth/oidc/callback
OIDC_SCOPES=openid,profile,email
OIDC_USE_PKCE=true

# Optional: Explicit endpoint configuration (overrides discovery)
OIDC_ISSUER=https://idp.example.com
OIDC_AUTHORIZATION_ENDPOINT=https://idp.example.com/oauth2/authorize
OIDC_TOKEN_ENDPOINT=https://idp.example.com/oauth2/token
OIDC_USERINFO_ENDPOINT=https://idp.example.com/oauth2/userinfo
OIDC_JWKS_URI=https://idp.example.com/oauth2/keys
```

### PKCE (Proof Key for Code Exchange)

PKCE is enabled by default for enhanced security:

```bash
OIDC_USE_PKCE=true
```

**PKCE Flow:**
1. Generate random `code_verifier` (43-128 characters)
2. Create `code_challenge` = BASE64URL(SHA256(code_verifier))
3. Send `code_challenge` in authorization request
4. Send `code_verifier` in token request
5. IdP verifies: `code_challenge == BASE64URL(SHA256(code_verifier))`

### OIDC Authentication Flow

1. **User clicks "Login with OIDC"** → `GET /api/v1/auth/oidc/login`
2. **SARK generates authorization URL** with state and PKCE
3. **User redirected to IdP** for authentication
4. **IdP authenticates user** and redirects back with code
5. **SARK receives callback** → `GET /api/v1/auth/oidc/callback?code=...&state=...`
6. **SARK exchanges code for tokens**
7. **SARK validates ID token** (signature, issuer, audience, expiry)
8. **SARK fetches user info** (optional)
9. **SARK issues JWT tokens** to client

### ID Token Validation

SARK validates ID tokens according to OIDC spec:

- **Signature verification** using IdP's JWKS
- **Issuer (`iss`) claim** matches expected issuer
- **Audience (`aud`) claim** matches client ID
- **Expiration (`exp`) claim** not expired
- **Nonce** matches (if provided)

---

## SAML 2.0

### Service Provider (SP) Setup

SARK acts as a SAML Service Provider.

```bash
# .env
SAML_ENABLED=true
SAML_SP_ENTITY_ID=https://sark.example.com
SAML_SP_ACS_URL=https://sark.example.com/api/auth/saml/acs
SAML_SP_SLS_URL=https://sark.example.com/api/auth/saml/slo
```

### Identity Provider (IdP) Configuration

```bash
# IdP Metadata URL (recommended)
SAML_IDP_METADATA_URL=https://idp.example.com/metadata.xml

# OR manual configuration
SAML_IDP_ENTITY_ID=https://idp.example.com
SAML_IDP_SSO_URL=https://idp.example.com/saml/sso
SAML_IDP_SLO_URL=https://idp.example.com/saml/slo
SAML_IDP_X509_CERT=MIIDXTCCAkWgAwIBAgIJAKZ...  # Base64 cert without headers
```

### Certificate Configuration

**For assertion/message signing:**

```bash
# SP Certificate (for signing)
SAML_SP_X509_CERT=MIIDXTCCAkWgAwIBAgIJAKZ...
SAML_SP_PRIVATE_KEY=MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...

# Signature requirements
SAML_WANT_ASSERTIONS_SIGNED=true
SAML_WANT_MESSAGES_SIGNED=false
```

**Generate SP certificates:**
```bash
# Generate private key and certificate
openssl req -x509 -newkey rsa:2048 -keyout sp_key.pem -out sp_cert.pem -days 365 -nodes

# Extract certificate without headers for .env
grep -v 'BEGIN CERTIFICATE' sp_cert.pem | grep -v 'END CERTIFICATE' | tr -d '\n'

# Extract private key without headers for .env
grep -v 'BEGIN PRIVATE KEY' sp_key.pem | grep -v 'END PRIVATE KEY' | tr -d '\n'
```

### NameID Format

```bash
# Common NameID formats
SAML_NAME_ID_FORMAT=urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress  # Default
SAML_NAME_ID_FORMAT=urn:oasis:names:tc:SAML:2.0:nameid-format:persistent
SAML_NAME_ID_FORMAT=urn:oasis:names:tc:SAML:2.0:nameid-format:transient
```

### Metadata Endpoints

**Download SP Metadata:**
```bash
curl https://sark.example.com/api/auth/saml/metadata > sp_metadata.xml
```

Upload this to your IdP configuration.

### SAML Authentication Flow

1. **User accesses protected resource**
2. **SARK redirects to IdP SSO URL** with `AuthnRequest`
3. **IdP authenticates user**
4. **IdP posts SAML Response** to ACS endpoint
5. **SARK validates SAML assertion**
   - Signature verification
   - Issuer validation
   - Audience restriction
   - Time validity (NotBefore/NotOnOrAfter)
6. **SARK extracts user attributes**
7. **SARK issues JWT tokens**

### Single Logout (SLO)

**IdP-Initiated Logout:**
```
POST /api/auth/saml/slo
```

**SP-Initiated Logout:**
```
POST /api/auth/saml/logout/initiate
```

### Common IdP Configurations

**Okta:**
```bash
SAML_IDP_METADATA_URL=https://dev-12345.okta.com/app/abc123/sso/saml/metadata
SAML_SP_ENTITY_ID=https://sark.example.com
SAML_SP_ACS_URL=https://sark.example.com/api/auth/saml/acs
```

**Azure AD:**
```bash
SAML_IDP_ENTITY_ID=https://sts.windows.net/{tenant-id}/
SAML_IDP_SSO_URL=https://login.microsoftonline.com/{tenant-id}/saml2
SAML_SP_ENTITY_ID=https://sark.example.com
SAML_SP_ACS_URL=https://sark.example.com/api/auth/saml/acs
```

---

## API Key Management

### Creating API Keys

```bash
curl -X POST https://sark.example.com/api/auth/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Automation",
    "description": "API key for CI/CD pipeline",
    "scopes": ["server:read", "server:write"],
    "rate_limit": 1000,
    "expires_in_days": 90,
    "environment": "live"
  }'
```

**Response:**
```json
{
  "api_key": {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "key_prefix": "sark_live_abc",
    "scopes": ["server:read", "server:write"],
    "rate_limit": 1000,
    "expires_at": "2025-05-22T00:00:00Z"
  },
  "key": "sark_live_abc123def456ghi789jkl012mno345",
  "message": "API key created successfully. Save this key securely - it won't be shown again!"
}
```

### Using API Keys

```bash
# In API requests
curl -H "X-API-Key: sark_live_abc123..." https://sark.example.com/api/v1/servers
```

### API Key Scopes

| Scope | Description |
|-------|-------------|
| `server:read` | Read server information |
| `server:write` | Register/update servers |
| `server:delete` | Delete servers |
| `policy:read` | Read policies |
| `policy:write` | Create/update policies |
| `audit:read` | Read audit logs |
| `admin` | Full admin access |

### Key Rotation

```bash
curl -X POST https://sark.example.com/api/auth/api-keys/{key_id}/rotate \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response:**
```json
{
  "api_key": {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "key_prefix": "sark_live_xyz"
  },
  "key": "sark_live_xyz789new456key123rotated",
  "message": "API key rotated successfully. Update your applications with the new key."
}
```

### Key Revocation

```bash
curl -X DELETE https://sark.example.com/api/auth/api-keys/{key_id} \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Rate Limiting

API keys have configurable rate limits (requests per minute):

```bash
# Create key with 500 req/min limit
{
  "rate_limit": 500
}
```

**When limit exceeded:**
```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds.",
  "retry_after": 45
}
```

### Environment Designation

API keys can be designated for specific environments:

- `live` - Production environment
- `test` - Testing/staging environment
- `dev` - Development environment

```bash
{
  "environment": "live"
}
```

---

## Token Management

### Access Token Refresh

```bash
curl -X POST https://sark.example.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "rt_abc123..."
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "rt_xyz789..."
}
```

### Token Rotation

When `REFRESH_TOKEN_ROTATION_ENABLED=true`:
- Old refresh token is revoked
- New refresh token is issued
- Prevents token reuse attacks

```bash
# .env
REFRESH_TOKEN_ROTATION_ENABLED=true
```

### Token Revocation

```bash
curl -X POST https://sark.example.com/api/v1/auth/revoke \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "rt_abc123..."
  }'
```

### Token Storage

- **Access tokens**: Stored client-side (memory or localStorage)
- **Refresh tokens**: Stored in Redis with TTL
- **Revoked tokens**: Tracked in Redis blacklist

### Security Best Practices

1. **Store access tokens in memory** (not localStorage for XSS protection)
2. **Use httpOnly cookies** for refresh tokens
3. **Enable token rotation** for refresh tokens
4. **Set appropriate expiration times**
   - Access: 15-60 minutes
   - Refresh: 7-30 days
5. **Implement token blacklisting** for logout
6. **Use HTTPS only** in production

---

## Troubleshooting

### Common Issues

#### LDAP Connection Failed

**Symptoms:**
```
503 Service Unavailable: Authentication service temporarily unavailable
```

**Solutions:**
1. Verify LDAP server is reachable:
   ```bash
   telnet ldap.example.com 636
   ```
2. Check SSL/TLS certificate:
   ```bash
   openssl s_client -connect ldap.example.com:636
   ```
3. Test with ldapsearch:
   ```bash
   ldapsearch -x -H ldaps://ldap.example.com:636 \
     -D "$LDAP_BIND_DN" -w "$LDAP_BIND_PASSWORD" \
     -b "$LDAP_USER_BASE_DN" "(uid=test)"
   ```
4. Check logs:
   ```bash
   docker logs sark-api | grep ldap
   ```

#### OIDC Discovery Failed

**Symptoms:**
```
503 Service Unavailable: OIDC configuration error
```

**Solutions:**
1. Verify discovery URL is accessible:
   ```bash
   curl https://accounts.google.com/.well-known/openid-configuration
   ```
2. Check client ID and secret are correct
3. Verify redirect URI matches exactly
4. Check logs for detailed error:
   ```bash
   docker logs sark-api | grep oidc
   ```

#### SAML Assertion Invalid

**Symptoms:**
```
401 Unauthorized: SAML authentication failed
```

**Solutions:**
1. Verify SP metadata matches IdP configuration
2. Check certificate expiration:
   ```bash
   openssl x509 -in sp_cert.pem -text -noout
   ```
3. Validate assertion signature requirements
4. Check clock synchronization (SAML requires time accuracy)
   ```bash
   timedatectl status
   ```
5. Enable debug logging:
   ```bash
   LOG_LEVEL=DEBUG
   ```

#### Invalid JWT Token

**Symptoms:**
```
401 Unauthorized: Could not validate credentials
```

**Solutions:**
1. Verify token hasn't expired
2. Check JWT secret key is correct
3. Verify algorithm matches (HS256 vs RS256)
4. Decode token to inspect claims:
   ```bash
   # Install jwt-cli: https://github.com/mike-engel/jwt-cli
   jwt decode $TOKEN
   ```

#### API Key Rate Limit Exceeded

**Symptoms:**
```
429 Too Many Requests: Rate limit exceeded
```

**Solutions:**
1. Check API key rate limit:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     https://sark.example.com/api/auth/api-keys/{key_id}
   ```
2. Increase rate limit if needed:
   ```bash
   curl -X PATCH https://sark.example.com/api/auth/api-keys/{key_id} \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"rate_limit": 2000}'
   ```
3. Implement exponential backoff in client
4. Use multiple API keys for load distribution

### Debug Logging

Enable detailed authentication logs:

```bash
# .env
LOG_LEVEL=DEBUG
DEBUG=true
```

View logs:
```bash
# Docker
docker logs -f sark-api

# Kubernetes
kubectl logs -f deployment/sark-api

# Grep for specific auth events
docker logs sark-api | grep -E "(ldap|oidc|saml|jwt|token)"
```

### Health Checks

```bash
# Check authentication service health
curl https://sark.example.com/health/detailed

# Check LDAP connectivity
curl https://sark.example.com/api/v1/auth/ldap/health

# Check OIDC configuration
curl https://sark.example.com/api/v1/auth/oidc/health

# Check SAML configuration
curl https://sark.example.com/api/auth/saml/health
```

### Error Codes Reference

| Code | Error | Cause | Solution |
|------|-------|-------|----------|
| 401 | Invalid credentials | Wrong username/password | Verify credentials |
| 401 | Token expired | Access token expired | Refresh token |
| 401 | Invalid token | Malformed or tampered token | Re-authenticate |
| 403 | Insufficient permissions | User lacks required role | Grant permissions |
| 503 | Service unavailable | LDAP/IdP down | Check service status |

---

## Security Recommendations

### Production Checklist

- [ ] Use HTTPS for all endpoints
- [ ] Enable token rotation for refresh tokens
- [ ] Set appropriate token expiration times
- [ ] Use RS256 for JWT in distributed systems
- [ ] Enable LDAPS (LDAP over SSL)
- [ ] Enable PKCE for OIDC flows
- [ ] Require signed SAML assertions
- [ ] Implement rate limiting for API keys
- [ ] Monitor authentication failures
- [ ] Rotate secrets regularly
- [ ] Use environment variables for secrets (not hardcoded)
- [ ] Enable audit logging for all auth events
- [ ] Implement IP allowlisting for sensitive operations
- [ ] Use short-lived access tokens (15-60 min)
- [ ] Implement MFA for admin accounts

### Secret Management

**Do NOT commit secrets to Git:**
```bash
# .gitignore
.env
*.pem
*.key
```

**Use a secret manager in production:**
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Google Secret Manager

**Example with Vault:**
```bash
# Store in Vault
vault kv put secret/sark/auth \
  jwt_secret_key="..." \
  ldap_bind_password="..." \
  oidc_client_secret="..."

# Load in application
export JWT_SECRET_KEY=$(vault kv get -field=jwt_secret_key secret/sark/auth)
```

---

## Additional Resources

- [API Reference](./API_REFERENCE.md) - Complete API endpoint documentation
- [OPA Policy Guide](./OPA_POLICY_GUIDE.md) - Authorization policies
- [Security Guide](./SECURITY.md) - Security best practices
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment

**External Documentation:**
- [JWT RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- [OIDC Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [SAML 2.0 Specification](http://docs.oasis-open.org/security/saml/v2.0/)
- [LDAP RFC 4510](https://datatracker.ietf.org/doc/html/rfc4510)
