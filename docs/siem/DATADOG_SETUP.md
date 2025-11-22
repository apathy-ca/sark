# Datadog Integration Setup Guide

This guide explains how to configure SARK to forward audit events to Datadog using the Logs API.

## Prerequisites

- Datadog account (Free tier or paid plan)
- Datadog API key
- Network connectivity from SARK to Datadog Logs API
- (Optional) Datadog Application key for additional features

## Datadog Configuration

### 1. Obtain Datadog API Key

1. Log in to your Datadog account
2. Navigate to **Organization Settings** > **API Keys**
3. Create a new API key or copy an existing one
4. **Important**: Keep this API key secure - treat it like a password

### 2. (Optional) Create Application Key

For additional features:
1. Navigate to **Organization Settings** > **Application Keys**
2. Create a new application key
3. Note: Application key is optional for log forwarding

### 3. Determine Your Datadog Site

Datadog operates in multiple regions. Determine your site:

| Region | Site | Logs API Endpoint |
|--------|------|-------------------|
| US1 (default) | `datadoghq.com` | `https://http-intake.logs.datadoghq.com` |
| US3 | `us3.datadoghq.com` | `https://http-intake.logs.us3.datadoghq.com` |
| US5 | `us5.datadoghq.com` | `https://http-intake.logs.us5.datadoghq.com` |
| EU | `datadoghq.eu` | `https://http-intake.logs.datadoghq.eu` |
| AP1 | `ap1.datadoghq.com` | `https://http-intake.logs.ap1.datadoghq.com` |
| US1-FED | `ddog-gov.com` | `https://http-intake.logs.ddog-gov.com` |

Check your Datadog URL to determine your site:
- If you access Datadog at `app.datadoghq.com` → use `datadoghq.com`
- If you access Datadog at `app.datadoghq.eu` → use `datadoghq.eu`

### 4. Test API Connectivity

Verify your API key and connectivity:

```bash
# Replace with your actual API key and site
DD_API_KEY="your-api-key-here"
DD_SITE="datadoghq.com"

curl -X POST "https://http-intake.logs.${DD_SITE}/api/v2/logs" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '[{
    "ddsource": "test",
    "ddtags": "env:test",
    "message": "Test log from SARK setup",
    "service": "sark-test"
  }]'
```

Expected response: `HTTP 202 Accepted`

## SARK Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Datadog SIEM Configuration
DATADOG_ENABLED=true
DATADOG_API_KEY=<your-api-key>
DATADOG_APP_KEY=<your-app-key>  # Optional
DATADOG_SITE=datadoghq.com
DATADOG_SERVICE=sark
DATADOG_ENVIRONMENT=production  # or staging, development
DATADOG_HOSTNAME=<your-hostname>  # Optional, defaults to system hostname
DATADOG_VERIFY_SSL=true
DATADOG_BATCH_SIZE=100
DATADOG_BATCH_TIMEOUT_SECONDS=5
DATADOG_RETRY_ATTEMPTS=3
```

### Python Configuration

Alternatively, configure programmatically:

```python
from sark.services.audit.siem import DatadogConfig, DatadogSIEM

config = DatadogConfig(
    api_key="your-api-key-here",
    app_key="your-app-key-here",  # Optional
    site="datadoghq.com",
    service="sark",
    environment="production",
    hostname="sark-prod-01",  # Optional
    verify_ssl=True,
    batch_size=100,
    batch_timeout_seconds=5,
    retry_attempts=3,
)

datadog = DatadogSIEM(config)

# Health check
health = await datadog.health_check()
print(f"Datadog healthy: {health.healthy}")

# Send event
await datadog.send_event(audit_event)
```

## Integration with Batch and Retry Handlers

For production deployments, use batch and retry handlers:

```python
from sark.services.audit.siem import (
    DatadogConfig,
    DatadogSIEM,
    BatchConfig,
    BatchHandler,
    RetryConfig,
    RetryHandler,
)

# Configure Datadog
datadog_config = DatadogConfig(
    api_key="your-api-key",
    site="datadoghq.com",
    service="sark",
    environment="production",
)
datadog = DatadogSIEM(datadog_config)

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
        operation=lambda: datadog.send_batch(events),
        timeout_seconds=30.0,
        operation_name="datadog_batch_send",
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

SARK sends events to Datadog in the following format:

