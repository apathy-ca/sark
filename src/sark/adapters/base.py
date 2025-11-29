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
        
        Args:
            discovery_config: Protocol-specific discovery configuration
            
        Returns:
            List of discovered resources with their capabilities
            
        Example (MCP):
            discovery_config = {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"]
            }
        
        Example (HTTP):
            discovery_config = {
                "base_url": "https://api.example.com",
                "openapi_spec_url": "https://api.example.com/openapi.json"
            }
        """
        pass
    
    @abstractmethod
    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """
        Get all capabilities for a resource.
        
        Args:
            resource: The resource to query
            
        Returns:
            List of capabilities available on this resource
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
        
        Args:
            request: The invocation request
            
        Returns:
            The invocation result
            
        Note:
            This method should NOT perform authorization checks.
            Authorization is handled by SARK core before calling invoke().
            This method only executes the protocol-specific invocation.
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
        Called when a resource is registered.
        
        Override to perform protocol-specific setup (e.g., establish
        connections, warm caches, etc.).
        
        Args:
            resource: The newly registered resource
        """
        pass
    
    async def on_resource_unregistered(
        self,
        resource: ResourceSchema
    ) -> None:
        """
        Called when a resource is unregistered.

        Override to perform protocol-specific cleanup (e.g., close
        connections, release resources, etc.).

        Args:
            resource: The resource being unregistered
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

        Example:
            async for chunk in adapter.invoke_streaming(request):
                # Process each chunk as it arrives
                process(chunk)

        Note:
            The default implementation raises UnsupportedOperationError.
            Adapters supporting streaming should override this method.
        """
        raise UnsupportedOperationError(
            f"Streaming is not supported by {self.protocol_name} adapter",
            operation="invoke_streaming",
            adapter_name=self.protocol_name
        )

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

        Note:
            The default implementation calls invoke() sequentially.
            Adapters supporting true batch operations should override this
            for better performance (e.g., HTTP batch APIs, gRPC batch calls).
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
            Dictionary with adapter information
        """
        return {
            "protocol_name": self.protocol_name,
            "protocol_version": self.protocol_version,
            "adapter_class": self.__class__.__name__,
            "supports_streaming": self.supports_streaming(),
            "supports_batch": self.supports_batch(),
            "module": self.__class__.__module__,
        }

    def __repr__(self) -> str:
        """String representation of the adapter."""
        return f"<{self.__class__.__name__} protocol={self.protocol_name} version={self.protocol_version}>"


__all__ = ["ProtocolAdapter"]