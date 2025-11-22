# API Keys Guide

Guide to managing API keys for programmatic access to SARK.

## Overview

API keys provide secure, programmatic access for:
- Service accounts
- Automation tools
- Third-party integrations
- CI/CD pipelines

### Features

- Scoped permissions
- Per-key rate limits
- Usage tracking
- Key rotation
- Audit logging

## Quick Start

### Create API Key

```bash
# Via API (requires authentication)
curl -X POST http://localhost:8000/api/admin/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Pipeline",
    "scopes": ["read:servers", "write:servers"],
    "rate_limit": 5000
  }'

# Response
{
  "key": "sark_1234567890abcdef",
  "name": "CI/CD Pipeline",
  "scopes": ["read:servers", "write:servers"],
  "created_at": "2025-11-22T20:00:00Z"
}
```

**⚠️ Save the key immediately - it's shown only once!**

### Use API Key

```bash
# Include in X-API-Key header
curl http://localhost:8000/api/servers \
  -H "X-API-Key: sark_1234567890abcdef"
```

## Permissions & Scopes

### Available Scopes

| Scope | Description |
|-------|-------------|
| `read:servers` | List and view MCP servers |
| `write:servers` | Create, update, delete servers |
| `read:policies` | View policies |
| `write:policies` | Create, update policies |
| `read:audit` | View audit logs |
| `admin` | Full access to all resources |

### Scope Examples

```json
// Read-only access
{
  "scopes": ["read:servers", "read:policies"]
}

// Service account for automation
{
  "scopes": ["read:servers", "write:servers"]
}

// Admin key (use sparingly)
{
  "scopes": ["admin"]
}
```

## Rate Limiting

API keys have dedicated rate limits:

```bash
# Default: 1000 requests/hour
RATE_LIMIT_PER_API_KEY=1000

# Per-key custom limit
{
  "name": "High-volume service",
  "rate_limit": 10000
}
```

Rate limit headers:
```http
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9523
X-RateLimit-Reset: 1732310400
```

## Managing API Keys

### List Keys

```bash
curl http://localhost:8000/api/admin/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Revoke Key

```bash
curl -X DELETE http://localhost:8000/api/admin/api-keys/KEY_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Rotate Keys

1. Create new key with same scopes
2. Update services to use new key
3. Monitor usage to ensure migration
4. Revoke old key

**Recommended: Rotate keys every 90 days**

## Security Best Practices

1. **Limit Scopes**
   - Grant minimum required permissions
   - Avoid `admin` scope unless necessary

2. **Secure Storage**
   - Never commit keys to git
   - Use environment variables or secrets manager
   - Encrypt keys at rest

3. **Monitor Usage**
   - Enable audit logging
   - Alert on unusual patterns
   - Track rate limit violations

4. **Rotate Regularly**
   - Set rotation schedule (90 days recommended)
   - Automate rotation where possible

5. **Revoke Compromised Keys**
   - Immediately revoke if exposed
   - Create new key
   - Update affected services

## Usage Tracking

### View Usage

```bash
curl http://localhost:8000/api/admin/api-keys/KEY_ID/usage \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "requests_today": 1234,
  "requests_this_hour": 45,
  "rate_limit": 5000,
  "last_used": "2025-11-22T19:55:00Z"
}
```

### Audit Logs

All API key usage is logged:

```bash
curl http://localhost:8000/api/audit/events?api_key_id=KEY_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Examples

### Python

```python
import httpx

API_KEY = "sark_1234567890abcdef"

client = httpx.Client(
    headers={"X-API-Key": API_KEY}
)

# List servers
response = client.get("https://sark.example.com/api/servers")
servers = response.json()
```

### cURL

```bash
#!/bin/bash
API_KEY="sark_1234567890abcdef"

curl -H "X-API-Key: $API_KEY" \
  https://sark.example.com/api/servers
```

### JavaScript/TypeScript

```typescript
const API_KEY = 'sark_1234567890abcdef';

const response = await fetch('https://sark.example.com/api/servers', {
  headers: {
    'X-API-Key': API_KEY
  }
});

const servers = await response.json();
```

## Troubleshooting

### "Invalid API key"

- Check key is correct (no extra spaces)
- Verify key hasn't been revoked
- Ensure using `X-API-Key` header

### "Insufficient permissions"

- Check key scopes include required permission
- Verify endpoint requires permission in scopes

### Rate limit exceeded

- Check `X-RateLimit-*` headers
- Wait for reset or request limit increase
- Implement exponential backoff

## Next Steps

- [Authentication Guide](./AUTHENTICATION.md)
- [Rate Limiting](./AUTHENTICATION.md#rate-limiting)
- [Troubleshooting](./TROUBLESHOOTING.md)
