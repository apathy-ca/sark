# SIEM Integration Framework

## Overview

The SIEM (Security Information and Event Management) integration framework provides a robust, extensible architecture for forwarding audit events from SARK to external SIEM systems like Splunk, Datadog, and others.

## Architecture

The framework consists of three main components:

1. **BaseSIEM** - Abstract base class for SIEM implementations
2. **RetryHandler** - Handles retry logic with exponential backoff
3. **BatchHandler** - Aggregates events for efficient batch forwarding

## Components

### 1. BaseSIEM (base.py)

The abstract base class that all SIEM implementations must inherit from.

#### Key Features:
- Abstract interface for consistency across SIEM implementations
- Built-in metrics tracking (events sent, failed, latency, etc.)
- Health check support
- Event formatting utilities

#### Required Methods:

```python
class MySIEM(BaseSIEM):
    async def send_event(self, event: AuditEvent) -> bool:
        """Send a single audit event to the SIEM."""
        pass

    async def send_batch(self, events: list[AuditEvent]) -> bool:
        """Send a batch of audit events to the SIEM."""
        pass

    async def health_check(self) -> SIEMHealth:
        """Check connectivity and health of the SIEM."""
        pass

    def format_event(self, event: AuditEvent) -> dict[str, Any]:
        """Format an audit event for the specific SIEM."""
        pass
```

#### Configuration:

```python
from sark.services.audit.siem import SIEMConfig

config = SIEMConfig(
    enabled=True,
    verify_ssl=True,
    timeout_seconds=30,
    batch_size=100,
    batch_timeout_seconds=5,
    retry_attempts=3,
    retry_backoff_base=2.0,
    retry_backoff_max=60.0,
)
```

#### Metrics:

The framework automatically tracks:
- `events_sent` - Total events successfully sent
- `events_failed` - Total events that failed
- `batches_sent` - Total batches sent
- `batches_failed` - Total batches failed
- `success_rate` - Calculated success rate (%)
- `average_latency_ms` - Average operation latency
- `retry_count` - Number of retry attempts
- `error_counts` - Count of errors by type

Access metrics:
```python
metrics = siem.get_metrics()
print(f"Success rate: {metrics.success_rate}%")
print(f"Average latency: {metrics.average_latency_ms}ms")
```

### 2. RetryHandler (retry_handler.py)

Handles retry logic with configurable exponential backoff for failed operations.

#### Features:
- Exponential backoff with configurable base and max values
- Configurable retry attempts
- Retryable vs. non-retryable exception handling
- Timeout support
- Retry callbacks for metrics/logging

#### Configuration:

```python
from sark.services.audit.siem import RetryConfig, RetryHandler

config = RetryConfig(
    max_attempts=3,
    backoff_base=2.0,
    backoff_max=60.0,
    retryable_exceptions=(ConnectionError, TimeoutError),
)

handler = RetryHandler(config)
```

#### Usage:

```python
# Simple retry
result = await handler.execute_with_retry(
    operation=async_function,
    operation_name="send_to_siem",
)

# Retry with timeout
result = await handler.execute_with_retry_and_timeout(
    operation=async_function,
    timeout_seconds=30.0,
    operation_name="send_to_siem",
)

# Retry with callback
def on_retry(attempt: int, exception: Exception):
    logger.warning(f"Retry {attempt} due to {exception}")

result = await handler.execute_with_retry(
    operation=async_function,
    operation_name="send_to_siem",
    on_retry=on_retry,
)
```

#### Backoff Calculation:

The backoff delay is calculated as:
```
delay = min(backoff_base ** (attempt - 1), backoff_max)
```

Example with `backoff_base=2.0`, `backoff_max=60.0`:
- Attempt 1: No delay
- Attempt 2: 2.0 seconds
- Attempt 3: 4.0 seconds
- Attempt 4: 8.0 seconds
- ...
- Max delay: 60.0 seconds

### 3. BatchHandler (batch_handler.py)

Aggregates events and forwards them in batches for efficient SIEM delivery.

#### Features:
- Configurable batch size and timeout
- Asynchronous background worker
- Queue management with overflow protection
- Flush on shutdown support
- Comprehensive metrics

