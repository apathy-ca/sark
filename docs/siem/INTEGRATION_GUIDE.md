# SIEM Integration Guide

Complete step-by-step guide for integrating SARK with Splunk Cloud or Datadog Logs API.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Splunk Cloud Integration](#splunk-cloud-integration)
- [Datadog Integration](#datadog-integration)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Verification](#verification)
- [Next Steps](#next-steps)

## Overview

SARK's SIEM integration forwards audit events to enterprise SIEM platforms for:
- Centralized security monitoring
- Compliance reporting
- Incident response
- Threat detection
- Audit trails

### Supported SIEM Platforms

- **Splunk Cloud** - Industry-leading SIEM via HTTP Event Collector (HEC)
- **Datadog** - Cloud monitoring platform via Logs API

### Key Features

✅ **High throughput** - 10,000+ events/minute
✅ **Reliability** - Circuit breaker, retry logic, fallback logging
✅ **Efficiency** - Automatic batching and gzip compression
✅ **Observability** - Health checks, metrics, and monitoring
✅ **Production-ready** - Error handling, alerting, and recovery

## Prerequisites

### General Requirements

- Python 3.11+
- SARK installed and configured
- Network connectivity to SIEM platform
- SIEM platform account with API access

### Python Dependencies

```bash
pip install httpx structlog pydantic
```

All dependencies are included in SARK's requirements.txt.

### Network Requirements

**Splunk Cloud:**
- Outbound HTTPS (443) to `*.splunkcloud.com` (or your instance domain)
- HEC endpoint typically on port 8088

**Datadog:**
- Outbound HTTPS (443) to `http-intake.logs.datadoghq.com` (or your site)
- Logs API endpoint varies by region

## Splunk Cloud Integration

### Step 1: Sign Up for Splunk Cloud

1. Go to [Splunk Cloud Free Trial](https://www.splunk.com/en_us/download/splunk-cloud.html)
2. Sign up for a free trial account
3. Note your instance URL (e.g., `https://prd-p-xxxxx.splunkcloud.com`)

### Step 2: Create HEC Token

1. Log in to Splunk Web
2. Navigate to: **Settings → Data Inputs → HTTP Event Collector**
3. Click **New Token**
4. Configure token:
   - **Name**: `sark-production`
   - **Source name override**: `sark`
   - **Index**: Create or select index (e.g., `sark_production`)
   - **Sourcetype**: `sark:audit:event`
5. Click **Review** then **Submit**
6. **Copy the token** - you won't see it again!

### Step 3: Create Index (if needed)

1. Navigate to: **Settings → Indexes**
2. Click **New Index**
3. Configure index:
   - **Index Name**: `sark_production`
   - **Index Data Type**: Events
   - **Max Size**: Set appropriate limit
   - **Retention**: Set per compliance requirements
4. Click **Save**

### Step 4: Configure SARK

Create a configuration file or use environment variables:

```python
# config.py
import os
from sark.services.audit.siem import SplunkConfig

splunk_config = SplunkConfig(
    hec_url=os.getenv("SPLUNK_HEC_URL"),
    hec_token=os.getenv("SPLUNK_HEC_TOKEN"),
    index="sark_production",
    sourcetype="sark:audit:event",
    source="sark",
    verify_ssl=True,
)
```

Environment variables:
```bash
export SPLUNK_HEC_URL="https://prd-p-xxxxx.splunkcloud.com:8088/services/collector"
export SPLUNK_HEC_TOKEN="your-hec-token-here"
export SPLUNK_INDEX="sark_production"
```

### Step 5: Test Connection

```python
import asyncio
from sark.services.audit.siem import SplunkConfig, SplunkSIEM

async def test_splunk():
    config = SplunkConfig(
        hec_url="https://prd-p-xxxxx.splunkcloud.com:8088/services/collector",
        hec_token="your-token",
        index="sark_production",
    )

    siem = SplunkSIEM(config)

    # Test health
    health = await siem.health_check()
    print(f"Healthy: {health.healthy}")
    print(f"Latency: {health.latency_ms}ms")

    if not health.healthy:
        print(f"Error: {health.error_message}")
        return

    # Send test event
    from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
    from datetime import UTC, datetime
    from uuid import uuid4

    event = AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.TOOL_INVOKED,
        severity=SeverityLevel.LOW,
        user_email="test@example.com",
        tool_name="test",
        details={"message": "Test event from SARK"},
    )

    result = await siem.send_event(event)
    print(f"Event sent: {result}")
    print(f"Search in Splunk: index={config.index} source=sark")

# Run test
asyncio.run(test_splunk())
```

### Step 6: Verify in Splunk

1. In Splunk Web, go to **Search & Reporting**
2. Run search query:
```spl
index=sark_production source=sark
| head 10
```
3. You should see your test event!

### Step 7: Set Up Dashboards (Optional)

Create a dashboard to monitor SARK events:

```spl
index=sark_production sourcetype=sark:audit:event
| stats count by event_type, severity
| sort -count
```

Common queries:
```spl
# High severity events
index=sark_production severity=high OR severity=critical

# Events by user
index=sark_production
| stats count by user_email
| sort -count

# Tool invocations
index=sark_production event_type=tool_invoked
| stats count by tool_name

# Authorization failures
index=sark_production event_type=authorization_denied
```

## Datadog Integration

### Step 1: Sign Up for Datadog

1. Go to [Datadog Free Trial](https://www.datadoghq.com/free-trial/)
2. Sign up for a free account
3. Select your region (US, EU, etc.)
4. Note your Datadog site (e.g., `datadoghq.com`, `datadoghq.eu`)

### Step 2: Create API Key

1. Log in to Datadog
2. Navigate to: **Organization Settings → API Keys**
3. Click **New Key**
4. Configure key:
   - **Name**: `sark-production`
5. Click **Create Key**
6. **Copy the API key** - store it securely

### Step 3: Create Application Key (Optional)

Required for some advanced features:

1. Navigate to: **Organization Settings → Application Keys**
2. Click **New Key**
3. Configure key:
   - **Name**: `sark-production`
4. Click **Create Key**
5. **Copy the Application key**

### Step 4: Configure SARK

Create a configuration file or use environment variables:

```python
# config.py
import os
from sark.services.audit.siem import DatadogConfig

datadog_config = DatadogConfig(
    api_key=os.getenv("DATADOG_API_KEY"),
    app_key=os.getenv("DATADOG_APP_KEY", ""),
    site=os.getenv("DATADOG_SITE", "datadoghq.com"),
    service="sark",
    environment="production",
    hostname=os.getenv("HOSTNAME"),
    verify_ssl=True,
)
```

Environment variables:
```bash
export DATADOG_API_KEY="your-api-key-here"
export DATADOG_SITE="datadoghq.com"  # or datadoghq.eu, etc.
export DATADOG_SERVICE="sark"
export DATADOG_ENVIRONMENT="production"
```

### Step 5: Test Connection

```python
import asyncio
from sark.services.audit.siem import DatadogConfig, DatadogSIEM

async def test_datadog():
    config = DatadogConfig(
        api_key="your-api-key",
        site="datadoghq.com",
        service="sark",
        environment="test",
    )

    siem = DatadogSIEM(config)

    # Test health
    health = await siem.health_check()
    print(f"Healthy: {health.healthy}")
    print(f"Latency: {health.latency_ms}ms")

    if not health.healthy:
        print(f"Error: {health.error_message}")
        return

    # Send test event
    from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
    from datetime import UTC, datetime
    from uuid import uuid4

    event = AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.TOOL_INVOKED,
        severity=SeverityLevel.LOW,
        user_email="test@example.com",
        tool_name="test",
        details={"message": "Test event from SARK"},
    )

    result = await siem.send_event(event)
    print(f"Event sent: {result}")
    print(f"Search in Datadog: service:{config.service} env:{config.environment}")

# Run test
asyncio.run(test_datadog())
```

### Step 6: Verify in Datadog

1. In Datadog, go to **Logs → Explorer**
2. Search for your events:
```
service:sark env:test
```
3. You should see your test event!

### Step 7: Set Up Dashboards (Optional)

Create a dashboard to monitor SARK events:

1. Go to **Dashboards → New Dashboard**
2. Add widgets:
   - **Timeseries**: Event count over time
   - **Top List**: Events by type
   - **Table**: Recent events

Common queries:
```
# High severity events
service:sark @severity:(high OR critical)

# Events by user
service:sark | group by @user_email

# Tool invocations
service:sark @event_type:tool_invoked

# Authorization failures
service:sark @event_type:authorization_denied
```

## Testing

### Run Integration Tests

SARK includes comprehensive integration tests:

```bash
# Test Splunk integration
export SPLUNK_HEC_URL="https://your-instance.splunkcloud.com:8088/services/collector"
export SPLUNK_HEC_TOKEN="your-token"
export SPLUNK_INDEX="sark_test"

pytest tests/integration/test_splunk_integration.py -v -s

# Test Datadog integration
export DATADOG_API_KEY="your-api-key"
export DATADOG_SITE="datadoghq.com"

pytest tests/integration/test_datadog_integration.py -v -s
```

### Run Load Tests

Validate 10,000 events/minute throughput:

```bash
# Test Splunk load
pytest tests/integration/test_siem_load.py::TestSplunkLoad -v -s

# Test Datadog load
pytest tests/integration/test_siem_load.py::TestDatadogLoad -v -s
```

Expected output:
```
========================================================================
📊 Splunk Load Test Report
========================================================================

⏱️  Timing:
   Duration: 58.42s

📈 Throughput:
   Events sent: 10,000
   Events failed: 0
   Success rate: 100.00%
   Events/second: 171.2
   Events/minute: 10,271 ✅
   Target: 10,000 events in ~60s

📦 Batching:
   Batches sent: 100
   Avg batch size: 100.0

🗜️  Compression:
   Compression rate: 68.2%

⚡ Latency:
   Average: 142.35ms
   P95: 287.21ms

========================================================================
```

### Verify Event Formatting

Test that events are correctly formatted:

```bash
pytest tests/test_audit/test_siem_event_formatting.py -v
```

## Production Deployment

### Full Production Setup

Here's a complete production-ready setup with all optimizations:

```python
import os
import asyncio
from sark.services.audit.siem import (
    SplunkConfig,
    SplunkSIEM,
    SIEMOptimizer,
    SIEMErrorHandler,
    BatchHandler,
    CompressionConfig,
    HealthMonitorConfig,
    CircuitBreakerConfig,
    BatchConfig,
    ErrorAlert,
    high_error_rate_condition,
    critical_error_condition,
)

class ProductionSIEM:
    """Production-ready SIEM integration."""

    def __init__(self):
        """Initialize production SIEM."""
        # Create base SIEM
        splunk_config = SplunkConfig(
            hec_url=os.getenv("SPLUNK_HEC_URL"),
            hec_token=os.getenv("SPLUNK_HEC_TOKEN"),
            index=os.getenv("SPLUNK_INDEX", "sark_production"),
            sourcetype="sark:audit:event",
            source="sark_production",
            verify_ssl=True,
            timeout_seconds=30,
        )
        splunk_siem = SplunkSIEM(splunk_config)

        # Add optimizer
        self.optimizer = SIEMOptimizer(
            siem=splunk_siem,
            name="splunk-production",
            compression_config=CompressionConfig(
                enabled=True,
                min_size_bytes=1024,
                compression_level=6,
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
            ),
        )

        # Add error handler
        self.error_handler = SIEMErrorHandler(
            fallback_log_dir="/var/log/sark/siem_fallback",
            enable_fallback=True,
        )

        # Configure alerts
        def alert_on_critical_error(errors):
            # Send to PagerDuty/Slack/etc.
            print(f"CRITICAL: {len(errors)} critical errors!")

        self.error_handler.add_alert(ErrorAlert(
            name="critical_errors",
            condition=critical_error_condition,
            callback=alert_on_critical_error,
            cooldown_seconds=300,
        ))

        self.error_handler.add_alert(ErrorAlert(
            name="high_error_rate",
            condition=lambda e: high_error_rate_condition(e, threshold=10),
            callback=lambda e: print(f"WARNING: High error rate - {len(e)} errors"),
            cooldown_seconds=600,
        ))

        # Create batch handler
        async def send_batch_safe(events):
            try:
                return await self.optimizer.send_batch(events)
            except Exception as e:
                for event in events:
                    await self.error_handler.handle_error(e, event=event)
                return False

        self.batch_handler = BatchHandler(
            callback=send_batch_safe,
            config=BatchConfig(
                batch_size=100,
                batch_timeout_seconds=5,
            ),
        )

    async def start(self):
        """Start SIEM services."""
        await self.optimizer.start_health_monitoring()
        await self.batch_handler.start()
        print("✅ SIEM integration started")

    async def stop(self):
        """Stop SIEM services."""
        await self.batch_handler.stop(flush=True)
        await self.optimizer.stop_health_monitoring()
        print("✅ SIEM integration stopped")

    async def send_event(self, event):
        """Send event to SIEM.

        Args:
            event: AuditEvent to send
        """
        await self.batch_handler.enqueue(event)

    def get_metrics(self):
        """Get comprehensive metrics."""
        return {
            "optimizer": self.optimizer.get_metrics(),
            "error_handler": self.error_handler.get_metrics(),
        }

# Usage
async def main():
    siem = ProductionSIEM()
    await siem.start()

    try:
        # Send events
        from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
        from datetime import UTC, datetime
        from uuid import uuid4

        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="user@example.com",
            tool_name="kubectl",
        )

        await siem.send_event(event)

        # Wait for batch to flush
        await asyncio.sleep(10)

        # Check metrics
        metrics = siem.get_metrics()
        print(f"Events sent: {metrics['optimizer']['siem']['events_sent']}")

    finally:
        await siem.stop()

# Run
asyncio.run(main())
```

### Deployment Checklist

See [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md) for complete checklist.

**Quick checklist:**
- [ ] Credentials configured securely
- [ ] Network connectivity verified
- [ ] SSL enabled
- [ ] Health check passing
- [ ] Load test successful
- [ ] Monitoring configured
- [ ] Alerts set up
- [ ] Fallback directory created
- [ ] Documentation updated
- [ ] Team notified

## Verification

### Verify Events in SIEM

**Splunk:**
```spl
index=sark_production sourcetype=sark:audit:event earliest=-15m
| stats count by event_type, severity
```

**Datadog:**
```
service:sark env:production
| group by @event_type
```

### Verify Metrics

```python
metrics = optimizer.get_metrics()

# Should see:
assert metrics["siem"]["events_sent"] > 0
assert metrics["siem"]["events_failed"] == 0
assert metrics["health"]["is_healthy"] is True
assert metrics["circuit_breaker"]["state"] == "closed"
assert 0 < metrics["compression"]["compression_rate"] < 1
```

### Verify Health

```python
health = await siem.health_check()

# Should see:
assert health.healthy is True
assert health.latency_ms < 1000  # < 1 second
assert health.error_message is None
```

## Next Steps

### 1. Configure Monitoring

Set up monitoring dashboards and alerts:
- Event throughput
- Error rates
- Latency
- Circuit breaker state
- Fallback file growth

See [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md#monitoring) for details.

### 2. Set Up Alerting

Configure alerts for:
- High error rate
- Circuit breaker open
- Health check failures
- High latency

See [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md#recommended-alerts) for details.

### 3. Create Dashboards

Build SIEM dashboards for:
- Security monitoring
- Compliance reporting
- Audit trails
- Incident investigation

### 4. Document Runbooks

Create operational runbooks for:
- Troubleshooting common issues
- Replaying fallback logs
- Credential rotation
- Incident response

### 5. Train Team

Ensure team members know:
- How to query SIEM
- How to respond to alerts
- How to troubleshoot issues
- Escalation procedures

## Troubleshooting

### Connection Issues

**Problem:** `ConnectionError: Network unreachable`

**Solution:**
1. Verify network connectivity: `ping your-instance.splunkcloud.com`
2. Check firewall rules
3. Verify URL is correct
4. Test with curl:
```bash
curl -k https://your-instance.splunkcloud.com:8088/services/collector/health
```

### Authentication Errors

**Problem:** `403 Forbidden` or `401 Unauthorized`

**Solution:**
1. Verify token/API key is correct
2. Check token hasn't expired
3. Verify token has correct permissions
4. Try regenerating token

### Events Not Appearing

**Problem:** Events sent successfully but not visible in SIEM

**Solution:**
1. Wait 1-2 minutes (indexing delay)
2. Verify index/service name
3. Check retention policies
4. Verify search query is correct
5. Check SIEM platform status

### High Latency

**Problem:** P95 latency > 2 seconds

**Solution:**
1. Check SIEM platform performance
2. Check network latency
3. Reduce batch size
4. Increase timeout
5. Consider regional endpoint

### Fallback Files Growing

**Problem:** Fallback files accumulating

**Solution:**
1. Fix underlying SIEM connectivity issue
2. Replay fallback files once fixed
3. Monitor circuit breaker state
4. Check error metrics

See [ERROR_HANDLING.md](ERROR_HANDLING.md) for comprehensive troubleshooting.

## Additional Resources

- [Production Configuration Guide](PRODUCTION_CONFIG.md)
- [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md)
- [Error Handling Guide](ERROR_HANDLING.md)
- [Splunk HEC Documentation](https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector)
- [Datadog Logs API Documentation](https://docs.datadoghq.com/api/latest/logs/)

## Support

If you encounter issues:

1. Check this documentation
2. Review troubleshooting section
3. Check application logs
4. Check SIEM platform status
5. Contact team support

---

**Last Updated:** 2024-11-22
**Version:** 1.0
**Maintained By:** SIEM Integration Team
