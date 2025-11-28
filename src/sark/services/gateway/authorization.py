"""Gateway authorization service.

Handles authorization decisions for Gateway operations including:
- Gateway tool invocations (OPA integration)
- Agent-to-Agent communication
- Server and tool filtering by permissions
"""

import structlog
from typing import Any

from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    A2AAuthorizationRequest,
    GatewayServerInfo,
    GatewayToolInfo,
    SensitivityLevel,
    AgentContext,
)
from sark.services.auth import UserContext

logger = structlog.get_logger()


async def authorize_gateway_request(
    user: UserContext,
    request: GatewayAuthorizationRequest,
) -> GatewayAuthorizationResponse:
    """
    Authorize Gateway request via OPA policy evaluation.

    Flow:
    1. Build OPA policy input from user context and request
    2. Query OPA for authorization decision
    3. Calculate cache TTL based on sensitivity
    4. Return decision with filtered parameters

    Args:
        user: User context from JWT
        request: Gateway authorization request

    Returns:
        Authorization decision with optional parameter filtering
    """
    try:
        # Build OPA input
        opa_input = {
            "user": {
                "id": str(user.user_id),
                "roles": user.roles,
                "permissions": user.permissions,
                "email": user.email,
            },
            "action": request.action,
            "resource": {
                "server": request.server_name,
                "tool": request.tool_name,
                "sensitivity": request.sensitivity_level.value if request.sensitivity_level else "medium",
            },
            "parameters": request.parameters or {},
            "context": request.context or {},
        }

        # Query OPA (placeholder - will integrate with actual OPA client)
        from sark.services.policy.opa import evaluate_policy

        opa_result = await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=opa_input,
        )

        # Extract decision
        allow = opa_result.get("result", {}).get("allow", False)
        reason = opa_result.get("result", {}).get("reason", "Policy evaluation completed")
        filtered_params = opa_result.get("result", {}).get("filtered_parameters")

        # Calculate cache TTL based on sensitivity
        cache_ttl = _get_cache_ttl(request.sensitivity_level)

        logger.info(
            "gateway_authorization_evaluated",
            user_id=str(user.user_id),
            action=request.action,
            server=request.server_name,
            tool=request.tool_name,
            allow=allow,
            cache_ttl=cache_ttl,
        )

        return GatewayAuthorizationResponse(
            allow=allow,
            reason=reason,
            filtered_parameters=filtered_params,
            cache_ttl=cache_ttl,
        )

    except Exception as e:
        logger.error(
            "gateway_authorization_error",
            error=str(e),
            user_id=str(user.user_id),
            action=request.action,
        )
        # Fail closed - deny on error
        return GatewayAuthorizationResponse(
            allow=False,
            reason=f"Authorization error: {str(e)}",
            cache_ttl=0,
        )


async def authorize_a2a_request(
    agent_context: AgentContext,
    request: A2AAuthorizationRequest,
) -> GatewayAuthorizationResponse:
    """
    Authorize agent-to-agent communication request.

    Flow:
    1. Validate trust levels (source agent can communicate with target)
    2. Check capability permissions
    3. Enforce A2A-specific restrictions (cross-environment, delegation)
    4. Return decision

    Args:
        agent_context: Agent context from JWT
        request: A2A authorization request

    Returns:
        Authorization decision for A2A communication
    """
    try:
        # Enforce A2A-specific restrictions
        restriction_result = await _enforce_a2a_restrictions(agent_context, request)
        if not restriction_result["allow"]:
            return GatewayAuthorizationResponse(
                allow=False,
                reason=restriction_result["reason"],
                cache_ttl=0,
            )

        # Build OPA input for A2A authorization
        opa_input = {
            "source_agent": {
                "id": agent_context.agent_id,
                "type": agent_context.agent_type.value,
                "trust_level": agent_context.trust_level.value,
                "capabilities": agent_context.capabilities,
                "environment": agent_context.environment,
            },
            "target_agent": {
                "id": request.target_agent_id,
                "environment": request.target_environment,
            },
            "capability": request.capability,
            "parameters": request.parameters or {},
            "context": request.context or {},
        }

        # Query OPA for A2A authorization
        from sark.services.policy.opa import evaluate_policy

        opa_result = await evaluate_policy(
            policy_path="/v1/data/mcp/a2a/allow",
            input_data=opa_input,
        )

        # Extract decision
        allow = opa_result.get("result", {}).get("allow", False)
        reason = opa_result.get("result", {}).get("reason", "A2A policy evaluation completed")

        # A2A requests get lower cache TTL for security
        cache_ttl = 60  # 1 minute

        logger.info(
            "a2a_authorization_evaluated",
            source_agent=agent_context.agent_id,
            target_agent=request.target_agent_id,
            capability=request.capability,
            allow=allow,
        )

        return GatewayAuthorizationResponse(
            allow=allow,
            reason=reason,
            cache_ttl=cache_ttl,
        )

    except Exception as e:
        logger.error(
            "a2a_authorization_error",
            error=str(e),
            source_agent=agent_context.agent_id,
            capability=request.capability,
        )
        # Fail closed - deny on error
        return GatewayAuthorizationResponse(
            allow=False,
            reason=f"A2A authorization error: {str(e)}",
            cache_ttl=0,
        )


