# Stdio Transport for MCP Gateway

## Overview

The Stdio Transport provides subprocess-based communication with MCP servers using JSON-RPC 2.0 over stdin/stdout. This transport is ideal for local MCP servers that run as separate processes and communicate via standard I/O streams.

## Features

### Core Functionality
- **Process Lifecycle Management**: Start, stop, and restart subprocess with proper cleanup
- **JSON-RPC 2.0 Protocol**: Full support for requests, responses, and notifications
- **Health Monitoring**: Heartbeat-based health checks with hung process detection
- **Resource Limits**: Memory, CPU, and file descriptor monitoring
- **Auto-Restart**: Automatic restart on crash with configurable retry limits
- **Clean Shutdown**: Graceful shutdown with SIGTERM, force kill on timeout

### Safety Features
- **No Zombie Processes**: Proper process cleanup and reaping
- **No Resource Leaks**: File descriptor and stream cleanup
- **Timeout Protection**: Request timeouts and health check timeouts
- **Error Recovery**: Automatic restart on crashes (up to configured max attempts)

## Quick Start

### Basic Usage

```python
from sark.gateway.transports import StdioTransport

# Create transport
transport = StdioTransport(
    command=["python", "my_mcp_server.py"],
    cwd="/path/to/server",
)

# Start subprocess
await transport.start()

try:
    # Send JSON-RPC request
    result = await transport.send_request(
        method="tools/list",
        params={},
        timeout=30.0,
    )
    print(f"Tools: {result}")

    # Send notification (no response expected)
    await transport.send_notification(
        method="$/cancelRequest",
        params={"id": 123},
    )

finally:
    # Clean shutdown
    await transport.stop(timeout=5.0)
```

### With Custom Configuration

```python
from sark.gateway.transports import StdioTransport, ResourceLimits, HealthConfig

# Configure resource limits
resource_limits = ResourceLimits(
    max_memory_mb=512,      # 512MB memory limit
    max_cpu_percent=75.0,   # 75% CPU warning threshold
    max_file_descriptors=500,  # Max 500 open file descriptors
)

# Configure health checks
health_config = HealthConfig(
    heartbeat_interval=5.0,  # Check health every 5 seconds
    hung_timeout=10.0,       # Consider hung after 10s without activity
)

# Create transport with custom config
transport = StdioTransport(
    command=["node", "server.js"],
    cwd="/opt/mcp-server",
    env={"NODE_ENV": "production", "LOG_LEVEL": "info"},
    resource_limits=resource_limits,
    health_config=health_config,
    max_restart_attempts=5,
)

await transport.start()
```

## Configuration

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `command` | `list[str]` | Required | Command and arguments to execute |
| `cwd` | `str \| None` | Current dir | Working directory for subprocess |
| `env` | `dict[str, str] \| None` | Parent env | Environment variables |
| `resource_limits` | `ResourceLimits \| None` | Default limits | Resource limit configuration |
| `health_config` | `HealthConfig \| None` | Default config | Health check configuration |
| `max_restart_attempts` | `int` | 3 | Maximum auto-restart attempts |

### ResourceLimits

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_memory_mb` | `int` | 1024 | Maximum memory usage (MB) - fatal if exceeded |
| `max_cpu_percent` | `float` | 80.0 | CPU usage warning threshold (%) - logs warning only |
| `max_file_descriptors` | `int` | 1000 | Maximum open file descriptors - fatal if exceeded |

### HealthConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `heartbeat_interval` | `float` | 10.0 | Seconds between health checks |
| `hung_timeout` | `float` | 15.0 | Seconds without activity before considering process hung |

## Process Lifecycle

### Start

```python
await transport.start()
```

1. Spawns subprocess with `asyncio.create_subprocess_exec`
2. Sets up stdin/stdout/stderr pipes
3. Initializes psutil process for resource monitoring
4. Starts health check loop (runs every `heartbeat_interval`)
5. Starts stderr reader task
6. Starts stdout reader task (handles JSON-RPC responses)

**Errors**: Raises `ProcessStartError` if subprocess fails to start.

### Stop

```python
await transport.stop(timeout=5.0)
```

1. Sets shutdown flag to prevent auto-restart
2. Sends SIGTERM for graceful shutdown
3. Waits up to `timeout` seconds for process to exit
4. If timeout expires, sends SIGKILL for force kill
5. Cancels health check and stderr reader tasks
6. Fails all pending requests with `StdioTransportError`
7. Closes and cleans up streams

**Parameters**:
- `timeout`: Seconds to wait for graceful shutdown before force kill (default: 5.0)

### Restart

```python
await transport.restart()
```

1. Calls `stop()` with 3-second timeout
2. Increments restart counter
3. Checks if restart attempts exceeded `max_restart_attempts`
4. Calls `start()` to spawn new process

**Errors**: Raises `ProcessCrashError` if max restart attempts exceeded.

## JSON-RPC Communication

### Send Request (with response)

```python
result = await transport.send_request(
    method="tools/call",
    params={"name": "grep", "arguments": {"pattern": "error"}},
    timeout=30.0,
)
```

Sends JSON-RPC 2.0 request and waits for response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {"name": "grep", "arguments": {"pattern": "error"}}
}
```

