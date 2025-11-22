# Authentication Troubleshooting Guide

Common issues and solutions for SARK authentication.

## Quick Diagnosis

```bash
# Check authentication health
curl http://localhost:8000/api/auth/health | jq

# Check current authentication status
curl -H "Cookie: session_id=YOUR_SESSION" \
  http://localhost:8000/api/auth/status | jq

# Enable debug logging
export LOG_LEVEL=DEBUG
python -m sark
```

## Common Issues

### Authentication Fails

#### Symptom

```http
HTTP/1.1 401 Unauthorized
{
  "detail": "Invalid credentials"
}
```

#### Solutions by Provider

**OIDC:**
- Check client ID and secret
- Verify redirect URI matches exactly
- Test with provider's authentication tester

**LDAP:**
- Test LDAP connection with ldapsearch
- Verify service account credentials
- Check user search filter and base DN

**SAML:**
- Validate clock synchronization (NTP)
- Check certificate expiration
- Verify audience URI matches

**API Keys:**
- Confirm key hasn't been revoked
- Check scopes include required permissions
- Verify `X-API-Key` header format

### Sessions Not Persisting

#### Symptom
User logged out immediately or on page refresh

#### Causes & Solutions

**Redis not running:**
```bash
# Check Redis
redis-cli ping
# Should return: PONG

# Start Redis
redis-server
```

**Wrong Redis configuration:**
```bash
# Verify settings
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0

# Test connection
redis-cli -h localhost -p 6379 ping
```

**Session timeout too short:**
```bash
# Increase session timeout
SESSION_TIMEOUT_SECONDS=86400  # 24 hours
```

**Cookies not being set:**
- Check HTTPS in production (secure cookies)
- Verify domain in cookie settings
- Check browser doesn't block cookies

### Rate Limit Issues

#### Symptom

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Remaining: 0
Retry-After: 1234

{
  "error": "Rate limit exceeded",
  "retry_after": 1234
}
```

#### Solutions

**Increase limits:**
```bash
RATE_LIMIT_PER_USER=10000
RATE_LIMIT_PER_API_KEY=5000
```

**Enable admin bypass:**
```bash
RATE_LIMIT_ADMIN_BYPASS=true
```

**Implement backoff:**
```python
import time
import requests

def api_call_with_retry(url, headers):
    for attempt in range(5):
        response = requests.get(url, headers=headers)

        if response.status_code != 429:
            return response

        # Rate limited - wait and retry
        retry_after = int(response.headers.get('Retry-After', 60))
        time.sleep(retry_after)

    raise Exception("Rate limit exceeded after retries")
```

### OIDC Issues

#### "Invalid redirect URI"

**Solution:**
1. Match exact URL in provider config
2. Include protocol (`https://`)
3. No trailing slash unless in config

```bash
# Correct
OIDC_REDIRECT_URI=https://sark.example.com/api/auth/oidc/callback

# Wrong
OIDC_REDIRECT_URI=https://sark.example.com/api/auth/oidc/callback/
```

#### "Token validation failed"

**Solutions:**
```bash
# Check issuer
OIDC_ISSUER=https://accounts.google.com

# Verify JWKS accessible
curl https://oauth2.googleapis.com/certs

# Sync system time
sudo ntpdate pool.ntp.org
```

### LDAP Issues

#### "Can't contact LDAP server"

**Solutions:**
```bash
# Test connectivity
telnet ldap.example.com 389

# Test with ldapsearch
ldapsearch -x -H ldap://ldap.example.com:389 -b ""

# Check firewall rules
sudo ufw allow from SARK_IP to LDAP_IP port 389
```

#### "User not found"

**Solutions:**
```bash
# Test search filter
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=sark,ou=service,dc=example,dc=com" \
  -w "password" \
  -b "ou=users,dc=example,dc=com" \
  "(uid=jdoe)"

# Check user base DN
LDAP_USER_BASE_DN=ou=users,dc=example,dc=com

# Try different search filter
LDAP_USER_SEARCH_FILTER=(sAMAccountName={username})  # Active Directory
LDAP_USER_SEARCH_FILTER=(uid={username})             # OpenLDAP
```

### SAML Issues

#### "Invalid SAML Response"

