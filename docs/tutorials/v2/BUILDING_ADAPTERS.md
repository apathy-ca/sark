# Building Your First Adapter

**Tutorial Duration:** 30-45 minutes
**Skill Level:** Intermediate
**Prerequisites:** Python 3.11+, understanding of async/await, familiarity with the protocol you're adapting

---

## Introduction

SARK v2.0's power comes from its **protocol adapter pattern**. This tutorial teaches you how to build custom adapters to govern any machine-to-machine protocol.

By the end of this tutorial, you'll have built a complete adapter for **Slack's Web API**, allowing you to:
- Discover Slack workspace capabilities (channels, messages, files)
- Authorize Slack API calls through SARK
- Audit all Slack interactions
- Apply consistent policies across Slack and other protocols

---

## Table of Contents

1. [Understanding the ProtocolAdapter Interface](#understanding-the-protocoladapter-interface)
2. [Planning Your Adapter](#planning-your-adapter)
3. [Implementing the Slack Adapter](#implementing-the-slack-adapter)
4. [Testing Your Adapter](#testing-your-adapter)
5. [Registering and Using Your Adapter](#registering-and-using-your-adapter)
6. [Advanced Features](#advanced-features)
7. [Best Practices](#best-practices)

---

## Understanding the ProtocolAdapter Interface

Every SARK adapter implements the `ProtocolAdapter` abstract base class. Let's examine the required methods:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)

class ProtocolAdapter(ABC):
    """Base class for all protocol adapters."""

    # Required: Protocol identification
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Return protocol identifier (e.g., 'slack', 'http', 'mcp')"""
        pass

    @property
    @abstractmethod
    def protocol_version(self) -> str:
        """Return protocol version this adapter supports"""
        pass

    # Required: Resource discovery
    @abstractmethod
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[ResourceSchema]:
        """
        Discover resources for this protocol.

        Args:
            discovery_config: Protocol-specific configuration

        Returns:
            List of discovered resources with their capabilities
        """
        pass

    # Required: Capability management
    @abstractmethod
    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """Get all capabilities for a resource"""
        pass

    # Required: Request validation
    @abstractmethod
    async def validate_request(
        self,
        request: InvocationRequest
    ) -> bool:
        """Validate request before execution"""
        pass

    # Required: Capability invocation
    @abstractmethod
    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        """Execute a capability (SARK handles authorization)"""
        pass

    # Required: Health checking
    @abstractmethod
    async def health_check(
        self,
        resource: ResourceSchema
    ) -> bool:
        """Check if resource is healthy and accessible"""
        pass

    # Optional: Lifecycle hooks
    async def on_resource_registered(self, resource: ResourceSchema) -> None:
        """Called when a resource is registered with SARK"""
        pass

    async def on_resource_unregistered(self, resource: ResourceSchema) -> None:
        """Called when a resource is removed from SARK"""
        pass
```

**Key Concepts:**

- **Protocol Name & Version**: Unique identifier for your protocol
- **Discovery**: How to find and enumerate resources
- **Capabilities**: What actions can be performed on resources
- **Validation**: Ensure requests are well-formed
- **Invocation**: Execute the actual protocol-specific logic
- **Health Check**: Verify resource connectivity

---

## Planning Your Adapter

Before coding, plan how your protocol maps to SARK's abstractions:

### Slack API → SARK Mapping

| Slack Concept | SARK Abstraction | Example |
|---------------|------------------|---------|
| Workspace | Resource | "Acme Corp Workspace" |
| API Method | Capability | `chat.postMessage`, `files.upload` |
| OAuth Token | Authentication | Stored in resource metadata |
| API Call | Invocation | Calling `chat.postMessage` |
| Workspace Info | Discovery | List available methods |

### Configuration Schema

Define what information you need to discover a Slack workspace:

```python
# discovery_config for Slack
{
    "workspace_url": "https://acme.slack.com",
    "oauth_token": "xoxb-your-bot-token",
    "scopes": ["chat:write", "files:read", "channels:read"]
}
```

---

## Implementing the Slack Adapter

Let's build the adapter step-by-step.

### Step 1: Create the Adapter Class

Create `src/sark/adapters/slack_adapter.py`:

```python
"""
Slack Web API Adapter for SARK v2.0.

Supports governance of Slack workspaces through their Web API.
"""

import time
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
import uuid

import httpx
import structlog

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import (
    AdapterConfigurationError,
    DiscoveryError,
    InvocationError,
    ValidationError,
    ConnectionError as AdapterConnectionError,
)
from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)

logger = structlog.get_logger(__name__)


class SlackAdapter(ProtocolAdapter):
    """
    Protocol adapter for Slack Web API.

    Example usage:
        ```python
        adapter = SlackAdapter()

        # Discover a Slack workspace
        resources = await adapter.discover_resources({
            "workspace_url": "https://acme.slack.com",
            "oauth_token": "xoxb-..."
        })

        # Invoke a capability
        result = await adapter.invoke(InvocationRequest(
            capability_id="slack-chat.postMessage",
            principal_id="user-123",
            arguments={
                "channel": "#general",
                "text": "Hello from SARK!"
            }
        ))
        ```
    """

    # Slack API base URL
    SLACK_API_BASE = "https://slack.com/api"

    # Timeout for API calls
    DEFAULT_TIMEOUT = 30.0

    def __init__(self):
        """Initialize the Slack adapter."""
        self._http_client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)
        self._tokens: Dict[str, str] = {}  # resource_id -> oauth_token

    @property
    def protocol_name(self) -> str:
        """Return protocol identifier."""
        return "slack"

    @property
    def protocol_version(self) -> str:
        """Return Slack API version."""
        return "v2"  # Slack Web API v2
```

### Step 2: Implement Resource Discovery

```python
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[ResourceSchema]:
        """
        Discover Slack workspace and its available API methods.

        Args:
            discovery_config: {
                "workspace_url": "https://acme.slack.com",
                "oauth_token": "xoxb-...",
                "scopes": ["chat:write", ...]  # Optional
            }
        """
        logger.info("slack_discovery_started", config=discovery_config)

        # Validate configuration
        if "oauth_token" not in discovery_config:
            raise AdapterConfigurationError(
                "Missing required field: oauth_token"
            )

        workspace_url = discovery_config.get("workspace_url", "Unknown Workspace")
        oauth_token = discovery_config["oauth_token"]

        try:
            # Test authentication and get workspace info
            auth_response = await self._http_client.post(
                f"{self.SLACK_API_BASE}/auth.test",
                headers={"Authorization": f"Bearer {oauth_token}"}
            )
            auth_response.raise_for_status()
            auth_data = auth_response.json()

            if not auth_data.get("ok"):
                raise AdapterConnectionError(
                    f"Slack authentication failed: {auth_data.get('error')}"
                )

            workspace_name = auth_data.get("team", "Unknown Workspace")
            workspace_id = auth_data.get("team_id", str(uuid.uuid4()))

            # Store token for later invocations
            resource_id = f"slack-{workspace_id}"
            self._tokens[resource_id] = oauth_token

            # Define Slack API capabilities
            # (In a real adapter, you might discover these dynamically)
            capabilities = [
                CapabilitySchema(
                    id=f"{resource_id}-chat.postMessage",
                    resource_id=resource_id,
                    name="chat.postMessage",
                    description="Post a message to a channel",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "channel": {"type": "string"},
                            "text": {"type": "string"},
                            "thread_ts": {"type": "string"}
                        },
                        "required": ["channel", "text"]
                    },
                    sensitivity_level="medium"
                ),
                CapabilitySchema(
                    id=f"{resource_id}-files.upload",
                    resource_id=resource_id,
                    name="files.upload",
                    description="Upload a file to Slack",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "channels": {"type": "string"},
                            "content": {"type": "string"},
                            "filename": {"type": "string"}
                        },
                        "required": ["channels", "content"]
                    },
                    sensitivity_level="high"
                ),
                CapabilitySchema(
                    id=f"{resource_id}-channels.list",
                    resource_id=resource_id,
                    name="channels.list",
                    description="List all channels in workspace",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 100}
                        }
                    },
                    sensitivity_level="low"
                ),
                CapabilitySchema(
                    id=f"{resource_id}-users.list",
                    resource_id=resource_id,
                    name="users.list",
                    description="List all users in workspace",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 100}
                        }
                    },
                    sensitivity_level="medium"
                ),
            ]

            # Create resource
            resource = ResourceSchema(
                id=resource_id,
                name=workspace_name,
                protocol="slack",
                endpoint=workspace_url,
                capabilities=capabilities,
                metadata={
                    "team_id": workspace_id,
                    "team_url": auth_data.get("url"),
                    "scopes": discovery_config.get("scopes", [])
                },
                sensitivity_level="medium",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )

            logger.info(
                "slack_discovery_completed",
                resource_id=resource_id,
                capabilities_count=len(capabilities)
            )

            return [resource]

        except httpx.HTTPError as e:
            raise DiscoveryError(f"Failed to discover Slack workspace: {e}")
```

### Step 3: Implement Get Capabilities

```python
    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """Get all capabilities for a Slack workspace."""
        # Capabilities are discovered during resource discovery
        # Just return what's already stored
        return resource.capabilities
```

### Step 4: Implement Request Validation

```python
    async def validate_request(
        self,
        request: InvocationRequest
    ) -> bool:
        """
        Validate that a Slack API request is well-formed.

        Checks:
        - Capability exists
        - Required arguments are present
        - Arguments match schema
        """
        # Extract capability name from capability_id
        # Format: "slack-{team_id}-{method}"
        parts = request.capability_id.split("-")
        if len(parts) < 3:
            raise ValidationError(
                f"Invalid capability_id format: {request.capability_id}"
            )

        method = "-".join(parts[2:])  # e.g., "chat.postMessage"

        # Validate based on method
        if method == "chat.postMessage":
            if "channel" not in request.arguments:
                raise ValidationError("Missing required argument: channel")
            if "text" not in request.arguments:
                raise ValidationError("Missing required argument: text")

        elif method == "files.upload":
            if "channels" not in request.arguments:
                raise ValidationError("Missing required argument: channels")
            if "content" not in request.arguments:
                raise ValidationError("Missing required argument: content")

        # Additional validation could check argument types, ranges, etc.

        return True
```

### Step 5: Implement Invocation

```python
    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        """
        Execute a Slack API method.

        Note: SARK core handles authorization before calling this method.
        This method only executes the protocol-specific logic.
        """
        start_time = time.time()

        # Extract resource_id and method from capability_id
        parts = request.capability_id.split("-")
        resource_id = "-".join(parts[:2])  # "slack-{team_id}"
        method = "-".join(parts[2:])       # e.g., "chat.postMessage"

        # Get OAuth token
        oauth_token = self._tokens.get(resource_id)
        if not oauth_token:
            return InvocationResult(
                success=False,
                error="OAuth token not found for resource",
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            # Call Slack API
            response = await self._http_client.post(
                f"{self.SLACK_API_BASE}/{method}",
                headers={"Authorization": f"Bearer {oauth_token}"},
                json=request.arguments
            )
            response.raise_for_status()
            data = response.json()

            # Check Slack's response
            if not data.get("ok"):
                return InvocationResult(
                    success=False,
                    error=data.get("error", "Unknown Slack API error"),
                    metadata={"slack_response": data},
                    duration_ms=(time.time() - start_time) * 1000
                )

            # Success
            return InvocationResult(
                success=True,
                result=data,
                metadata={
                    "method": method,
                    "response_metadata": data.get("response_metadata", {})
                },
                duration_ms=(time.time() - start_time) * 1000
            )

        except httpx.HTTPError as e:
            logger.error(
                "slack_invocation_failed",
                method=method,
                error=str(e)
            )
            return InvocationResult(
                success=False,
                error=f"HTTP error calling Slack API: {e}",
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.error(
                "slack_invocation_error",
                method=method,
                error=str(e),
                exc_info=True
            )
            return InvocationResult(
                success=False,
                error=f"Unexpected error: {e}",
                duration_ms=(time.time() - start_time) * 1000
            )
```

### Step 6: Implement Health Check

```python
    async def health_check(
        self,
        resource: ResourceSchema
    ) -> bool:
        """
        Check if Slack workspace is accessible.

        Tests authentication and connectivity.
        """
        resource_id = resource.id
        oauth_token = self._tokens.get(resource_id)

        if not oauth_token:
            logger.warning("health_check_no_token", resource_id=resource_id)
            return False

        try:
            response = await self._http_client.post(
                f"{self.SLACK_API_BASE}/auth.test",
                headers={"Authorization": f"Bearer {oauth_token}"},
                timeout=5.0
            )
            data = response.json()
            return data.get("ok", False)

        except Exception as e:
            logger.error(
                "health_check_failed",
                resource_id=resource_id,
                error=str(e)
            )
            return False
```

### Step 7: Implement Lifecycle Hooks (Optional)

```python
    async def on_resource_registered(self, resource: ResourceSchema) -> None:
        """Called when Slack workspace is registered with SARK."""
        logger.info(
            "slack_resource_registered",
            resource_id=resource.id,
            workspace=resource.name
        )

    async def on_resource_unregistered(self, resource: ResourceSchema) -> None:
        """Called when Slack workspace is removed from SARK."""
        # Clean up stored tokens
        if resource.id in self._tokens:
            del self._tokens[resource.id]

        logger.info(
            "slack_resource_unregistered",
            resource_id=resource.id,
            workspace=resource.name
        )
```

---

## Testing Your Adapter

Create comprehensive tests in `tests/adapters/test_slack_adapter.py`:

```python
"""Tests for Slack adapter."""

import pytest
from unittest.mock import AsyncMock, patch

from sark.adapters.slack_adapter import SlackAdapter
from sark.models.base import InvocationRequest, ResourceSchema


@pytest.mark.asyncio
class TestSlackAdapter:
    """Test suite for Slack adapter."""

    @pytest.fixture
    def adapter(self):
        """Create a Slack adapter instance."""
        return SlackAdapter()

    @pytest.fixture
    def mock_slack_response(self):
        """Mock successful Slack API response."""
        return {
            "ok": True,
            "team": "Acme Corp",
            "team_id": "T123456",
            "url": "https://acme.slack.com"
        }

    async def test_protocol_properties(self, adapter):
        """Test protocol name and version."""
        assert adapter.protocol_name == "slack"
        assert adapter.protocol_version == "v2"

    @patch("httpx.AsyncClient.post")
    async def test_discover_resources(self, mock_post, adapter, mock_slack_response):
        """Test discovering a Slack workspace."""
        mock_post.return_value = AsyncMock(
            json=lambda: mock_slack_response,
            raise_for_status=lambda: None
        )

        resources = await adapter.discover_resources({
            "workspace_url": "https://acme.slack.com",
            "oauth_token": "xoxb-test-token"
        })

        assert len(resources) == 1
        assert resources[0].name == "Acme Corp"
        assert resources[0].protocol == "slack"
        assert len(resources[0].capabilities) >= 4

    @patch("httpx.AsyncClient.post")
    async def test_invoke_post_message(self, mock_post, adapter):
        """Test invoking chat.postMessage."""
        # Setup
        adapter._tokens["slack-T123"] = "xoxb-test-token"
        mock_post.return_value = AsyncMock(
            json=lambda: {
                "ok": True,
                "message": {
                    "text": "Hello!",
                    "ts": "1234567890.123"
                }
            },
            raise_for_status=lambda: None
        )

        # Invoke
        request = InvocationRequest(
            capability_id="slack-T123-chat.postMessage",
            principal_id="user-1",
            arguments={
                "channel": "#general",
                "text": "Hello!"
            }
        )
        result = await adapter.invoke(request)

        # Assert
        assert result.success is True
        assert result.result["ok"] is True
        assert result.duration_ms > 0

    async def test_validate_request_valid(self, adapter):
        """Test validating a valid request."""
        request = InvocationRequest(
            capability_id="slack-T123-chat.postMessage",
            principal_id="user-1",
            arguments={
                "channel": "#general",
                "text": "Hello!"
            }
        )

        is_valid = await adapter.validate_request(request)
        assert is_valid is True

    async def test_validate_request_missing_argument(self, adapter):
        """Test validating request with missing required argument."""
        request = InvocationRequest(
            capability_id="slack-T123-chat.postMessage",
            principal_id="user-1",
            arguments={
                "channel": "#general"
                # Missing required 'text' argument
            }
        )

        with pytest.raises(Exception):  # Should raise ValidationError
            await adapter.validate_request(request)

    @patch("httpx.AsyncClient.post")
    async def test_health_check_healthy(self, mock_post, adapter):
        """Test health check for healthy workspace."""
        adapter._tokens["slack-T123"] = "xoxb-test-token"
        mock_post.return_value = AsyncMock(
            json=lambda: {"ok": True}
        )

        resource = ResourceSchema(
            id="slack-T123",
            name="Test",
            protocol="slack",
            endpoint="https://test.slack.com",
            capabilities=[]
        )

        is_healthy = await adapter.health_check(resource)
        assert is_healthy is True
```

Run the tests:

```bash
pytest tests/adapters/test_slack_adapter.py -v
```

---

## Registering and Using Your Adapter

### Step 1: Register the Adapter

Add to `src/sark/adapters/__init__.py`:

```python
from sark.adapters.slack_adapter import SlackAdapter

# Export
__all__ = ["SlackAdapter", ...]
```

Register in `src/sark/adapters/registry.py`:

```python
from sark.adapters.slack_adapter import SlackAdapter

# In the registry initialization
def initialize_default_adapters():
    """Register all built-in adapters."""
    registry = AdapterRegistry()
    registry.register(MCPAdapter())
    registry.register(HTTPAdapter())
    registry.register(GRPCAdapter())
    registry.register(SlackAdapter())  # Add your adapter
    return registry
```

### Step 2: Use the Adapter

Now you can use your Slack adapter through SARK:

```bash
# Register a Slack workspace
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "slack",
    "discovery_config": {
      "workspace_url": "https://acme.slack.com",
      "oauth_token": "xoxb-your-token-here"
    }
  }'

# Invoke a Slack capability
curl -X POST http://localhost:8000/api/v2/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "capability_id": "slack-T123-chat.postMessage",
    "principal_id": "user-alice",
    "arguments": {
      "channel": "#general",
      "text": "Hello from SARK!"
    }
  }'
```

---

## Advanced Features

### Streaming Support

For protocols that support streaming (like SSE, WebSockets):

```python
from typing import AsyncIterator

async def invoke_streaming(
    self,
    request: InvocationRequest
) -> AsyncIterator[InvocationResult]:
    """Stream results for long-running operations."""
    # Example: Streaming Slack messages
    async for message in self._stream_messages(request.arguments["channel"]):
        yield InvocationResult(
            success=True,
            result=message,
            duration_ms=0  # Streaming
        )
```

### Caching

Cache expensive discovery operations:

```python
from functools import lru_cache
import asyncio

class SlackAdapter(ProtocolAdapter):
    def __init__(self):
        super().__init__()
        self._capability_cache: Dict[str, List[CapabilitySchema]] = {}
        self._cache_ttl = 300  # 5 minutes

    async def get_capabilities(self, resource: ResourceSchema):
        # Check cache
        if resource.id in self._capability_cache:
            return self._capability_cache[resource.id]

        # Fetch and cache
        capabilities = await self._fetch_capabilities(resource)
        self._capability_cache[resource.id] = capabilities

        # Schedule cache invalidation
        asyncio.create_task(self._invalidate_cache(resource.id))

        return capabilities
```

### Rate Limiting

Implement rate limiting to respect API limits:

```python
from asyncio import Semaphore

class SlackAdapter(ProtocolAdapter):
    def __init__(self):
        super().__init__()
        self._rate_limiter = Semaphore(20)  # Max 20 concurrent requests

    async def invoke(self, request: InvocationRequest):
        async with self._rate_limiter:
            # Rate-limited invocation
            return await self._do_invoke(request)
```

---

## Best Practices

### 1. Error Handling

Use SARK's exception hierarchy for consistent error handling:

```python
from sark.adapters.exceptions import (
    AdapterConfigurationError,    # Bad configuration
    DiscoveryError,                # Discovery failed
    ConnectionError,               # Can't connect
    ValidationError,               # Invalid request
    InvocationError,               # Execution failed
    TimeoutError,                  # Operation timed out
)
```

### 2. Logging

Use structured logging for observability:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("operation_started", resource_id=resource.id, operation="discovery")
logger.error("operation_failed", resource_id=resource.id, error=str(e))
```

### 3. Resource Cleanup

Always clean up resources in lifecycle hooks:

```python
async def on_resource_unregistered(self, resource):
    # Close connections
    if resource.id in self._connections:
        await self._connections[resource.id].close()
        del self._connections[resource.id]
```

### 4. Configuration Validation

Validate configuration early:

```python
def _validate_discovery_config(self, config: Dict[str, Any]):
    required_fields = ["oauth_token"]
    for field in required_fields:
        if field not in config:
            raise AdapterConfigurationError(f"Missing required field: {field}")
```

### 5. Documentation

Document your adapter thoroughly:

```python
class MyAdapter(ProtocolAdapter):
    """
    Protocol adapter for XYZ.

    Supports:
    - Feature A
    - Feature B
    - Feature C

    Configuration:
        discovery_config = {
            "field1": "value1",
            "field2": "value2"
        }

    Example:
        ```python
        adapter = MyAdapter()
        resources = await adapter.discover_resources(config)
        ```
    """
```

---

## Checklist: Is Your Adapter Complete?

Before submitting your adapter:

- [ ] Implements all required abstract methods
- [ ] Has comprehensive unit tests (>85% coverage)
- [ ] Handles errors gracefully with proper exceptions
- [ ] Includes docstrings and examples
- [ ] Validates configuration
- [ ] Performs health checks
- [ ] Cleans up resources on unregistration
- [ ] Uses structured logging
- [ ] Respects API rate limits (if applicable)
- [ ] Works with SARK's authorization flow

---

## Next Steps

Congratulations! You've built a complete protocol adapter for SARK v2.0.

**Continue learning:**

- **[Multi-Protocol Orchestration](MULTI_PROTOCOL_ORCHESTRATION.md)** - Combine multiple protocols in workflows
- **[Advanced Adapter Patterns](../v2.0/ADAPTER_DEVELOPMENT_GUIDE.md)** - Deep dive into adapter architecture
- **[Examples](../../examples/v2/custom-adapter-example/)** - More adapter examples

**Share your adapter:**

1. Submit a pull request to the SARK repository
2. Publish to PyPI as a plugin: `sark-adapter-{protocol}`
3. Join our community and showcase your work

---

**Happy building!** 🔧

SARK v2.0 - Build adapters for any protocol
