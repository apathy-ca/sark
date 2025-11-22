# Splunk Integration Setup Guide

This guide explains how to configure SARK to forward audit events to Splunk using the HTTP Event Collector (HEC).

## Prerequisites

- Splunk Enterprise or Splunk Cloud instance
- Splunk HEC token with appropriate permissions
- Network connectivity from SARK to Splunk HEC endpoint

## Splunk Configuration

### 1. Enable HTTP Event Collector

1. Log in to Splunk Web
2. Navigate to **Settings** > **Data Inputs**
3. Click **HTTP Event Collector**
4. Click **Global Settings**
5. Ensure **All Tokens** is set to **Enabled**
6. Click **Save**

### 2. Create HEC Token

1. Click **New Token**
2. Enter a name (e.g., "SARK Audit Events")
3. (Optional) Set Source name override to `sark`
4. Click **Next**
5. Configure input settings:
   - **Source type**: Select **Automatic** or create custom `sark:audit:event`
   - **Index**: Select or create index `sark_audit`
   - **Default Index**: `main` (or your preferred index)
6. Click **Review** and then **Submit**
7. Copy the generated HEC token (you'll need this for SARK configuration)

### 3. Verify HEC Endpoint

Default HEC endpoint: `https://<splunk-host>:8088/services/collector`

Test the endpoint:
```bash
curl -k https://<splunk-host>:8088/services/collector/health \
  -H "Authorization: Splunk <your-hec-token>"
```

Expected response:
```json
{
  "text": "HEC is healthy",
  "code": 17
}
```

## SARK Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Splunk SIEM Configuration
SPLUNK_ENABLED=true
SPLUNK_HEC_URL=https://<splunk-host>:8088/services/collector
SPLUNK_HEC_TOKEN=<your-hec-token>
SPLUNK_INDEX=sark_audit
SPLUNK_SOURCETYPE=sark:audit:event
SPLUNK_SOURCE=sark
SPLUNK_HOST=<sark-hostname>  # Optional
SPLUNK_VERIFY_SSL=true
SPLUNK_BATCH_SIZE=100
SPLUNK_BATCH_TIMEOUT_SECONDS=5
SPLUNK_RETRY_ATTEMPTS=3
```

### Python Configuration

Alternatively, configure programmatically:

```python
from sark.services.audit.siem import SplunkConfig, SplunkSIEM

config = SplunkConfig(
    hec_url="https://splunk.example.com:8088/services/collector",
    hec_token="your-hec-token-here",
    index="sark_audit",
    sourcetype="sark:audit:event",
    source="sark",
    host="sark-prod-01",  # Optional
    verify_ssl=True,
    batch_size=100,
    batch_timeout_seconds=5,
    retry_attempts=3,
)

splunk = SplunkSIEM(config)

# Health check
health = await splunk.health_check()
print(f"Splunk healthy: {health.healthy}")

# Send event
await splunk.send_event(audit_event)
```

## Integration with Batch and Retry Handlers

For production deployments, use batch and retry handlers:

```python
from sark.services.audit.siem import (
    SplunkConfig,
    SplunkSIEM,
    BatchConfig,
    BatchHandler,
    RetryConfig,
    RetryHandler,
)

# Configure Splunk
splunk_config = SplunkConfig(
    hec_url="https://splunk.example.com:8088/services/collector",
    hec_token="your-hec-token",
)
splunk = SplunkSIEM(splunk_config)

# Configure retry handler
retry_config = RetryConfig(
    max_attempts=3,
    backoff_base=2.0,
    backoff_max=60.0,
)
retry_handler = RetryHandler(retry_config)

# Wrap with retry logic
async def send_batch_with_retry(events):
    return await retry_handler.execute_with_retry_and_timeout(
        operation=lambda: splunk.send_batch(events),
        timeout_seconds=30.0,
        operation_name="splunk_batch_send",
    )

# Configure batch handler
batch_config = BatchConfig(
    batch_size=100,
    batch_timeout_seconds=5.0,
)
batch_handler = BatchHandler(
    send_batch_callback=send_batch_with_retry,
    config=batch_config,
)

# Start processing
await batch_handler.start()

# Enqueue events
for event in audit_events:
    await batch_handler.enqueue(event)

# Graceful shutdown
await batch_handler.stop(flush=True)
```

## Event Format

SARK sends events to Splunk in the following format:

```json
{
  "time": 1700000000.123,
  "source": "sark",
  "sourcetype": "sark:audit:event",
  "index": "sark_audit",
  "host": "sark-prod-01",
  "event": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-22T15:30:00.000000Z",
    "event_type": "server_registered",
    "severity": "high",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_email": "user@example.com",
    "server_id": "789e0123-e45b-67d8-a901-234567890abc",
    "tool_name": "database_query",
    "decision": "allow",
    "policy_id": "456e7890-e12b-34d5-a678-901234567def",
    "ip_address": "192.168.1.100",
    "user_agent": "SARK-Client/1.0",
    "request_id": "req-abc123",
    "details": {
      "server_name": "production-db-01",
      "tags": ["production", "database"]
    }
  }
}
```

## Splunk Search Queries

### View Recent Audit Events

```spl
index=sark_audit sourcetype="sark:audit:event"
| table _time event.event_type event.severity event.user_email event.decision
| sort - _time
```

### Security Violations

```spl
index=sark_audit sourcetype="sark:audit:event" event.severity=critical
| table _time event.event_type event.user_email event.details
```

### Authorization Denials

```spl
index=sark_audit sourcetype="sark:audit:event" event.decision=deny
| stats count by event.user_email, event.tool_name
| sort - count
```

### Server Registration Activity

```spl
index=sark_audit sourcetype="sark:audit:event" event.event_type=server_registered
| timechart span=1h count by event.severity
```

## Troubleshooting

### Events Not Appearing in Splunk

1. **Check HEC health:**
   ```bash
   curl -k https://<splunk-host>:8088/services/collector/health \
     -H "Authorization: Splunk <your-hec-token>"
   ```

2. **Verify SARK configuration:**
   ```python
   health = await splunk.health_check()
   print(health.healthy, health.error_message)
   ```

3. **Check SARK logs:**
   ```bash
   grep "splunk" /var/log/sark/sark.log
   ```

4. **Verify index exists:**
   - In Splunk Web, go to **Settings** > **Indexes**
   - Ensure `sark_audit` index exists

### SSL/TLS Certificate Errors

If using self-signed certificates:

```bash
# Option 1: Disable SSL verification (NOT recommended for production)
SPLUNK_VERIFY_SSL=false

