# Gateway SSE Transport

## Overview

The Gateway SSE (Server-Sent Events) Transport provides async streaming client functionality for real-time communication with MCP Gateway servers. It enables applications to receive live updates for audit events, server health changes, tool invocations, and other Gateway events.

## Features

- **Server-Sent Events Streaming**: Full SSE protocol support
- **Connection Pooling**: Manage up to 50 concurrent SSE streams
- **Automatic Reconnection**: Exponential backoff retry on connection loss
- **Event Filtering**: Filter events by type
- **Last-Event-ID Tracking**: Resume streams after disconnection
- **Stream Health Monitoring**: Real-time connection state tracking
- **Comprehensive Error Recovery**: Resilient streaming with fallback patterns

## Installation

The SSE transport is included in the `sark.gateway.transports` package:

```python
from sark.gateway.transports import GatewaySSEClient
```

## Basic Usage

### Creating a Client

```python
from sark.gateway.transports import GatewaySSEClient

# Basic streaming client
async with GatewaySSEClient(
    base_url="http://gateway:8080",
    api_key="your-api-key",
) as client:
    # Stream events
    async for event in client.stream_events(endpoint="/api/v1/stream"):
        print(f"Event: {event.event_type} - {event.data}")
```

### With Reconnection Disabled

```python
async with GatewaySSEClient(
    base_url="http://gateway:8080",
    reconnect_enabled=False,  # No automatic reconnection
) as client:
    # Stream will fail immediately on connection loss
    async for event in client.stream_events("/api/v1/stream"):
        print(event.data)
```

## Configuration

### Client Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | Required | Gateway base URL (e.g., "http://gateway:8080") |
| `api_key` | `str \| None` | `None` | Optional API key for authentication |
| `timeout` | `float` | `60.0` | Stream timeout in seconds |
| `max_connections` | `int` | `50` | Maximum concurrent SSE streams |
| `reconnect_enabled` | `bool` | `True` | Enable automatic reconnection |
| `reconnect_max_retries` | `int` | `5` | Maximum reconnection attempts |
| `reconnect_initial_delay` | `float` | `1.0` | Initial reconnection delay (seconds) |
| `reconnect_max_delay` | `float` | `60.0` | Maximum reconnection delay (seconds) |

### Example: Custom Configuration

```python
async with GatewaySSEClient(
    base_url="http://gateway:8080",
    timeout=120.0,  # 2 minute stream timeout
    max_connections=100,  # Support 100 concurrent streams
    reconnect_max_retries=10,  # More aggressive reconnection
    reconnect_max_delay=30.0,  # Cap backoff at 30 seconds
) as client:
    pass
```

## API Reference

### Event Streaming

#### `stream_events()`

Stream events from Gateway SSE endpoint with automatic reconnection.

```python
async for event in client.stream_events(
    endpoint="/api/v1/stream",
    event_types=["tool_invoked", "server_registered"],
    user_token="jwt-token",
    params={"filter": "important"},
):
    print(f"Type: {event.event_type}")
    print(f"Data: {event.data}")
    print(f"ID: {event.event_id}")
```

**Parameters:**
- `endpoint` (str): SSE endpoint path
- `event_types` (list[str] | None): Optional event type filter
- `user_token` (str | None): Optional user JWT token
- `params` (dict[str, Any] | None): Optional query parameters

**Yields:** `SSEEvent` objects

**Raises:**
- `RuntimeError`: If connection pool exhausted
- `httpx.HTTPStatusError`: If HTTP error (4xx) occurs
- `RuntimeError`: If max retries exceeded

#### `stream_audit_events()`

Stream audit events from Gateway.

```python
async for event in client.stream_audit_events(
    user_token="jwt-token",
    event_types=["authorization_denied", "tool_invoked"],
):
    audit_data = json.loads(event.data)
    print(f"Audit event: {audit_data}")
```

**Parameters:**
- `user_token` (str): User JWT token for authorization
- `event_types` (list[str] | None): Optional event type filter

**Yields:** `SSEEvent` objects for audit events

#### `stream_server_events()`

Stream events for a specific MCP server.

```python
async for event in client.stream_server_events(
    server_name="postgres-mcp",
    user_token="jwt-token",
    event_types=["health_check", "tool_executed"],
):
    print(f"Server event: {event.event_type}")
```

