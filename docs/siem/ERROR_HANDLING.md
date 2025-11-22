# SIEM Error Handling Guide

Comprehensive error handling for SIEM integrations with classification, graceful degradation, and alerting.

## Overview

The SIEM error handler provides production-ready reliability features:

1. **Error Classification**: Automatic categorization of errors by type and severity
2. **Recovery Strategies**: Intelligent recovery based on error type
3. **Fallback Logging**: Graceful degradation to file logging when SIEM unavailable
4. **Error Alerting**: Configurable alerts for critical conditions
5. **Metrics Tracking**: Comprehensive error statistics and history

## Components

### Error Classification

Errors are automatically classified by **category** and **severity**:

**Categories:**
- `NETWORK`: Network connectivity issues
- `AUTHENTICATION`: Auth/authorization failures
- `RATE_LIMIT`: Rate limiting (429, too many requests)
- `VALIDATION`: Data validation errors
- `TIMEOUT`: Request timeouts
- `SIEM_ERROR`: SIEM-specific errors
- `UNKNOWN`: Unclassified errors

**Severities:**
- `LOW`: Transient errors, will retry automatically
- `MEDIUM`: Recoverable errors, may need attention
- `HIGH`: Serious errors, requires investigation
- `CRITICAL`: Service degraded, immediate action needed

### Recovery Strategies

Based on error classification, the handler recommends recovery strategies:

- `RETRY`: Retry with exponential backoff
- `FALLBACK`: Fall back to file logging
- `CIRCUIT_BREAK`: Open circuit breaker
- `ALERT`: Alert operators
- `SKIP`: Skip event and continue

## Quick Start

### Basic Usage

```python
from sark.services.audit.siem import SIEMErrorHandler
from sark.models.audit import AuditEvent

# Create error handler
error_handler = SIEMErrorHandler(
    fallback_log_dir="/var/log/siem_fallback",
    max_error_history=100,
    enable_fallback=True,
)

# Handle error
try:
    await splunk_siem.send_event(event)
except Exception as e:
    strategy = await error_handler.handle_error(
        error=e,
        event=event,
        context={"siem": "splunk", "attempt": 1},
    )

    # Act on recovery strategy
    if strategy == RecoveryStrategy.FALLBACK:
        logger.info("Event logged to fallback, will retry later")
    elif strategy == RecoveryStrategy.CIRCUIT_BREAK:
        logger.error("Circuit breaker opened, stopping sends")
    elif strategy == RecoveryStrategy.ALERT:
        logger.critical("Critical error, alerting operators")
```

### With Alerts

```python
from sark.services.audit.siem import (
    SIEMErrorHandler,
    ErrorAlert,
    high_error_rate_condition,
    critical_error_condition,
)

error_handler = SIEMErrorHandler(fallback_log_dir="/var/log/siem_fallback")

# Add high error rate alert
def on_high_error_rate(errors):
    send_pagerduty_alert(
        message=f"High SIEM error rate: {len(errors)} errors in 60s",
        severity="warning",
    )

error_handler.add_alert(ErrorAlert(
    name="high_error_rate",
    condition=lambda errors: high_error_rate_condition(errors, threshold=10, window_seconds=60),
    callback=on_high_error_rate,
    cooldown_seconds=300,  # 5min between alerts
))

# Add critical error alert
def on_critical_error(errors):
    send_pagerduty_alert(
        message=f"Critical SIEM error: {errors[-1].error_message}",
        severity="critical",
    )

error_handler.add_alert(ErrorAlert(
    name="critical_error",
    condition=critical_error_condition,
    callback=on_critical_error,
    cooldown_seconds=60,
))
```

## Fallback Logging

When SIEM is unavailable, events are logged to files for later replay.

### Configuration

```python
from sark.services.audit.siem import FallbackLogger

fallback = FallbackLogger(
    log_dir="/var/log/siem_fallback",
    max_file_size_mb=100,  # Rotate after 100MB
)

# Log event
fallback.log_event(audit_event)

# Get statistics
stats = fallback.get_stats()
print(f"Events logged: {stats['events_logged']}")
print(f"Current file: {stats['current_file']}")
print(f"File size: {stats['current_file_size_mb']:.2f}MB")
```

### Fallback File Format

Events are logged as newline-delimited JSON:

```json
{"id":"550e8400-e29b-41d4-a716-446655440000","timestamp":"2025-11-22T18:00:00Z","event_type":"tool_invoked","severity":"medium","user_email":"user@example.com","tool_name":"bash","decision":"allow","ip_address":"192.168.1.100","details":{"command":"ls -la"}}
{"id":"650e8400-e29b-41d4-a716-446655440001","timestamp":"2025-11-22T18:00:01Z","event_type":"authorization_allowed",...}
```

### Replaying Fallback Logs

```python
import json
from pathlib import Path

def replay_fallback_logs(log_file: Path, siem):
    """Replay events from fallback log."""
    with open(log_file) as f:
        for line in f:
            event_data = json.loads(line)
            # Reconstruct event and send
            try:
                await siem.send_event(reconstruct_event(event_data))
            except Exception as e:
                logger.error(f"Failed to replay: {e}")

# Replay all fallback logs
for log_file in Path("/var/log/siem_fallback").glob("*.log"):
    await replay_fallback_logs(log_file, splunk_siem)
```