# Option 2: Add certificate to trust store
# Copy Splunk CA certificate to SARK host
# Update system trust store
```

### High Latency

1. **Increase batch size:**
   ```bash
   SPLUNK_BATCH_SIZE=500
   ```

2. **Adjust timeout:**
   ```bash
   SPLUNK_BATCH_TIMEOUT_SECONDS=10
   ```

3. **Check Splunk HEC performance:**
   - Monitor HEC queue size
   - Check indexer performance
   - Review network latency

### Authentication Failures

1. **Verify token:**
   ```bash
   curl -k https://<splunk-host>:8088/services/collector \
     -H "Authorization: Splunk <your-hec-token>" \
     -d '{"event": "test"}'
   ```

2. **Check token permissions:**
   - Ensure token is enabled
   - Verify index permissions
   - Check token expiration

## Monitoring

### Prometheus Metrics

SARK exposes Prometheus metrics for Splunk integration:

```promql
# Events sent successfully
siem_events_sent_total{siem_type="splunk"}

# Events failed
siem_events_failed_total{siem_type="splunk"}

# Send latency
siem_send_latency_seconds{siem_type="splunk", operation="batch"}

# Health status
siem_health_status{siem_type="splunk"}
```

### Example Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Splunk Event Throughput",
      "targets": [
        {
          "expr": "rate(siem_events_sent_total{siem_type=\"splunk\"}[5m])"
        }
      ]
    },
    {
      "title": "Splunk Send Latency (p95)",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, siem_send_latency_seconds{siem_type=\"splunk\"})"
        }
      ]
    },
    {
      "title": "Splunk Error Rate",
      "targets": [
        {
          "expr": "rate(siem_events_failed_total{siem_type=\"splunk\"}[5m])"
        }
      ]
    }
  ]
}
```

## Best Practices

1. **Use dedicated index:** Create a separate index for SARK audit events
2. **Set appropriate retention:** Configure index retention based on compliance requirements
3. **Monitor HEC health:** Set up alerts for HEC connectivity issues
4. **Enable SSL/TLS:** Always use encrypted connections in production
5. **Rotate tokens:** Periodically rotate HEC tokens
6. **Size batches appropriately:** Balance throughput vs latency (100-500 events recommended)
7. **Use retry logic:** Configure retries to handle transient failures
8. **Monitor metrics:** Track success rate, latency, and error rates

## Security Considerations

1. **Token Security:**
   - Store HEC token in secure secrets manager (e.g., HashiCorp Vault)
   - Never commit tokens to version control
   - Use environment variables or secret mounts

2. **Network Security:**
   - Use private network connections when possible
   - Configure firewall rules to restrict HEC access
   - Enable SSL/TLS certificate verification

3. **Access Control:**
   - Limit HEC token to specific indexes
   - Use role-based access control in Splunk
   - Audit HEC token usage

## Production Deployment Checklist

- [ ] HEC enabled in Splunk
- [ ] HEC token created with appropriate permissions
- [ ] Index created (`sark_audit`)
- [ ] SARK configuration updated with HEC token
- [ ] SSL/TLS certificate trust configured
- [ ] Batch and retry handlers configured
- [ ] Health checks passing
- [ ] Metrics monitoring configured
- [ ] Alerts configured for failures
- [ ] Documentation updated with Splunk URLs
- [ ] Security review completed
- [ ] Load testing completed

## Support

For issues or questions:
- SARK Documentation: `/docs/siem/SIEM_FRAMEWORK.md`
- Splunk HEC Documentation: https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector
- GitHub Issues: https://github.com/apathy-ca/sark/issues
