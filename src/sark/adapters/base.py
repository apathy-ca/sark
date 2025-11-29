"""
Base protocol adapter interface for SARK v2.0.

This module defines the abstract base class that all protocol adapters must implement.
Adapters translate protocol-specific concepts into GRID's universal abstractions.

Version: 2.0.0
Status: Frozen for Week 1 (foundation phase)
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
import structlog

from sark.models.base import (
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)
from sark.adapters.exceptions import (
    ValidationError,
    InvocationError,
    UnsupportedOperationError,
)

logger = structlog.get_logger(__name__)


class ProtocolAdapter(ABC):
    """
    Abstract base class for all protocol adapters.
    
    Each adapter translates protocol-specific concepts into GRID's
    universal abstractions (Resource, Capability, Action).
    
    This is the v2.0 interface. In v1.x, this serves as a specification
    for future implementation.
    """
    
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """
        Return the protocol identifier (e.g., 'mcp', 'http', 'grpc').
        
        Returns:
            str: Protocol name in lowercase
        """
        pass
    
    @property
    @abstractmethod
    def protocol_version(self) -> str:
        """
        Return the protocol version this adapter supports.
        
        Returns:
            str: Protocol version string
        """
        pass
    
    @abstractmethod
    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[ResourceSchema]:
        """
        Discover available resources for this protocol.

        This method is called when a new resource is being registered with SARK.
        It should connect to the resource, enumerate its capabilities, and return
        a structured representation.

        Args:
            discovery_config: Protocol-specific discovery configuration
                The structure of this dict varies by protocol (see examples)

        Returns:
            List of discovered resources with their capabilities.
            May return multiple resources if the discovery process finds more
            than one (e.g., discovering multiple gRPC services at an endpoint).

        Raises:
            DiscoveryError: If resource discovery fails
            ConnectionError: If cannot connect to the resource
            TimeoutError: If discovery operation times out
            AdapterConfigurationError: If discovery_config is invalid

        Example (MCP stdio transport):
            ```python
            discovery_config = {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "env": {"HOME": "/path/to/home"}
            }
            resources = await adapter.discover_resources(discovery_config)
            # Returns list with discovered MCP server and its tools
            ```

        Example (HTTP with OpenAPI):
            ```python
            discovery_config = {
                "base_url": "https://api.example.com",
                "openapi_spec_url": "https://api.example.com/openapi.json",
                "auth": {"type": "bearer", "token": "..."}
            }
            resources = await adapter.discover_resources(discovery_config)
            # Returns list with REST API and its endpoints as capabilities
            ```

        Example (gRPC with reflection):
            ```python
            discovery_config = {
                "host": "grpc.example.com",
                "port": 50051,
                "use_tls": True,
                "reflection": True
            }
            resources = await adapter.discover_resources(discovery_config)
            # Returns list with gRPC services and their methods
            ```
        """
        pass
    
    @abstractmethod
    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """
        Get all capabilities for a resource.

        This method retrieves the current list of capabilities (tools, endpoints,
        methods) available on a resource. Called during resource initialization
        and when capabilities need to be refreshed.

        Args:
            resource: The resource to query

        Returns:
            List of capabilities available on this resource.
            Returns empty list if resource has no capabilities.

        Raises:
            ResourceNotFoundError: If resource doesn't exist or is unreachable
            ConnectionError: If cannot connect to the resource
            TimeoutError: If operation times out
            ProtocolError: If protocol-specific error occurs

        Example:
            ```python
            resource = ResourceSchema(
                id="mcp-server-1",
                protocol="mcp",
                endpoint="npx @modelcontextprotocol/server-filesystem",
                ...
            )

            capabilities = await adapter.get_capabilities(resource)
            # [
            #     Capability(id="...", name="read_file", ...),
            #     Capability(id="...", name="write_file", ...),
            # ]
            ```
        """
        pass
    
    @abstractmethod
    async def validate_request(
        self,
        request: InvocationRequest
    ) -> bool:
        """
        Validate an invocation request before execution.
        
        Args:
            request: The invocation request to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If request is invalid with details
        """
        pass
    
    @abstractmethod
    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        """
        Invoke a capability on a resource.

        This is the core execution method. It receives a validated and authorized
        request and executes the protocol-specific invocation.

        Args:
            request: The invocation request containing:
                - capability_id: Which capability to invoke
                - principal_id: Who is invoking (for audit)
                - arguments: Invocation arguments
                - context: Additional context (optional)

        Returns:
            InvocationResult containing:
            - success: Whether invocation succeeded
            - result: The returned data (if successful)
            - error: Error message (if failed)
            - metadata: Additional metadata (timing, etc.)
            - duration_ms: Execution duration

        Raises:
            InvocationError: If the invocation fails
            CapabilityNotFoundError: If capability doesn't exist
            ConnectionError: If cannot connect to resource
            TimeoutError: If invocation times out
            ProtocolError: If protocol-specific error occurs

        Important:
            This method should NOT perform authorization checks.
            Authorization is handled by SARK core before calling invoke().
            This method only executes the protocol-specific invocation.

        Example:
            ```python
            request = InvocationRequest(
                capability_id="mcp-filesystem-read_file",
                principal_id="user-123",
                arguments={"path": "/etc/hosts"}
            )

            result = await adapter.invoke(request)
            if result.success:
                print(f"File content: {result.result}")
            else:
                print(f"Error: {result.error}")
            ```
        """
        pass
    
    @abstractmethod
    async def health_check(
        self,
        resource: ResourceSchema
    ) -> bool:
        """
        Check if a resource is healthy and reachable.
        
        Args:
            resource: The resource to check
            
        Returns:
            True if healthy and reachable, False otherwise
        """
        pass
    
    # Optional lifecycle hooks with default implementations
    
    async def on_resource_registered(
        self,
        resource: ResourceSchema
    ) -> None:
        """
        Lifecycle hook called when a resource is registered with SARK.

        This is called AFTER the resource is persisted to the database
        but BEFORE it's available for invocations.

        Override to perform protocol-specific setup (e.g., establish
        connections, warm caches, validate configuration).

        Args:
            resource: The newly registered resource

        Raises:
            ConnectionError: If setup fails (will prevent registration)
            AdapterConfigurationError: If resource config is invalid

        Example:
            ```python
            async def on_resource_registered(self, resource: ResourceSchema) -> None:
                # Establish persistent connection
                self._connections[resource.id] = await self._connect(resource.endpoint)
                # Warm capability cache
                await self._cache_capabilities(resource)
                logger.info("Resource ready", resource_id=resource.id)
            ```

        Note:
            If this method raises an exception, the resource registration
            will be rolled back and marked as failed.
        """
        pass

    async def on_resource_unregistered(
        self,
        resource: ResourceSchema
    ) -> None:
        """
        Lifecycle hook called when a resource is unregistered from SARK.

        This is called BEFORE the resource is removed from the database.

        Override to perform protocol-specific cleanup (e.g., close
        connections, release resources, clear caches).

        Args:
            resource: The resource being unregistered

        Raises:
            No exceptions should be raised from this method. Log errors instead.

        Example:
            ```python
            async def on_resource_unregistered(self, resource: ResourceSchema) -> None:
                # Close connection gracefully
                conn = self._connections.pop(resource.id, None)
                if conn:
                    await conn.close()
                # Clear cached data
                self._cache.delete(resource.id)
                logger.info("Resource cleanup complete", resource_id=resource.id)
            ```

        Note:
            This method should handle errors gracefully and not raise exceptions.
            Any raised exceptions will be logged but will not prevent unregistration.
        """
        pass

    # Enhanced methods for v2.0

    async def invoke_streaming(
        self,
        request: InvocationRequest
    ) -> AsyncIterator[Any]:
        """
        Invoke a capability with streaming response support.

        This method should be implemented by adapters that support streaming
        responses (e.g., SSE, gRPC streaming, WebSocket).

        Args:
            request: The invocation request

        Yields:
            Response chunks as they become available

        Raises:
            UnsupportedOperationError: If streaming is not supported by this adapter
            StreamingError: If streaming fails mid-stream
            ValidationError: If the request is invalid
            InvocationError: If the invocation fails

        Example (MCP SSE streaming):
            ```python
            request = InvocationRequest(
                capability_id="mcp-server-tool",
                principal_id="user-123",
                arguments={"query": "stream data"}
            )

            async for chunk in adapter.invoke_streaming(request):
                # chunk might be: {"type": "progress", "data": {...}}
                print(f"Received: {chunk}")
            ```

        Example (gRPC server streaming):
            ```python
            async for response in adapter.invoke_streaming(request):
                # response is a protobuf message
                process_grpc_response(response)
            ```

        Note:
            The default implementation raises UnsupportedOperationError.
            Adapters supporting streaming should override this method.
            Streaming is typically used for long-running operations or
            large result sets where incremental processing is beneficial.
        """
        # Make this an async generator that raises immediately
        # This allows it to be used with `async for` syntax
        raise UnsupportedOperationError(
            f"Streaming is not supported by {self.protocol_name} adapter",
            operation="invoke_streaming",
            adapter_name=self.protocol_name
        )
        # Make this unreachable code to satisfy the async generator requirement
        yield  # pragma: no cover

    async def invoke_batch(
        self,
        requests: List[InvocationRequest]
    ) -> List[InvocationResult]:
        """
        Invoke multiple capabilities in a batch operation.

        This method should be implemented by adapters that support
        batch/bulk operations for better performance.

        Args:
            requests: List of invocation requests

        Returns:
            List of invocation results (same order as requests)

        Raises:
            UnsupportedOperationError: If batch operations are not supported
            ValidationError: If any request is invalid

        Example (HTTP batch endpoint):
            ```python
            requests = [
                InvocationRequest(
                    capability_id="POST-/users",
                    principal_id="admin",
                    arguments={"name": "Alice"}
                ),
                InvocationRequest(
                    capability_id="POST-/users",
                    principal_id="admin",
                    arguments={"name": "Bob"}
                )
            ]

            results = await adapter.invoke_batch(requests)
            # All requests processed in single HTTP call
            for result in results:
                print(f"Success: {result.success}")
            ```

        Note:
            The default implementation calls invoke() sequentially.
            Adapters supporting true batch operations should override this
            for better performance (e.g., HTTP batch APIs, gRPC batch calls).
            Each result corresponds to the request at the same index.
            If one request fails, the adapter should still attempt remaining requests.
        """
        results = []
        for request in requests:
            try:
                result = await self.invoke(request)
                results.append(result)
            except Exception as e:
                # If one fails, still try the rest
                results.append(InvocationResult(
                    success=False,
                    error=str(e),
                    metadata={"batch_index": len(results)},
                    duration_ms=0.0
                ))
        return results

    async def refresh_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """
        Refresh the capabilities list for a resource.

        This method re-queries the resource to detect any new capabilities
        or changes to existing ones. Useful for resources that dynamically
        add/remove capabilities.

        Args:
            resource: The resource to refresh

        Returns:
            Updated list of capabilities

        Raises:
            DiscoveryError: If capability refresh fails

        Note:
            The default implementation calls get_capabilities().
            Adapters may override this for more efficient refresh logic.
        """
        return await self.get_capabilities(resource)

    async def authenticate(
        self,
        resource: ResourceSchema,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Authenticate to a resource using provided credentials.

        This method handles protocol-specific authentication (e.g., OAuth tokens,
        API keys, mTLS certificates).

        Args:
            resource: The resource to authenticate to
            credentials: Protocol-specific credentials dictionary

        Returns:
            Authentication result with tokens/session info

        Raises:
            AuthenticationError: If authentication fails
            UnsupportedOperationError: If auth is handled externally

        Example credentials formats:
            # API Key
            {"type": "api_key", "key": "sk-..."}

            # OAuth Bearer Token
            {"type": "bearer", "token": "eyJ..."}

            # Basic Auth
            {"type": "basic", "username": "user", "password": "pass"}

            # mTLS Certificate
            {"type": "mtls", "cert_path": "/path/to/cert.pem", "key_path": "/path/to/key.pem"}

        Note:
            The default implementation raises UnsupportedOperationError.
            Adapters requiring authentication should override this method.
        """
        raise UnsupportedOperationError(
            f"Authentication is handled externally for {self.protocol_name} adapter",
            operation="authenticate",
            adapter_name=self.protocol_name
        )

    def supports_streaming(self) -> bool:
        """
        Check if this adapter supports streaming responses.

        Returns:
            True if invoke_streaming() is implemented, False otherwise
        """
        # Check if invoke_streaming was overridden from the base implementation
        return (
            self.__class__.invoke_streaming
            != ProtocolAdapter.invoke_streaming
        )

    def supports_batch(self) -> bool:
        """
        Check if this adapter supports optimized batch operations.

        Returns:
            True if invoke_batch() is optimized, False if it uses default sequential impl
        """
        # Check if invoke_batch was overridden from the base implementation
        return (
            self.__class__.invoke_batch
            != ProtocolAdapter.invoke_batch
        )

    def get_adapter_info(self) -> Dict[str, Any]:
        """
        Get adapter metadata and capabilities.

        Returns:
            Dictionary with adapter information including:
            - protocol_name: Protocol identifier
            - protocol_version: Protocol version supported
            - adapter_class: Python class name
            - supports_streaming: Whether streaming is supported
            - supports_batch: Whether batch operations are optimized
            - module: Python module path
            - custom_metadata: Adapter-specific metadata (from get_adapter_metadata)

        Example:
            ```python
            info = adapter.get_adapter_info()
            # {
            #     "protocol_name": "mcp",
            #     "protocol_version": "2024-11-05",
            #     "adapter_class": "MCPAdapter",
            #     "supports_streaming": True,
            #     "supports_batch": False,
            #     "module": "sark.adapters.mcp_adapter",
            #     "custom_metadata": {"transport_types": ["stdio", "sse"]}
            # }
            ```
        """
        info = {
            "protocol_name": self.protocol_name,
            "protocol_version": self.protocol_version,
            "adapter_class": self.__class__.__name__,
            "supports_streaming": self.supports_streaming(),
            "supports_batch": self.supports_batch(),
            "module": self.__class__.__module__,
        }

        # Include custom metadata if provided
        custom = self.get_adapter_metadata()
        if custom:
            info["custom_metadata"] = custom

        return info

    def get_adapter_metadata(self) -> Dict[str, Any]:
        """
        Get adapter-specific metadata beyond the standard interface.

        Override this method to provide protocol-specific metadata such as:
        - Supported transport types
        - Feature flags
        - Configuration requirements
        - Version compatibility info

        Returns:
            Dictionary with adapter-specific metadata

        Example (MCP Adapter):
            ```python
            def get_adapter_metadata(self) -> Dict[str, Any]:
                return {
                    "transport_types": ["stdio", "sse", "http"],
                    "mcp_features": ["tools", "prompts", "resources"],
                    "max_concurrent_servers": 100,
                    "connection_pooling": True
                }
            ```

        Example (HTTP Adapter):
            ```python
            def get_adapter_metadata(self) -> Dict[str, Any]:
                return {
                    "supported_auth": ["bearer", "api_key", "oauth2"],
                    "openapi_versions": ["3.0", "3.1"],
                    "max_request_size_mb": 10
                }
            ```

        Note:
            The default implementation returns an empty dictionary.
            Adapters may override to provide additional metadata.
        """
        return {}

    def __repr__(self) -> str:
        """String representation of the adapter."""
        return f"<{self.__class__.__name__} protocol={self.protocol_name} version={self.protocol_version}>"


__all__ = ["ProtocolAdapter"]