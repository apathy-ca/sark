# Gateway HTTP Transport

## Overview

The Gateway HTTP Transport provides async HTTP client functionality for communicating with MCP Gateway servers. It includes features for server discovery, tool listing, tool invocation, response caching, and OPA authorization integration.

## Features

- **Async HTTP Client**: Built on `httpx` with full async/await support
- **Connection Pooling**: Configurable connection pool (default: 50 concurrent connections)
- **Pagination Support**: Handles large result sets (1000+ servers) automatically
- **TTL Caching**: Response caching with configurable TTL (default: 5 minutes)
- **OPA Integration**: Optional authorization checks before tool invocation
- **Retry Logic**: Exponential backoff retry for transient failures
- **Comprehensive Error Handling**: Fail-safe patterns with detailed logging

## Installation

The HTTP transport is included in the `sark.gateway.transports` package:

```python
from sark.gateway.transports import GatewayHTTPClient
```

## Basic Usage

### Creating a Client

```python
from sark.gateway.transports import GatewayHTTPClient

# Basic client
async with GatewayHTTPClient(
    base_url="http://gateway:8080",
    api_key="your-api-key",
) as client:
    # Use client
    pass
```

### With OPA Authorization

```python
from sark.gateway.transports import GatewayHTTPClient
from sark.services.policy.opa_client import OPAClient

opa_client = OPAClient(opa_url="http://opa:8181")

async with GatewayHTTPClient(
    base_url="http://gateway:8080",
    api_key="your-api-key",
    opa_client=opa_client,
) as client:
    # Client will check OPA before tool invocations
    pass
```

## Configuration

### Client Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | Required | Gateway base URL (e.g., "http://gateway:8080") |
| `api_key` | `str \| None` | `None` | Optional API key for Gateway authentication |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `max_connections` | `int` | `50` | Maximum concurrent connections |
| `opa_client` | `OPAClient \| None` | `None` | Optional OPA client for authorization |
| `cache_enabled` | `bool` | `True` | Enable response caching |
| `cache_ttl_seconds` | `int` | `300` | Cache TTL in seconds (5 minutes) |
| `max_retries` | `int` | `3` | Maximum retry attempts |

### Example: Custom Configuration

```python
async with GatewayHTTPClient(
    base_url="http://gateway:8080",
    timeout=60.0,
    max_connections=100,
    cache_ttl_seconds=600,  # 10 minutes
    max_retries=5,
) as client:
    pass
```

## API Reference

### Server Discovery

#### `list_servers()`

List MCP servers with pagination support.

```python
servers = await client.list_servers(
    page=1,
    page_size=100,
    use_cache=True,
)

for server in servers:
    print(f"{server.server_name}: {server.health_status}")
```

**Parameters:**
- `page` (int): Page number (1-indexed), default: 1
- `page_size` (int): Items per page (max 1000), default: 100
- `use_cache` (bool): Whether to use cache, default: True

**Returns:** `list[GatewayServerInfo]`

#### `list_all_servers()`

Automatically paginate through all servers.

```python
# Fetch ALL servers across multiple pages
all_servers = await client.list_all_servers(page_size=100)
print(f"Total servers: {len(all_servers)}")
```

**Parameters:**
- `page_size` (int): Items per page (max 1000), default: 100
- `use_cache` (bool): Whether to use cache, default: True

**Returns:** `list[GatewayServerInfo]`

#### `get_server()`

Get specific server by name.

```python
server = await client.get_server("postgres-mcp")
print(f"Tools: {server.tools_count}")
print(f"Sensitivity: {server.sensitivity_level}")
```

**Parameters:**
- `server_name` (str): Server name to retrieve
- `use_cache` (bool): Whether to use cache, default: True

**Returns:** `GatewayServerInfo`

**Raises:** `httpx.HTTPStatusError` if server not found (404)

### Tool Discovery

#### `list_tools()`

List available tools, optionally filtered by server.

```python
# List all tools
all_tools = await client.list_tools()

# List tools for specific server
postgres_tools = await client.list_tools(server_name="postgres-mcp")

for tool in postgres_tools:
    print(f"{tool.tool_name}: {tool.description}")
```

**Parameters:**
- `server_name` (str | None): Optional server filter, default: None
- `page` (int): Page number (1-indexed), default: 1
- `page_size` (int): Items per page, default: 100
- `use_cache` (bool): Whether to use cache, default: True

**Returns:** `list[GatewayToolInfo]`

### Tool Invocation

#### `invoke_tool()`

Invoke a tool via Gateway with optional OPA authorization.

