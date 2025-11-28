# SARK v2.0: Protocol Adapter Specification

**Version:** 1.0 (Draft)
**Status:** Specification for v2.0 implementation
**Created:** November 28, 2025

---

## Overview

This specification defines the `ProtocolAdapter` interface that enables SARK to govern any machine-to-machine protocol, not just MCP. Each adapter translates protocol-specific concepts into GRID's universal abstractions.

---

## Core Concept

SARK v2.0 uses adapters to support multiple protocols:

```
SARK Core (Protocol-Agnostic)
├─ Policy Evaluation (OPA)
├─ Audit Logging (TimescaleDB)
├─ Authentication
└─ Authorization
        ↓ Universal GRID Interface
┌───────┼───────┬───────┐
│       │       │       │
MCP   HTTP   gRPC   Custom
Adapter Adapter Adapter Adapter
```

---

## Universal Data Models

### Resource
Represents any governed entity (MCP server, REST API, gRPC service, etc.)

```python
class Resource(BaseModel):
    id: str
    name: str
    protocol: str  # "mcp", "http", "grpc"
    endpoint: str
    capabilities: List[Capability]
    metadata: Dict[str, Any] = {}
    sensitivity_level: str = "medium"
    created_at: datetime
    updated_at: datetime
```

### Capability
Represents an action that can be performed on a resource

```python
class Capability(BaseModel):
    id: str
    resource_id: str
    name: str
    description: Optional[str]
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    sensitivity_level: str = "medium"
```

### InvocationRequest
Universal request format

```python
class InvocationRequest(BaseModel):
    capability_id: str
    principal_id: str
    arguments: Dict[str, Any]
    context: Dict[str, Any] = {}
```

### InvocationResult
Universal response format

```python
class InvocationResult(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    duration_ms: float
```

---

## ProtocolAdapter Interface

```python
from abc import ABC, abstractmethod

class ProtocolAdapter(ABC):
    """Base class for all protocol adapters"""
    
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Protocol identifier (e.g., 'mcp', 'http')"""
        pass
    
    @property
    @abstractmethod
    def protocol_version(self) -> str:
        """Protocol version supported"""
        pass
    
    @abstractmethod
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[Resource]:
        """
        Discover available resources.
        
        Args:
            discovery_config: Protocol-specific discovery config
            
        Returns:
            List of discovered resources with capabilities
        """
        pass
    
    @abstractmethod
    async def get_capabilities(
        self,
        resource: Resource
    ) -> List[Capability]:
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
        """
        Execute a capability.
        
        Note: Authorization is handled by SARK core,
        not by the adapter.
        """
        pass
    
    @abstractmethod
    async def health_check(
        self,
        resource: Resource
    ) -> bool:
        """Check if resource is healthy"""
        pass
    
    # Optional lifecycle hooks
    async def on_resource_registered(self, resource: Resource) -> None:
        """Called when resource is registered"""
        pass
    
    async def on_resource_unregistered(self, resource: Resource) -> None:
        """Called when resource is unregistered"""
        pass
```

---

## Example: MCP Adapter

```python
class MCPAdapter(ProtocolAdapter):
    @property
    def protocol_name(self) -> str:
        return "mcp"
    
    @property
    def protocol_version(self) -> str:
        return "2024-11-05"
    
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[Resource]:
        # discovery_config = {
        #     "transport": "stdio",
        #     "command": "npx",
        #     "args": ["-y", "@modelcontextprotocol/server-filesystem"]
        # }
        
        server = await self._start_mcp_server(discovery_config)
        await server.initialize()
        tools = await server.list_tools()
        
        return [Resource(
            id=f"mcp-{server.name}",
            name=server.name,
            protocol="mcp",
            endpoint=discovery_config["command"],
            capabilities=[
                Capability(
                    id=f"{server.name}-{tool.name}",
                    resource_id=f"mcp-{server.name}",
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.inputSchema,
                    metadata={"mcp_tool": tool}
                )
                for tool in tools
            ],
            metadata=discovery_config,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )]
    
    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        start = time.time()
        try:
            server = await self._get_server(request.capability_id)
            result = await server.call_tool(
                name=request.capability_id.split("-")[-1],
                arguments=request.arguments
            )
            return InvocationResult(
                success=True,
                result=result.content,
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

## Example: HTTP Adapter

```python
class HTTPAdapter(ProtocolAdapter):
    @property
    def protocol_name(self) -> str:
        return "http"
    
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[Resource]:
        # discovery_config = {
        #     "base_url": "https://api.example.com",
        #     "openapi_spec_url": "https://api.example.com/openapi.json"
        # }
        
        spec = await self._fetch_openapi_spec(
            discovery_config["openapi_spec_url"]
        )
        
        capabilities = []
        for path, methods in spec["paths"].items():
            for method, operation in methods.items():
                capabilities.append(Capability(
                    id=f"{method.upper()}-{path}",
                    resource_id=discovery_config["base_url"],
                    name=operation.get("operationId", f"{method}_{path}"),
                    description=operation.get("summary"),
                    input_schema=operation.get("requestBody", {}),
                    metadata={"http_method": method.upper(), "http_path": path}
                ))
        
        return [Resource(
            id=discovery_config["base_url"],
            name=spec["info"]["title"],
            protocol="http",
            endpoint=discovery_config["base_url"],
            capabilities=capabilities,
            metadata={"openapi_version": spec["openapi"]},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )]