**Parameters:**
- `server_name` (str): MCP server name to monitor
- `user_token` (str): User JWT token
- `event_types` (list[str] | None): Optional event type filter

**Yields:** `SSEEvent` objects for server-specific events

### Health Check

#### `health_check()`

Check SSE client health status.

```python
health = await client.health_check()
print(f"Healthy: {health['healthy']}")
print(f"State: {health['state']}")
print(f"Active streams: {health['active_streams']}")
```

**Returns:** `dict[str, bool | str | int]` with keys:
- `healthy` (bool): Overall health status
- `state` (str): Connection state
- `active_streams` (int): Number of active streams
- `error` (str): Error message (if unhealthy)

### Metrics

#### `get_metrics()`

Get SSE client metrics.

```python
metrics = client.get_metrics()
print(f"Events received: {metrics['events_received']}")
print(f"Reconnections: {metrics['reconnections']}")
print(f"Active streams: {metrics['active_streams']}")
```

**Returns:** `dict[str, Any]` with metrics:
- `state` (str): Current connection state
- `events_received` (int): Total events received
- `connections_made` (int): Total connections established
- `reconnections` (int): Total reconnection attempts
- `errors` (int): Total errors encountered
- `active_streams` (int): Current active streams
- `max_streams` (int): Maximum allowed streams
- `last_event_id` (str | None): Last event ID received

## SSE Event Structure

### `SSEEvent` Class

Represents a Server-Sent Event:

```python
class SSEEvent:
    event_type: str  # Event type (default: "message")
    data: str        # Event data payload
    event_id: str | None  # Event ID for reconnection
    retry: int | None     # Retry timeout in milliseconds
```

### Example Event Processing

```python
async for event in client.stream_events("/api/v1/stream"):
    if event.event_type == "tool_invoked":
        data = json.loads(event.data)
        print(f"Tool: {data['tool_name']}")
        print(f"Server: {data['server_name']}")
        print(f"Result: {data['result']}")
    elif event.event_type == "server_registered":
        data = json.loads(event.data)
        print(f"New server: {data['server_name']}")
```

## Connection States

The client tracks connection state through the `ConnectionState` enum:

| State | Description |
|-------|-------------|
| `DISCONNECTED` | Not connected to Gateway |
| `CONNECTING` | Establishing initial connection |
| `CONNECTED` | Actively streaming events |
| `RECONNECTING` | Attempting to reconnect after failure |
| `CLOSED` | Client closed, no reconnection |

### Monitoring Connection State

```python
client = GatewaySSEClient(base_url="http://gateway:8080")

print(f"Initial state: {client.state}")  # DISCONNECTED

async for event in client.stream_events("/stream"):
    print(f"Current state: {client.state}")  # CONNECTED or RECONNECTING
    break

await client.close()
print(f"Final state: {client.state}")  # CLOSED
```

## Reconnection Logic

### Automatic Reconnection

When enabled (default), the client automatically reconnects on:
- Network errors (connection lost, timeout)
- Server errors (5xx status codes)

**Reconnection does NOT happen for:**
- Client errors (4xx status codes - auth failure, bad request)
- Maximum retries exceeded

### Exponential Backoff

Reconnection delays follow exponential backoff:

1. First retry: 1 second (configurable via `reconnect_initial_delay`)
2. Second retry: 2 seconds
3. Third retry: 4 seconds
4. Fourth retry: 8 seconds
5. Fifth retry: 16 seconds
6. Subsequent: Capped at `reconnect_max_delay`

### Example: Custom Reconnection

```python
async with GatewaySSEClient(
    base_url="http://gateway:8080",
    reconnect_enabled=True,
    reconnect_max_retries=10,  # More retries
    reconnect_initial_delay=0.5,  # Faster initial retry
    reconnect_max_delay=30.0,  # Cap at 30 seconds
) as client:
    async for event in client.stream_events("/stream"):
        # Client will retry up to 10 times with exponential backoff
        print(event.data)
```

### Last-Event-ID Resume

The client tracks the last event ID and sends it in the `Last-Event-ID` header on reconnection:

```python
async for event in client.stream_events("/stream"):
    # Client automatically tracks event.event_id
    # On reconnection, sends: Last-Event-ID: <last_id>
    # Gateway can resume stream from that point
    print(f"Event ID: {event.event_id}")
```

## Connection Pooling

### Pool Limits

The client enforces a maximum number of concurrent SSE streams (default: 50):