async def filter_servers_by_permission(
    user: UserContext,
    servers: list[GatewayServerInfo],
) -> list[GatewayServerInfo]:
    """
    Filter servers by user permissions.

    Batch evaluates OPA policies to determine which servers user can access.

    Args:
        user: User context from JWT
        servers: List of all available servers

    Returns:
        List of servers user is authorized to access
    """
    try:
        authorized_servers = []

        for server in servers:
            # Build OPA input for server access
            opa_input = {
                "user": {
                    "id": str(user.user_id),
                    "roles": user.roles,
                    "permissions": user.permissions,
                },
                "action": "list",
                "resource": {
                    "type": "server",
                    "server": server.name,
                },
            }

            # Query OPA
            from sark.services.policy.opa import evaluate_policy

            opa_result = await evaluate_policy(
                policy_path="/v1/data/mcp/gateway/allow",
                input_data=opa_input,
            )

            if opa_result.get("result", {}).get("allow", False):
                authorized_servers.append(server)

        logger.info(
            "servers_filtered_by_permission",
            user_id=str(user.user_id),
            total_servers=len(servers),
            authorized_servers=len(authorized_servers),
        )

        return authorized_servers

    except Exception as e:
        logger.error(
            "server_filtering_error",
            error=str(e),
            user_id=str(user.user_id),
        )
        # Fail closed - return empty list on error
        return []


async def filter_tools_by_permission(
    user: UserContext,
    tools: list[GatewayToolInfo],
) -> list[GatewayToolInfo]:
    """
    Filter tools by user permissions.

    Batch evaluates OPA policies to determine which tools user can invoke.

    Args:
        user: User context from JWT
        tools: List of all available tools

    Returns:
        List of tools user is authorized to invoke
    """
    try:
        authorized_tools = []

        for tool in tools:
            # Build OPA input for tool access
            opa_input = {
                "user": {
                    "id": str(user.user_id),
                    "roles": user.roles,
                    "permissions": user.permissions,
                },
                "action": "invoke",
                "resource": {
                    "type": "tool",
                    "server": tool.server_name,
                    "tool": tool.name,
                    "sensitivity": tool.sensitivity_level.value if tool.sensitivity_level else "medium",
                },
            }

            # Query OPA
            from sark.services.policy.opa import evaluate_policy

            opa_result = await evaluate_policy(
                policy_path="/v1/data/mcp/gateway/allow",
                input_data=opa_input,
            )

            if opa_result.get("result", {}).get("allow", False):
                authorized_tools.append(tool)

        logger.info(
            "tools_filtered_by_permission",
            user_id=str(user.user_id),
            total_tools=len(tools),
            authorized_tools=len(authorized_tools),
        )

        return authorized_tools

    except Exception as e:
        logger.error(
            "tool_filtering_error",
            error=str(e),
            user_id=str(user.user_id),
        )
        # Fail closed - return empty list on error
        return []


def _get_cache_ttl(sensitivity_level: SensitivityLevel | None) -> int:
    """
    Calculate cache TTL based on sensitivity level.

    Args:
        sensitivity_level: Sensitivity level of the resource

    Returns:
        Cache TTL in seconds
    """
    if not sensitivity_level:
        return 300  # 5 minutes default

    ttl_map = {
        SensitivityLevel.PUBLIC: 3600,      # 1 hour
        SensitivityLevel.LOW: 1800,         # 30 minutes
        SensitivityLevel.MEDIUM: 300,       # 5 minutes
        SensitivityLevel.HIGH: 60,          # 1 minute
        SensitivityLevel.CRITICAL: 0,       # No caching
    }

    return ttl_map.get(sensitivity_level, 300)


async def _enforce_a2a_restrictions(
    agent_context: AgentContext,
    request: A2AAuthorizationRequest,
) -> dict[str, Any]:
    """
    Enforce A2A-specific restrictions.

    Restrictions:
    - Cross-environment communication (untrusted agents cannot cross environments)
    - Trust level validation
    - Capability checks

    Args:
        agent_context: Source agent context
        request: A2A authorization request

    Returns:
        Dict with 'allow' (bool) and 'reason' (str)
    """
    from sark.models.gateway import TrustLevel

    # Block cross-environment for untrusted agents
    if agent_context.trust_level == TrustLevel.UNTRUSTED:
        if agent_context.environment != request.target_environment:
            return {
                "allow": False,
                "reason": "Untrusted agents cannot communicate across environments",
            }

    # Check if agent has required capability
    if request.capability not in agent_context.capabilities:
        return {
            "allow": False,
            "reason": f"Agent lacks required capability: {request.capability}",
        }

    # Prevent delegation chains (agents calling agents calling agents)
    if request.context and request.context.get("delegation_depth", 0) > 2:
        return {
            "allow": False,
            "reason": "Maximum delegation depth exceeded",
        }

    return {
        "allow": True,
        "reason": "A2A restrictions passed",
    }