## Error Alerts

### Predefined Alert Conditions

```python
# High error rate (>10 errors in 60s)
high_error_rate_condition(errors, threshold=10, window_seconds=60)

# Critical error occurred
critical_error_condition(errors)

# Authentication failure
auth_failure_condition(errors)
```

### Custom Alert Conditions

```python
def custom_condition(errors: list[ErrorRecord]) -> bool:
    """Alert if >5 network errors in last 30s."""
    cutoff = datetime.now(UTC).timestamp() - 30
    network_errors = [
        e for e in errors
        if e.category == ErrorCategory.NETWORK
        and e.timestamp.timestamp() > cutoff
    ]
    return len(network_errors) > 5

error_handler.add_alert(ErrorAlert(
    name="high_network_errors",
    condition=custom_condition,
    callback=lambda errors: send_slack_alert(errors),
    cooldown_seconds=180,
))
```

## Production Integration

### Complete Example

```python
import asyncio
from sark.services.audit.siem import (
    SIEMErrorHandler,
    SIEMOptimizer,
    BatchHandler,
    ErrorAlert,
    RecoveryStrategy,
    SplunkSIEM,
    SplunkConfig,
    high_error_rate_condition,
    critical_error_condition,
)

class ProductionSIEMService:
    """Production SIEM service with comprehensive error handling."""

    def __init__(self):
        # Initialize components
        self.splunk = SplunkSIEM(SplunkConfig(
            hec_url=os.environ["SPLUNK_HEC_URL"],
            hec_token=os.environ["SPLUNK_HEC_TOKEN"],
        ))

        self.optimizer = SIEMOptimizer(
            siem=self.splunk,
            name="splunk-prod",
        )

        self.error_handler = SIEMErrorHandler(
            fallback_log_dir="/var/log/siem_fallback",
            max_error_history=100,
            enable_fallback=True,
        )

        # Setup alerts
        self._setup_alerts()

        # Batch handler with error handling
        self.batch_handler = BatchHandler(
            callback=self._send_batch_with_error_handling,
            config=BatchConfig(batch_size=100, batch_timeout_seconds=5),
        )

    def _setup_alerts(self):
        """Configure error alerts."""
        # High error rate
        self.error_handler.add_alert(ErrorAlert(
            name="high_error_rate",
            condition=lambda e: high_error_rate_condition(e, threshold=10),
            callback=self._on_high_error_rate,
            cooldown_seconds=300,
        ))

        # Critical errors
        self.error_handler.add_alert(ErrorAlert(
            name="critical_error",
            condition=critical_error_condition,
            callback=self._on_critical_error,
            cooldown_seconds=60,
        ))

    async def _send_batch_with_error_handling(self, events):
        """Send batch with comprehensive error handling."""
        try:
            return await self.optimizer.send_batch(events)

        except Exception as e:
            # Handle error for each event in batch
            for event in events:
                strategy = await self.error_handler.handle_error(
                    error=e,
                    event=event,
                    context={"batch_size": len(events)},
                )

                # Apply recovery strategy
                if strategy == RecoveryStrategy.CIRCUIT_BREAK:
                    self.optimizer.circuit_breaker.reset()
                    raise  # Re-raise to open circuit

            return False

    def _on_high_error_rate(self, errors):
        """Handle high error rate alert."""
        logger.error(
            "high_siem_error_rate",
            error_count=len(errors),
            recent_errors=[e.error_type for e in errors[-5:]],
        )
        # Send to monitoring system
        send_alert("High SIEM error rate", severity="warning")

    def _on_critical_error(self, errors):
        """Handle critical error alert."""
        logger.critical(
            "critical_siem_error",
            error=errors[-1].error_message,
            category=errors[-1].category.value,
        )
        # Page on-call
        send_alert("Critical SIEM error", severity="critical")

    async def send_event(self, event):
        """Send event through batch handler."""
        await self.batch_handler.enqueue(event)

    async def start(self):
        """Start service."""
        await self.optimizer.start_health_monitoring()
        await self.batch_handler.start()

    async def stop(self):
        """Stop service gracefully."""
        await self.batch_handler.stop(flush=True)
        await self.optimizer.stop_health_monitoring()

        # Log final metrics
        metrics = self.error_handler.get_metrics()
        logger.info("siem_service_stopped", error_metrics=metrics)
```

## Monitoring

### Metrics

```python
metrics = error_handler.get_metrics()

print(f"Total errors: {metrics['total_errors']}")
print(f"Fallback count: {metrics['fallback_count']}")
print(f"Alerts fired: {metrics['alerts_fired']}")

# Errors by category
for category, count in metrics['errors_by_category'].items():
    print(f"  {category}: {count}")

# Errors by severity
for severity, count in metrics['errors_by_severity'].items():
    print(f"  {severity}: {count}")

# Recent errors
recent = error_handler.get_recent_errors(count=10)
for error in recent:
    print(f"{error['timestamp']}: {error['error_type']} - {error['error_message']}")
```

