# MCP Transport Types Comparison

## Overview
This document compares the three MCP transport types: HTTP, stdio (standard input/output), and SSE (Server-Sent Events). Each has different use cases, performance characteristics, and security implications.

## Transport Architecture Overview

```mermaid
graph TB
    subgraph "AI Client"
        CLIENT[AI Assistant<br/>Claude, GPT, etc.]
    end

    subgraph "SARK Governance Layer"
        SARK[SARK Gateway]
    end

    subgraph "MCP Servers - Different Transports"
        direction TB

        subgraph "HTTP Transport"
            HTTP_MCP[MCP Server<br/>HTTP REST API]
            HTTP_DESC[• Remote server<br/>• Stateless<br/>• Request/Response<br/>• Port: 8080/443]
        end

        subgraph "stdio Transport"
            STDIO_MCP[MCP Server<br/>Local Process]
            STDIO_DESC[• Local execution<br/>• Standard I/O<br/>• Subprocess<br/>• No network]
        end

        subgraph "SSE Transport"
            SSE_MCP[MCP Server<br/>Server-Sent Events]
            SSE_DESC[• Streaming<br/>• Long-lived connection<br/>• Push updates<br/>• HTTP/2]
        end
    end

    CLIENT -->|REST API| SARK
    SARK -->|HTTP POST| HTTP_MCP
    SARK -->|Process spawn| STDIO_MCP
    SARK -->|EventSource| SSE_MCP

    HTTP_MCP -.-> HTTP_DESC
    STDIO_MCP -.-> STDIO_DESC
    SSE_MCP -.-> SSE_DESC

    classDef httpColor fill:#4a90e2,stroke:#2e5c8a,color:#fff
    classDef stdioColor fill:#50c878,stroke:#2d7a4a,color:#fff
    classDef sseColor fill:#ffd43b,stroke:#e6b800,color:#000

    class HTTP_MCP,HTTP_DESC httpColor
    class STDIO_MCP,STDIO_DESC stdioColor
    class SSE_MCP,SSE_DESC sseColor
```

## HTTP Transport

### Request/Response Flow

```mermaid
sequenceDiagram
    participant AI as AI Client
    participant SARK as SARK Gateway
    participant MCP as MCP Server (HTTP)
    participant Backend as Backend System

    Note over AI,Backend: HTTP Transport - Synchronous Request/Response

    AI->>SARK: POST /api/v1/tools/invoke<br/>{tool_id: "...", params: {...}}
    SARK->>SARK: Authenticate & Authorize

    SARK->>MCP: POST https://mcp-server.internal:8443/mcp/v1<br/>Content-Type: application/json<br/>Authorization: Bearer {token}<br/>{<br/>  jsonrpc: "2.0",<br/>  method: "tools/call",<br/>  params: {<br/>    name: "query_database",<br/>    arguments: {query: "SELECT ..."}}<br/>  }<br/>}

    MCP->>MCP: Parse JSON-RPC request
    MCP->>MCP: Validate parameters
    MCP->>Backend: Execute query
    Backend-->>MCP: Query results

    MCP->>MCP: Format MCP response
    MCP-->>SARK: 200 OK<br/>{<br/>  jsonrpc: "2.0",<br/>  result: {<br/>    content: [{<br/>      type: "text",<br/>      text: "Results: ..."<br/>    }]<br/>  }<br/>}

    SARK->>SARK: Log audit event
    SARK-->>AI: Return results

    Note over AI,Backend: Connection closed after response
```

### HTTP Configuration Example

```json
{
  "name": "finance-mcp-server",
  "transport": "http",
  "endpoint": "https://finance-mcp.internal.company.com:8443",
  "health_endpoint": "https://finance-mcp.internal.company.com:8443/health",
  "capabilities": ["tools", "resources"],
  "tls": {
    "enabled": true,
    "verify_cert": true,
    "client_cert_required": true
  },
  "timeout_seconds": 30,
  "retry_policy": {
    "max_retries": 3,
    "backoff": "exponential"
  }
}
```

### HTTP Pros & Cons

