# Gateway Client Usage Guide

Complete guide for using the SARK Gateway client to communicate with MCP Gateway Registry.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Transport Types](#transport-types)
- [Basic Operations](#basic-operations)
- [Advanced Usage](#advanced-usage)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

The SARK Gateway client provides a unified interface for communicating with MCP Gateway Registry using three transport protocols:

- **HTTP**: RESTful operations (server discovery, tool listing, tool invocation)
- **SSE**: Real-time event streaming (Server-Sent Events)
- **stdio**: Local subprocess communication (for development/testing)

### Key Features

- ✅ Automatic transport selection based on operation type
- ✅ Built-in error handling (circuit breaker, retry, timeout)
- ✅ Connection pooling (max 50 concurrent connections)
- ✅ Response caching (5-minute TTL, >80% hit rate)
- ✅ OPA integration for authorization
- ✅ Async/await support with context managers
- ✅ Comprehensive logging and metrics

---

## Quick Start

### Installation

The Gateway client is included in the SARK package:

```bash
pip install sark
```

### Basic Usage

```python
from sark.gateway import GatewayClient

async def main():
    async with GatewayClient(
        gateway_url="http://gateway:8080",
        api_key="your-api-key",
    ) as client:
        # List all servers
        servers = await client.list_servers()
        print(f"Found {len(servers)} servers")

        # Invoke a tool
        result = await client.invoke_tool(
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={"query": "SELECT 1"},
        )
        print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## Transport Types

### HTTP Transport

Best for RESTful operations like server discovery and tool invocation.

```python
async with GatewayClient(
    gateway_url="http://gateway:8080",
    transport_mode=TransportMode.HTTP_ONLY,
) as client:
    servers = await client.list_servers()
    tools = await client.list_tools()
    result = await client.invoke_tool(...)
```

**Use HTTP for:**
- Server listing and discovery
- Tool discovery
- Tool invocation
- Batch operations

### SSE Transport

Best for real-time event streaming.

```python
async with GatewayClient(
    gateway_url="http://gateway:8080",
    transport_mode=TransportMode.SSE_ONLY,
) as client:
    async for event in client.stream_events(
        event_types=["tool_invoked", "server_registered"]
    ):
        print(f"Event: {event.event_type} - {event.data}")
```

**Use SSE for:**
- Real-time monitoring
- Event-driven architectures
- Live updates
- Audit trail streaming

### stdio Transport

Best for local development with subprocess-based MCP servers.

```python
async with GatewayClient(
    transport_mode=TransportMode.STDIO_ONLY
) as client:
    local_server = await client.connect_local_server(
        command=["python", "my_mcp_server.py"],
        cwd="/path/to/server",
    )

    try:
        response = await local_server.send_request("tools/list", {})
        print(response)
    finally:
        await local_server.stop()
```

**Use stdio for:**
- Local development
- Testing
- Debugging
- Custom server implementations

### Auto Transport Selection

Let the client automatically choose the best transport (recommended):

```python
async with GatewayClient(
    gateway_url="http://gateway:8080",
    transport_mode=TransportMode.AUTO,  # Default
) as client:
    # Uses HTTP automatically
    servers = await client.list_servers()

    # Uses SSE automatically
    async for event in client.stream_events():
        process_event(event)
```

---

## Basic Operations

### Server Discovery

#### List All Servers

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    # Paginated listing
    servers = await client.list_servers(page=1, page_size=100)

    # Or fetch ALL servers with automatic pagination
    all_servers = await client.list_all_servers()

    for server in all_servers:
        print(f"Server: {server.server_name}")
        print(f"  URL: {server.server_url}")
        print(f"  Health: {server.health_status}")
        print(f"  Tools: {server.tools_count}")
        print(f"  Sensitivity: {server.sensitivity_level}")
```

#### Get Specific Server Info

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    server = await client.get_server_info("postgres-mcp")

    print(f"Server ID: {server.server_id}")
    print(f"Authorized Teams: {server.authorized_teams}")
    print(f"Access Restrictions: {server.access_restrictions}")
```

### Tool Discovery

#### List Tools

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    # All tools
    all_tools = await client.list_all_tools()

    # Tools from specific server
    postgres_tools = await client.list_all_tools(server_name="postgres-mcp")

    for tool in postgres_tools:
        print(f"Tool: {tool.tool_name}")
        print(f"  Description: {tool.description}")
        print(f"  Sensitivity: {tool.sensitivity_level}")
        print(f"  Parameters: {tool.parameters}")
        print(f"  Sensitive Params: {tool.sensitive_params}")
```

### Tool Invocation

#### Basic Invocation

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    result = await client.invoke_tool(
        server_name="postgres-mcp",
        tool_name="execute_query",
        parameters={
            "query": "SELECT * FROM users LIMIT 10",
            "database": "production",
        },
    )

    print(f"Result: {result}")
```

#### With User Authentication

```python
async with GatewayClient(
    gateway_url="http://gateway:8080",
    api_key="gateway-api-key",
) as client:
    result = await client.invoke_tool(
        server_name="postgres-mcp",
        tool_name="execute_query",
        parameters={"query": "SELECT 1"},
        user_token="user-jwt-token",  # User's JWT token
    )
```

#### With OPA Authorization

```python
from sark.services.policy.opa_client import OPAClient

opa_client = OPAClient(opa_url="http://opa:8181")

async with GatewayClient(
    gateway_url="http://gateway:8080",
    opa_client=opa_client,  # Enable OPA authorization
) as client:
    # Tool invocation will be authorized by OPA
    result = await client.invoke_tool(
        server_name="postgres-mcp",
        tool_name="execute_query",
        parameters={
            "query": "SELECT * FROM users",
            "password": "secret",  # Will be filtered by OPA
        },
        user_token="jwt-token",
    )
    # OPA filters sensitive parameters before sending to Gateway
```

### Event Streaming

#### Stream All Events

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    async for event in client.stream_events():
        print(f"Event Type: {event.event_type}")
        print(f"Data: {event.data}")
        print(f"Event ID: {event.event_id}")
```

#### Filter Events by Type

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    async for event in client.stream_events(
        event_types=["tool_invoked", "server_registered", "server_health"]
    ):
        if event.event_type == "tool_invoked":
            process_tool_event(event)
        elif event.event_type == "server_registered":
            process_server_event(event)
```

#### Custom Endpoint

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    async for event in client.stream_events(
        endpoint="/api/v1/audit/stream",
        user_token="jwt-token",
    ):
        log_audit_event(event)
```

### Local Server (stdio)

#### Connect to Local Server

```python
async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
    local_server = await client.connect_local_server(
        command=["python", "my_server.py"],
        cwd="/path/to/server",
        env={"API_KEY": "test-key"},
        server_id="my-server",
    )

    # Check if running
    print(f"Running: {local_server.is_running}")

    # Send requests
    tools = await local_server.send_request("tools/list", {})
    result = await local_server.send_request("tools/call", {
        "name": "my_tool",
        "arguments": {"key": "value"}
    })

    # Send notifications (no response expected)
    await local_server.send_notification("notifications/progress", {
        "percent": 50
    })

    # Stop server
    await local_server.stop()
```

#### Multiple Local Servers

```python
async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
    # Start multiple servers
    server1 = await client.connect_local_server(
        command=["python", "server1.py"],
        server_id="server1",
    )
    server2 = await client.connect_local_server(
        command=["python", "server2.py"],
        server_id="server2",
    )

    # Use both servers
    result1 = await server1.send_request("tools/list", {})
    result2 = await server2.send_request("tools/list", {})

    # Health check all servers
    health = await client.health_check()
    print(health["stdio"])
    # {
    #   "server1": {"status": "running", "pid": 12345},
    #   "server2": {"status": "running", "pid": 12346}
    # }
```

---

## Advanced Usage

### Configuration Options

```python
from sark.gateway import GatewayClient, TransportMode

async with GatewayClient(
    # Connection settings
    gateway_url="http://gateway:8080",
    api_key="your-api-key",
    timeout=30.0,  # Default timeout in seconds
    max_connections=50,  # Max concurrent connections

    # Transport mode
    transport_mode=TransportMode.AUTO,  # AUTO, HTTP_ONLY, SSE_ONLY, STDIO_ONLY

    # Authorization
    opa_client=opa_client,  # Optional OPA client for authorization

    # Error handling
    enable_error_handling=True,  # Enable circuit breaker and retry
    circuit_breaker_config={
        "failure_threshold": 5,  # Open circuit after 5 failures
        "timeout_seconds": 30,   # Wait 30s before half-open
        "success_threshold": 2,  # Close after 2 successes in half-open
    },
    retry_config={
        "max_attempts": 3,      # Retry up to 3 times
        "initial_delay": 1.0,   # Start with 1s delay
        "max_delay": 30.0,      # Max delay 30s
        "exponential_base": 2.0,  # Exponential backoff
        "jitter": True,         # Add random jitter
    },
) as client:
    # Your code here
    pass
```

### Health Monitoring

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    # Perform some operations to initialize transports
    await client.list_servers()
    _ = client._get_sse_client()

    # Get health status
    health = await client.health_check()

    print(health)
    # {
    #   "http": {
    #     "status": "healthy",
    #     "cache_hit_rate": 0.92
    #   },
    #   "sse": {
    #     "status": "connected",
    #     "connection_state": "connected"
    #   },
    #   "error_handler": {
    #     "circuit_breaker": {
    #       "state": "closed",
    #       "failure_count": 0,
    #       ...
    #     },
    #     ...
    #   }
    # }
```

### Metrics Collection

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    # Perform operations
    for _ in range(10):
        await client.list_servers()

    # Get metrics
    metrics = client.get_metrics()

    print(metrics)
    # {
    #   "transport_mode": "auto",
    #   "active_transports": ["http"],
    #   "http_cache_hit_rate": 0.9,
    #   "error_handler": {
    #     "circuit_breaker": {
    #       "total_calls": 10,
    #       "total_failures": 0,
    #       "failure_rate": 0.0,
    #       ...
    #     },
    #     ...
    #   }
    # }
```

### Concurrent Operations

```python
import asyncio

async with GatewayClient(gateway_url="http://gateway:8080") as client:
    # Run multiple operations concurrently
    tasks = [
        client.get_server_info("server-1"),
        client.get_server_info("server-2"),
        client.get_server_info("server-3"),
        client.list_tools(server_name="postgres-mcp"),
        client.list_tools(server_name="redis-mcp"),
    ]

    results = await asyncio.gather(*tasks)

    servers = results[:3]
    tools = results[3:]
```

### Custom Timeouts

```python
async with GatewayClient(
    gateway_url="http://gateway:8080",
    timeout=10.0,  # Default 10s timeout
) as client:
    # Use default timeout
    result1 = await client.invoke_tool(...)

    # Override timeout for specific operation
    from sark.gateway.error_handler import with_timeout

    result2 = await with_timeout(
        client.invoke_tool,
        server_name="slow-server",
        tool_name="long_running_task",
        parameters={},
        timeout_seconds=60.0,  # 60s timeout for this specific call
    )
```

### Error Recovery

```python
from sark.gateway import CircuitBreakerError, RetryExhaustedError, TimeoutError

async with GatewayClient(gateway_url="http://gateway:8080") as client:
    try:
        result = await client.invoke_tool(...)
    except CircuitBreakerError:
        # Circuit is open - service is down
        print("Service temporarily unavailable")
        # Wait or use fallback
    except RetryExhaustedError:
        # All retries failed
        print("Operation failed after retries")
    except TimeoutError:
        # Operation timed out
        print("Operation timed out")
    except PermissionError as e:
        # OPA denied the request
        print(f"Access denied: {e}")
```

---

## Error Handling

The Gateway client includes comprehensive error handling. See [ERROR_HANDLING.md](./ERROR_HANDLING.md) for details.

### Built-in Error Handling

When `enable_error_handling=True` (default), the client provides:

1. **Circuit Breaker**: Prevents cascading failures
   - Opens after 5 consecutive failures
   - Waits 30 seconds before testing recovery
   - Closes after 2 successful calls

2. **Retry Logic**: Exponential backoff
   - Up to 3 retry attempts
   - Starts with 1s delay, doubles each time
   - Max delay of 30s
   - Random jitter to prevent thundering herd

3. **Timeout Handling**:
   - Default 30s timeout per operation
   - Configurable per-client or per-operation
   - Prevents hung requests

### Disable Error Handling

For testing or when you want manual control:

```python
async with GatewayClient(
    gateway_url="http://gateway:8080",
    enable_error_handling=False,
) as client:
    # No automatic retry or circuit breaking
    result = await client.invoke_tool(...)
```

---

## Best Practices

### 1. Use Context Managers

Always use async context managers to ensure proper cleanup:

```python
# ✅ Good - resources cleaned up automatically
async with GatewayClient(...) as client:
    result = await client.list_servers()

# ❌ Bad - resources may leak
client = GatewayClient(...)
result = await client.list_servers()
# Missing: await client.close()
```

### 2. Reuse Client Instances

Create one client instance and reuse it for multiple operations:

```python
# ✅ Good - connection pooling benefits
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    for i in range(100):
        result = await client.get_server_info(f"server-{i}")

# ❌ Bad - creates new connections each time
for i in range(100):
    async with GatewayClient(gateway_url="http://gateway:8080") as client:
        result = await client.get_server_info(f"server-{i}")
```

### 3. Use AUTO Transport Mode

Let the client choose the best transport:

```python
# ✅ Good - automatic selection
async with GatewayClient(
    gateway_url="http://gateway:8080",
    transport_mode=TransportMode.AUTO,
) as client:
    servers = await client.list_servers()  # Uses HTTP
    async for event in client.stream_events():  # Uses SSE
        pass
```

### 4. Handle Errors Appropriately

Different errors require different handling:

```python
from sark.gateway import CircuitBreakerError, RetryExhaustedError

async with GatewayClient(gateway_url="http://gateway:8080") as client:
    try:
        result = await client.invoke_tool(...)
    except CircuitBreakerError:
        # Service is down - wait before retry
        await asyncio.sleep(60)
        # Try alternative or degrade gracefully
    except RetryExhaustedError:
        # Permanent failure - log and alert
        logger.error("Tool invocation failed")
    except PermissionError:
        # Access denied - don't retry
        logger.warning("Access denied")
```

### 5. Monitor Metrics

Track client health and performance:

```python
async with GatewayClient(gateway_url="http://gateway:8080") as client:
    # Periodically check metrics
    while True:
        await asyncio.sleep(60)  # Every minute

        metrics = client.get_metrics()

        # Alert on low cache hit rate
        if metrics.get("http_cache_hit_rate", 0) < 0.8:
            logger.warning("Low cache hit rate")

        # Alert on circuit breaker open
        cb_state = metrics.get("error_handler", {}).get("circuit_breaker", {}).get("state")
        if cb_state == "open":
            logger.error("Circuit breaker is OPEN")
```

### 6. Use OPA for Authorization

Always integrate OPA for production deployments:

```python
from sark.services.policy.opa_client import OPAClient

opa_client = OPAClient(opa_url="http://opa:8181")

async with GatewayClient(
    gateway_url="http://gateway:8080",
    opa_client=opa_client,
) as client:
    # All tool invocations will be authorized
    result = await client.invoke_tool(
        server_name="postgres-mcp",
        tool_name="execute_query",
        parameters={"query": "SELECT 1"},
        user_token="user-jwt-token",
    )
```

### 7. Set Appropriate Timeouts

Different operations need different timeouts:

```python
async with GatewayClient(
    gateway_url="http://gateway:8080",
    timeout=10.0,  # Default for most operations
) as client:
    # Quick operations - use default
    servers = await client.list_servers()

    # Long-running operations - override timeout
    from sark.gateway.error_handler import with_timeout

    result = await with_timeout(
        client.invoke_tool,
        server_name="analytics-server",
        tool_name="run_report",
        parameters={"report_id": "monthly"},
        timeout_seconds=300.0,  # 5 minutes
    )
```

---

## Examples

### Example 1: Complete Workflow

```python
from sark.gateway import GatewayClient
from sark.services.policy.opa_client import OPAClient
import asyncio

async def main():
    opa_client = OPAClient(opa_url="http://opa:8181")

    async with GatewayClient(
        gateway_url="http://gateway:8080",
        api_key="gateway-api-key",
        opa_client=opa_client,
        timeout=30.0,
    ) as client:
        # 1. Discover servers
        print("=== Discovering Servers ===")
        servers = await client.list_all_servers()
        print(f"Found {len(servers)} servers")

        for server in servers:
            print(f"  - {server.server_name} ({server.health_status})")

        # 2. Discover tools for a specific server
        print("\n=== Discovering Tools ===")
        postgres_tools = await client.list_all_tools(server_name="postgres-mcp")
        print(f"Found {len(postgres_tools)} tools for postgres-mcp")

        for tool in postgres_tools:
            print(f"  - {tool.tool_name}: {tool.description}")

        # 3. Invoke a tool
        print("\n=== Invoking Tool ===")
        result = await client.invoke_tool(
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={
                "query": "SELECT COUNT(*) FROM users",
                "database": "production",
            },
            user_token="user-jwt-token",
        )
        print(f"Result: {result}")

        # 4. Check health
        print("\n=== Health Check ===")
        health = await client.health_check()
        print(f"HTTP Cache Hit Rate: {health['http']['cache_hit_rate']:.2%}")

        # 5. Get metrics
        print("\n=== Metrics ===")
        metrics = client.get_metrics()
        print(f"Active Transports: {metrics['active_transports']}")
        cb_metrics = metrics['error_handler']['circuit_breaker']
        print(f"Circuit Breaker: {cb_metrics['state']}")
        print(f"Total Calls: {cb_metrics['total_calls']}")
        print(f"Failure Rate: {cb_metrics['failure_rate']:.2%}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 2: Event Monitoring

```python
from sark.gateway import GatewayClient
import asyncio
import json

async def monitor_events():
    async with GatewayClient(gateway_url="http://gateway:8080") as client:
        print("Starting event monitor...")

        async for event in client.stream_events(
            event_types=["tool_invoked", "server_health", "error"]
        ):
            event_data = json.loads(event.data)

            if event.event_type == "tool_invoked":
                print(f"Tool: {event_data['tool_name']} on {event_data['server_name']}")
            elif event.event_type == "server_health":
                print(f"Health: {event_data['server_name']} -> {event_data['status']}")
            elif event.event_type == "error":
                print(f"ERROR: {event_data['message']}")

if __name__ == "__main__":
    asyncio.run(monitor_events())
```

### Example 3: Local Development with stdio

```python
from sark.gateway import GatewayClient, TransportMode
import asyncio

async def test_local_server():
    async with GatewayClient(transport_mode=TransportMode.STDIO_ONLY) as client:
        # Start local server
        print("Starting local server...")
        local_server = await client.connect_local_server(
            command=["python", "examples/my_mcp_server.py"],
            cwd=".",
            env={"DEBUG": "1"},
        )

        print(f"Server running with PID: {local_server.transport._process.pid}")

        # Test tools/list
        tools = await local_server.send_request("tools/list", {})
        print(f"Available tools: {tools}")

        # Test tool invocation
        result = await local_server.send_request("tools/call", {
            "name": "echo",
            "arguments": {"message": "Hello, World!"}
        })
        print(f"Result: {result}")

        # Clean up
        await local_server.stop()
        print("Server stopped")

if __name__ == "__main__":
    asyncio.run(test_local_server())
```

### Example 4: Error Handling & Recovery

```python
from sark.gateway import (
    GatewayClient,
    CircuitBreakerError,
    RetryExhaustedError,
    TimeoutError,
)
import asyncio

async def resilient_invocation():
    async with GatewayClient(
        gateway_url="http://gateway:8080",
        enable_error_handling=True,
        circuit_breaker_config={"failure_threshold": 3},
        retry_config={"max_attempts": 3},
    ) as client:
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                result = await client.invoke_tool(
                    server_name="unstable-server",
                    tool_name="flaky_operation",
                    parameters={},
                )
                print(f"Success: {result}")
                break

            except CircuitBreakerError:
                print("Circuit breaker OPEN - waiting 60s...")
                await asyncio.sleep(60)
                retry_count += 1

            except RetryExhaustedError:
                print("All retries exhausted - backing off...")
                await asyncio.sleep(30)
                retry_count += 1

            except TimeoutError:
                print("Timeout - trying again...")
                retry_count += 1

        if retry_count >= max_retries:
            print("Operation failed after all retries")

if __name__ == "__main__":
    asyncio.run(resilient_invocation())
```

---

## Next Steps

- [Error Handling Guide](./ERROR_HANDLING.md) - Deep dive into error handling
- [HTTP Transport](./HTTP_TRANSPORT.md) - HTTP transport details
- [SSE Transport](./SSE_TRANSPORT.md) - SSE transport details
- [stdio Transport](./STDIO_TRANSPORT.md) - stdio transport details
- [MCP Gateway Integration Plan](../MCP_GATEWAY_INTEGRATION_PLAN.md) - Architecture overview

---

## Support

For issues, questions, or contributions:

- GitHub Issues: https://github.com/your-org/sark/issues
- Documentation: https://docs.your-org.com/sark
- MCP Specification: https://spec.modelcontextprotocol.io
