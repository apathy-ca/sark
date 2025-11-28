"""
Base protocol adapter interface for SARK v2.0.

This module defines the abstract base class that all protocol adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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
    
    def __repr__(self) -> str:
        """String representation of the adapter."""
        return f"<{self.__class__.__name__} protocol={self.protocol_name} version={self.protocol_version}>"


__all__ = ["ProtocolAdapter"]