**Advantages:**
- ✅ **Scalable**: Can run on multiple servers behind load balancer
- ✅ **Remote**: MCP server can be anywhere on network
- ✅ **Stateless**: No connection state, easy to restart
- ✅ **Standard**: Works with existing HTTP infrastructure (proxies, load balancers, WAF)
- ✅ **Secure**: TLS encryption, certificate auth, mTLS support
- ✅ **Monitored**: Standard HTTP metrics and logging

**Disadvantages:**
- ❌ **Network Overhead**: HTTP headers, TCP handshake per request
- ❌ **Latency**: Higher latency than local execution
- ❌ **Firewall**: Requires open network ports
- ❌ **Request/Response Only**: No streaming or push notifications

**Best Use Cases:**
- Production MCP servers serving multiple clients
- Cloud-deployed MCP services
- Enterprise-managed MCP servers
- High-availability requirements

---

## stdio Transport

### Process Execution Flow

```mermaid
sequenceDiagram
    participant AI as AI Client
    participant SARK as SARK Gateway
    participant OS as Operating System
    participant PROC as MCP Process<br/>(stdio)
    participant FS as File System

    Note over AI,FS: stdio Transport - Local Process Execution

    AI->>SARK: POST /api/v1/tools/invoke<br/>{tool_id: "local_tool", params: {...}}
    SARK->>SARK: Authenticate & Authorize

    SARK->>OS: spawn process:<br/>python3 /opt/mcp-servers/file-tools/server.py

    OS->>PROC: Create process (stdin/stdout/stderr pipes)
    PROC->>PROC: Initialize MCP server
    PROC-->>SARK: READY (via stdout)

    SARK->>PROC: Write to stdin:<br/>{<br/>  jsonrpc: "2.0",<br/>  method: "tools/call",<br/>  params: {<br/>    name: "read_file",<br/>    arguments: {path: "/data/report.txt"}<br/>  }<br/>}\n

    PROC->>PROC: Parse JSON from stdin
    PROC->>PROC: Validate parameters

    PROC->>FS: Read file: /data/report.txt
    FS-->>PROC: File contents

    PROC->>PROC: Format response

    PROC->>SARK: Write to stdout:<br/>{<br/>  jsonrpc: "2.0",<br/>  result: {<br/>    content: [{<br/>      type: "text",<br/>      text: "File contents: ..."<br/>    }]<br/>  }<br/>}\n

    SARK->>SARK: Log audit event
    SARK-->>AI: Return results

    alt Keep Process Alive
        Note over PROC: Process remains running<br/>for next request
    else Terminate Process
        SARK->>PROC: Send EOF or SIGTERM
        PROC->>OS: Exit process
    end
```

### stdio Configuration Example

```json
{
  "name": "local-file-tools",
  "transport": "stdio",
  "command": "/usr/bin/python3 /opt/mcp-servers/file-tools/server.py",
  "env": {
    "MCP_SERVER_NAME": "file-tools",
    "DATA_DIR": "/data",
    "LOG_LEVEL": "INFO"
  },
  "working_directory": "/opt/mcp-servers/file-tools",
  "capabilities": ["tools"],
  "process_management": {
    "keep_alive": true,
    "idle_timeout_seconds": 300,
    "max_concurrent": 10
  }
}
```

### stdio Pros & Cons

**Advantages:**
- ✅ **Zero Latency**: No network overhead, local execution
- ✅ **Simple**: No HTTP server needed, just stdin/stdout
- ✅ **Secure**: No network exposure, process isolation
- ✅ **Portable**: Works on any OS with process execution
- ✅ **Lightweight**: Minimal dependencies
- ✅ **File Access**: Direct access to local file system

**Disadvantages:**
- ❌ **Local Only**: Cannot access remote MCP servers
- ❌ **Process Management**: Need to spawn/kill processes
- ❌ **Resource Limits**: Limited by single machine resources
- ❌ **Not Scalable**: Cannot distribute across multiple machines
- ❌ **No Load Balancing**: All requests to same process
- ❌ **Process Crashes**: Need restart logic

**Best Use Cases:**
- Development and testing
- Local tools (file operations, system commands)
- Single-user scenarios
- CLI applications
- Resource-constrained environments

---

## SSE (Server-Sent Events) Transport

### Streaming Connection Flow

