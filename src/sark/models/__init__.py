"""Database models and schemas."""

# Handle both installed package (sark) and test environment (src.sark) imports
try:
    from sark.models.audit import AuditEvent
    from sark.models.base import (
        CapabilityBase,
        CapabilitySchema,
        InvocationRequest,
        InvocationResult,
        ResourceBase,
        ResourceSchema,
    )
    from sark.models.gateway import (
        A2AAuthorizationRequest,
        AgentContext,
        AgentType,
        GatewayAuditEvent,
        GatewayAuthorizationRequest,
        GatewayAuthorizationResponse,
        GatewayServerInfo,
        GatewayToolInfo,
        SensitivityLevel,
        TrustLevel,
    )
    from sark.models.mcp_server import MCPServer, MCPTool
    from sark.models.policy import Policy, PolicyVersion
    from sark.models.session import (
        Session,
        SessionCreateRequest,
        SessionListResponse,
        SessionResponse,
    )
    from sark.models.principal import Principal, PrincipalType, Team
except ModuleNotFoundError:
    from .audit import AuditEvent  # type: ignore
    from .base import (  # type: ignore
        CapabilityBase,
        CapabilitySchema,
        InvocationRequest,
        InvocationResult,
        ResourceBase,
        ResourceSchema,
    )
    from .gateway import (  # type: ignore
        A2AAuthorizationRequest,
        AgentContext,
        AgentType,
        GatewayAuditEvent,
        GatewayAuthorizationRequest,
        GatewayAuthorizationResponse,
        GatewayServerInfo,
        GatewayToolInfo,
        SensitivityLevel,
        TrustLevel,
    )
    from .mcp_server import MCPServer, MCPTool  # type: ignore
    from .policy import Policy, PolicyVersion  # type: ignore
    from .session import (  # type: ignore
        Session,
        SessionCreateRequest,
        SessionListResponse,
        SessionResponse,
    )
    from .principal import Principal, PrincipalType, Team  # type: ignore

# Backward compatibility alias - to be deprecated
User = Principal  # Use Principal instead - User is deprecated

# v2.0 type aliases - gradual terminology migration
# In v2.0, these will become actual base classes
# For v1.x, they're aliases to help adopt v2.0 terminology
Resource = MCPServer  # Will become generic Resource class in v2.0
Capability = MCPTool  # Will become generic Capability class in v2.0

__all__ = [
    "A2AAuthorizationRequest",
    "AgentContext",
    "AgentType",
    # Existing models
    "AuditEvent",
    "Capability",
    "CapabilityBase",
    "CapabilitySchema",
    "GatewayAuditEvent",
    "GatewayAuthorizationRequest",
    "GatewayAuthorizationResponse",
    "GatewayServerInfo",
    "GatewayToolInfo",
    "InvocationRequest",
    "InvocationResult",
    "MCPServer",
    "MCPTool",
    "Policy",
    "PolicyVersion",
    "Principal",
    "PrincipalType",
    # v2.0 type aliases
    "Resource",
    # v2.0 base classes
    "ResourceBase",
    "ResourceSchema",
    # Gateway models
    "SensitivityLevel",
    "Session",
    "SessionCreateRequest",
    "SessionListResponse",
    "SessionResponse",
    "Team",
    "TrustLevel",
    "User",  # Deprecated - use Principal
]