**Returns**: Response `result` field
**Errors**:
- `StdioTransportError`: If transport not started or JSON-RPC error response
- `asyncio.TimeoutError`: If request times out

### Send Notification (no response)

```python
await transport.send_notification(
    method="notifications/initialized",
    params={},
)
```

Sends JSON-RPC 2.0 notification (no `id` field):

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized",
  "params": {}
}
```

**Note**: Notifications do not expect responses and complete immediately after sending.

## Health Monitoring

### Heartbeat Tracking

The transport tracks the last activity time on:
- Sending requests or notifications
- Receiving responses or notifications

### Health Check Loop

Runs every `heartbeat_interval` seconds and performs:

1. **Hung Process Detection**
   - Checks time since last heartbeat
   - If > `hung_timeout`, triggers restart
   - Logs error: `stdio_transport_hung_process`

2. **Memory Usage**
   - Checks RSS (resident set size)
   - If > `max_memory_mb`, kills process
   - Logs error: `stdio_transport_memory_limit_exceeded`
   - Raises `ResourceLimitExceededError`

3. **CPU Usage**
   - Checks CPU percentage
   - If > `max_cpu_percent`, logs warning
   - Does NOT kill process (warning only)
   - Logs warning: `stdio_transport_high_cpu`

4. **File Descriptors**
   - Checks number of open FDs
   - If > `max_file_descriptors`, kills process
   - Logs error: `stdio_transport_fd_limit_exceeded`
   - Raises `ResourceLimitExceededError`

### Auto-Restart on Crash

If subprocess crashes (EOF on stdout) and not shutting down:
1. Logs error: `stdio_transport_unexpected_eof`
2. Checks restart counter < `max_restart_attempts`
3. Triggers `restart()` via background task
4. If max attempts exceeded, does not restart

## Error Handling

### Exceptions

| Exception | Description | Recovery |
|-----------|-------------|----------|
| `ProcessStartError` | Subprocess failed to start | Check command and environment |
| `ProcessCrashError` | Max restart attempts exceeded | Investigate subprocess logs |
| `ResourceLimitExceededError` | Memory or FD limit exceeded | Increase limits or fix memory leak |
| `StdioTransportError` | General transport error | Check logs for details |
| `asyncio.TimeoutError` | Request timeout | Increase timeout or check subprocess |

### Logging

All operations are logged with structured logging (structlog):

```python
logger.info("stdio_transport_started", command=cmd, pid=12345)
logger.warning("stdio_transport_high_cpu", pid=12345, cpu_percent=85.0)
logger.error("stdio_transport_memory_limit_exceeded", pid=12345, memory_mb=2048)
```

**Log Events**:
- `stdio_transport_starting`: Starting subprocess
- `stdio_transport_started`: Subprocess started successfully
- `stdio_transport_stopping`: Stopping subprocess
- `stdio_transport_stopped_gracefully`: Graceful shutdown completed
- `stdio_transport_force_killing`: Force kill after timeout
- `stdio_transport_cleaned_up`: Cleanup completed
- `stdio_transport_request_sent`: JSON-RPC request sent
- `stdio_transport_notification_sent`: JSON-RPC notification sent
- `stdio_transport_request_timeout`: Request timed out
- `stdio_transport_hung_process`: Process detected as hung
- `stdio_transport_unexpected_eof`: Process crashed (EOF on stdout)
- `stdio_transport_memory_limit_exceeded`: Memory limit exceeded
- `stdio_transport_high_cpu`: High CPU usage (warning)
- `stdio_transport_fd_limit_exceeded`: File descriptor limit exceeded
- `stdio_transport_stderr`: Stderr output from subprocess
- `stdio_transport_invalid_json`: Invalid JSON received

## Properties

### `is_running` (bool)

Returns `True` if subprocess is currently running and not shutting down.

```python
if transport.is_running:
    await transport.send_request("ping", {})
```

### `pid` (int | None)

Returns subprocess PID or `None` if not started.

```python
print(f"MCP server running with PID: {transport.pid}")
```

## Best Practices

### 1. Always Use Context Manager Pattern

```python
transport = StdioTransport(command=["python", "server.py"])
await transport.start()
try:
    # Use transport
    result = await transport.send_request("tools/list", {})
finally:
    await transport.stop()
```

### 2. Set Appropriate Timeouts

```python
# Quick operations
result = await transport.send_request("ping", {}, timeout=5.0)

# Long-running operations
result = await transport.send_request("analyze/large_file", params, timeout=120.0)
```

### 3. Monitor Resource Usage

```python
# For memory-intensive servers
transport = StdioTransport(
    command=["python", "ml_server.py"],
    resource_limits=ResourceLimits(max_memory_mb=4096),  # 4GB
)
```

### 4. Handle Errors Gracefully

```python
try:
    result = await transport.send_request("risky/operation", {})
except asyncio.TimeoutError:
    logger.error("Operation timed out")
    # Consider restarting transport
    await transport.restart()
