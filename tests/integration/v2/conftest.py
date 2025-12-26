"""
Shared fixtures for SARK v2.0 integration tests.

Provides fixtures for:
- Mock protocol adapters (MCP, HTTP, gRPC)
- Multi-protocol scenarios
- Federation node simulation
- Adapter registry testing
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sark.adapters.base import ProtocolAdapter
from sark.adapters.registry import AdapterRegistry, reset_registry
from sark.models.base import (
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
    ResourceSchema,
)

# ============================================================================
# Mock Adapters
# ============================================================================


class MockMCPAdapter(ProtocolAdapter):
    """Mock MCP adapter for testing."""

    @property
    def protocol_name(self) -> str:
        return "mcp"

    @property
    def protocol_version(self) -> str:
        return "2024-11-05"

    async def discover_resources(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """Mock MCP resource discovery."""
        return [
            ResourceSchema(
                id=f"mcp-{discovery_config.get('name', 'server')}",
                name=discovery_config.get("name", "Test MCP Server"),
                protocol="mcp",
                endpoint=discovery_config.get("command", "npx"),
                capabilities=[],
                metadata=discovery_config,
                sensitivity_level="medium",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]

    async def get_capabilities(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """Mock capability listing."""
        return [
            CapabilitySchema(
                id=f"{resource.id}-read_file",
                resource_id=resource.id,
                name="read_file",
                description="Read a file from the filesystem",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                output_schema={},
                metadata={},
                sensitivity_level="medium",
            ),
            CapabilitySchema(
                id=f"{resource.id}-list_files",
                resource_id=resource.id,
                name="list_files",
                description="List files in a directory",
                input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
                output_schema={},
                metadata={},
                sensitivity_level="low",
            ),
        ]

    async def validate_request(self, request: InvocationRequest) -> bool:
        """Mock request validation."""
        return True

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        """Mock MCP tool invocation."""
        return InvocationResult(
            success=True,
            result={"content": [{"type": "text", "text": "Mock MCP result"}]},
            metadata={"adapter": "mcp", "mock": True},
            duration_ms=10.5,
        )

    async def health_check(self, resource: ResourceSchema) -> bool:
        """Mock health check."""
        return True


class MockHTTPAdapter(ProtocolAdapter):
    """Mock HTTP/REST adapter for testing."""

    @property
    def protocol_name(self) -> str:
        return "http"

    @property
    def protocol_version(self) -> str:
        return "1.1"

    async def discover_resources(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """Mock HTTP API discovery via OpenAPI."""
        base_url = discovery_config.get("base_url", "https://api.example.com")
        return [
            ResourceSchema(
                id=base_url,
                name=discovery_config.get("name", "Test REST API"),
                protocol="http",
                endpoint=base_url,
                capabilities=[],
                metadata={
                    "openapi_spec_url": discovery_config.get("openapi_spec_url"),
                    "auth_type": discovery_config.get("auth_type", "bearer"),
                },
                sensitivity_level="medium",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]

    async def get_capabilities(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """Mock HTTP endpoint capabilities."""
        return [
            CapabilitySchema(
                id=f"{resource.id}-GET-/users",
                resource_id=resource.id,
                name="list_users",
                description="List all users",
                input_schema={},
                output_schema={},
                metadata={
                    "http_method": "GET",
                    "http_path": "/users",
                },
                sensitivity_level="low",
            ),
            CapabilitySchema(
                id=f"{resource.id}-POST-/users",
                resource_id=resource.id,
                name="create_user",
                description="Create a new user",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                },
                output_schema={},
                metadata={
                    "http_method": "POST",
                    "http_path": "/users",
                },
                sensitivity_level="medium",
            ),
        ]

    async def validate_request(self, request: InvocationRequest) -> bool:
        """Mock HTTP request validation."""
        return True

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        """Mock HTTP API call."""
        return InvocationResult(
            success=True,
            result={"status": 200, "data": {"mock": "http_response"}},
            metadata={"adapter": "http", "mock": True},
            duration_ms=25.3,
        )

    async def health_check(self, resource: ResourceSchema) -> bool:
        """Mock HTTP health check."""
        return True


class MockGRPCAdapter(ProtocolAdapter):
    """Mock gRPC adapter for testing."""

    @property
    def protocol_name(self) -> str:
        return "grpc"

    @property
    def protocol_version(self) -> str:
        return "1.0"

    async def discover_resources(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """Mock gRPC service discovery via reflection."""
        endpoint = discovery_config.get("endpoint", "localhost:50051")
        return [
            ResourceSchema(
                id=f"grpc-{endpoint}",
                name=discovery_config.get("name", "Test gRPC Service"),
                protocol="grpc",
                endpoint=endpoint,
                capabilities=[],
                metadata={
                    "use_reflection": discovery_config.get("use_reflection", True),
                    "proto_files": discovery_config.get("proto_files", []),
                },
                sensitivity_level="medium",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]

    async def get_capabilities(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """Mock gRPC method capabilities."""
        return [
            CapabilitySchema(
                id=f"{resource.id}-UserService.GetUser",
                resource_id=resource.id,
                name="GetUser",
                description="Get user by ID",
                input_schema={"type": "object", "properties": {"user_id": {"type": "string"}}},
                output_schema={},
                metadata={
                    "service": "UserService",
                    "method": "GetUser",
                    "streaming": False,
                },
                sensitivity_level="medium",
            ),
            CapabilitySchema(
                id=f"{resource.id}-UserService.ListUsers",
                resource_id=resource.id,
                name="ListUsers",
                description="List all users (streaming)",
                input_schema={},
                output_schema={},
                metadata={
                    "service": "UserService",
                    "method": "ListUsers",
                    "streaming": True,
                },
                sensitivity_level="low",
            ),
        ]

    async def validate_request(self, request: InvocationRequest) -> bool:
        """Mock gRPC request validation."""
        return True

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        """Mock gRPC method invocation."""
        return InvocationResult(
            success=True,
            result={"user_id": "123", "name": "Mock User"},
            metadata={"adapter": "grpc", "mock": True},
            duration_ms=15.7,
        )

    async def health_check(self, resource: ResourceSchema) -> bool:
        """Mock gRPC health check."""
        return True

    async def invoke_streaming(self, request: InvocationRequest) -> AsyncIterator[Any]:
        """Mock streaming gRPC response."""
        for i in range(3):
            yield {"index": i, "data": f"chunk_{i}"}


# ============================================================================
# Adapter Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_adapter():
    """Provide mock MCP adapter instance."""
    return MockMCPAdapter()


@pytest.fixture
def mock_http_adapter():
    """Provide mock HTTP adapter instance."""
    return MockHTTPAdapter()


@pytest.fixture
def mock_grpc_adapter():
    """Provide mock gRPC adapter instance."""
    return MockGRPCAdapter()


@pytest.fixture
def adapter_registry():
    """Provide clean adapter registry for tests."""
    reset_registry()
    registry = AdapterRegistry()
    yield registry
    reset_registry()


@pytest.fixture
def populated_registry(adapter_registry, mock_mcp_adapter, mock_http_adapter, mock_grpc_adapter):
    """Provide registry populated with all mock adapters."""
    adapter_registry.register(mock_mcp_adapter)
    adapter_registry.register(mock_http_adapter)
    adapter_registry.register(mock_grpc_adapter)
    return adapter_registry


# ============================================================================
# Resource & Capability Fixtures
# ============================================================================


@pytest.fixture
def sample_mcp_resource():
    """Sample MCP resource for testing."""
    return ResourceSchema(
        id="mcp-filesystem",
        name="Filesystem MCP Server",
        protocol="mcp",
        endpoint="npx -y @modelcontextprotocol/server-filesystem",
        capabilities=[],
        metadata={
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        },
        sensitivity_level="high",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_http_resource():
    """Sample HTTP API resource for testing."""
    return ResourceSchema(
        id="https://api.github.com",
        name="GitHub API",
        protocol="http",
        endpoint="https://api.github.com",
        capabilities=[],
        metadata={
            "openapi_spec_url": "https://api.github.com/openapi.json",
            "auth_type": "bearer",
        },
        sensitivity_level="medium",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_grpc_resource():
    """Sample gRPC service resource for testing."""
    return ResourceSchema(
        id="grpc-localhost:50051",
        name="User Management Service",
        protocol="grpc",
        endpoint="localhost:50051",
        capabilities=[],
        metadata={
            "use_reflection": True,
            "proto_files": [],
        },
        sensitivity_level="medium",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_capability():
    """Generic capability for testing."""
    return CapabilitySchema(
        id="test-capability-1",
        resource_id="test-resource-1",
        name="test_operation",
        description="Test operation",
        input_schema={},
        output_schema={},
        metadata={},
        sensitivity_level="medium",
    )


@pytest.fixture
def sample_invocation_request(sample_capability):
    """Sample invocation request."""
    return InvocationRequest(
        capability_id=sample_capability.id,
        principal_id=str(uuid4()),
        arguments={"test": "data"},
        context={"source": "test"},
    )


# ============================================================================
# Federation Fixtures
# ============================================================================


@pytest.fixture
def mock_federation_node():
    """Mock federation node for testing."""
    node = MagicMock()
    node.name = "test-org"
    node.endpoint = "https://sark.test-org.com:8443"
    node.is_healthy = AsyncMock(return_value=True)
    node.authorize_remote = AsyncMock(return_value={"allow": True})
    node.query_resource = AsyncMock(return_value={"exists": True})
    return node


@pytest.fixture
def mock_federation_service():
    """Mock federation service for testing."""
    service = MagicMock()
    service.discover_nodes = AsyncMock(return_value=[])
    service.establish_trust = AsyncMock(return_value=True)
    service.query_remote_authorization = AsyncMock(return_value={"allow": True})
    service.audit_cross_org_access = AsyncMock()
    return service


# ============================================================================
# Multi-Protocol Scenario Fixtures
# ============================================================================


@pytest.fixture
def multi_protocol_scenario():
    """
    Multi-protocol orchestration scenario.

    Simulates a workflow that uses MCP -> HTTP -> gRPC in sequence.
    """
    return {
        "name": "Multi-Protocol Workflow",
        "steps": [
            {
                "protocol": "mcp",
                "resource_id": "mcp-filesystem",
                "capability": "read_file",
                "arguments": {"path": "/data/config.json"},
            },
            {
                "protocol": "http",
                "resource_id": "https://api.example.com",
                "capability": "create_user",
                "arguments": {"name": "test", "email": "test@example.com"},
            },
            {
                "protocol": "grpc",
                "resource_id": "grpc-localhost:50051",
                "capability": "GetUser",
                "arguments": {"user_id": "123"},
            },
        ],
    }


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with v2.0 integration test markers."""
    config.addinivalue_line("markers", "v2: mark test as SARK v2.0 test")
    config.addinivalue_line("markers", "adapter: mark test as adapter integration test")
    config.addinivalue_line("markers", "multi_protocol: mark test as multi-protocol test")
    config.addinivalue_line("markers", "federation: mark test as federation test")
    config.addinivalue_line("markers", "requires_adapters: mark test as requiring all adapters")