```mermaid
sequenceDiagram
    participant AI as AI Client
    participant SARK as SARK Gateway
    participant MCP as MCP Server (SSE)
    participant Backend as Backend System

    Note over AI,Backend: SSE Transport - Streaming Connection

    AI->>SARK: POST /api/v1/tools/invoke<br/>{tool_id: "streaming_tool", params: {...}}
    SARK->>SARK: Authenticate & Authorize

    rect rgb(220, 240, 255)
        Note over SARK,MCP: Establish SSE Connection (if not exists)
        SARK->>MCP: GET https://mcp-server.internal/mcp/v1/sse<br/>Accept: text/event-stream<br/>Authorization: Bearer {token}

        MCP-->>SARK: 200 OK<br/>Content-Type: text/event-stream<br/>Connection: keep-alive

        Note over SARK,MCP: Long-lived HTTP connection established
    end

    rect rgb(220, 255, 220)
        Note over SARK,Backend: Send Tool Request
        SARK->>MCP: event: request<br/>data: {<br/>data:   "jsonrpc": "2.0",<br/>data:   "method": "tools/call",<br/>data:   "params": {<br/>data:     "name": "analyze_data",<br/>data:     "arguments": {...}<br/>data:   }<br/>data: }<br/><br/>

        MCP->>MCP: Parse event
        MCP->>Backend: Start analysis
    end

    rect rgb(255, 240, 220)
        Note over MCP,SARK: Stream Progress Updates

        loop While processing
            Backend-->>MCP: Progress update
            MCP->>SARK: event: progress<br/>data: {<br/>data:   "status": "processing",<br/>data:   "percent": 25,<br/>data:   "message": "Analyzing chunk 1/4..."<br/>data: }<br/><br/>

            SARK-->>AI: Forward progress update
        end
    end

    rect rgb(255, 220, 220)
        Note over MCP,SARK: Stream Final Result

        Backend-->>MCP: Analysis complete

        MCP->>SARK: event: result<br/>data: {<br/>data:   "jsonrpc": "2.0",<br/>data:   "result": {<br/>data:     "content": [{<br/>data:       "type": "text",<br/>data:       "text": "Analysis results: ..."<br/>data:     }]<br/>data:   }<br/>data: }<br/><br/>

        SARK->>SARK: Log audit event
        SARK-->>AI: Return final results
    end

    Note over SARK,MCP: Connection remains open for future requests
```

### SSE Configuration Example

```json
{
  "name": "analytics-mcp-server",
  "transport": "sse",
  "endpoint": "https://analytics-mcp.internal.company.com/mcp/v1/sse",
  "capabilities": ["tools", "resources"],
  "connection": {
    "keep_alive": true,
    "reconnect": true,
    "reconnect_interval_seconds": 5,
    "heartbeat_interval_seconds": 30
  },
  "streaming": {
    "buffer_size_kb": 64,
    "max_message_size_kb": 1024
  }
}
```

### SSE Event Format

```
event: progress
id: 123
data: {"status": "processing", "percent": 25}

event: log
id: 124
data: {"level": "info", "message": "Starting analysis"}

event: result
id: 125
data: {"jsonrpc": "2.0", "result": {...}}

event: error
id: 126
data: {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error"}}
```

### SSE Pros & Cons

**Advantages:**
- ✅ **Real-time Updates**: Stream progress, logs, intermediate results
- ✅ **Efficient**: Single connection for multiple requests
- ✅ **Push Notifications**: Server can push updates without polling
- ✅ **Long-running Tasks**: Perfect for tasks that take minutes/hours
- ✅ **HTTP-based**: Works with existing infrastructure
- ✅ **Reconnection**: Built-in automatic reconnection

**Disadvantages:**
- ❌ **Stateful**: Requires connection management
- ❌ **Complexity**: More complex than request/response
- ❌ **One-way**: Server to client only (need separate channel for requests)
- ❌ **Connection Limits**: Limited concurrent connections per client
- ❌ **Proxy Issues**: Some proxies don't support long-lived connections
- ❌ **Resource Usage**: Keeps connection open, uses server resources

**Best Use Cases:**
- Long-running data analysis or processing
- Real-time monitoring and dashboards
- Progress reporting for multi-step workflows
- Live log streaming
- Continuous data feeds

---

## Transport Comparison Matrix

