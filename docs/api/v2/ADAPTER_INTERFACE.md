# SARK v2.0: Protocol Adapter Interface

**Version:** 2.0.0
**Last Updated:** December 2025
**Status:** Frozen Specification for v2.0

---

## Table of Contents

- [Overview](#overview)
- [Interface Definition](#interface-definition)
- [Core Methods](#core-methods)
- [Advanced Methods](#advanced-methods)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Data Models](#data-models)
- [Implementation Guide](#implementation-guide)
- [Testing Your Adapter](#testing-your-adapter)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

The `ProtocolAdapter` interface is the foundation of SARK's protocol abstraction layer. It defines a standard contract that all protocol adapters must implement, enabling SARK to govern any machine-to-machine protocol through a unified interface.

### Design Principles

1. **Protocol Agnostic**: Core SARK logic knows nothing about specific protocols
2. **Consistent Abstractions**: All protocols map to Resource → Capability → Invocation
3. **Minimal Interface**: Only essential methods are required
4. **Extensible**: Optional methods for advanced features
5. **Type Safe**: Strong typing for better developer experience

### Adapter Responsibilities

An adapter is responsible for:

- **Discovery**: Finding resources and their capabilities
- **Translation**: Converting protocol-specific concepts to GRID abstractions
- **Execution**: Invoking capabilities in the native protocol
- **Health Checking**: Verifying resource availability
- **Error Handling**: Providing meaningful error messages

An adapter is **NOT** responsible for:

- Authorization (handled by SARK core)
- Audit logging (handled by SARK core)
- Rate limiting (handled by SARK core)
- Cost attribution (handled by cost service)

---

## Interface Definition

```python
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)

class ProtocolAdapter(ABC):
    """
    Abstract base class for all protocol adapters.

    Each adapter translates protocol-specific concepts into GRID's
    universal abstractions (Resource, Capability, Action).
    """

    # Required properties
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Protocol identifier (e.g., 'mcp', 'http', 'grpc')"""
        pass

    @property
    @abstractmethod
    def protocol_version(self) -> str:
        """Protocol version this adapter supports"""
        pass

    # Required methods
    @abstractmethod
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[ResourceSchema]:
        """Discover available resources"""
        pass

    @abstractmethod
    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """Get all capabilities for a resource"""
        pass

    @abstractmethod
    async def validate_request(
        self,
        request: InvocationRequest
    ) -> bool:
        """Validate request before execution"""
        pass

    @abstractmethod
    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        """Execute a capability"""
        pass

    @abstractmethod
    async def health_check(
        self,
        resource: ResourceSchema
    ) -> bool:
        """Check if resource is healthy"""
        pass
```

---

## Core Methods

### `protocol_name`

**Signature:**
```python
@property
def protocol_name(self) -> str
```

**Description:**
Returns the unique identifier for this protocol. Must be lowercase and alphanumeric (dashes allowed).

**Example:**
```python
@property
def protocol_name(self) -> str:
    return "mcp"  # or "http", "grpc", "custom-protocol"
```

**Requirements:**
- Must be unique across all registered adapters
- Should be lowercase
- No spaces (use dashes for multi-word names)

---

### `protocol_version`

**Signature:**
```python
@property
def protocol_version(self) -> str
```

**Description:**
Returns the version of the protocol that this adapter supports.

**Example:**
```python
@property
def protocol_version(self) -> str:
    return "2024-11-05"  # MCP version
    # or "1.1" for HTTP/1.1
    # or "3.0.0" for semantic versioning
```

---

### `discover_resources`

**Signature:**
```python
async def discover_resources(
    self,
    discovery_config: Dict[str, Any]
) -> List[ResourceSchema]
```

**Description:**
Discovers available resources using protocol-specific configuration. This is called when a user registers a new resource through the API.

**Parameters:**
- `discovery_config`: Protocol-specific configuration dictionary

**Returns:**
- List of discovered `ResourceSchema` objects (usually just one, but can be multiple)

**Example (MCP):**
```python
async def discover_resources(
    self,
    discovery_config: Dict[str, Any]
) -> List[ResourceSchema]:
    # discovery_config = {
    #     "transport": "stdio",
    #     "command": "npx",
    #     "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    # }

    # Start MCP server
    server = await self._start_mcp_server(
        command=discovery_config["command"],
        args=discovery_config["args"]
    )

    # Initialize and discover tools
    await server.initialize()
    tools = await server.list_tools()

    # Convert to GRID Resource
    resource = ResourceSchema(
        id=f"mcp-{server.name}",
        name=server.name,
        protocol="mcp",
        endpoint=f"{discovery_config['command']} {' '.join(discovery_config['args'])}",
        sensitivity_level="medium",
        metadata=discovery_config,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Convert tools to capabilities
    capabilities = [
        CapabilitySchema(
            id=f"{server.name}-{tool.name}",
            resource_id=resource.id,
            name=tool.name,
            description=tool.description,
            input_schema=tool.inputSchema,
            sensitivity_level="medium",
            metadata={"mcp_tool": tool.dict()}
        )
        for tool in tools
    ]

    # Store capabilities in resource (will be saved to DB by SARK core)
    resource.capabilities = capabilities

    return [resource]
```

**Example (HTTP):**
```python
async def discover_resources(
    self,
    discovery_config: Dict[str, Any]
) -> List[ResourceSchema]:
    # discovery_config = {
    #     "base_url": "https://api.example.com",
    #     "openapi_spec_url": "https://api.example.com/openapi.json"
    # }

    # Fetch OpenAPI spec
    async with httpx.AsyncClient() as client:
        response = await client.get(discovery_config["openapi_spec_url"])
        spec = response.json()

    # Parse capabilities from paths
    capabilities = []
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            capabilities.append(
                CapabilitySchema(
                    id=f"{method.upper()}-{path.replace('/', '-')}",
                    resource_id=discovery_config["base_url"],
                    name=operation.get("operationId", f"{method}_{path}"),
                    description=operation.get("summary"),
                    input_schema=operation.get("requestBody", {}),
                    output_schema=operation.get("responses", {}),
                    sensitivity_level="medium",
                    metadata={
                        "http_method": method.upper(),
                        "http_path": path
                    }
                )
            )

    resource = ResourceSchema(
        id=discovery_config["base_url"],
        name=spec["info"]["title"],
        protocol="http",
        endpoint=discovery_config["base_url"],
        sensitivity_level="medium",
        metadata={"openapi_version": spec["openapi"]},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    resource.capabilities = capabilities

    return [resource]
```

---

### `get_capabilities`

**Signature:**
```python
async def get_capabilities(
    self,
    resource: ResourceSchema
) -> List[CapabilitySchema]
```

**Description:**
Retrieves all capabilities for a given resource. This may re-query the resource or return cached capabilities.

**Parameters:**
- `resource`: The resource to query

**Returns:**
- List of `CapabilitySchema` objects

**Example:**
```python
async def get_capabilities(
    self,
    resource: ResourceSchema
) -> List[CapabilitySchema]:
    # For most adapters, capabilities are stored in the database
    # and this method just queries them. However, for dynamic
    # resources, you might re-query the resource.

    # Simple implementation (capabilities already in DB):
    return []  # SARK core will query DB

    # Dynamic implementation (re-query resource):
    server = await self._get_server(resource.id)
    tools = await server.list_tools()

    return [
        CapabilitySchema(
            id=f"{resource.id}-{tool.name}",
            resource_id=resource.id,
            name=tool.name,
            description=tool.description,
            input_schema=tool.inputSchema,
            sensitivity_level="medium",
            metadata={}
        )
        for tool in tools
    ]
```

---

### `validate_request`

**Signature:**
```python
async def validate_request(
    self,
    request: InvocationRequest
) -> bool
```

**Description:**
Validates an invocation request before execution. This is protocol-specific validation (e.g., checking argument types, required fields).

**Parameters:**
- `request`: The invocation request to validate

**Returns:**
- `True` if valid, `False` if invalid

**Raises:**
- `ValidationError`: If validation fails with details

**Example:**
```python
from sark.adapters.exceptions import ValidationError

async def validate_request(
    self,
    request: InvocationRequest
) -> bool:
    # Get capability from database
    capability = await self._get_capability(request.capability_id)

    # Validate arguments against input schema
    if "required" in capability.input_schema:
        required_fields = capability.input_schema["required"]
        missing = set(required_fields) - set(request.arguments.keys())

        if missing:
            raise ValidationError(
                f"Missing required fields: {missing}",
                missing_fields=list(missing)
            )

    # Protocol-specific validation
    # For example, MCP might validate JSON-RPC format
    # HTTP might validate headers and body format

    return True
```

---

### `invoke`

**Signature:**
```python
async def invoke(
    self,
    request: InvocationRequest
) -> InvocationResult
```

**Description:**
Executes a capability on a resource. This is where the actual protocol interaction happens.

**Important:** This method should NOT perform authorization checks. Authorization is handled by SARK core before `invoke()` is called.

**Parameters:**
- `request`: The invocation request

**Returns:**
- `InvocationResult` with success/failure and result data

**Example:**
```python
import time

async def invoke(
    self,
    request: InvocationRequest
) -> InvocationResult:
    start = time.time()

    try:
        # Get the MCP server instance
        server = await self._get_server_for_capability(request.capability_id)

        # Extract capability name from capability_id
        capability_name = request.capability_id.split("-")[-1]

        # Call the MCP tool
        result = await server.call_tool(
            name=capability_name,
            arguments=request.arguments
        )

        duration_ms = (time.time() - start) * 1000

        return InvocationResult(
            success=True,
            result=result.content,
            metadata={
                "mcp_is_error": result.isError if hasattr(result, 'isError') else False
            },
            duration_ms=duration_ms
        )

    except Exception as e:
        duration_ms = (time.time() - start) * 1000

        return InvocationResult(
            success=False,
            error=str(e),
            metadata={"error_type": type(e).__name__},
            duration_ms=duration_ms
        )
```

**HTTP Example:**
```python
async def invoke(
    self,
    request: InvocationRequest
) -> InvocationResult:
    start = time.time()

    try:
        # Parse capability ID to get HTTP method and path
        method, path_encoded = request.capability_id.split("-", 1)
        path = path_encoded.replace("-", "/")

        # Get resource to find base URL
        resource = await self._get_resource(request.capability_id)
        url = f"{resource.endpoint}{path}"

        # Make HTTP request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=request.arguments if method in ["POST", "PUT", "PATCH"] else None,
                params=request.arguments if method == "GET" else None,
                timeout=30.0
            )

            response.raise_for_status()

            return InvocationResult(
                success=True,
                result=response.json() if response.content else None,
                metadata={
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                },
                duration_ms=(time.time() - start) * 1000
            )

    except httpx.HTTPStatusError as e:
        return InvocationResult(
            success=False,
            error=f"HTTP {e.response.status_code}: {e.response.text}",
            metadata={"status_code": e.response.status_code},
            duration_ms=(time.time() - start) * 1000
        )
    except Exception as e:
        return InvocationResult(
            success=False,
            error=str(e),
            duration_ms=(time.time() - start) * 1000
        )
```

---

### `health_check`

**Signature:**
```python
async def health_check(
    self,
    resource: ResourceSchema
) -> bool
```

**Description:**
Checks if a resource is healthy and reachable. This is used for monitoring and should be lightweight.

**Parameters:**
- `resource`: The resource to check

**Returns:**
- `True` if healthy, `False` otherwise

**Example:**
```python
async def health_check(
    self,
    resource: ResourceSchema
) -> bool:
    try:
        # For MCP: try to initialize connection
        server = await self._get_server(resource.id)
        await server.initialize()
        return True

    except Exception:
        return False
```

**HTTP Example:**
```python
async def health_check(
    self,
    resource: ResourceSchema
) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                resource.endpoint,
                timeout=5.0
            )
            # Consider 2xx and 3xx as healthy
            return response.status_code < 400

    except Exception:
        return False
```

---

## Advanced Methods

These methods are optional but provide additional functionality.

### `invoke_streaming`

**Signature:**
```python
async def invoke_streaming(
    self,
    request: InvocationRequest
) -> AsyncIterator[Any]
```

**Description:**
Invoke a capability with streaming response support (SSE, gRPC streaming, WebSocket).

**Example:**
```python
async def invoke_streaming(
    self,
    request: InvocationRequest
) -> AsyncIterator[Any]:
    server = await self._get_server_for_capability(request.capability_id)
    capability_name = request.capability_id.split("-")[-1]

    # For MCP SSE streaming
    async for chunk in server.call_tool_streaming(
        name=capability_name,
        arguments=request.arguments
    ):
        yield chunk
```

---

### `invoke_batch`

**Signature:**
```python
async def invoke_batch(
    self,
    requests: List[InvocationRequest]
) -> List[InvocationResult]
```

**Description:**
Invoke multiple capabilities in a batch for better performance.

**Default Behavior:**
The base class provides a default implementation that calls `invoke()` sequentially. Override this for protocols that support true batch operations.

**Example:**
```python
async def invoke_batch(
    self,
    requests: List[InvocationRequest]
) -> List[InvocationResult]:
    # For HTTP batch API
    batch_request = {
        "requests": [
            {
                "method": self._parse_method(req.capability_id),
                "url": self._parse_url(req.capability_id),
                "body": req.arguments
            }
            for req in requests
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.base_url}/batch",
            json=batch_request
        )
        batch_response = response.json()

    results = []
    for i, item in enumerate(batch_response["responses"]):
        if item["status"] < 400:
            results.append(InvocationResult(
                success=True,
                result=item["body"],
                metadata={"status_code": item["status"]},
                duration_ms=item.get("duration_ms", 0)
            ))
        else:
            results.append(InvocationResult(
                success=False,
                error=item["error"],
                metadata={"status_code": item["status"]},
                duration_ms=item.get("duration_ms", 0)
            ))

    return results
```

---

### `authenticate`

**Signature:**
```python
async def authenticate(
    self,
    resource: ResourceSchema,
    credentials: Dict[str, Any]
) -> Dict[str, Any]
```

**Description:**
Handle protocol-specific authentication (OAuth, API keys, mTLS).

**Example:**
```python
async def authenticate(
    self,
    resource: ResourceSchema,
    credentials: Dict[str, Any]
) -> Dict[str, Any]:
    if credentials["type"] == "oauth2":
        # OAuth2 flow
        token = await self._exchange_oauth_code(
            auth_code=credentials["code"],
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"]
        )

        return {
            "access_token": token["access_token"],
            "refresh_token": token["refresh_token"],
            "expires_at": token["expires_at"]
        }

    elif credentials["type"] == "api_key":
        # Validate API key
        is_valid = await self._validate_api_key(
            resource=resource,
            api_key=credentials["key"]
        )

        if not is_valid:
            raise AuthenticationError("Invalid API key")

        return {"api_key": credentials["key"]}

    else:
        raise UnsupportedOperationError(
            f"Authentication type {credentials['type']} not supported"
        )
```

---

## Lifecycle Hooks

### `on_resource_registered`

**Signature:**
```python
async def on_resource_registered(
    self,
    resource: ResourceSchema
) -> None
```

**Description:**
Called when a resource is registered. Use this for setup tasks like establishing connections, warming caches, etc.

**Example:**
```python
async def on_resource_registered(
    self,
    resource: ResourceSchema
) -> None:
    # Pre-establish connection pool
    self._connections[resource.id] = await self._create_connection(resource)

    # Warm cache
    capabilities = await self.get_capabilities(resource)
    self._capability_cache[resource.id] = capabilities
```

---

### `on_resource_unregistered`

**Signature:**
```python
async def on_resource_unregistered(
    self,
    resource: ResourceSchema
) -> None
```

**Description:**
Called when a resource is unregistered. Use this for cleanup tasks.

**Example:**
```python
async def on_resource_unregistered(
    self,
    resource: ResourceSchema
) -> None:
    # Close connection
    if resource.id in self._connections:
        await self._connections[resource.id].close()
        del self._connections[resource.id]

    # Clear cache
    self._capability_cache.pop(resource.id, None)
```

---

## Data Models

### ResourceSchema

```python
class ResourceSchema(BaseModel):
    id: str                          # Unique resource identifier
    name: str                        # Human-readable name
    protocol: str                    # Protocol type (mcp, http, grpc)
    endpoint: str                    # Connection endpoint
    sensitivity_level: str           # low, medium, high, critical
    metadata: Dict[str, Any]         # Protocol-specific metadata
    created_at: datetime
    updated_at: datetime
    capabilities: List[CapabilitySchema] = []  # Optional
```

### CapabilitySchema

```python
class CapabilitySchema(BaseModel):
    id: str                          # Unique capability identifier
    resource_id: str                 # Parent resource ID
    name: str                        # Capability name
    description: Optional[str]       # Description
    input_schema: Dict[str, Any]     # Input validation schema
    output_schema: Dict[str, Any]    # Output schema
    sensitivity_level: str           # low, medium, high, critical
    metadata: Dict[str, Any]         # Protocol-specific metadata
```

### InvocationRequest

```python
class InvocationRequest(BaseModel):
    capability_id: str               # Which capability to invoke
    principal_id: str                # Who is invoking
    arguments: Dict[str, Any]        # Capability arguments
    context: Dict[str, Any] = {}     # Additional context (IP, user agent, etc.)
```

### InvocationResult

```python
class InvocationResult(BaseModel):
    success: bool                    # True if successful
    result: Optional[Any] = None     # Result data (if successful)
    error: Optional[str] = None      # Error message (if failed)
    metadata: Dict[str, Any] = {}    # Additional metadata
    duration_ms: float               # Execution duration in milliseconds
```

---

## Implementation Guide

### Step 1: Create Your Adapter Class

```python
from sark.adapters.base import ProtocolAdapter
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)

class MyProtocolAdapter(ProtocolAdapter):
    """Adapter for MyProtocol."""

    @property
    def protocol_name(self) -> str:
        return "myprotocol"

    @property
    def protocol_version(self) -> str:
        return "1.0.0"

    # Implement all required methods...
```

### Step 2: Register Your Adapter

```python
from sark.adapters import get_registry

registry = get_registry()
registry.register(MyProtocolAdapter())
```

### Step 3: Test Your Adapter

See [Testing Your Adapter](#testing-your-adapter) section below.

---

## Testing Your Adapter

SARK provides a base test class for adapter testing:

```python
from tests.adapters.base_adapter_test import BaseAdapterTest
import pytest

class TestMyProtocolAdapter(BaseAdapterTest):
    @pytest.fixture
    def adapter(self):
        return MyProtocolAdapter()

    @pytest.fixture
    def discovery_config(self):
        return {
            "endpoint": "https://api.example.com",
            "api_key": "test-key"
        }

    @pytest.fixture
    def sample_resource(self):
        return ResourceSchema(
            id="test-resource",
            name="Test Resource",
            protocol="myprotocol",
            endpoint="https://api.example.com",
            sensitivity_level="medium",
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_capability(self):
        return CapabilitySchema(
            id="test-capability",
            resource_id="test-resource",
            name="test_action",
            description="A test capability",
            sensitivity_level="medium",
            metadata={}
        )

    @pytest.fixture
    def valid_invocation_request(self):
        return InvocationRequest(
            capability_id="test-capability",
            principal_id="test-user",
            arguments={"param": "value"}
        )
```

Run tests:

```bash
pytest tests/adapters/test_my_adapter.py -v
```

---

## Best Practices

### 1. Error Handling

Always return `InvocationResult` with proper error information:

```python
try:
    result = await do_something()
    return InvocationResult(success=True, result=result, duration_ms=...)
except SpecificError as e:
    logger.error("Specific error occurred", error=str(e))
    return InvocationResult(success=False, error=f"Specific error: {e}", duration_ms=...)
except Exception as e:
    logger.error("Unexpected error occurred", error=str(e), exc_info=True)
    return InvocationResult(success=False, error=f"Unexpected error: {e}", duration_ms=...)
```

### 2. Connection Management

Reuse connections for better performance:

```python
def __init__(self):
    self._client = httpx.AsyncClient()

async def invoke(self, request):
    # Reuse self._client instead of creating new one
    response = await self._client.request(...)
```

### 3. Timeouts

Always set reasonable timeouts:

```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url)
```

### 4. Logging

Use structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)

async def invoke(self, request):
    logger.info("Invoking capability",
                capability_id=request.capability_id,
                principal_id=request.principal_id)
    # ...
```

### 5. Metadata Storage

Store protocol-specific data in metadata fields:

```python
resource.metadata = {
    "auth_type": "oauth2",
    "token_url": "https://...",
    "custom_field": "value"
}

capability.metadata = {
    "http_method": "POST",
    "http_path": "/api/users",
    "rate_limit": 100
}
```

### 6. Capability IDs

Use a consistent naming scheme:

```python
# Good: protocol-resource-capability
capability_id = f"{protocol_name}-{resource_id}-{capability_name}"

# Example: "mcp-filesystem-read_file"
# Example: "http-example-api-POST-users"
```

---

## Examples

See the complete examples in the `/docs/v2.0/ADAPTER_DEVELOPMENT_GUIDE.md` file.

### Built-in Adapters

SARK v2.0 includes the following adapters:

- **MCPAdapter**: Model Context Protocol support
- **HTTPAdapter**: REST API support with OpenAPI discovery
- **GRPCAdapter**: gRPC service support with reflection

### Community Adapters

- **OpenAI Functions Adapter**: Govern OpenAI function calling
- **Anthropic Tools Adapter**: Govern Anthropic tool use
- **GraphQL Adapter**: Govern GraphQL APIs

---

## Adapter Checklist

Before submitting your adapter:

- [ ] All abstract methods implemented
- [ ] Protocol-specific concepts properly translated to GRID abstractions
- [ ] All tests passing (base test suite + custom tests)
- [ ] Test coverage ≥ 85%
- [ ] Protocol-specific configuration documented
- [ ] Error handling comprehensive
- [ ] Connection pooling implemented (if applicable)
- [ ] Timeouts configured
- [ ] Structured logging added
- [ ] README with usage examples

---

## Support

- **Adapter Development Guide**: `/docs/v2.0/ADAPTER_DEVELOPMENT_GUIDE.md`
- **Protocol Spec**: `/docs/v2.0/PROTOCOL_ADAPTER_SPEC.md`
- **GitHub Discussions**: https://github.com/yourusername/sark/discussions
- **Discord #adapter-development**: https://discord.gg/sark

---

**Document Version:** 1.0
**Last Updated:** December 2025
**Maintainer:** SARK Core Team
