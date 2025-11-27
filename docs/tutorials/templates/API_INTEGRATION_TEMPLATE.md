# API Integration: [Integration Name]

**API Type:** [REST | GraphQL | gRPC | WebSocket]
**Difficulty:** Intermediate
**Estimated Time:** [30-60] minutes
**API Version:** [vX.X]

---

## Overview

This tutorial shows you how to integrate [System/Service] with SARK's API.

### What You'll Build

A working integration that:
- [ ] [Capability 1]
- [ ] [Capability 2]
- [ ] [Capability 3]
- [ ] [Capability 4]

### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| [GET] | [/api/v1/endpoint] | [Description] |
| [POST] | [/api/v1/endpoint] | [Description] |
| [PUT] | [/api/v1/endpoint] | [Description] |
| [DELETE] | [/api/v1/endpoint] | [Description] |

---

## Prerequisites

### Required Access

- [ ] SARK API URL: `https://sark.your-domain.com`
- [ ] API Key with `[permission1, permission2]` permissions
- [ ] [Service name] account with [permissions]

### Required Tools

```bash
# Install required tools
curl --version  # For API testing
jq --version    # For JSON processing
[other tools]

# Optional but recommended
httpie --version  # Better HTTP client
postman          # API testing GUI
```

### Environment Setup

```bash
# Set environment variables
export SARK_API_URL="https://sark.your-domain.com"
export SARK_API_KEY="your-api-key-here"
export [SERVICE]_API_KEY="your-service-key-here"

# Verify connectivity
curl -H "Authorization: Bearer ${SARK_API_KEY}" \
  ${SARK_API_URL}/api/v1/health
```

---

## Authentication

### Option 1: API Key (Recommended for Services)

```bash
# Set up API key
export SARK_API_KEY="sk_live_[your-key-here]"

# Test authentication
curl -X GET "${SARK_API_URL}/api/v1/auth/verify" \
  -H "Authorization: Bearer ${SARK_API_KEY}"
```

### Option 2: OAuth 2.0 / OIDC (For User Sessions)

```bash
# Get OAuth token
[auth commands]
```

---

## Step 1: Create Integration Configuration

**Goal:** Set up the integration credentials and configuration

```bash
# Create configuration file
cat > integration-config.json <<'EOF'
{
  "name": "[Integration Name]",
  "type": "[integration-type]",
  "credentials": {
    "api_key": "${SERVICE_API_KEY}",
    "endpoint": "https://api.service.com"
  },
  "settings": {
    "sync_interval": 300,
    "batch_size": 100
  }
}
EOF
```

**Register the integration:**

```bash
curl -X POST "${SARK_API_URL}/api/v1/integrations" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @integration-config.json
```

**Expected Response:**

```json
{
  "id": "int_abc123",
  "name": "[Integration Name]",
  "status": "active",
  "created_at": "2025-11-27T12:00:00Z"
}
```

---

## Step 2: [Core Integration Step]

**Goal:** [What this step accomplishes]

```bash
# [Explanation of the API call]
curl -X POST "${SARK_API_URL}/api/v1/[endpoint]" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "param1": "value1",
    "param2": "value2"
  }'
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "id": "abc123",
    "result": "value"
  }
}
```

**Explanation:**
- **param1:** [Description of parameter]
- **param2:** [Description of parameter]

---

## Step 3: Implement Webhook Handler (Optional)

**Goal:** Receive real-time events from SARK

### 3.1: Create Webhook Endpoint

```python
# Example webhook handler (Python/Flask)
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

@app.route('/webhooks/sark', methods=['POST'])
def handle_sark_webhook():
    # Verify webhook signature
    signature = request.headers.get('X-SARK-Signature')
    body = request.get_data()

    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if signature != expected_sig:
        return jsonify({'error': 'Invalid signature'}), 401

    # Process webhook event
    event = request.json
    event_type = event['type']

    if event_type == 'server.registered':
        handle_server_registered(event['data'])
    elif event_type == 'tool.invoked':
        handle_tool_invoked(event['data'])

    return jsonify({'status': 'processed'}), 200

if __name__ == '__main__':
    app.run(port=5000)
```