```mermaid
graph TB
    subgraph "Transport Comparison"
        direction TB

        HEADER[Feature Comparison Matrix]

        HTTP_FEAT[HTTP Transport]
        STDIO_FEAT[stdio Transport]
        SSE_FEAT[SSE Transport]
    end

    HTTP_FEAT --> HTTP_TABLE["
    <table>
    <tr><th>Feature</th><th>Rating</th></tr>
    <tr><td>Latency</td><td>⭐⭐⭐ (50-200ms)</td></tr>
    <tr><td>Scalability</td><td>⭐⭐⭐⭐⭐ (Excellent)</td></tr>
    <tr><td>Security</td><td>⭐⭐⭐⭐ (TLS, mTLS)</td></tr>
    <tr><td>Setup Complexity</td><td>⭐⭐⭐ (Moderate)</td></tr>
    <tr><td>Monitoring</td><td>⭐⭐⭐⭐⭐ (Standard)</td></tr>
    <tr><td>Streaming</td><td>❌ (No)</td></tr>
    </table>
    "]

    STDIO_FEAT --> STDIO_TABLE["
    <table>
    <tr><th>Feature</th><th>Rating</th></tr>
    <tr><td>Latency</td><td>⭐⭐⭐⭐⭐ (<10ms)</td></tr>
    <tr><td>Scalability</td><td>⭐⭐ (Limited)</td></tr>
    <tr><td>Security</td><td>⭐⭐⭐⭐⭐ (Isolated)</td></tr>
    <tr><td>Setup Complexity</td><td>⭐⭐⭐⭐⭐ (Simple)</td></tr>
    <tr><td>Monitoring</td><td>⭐⭐ (Limited)</td></tr>
    <tr><td>Streaming</td><td>✅ (via stdout)</td></tr>
    </table>
    "]

    SSE_FEAT --> SSE_TABLE["
    <table>
    <tr><th>Feature</th><th>Rating</th></tr>
    <tr><td>Latency</td><td>⭐⭐⭐⭐ (Real-time)</td></tr>
    <tr><td>Scalability</td><td>⭐⭐⭐⭐ (Good)</td></tr>
    <tr><td>Security</td><td>⭐⭐⭐⭐ (TLS)</td></tr>
    <tr><td>Setup Complexity</td><td>⭐⭐ (Complex)</td></tr>
    <tr><td>Monitoring</td><td>⭐⭐⭐⭐ (Good)</td></tr>
    <tr><td>Streaming</td><td>✅ (Native)</td></tr>
    </table>
    "]

    style HTTP_FEAT fill:#4a90e2,color:#fff
    style STDIO_FEAT fill:#50c878,color:#fff
    style SSE_FEAT fill:#ffd43b,color:#000
```

## Performance Characteristics

| Metric | HTTP | stdio | SSE |
|--------|------|-------|-----|
| **Connection Setup** | 50-100ms (TCP + TLS) | <1ms (process spawn cached) | 50-100ms (initial), then reused |
| **Request Latency** | 50-200ms | <10ms | 10-50ms (connection exists) |
| **Throughput** | 100-10,000 req/s | 1,000-100,000 req/s | Varies (streaming) |
| **Memory Overhead** | Low (per request) | Medium (process memory) | High (connection state) |
| **Network Bandwidth** | High (HTTP headers) | None (local) | Medium (efficient streaming) |
| **Max Concurrent** | Unlimited (horizontal scaling) | Limited (process count) | Limited (connection limits) |

## Security Comparison

| Security Feature | HTTP | stdio | SSE |
|------------------|------|-------|-----|
| **Encryption** | ✅ TLS 1.3 | ❌ Not needed (local) | ✅ TLS 1.3 |
| **Authentication** | ✅ Bearer tokens, mTLS | ✅ Process isolation | ✅ Bearer tokens |
| **Authorization** | ✅ SARK OPA policies | ✅ SARK OPA policies | ✅ SARK OPA policies |
| **Network Isolation** | ❌ Exposed on network | ✅ No network exposure | ❌ Exposed on network |
| **Certificate Auth** | ✅ Client certificates | ❌ N/A | ✅ Client certificates |
| **Audit Logging** | ✅ Full request/response | ✅ stdin/stdout logs | ✅ Event stream logs |

## Decision Tree: Which Transport to Use?