### Prometheus Metrics

Export error handler metrics to Prometheus:

```python
from prometheus_client import Counter, Gauge, Histogram

# Error counters
siem_errors_total = Counter(
    'siem_errors_total',
    'Total SIEM errors',
    ['category', 'severity', 'siem'],
)

# Fallback counter
siem_fallback_total = Counter(
    'siem_fallback_total',
    'Events sent to fallback logging',
    ['siem'],
)

# Alert counter
siem_alerts_fired = Counter(
    'siem_alerts_fired_total',
    'Error alerts fired',
    ['alert_name', 'siem'],
)

# Update metrics on error
async def handle_error_with_metrics(error, event, context):
    strategy = await error_handler.handle_error(error, event, context)

    # Record metrics
    category, severity = error_handler.classify_error(error)
    siem_errors_total.labels(
        category=category.value,
        severity=severity.value,
        siem=context.get('siem', 'unknown'),
    ).inc()

    if strategy == RecoveryStrategy.FALLBACK:
        siem_fallback_total.labels(siem=context.get('siem', 'unknown')).inc()

    return strategy
```

## Best Practices

### 1. Always Enable Fallback in Production

```python
# ✅ GOOD - Fallback enabled
error_handler = SIEMErrorHandler(
    fallback_log_dir="/var/log/siem_fallback",
    enable_fallback=True,
)

# ❌ BAD - No fallback (lose events on SIEM failure)
error_handler = SIEMErrorHandler(enable_fallback=False)
```

### 2. Configure Appropriate Alerts

```python
# ✅ GOOD - Multiple alert levels
error_handler.add_alert(high_error_rate_alert)  # Warning
error_handler.add_alert(critical_error_alert)   # Critical
error_handler.add_alert(auth_failure_alert)     # High

# ❌ BAD - No alerts (won't know about issues)
# Just handle errors without alerting
```

### 3. Use Alert Cooldowns

```python
# ✅ GOOD - Cooldown prevents alert spam
ErrorAlert(
    name="high_errors",
    condition=...,
    callback=...,
    cooldown_seconds=300,  # 5min between alerts
)

# ❌ BAD - No cooldown (alert spam)
ErrorAlert(name="high_errors", condition=..., callback=..., cooldown_seconds=0)
```

### 4. Include Context in Error Handling

```python
# ✅ GOOD - Rich context
await error_handler.handle_error(
    error=e,
    event=event,
    context={
        "siem": "splunk",
        "batch_size": 100,
        "retry_attempt": 2,
        "circuit_state": circuit.state,
    },
)

# ❌ BAD - No context (hard to debug)
await error_handler.handle_error(error=e)
```

### 5. Monitor Fallback Logs

```python
# ✅ GOOD - Regular fallback log checks
async def check_fallback_logs():
    """Monitor fallback logs and alert if growing."""
    stats = fallback_logger.get_stats()
    if stats['events_logged'] > 1000:
        send_alert("High fallback log count - SIEM may be down")

# Schedule regular checks
asyncio.create_task(periodic_task(check_fallback_logs, interval=300))
```

## Troubleshooting

### High Fallback Rate

**Symptom:** Many events going to fallback logs

**Diagnosis:**
```python
metrics = error_handler.get_metrics()
fallback_rate = metrics['fallback_count'] / max(1, metrics['total_errors'])
print(f"Fallback rate: {fallback_rate:.2%}")
```

**Solutions:**
1. Check SIEM connectivity: `await siem.health_check()`
2. Review network errors in metrics
3. Check circuit breaker state
4. Verify SIEM endpoint is operational

### Alerts Not Firing

**Symptom:** Expected alerts don't fire

**Diagnosis:**
```python
# Check alert configuration
for alert in error_handler.alerts:
    print(f"{alert.name}: fired {alert.alert_count} times")
    print(f"  Last: {alert.last_alert_time}")
    print(f"  Cooldown: {alert.cooldown_seconds}s")

# Test condition manually
recent_errors = list(error_handler.error_history)
if alert.condition(recent_errors):
    print("Condition met but alert didn't fire - check cooldown")
```

**Solutions:**
1. Check cooldown period (may be suppressing alerts)
2. Verify condition logic
3. Check callback isn't raising exceptions
4. Review error history length

### Fallback Logs Growing Too Large

**Symptom:** Fallback log files consuming disk space

**Diagnosis:**
```python
stats = fallback_logger.get_stats()
print(f"Current file: {stats['current_file_size_mb']:.2f}MB")
print(f"Total events: {stats['events_logged']}")
```

**Solutions:**
1. Replay and delete old logs
2. Reduce `max_file_size_mb` for more frequent rotation
3. Setup log rotation with logrotate
4. Archive old logs to S3/cold storage

---

**Version:** 1.0
**Last Updated:** 2025-11-22
**Maintainer:** Engineer 3 (SIEM Lead)
