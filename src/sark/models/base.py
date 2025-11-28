"""
Base models for SARK v2.0 protocol abstraction.

These base classes will be used by all protocol adapters in v2.0.
For v1.x, they serve as a foundation for gradual migration.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Column, String, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declared_attr
from pydantic import BaseModel as PydanticBaseModel


class ResourceBase:
    """
    Base class for all resource types (MCP servers, HTTP APIs, gRPC services, etc.).
    
    In v2.0, this will be the parent class for protocol-specific resource models.
    For v1.x, MCPServer can optionally inherit from this to prepare for migration.
    """
    
    @declared_attr
    def id(cls):
        """Unique resource identifier"""
        return Column(String, primary_key=True)
    
    @declared_attr
    def name(cls):
        """Human-readable resource name"""
        return Column(String, nullable=False, index=True)
    
    @declared_attr
    def protocol(cls):
        """Protocol type: 'mcp', 'http', 'grpc', etc."""
        return Column(String, nullable=False, index=True, default="mcp")
    
    @declared_attr
    def endpoint(cls):
        """Resource endpoint (command, URL, host:port, etc.)"""
        return Column(String, nullable=False)
    
    @declared_attr
    def sensitivity_level(cls):
        """Sensitivity classification: 'low', 'medium', 'high', 'critical'"""
        return Column(String, nullable=False, default="medium", index=True)
    
    @declared_attr
    def metadata(cls):
        """Protocol-specific metadata (JSON)"""
        return Column(JSON, default={})
    
    @declared_attr
    def created_at(cls):
        """Resource creation timestamp"""
        return Column(DateTime, nullable=False, default=datetime.utcnow)
    
    @declared_attr
    def updated_at(cls):
        """Resource last update timestamp"""
        return Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CapabilityBase:
    """
    Base class for all capability types (MCP tools, HTTP endpoints, gRPC methods, etc.).
    
    In v2.0, this will be the parent class for protocol-specific capability models.
    For v1.x, MCPTool can optionally inherit from this to prepare for migration.
    """
    
    @declared_attr
    def id(cls):
        """Unique capability identifier"""
        return Column(String, primary_key=True)
    
    @declared_attr
    def resource_id(cls):
        """ID of the resource this capability belongs to"""
        return Column(String, nullable=False, index=True)
    
    @declared_attr
    def name(cls):
        """Capability name"""
        return Column(String, nullable=False, index=True)
    
    @declared_attr
    def description(cls):
        """Capability description"""
        return Column(Text, nullable=True)
    
    @declared_attr
    def input_schema(cls):
        """Input schema (JSON Schema or protocol-specific)"""
        return Column(JSON, default={})
    
    @declared_attr
    def output_schema(cls):
        """Output schema (JSON Schema or protocol-specific)"""
        return Column(JSON, default={})
    
    @declared_attr
    def sensitivity_level(cls):
        """Sensitivity classification: 'low', 'medium', 'high', 'critical'"""
        return Column(String, nullable=False, default="medium", index=True)
    
    @declared_attr
    def metadata(cls):
        """Protocol-specific metadata (JSON)"""
        return Column(JSON, default={})


# Pydantic models for API requests/responses (v2.0 preview)

class ResourceSchema(PydanticBaseModel):
    """Generic resource schema for API"""
    id: str
    name: str
    protocol: str
    endpoint: str
    sensitivity_level: str = "medium"
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CapabilitySchema(PydanticBaseModel):
    """Generic capability schema for API"""
    id: str
    resource_id: str
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    sensitivity_level: str = "medium"
    metadata: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True


class InvocationRequest(PydanticBaseModel):
    """Universal invocation request (v2.0)"""
    capability_id: str
    principal_id: str
    arguments: Dict[str, Any]
    context: Dict[str, Any] = {}


class InvocationResult(PydanticBaseModel):
    """Universal invocation result (v2.0)"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    duration_ms: float


__all__ = [
    "ResourceBase",
    "CapabilityBase",
    "ResourceSchema",
    "CapabilitySchema",
    "InvocationRequest",
    "InvocationResult",
]