```mermaid
graph TB
    START{Choose MCP Transport}

    START -->|Need real-time updates?| SSE_Q{SSE Requirements}
    START -->|Simple, local tools?| STDIO_Q{stdio Requirements}
    START -->|Production, scalable?| HTTP_Q{HTTP Requirements}

    SSE_Q -->|Long-running tasks| SSE[Use SSE Transport]
    SSE_Q -->|Progress updates needed| SSE
    SSE_Q -->|Streaming data| SSE

    STDIO_Q -->|Local file access| STDIO[Use stdio Transport]
    STDIO_Q -->|Development/testing| STDIO
    STDIO_Q -->|CLI tools| STDIO
    STDIO_Q -->|Single user| STDIO

    HTTP_Q -->|Multiple clients| HTTP[Use HTTP Transport]
    HTTP_Q -->|Cloud deployment| HTTP
    HTTP_Q -->|Load balancing needed| HTTP
    HTTP_Q -->|Enterprise production| HTTP

    style SSE fill:#ffd43b,color:#000
    style STDIO fill:#50c878,color:#fff
    style HTTP fill:#4a90e2,color:#fff
```

## Transport Selection Guidelines

### Use HTTP When:
- ✅ Deploying to cloud or multiple servers
- ✅ Need horizontal scaling and load balancing
- ✅ Serving multiple concurrent clients
- ✅ Integrating with existing HTTP infrastructure
- ✅ Require enterprise security (mTLS, WAF, etc.)
- ✅ **Recommendation**: Default choice for production

### Use stdio When:
- ✅ Building local development tools
- ✅ Need direct file system access
- ✅ Single-user CLI applications
- ✅ Minimal latency requirements (<10ms)
- ✅ No network connectivity available
- ✅ **Recommendation**: Development, testing, local tools

### Use SSE When:
- ✅ Long-running tasks (minutes to hours)
- ✅ Need progress updates during execution
- ✅ Real-time monitoring or dashboards
- ✅ Live log streaming
- ✅ Continuous data feeds
- ✅ **Recommendation**: Analytics, monitoring, real-time systems

## Code Examples

### HTTP Transport - Client

```python
import requests

response = requests.post(
    "https://mcp-server.company.com/mcp/v1",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_TOKEN"
    },
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "query_database",
            "arguments": {"query": "SELECT * FROM users LIMIT 10"}
        },
        "id": 1
    }
)

result = response.json()
print(result["result"])
```

### stdio Transport - Client

```python
import subprocess
import json

# Spawn MCP server process
proc = subprocess.Popen(
    ["python3", "mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

# Send request
request = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "read_file",
        "arguments": {"path": "/data/report.txt"}
    },
    "id": 1
}

proc.stdin.write(json.dumps(request) + "\n")
proc.stdin.flush()

# Read response
response_line = proc.stdout.readline()
result = json.loads(response_line)
print(result["result"])
```

### SSE Transport - Client

```python
import sseclient
import requests

# Establish SSE connection
response = requests.get(
    "https://mcp-server.company.com/mcp/v1/sse",
    headers={
        "Accept": "text/event-stream",
        "Authorization": "Bearer YOUR_TOKEN"
    },
    stream=True
)

client = sseclient.SSEClient(response)

# Send request (via separate channel or initial query params)
# ...

# Listen for events
for event in client.events():
    if event.event == "progress":
        print(f"Progress: {event.data}")
    elif event.event == "result":
        print(f"Result: {event.data}")
        break
```

## Monitoring & Observability

| Aspect | HTTP | stdio | SSE |
|--------|------|-------|-----|
| **Metrics** | Standard HTTP metrics (latency, throughput, errors) | Process metrics (CPU, memory, exit codes) | Connection metrics + event counts |
| **Logging** | Access logs, error logs | stdout/stderr capture | Event stream logs |
| **Tracing** | Distributed tracing (OpenTelemetry) | Local tracing only | Distributed tracing |
| **Health Checks** | HTTP /health endpoint | Process alive check | Connection heartbeat |
| **Alerting** | HTTP error rates, latency spikes | Process crashes, resource limits | Connection drops, event errors |

## Next Steps

- See [MCP Architecture](01_mcp_architecture.md) for overall system design
- See [Tool Invocation Flow](02_tool_invocation_flow.md) for detailed request flow
- See [API Reference](../API_REFERENCE.md) for transport configuration