#### Configuration:

```python
from sark.services.audit.siem import BatchConfig, BatchHandler

config = BatchConfig(
    batch_size=100,
    batch_timeout_seconds=5.0,
    max_queue_size=10000,
)

handler = BatchHandler(
    send_batch_callback=siem.send_batch,
    config=config,
)
```

#### Usage:

```python
# Start the batch handler
await handler.start()

# Enqueue events
for event in audit_events:
    success = await handler.enqueue(event)
    if not success:
        logger.error("Queue full, event dropped")

# Stop with flush (sends remaining events)
await handler.stop(flush=True)

# Get metrics
metrics = handler.get_metrics()
print(f"Batches sent: {metrics['batches_sent']}")
print(f"Events dropped: {metrics['events_dropped']}")
```

#### Batch Triggering:

Batches are sent when:
1. Batch size is reached (e.g., 100 events)
2. Timeout is reached (e.g., 5 seconds since last flush)
3. Stop is called with `flush=True`

### 4. Prometheus Metrics (metrics.py)

The framework exposes Prometheus metrics for monitoring:

#### Event Metrics:
- `siem_events_sent_total` - Counter of successfully sent events
- `siem_events_failed_total` - Counter of failed events
- `siem_events_dropped_total` - Counter of dropped events

#### Batch Metrics:
- `siem_batches_sent_total` - Counter of successfully sent batches
- `siem_batches_failed_total` - Counter of failed batches

#### Performance Metrics:
- `siem_send_latency_seconds` - Histogram of send operation latency
- `siem_health_check_latency_seconds` - Histogram of health check latency
- `siem_retry_attempts_total` - Counter of retry attempts

#### Queue Metrics:
- `siem_queue_size` - Gauge of current queue size
- `siem_current_batch_size` - Gauge of current batch size

#### Health Metrics:
- `siem_health_status` - Gauge (1=healthy, 0=unhealthy)

## Implementation Example

Here's a complete example of implementing a custom SIEM:

```python
from datetime import UTC, datetime
from typing import Any

import httpx
from sark.models.audit import AuditEvent
from sark.services.audit.siem import BaseSIEM, SIEMConfig, SIEMHealth


class CustomSIEM(BaseSIEM):
    """Custom SIEM implementation."""

    def __init__(self, config: SIEMConfig, api_url: str, api_key: str) -> None:
        super().__init__(config)
        self.api_url = api_url
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=config.timeout_seconds,
            verify=config.verify_ssl,
        )

    async def send_event(self, event: AuditEvent) -> bool:
        """Send a single event."""
        try:
            start_time = datetime.now(UTC)

            formatted = self.format_event(event)
            response = await self._client.post(
                f"{self.api_url}/events",
                json=formatted,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                await self._update_success_metrics(event_count=1, latency_ms=latency_ms)
                return True
            else:
                await self._update_failure_metrics(
                    event_count=1,
                    error_type=f"http_{response.status_code}"
                )
                return False

        except Exception as e:
            await self._update_failure_metrics(
                event_count=1,
                error_type=type(e).__name__
            )
            raise

    async def send_batch(self, events: list[AuditEvent]) -> bool:
        """Send a batch of events."""
        try:
            start_time = datetime.now(UTC)

            formatted_events = [self.format_event(e) for e in events]
            response = await self._client.post(
                f"{self.api_url}/events/batch",
                json={"events": formatted_events},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                await self._update_success_metrics(
                    event_count=len(events),
                    latency_ms=latency_ms
                )
                return True
            else:
                await self._update_failure_metrics(
                    event_count=len(events),
                    error_type=f"http_{response.status_code}"
                )
                return False

        except Exception as e:
            await self._update_failure_metrics(
                event_count=len(events),
                error_type=type(e).__name__
            )
            raise

    async def health_check(self) -> SIEMHealth:
        """Check SIEM health."""
        try:
            start_time = datetime.now(UTC)

            response = await self._client.get(
                f"{self.api_url}/health",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                return SIEMHealth(
                    healthy=True,
                    latency_ms=latency_ms,
                    details={"status": response.json()},
                )
            else:
                return SIEMHealth(
                    healthy=False,
                    latency_ms=latency_ms,
                    error_message=f"HTTP {response.status_code}",
                )

        except Exception as e:
            return SIEMHealth(
                healthy=False,
                error_message=str(e),
            )

    def format_event(self, event: AuditEvent) -> dict[str, Any]:
        """Format event for custom SIEM."""
        base_dict = self._convert_event_to_dict(event)

        # Add custom SIEM-specific formatting
        return {
            "timestamp": base_dict["timestamp"],
            "event_type": base_dict["event_type"],
            "severity": base_dict["severity"],
            "user": {
                "id": base_dict["user_id"],
                "email": base_dict["user_email"],
            },
            "resource": {
                "server_id": base_dict["server_id"],
                "tool_name": base_dict["tool_name"],
            },
            "decision": base_dict["decision"],
            "context": {
                "ip_address": base_dict["ip_address"],
                "user_agent": base_dict["user_agent"],
                "request_id": base_dict["request_id"],
            },
            "details": base_dict["details"],
        }
```