```python
result = await client.invoke_tool(
    server_name="postgres-mcp",
    tool_name="execute_query",
    parameters={
        "query": "SELECT * FROM users LIMIT 10",
        "database": "production",
    },
    user_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    check_authorization=True,  # Check OPA before invoking
)

if result["status"] == "success":
    print(f"Result: {result['data']}")
```

**Parameters:**
- `server_name` (str): Target MCP server name
- `tool_name` (str): Tool to invoke
- `parameters` (dict[str, Any]): Tool parameters
- `user_token` (str): User JWT token for authorization
- `check_authorization` (bool): Check OPA first, default: True

**Returns:** `dict[str, Any]` - Tool invocation result

**Raises:**
- `PermissionError`: If OPA authorization fails
- `httpx.HTTPStatusError`: If Gateway request fails

**Authorization Flow:**
1. If `check_authorization=True` and OPA client is configured:
   - Check authorization via OPA
   - Use filtered parameters if provided by OPA
   - Deny if OPA denies
2. Forward request to Gateway with user JWT
3. Gateway validates with SARK authorization endpoint
4. Gateway routes to MCP server
5. Return result

### Health Check

#### `health_check()`

Check Gateway health status.

```python
health = await client.health_check()
if health["healthy"]:
    print("Gateway is healthy!")
else:
    print(f"Gateway unhealthy: {health.get('error')}")
```

**Returns:** `dict[str, bool]` with keys:
- `healthy` (bool): Overall health status
- `details` (dict): Health check details (if available)
- `error` (str): Error message (if unhealthy)

## Caching

### Cache Metrics

Get cache performance metrics:

```python
metrics = client.get_cache_metrics()
print(f"Hit rate: {metrics['hit_rate']:.1%}")
print(f"Cache size: {metrics['cache_size']}/{metrics['cache_maxsize']}")
print(f"Total requests: {metrics['total_requests']}")
```

**Metrics:**
- `cache_enabled` (bool): Whether caching is enabled
- `cache_size` (int): Current number of cached entries
- `cache_maxsize` (int): Maximum cache size (1000)
- `cache_ttl_seconds` (int): Cache TTL in seconds
- `cache_hits` (int): Number of cache hits
- `cache_misses` (int): Number of cache misses
- `total_requests` (int): Total cacheable requests
- `hit_rate` (float): Cache hit rate (0.0-1.0)

### Clear Cache

```python
client.clear_cache()
```

### Caching Behavior

- **GET requests**: Cached by default (servers, tools)
- **POST requests**: Never cached (tool invocations)
- **Health checks**: Never cached
- **Cache key**: Endpoint + query parameters
- **TTL**: Configurable per client (default: 5 minutes)

## Error Handling

### Retry Logic

The client automatically retries failed requests with exponential backoff:

- **Server errors (5xx)**: Retried up to `max_retries` times
- **Client errors (4xx)**: Not retried (fail immediately)
- **Network errors**: Retried up to `max_retries` times
- **Backoff**: 1s, 2s, 4s (exponential)

```python
# Custom retry configuration
async with GatewayHTTPClient(
    base_url="http://gateway:8080",
    max_retries=5,  # Retry up to 5 times
) as client:
    # Retries happen automatically
    servers = await client.list_servers()
```

### Error Handling Example

```python
import httpx

try:
    result = await client.invoke_tool(
        server_name="postgres-mcp",
        tool_name="execute_query",
        parameters={"query": "SELECT 1"},
        user_token="token",
    )
except PermissionError as e:
    print(f"Authorization denied: {e}")
except httpx.HTTPStatusError as e:
    print(f"HTTP error {e.response.status_code}: {e}")
except httpx.RequestError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance

### Benchmarks

- **p95 latency**: <100ms (cached responses)
- **p95 latency**: <200ms (uncached, local network)
- **Connection pool**: Supports 50 concurrent requests
- **Cache hit rate**: >80% in typical usage
- **Throughput**: 500+ requests/second (cached)

### Optimization Tips

1. **Enable Caching**: Keep cache enabled for read operations
2. **Tune Connection Pool**: Increase `max_connections` for high concurrency
3. **Adjust TTL**: Balance freshness vs. performance
4. **Reuse Client**: Use a single client instance (singleton pattern)
5. **Pagination**: Use appropriate `page_size` (100-500 recommended)

### Example: High-Performance Setup

```python
# Optimized for high throughput
async with GatewayHTTPClient(
    base_url="http://gateway:8080",
    max_connections=100,  # Higher connection pool
    cache_ttl_seconds=600,  # Longer cache TTL
    timeout=10.0,  # Shorter timeout
) as client:
    # Fetch all servers efficiently
    all_servers = await client.list_all_servers(page_size=500)
