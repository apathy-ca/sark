# SARK SIEM Integration Guide

This guide consolidates all SIEM integration documentation, including framework overview, Splunk setup, Datadog setup, custom adapters, and performance tuning.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Splunk Integration](#splunk-integration)
4. [Datadog Integration](#datadog-integration)
5. [Custom Adapter Development](#custom-adapter-development)
6. [Performance Tuning](#performance-tuning)
7. [Testing](#testing)

---

## Overview

SARK provides a robust SIEM integration framework for forwarding audit events to external security monitoring systems. The framework supports:

- **Multiple SIEM platforms**: Splunk, Datadog, and custom adapters
- **Batch processing**: Efficient event aggregation (up to 100 events/batch)
- **Retry logic**: Exponential backoff for transient failures
- **Health monitoring**: Built-in health checks and metrics
- **High throughput**: Tested at 10,000+ events/min

### Supported SIEM Systems

| SIEM | Method | Protocol | Performance |
|------|--------|----------|-------------|
| **Splunk** | HEC (HTTP Event Collector) | HTTPS | 10,000+ events/min |
| **Datadog** | Logs API | HTTPS | 10,000+ events/min |
| **Custom** | Implement BaseSIEM | Any | Depends on implementation |

---

## Architecture

```
┌─────────────────┐
│  Audit Events   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BatchHandler    │  Aggregates events
│ (100 events or  │  (size or timeout)
│  5s timeout)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SIEM Adapter   │  Splunk/Datadog/Custom
│  (BaseSIEM)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RetryHandler   │  Exponential backoff
│  (3 attempts)   │  (2s, 4s, 8s...)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  External SIEM  │
└─────────────────┘
```

### Components

1. **BaseSIEM**: Abstract base class for all SIEM implementations
2. **BatchHandler**: Aggregates events for efficient batch forwarding
3. **RetryHandler**: Handles retry logic with exponential backoff
4. **Metrics**: Tracks success rate, latency, and errors

---

## Splunk Integration

See also: [SPLUNK_SETUP.md](./SPLUNK_SETUP.md)

### Configuration

```bash
# .env
SIEM_ENABLED=true
SIEM_TYPE=splunk
SPLUNK_HEC_URL=https://splunk.example.com:8088
SPLUNK_HEC_TOKEN=your-hec-token-here
SPLUNK_INDEX=sark_audit
SPLUNK_SOURCETYPE=sark:audit
SPLUNK_VERIFY_SSL=true
```

### Setup Steps

1. **Create HEC Token in Splunk**

```bash
# Splunk Web UI:
# Settings → Data Inputs → HTTP Event Collector → New Token

# Name: SARK Audit
# Source type: sark:audit
# Index: sark_audit (or main)
```

2. **Test Connection**

```bash
curl -X POST https://splunk.example.com:8088/services/collector/event \
  -H "Authorization: Splunk your-hec-token" \
  -d '{
    "event": {
      "message": "Test event from SARK"
    },
    "index": "sark_audit",
    "sourcetype": "sark:audit"
  }'
```

3. **Configure SARK**

```python
from sark.services.audit.siem import SplunkSIEM, SIEMConfig

config = SIEMConfig(
    enabled=True,
    batch_size=100,
    batch_timeout_seconds=5,
    retry_attempts=3,
)

splunk = SplunkSIEM(
    hec_url="https://splunk.example.com:8088",
    hec_token="your-hec-token",
    index="sark_audit",
    sourcetype="sark:audit",
    config=config,
)

# Send event
await splunk.send_event(audit_event)
```

### Splunk Queries

```spl
# All SARK audit events
index=sark_audit sourcetype=sark:audit

# Server registrations
index=sark_audit event_type="SERVER_REGISTERED"

# Failed authentications
index=sark_audit event_type="AUTH_FAILED"
| stats count by user_email

# High-severity events
index=sark_audit severity="HIGH" OR severity="CRITICAL"
| timechart count by event_type

# Policy denials
index=sark_audit event_type="POLICY_DENIED"
| stats count by user_email, details.reason
```

---

## Datadog Integration

See also: [DATADOG_SETUP.md](./DATADOG_SETUP.md)

### Configuration

```bash
# .env
SIEM_ENABLED=true
SIEM_TYPE=datadog
DATADOG_API_KEY=your-api-key-here
DATADOG_APP_KEY=your-app-key-here
DATADOG_SITE=datadoghq.com
DATADOG_SERVICE=sark
DATADOG_SOURCE=sark-audit
```

### Setup Steps

1. **Get API Keys**

```bash
# Datadog UI:
# Organization Settings → API Keys → New API Key
# Organization Settings → Application Keys → New Application Key
```

2. **Test Connection**

```bash
curl -X POST "https://http-intake.logs.datadoghq.com/api/v2/logs" \
  -H "DD-API-KEY: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ddsource": "sark-audit",
    "ddtags": "env:production,service:sark",
    "message": "Test event from SARK"
  }'
```

3. **Configure SARK**

```python
from sark.services.audit.siem import DatadogSIEM, SIEMConfig

config = SIEMConfig(
    enabled=True,
    batch_size=100,
    batch_timeout_seconds=5,
)

datadog = DatadogSIEM(
    api_key="your-api-key",
    site="datadoghq.com",
    service="sark",
    source="sark-audit",
    config=config,
)

# Send event
await datadog.send_event(audit_event)
```

### Datadog Queries

```
# All SARK audit events
source:sark-audit

# Server registrations
source:sark-audit @event_type:SERVER_REGISTERED

# Failed authentications by user
source:sark-audit @event_type:AUTH_FAILED | group by @user_email

# High-severity events
source:sark-audit @severity:(HIGH OR CRITICAL)

# Policy denials
source:sark-audit @event_type:POLICY_DENIED
```

---

## Custom Adapter Development

### Step 1: Implement BaseSIEM

```python
from sark.services.audit.siem import BaseSIEM, SIEMConfig, SIEMHealth
from sark.models.audit import AuditEvent
import httpx

class CustomSIEM(BaseSIEM):
    """Custom SIEM adapter."""

    def __init__(self, endpoint_url: str, api_key: str, config: SIEMConfig):
        super().__init__(config)
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=config.timeout_seconds,
        )

    async def send_event(self, event: AuditEvent) -> bool:
        """Send single event."""
        try:
            formatted = self.format_event(event)

            response = await self.client.post(
                f"{self.endpoint_url}/events",
                json=formatted,
            )

            response.raise_for_status()
            self._record_success(1)
            return True

        except Exception as e:
            self._record_failure(1, str(e))
            return False

    async def send_batch(self, events: list[AuditEvent]) -> bool:
        """Send batch of events."""
        try:
            formatted_events = [self.format_event(e) for e in events]

            response = await self.client.post(
                f"{self.endpoint_url}/events/batch",
                json={"events": formatted_events},
            )

            response.raise_for_status()
            self._record_success(len(events))
            return True

        except Exception as e:
            self._record_failure(len(events), str(e))
            return False

    async def health_check(self) -> SIEMHealth:
        """Check health."""
        try:
            response = await self.client.get(f"{self.endpoint_url}/health")
            healthy = response.status_code == 200

            return SIEMHealth(
                healthy=healthy,
                latency_ms=response.elapsed.total_seconds() * 1000,
            )

        except Exception as e:
            return SIEMHealth(
                healthy=False,
                error=str(e),
            )

    def format_event(self, event: AuditEvent) -> dict:
        """Format event for custom SIEM."""
        return {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "user_id": str(event.user_id) if event.user_id else None,
            "user_email": event.user_email,
            "server_id": str(event.server_id) if event.server_id else None,
            "details": event.details or {},
        }

    async def close(self):
        """Cleanup."""
        await self.client.aclose()
```

### Step 2: Configure and Use

```python
# Initialize custom SIEM
custom_siem = CustomSIEM(
    endpoint_url="https://siem.example.com",
    api_key="your-api-key",
    config=SIEMConfig(
        enabled=True,
        batch_size=50,
        batch_timeout_seconds=10,
    ),
)

# Send event
await custom_siem.send_event(audit_event)

# Send batch
await custom_siem.send_batch(audit_events)

# Check health
health = await custom_siem.health_check()
print(f"SIEM healthy: {health.healthy}")

# Get metrics
metrics = custom_siem.get_metrics()
print(f"Success rate: {metrics.success_rate}%")
```

### Step 3: Test Adapter

```python
import pytest
from tests.fixtures import sample_audit_event

@pytest.mark.asyncio
async def test_custom_siem_send_event():
    siem = CustomSIEM(...)

    event = sample_audit_event()
    result = await siem.send_event(event)

    assert result is True

@pytest.mark.asyncio
async def test_custom_siem_health_check():
    siem = CustomSIEM(...)

    health = await siem.health_check()

    assert health.healthy is True
    assert health.latency_ms < 100
```

---

## Performance Tuning

See also: [LOAD_TEST_REPORT.md](./LOAD_TEST_REPORT.md)

### Configuration Parameters

```python
config = SIEMConfig(
    enabled=True,

    # Batch configuration
    batch_size=100,              # Max events per batch (1-1000)
    batch_timeout_seconds=5,     # Max wait time for batch

    # Retry configuration
    retry_attempts=3,            # Max retry attempts
    retry_backoff_base=2.0,      # Backoff multiplier (2^n seconds)
    retry_backoff_max=60.0,      # Max backoff delay

    # Connection configuration
    timeout_seconds=30,          # HTTP timeout
    verify_ssl=True,             # SSL verification
)
```

### Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Throughput | 10,000 events/min | 12,000-15,000 |
| Batch latency | <100ms P95 | 50-80ms |
| Success rate | >99% | 99.5-99.9% |
| Retry rate | <1% | 0.1-0.5% |

### Optimization Strategies

#### 1. Batch Size Tuning

```python
# Small batches: Lower latency, higher overhead
config = SIEMConfig(batch_size=10, batch_timeout_seconds=1)

# Large batches: Higher throughput, higher latency
config = SIEMConfig(batch_size=100, batch_timeout_seconds=5)

# Balanced (recommended)
config = SIEMConfig(batch_size=50, batch_timeout_seconds=3)
```

#### 2. Connection Pooling

```python
# Increase connection pool for high throughput
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
    )
)
```

#### 3. Async Processing

```python
# Process events asynchronously
import asyncio

async def forward_events(events: list[AuditEvent]):
    tasks = [siem.send_batch(batch) for batch in batches(events, 100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

#### 4. Monitoring

```python
# Track metrics
metrics = siem.get_metrics()

if metrics.success_rate < 95:
    logger.warning(f"Low SIEM success rate: {metrics.success_rate}%")

if metrics.average_latency_ms > 100:
    logger.warning(f"High SIEM latency: {metrics.average_latency_ms}ms")
```

### Load Testing

```bash
# Run SIEM load test
pytest tests/load_testing/test_siem_load.py

# Test batch performance
pytest tests/load_testing/test_siem_batch_load.py
```

**Load Test Results** (from LOAD_TEST_REPORT.md):
- **Splunk**: 12,500 events/min sustained, 99.8% success rate
- **Datadog**: 14,200 events/min sustained, 99.9% success rate
- **P95 latency**: 65ms (Splunk), 48ms (Datadog)

---

## Testing

### Unit Tests

```python
import pytest
from sark.services.audit.siem import SplunkSIEM, DatadogSIEM

@pytest.mark.asyncio
async def test_splunk_send_event(mock_httpx):
    siem = SplunkSIEM(...)

    event = AuditEvent(...)
    result = await siem.send_event(event)

    assert result is True
    assert mock_httpx.called

@pytest.mark.asyncio
async def test_datadog_batch_send(mock_httpx):
    siem = DatadogSIEM(...)

    events = [AuditEvent(...) for _ in range(10)]
    result = await siem.send_batch(events)

    assert result is True
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_siem_end_to_end():
    # Setup SIEM
    siem = SplunkSIEM(...)

    # Generate audit event
    event = AuditEvent(
        event_type=AuditEventType.SERVER_REGISTERED,
        severity=SeverityLevel.MEDIUM,
        user_email="test@example.com",
        details={"server_name": "test-server"},
    )

    # Send event
    result = await siem.send_event(event)
    assert result is True

    # Verify in SIEM (if possible)
    # ...
```

### Health Checks

```bash
# Check SIEM health via API
curl http://localhost:8000/health/siem

# Response
{
  "splunk": {
    "healthy": true,
    "latency_ms": 45.2
  },
  "datadog": {
    "healthy": true,
    "latency_ms": 32.1
  }
}
```

---

## Troubleshooting

### Connection Errors

**Error**: `httpx.ConnectError: Connection refused`

**Solutions**:
- Verify SIEM endpoint URL
- Check network connectivity
- Verify firewall rules

### Authentication Errors

**Error**: `401 Unauthorized`

**Solutions**:
- Verify API key/token
- Check token permissions
- Regenerate token if expired

### Batch Size Errors

**Error**: `413 Payload Too Large`

**Solutions**:
- Reduce `batch_size`
- Check SIEM payload limits
- Split into smaller batches

### High Latency

**Symptoms**: P95 latency >500ms

**Solutions**:
- Check network latency
- Reduce batch size
- Enable connection pooling
- Scale SIEM infrastructure

---

## Additional Resources

- **Framework Details**: [SIEM_FRAMEWORK.md](./SIEM_FRAMEWORK.md)
- **Splunk Setup**: [SPLUNK_SETUP.md](./SPLUNK_SETUP.md)
- **Datadog Setup**: [DATADOG_SETUP.md](./DATADOG_SETUP.md)
- **Load Test Results**: [LOAD_TEST_REPORT.md](./LOAD_TEST_REPORT.md)
- **API Reference**: [../API_REFERENCE.md](../API_REFERENCE.md)
- **Security Guide**: [../SECURITY.md](../SECURITY.md)