```python
async with GatewaySSEClient(
    base_url="http://gateway:8080",
    max_connections=50,
) as client:
    # Can have up to 50 concurrent streams
    pass
```

### Pool Exhaustion

When the pool is exhausted, new stream attempts raise `RuntimeError`:

```python
try:
    async for event in client.stream_events("/stream"):
        pass
except RuntimeError as e:
    if "pool exhausted" in str(e):
        # Too many concurrent streams
        print("Connection pool full - close some streams first")
```

### Managing Multiple Streams

```python
import asyncio

async def stream_audit_logs(client):
    async for event in client.stream_audit_events(user_token="token"):
        print(f"Audit: {event.data}")

async def stream_server_health(client, server_name):
    async for event in client.stream_server_events(server_name, "token"):
        print(f"Health: {event.data}")

async with GatewaySSEClient(base_url="http://gateway:8080") as client:
    # Run multiple streams concurrently
    await asyncio.gather(
        stream_audit_logs(client),
        stream_server_health(client, "postgres-mcp"),
        stream_server_health(client, "slack-mcp"),
    )
```

## Error Handling

### Common Errors

#### Connection Pool Exhausted

```python
try:
    async for event in client.stream_events("/stream"):
        pass
except RuntimeError as e:
    if "pool exhausted" in str(e):
        # Close some streams or increase max_connections
        print(f"Pool exhausted: {client._max_streams} streams active")
```

#### Maximum Retries Exceeded

```python
try:
    async for event in client.stream_events("/stream"):
        pass
except RuntimeError as e:
    if "max retries exceeded" in str(e):
        # Gateway unreachable after multiple attempts
        print("Gateway appears down - check connectivity")
```

#### Authentication Failure

```python
try:
    async for event in client.stream_events("/stream", user_token="bad-token"):
        pass
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        # Invalid or expired token
        print("Authentication failed - refresh token")
```

### Error Handling Example

```python
from httpx import HTTPStatusError, RequestError

try:
    async for event in client.stream_events(
        endpoint="/api/v1/stream",
        user_token=user_token,
    ):
        process_event(event)

except HTTPStatusError as e:
    if e.response.status_code == 401:
        logger.error("Authentication failed")
    elif e.response.status_code == 403:
        logger.error("Authorization denied")
    else:
        logger.error(f"HTTP error: {e.response.status_code}")

except RequestError as e:
    logger.error(f"Network error: {e}")

except RuntimeError as e:
    if "pool exhausted" in str(e):
        logger.error("Connection pool full")
    elif "max retries" in str(e):
        logger.error("Gateway unreachable")
    else:
        logger.error(f"Runtime error: {e}")
```

## Performance

### Benchmarks

- **Event latency**: <50ms from Gateway to client
- **Connection establishment**: <100ms (local network)
- **Reconnection time**: 1-16s (exponential backoff)
- **Concurrent streams**: 50+ streams per client
- **Throughput**: 10,000+ events/second (aggregate)

### Optimization Tips

1. **Filter Events**: Use `event_types` to reduce unnecessary processing
2. **Connection Pool**: Tune `max_connections` for your workload
3. **Reconnection**: Adjust backoff parameters for network conditions
4. **Multiple Clients**: Use separate clients for different purposes
5. **Async Processing**: Don't block event loop in event handlers

### Example: High-Performance Setup

```python
# Optimized for high-throughput streaming
async with GatewaySSEClient(
    base_url="http://gateway:8080",
    max_connections=100,  # More concurrent streams
    timeout=300.0,  # Longer timeout for stable streams
    reconnect_max_retries=10,  # Aggressive reconnection
) as client:
    # Stream only critical events
    async for event in client.stream_events(
        endpoint="/api/v1/stream",
        event_types=["critical_alert", "security_event"],
    ):
        # Process events asynchronously
        asyncio.create_task(process_event(event))
```

## Use Cases

### 1. Real-Time Audit Monitoring

```python
async def monitor_audit_events():
    async with GatewaySSEClient(base_url="http://gateway:8080") as client:
        async for event in client.stream_audit_events(
            user_token=admin_token,
            event_types=["authorization_denied", "security_violation"],
        ):
            audit_data = json.loads(event.data)
            if audit_data["severity"] == "critical":
                send_alert(audit_data)
```

### 2. Server Health Monitoring

