# SIEM Production Configuration Guide

This guide covers production deployment, configuration, and operational best practices for SARK's SIEM integration.

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Configuration Reference](#configuration-reference)
- [Security Best Practices](#security-best-practices)
- [Deployment Checklist](#deployment-checklist)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)

## Quick Start

### Splunk Cloud Production Setup

```bash
# 1. Set required environment variables
export SPLUNK_HEC_URL="https://your-instance.splunkcloud.com:8088/services/collector"
export SPLUNK_HEC_TOKEN="your-production-hec-token"
export SPLUNK_INDEX="sark_production"

# 2. Set optional configuration
export SPLUNK_SOURCETYPE="sark:audit:event"
export SPLUNK_SOURCE="sark_production"
export SPLUNK_VERIFY_SSL="true"

# 3. Test connectivity
python -c "
from sark.services.audit.siem import SplunkConfig, SplunkSIEM
import asyncio

config = SplunkConfig(
    hec_url='$SPLUNK_HEC_URL',
    hec_token='$SPLUNK_HEC_TOKEN',
    index='$SPLUNK_INDEX'
)
siem = SplunkSIEM(config)
health = asyncio.run(siem.health_check())
print(f'Healthy: {health.healthy}, Latency: {health.latency_ms}ms')
"
```

### Datadog Production Setup

```bash
# 1. Set required environment variables
export DATADOG_API_KEY="your-production-api-key"
export DATADOG_SITE="datadoghq.com"  # or datadoghq.eu, us3.datadoghq.com, etc.

# 2. Set optional configuration
export DATADOG_SERVICE="sark"
export DATADOG_ENVIRONMENT="production"
export DATADOG_HOSTNAME="$(hostname)"

# 3. Test connectivity
python -c "
from sark.services.audit.siem import DatadogConfig, DatadogSIEM
import asyncio

config = DatadogConfig(
    api_key='$DATADOG_API_KEY',
    site='$DATADOG_SITE',
    service='$DATADOG_SERVICE',
    environment='$DATADOG_ENVIRONMENT'
)
siem = DatadogSIEM(config)
health = asyncio.run(siem.health_check())
print(f'Healthy: {health.healthy}, Latency: {health.latency_ms}ms')
"
```

## Environment Variables

### Splunk Cloud

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPLUNK_HEC_URL` | Yes | - | Splunk HEC endpoint URL |
| `SPLUNK_HEC_TOKEN` | Yes | - | Splunk HEC authentication token |
| `SPLUNK_INDEX` | No | `main` | Target index for events |
| `SPLUNK_SOURCETYPE` | No | `sark:audit:event` | Event sourcetype |
| `SPLUNK_SOURCE` | No | `sark` | Event source identifier |
| `SPLUNK_VERIFY_SSL` | No | `true` | Enable SSL verification |
| `SPLUNK_TIMEOUT_SECONDS` | No | `30` | Request timeout |

### Datadog

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATADOG_API_KEY` | Yes | - | Datadog API key |
| `DATADOG_APP_KEY` | No | - | Datadog Application key (optional) |
| `DATADOG_SITE` | No | `datadoghq.com` | Datadog site (US, EU, etc.) |
| `DATADOG_SERVICE` | No | `sark` | Service name for tagging |
| `DATADOG_ENVIRONMENT` | No | `production` | Environment tag |
| `DATADOG_HOSTNAME` | No | - | Hostname for log attribution |
| `DATADOG_VERIFY_SSL` | No | `true` | Enable SSL verification |
| `DATADOG_TIMEOUT_SECONDS` | No | `30` | Request timeout |

### Optimization Features

| Variable | Default | Description |
|----------|---------|-------------|
| `SIEM_BATCH_SIZE` | `100` | Events per batch |
| `SIEM_BATCH_TIMEOUT_SECONDS` | `5` | Max wait time before sending batch |
| `SIEM_COMPRESSION_ENABLED` | `true` | Enable gzip compression |
| `SIEM_COMPRESSION_MIN_BYTES` | `1024` | Min payload size for compression |
| `SIEM_COMPRESSION_LEVEL` | `6` | Gzip compression level (1-9) |
| `SIEM_CIRCUIT_BREAKER_ENABLED` | `true` | Enable circuit breaker |
| `SIEM_CIRCUIT_FAILURE_THRESHOLD` | `5` | Failures before opening circuit |
| `SIEM_CIRCUIT_RECOVERY_TIMEOUT` | `60` | Seconds before attempting recovery |
| `SIEM_HEALTH_CHECK_ENABLED` | `true` | Enable health monitoring |
| `SIEM_HEALTH_CHECK_INTERVAL` | `30` | Seconds between health checks |
| `SIEM_FALLBACK_ENABLED` | `true` | Enable fallback file logging |
| `SIEM_FALLBACK_DIR` | `/var/log/sark/siem_fallback` | Fallback log directory |

## Configuration Reference

### Recommended Production Configuration

#### Splunk

```python
from sark.services.audit.siem import (
    SplunkConfig,
    SplunkSIEM,
    SIEMOptimizer,
    SIEMErrorHandler,
    CompressionConfig,
    HealthMonitorConfig,
    CircuitBreakerConfig,
    BatchConfig,
    BatchHandler,
)

# Base SIEM configuration
splunk_config = SplunkConfig(
    hec_url=os.getenv("SPLUNK_HEC_URL"),
    hec_token=os.getenv("SPLUNK_HEC_TOKEN"),
    index=os.getenv("SPLUNK_INDEX", "sark_production"),
    sourcetype="sark:audit:event",
    source="sark_production",
    verify_ssl=True,
    timeout_seconds=30,
)

# Create base SIEM
splunk_siem = SplunkSIEM(splunk_config)

# Wrap with optimizer for performance
optimizer = SIEMOptimizer(
    siem=splunk_siem,
    name="splunk-production",
    compression_config=CompressionConfig(
        enabled=True,
        min_size_bytes=1024,  # Only compress payloads > 1KB
        compression_level=6,   # Balanced compression
    ),
    health_config=HealthMonitorConfig(
        enabled=True,
        check_interval_seconds=30,
        failure_threshold=3,
    ),
    circuit_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=2,
        timeout=30,
    ),
)

# Create error handler with fallback
error_handler = SIEMErrorHandler(
    fallback_log_dir="/var/log/sark/siem_fallback",
    max_error_history=100,
    enable_fallback=True,
)

# Add production alerts
from sark.services.audit.siem import (
    ErrorAlert,
    high_error_rate_condition,
    critical_error_condition,
    auth_failure_condition,
)

def alert_pagerduty(errors):
    """Send alert to PagerDuty."""
    # Implementation depends on your PagerDuty setup
    pass

error_handler.add_alert(ErrorAlert(
    name="critical_errors",
    condition=critical_error_condition,
    callback=alert_pagerduty,
    cooldown_seconds=300,  # 5 minutes
))

error_handler.add_alert(ErrorAlert(
    name="high_error_rate",
    condition=lambda e: high_error_rate_condition(e, threshold=10, window_seconds=60),
    callback=alert_pagerduty,
    cooldown_seconds=600,  # 10 minutes
))

# Create batch handler
async def send_batch_with_error_handling(events):
    try:
        return await optimizer.send_batch(events)
    except Exception as e:
        # Handle errors with fallback
        for event in events:
            await error_handler.handle_error(e, event=event)
        return False

batch_handler = BatchHandler(
    callback=send_batch_with_error_handling,
    config=BatchConfig(
        batch_size=100,
        batch_timeout_seconds=5,
    ),
)

# Start services
await optimizer.start_health_monitoring()
await batch_handler.start()

# Send events
await batch_handler.enqueue(event)

# Shutdown
await batch_handler.stop(flush=True)
await optimizer.stop_health_monitoring()
```

#### Datadog

```python
from sark.services.audit.siem import (
    DatadogConfig,
    DatadogSIEM,
    SIEMOptimizer,
    SIEMErrorHandler,
    CompressionConfig,
    HealthMonitorConfig,
    CircuitBreakerConfig,
    BatchConfig,
    BatchHandler,
)

# Base SIEM configuration
datadog_config = DatadogConfig(
    api_key=os.getenv("DATADOG_API_KEY"),
    site=os.getenv("DATADOG_SITE", "datadoghq.com"),
    service="sark",
    environment="production",
    hostname=os.getenv("HOSTNAME"),
    verify_ssl=True,
    timeout_seconds=30,
)

# Create base SIEM
datadog_siem = DatadogSIEM(datadog_config)

# Configuration is similar to Splunk (see above)
# ... same optimizer, error handler, and batch handler setup
```

## Security Best Practices

### 1. Credential Management

**DO:**
- Store credentials in secure secret management systems (AWS Secrets Manager, HashiCorp Vault, etc.)
- Use environment variables for deployment
- Rotate credentials regularly (quarterly minimum)
- Use least-privilege tokens/keys

**DON'T:**
- Hard-code credentials in source code
- Commit credentials to version control
- Share production credentials via insecure channels
- Use the same credentials across environments

### 2. Network Security

**DO:**
- Enable SSL/TLS verification in production (`verify_ssl=True`)
- Use private networks when possible
- Implement network segmentation
- Whitelist source IPs in SIEM platform

**DON'T:**
- Disable SSL verification in production
- Expose SIEM credentials to untrusted networks
- Use unencrypted connections

### 3. Access Control

**DO:**
- Limit access to SIEM dashboards/data to authorized personnel
- Implement role-based access control (RBAC)
- Audit access to SIEM data
- Use separate credentials for different environments

**DON'T:**
- Share SIEM access credentials
- Grant broad read/write access unnecessarily

### 4. Data Protection

**DO:**
- Redact sensitive data before sending to SIEM
- Implement data retention policies
- Comply with data residency requirements
- Review what data is being logged

**DON'T:**
- Log passwords, API keys, or other secrets
- Log personally identifiable information (PII) unnecessarily
- Violate data protection regulations (GDPR, CCPA, etc.)

## Deployment Checklist

### Pre-Deployment

- [ ] Splunk/Datadog account provisioned
- [ ] HEC token/API key created with appropriate permissions
- [ ] Index/service configured in SIEM platform
- [ ] Credentials stored in secret management system
- [ ] Network connectivity verified
- [ ] SSL certificates validated
- [ ] Test environment validated
- [ ] Load testing completed successfully
- [ ] Monitoring and alerting configured
- [ ] Documentation reviewed and updated
- [ ] Runbook created for common issues
- [ ] On-call rotation established

### Deployment

- [ ] Environment variables configured
- [ ] Application deployed with SIEM integration
- [ ] Health check passing
- [ ] Test event sent successfully
- [ ] Batch handler started
- [ ] Health monitoring started
- [ ] Fallback directory created with proper permissions
- [ ] Logs aggregation configured
- [ ] Metrics collection enabled
- [ ] Alerts configured and tested

### Post-Deployment

- [ ] Events flowing to SIEM
- [ ] No errors in application logs
- [ ] SIEM dashboards showing data
- [ ] Latency within acceptable range (< 1s)
- [ ] Throughput meeting requirements (10k events/min)
- [ ] Circuit breaker in closed state
- [ ] No fallback files being created
- [ ] Error rate < 1%
- [ ] Compression working (check metrics)
- [ ] Team notified of deployment
- [ ] Monitoring dashboards reviewed

### 30-Day Review

- [ ] Review event volume and trends
- [ ] Analyze error patterns
- [ ] Optimize batch size if needed
- [ ] Review and tune compression settings
- [ ] Check fallback file growth
- [ ] Review circuit breaker metrics
- [ ] Validate alert configuration
- [ ] Review costs/usage
- [ ] Update documentation based on lessons learned

## Monitoring

### Key Metrics to Monitor

#### Application Metrics

```python
# Get comprehensive metrics
metrics = optimizer.get_metrics()

# Key metrics to track:
- metrics["siem"]["events_sent"]           # Total events sent
- metrics["siem"]["events_failed"]          # Total failures
- metrics["siem"]["avg_latency_ms"]         # Average latency
- metrics["health"]["is_healthy"]           # Current health status
- metrics["circuit_breaker"]["state"]       # Circuit state
- metrics["compression"]["compression_rate"] # Compression effectiveness
- metrics["batching"]["avg_batch_size"]     # Batching efficiency
```

#### Prometheus Metrics (if enabled)

```
# Event throughput
siem_events_sent_total{siem="splunk"}
siem_events_failed_total{siem="splunk"}

# Latency
siem_send_duration_seconds{siem="splunk"}

# Health
siem_health_check_success{siem="splunk"}
siem_health_check_latency_seconds{siem="splunk"}

# Circuit breaker
siem_circuit_breaker_state{siem="splunk"} # 0=closed, 1=open, 2=half_open

# Compression
siem_compression_ratio{siem="splunk"}
siem_bytes_saved_total{siem="splunk"}

# Errors
siem_error_total{category="network", severity="medium"}
```

### Recommended Alerts

1. **High Error Rate**
   - Threshold: > 5% error rate over 5 minutes
   - Action: Investigate immediately, check SIEM platform status

2. **Circuit Breaker Open**
   - Threshold: Circuit open for > 5 minutes
   - Action: Verify SIEM platform health, check credentials

3. **High Latency**
   - Threshold: P95 latency > 2 seconds
   - Action: Check network, SIEM platform performance

4. **Fallback Files Growing**
   - Threshold: Fallback files > 1GB
   - Action: Investigate why events aren't sending, replay events

5. **Health Check Failing**
   - Threshold: 3 consecutive failures
   - Action: Verify connectivity, credentials, SIEM status

## Troubleshooting

### Events Not Appearing in SIEM

**Check:**
1. Health check status: `await siem.health_check()`
2. Application logs for errors
3. SIEM credentials are valid
4. Network connectivity
5. Index/service configuration in SIEM platform
6. Fallback files for unsent events

**Commands:**
```bash
# Check health
python -c "from sark.services.audit.siem import SplunkSIEM, SplunkConfig; import asyncio; import os; print(asyncio.run(SplunkSIEM(SplunkConfig(hec_url=os.getenv('SPLUNK_HEC_URL'), hec_token=os.getenv('SPLUNK_HEC_TOKEN'), index=os.getenv('SPLUNK_INDEX'))).health_check()))"

# Check fallback files
ls -lh /var/log/sark/siem_fallback/

# Check application metrics
python -c "from your_app import optimizer; print(optimizer.get_metrics())"
```

### High Error Rate

**Potential Causes:**
- SIEM platform degradation
- Network issues
- Rate limiting
- Invalid credentials
- Malformed events

**Actions:**
1. Check error metrics: `error_handler.get_metrics()`
2. Review recent errors: `error_handler.get_recent_errors(10)`
3. Verify SIEM platform status page
4. Check circuit breaker state
5. Review fallback logs

### Circuit Breaker Stuck Open

**Potential Causes:**
- Persistent SIEM platform issues
- Invalid credentials
- Network firewall rules
- High failure threshold

**Actions:**
1. Fix underlying issue
2. Verify health check passes
3. Wait for recovery timeout
4. Or manually reset: `optimizer.circuit_breaker.reset()`

### Fallback Files Growing

**Potential Causes:**
- SIEM platform downtime
- Network connectivity issues
- Circuit breaker open
- Persistent failures

**Actions:**
1. Fix underlying issue
2. Replay fallback files:
```python
import json
from pathlib import Path

fallback_dir = Path("/var/log/sark/siem_fallback")
for log_file in fallback_dir.glob("*.log"):
    with open(log_file) as f:
        for line in f:
            event_data = json.loads(line)
            # Recreate event and send
            # event = AuditEvent(**event_data)
            # await siem.send_event(event)
```

## Performance Tuning

### Batch Size Optimization

```python
from sark.services.audit.siem import get_optimal_batch_size, estimate_event_size

# Estimate your average event size
sample_event = create_typical_event()
avg_size = estimate_event_size(sample_event)

# Calculate optimal batch size (target 100KB batches)
optimal_size = get_optimal_batch_size(avg_size, target_batch_size_kb=100)
print(f"Recommended batch size: {optimal_size}")

# Update configuration
batch_config = BatchConfig(
    batch_size=optimal_size,
    batch_timeout_seconds=5,
)
```

### Compression Tuning

```python
# Monitor compression effectiveness
metrics = optimizer.get_metrics()
compression_rate = metrics["compression"]["compression_rate"]
bytes_saved = metrics["compression"]["total_bytes_saved"]

# Adjust minimum size threshold if needed
if compression_rate < 0.1:  # Less than 10% compression
    # Events might be too small or incompressible
    # Increase min_size_bytes to avoid overhead
    compression_config = CompressionConfig(
        enabled=True,
        min_size_bytes=2048,  # Increased from 1024
    )

# Adjust compression level for speed vs ratio
# Level 1: Fastest, lowest compression
# Level 9: Slowest, highest compression
# Level 6: Balanced (recommended)
```

### Timeout Tuning

```python
# Monitor latencies
metrics = optimizer.get_metrics()
p95_latency = metrics["siem"]["p95_latency_ms"]

# If P95 latency is close to timeout, increase timeout
if p95_latency > 25000:  # > 25s (close to 30s default)
    config = SplunkConfig(
        ...,
        timeout_seconds=60,  # Increased from 30
    )
```

## Cost Optimization

### Splunk

- Use selective indexing (only index necessary fields)
- Set appropriate retention policies
- Consider using summary indexing for older data
- Monitor daily ingest volume
- Right-size your Splunk Cloud instance

### Datadog

- Tag events appropriately for filtering
- Use log sampling for high-volume low-value events
- Set retention policies per environment
- Monitor log volume in Datadog UI
- Consider excluding verbose debug events

## Compliance Considerations

### Data Retention

- Configure retention policies per compliance requirements
- Document what data is being logged
- Implement data deletion procedures
- Regular compliance audits

### Audit Logging

- Log all access to SIEM data
- Monitor configuration changes
- Track credential usage
- Maintain audit trail for compliance

### Privacy

- Redact PII before sending to SIEM
- Implement data minimization
- Document data flows
- Comply with GDPR, CCPA, etc.

## Support

### Getting Help

1. Check this documentation
2. Review troubleshooting guide
3. Check application logs
4. Review SIEM platform status page
5. Contact SIEM platform support
6. Escalate to on-call engineer

### Escalation Path

1. On-call engineer
2. Engineering team lead
3. Security team (for security-related issues)
4. SIEM vendor support

---

**Last Updated:** 2024-11-22
**Version:** 1.0
**Maintained By:** SIEM Integration Team
