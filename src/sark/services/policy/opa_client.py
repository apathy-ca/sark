"""Open Policy Agent client for authorization decisions."""

from typing import Any

import httpx
from pydantic import BaseModel
import structlog

from sark.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AuthorizationInput(BaseModel):
    """Authorization request input."""

    user: dict[str, Any]
    action: str
    tool: dict[str, Any] | None = None
    server: dict[str, Any] | None = None
    context: dict[str, Any]


class AuthorizationDecision(BaseModel):
    """Authorization decision response."""

    allow: bool
    reason: str
    filtered_parameters: dict[str, Any] | None = None
    audit_id: str | None = None


class OPAClient:
    """Client for interacting with Open Policy Agent."""

    def __init__(self, opa_url: str | None = None, timeout: float | None = None) -> None:
        """Initialize OPA client."""
        self.opa_url = opa_url or settings.opa_url
        self.timeout = timeout or settings.opa_timeout_seconds
        self.policy_path = settings.opa_policy_path
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def evaluate_policy(self, auth_input: AuthorizationInput) -> AuthorizationDecision:
        """
        Evaluate authorization policy via OPA.

        Args:
            auth_input: Authorization input containing user, action, tool, and context

        Returns:
            Authorization decision with allow/deny and reason

        Raises:
            httpx.HTTPError: If OPA request fails
        """
        try:
            response = await self.client.post(
                f"{self.opa_url}{self.policy_path}",
                json={"input": auth_input.model_dump()},
            )
            response.raise_for_status()

            result = response.json()

            # OPA returns {"result": {"allow": true, "reason": "..."}}
            policy_result = result.get("result", {})

            decision = AuthorizationDecision(
                allow=policy_result.get("allow", False),
                reason=policy_result.get("audit_reason", "Policy evaluation completed"),
                filtered_parameters=policy_result.get("filtered_parameters"),
                audit_id=policy_result.get("audit_id"),
            )

            logger.info(
                "policy_evaluated",
                decision=decision.allow,
                user_id=auth_input.user.get("id"),
                action=auth_input.action,
            )

            return decision

        except httpx.HTTPError as e:
            logger.error("opa_request_failed", error=str(e), opa_url=self.opa_url)
            # Fail closed - deny on error
            return AuthorizationDecision(
                allow=False,
                reason=f"Policy evaluation failed: {e!s}",
            )

        except Exception as e:
            logger.error("unexpected_error", error=str(e))
            # Fail closed
            return AuthorizationDecision(
                allow=False,
                reason="Internal error during policy evaluation",
            )

    async def check_tool_access(
        self,
        user_id: str,
        user_email: str,
        user_role: str,
        tool_name: str,
        tool_sensitivity: str,
        tool_owner_id: str | None = None,
        team_ids: list[str] | None = None,
    ) -> AuthorizationDecision:
        """
        Check if user has access to invoke a specific tool.

        Args:
            user_id: User identifier
            user_email: User email
            user_role: User role (developer, admin, etc.)
            tool_name: Tool name to check
            tool_sensitivity: Tool sensitivity level (low, medium, high, critical)
            tool_owner_id: Tool owner user ID
            team_ids: List of team IDs managing the tool

        Returns:
            Authorization decision
        """
        auth_input = AuthorizationInput(
            user={
                "id": user_id,
                "email": user_email,
                "role": user_role,
                "teams": team_ids or [],
            },
            action="tool:invoke",
            tool={
                "name": tool_name,
                "sensitivity_level": tool_sensitivity,
                "owner": tool_owner_id,
                "managers": team_ids or [],
            },
            context={
                "timestamp": (
                    httpx.get("https://worldtimeapi.org/api/ip").json()["unixtime"]
                    if settings.environment == "production"
                    else 0
                )
            },
        )

        return await self.evaluate_policy(auth_input)

    async def check_server_registration(
        self,
        user_id: str,
        user_email: str,
        user_role: str,
        server_name: str,
        server_sensitivity: str,
    ) -> AuthorizationDecision:
        """
        Check if user can register a new MCP server.

        Args:
            user_id: User identifier
            user_email: User email
            user_role: User role
            server_name: Server name to register
            server_sensitivity: Server sensitivity level

        Returns:
            Authorization decision
        """
        auth_input = AuthorizationInput(
            user={
                "id": user_id,
                "email": user_email,
                "role": user_role,
            },
            action="server:register",
            server={
                "name": server_name,
                "sensitivity_level": server_sensitivity,
            },
            context={"timestamp": 0},
        )

        return await self.evaluate_policy(auth_input)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