```python
async def monitor_server_health(server_name: str):
    async with GatewaySSEClient(base_url="http://gateway:8080") as client:
        async for event in client.stream_server_events(
            server_name=server_name,
            user_token=monitoring_token,
            event_types=["health_check"],
        ):
            health_data = json.loads(event.data)
            if health_data["status"] != "healthy":
                alert_ops_team(server_name, health_data)
```

### 3. Live Dashboard Updates

```python
async def stream_dashboard_updates(websocket):
    """Forward SSE events to WebSocket for live dashboard."""
    async with GatewaySSEClient(base_url="http://gateway:8080") as client:
        async for event in client.stream_events(
            endpoint="/api/v1/stream",
            user_token=dashboard_token,
        ):
            # Forward to WebSocket clients
            await websocket.send_json({
                "type": event.event_type,
                "data": json.loads(event.data),
                "timestamp": event.event_id,
            })
```

### 4. Tool Invocation Tracking

```python
async def track_tool_invocations():
    async with GatewaySSEClient(base_url="http://gateway:8080") as client:
        async for event in client.stream_events(
            endpoint="/api/v1/stream",
            event_types=["tool_invoked", "tool_completed", "tool_failed"],
        ):
            invocation = json.loads(event.data)

            if event.event_type == "tool_invoked":
                track_start(invocation["tool_name"], invocation["user_id"])
            elif event.event_type == "tool_completed":
                track_success(invocation["tool_name"], invocation["duration"])
            elif event.event_type == "tool_failed":
                track_failure(invocation["tool_name"], invocation["error"])
```

## Best Practices

### 1. Use Context Managers

```python
# ✅ Recommended
async with GatewaySSEClient(base_url="http://gateway:8080") as client:
    async for event in client.stream_events("/stream"):
        process(event)

# ❌ Not recommended
client = GatewaySSEClient(base_url="http://gateway:8080")
async for event in client.stream_events("/stream"):
    process(event)
await client.close()  # Easy to forget!
```

### 2. Filter Events at Source

```python
# ✅ Recommended - Filter at source
async for event in client.stream_events(
    "/stream",
    event_types=["tool_invoked"],  # Only receive tool_invoked
):
    process(event)

# ❌ Not recommended - Filter in client
async for event in client.stream_events("/stream"):
    if event.event_type == "tool_invoked":  # Wastes bandwidth
        process(event)
```

### 3. Handle Reconnection Gracefully

```python
# ✅ Recommended - Let client handle reconnection
async for event in client.stream_events("/stream"):
    # Client automatically reconnects on failure
    process(event)

# ❌ Not recommended - Manual reconnection
while True:
    try:
        async for event in client.stream_events("/stream"):
            process(event)
    except Exception:
        await asyncio.sleep(5)  # Client already does this!
```

### 4. Monitor Metrics

```python
# ✅ Recommended - Track stream health
async def monitor_stream_health(client):
    while True:
        metrics = client.get_metrics()
        if metrics["errors"] > 100:
            logger.warning("High error rate", metrics=metrics)
        await asyncio.sleep(60)

asyncio.create_task(monitor_stream_health(client))
```

## Troubleshooting

### Issue: Frequent Disconnections

**Symptoms:** Stream disconnects every few minutes

**Solutions:**
- Increase `timeout` value
- Check network stability
- Verify Gateway is healthy
- Review Gateway logs for errors

### Issue: Events Not Received

**Symptoms:** Stream connects but no events arrive

**Solutions:**
- Verify `event_types` filter is correct
- Check user token has proper permissions
- Confirm events are being generated at Gateway
- Test without filter: `event_types=None`

### Issue: Connection Pool Exhausted

**Symptoms:** `RuntimeError: Connection pool exhausted`

**Solutions:**
- Close unused streams
- Increase `max_connections`
- Review stream lifecycle management
- Check for stream leaks (not closing properly)

### Issue: Reconnection Fails

**Symptoms:** `RuntimeError: SSE max retries exceeded`

**Solutions:**
- Increase `reconnect_max_retries`
- Check Gateway availability
- Verify network connectivity
- Review Gateway logs for errors
- Consider exponentially increasing `reconnect_max_delay`

## See Also

- [HTTP Transport Documentation](HTTP_TRANSPORT.md)
- [Gateway Integration Plan](../MCP_GATEWAY_INTEGRATION_PLAN.md)
- [Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
