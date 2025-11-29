# gRPC Adapter Example

This example demonstrates how to use the SARK gRPC Adapter to govern gRPC services.

## Overview

The gRPC Adapter enables SARK to:
- Discover gRPC services via reflection
- Govern access to gRPC methods
- Handle all RPC types (unary, streaming, client streaming, bidirectional)
- Support mTLS and token-based authentication
- Pool connections and load balance

## Files

- `example_service.proto` - Example protobuf service definition
- `basic_example.py` - Basic usage of gRPC adapter
- `streaming_example.py` - Server streaming RPC example
- `authenticated_example.py` - mTLS and token auth examples
- `bidirectional_chat_example.py` - **NEW!** Enhanced bidirectional streaming demo
- `mock_grpc_server.py` - Mock gRPC server for testing

## Prerequisites

```bash
pip install grpcio grpcio-tools grpcio-reflection
```

## Running the Examples

### 1. Start the Mock Server

```bash
python mock_grpc_server.py
```

This starts a gRPC server on `localhost:50051` with reflection enabled.

### 2. Run Basic Example

```bash
python basic_example.py
```

This demonstrates:
- Service discovery
- Capability listing
- Unary RPC invocation

### 3. Run Streaming Example

```bash
python streaming_example.py
```

This demonstrates:
- Server streaming
- Client streaming
- Bidirectional streaming

### 4. Run Authenticated Example

```bash
python authenticated_example.py
```

This demonstrates:
- Bearer token authentication
- API key authentication
- Custom metadata injection

### 5. Run Enhanced Bidirectional Streaming Example (BONUS)

```bash
python bidirectional_chat_example.py
```

This demonstrates:
- Real-time bidirectional communication
- Chat-like message streaming
- Advanced stream lifecycle management
- Response processing as they arrive
- Error handling and recovery

## Example Output

```
=== gRPC Adapter Example ===

1. Discovering gRPC services...
   Found services: ['example.v1.UserService', 'example.v1.EventService']

2. Listing capabilities...
   UserService.GetUser (unary)
   UserService.ListUsers (server streaming)
   EventService.StreamEvents (server streaming)

3. Invoking GetUser (unary RPC)...
   Response: {'user_id': '123', 'name': 'Alice', 'email': 'alice@example.com'}

4. Streaming events (server streaming)...
   Event 1: {'event_id': '1', 'type': 'user.created', 'timestamp': 1234567890}
   Event 2: {'event_id': '2', 'type': 'user.updated', 'timestamp': 1234567891}
   Event 3: {'event_id': '3', 'type': 'user.deleted', 'timestamp': 1234567892}

Done!
```

## Integration with SARK

To use the gRPC adapter in SARK:

```python
from sark.adapters.grpc_adapter import GRPCAdapter
from sark.adapters.registry import get_registry

# Register adapter
registry = get_registry()
registry.register(GRPCAdapter())

# Discover and register gRPC service
discovery_config = {
    "host": "grpc.example.com",
    "port": 50051,
    "use_tls": True,
    "auth": {
        "type": "bearer",
        "token": "your-token-here"
    }
}

resources = await grpc_adapter.discover_resources(discovery_config)

# Resources are now governed by SARK policies
```

## Authentication Examples

### Bearer Token (OAuth, JWT)

```python
auth_config = {
    "type": "bearer",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### API Key

```python
auth_config = {
    "type": "apikey",
    "token": "sk-1234567890abcdef",
    "header_name": "x-api-key"
}
```

### mTLS

```python
auth_config = {
    "type": "mtls",
    "cert_path": "/path/to/client-cert.pem",
    "key_path": "/path/to/client-key.pem",
    "ca_path": "/path/to/ca-cert.pem"
}
```

## Custom Metadata

```python
auth_config = {
    "type": "bearer",
    "token": "your-token",
    "metadata": {
        "x-client-id": "client-123",
        "x-api-version": "v1",
        "x-request-id": "req-456"
    }
}
```

## Health Checking

The adapter automatically uses the gRPC Health Checking Protocol if available,
or falls back to reflection-based health checks.

```python
is_healthy = await adapter.health_check(resource)
print(f"Service health: {'UP' if is_healthy else 'DOWN'}")
```

## Error Handling

The adapter provides detailed error information:

```python
from sark.adapters.exceptions import (
    DiscoveryError,
    ConnectionError,
    AuthenticationError,
    InvocationError,
    StreamingError
)

try:
    result = await adapter.invoke(request)
except AuthenticationError as e:
    print(f"Auth failed: {e.message}")
    print(f"Details: {e.details}")
except InvocationError as e:
    print(f"Invocation failed: {e.message}")
    print(f"gRPC code: {e.details.get('grpc_code')}")
```

## Testing

Run the test suite:

```bash
pytest tests/adapters/test_grpc_adapter.py -v
```

## References

- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [gRPC Reflection Guide](https://github.com/grpc/grpc/blob/master/doc/server-reflection.md)
- [SARK Protocol Adapter Specification](../../docs/v2.0/PROTOCOL_ADAPTER_SPEC.md)
- [GRID Protocol Specification](../../GRID_PROTOCOL_SPECIFICATION_v0.1.md)
