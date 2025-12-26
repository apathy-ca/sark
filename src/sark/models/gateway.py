"""Gateway integration data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class SensitivityLevel(str, Enum):
    """Tool/server sensitivity classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GatewayServerInfo(BaseModel):
    """Gateway-managed MCP server information."""

    server_id: str = Field(..., description="Unique server identifier")
    server_name: str = Field(..., description="Human-readable server name")
    server_url: HttpUrl = Field(..., description="Server endpoint URL")
    sensitivity_level: SensitivityLevel = Field(default=SensitivityLevel.MEDIUM)
    authorized_teams: list[str] = Field(default_factory=list, description="Team IDs with access")
    access_restrictions: dict[str, Any] | None = Field(None, description="Custom access rules")
    health_status: str = Field(..., description="Current health status")
    tools_count: int = Field(ge=0, description="Number of available tools")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "server_id": "srv_abc123",
                "server_name": "postgres-mcp",
                "server_url": "http://postgres-mcp:8080",
                "sensitivity_level": "high",
                "authorized_teams": ["data-eng", "backend-dev"],
                "health_status": "healthy",
                "tools_count": 15,
            }
        }
    )


class GatewayToolInfo(BaseModel):
    """Gateway-discovered tool information."""

    tool_name: str = Field(..., description="Tool identifier")
    server_name: str = Field(..., description="Parent server name")
    description: str = Field(..., description="Tool description")
    sensitivity_level: SensitivityLevel = Field(default=SensitivityLevel.MEDIUM)
    parameters: list[dict[str, Any]] = Field(
        default_factory=list, description="Tool parameters schema"
    )
    sensitive_params: list[str] = Field(default_factory=list, description="Parameters to filter")
    required_capabilities: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tool_name": "execute_query",
                "server_name": "postgres-mcp",
                "description": "Execute SQL query on database",
                "sensitivity_level": "high",
                "parameters": [
                    {"name": "query", "type": "string", "required": True},
                    {"name": "database", "type": "string", "required": True},
                ],
                "sensitive_params": ["password", "secret"],
            }
        }
    )


class AgentType(str, Enum):
    """Agent classification types."""

    SERVICE = "service"
    WORKER = "worker"
    QUERY = "query"


class TrustLevel(str, Enum):
    """Agent trust levels."""

    TRUSTED = "trusted"
    LIMITED = "limited"
    UNTRUSTED = "untrusted"


class AgentContext(BaseModel):
    """Agent authentication context for A2A."""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_type: AgentType = Field(..., description="Agent classification")
    trust_level: TrustLevel = Field(default=TrustLevel.LIMITED)
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    environment: str = Field(..., description="Environment (dev/staging/prod)")
    rate_limited: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewayAuthorizationRequest(BaseModel):
    """Request to authorize a Gateway operation."""

    action: str = Field(..., description="Action to authorize (e.g., 'gateway:tool:invoke')")
    server_name: str | None = Field(None, description="Target server name")
    tool_name: str | None = Field(None, description="Tool to invoke")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Request parameters")
    gateway_metadata: dict[str, Any] = Field(default_factory=dict, description="Gateway context")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid_actions = [
            "gateway:tool:invoke",
            "gateway:server:list",
            "gateway:tool:discover",
            "gateway:server:info",
        ]
        if v not in valid_actions:
            raise ValueError(f"Action must be one of {valid_actions}")
        return v


class GatewayAuthorizationResponse(BaseModel):
    """Response from authorization request."""

    allow: bool = Field(..., description="Authorization decision")
    reason: str = Field(..., description="Human-readable reason")
    filtered_parameters: dict[str, Any] | None = Field(None, description="Sanitized parameters")
    audit_id: str | None = Field(None, description="Audit event ID")
    cache_ttl: int = Field(default=60, ge=0, description="Suggested cache TTL (seconds)")


class A2AAuthorizationRequest(BaseModel):
    """Agent-to-agent communication authorization request."""

    source_agent_id: str = Field(..., description="Source agent ID")
    target_agent_id: str = Field(..., description="Target agent ID")
    capability: str = Field(..., description="Requested capability (execute/query/delegate)")
    message_type: str = Field(..., description="Message type (request/response/notification)")
    payload_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability")
    @classmethod
    def validate_capability(cls, v: str) -> str:
        valid_capabilities = ["execute", "query", "delegate"]
        if v not in valid_capabilities:
            raise ValueError(f"Capability must be one of {valid_capabilities}")
        return v


class GatewayAuditEvent(BaseModel):
    """Audit event from Gateway."""

    event_type: str = Field(..., description="Event type (tool_invoke/a2a_communication/discovery)")
    user_id: str | None = Field(None, description="User ID (if user request)")
    agent_id: str | None = Field(None, description="Agent ID (if agent request)")
    server_name: str | None = Field(None)
    tool_name: str | None = Field(None)
    decision: str = Field(..., description="Authorization decision (allow/deny)")
    reason: str = Field(..., description="Decision reason")
    timestamp: int = Field(..., description="Unix timestamp")
    gateway_request_id: str = Field(..., description="Gateway request ID")
    metadata: dict[str, Any] = Field(default_factory=dict)