### 3.2: Register Webhook

```bash
curl -X POST "${SARK_API_URL}/api/v1/webhooks" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhooks/sark",
    "events": ["server.registered", "tool.invoked"],
    "secret": "your-webhook-secret"
  }'
```

---

## Step 4: Test the Integration

### 4.1: Manual Testing

```bash
# Test data sync
curl -X POST "${SARK_API_URL}/api/v1/integrations/${INTEGRATION_ID}/sync" \
  -H "Authorization: Bearer ${SARK_API_KEY}"

# Check sync status
curl -X GET "${SARK_API_URL}/api/v1/integrations/${INTEGRATION_ID}/status" \
  -H "Authorization: Bearer ${SARK_API_KEY}"
```

### 4.2: Automated Testing

```bash
# Run integration tests
./scripts/test-integration.sh [integration-name]
```

---

## Error Handling

### Common API Errors

| Status Code | Error | Solution |
|-------------|-------|----------|
| 401 | Unauthorized | Check API key validity |
| 403 | Forbidden | Verify API key permissions |
| 429 | Rate Limited | Implement backoff strategy |
| 500 | Server Error | Check SARK logs, retry with exponential backoff |

### Rate Limiting

```javascript
// Example rate limiting with exponential backoff
async function callSarkApiWithRetry(endpoint, options, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(endpoint, options);

      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After') || 2 ** attempt;
        await sleep(retryAfter * 1000);
        continue;
      }

      return response;
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
      await sleep(2 ** attempt * 1000);
    }
  }
}
```

---

## Monitoring and Logging

### Enable API Logging

```bash
# Configure detailed API logging
curl -X PATCH "${SARK_API_URL}/api/v1/integrations/${INTEGRATION_ID}" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "logging": {
        "level": "debug",
        "include_request_body": true,
        "include_response_body": true
      }
    }
  }'
```

### View Integration Logs

```bash
# Fetch integration logs
curl -X GET "${SARK_API_URL}/api/v1/integrations/${INTEGRATION_ID}/logs" \
  -H "Authorization: Bearer ${SARK_API_KEY}" \
  | jq '.'
```

---

## Production Checklist

Before deploying to production:

- [ ] **Security**
  - [ ] Store API keys in secrets manager (e.g., Vault, AWS Secrets Manager)
  - [ ] Implement webhook signature verification
  - [ ] Enable TLS/SSL for all API calls
  - [ ] Rotate API keys regularly

- [ ] **Reliability**
  - [ ] Implement exponential backoff for retries
  - [ ] Add timeout handling (recommended: 30s)
  - [ ] Set up health check monitoring
  - [ ] Configure error alerting

- [ ] **Performance**
  - [ ] Implement request rate limiting
  - [ ] Use connection pooling
  - [ ] Cache frequently accessed data
  - [ ] Batch API calls when possible

- [ ] **Monitoring**
  - [ ] Set up API metrics dashboard
  - [ ] Configure alerts for errors/failures
  - [ ] Track API call volume and latency
  - [ ] Monitor rate limit usage

---

## Complete Example

Here's a complete integration example in [Language]:

```[language]
[Full working example code]
```

**Usage:**

```bash
# Run the integration
[command to run example]
```

---

## API Reference

### Full Endpoint Documentation

See the complete API reference: [API_REFERENCE.md](../../API_REFERENCE.md)

### SDK Libraries

- **Python:** `pip install sark-api-client`
- **JavaScript:** `npm install @sark/api-client`
- **Go:** `go get github.com/your-org/sark-go`
- **Java:** Maven/Gradle coordinates

---

## Next Steps

- **Advanced Integration:** [Link to advanced topics]
- **Webhooks Guide:** [Link to webhook documentation]
- **API Best Practices:** [Link to best practices]
- **Production Deployment:** [Link to deployment guide]

---

## Support

- **API Documentation:** [Link]
- **API Status:** https://status.sark.io
- **Community Forum:** https://community.sark.io
- **GitHub Issues:** https://github.com/your-org/sark/issues

---

**Tutorial Info:**
- **Last Updated:** [Date]
- **API Version:** vX.X
- **Author:** [Name]