```

---

## Adapter Registry

```python
class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, ProtocolAdapter] = {}
    
    def register(self, adapter: ProtocolAdapter) -> None:
        self._adapters[adapter.protocol_name] = adapter
    
    def get(self, protocol: str) -> Optional[ProtocolAdapter]:
        return self._adapters.get(protocol)
    
    def list_protocols(self) -> List[str]:
        return list(self._adapters.keys())

# Global registry
registry = AdapterRegistry()

# Register built-in adapters
registry.register(MCPAdapter())
registry.register(HTTPAdapter())
registry.register(GRPCAdapter())
```

---

## Integration with SARK Core

### Resource Registration

```python
@router.post("/api/v2/resources")
async def register_resource(
    protocol: str,
    discovery_config: Dict[str, Any],
    db: Session = Depends(get_db)
):
    # Get adapter for protocol
    adapter = registry.get(protocol)
    if not adapter:
        raise HTTPException(404, f"Protocol '{protocol}' not supported")
    
    # Discover resources
    resources = await adapter.discover_resources(discovery_config)
    
    # Store in database
    for resource in resources:
        db.add(resource)
    db.commit()
    
    return resources
```

### Authorization Flow

```python
@router.post("/api/v2/authorize")
async def authorize_invocation(
    request: InvocationRequest,
    principal: Principal = Depends(get_current_principal)
):
    # Get capability and resource
    capability = db.query(Capability).get(request.capability_id)
    resource = db.query(Resource).get(capability.resource_id)
    
    # Get adapter
    adapter = registry.get(resource.protocol)
    
    # Validate request
    if not await adapter.validate_request(request):
        raise HTTPException(400, "Invalid request")
    
    # Evaluate policy (protocol-agnostic)
    decision = await policy_service.evaluate({
        "principal": principal,
        "resource": resource,
        "capability": capability,
        "action": "execute"
    })
    
    if not decision.allow:
        # Audit denial
        await audit_service.log_denial(principal, capability, decision.reason)
        raise HTTPException(403, decision.reason)
    
    # Execute via adapter
    result = await adapter.invoke(request)
    
    # Audit execution
    await audit_service.log_execution(principal, capability, result)
    
    return result
```

---

## Adapter Development Guide

### 1. Implement the Interface

```python
class MyProtocolAdapter(ProtocolAdapter):
    @property
    def protocol_name(self) -> str:
        return "myprotocol"
    
    # Implement all abstract methods...
```

### 2. Register the Adapter

```python
registry.register(MyProtocolAdapter())
```

### 3. Test the Adapter

```python
async def test_my_adapter():
    adapter = MyProtocolAdapter()
    
    # Test discovery
    resources = await adapter.discover_resources(config)
    assert len(resources) > 0
    
    # Test invocation
    result = await adapter.invoke(request)
    assert result.success
```

---

## Success Criteria

An adapter is complete when it:
- ✅ Implements all abstract methods
- ✅ Translates protocol concepts to GRID abstractions
- ✅ Passes adapter test suite
- ✅ Has >85% test coverage
- ✅ Documents protocol-specific configuration
- ✅ Handles errors gracefully

---

**Document Version:** 1.0
**Status:** Draft for v2.0 implementation
**Next Steps:** Implement MCPAdapter extraction, then HTTP/gRPC adapters