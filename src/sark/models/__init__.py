"""Database models and schemas."""

# Handle both installed package (sark) and test environment (src.sark) imports
try:
    from sark.models.action import Action, ActionContext, ActionRequest, OperationType
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
    from sark.models.resource import (
        Classification,
        GridResource,
        ResourceStatus,
        ResourceTool,
        ResourceType,
    )
    from sark.models.session import (
        Session,
        SessionCreateRequest,
        SessionListResponse,
        SessionResponse,
    )
    from sark.models.principal import Principal, PrincipalType, Team
except ModuleNotFoundError:
    from .action import Action, ActionContext, ActionRequest, OperationType  # type: ignore
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
    from .resource import (  # type: ignore
        Classification,
        GridResource,
        ResourceStatus,
        ResourceTool,
        ResourceType,
    )
    from .session import (  # type: ignore
        Session,
        SessionCreateRequest,
        SessionListResponse,
        SessionResponse,
    )
    from .principal import Principal, PrincipalType, Team  # type: ignore

# Backward compatibility alias - to be deprecated
User = Principal  # Use Principal instead - User is deprecated

# v2.0 GRID-compliant models
# Resource is now a proper GRID-compliant model (not just an alias)
# Capability remains an alias for now (MCPTool -> ResourceTool migration)
Capability = MCPTool  # Will become generic Capability class in v2.0

__all__ = [
    "A2AAuthorizationRequest",
    # v2.0 Action model
    "Action",
    "ActionContext",
    "ActionRequest",
    "AgentContext",
    "AgentType",
    # Existing models
    "AuditEvent",
    "Capability",
    "CapabilityBase",
    "CapabilitySchema",
    "Classification",
    "GatewayAuditEvent",
    "GatewayAuthorizationRequest",
    "GatewayAuthorizationResponse",
    "GatewayServerInfo",
    "GatewayToolInfo",
    "GridResource",
    "InvocationRequest",
    "InvocationResult",
    "MCPServer",
    "MCPTool",
    "OperationType",
    "Policy",
    "PolicyVersion",
    "Principal",
    "PrincipalType",
    # v2.0 GRID-compliant models (Resource from base.py, GridResource from resource.py)
    "Resource",
    "ResourceStatus",
    "ResourceTool",
    "ResourceType",
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