except StdioTransportError as e:
    logger.error("Transport error", error=str(e))
    # Handle or re-raise
```

### 5. Use Notifications for Fire-and-Forget

```python
# Don't wait for response
await transport.send_notification("log/event", {"level": "info", "message": "..."})
```

## Troubleshooting

### Process Keeps Crashing

1. Check subprocess logs in stderr
2. Verify command and arguments are correct
3. Check environment variables and working directory
4. Increase resource limits if needed
5. Look for memory leaks or excessive FD usage

### Requests Timing Out

1. Check if subprocess is hung (check logs for `stdio_transport_hung_process`)
2. Increase request timeout
3. Verify subprocess is responding to JSON-RPC
4. Check for deadlocks in subprocess

### Memory Limit Exceeded

1. Increase `max_memory_mb` if reasonable
2. Check for memory leaks in subprocess
3. Profile subprocess memory usage
4. Consider pagination or streaming for large data

### High CPU Usage

1. High CPU logs warning but doesn't kill process
2. Check if subprocess is doing heavy computation
3. Consider optimizing subprocess code
4. Adjust `max_cpu_percent` threshold if needed

### File Descriptor Leaks

1. Check subprocess for unclosed files/sockets
2. Increase `max_file_descriptors` temporarily
3. Fix FD leaks in subprocess
4. Monitor with `lsof -p <pid>`

## Examples

### Integration with MCP Server

```python
# Start MCP server with stdio transport
transport = StdioTransport(
    command=["python", "-m", "mcp_server", "--stdio"],
    cwd="/opt/mcp-server",
    env={"MCP_CONFIG": "/etc/mcp/config.json"},
)

await transport.start()

# Initialize MCP protocol
await transport.send_request("initialize", {
    "protocolVersion": "1.0",
    "capabilities": {},
})

# List available tools
tools = await transport.send_request("tools/list", {})
print(f"Available tools: {tools}")

# Call a tool
result = await transport.send_request("tools/call", {
    "name": "filesystem/read",
    "arguments": {"path": "/etc/passwd"},
})

await transport.stop()
```

### Long-Running Server

```python
# For long-running server, use context manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def mcp_server_context():
    transport = StdioTransport(
        command=["./mcp-server", "--mode", "daemon"],
        health_config=HealthConfig(
            heartbeat_interval=30.0,  # Check every 30s
            hung_timeout=60.0,        # 1 minute timeout
        ),
        max_restart_attempts=10,  # More restarts for long-running
    )

    await transport.start()
    try:
        yield transport
    finally:
        await transport.stop(timeout=10.0)

# Use it
async with mcp_server_context() as transport:
    # Server runs for duration of context
    result = await transport.send_request("status", {})
    # ...
```

### Multiple Servers

```python
# Manage multiple MCP servers
servers = {
    "filesystem": StdioTransport(["python", "fs_server.py"]),
    "database": StdioTransport(["python", "db_server.py"]),
    "network": StdioTransport(["python", "net_server.py"]),
}

# Start all
for name, transport in servers.items():
    await transport.start()
    print(f"{name} started with PID {transport.pid}")

try:
    # Use servers
    fs_tools = await servers["filesystem"].send_request("tools/list", {})
    db_tools = await servers["database"].send_request("tools/list", {})

finally:
    # Stop all
    for transport in servers.values():
        await transport.stop()
```

## Testing

### Unit Tests

The stdio transport includes comprehensive unit tests covering:

- Process lifecycle (start/stop/restart)
- JSON-RPC messaging (requests/responses/notifications)
- Health checks and heartbeat monitoring
- Resource limit enforcement
- Error handling and edge cases
- Auto-restart behavior
- Clean shutdown

Run tests:

```bash
pytest tests/unit/gateway/transports/test_stdio_client.py -v
```

### Coverage

Target: 90%+ code coverage

Check coverage:

```bash
pytest tests/unit/gateway/transports/test_stdio_client.py --cov=src/sark/gateway/transports/stdio_client --cov-report=term-missing
```

## Performance Considerations

### Memory Usage

- Base overhead: ~10MB per transport instance
- Subprocess memory: Depends on MCP server
- Total = overhead + subprocess memory

### CPU Usage

- Health checks: Negligible (<1% CPU)
- JSON parsing: Depends on message frequency and size
- Subprocess CPU: Depends on MCP server

### Latency

- Local IPC overhead: <1ms for small messages
- JSON serialization: ~0.1ms for typical messages
- Total latency dominated by subprocess processing time

## Security Considerations

1. **Command Injection**: Always validate `command` parameter
2. **Environment Variables**: Sanitize `env` to prevent injection
3. **Working Directory**: Validate `cwd` exists and has correct permissions
4. **Resource Limits**: Set appropriate limits to prevent DoS
5. **Signal Handling**: SIGTERM for graceful shutdown, SIGKILL as last resort

## Future Enhancements

- [ ] Support for bidirectional streaming
- [ ] Subprocess output buffering configuration
- [ ] Custom health check callbacks
- [ ] Metrics and telemetry integration
- [ ] Process isolation (cgroups, namespaces)
- [ ] Windows support (currently Linux/macOS only)
