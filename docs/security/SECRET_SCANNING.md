# Secret Scanning

## Overview

SARK's secret scanning feature automatically detects and redacts accidentally exposed secrets in tool responses before they are returned to clients. This prevents credential leakage through MCP tool outputs and protects sensitive information from being inadvertently exposed.

## Features

- **Pattern-based detection** for 10+ secret types
- **Automatic redaction** with `[REDACTED]` placeholder
- **Security alerts** sent to SIEM when secrets are detected
- **High performance** with <1ms scanning overhead (p95)
- **Zero secret exposure** in responses
- **Feature flag** for gradual rollout

## Supported Secret Types

The scanner detects the following types of secrets:

| Secret Type | Pattern | Example |
|------------|---------|---------|
| OpenAI API Keys | `sk-[a-zA-Z0-9_-]{20,}` | `sk-1234567890abcdefghijklmnopqrst` |
| GitHub Tokens | `gh[ps]_[a-zA-Z0-9]{20,}` | `ghp_1234567890abcdefghijklmnopqrstuvwxyz` |
| AWS Access Keys | `AKIA[0-9A-Z]{16}` | `AKIAIOSFODNN7EXAMPLE` |
| Private Keys | `-----BEGIN.*PRIVATE KEY-----` | RSA/EC/DSA private keys |
| JWT Tokens | `eyJ[a-zA-Z0-9_-]+\.eyJ...` | JSON Web Tokens |
| Database URLs | `postgres://user:pass@host/db` | Connection strings |
| Generic API Keys | `api_key: [a-zA-Z0-9_-]{32,}` | Generic API keys |
| Slack Tokens | `xox[baprs]-...` | Slack OAuth tokens |
| Stripe Keys | `sk_live_...` or `pk_live_...` | Stripe API keys |
| High-Entropy Secrets | Base64 strings >40 chars, entropy >4.5 | Random secrets |

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Gateway                          │
│  ┌──────────────┐                                       │
│  │ Tool Response │                                      │
│  └──────┬────────┘                                      │
│         │                                                │
│         v                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ POST /gateway/scan-response                      │  │
│  │ (Gateway API key required)                       │  │
│  └──────┬───────────────────────────────────────────┘  │
└─────────┼──────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────┐
│                    SARK API Server                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Gateway Router                                   │  │
│  │  1. Validate Gateway API key                     │  │
│  │  2. Check feature flag                           │  │
│  │  3. Scan response data                           │  │
│  └──────┬───────────────────────────────────────────┘  │
│         │                                                │
│         v                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ SecretScanner                                    │  │
│  │  - Pattern matching (regex)                      │  │
│  │  - High-entropy detection (Shannon entropy)      │  │
│  │  - Redaction (structure-preserving)              │  │
│  └──────┬───────────────────────────────────────────┘  │
│         │                                                │
│         v                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ If secrets found:                                │  │
│  │  - Log security violation (CRITICAL)             │  │
│  │  - Send alert to SIEM                            │  │
│  │  - Return redacted response                      │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Flow

1. **Gateway receives tool response** from MCP server
2. **Gateway calls** `/gateway/scan-response` endpoint with response data
3. **SARK validates** Gateway API key
4. **Feature flag check**: If `FEATURE_SECRET_SCANNING=false`, return original data
5. **Scan for secrets** using pattern matching and entropy analysis
6. **Redact secrets** if found, preserving data structure
7. **Log security alert** if secrets detected (CRITICAL severity, forwarded to SIEM)
8. **Return response** with redacted data to Gateway
9. **Gateway returns** safe response to client

## Configuration

### Feature Flag

Enable or disable secret scanning via environment variable:

```bash
FEATURE_SECRET_SCANNING=true  # Default: true
```

### Gateway API Key

The scanning endpoint requires a Gateway API key:

```bash
GATEWAY_API_KEY=your-secret-key-here
```

### SIEM Integration

Secret detection alerts are automatically forwarded to configured SIEM systems (Splunk, Datadog) when secrets are found. No additional configuration required - uses existing audit service configuration.

## API Reference

### POST /gateway/scan-response

Scan tool response for secrets and redact if found.

**Authentication**: Gateway API key (in `X-Gateway-Api-Key` header)

**Request Body**:

```json
{
  "response_data": {
    "result": "Database connection: postgres://user:password@localhost/db"
  },
  "server_name": "postgres-mcp",
  "tool_name": "get_connection_info",
  "user_id": "user_123",
  "gateway_request_id": "req_abc456"
}
```

**Response**:

```json
{
  "redacted_data": {
    "result": "Database connection: [REDACTED]"
  },
  "secrets_found": 1,
  "secret_types": ["database_url"],
  "alert_sent": true,
  "scan_duration_ms": 0.42
}
```

## Usage Examples

### Python SDK

```python
from sark.security import SecretScanner

# Initialize scanner
scanner = SecretScanner()

# Scan text for secrets
findings = scanner.scan("API key: sk-1234567890abcdefghijklmnopqrst")
print(f"Found {len(findings)} secrets")
# Output: Found 1 secrets

# Redact secrets from data
data = {
    "config": {
        "api_key": "sk-1234567890abcdefghijklmnopqrst",
        "safe_value": "normal data"
    }
}
redacted_data, findings = scanner.redact(data)
print(redacted_data)
# Output: {'config': {'api_key': '[REDACTED]', 'safe_value': 'normal data'}}

# Custom redaction placeholder
scanner = SecretScanner(redaction_placeholder="***HIDDEN***")
```