## Usage with Retry and Batch Handlers

Complete integration example:

```python
from sark.services.audit.siem import (
    SIEMConfig,
    RetryConfig,
    RetryHandler,
    BatchConfig,
    BatchHandler,
)

# Configure SIEM
siem_config = SIEMConfig(
    enabled=True,
    batch_size=100,
    retry_attempts=3,
)

siem = CustomSIEM(
    config=siem_config,
    api_url="https://siem.example.com",
    api_key="secret-key",
)

# Configure retry handler
retry_config = RetryConfig(
    max_attempts=3,
    backoff_base=2.0,
)

retry_handler = RetryHandler(retry_config)

# Wrap send_batch with retry logic
async def send_batch_with_retry(events):
    return await retry_handler.execute_with_retry_and_timeout(
        operation=lambda: siem.send_batch(events),
        timeout_seconds=30.0,
        operation_name="siem_batch_send",
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

## Testing

The framework includes comprehensive unit tests with 85%+ coverage:

```bash
# Run SIEM framework tests
pytest tests/test_audit/ -v

# Run with coverage report
pytest tests/test_audit/ --cov=src/sark/services/audit/siem --cov-report=term-missing
```

## Best Practices

1. **Error Handling**: Always catch and log exceptions in SIEM implementations
2. **Timeouts**: Set appropriate timeouts to prevent hanging operations
3. **Backoff**: Use exponential backoff to avoid overwhelming failed SIEMs
4. **Batching**: Use batch operations for better throughput
5. **Monitoring**: Track metrics to identify issues early
6. **Health Checks**: Implement robust health checks for circuit breaker patterns
7. **Testing**: Test with mock SIEM endpoints before production deployment

## Performance Considerations

1. **Batch Size**: Larger batches reduce overhead but increase latency
   - Recommended: 100-500 events per batch

2. **Batch Timeout**: Balance between latency and efficiency
   - Recommended: 5-10 seconds

3. **Queue Size**: Prevent memory exhaustion
   - Recommended: 10,000-100,000 events

4. **Retry Attempts**: Limit retries to avoid cascading failures
   - Recommended: 3-5 attempts

5. **Backoff Max**: Prevent excessive delays
   - Recommended: 60-120 seconds

## Troubleshooting

### Events Not Being Sent

1. Check SIEM health: `await siem.health_check()`
2. Verify configuration: `siem.config.enabled`
3. Check metrics: `siem.get_metrics()`
4. Review logs for errors

### High Latency

1. Check network connectivity
2. Verify SIEM endpoint performance
3. Consider increasing batch size
4. Review retry configuration

### Events Being Dropped

1. Check queue size: `batch_handler.get_metrics()['queue_size']`
2. Increase `max_queue_size` if needed
3. Check if SIEM is down (health check)
4. Review error metrics

### Memory Usage

1. Reduce batch size
2. Reduce max queue size
3. Implement event sampling for non-critical events
4. Monitor metrics and adjust accordingly

## Next Steps

- **Day 2**: Implement Splunk SIEM integration
- **Day 3**: Implement Datadog SIEM integration
- **Day 4**: Implement Kafka background worker
- **Week 2**: Performance optimization and circuit breaker pattern