```json
{
  "ddsource": "sark",
  "ddtags": "env:production,service:sark,event_type:server_registered,severity:high,user_role:admin",
  "service": "sark",
  "hostname": "sark-prod-01",
  "timestamp": 1700000000123,
  "message": "SARK audit event: server_registered",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "server_registered",
  "severity": "high",
  "user_email": "user@example.com",
  "decision": "allow",
  "sark": {
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
      "user_role": "admin"
    }
  }
}
```

## Tags

SARK automatically applies the following tags to all events:

| Tag | Description | Example |
|-----|-------------|---------|
| `env` | Environment name | `env:production` |
| `service` | Service name | `service:sark` |
| `event_type` | Type of audit event | `event_type:server_registered` |
| `severity` | Event severity level | `severity:critical` |
| `user_role` | User role (if available) | `user_role:developer` |

## Searching Logs in Datadog

### View Recent Audit Events

```
service:sark
```

### Filter by Severity

```
service:sark severity:critical
```

### Filter by Event Type

```
service:sark event_type:authorization_denied
```

### Filter by User

```
service:sark @user_email:"user@example.com"
```

### Security Violations

```
service:sark event_type:security_violation
```

### Authorization Denials

```
service:sark @decision:deny
```

### Complex Query Example

```
service:sark env:production severity:(high OR critical) @decision:deny
```

## Creating Datadog Monitors

### 1. High-Severity Events Monitor

1. Navigate to **Monitors** > **New Monitor**
2. Select **Logs**
3. Define the search query:
   ```
   service:sark severity:critical
   ```
4. Set alert conditions:
   - Alert threshold: > 5 events in 5 minutes
5. Configure notifications (email, Slack, PagerDuty)
6. Name: "SARK Critical Security Events"

### 2. Authorization Denial Monitor

1. Create new Logs monitor
2. Query:
   ```
   service:sark @decision:deny
   ```
3. Alert threshold: > 10 denials in 1 minute
4. Name: "SARK High Authorization Denial Rate"

### 3. Service Health Monitor

1. Create new Logs monitor
2. Query:
   ```
   service:sark event_type:security_violation
   ```
3. Alert threshold: > 1 event in 5 minutes
4. Name: "SARK Security Violations Detected"

## Dashboards

### Creating a SARK Security Dashboard

1. Navigate to **Dashboards** > **New Dashboard**
2. Add the following widgets:

#### Widget 1: Event Count Timeline
- **Type**: Timeseries
- **Query**: `service:sark`
- **Group by**: `event_type`

#### Widget 2: Severity Distribution
- **Type**: Pie Chart
- **Query**: `service:sark`
- **Group by**: `severity`

#### Widget 3: Top Users
- **Type**: Top List
- **Query**: `service:sark`
- **Group by**: `@user_email`
- **Sort by**: Count (descending)

#### Widget 4: Authorization Denials
- **Type**: Query Value
- **Query**: `service:sark @decision:deny`
- **Visualization**: Display count with red color

#### Widget 5: Event Types Over Time
- **Type**: Heatmap
- **Query**: `service:sark`
- **Group by**: `event_type`, `hour`

## Log Pipelines (Optional)

Create a custom pipeline for SARK logs:

1. Navigate to **Logs** > **Pipelines**
2. Create new pipeline
3. Filter: `service:sark`
4. Add processors:

### Processor 1: Grok Parser
Extract additional fields from the message:
```
rule %{word:action} %{data:resource}
```

### Processor 2: Category Processor
Categorize events:
- Source: `event_type`
- Categories:
  - `authentication` → `user_login`, `user_logout`
  - `authorization` → `authorization_allowed`, `authorization_denied`
  - `security` → `security_violation`

### Processor 3: Status Remapper
Map severity to status:
- `critical` → `error`
- `high` → `warning`
- `medium` → `info`
- `low` → `debug`

## Troubleshooting

### Events Not Appearing in Datadog

1. **Check API key:**
   ```python
   health = await datadog.health_check()
   print(health.healthy, health.error_message)
   ```

2. **Verify site configuration:**
   - Ensure `DATADOG_SITE` matches your Datadog account region
   - Check the logs URL in health check details

3. **Check SARK logs:**
   ```bash
   grep "datadog" /var/log/sark/sark.log
   ```

4. **Test with curl:**
   ```bash
   curl -X POST "https://http-intake.logs.datadoghq.com/api/v2/logs" \
     -H "DD-API-KEY: your-key" \
     -H "Content-Type: application/json" \
     -d '[{"message":"test","ddsource":"sark"}]'
   ```

### API Key Authentication Errors

**Error**: `HTTP 403 Forbidden`