### cURL Example

```bash
curl -X POST https://sark.example.com/api/v1/gateway/scan-response \
  -H "X-Gateway-Api-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "response_data": {"result": "sk-1234567890abcdefghijklmnopqrst"},
    "server_name": "test-server",
    "tool_name": "test-tool",
    "gateway_request_id": "req_123"
  }'
```

## Security Alerts

When secrets are detected, a CRITICAL severity audit event is logged:

```json
{
  "event_type": "SECURITY_VIOLATION",
  "severity": "CRITICAL",
  "user_id": "user_123",
  "server_name": "postgres-mcp",
  "tool_name": "get_connection_info",
  "decision": "redacted",
  "details": {
    "violation_type": "secret_detected",
    "secret_count": 1,
    "secrets": [
      {
        "type": "database_url",
        "line_number": 1,
        "length": 42
      }
    ],
    "gateway_request_id": "req_abc456"
  }
}
```

This event is automatically forwarded to SIEM for security monitoring.

## Performance

- **Scanning overhead**: <1ms (p95) for typical payloads
- **Redaction overhead**: <2ms (p95) for typical payloads
- **Memory efficient**: Streaming pattern matching, no full document buffering
- **Concurrent safe**: Scanner instances are thread-safe

### Benchmarks

| Operation | Payload Size | Duration (p95) |
|-----------|--------------|----------------|
| Scan | 1KB text | 0.3ms |
| Scan | 10KB text | 0.8ms |
| Redact | 100-row dict | 1.2ms |
| Redact | Nested JSON (5 levels) | 1.5ms |

## Best Practices

### For Developers

1. **Always enable in production**: `FEATURE_SECRET_SCANNING=true`
2. **Monitor SIEM alerts**: Review secret detection events regularly
3. **Test with realistic secrets**: Use test patterns in development
4. **Don't log original secrets**: Scanner prevents exposure, but don't circumvent it
5. **Rotate exposed secrets**: If detected, rotate immediately

### For Security Teams

1. **Alert on detection**: Set up alerts for `SECRET_DETECTED` events
2. **Investigate promptly**: Secrets in tool outputs may indicate configuration issues
3. **Track patterns**: Monitor which tools/servers expose secrets most frequently
4. **Update patterns**: Add custom patterns via scanner configuration
5. **Review false positives**: High-entropy detection may flag non-secrets

## Testing

### Unit Tests

Run the secret scanner test suite:

```bash
pytest tests/unit/security/test_secret_scanner.py -v
```

**Test Coverage**:
- All 10+ secret pattern types
- Redaction correctness
- Nested data structures (dicts, lists, tuples)
- Performance requirements (<1ms)
- Edge cases (empty data, unicode, special chars)
- High-entropy detection

### Integration Testing

Test the Gateway endpoint:

```bash
pytest tests/integration/gateway/test_secret_scanning.py -v
```

## Troubleshooting

### Secrets not being detected

**Symptoms**: Secrets pass through without redaction

**Possible causes**:
1. Feature flag disabled: Check `FEATURE_SECRET_SCANNING=true`
2. Pattern mismatch: Secret format doesn't match regex patterns
3. Too short: Secrets must meet minimum length requirements

**Solutions**:
- Enable feature flag
- Review patterns in `src/sark/security/secret_scanner.py`
- Add custom patterns for your secret types

### False positives

**Symptoms**: Non-secrets being flagged as high-entropy

**Possible causes**:
1. High-entropy detection threshold too low
2. Base64-encoded data being flagged

**Solutions**:
- Adjust entropy threshold in `_scan_high_entropy()` method
- Disable high-entropy detection for specific data types
- Add exclusion patterns

### Performance degradation

**Symptoms**: Scanning takes >1ms consistently

**Possible causes**:
1. Very large payloads (>100KB)
2. Many nested structures
3. Complex regex backtracking

**Solutions**:
- Implement payload size limits
- Optimize patterns to reduce backtracking
- Cache compiled regex patterns (already done)

## Compliance

Secret scanning helps meet compliance requirements for:

- **PCI DSS**: Protect cardholder data (database credentials, API keys)
- **GDPR**: Prevent exposure of authentication credentials
- **SOC 2**: Access control and data protection
- **HIPAA**: Safeguard authentication mechanisms
- **ISO 27001**: Information security controls

## References

- **Implementation Plan**: `docs/v1.3.0/IMPLEMENTATION_PLAN.md` (Stream 4)
- **TruffleHog Patterns**: https://github.com/trufflesecurity/truffleHog
- **OWASP Secret Management**: https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password

## Change Log

### v1.3.0 (Week 6)
- Initial implementation of secret scanning
- 10+ secret type patterns
- Gateway integration
- SIEM alerting
- Performance optimization (<1ms overhead)
- Comprehensive test coverage

## Support

For issues or questions:
- **Security Issues**: Report to security@example.com
- **Bug Reports**: GitHub Issues
- **Feature Requests**: Product team