```

## OPA Authorization Integration

### Setup

```python
from sark.gateway.transports import GatewayHTTPClient
from sark.services.policy.opa_client import OPAClient

# Initialize OPA client
opa_client = OPAClient(
    opa_url="http://opa:8181",
    timeout=5.0,
)

# Create HTTP client with OPA
client = GatewayHTTPClient(
    base_url="http://gateway:8080",
    opa_client=opa_client,
)
```

### Authorization Flow

When `check_authorization=True` (default for `invoke_tool`):

1. **OPA Check**: Query OPA with user context, action, server, and tool
2. **Parameter Filtering**: Apply OPA-filtered parameters if provided
3. **Deny on Failure**: Raise `PermissionError` if OPA denies
4. **Gateway Request**: Forward to Gateway with user JWT
5. **SARK Validation**: Gateway validates with SARK authorization endpoint
6. **MCP Routing**: Gateway routes to MCP server
7. **Return Result**: Return tool invocation result

### Example: Filtered Parameters

OPA can filter sensitive parameters:

```python
# User requests query with sensitive data
parameters = {
    "query": "SELECT * FROM users",
    "include_ssn": True,  # Sensitive parameter
}

# OPA filters parameters
result = await client.invoke_tool(
    server_name="postgres-mcp",
    tool_name="execute_query",
    parameters=parameters,
    user_token=user_token,
    check_authorization=True,
)

# OPA may have filtered 'include_ssn' based on policy
```

## Best Practices

### 1. Use Context Managers

```python
# ✅ Recommended
async with GatewayHTTPClient(base_url="http://gateway:8080") as client:
    servers = await client.list_servers()

# ❌ Not recommended
client = GatewayHTTPClient(base_url="http://gateway:8080")
servers = await client.list_servers()
await client.close()  # Easy to forget!
```

### 2. Reuse Client Instances

```python
# ✅ Recommended - Singleton pattern
_http_client: GatewayHTTPClient | None = None

async def get_http_client() -> GatewayHTTPClient:
    global _http_client
    if _http_client is None:
        _http_client = GatewayHTTPClient(base_url="http://gateway:8080")
    return _http_client
```

### 3. Handle Errors Gracefully

```python
# ✅ Recommended
try:
    result = await client.invoke_tool(...)
except PermissionError:
    # Handle authorization failure
    return {"error": "Permission denied"}
except httpx.HTTPStatusError as e:
    # Handle HTTP errors
    if e.response.status_code == 404:
        return {"error": "Tool not found"}
    raise
```

### 4. Monitor Cache Performance

```python
# ✅ Recommended - Monitor cache metrics
metrics = client.get_cache_metrics()
if metrics["hit_rate"] < 0.7:
    # Low hit rate - consider increasing TTL
    logger.warning("Low cache hit rate", hit_rate=metrics["hit_rate"])
```

## Troubleshooting

### Issue: Low Cache Hit Rate

**Symptoms:** `hit_rate < 0.5` in cache metrics

**Solutions:**
- Increase `cache_ttl_seconds`
- Check if requests have unique parameters
- Verify `use_cache=True` in calls

### Issue: Connection Pool Exhausted

**Symptoms:** `HTTPError: Connection pool exhausted`

**Solutions:**
- Increase `max_connections`
- Reduce concurrent requests
- Check for connection leaks (not closing client)

### Issue: Timeout Errors

**Symptoms:** `httpx.TimeoutException`

**Solutions:**
- Increase `timeout` value
- Check Gateway health
- Verify network connectivity

### Issue: Authorization Always Fails

**Symptoms:** `PermissionError` on all invocations

**Solutions:**
- Verify OPA client is configured correctly
- Check OPA policies are loaded
- Verify user JWT token is valid
- Test with `check_authorization=False` to isolate issue

## Migration Guide

### From Legacy `GatewayClient`

```python
# Old (placeholder client)
from sark.services.gateway.client import GatewayClient

client = GatewayClient(
    base_url="http://gateway:8080",
    api_key="key",
)
servers = await client.list_servers()  # Returns empty list

# New (full HTTP client)
from sark.gateway.transports import GatewayHTTPClient

async with GatewayHTTPClient(
    base_url="http://gateway:8080",
    api_key="key",
) as client:
    servers = await client.list_servers()  # Returns actual servers
```

**Key Differences:**
- Async context manager support
- Real HTTP requests (not placeholders)
- Pagination support
- Caching support
- OPA integration
- Retry logic

## See Also

- [SSE Transport Documentation](SSE_TRANSPORT.md)
- [OPA Policy Guide](../OPA_POLICY_GUIDE.md)
- [Gateway Integration Plan](../MCP_GATEWAY_INTEGRATION_PLAN.md)