**Solutions**:
1. Verify API key is correct
2. Check API key has not been revoked
3. Ensure API key permissions include log submission

### High Latency

1. **Check Datadog status:**
   - Visit [status.datadoghq.com](https://status.datadoghq.com)

2. **Increase batch size:**
   ```bash
   DATADOG_BATCH_SIZE=500
   ```

3. **Adjust timeout:**
   ```bash
   DATADOG_BATCH_TIMEOUT_SECONDS=10
   ```

4. **Check network connectivity:**
   ```bash
   ping http-intake.logs.datadoghq.com
   ```

### Missing Tags

1. **Verify tags in event:**
   ```python
   event = datadog._format_datadog_event(audit_event)
   print(event['ddtags'])
   ```

2. **Check user_role in details:**
   - The `user_role` tag is only added if present in `event.details`

## Monitoring

### Prometheus Metrics

SARK exposes Prometheus metrics for Datadog integration:

```promql
# Events sent successfully
siem_events_sent_total{siem_type="datadog"}

# Events failed
siem_events_failed_total{siem_type="datadog"}

# Send latency
siem_send_latency_seconds{siem_type="datadog", operation="batch"}

# Health status
siem_health_status{siem_type="datadog"}
```

### Grafana Dashboard

Example dashboard configuration:

```json
{
  "panels": [
    {
      "title": "Datadog Event Throughput",
      "targets": [
        {
          "expr": "rate(siem_events_sent_total{siem_type=\"datadog\"}[5m])"
        }
      ]
    },
    {
      "title": "Datadog Send Latency (p95)",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, siem_send_latency_seconds{siem_type=\"datadog\"})"
        }
      ]
    },
    {
      "title": "Datadog Error Rate",
      "targets": [
        {
          "expr": "rate(siem_events_failed_total{siem_type=\"datadog\"}[5m])"
        }
      ]
    }
  ]
}
```

## Best Practices

1. **Use appropriate service names:** Set `DATADOG_SERVICE` to a descriptive name
2. **Tag consistently:** Use standard environment tags (dev, staging, production)
3. **Monitor API usage:** Track your Datadog log ingestion against your plan limits
4. **Set up alerts:** Create monitors for critical events
5. **Use log pipelines:** Process and enrich logs in Datadog
6. **Optimize batch size:** Balance throughput vs latency (100-1000 events recommended)
7. **Enable compression:** Datadog automatically compresses log payloads
8. **Implement retention policies:** Configure log retention based on compliance needs

## Security Considerations

1. **API Key Security:**
   - Store API key in secure secrets manager (e.g., HashiCorp Vault)
   - Never commit API keys to version control
   - Rotate API keys periodically
   - Use environment variables or secret mounts

2. **Network Security:**
   - Use HTTPS (SSL/TLS) for all communications (default)
   - Consider IP allowlisting if available in your Datadog plan
   - Use private network connections when possible

3. **Access Control:**
   - Limit API key permissions to log submission only
   - Use role-based access control in Datadog
   - Audit API key usage regularly

4. **Data Privacy:**
   - Review sensitive data in logs
   - Use log scrubbing if needed
   - Configure PII masking in Datadog pipelines

## Cost Optimization

1. **Monitor ingestion volume:**
   - Track logs ingested per day
   - Set up alerts for unusual spikes

2. **Use sampling for high-volume events:**
   ```python
   import random
   if event.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL) or random.random() < 0.1:
       await datadog.send_event(event)
   ```

3. **Filter low-value logs:**
   - Only send high/critical severity events
   - Sample informational events

4. **Optimize retention:**
   - Use shorter retention for low-severity logs
   - Archive important logs to S3 for long-term storage

## Production Deployment Checklist

- [ ] Datadog account created
- [ ] API key obtained and secured
- [ ] Correct Datadog site determined
- [ ] SARK configuration updated with API key
- [ ] Health check passing
- [ ] Test events visible in Datadog
- [ ] Tags applied correctly
- [ ] Batch and retry handlers configured
- [ ] Monitors created for critical events
- [ ] Dashboard created
- [ ] Alerts configured
- [ ] Team notifications set up
- [ ] Documentation updated with Datadog URLs
- [ ] Security review completed
- [ ] Cost monitoring configured

## Support

For issues or questions:
- SARK Documentation: `/docs/siem/SIEM_FRAMEWORK.md`
- Datadog Logs API Documentation: https://docs.datadoghq.com/api/latest/logs/
- Datadog Status: https://status.datadoghq.com
- GitHub Issues: https://github.com/apathy-ca/sark/issues
