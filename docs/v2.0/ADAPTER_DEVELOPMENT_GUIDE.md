# SARK v2.0: Adapter Development Guide

**Version:** 1.0
**Status:** Developer guide
**Created:** November 28, 2025

---

## Overview

This guide shows how to create a custom protocol adapter for SARK v2.0.

---

## Quick Start

### 1. Create Your Adapter Class

```python
from sark.adapters.base import ProtocolAdapter
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)
from typing import Dict, Any, List
import time

class MyProtocolAdapter(ProtocolAdapter):
    """Adapter for MyProtocol."""
    
    @property
    def protocol_name(self) -> str:
        return "myprotocol"
    
    @property
    def protocol_version(self) -> str:
        return "1.0.0"
    
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[ResourceSchema]:
        """Discover resources for your protocol."""
        # Your discovery logic here
        return []
    
    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """List capabilities for a resource."""
        # Your capability listing logic here
        return []
    
    async def validate_request(
        self,
        request: InvocationRequest
    ) -> bool:
        """Validate an invocation request."""
        # Your validation logic here
        return True
    
    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        """Execute a capability."""
        start = time.time()
        
        try:
            # Your invocation logic here
            result = {"message": "Success"}
            
            return InvocationResult(
                success=True,
                result=result,
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return InvocationResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )
    
    async def health_check(
        self,
        resource: ResourceSchema
    ) -> bool:
        """Check if resource is healthy."""
        # Your health check logic here
        return True
```

### 2. Register Your Adapter

```python
from sark.adapters import get_registry

# Get the global registry
registry = get_registry()

# Register your adapter
registry.register(MyProtocolAdapter())
```

### 3. Test Your Adapter

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
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
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

---

## Complete Example: REST API Adapter

```python
import httpx
from typing import Dict, Any, List
from sark.adapters.base import ProtocolAdapter
from sark.models.base import *

class RESTAPIAdapter(ProtocolAdapter):
    """Adapter for REST APIs with OpenAPI specs."""
    
    def __init__(self):
        self._clients: Dict[str, httpx.AsyncClient] = {}
    
    @property
    def protocol_name(self) -> str:
        return "rest"
    
    @property
    def protocol_version(self) -> str:
        return "1.0"
    
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[ResourceSchema]:
        """
        Discover REST API from OpenAPI spec.
        
        discovery_config format:
        {
            "base_url": "https://api.example.com",
            "openapi_url": "https://api.example.com/openapi.json",
            "auth": {"type": "bearer", "token": "..."}
        }
        """
        base_url = discovery_config["base_url"]
        openapi_url = discovery_config["openapi_url"]
        
        # Fetch OpenAPI spec
        async with httpx.AsyncClient() as client:
            response = await client.get(openapi_url)
            response.raise_for_status()
            spec = response.json()
        
        # Parse capabilities from OpenAPI paths
        capabilities = []
        for path, methods in spec.get("paths", {}).items():
            for method, operation in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    cap_id = f"{method.upper()}-{path.replace('/', '-')}"
                    capabilities.append(
                        CapabilitySchema(
                            id=cap_id,
                            resource_id=base_url,
                            name=operation.get("operationId", cap_id),
                            description=operation.get("summary", ""),
                            input_schema=operation.get("requestBody", {}),
                            output_schema=operation.get("responses", {}),
                            sensitivity_level="medium",
                            metadata={
                                "http_method": method.upper(),
                                "http_path": path,
                                "tags": operation.get("tags", [])
                            }
                        )
                    )
        
        # Create resource
        resource = ResourceSchema(
            id=base_url,
            name=spec.get("info", {}).get("title", "REST API"),
            protocol="rest",
            endpoint=base_url,
            sensitivity_level="medium",
            metadata={
                "openapi_version": spec.get("openapi", "3.0"),
                "auth": discovery_config.get("auth", {}),
                "spec_url": openapi_url
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store capabilities in resource metadata for now
        # In production, these would be stored in the database
        resource.capabilities = capabilities
        
        return [resource]
    
    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """Get capabilities from resource metadata."""
        return resource.capabilities if hasattr(resource, 'capabilities') else []
    
    async def validate_request(
        self,
        request: InvocationRequest
    ) -> bool:
        """Validate REST API request."""
        # Check capability ID format
        if not request.capability_id.count("-") >= 1:
            return False
        
        # Parse method and path
        parts = request.capability_id.split("-", 1)
        method = parts[0]
        
        # Validate HTTP method
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            return False
        
        return True
    
    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        """Execute REST API call."""
        start = time.time()
        
        try:
            # Parse capability ID
            method, path_encoded = request.capability_id.split("-", 1)
            path = path_encoded.replace("-", "/")
            
            # Get or create HTTP client
            # In production, use connection pooling
            async with httpx.AsyncClient() as client:
                # Build request
                url = f"{resource.endpoint}{path}"
                headers = self._build_headers(resource)
                
                # Make request
                response = await client.request(
                    method=method,
                    url=url,
                    json=request.arguments if method in ["POST", "PUT", "PATCH"] else None,
                    params=request.arguments if method == "GET" else None,
                    headers=headers,
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
    
    async def health_check(
        self,
        resource: ResourceSchema
    ) -> bool:
        """Check if REST API is reachable."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    resource.endpoint,
                    timeout=5.0
                )
                return response.status_code < 500
        except:
            return False
    
    def _build_headers(self, resource: ResourceSchema) -> Dict[str, str]:
        """Build HTTP headers from resource metadata."""
        headers = {"Content-Type": "application/json"}
        
        auth = resource.metadata.get("auth", {})
        if auth.get("type") == "bearer":
            headers["Authorization"] = f"Bearer {auth['token']}"
        elif auth.get("type") == "api_key":
            headers[auth.get("header", "X-API-Key")] = auth["key"]
        
        return headers
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
    return InvocationResult(success=False, error=f"Specific error: {e}", duration_ms=...)
except Exception as e:
    return InvocationResult(success=False, error=f"Unexpected error: {e}", duration_ms=...)
```

### 2. Connection Pooling

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

### 4. Metadata Usage

Store protocol-specific data in metadata:

```python
resource.metadata = {
    "auth_type": "oauth2",
    "token_url": "https://...",
    "custom_field": "value"
}
```

---

## Testing Your Adapter

Run the base adapter tests:

```bash
pytest tests/adapters/test_my_adapter.py -v
```

All tests should pass before registering your adapter.

---

**Document Version:** 1.0
**Status:** Developer guide for v2.0