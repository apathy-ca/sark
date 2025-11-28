"""Database models and schemas."""

from sark.models.audit import AuditEvent
from sark.models.mcp_server import MCPServer, MCPTool
from sark.models.policy import Policy, PolicyVersion
from sark.models.session import Session, SessionCreateRequest, SessionListResponse, SessionResponse
from sark.models.user import Team, User

# v2.0 base classes for protocol abstraction
from sark.models.base import (
    ResourceBase,
    CapabilityBase,
    ResourceSchema,
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
)

# v2.0 type aliases - gradual terminology migration
# In v2.0, these will become actual base classes
# For v1.x, they're aliases to help adopt v2.0 terminology
Resource = MCPServer  # Will become generic Resource class in v2.0
Capability = MCPTool  # Will become generic Capability class in v2.0

__all__ = [
    # Existing models
    "AuditEvent",
    "MCPServer",
    "MCPTool",
    "Policy",
    "PolicyVersion",
    "Session",
    "SessionCreateRequest",
    "SessionListResponse",
    "SessionResponse",
    "Team",
    "User",
    # v2.0 base classes
    "ResourceBase",
    "CapabilityBase",
    "ResourceSchema",
    "CapabilitySchema",
    "InvocationRequest",
    "InvocationResult",
    # v2.0 type aliases
    "Resource",
    "Capability",
]