**Solutions:**
```bash
# Check clock skew
sudo ntpdate pool.ntp.org

# Verify certificate
openssl x509 -in idp-cert.pem -text -noout

# Check signature validation
SAML_VALIDATE_SIGNATURE=true
```

#### "Audience mismatch"

**Solution:**
Ensure Entity ID matches exactly:
```bash
# SARK config
SAML_SP_ENTITY_ID=https://sark.example.com

# IdP config (must match exactly)
Audience: https://sark.example.com
```

### Performance Issues

#### Slow authentication

**Solutions:**
```bash
# Increase connection pools
LDAP_POOL_SIZE=20

# Enable Redis connection pooling
REDIS_POOL_SIZE=50

# Check provider health
curl http://localhost:8000/api/auth/health
```

#### High memory usage

**Solutions:**
```bash
# Reduce session timeout
SESSION_TIMEOUT_SECONDS=3600  # 1 hour

# Lower max concurrent sessions
SESSION_MAX_CONCURRENT=3

# Limit connection pools
LDAP_POOL_SIZE=10
```

## Debug Tools

### Enable Verbose Logging

```bash
# .env or environment
LOG_LEVEL=DEBUG
DEBUG=true

# Start SARK
python -m sark
```

### Test Providers

```python
import asyncio
from sark.services.auth.providers import OIDCProvider, LDAPProvider

async def test_providers():
    # Test OIDC
    oidc = OIDCProvider(
        client_id="your-id",
        client_secret="your-secret",
        provider="google"
    )
    oidc_healthy = await oidc.health_check()
    print(f"OIDC: {oidc_healthy}")

    # Test LDAP
    ldap = LDAPProvider(
        server_uri="ldap://ldap.example.com:389",
        bind_dn="cn=sark,ou=service,dc=example,dc=com",
        bind_password="password",
        user_base_dn="ou=users,dc=example,dc=com"
    )
    ldap_healthy = await ldap.health_check()
    print(f"LDAP: {ldap_healthy}")

asyncio.run(test_providers())
```

### Monitor Redis

```bash
# Connect to Redis CLI
redis-cli

# Monitor commands
MONITOR

# Check session keys
KEYS session:*

# Get session data
GET session:YOUR_SESSION_ID

# Check rate limit keys
KEYS rate_limit:*
```

### Check Endpoints

```bash
# List providers
curl http://localhost:8000/api/auth/providers | jq

# Health check
curl http://localhost:8000/api/auth/health | jq

# Current status
curl -H "Cookie: session_id=ID" \
  http://localhost:8000/api/auth/status | jq
```

## Getting Help

### Gather Information

Before requesting help, gather:

1. **SARK version:**
   ```bash
   python -m sark --version
   ```

2. **Configuration** (redact secrets):
   ```bash
   env | grep -E "(OIDC|LDAP|SAML|SESSION|RATE)" | sed 's/=.*/=***/'
   ```

3. **Logs:**
   ```bash
   # Last 100 lines with timestamps
   tail -100 sark.log
   ```

4. **Health check:**
   ```bash
   curl http://localhost:8000/api/auth/health | jq
   ```

### Submit Issue

Include:
- SARK version
- Provider type (OIDC, LDAP, SAML, API Key)
- Redacted configuration
- Error message
- Steps to reproduce
- Relevant logs

## FAQ

**Q: Can I use multiple authentication methods?**
A: Yes, SARK supports multiple providers simultaneously. Users can choose their preferred method.

**Q: How do I migrate users between providers?**
A: Enable both providers, gradually migrate users, then disable old provider.

**Q: Can I customize session timeout per user?**
A: Currently global setting only. Per-user settings planned for future release.

**Q: How do I backup sessions?**
A: Sessions are in Redis. Use Redis backup tools (RDB, AOF).

**Q: What happens if Redis goes down?**
A: Users will be logged out. Enable Redis persistence and clustering for production.

## Next Steps

- [Authentication Guide](./AUTHENTICATION.md)
- [OIDC Setup](./OIDC_SETUP.md)
- [LDAP Setup](./LDAP_SETUP.md)
- [SAML Setup](./SAML_SETUP.md)
- [API Keys](./API_KEYS.md)

## Support

- GitHub Issues: https://github.com/apathy-ca/sark/issues
- Documentation: https://sark.readthedocs.io
- Security Issues: security@example.com
